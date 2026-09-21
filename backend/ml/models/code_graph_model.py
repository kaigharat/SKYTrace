"""SkyTrace — Code + Graph fusion model (Experiment B).

Architecture:
    Function code
        ↓
    CodeBERT (frozen, 12 layers)
        ↓
    Code embedding [768]   ← same as Experiment A
        │
        ├─────────────────────────────────────┐
        │                                     │
        │    Co-change graph edges            │
        │    (functions in same commit)       │
        │         ↓                           │
        │    GraphSAGE GNN                    │
        │    (node feat = code embedding)     │
        │         ↓                           │
        │    Graph embedding [256]            │
        │                                     │
        └────────────┬────────────────────────┘
                     ↓
             Concat [768 + 256 = 1024]
                     ↓
                 Fusion MLP
              (1024 → 512 → 256 → 1)
                     ↓
             Vulnerability logit
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import torch
import torch.nn as nn

from .code_encoder import CodeBERTClassifier, CodeBERTConfig
from .graph_encoder import GraphEncoder, GNNConfig


@dataclass
class CodeGraphConfig:
    # CodeBERT settings (same as Experiment A baseline)
    codebert_model_name: str = "microsoft/codebert-base"
    codebert_hidden_size: int = 768
    codebert_freeze_layers: int = 12
    codebert_pooling: str = "mean"

    # GNN settings
    gnn_hidden_channels: int = 256
    gnn_out_channels: int = 256
    gnn_num_layers: int = 2
    gnn_dropout: float = 0.1

    # Fusion head
    fusion_hidden_dims: List[int] = field(default_factory=lambda: [512, 256])
    fusion_dropout: float = 0.1

    # Output
    n_classes: int = 1


class CodeGraphModel(nn.Module):
    """Experiment B: Code + Graph vulnerability classifier.

    The CodeBERT encoder is FROZEN (same weights as Experiment A) so that
    Experiment A and B are directly comparable. Only the GNN and fusion
    head are trained.
    """

    def __init__(self, cfg: CodeGraphConfig):
        super().__init__()
        self.cfg = cfg

        # CodeBERT encoder (frozen)
        codebert_cfg = CodeBERTConfig(
            model_name=cfg.codebert_model_name,
            hidden_size=cfg.codebert_hidden_size,
            freeze_layers=cfg.codebert_freeze_layers,
            pooling=cfg.codebert_pooling,
        )
        # We only need the encoder, not the full classifier head
        from .code_encoder import CodeBERTEncoder
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

        # Fusion MLP
        in_dim = cfg.codebert_hidden_size + cfg.gnn_out_channels  # 768 + 256 = 1024
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
        edge_index: torch.Tensor,
        batch_node_indices: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        """
        Args:
            input_ids:         (B, L) tokenised input
            attention_mask:    (B, L) attention mask
            edge_index:        (2, E) co-change edges within the batch.
                               Node indices are LOCAL to the batch (0..B-1).
            batch_node_indices: unused placeholder for future use

        Returns:
            dict with keys: logits (B, 1), code_emb (B, 768), graph_emb (B, 256)
        """
        # 1. Code embeddings (frozen)
        with torch.no_grad():
            code_emb = self.code_encoder(input_ids, attention_mask)  # (B, 768)

        # 2. GNN over batch graph
        graph_emb = self.gnn(code_emb, edge_index)  # (B, 256)

        # 3. Fuse and classify
        fused = torch.cat([code_emb, graph_emb], dim=-1)  # (B, 1024)
        logits = self.head(fused)                          # (B, 1)

        return {"logits": logits, "code_emb": code_emb, "graph_emb": graph_emb}

    def load_codebert_weights(self, checkpoint_path: str, device: torch.device) -> None:
        """Load CodeBERT encoder weights from the Experiment A checkpoint.

        This ensures Experiments A and B start from the same representation.
        The checkpoint was saved with CodeBERTClassifier state_dict, so we
        extract only the encoder weights.
        """
        state = torch.load(checkpoint_path, map_location=device, weights_only=False)
        full_state = state["model_state_dict"]
        # Keys from CodeBERTClassifier: encoder.encoder.* → we want encoder.*
        encoder_state = {
            k[len("encoder."):]: v
            for k, v in full_state.items()
            if k.startswith("encoder.")
        }
        missing, unexpected = self.code_encoder.load_state_dict(encoder_state, strict=False)
        print(f"[CodeGraphModel] Loaded CodeBERT weights from {checkpoint_path}")
        if missing:
            print(f"  missing keys: {missing[:5]}")
        if unexpected:
            print(f"  unexpected keys: {unexpected[:5]}")
