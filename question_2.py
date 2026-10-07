#!/usr/bin/env python3
"""Question 2: plot Pacers four factors vs opponents and league averages."""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FACTORS = {
    "eFG%": ("efg_pct", "opp_efg_pct", "eFG%"),
    "OREB%": ("oreb_pct", "opp_oreb_pct", "OREB%"),
    "TOV%": ("tov_pct", "opp_tov_pct", "TOV%"),
    "FTM Rate": ("ftm_rate", "oftm_rate", "FTM rate"),
}

def auc_binary(scores: pd.Series, wins: pd.Series) -> float:
    """AUC for a one-dimensional score, with ties receiving half credit."""
    y = wins.astype(int).to_numpy()
    s = scores.to_numpy(dtype=float)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    return float((pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean())

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=Path("."))
    ap.add_argument("--output-dir", type=Path, default=Path("."))
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    games = pd.read_csv(args.data_dir / "pacers_games_four_factors.csv", encoding="utf-8-sig")
    league = pd.read_csv(args.data_dir / "league_avg_four_factors.csv", encoding="utf-8-sig").iloc[0]
    games["win"] = games["win"].astype(str).str.upper().eq("TRUE")
    games["game_date"] = pd.to_datetime(games["game_date"])
    games = games.sort_values("game_date").reset_index(drop=True)

    summary = []
    for label, (pac_col, opp_col, axis_label) in FACTORS.items():
        # Favorable margin points in the direction expected to help Indiana.
        # For the Pacers' own TOV%, lower is better; for the opponent values,
        # higher TOV% is better. For the other factors, Pacers > opponent.
        if label == "TOV%":
            favorable_margin = games[opp_col] - games[pac_col]
        else:
            favorable_margin = games[pac_col] - games[opp_col]
        wins = games.loc[games["win"], "win"]
        win_m = favorable_margin[games["win"]].mean()
        loss_m = favorable_margin[~games["win"]].mean()
        summary.append({
            "factor": label,
            "win_mean_favorable_margin": win_m,
            "loss_mean_favorable_margin": loss_m,
            "win_minus_loss_gap": win_m - loss_m,
            "favorable_margin_auc": auc_binary(favorable_margin, games["win"]),
            "league_pacers_value": float(league[pac_col]),
            "league_opponent_value": float(league[pac_col] if opp_col not in league.index else league[pac_col]),
        })

        fig, ax = plt.subplots(figsize=(7.2, 6.2), dpi=180)
        for is_win, color, name in [(True, "#12A8B0", "Win"), (False, "#E76F51", "Loss")]:
            d = games[games["win"] == is_win]
            ax.scatter(d[pac_col], d[opp_col], s=42, alpha=0.86, color=color,
                       edgecolors="white", linewidths=0.5, label=name)
        ax.axvline(float(league[pac_col]), color="#333333", linestyle="--", linewidth=1.2,
                   label="League average")
        # Opponent columns are represented by the same factor's league baseline.
        # The supplied league file has one team-neutral average for each factor.
        opp_league_col = pac_col
        ax.axhline(float(league[opp_league_col]), color="#333333", linestyle="--", linewidth=1.2)
        ax.set_title(f"Indiana Pacers 2024–25 {axis_label}: Pacers vs. opponent", fontsize=13, weight="bold")
        ax.set_xlabel(f"Pacers {axis_label}")
        ax.set_ylabel(f"Opponent {axis_label}")
        ax.grid(True, alpha=0.18)
        ax.legend(frameon=False, loc="best")
        ax.text(0.02, 0.02, "Dashed lines = league average", transform=ax.transAxes,
                fontsize=8.5, color="#555555")
        fig.tight_layout()
        safe = label.lower().replace("%", "pct").replace(" ", "_")
        fig.savefig(args.output_dir / f"{safe}_comparison.png", bbox_inches="tight")
        fig.savefig(args.output_dir / f"{safe}_comparison.svg", bbox_inches="tight")
        plt.close(fig)

    summary_df = pd.DataFrame(summary)
    summary_df["abs_gap"] = summary_df["win_minus_loss_gap"].abs()
    summary_df = summary_df.sort_values("abs_gap", ascending=False)
    summary_df.to_csv(args.output_dir / "factor_summary.csv", index=False)
    leader = summary_df.iloc[0]
    (args.output_dir / "interpretation.txt").write_text(
        f"Largest descriptive win–loss favorable-margin gap: {leader['factor']} "
        f"({leader['win_minus_loss_gap']:.4f}). This identifies the factor most associated "
        "with the Pacers' wins in this supplied game sample; it does not establish causation.\n",
        encoding="utf-8",
    )

    fig, axes = plt.subplots(2, 2, figsize=(12, 9), dpi=180)
    for ax, (label, (pac_col, opp_col, axis_label)) in zip(axes.flat, FACTORS.items()):
        for is_win, color, name in [(True, "#12A8B0", "Win"), (False, "#E76F51", "Loss")]:
            d = games[games["win"] == is_win]
            ax.scatter(d[pac_col], d[opp_col], s=24, alpha=0.82, color=color,
                       edgecolors="white", linewidths=0.35, label=name)
        ax.axvline(float(league[pac_col]), color="#444444", linestyle="--", linewidth=0.9)
        ax.axhline(float(league[pac_col]), color="#444444", linestyle="--", linewidth=0.9)
        ax.set_title(axis_label, fontsize=12, weight="bold")
        ax.set_xlabel("Pacers")
        ax.set_ylabel("Opponent")
        ax.grid(True, alpha=0.16)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.98))
    fig.suptitle("Indiana Pacers 2024–25 Four Factors by Game", fontsize=16, weight="bold", y=1.01)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(args.output_dir / "four_factors_all.png", bbox_inches="tight")
    fig.savefig(args.output_dir / "four_factors_all.svg", bbox_inches="tight")
    plt.close(fig)

if __name__ == "__main__":
    main()
