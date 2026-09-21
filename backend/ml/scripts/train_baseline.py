"""SkyTrace — Random Forest baseline training script.

Usage:
    python scripts/train_baseline.py --config configs/baseline.yaml
    python scripts/train_baseline.py --config configs/baseline.yaml --sample-size 10000

Pipeline:
    1. Load the existing leakage-safe splits (train / val / test)
    2. Extract static code features (cached)
    3. Train RandomForestClassifier with class_weight='balanced'
    4. Tune the decision threshold on the VALIDATION set only
    5. Evaluate on the untouched TEST set
    6. Save metrics, plots, and experiment artifacts
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict

import numpy as np
import pandas as pd
import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "..", "src")
sys.path.insert(0, _SRC)

from skytrace.data.dataset import load_splits, class_distribution
from skytrace.features.static_features import extract_features_batch, FEATURE_NAMES
from skytrace.models.baselines import RandomForestBaseline
from skytrace.evaluation.metrics import compute_all_metrics, find_best_threshold_by_f1
from skytrace.evaluation.plots import (
    plot_confusion_matrix, plot_roc_curve, plot_pr_curve, save_metrics_report
)


def load_config(path: str) -> Dict[str, Any]:
    path = os.path.abspath(path)
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    # Merge in dataset config (resolve relative to the config file's dir)
    dcfg_path = os.path.join(os.path.dirname(path), cfg["dataset"]["config"])
    with open(dcfg_path, "r", encoding="utf-8") as f:
        cfg["dataset_full"] = yaml.safe_load(f)
    return cfg


def get_or_compute_features(
    df: pd.DataFrame,
    cache_path: str,
    use_cache: bool,
    text_col: str = "function_code",
) -> tuple:
    """Return (X, feature_names). Uses cache if available and enabled."""
    if use_cache and os.path.exists(cache_path):
        cached = pd.read_parquet(cache_path)
        if len(cached) == len(df) and "sample_id" in cached.columns:
            cached = cached.set_index("sample_id").loc[df["sample_id"].values].reset_index()
            X = cached[FEATURE_NAMES].values
            print(f"[features] loaded cached features ({len(cached):,} rows) from {cache_path}")
            return X, FEATURE_NAMES
        else:
            print(f"[features] cache size mismatch ({len(cached)} vs {len(df)}); recomputing")
    print(f"[features] extracting {len(FEATURE_NAMES)} features for {len(df):,} rows ...")
    t0 = time.time()
    feats = extract_features_batch(df[text_col])
    feats["sample_id"] = df["sample_id"].values
    X = feats[FEATURE_NAMES].values
    print(f"[features] done in {time.time() - t0:.1f}s  shape={X.shape}")
    if use_cache:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        feats.to_parquet(cache_path, index=False)
        print(f"[features] cached -> {cache_path}")
    return X, FEATURE_NAMES


def main():
    ap = argparse.ArgumentParser(description="SkyTrace Random Forest baseline training")
    ap.add_argument("--config", default="configs/baseline.yaml")
    ap.add_argument("--sample-size", type=int, default=None,
                    help="Dev mode: take first N rows of each split.")
    args = ap.parse_args()

    cfg = load_config(args.config)
    exp_cfg = cfg["experiment"]
    feat_cfg = cfg["features"]
    model_cfg = cfg["model"]
    eval_cfg = cfg["evaluation"]
    dataset_cfg = cfg["dataset_full"]["dataset"]
    sample_size = args.sample_size or cfg["dataset"].get("sample_size")

    out_dir = exp_cfg["output_dir"]
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs("reports/confusion_matrices", exist_ok=True)
    os.makedirs("reports/roc_curves", exist_ok=True)
    os.makedirs("reports/pr_curves", exist_ok=True)

    print("=" * 70)
    print(f"SkyTrace — Random Forest Baseline")
    print(f"  experiment: {exp_cfg['name']}")
    print(f"  output_dir: {out_dir}")
    print(f"  sample_size: {sample_size or 'FULL'}")
    print(f"  seed: {exp_cfg['seed']}")
    print("=" * 70)

    # 1. Load splits
    print("\n[1/6] Loading splits ...")
    splits = load_splits(dataset_cfg, sample_size=sample_size)
    for name, df in splits.items():
        print(f"  {name:<10}: {len(df):,} rows  class_dist={class_distribution(df)}")

    # 2. Extract features (cached)
    print("\n[2/6] Extracting static code features ...")
    use_cache = feat_cfg.get("cache", True)
    cache_path = feat_cfg.get("cache_path", os.path.join(out_dir, "features_cache.parquet"))
    Xs = {}
    ys = {}
    for name, df in splits.items():
        X, _ = get_or_compute_features(df, cache_path + f".{name}", use_cache)
        Xs[name] = X
        ys[name] = df["label"].astype(int).values
    print(f"  feature dim: {Xs['train'].shape[1]}")

    # 3. Train RF
    print("\n[3/6] Training RandomForestClassifier ...")
    rf = RandomForestBaseline(params=model_cfg["params"])
    rf.fit(Xs["train"], ys["train"])
    print(f"  fit time: {rf.fit_time_sec:.1f}s")

    # 4. Predict probabilities on val/test
    print("\n[4/6] Predicting ...")
    val_proba = rf.predict_proba(Xs["validation"])
    test_proba = rf.predict_proba(Xs["test"])

    # 5. Tune threshold on VALIDATION only
    best_t, best_f1 = find_best_threshold_by_f1(ys["validation"], val_proba)
    print(f"  best threshold (tuned on validation): {best_t:.3f}  (val F1={best_f1:.4f})")

    # 6. Evaluate on test
    print("\n[5/6] Evaluating on TEST set ...")
    test_preds = (test_proba >= best_t).astype(int)
    test_metrics = compute_all_metrics(ys["test"], test_preds, test_proba, threshold=best_t)
    # Also evaluate at default 0.5 threshold for transparency
    test_metrics_05 = compute_all_metrics(ys["test"], (test_proba >= 0.5).astype(int), test_proba, threshold=0.5)

    # Validation metrics (for transparency — NOT used as test performance)
    val_preds = (val_proba >= best_t).astype(int)
    val_metrics = compute_all_metrics(ys["validation"], val_preds, val_proba, threshold=best_t)

    print("\nTEST METRICS (threshold tuned on validation):")
    print(json.dumps({k: v for k, v in test_metrics.items() if k not in ("roc_curve", "pr_curve", "sample_ids", "projects")}, indent=2, default=str))
    print("\nTEST METRICS (threshold=0.5):")
    print(json.dumps({k: v for k, v in test_metrics_05.items() if k not in ("roc_curve", "pr_curve", "sample_ids", "projects")}, indent=2, default=str))

    # 7. Save artifacts
    print("\n[6/6] Saving artifacts ...")
    save_metrics_report(test_metrics, os.path.join(out_dir, "test_metrics.json"))
    save_metrics_report(val_metrics, os.path.join(out_dir, "validation_metrics.json"))

    # Plots
    plot_confusion_matrix(test_metrics["confusion_matrix"],
                          "Random Forest — Test Confusion Matrix",
                          "reports/confusion_matrices/random_forest_test.png")
    if test_metrics.get("roc_curve"):
        plot_roc_curve(test_metrics["roc_curve"],
                       "Random Forest — Test ROC Curve",
                       "reports/roc_curves/random_forest_test.png",
                       auc=test_metrics.get("roc_auc"))
    if test_metrics.get("pr_curve"):
        plot_pr_curve(test_metrics["pr_curve"],
                      "Random Forest — Test PR Curve",
                      "reports/pr_curves/random_forest_test.png",
                      ap=test_metrics.get("pr_auc"))

    # Experiment metadata
    experiment_metadata = {
        "experiment_name": exp_cfg["name"],
        "model": rf.get_params(),
        "feature_names": FEATURE_NAMES,
        "n_features": len(FEATURE_NAMES),
        "dataset_version": dataset_cfg["version"],
        "sample_size": sample_size,
        "split_sizes": {k: len(v) for k, v in splits.items()},
        "class_distribution_train": class_distribution(splits["train"]),
        "class_distribution_val": class_distribution(splits["validation"]),
        "class_distribution_test": class_distribution(splits["test"]),
        "best_threshold_tuned_on_validation": best_t,
        "validation_f1_at_best_threshold": best_f1,
        "fit_time_sec": rf.fit_time_sec,
        "test_metrics_at_best_threshold": {k: v for k, v in test_metrics.items() if k not in ("roc_curve", "pr_curve", "sample_ids", "projects")},
        "test_metrics_at_0_5_threshold": {k: v for k, v in test_metrics_05.items() if k not in ("roc_curve", "pr_curve", "sample_ids", "projects")},
        "validation_metrics": {k: v for k, v in val_metrics.items() if k not in ("roc_curve", "pr_curve", "sample_ids", "projects")},
        "seed": exp_cfg["seed"],
        "top10_features_by_importance": dict(sorted(
            {f"feature_{i:02d}_{FEATURE_NAMES[i]}": float(v)
             for i, v in enumerate(rf.model.feature_importances_)}.items(),
            key=lambda x: -x[1]
        )[:10]),
    }
    with open(os.path.join(out_dir, "experiment.json"), "w", encoding="utf-8") as f:
        json.dump(experiment_metadata, f, indent=2, default=str)
    print(f"[experiment] saved -> {os.path.join(out_dir, 'experiment.json')}")

    print("\n" + "=" * 70)
    print("Random Forest baseline COMPLETE")
    print("=" * 70)
    print(f"  TEST ROC-AUC: {test_metrics.get('roc_auc')}")
    print(f"  TEST PR-AUC:  {test_metrics.get('pr_auc')}")
    print(f"  TEST F1:      {test_metrics.get('f1')}  (threshold={best_t:.3f})")
    print(f"  TEST Macro F1: {test_metrics.get('macro_f1')}")
    print(f"  TEST confusion: TP={test_metrics['confusion_matrix']['tp']}  "
          f"FP={test_metrics['confusion_matrix']['fp']}  "
          f"FN={test_metrics['confusion_matrix']['fn']}  "
          f"TN={test_metrics['confusion_matrix']['tn']}")


if __name__ == "__main__":
    main()
