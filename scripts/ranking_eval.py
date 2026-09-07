"""SkyTrace — Ranking Evaluation: Precision@K, Recall@K, MRR.

Usage:
    python scripts/ranking_eval.py

Loads the test_metrics.json for each experiment, extracts predicted
probabilities from the saved experiment artifacts, and computes:
    - Precision@K for K in [5, 10, 20, 50, 100, 200, 500]
    - Recall@K for same K values
    - MRR (Mean Reciprocal Rank)

The test set has 1,795 actual vulnerabilities in 33,352 samples.
Ranking by predicted probability and evaluating how many true positives
appear near the top answers RQ6: "How well can the system rank risky components?"

Output:
    reports/ranking_eval.json   — machine-readable results
    reports/ranking_eval.png    — Precision@K and Recall@K curves
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "..", "src")
sys.path.insert(0, _SRC)


def precision_at_k(y_true: np.ndarray, y_score: np.ndarray, k: int) -> float:
    """Precision@K: fraction of top-K predictions that are truly positive."""
    top_k_idx = np.argsort(y_score)[::-1][:k]
    return float(y_true[top_k_idx].sum()) / k


def recall_at_k(y_true: np.ndarray, y_score: np.ndarray, k: int) -> float:
    """Recall@K: fraction of all positives captured in top-K."""
    n_pos = y_true.sum()
    if n_pos == 0:
        return 0.0
    top_k_idx = np.argsort(y_score)[::-1][:k]
    return float(y_true[top_k_idx].sum()) / n_pos


def mrr(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Mean Reciprocal Rank: 1 / rank of first true positive."""
    sorted_idx = np.argsort(y_score)[::-1]
    for rank, idx in enumerate(sorted_idx, 1):
        if y_true[idx] == 1:
            return 1.0 / rank
    return 0.0


def average_precision(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Average Precision (equivalent to sklearn's average_precision_score)."""
    sorted_idx = np.argsort(y_score)[::-1]
    y_sorted = y_true[sorted_idx]
    n_pos = y_true.sum()
    if n_pos == 0:
        return 0.0
    precisions = np.cumsum(y_sorted) / np.arange(1, len(y_sorted) + 1)
    return float((precisions * y_sorted).sum() / n_pos)


def ranking_metrics(y_true: np.ndarray, y_score: np.ndarray, k_values: List[int]) -> Dict:
    results = {}
    for k in k_values:
        if k > len(y_true):
            continue
        results[f"precision@{k}"] = precision_at_k(y_true, y_score, k)
        results[f"recall@{k}"] = recall_at_k(y_true, y_score, k)
    results["mrr"] = mrr(y_true, y_score)
    results["map"] = average_precision(y_true, y_score)
    results["n_total"] = int(len(y_true))
    results["n_positive"] = int(y_true.sum())
    return results


def load_test_probabilities(experiment_dir: str) -> Optional[Dict]:
    """Load test labels and predicted probabilities from a saved test_metrics.json.

    The test_metrics.json contains roc_curve.fpr/tpr but not raw probabilities.
    We reconstruct them from the pr_curve (precision, recall at each threshold),
    or fall back to using the confusion matrix to derive approximate counts.

    NOTE: For accurate ranking, we need raw per-sample probabilities.
    The best approach is to have each training script save probabilities.
    We check for a 'test_probabilities.npz' file saved alongside test_metrics.json.
    """
    proba_path = os.path.join(experiment_dir, "test_probabilities.npz")
    if os.path.exists(proba_path):
        data = np.load(proba_path)
        return {"y_true": data["y_true"], "y_score": data["y_score"]}

    # If raw probabilities not saved, we can't do accurate ranking
    return None


def plot_ranking_curves(all_results: Dict[str, Dict], k_values: List[int], save_path: str):
    """Plot Precision@K and Recall@K for all experiments."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    colors = {"Code Only (A)": "#2196F3", "Code+Graph (B)": "#4CAF50",
              "Code+History (C)": "#FF9800", "Code+Graph+History (D)": "#9C27B0"}

    for exp_name, metrics in all_results.items():
        color = colors.get(exp_name, "gray")
        ks = [k for k in k_values if f"precision@{k}" in metrics]
        prec = [metrics[f"precision@{k}"] for k in ks]
        rec = [metrics[f"recall@{k}"] for k in ks]
        ax1.plot(ks, prec, marker="o", label=exp_name, color=color, linewidth=2)
        ax2.plot(ks, rec, marker="s", label=exp_name, color=color, linewidth=2)

    ax1.set_xlabel("K", fontsize=12)
    ax1.set_ylabel("Precision@K", fontsize=12)
    ax1.set_title("Precision@K", fontsize=14, fontweight="bold")
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)

    ax2.set_xlabel("K", fontsize=12)
    ax2.set_ylabel("Recall@K", fontsize=12)
    ax2.set_title("Recall@K", fontsize=14, fontweight="bold")
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)

    plt.suptitle("SkyTrace — Ranking Evaluation", fontsize=16, fontweight="bold")
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"[ranking] Saved plot -> {save_path}")


def main():
    K_VALUES = [5, 10, 20, 50, 100, 200, 500, 1000]

    # Experiment directories and display names
    experiments = [
        ("Code Only (A)",          None,                          "experiments/codebert"),
        ("Code+Graph (B)",         "experiments/code_graph",      "experiments/code_graph"),
        ("Code+History (C)",       "experiments/code_history",    "experiments/code_history"),
        ("Code+Graph+History (D)", "experiments/code_graph_history", "experiments/code_graph_history"),
    ]

    all_results = {}
    all_mrr = {}

    print("SkyTrace — Ranking Evaluation")
    print("=" * 60)

    for exp_name, _, exp_dir in experiments:
        proba_data = load_test_probabilities(exp_dir)
        if proba_data is None:
            print(f"  [{exp_name}] No test_probabilities.npz found in {exp_dir} — skipping")
            print(f"             Run the training script first, or re-run with --save-probabilities")
            continue

        y_true = proba_data["y_true"]
        y_score = proba_data["y_score"]
        metrics = ranking_metrics(y_true, y_score, K_VALUES)
        all_results[exp_name] = metrics
        all_mrr[exp_name] = metrics["mrr"]

        print(f"\n[{exp_name}]")
        print(f"  n_total={metrics['n_total']:,}  n_positive={metrics['n_positive']:,}")
        print(f"  MRR = {metrics['mrr']:.6f}  MAP = {metrics['map']:.6f}")
        for k in K_VALUES:
            if f"precision@{k}" in metrics:
                print(f"  P@{k:<5} = {metrics[f'precision@{k}']:.4f}   R@{k:<5} = {metrics[f'recall@{k}']:.4f}")

    if all_results:
        plot_ranking_curves(all_results, K_VALUES, "reports/ranking_eval.png")
        with open("reports/ranking_eval.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)
        print("\n[done] Saved reports/ranking_eval.json and reports/ranking_eval.png")
    else:
        print("\n[note] No experiment has saved test probabilities yet.")
        print("       Run training scripts first, then re-run ranking_eval.py")
        print("       The training scripts save test_probabilities.npz automatically.")


if __name__ == "__main__":
    main()
