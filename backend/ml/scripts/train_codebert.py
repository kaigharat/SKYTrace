"""SkyTrace — CodeBERT baseline training script.

Usage:
    python scripts/train_codebert.py --config configs/codebert.yaml --sample-size 5000
    python scripts/train_codebert.py --config configs/codebert.yaml

Pipeline:
    1. Load splits
    2. Build tokenizer + CodeBERTClassifier
    3. (Optional, default ON) Pre-compute CodeBERT embeddings once on
       train+val+test, cache to disk. Then train the MLP head on cached
       embeddings — fast even on CPU.
    4. Train MLP head with class-weighted BCE + early stopping on val PR-AUC
    5. Evaluate on test
    6. Save metrics, plots, checkpoints, experiment artifacts

In full-fine-tune mode (cache_embeddings=false), the encoder is also
trained end-to-end. This requires a GPU to be practical on the full
DiverseVul dataset (327K samples).
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
from torch.utils.data import DataLoader
from transformers import AutoTokenizer

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "..", "src")
sys.path.insert(0, _SRC)

from skytrace.data.dataset import CodeDataset, CodeDatasetConfig, collate_codebert, load_splits, class_distribution
from skytrace.models.code_encoder import CodeBERTClassifier, CodeBERTConfig, \
    compute_embeddings, save_embedding_cache, load_embedding_cache
from skytrace.training.trainer import CodeBERTTrainer, TrainerConfig, set_seed
from skytrace.evaluation.metrics import compute_all_metrics, find_best_threshold_by_f1
from skytrace.evaluation.plots import (
    plot_confusion_matrix, plot_roc_curve, plot_pr_curve, plot_training_curves, save_metrics_report
)


def load_config(path: str) -> Dict[str, Any]:
    path = os.path.abspath(path)
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    dcfg_path = os.path.join(os.path.dirname(path), cfg["dataset"]["config"])
    with open(dcfg_path, "r", encoding="utf-8") as f:
        cfg["dataset_full"] = yaml.safe_load(f)
    return cfg


def get_dataloaders(splits, tokenizer, tok_cfg, dl_cfg, sample_size=None):
    """Build train/val/test DataLoaders."""
    code_cfg = CodeDatasetConfig(
        text_col="function_code",
        label_col="label",
        sample_id_col="sample_id",
        project_col="project",
        max_length=tok_cfg["max_length"],
        truncation=tok_cfg["truncation"],
        padding=tok_cfg["padding"],
    )
    loaders = {}
    for name, df in splits.items():
        ds = CodeDataset(df, tokenizer, code_cfg)
        bs = dl_cfg.get("eval_batch_size", 32) if name != "train" else None
        if bs is None:
            bs = 16
        loaders[name] = DataLoader(
            ds, batch_size=bs, shuffle=(name == "train"),
            num_workers=dl_cfg.get("num_workers", 0),
            pin_memory=dl_cfg.get("pin_memory", False),
            collate_fn=collate_codebert,
        )
    return loaders


@torch.no_grad()
def precompute_embeddings(model, loaders, device, cache_path):
    """Compute + cache embeddings for train/val/test."""
    if os.path.exists(cache_path):
        print(f"[encoder] loading cached embeddings from {cache_path}")
        cache = np.load(cache_path, allow_pickle=True)
        emb = {k: cache[k] for k in cache.files}
        return emb
    print(f"[encoder] pre-computing CodeBERT embeddings (CPU) ...")
    emb_dict = {}
    for name, loader in loaders.items():
        print(f"  encoding {name} ({len(loader.dataset):,} rows) ...")
        t0 = time.time()
        e, sids, projs = compute_embeddings(model.encoder, loader, device)
        labels = loader.dataset.labels
        emb_dict[name] = {
            "embeddings": e,
            "sample_ids": np.array(sids, dtype=object),
            "projects": np.array(projs, dtype=object),
            "labels": np.array(labels, dtype=np.int64),
        }
        print(f"  done in {time.time() - t0:.1f}s  shape={e.shape}")
    np.savez_compressed(cache_path, **{k: v for d in emb_dict.values() for k, v in d.items()})
    # Actually we need per-split; restructure
    save_obj = {}
    for split_name, d in emb_dict.items():
        for k, v in d.items():
            save_obj[f"{split_name}__{k}"] = v
    np.savez_compressed(cache_path, **save_obj)
    print(f"[encoder] saved cache -> {cache_path}")
    return emb_dict


def load_cached_embeddings(cache_path):
    cache = np.load(cache_path, allow_pickle=True)
    out = {}
    for split_name in ["train", "validation", "test"]:
        out[split_name] = {
            "embeddings": cache[f"{split_name}__embeddings"],
            "sample_ids": list(cache[f"{split_name}__sample_ids"]),
            "projects": list(cache[f"{split_name}__projects"]),
            "labels": cache[f"{split_name}__labels"],
        }
    return out


# ----- MLP head for cached embeddings --------------------------------------

class CachedEmbeddingMLP(nn.Module):
    """MLP head trained on pre-computed CodeBERT embeddings.

    Architecturally identical to CodeBERTClassifier.head — designed so that
    a model trained here can later be loaded into the full
    CodeBERTClassifier for inference on new code.
    """

    def __init__(self, hidden_size: int, classifier_hidden_dims, dropout: float, n_classes: int = 1):
        super().__init__()
        layers = []
        in_dim = hidden_size
        for h in classifier_hidden_dims:
            layers.append(nn.Linear(in_dim, h))
            layers.append(nn.GELU())
            layers.append(nn.Dropout(dropout))
            in_dim = h
        layers.append(nn.Linear(in_dim, n_classes))
        self.head = nn.Sequential(*layers)

    def forward(self, embeddings: torch.Tensor) -> Dict[str, torch.Tensor]:
        logits = self.head(embeddings)
        return {"logits": logits, "pooled": embeddings}


class CachedEmbeddingDataset(torch.utils.data.Dataset):
    def __init__(self, embeddings, labels, sample_ids, projects):
        self.embeddings = torch.tensor(embeddings, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.float32)
        self.sample_ids = sample_ids
        self.projects = projects

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            "input_ids": self.embeddings[idx],   # reuse key for compatibility with trainer
            "attention_mask": torch.ones_like(self.embeddings[idx]),
            "label": self.labels[idx],
            "sample_id": self.sample_ids[idx],
            "project": self.projects[idx],
        }


def collate_cached(batch):
    emb = torch.stack([b["input_ids"] for b in batch])
    labels = torch.stack([b["label"] for b in batch])
    return {
        "input_ids": emb,
        "attention_mask": torch.ones_like(emb),
        "labels": labels,
        "sample_ids": [b["sample_id"] for b in batch],
        "projects": [b["project"] for b in batch],
    }


def main():
    ap = argparse.ArgumentParser(description="SkyTrace CodeBERT baseline training")
    ap.add_argument("--config", default="configs/codebert.yaml")
    ap.add_argument("--sample-size", type=int, default=None,
                    help="Dev mode: take first N rows of each split.")
    ap.add_argument("--resume", default=None,
                    help="Resume full fine-tuning from a checkpoint (.pt).")
    ap.add_argument("--rebuild-cache", action="store_true",
                    help="Force re-computing the embedding cache.")
    args = ap.parse_args()

    cfg = load_config(args.config)
    exp_cfg = cfg["experiment"]
    model_cfg = cfg["model"]
    tok_cfg = cfg["tokenizer"]
    train_cfg = cfg["training"]
    dl_cfg = cfg["dataloader"]
    eval_cfg = cfg["evaluation"]
    dataset_cfg = cfg["dataset_full"]["dataset"]
    sample_size = args.sample_size or cfg["dataset"].get("sample_size")

    out_dir = exp_cfg["output_dir"]
    os.makedirs(out_dir, exist_ok=True)
    ckpt_dir = train_cfg["checkpoint"]["save_dir"]
    os.makedirs(ckpt_dir, exist_ok=True)
    cache_path = model_cfg.get("cache_path", os.path.join(out_dir, "embeddings_cache.npz"))
    if args.rebuild_cache and os.path.exists(cache_path):
        os.remove(cache_path)

    print("=" * 70)
    print(f"SkyTrace — CodeBERT Baseline")
    print(f"  experiment: {exp_cfg['name']}")
    print(f"  encoder: {model_cfg['encoder']['name']}")
    print(f"  pooling: {model_cfg['pooling']}")
    print(f"  cache_embeddings: {model_cfg['cache_embeddings']}")
    print(f"  sample_size: {sample_size or 'FULL'}")
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    set_seed(exp_cfg["seed"])
    print(f"  device: {device}")
    print("=" * 70)


    # 1. Load splits
    print("\n[1/5] Loading splits ...")
    splits = load_splits(dataset_cfg, sample_size=sample_size)
    for name, df in splits.items():
        print(f"  {name:<10}: {len(df):,} rows  class_dist={class_distribution(df)}")

    # 2. Tokenizer + model
    print("\n[2/5] Building tokenizer + CodeBERT model ...")
    tokenizer = AutoTokenizer.from_pretrained(model_cfg["encoder"]["name"])
    codebert_cfg = CodeBERTConfig(
        model_name=model_cfg["encoder"]["name"],
        hidden_size=model_cfg["encoder"]["hidden_size"],
        freeze_layers=model_cfg["encoder"]["freeze_layers"],
        pooling=model_cfg["pooling"],
        classifier_hidden_dims=model_cfg["classifier"]["hidden_dims"],
        dropout=model_cfg["classifier"]["dropout"],
        n_classes=model_cfg["classifier"]["n_classes"],
    )

    if model_cfg["cache_embeddings"]:
        # ----- Cached-embedding mode -----
        print("\n[3/5] Pre-computing CodeBERT embeddings (CPU-friendly) ...")
        full_model = CodeBERTClassifier(codebert_cfg)
        full_model.to(device)

        if os.path.exists(cache_path):
            print(f"  cache found, loading ...")
            emb_dict = load_cached_embeddings(cache_path)
            # Filter to match sample_size if requested
            for k in emb_dict:
                n = len(splits[k])
                if len(emb_dict[k]["labels"]) > n:
                    emb_dict[k] = {
                        "embeddings": emb_dict[k]["embeddings"][:n],
                        "sample_ids": emb_dict[k]["sample_ids"][:n],
                        "projects": emb_dict[k]["projects"][:n],
                        "labels": emb_dict[k]["labels"][:n],
                    }
        else:
            loaders = get_dataloaders(splits, tokenizer, tok_cfg, dl_cfg, sample_size)
            emb_dict = {}
            for name, loader in loaders.items():
                print(f"  encoding {name} ({len(loader.dataset):,} rows) ...")
                t0 = time.time()
                e, sids, projs = compute_embeddings(full_model.encoder, loader, device)
                emb_dict[name] = {
                    "embeddings": e,
                    "sample_ids": sids,
                    "projects": projs,
                    "labels": np.array(loader.dataset.labels, dtype=np.int64),
                }
                print(f"    done in {time.time() - t0:.1f}s  shape={e.shape}")
            save_obj = {}
            for split_name, d in emb_dict.items():
                for k, v in d.items():
                    if isinstance(v, list):
                        save_obj[f"{split_name}__{k}"] = np.array(v, dtype=object)
                    else:
                        save_obj[f"{split_name}__{k}"] = v
            np.savez_compressed(cache_path, **save_obj)
            print(f"  cache saved -> {cache_path}")

        # Train MLP head on cached embeddings
        print("\n[4/5] Training MLP head on cached embeddings ...")
        mlp = CachedEmbeddingMLP(
            hidden_size=codebert_cfg.hidden_size,
            classifier_hidden_dims=codebert_cfg.classifier_hidden_dims,
            dropout=codebert_cfg.dropout,
            n_classes=codebert_cfg.n_classes,
        )
        mlp.to(device)

        train_ds = CachedEmbeddingDataset(
            emb_dict["train"]["embeddings"],
            emb_dict["train"]["labels"],
            emb_dict["train"]["sample_ids"],
            emb_dict["train"]["projects"],
        )
        val_ds = CachedEmbeddingDataset(
            emb_dict["validation"]["embeddings"],
            emb_dict["validation"]["labels"],
            emb_dict["validation"]["sample_ids"],
            emb_dict["validation"]["projects"],
        )
        test_ds = CachedEmbeddingDataset(
            emb_dict["test"]["embeddings"],
            emb_dict["test"]["labels"],
            emb_dict["test"]["sample_ids"],
            emb_dict["test"]["projects"],
        )
        train_loader = DataLoader(
            train_ds, batch_size=train_cfg["batch_size"], shuffle=True,
            num_workers=0, collate_fn=collate_cached,
        )
        val_loader = DataLoader(
            val_ds, batch_size=train_cfg["eval_batch_size"], shuffle=False,
            num_workers=0, collate_fn=collate_cached,
        )
        test_loader = DataLoader(
            test_ds, batch_size=train_cfg["eval_batch_size"], shuffle=False,
            num_workers=0, collate_fn=collate_cached,
        )

        # Trainer — but we need to adapt because input is embeddings, not token IDs.
        # Use a simplified trainer inline.
        trainer_cfg = TrainerConfig(
            epochs=train_cfg["epochs"],
            learning_rate=train_cfg["learning_rate"],
            weight_decay=train_cfg["weight_decay"],
            warmup_ratio=train_cfg["warmup_ratio"],
            max_grad_norm=train_cfg["max_grad_norm"],
            fp16=False,
            scheduler=train_cfg["scheduler"],
            class_weighted_loss=train_cfg["class_weighted_loss"],
            early_stopping_patience=train_cfg["early_stopping"]["patience"],
            early_stopping_metric=train_cfg["early_stopping"]["metric"],
            early_stopping_mode=train_cfg["early_stopping"]["mode"],
            log_interval=train_cfg["log_interval"],
            eval_interval=train_cfg["eval_interval"],
            save_dir=ckpt_dir,
            save_best=train_cfg["checkpoint"]["save_best"],
            save_last=train_cfg["checkpoint"]["save_last"],
            seed=exp_cfg["seed"],
            threshold=eval_cfg["threshold"],
        )
        trainer = CodeBERTTrainer(mlp, train_loader, val_loader, trainer_cfg, device=device)
        # Monkey-patch _forward_step to use embeddings as input directly
        def _forward_step_embed(self, batch):
            emb = batch["input_ids"].to(self.device)
            labels = batch["labels"].to(self.device).float()
            out = self.model(emb)
            logits = out["logits"]
            if logits.dim() == 2 and logits.size(1) == 1:
                logits = logits.squeeze(-1)
            loss = self.loss_fn(logits, labels)
            return {"loss": loss, "logits": logits, "labels": labels}
        import types
        trainer._forward_step = types.MethodType(_forward_step_embed, trainer)
        train_result = trainer.train(config_for_log=cfg)
        history = train_result["history"]

        # Save training curves
        plot_training_curves(history,
                             os.path.join("reports", "training_curves", "codebert_baseline.png"),
                             title="CodeBERT Baseline (cached embeddings)")

        # Evaluate on test
        print("\n[5/5] Evaluating on TEST set ...")
        test_metrics = trainer.evaluate(test_loader)

        # Tune threshold on validation
        val_metrics_for_threshold = trainer.evaluate(val_loader)
        # Re-extract probabilities
        val_logits = []
        val_labels = []
        with torch.no_grad():
            for batch in val_loader:
                emb = batch["input_ids"].to(device)
                out = mlp(emb)
                val_logits.append(out["logits"].cpu().numpy())
                val_labels.append(batch["labels"].numpy())
        val_logits = np.concatenate(val_logits)
        val_labels = np.concatenate(val_labels)
        val_proba = 1.0 / (1.0 + np.exp(-val_logits))
        best_t, best_f1 = find_best_threshold_by_f1(val_labels, val_proba)
        print(f"  best threshold tuned on validation: {best_t:.3f}  (val F1={best_f1:.4f})")

        # Re-evaluate test at best threshold
        with torch.no_grad():
            test_logits = []
            test_labels = []
            for batch in test_loader:
                emb = batch["input_ids"].to(device)
                out = mlp(emb)
                test_logits.append(out["logits"].cpu().numpy())
                test_labels.append(batch["labels"].numpy())
        test_logits = np.concatenate(test_logits)
        test_labels = np.concatenate(test_labels)
        test_proba = 1.0 / (1.0 + np.exp(-test_logits))
        test_preds = (test_proba >= best_t).astype(int)
        test_metrics_best = compute_all_metrics(test_labels, test_preds, test_proba, threshold=best_t)

        print("\nTEST METRICS (threshold tuned on validation):")
        print(json.dumps({k: v for k, v in test_metrics_best.items() if k not in ("roc_curve", "pr_curve", "sample_ids", "projects")}, indent=2, default=str))

        save_metrics_report(test_metrics_best, os.path.join(out_dir, "test_metrics.json"))
        save_metrics_report({k: v for k, v in val_metrics_for_threshold.items() if k not in ("sample_ids", "projects")},
                            os.path.join(out_dir, "validation_metrics.json"))

        plot_confusion_matrix(test_metrics_best["confusion_matrix"],
                              "CodeBERT — Test Confusion Matrix",
                              "reports/confusion_matrices/codebert_test.png")
        if test_metrics_best.get("roc_curve"):
            plot_roc_curve(test_metrics_best["roc_curve"],
                           "CodeBERT — Test ROC Curve",
                           "reports/roc_curves/codebert_test.png",
                           auc=test_metrics_best.get("roc_auc"))
        if test_metrics_best.get("pr_curve"):
            plot_pr_curve(test_metrics_best["pr_curve"],
                          "CodeBERT — Test PR Curve",
                          "reports/pr_curves/codebert_test.png",
                          ap=test_metrics_best.get("pr_auc"))

        # Experiment metadata
        experiment_metadata = {
            "experiment_name": exp_cfg["name"],
            "model": {
                "type": "CodeBERTClassifier",
                "encoder": model_cfg["encoder"]["name"],
                "pooling": model_cfg["pooling"],
                "classifier_hidden_dims": model_cfg["classifier"]["hidden_dims"],
                "dropout": model_cfg["classifier"]["dropout"],
                "cache_embeddings": True,
            },
            "dataset_version": dataset_cfg["version"],
            "sample_size": sample_size,
            "split_sizes": {k: len(v) for k, v in splits.items()},
            "class_distribution_train": class_distribution(splits["train"]),
            "class_distribution_val": class_distribution(splits["validation"]),
            "class_distribution_test": class_distribution(splits["test"]),
            "training_config": {
                "epochs_requested": train_cfg["epochs"],
                "batch_size": train_cfg["batch_size"],
                "learning_rate": train_cfg["learning_rate"],
                "weight_decay": train_cfg["weight_decay"],
                "warmup_ratio": train_cfg["warmup_ratio"],
                "class_weighted_loss": train_cfg["class_weighted_loss"],
                "fp16": train_cfg["fp16"],
            },
            "epochs_actually_trained": len(history),
            "best_threshold_tuned_on_validation": best_t,
            "validation_f1_at_best_threshold": best_f1,
            "test_metrics_at_best_threshold": {k: v for k, v in test_metrics_best.items() if k not in ("roc_curve", "pr_curve", "sample_ids", "projects")},
            "validation_metrics": {k: v for k, v in val_metrics_for_threshold.items() if k not in ("roc_curve", "pr_curve", "sample_ids", "projects")},
            "history": history,
            "seed": exp_cfg["seed"],
            "device": str(device),
            "embeddings_cache_path": cache_path,
        }
        with open(os.path.join(out_dir, "experiment.json"), "w", encoding="utf-8") as f:
            json.dump(experiment_metadata, f, indent=2, default=str)
        print(f"\n[experiment] saved -> {os.path.join(out_dir, 'experiment.json')}")

    else:
        # ----- Full fine-tune mode (encoder + head end-to-end) -----
        print("\n[3/5] Building full CodeBERTClassifier for end-to-end training ...")
        model = CodeBERTClassifier(codebert_cfg)
        model.to(device)
        loaders = get_dataloaders(splits, tokenizer, tok_cfg, dl_cfg, sample_size)

        trainer_cfg = TrainerConfig(
            epochs=train_cfg["epochs"],
            learning_rate=train_cfg["learning_rate"],
            weight_decay=train_cfg["weight_decay"],
            warmup_ratio=train_cfg["warmup_ratio"],
            max_grad_norm=train_cfg["max_grad_norm"],
            fp16=train_cfg["fp16"] and device.type == "cuda",
            scheduler=train_cfg["scheduler"],
            class_weighted_loss=train_cfg["class_weighted_loss"],
            early_stopping_patience=train_cfg["early_stopping"]["patience"],
            early_stopping_metric=train_cfg["early_stopping"]["metric"],
            early_stopping_mode=train_cfg["early_stopping"]["mode"],
            log_interval=train_cfg["log_interval"],
            eval_interval=train_cfg["eval_interval"],
            save_dir=ckpt_dir,
            save_best=train_cfg["checkpoint"]["save_best"],
            save_last=train_cfg["checkpoint"]["save_last"],
            seed=exp_cfg["seed"],
            threshold=eval_cfg["threshold"],
        )
        trainer = CodeBERTTrainer(model, loaders["train"], loaders["validation"], trainer_cfg, device=device)
        train_result = trainer.train(config_for_log=cfg, resume_path=args.resume)
        history = train_result["history"]

        plot_training_curves(history,
                             os.path.join("reports", "training_curves", "codebert_full.png"),
                             title="CodeBERT Full Fine-tune")

        print("\n[5/5] Evaluating on TEST set ...")
        test_metrics = trainer.evaluate(loaders["test"])
        save_metrics_report(test_metrics, os.path.join(out_dir, "test_metrics.json"))
        plot_confusion_matrix(test_metrics["confusion_matrix"],
                              "CodeBERT (full) — Test Confusion Matrix",
                              "reports/confusion_matrices/codebert_full_test.png")
        if test_metrics.get("roc_curve"):
            plot_roc_curve(test_metrics["roc_curve"],
                           "CodeBERT (full) — Test ROC Curve",
                           "reports/roc_curves/codebert_full_test.png",
                           auc=test_metrics.get("roc_auc"))
        if test_metrics.get("pr_curve"):
            plot_pr_curve(test_metrics["pr_curve"],
                          "CodeBERT (full) — Test PR Curve",
                          "reports/pr_curves/codebert_full_test.png",
                          ap=test_metrics.get("pr_auc"))

    print("\n" + "=" * 70)
    print("CodeBERT baseline COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
