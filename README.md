# Module-06---AI-in-Retail
GenAI-Powered Product Description Generator
# AI Product Description Generator

A small Flask web app that turns a product name and a list of keywords into an e-commerce product description using a **local LLM** (Option C: Ollama or LM Studio). It includes the optional stretch goal: tone selection and a rule-based decision layer.

## Features

- Takes a product name and comma-separated keywords
- Generates a description with a local small LLM (no API key, no cost, data stays on your machine)
- **Tone selection:** neutral, formal, casual, humorous, for young adults, for professionals
- **Decision layer:** rules inspect the keywords and add instructions to the prompt (for example, anti-greenwashing wording for sustainability keywords, no medical claims for health keywords, no fake urgency for sale keywords)
- **Claim flagging:** warns about unverifiable claims such as "guaranteed" or "clinically proven" so a human can review before publishing
- Friendly error messages when the LLM server is down, slow, or the model is missing

## Project structure

```
product-description-generator/
├── app.py               # Flask app, prompt building, LLM call
├── templates/
│   └── index.html       # Form and output page
└── README.md
```

## Requirements

- Python 3.8+
- [Ollama](https://ollama.com) (or LM Studio) running locally
- A small model, for example `gemma3`

## Setup

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   ```
2. Install the libraries:
   ```bash
   pip install flask requests
   ```
3. Install a model and make sure Ollama is running:
   ```bash
   ollama pull gemma3
   ```

## Run

```bash
python app.py
```

Open http://127.0.0.1:5000/ in your browser.

## Try it

| Product name | Keywords | Tone |
|---|---|---|
| Leather Boots | durable, stylish, waterproof | For professionals |
| Reusable Water Bottle | eco, recycled steel, leak-proof | Casual |
| Wireless Earbuds | long battery, noise cancelling | For young adults |

## Configuration

Settings are read from environment variables. All are optional.

| Variable | Default | Purpose |
|---|---|---|
| `LLM_BACKEND` | `ollama` | `ollama` or `lmstudio` |
| `LLM_URL` | `http://localhost:11434` | Server address (LM Studio: `http://localhost:1234`) |
| `LLM_MODEL` | `gemma3` | Model name, e.g. `phi3`, `qwen2.5` |

Examples:
```bash
LLM_MODEL=phi3 python app.py
LLM_BACKEND=lmstudio LLM_URL=http://localhost:1234 LLM_MODEL=your-model python app.py
```
On Windows PowerShell, set the variable first: `$env:LLM_MODEL="phi3"; python app.py`

## How it works

1. `parse_keywords` cleans the input: trims, removes duplicates, caps at 10 keywords.
2. `decide_prompt_rules` is the decision layer. It combines the chosen tone (style and length) with rules triggered by keywords.
3. `build_prompt` assembles the final prompt, including a rule that the model must not invent facts beyond the product name and keywords.
4. `call_llm` sends the prompt to Ollama or LM Studio.
5. `generate_description` handles errors and scans the output for risky claims.

## Troubleshooting

- **"Could not reach the LLM server":** start Ollama (`ollama serve`) or LM Studio's local server.
- **Error mentioning the model:** run `ollama pull <model>` and check that `LLM_MODEL` matches.
- **Slow or timed-out responses:** use a smaller model (for example `gemma3:1b`) or close other heavy programs.
- **Weak or off-topic output:** small models vary a lot. Try another model or adjust the rules in `decide_prompt_rules`.

## Ethical notes

LLMs can invent product details, so a human should review every description before it is published. This app tells the model not to fabricate facts and flags risky claims, but that is not a guarantee. In a real retail setting, also consider greenwashing, fake urgency, bias in segment-targeted tone, and disclosing AI-generated content to customers.

## Possible extensions

- Pull product attributes from a catalogue or database instead of free-text keywords
- A/B test generated descriptions against conversion data
- Multilingual output and SEO checks
- Generate several variants per request and let the user pick
