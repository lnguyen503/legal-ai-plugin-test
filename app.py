"""
Legal AI Plugin Test — Flask Application

Compares Standard (single-pass) Analysis vs Doer/Reviewer Debate
for 5 legal workflow plugins against uploaded documents.
"""
import os
import json
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from werkzeug.utils import secure_filename

from src.services.llm_service import LLMService, AVAILABLE_MODELS
from src.services.plugin_loader import load_plugin, load_plugin_for_automation, list_plugins, get_plugin_name
from src.services.document_parser import parse_document
from src.services.debate_orchestrator import DoerReviewerOrchestrator

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ── Global state (BYOK — keys never persisted to disk) ────────────────────────
api_keys = {"anthropic": "", "google": ""}

# In-memory document store (shared across requests in single-worker dev mode)
current_document = {"text": "", "filename": "", "char_count": 0}

# Upload configuration
UPLOAD_FOLDER = Path(__file__).parent / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt", "md"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_llm() -> LLMService:
    return LLMService(
        anthropic_key=api_keys["anthropic"] or None,
        google_key=api_keys["google"] or None,
    )


def sse_headers() -> dict:
    return {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Access-Control-Allow-Origin": "*",
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", models=AVAILABLE_MODELS)


@app.route("/api/set-keys", methods=["POST"])
def set_keys():
    data = request.json or {}
    api_keys["anthropic"] = data.get("anthropic_key", "").strip()
    api_keys["google"] = data.get("google_key", "").strip()
    return jsonify({
        "status": "success",
        "anthropic_set": bool(api_keys["anthropic"]),
        "google_set": bool(api_keys["google"]),
    })


@app.route("/api/check-keys", methods=["GET"])
def check_keys():
    return jsonify({
        "anthropic_set": bool(api_keys["anthropic"]),
        "google_set": bool(api_keys["google"]),
        "anthropic_length": len(api_keys["anthropic"]),
        "google_length": len(api_keys["google"]),
    })


@app.route("/api/plugins", methods=["GET"])
def get_plugins():
    return jsonify(list_plugins())


@app.route("/api/upload", methods=["POST"])
def upload_document():
    """Upload a document file or accept pasted text. Stores extracted text in memory."""

    # Handle pasted text
    if request.content_type and "application/json" in request.content_type:
        data = request.json or {}
        text = data.get("text", "").strip()
        if text:
            current_document["text"] = text
            current_document["filename"] = "pasted-text.txt"
            current_document["char_count"] = len(text)
            return jsonify({
                "success": True,
                "filename": "Pasted Text",
                "char_count": len(text),
                "preview": text[:300] + "…" if len(text) > 300 else text,
            })
        return jsonify({"error": "No text provided"}), 400

    # Handle file upload
    if "file" not in request.files:
        # Also check for pasted text in form data
        text = request.form.get("text", "").strip()
        if text:
            current_document["text"] = text
            current_document["filename"] = "pasted-text.txt"
            current_document["char_count"] = len(text)
            return jsonify({
                "success": True,
                "filename": "Pasted Text",
                "char_count": len(text),
                "preview": text[:300] + "…" if len(text) > 300 else text,
            })
        return jsonify({"error": "No file or text provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "error": f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        }), 400

    filename = secure_filename(file.filename)
    filepath = UPLOAD_FOLDER / filename
    file.save(str(filepath))

    try:
        text = parse_document(str(filepath), filename)
        current_document["text"] = text
        current_document["filename"] = filename
        current_document["char_count"] = len(text)
        return jsonify({
            "success": True,
            "filename": filename,
            "char_count": len(text),
            "preview": text[:300] + "…" if len(text) > 300 else text,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            filepath.unlink()
        except Exception:
            pass


@app.route("/api/run-standard", methods=["POST"])
def run_standard():
    """
    Standard single-pass analysis with token-by-token SSE streaming.
    The plugin's MD content becomes the system prompt.
    """
    data = request.json or {}
    plugin_id = data.get("plugin_id", "")
    model = data.get("model", "")
    context_notes = data.get("context_notes", "")
    document_text = data.get("document_text") or current_document.get("text", "")

    if not plugin_id or not model:
        return jsonify({"error": "Missing plugin_id or model"}), 400
    if not document_text:
        return jsonify({"error": "No document loaded. Please upload a document first."}), 400
    if not api_keys["anthropic"] and not api_keys["google"]:
        return jsonify({"error": "No API keys set. Please enter your API key above."}), 400

    try:
        plugin_content = load_plugin_for_automation(plugin_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    context_block = f"\nADDITIONAL CONTEXT: {context_notes}\n" if context_notes.strip() else ""
    user_prompt = (
        f"Please analyze the following legal document according to the workflow.\n"
        f"{context_block}\n"
        f"DOCUMENT:\n{document_text}"
    )

    def generate():
        try:
            llm = get_llm()
            for chunk in llm.stream_model(
                model=model,
                prompt=user_prompt,
                system_prompt=plugin_content,
                temperature=0.7,
                max_tokens=8192,
            ):
                yield f"data: {json.dumps({'type': 'text', 'text': chunk})}\n\n"

            usage = llm.get_last_usage()
            yield f"data: {json.dumps({'type': 'done', 'token_counts': usage})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(stream_with_context(generate()), content_type="text/event-stream", headers=sse_headers())


@app.route("/api/run-debate", methods=["POST"])
def run_debate():
    """
    Doer/Reviewer debate with per-exchange SSE events.
    Each exchange is a complete LLM call; events fire after each completes.
    """
    data = request.json or {}
    plugin_id = data.get("plugin_id", "")
    doer_model = data.get("doer_model", "")
    reviewer_model = data.get("reviewer_model", "")
    max_rounds = max(2, min(5, int(data.get("max_rounds", 3))))
    exchanges_per_round = max(3, min(5, int(data.get("exchanges_per_round", 3))))
    context_notes = data.get("context_notes", "")
    document_text = data.get("document_text") or current_document.get("text", "")

    if not plugin_id or not doer_model or not reviewer_model:
        return jsonify({"error": "Missing plugin_id, doer_model, or reviewer_model"}), 400
    if not document_text:
        return jsonify({"error": "No document loaded. Please upload a document first."}), 400
    if not api_keys["anthropic"] and not api_keys["google"]:
        return jsonify({"error": "No API keys set. Please enter your API key above."}), 400

    try:
        plugin_content = load_plugin_for_automation(plugin_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    def generate():
        try:
            llm = get_llm()
            orchestrator = DoerReviewerOrchestrator(llm)
            yield from orchestrator.run_debate(
                document_text=document_text,
                plugin_content=plugin_content,
                context_notes=context_notes,
                doer_model=doer_model,
                reviewer_model=reviewer_model,
                max_rounds=max_rounds,
                exchanges_per_round=exchanges_per_round,
            )
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(stream_with_context(generate()), content_type="text/event-stream", headers=sse_headers())


@app.route("/api/run-final-review", methods=["POST"])
def run_final_review():
    """
    Independent Final Reviewer compares Standard vs Debate outputs.
    Streams token-by-token.
    """
    data = request.json or {}
    plugin_id = data.get("plugin_id", "")
    model = data.get("model", "")
    standard_output = data.get("standard_output", "")
    debate_output = data.get("debate_output", "")

    if not plugin_id or not model:
        return jsonify({"error": "Missing plugin_id or model"}), 400
    if not standard_output or not debate_output:
        return jsonify({"error": "Both standard and debate outputs are required"}), 400
    if not api_keys["anthropic"] and not api_keys["google"]:
        return jsonify({"error": "No API keys set"}), 400

    try:
        plugin_content = load_plugin_for_automation(plugin_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    system_prompt = (
        "You are the FINAL REVIEWER — an independent senior legal analyst comparing two analyses of the same document. "
        "Your role is to objectively evaluate both analyses and determine which is superior based on accuracy, thoroughness, and practical value."
    )

    user_prompt = f"""THE LEGAL WORKFLOW USED:
{plugin_content}

---

ANALYSIS A — Standard (Single-Pass AI):
{standard_output}

---

ANALYSIS B — Debate Consensus (Doer/Reviewer):
{debate_output}

---

INSTRUCTIONS:
- Compare both analyses for accuracy, thoroughness, and practical value
- Identify findings that appear in one but not the other
- Identify any errors or misinterpretations in either analysis
- Determine which analysis is MORE:
  1. Accurate (correct interpretation of clauses and risks)
  2. Thorough (complete coverage of the workflow requirements)
  3. Actionable (provides specific, useful next steps)
  4. Reliable (fewer errors, better-supported conclusions)
- Declare a winner and explain WHY with specific examples from both analyses
- Note any areas where NEITHER analysis was adequate
- Provide your confidence level (High/Medium/Low) in your winner determination

OUTPUT FORMAT:
## Final Review: Standard vs. Debate Analysis

### Winner: [Analysis A or Analysis B]
### Confidence: [High/Medium/Low]

### Comparison Summary
[2-3 sentence summary of key differences]

### Accuracy Comparison
[Which got more things right, with specific examples]

### Thoroughness Comparison
[Which covered more ground, with specific examples]

### Unique Findings
- Found only in Standard: [list]
- Found only in Debate: [list]

### Errors Identified
- Standard errors: [list or "None identified"]
- Debate errors: [list or "None identified"]

### Verdict
[Detailed explanation of why the winner is better and what the loser missed]"""

    def generate():
        try:
            llm = get_llm()
            for chunk in llm.stream_model(
                model=model,
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.4,
                max_tokens=8192,
            ):
                yield f"data: {json.dumps({'type': 'text', 'text': chunk})}\n\n"

            usage = llm.get_last_usage()
            yield f"data: {json.dumps({'type': 'done', 'token_counts': usage})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(stream_with_context(generate()), content_type="text/event-stream", headers=sse_headers())


@app.route("/api/export", methods=["POST"])
def export_report():
    """Export the full analysis session as a markdown file download."""
    data = request.json or {}
    plugin_name = data.get("plugin_name", "Unknown Plugin")
    document_name = data.get("document_name", "Unknown Document")
    standard_output = data.get("standard_output", "*(No output)*")
    debate_output = data.get("debate_output", "*(No output)*")
    final_review = data.get("final_review", "*(Not run)*")
    token_counts = data.get("token_counts", {})
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    std_tokens = token_counts.get("standard", {})
    dbt_tokens = token_counts.get("debate", {})
    rev_tokens = token_counts.get("final_review", {})

    report = f"""# Legal AI Analysis Report

**Generated:** {timestamp}
**Plugin:** {plugin_name}
**Document:** {document_name}

---

## Standard Analysis (Single-Pass)

{standard_output}

---

## Debate Analysis (Doer/Reviewer Consensus)

{debate_output}

---

## Final Review

{final_review}

---

## Token Usage Summary

| Panel | Input Tokens | Output Tokens | Total |
|-------|-------------|---------------|-------|
| Standard | {std_tokens.get('input_tokens', 0):,} | {std_tokens.get('output_tokens', 0):,} | {std_tokens.get('input_tokens', 0) + std_tokens.get('output_tokens', 0):,} |
| Debate | {dbt_tokens.get('input_tokens', 0):,} | {dbt_tokens.get('output_tokens', 0):,} | {dbt_tokens.get('input_tokens', 0) + dbt_tokens.get('output_tokens', 0):,} |
| Final Review | {rev_tokens.get('input_tokens', 0):,} | {rev_tokens.get('output_tokens', 0):,} | {rev_tokens.get('input_tokens', 0) + rev_tokens.get('output_tokens', 0):,} |
"""

    safe_date = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Response(
        report,
        mimetype="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=legal-analysis-{safe_date}.md"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
