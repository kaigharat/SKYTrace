"""SkyTrace Phase-1 tests: dataset, features, metrics, model forward pass."""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "..", "src")
sys.path.insert(0, _SRC)

from skytrace.data.dataset import load_splits, class_distribution, CodeDataset, CodeDatasetConfig
from skytrace.features.static_features import extract_features, FEATURE_NAMES, extract_features_batch
from skytrace.evaluation.metrics import compute_all_metrics, find_best_threshold_by_f1
from skytrace.models.baselines import RandomForestBaseline


ROOT = os.path.join(_HERE, "..")
DATASET_CFG = {
    "splits": {
        "train": os.path.join(ROOT, "data", "splits", "train.parquet"),
        "validation": os.path.join(ROOT, "data", "splits", "validation.parquet"),
        "test": os.path.join(ROOT, "data", "splits", "test.parquet"),
    },
    "version": "test",
}

pytestmark = pytest.mark.skipif(
    not os.path.exists(os.path.join(ROOT, "data", "splits", "train.parquet")),
    reason="Dataset splits not built. Run scripts/build_dataset.py first.",
)


# ----- Dataset loading -----

def test_load_splits_returns_three_splits():
    splits = load_splits(DATASET_CFG, sample_size=200)
    assert set(splits.keys()) == {"train", "validation", "test"}
    for name, df in splits.items():
        assert len(df) > 0
        assert "function_code" in df.columns
        assert "label" in df.columns


def test_sample_size_truncates():
    splits = load_splits(DATASET_CFG, sample_size=100)
    assert len(splits["train"]) == 100
    assert len(splits["validation"]) == 100
    assert len(splits["test"]) == 100


def test_class_distribution_format():
    splits = load_splits(DATASET_CFG, sample_size=200)
    cd = class_distribution(splits["train"])
    assert "0" in cd and "1" in cd


def test_no_project_leakage_in_splits():
    splits = load_splits(DATASET_CFG, sample_size=500)
    train_p = set(splits["train"]["project"].dropna().unique())
    val_p = set(splits["validation"]["project"].dropna().unique())
    test_p = set(splits["test"]["project"].dropna().unique())
    assert not (train_p & val_p)
    assert not (train_p & test_p)
    assert not (val_p & test_p)


# ----- Static features -----

def test_extract_features_returns_all_feature_names():
    code = """
    int foo(int x) {
        if (x > 0) return 1;
        return 0;
    }
    """
    feats = extract_features(code)
    for name in FEATURE_NAMES:
        assert name in feats, f"Missing feature: {name}"


def test_extract_features_handles_empty_code():
    feats = extract_features("")
    assert feats["length_chars"] == 0
    assert feats["n_lines"] == 0


def test_extract_features_batch_returns_dataframe():
    codes = pd.Series(["int a() { return 1; }", "void b() { if(1) {} }"])
    df = extract_features_batch(codes)
    assert len(df) == 2
    assert list(df.columns) == FEATURE_NAMES


def test_features_distinguish_vulnerable_pattern():
    """A function with strcpy + gets should have higher risk-pattern flags."""
    safe = extract_features("int add(int a, int b) { return a + b; }")
    risky = extract_features("void f(char* d, char* s) { strcpy(d, s); gets(d); free(d); }")
    assert risky["has_strcpy"] == 1.0
    assert risky["has_gets"] == 1.0
    assert safe["has_strcpy"] == 0.0
    assert safe["has_gets"] == 0.0


# ----- Metrics -----

def test_compute_all_metrics_perfect_predictions():
    y_true = np.array([0, 0, 1, 1])
    y_pred = np.array([0, 0, 1, 1])
    proba = np.array([0.1, 0.2, 0.9, 0.95])
    m = compute_all_metrics(y_true, y_pred, proba)
    assert m["accuracy"] == 1.0
    assert m["precision"] == 1.0
    assert m["recall"] == 1.0
    assert m["f1"] == 1.0
    assert m["roc_auc"] == 1.0
    assert m["pr_auc"] == 1.0
    assert m["confusion_matrix"]["tp"] == 2
    assert m["confusion_matrix"]["tn"] == 2


def test_compute_all_metrics_handles_no_probabilities():
    y_true = np.array([0, 1, 0, 1])
    y_pred = np.array([0, 1, 1, 1])
    m = compute_all_metrics(y_true, y_pred)
    assert m["accuracy"] == 0.75
    assert m["roc_auc"] is None
    assert m["pr_auc"] is None


def test_find_best_threshold_by_f1():
    y_true = np.array([0, 0, 0, 1, 1, 1])
    proba = np.array([0.1, 0.2, 0.3, 0.6, 0.7, 0.95])
    t, f1 = find_best_threshold_by_f1(y_true, proba)
    assert 0.0 < t < 1.0
    assert f1 > 0.5


# ----- Random Forest baseline -----

def test_random_forest_fit_predict():
    rng = np.random.RandomState(42)
    X = rng.rand(200, 10)
    y = (X[:, 0] > 0.5).astype(int)
    rf = RandomForestBaseline(params={
        "n_estimators": 10, "max_depth": 5, "random_state": 42, "n_jobs": 1
    })
    rf.fit(X, y)
    preds = rf.predict(X)
    proba = rf.predict_proba(X)
    assert len(preds) == 200
    assert proba.shape == (200,)
    assert ((proba >= 0) & (proba <= 1)).all()


# ----- PyTorch Dataset (skipped if torch unavailable) -----

def test_code_dataset_returns_tensors():
    try:
        import torch
        from transformers import AutoTokenizer
    except ImportError:
        pytest.skip("torch/transformers not available")
    splits = load_splits(DATASET_CFG, sample_size=20)
    tok = AutoTokenizer.from_pretrained("microsoft/codebert-base")
    ds = CodeDataset(splits["train"].head(5), tok, CodeDatasetConfig(max_length=64))
    item = ds[0]
    assert "input_ids" in item
    assert "attention_mask" in item
    assert "label" in item
    assert item["input_ids"].shape[0] == 64
