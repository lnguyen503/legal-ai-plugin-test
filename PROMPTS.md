# Context Notes — Quick Reference

Paste one of the prompts below into the **Context Notes** field before clicking Run.
Replace anything in `[square brackets]` with your own details.

---

## 📋 Contract Review

Use this plugin for any commercial contract — MSA, SaaS agreement, employment offer, vendor agreement, license, etc.

```
I am on the [buyer / seller / licensee / licensor / employee / employer] side.
[Optional: Deadline: review must be complete by [date].]
Focus on: [e.g., liability cap, termination rights, IP ownership, data rights, non-compete scope — or leave blank to review all clauses].
No playbook configured — use general commercial standards.
```

**Minimal version (works for any contract):**
```
I am on the [buyer / seller / employee / employer] side. No hard deadline. No playbook configured — use general commercial standards.
```

---

## 🔍 NDA Triage

Use this plugin for any NDA — mutual, unilateral, M&A, vendor, or employment.

```
We are the [disclosing / receiving / both] party.
[Optional: Counterparty name: [name].]
[Optional: Purpose of NDA: [e.g., vendor evaluation, potential acquisition, employment].]
Use default market standards — no playbook configured.
```

**Minimal version (works for any NDA):**
```
We are the [disclosing / receiving / both] party. Use default market standards — no playbook configured.
```

---

## 📰 Legal Brief

Use this plugin to generate a structured briefing from any document. Choose one of three modes.

### Topic Brief — research a specific question from the document
```
Mode: topic brief.
Topic: [describe the specific legal question you want answered, e.g., "data retention obligations", "termination rights", "indemnification scope"].
No external systems (email, calendar, CLM, CRM) are connected — base the entire brief only on the uploaded document.
```

### Daily Brief — morning summary (use when connected to email/calendar)
```
Mode: daily brief.
No external systems are connected — base the brief only on the uploaded document.
```

### Incident Brief — rapid brief on a developing situation
```
Mode: incident brief.
Incident: [brief description, e.g., "potential data breach", "contract dispute with vendor", "regulatory inquiry"].
No external systems (email, calendar, CLM, CRM) are connected — base the brief only on the uploaded document.
```

**Minimal version (topic brief, works for any document):**
```
Mode: topic brief. Topic: [your question about the document]. No external systems are connected — base the brief only on the uploaded document.
```

---

## ✉️ Response Generation

Use this plugin to draft a response to any legal inquiry. Choose the inquiry type that matches your situation.

### Vendor question
```
Inquiry type: vendor-question.
Vendor: [vendor's full name].
Question: [describe the specific question the vendor asked, e.g., "whether their breach notification timeline meets our requirements", "whether their subprocessor list is adequate"].
No templates configured — use reasonable defaults. Draft a response suitable for sending to the vendor.
```

### Data subject request (DSR)
```
Inquiry type: dsr.
Requester: [requester name or "anonymous"].
Request type: [access / deletion / correction / portability].
Regulation: [GDPR / CCPA / CPRA / other].
[Optional: Deadline: [date].]
No templates configured — use reasonable defaults.
```

### NDA request from a business team
```
Inquiry type: nda-request.
Requesting team: [team or person name].
Counterparty: [counterparty name].
Purpose: [e.g., vendor evaluation, partnership discussion].
No templates configured — use reasonable defaults.
```

### Litigation hold
```
Inquiry type: discovery-hold.
Matter: [matter name or reference number].
No templates configured — use reasonable defaults.
```

**Minimal version (vendor question, works for any document):**
```
Inquiry type: vendor-question. Vendor: [vendor name]. Question: [what the vendor is asking about]. No templates configured — use reasonable defaults.
```

---

## 🏢 Vendor Check

Use this plugin to audit the full legal relationship with any vendor.

```
Vendor: [vendor's full legal name].
No CLM, CRM, email, or document systems are connected — treat the uploaded document as the only executed agreement on file.
[Optional: Flag any missing agreements such as MSA, SLA, DPA, or insurance certificate.]
[Optional: Highlight any clauses approaching expiration or requiring action within [timeframe, e.g., 90 days].]
```

**Minimal version (works for any vendor agreement):**
```
Vendor: [vendor name]. No CLM, CRM, email, or document systems are connected — treat the uploaded document as the only executed agreement on file.
```

---

## Tips

- **The minimal versions always work.** Fill in just the vendor name or your side of the contract and the AI handles the rest.
- **More detail = more targeted output.** Adding a focus area (e.g., "focus on liability cap") narrows the analysis to what matters most.
- **"No playbook configured"** tells the AI to use standard market practice instead of asking for a missing internal playbook.
- **"No external systems connected"** tells the AI not to ask about email, CLM, or CRM integrations that aren't set up.
