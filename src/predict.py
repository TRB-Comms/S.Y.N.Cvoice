from __future__ import annotations

import re
from typing import Dict, List, Tuple

from src.guardrails_rules import (
    rule_flags,
    behavior_flags,
    guidance,
    substitution_suggestions,
)

# ----------------------------
# Deterministic / explainable inference
# (No torch, no sklearn, no numpy)
# ----------------------------

# TRB / S.Y.N.Cvoice™ positive signals (what we want to detect)
POSITIVE_SIGNALS: Dict[str, List[str]] = {
    "state_based": [
        "state",
        "right now",
        "today",
        "in this moment",
        "temporary",
        "current",
    ],
    "signal_based": [
        "signal",
        "signals",
        "information",
        "data point",
        "your system is sending",
        "your body is sending",
    ],
    "capacity_honoring": [
        "capacity",
        "at your pace",
        "as you're able",
        "what’s possible",
        "what is possible",
        "meet yourself where",
    ],
    "regulation_focused": [
        "regulation",
        "regulate",
        "support regulation",
        "steady",
        "settle",
        "ground",
        "pause",
        "breathe",
    ],
    "integration_oriented": [
        "integration",
        "carry this",
        "carry that",
        "into your next moment",
        "into life",
        "beyond this",
    ],
    "choice_led": [
        "choose",
        "choice",
        "if it fits",
        "does that fit",
        "you can",
        "you’re allowed",
        "optional",
        "invite",
        "invitational",
    ],
}

# Tone tags (simple, explainable)
TONE_TAGS: Dict[str, List[str]] = {
    "invitational": ["invite", "invitational", "you can", "you’re allowed", "if you want", "optional"],
    "shame_free": ["no shame", "without shame", "no judgment", "non-judgment", "gentle"],
    "body_led": ["body", "nervous system", "somatic", "breath", "breathe", "ground", "pause"],
    "non_urgent": ["at your pace", "when you're ready", "no rush", "take your time", "slow"],
    "choice_led": ["choose", "choice", "if it fits", "does that fit", "you decide"],
}

WORD_RE = re.compile(r"\b[\w’']+\b", re.UNICODE)


def _normalize(text: str) -> str:
    # keep punctuation for term checks in guardrails_rules; normalize here for matching
    return " ".join(text.strip().lower().split())


def _count_hits(text: str, phrases: List[str]) -> int:
    t = _normalize(text)
    hits = 0
    for p in phrases:
        p_norm = p.lower().strip()
        if not p_norm:
            continue
        if p_norm in t:
            hits += 1
    return hits


def _score_tags(text: str, tag_map: Dict[str, List[str]]) -> List[Tuple[str, float]]:
    # Score tags by number of phrase hits, lightly normalized to 0..1
    scored: List[Tuple[str, float]] = []
    for tag, phrases in tag_map.items():
        h = _count_hits(text, phrases)
        if h > 0:
            # diminishing returns: 1 hit ~0.55, 2 hits ~0.7, 3+ ~0.82
            score = 0.45 + (0.18 * min(h, 3))
            scored.append((tag, float(min(score, 0.92))))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def confidence_bucket(conf: float, conf_high: float = 0.70, conf_med: float = 0.50):
    if conf >= conf_high:
        return "high"
    if conf >= conf_med:
        return "medium"
    return "low"


def route_message(bucket: str, rule_triggered: bool, behaviors_count: int) -> str:
    if rule_triggered:
        return "Rule-triggered: revise language first (remove pressure/fixing/hustle). Then re-check."
    if bucket == "high" and behaviors_count >= 1:
        return "High confidence: show tone behaviors + targeted suggestions. Human approves final copy."
    if bucket in ("high", "medium"):
        return "Medium confidence: show top tags + ask 2 clarifying questions before recommending edits."
    return "Low confidence: insufficient signal. Ask for audience + intent + channel. Suggest substitutions."


def predict(text: str, threshold: float = 0.5):
    """
    Deterministic, explainable 'classifier':
    - Uses guardrails_rules for rule + behavior flags
    - Adds positive TRB-aligned signals
    - Produces a confidence score based on evidence, not probabilities
    """
    raw = text or ""
    t = _normalize(raw)

    # Deterministic flags from your ruleset
    rf = rule_flags(raw)
    bf = behavior_flags(raw)

    rule_triggered = any(bool(v) for v in rf.values())
    behaviors_count = sum(1 for v in bf.values() if v)

    # TRB-aligned evidence
    positive_evidence = _score_tags(raw, POSITIVE_SIGNALS)
    tone_evidence = _score_tags(raw, TONE_TAGS)

    # Risk flags list (as pairs like the old ML output)
    risks: List[Tuple[str, float]] = []
    for k, v in rf.items():
        if v:
            risks.append((k, 0.99))

    # Include behavior flags that indicate pressure/shame as risks too
    for k, v in bf.items():
        if v and k.startswith(("pressure", "shame", "urgency")):
            risks.append((k, 0.90))

    # De-dup and sort
    seen = set()
    deduped = []
    for name, score in sorted(risks, key=lambda x: x[1], reverse=True):
        if name not in seen:
            deduped.append((name, float(score)))
            seen.add(name)
    risks = deduped[:10]

    # Tone tags: combine explicit tone evidence + any behavior flags (as tags)
    tones: List[Tuple[str, float]] = tone_evidence[:]
    for k, v in bf.items():
        if v:
            # treat behavior detections as high-signal tags
            tones.append((k, 0.85))

    # De-dup + top-N
    seen = set()
    tones2 = []
    for name, score in sorted(tones, key=lambda x: x[1], reverse=True):
        if name not in seen:
            tones2.append((name, float(score)))
            seen.add(name)
    tones = tones2[:8]

    # Confidence is evidence-based:
    # - Starts modest
    # - Increases with TRB-aligned signals + tone evidence
    # - Decreases if rule-triggered
    base = 0.42
    base += 0.08 * min(len(positive_evidence), 5)
    base += 0.05 * min(len(tone_evidence), 4)
    if rule_triggered:
        base -= 0.18
    if behaviors_count >= 3:
        base -= 0.06

    conf = max(0.05, min(base, 0.92))
    bucket = confidence_bucket(conf)

    # Threshold behavior: since this isn't probabilistic, we interpret threshold as
    # "how strict to be in showing tags"
    # threshold 0.5 shows most; higher threshold shows fewer
    show_min = 0.45 + (threshold - 0.5) * 0.5  # maps 0.2..0.9 -> ~0.30..0.65
    tones = [(n, s) for (n, s) in tones if s >= show_min]
    risks = [(n, s) for (n, s) in risks if s >= show_min]

    # Guidance outputs
    rewrite_guidance = guidance(rf)
    subs = substitution_suggestions(raw)

    return {
        "confidence_bucket": bucket,
        "confidence_score": float(conf),
        "tone_tags": tones,
        "risk_flags": risks,
        "behavior_flags": bf,
        "rule_flags": rf,
        "rewrite_guidance": rewrite_guidance,
        "substitution_suggestions": subs,
        "routing": route_message(bucket, rule_triggered, behaviors_count),
        "final_gate_question": "Does this copy help someone listen to themselves without pressure?",
    }
