"""SkyTrace — Code + Graph + History multimodal model (Experiment D).

Architecture:
    Code emb [768]  +  Graph emb [256]  +  History emb [64]
           │                  │                  │
           └──────────────────┼──────────────────┘
                              ↓
                     Concat [768+256+64 = 1088]
                              ↓
                        Fusion MLP
                    (1088 → 512 → 256 → 1)
                              ↓
                      Vulnerability logit

Multi-task extension (optional, enabled via cfg.multi_task):
    The 256-d unified representation before the final linear layer
    is split into:
        - Vulnerability/Security head (primary)
        - CWE presence head (secondary binary)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import torch
import torch.nn as nn

from .code_encoder import CodeBERTConfig, CodeBERTEncoder
from .graph_encoder import GraphEncoder, GNNConfig
from .history_encoder import HistoryEncoder, HistoryEncoderConfig
from ..features.history_features import N_HISTORY_FEATURES


@dataclass
class MultimodalConfig:
    # CodeBERT (frozen)
    codebert_model_name: str = "microsoft/codebert-base"
    codebert_hidden_size: int = 768
    codebert_freeze_layers: int = 12
    codebert_pooling: str = "mean"

    # GNN
    gnn_hidden_channels: int = 256
    gnn_out_channels: int = 256
    gnn_num_layers: int = 2
    gnn_dropout: float = 0.1

    # History encoder
    history_in_features: int = N_HISTORY_FEATURES   # 6
    history_hidden_dims: List[int] = field(default_factory=lambda: [64, 64])
    history_out_dim: int = 64
    history_dropout: float = 0.1

    # Fusion
    fusion_hidden_dims: List[int] = field(default_factory=lambda: [512, 256])
    fusion_dropout: float = 0.1

    # Multi-task
    multi_task: bool = False          # Enable secondary CWE-presence head
    n_classes: int = 1                # Primary output (vulnerability)


class MultimodalModel(nn.Module):
    """Experiment D: Code + Graph + History multimodal vulnerability classifier.

    CodeBERT encoder is FROZEN (loaded from Experiment A checkpoint).
    GNN, history encoder, and fusion head are trained.

    If cfg.multi_task=True, also predicts CWE presence as a secondary task.
    """

    def __init__(self, cfg: MultimodalConfig):
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

        # GNN encoder
        gnn_cfg = GNNConfig(
            in_channels=cfg.codebert_hidden_size,
            hidden_channels=cfg.gnn_hidden_channels,
            out_channels=cfg.gnn_out_channels,
            num_layers=cfg.gnn_num_layers,
            dropout=cfg.gnn_dropout,
        )
        self.gnn = GraphEncoder(gnn_cfg)

        # History encoder
        hist_cfg = HistoryEncoderConfig(
            in_features=cfg.history_in_features,
            hidden_dims=cfg.history_hidden_dims,
            out_dim=cfg.history_out_dim,
            dropout=cfg.history_dropout,
        )
        self.history_encoder = HistoryEncoder(hist_cfg)

        # Fusion MLP (shared trunk)
        concat_dim = (
            cfg.codebert_hidden_size    # 768
            + cfg.gnn_out_channels      # 256
            + cfg.history_out_dim       # 64
        )                               # = 1088
        self.fusion_in_dim = concat_dim

        trunk_layers = []
        in_dim = concat_dim
        for h in cfg.fusion_hidden_dims[:-1]:
            trunk_layers.append(nn.Linear(in_dim, h))
            trunk_layers.append(nn.GELU())
            trunk_layers.append(nn.Dropout(cfg.fusion_dropout))
            in_dim = h
        # Final trunk hidden layer
        if cfg.fusion_hidden_dims:
            last_h = cfg.fusion_hidden_dims[-1]
            trunk_layers.append(nn.Linear(in_dim, last_h))
            trunk_layers.append(nn.GELU())
            trunk_layers.append(nn.Dropout(cfg.fusion_dropout))
            self.trunk = nn.Sequential(*trunk_layers)
            trunk_out_dim = last_h
        else:
            self.trunk = nn.Identity()
            trunk_out_dim = concat_dim

        # Primary head: vulnerability
        self.vuln_head = nn.Linear(trunk_out_dim, cfg.n_classes)

        # Secondary head: CWE presence (multi-task)
        if cfg.multi_task:
            self.cwe_head = nn.Linear(trunk_out_dim, 1)
        else:
            self.cwe_head = None

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        edge_index: torch.Tensor,
        history_features: torch.Tensor,
    ) -> Dict[str, torch.Tensor]:
        """
        Args:
            input_ids:        (B, L) tokenised code
            attention_mask:   (B, L)
            edge_index:       (2, E) co-change edges (local to batch)
            history_features: (B, 6) proxy history features
        Returns:
            dict: logits (B, 1), cwe_logits (B, 1) if multi_task,
                  code_emb, graph_emb, hist_emb, fused_emb
        """
        with torch.no_grad():
            code_emb = self.code_encoder(input_ids, attention_mask)  # (B, 768)

        graph_emb = self.gnn(code_emb, edge_index)                  # (B, 256)
        hist_emb = self.history_encoder(history_features)            # (B, 64)

        fused = torch.cat([code_emb, graph_emb, hist_emb], dim=-1)  # (B, 1088)
        trunk_out = self.trunk(fused)                                 # (B, 256)
        logits = self.vuln_head(trunk_out)                           # (B, 1)

        out = {
            "logits": logits,
            "code_emb": code_emb,
            "graph_emb": graph_emb,
            "hist_emb": hist_emb,
            "fused_emb": trunk_out,
        }
        if self.cwe_head is not None:
            out["cwe_logits"] = self.cwe_head(trunk_out)

        return out

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
        print(f"[MultimodalModel] Loaded CodeBERT weights from {checkpoint_path}")
        if missing:
            print(f"  missing keys: {missing[:5]}")
        if unexpected:
            print(f"  unexpected keys: {unexpected[:5]}")
