"""
Analysis & Graphs — Project Hail Mary Simulation
Generates quantitative analysis plots required by the assessment brief.
Run this after running batch simulations.
"""

import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use("Agg")   # headless backend for file output
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from simulation import BatchRunner
from config import *


def run_analysis(n_runs=20, output_dir="analysis_output"):
    """Run n_runs simulations and generate all analysis graphs."""
    os.makedirs(output_dir, exist_ok=True)

    print(f"Running {n_runs} simulations for analysis...")
    seeds = list(range(1000, 1000 + n_runs))
    runner = BatchRunner(n_runs=n_runs, verbose=False)
    results = runner.run_all(seeds=seeds)
    stats = runner.print_report()

    # ── 1. Knowledge Score Progression ────────────────────────────────
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.patch.set_facecolor("#0d1117")
    for ax in axes.flat:
        ax.set_facecolor("#161b22")
        ax.tick_params(colors="#8b949e")
        ax.xaxis.label.set_color("#c9d1d9")
        ax.yaxis.label.set_color("#c9d1d9")
        ax.title.set_color("#58a6ff")
        for spine in ax.spines.values():
            spine.set_color("#30363d")

    # Plot 1: Knowledge score progression across runs
    ax = axes[0, 0]
    for r in results:
        if r.knowledge_history:
            x = [i * 5 for i in range(len(r.knowledge_history))]
            color = "#00ff88" if r.cause_of_end == "mission_complete" else "#8b949e"
            ax.plot(x, r.knowledge_history, alpha=0.4, linewidth=1, color=color)
    # Mean line
    max_len = max((len(r.knowledge_history) for r in results if r.knowledge_history), default=0)
    if max_len > 0:
        padded = []
        for r in results:
            h = r.knowledge_history
            padded.append(h + [h[-1]] * (max_len - len(h)) if h else [0] * max_len)
        mean_k = np.mean(padded, axis=0)
        ax.plot([i * 5 for i in range(max_len)], mean_k,
                color="#58a6ff", linewidth=2.5, label="Mean", zorder=5)
    ax.set_title("Knowledge Score Progression")
    ax.set_xlabel("Turn")
    ax.set_ylabel("Knowledge Score")
    ax.legend(facecolor="#161b22", labelcolor="#c9d1d9")
    completed_patch = mpatches.Patch(color="#00ff88", alpha=0.5, label="Mission Complete")
    failed_patch = mpatches.Patch(color="#8b949e", alpha=0.5, label="Mission Failed")
    ax.legend(handles=[completed_patch, failed_patch],
              facecolor="#161b22", labelcolor="#c9d1d9")

    # Plot 2: Astrophage spread over time
    ax = axes[0, 1]
    for r in results:
        if r.astrophage_history:
            x = [i * 5 for i in range(len(r.astrophage_history))]
            ax.plot(x, r.astrophage_history, alpha=0.35, linewidth=1, color="#8B0000")
    if max_len > 0:
        padded_aph = []
        for r in results:
            h = r.astrophage_history
            if h:
                padded_aph.append(h + [h[-1]] * (max_len - len(h)))
        if padded_aph:
            mean_aph = np.mean(padded_aph, axis=0)
            ax.plot([i * 5 for i in range(len(mean_aph))], mean_aph,
                    color="#ff4444", linewidth=2.5, label="Mean Astrophage")
    ax.set_title("Astrophage Spread Over Time")
    ax.set_xlabel("Turn")
    ax.set_ylabel("Astrophage Cells")
    ax.legend(facecolor="#161b22", labelcolor="#c9d1d9")

    # Plot 3: Mission outcomes pie chart
    ax = axes[0, 2]
    causes = stats["cause_of_end_breakdown"]
    labels = list(causes.keys())
    sizes = list(causes.values())
    colors_pie = ["#00ff88", "#f85149", "#ffd700", "#8b949e"]
    explode = [0.05] * len(labels)
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors_pie[:len(labels)],
        autopct="%1.1f%%", explode=explode,
        textprops={"color": "#c9d1d9", "fontsize": 8}
    )
    for at in autotexts:
        at.set_color("#0d1117")
        at.set_fontweight("bold")
    ax.set_title("Simulation End Conditions")

    # Plot 4: Final knowledge distribution
    ax = axes[1, 0]
    k_vals = [r.knowledge_final for r in results]
    ax.hist(k_vals, bins=10, color="#58a6ff", alpha=0.8, edgecolor="#30363d")
    ax.axvline(np.mean(k_vals), color="#ffd700", linewidth=2, linestyle="--",
               label=f"Mean: {np.mean(k_vals):.1f}")
    ax.set_title("Final Knowledge Score Distribution")
    ax.set_xlabel("Knowledge Score")
    ax.set_ylabel("Frequency")
    ax.legend(facecolor="#161b22", labelcolor="#c9d1d9")

    # Plot 5: Experiments and success rate scatter
    ax = axes[1, 1]
    exp_totals = [r.experiments_total for r in results]
    exp_rates = [(r.experiments_success / max(1, r.experiments_total)) * 100 for r in results]
    colors_scatter = ["#00ff88" if r.taumoeba_bred else "#8b949e" for r in results]
    ax.scatter(exp_totals, exp_rates, c=colors_scatter, alpha=0.8, s=60, edgecolors="#30363d")
    ax.set_title("Experiments vs Success Rate")
    ax.set_xlabel("Total Experiments")
    ax.set_ylabel("Success Rate (%)")
    bred_patch = mpatches.Patch(color="#00ff88", label="Taumoeba bred")
    not_bred_patch = mpatches.Patch(color="#8b949e", label="Not bred")
    ax.legend(handles=[bred_patch, not_bred_patch],
              facecolor="#161b22", labelcolor="#c9d1d9")

    # Plot 6: Rocky trust level vs mission score
    ax = axes[1, 2]
    trust_levels = [r.trust_reached for r in results]
    mission_scores = [r.mission_score for r in results]
    ax.scatter(trust_levels, mission_scores, c="#ff6b35", alpha=0.8, s=60)
    # Add jitter for readability
    jitter = np.random.uniform(-0.1, 0.1, size=len(trust_levels))
    ax.scatter(np.array(trust_levels) + jitter, mission_scores,
               c="#ff6b35", alpha=0.7, s=50)
    ax.set_title("Rocky Trust Level vs Mission Score")
    ax.set_xlabel("Rocky Trust Level (0-3)")
    ax.set_ylabel("Mission Success Score")
    ax.set_xticks([0, 1, 2, 3])
    ax.set_xticklabels(["Strangers", "Colleagues", "Friends", "Allies"],
                       fontsize=8)

    plt.suptitle("Project Hail Mary — Multi-Agent Simulation Analysis\n"
                 f"(n={n_runs} runs, max {MAX_TURNS} turns each)",
                 color="#58a6ff", fontsize=13, y=1.01)
    plt.tight_layout()

    out_path = os.path.join(output_dir, "simulation_analysis.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight",
                facecolor="#0d1117", edgecolor="none")
    plt.close()
    print(f"\nAnalysis graphs saved: {out_path}")

    # ── 2. Save raw results as CSV ─────────────────────────────────────
    csv_path = os.path.join(output_dir, "simulation_results.csv")
    import csv
    fieldnames = list(results[0].to_dict().keys())
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r.to_dict())
    print(f"Raw results saved:    {csv_path}")

    return stats, out_path


if __name__ == "__main__":
    run_analysis(n_runs=20, output_dir="analysis_output")
