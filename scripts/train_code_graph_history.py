"""SkyTrace — Experiment D: Code + Graph + History training script.

Usage:
    python scripts/train_code_graph_history.py --config configs/code_graph_history.yaml
    python scripts/train_code_graph_history.py --config configs/code_graph_history.yaml --sample-size 5000

Multi-task loss (if cfg.model.multi_task=true):
    L_total = L_vuln + lambda_cwe * L_cwe
    L_vuln  = WeightedBCEWithLogitsLoss (primary)
    L_cwe   = BCEWithLogitsLoss (secondary — CWE presence prediction)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader, Dataset

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "..", "src")
sys.path.insert(0, _SRC)

from skytrace.data.dataset import load_splits, class_distribution, CodeDataset, CodeDatasetConfig, collate_codebert
from skytrace.models.code_encoder import CodeBERTEncoder, CodeBERTConfig
from skytrace.models.multimodal_model import MultimodalModel, MultimodalConfig
from skytrace.training.losses import WeightedBCEWithLogitsLoss, compute_class_weights
from skytrace.training.callbacks import EarlyStopping, ModelCheckpoint
from skytrace.training.trainer import set_seed
from skytrace.evaluation.metrics import compute_all_metrics, find_best_threshold_by_f1
from skytrace.evaluation.plots import (
    plot_confusion_matrix, plot_roc_curve, plot_pr_curve,
    plot_training_curves, save_metrics_report,
)
from skytrace.features.history_features import HistoryFeatureExtractor
from skytrace.features.graph_builder import graph_stats


# ─── Dataset ─────────────────────────────────────────────────────────────────

class MultimodalDataset(Dataset):
    """Dataset: pre-computed embeddings + commit_keys (for graph) + history features."""

    def __init__(self, embeddings, history, labels, commit_keys, sample_ids, projects, has_cwe=None):
        self.embeddings = torch.tensor(embeddings, dtype=torch.float32)
        self.history = torch.tensor(history, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.float32)
        self.commit_keys = commit_keys
        self.sample_ids = sample_ids
        self.projects = projects
        # CWE presence labels for multi-task
        self.has_cwe = torch.tensor(has_cwe, dtype=torch.float32) if has_cwe is not None \
                       else torch.zeros(len(labels))

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            "embedding": self.embeddings[idx],
            "history": self.history[idx],
            "label": self.labels[idx],
            "commit_key": self.commit_keys[idx],
            "sample_id": self.sample_ids[idx],
            "project": self.projects[idx],
            "has_cwe": self.has_cwe[idx],
        }


def collate_multimodal(batch):
    embeddings = torch.stack([b["embedding"] for b in batch])
    history = torch.stack([b["history"] for b in batch])
    labels = torch.stack([b["label"] for b in batch])
    has_cwe = torch.stack([b["has_cwe"] for b in batch])
    commit_keys = [b["commit_key"] for b in batch]

    # Build co-change edge_index for this batch
    key_to_indices = {}
    for i, ck in enumerate(commit_keys):
        key_to_indices.setdefault(ck, []).append(i)

    src_list, dst_list = [], []
    for ck, indices in key_to_indices.items():
        if 2 <= len(indices) <= 50:
            for i in range(len(indices)):
                for j in range(i + 1, len(indices)):
                    src_list += [indices[i], indices[j]]
                    dst_list += [indices[j], indices[i]]

    if src_list:
        edge_index = torch.tensor([src_list, dst_list], dtype=torch.long)
    else:
        edge_index = torch.zeros((2, 0), dtype=torch.long)

    return {
        "embeddings": embeddings,
        "history": history,
        "labels": labels,
        "has_cwe": has_cwe,
        "edge_index": edge_index,
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
                "commit_keys": list(cache[f"{split_name}__commit_keys"]),
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
        df_r = df.reset_index(drop=True)
        commit_keys = (df_r["project"].astype(str).fillna("UNKNOWN") + "__" +
                       df_r["commit_id"].astype(str).fillna("UNKNOWN")).tolist()
        out[split_name] = {
            "embeddings": np.concatenate(all_emb),
            "labels": np.array(all_labels, dtype=np.float32),
            "sample_ids": all_sids, "projects": all_projs, "commit_keys": commit_keys,
        }
        print(f"  [{split_name}] done in {time.time()-t0:.1f}s")

    save_obj = {}
    for sn, d in out.items():
        for k, v in d.items():
            save_obj[f"{sn}__{k}"] = np.array(v, dtype=object) if isinstance(v, list) else v
    np.savez_compressed(cache_path, **save_obj)
    print(f"[embed] Saved -> {cache_path}")
    return out


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="SkyTrace Experiment D: Code + Graph + History")
    ap.add_argument("--config", default="configs/code_graph_history.yaml")
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
    graph_cfg = cfg.get("graph", {})
    sample_size = args.sample_size or cfg["dataset"].get("sample_size")

    out_dir = exp_cfg["output_dir"]
    ckpt_dir = train_cfg["checkpoint"]["save_dir"]
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(ckpt_dir, exist_ok=True)

    embed_cache = graph_cfg.get("embedding_cache", os.path.join(out_dir, "embeddings_cache.npz"))
    hist_cache = hist_cfg_yaml.get("cache_path", os.path.join(out_dir, "history_features.npz"))
    if args.rebuild_cache:
        for p in [embed_cache, hist_cache]:
            if os.path.exists(p): os.remove(p)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    set_seed(exp_cfg["seed"])

    print("=" * 70)
    print("SkyTrace — Experiment D: Code + Graph + History")
    print(f"  device: {device}  multi_task: {model_cfg.get('multi_task', False)}")
    print(f"  sample_size: {sample_size or 'FULL'}")
    print("=" * 70)

    # 1. Load splits
    print("\n[1/6] Loading splits ...")
    splits = load_splits(dataset_cfg, sample_size=sample_size)
    for name, df in splits.items():
        print(f"  {name:<10}: {len(df):,} rows  class_dist={class_distribution(df)}")

    # 2. History features
    print("\n[2/6] Extracting history features ...")
    extractor = HistoryFeatureExtractor(hist_cfg_yaml.get("long_function_threshold", 50))
    if os.path.exists(hist_cache):
        cache = np.load(hist_cache, allow_pickle=True)
        hist_features = {sn: cache[sn] for sn in ["train", "validation", "test"]}
        extractor.fit(splits["train"])  # re-fit for project density dict
    else:
        hist_features = {
            "train": extractor.fit_transform(splits["train"]),
            "validation": extractor.transform(splits["validation"]),
            "test": extractor.transform(splits["test"]),
        }
        np.savez_compressed(hist_cache, **hist_features)
        print(f"  Saved -> {hist_cache}")

    # 3. Embeddings
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
        print(f"  Loaded from {ckpt_path_a}")

    emb_dict = compute_and_cache_embeddings(
        splits, tokenizer, tok_cfg, train_cfg.get("eval_batch_size", 64),
        encoder, device, embed_cache,
    )

    # 4. Build datasets
    print("\n[4/6] Building datasets ...")
    loaders = {}
    for split_name in ["train", "validation", "test"]:
        d = emb_dict[split_name]
        df_r = splits[split_name].reset_index(drop=True)
        # Build has_cwe from the cwe column
        has_cwe = (df_r["cwe"].astype(str).apply(
            lambda x: 0.0 if x in ("nan", "None", "<NA>", "") else 1.0
        )).values.astype(np.float32)

        ds = MultimodalDataset(
            embeddings=d["embeddings"], history=hist_features[split_name],
            labels=d["labels"], commit_keys=d["commit_keys"],
            sample_ids=d["sample_ids"], projects=d["projects"], has_cwe=has_cwe,
        )
        bs = train_cfg["batch_size"] if split_name == "train" else train_cfg["eval_batch_size"]
        loaders[split_name] = DataLoader(ds, batch_size=bs, shuffle=(split_name == "train"),
                                          num_workers=0, collate_fn=collate_multimodal)
        print(f"  {split_name}: {len(ds):,} samples")

    # 5. Build model
    print("\n[5/6] Building multimodal model ...")
    mm_cfg = MultimodalConfig(
        codebert_model_name=model_cfg["encoder"]["name"],
        codebert_hidden_size=model_cfg["encoder"]["hidden_size"],
        codebert_freeze_layers=model_cfg["encoder"]["freeze_layers"],
        codebert_pooling=model_cfg["pooling"],
        gnn_hidden_channels=model_cfg["gnn"]["hidden_channels"],
        gnn_out_channels=model_cfg["gnn"]["out_channels"],
        gnn_num_layers=model_cfg["gnn"]["num_layers"],
        gnn_dropout=model_cfg["gnn"]["dropout"],
        history_in_features=model_cfg["history"]["in_features"],
        history_hidden_dims=model_cfg["history"]["hidden_dims"],
        history_out_dim=model_cfg["history"]["out_dim"],
        history_dropout=model_cfg["history"]["dropout"],
        fusion_hidden_dims=model_cfg["fusion"]["hidden_dims"],
        fusion_dropout=model_cfg["fusion"]["dropout"],
        multi_task=model_cfg.get("multi_task", False),
        n_classes=model_cfg["n_classes"],
    )
    model = MultimodalModel(mm_cfg)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Trainable params: {trainable:,}")
    model.to(device)

    all_train_labels = torch.tensor(emb_dict["train"]["labels"])
    cw = compute_class_weights(all_train_labels)
    loss_fn = WeightedBCEWithLogitsLoss(pos_weight=cw["pos_weight"].to(device))
    cwe_loss_fn = torch.nn.BCEWithLogitsLoss() if mm_cfg.multi_task else None
    lambda_cwe = train_cfg.get("multi_task_lambda_cwe", 0.2)
    print(f"  pos_weight={cw['pos_weight'].item():.3f}  lambda_cwe={lambda_cwe}")

    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable_params, lr=train_cfg["learning_rate"],
                                   weight_decay=train_cfg["weight_decay"])
    total_steps = len(loaders["train"]) * train_cfg["epochs"]
    warmup_steps = int(total_steps * train_cfg["warmup_ratio"])
    def lr_lambda(step):
        if step < warmup_steps:
            return float(step) / max(1, warmup_steps)
        return max(0.0, (total_steps - step) / max(1, total_steps - warmup_steps))
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

        # Training epoch
        model.train()
        total_loss, n_batches = 0.0, 0
        train_logits_epoch, train_labels_epoch = [], []
        t0 = time.time()
        for step, batch in enumerate(loaders["train"]):
            emb = batch["embeddings"].to(device)
            hist = batch["history"].to(device)
            edge_index = batch["edge_index"].to(device)
            labels = batch["labels"].to(device)
            has_cwe_batch = batch["has_cwe"].to(device)

            # Forward using pre-computed code embeddings
            graph_emb = model.gnn(emb, edge_index)
            hist_emb = model.history_encoder(hist)
            fused = torch.cat([emb, graph_emb, hist_emb], dim=-1)
            trunk_out = model.trunk(fused)
            logits = model.vuln_head(trunk_out).squeeze(-1)

            loss = loss_fn(logits, labels.float())
            if mm_cfg.multi_task and model.cwe_head is not None:
                cwe_logits = model.cwe_head(trunk_out).squeeze(-1)
                loss = loss + lambda_cwe * cwe_loss_fn(cwe_logits, has_cwe_batch)

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            if scheduler is not None:
                scheduler.step()

            total_loss += loss.item()
            n_batches += 1
            train_logits_epoch.append(logits.detach().cpu().numpy())
            train_labels_epoch.append(labels.cpu().numpy())

            if (step + 1) % train_cfg.get("log_interval", 100) == 0:
                print(f"  step {step+1}/{len(loaders['train'])}  loss={loss.item():.4f}  "
                      f"elapsed={time.time()-t0:.1f}s")

        # Validation epoch
        model.eval()
        val_logits_all, val_labels_all = [], []
        with torch.no_grad():
            for batch in loaders["validation"]:
                emb = batch["embeddings"].to(device)
                hist = batch["history"].to(device)
                ei = batch["edge_index"].to(device)
                graph_emb = model.gnn(emb, ei)
                hist_emb = model.history_encoder(hist)
                fused = torch.cat([emb, graph_emb, hist_emb], dim=-1)
                trunk_out = model.trunk(fused)
                logits = model.vuln_head(trunk_out).squeeze(-1)
                val_logits_all.append(logits.cpu().numpy())
                val_labels_all.append(batch["labels"].numpy())

        val_proba = 1.0 / (1.0 + np.exp(-np.concatenate(val_logits_all)))
        val_labels_arr = np.concatenate(val_labels_all)
        val_preds = (val_proba >= 0.5).astype(int)
        val_metrics = compute_all_metrics(val_labels_arr, val_preds, val_proba)
        val_metrics["loss"] = total_loss / max(1, n_batches)

        epoch_log = {"epoch": epoch, "train_loss": total_loss / max(1, n_batches),
                     "val_f1": val_metrics["f1"], "val_roc_auc": val_metrics.get("roc_auc"),
                     "val_pr_auc": val_metrics.get("pr_auc")}
        history.append(epoch_log)
        print(json.dumps(epoch_log, indent=2, default=str))
        checkpoint.maybe_save(model, optimizer, scheduler, val_metrics, epoch, cfg)
        early_stopping.step(val_metrics)
        if early_stopping.should_stop:
            print(f"Early stopping at epoch {epoch}")
            break

    plot_training_curves(history, os.path.join("reports", "training_curves", "code_graph_history.png"),
                         title="Experiment D: Code + Graph + History")

    # Load best
    best_ckpt = os.path.join(ckpt_dir, "best.pt")
    if os.path.exists(best_ckpt):
        state = torch.load(best_ckpt, map_location=device, weights_only=False)
        model.load_state_dict(state["model_state_dict"])

    # Threshold search
    model.eval()
    val_logits_all, val_labels_all = [], []
    with torch.no_grad():
        for batch in loaders["validation"]:
            emb = batch["embeddings"].to(device)
            hist = batch["history"].to(device)
            ei = batch["edge_index"].to(device)
            graph_emb = model.gnn(emb, ei)
            hist_emb = model.history_encoder(hist)
            fused = torch.cat([emb, graph_emb, hist_emb], dim=-1)
            logits = model.vuln_head(model.trunk(fused)).squeeze(-1)
            val_logits_all.append(logits.cpu().numpy())
            val_labels_all.append(batch["labels"].numpy())
    val_proba = 1.0 / (1.0 + np.exp(-np.concatenate(val_logits_all)))
    best_t, best_val_f1 = find_best_threshold_by_f1(np.concatenate(val_labels_all), val_proba)
    print(f"\nBest threshold: {best_t:.2f}  Val F1: {best_val_f1:.6f}")

    # Final test
    test_logits_all, test_labels_all = [], []
    with torch.no_grad():
        for batch in loaders["test"]:
            emb = batch["embeddings"].to(device)
            hist = batch["history"].to(device)
            ei = batch["edge_index"].to(device)
            graph_emb = model.gnn(emb, ei)
            hist_emb = model.history_encoder(hist)
            fused = torch.cat([emb, graph_emb, hist_emb], dim=-1)
            logits = model.vuln_head(model.trunk(fused)).squeeze(-1)
            test_logits_all.append(logits.cpu().numpy())
            test_labels_all.append(batch["labels"].numpy())
    test_proba = 1.0 / (1.0 + np.exp(-np.concatenate(test_logits_all)))
    test_labels_arr = np.concatenate(test_labels_all)
    test_preds = (test_proba >= best_t).astype(int)
    test_metrics = compute_all_metrics(test_labels_arr, test_preds, test_proba, threshold=best_t)

    print("\n" + "=" * 60)
    print("EXPERIMENT D — CODE + GRAPH + HISTORY — TEST RESULTS")
    print(f"  Threshold: {best_t:.2f}  ROC-AUC: {test_metrics.get('roc_auc', 0):.6f}")
    print(f"  PR-AUC: {test_metrics.get('pr_auc', 0):.6f}  F1: {test_metrics['f1']:.6f}")
    print("=" * 60)

    save_metrics_report(test_metrics, os.path.join(out_dir, "test_metrics.json"))
    plot_confusion_matrix(test_metrics["confusion_matrix"], "Exp D — Test",
                          "reports/confusion_matrices/code_graph_history_test.png")
    if test_metrics.get("roc_curve"):
        plot_roc_curve(test_metrics["roc_curve"], "Exp D — ROC",
                       "reports/roc_curves/code_graph_history_test.png", auc=test_metrics.get("roc_auc"))
    if test_metrics.get("pr_curve"):
        plot_pr_curve(test_metrics["pr_curve"], "Exp D — PR",
                      "reports/pr_curves/code_graph_history_test.png", ap=test_metrics.get("pr_auc"))

    with open(os.path.join(out_dir, "experiment.json"), "w", encoding="utf-8") as f:
        json.dump({
            "experiment_name": exp_cfg["name"], "model": "MultimodalModel",
            "multi_task": mm_cfg.multi_task, "lambda_cwe": lambda_cwe,
            "best_threshold": best_t, "val_f1_at_best_threshold": best_val_f1,
            "test_metrics": {k: v for k, v in test_metrics.items()
                             if k not in ("roc_curve", "pr_curve")},
            "history": history, "seed": exp_cfg["seed"], "device": str(device),
        }, f, indent=2, default=str)
    print(f"\n[done] -> {out_dir}/experiment.json")


if __name__ == "__main__":
    main()
