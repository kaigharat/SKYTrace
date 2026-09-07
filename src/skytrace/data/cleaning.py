"""Cleaning pipeline.

Performs ONLY defensible cleaning operations on the raw mapped dataframe.
Every transformation is logged with the count of rows affected, and the
final cleaning_report.json records the before/after class distribution.

Operations (in order):

    C1. Drop rows with missing label or non-binary label
    C2. Drop rows with empty / whitespace-only function code
    C3. Drop rows with extremely short function code (< min_function_chars)
    C4. Drop rows with malformed source (no '{' brace at all)
    C5. Apply deduplication rules (R3 / R4 / R5 — see deduplication.py)

The output is the cleaned dataframe PLUS a JSON-serialisable report.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

import pandas as pd

from .deduplication import find_drop_mask


def _class_distribution(df: pd.DataFrame) -> Dict[str, int]:
    if "label" not in df.columns:
        return {}
    vc = df["label"].value_counts(dropna=False).to_dict()
    out: Dict[str, int] = {}
    for k, v in vc.items():
        try:
            if pd.isna(k):
                out["NaN"] = int(v)
            else:
                out[str(int(k))] = int(v)
        except (TypeError, ValueError):
            out[str(k)] = int(v)
    return out


def clean_dataframe(
    df: pd.DataFrame,
    min_function_chars: int = 15,
    drop_exact_duplicates: bool = True,
    drop_duplicate_functions_with_contradictory_labels: bool = True,
    drop_same_label_duplicate_functions: bool = True,
    contradictory_label_rule: str = "drop_both",
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Run the cleaning pipeline. Returns (cleaned_df, report)."""
    n_raw = len(df)
    reasons: List[Dict[str, Any]] = []
    drop_mask = pd.Series([False] * n_raw, index=df.index)

    # Snapshot the pre-cleaning class distribution.
    class_before = _class_distribution(df)

    # C1. Missing or non-binary label
    if "label" in df.columns:
        bad_label = ~df["label"].isin([0, 1])
        n_c1 = int(bad_label.sum())
        if n_c1:
            drop_mask = drop_mask | bad_label
            reasons.append({
                "rule": "C1_missing_or_non_binary_label",
                "n_dropped": n_c1,
                "description": "Rows where label is NaN or not in {0, 1}.",
            })

    # C2. Empty / whitespace-only function code
    if "function_code" in df.columns:
        code_str = df["function_code"].astype("string").fillna("")
        empty_mask = code_str.str.strip() == ""
        n_c2 = int(empty_mask.sum())
        if n_c2:
            drop_mask = drop_mask | empty_mask
            reasons.append({
                "rule": "C2_empty_function_code",
                "n_dropped": n_c2,
                "description": "Rows where function_code is empty, NaN, or whitespace-only.",
            })

        # C3. Extremely short function code
        code_lens = code_str.apply(len)
        short_mask = (code_lens > 0) & (code_lens < min_function_chars)
        n_c3 = int(short_mask.sum())
        if n_c3:
            drop_mask = drop_mask | short_mask
            reasons.append({
                "rule": "C3_extremely_short_function",
                "n_dropped": n_c3,
                "description": f"Rows where function_code is shorter than {min_function_chars} characters.",
            })

        # C4. Malformed source (no opening brace)
        has_brace = code_str.str.contains(r"\{", regex=True, na=False)
        malformed_mask = (code_str.str.strip() != "") & (~has_brace)
        n_c4 = int(malformed_mask.sum())
        if n_c4:
            drop_mask = drop_mask | malformed_mask
            reasons.append({
                "rule": "C4_malformed_no_brace",
                "n_dropped": n_c4,
                "description": "Rows where function_code has no '{' brace (malformed C/C++ source).",
            })

    # C5. Deduplication (R3/R4/R5)
    # Apply only AFTER C1–C4 so the dedup operates on the still-valid rows.
    # But we still need to record dedup counts over the original frame.
    # Strategy: run find_drop_mask on the full frame; the rows it identifies
    # that are ALSO not already flagged by C1–C4 will be dropped here.
    if any([drop_exact_duplicates, drop_duplicate_functions_with_contradictory_labels,
            drop_same_label_duplicate_functions]):
        dup_mask, dup_reasons = find_drop_mask(
            df,
            drop_exact_duplicates=drop_exact_duplicates,
            drop_contradictory_label_duplicates=drop_duplicate_functions_with_contradictory_labels,
            drop_same_label_duplicates=drop_same_label_duplicate_functions,
        )
        # Only count rows that weren't already dropped by C1-C4
        new_dup_drops = dup_mask & ~drop_mask
        for r in dup_reasons:
            # Re-count what's NEW
            # We can't perfectly attribute each dup rule to "new" vs "already-flagged"
            # without re-running groupby, so we record the original count and also
            # note that some overlap is possible.
            r_copy = dict(r)
            r_copy["n_already_dropped_by_earlier_rules"] = int((dup_mask & drop_mask).sum())
            reasons.append(r_copy)
        drop_mask = drop_mask | dup_mask

    cleaned = df.loc[~drop_mask].copy().reset_index(drop=True)
    class_after = _class_distribution(cleaned)

    report: Dict[str, Any] = {
        "raw_count": int(n_raw),
        "removed_count_total": int(drop_mask.sum()),
        "remaining_count": int(len(cleaned)),
        "removal_reasons": reasons,
        "class_distribution_before_cleaning": class_before,
        "class_distribution_after_cleaning": class_after,
        "config": {
            "min_function_chars": min_function_chars,
            "drop_exact_duplicates": drop_exact_duplicates,
            "drop_duplicate_functions_with_contradictory_labels": drop_duplicate_functions_with_contradictory_labels,
            "drop_same_label_duplicate_functions": drop_same_label_duplicate_functions,
            "contradictory_label_rule": contradictory_label_rule,
        },
    }
    return cleaned, report


def write_cleaning_report(report: Dict[str, Any], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"[cleaning] Wrote cleaning report -> {path}")
