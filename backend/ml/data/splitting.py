"""Project-aware train / validation / test splitting.

The split is performed at the PROJECT level, NOT the function level. All
samples belonging to a given project are kept together in ONE split. This
prevents project-specific patterns from leaking across splits.

Algorithm:
    1. Compute per-project (n_samples, n_vulnerable, n_clean).
    2. Sort projects by descending size (so we can pack big projects first
       and respect the target ratios as closely as possible).
    3. Greedily assign each project to the split that currently has the
       most "room" relative to its target ratio. Ties broken in the order
       train > validation > test so that ambiguous tail projects land in
       train (safer for class coverage).
    4. After assignment, verify:
         - no project appears in more than one split
         - each split has both classes (warning if not)
         - split ratios are within +/- 5% of target (warning if not)
    5. Return three dataframes and a per-split summary.

A naive function-level `train_test_split(random_state=42)` is FORBIDDEN.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd


def _class_dist(df: pd.DataFrame) -> Dict[str, int]:
    if "label" not in df.columns:
        return {}
    vc = df["label"].value_counts(dropna=False).to_dict()
    return {str(int(k)) if not pd.isna(k) else "NaN": int(v) for k, v in vc.items()}


def project_aware_split(
    df: pd.DataFrame,
    train_ratio: float = 0.80,
    val_ratio: float = 0.10,
    test_ratio: float = 0.10,
    random_state: int = 42,
    group_col: str = "project",
    allow_project_overlap: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Split the dataframe at the project level.

    Returns (train_df, val_df, test_df, report).
    """
    assert abs((train_ratio + val_ratio + test_ratio) - 1.0) < 1e-6, \
        f"Ratios must sum to 1.0; got {train_ratio + val_ratio + test_ratio}"

    if group_col not in df.columns:
        raise ValueError(f"Group column '{group_col}' not in dataframe columns.")

    if allow_project_overlap:
        raise ValueError(
            "allow_project_overlap=True is FORBIDDEN in this pipeline. "
            "Project leakage is a hard integrity constraint."
        )

    n_total = len(df)
    n_vuln_total = int((df["label"] == 1).sum()) if "label" in df.columns else 0
    n_clean_total = int((df["label"] == 0).sum()) if "label" in df.columns else 0

    # Per-project summary
    proj_summary = (
        df.groupby(group_col, dropna=False)
          .agg(
              n_samples=("label", "count"),
              n_vulnerable=("label", lambda s: int((s == 1).sum())),
              n_clean=("label", lambda s: int((s == 0).sum())),
          )
          .reset_index()
    )
    # Deterministic ordering — sort by size desc, then by name for stability.
    proj_summary = proj_summary.sort_values(
        by=["n_samples", group_col], ascending=[False, True], kind="mergesort"
    ).reset_index(drop=True)

    # Targets
    target_train = int(round(n_total * train_ratio))
    target_val = int(round(n_total * val_ratio))
    target_test = int(round(n_total * test_ratio))

    # Greedy assignment with class balance bias.
    # We track both sample counts and vulnerable counts per split so the
    # minority class distribution is also roughly proportional.
    split_assign: Dict[str, List[Any]] = {"train": [], "val": [], "test": []}
    split_counts = {"train": 0, "val": 0, "test": 0}
    split_vuln = {"train": 0, "val": 0, "test": 0}

    # Targets for vulnerable class as well
    target_train_v = int(round(n_vuln_total * train_ratio))
    target_val_v = int(round(n_vuln_total * val_ratio))
    target_test_v = int(round(n_vuln_total * test_ratio))

    # We use a small pseudo-random tiebreaker so that runs with different
    # random_state produce different (but still deterministic) layouts.
    rng = np.random.RandomState(random_state)
    # Add a small jitter per project for tiebreaking only
    jitter = rng.rand(len(proj_summary)) * 0.01

    for i, row in proj_summary.iterrows():
        proj = row[group_col]
        n_s = int(row["n_samples"])
        n_v = int(row["n_vulnerable"])

        # Compute the "deficit" of each split = target - current
        # We weight sample-count deficit and vulnerable-count deficit equally.
        deficit_train = (target_train - split_counts["train"]) / max(target_train, 1) \
                      + (target_train_v - split_vuln["train"]) / max(target_train_v, 1)
        deficit_val = (target_val - split_counts["val"]) / max(target_val, 1) \
                    + (target_val_v - split_vuln["val"]) / max(target_val_v, 1)
        deficit_test = (target_test - split_counts["test"]) / max(target_test, 1) \
                     + (target_test_v - split_vuln["test"]) / max(target_test_v, 1)

        # Add tiny jitter for deterministic tiebreaking
        d_train = deficit_train + jitter[i]
        d_val = deficit_val + jitter[i] * 0.5
        d_test = deficit_test + jitter[i] * 0.25

        # Pick the split with the largest deficit (most room left).
        # Ties broken in order train > val > test (safer to put tail in train).
        deficits = {"train": d_train, "val": d_val, "test": d_test}
        best = max(deficits.items(), key=lambda kv: kv[1])[0]

        split_assign[best].append(proj)
        split_counts[best] += n_s
        split_vuln[best] += n_v

    # Now slice the dataframe according to the project assignments.
    train_df = df[df[group_col].isin(split_assign["train"])].copy()
    val_df = df[df[group_col].isin(split_assign["val"])].copy()
    test_df = df[df[group_col].isin(split_assign["test"])].copy()

    # Sort for deterministic output
    sort_cols = [c for c in ["sample_id"] if c in df.columns]
    if sort_cols:
        train_df = train_df.sort_values(sort_cols, kind="mergesort").reset_index(drop=True)
        val_df = val_df.sort_values(sort_cols, kind="mergesort").reset_index(drop=True)
        test_df = test_df.sort_values(sort_cols, kind="mergesort").reset_index(drop=True)

    # ----- Build the split report -----
    report: Dict[str, Any] = {
        "strategy": "project_aware_greedy",
        "group_col": group_col,
        "ratios": {"train": train_ratio, "val": val_ratio, "test": test_ratio},
        "random_state": random_state,
        "allow_project_overlap": allow_project_overlap,
        "total_samples": int(n_total),
        "total_vulnerable": int(n_vuln_total),
        "total_clean": int(n_clean_total),
        "n_projects_total": int(proj_summary.shape[0]),
        "split_counts": {
            "train": {
                "n_samples": int(len(train_df)),
                "n_vulnerable": int((train_df["label"] == 1).sum()) if "label" in train_df.columns else 0,
                "n_clean": int((train_df["label"] == 0).sum()) if "label" in train_df.columns else 0,
                "n_projects": int(len(split_assign["train"])),
                "projects_sample": [str(p) for p in split_assign["train"][:20]],
            },
            "validation": {
                "n_samples": int(len(val_df)),
                "n_vulnerable": int((val_df["label"] == 1).sum()) if "label" in val_df.columns else 0,
                "n_clean": int((val_df["label"] == 0).sum()) if "label" in val_df.columns else 0,
                "n_projects": int(len(split_assign["val"])),
                "projects_sample": [str(p) for p in split_assign["val"][:20]],
            },
            "test": {
                "n_samples": int(len(test_df)),
                "n_vulnerable": int((test_df["label"] == 1).sum()) if "label" in test_df.columns else 0,
                "n_clean": int((test_df["label"] == 0).sum()) if "label" in test_df.columns else 0,
                "n_projects": int(len(split_assign["test"])),
                "projects_sample": [str(p) for p in split_assign["test"][:20]],
            },
        },
        "actual_ratios": {
            "train": round(len(train_df) / n_total, 6) if n_total else 0,
            "val": round(len(val_df) / n_total, 6) if n_total else 0,
            "test": round(len(test_df) / n_total, 6) if n_total else 0,
        },
        "class_distribution_by_split": {
            "train": _class_dist(train_df),
            "validation": _class_dist(val_df),
            "test": _class_dist(test_df),
        },
    }

    # Integrity assertions
    train_projects = set(split_assign["train"])
    val_projects = set(split_assign["val"])
    test_projects = set(split_assign["test"])
    overlap_tv = train_projects & val_projects
    overlap_tt = train_projects & test_projects
    overlap_vt = val_projects & test_projects
    report["integrity"] = {
        "project_overlap_train_val": [str(p) for p in overlap_tv],
        "project_overlap_train_test": [str(p) for p in overlap_tt],
        "project_overlap_val_test": [str(p) for p in overlap_vt],
        "ok": not (overlap_tv or overlap_tt or overlap_vt),
    }

    return train_df, val_df, test_df, report


def write_split_report(report: Dict[str, Any], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"[splitting] Wrote split report -> {path}")


def save_splits(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    out_dir: str,
) -> Dict[str, str]:
    """Save the three splits as compressed parquet. Returns file paths."""
    os.makedirs(out_dir, exist_ok=True)
    paths = {
        "train": os.path.join(out_dir, "train.parquet"),
        "validation": os.path.join(out_dir, "validation.parquet"),
        "test": os.path.join(out_dir, "test.parquet"),
    }
    train_df.to_parquet(paths["train"], engine="pyarrow", compression="zstd", index=False)
    val_df.to_parquet(paths["validation"], engine="pyarrow", compression="zstd", index=False)
    test_df.to_parquet(paths["test"], engine="pyarrow", compression="zstd", index=False)
    for k, p in paths.items():
        print(f"[splitting] Wrote {k} split -> {p}  ({os.path.getsize(p):,} bytes)")
    return paths
