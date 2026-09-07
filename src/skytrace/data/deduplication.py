"""Deduplication module.

Identifies and removes duplicate records according to a documented, defensible
rule set. Does NOT touch the dataframe in place — every function returns a
mask of rows to DROP and a list of human-readable reasons, so cleaning.py can
record the precise reason for every removed row.

Rules (in priority order):

    R1. Drop rows with missing or non-binary label  (handled by cleaning, not here)
    R2. Drop rows with empty / whitespace-only code (handled by cleaning, not here)
    R3. Drop EXACT duplicate rows (same function_code + label + project + commit_id)
    R4. Drop duplicate functions (same _function_hash) with CONTRADICTORY labels.
        Rule: drop BOTH sides — keeping one would inject label noise.
    R5. Drop duplicate functions (same _function_hash) with the SAME label.
        Rule: keep the FIRST occurrence (stable sort by sample_id), drop the rest.

We DO NOT use near-duplicate detection (minhash/LSH) in this phase — that
requires heavy computation and is documented as a future enhancement in
the leakage module.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd


def find_drop_mask(
    df: pd.DataFrame,
    drop_exact_duplicates: bool = True,
    drop_contradictory_label_duplicates: bool = True,
    drop_same_label_duplicates: bool = True,
) -> Tuple[pd.Series, List[Dict[str, object]]]:
    """Return a boolean mask of rows to drop, plus a list of per-reason counts.

    The mask is True for rows that should be REMOVED.
    """
    n = len(df)
    drop_mask = pd.Series([False] * n, index=df.index)
    reasons: List[Dict[str, object]] = []

    if not drop_exact_duplicates and not drop_contradictory_label_duplicates and not drop_same_label_duplicates:
        return drop_mask, reasons

    # R3. Exact duplicates (same function_code + label + project + commit_id + cwe + cve + file_path)
    exact_cols = [c for c in [
        "function_code", "label", "project", "commit_id", "cwe", "cve", "file_path"
    ] if c in df.columns]
    if drop_exact_duplicates and exact_cols:
        exact_dup_mask = df.duplicated(subset=exact_cols, keep="first")
        n_drop = int(exact_dup_mask.sum())
        if n_drop:
            drop_mask = drop_mask | exact_dup_mask
            reasons.append({
                "rule": "R3_exact_duplicate",
                "n_dropped": n_drop,
                "description": f"Rows that are exact duplicates on {exact_cols} (keep=first).",
            })

    # R4 + R5. Duplicate functions by _function_hash.
    if "_function_hash" in df.columns and "label" in df.columns:
        # Order the dataframe by sample_id so 'first' is deterministic.
        sort_key = "sample_id" if "sample_id" in df.columns else df.index
        ordered = df.sort_values(by=sort_key, kind="mergesort")

        # Group by function hash; for each group, examine label cardinality.
        grouped = ordered.groupby("_function_hash", sort=False)

        contradictory_hashes = []
        same_label_drops = 0

        # We'll work with positional indices for clarity.
        # For each group:
        #   - if labels disagree -> mark ALL rows in the group for drop (R4)
        #   - if labels agree      -> mark all rows EXCEPT the first for drop (R5)
        for fh, group in grouped:
            labels = group["label"].dropna().unique()
            if len(labels) > 1:
                contradictory_hashes.append(fh)
                drop_mask.loc[group.index] = True
            elif drop_same_label_duplicates and len(group) > 1:
                # Same label, multiple copies — keep the first, drop the rest.
                first_idx = group.index[0]
                rest = group.index[1:]
                drop_mask.loc[rest] = True
                same_label_drops += len(rest)

        if drop_contradictory_label_duplicates and contradictory_hashes:
            reasons.append({
                "rule": "R4_contradictory_label_duplicate",
                "n_dropped": int(sum(
                    len(g) for fh, g in df.groupby("_function_hash", sort=False)
                    if fh in set(contradictory_hashes)
                )),
                "n_distinct_function_hashes": len(contradictory_hashes),
                "description": "Same function source appears with multiple distinct labels (0 and 1). "
                               "Both sides dropped — keeping one would inject label noise.",
            })
        if drop_same_label_duplicates and same_label_drops:
            reasons.append({
                "rule": "R5_same_label_duplicate",
                "n_dropped": same_label_drops,
                "description": "Same function source AND same label, appearing multiple times. "
                               "First occurrence (by stable sample_id sort) is kept; rest dropped.",
            })

    return drop_mask, reasons
