"""SkyTrace — History encoder MLP.

Encodes 6 proxy history features into a dense embedding vector.

Architecture:
    History features (6-d float32)
        ↓
    BatchNorm1d (normalise inputs — features have very different scales)
        ↓
    Linear(6 → 64) → GELU → Dropout
        ↓
    Linear(64 → 64) → GELU → Dropout
        ↓
    History embedding (64-d)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import torch
import torch.nn as nn

from ..features.history_features import N_HISTORY_FEATURES


@dataclass
class HistoryEncoderConfig:
    in_features: int = N_HISTORY_FEATURES   # 6
    hidden_dims: List[int] = field(default_factory=lambda: [64, 64])
    out_dim: int = 64
    dropout: float = 0.1
    use_batchnorm: bool = True


class HistoryEncoder(nn.Module):
    """MLP that maps history features → dense history embedding.

    The BatchNorm at the input handles the scale mismatch between features
    (e.g., commit_size can be 1..50, project_vuln_density is 0..1).
    """

    def __init__(self, cfg: HistoryEncoderConfig):
        super().__init__()
        self.cfg = cfg

        layers = []
        if cfg.use_batchnorm:
            layers.append(nn.BatchNorm1d(cfg.in_features))

        in_dim = cfg.in_features
        for h in cfg.hidden_dims:
            layers.append(nn.Linear(in_dim, h))
            layers.append(nn.GELU())
            layers.append(nn.Dropout(cfg.dropout))
            in_dim = h

        layers.append(nn.Linear(in_dim, cfg.out_dim))
        self.net = nn.Sequential(*layers)

    def forward(self, history_features: torch.Tensor) -> torch.Tensor:
        """
        Args:
            history_features: (B, in_features) float32
        Returns:
            (B, out_dim) history embedding
        """
        return self.net(history_features)
