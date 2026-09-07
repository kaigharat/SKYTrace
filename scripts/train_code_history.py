"""SkyTrace — Experiment C: Code + History training script.

Usage:
    python scripts/train_code_history.py --config configs/code_history.yaml
    python scripts/train_code_history.py --config configs/code_history.yaml --sample-size 5000

Pipeline:
    1. Load splits
    2. Fit HistoryFeatureExtractor on TRAINING data only (leakage-safe)
    3. Transform all splits to history feature matrices
    4. Pre-compute/cache CodeBERT embeddings (frozen encoder, same as Exp A)
    5. Train History encoder + fusion head
    6. Threshold search on validation
    7. Final test evaluation
    8. Save metrics, plots, checkpoint, experiment.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict

import numpy as np
import torch
import torch.nn as nn
import yaml
from torch.utils.data import DataLoader, Dataset

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "..", "src")
sys.path.insert(0, _SRC)

from skytrace.data.dataset import load_splits, class_distribution, CodeDataset, CodeDatasetConfig, collate_codebert
from skytrace.models.code_encoder import CodeBERTEncoder, CodeBERTConfig
from skytrace.models.code_history_model import CodeHistoryModel, CodeHistoryConfig
from skytrace.training.losses import WeightedBCEWithLogitsLoss, compute_class_weights
from skytrace.training.callbacks import EarlyStopping, ModelCheckpoint
from skytrace.training.trainer import set_seed
from skytrace.evaluation.metrics import compute_all_metrics, find_best_threshold_by_f1
from skytrace.evaluation.plots import (
    plot_confusion_matrix, plot_roc_curve, plot_pr_curve,
    plot_training_curves, save_metrics_report,
)
from skytrace.features.history_features import HistoryFeatureExtractor


# ─── Dataset ─────────────────────────────────────────────────────────────────

class CodeHistoryDataset(Dataset):
    """Dataset combining pre-computed CodeBERT embeddings + history features."""

    def __init__(self, embeddings: np.ndarray, history: np.ndarray,
                 labels: np.ndarray, sample_ids: list, projects: list):
        self.embeddings = torch.tensor(embeddings, dtype=torch.float32)
        self.history = torch.tensor(history, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.float32)
        self.sample_ids = sample_ids
        self.projects = projects

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            "embedding": self.embeddings[idx],
            "history": self.history[idx],
            "label": self.labels[idx],
            "sample_id": self.sample_ids[idx],
            "project": self.projects[idx],
        }


def collate_code_history(batch):
    return {
        "embeddings": torch.stack([b["embedding"] for b in batch]),
        "history": torch.stack([b["history"] for b in batch]),
        "labels": torch.stack([b["label"] for b in batch]),
        "sample_ids": [b["sample_id"] for b in batch],
        "projects": [b["project"] for b in batch],
    }


# ─── Embedding pre-computation ───────────────────────────────────────────────

@torch.no_grad()
def compute_and_cache_embeddings(splits, tokenizer, tok_cfg, batch_size, encoder, device, cache_path):
    if os.path.exists(cache_path):
        print(f"[embed] Loading cached embeddings from {cache_path}")
        cache = np.load(cache_path, allow_pickle=True)
        out = {}
        for split_name in ["train", "validation", "test"]:
            out[split_name] = {
                "embeddings": cache[f"{split_name}__embeddings"],
                "labels":     cache[f"{split_name}__labels"],
                "sample_ids": list(cache[f"{split_name}__sample_ids"]),
                "projects":   list(cache[f"{split_name}__projects"]),
            }
        return out

    print("[embed] Pre-computing CodeBERT embeddings ...")
    code_cfg = CodeDatasetConfig(
        max_length=tok_cfg["max_length"],
        truncation=tok_cfg["truncation"],
        padding=tok_cfg["padding"],
    )
    encoder.eval()
    encoder.to(device)
    out = {}

    for split_name, df in splits.items():
        t0 = time.time()
        ds = CodeDataset(df, tokenizer, code_cfg)
        loader = DataLoader(ds, batch_size=batch_size, shuffle=False,
                            num_workers=0, collate_fn=collate_codebert)
        all_emb, all_labels, all_sids, all_projs = [], [], [], []
        for i, batch in enumerate(loader, 1):
            if i == 1 or i % 200 == 0 or i == len(loader):
                print(f"  [{split_name}] batch {i}/{len(loader)}")
            emb = encoder(batch["input_ids"].to(device), batch["attention_mask"].to(device))
            all_emb.append(emb.cpu().float().numpy())
            all_labels.extend(batch["labels"].numpy().tolist())
            all_sids.extend(batch["sample_ids"])
            all_projs.extend(batch["projects"])

        out[split_name] = {
            "embeddings": np.concatenate(all_emb),
            "labels": np.array(all_labels, dtype=np.float32),
            "sample_ids": all_sids,
            "projects": all_projs,
        }
        print(f"  [{split_name}] done in {time.time()-t0:.1f}s")

    save_obj = {}
    for sn, d in out.items():
        save_obj[f"{sn}__embeddings"] = d["embeddings"]
        save_obj[f"{sn}__labels"] = d["labels"]
        save_obj[f"{sn}__sample_ids"] = np.array(d["sample_ids"], dtype=object)
        save_obj[f"{sn}__projects"] = np.array(d["projects"], dtype=object)
    np.savez_compressed(cache_path, **save_obj)
    print(f"[embed] Saved -> {cache_path}")
    return out


# ─── Training loop ───────────────────────────────────────────────────────────

def run_epoch(model, loader, optimizer, scheduler, loss_fn, device, is_train, log_interval=100):
    model.train() if is_train else model.eval()
    total_loss, n_batches = 0.0, 0
    all_logits, all_labels = [], []
    t0 = time.time()

    ctx = torch.enable_grad() if is_train else torch.no_grad()
    with ctx:
        for step, batch in enumerate(loader):
            emb = batch["embeddings"].to(device)
            hist = batch["history"].to(device)
            labels = batch["labels"].to(device)

            # Forward: bypass code_encoder (pre-computed), run history+fusion
            hist_emb = model.history_encoder(hist)
            fused = torch.cat([emb, hist_emb], dim=-1)
            logits = model.head(fused)
            if logits.dim() == 2 and logits.size(1) == 1:
                logits = logits.squeeze(-1)
            loss = loss_fn(logits, labels.float())

            if is_train:
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                if scheduler is not None:
                    scheduler.step()

            total_loss += loss.item()
            n_batches += 1
            all_logits.append(logits.detach().cpu().numpy())
            all_labels.append(labels.cpu().numpy())

            if is_train and (step + 1) % log_interval == 0:
                print(f"  step {step+1}/{len(loader)}  loss={loss.item():.4f}  "
                      f"lr={optimizer.param_groups[0]['lr']:.2e}  elapsed={time.time()-t0:.1f}s")

    logits_arr = np.concatenate(all_logits)
    labels_arr = np.concatenate(all_labels)
    proba = 1.0 / (1.0 + np.exp(-logits_arr))
    preds = (proba >= 0.5).astype(int)
    metrics = compute_all_metrics(labels_arr, preds, proba)
    metrics["loss"] = total_loss / max(1, n_batches)
    return metrics


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="SkyTrace Experiment C: Code + History")
    ap.add_argument("--config", default="configs/code_history.yaml")
    ap.add_argument("--sample-size", type=int, default=None)
    ap.add_argument("--rebuild-cache", action="store_true")
    args = ap.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    with open(os.path.join(os.path.dirname(args.config), cfg["dataset"]["config"]), encoding="utf-8") as f:
        dataset_cfg = yaml.safe_load(f)["dataset"]

    exp_cfg = cfg["experiment"]
    model_cfg = cfg["model"]
    tok_cfg = cfg["tokenizer"]
    train_cfg = cfg["training"]
    hist_cfg_yaml = cfg.get("history_features", {})
    sample_size = args.sample_size or cfg["dataset"].get("sample_size")

    out_dir = exp_cfg["output_dir"]
    ckpt_dir = train_cfg["checkpoint"]["save_dir"]
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(ckpt_dir, exist_ok=True)

    embed_cache = os.path.join(out_dir, "embeddings_cache.npz")
    hist_cache = hist_cfg_yaml.get("cache_path", os.path.join(out_dir, "history_features.npz"))
    if args.rebuild_cache:
        for p in [embed_cache, hist_cache]:
            if os.path.exists(p):
                os.remove(p)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    set_seed(exp_cfg["seed"])

    print("=" * 70)
    print("SkyTrace — Experiment C: Code + History")
    print(f"  device: {device}")
    print(f"  sample_size: {sample_size or 'FULL'}")
    print("=" * 70)

    # 1. Load splits
    print("\n[1/6] Loading splits ...")
    splits = load_splits(dataset_cfg, sample_size=sample_size)
    for name, df in splits.items():
        print(f"  {name:<10}: {len(df):,} rows  class_dist={class_distribution(df)}")

    # 2. History features (fit on train only)
    print("\n[2/6] Extracting history features ...")
    extractor = HistoryFeatureExtractor(
        long_function_threshold=hist_cfg_yaml.get("long_function_threshold", 50)
    )
    if os.path.exists(hist_cache):
        print(f"  Loading cached history features from {hist_cache}")
        cache = np.load(hist_cache, allow_pickle=True)
        hist_features = {sn: cache[sn] for sn in ["train", "validation", "test"]}
        # Re-fit extractor for leakage-safe project density (needed for test)
        extractor.fit(splits["train"])
    else:
        train_hist = extractor.fit_transform(splits["train"])
        val_hist = extractor.transform(splits["validation"])
        test_hist = extractor.transform(splits["test"])
        hist_features = {"train": train_hist, "validation": val_hist, "test": test_hist}
        np.savez_compressed(hist_cache, **hist_features)
        print(f"  Saved history features -> {hist_cache}")

    for sn, h in hist_features.items():
        print(f"  {sn}: shape={h.shape}  mean={h.mean(axis=0).round(3)}")

    # 3. Pre-compute CodeBERT embeddings
    print("\n[3/6] Pre-computing CodeBERT embeddings ...")
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_cfg["encoder"]["name"])

    codebert_cfg = CodeBERTConfig(
        model_name=model_cfg["encoder"]["name"],
        hidden_size=model_cfg["encoder"]["hidden_size"],
        freeze_layers=model_cfg["encoder"]["freeze_layers"],
        pooling=model_cfg["pooling"],
    )
    encoder = CodeBERTEncoder(codebert_cfg)
    ckpt_path_a = model_cfg.get("load_codebert_from", "models/checkpoints/codebert_baseline/best.pt")
    if os.path.exists(ckpt_path_a):
        state = torch.load(ckpt_path_a, map_location="cpu", weights_only=False)
        encoder_state = {k[len("encoder."):]: v for k, v in state["model_state_dict"].items()
                         if k.startswith("encoder.")}
        encoder.load_state_dict(encoder_state, strict=False)
        print(f"  Loaded CodeBERT from {ckpt_path_a}")

    emb_dict = compute_and_cache_embeddings(
        splits, tokenizer, tok_cfg, train_cfg.get("eval_batch_size", 64),
        encoder, device, embed_cache,
    )

    # 4. Build datasets
    print("\n[4/6] Building datasets ...")
    loaders = {}
    for split_name in ["train", "validation", "test"]:
        d = emb_dict[split_name]
        ds = CodeHistoryDataset(
            embeddings=d["embeddings"],
            history=hist_features[split_name],
            labels=d["labels"],
            sample_ids=d["sample_ids"],
            projects=d["projects"],
        )
        bs = train_cfg["batch_size"] if split_name == "train" else train_cfg["eval_batch_size"]
        loaders[split_name] = DataLoader(ds, batch_size=bs, shuffle=(split_name == "train"),
                                          num_workers=0, collate_fn=collate_code_history)
        print(f"  {split_name}: {len(ds):,} samples")

    # 5. Build model
    print("\n[5/6] Building Code + History model ...")
    ch_cfg = CodeHistoryConfig(
        codebert_model_name=model_cfg["encoder"]["name"],
        codebert_hidden_size=model_cfg["encoder"]["hidden_size"],
        codebert_freeze_layers=model_cfg["encoder"]["freeze_layers"],
        codebert_pooling=model_cfg["pooling"],
        history_in_features=model_cfg["history"]["in_features"],
        history_hidden_dims=model_cfg["history"]["hidden_dims"],
        history_out_dim=model_cfg["history"]["out_dim"],
        history_dropout=model_cfg["history"]["dropout"],
        fusion_hidden_dims=model_cfg["fusion"]["hidden_dims"],
        fusion_dropout=model_cfg["fusion"]["dropout"],
        n_classes=model_cfg["n_classes"],
    )
    model = CodeHistoryModel(ch_cfg)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"  Trainable params: {trainable:,} / {total:,}")
    model.to(device)

    all_train_labels = torch.tensor(emb_dict["train"]["labels"])
    cw = compute_class_weights(all_train_labels)
    loss_fn = WeightedBCEWithLogitsLoss(pos_weight=cw["pos_weight"].to(device))
    print(f"  pos_weight={cw['pos_weight'].item():.3f}")

    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable_params, lr=train_cfg["learning_rate"],
                                   weight_decay=train_cfg["weight_decay"])
    total_steps = len(loaders["train"]) * train_cfg["epochs"]
    warmup_steps = int(total_steps * train_cfg["warmup_ratio"])
    def lr_lambda(step):
        if step < warmup_steps:
            return float(step) / float(max(1, warmup_steps))
        return max(0.0, float(total_steps - step) / float(max(1, total_steps - warmup_steps)))
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    early_stopping = EarlyStopping(patience=train_cfg["early_stopping"]["patience"],
                                    metric=train_cfg["early_stopping"]["metric"],
                                    mode=train_cfg["early_stopping"]["mode"])
    checkpoint = ModelCheckpoint(save_dir=ckpt_dir,
                                  metric=train_cfg["early_stopping"]["metric"],
                                  mode=train_cfg["early_stopping"]["mode"])

    # 6. Train
    print("\n[6/6] Training ...")
    history = []
    for epoch in range(1, train_cfg["epochs"] + 1):
        print(f"\n===== Epoch {epoch}/{train_cfg['epochs']} =====")
        train_m = run_epoch(model, loaders["train"], optimizer, scheduler, loss_fn,
                             device, is_train=True, log_interval=train_cfg.get("log_interval", 100))
        val_m = run_epoch(model, loaders["validation"], optimizer, scheduler, loss_fn,
                           device, is_train=False)
        epoch_log = {"epoch": epoch, "train_loss": train_m["loss"], "val_loss": val_m["loss"],
                     "val_f1": val_m["f1"], "val_roc_auc": val_m.get("roc_auc"),
                     "val_pr_auc": val_m.get("pr_auc")}
        history.append(epoch_log)
        print(json.dumps(epoch_log, indent=2, default=str))
        checkpoint.maybe_save(model, optimizer, scheduler, val_m, epoch, cfg)
        early_stopping.step(val_m)
        if early_stopping.should_stop:
            print(f"Early stopping at epoch {epoch}")
            break

    plot_training_curves(history, os.path.join("reports", "training_curves", "code_history.png"),
                         title="Experiment C: Code + History")

    # Load best checkpoint
    best_ckpt = os.path.join(ckpt_dir, "best.pt")
    if os.path.exists(best_ckpt):
        state = torch.load(best_ckpt, map_location=device, weights_only=False)
        model.load_state_dict(state["model_state_dict"])

    # Threshold search
    model.eval()
    val_logits_all, val_labels_all = [], []
    with torch.no_grad():
        for batch in loaders["validation"]:
            hist_emb = model.history_encoder(batch["history"].to(device))
            fused = torch.cat([batch["embeddings"].to(device), hist_emb], dim=-1)
            logits = model.head(fused).squeeze(-1)
            val_logits_all.append(logits.cpu().numpy())
            val_labels_all.append(batch["labels"].numpy())
    val_proba = 1.0 / (1.0 + np.exp(-np.concatenate(val_logits_all)))
    val_labels_all = np.concatenate(val_labels_all)
    best_t, best_val_f1 = find_best_threshold_by_f1(val_labels_all, val_proba)
    print(f"\nBest threshold: {best_t:.2f}  Val F1: {best_val_f1:.6f}")

    # Final test
    test_logits_all, test_labels_all = [], []
    with torch.no_grad():
        for batch in loaders["test"]:
            hist_emb = model.history_encoder(batch["history"].to(device))
            fused = torch.cat([batch["embeddings"].to(device), hist_emb], dim=-1)
            logits = model.head(fused).squeeze(-1)
            test_logits_all.append(logits.cpu().numpy())
            test_labels_all.append(batch["labels"].numpy())
    test_proba = 1.0 / (1.0 + np.exp(-np.concatenate(test_logits_all)))
    test_labels_all = np.concatenate(test_labels_all)
    test_preds = (test_proba >= best_t).astype(int)
    test_metrics = compute_all_metrics(test_labels_all, test_preds, test_proba, threshold=best_t)

    print("\n" + "=" * 60)
    print("EXPERIMENT C — CODE + HISTORY — TEST RESULTS")
    print(f"  Threshold: {best_t:.2f}  ROC-AUC: {test_metrics.get('roc_auc', 0):.6f}")
    print(f"  PR-AUC: {test_metrics.get('pr_auc', 0):.6f}  F1: {test_metrics['f1']:.6f}")
    print("=" * 60)

    save_metrics_report(test_metrics, os.path.join(out_dir, "test_metrics.json"))
    plot_confusion_matrix(test_metrics["confusion_matrix"], "Exp C (Code+History) — Test",
                          "reports/confusion_matrices/code_history_test.png")
    if test_metrics.get("roc_curve"):
        plot_roc_curve(test_metrics["roc_curve"], "Exp C — ROC Curve",
                       "reports/roc_curves/code_history_test.png", auc=test_metrics.get("roc_auc"))
    if test_metrics.get("pr_curve"):
        plot_pr_curve(test_metrics["pr_curve"], "Exp C — PR Curve",
                      "reports/pr_curves/code_history_test.png", ap=test_metrics.get("pr_auc"))

    with open(os.path.join(out_dir, "experiment.json"), "w", encoding="utf-8") as f:
        json.dump({
            "experiment_name": exp_cfg["name"],
            "model": "CodeHistoryModel",
            "history_features": extractor.feature_names(),
            "best_threshold": best_t, "val_f1_at_best_threshold": best_val_f1,
            "test_metrics": {k: v for k, v in test_metrics.items()
                             if k not in ("roc_curve", "pr_curve")},
            "history": history, "seed": exp_cfg["seed"], "device": str(device),
        }, f, indent=2, default=str)
    print(f"\n[done] Saved -> {out_dir}/experiment.json")


if __name__ == "__main__":
    main()
