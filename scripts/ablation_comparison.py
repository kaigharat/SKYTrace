"""SkyTrace — Ablation Study Comparison Script.

Usage:
    python scripts/ablation_comparison.py

Reads test_metrics.json from all four experiment directories and generates:
    1. A clean ablation comparison table (console + JSON)
    2. A bar chart comparing key metrics across experiments
    3. A combined ROC curve plot
    4. A combined PR curve plot
    5. reports/ablation_results.md — research report section

Research questions answered:
    RQ1: How effective is code-only for vulnerability prediction?
    RQ2: Does graph information improve prediction?
    RQ3: Does history information improve prediction?
    RQ4: Does combining all modalities outperform individual ones?
    RQ5: Which modality contributes the most?
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "..", "src")
sys.path.insert(0, _SRC)


EXPERIMENTS = [
    {
        "name": "Exp A: Code Only",
        "short": "Code Only",
        "dir": "experiments/codebert",
        "ckpt": "models/checkpoints/codebert_baseline",
        "color": "#2196F3",
        "marker": "o",
    },
    {
        "name": "Exp B: Code + Graph",
        "short": "Code+Graph",
        "dir": "experiments/code_graph",
        "ckpt": "models/checkpoints/code_graph",
        "color": "#4CAF50",
        "marker": "s",
    },
    {
        "name": "Exp C: Code + History",
        "short": "Code+History",
        "dir": "experiments/code_history",
        "ckpt": "models/checkpoints/code_history",
        "color": "#FF9800",
        "marker": "^",
    },
    {
        "name": "Exp D: Code+Graph+History",
        "short": "Code+Graph+Hist",
        "dir": "experiments/code_graph_history",
        "ckpt": "models/checkpoints/code_graph_history",
        "color": "#9C27B0",
        "marker": "D",
    },
]

KEY_METRICS = ["precision", "recall", "f1", "roc_auc", "pr_auc"]


def load_test_metrics(exp_dir: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(exp_dir, "test_metrics.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_experiment_json(exp_dir: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(exp_dir, "experiment.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def plot_metric_bars(results: Dict, metrics: list, save_path: str):
    """Bar chart comparing experiments across metrics."""
    fig, axes = plt.subplots(1, len(metrics), figsize=(4 * len(metrics), 6))
    if len(metrics) == 1:
        axes = [axes]

    for ax, metric in zip(axes, metrics):
        names = []
        values = []
        colors = []
        for exp in EXPERIMENTS:
            r = results.get(exp["name"])
            if r is None:
                continue
            v = r.get(metric)
            if v is None:
                continue
            names.append(exp["short"])
            values.append(float(v))
            colors.append(exp["color"])

        bars = ax.bar(range(len(names)), values, color=colors, alpha=0.85, width=0.6)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=15, ha="right", fontsize=9)
        ax.set_title(metric.upper().replace("_", "-"), fontsize=12, fontweight="bold")
        ax.set_ylim(0, max(values) * 1.2 if values else 1.0)
        ax.grid(axis="y", alpha=0.3)
        # Value labels
        for bar, v in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.002,
                    f"{v:.4f}", ha="center", va="bottom", fontsize=8, fontweight="bold")

    plt.suptitle("SkyTrace — Ablation Study", fontsize=16, fontweight="bold", y=1.02)
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"[ablation] Bar chart saved -> {save_path}")


def plot_combined_roc(results: Dict, save_path: str):
    """Combined ROC curve for all experiments."""
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4, label="Random")

    for exp in EXPERIMENTS:
        r = results.get(exp["name"])
        if r is None or r.get("roc_curve") is None:
            continue
        roc = r["roc_curve"]
        auc = r.get("roc_auc", 0)
        ax.plot(roc["fpr"], roc["tpr"], color=exp["color"], linewidth=2,
                marker=exp["marker"], markevery=50, markersize=6,
                label=f"{exp['short']}  (AUC={auc:.4f})")

    ax.set_xlabel("False Positive Rate", fontsize=12)
    ax.set_ylabel("True Positive Rate", fontsize=12)
    ax.set_title("SkyTrace — Ablation ROC Curves", fontsize=14, fontweight="bold")
    ax.legend(fontsize=10, loc="lower right")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"[ablation] Combined ROC saved -> {save_path}")


def plot_combined_pr(results: Dict, save_path: str):
    """Combined PR curve for all experiments."""
    fig, ax = plt.subplots(figsize=(8, 7))

    for exp in EXPERIMENTS:
        r = results.get(exp["name"])
        if r is None or r.get("pr_curve") is None:
            continue
        pr = r["pr_curve"]
        ap = r.get("pr_auc", 0)
        ax.plot(pr["recall"], pr["precision"], color=exp["color"], linewidth=2,
                marker=exp["marker"], markevery=50, markersize=6,
                label=f"{exp['short']}  (AP={ap:.4f})")

    ax.set_xlabel("Recall", fontsize=12)
    ax.set_ylabel("Precision", fontsize=12)
    ax.set_title("SkyTrace — Ablation PR Curves", fontsize=14, fontweight="bold")
    ax.legend(fontsize=10, loc="upper right")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"[ablation] Combined PR saved -> {save_path}")


def format_table_row(exp_name: str, r: Dict, metrics: list) -> str:
    vals = []
    for m in metrics:
        v = r.get(m)
        vals.append(f"{v:.4f}" if v is not None else "  N/A")
    name_col = f"{exp_name:<28}"
    return f"| {name_col} | " + " | ".join(f"{v:>10}" for v in vals) + " |"


def generate_report(results: Dict, save_path: str):
    """Write a markdown report section for the ablation study."""
    metrics = ["precision", "recall", "f1", "roc_auc", "pr_auc"]
    header = "| Model                        | " + " | ".join(f"{m:>10}" for m in metrics) + " |"
    sep = "|------------------------------|" + "|".join(["----------:"] * len(metrics)) + "|"

    rows = [header, sep]
    for exp in EXPERIMENTS:
        r = results.get(exp["name"])
        if r is None:
            r = {m: None for m in metrics}
        rows.append(format_table_row(exp["name"], r, metrics))

    table = "\n".join(rows)

    best_roc = max(
        ((exp["name"], results[exp["name"]].get("roc_auc", 0))
         for exp in EXPERIMENTS if exp["name"] in results),
        key=lambda x: x[1], default=("N/A", 0)
    )
    best_f1 = max(
        ((exp["name"], results[exp["name"]].get("f1", 0))
         for exp in EXPERIMENTS if exp["name"] in results),
        key=lambda x: x[1], default=("N/A", 0)
    )

    report = f"""# SkyTrace — Ablation Study Results

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**Dataset:** DiverseVul — Test set: 33,352 samples (1,795 vulnerable)  
**Threshold:** Selected on validation set (never test)  

