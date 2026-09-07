"""SkyTrace reusable training engine.

Phase-1 supports:
    - CodeBERT baseline training (encoder + classifier head)
    - Training / validation loops
    - AdamW + linear-warmup scheduler
    - Gradient clipping
    - Mixed precision (disabled on CPU)
    - Early stopping
    - ModelCheckpoint (best + last)
    - Reproducible seeding
    - Per-epoch metric logging

Future phases will extend this to multi-task learning.
"""

from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from ..evaluation.metrics import compute_all_metrics
from .callbacks import EarlyStopping, ModelCheckpoint
from .losses import WeightedBCEWithLogitsLoss, compute_class_weights


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


@dataclass
class TrainerConfig:
    epochs: int = 3
    learning_rate: float = 2e-5
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    max_grad_norm: float = 1.0
    fp16: bool = False
    scheduler: str = "linear_with_warmup"
    class_weighted_loss: bool = True
    early_stopping_patience: int = 2
    early_stopping_metric: str = "pr_auc"
    early_stopping_mode: str = "max"
    log_interval: int = 50
    eval_interval: int = 1
    save_dir: str = "models/checkpoints/codebert_baseline"
    save_best: bool = True
    save_last: bool = True
    seed: int = 42
    threshold: float = 0.5


class CodeBERTTrainer:
    """Trainer for CodeBERTClassifier. Logs JSON metrics per epoch."""

    def __init__(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        cfg: TrainerConfig,
        device: Optional[torch.device] = None,
    ):
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.cfg = cfg
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Optimizer
        self.optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=cfg.learning_rate,
            weight_decay=cfg.weight_decay,
        )

        # Scheduler
        total_steps = max(1, len(train_loader) * cfg.epochs)
        warmup_steps = int(total_steps * cfg.warmup_ratio)
        if cfg.scheduler == "linear_with_warmup":
            def lr_lambda(step):
                if step < warmup_steps:
                    return float(step) / float(max(1, warmup_steps))
                return max(0.0, float(total_steps - step) / float(max(1, total_steps - warmup_steps)))
            self.scheduler = torch.optim.lr_scheduler.LambdaLR(self.optimizer, lr_lambda)
        else:
            self.scheduler = None

        # Loss — compute pos_weight from training labels
        train_labels = []
        try:
            for batch in train_loader:
                train_labels.extend(batch["labels"].tolist())
                if len(train_labels) >= 50000:  # sample enough to estimate
                    break
        except Exception:
            pass
        if cfg.class_weighted_loss and train_labels:
            cw = compute_class_weights(torch.tensor(train_labels))
            self.loss_fn = WeightedBCEWithLogitsLoss(pos_weight=cw["pos_weight"].to(self.device))
            print(f"[trainer] class-weighted loss enabled. pos_weight={cw['pos_weight'].item():.3f}  "
                  f"(n_pos={cw['n_pos']:,}, n_neg={cw['n_neg']:,})")
        else:
            self.loss_fn = WeightedBCEWithLogitsLoss()
            print("[trainer] class-weighted loss disabled")

        # Callbacks
        self.early_stopping = EarlyStopping(
            patience=cfg.early_stopping_patience,
            metric=cfg.early_stopping_metric,
            mode=cfg.early_stopping_mode,
        )
        self.checkpoint = ModelCheckpoint(
            save_dir=cfg.save_dir,
            save_best=cfg.save_best,
            save_last=cfg.save_last,
            metric=cfg.early_stopping_metric,
            mode=cfg.early_stopping_mode,
        )

        self.history: list = []

    def _forward_step(self, batch) -> Dict[str, torch.Tensor]:
        input_ids = batch["input_ids"].to(self.device)
        attention_mask = batch["attention_mask"].to(self.device)
        labels = batch["labels"].to(self.device).float()
        out = self.model(input_ids=input_ids, attention_mask=attention_mask)
        logits = out["logits"]
        if logits.dim() == 2 and logits.size(1) == 1:
            logits = logits.squeeze(-1)
        loss = self.loss_fn(logits, labels)
        return {"loss": loss, "logits": logits, "labels": labels}

    def train_one_epoch(self, epoch: int) -> Dict[str, float]:
        self.model.train()
        total_loss = 0.0
        n_batches = 0
        t0 = time.time()
        for step, batch in enumerate(self.train_loader):
            self.optimizer.zero_grad()
            out = self._forward_step(batch)
            out["loss"].backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.cfg.max_grad_norm)
            self.optimizer.step()
            if self.scheduler is not None:
                self.scheduler.step()
            total_loss += out["loss"].item()
            n_batches += 1
            if (step + 1) % self.cfg.log_interval == 0:
                elapsed = time.time() - t0
                print(f"  [epoch {epoch}] step {step+1}/{len(self.train_loader)}  "
                      f"loss={out['loss'].item():.4f}  lr={self.optimizer.param_groups[0]['lr']:.2e}  "
                      f"elapsed={elapsed:.1f}s")
        avg_loss = total_loss / max(1, n_batches)
        return {"train_loss": avg_loss, "train_time_sec": time.time() - t0}

    @torch.no_grad()
    def evaluate(self, loader: Optional[DataLoader] = None) -> Dict[str, Any]:
        self.model.eval()
        loader = loader or self.val_loader
        all_logits = []
        all_labels = []
        all_sids = []
        all_projs = []
        for i, batch in enumerate(loader, 1):
            if i == 1 or i % 100 == 0 or i == len(loader):
                print(f"  [eval] batch {i}/{len(loader)}")
            out = self._forward_step(batch)
            all_logits.append(out["logits"].cpu().numpy())
            all_labels.append(out["labels"].cpu().numpy())
            all_sids.extend(batch.get("sample_ids", []))
            all_projs.extend(batch.get("projects", []))
        logits = np.concatenate(all_logits)
        labels = np.concatenate(all_labels)
        proba = 1.0 / (1.0 + np.exp(-logits))
        preds = (proba >= self.cfg.threshold).astype(int)
        metrics = compute_all_metrics(labels, preds, proba, threshold=self.cfg.threshold)
        metrics["sample_ids"] = all_sids
        metrics["projects"] = all_projs
        return metrics


    def train(self, config_for_log: Optional[Dict[str, Any]] = None, resume_path: Optional[str] = None) -> Dict[str, Any]:
        set_seed(self.cfg.seed)
        start_epoch = 1
        if resume_path:
            print(f"[trainer] loading checkpoint: {resume_path}")
            checkpoint = torch.load(resume_path, map_location=self.device, weights_only=False)
            self.model.load_state_dict(checkpoint["model_state_dict"])
            if checkpoint.get("optimizer_state_dict"):
                self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
            if self.scheduler is not None and checkpoint.get("scheduler_state_dict"):
                self.scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
            saved_epoch = int(checkpoint.get("epoch", 0))
            start_epoch = saved_epoch + 1
            if start_epoch > self.cfg.epochs:
                print(f"[trainer] checkpoint is already at epoch {saved_epoch}; nothing to resume.")
                return {"history": self.history, "best_metric_value": self.early_stopping.best}
            saved_metrics = checkpoint.get("metrics", {})
            if saved_metrics.get(self.cfg.early_stopping_metric) is not None:
                self.early_stopping.best = saved_metrics[self.cfg.early_stopping_metric]
            self.history = checkpoint.get("history", []) or []
            print(f"[trainer] resumed from epoch {saved_epoch}; continuing at epoch {start_epoch}")
        print(f"[trainer] device={self.device}  epochs={self.cfg.epochs}  "
              f"train_batches={len(self.train_loader)}  val_batches={len(self.val_loader)}")
        for epoch in range(start_epoch, self.cfg.epochs + 1):
            print(f"\n===== Epoch {epoch}/{self.cfg.epochs} =====")
            train_stats = self.train_one_epoch(epoch)
            val_metrics = self.evaluate()
            epoch_log = {
                "epoch": epoch,
                "train_loss": train_stats["train_loss"],
                "train_time_sec": train_stats["train_time_sec"],
                "val_accuracy": val_metrics.get("accuracy"),
                "val_precision": val_metrics.get("precision"),
                "val_recall": val_metrics.get("recall"),
                "val_f1": val_metrics.get("f1"),
                "val_macro_f1": val_metrics.get("macro_f1"),
                "val_weighted_f1": val_metrics.get("weighted_f1"),
                "val_roc_auc": val_metrics.get("roc_auc"),
                "val_pr_auc": val_metrics.get("pr_auc"),
                "val_confusion_matrix": val_metrics.get("confusion_matrix"),
            }
            self.history.append(epoch_log)
            print(json.dumps(epoch_log, indent=2, default=str))

            best_path = self.checkpoint.maybe_save(
                self.model, self.optimizer, self.scheduler,
                val_metrics, epoch, config_for_log or {},
            )
            if best_path:
                print(f"[trainer] new best model saved -> {best_path}")

            is_best = self.early_stopping.step(val_metrics)
            if self.early_stopping.should_stop:
                print(f"[trainer] early stopping triggered at epoch {epoch} "
                      f"(no improvement in {self.cfg.early_stopping_metric} for "
                      f"{self.cfg.early_stopping_patience} epochs)")
                break

        return {"history": self.history, "best_metric_value": self.early_stopping.best}

