"""SkyTrace — Save Experiment A test probabilities for ranking evaluation.

Usage:
    python scripts/save_exp_a_probabilities.py

Loads the best Experiment A checkpoint (codebert_baseline/best.pt),
runs inference on the test set, and saves:
    experiments/codebert/test_probabilities.npz  (y_true, y_score)

This enables ranking_eval.py to include Experiment A in the ranking comparison.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader
from transformers import AutoTokenizer

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "..", "src")
sys.path.insert(0, _SRC)

from skytrace.data.dataset import load_splits, CodeDataset, CodeDatasetConfig, collate_codebert
from skytrace.models.code_encoder import CodeBERTClassifier, CodeBERTConfig

with open("configs/codebert.yaml", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)
with open("configs/dataset.yaml", encoding="utf-8") as f:
    dataset_cfg = yaml.safe_load(f)["dataset"]

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {device}")

splits = load_splits(dataset_cfg)
tok = AutoTokenizer.from_pretrained(cfg["model"]["encoder"]["name"])

cc = CodeBERTConfig(
    model_name=cfg["model"]["encoder"]["name"],
    hidden_size=cfg["model"]["encoder"]["hidden_size"],
    freeze_layers=cfg["model"]["encoder"]["freeze_layers"],
    classifier_hidden_dims=cfg["model"]["classifier"]["hidden_dims"],
    dropout=cfg["model"]["classifier"]["dropout"],
    n_classes=cfg["model"]["classifier"]["n_classes"],
    pooling=cfg["model"]["pooling"],
)
model = CodeBERTClassifier(cc)
checkpoint = torch.load(r"models\checkpoints\codebert_baseline\best.pt", map_location="cpu", weights_only=False)
model.load_state_dict(checkpoint["model_state_dict"])
model.to(device)
model.eval()

ds_cfg = CodeDatasetConfig(
    max_length=cfg["tokenizer"]["max_length"],
    truncation=cfg["tokenizer"]["truncation"],
    padding=cfg["tokenizer"]["padding"],
)
ds = CodeDataset(splits["test"], tok, ds_cfg)
loader = DataLoader(ds, batch_size=16, shuffle=False, num_workers=0, collate_fn=collate_codebert)

all_probs, all_labels = [], []
print(f"Running inference on test set ({len(ds):,} samples)...")
with torch.no_grad():
    for i, batch in enumerate(loader, 1):
        if i == 1 or i % 200 == 0 or i == len(loader):
            print(f"  batch {i}/{len(loader)}")
        out = model(input_ids=batch["input_ids"].to(device),
                    attention_mask=batch["attention_mask"].to(device))
        logits = out["logits"].detach().cpu().numpy().reshape(-1)
        probs = 1.0 / (1.0 + np.exp(-logits))
        all_probs.extend(probs.tolist())
        all_labels.extend(batch["labels"].detach().cpu().numpy().reshape(-1).tolist())

y_true = np.array(all_labels, dtype=np.float32)
y_score = np.array(all_probs, dtype=np.float32)

os.makedirs("experiments/codebert", exist_ok=True)
np.savez_compressed("experiments/codebert/test_probabilities.npz",
                    y_true=y_true, y_score=y_score)
print(f"\nSaved experiments/codebert/test_probabilities.npz")
print(f"  n_samples={len(y_true):,}  n_positive={int(y_true.sum()):,}")
print(f"  score range: [{y_score.min():.4f}, {y_score.max():.4f}]")
