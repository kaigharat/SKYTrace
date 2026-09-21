"""SkyTrace — Dataset integrity tests.

Run with:  pytest tests/test_dataset.py -v

These tests assert the integrity of the FINAL processed dataset. They
require the build pipeline to have been run at least once.
"""

from __future__ import annotations

import os
import sys

import pandas as pd
import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "..", "src")
sys.path.insert(0, _SRC)

from skytrace.data.schema import CANONICAL_FIELDS, validate_schema

ROOT = os.path.join(_HERE, "..")
PROCESSED = os.path.join(ROOT, "data", "processed", "skytrace_diversevul.parquet")
TRAIN = os.path.join(ROOT, "data", "splits", "train.parquet")
VAL = os.path.join(ROOT, "data", "splits", "validation.parquet")
TEST = os.path.join(ROOT, "data", "splits", "test.parquet")


# Skip the entire module if the dataset has not been built yet.
pytestmark = pytest.mark.skipif(
    not os.path.exists(PROCESSED),
    reason="Processed dataset not built. Run scripts/build_dataset.py first.",
)


@pytest.fixture(scope="module")
def processed_df():
    return pd.read_parquet(PROCESSED)


@pytest.fixture(scope="module")
def splits():
    return {
        "train": pd.read_parquet(TRAIN),
        "val": pd.read_parquet(VAL),
        "test": pd.read_parquet(TEST),
    }


def test_processed_file_exists():
    assert os.path.exists(PROCESSED), f"Missing processed file: {PROCESSED}"


def test_split_files_exist():
    for p in [TRAIN, VAL, TEST]:
        assert os.path.exists(p), f"Missing split file: {p}"


def test_no_duplicate_sample_ids(processed_df):
    n_dup = int(processed_df["sample_id"].duplicated().sum())
    assert n_dup == 0, f"Found {n_dup} duplicate sample_ids in processed dataset"


def test_no_empty_labels(processed_df):
    n_empty = int(processed_df["label"].isna().sum())
    assert n_empty == 0, f"Found {n_empty} empty labels in processed dataset"


def test_no_empty_function_code(processed_df):
    n_empty = int((processed_df["function_code"].astype("string").fillna("").str.strip() == "").sum())
    assert n_empty == 0, f"Found {n_empty} empty function_code rows in processed dataset"


def test_no_project_leakage_between_splits(splits):
    train_p = set(splits["train"]["project"].dropna().unique())
    val_p = set(splits["val"]["project"].dropna().unique())
    test_p = set(splits["test"]["project"].dropna().unique())
    assert not (train_p & val_p), f"train/val project overlap: {train_p & val_p}"
    assert not (train_p & test_p), f"train/test project overlap: {train_p & test_p}"
    assert not (val_p & test_p), f"val/test project overlap: {val_p & test_p}"


def test_expected_schema_exists(processed_df):
    violations = validate_schema(processed_df)
    assert not violations, f"Schema violations: {violations}"


def test_train_val_test_non_empty(splits):
    assert len(splits["train"]) > 0, "train split is empty"
    assert len(splits["val"]) > 0, "validation split is empty"
    assert len(splits["test"]) > 0, "test split is empty"


def test_class_distribution_reported(processed_df):
    counts = processed_df["label"].value_counts(dropna=False).to_dict()
    assert 0 in counts or "0" in counts or 0.0 in counts, "No class 0 in label distribution"
    assert 1 in counts or "1" in counts or 1.0 in counts, "No class 1 in label distribution"


def test_dataset_count_reproducible(processed_df):
    """Reproducibility: re-reading the parquet must give the same row count."""
    df2 = pd.read_parquet(PROCESSED)
    assert len(df2) == len(processed_df), "Row count changed on re-read"


def test_canonical_fields_present(processed_df):
    for f in CANONICAL_FIELDS:
        assert f in processed_df.columns, f"Canonical field missing: {f}"


def test_future_derived_fields_are_null(processed_df):
    """Future-derived fields must be all-NULL in this phase — never zeros."""
    for f in ["prior_defect_count", "prior_vulnerability_count",
              "co_change_frequency", "file_volatility"]:
        if f in processed_df.columns:
            non_null = int(processed_df[f].notna().sum())
            assert non_null == 0, (
                f"Future-derived field '{f}' has {non_null} non-null values — "
                "this phase must NOT populate derived features."
            )


def test_min_sample_count(processed_df):
    """Spec requirement: at least 60K usable samples (soft, but enforced)."""
    assert len(processed_df) >= 60_000, (
        f"Processed dataset has only {len(processed_df):,} rows; "
        f"minimum 60,000 required."
    )


def test_splits_sum_to_processed(splits, processed_df):
    total = len(splits["train"]) + len(splits["val"]) + len(splits["test"])
    assert total == len(processed_df), (
        f"Split sizes ({total}) don't sum to processed ({len(processed_df)})"
    )
