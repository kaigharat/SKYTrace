"""SkyTrace evaluation metrics.

Computes the full metric set required by the project spec:
    - Accuracy
    - Precision / Recall / F1 (binary)
    - Macro F1 / Weighted F1
    - ROC-AUC
    - PR-AUC (average_precision_score)
    - Confusion matrix

All functions accept true labels (0/1) and either predicted labels or
predicted probabilities, depending on the metric.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


def compute_all_metrics(
    y_true: np.ndarray,
    y_pred_labels: np.ndarray,
    y_pred_proba: Optional[np.ndarray] = None,
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """Compute the full SkyTrace metric set.

    Args:
        y_true: ground-truth labels (0/1), shape (N,)
        y_pred_labels: predicted labels (0/1), shape (N,)
        y_pred_proba: predicted probability of positive class, shape (N,).
                      If None, ROC-AUC / PR-AUC are skipped.
        threshold: threshold used to derive y_pred_labels (for reporting only)

    Returns:
        dict with all metrics + confusion matrix
    """
    y_true = np.asarray(y_true).astype(int)
    y_pred_labels = np.asarray(y_pred_labels).astype(int)

    metrics: Dict[str, Any] = {
        "threshold": threshold,
        "n_samples": int(len(y_true)),
        "n_positive": int(y_true.sum()),
        "n_negative": int((y_true == 0).sum()),
        "accuracy": float(accuracy_score(y_true, y_pred_labels)),
        "precision": float(precision_score(y_true, y_pred_labels, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred_labels, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred_labels, zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred_labels, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred_labels, average="weighted", zero_division=0)),
    }

    cm = confusion_matrix(y_true, y_pred_labels, labels=[0, 1])
    metrics["confusion_matrix"] = {
        "tn": int(cm[0, 0]),
        "fp": int(cm[0, 1]),
        "fn": int(cm[1, 0]),
        "tp": int(cm[1, 1]),
    }

    if y_pred_proba is not None:
        y_pred_proba = np.asarray(y_pred_proba).astype(float)
        # ROC-AUC is only defined if both classes are present
        if len(np.unique(y_true)) == 2:
            metrics["roc_auc"] = float(roc_auc_score(y_true, y_pred_proba))
            metrics["pr_auc"] = float(average_precision_score(y_true, y_pred_proba))
            # ROC + PR curve points for plotting
            fpr, tpr, _ = roc_curve(y_true, y_pred_proba)
            metrics["roc_curve"] = {
                "fpr": fpr.tolist(),
                "tpr": tpr.tolist(),
            }
            prec, rec, _ = precision_recall_curve(y_true, y_pred_proba)
            metrics["pr_curve"] = {
                "precision": prec.tolist(),
                "recall": rec.tolist(),
            }
        else:
            metrics["roc_auc"] = None
            metrics["pr_auc"] = None
            metrics["roc_curve"] = None
            metrics["pr_curve"] = None
            metrics["_warning"] = "ROC-AUC / PR-AUC skipped: only one class present in y_true."
    else:
        metrics["roc_auc"] = None
        metrics["pr_auc"] = None
        metrics["roc_curve"] = None
        metrics["pr_curve"] = None

    return metrics


def find_best_threshold_by_f1(y_true: np.ndarray, y_pred_proba: np.ndarray) -> Tuple[float, float]:
    """Sweep thresholds and return (best_threshold, best_f1).

    Used for picking an operating point on the validation set; the test
    set must NEVER be used for threshold tuning.
    """
    y_true = np.asarray(y_true).astype(int)
    y_pred_proba = np.asarray(y_pred_proba).astype(float)
    best_t, best_f1 = 0.5, 0.0
    for t in np.linspace(0.01, 0.99, 99):
        preds = (y_pred_proba >= t).astype(int)
        f1 = f1_score(y_true, preds, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_t = float(t)
    return best_t, float(best_f1)


def bootstrap_ci(
    y_true: np.ndarray,
    y_pred_proba: np.ndarray,
    metric_fn,
    n_boot: int = 1000,
    ci: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float, float]:
    """Bootstrap confidence interval for any metric.

    Args:
        metric_fn: callable(y_true, y_pred_proba) -> float
    Returns:
        (point_estimate, lower, upper)
    """
    y_true = np.asarray(y_true).astype(int)
    y_pred_proba = np.asarray(y_pred_proba).astype(float)
    rng = np.random.RandomState(seed)
    n = len(y_true)
    point = metric_fn(y_true, y_pred_proba)
    boots = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.randint(0, n, size=n)
        if len(np.unique(y_true[idx])) < 2:
            boots[i] = np.nan
            continue
        boots[i] = metric_fn(y_true[idx], y_pred_proba[idx])
    boots = boots[~np.isnan(boots)]
    alpha = (1 - ci) / 2
    lower = float(np.quantile(boots, alpha))
    upper = float(np.quantile(boots, 1 - alpha))
    return float(point), lower, upper
