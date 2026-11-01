"""
AI Product Description Generator (Flask + local LLM via Ollama)

Run:
    ollama pull gemma3          # or any small model: phi3, qwen2.5, ministral...
    pip install flask requests
    python app.py
Then open http://127.0.0.1:5000/
"""

import os
import re

import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# --- LLM configuration (Option C: local small LLM) ---------------------------
# Ollama:    http://localhost:11434   (default)
# LM Studio: set LLM_BACKEND=lmstudio and LLM_URL=http://localhost:1234
LLM_BACKEND = os.environ.get("LLM_BACKEND", "ollama")
LLM_URL = os.environ.get("LLM_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("LLM_MODEL", "gemma3")
REQUEST_TIMEOUT = 120  # seconds; small local models can be slow on CPU

# --- Stretch goal: tone options + programmable decision layer ----------------
# Each tone maps to a style guide, a target length, and a customer segment.
# The decision layer below turns user input into prompt rules (not just a
# string pasted into the prompt), so behaviour is explicit and testable.
TONES = {
    "neutral": {
        "label": "Neutral",
        "style": "Clear, factual and balanced.",
        "words": 70,
    },
    "formal": {
        "label": "Formal",
        "style": "Polished and precise. No slang, no exclamation marks.",
        "words": 80,
    },
    "casual": {
        "label": "Casual",
        "style": "Friendly and conversational, like a helpful shop assistant.",
        "words": 70,
    },
    "humorous": {
        "label": "Humorous",
        "style": "Light, witty, one gentle joke at most. Never mock the customer.",
        "words": 70,
    },
    "young adults": {
        "label": "For young adults",
        "style": "Energetic and trend-aware, short punchy sentences, "
                 "focused on lifestyle and self-expression.",
        "words": 55,
    },
    "professionals": {
        "label": "For professionals",
        "style": "Confident and efficient. Emphasise reliability, performance "
                 "and value for time.",
        "words": 80,
    },
}

# Claims a retailer cannot verify from keywords alone. Flagged after generation.
RISKY_CLAIMS = [
    r"\bguarantee[sd]?\b", r"\bbest in the world\b", r"\b#1\b", r"\bcures?\b",
    r"\bclinically proven\b", r"\b100% (safe|natural|organic)\b",
    r"\bnever (breaks?|fails?)\b", r"\bmiracle\b",
]


def parse_keywords(raw):
    """Split, trim, de-duplicate (case-insensitive) and cap keywords."""
    seen, keywords = set(), []
    for part in raw.split(","):
        word = part.strip()
        if word and word.lower() not in seen:
            seen.add(word.lower())
            keywords.append(word)
    return keywords[:10]


def decide_prompt_rules(product_name, keywords, tone_key):
    """
    Rule-based decision model: inspects the input and returns the rules the
    LLM must follow. This is the 'programmable' part of the AI.
    """
    tone = TONES[tone_key]
    rules = [
        f"Write about {tone['words']} words in one short paragraph.",
        f"Style: {tone['style']}",
        "Mention every keyword naturally; do not just list them.",
        "Only use facts implied by the product name and keywords. "
        "Do not invent materials, certifications, prices, awards or statistics.",
    ]
    joined = " ".join(keywords).lower()

    if any(k in joined for k in ("eco", "sustainable", "recycled", "organic")):
        rules.append(
            "If you mention sustainability, keep it modest and specific to the "
            "keywords given (avoid vague greenwashing like 'saves the planet')."
        )
    if any(k in joined for k in ("kids", "child", "baby", "toddler")):
        rules.append("Write for the parent or buyer. Avoid safety claims.")
    if any(k in joined for k in ("supplement", "vitamin", "skin", "health", "pain")):
        rules.append("Do not make medical or health-benefit claims.")
    if any(k in joined for k in ("sale", "discount", "deal", "limited")):
        rules.append("Do not use fake urgency such as 'only 2 left'.")
    return rules


def build_prompt(product_name, keywords, tone_key):
    rules = "\n".join(f"- {r}" for r in decide_prompt_rules(product_name, keywords, tone_key))
    return (
        "You are a retail copywriter writing an e-commerce product description.\n"
        f"Product: {product_name}\n"
        f"Keywords: {', '.join(keywords)}\n"
        f"Rules:\n{rules}\n"
        "Return only the description text, with no title, preamble or quotes."
    )


def call_llm(prompt):
    """Send the prompt to the local LLM server and return the text."""
    if LLM_BACKEND == "lmstudio":
        resp = requests.post(
            f"{LLM_URL}/v1/chat/completions",
            json={
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 250,
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    resp = requests.post(
        f"{LLM_URL}/api/chat",
        json={
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 250},
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def generate_description(product_name, keywords, tone="neutral"):
    """Return (description, warnings). Raises RuntimeError with a friendly message."""
    if tone not in TONES:
        tone = "neutral"
    prompt = build_prompt(product_name, keywords, tone)
    try:
        text = call_llm(prompt)
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Could not reach the LLM server at {LLM_URL}. "
            "Start Ollama (or LM Studio) and try again."
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("The model took too long to respond. Try a smaller model.")
    except requests.exceptions.HTTPError as err:
        raise RuntimeError(
            f"The LLM server returned an error ({err.response.status_code}). "
            f"Check that the model '{LLM_MODEL}' is installed."
        )
    except (KeyError, ValueError):
        raise RuntimeError("The LLM server sent a response the app could not read.")

    if not text:
        raise RuntimeError("The model returned an empty description. Try again.")

    warnings = [
        f"Check this claim before publishing: “{m.group(0)}”"
        for pattern in RISKY_CLAIMS
        for m in [re.search(pattern, text, re.IGNORECASE)]
        if m
    ]
    return text, warnings


@app.route("/", methods=["GET", "POST"])
def index():
    context = {
        "tones": TONES,
        "description": None,
        "warnings": [],
        "error": None,
        "form": {"product_name": "", "keywords": "", "tone": "neutral"},
        "model": LLM_MODEL,
    }

    if request.method == "POST":
        product_name = request.form.get("product_name", "").strip()
        raw_keywords = request.form.get("keywords", "")
        tone = request.form.get("tone", "neutral")
        context["form"] = {"product_name": product_name, "keywords": raw_keywords, "tone": tone}

        keywords = parse_keywords(raw_keywords)
        if not product_name or not keywords:
            context["error"] = "Enter a product name and at least one keyword."
        else:
            try:
                context["description"], context["warnings"] = generate_description(
                    product_name, keywords, tone
                )
            except RuntimeError as err:
                context["error"] = str(err)

    return render_template("index.html", **context)


if __name__ == "__main__":
    app.run(debug=True)