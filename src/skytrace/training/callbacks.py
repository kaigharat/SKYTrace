"""SkyTrace training callbacks.

Phase-1:
    - EarlyStopping (patience-based, mode='max' or 'min')
    - ModelCheckpoint (save best + last)

Future phases will add:
    - TensorBoard / W&B logging
    - LR scheduler callbacks
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import torch


class EarlyStopping:
    """Stop training when a monitored metric stops improving."""

    def __init__(self, patience: int = 2, metric: str = "pr_auc", mode: str = "max"):
        assert mode in ("max", "min")
        self.patience = patience
        self.metric = metric
        self.mode = mode
        self.best: Optional[float] = None
        self.counter = 0
        self.should_stop = False

    def step(self, metrics: Dict[str, Any]) -> bool:
        """Returns True if this is a new best."""
        val = metrics.get(self.metric)
        if val is None:
            return False
        if self.best is None:
            self.best = val
            return True
        improved = (val > self.best) if self.mode == "max" else (val < self.best)
        if improved:
            self.best = val
            self.counter = 0
            return True
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True
            return False


class ModelCheckpoint:
    """Save best + last model checkpoints with metadata."""

    def __init__(
        self,
        save_dir: str,
        save_best: bool = True,
        save_last: bool = True,
        metric: str = "pr_auc",
        mode: str = "max",
    ):
        self.save_dir = save_dir
        self.save_best = save_best
        self.save_last = save_last
        self.metric = metric
        self.mode = mode
        self.best: Optional[float] = None
        os.makedirs(save_dir, exist_ok=True)

    def maybe_save(
        self,
        model: torch.nn.Module,
        optimizer,
        scheduler,
        metrics: Dict[str, Any],
        epoch: int,
        config: Dict[str, Any],
    ) -> Optional[str]:
        """Save best model if improved; always save last. Returns best path if updated."""
        val = metrics.get(self.metric)
        if val is None:
            return None

        is_best = False
        if self.best is None:
            self.best = val
            is_best = True
        else:
            is_best = (val > self.best) if self.mode == "max" else (val < self.best)
            if is_best:
                self.best = val

        last_path = None
        if self.save_last:
            last_path = os.path.join(self.save_dir, "last.pt")
            self._save(model, optimizer, scheduler, metrics, epoch, config, last_path, is_best=False)

        best_path = None
        if is_best and self.save_best:
            best_path = os.path.join(self.save_dir, "best.pt")
            self._save(model, optimizer, scheduler, metrics, epoch, config, best_path, is_best=True)

        return best_path

    def _save(self, model, optimizer, scheduler, metrics, epoch, config, path, is_best):
        state = {
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict() if optimizer else None,
            "scheduler_state_dict": scheduler.state_dict() if scheduler else None,
            "metrics": metrics,
            "epoch": epoch,
            "config": config,
            "is_best": is_best,
        }
        torch.save(state, path)
