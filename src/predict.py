import json
import joblib

import numpy as np
import torch

from src.preprocess import normalize_text
from src.model import MLP
from src.guardrails_rules import rule_flags, behavior_flags, guidance, substitution_suggestions
from src.utils import abs_path

def load_artifacts():
    vectorizer = joblib.load(abs_path("models", "vectorizer.joblib"))
    mlb = joblib.load(abs_path("models", "mlb.joblib"))
    cfg = json.loads(abs_path("models", "train_config.json").read_text())

    input_dim = len(vectorizer.get_feature_names_out())
    output_dim = len(mlb.classes_)

    model = MLP(input_dim=input_dim, output_dim=output_dim, hidden_dim=cfg["hidden_dim"], dropout=cfg["dropout"])
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.load_state_dict(torch.load(abs_path("models", "model.pt"), map_location=device))
    model.to(device)
    model.eval()
    return model, vectorizer, mlb, cfg, device

def confidence_bucket(probs, conf_high=0.65, conf_med=0.45):
    c = float(np.max(probs)) if probs.size else 0.0
    if c >= conf_high: return "high", c
    if c >= conf_med: return "medium", c
    return "low", c

def split_labels(picked):
    tones, risks = [], []
    for name, p in picked:
        if name.startswith("tone:"):
            tones.append((name.replace("tone:", ""), p))
        elif name.startswith("risk:"):
            risks.append((name.replace("risk:", ""), p))
    tones.sort(key=lambda x: x[1], reverse=True)
    risks.sort(key=lambda x: x[1], reverse=True)
    return tones, risks

def route_message(bucket: str, rule_triggered: bool, behaviors_count: int) -> str:
    if rule_triggered:
        return "Rule-triggered: revise language first (remove pressure/fixing/hustle). Then re-check."
    if bucket == "high" and behaviors_count >= 1:
        return "High confidence: show tone behaviors + targeted suggestions. Human approves final copy."
    if bucket in ("high", "medium"):
        return "Medium confidence: show top tags + ask 2 clarifying questions before recommending edits."
    return "Low confidence: insufficient signal. Ask for audience + intent + channel. Suggest substitutions."

def predict(text: str, threshold=0.5):
    model, vectorizer, mlb, cfg, device = load_artifacts()
    clean = normalize_text(text)

    X = vectorizer.transform([clean]).toarray().astype(np.float32)
    with torch.no_grad():
        logits = model(torch.from_numpy(X).to(device)).cpu().numpy().squeeze(0)

    probs = 1 / (1 + np.exp(-logits))
    labels = mlb.classes_

    picked = [(labels[i], float(probs[i])) for i in range(len(labels)) if probs[i] >= threshold]
    picked.sort(key=lambda x: x[1], reverse=True)

    bucket, conf = confidence_bucket(probs, cfg["conf_high"], cfg["conf_med"])

    rf = rule_flags(text)
    bf = behavior_flags(text)
    rule_triggered = any(rf.values())
    behaviors_count = sum(1 for v in bf.values() if v)

    if rule_triggered and bucket == "high":
        bucket = "medium"

    tones, risks = split_labels(picked)


return {
    "confidence_bucket": bucket,
    "confidence_score": conf,
    "tone_tags": tones[:8],
    "risk_flags": risks[:10],
    "behavior_flags": bf,
    "rule_flags": rf,
    "rewrite_guidance": guidance(rf),
    "substitution_suggestions": substitution_suggestions(text),
    "routing": route_message(bucket, rule_triggered, behaviors_count),
    "final_gate_question": "Does this copy help someone listen to themselves without pressure?",
}
