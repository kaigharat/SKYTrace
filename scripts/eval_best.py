import json
import yaml
import torch
import numpy as np
from transformers import AutoTokenizer
from torch.utils.data import DataLoader
from sklearn.metrics import roc_auc_score, average_precision_score, precision_recall_fscore_support, confusion_matrix

from skytrace.models.code_encoder import CodeBERTClassifier, CodeBERTConfig
from skytrace.data.dataset import CodeDataset, CodeDatasetConfig, collate_codebert, load_splits

cfg = yaml.safe_load(open(r"configs/codebert.yaml", encoding="utf-8"))
dataset_cfg = yaml.safe_load(open(r"configs/dataset.yaml", encoding="utf-8"))
splits = load_splits(dataset_cfg["dataset"])

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {device}")
print(f"GPU: {torch.cuda.get_device_name(0)}") if torch.cuda.is_available() else None

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

tok_cfg = cfg["tokenizer"]
dl_cfg = cfg["dataloader"]
model_cfg = cfg["model"]

ds_cfg = CodeDatasetConfig(
    max_length=tok_cfg["max_length"],
    truncation=tok_cfg["truncation"],
    padding=tok_cfg["padding"],
)

def predict_split(split_name):
    ds = CodeDataset(splits[split_name], tok, ds_cfg)
    loader = DataLoader(ds, batch_size=16, shuffle=False, num_workers=0, collate_fn=collate_codebert)
    labels = []
    probs = []
    print(f"Predicting {split_name}: {len(ds)} samples")
    with torch.no_grad():
        for i, batch in enumerate(loader, 1):
            if i == 1 or i % 100 == 0 or i == len(loader): print(f"  batch {i}/{len(loader)}")
            batch = {k: v.to(device) if torch.is_tensor(v) else v for k, v in batch.items()}
            out = model(**{k: batch[k] for k in ["input_ids", "attention_mask"]})
            logits = out["logits"].detach().cpu().numpy().reshape(-1)
            probs.extend((1.0 / (1.0 + np.exp(-logits))).tolist())
            labels.extend(batch["labels"].detach().cpu().numpy().reshape(-1).tolist())
    return np.asarray(labels), np.asarray(probs)

val_y, val_p = predict_split("validation")

best_threshold = 0.5
best_f1 = -1.0
for threshold in np.arange(0.01, 1.00, 0.01):
    preds = (val_p >= threshold).astype(int)
    _, _, f1, _ = precision_recall_fscore_support(val_y, preds, average="binary", zero_division=0)
    if f1 > best_f1:
        best_f1 = f1
        best_threshold = float(threshold)

print(f"BEST VALIDATION THRESHOLD: {best_threshold:.2f}")
print(f"BEST VALIDATION F1: {best_f1:.6f}")

import pandas as pd
import matplotlib.pyplot as plt

threshold_rows = []
for threshold in np.arange(0.01, 1.00, 0.01):
    preds = (val_p >= threshold).astype(int)
    precision_t, recall_t, f1_t, _ = precision_recall_fscore_support(val_y, preds, average="binary", zero_division=0)
    threshold_rows.append({"threshold": round(float(threshold), 2), "precision": float(precision_t), "recall": float(recall_t), "f1": float(f1_t), "predicted_vulnerabilities": int(preds.sum())})

threshold_df = pd.DataFrame(threshold_rows)
threshold_df.to_csv(r"reports\threshold_analysis.csv", index=False)

plt.figure(figsize=(10, 6))
plt.plot(threshold_df["threshold"], threshold_df["precision"], label="Precision")
plt.plot(threshold_df["threshold"], threshold_df["recall"], label="Recall")
plt.plot(threshold_df["threshold"], threshold_df["f1"], label="F1")
plt.axvline(best_threshold, linestyle="--", label=f"Selected threshold = {best_threshold:.2f}")
plt.xlabel("Classification threshold")
plt.ylabel("Score")
plt.title("Validation Threshold Performance")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(r"reports\threshold_analysis.png", dpi=200)
plt.close()

print("Saved: reports\\threshold_analysis.csv")
print("Saved: reports\\threshold_analysis.png")

test_y, test_p = predict_split("test")
test_preds = (test_p >= best_threshold).astype(int)
precision, recall, f1, _ = precision_recall_fscore_support(test_y, test_preds, average="binary", zero_division=0)
roc = roc_auc_score(test_y, test_p)
pr = average_precision_score(test_y, test_p)
cm = confusion_matrix(test_y, test_preds)

print("TEST RESULTS AT VALIDATION-SELECTED THRESHOLD")
print(f"Threshold: {best_threshold:.2f}")
print(f"ROC-AUC: {roc:.6f}")
print(f"PR-AUC: {pr:.6f}")
print(f"Precision: {precision:.6f}")
print(f"Recall: {recall:.6f}")
print(f"F1: {f1:.6f}")
print(f"Predicted positives: {int(test_preds.sum())}")
print("Confusion matrix:")
print(cm)

print("VALIDATION SCORE DISTRIBUTION")
print(f"min={val_p.min():.6f} max={val_p.max():.6f} mean={val_p.mean():.6f} median={np.median(val_p):.6f}")
for q in [0.50, 0.90, 0.95, 0.99, 0.995, 0.999]:
    print(f"q{q}: {np.quantile(val_p, q):.6f}")

print("CHECKPOINT INFO")
print("epoch:", checkpoint.get("epoch")); print("global_step:", checkpoint.get("global_step")); print("best_metric:", checkpoint.get("best_metric")); print("checkpoint keys:", list(checkpoint.keys()))

