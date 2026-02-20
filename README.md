# Legal AI Plugin Tester

A Flask web app that benchmarks legal AI plugins by running them two ways simultaneously and letting an independent judge declare a winner.

![Split-screen UI showing Standard Analysis vs Doer/Reviewer Debate panels](https://placehold.co/900x400?text=Legal+AI+Plugin+Tester+UI)

---

## What It Does

Upload any legal document (contract, NDA, DPA, employment agreement, etc.) and choose a plugin. The app runs two analyses in parallel:

| Panel | How It Works |
|-------|-------------|
| **Standard Analysis** (left) | Single AI pass — one model reads the document and applies the plugin |
| **Doer/Reviewer Debate** (right) | Two AIs debate: Doer analyzes, Reviewer challenges, they argue for multiple rounds until consensus |
| **Final Review** (bottom) | Independent judge compares both outputs and declares a winner with reasoning |

---

## Plugins Included

| Plugin | What It Does |
|--------|-------------|
| `review-contract.md` | Full contract redline — flags risks, suggests fallback positions |
| `triage-nda.md` | NDA quick triage — approval / negotiate / reject recommendation |
| `brief.md` | Legal brief generator — topic, daily, or incident modes |
| `respond.md` | Draft legal responses — vendor questions, DSRs, NDA requests, litigation holds |
| `vendor-check.md` | Vendor legal audit — agreement gaps, expiry dates, action items |

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/legal-ai-plugin-test.git
cd legal-ai-plugin-test
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the app

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

### 4. Enter your API keys (BYOK)

Click **Set API Keys** in the top-right corner and enter your keys:

- **Anthropic key** — get one at [console.anthropic.com](https://console.anthropic.com)
- **Google key** — get one at [aistudio.google.com](https://aistudio.google.com)

> **Privacy:** Keys are stored in memory only for the duration of your session. They are never written to disk, logged, or transmitted anywhere except directly to the AI provider APIs.

---

## Usage

1. **Select a plugin** from the dropdown
2. **Upload a document** (PDF, DOCX, or TXT) — or paste text directly
3. **Add a context note** (see [PROMPTS.md](PROMPTS.md) for copy-paste templates)
4. **Click Run All** — both panels stream simultaneously
5. **Read the Final Review** at the bottom to see which approach won

### Context Notes

Context notes answer questions that the plugins would normally ask interactively (e.g., *"Which side are you on?"*, *"What mode do you want?"*). Without a context note the AI may pause and wait for input.

See **[PROMPTS.md](PROMPTS.md)** for ready-to-use templates for each plugin.

---

## Models

| Role | Default Model |
|------|--------------|
| Standard Analysis | `claude-sonnet-4-6` |
| Doer (Debate) | `claude-sonnet-4-6` |
| Reviewer (Debate) | `claude-opus-4-6` |
| Final Review Judge | `claude-opus-4-6` |

Models can be changed in `app.py` → `DEFAULT_MODELS`.

Google Gemini models (`gemini-3-flash-preview`, `gemini-3-pro-preview`) are also supported — just enter a Google API key.

---

## Project Structure

```
legal-ai-plugin-test/
├── app.py                          # Flask server + all SSE endpoints
├── requirements.txt
├── .gitignore
├── LICENSE
├── README.md
├── PROMPTS.md                      # Copy-paste context note templates
├── USER_GUIDE.md                   # Full user guide
│
├── review-contract.md              # Plugin: Contract Review
├── triage-nda.md                   # Plugin: NDA Triage
├── brief.md                        # Plugin: Legal Brief
├── respond.md                      # Plugin: Response Generation
├── vendor-check.md                 # Plugin: Vendor Check
│
├── src/
│   └── services/
│       ├── llm_service.py          # Unified LLM interface (Anthropic + Google)
│       ├── plugin_loader.py        # Loads plugins + automation preamble
│       ├── document_parser.py      # PDF / DOCX / TXT extraction
│       └── debate_orchestrator.py  # Doer/Reviewer debate engine
│
├── templates/
│   └── index.html                  # Split-screen UI
│
├── static/
│   ├── js/app.js                   # SSE streaming + UI logic
│   └── css/style.css
│
└── uploads/                        # Temp upload dir (contents gitignored)
    └── .gitkeep
```

---

## Architecture Notes

### SSE Streaming
All three analysis endpoints use Server-Sent Events over POST (not `EventSource` — requires `fetch` + `ReadableStream` on the frontend). This allows request bodies with the document and plugin configuration.

### Debate Orchestrator
The debate runs sequentially (not in parallel) — each LLM call waits for the previous one so the Reviewer can actually challenge the Doer's specific arguments. SSE events stream per-exchange, not per-token, during the debate.

### Automation Preamble
The plugin MD files were written as interactive Claude prompts. The app prepends an automation preamble to each plugin at load time, instructing the AI not to ask questions and to use the context note as its configuration input.

---

## Security

- **No API keys are ever stored on disk** — BYOK, memory-only
- **No database** — fully stateless, all data in-memory per session
- **Uploaded files are deleted** after text extraction
- **All user content is HTML-escaped** before display

---

## Requirements

- Python 3.9+
- Anthropic API key (for Claude models)
- Google AI API key (optional, for Gemini models)

```
flask>=3.0.0
anthropic>=0.40.0
google-genai>=1.0.0
PyPDF2>=3.0.0
pdfplumber>=0.10.0
python-docx>=1.1.0
gunicorn>=22.0.0
```

---

## License

MIT — see [LICENSE](LICENSE)
