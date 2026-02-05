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

def rule_flags(text: str) -> list:
    """Return soft rule violations found in text."""
    flags = []
    blocked = RULES.get("never_say", [])
    for word in blocked:
        if word.lower() in text.lower():
            flags.append(f"blocked_term:{word}")
    return flags

def behavior_flags(text: str) -> list:
    """Detect urgency / pressure language."""
    pressure_terms = ["must", "now", "fix", "urgent", "immediately"]
    return [t for t in pressure_terms if t in text.lower()]

def guidance(text: str) -> str:
    """High-level tone guidance."""
    if rule_flags(text) or behavior_flags(text):
        return "Consider revising language to be state-based, invitational, and choice-led."
    return "Language appears aligned with S.Y.N.Cvoice™ guardrails."

def substitution_suggestions(text: str) -> dict:
    """Suggest softer alternatives for flagged terms."""
    suggestions = {}
    replacements = SUBSTITUTIONS.get("substitutions", {})
    for bad, good in replacements.items():
        if bad.lower() in text.lower():
            suggestions[bad] = good
    return suggestions
