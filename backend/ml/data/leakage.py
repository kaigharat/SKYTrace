"""Data leakage analysis.

Identifies potential sources of train/validation/test leakage BEFORE
constructing the splits. The point is to make leakage EXPLICIT so the
splitting strategy can defend against it.

Leakage sources analysed:

    L1. Duplicate function-code hashes across the whole dataset
    L2. (Optional) Near-duplicate functions via MinHash — OFF by default
    L3. Same project appearing in multiple splits (controlled by splitting.py)
    L4. Same commit_id appearing in multiple splits
    L5. Same repository appearing in multiple splits
    L6. Repeated vulnerable examples (same CVE / CWE repeated many times)

This module only REPORTS leakage — it does NOT modify the dataframe.
The splitting module uses these findings to design a project-aware split.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

import pandas as pd


def analyse_leakage(df: pd.DataFrame, near_duplicate: bool = False) -> Dict[str, Any]:
    """Return a JSON-serialisable leakage report."""
    report: Dict[str, Any] = {}
    n = len(df)

    # L1. Duplicate function-code hashes
    if "_function_hash" in df.columns:
        fh_dup_mask = df["_function_hash"].duplicated(keep=False)
        n_dup_rows = int(fh_dup_mask.sum())
        n_dup_hashes = int(df.loc[fh_dup_mask, "_function_hash"].nunique())
        report["L1_duplicate_function_hashes"] = {
            "n_rows_involved": n_dup_rows,
            "n_distinct_duplicate_hashes": n_dup_hashes,
            "pct_of_dataset": round(100.0 * n_dup_rows / n, 4) if n else 0.0,
            "interpretation": (
                "Same function source appearing multiple times. If these rows end up "
                "in different splits, the model can memorise the function and "
                "trivially predict the label. splitting.py must keep all copies of "
                "the same _function_hash in the SAME split."
            ),
        }

    # L2. Near-duplicate via MinHash (optional, expensive)
    if near_duplicate:
        try:
            from datasketch import MinHash, MinHashLSH
            lsh = MinHashLSH(threshold=0.9, num_perm=64)
            mhs = {}
            for i, code in enumerate(df["function_code"].fillna("").tolist()):
                mh = MinHash(num_perm=64)
                for tok in code.split():
                    mh.update(tok.encode("utf-8", errors="ignore"))
                lsh.insert(i, mh)
                mhs[i] = mh
            clusters = []
            seen = set()
            for i in range(len(df)):
                if i in seen:
                    continue
                neighbours = lsh.query(mhs[i])
                if len(neighbours) > 1:
                    clusters.append(neighbours)
                    seen.update(neighbours)
            report["L2_near_duplicate_clusters"] = {
                "n_clusters": len(clusters),
                "n_rows_involved": sum(len(c) for c in clusters),
                "threshold": 0.9,
            }
        except ImportError:
            report["L2_near_duplicate_clusters"] = {
                "status": "skipped",
                "reason": "datasketch not installed; install with `pip install datasketch` to enable.",
            }
    else:
        report["L2_near_duplicate_clusters"] = {
            "status": "disabled",
            "reason": "near_duplicate=False (default). Toggle on for thorough analysis.",
        }

    # L3. Project-level concentration
    if "project" in df.columns:
        proj_counts = df["project"].value_counts(dropna=False)
        report["L3_project_concentration"] = {
            "n_projects": int(df["project"].nunique(dropna=False)),
            "top10_projects_by_size": [
                {"project": str(p), "n_samples": int(c),
                 "pct_of_dataset": round(100.0 * c / n, 4) if n else 0.0}
                for p, c in proj_counts.head(10).items()
            ],
            "n_projects_with_single_sample": int((proj_counts == 1).sum()),
            "interpretation": (
                "If the largest project dominates the dataset, a random function-level "
                "split will leak project-specific patterns. splitting.py must group "
                "by project so that ALL samples of a project stay in ONE split."
            ),
        }

    # L4. Commit-level concentration
    if "commit_id" in df.columns:
        commit_counts = df["commit_id"].value_counts(dropna=False)
        report["L4_commit_concentration"] = {
            "n_unique_commits": int(df["commit_id"].nunique(dropna=False)),
            "top10_commits_by_size": [
                {"commit_id": str(c)[:16], "n_samples": int(n),
                 "pct_of_dataset": round(100.0 * n / len(df), 4) if len(df) else 0.0}
                for c, n in commit_counts.head(10).items()
            ],
            "n_commits_with_single_sample": int((commit_counts == 1).sum()),
            "interpretation": (
                "Multiple samples from the SAME commit are highly correlated "
                "(same author, same change context). They must stay in ONE split."
            ),
        }

    # L5. Repository-level concentration (same as project for DiverseVul, but
    # we still report because future datasets may separate them)
    if "repository" in df.columns:
        repo_counts = df["repository"].value_counts(dropna=False)
        report["L5_repository_concentration"] = {
            "n_repositories": int(df["repository"].nunique(dropna=False)),
            "top10_repositories_by_size": [
                {"repository": str(r), "n_samples": int(c)}
                for r, c in repo_counts.head(10).items()
            ],
            "note": "For DiverseVul, repository mirrors project (no separate field).",
        }

    # L6. Repeated vulnerable examples (same CWE / CVE repeated)
    if "cwe" in df.columns:
        cwe_counts = df["cwe"].dropna().value_counts()
        report["L6_vulnerable_example_repetition"] = {
            "n_distinct_cwe_combinations": int(cwe_counts.nunique()),
            "top10_cwe_by_size": [
                {"cwe": str(c), "n_samples": int(n)}
                for c, n in cwe_counts.head(10).items()
            ],
        }

    # ----- Leakage verdict -----
    findings: List[str] = []
    if "_function_hash" in df.columns:
        n_dup = report["L1_duplicate_function_hashes"]["n_rows_involved"]
        if n_dup > 0:
            findings.append(
                f"{n_dup} rows have duplicate function-code hashes — must be kept "
                "in the SAME split to avoid memorisation leakage."
            )
    if "project" in df.columns:
        n_proj = report["L3_project_concentration"]["n_projects"]
        top_proj_pct = (
            report["L3_project_concentration"]["top10_projects_by_size"][0]["pct_of_dataset"]
            if report["L3_project_concentration"]["top10_projects_by_size"] else 0.0
        )
        findings.append(
            f"Dataset has {n_proj} distinct projects; largest project covers "
            f"{top_proj_pct}% of samples. Project-aware split is REQUIRED."
        )
    if "commit_id" in df.columns:
        n_commits = report["L4_commit_concentration"]["n_unique_commits"]
        findings.append(
            f"Dataset has {n_commits} unique commits. Samples from the same commit "
            "are highly correlated and should ideally stay in the SAME split."
        )

    report["leakage_findings"] = findings
    report["recommended_split_strategy"] = (
        "Group by project; keep all samples of a project in ONE split. "
        "Within a split, samples from the same commit are allowed but should "
        "be reported. A naive function-level random split is FORBIDDEN."
    )
    return report


def write_leakage_report(report: Dict[str, Any], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"[leakage] Wrote leakage report -> {path}")
