# Legal AI Plugin Test — User Guide

## What This App Does

This app runs the same legal document through **two AI approaches simultaneously**, then compares the results:

| Panel | What it does |
|-------|-------------|
| **Standard Analysis** (left) | One AI reads the document and runs the selected legal workflow start to finish |
| **Doer / Reviewer Debate** (right) | Two AIs argue about the analysis across multiple rounds until they reach consensus |
| **Final Review** (bottom) | A third independent AI compares both outputs and declares a winner |

The goal is to find out whether a structured debate between two AI agents produces a more accurate and thorough legal analysis than a single AI working alone.

---

## Step 1 — Get an API Key

You need at least one key. The app supports both providers; you do not need both.

| Provider | Where to get it | Models unlocked |
|----------|----------------|-----------------|
| **Anthropic** | [console.anthropic.com](https://console.anthropic.com) | Claude Sonnet 4.6, Claude Opus 4.6 |
| **Google** | [aistudio.google.com](https://aistudio.google.com) | Gemini 3 Flash, Gemini 3 Pro |

Anthropic is recommended for best results on legal analysis tasks.

---

## Step 2 — Start the App

```
python app.py
```

Then open **http://localhost:5000** in your browser.

---

## Step 3 — Enter Your API Key

At the top of the page, expand **🔑 API Keys**, paste your key, and click **Set Keys**. You will see a green confirmation message. You only need to do this once per browser session.

---

## Step 4 — Select a Plugin

Open **📂 Plugin & Document** and choose one of the five legal workflow plugins from the dropdown:

| Plugin | Best for |
|--------|----------|
| 📋 **Contract Review** | Any commercial contract — reviews clause by clause, flags RED / YELLOW / GREEN deviations |
| 🔍 **NDA Triage** | NDAs — rapid pass/fail screen against 12 standard criteria, routes to appropriate review level |
| 📰 **Legal Brief** | Generating a structured briefing (topic, daily, or incident) from a document |
| ✉️ **Response Generation** | Drafting responses to legal inquiries — DSRs, vendor questions, NDA requests, holds |
| 🏢 **Vendor Check** | Reviewing a vendor agreement and identifying gaps, expiries, and missing documents |

---

## Step 5 — Upload Your Document

You can either:
- **Click the upload zone** to browse for a file (PDF, DOCX, or TXT)
- **Paste text** directly into the paste box below it

A green confirmation shows the file name and character count when loaded successfully.

### Test documents included

Four sample documents are in the `test-docs/` folder if you want to try the app immediately:

| File | Best plugin | Scenario |
|------|-------------|----------|
| `saas-master-agreement.txt` | Contract Review | SaaS vendor agreement — loaded with buyer-unfavorable clauses |
| `mutual-nda-acquisition.txt` | NDA Triage | M&A mutual NDA — offshore counterparty, standstill clause |
| `vendor-data-processing-agreement.txt` | Vendor Check | Healthcare DPA — HIPAA / GDPR cross-border scenario |
| `employment-ip-agreement.txt` | Contract Review | Employment offer with aggressive non-compete and IP assignment |

---

## Step 6 — Add Context Notes (Important)

The **Context Notes** field is how you answer questions the AI would normally ask you interactively. Without it, the AI makes assumptions. With it, the analysis is significantly more targeted.

Use the cheat sheet below based on the plugin you selected:

### 📋 Contract Review
```
I am on the [buyer / seller / licensee / licensor] side.
[Optional: No hard deadline. Focus on liability cap, data rights, and termination.]
```

### 🔍 NDA Triage
```
We are the [disclosing / receiving / both] party. Use default market standards.
```

### 📰 Legal Brief
```
Mode: [topic brief / incident brief / daily brief].
Topic: [describe the specific question or incident].
No external systems (email, calendar, CLM, CRM) are connected — base the brief only on the uploaded document.
```

### ✉️ Response Generation
```
Inquiry type: [dsr / vendor-question / nda-request / discovery-hold].
[Key details: requester name, vendor name, specific question, applicable regulation, deadline if known.]
No templates are configured — use reasonable defaults.
```

### 🏢 Vendor Check
```
Vendor: [Full legal vendor name].
No CLM, CRM, or email systems are connected — treat the uploaded document as the executed agreement on file.
```

---

## Step 7 — Run the Analysis

Click **▶ Run All (Standard + Debate)**.

Both panels start simultaneously. You will see output streaming in real time:
- **Left panel** — the AI's analysis appears token by token as it writes
- **Right panel** — each Doer and Reviewer exchange appears as it completes, labeled clearly
- **Bottom panel** — the Final Review appears automatically after both sides finish

This typically takes **2–5 minutes** for a full document depending on the model and debate settings.

---

## Reading the Results

### Standard Analysis (left)
A single complete analysis formatted per the plugin's output spec — clause tables, risk flags, redline suggestions, etc.

### Doer / Reviewer Debate (right)

Each exchange is labeled and color-coded:

| Color | Role | What it means |
|-------|------|---------------|
| 🔵 Blue | **DOER** | Executing the analysis and defending positions |
| 🟢 Green | **REVIEWER** | Challenging the analysis, identifying gaps |
| 🟣 Purple | **Final Synthesis** | Unified consensus analysis combining both positions |

Between rounds you will see a **consensus badge** — either ✓ (consensus reached, debate ends early) or ↻ (disagreement remains, next round starts).

### Final Review (bottom)
Structured comparison declaring a winner across four dimensions: accuracy, thoroughness, actionability, and reliability. Includes confidence level (High / Medium / Low).

---

## Changing Models

Expand **🤖 Model Configuration** to assign different models to each role:

| Role | Default | When to change |
|------|---------|----------------|
| Standard Analysis | Claude Sonnet 4.6 | Use Opus for highest quality on complex contracts |
| Doer | Claude Sonnet 4.6 | Sonnet is good for thorough initial analysis |
| Reviewer | Claude Opus 4.6 | Opus is better at catching subtle errors |
| Final Reviewer | Claude Opus 4.6 | Keep Opus here for the most reliable verdict |

You can also mix providers — e.g., Claude as Doer, Gemini as Reviewer — to test cross-model debate.

**Debate Rounds** (default 3, max 5) — more rounds = deeper debate, longer runtime, higher cost.
**Exchanges per Round** (default 3, max 5) — more exchanges = more back-and-forth within each round.

---

## Exporting Results

After both panels complete, an **⬇ Export** button appears. This downloads a single Markdown file containing:
- Standard Analysis output
- Full debate transcript with synthesis
- Final Review verdict
- Token usage summary per panel

---

## Tips

- **Start with Standard Only** on your first run to verify the document loaded correctly before committing to a full debate.
- **Shorter context notes are fine** — the AI handles assumptions gracefully; you just need to unblock the mode/side/vendor-name questions.
- **The debate is slower by design** — each exchange is a separate AI call. A 3-round, 3-exchange-per-round debate makes roughly 10 sequential API calls.
- **Cost comparison** — the token counter at the top right of each panel shows input/output tokens. The debate panel will typically use 4–8× more tokens than the standard analysis.
- **Reload if stuck** — if a panel stops streaming mid-way, refresh the page, re-enter your API key, and try again. The document stays loaded server-side until the server restarts.

---

## Common Issues

| Problem | Fix |
|---------|-----|
| "Please set your API keys first" | Click **Set Keys** after entering your key — entering it is not enough |
| "No document loaded" | Upload a file or paste text before clicking Run |
| AI asks a question instead of analyzing | Add the relevant context notes from the cheat sheet above |
| Panel shows an error | Check that your API key is valid and has available credits |
| PDF extracted as garbled text | The PDF may be image-based (scanned). Use a text-based PDF or paste the text manually |

---

*This app is a research and testing tool. All analyses should be reviewed by qualified legal counsel before being relied upon.*
