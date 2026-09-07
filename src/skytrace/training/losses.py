"""SkyTrace loss functions.

Phase-1:
    - BinaryCrossEntropyWithLogitsLoss with optional positive class weight
      (for imbalanced vulnerability detection — vulnerable class is ~5.7%).

Future phases will add:
    - Multi-task loss (defect + vulnerability + regression)
    - Focal loss
"""

from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn


def compute_class_weights(labels: torch.Tensor) -> dict:
    """Return pos_weight for BCEWithLogitsLoss given imbalanced binary labels.

    pos_weight = n_negative / n_positive
    """
    labels = labels.float()
    n_pos = float(labels.sum().item())
    n_neg = float(len(labels) - n_pos)
    if n_pos == 0:
        return {"pos_weight": torch.tensor(1.0), "n_pos": 0, "n_neg": int(n_neg)}
    pos_weight = torch.tensor(n_neg / n_pos)
    return {"pos_weight": pos_weight, "n_pos": int(n_pos), "n_neg": int(n_neg)}


class WeightedBCEWithLogitsLoss(nn.Module):
    """BCEWithLogitsLoss with positive-class weighting for imbalanced data."""

    def __init__(self, pos_weight: Optional[torch.Tensor] = None):
        super().__init__()
        self.loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    def forward(self, logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        # logits: (B, 1) | labels: (B,)
        if logits.dim() == 2 and logits.size(1) == 1:
            logits = logits.squeeze(-1)
        return self.loss_fn(logits, labels.float())
