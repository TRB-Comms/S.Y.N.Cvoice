import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score

import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader

from preprocess import normalize_text
from model import MLP
from utils import abs_path

def split_pipe_labels(s: str):
    if s is None or str(s).strip() == "":
        return []
    return [x.strip() for x in str(s).split("|") if x.strip()]

def main(
    data_csv: str = "data/trb_training_278_rows_combined.csv",
    out_dir: str = "models",
    label_prefix: str = "",  # keep empty; labels already include tone/risk as plain names
    epochs: int = 12,
    batch_size: int = 32,
    lr: float = 2e-3,
    hidden_dim: int = 256,
    dropout: float = 0.2,
    conf_high: float = 0.65,
    conf_med: float = 0.45,
):
    data_path = abs_path(*data_csv.split("/"))
    df = pd.read_csv(data_path)

    # Build a single multi-label target space:
    # We prefix labels so predict.py can separate tone vs risk reliably.
    y_labels = []
    for _, r in df.iterrows():
        tones = ["tone:" + t for t in split_pipe_labels(r.get("tone_labels", ""))]
        risks = ["risk:" + t for t in split_pipe_labels(r.get("risk_labels", ""))]
        y_labels.append(tones + risks)

    texts = [normalize_text(t) for t in df["text"].astype(str).tolist()]

    X_train, X_test, y_train, y_test = train_test_split(
        texts, y_labels, test_size=0.2, random_state=42
    )

    vectorizer = TfidfVectorizer(ngram_range=(1,2), min_df=2, max_features=20000)
    Xtr = vectorizer.fit_transform(X_train).toarray().astype(np.float32)
    Xte = vectorizer.transform(X_test).toarray().astype(np.float32)

    mlb = MultiLabelBinarizer()
    Ytr = mlb.fit_transform(y_train).astype(np.float32)
    Yte = mlb.transform(y_test).astype(np.float32)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = MLP(input_dim=Xtr.shape[1], output_dim=Ytr.shape[1], hidden_dim=hidden_dim, dropout=dropout).to(device)

    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    loss_fn = nn.BCEWithLogitsLoss()

    train_ds = TensorDataset(torch.from_numpy(Xtr), torch.from_numpy(Ytr))
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

    model.train()
    for ep in range(epochs):
        losses = []
        for xb, yb in train_dl:
            xb = xb.to(device)
            yb = yb.to(device)
            opt.zero_grad()
            logits = model(xb)
            loss = loss_fn(logits, yb)
            loss.backward()
            opt.step()
            losses.append(float(loss.item()))
        print(f"epoch {ep+1}/{epochs} loss={np.mean(losses):.4f}")

    # Eval
    model.eval()
    with torch.no_grad():
        logits = model(torch.from_numpy(Xte).to(device)).cpu().numpy()
    probs = 1/(1+np.exp(-logits))
    preds = (probs >= 0.5).astype(int)
    f1 = f1_score(Yte, preds, average="macro", zero_division=0)
    print("macro_f1:", round(float(f1), 4))

    out_path = abs_path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    torch.save(model.state_dict(), out_path / "model.pt")
    joblib.dump(vectorizer, out_path / "vectorizer.joblib")
    joblib.dump(mlb, out_path / "mlb.joblib")

    cfg = {
        "hidden_dim": hidden_dim,
        "dropout": dropout,
        "conf_high": conf_high,
        "conf_med": conf_med,
        "threshold": 0.5,
        "trained_on": str(data_path),
    }
    with open(out_path / "train_config.json", "w") as f:
        json.dump(cfg, f, indent=2)

if __name__ == "__main__":
    main()
