"""SkyTrace training-phase dataset utilities.

Reads the existing leakage-safe splits produced by the dataset-foundation
phase. Does NOT regenerate splits, does NOT shuffle across projects.

Public API:
    load_splits(cfg) -> dict[str, pd.DataFrame]
    CodeDataset(torch.utils.data.Dataset)
    collate_codebert(batch) -> batch dict
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import pandas as pd
import torch
from torch.utils.data import Dataset


def load_splits(dataset_cfg: Dict[str, Any], sample_size: Optional[int] = None) -> Dict[str, pd.DataFrame]:
    """Load train / validation / test parquet files.

    Args:
        dataset_cfg: the `dataset:` block from configs/dataset.yaml
        sample_size: if not None, take the first N rows of each split
                     (dev mode). Splits are NOT reshuffled — we take the
                     first N rows in their existing (deterministic) order.

    Returns:
        {"train": df, "validation": df, "test": df}
    """
    splits_paths = dataset_cfg["splits"]
    out: Dict[str, pd.DataFrame] = {}
    for name, path in splits_paths.items():
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Split file not found: {path}. "
                "Run the dataset foundation pipeline (scripts/build_dataset.py) first."
            )
        df = pd.read_parquet(path)
        if sample_size is not None and len(df) > sample_size:
            df = df.head(sample_size).copy()
        out[name] = df
        print(f"[dataset] {name:<10}: {len(df):,} rows  ({df['project'].nunique()} projects)  from {path}")
    return out


def class_distribution(df: pd.DataFrame, label_col: str = "label") -> Dict[str, int]:
    vc = df[label_col].value_counts(dropna=False).to_dict()
    return {str(int(k)) if not pd.isna(k) else "NaN": int(v) for k, v in vc.items()}


# ----- PyTorch Datasets -----------------------------------------------------


@dataclass
class CodeDatasetConfig:
    text_col: str = "function_code"
    label_col: str = "label"
    sample_id_col: str = "sample_id"
    project_col: str = "project"
    max_length: int = 512
    truncation: bool = True
    padding: str = "max_length"


class CodeDataset(Dataset):
    """PyTorch Dataset for raw function source code + label.

    Returns dicts with keys: input_ids, attention_mask, label, sample_id, project.
    Tokenization happens here so the DataLoader can parallelise it across workers.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        tokenizer,
        cfg: Optional[CodeDatasetConfig] = None,
    ):
        self.df = df.reset_index(drop=True)
        self.tokenizer = tokenizer
        self.cfg = cfg or CodeDatasetConfig()
        # Pre-extract columns as numpy arrays for speed
        self.texts = self.df[self.cfg.text_col].astype(str).tolist()
        self.labels = self.df[self.cfg.label_col].astype(int).tolist()
        self.sample_ids = self.df[self.cfg.sample_id_col].astype(str).tolist() \
            if self.cfg.sample_id_col in self.df.columns else [str(i) for i in range(len(self.df))]
        self.projects = self.df[self.cfg.project_col].astype(str).tolist() \
            if self.cfg.project_col in self.df.columns else ["unknown"] * len(self.df)

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        text = self.texts[idx]
        enc = self.tokenizer(
            text,
            truncation=self.cfg.truncation,
            padding=self.cfg.padding,
            max_length=self.cfg.max_length,
            return_tensors="pt",
        )
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "label": torch.tensor(self.labels[idx], dtype=torch.float),
            "sample_id": self.sample_ids[idx],
            "project": self.projects[idx],
        }


def collate_codebert(batch):
    """Custom collate that stacks tensors and keeps strings as lists."""
    input_ids = torch.stack([b["input_ids"] for b in batch])
    attention_mask = torch.stack([b["attention_mask"] for b in batch])
    labels = torch.stack([b["label"] for b in batch])
    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels,
        "sample_ids": [b["sample_id"] for b in batch],
        "projects": [b["project"] for b in batch],
    }


# ----- For Random Forest / static-feature baselines -------------------------

class StaticFeatureDataset:
    """Thin wrapper around a feature matrix + label vector.

    Used by the Random Forest baseline. The actual feature extraction lives
    in skytrace.features.static_features.
    """

    def __init__(self, X, y, sample_ids=None, projects=None):
        self.X = X
        self.y = y
        self.sample_ids = sample_ids
        self.projects = projects

    def __len__(self) -> int:
        return len(self.y)

    def as_arrays(self):
        import numpy as np
        X = self.X if isinstance(self.X, np.ndarray) else self.X.to_numpy()
        y = self.y if isinstance(self.y, np.ndarray) else self.y.to_numpy()
        return X, y
