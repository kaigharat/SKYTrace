"""SkyTrace — Code + History fusion model (Experiment C).

Architecture:
    Function code                History features (6-d)
        ↓                              ↓
    CodeBERT (frozen)           BatchNorm → MLP
        ↓                              ↓
    Code embedding [768]    History embedding [64]
        │                              │
        └──────────┬───────────────────┘
                   ↓
            Concat [768 + 64 = 832]
                   ↓
               Fusion MLP
            (832 → 256 → 128 → 1)
                   ↓
            Vulnerability logit
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import torch
import torch.nn as nn

from .code_encoder import CodeBERTConfig, CodeBERTEncoder
from .history_encoder import HistoryEncoder, HistoryEncoderConfig
from ..features.history_features import N_HISTORY_FEATURES


@dataclass
class CodeHistoryConfig:
    # CodeBERT (same frozen encoder as Exp A)
    codebert_model_name: str = "microsoft/codebert-base"
    codebert_hidden_size: int = 768
    codebert_freeze_layers: int = 12
    codebert_pooling: str = "mean"

    # History encoder
    history_in_features: int = N_HISTORY_FEATURES  # 6
    history_hidden_dims: List[int] = field(default_factory=lambda: [64, 64])
    history_out_dim: int = 64
    history_dropout: float = 0.1

    # Fusion head
    fusion_hidden_dims: List[int] = field(default_factory=lambda: [256, 128])
    fusion_dropout: float = 0.1

    # Output
    n_classes: int = 1


class CodeHistoryModel(nn.Module):
    """Experiment C: Code + History vulnerability classifier.

    The CodeBERT encoder is FROZEN (same weights as Experiment A).
    Only the history encoder and fusion head are trained.
    """

    def __init__(self, cfg: CodeHistoryConfig):
        super().__init__()
        self.cfg = cfg

        # CodeBERT encoder (frozen)
        codebert_cfg = CodeBERTConfig(
            model_name=cfg.codebert_model_name,
            hidden_size=cfg.codebert_hidden_size,
            freeze_layers=cfg.codebert_freeze_layers,
            pooling=cfg.codebert_pooling,
        )
        self.code_encoder = CodeBERTEncoder(codebert_cfg)

        # History encoder
        hist_cfg = HistoryEncoderConfig(
            in_features=cfg.history_in_features,
            hidden_dims=cfg.history_hidden_dims,
            out_dim=cfg.history_out_dim,
            dropout=cfg.history_dropout,
        )
        self.history_encoder = HistoryEncoder(hist_cfg)

        # Fusion MLP
        in_dim = cfg.codebert_hidden_size + cfg.history_out_dim  # 768 + 64 = 832
        layers = []
        for h in cfg.fusion_hidden_dims:
            layers.append(nn.Linear(in_dim, h))
            layers.append(nn.GELU())
            layers.append(nn.Dropout(cfg.fusion_dropout))
            in_dim = h
        layers.append(nn.Linear(in_dim, cfg.n_classes))
        self.head = nn.Sequential(*layers)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        history_features: torch.Tensor,
    ) -> Dict[str, torch.Tensor]:
        """
        Args:
            input_ids:        (B, L) tokenised code
            attention_mask:   (B, L) attention mask
            history_features: (B, N_HISTORY_FEATURES) float32 proxy history features
        Returns:
            dict: logits (B, 1), code_emb (B, 768), hist_emb (B, 64)
        """
        with torch.no_grad():
            code_emb = self.code_encoder(input_ids, attention_mask)   # (B, 768)
        hist_emb = self.history_encoder(history_features)             # (B, 64)

        fused = torch.cat([code_emb, hist_emb], dim=-1)               # (B, 832)
        logits = self.head(fused)                                      # (B, 1)

        return {"logits": logits, "code_emb": code_emb, "hist_emb": hist_emb}

    def load_codebert_weights(self, checkpoint_path: str, device: torch.device) -> None:
        """Load CodeBERT encoder weights from the Experiment A checkpoint."""
        state = torch.load(checkpoint_path, map_location=device, weights_only=False)
        full_state = state["model_state_dict"]
        encoder_state = {
            k[len("encoder."):]: v
            for k, v in full_state.items()
            if k.startswith("encoder.")
        }
        missing, unexpected = self.code_encoder.load_state_dict(encoder_state, strict=False)
        print(f"[CodeHistoryModel] Loaded CodeBERT weights from {checkpoint_path}")
        if missing:
            print(f"  missing keys: {missing[:5]}")
        if unexpected:
            print(f"  unexpected keys: {unexpected[:5]}")
