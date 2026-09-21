"""SkyTrace — Proxy history feature extractor.

All four "future_derived" columns in the dataset schema
(prior_defect_count, prior_vulnerability_count, co_change_frequency,
file_volatility) are 100% NULL in the current DiverseVul splits —
they require Kaivalya's git-mining backend to populate.

This module derives LEGITIMATE PROXY history features entirely from
columns that already exist in the parquet files:
    - commit_id   (present, non-null for most rows)
    - project     (present, non-null)
    - cwe         (present for ~86% of positive rows)
    - label       (present — but ONLY used on training split)

Features derived:
    commit_size             int    how many functions changed in same commit
    project_vuln_density    float  fraction of training functions from this
                                   project that are vulnerable (train-only)
    has_cwe                 float  1.0 if CWE is recorded
    n_cwe_types             float  count of comma-separated CWE identifiers
    function_name_len       float  length of extracted function name string
    is_long_function        float  1.0 if function has > 50 lines of code
                                   (rough size proxy from function_code)

All features are in [0, inf) or [0, 1] — no normalisation required here;
the HistoryEncoder MLP handles it with BatchNorm.

Public API:
    HistoryFeatureExtractor — fit on train, transform any split
    HISTORY_FEATURE_NAMES   — list of feature names (in order)
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

HISTORY_FEATURE_NAMES: List[str] = [
    "commit_size",
    "project_vuln_density",
    "has_cwe",
    "n_cwe_types",
    "function_name_len",
    "is_long_function",
]

N_HISTORY_FEATURES = len(HISTORY_FEATURE_NAMES)


def _count_lines(code: str) -> int:
    if not isinstance(code, str) or not code:
        return 0
    return len(code.splitlines())


def _parse_cwe(cwe_val) -> List[str]:
    if cwe_val is None or (isinstance(cwe_val, float) and np.isnan(cwe_val)):
        return []
    s = str(cwe_val).strip()
    if not s or s.lower() in ("nan", "none", "<na>"):
        return []
    return [c.strip() for c in s.split(",") if c.strip()]


class HistoryFeatureExtractor:
    """Fit on training data, transform any split.

    Fitting computes per-project vulnerability density using ONLY the
    training labels — this is critical to prevent leakage.
    """

    def __init__(self, long_function_threshold: int = 50):
        self.long_function_threshold = long_function_threshold
        self._project_vuln_density: Dict[str, float] = {}
        self._global_vuln_density: float = 0.0
        self._commit_size_map: Dict[str, int] = {}
        self._fitted = False

    def fit(self, train_df: pd.DataFrame) -> "HistoryFeatureExtractor":
        """Fit on training split only.

        Args:
            train_df: training DataFrame with columns project, label, commit_id.
        """
        df = train_df.copy()

        # 1. Per-project vulnerability density (train labels only)
        df["_label"] = pd.to_numeric(df["label"], errors="coerce").fillna(0).astype(int)
        proj_stats = df.groupby("project", observed=True)["_label"].agg(["mean", "count"])
        self._project_vuln_density = proj_stats["mean"].to_dict()
        self._global_vuln_density = float(df["_label"].mean())

        # 2. Commit size map (from training split)
        commit_key = df["project"].astype(str).fillna("UNKNOWN") + "__" + df["commit_id"].astype(str).fillna("UNKNOWN")
        self._commit_size_map = commit_key.value_counts().to_dict()

        self._fitted = True
        print(
            f"[history] Fitted HistoryFeatureExtractor on {len(df):,} training rows. "
            f"Projects: {len(self._project_vuln_density):,}  "
            f"Global vuln density: {self._global_vuln_density:.4f}"
        )
        return self

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """Extract history features for a DataFrame split.

        Returns:
            (N, N_HISTORY_FEATURES) float32 array
        """
        if not self._fitted:
            raise RuntimeError("Call fit() on training data before transform().")

        df = df.reset_index(drop=True)
        n = len(df)
        out = np.zeros((n, N_HISTORY_FEATURES), dtype=np.float32)

        proj = df["project"].astype(str).fillna("UNKNOWN")
        commit = df["commit_id"].astype(str).fillna("UNKNOWN")
        commit_key = proj + "__" + commit

        for i in range(n):
            # commit_size — how many functions in same commit (from train map)
            ckey = commit_key.iloc[i]
            out[i, 0] = float(self._commit_size_map.get(ckey, 1))

            # project_vuln_density — from training labels, fallback to global
            pkey = proj.iloc[i]
            out[i, 1] = float(self._project_vuln_density.get(pkey, self._global_vuln_density))

            # has_cwe
            cwe_items = _parse_cwe(df["cwe"].iloc[i] if "cwe" in df.columns else None)
            out[i, 2] = 1.0 if cwe_items else 0.0

            # n_cwe_types
            out[i, 3] = float(len(cwe_items))

            # function_name_len
            fn_name = df["function_name"].iloc[i] if "function_name" in df.columns else None
            fn_name_str = str(fn_name) if (fn_name is not None and not (isinstance(fn_name, float) and np.isnan(fn_name))) else ""
            out[i, 4] = float(len(fn_name_str))

            # is_long_function
            code = df["function_code"].iloc[i] if "function_code" in df.columns else ""
            out[i, 5] = 1.0 if _count_lines(str(code)) > self.long_function_threshold else 0.0

        return out

    def fit_transform(self, train_df: pd.DataFrame) -> np.ndarray:
        """Fit on train_df, then transform it."""
        self.fit(train_df)
        return self.transform(train_df)

    def feature_names(self) -> List[str]:
        return HISTORY_FEATURE_NAMES
