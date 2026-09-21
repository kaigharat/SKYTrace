"""SkyTrace — Co-change graph builder.

Constructs a function-level co-change graph from DiverseVul parquet splits.
Two functions are connected if they appear in the same commit_id.

Design decisions:
    - Graph construction is entirely from existing data (commit_id, project).
      No AST parsing, no tree-sitter, no external backend required.
    - Nodes are functions (one per row); node features are pre-computed
      CodeBERT embeddings (768-d) from the frozen encoder.
    - Edges: UNDIRECTED co-change edges. Two functions share an edge if
      they share a commit_id within the same project.
    - The graph is built per-batch or per-split for memory efficiency.

When Kaivalya's AST/call-graph backend is available, this module can be
replaced with richer edge types (CALLS, IMPORTS, DEPENDS_ON) while keeping
the same API.

Public API:
    build_cochange_graph(df, embeddings) -> (edge_index, edge_weight)
    build_split_graph(df, embeddings) -> Data (PyTorch Geometric Data object)
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
import torch


def build_cochange_edges(
    df: pd.DataFrame,
    commit_col: str = "commit_id",
    project_col: str = "project",
    max_commit_size: int = 50,
) -> Tuple[np.ndarray, np.ndarray]:
    """Build co-change edge list from a DataFrame.

    Two functions are connected if they share the same (project, commit_id).
    Large commits (> max_commit_size functions) are skipped to avoid
    creating dense cliques that dominate the graph.

    Args:
        df: DataFrame with at least commit_id and project columns.
            The DataFrame index is used as node index — reset before calling.
        commit_col: column with commit hash / ID.
        project_col: column with project name.
        max_commit_size: skip commits with more than this many functions
                         (avoids mega-cliques from release commits).

    Returns:
        edge_index: (2, E) int64 array of [src, dst] pairs (undirected → E is even)
        edge_weight: (E,) float32 array of 1.0 for all co-change edges
    """
    df = df.reset_index(drop=True)

    # Build (project, commit) → list of row indices
    commit_col_vals = df[commit_col].astype(str).fillna("UNKNOWN")
    proj_col_vals = df[project_col].astype(str).fillna("UNKNOWN")
    key = proj_col_vals + "__" + commit_col_vals

    groups: Dict[str, list] = {}
    for idx, k in enumerate(key):
        if k not in groups:
            groups[k] = []
        groups[k].append(idx)

    src_list = []
    dst_list = []

    for k, indices in groups.items():
        if len(indices) < 2 or len(indices) > max_commit_size:
            continue
        # All pairs in same commit → undirected edges
        for i in range(len(indices)):
            for j in range(i + 1, len(indices)):
                src_list.append(indices[i])
                dst_list.append(indices[j])
                src_list.append(indices[j])
                dst_list.append(indices[i])

    if not src_list:
        # Return empty edge index
        edge_index = np.zeros((2, 0), dtype=np.int64)
        edge_weight = np.zeros(0, dtype=np.float32)
        return edge_index, edge_weight

    edge_index = np.array([src_list, dst_list], dtype=np.int64)
    edge_weight = np.ones(len(src_list), dtype=np.float32)
    return edge_index, edge_weight


def build_split_graph(
    df: pd.DataFrame,
    embeddings: np.ndarray,
    commit_col: str = "commit_id",
    project_col: str = "project",
    max_commit_size: int = 50,
) -> "torch_geometric.data.Data":
    """Build a PyTorch Geometric Data object for a full split.

    Args:
        df: DataFrame (reset index before calling).
        embeddings: (N, 768) float32 CodeBERT embeddings, one per row.
        commit_col: commit identifier column.
        project_col: project name column.
        max_commit_size: passed to build_cochange_edges.

    Returns:
        torch_geometric.data.Data with:
            x:          (N, 768) node feature matrix
            edge_index: (2, E) edge list
            edge_attr:  (E, 1) edge weights (all 1.0)
    """
    try:
        from torch_geometric.data import Data
    except ImportError as e:
        raise ImportError(
            "torch_geometric is required for graph experiments. "
            "Install with: pip install torch_geometric"
        ) from e

    df = df.reset_index(drop=True)
    assert len(df) == len(embeddings), (
        f"df length ({len(df)}) must match embeddings length ({len(embeddings)})"
    )

    edge_index, edge_weight = build_cochange_edges(
        df, commit_col=commit_col, project_col=project_col,
        max_commit_size=max_commit_size
    )

    x = torch.tensor(embeddings, dtype=torch.float32)
    ei = torch.tensor(edge_index, dtype=torch.long)
    ew = torch.tensor(edge_weight, dtype=torch.float32).unsqueeze(1)

    return Data(x=x, edge_index=ei, edge_attr=ew)


def graph_stats(df: pd.DataFrame, max_commit_size: int = 50) -> dict:
    """Report graph statistics (node count, edge count, connectivity) without
    building PyG objects. Useful for debugging before training.
    """
    edge_index, _ = build_cochange_edges(df, max_commit_size=max_commit_size)
    n_nodes = len(df)
    n_edges = edge_index.shape[1] // 2  # undirected count
    connected_nodes = len(set(edge_index[0].tolist())) if edge_index.shape[1] > 0 else 0
    return {
        "n_nodes": n_nodes,
        "n_directed_edges": edge_index.shape[1],
        "n_undirected_edges": n_edges,
        "connected_nodes": connected_nodes,
        "isolated_nodes": n_nodes - connected_nodes,
        "connectivity_ratio": connected_nodes / max(1, n_nodes),
    }
