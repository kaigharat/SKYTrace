"""SkyTrace — Experiment B: Code + Graph training script.

Usage:
    python scripts/train_code_graph.py --config configs/code_graph.yaml
    python scripts/train_code_graph.py --config configs/code_graph.yaml --sample-size 5000

Pipeline:
    1. Load splits
    2. Pre-compute CodeBERT embeddings (frozen encoder, cached)
    3. Build per-batch co-change graphs from commit_id
    4. Train GraphSAGE + fusion head
    5. Threshold search on validation
    6. Final test evaluation
    7. Save metrics, plots, checkpoint, experiment.json

Design notes:
    - CodeBERT encoder is FROZEN (loaded from Exp A best.pt)
    - Embeddings are pre-computed once and cached — same as what was used
      in Exp A, ensuring the code representation is identical
    - The graph is built PER BATCH from commit_id co-occurrence
    - This means the GNN sees a different subgraph each mini-batch,
      which acts as a form of graph dropout / data augmentation
    - num_workers=0 throughout (Windows multiprocessing limitation)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import yaml
from torch.utils.data import DataLoader, Dataset

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "..", "src")
sys.path.insert(0, _SRC)

from skytrace.data.dataset import load_splits, class_distribution, CodeDataset, CodeDatasetConfig, collate_codebert
from skytrace.models.code_encoder import CodeBERTEncoder, CodeBERTConfig
from skytrace.models.code_graph_model import CodeGraphModel, CodeGraphConfig
from skytrace.training.losses import WeightedBCEWithLogitsLoss, compute_class_weights
from skytrace.training.callbacks import EarlyStopping, ModelCheckpoint
from skytrace.training.trainer import set_seed
from skytrace.evaluation.metrics import compute_all_metrics, find_best_threshold_by_f1
from skytrace.evaluation.plots import (
    plot_confusion_matrix, plot_roc_curve, plot_pr_curve,
    plot_training_curves, save_metrics_report,
)
from skytrace.features.graph_builder import build_cochange_edges, graph_stats


# ─── Dataset ─────────────────────────────────────────────────────────────────

class GraphDataset(Dataset):
    """Dataset that returns pre-computed embeddings + graph info.

    Each item contains:
        embedding:    (768,) float32 CodeBERT embedding
        label:        float32
        commit_key:   str — "project__commit_id" for graph construction
        sample_id:    str
        project:      str
    """

    def __init__(self, embeddings: np.ndarray, labels: np.ndarray,
                 commit_keys: list, sample_ids: list, projects: list):
        self.embeddings = torch.tensor(embeddings, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.float32)
        self.commit_keys = commit_keys
        self.sample_ids = sample_ids
        self.projects = projects

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            "embedding": self.embeddings[idx],
            "label": self.labels[idx],
            "commit_key": self.commit_keys[idx],
            "sample_id": self.sample_ids[idx],
            "project": self.projects[idx],
        }


def collate_graph(batch):
    """Collate function that builds the batch-level co-change graph."""
    embeddings = torch.stack([b["embedding"] for b in batch])
    labels = torch.stack([b["label"] for b in batch])
    commit_keys = [b["commit_key"] for b in batch]
    sample_ids = [b["sample_id"] for b in batch]
    projects = [b["project"] for b in batch]

    # Build co-change edge_index for this batch
    # Group by commit_key within the batch
    key_to_indices: Dict[str, list] = {}
    for i, ck in enumerate(commit_keys):
        if ck not in key_to_indices:
            key_to_indices[ck] = []
        key_to_indices[ck].append(i)

    src_list, dst_list = [], []
    for ck, indices in key_to_indices.items():
        if len(indices) < 2 or len(indices) > 50:
            continue
        for i in range(len(indices)):
            for j in range(i + 1, len(indices)):
                src_list.append(indices[i])
                dst_list.append(indices[j])
                src_list.append(indices[j])
                dst_list.append(indices[i])

    if src_list:
        edge_index = torch.tensor([src_list, dst_list], dtype=torch.long)
    else:
        edge_index = torch.zeros((2, 0), dtype=torch.long)

    return {
        "embeddings": embeddings,
        "labels": labels,
        "edge_index": edge_index,
        "sample_ids": sample_ids,
        "projects": projects,
    }


# ─── Embedding pre-computation ───────────────────────────────────────────────

@torch.no_grad()
def compute_and_cache_embeddings(splits, tokenizer, tok_cfg, dl_cfg, encoder, device, cache_path):
    """Compute CodeBERT embeddings for all splits and cache them."""
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
                "commit_keys": list(cache[f"{split_name}__commit_keys"]),
            }
        return out

    print(f"[embed] Pre-computing CodeBERT embeddings ...")
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
        loader = DataLoader(
            ds, batch_size=dl_cfg.get("eval_batch_size", 128),
            shuffle=False, num_workers=0, collate_fn=collate_codebert,
        )
        all_emb, all_labels, all_sids, all_projs = [], [], [], []
        for i, batch in enumerate(loader, 1):
            if i == 1 or i % 200 == 0 or i == len(loader):
                print(f"  [{split_name}] batch {i}/{len(loader)}")
            input_ids = batch["input_ids"].to(device)
            attn = batch["attention_mask"].to(device)
            emb = encoder(input_ids, attn)  # (B, 768)
            all_emb.append(emb.cpu().float().numpy())
            all_labels.extend(batch["labels"].numpy().tolist())
            all_sids.extend(batch["sample_ids"])
            all_projs.extend(batch["projects"])

        embeddings = np.concatenate(all_emb, axis=0)

        # Build commit_keys from the original df (reset index)
        df_r = df.reset_index(drop=True)
        proj_col = df_r["project"].astype(str).fillna("UNKNOWN")
        commit_col = df_r["commit_id"].astype(str).fillna("UNKNOWN")
        commit_keys = (proj_col + "__" + commit_col).tolist()

        out[split_name] = {
            "embeddings": embeddings,
            "labels": np.array(all_labels, dtype=np.float32),
            "sample_ids": all_sids,
            "projects": all_projs,
            "commit_keys": commit_keys,
        }
        print(f"  [{split_name}] done in {time.time()-t0:.1f}s  shape={embeddings.shape}")

    # Cache to disk
    save_obj = {}
    for sn, d in out.items():
        save_obj[f"{sn}__embeddings"] = d["embeddings"]
        save_obj[f"{sn}__labels"] = d["labels"]
        save_obj[f"{sn}__sample_ids"] = np.array(d["sample_ids"], dtype=object)
        save_obj[f"{sn}__projects"] = np.array(d["projects"], dtype=object)
        save_obj[f"{sn}__commit_keys"] = np.array(d["commit_keys"], dtype=object)
    np.savez_compressed(cache_path, **save_obj)
    print(f"[embed] Saved cache -> {cache_path}")
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
            embeddings = batch["embeddings"].to(device)
            labels = batch["labels"].to(device)
            edge_index = batch["edge_index"].to(device)

            # Build a "fake" forward with pre-computed embeddings:
            # inject into model's code_encoder output directly
            # by bypassing tokenisation and running GNN + fusion only
            out = _forward_precomputed(model, embeddings, edge_index)
            logits = out["logits"]
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
                elapsed = time.time() - t0
                print(f"  step {step+1}/{len(loader)}  loss={loss.item():.4f}  "
                      f"lr={optimizer.param_groups[0]['lr']:.2e}  elapsed={elapsed:.1f}s")

    logits_arr = np.concatenate(all_logits)
    labels_arr = np.concatenate(all_labels)
    proba = 1.0 / (1.0 + np.exp(-logits_arr))
    preds = (proba >= 0.5).astype(int)
    metrics = compute_all_metrics(labels_arr, preds, proba)
    metrics["loss"] = total_loss / max(1, n_batches)
    return metrics


def _forward_precomputed(model: CodeGraphModel, embeddings: torch.Tensor, edge_index: torch.Tensor):
    """Run GNN + fusion head with pre-computed embeddings as code_emb.

    Bypasses the CodeBERT encoder (already pre-computed and frozen).
    """
    code_emb = embeddings                          # (B, 768) — pre-computed
    graph_emb = model.gnn(code_emb, edge_index)   # (B, 256)
    fused = torch.cat([code_emb, graph_emb], dim=-1)  # (B, 1024)
    logits = model.head(fused)
    return {"logits": logits, "code_emb": code_emb, "graph_emb": graph_emb}


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="SkyTrace Experiment B: Code + Graph")
    ap.add_argument("--config", default="configs/code_graph.yaml")
    ap.add_argument("--sample-size", type=int, default=None)
    ap.add_argument("--rebuild-cache", action="store_true")
    args = ap.parse_args()

    # Load configs
    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    with open(os.path.join(os.path.dirname(args.config), cfg["dataset"]["config"]), encoding="utf-8") as f:
        dataset_cfg = yaml.safe_load(f)["dataset"]

    exp_cfg = cfg["experiment"]
    model_cfg = cfg["model"]
    tok_cfg = cfg["tokenizer"]
    train_cfg = cfg["training"]
    dl_cfg = cfg["dataloader"]
    graph_cfg = cfg.get("graph", {})
    sample_size = args.sample_size or cfg["dataset"].get("sample_size")

    out_dir = exp_cfg["output_dir"]
    ckpt_dir = train_cfg["checkpoint"]["save_dir"]
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(ckpt_dir, exist_ok=True)

    cache_path = graph_cfg.get("embedding_cache", os.path.join(out_dir, "embeddings_cache.npz"))
    if args.rebuild_cache and os.path.exists(cache_path):
        os.remove(cache_path)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    set_seed(exp_cfg["seed"])

    print("=" * 70)
    print("SkyTrace — Experiment B: Code + Graph")
    print(f"  device: {device}")
    if torch.cuda.is_available():
        print(f"  GPU: {torch.cuda.get_device_name(0)}")
    print(f"  sample_size: {sample_size or 'FULL'}")
    print("=" * 70)

    # 1. Load splits
    print("\n[1/6] Loading splits ...")
    splits = load_splits(dataset_cfg, sample_size=sample_size)
    for name, df in splits.items():
        print(f"  {name:<10}: {len(df):,} rows  class_dist={class_distribution(df)}")

    # 2. Pre-compute CodeBERT embeddings
    print("\n[2/6] Pre-computing CodeBERT embeddings (frozen encoder) ...")
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_cfg["encoder"]["name"])

    codebert_cfg = CodeBERTConfig(
        model_name=model_cfg["encoder"]["name"],
        hidden_size=model_cfg["encoder"]["hidden_size"],
        freeze_layers=model_cfg["encoder"]["freeze_layers"],
        pooling=model_cfg["pooling"],
    )
    encoder = CodeBERTEncoder(codebert_cfg)

    # Load encoder weights from Exp A checkpoint
    ckpt_path_a = model_cfg.get("load_codebert_from", "models/checkpoints/codebert_baseline/best.pt")
    if os.path.exists(ckpt_path_a):
        state = torch.load(ckpt_path_a, map_location="cpu", weights_only=False)
        encoder_state = {
            k[len("encoder."):]: v
            for k, v in state["model_state_dict"].items()
            if k.startswith("encoder.")
        }
        encoder.load_state_dict(encoder_state, strict=False)
        print(f"  Loaded CodeBERT weights from {ckpt_path_a}")
    else:
        print(f"  WARNING: Exp A checkpoint not found at {ckpt_path_a}; using pretrained weights")

    emb_dict = compute_and_cache_embeddings(
        splits, tokenizer, tok_cfg,
        {"eval_batch_size": train_cfg.get("eval_batch_size", 128)},
        encoder, device, cache_path,
    )

    # 3. Graph stats
    print("\n[3/6] Graph statistics (training split) ...")
    for split_name, df in splits.items():
        stats = graph_stats(df.reset_index(drop=True),
                            max_commit_size=graph_cfg.get("max_commit_size", 50))
        print(f"  {split_name}: {stats}")

    # 4. Build datasets and dataloaders
    print("\n[4/6] Building graph datasets ...")
    datasets, loaders = {}, {}
    for split_name in ["train", "validation", "test"]:
        d = emb_dict[split_name]
        ds = GraphDataset(
            embeddings=d["embeddings"],
            labels=d["labels"],
            commit_keys=d["commit_keys"],
            sample_ids=d["sample_ids"],
            projects=d["projects"],
        )
        datasets[split_name] = ds
        bs = train_cfg["batch_size"] if split_name == "train" else train_cfg["eval_batch_size"]
        loaders[split_name] = DataLoader(
            ds, batch_size=bs, shuffle=(split_name == "train"),
            num_workers=0, collate_fn=collate_graph,
        )
        print(f"  {split_name}: {len(ds):,} samples  batches={len(loaders[split_name])}")

    # 5. Build model
    print("\n[5/6] Building Code + Graph model ...")
    graph_model_cfg = CodeGraphConfig(
        codebert_model_name=model_cfg["encoder"]["name"],
        codebert_hidden_size=model_cfg["encoder"]["hidden_size"],
        codebert_freeze_layers=model_cfg["encoder"]["freeze_layers"],
        codebert_pooling=model_cfg["pooling"],
        gnn_hidden_channels=model_cfg["gnn"]["hidden_channels"],
        gnn_out_channels=model_cfg["gnn"]["out_channels"],
        gnn_num_layers=model_cfg["gnn"]["num_layers"],
        gnn_dropout=model_cfg["gnn"]["dropout"],
        fusion_hidden_dims=model_cfg["fusion"]["hidden_dims"],
        fusion_dropout=model_cfg["fusion"]["dropout"],
        n_classes=model_cfg["n_classes"],
    )
    model = CodeGraphModel(graph_model_cfg)
    # Only GNN + head are trainable (code_encoder already frozen in __init__)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"  Trainable params: {trainable:,} / {total:,}")
    model.to(device)

    # Loss
    all_train_labels = torch.tensor(emb_dict["train"]["labels"])
    cw = compute_class_weights(all_train_labels)
    loss_fn = WeightedBCEWithLogitsLoss(pos_weight=cw["pos_weight"].to(device))
    print(f"  pos_weight={cw['pos_weight'].item():.3f}  (n_pos={cw['n_pos']:,}, n_neg={cw['n_neg']:,})")

    # Optimizer — only train GNN + head
    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable_params, lr=train_cfg["learning_rate"],
                                   weight_decay=train_cfg["weight_decay"])

    # Scheduler
    total_steps = len(loaders["train"]) * train_cfg["epochs"]
    warmup_steps = int(total_steps * train_cfg["warmup_ratio"])
    def lr_lambda(step):
        if step < warmup_steps:
            return float(step) / float(max(1, warmup_steps))
        return max(0.0, float(total_steps - step) / float(max(1, total_steps - warmup_steps)))
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    early_stopping = EarlyStopping(
        patience=train_cfg["early_stopping"]["patience"],
        metric=train_cfg["early_stopping"]["metric"],
        mode=train_cfg["early_stopping"]["mode"],
    )
    checkpoint = ModelCheckpoint(
        save_dir=ckpt_dir,
        save_best=train_cfg["checkpoint"]["save_best"],
        save_last=train_cfg["checkpoint"]["save_last"],
        metric=train_cfg["early_stopping"]["metric"],
        mode=train_cfg["early_stopping"]["mode"],
    )

    # 6. Train
    print("\n[6/6] Training Code + Graph model ...")
    history = []
    for epoch in range(1, train_cfg["epochs"] + 1):
        print(f"\n===== Epoch {epoch}/{train_cfg['epochs']} =====")
        train_metrics = run_epoch(
            model, loaders["train"], optimizer, scheduler, loss_fn, device,
            is_train=True, log_interval=train_cfg.get("log_interval", 100),
        )
        val_metrics = run_epoch(
            model, loaders["validation"], optimizer, scheduler, loss_fn, device,
            is_train=False,
        )
        epoch_log = {
            "epoch": epoch,
            "train_loss": train_metrics["loss"],
            "val_loss": val_metrics["loss"],
            "val_precision": val_metrics["precision"],
            "val_recall": val_metrics["recall"],
            "val_f1": val_metrics["f1"],
            "val_roc_auc": val_metrics.get("roc_auc"),
            "val_pr_auc": val_metrics.get("pr_auc"),
        }
        history.append(epoch_log)
        print(json.dumps(epoch_log, indent=2, default=str))

        checkpoint.maybe_save(model, optimizer, scheduler, val_metrics, epoch, cfg)
        early_stopping.step(val_metrics)
        if early_stopping.should_stop:
            print(f"[trainer] Early stopping at epoch {epoch}")
            break

    # Plot training curves
    plot_training_curves(history,
                         os.path.join("reports", "training_curves", "code_graph.png"),
                         title="Experiment B: Code + Graph")

    # Load best checkpoint for final eval
    best_ckpt = os.path.join(ckpt_dir, "best.pt")
    if os.path.exists(best_ckpt):
        state = torch.load(best_ckpt, map_location=device, weights_only=False)
        model.load_state_dict(state["model_state_dict"])
        print(f"\nLoaded best checkpoint from {best_ckpt}")

    # Threshold search on validation
    print("\nThreshold search on VALIDATION ...")
    model.eval()
    val_logits_all, val_labels_all = [], []
    with torch.no_grad():
        for batch in loaders["validation"]:
            emb = batch["embeddings"].to(device)
            ei = batch["edge_index"].to(device)
            out = _forward_precomputed(model, emb, ei)
            logits = out["logits"]
            if logits.dim() == 2:
                logits = logits.squeeze(-1)
            val_logits_all.append(logits.cpu().numpy())
            val_labels_all.append(batch["labels"].numpy())

    val_logits_all = np.concatenate(val_logits_all)
    val_labels_all = np.concatenate(val_labels_all)
    val_proba = 1.0 / (1.0 + np.exp(-val_logits_all))
    best_t, best_val_f1 = find_best_threshold_by_f1(val_labels_all, val_proba)
    print(f"Best threshold: {best_t:.2f}  Val F1: {best_val_f1:.6f}")

    # Final test evaluation
    print("\nFinal TEST evaluation ...")
    test_logits_all, test_labels_all = [], []
    with torch.no_grad():
        for batch in loaders["test"]:
            emb = batch["embeddings"].to(device)
            ei = batch["edge_index"].to(device)
            out = _forward_precomputed(model, emb, ei)
            logits = out["logits"]
            if logits.dim() == 2:
                logits = logits.squeeze(-1)
            test_logits_all.append(logits.cpu().numpy())
            test_labels_all.append(batch["labels"].numpy())

    test_logits_all = np.concatenate(test_logits_all)
    test_labels_all = np.concatenate(test_labels_all)
    test_proba = 1.0 / (1.0 + np.exp(-test_logits_all))
    test_preds = (test_proba >= best_t).astype(int)
    test_metrics = compute_all_metrics(test_labels_all, test_preds, test_proba, threshold=best_t)

    print("\n" + "=" * 60)
    print("EXPERIMENT B — CODE + GRAPH — TEST RESULTS")
    print(f"  Threshold (val-selected): {best_t:.2f}")
    print(f"  ROC-AUC:   {test_metrics.get('roc_auc', 'N/A'):.6f}")
    print(f"  PR-AUC:    {test_metrics.get('pr_auc', 'N/A'):.6f}")
    print(f"  Precision: {test_metrics['precision']:.6f}")
    print(f"  Recall:    {test_metrics['recall']:.6f}")
    print(f"  F1:        {test_metrics['f1']:.6f}")
    print("=" * 60)

    # Save artifacts
    save_metrics_report(test_metrics, os.path.join(out_dir, "test_metrics.json"))

    # Save raw probabilities for ranking evaluation
    np.savez_compressed(os.path.join(out_dir, "test_probabilities.npz"),
                        y_true=test_labels_all, y_score=test_proba)
    print(f"[saved] test_probabilities.npz -> {out_dir}/")

    plot_confusion_matrix(test_metrics["confusion_matrix"],
                          "Exp B (Code+Graph) — Test Confusion Matrix",
                          "reports/confusion_matrices/code_graph_test.png")
    if test_metrics.get("roc_curve"):
        plot_roc_curve(test_metrics["roc_curve"],
                       "Exp B (Code+Graph) — Test ROC Curve",
                       "reports/roc_curves/code_graph_test.png",
                       auc=test_metrics.get("roc_auc"))
    if test_metrics.get("pr_curve"):
        plot_pr_curve(test_metrics["pr_curve"],
                      "Exp B (Code+Graph) — Test PR Curve",
                      "reports/pr_curves/code_graph_test.png",
                      ap=test_metrics.get("pr_auc"))

    experiment_metadata = {
        "experiment_name": exp_cfg["name"],
        "model": "CodeGraphModel",
        "codebert_checkpoint": ckpt_path_a,
        "device": str(device),
        "sample_size": sample_size,
        "split_sizes": {k: len(v) for k, v in splits.items()},
        "best_threshold": best_t,
        "val_f1_at_best_threshold": best_val_f1,
        "test_metrics": {k: v for k, v in test_metrics.items()
                         if k not in ("roc_curve", "pr_curve", "sample_ids", "projects")},
        "history": history,
        "seed": exp_cfg["seed"],
    }
    with open(os.path.join(out_dir, "experiment.json"), "w", encoding="utf-8") as f:
        json.dump(experiment_metadata, f, indent=2, default=str)
    print(f"\n[done] Saved experiment metadata -> {out_dir}/experiment.json")


if __name__ == "__main__":
    main()
