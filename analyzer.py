"""
TRI·TFM v3.0 — Results Analyzer
Usage:
    python analyzer.py --csv results/tri_tfm_gemini-2.5-flash_20260306_1200.csv
    python analyzer.py --csv results/latest.csv --output-dir reports
Generates Markdown report + PNG plots in reports/ directory.
"""

import os, sys
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import argparse
import math
from datetime import datetime

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from config import (
    POSITIVE_AXES, BAL_WEIGHTS, BAL_SIGMA_CEIL,
    STABLE_THRESHOLD, DRIFTING_THRESHOLD,
)


def auto_observe(df):
    obs = []
    n = len(df)

    for axis in POSITIVE_AXES:
        if axis in df.columns and (df[axis] >= 0.95).sum() / n >= 0.5:
            obs.append(("CRITICAL", f"Ceiling on {axis}: {(df[axis] >= 0.95).sum()}/{n} scored >= 0.95"))

    for axis in POSITIVE_AXES + ["B", "bal"]:
        if axis in df.columns:
            s = df[axis].std()
            if s > 0.15:
                obs.append(("HIGH", f"High variance {axis}: sigma={s:.3f}"))

    if "category" in df.columns:
        ph = df[df["category"].isin(["philosophical", "ethical"])]
        fa = df[df["category"] == "factual"]
        if len(ph) >= 2 and ph["F"].mean() > 0.55:
            obs.append(("CRITICAL", f"F inflation philosophical: mean={ph['F'].mean():.2f} (expect 0.20-0.45)"))
        if len(fa) >= 2 and fa["F"].mean() < 0.70:
            obs.append(("HIGH", f"F too low factual: mean={fa['F'].mean():.2f} (expect >= 0.70)"))
        if len(fa) >= 2 and len(ph) >= 2:
            gap = fa["F"].mean() - ph["F"].mean()
            if gap < 0.20:
                obs.append(("HIGH", f"Weak F discrimination: delta_F={gap:.2f} (expect >= 0.30)"))

    stable = (df["bal"] >= STABLE_THRESHOLD).sum()
    drift = ((df["bal"] >= DRIFTING_THRESHOLD) & (df["bal"] < STABLE_THRESHOLD)).sum()
    dom = (df["bal"] < DRIFTING_THRESHOLD).sum()
    obs.append(("INFO", f"Bal: STABLE={stable} DRIFTING={drift} DOM={dom} mean={df['bal'].mean():.3f}"))

    return obs


def plot_efnm_histograms(df, out_path):
    fig, axes_arr = plt.subplots(1, 4, figsize=(16, 4), sharey=True)
    colors = {"E": "#e74c3c", "F": "#3498db", "N": "#2ecc71", "M": "#9b59b6"}
    for ax, axis in zip(axes_arr, POSITIVE_AXES):
        if axis in df.columns:
            ax.hist(df[axis], bins=20, range=(0, 1), color=colors[axis], alpha=0.8, edgecolor="white")
        ax.set_title(f"{axis} Distribution")
        ax.set_xlabel(axis)
        ax.set_xlim(0, 1)
    axes_arr[0].set_ylabel("Count")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_balance_histogram(df, out_path):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(df["bal"], bins=20, range=(0, 1), color="#8e44ad", alpha=0.8, edgecolor="white")
    ax.axvline(x=STABLE_THRESHOLD, color="green", linestyle="--", label=f"STABLE ({STABLE_THRESHOLD})")
    ax.axvline(x=DRIFTING_THRESHOLD, color="orange", linestyle="--", label=f"DRIFTING ({DRIFTING_THRESHOLD})")
    ax.set_title("Balance Distribution")
    ax.set_xlabel("Bal")
    ax.set_ylabel("Count")
    ax.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_m_vs_f(df, out_path):
    fig, ax = plt.subplots(figsize=(8, 6))
    if "category" in df.columns:
        categories = df["category"].unique()
        cmap = plt.cm.get_cmap("tab10", len(categories))
        for i, cat in enumerate(categories):
            sub = df[df["category"] == cat]
            ax.scatter(sub["F"], sub["M"], label=cat, alpha=0.7, s=50, color=cmap(i))
        ax.legend(title="Category", fontsize=8)
    else:
        ax.scatter(df["F"], df["M"], alpha=0.7, s=50, color="#8e44ad")
    ax.axhline(y=0.5, color="gray", linestyle=":", alpha=0.5)
    ax.axvline(x=0.5, color="gray", linestyle=":", alpha=0.5)
    ax.set_xlabel("F (Epistemic Grounding)")
    ax.set_ylabel("M (Explanatory Depth)")
    ax.set_title("M vs F Scatter")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_e_vs_f(df, out_path):
    fig, ax = plt.subplots(figsize=(8, 6))
    if "category" in df.columns:
        categories = df["category"].unique()
        cmap = plt.cm.get_cmap("tab10", len(categories))
        for i, cat in enumerate(categories):
            sub = df[df["category"] == cat]
            ax.scatter(sub["F"], sub["E"], label=cat, alpha=0.7, s=50, color=cmap(i))
        ax.legend(title="Category", fontsize=8)
    else:
        ax.scatter(df["F"], df["E"], alpha=0.7, s=50, color="#e74c3c")
    ax.set_xlabel("F (Epistemic Grounding)")
    ax.set_ylabel("E (Emotion)")
    ax.set_title("E vs F Scatter")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_category_bars(df, out_path):
    if "category" not in df.columns or df["category"].nunique() <= 1:
        return False
    means = df.groupby("category")[POSITIVE_AXES].mean()
    means.plot(kind="bar", figsize=(10, 5), width=0.7, edgecolor="white")
    plt.title("Mean Axes by Category")
    plt.ylabel("Score")
    plt.ylim(0, 1)
    plt.xticks(rotation=45, ha="right")
    plt.legend(title="Axis")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    return True


