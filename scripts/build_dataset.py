"""SkyTrace — Dataset foundation build script.

Orchestrates the full pipeline:

    1. Load raw DiverseVul from HuggingFace
    2. Audit the raw dataset (stats, missing, duplicates, code quality)
    3. Run leakage analysis
    4. Clean (drop exact dup, drop contradictory-label dup, drop empty/short/malformed)
    5. Audit the CLEANED dataset
    6. Project-aware 80/10/10 split (no project leakage)
    7. Write canonical processed parquet + split parquets
    8. Write dataset_card.md
    9. Generate 6 analysis plots
    10. Run integrity tests

Usage:
    python scripts/build_dataset.py                       # full mode
    python scripts/build_dataset.py --sample-size 10000   # dev mode
    python scripts/build_dataset.py --streaming           # low-memory streaming
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import time
from typing import Any, Dict

import pandas as pd
import yaml

# Make src/ importable when running the script directly.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "..", "src")
sys.path.insert(0, _SRC)

from skytrace.data.loader import LoaderConfig, load_diversevul
from skytrace.data.audit import audit_dataframe, write_audit_report
from skytrace.data.leakage import analyse_leakage, write_leakage_report
from skytrace.data.cleaning import clean_dataframe, write_cleaning_report
from skytrace.data.splitting import project_aware_split, save_splits, write_split_report
from skytrace.data.schema import coerce_to_canonical, validate_schema, CANONICAL_FIELDS
from skytrace.data.plots import generate_all_plots


CONFIG_PATH = os.path.join(_HERE, "..", "configs", "dataset.yaml")


def load_config(path: str = CONFIG_PATH) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_dataset_card(
    cfg: Dict[str, Any],
    raw_df: pd.DataFrame,
    cleaned_df: pd.DataFrame,
    raw_audit: Dict[str, Any],
    cleaned_audit: Dict[str, Any],
    leakage_report: Dict[str, Any],
    split_report: Dict[str, Any],
    cleaning_report: Dict[str, Any],
    out_path: str,
) -> None:
    """Generate data/reports/dataset_card.md."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    now = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    dataset = cfg["dataset"]
    paths = cfg["paths"]
    cleaning_cfg = cfg["cleaning"]
    split_cfg = cfg["splitting"]

    raw_basic = raw_audit.get("basic_statistics", {})
    clean_basic = cleaned_audit.get("basic_statistics", {})

    md = []
    md.append(f"# SkyTrace Dataset Card — `{dataset['version_label']}`\n")
    md.append(f"Generated: **{now}**\n")
    md.append("---\n")
    md.append("## 1. Source dataset\n")
    md.append(f"- Name: **{dataset['name']}**")
    md.append(f"- HuggingFace source: `{dataset['source']}`")
    md.append(f"- Language: {dataset['language']}")
    md.append(f"- Task: {dataset['task']}")
    md.append(f"- Original paper: Chen et al., *DiverseVul: A New Vulnerable Source Code "
              "Dataset for Deep Learning Based Vulnerability Detection*, RAID 2023.")
    md.append(f"- SkyTrace version label: `{dataset['version_label']}`\n")

    md.append("## 2. Preprocessing version\n")
    md.append(f"- SkyTrace data module version: `0.1.0`")
    md.append(f"- Cleaning config: `{json.dumps(cleaning_cfg, ensure_ascii=False)}`")
    md.append(f"- Split config: `{json.dumps(split_cfg, ensure_ascii=False)}`\n")

    md.append("## 3. Sample counts\n")
    md.append("| Stage | Total | Vulnerable | Non-vulnerable |")
    md.append("|---|---|---|---|")
    md.append(f"| Raw | {raw_audit['total_samples']:,} | {raw_basic.get('n_vulnerable', 0):,} | {raw_basic.get('n_non_vulnerable', 0):,} |")
    md.append(f"| Cleaned | {cleaned_audit['total_samples']:,} | {clean_basic.get('n_vulnerable', 0):,} | {clean_basic.get('n_non_vulnerable', 0):,} |")
    sc = split_report["split_counts"]
    md.append(f"| Train | {sc['train']['n_samples']:,} | {sc['train']['n_vulnerable']:,} | {sc['train']['n_clean']:,} |")
    md.append(f"| Validation | {sc['validation']['n_samples']:,} | {sc['validation']['n_vulnerable']:,} | {sc['validation']['n_clean']:,} |")
    md.append(f"| Test | {sc['test']['n_samples']:,} | {sc['test']['n_vulnerable']:,} | {sc['test']['n_clean']:,} |\n")

    md.append("## 4. Class distribution\n")
    md.append("```json")
    md.append(json.dumps({
        "raw": cleaning_report["class_distribution_before_cleaning"],
        "cleaned": cleaning_report["class_distribution_after_cleaning"],
        "by_split": split_report["class_distribution_by_split"],
    }, indent=2, ensure_ascii=False))
    md.append("```\n")

    md.append("## 5. Cleaning rules applied\n")
    for r in cleaning_report["removal_reasons"]:
        md.append(f"- **{r['rule']}** — {r.get('description','')} "
                  f"({r.get('n_dropped', 0):,} rows)")
    md.append("")

    md.append("## 6. Split strategy\n")
    md.append(f"- Strategy: `{split_report['strategy']}`")
    md.append(f"- Group column: `{split_report['group_col']}`")
    md.append(f"- Random state: {split_report['random_state']}")
    md.append(f"- Project overlap allowed: {split_report['allow_project_overlap']}  (HARD CONSTRAINT: must be False)")
    md.append(f"- Actual ratios: train={split_report['actual_ratios']['train']:.4f}, "
              f"val={split_report['actual_ratios']['val']:.4f}, "
              f"test={split_report['actual_ratios']['test']:.4f}")
    md.append(f"- Project counts: train={sc['train']['n_projects']}, "
              f"val={sc['validation']['n_projects']}, "
              f"test={sc['test']['n_projects']}")
    md.append(f"- Project overlap integrity: "
              f"{'OK (no overlap)' if split_report['integrity']['ok'] else 'VIOLATION!'}\n")

    md.append("## 7. Leakage findings\n")
    for f in leakage_report.get("leakage_findings", []):
        md.append(f"- {f}")
    md.append("")
    md.append(f"Recommended strategy: {leakage_report.get('recommended_split_strategy','')}\n")

    md.append("## 8. Schema\n")
    md.append("Canonical schema (see `src/skytrace/data/schema.py`):\n")
    md.append("```")
    for f in CANONICAL_FIELDS:
        md.append(f"  - {f}")
    md.append("```\n")
    md.append("Future-derived fields (`prior_defect_count`, `prior_vulnerability_count`, "
              "`co_change_frequency`, `file_volatility`) are **intentionally NULL** in this "
              "phase and will be populated during the repository-mining phase.\n")

    md.append("## 9. File outputs\n")
    md.append("```")
    md.append(f"{paths['processed_file']}")
    md.append(f"{paths['splits_dir']}/train.parquet")
    md.append(f"{paths['splits_dir']}/validation.parquet")
    md.append(f"{paths['splits_dir']}/test.parquet")
    md.append(f"{paths['audit_report']}")
    md.append(f"{paths['cleaning_report']}")
    md.append(f"{paths['leakage_report']}")
    md.append(f"{paths['split_report']}")
    md.append(f"{paths['dataset_card']}")
    md.append(f"{paths['plots_dir']}/  (6 PNG plots)")
    md.append("```\n")

    md.append("## 10. Research integrity\n")
    md.append("- No samples were fabricated.")
    md.append("- No rows were duplicated to reach a target size.")
    md.append("- No vulnerability labels, commits, CWE values, or repository "
              "relationships were invented.")
    md.append("- Every removed row is accounted for in `cleaning_report.json`.")
    md.append("- Split is project-aware; the same project does NOT appear in multiple splits.\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"[build] Wrote dataset card -> {out_path}")


def run_integrity_checks(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    cleaned_df: pd.DataFrame,
) -> Dict[str, Any]:
    """Run automated integrity assertions. Returns a report dict; raises on hard failure."""
    results: Dict[str, Any] = {"checks": [], "all_passed": True}

    def _check(name: str, ok: bool, detail: str = "") -> None:
        results["checks"].append({"name": name, "passed": bool(ok), "detail": detail})
        if not ok:
            results["all_passed"] = False
            print(f"  [FAIL] {name}: {detail}")
        else:
            print(f"  [ ok ] {name}")

    # 1. No duplicate sample IDs in cleaned
    n_dup = int(cleaned_df["sample_id"].duplicated().sum()) if "sample_id" in cleaned_df.columns else -1
    _check("no_duplicate_sample_ids_in_cleaned", n_dup == 0, f"{n_dup} duplicates")

    # 2. No empty labels in cleaned
    n_empty_label = int(cleaned_df["label"].isna().sum()) if "label" in cleaned_df.columns else -1
    _check("no_empty_labels_in_cleaned", n_empty_label == 0, f"{n_empty_label} empty labels")

    # 3. No empty source code in cleaned
    n_empty_code = int((cleaned_df["function_code"].astype("string").fillna("").str.strip() == "").sum()) \
        if "function_code" in cleaned_df.columns else -1
    _check("no_empty_function_code_in_cleaned", n_empty_code == 0, f"{n_empty_code} empty codes")

    # 4. No project leakage between splits
    tp = set(train_df["project"].dropna().unique()) if "project" in train_df.columns else set()
    vp = set(val_df["project"].dropna().unique()) if "project" in val_df.columns else set()
    ep = set(test_df["project"].dropna().unique()) if "project" in test_df.columns else set()
    ov_tv = tp & vp
    ov_te = tp & ep
    ov_ve = vp & ep
    _check("no_project_overlap_train_val", len(ov_tv) == 0, f"{len(ov_tv)} overlapping projects: {list(ov_tv)[:5]}")
    _check("no_project_overlap_train_test", len(ov_te) == 0, f"{len(ov_te)} overlapping projects: {list(ov_te)[:5]}")
    _check("no_project_overlap_val_test", len(ov_ve) == 0, f"{len(ov_ve)} overlapping projects: {list(ov_ve)[:5]}")

    # 5. Expected schema exists in cleaned
    violations = validate_schema(cleaned_df)
    _check("canonical_schema_valid", len(violations) == 0, "; ".join(violations))

    # 6. Train/val/test non-empty
    _check("train_non_empty", len(train_df) > 0, f"{len(train_df)} rows")
    _check("val_non_empty", len(val_df) > 0, f"{len(val_df)} rows")
    _check("test_non_empty", len(test_df) > 0, f"{len(test_df)} rows")

    # 7. Class distribution is reported (just check the column exists and has both classes in train)
    train_labels = set(train_df["label"].dropna().unique().tolist()) if "label" in train_df.columns else set()
    _check("train_has_both_classes", {0, 1}.issubset(train_labels), f"labels found: {train_labels}")

    return results


def main():
    ap = argparse.ArgumentParser(description="SkyTrace dataset foundation build pipeline.")
    ap.add_argument("--sample-size", type=int, default=None,
                    help="Dev mode: take first N rows per source split. "
                         "Default = full dataset.")
    ap.add_argument("--streaming", action="store_true",
                    help="Use HF streaming (lower memory, slower).")
    ap.add_argument("--config", default=CONFIG_PATH)
    args = ap.parse_args()

    cfg = load_config(args.config)
    paths = cfg["paths"]
    os.makedirs(paths["raw_dir"], exist_ok=True)
    os.makedirs(paths["processed_dir"], exist_ok=True)
    os.makedirs(paths["splits_dir"], exist_ok=True)
    os.makedirs(paths["reports_dir"], exist_ok=True)
    os.makedirs(paths["plots_dir"], exist_ok=True)

    t0 = time.time()
    print("=" * 70)
    print("SkyTrace — Dataset Foundation Build Pipeline")
    print("=" * 70)
    print(f"Mode: {'DEV (sample_size=' + str(args.sample_size) + ')' if args.sample_size else 'FULL'}")
    print(f"Streaming: {args.streaming}")
    print()

    # ---------- 1. LOAD ----------
    print("[1/10] Loading raw DiverseVul ...")
    raw_df = load_diversevul(sample_size=args.sample_size, streaming=args.streaming)
    print(f"  -> raw rows: {len(raw_df):,}")
    print()

    # ---------- 2. AUDIT RAW ----------
    print("[2/10] Auditing raw dataset ...")
    raw_audit = audit_dataframe(raw_df, min_function_chars=cfg["cleaning"]["min_function_chars"])
    write_audit_report(raw_audit, paths["audit_report"])
    print(f"  -> total: {raw_audit['total_samples']:,}, "
          f"vuln: {raw_audit['basic_statistics']['n_vulnerable']:,}, "
          f"clean: {raw_audit['basic_statistics']['n_non_vulnerable']:,}")
    print()

    # ---------- 3. LEAKAGE ----------
    print("[3/10] Running leakage analysis ...")
    leakage_report = analyse_leakage(raw_df, near_duplicate=cfg["audit"]["near_duplicate_minhash"])
    write_leakage_report(leakage_report, paths["leakage_report"])
    for f in leakage_report["leakage_findings"]:
        print(f"  -> {f}")
    print()

    # ---------- 4. CLEAN ----------
    print("[4/10] Cleaning ...")
    cl_cfg = cfg["cleaning"]
    cleaned_df, cleaning_report = clean_dataframe(
        raw_df,
        min_function_chars=cl_cfg["min_function_chars"],
        drop_exact_duplicates=cl_cfg["drop_exact_duplicates"],
        drop_duplicate_functions_with_contradictory_labels=cl_cfg["drop_duplicate_functions_with_contradictory_labels"],
        drop_same_label_duplicate_functions=True,
        contradictory_label_rule=cl_cfg["contradictory_label_rule"],
    )
    write_cleaning_report(cleaning_report, paths["cleaning_report"])
    print(f"  -> raw: {cleaning_report['raw_count']:,}, "
          f"removed: {cleaning_report['removed_count_total']:,}, "
          f"remaining: {cleaning_report['remaining_count']:,}")
    print()

    # ---------- 5. AUDIT CLEANED ----------
    print("[5/10] Auditing cleaned dataset ...")
    cleaned_audit = audit_dataframe(cleaned_df, min_function_chars=cl_cfg["min_function_chars"])
    write_audit_report(cleaned_audit, os.path.join(paths["reports_dir"], "cleaned_audit.json"))
    print()

    # ---------- 6. COERCE TO CANONICAL SCHEMA ----------
    print("[6/10] Coercing to canonical schema ...")
    # Drop internal columns before writing canonical parquet
    internal_cols = [c for c in cleaned_df.columns if c.startswith("_")]
    canonical_df = cleaned_df.drop(columns=internal_cols).copy()
    canonical_df = coerce_to_canonical(canonical_df)
    violations = validate_schema(canonical_df)
    if violations:
        print("  [WARN] Schema violations:")
        for v in violations:
            print(f"    - {v}")
    else:
        print("  -> Schema valid.")
    # Persist processed parquet
    canonical_df.to_parquet(paths["processed_file"], engine="pyarrow", compression="zstd", index=False)
    print(f"  -> wrote {paths['processed_file']}  ({os.path.getsize(paths['processed_file']):,} bytes)")
    print()

    # ---------- 7. SPLIT ----------
    print("[7/10] Project-aware split ...")
    sp_cfg = cfg["splitting"]
    train_df, val_df, test_df, split_report = project_aware_split(
        canonical_df,
        train_ratio=sp_cfg["train_ratio"],
        val_ratio=sp_cfg["val_ratio"],
        test_ratio=sp_cfg["test_ratio"],
        random_state=sp_cfg["random_state"],
        group_col="project",
        allow_project_overlap=sp_cfg["allow_project_overlap"],
    )
    write_split_report(split_report, paths["split_report"])
    save_splits(train_df, val_df, test_df, paths["splits_dir"])
    print(f"  -> train: {len(train_df):,}, val: {len(val_df):,}, test: {len(test_df):,}")
    print(f"  -> integrity OK: {split_report['integrity']['ok']}")
    if not split_report["integrity"]["ok"]:
        print("  [FAIL] Project leakage detected — aborting.")
        sys.exit(2)
    print()

    # ---------- 8. DATASET CARD ----------
    print("[8/10] Writing dataset card ...")
    build_dataset_card(
        cfg, raw_df, canonical_df, raw_audit, cleaned_audit,
        leakage_report, split_report, cleaning_report,
        paths["dataset_card"],
    )
    print()

    # ---------- 9. PLOTS ----------
    print("[9/10] Generating plots ...")
    plot_paths = generate_all_plots(canonical_df, raw_audit, paths["plots_dir"])
    for k, p in plot_paths.items():
        print(f"  -> {k}: {p}")
    print()

    # ---------- 10. INTEGRITY CHECKS ----------
    print("[10/10] Running integrity checks ...")
    integrity = run_integrity_checks(train_df, val_df, test_df, canonical_df)
    with open(os.path.join(paths["reports_dir"], "integrity_report.json"), "w", encoding="utf-8") as f:
        json.dump(integrity, f, indent=2, ensure_ascii=False, default=str)
    if not integrity["all_passed"]:
        print("\n[FAIL] One or more integrity checks failed. See integrity_report.json.")
        sys.exit(3)
    print()

    elapsed = time.time() - t0
    print("=" * 70)
    print(f"DONE in {elapsed:.1f}s")
    print("=" * 70)
    print()
    print("FINAL REPORT")
    print("-" * 70)
    print(f"RAW DATASET")
    print(f"  exact raw sample count:        {raw_audit['total_samples']:,}")
    print(f"  projects:                      {raw_audit['basic_statistics']['n_projects']:,}")
    print(f"  vulnerable samples:            {raw_audit['basic_statistics']['n_vulnerable']:,}")
    print(f"  non-vulnerable samples:        {raw_audit['basic_statistics']['n_non_vulnerable']:,}")
    print()
    print(f"CLEANED DATASET")
    print(f"  exact final sample count:      {cleaned_audit['total_samples']:,}")
    print(f"  removed samples:               {cleaning_report['removed_count_total']:,}")
    print(f"  final vulnerable samples:      {cleaned_audit['basic_statistics']['n_vulnerable']:,}")
    print(f"  final clean samples:           {cleaned_audit['basic_statistics']['n_non_vulnerable']:,}")
    print()
    print(f"SPLITS")
    sc = split_report["split_counts"]
    print(f"  training count:                {sc['train']['n_samples']:,}  ({sc['train']['n_projects']} projects)")
    print(f"  validation count:              {sc['validation']['n_samples']:,}  ({sc['validation']['n_projects']} projects)")
    print(f"  test count:                    {sc['test']['n_samples']:,}  ({sc['test']['n_projects']} projects)")
    print()
    print(f"QUALITY")
    d = raw_audit["duplicates"]
    print(f"  duplicate sample IDs:          {d['duplicate_sample_ids']['n_rows_involved']:,}")
    print(f"  duplicate function hashes:     {d['duplicate_function_hashes']['n_rows_involved']:,}")
    print(f"  exact duplicate rows:          {d['exact_duplicate_rows']['n_rows_involved']:,}")
    print(f"  contradictory-label duplicates:{d['duplicate_functions_with_contradictory_labels']['n_rows_involved']:,}")
    q = raw_audit["code_quality"]
    print(f"  empty functions:               {q['empty_functions']:,}")
    print(f"  extremely short functions:     {q['extremely_short_functions']:,}")
    print(f"  malformed (no brace):          {q['malformed_no_brace']:,}")
    print(f"  missing labels:                {q['missing_labels']:,}")
    print()
    print(f"  project leakage:               {'NONE (OK)' if split_report['integrity']['ok'] else 'VIOLATION!'}")
    print()
    print("All artifacts written to:")
    print(f"  {paths['processed_file']}")
    print(f"  {paths['splits_dir']}/")
    print(f"  {paths['reports_dir']}/")
    print()
    print("STOP — dataset foundation complete. Do NOT proceed to model development.")


if __name__ == "__main__":
    main()
