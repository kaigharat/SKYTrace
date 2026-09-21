"""SkyTrace — GNN encoder for the Code + Graph experiment.

Architecture:
    Node features (768-d CodeBERT embeddings)
        ↓
    Linear projection (768 → gnn_hidden)
        ↓
    GraphSAGE layers (mean aggregation, 2 layers)
        ↓
    Global mean pooling per function (identity — node-level task)
        ↓
    Graph embedding (gnn_out_dim)

We use GraphSAGE because:
    1. It naturally handles isolated nodes (no neighbours)
    2. It does not require symmetric normalisation (unlike GCN)
    3. It generalises to inductive settings (new nodes at inference)

The GNN operates on BATCHED mini-graphs constructed per training batch
(each batch contains functions from multiple commits, connected by
co-change edges within the batch). This is memory-efficient and avoids
loading the entire 259K-node graph into GPU memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class GNNConfig:
    in_channels: int = 768          # CodeBERT embedding dim
    hidden_channels: int = 256      # GNN hidden dim
    out_channels: int = 256         # Final graph embedding dim
    num_layers: int = 2             # Number of GraphSAGE layers
    dropout: float = 0.1
    activation: str = "relu"        # "relu" | "gelu"
    normalize: bool = True          # L2-normalize node embeddings


class SAGEConvManual(nn.Module):
    """Single GraphSAGE convolution layer, implemented in pure PyTorch.

    Does NOT depend on torch_geometric's C extensions (torch_scatter, etc.)
    which may not be available for all CUDA versions. Falls back to PyG's
    SAGEConv if available.

    Mean aggregation:
        h_v' = W_self * h_v + W_neigh * mean({h_u | u ∈ N(v)})
    """

    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.lin_self = nn.Linear(in_channels, out_channels, bias=False)
        self.lin_neigh = nn.Linear(in_channels, out_channels, bias=False)
        self.bias = nn.Parameter(torch.zeros(out_channels))

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
    ) -> torch.Tensor:
        """
        Args:
            x:          (N, in_channels) node features
            edge_index: (2, E) edge indices [src, dst]
        Returns:
            (N, out_channels)
        """
        N = x.size(0)
        self_out = self.lin_self(x)

        if edge_index.numel() == 0:
            # No edges — return self-transform only
            return self_out + self.bias

        src, dst = edge_index[0], edge_index[1]

        # Aggregate: mean of source node features for each destination
        neigh_feat = x[src]  # (E, in_channels)
        # Scatter mean into dst nodes
        agg = torch.zeros(N, x.size(1), device=x.device, dtype=x.dtype)
        count = torch.zeros(N, 1, device=x.device, dtype=x.dtype)
        agg.scatter_add_(0, dst.unsqueeze(1).expand_as(neigh_feat), neigh_feat)
        count.scatter_add_(0, dst.unsqueeze(1), torch.ones(len(dst), 1, device=x.device))
        count = count.clamp(min=1.0)
        agg = agg / count

        neigh_out = self.lin_neigh(agg)
        return self_out + neigh_out + self.bias


class GraphEncoder(nn.Module):
    """GraphSAGE encoder producing per-node embeddings.

    Input:  node feature matrix x (N, in_channels) + edge_index (2, E)
    Output: updated node embeddings (N, out_channels)

    For the vulnerability detection task, the "graph embedding" of a
    function is its updated node representation after message passing.
    This captures information from co-changed neighbours.
    """

    def __init__(self, cfg: GNNConfig):
        super().__init__()
        self.cfg = cfg

        # Try to use PyG's SAGEConv; fall back to manual implementation
        self._use_pyg = False
        try:
            from torch_geometric.nn import SAGEConv
            self._use_pyg = True
        except ImportError:
            pass

        # Input projection
        self.input_proj = nn.Linear(cfg.in_channels, cfg.hidden_channels)

        # GNN layers
        layers = []
        for i in range(cfg.num_layers):
            in_dim = cfg.hidden_channels
            out_dim = cfg.out_channels if i == cfg.num_layers - 1 else cfg.hidden_channels
            if self._use_pyg:
                from torch_geometric.nn import SAGEConv
                layers.append(SAGEConv(in_dim, out_dim, aggr="mean"))
            else:
                layers.append(SAGEConvManual(in_dim, out_dim))
        self.convs = nn.ModuleList(layers)

        self.dropout = nn.Dropout(cfg.dropout)
        self.act = nn.GELU() if cfg.activation == "gelu" else nn.ReLU()

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
    ) -> torch.Tensor:
        """
        Args:
            x:          (N, in_channels) node features (CodeBERT embeddings)
            edge_index: (2, E) co-change edges within the batch
        Returns:
            (N, out_channels) updated node embeddings
        """
        h = self.input_proj(x)
        h = self.act(h)

        for i, conv in enumerate(self.convs):
            if self._use_pyg:
                h = conv(h, edge_index)
            else:
                h = conv(h, edge_index)
            if i < len(self.convs) - 1:
                h = self.act(h)
                h = self.dropout(h)

        if self.cfg.normalize:
            h = F.normalize(h, p=2, dim=-1)

        return h
