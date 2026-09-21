"""Dataset audit pipeline.

Inspects the raw mapped dataframe and reports:

    BASIC STATISTICS
      - total samples
      - number of projects
      - number of repositories
      - vulnerable / non-vulnerable counts
      - class ratio
      - number of CWE categories
      - number of CVEs (if available)

    MISSING VALUES  (per column, count + percentage)

    DUPLICATES
      - duplicate sample IDs
      - duplicate function-code hashes
      - exact duplicate rows
      - duplicate functions with DIFFERENT labels (contradictory)

    CODE QUALITY
      - empty functions (empty / whitespace only)
      - extremely short functions (below threshold)
      - malformed source (no opening brace)
      - invalid records (missing label, missing code, non-binary label)
      - missing labels

The audit does NOT modify the dataframe. It only reports.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import numpy as np
import pandas as pd

# Columns considered part of the canonical "row identity" for exact-duplicate
# detection. We exclude sample_id (because it's derived) and metadata columns
# like _raw_hash that may legitimately vary.
_EXACT_DUP_COLS = [
    "function_code", "label", "project", "commit_id", "cwe", "cve", "file_path"
]


def _safe_len(s) -> int:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return 0
    try:
        return len(str(s))
    except Exception:
        return 0


def audit_dataframe(
    df: pd.DataFrame,
    min_function_chars: int = 15,
) -> Dict[str, Any]:
    """Run the full audit. Returns a JSON-serialisable dict."""
    report: Dict[str, Any] = {}
    n = len(df)
    report["total_samples"] = int(n)

    # ----- BASIC STATISTICS -----
    basic: Dict[str, Any] = {}
    basic["total_samples"] = int(n)

    projects = df["project"].dropna().unique() if "project" in df.columns else np.array([])
    repos = df["repository"].dropna().unique() if "repository" in df.columns else np.array([])
    basic["n_projects"] = int(len(projects))
    basic["n_repositories"] = int(len(repos))
    basic["project_list_sample"] = [str(p) for p in projects[:30]]

    label_col = df["label"] if "label" in df.columns else pd.Series(dtype="Int64")
    label_counts = label_col.value_counts(dropna=False).to_dict()
    # Normalise keys to strings
    label_counts_str = {str(int(k)) if isinstance(k, (int, np.integer)) and not pd.isna(k) else ("NaN" if pd.isna(k) else str(k)): int(v)
                        for k, v in label_counts.items()}
    basic["label_counts"] = label_counts_str

    n_vuln = int(label_counts_str.get("1", 0))
    n_clean = int(label_counts_str.get("0", 0))
    n_missing_label = int(label_counts_str.get("NaN", 0))
    basic["n_vulnerable"] = n_vuln
    basic["n_non_vulnerable"] = n_clean
    basic["n_missing_label"] = n_missing_label
    total_labelled = n_vuln + n_clean
    basic["class_ratio_vulnerable_to_total"] = (
        round(n_vuln / total_labelled, 6) if total_labelled else None
    )
    basic["class_imbalance_ratio_clean_to_vuln"] = (
        round(n_clean / n_vuln, 4) if n_vuln else None
    )

    # CWE categories — explode comma-separated values
    cwe_series = df["cwe"].dropna() if "cwe" in df.columns else pd.Series(dtype="string")
    cwe_exploded = cwe_series.str.split(",").explode().str.strip()
    cwe_exploded = cwe_exploded[cwe_exploded != ""]
    unique_cwes = sorted(cwe_exploded.unique().tolist())
    basic["n_cwe_categories"] = len(unique_cwes)
    basic["cwe_list_sample"] = unique_cwes[:30]
    basic["cwe_counts_top10"] = {str(k): int(v) for k, v in cwe_exploded.value_counts().head(10).items()}

    # CVEs
    cve_series = df["cve"].dropna() if "cve" in df.columns else pd.Series(dtype="string")
    cve_series = cve_series[cve_series.astype(str).str.strip() != ""]
    basic["n_cves"] = int(cve_series.nunique())
    basic["n_samples_with_cve"] = int(len(cve_series))

    report["basic_statistics"] = basic

    # ----- MISSING VALUES -----
    missing: Dict[str, Dict[str, Any]] = {}
    for col in df.columns:
        n_null = int(df[col].isna().sum())
        # Also count empty strings as missing for string columns
        if df[col].dtype == "string" or df[col].dtype == "object":
            n_empty_str = int((df[col].astype("string").fillna("").str.strip() == "").sum())
            n_null = max(n_null, n_empty_str)
        pct = round(100.0 * n_null / n, 4) if n else 0.0
        missing[str(col)] = {"n_missing": n_null, "pct_missing": pct}
    report["missing_values"] = missing

    # ----- DUPLICATES -----
    dups: Dict[str, Any] = {}

    # Duplicate sample IDs
    if "sample_id" in df.columns:
        sid_dup_mask = df["sample_id"].duplicated(keep=False)
        dups["duplicate_sample_ids"] = {
            "n_rows_involved": int(sid_dup_mask.sum()),
            "n_distinct_duplicate_ids": int(df.loc[sid_dup_mask, "sample_id"].nunique()),
        }
    else:
        dups["duplicate_sample_ids"] = {"n_rows_involved": 0, "n_distinct_duplicate_ids": 0}

    # Duplicate function-code hashes (same function source, possibly different metadata)
    if "_function_hash" in df.columns:
        fh_dup_mask = df["_function_hash"].duplicated(keep=False)
        dups["duplicate_function_hashes"] = {
            "n_rows_involved": int(fh_dup_mask.sum()),
            "n_distinct_duplicate_hashes": int(df.loc[fh_dup_mask, "_function_hash"].nunique()),
        }
    else:
        dups["duplicate_function_hashes"] = {"n_rows_involved": 0, "n_distinct_duplicate_hashes": 0}

    # Exact duplicate rows (on canonical identity columns)
    present_exact_cols = [c for c in _EXACT_DUP_COLS if c in df.columns]
    if present_exact_cols:
        exact_dup_mask = df.duplicated(subset=present_exact_cols, keep=False)
        dups["exact_duplicate_rows"] = {
            "n_rows_involved": int(exact_dup_mask.sum()),
            "columns_used": present_exact_cols,
        }
    else:
        dups["exact_duplicate_rows"] = {"n_rows_involved": 0, "columns_used": []}

    # Duplicate functions (by code hash) with CONTRADICTORY labels
    if "_function_hash" in df.columns and "label" in df.columns:
        fh_groups = df.groupby("_function_hash")["label"].nunique(dropna=False)
        contradictory_hashes = fh_groups[fh_groups > 1]
        n_contradictory_rows = int(df[df["_function_hash"].isin(contradictory_hashes.index)].shape[0])
        dups["duplicate_functions_with_contradictory_labels"] = {
            "n_distinct_function_hashes_with_contradiction": int(len(contradictory_hashes)),
            "n_rows_involved": n_contradictory_rows,
        }
    else:
        dups["duplicate_functions_with_contradictory_labels"] = {
            "n_distinct_function_hashes_with_contradiction": 0,
            "n_rows_involved": 0,
        }

    report["duplicates"] = dups

    # ----- CODE QUALITY -----
    quality: Dict[str, Any] = {}
    code = df["function_code"] if "function_code" in df.columns else pd.Series(dtype="string")
    code_str = code.astype("string").fillna("")
    code_lens = code_str.apply(_safe_len)

    quality["empty_functions"] = int((code_str.str.strip() == "").sum())
    quality["extremely_short_functions"] = int(
        ((code_lens > 0) & (code_lens < min_function_chars)).sum()
    )
    quality["min_function_chars_threshold"] = min_function_chars
    # Malformed = no opening brace AND non-empty (every C/C++ function should have one)
    has_brace = code_str.str.contains(r"\{", regex=True, na=False)
    non_empty = code_str.str.strip() != ""
    malformed_mask = non_empty & (~has_brace)
    quality["malformed_no_brace"] = int(malformed_mask.sum())

    # Invalid records: missing label OR non-binary label OR missing code
    label_invalid = ~df["label"].isin([0, 1]) if "label" in df.columns else pd.Series([True] * n)
    code_missing = code_str.str.strip() == ""
    quality["invalid_records"] = {
        "missing_label": int(label_invalid.sum()),
        "missing_code": int(code_missing.sum()),
        "total_invalid": int((label_invalid | code_missing).sum()),
    }
    quality["missing_labels"] = int(label_invalid.sum())

    # Length distribution summary
    quality["function_length_stats"] = {
        "min": int(code_lens.min()) if n else 0,
        "max": int(code_lens.max()) if n else 0,
        "mean": round(float(code_lens.mean()), 2) if n else 0,
        "median": float(code_lens.median()) if n else 0,
        "p25": float(code_lens.quantile(0.25)) if n else 0,
        "p75": float(code_lens.quantile(0.75)) if n else 0,
        "p95": float(code_lens.quantile(0.95)) if n else 0,
        "p99": float(code_lens.quantile(0.99)) if n else 0,
    }

    report["code_quality"] = quality

    # ----- PROJECT-LEVEL SUMMARY (for leakage analysis preview) -----
    if "project" in df.columns:
        proj_summary = (
            df.groupby("project", dropna=False)
              .agg(
                  n_samples=("sample_id", "count"),
                  n_vulnerable=("label", lambda s: int((s == 1).sum())),
                  n_commits=("commit_id", "nunique"),
              )
              .sort_values("n_samples", ascending=False)
        )
        report["project_summary_top20"] = [
            {
                "project": str(idx) if not pd.isna(idx) else "NULL",
                "n_samples": int(row["n_samples"]),
                "n_vulnerable": int(row["n_vulnerable"]),
                "n_commits": int(row["n_commits"]),
            }
            for idx, row in proj_summary.head(20).iterrows()
        ]
        report["n_projects_total"] = int(df["project"].nunique(dropna=False))
        report["n_commits_total"] = int(df["commit_id"].nunique(dropna=False)) if "commit_id" in df.columns else 0

    return report


def write_audit_report(report: Dict[str, Any], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"[audit] Wrote audit report -> {path}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from skytrace.data.loader import load_diversevul
    df = load_diversevul(sample_size=500)
    rep = audit_dataframe(df)
    print(json.dumps(rep, indent=2, default=str)[:2000])
