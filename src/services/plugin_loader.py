"""
Plugin Loader - loads and manages the 5 legal workflow MD plugin files
"""
from pathlib import Path
from typing import Dict, List

# Project root is 2 levels up from src/services/
PROJECT_ROOT = Path(__file__).parent.parent.parent

PLUGIN_REGISTRY: Dict[str, Dict[str, str]] = {
    "review-contract": {
        "name": "Contract Review",
        "file": "review-contract.md",
        "description": "Clause-by-clause contract review with RED/YELLOW/GREEN playbook flags and redline suggestions",
        "icon": "📋",
    },
    "triage-nda": {
        "name": "NDA Triage",
        "file": "triage-nda.md",
        "description": "Pre-screen and classify NDAs using 12 screening criteria with GREEN/YELLOW/RED routing",
        "icon": "🔍",
    },
    "brief": {
        "name": "Legal Brief",
        "file": "brief.md",
        "description": "Generate legal team briefings — daily brief, topic brief, or incident brief",
        "icon": "📰",
    },
    "respond": {
        "name": "Response Generation",
        "file": "respond.md",
        "description": "Generate legal responses from templates — DSR, discovery hold, vendor Q&A, NDA requests",
        "icon": "✉️",
    },
    "vendor-check": {
        "name": "Vendor Check",
        "file": "vendor-check.md",
        "description": "Consolidated vendor agreement status check across connected systems",
        "icon": "🏢",
    },
}


def load_plugin(plugin_id: str) -> str:
    """Load and return plugin content from its MD file."""
    if plugin_id not in PLUGIN_REGISTRY:
        raise ValueError(f"Unknown plugin '{plugin_id}'. Available: {', '.join(PLUGIN_REGISTRY.keys())}")

    plugin_info = PLUGIN_REGISTRY[plugin_id]
    plugin_path = PROJECT_ROOT / plugin_info["file"]

    if not plugin_path.exists():
        raise FileNotFoundError(f"Plugin file not found: {plugin_path}")

    return plugin_path.read_text(encoding="utf-8")


def list_plugins() -> List[Dict]:
    """Return list of available plugins with metadata for the UI."""
    return [
        {
            "id": plugin_id,
            "name": info["name"],
            "description": info["description"],
            "icon": info["icon"],
        }
        for plugin_id, info in PLUGIN_REGISTRY.items()
    ]


def get_plugin_name(plugin_id: str) -> str:
    """Return the display name of a plugin."""
    if plugin_id in PLUGIN_REGISTRY:
        return PLUGIN_REGISTRY[plugin_id]["name"]
    return plugin_id


AUTOMATION_PREAMBLE = """
## OPERATING MODE: AUTOMATED BATCH ANALYSIS

You are running in automated batch mode — NOT in an interactive conversation.

**Critical rules that override all workflow steps below:**
1. **DO NOT ask the user any questions.** The document and all available context have already been provided. Proceed immediately to the analysis.
2. **DO NOT wait for input.** Any workflow step that says "ask the user", "prompt the user", or "gather context" should be skipped or satisfied using the context notes provided.
3. **Use context notes as your answers.** If context notes are provided, treat them as the user's answers to any setup questions. If a piece of context is missing (e.g., no deadline given), state your assumption briefly and continue.
4. **If no playbook is configured**, proceed immediately with general commercial standards as the baseline and note this clearly.
5. **If no MCP/CLM/CRM/system is connected**, skip those steps and note that they are unavailable.
6. **Produce a complete, standalone analysis** in a single response using the output format specified in the workflow.

---
"""


def load_plugin_for_automation(plugin_id: str) -> str:
    """
    Load plugin content and prepend the automation preamble.
    Use this instead of load_plugin() for all AI calls to prevent the model
    from asking interactive questions mid-analysis.
    """
    raw = load_plugin(plugin_id)
    return AUTOMATION_PREAMBLE + raw
