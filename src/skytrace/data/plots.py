"""Generate dataset analysis plots.

Six plots required by the project spec:
    1. Class distribution (vulnerable vs non-vulnerable)
    2. CWE distribution (top-N)
    3. Samples per project (top-N)
    4. Function length distribution (log-scale histogram)
    5. Missing-value summary (bar chart per column)
    6. Duplicate summary (bar chart by category)

All plots use Matplotlib. Chinese font fallback is configured in case the
project is later extended with Chinese annotations.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Font fallback — per project rule 7.
try:
    fm.fontManager.addfont('/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf')
except Exception:
    pass
try:
    fm.fontManager.addfont('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
except Exception:
    pass
plt.rcParams['font.sans-serif'] = ['Noto Sans SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# SkyTrace colour palette (deliberately restrained, accessibility-friendly)
COLOR_VULN = "#c0392b"
COLOR_CLEAN = "#2980b9"
COLOR_NEUTRAL = "#7f8c8d"
COLOR_ACCENT = "#27ae60"


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _save(fig, path: str) -> None:
    fig.savefig(path, dpi=120, bbox_inches=None)
    plt.close(fig)
    print(f"[plots] saved -> {path}")


def plot_class_distribution(df: pd.DataFrame, out_path: str) -> None:
    _ensure_dir(os.path.dirname(out_path))
    counts = df["label"].value_counts(dropna=False).to_dict()
    labels = []
    sizes = []
    colors = []
    for k, v in counts.items():
        if pd.isna(k):
            labels.append("Missing")
            colors.append(COLOR_NEUTRAL)
        elif int(k) == 1:
            labels.append("Vulnerable (1)")
            colors.append(COLOR_VULN)
        else:
            labels.append("Non-vulnerable (0)")
            colors.append(COLOR_CLEAN)
        sizes.append(int(v))

    fig, ax = plt.subplots(figsize=(7, 5), constrained_layout=True)
    bars = ax.bar(labels, sizes, color=colors, edgecolor="black", linewidth=0.5)
    for b, s in zip(bars, sizes):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                f"{s:,}\n({100.0 * s / sum(sizes):.2f}%)",
                ha="center", va="bottom", fontsize=10)
    ax.set_title("SkyTrace / DiverseVul — Class Distribution", fontsize=13, fontweight="bold")
    ax.set_ylabel("Number of samples")
    ax.set_ylim(0, max(sizes) * 1.15)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    _save(fig, out_path)


def plot_cwe_distribution(df: pd.DataFrame, out_path: str, top_n: int = 25) -> None:
    _ensure_dir(os.path.dirname(out_path))
    cwe_series = df["cwe"].dropna() if "cwe" in df.columns else pd.Series(dtype="string")
    cwe_exploded = cwe_series.str.split(",").explode().str.strip()
    cwe_exploded = cwe_exploded[cwe_exploded != ""]
    top = cwe_exploded.value_counts().head(top_n)

    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    ax.barh(top.index[::-1], top.values[::-1], color=COLOR_VULN, edgecolor="black", linewidth=0.4)
    ax.set_title(f"SkyTrace / DiverseVul — Top-{top_n} CWE Categories", fontsize=13, fontweight="bold")
    ax.set_xlabel("Number of samples")
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    _save(fig, out_path)


def plot_samples_per_project(df: pd.DataFrame, out_path: str, top_n: int = 25) -> None:
    _ensure_dir(os.path.dirname(out_path))
    if "project" not in df.columns:
        return
    proj = df["project"].value_counts(dropna=False).head(top_n)
    labels = [str(p)[:25] for p in proj.index]

    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    ax.barh(labels[::-1], proj.values[::-1], color=COLOR_CLEAN, edgecolor="black", linewidth=0.4)
    ax.set_title(f"SkyTrace / DiverseVul — Top-{top_n} Projects by Sample Count", fontsize=13, fontweight="bold")
    ax.set_xlabel("Number of samples")
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    _save(fig, out_path)


def plot_function_length_distribution(df: pd.DataFrame, out_path: str) -> None:
    _ensure_dir(os.path.dirname(out_path))
    code_lens = df["function_code"].astype("string").fillna("").apply(len)
    code_lens = code_lens[code_lens > 0]

    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    # Use log-spaced bins
    bins = np.logspace(np.log10(max(1, code_lens.min())),
                       np.log10(code_lens.max() + 1), 60)
    ax.hist(code_lens, bins=bins, color=COLOR_ACCENT, edgecolor="black", linewidth=0.3)
    ax.set_xscale("log")
    ax.set_title("SkyTrace / DiverseVul — Function Length Distribution", fontsize=13, fontweight="bold")
    ax.set_xlabel("Function length (chars, log scale)")
    ax.set_ylabel("Number of samples")
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    # Annotate median / mean
    med = code_lens.median()
    mean = code_lens.mean()
    ax.axvline(med, color=COLOR_VULN, linestyle="--", linewidth=1.5, label=f"median = {med:.0f}")
    ax.axvline(mean, color="black", linestyle=":", linewidth=1.5, label=f"mean = {mean:.0f}")
    ax.legend(loc="upper right")
    _save(fig, out_path)


def plot_missing_values(audit_report: Dict[str, Any], out_path: str) -> None:
    _ensure_dir(os.path.dirname(out_path))
    mv = audit_report.get("missing_values", {})
    if not mv:
        return
    cols = list(mv.keys())
    pcts = [mv[c]["pct_missing"] for c in cols]
    # Sort descending by pct
    order = np.argsort(pcts)[::-1]
    cols = [cols[i] for i in order]
    pcts = [pcts[i] for i in order]

    fig, ax = plt.subplots(figsize=(9, 6), constrained_layout=True)
    bars = ax.barh(cols[::-1], pcts[::-1], color=COLOR_NEUTRAL, edgecolor="black", linewidth=0.4)
    for b, p in zip(bars, pcts[::-1]):
        ax.text(b.get_width() + 0.5, b.get_y() + b.get_height() / 2,
                f"{p:.2f}%", va="center", fontsize=9)
    ax.set_title("SkyTrace / DiverseVul — Missing-Value Summary (per column)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Percentage missing (%)")
    ax.set_xlim(0, max(105, max(pcts) + 5))
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    _save(fig, out_path)


def plot_duplicate_summary(audit_report: Dict[str, Any], out_path: str) -> None:
    _ensure_dir(os.path.dirname(out_path))
    d = audit_report.get("duplicates", {})
    categories = []
    counts = []
    for k, v in d.items():
        if isinstance(v, dict) and "n_rows_involved" in v:
            categories.append(k.replace("_", " ").title())
            counts.append(int(v["n_rows_involved"]))

    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    bars = ax.bar(categories, counts, color=COLOR_VULN, edgecolor="black", linewidth=0.4)
    for b, c in zip(bars, counts):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                f"{c:,}", ha="center", va="bottom", fontsize=10)
    ax.set_title("SkyTrace / DiverseVul — Duplicate Summary", fontsize=13, fontweight="bold")
    ax.set_ylabel("Number of rows involved")
    max_c = max(counts) if counts else 1
    ax.set_ylim(0, max(max_c * 1.15, 1))
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    plt.xticks(rotation=15, ha="right")
    _save(fig, out_path)


def generate_all_plots(
    df: pd.DataFrame,
    audit_report: Dict[str, Any],
    out_dir: str,
) -> Dict[str, str]:
    """Generate all 6 required plots. Returns path dict."""
    _ensure_dir(out_dir)
    paths = {
        "class_distribution": os.path.join(out_dir, "01_class_distribution.png"),
        "cwe_distribution": os.path.join(out_dir, "02_cwe_distribution.png"),
        "samples_per_project": os.path.join(out_dir, "03_samples_per_project.png"),
        "function_length": os.path.join(out_dir, "04_function_length_distribution.png"),
        "missing_values": os.path.join(out_dir, "05_missing_values.png"),
        "duplicate_summary": os.path.join(out_dir, "06_duplicate_summary.png"),
    }
    plot_class_distribution(df, paths["class_distribution"])
    plot_cwe_distribution(df, paths["cwe_distribution"])
    plot_samples_per_project(df, paths["samples_per_project"])
    plot_function_length_distribution(df, paths["function_length"])
    plot_missing_values(audit_report, paths["missing_values"])
    plot_duplicate_summary(audit_report, paths["duplicate_summary"])
    return paths
