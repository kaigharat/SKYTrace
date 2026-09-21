"""SkyTrace evaluation plots: confusion matrix, ROC curve, PR curve, training curves."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np

# Font fallback
try:
    fm.fontManager.addfont('/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf')
except Exception:
    pass
plt.rcParams['font.sans-serif'] = ['Noto Sans SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def plot_confusion_matrix(cm: Dict[str, int], title: str, out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tn, fp, fn, tp = cm["tn"], cm["fp"], cm["fn"], cm["tp"]
    matrix = np.array([[tn, fp], [fn, tp]])
    fig, ax = plt.subplots(figsize=(5, 4), constrained_layout=True)
    im = ax.imshow(matrix, cmap="Blues")
    for i in range(2):
        for j in range(2):
            color = "white" if matrix[i, j] > matrix.max() * 0.5 else "black"
            ax.text(j, i, f"{matrix[i, j]:,}", ha="center", va="center",
                    color=color, fontsize=14, fontweight="bold")
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["Predicted 0", "Predicted 1"])
    ax.set_yticklabels(["Actual 0", "Actual 1"])
    ax.set_title(title, fontsize=12, fontweight="bold")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"[plots] saved -> {out_path}")


def plot_roc_curve(roc: Dict[str, List[float]], title: str, out_path: str, auc: Optional[float] = None) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 5), constrained_layout=True)
    ax.plot(roc["fpr"], roc["tpr"], color="#c0392b", linewidth=2,
            label=f"ROC (AUC = {auc:.4f})" if auc is not None else "ROC")
    ax.plot([0, 1], [0, 1], color="#7f8c8d", linestyle="--", linewidth=1)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.legend(loc="lower right")
    ax.grid(linestyle="--", alpha=0.4)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"[plots] saved -> {out_path}")


def plot_pr_curve(pr: Dict[str, List[float]], title: str, out_path: str, ap: Optional[float] = None) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 5), constrained_layout=True)
    ax.plot(pr["recall"], pr["precision"], color="#2980b9", linewidth=2,
            label=f"PR (AP = {ap:.4f})" if ap is not None else "PR")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.legend(loc="upper right")
    ax.grid(linestyle="--", alpha=0.4)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"[plots] saved -> {out_path}")


def plot_training_curves(history: List[Dict[str, Any]], out_path: str, title: str = "Training Curves") -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    if not history:
        return
    epochs = [h["epoch"] for h in history]
    train_loss = [h.get("train_loss", 0) for h in history]
    val_f1 = [h.get("val_f1", 0) for h in history]
    val_pr_auc = [h.get("val_pr_auc", 0) or 0 for h in history]
    val_roc_auc = [h.get("val_roc_auc", 0) or 0 for h in history]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    ax1.plot(epochs, train_loss, marker="o", color="#c0392b", label="train loss")
    ax1.set_xlabel("Epoch")
    ax1.set_ylabel("Loss")
    ax1.set_title(f"{title} — Loss")
    ax1.grid(linestyle="--", alpha=0.4)
    ax1.legend()

    ax2.plot(epochs, val_f1, marker="o", color="#2980b9", label="val F1")
    ax2.plot(epochs, val_pr_auc, marker="s", color="#27ae60", label="val PR-AUC")
    ax2.plot(epochs, val_roc_auc, marker="^", color="#8e44ad", label="val ROC-AUC")
    ax2.set_xlabel("Epoch")
    ax2.set_ylabel("Metric")
    ax2.set_title(f"{title} — Validation Metrics")
    ax2.grid(linestyle="--", alpha=0.4)
    ax2.legend()

    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"[plots] saved -> {out_path}")


def save_metrics_report(metrics: Dict[str, Any], out_path: str) -> None:
    """Save metrics as JSON, dropping non-serializable bits."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    # Drop the heavy sample_ids / projects lists before saving
    save = {k: v for k, v in metrics.items() if k not in ("sample_ids", "projects")}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(save, f, indent=2, default=str)
    print(f"[metrics] saved -> {out_path}")