---

## Ablation Comparison Table

{table}

---

## Key Findings

- **Best ROC-AUC:** {best_roc[0]} — {best_roc[1]:.4f}
- **Best F1:** {best_f1[0]} — {best_f1[1]:.4f}

### RQ2: Does graph information improve over code-only?
"""
    if "Exp A: Code Only" in results and "Exp B: Code + Graph" in results:
        a_roc = results["Exp A: Code Only"].get("roc_auc", 0)
        b_roc = results["Exp B: Code + Graph"].get("roc_auc", 0)
        delta = b_roc - a_roc
        direction = "improves" if delta > 0 else "does not improve"
        report += f"Code+Graph {direction} over Code Only by ΔROC-AUC={delta:+.4f}\n"
    else:
        report += "Awaiting Experiment B results.\n"

    report += "\n### RQ3: Does history information improve over code-only?\n"
    if "Exp A: Code Only" in results and "Exp C: Code + History" in results:
        a_roc = results["Exp A: Code Only"].get("roc_auc", 0)
        c_roc = results["Exp C: Code + History"].get("roc_auc", 0)
        delta = c_roc - a_roc
        direction = "improves" if delta > 0 else "does not improve"
        report += f"Code+History {direction} over Code Only by ΔROC-AUC={delta:+.4f}\n"
    else:
        report += "Awaiting Experiment C results.\n"

    report += "\n### RQ4: Does the full multimodal model outperform individual modalities?\n"
    if "Exp D: Code+Graph+History" in results:
        d_roc = results["Exp D: Code+Graph+History"].get("roc_auc", 0)
        report += f"Full model ROC-AUC: {d_roc:.4f}\n"
    else:
        report += "Awaiting Experiment D results.\n"

    report += "\n---\n\n## History Feature Limitation Note\n\n"
    report += (
        "The history features used in Experiments C and D are **proxy features** derived from "
        "columns already present in DiverseVul: commit_id, project, cwe, function_code, "
        "function_name. The original schema columns "
        "(prior_defect_count, prior_vulnerability_count, co_change_frequency, file_volatility) "
        "are 100% NULL in the current dataset — they require external git-mining which is "
        "handled by the backend infrastructure (Kaivalya's module). When the backend is available, "
        "these proxy features should be replaced with the actual history signals for a stronger comparison.\n"
    )

    os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else ".", exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[ablation] Report saved -> {save_path}")


def main():
    print("SkyTrace — Ablation Study Comparison")
    print("=" * 60)

    results = {}
    for exp in EXPERIMENTS:
        r = load_test_metrics(exp["dir"])
        if r is None:
            print(f"  [{exp['name']}] test_metrics.json NOT FOUND — experiment not run yet")
        else:
            results[exp["name"]] = r
            print(f"  [{exp['name']}] loaded  ROC-AUC={r.get('roc_auc', 'N/A'):.4f}  F1={r.get('f1', 'N/A'):.4f}")

    if not results:
        print("\nNo experiments have been run yet. Run training scripts first.")
        return

    print("\n\nABLATION TABLE")
    metrics_display = ["precision", "recall", "f1", "roc_auc", "pr_auc"]
    print(f"{'Model':<32} " + "  ".join(f"{m:>10}" for m in metrics_display))
    print("-" * 90)
    for exp in EXPERIMENTS:
        r = results.get(exp["name"], {})
        vals = [f"{r.get(m, 0):.4f}" if r.get(m) is not None else "    N/A" for m in metrics_display]
        print(f"{exp['name']:<32} " + "  ".join(f"{v:>10}" for v in vals))

    # Save comparison JSON
    os.makedirs("reports", exist_ok=True)
    with open("reports/ablation_results.json", "w", encoding="utf-8") as f:
        json.dump({k: {m: v for m, v in r.items() if m not in ("roc_curve", "pr_curve")}
                   for k, r in results.items()}, f, indent=2, default=str)
    print("\n[done] Saved reports/ablation_results.json")

    # Plots
    plot_metric_bars(results, ["f1", "roc_auc", "pr_auc"], "reports/ablation_bars.png")
    plot_combined_roc(results, "reports/ablation_roc.png")
    plot_combined_pr(results, "reports/ablation_pr.png")

    # Markdown report
    generate_report(results, "reports/ablation_results.md")


if __name__ == "__main__":
    main()