def generate_report(df, plots_prefix, report_path):
    lines = [
        "# TRI-TFM v3.0 Analysis Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Measurements: {len(df)}",
    ]

    if "model" in df.columns:
        lines.append(f"Models: {', '.join(df['model'].unique())}")
    lines.append("")

    # Summary
    lines.append("## Summary Statistics")
    lines.append("| Axis | Mean | Std | Min | Max |")
    lines.append("|------|------|-----|-----|-----|")
    for a in POSITIVE_AXES + ["B", "bal"]:
        if a in df.columns:
            lines.append(f"| {a} | {df[a].mean():.3f} | {df[a].std():.3f} | {df[a].min():.3f} | {df[a].max():.3f} |")
    lines.append("")

    # Status
    if "status" in df.columns:
        lines.append("## Balance Status")
        for s in ["STABLE", "DRIFTING"]:
            cnt = (df["status"] == s).sum()
            lines.append(f"- {s}: {cnt} ({cnt / len(df) * 100:.0f}%)")
        dom_cnt = (~df["status"].isin(["STABLE", "DRIFTING"])).sum()
        lines.append(f"- DOM: {dom_cnt} ({dom_cnt / len(df) * 100:.0f}%)")
        lines.append("")

    # By category
    if "category" in df.columns and df["category"].nunique() > 1:
        lines.append("## By Category")
        lines.append("| Category | E | F | N | M | B | Bal | n |")
        lines.append("|----------|---|---|---|---|---|-----|---|")
        for cat, g in df.groupby("category"):
            lines.append(
                f"| {cat} | {g['E'].mean():.2f} | {g['F'].mean():.2f} | {g['N'].mean():.2f} | "
                f"{g['M'].mean():.2f} | {g['B'].mean():+.2f} | {g['bal'].mean():.3f} | {len(g)} |")
        lines.append("")

    # Variance per prompt (if repeats)
    if "repeat" in df.columns and df.groupby("prompt").size().max() > 1:
        lines.append("## Variance (Repeated Prompts)")
        lines.append("| Prompt | n | sigma_E | sigma_F | sigma_N | sigma_M | sigma_Bal |")
        lines.append("|--------|---|---------|---------|---------|---------|-----------|")
        for prompt, g in df.groupby("prompt"):
            if len(g) > 1:
                lines.append(
                    f"| {prompt[:50]} | {len(g)} | {g['E'].std():.3f} | {g['F'].std():.3f} | "
                    f"{g['N'].std():.3f} | {g['M'].std():.3f} | {g['bal'].std():.3f} |")
        lines.append("")

    # Plots
    lines.append("## Plots")
    lines.append(f"![E/F/N/M Histograms]({plots_prefix}_efnm_hist.png)")
    lines.append(f"![Balance Distribution]({plots_prefix}_bal_hist.png)")
    lines.append(f"![M vs F Scatter]({plots_prefix}_m_vs_f.png)")
    lines.append(f"![E vs F Scatter]({plots_prefix}_e_vs_f.png)")
    if "category" in df.columns and df["category"].nunique() > 1:
        lines.append(f"![Category Bars]({plots_prefix}_category_bars.png)")
    lines.append("")

    # Observations
    obs = auto_observe(df)
    if obs:
        lines.append("## Auto-Observations")
        for sev, txt in obs:
            lines.append(f"- **{sev}**: {txt}")
        lines.append("")

    report = "\n".join(lines)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    return report


def main():
    parser = argparse.ArgumentParser(description="TRI-TFM v3.0 Results Analyzer")
    parser.add_argument("--csv", required=True, help="Results CSV from experiment_runner.py")
    parser.add_argument("--output-dir", default="reports", help="Output directory for report and plots")
    args = parser.parse_args()

    df = pd.read_csv(args.csv, encoding="utf-8")
    for c in POSITIVE_AXES + ["B", "bal"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    print(f"TRI-TFM v3.0 Analyzer")
    print(f"  Input: {args.csv}")
    print(f"  Rows: {len(df)}")
    print()

    os.makedirs(args.output_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"tri_tfm_{ts}"
    plots_dir = args.output_dir
    plots_prefix = prefix

    # Generate plots
    print("  Generating plots...")
    plot_efnm_histograms(df, os.path.join(plots_dir, f"{prefix}_efnm_hist.png"))
    plot_balance_histogram(df, os.path.join(plots_dir, f"{prefix}_bal_hist.png"))
    if "M" in df.columns and "F" in df.columns:
        plot_m_vs_f(df, os.path.join(plots_dir, f"{prefix}_m_vs_f.png"))
    if "E" in df.columns and "F" in df.columns:
        plot_e_vs_f(df, os.path.join(plots_dir, f"{prefix}_e_vs_f.png"))
    if "category" in df.columns:
        plot_category_bars(df, os.path.join(plots_dir, f"{prefix}_category_bars.png"))

    # Generate report
    report_path = os.path.join(args.output_dir, f"{prefix}_report.md")
    print("  Generating report...")
    generate_report(df, plots_prefix, report_path)

    print(f"\n  Report: {report_path}")
    print(f"  Plots:  {plots_dir}/{prefix}_*.png")
    print("  Done.")


if __name__ == "__main__":
    main()
