from pathlib import Path
import yaml
import json

# Resolve guardrails directory safely
BASE_DIR = Path(__file__).resolve().parent.parent
GUARDRAILS_DIR = BASE_DIR / "guardrails"

# Load YAML rules
def _load_yaml(filename: str):
    path = GUARDRAILS_DIR / filename
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

# Load JSON rules
def _load_json(filename: str):
    path = GUARDRAILS_DIR / filename
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# Load rule sources
RULES = _load_yaml("trb_guardrails.yaml")
SUBSTITUTIONS = _load_json("trb_guardrails.json")

# ---- Public API expected by predict.py ----

def rule_flags(text: str) -> dict:
    """
    Return dict of rule violations: {flag_name: True/False}
    """
    out = {}
    never = RULES.get("never_say", []) or []
    lower = (text or "").lower()

    for term in never:
        key = f"blocked_term:{term}"
        out[key] = term.lower() in lower

    return out


def behavior_flags(text: str) -> dict:
    """
    Return dict of behavior signals (soft violations): {flag_name: True/False}
    """
    lower = (text or "").lower()
    pressure_terms = ["must", "now", "fix", "urgent", "immediately", "push through", "should"]

    out = {}
    for term in pressure_terms:
        key = f"pressure:{term}"
        out[key] = term in lower

    return out


def guidance(rule_flag_dict: dict):
    if any(rule_flag_dict.values()):
        return [
            "Use **State** language (temporary) instead of identity language.",
            "Name **Signals** as information, not flaws or symptoms.",
            "Honor **Capacity** (offer options, remove urgency).",
            "Support **Regulation** without force (gentle, body-led).",
            "Add **Integration** (how to carry steadiness into the next moment).",
        ]
    return [
        "Language feels invitational, shame-free, and choice-led.",
        "Optional: add one capacity line (e.g., “if it fits today”).",
    ]


def substitution_suggestions(text: str) -> list[str]:
    lower = (text or "").lower()
    substitutions = (SUBSTITUTIONS.get("substitutions", {}) or {})
    hits = []

    for bad, good in substitutions.items():
        if bad.lower() in lower:
            hits.append(f"Replace **{bad}** → {good}")

    return hits

    for bad, good in substitutions.items():
        if bad.lower() in lower:
            hits.append(f"Replace **{bad}** → {good}")

    if not hits:
        return ""

    return "\nSuggested substitutions:\n- " + "\n- ".join(hits) + "\n"
