"""Brand-consistent charts (matplotlib, headless) for the monthly letter.

Each function returns the path to a PNG saved under build/. Colors come from the
XP token module so the whole report stays on-brand.
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from . import config
from . import brand as B

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "axes.edgecolor": B.XP_GRAY,
    "axes.linewidth": 0.8,
    "figure.dpi": 200,
})

_PCT = FuncFormatter(lambda v, _: f"{v:+.1f}%")

# display labels (facts.json stores ASCII class keys)
CLASS_LABELS = {"Acoes": "Ações", "Fundos": "Fundos", "Renda Fixa": "Renda Fixa"}


def _save(fig, name: str) -> str:
    config.BUILD_DIR.mkdir(parents=True, exist_ok=True)
    path = config.BUILD_DIR / name
    fig.savefig(path, bbox_inches="tight", transparent=False, facecolor="white")
    plt.close(fig)
    return str(path)


def allocation_donut(facts: dict) -> str:
    labels = [CLASS_LABELS.get(a["asset_class"], a["asset_class"]) for a in facts["allocation"]]
    sizes = [a["pct"] for a in facts["allocation"]]
    colors = [B.XP_YELLOW, B.XP_BLACK, B.XP_GRAPHITE][: len(sizes)]
    fig, ax = plt.subplots(figsize=(3.6, 3.6))
    wedges, _ = ax.pie(sizes, colors=colors, startangle=90,
                       wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2))
    ax.legend(wedges, [f"{l}  {s:.1f}%" for l, s in zip(labels, sizes)],
              loc="center", frameon=False, fontsize=8.5,
              bbox_to_anchor=(0.5, -0.06), ncol=1)
    inv = facts["totals"]["invested_brl"]
    ax.text(0, 0.12, "Investido", ha="center", va="center", fontsize=8, color=B.XP_GRAY)
    ax.text(0, -0.10, f"R$ {inv:,.0f}".replace(",", "."), ha="center", va="center",
            fontsize=11, fontweight="bold", color=B.XP_BLACK)
    ax.set_aspect("equal")
    return _save(fig, "alloc_donut.png")


def monthly_stock_returns(facts: dict) -> str:
    legs = [l for l in facts["performance"]["legs"] if l["asset_class"] == "Acoes"]
    legs.sort(key=lambda l: l["monthly_return_pct"])
    names = [l["name"] for l in legs]
    vals = [l["monthly_return_pct"] for l in legs]
    colors = [B.signed_color(v) for v in vals]
    fig, ax = plt.subplots(figsize=(4.2, 3.0))
    bars = ax.barh(names, vals, color=colors, height=0.6)
    ax.axvline(0, color=B.XP_GRAY, linewidth=0.8)
    ax.xaxis.set_major_formatter(_PCT)
    ax.tick_params(labelsize=8.5)
    for b, v in zip(bars, vals):
        ax.text(v + (0.8 if v >= 0 else -0.8), b.get_y() + b.get_height() / 2,
                f"{v:+.1f}%", va="center", ha="left" if v >= 0 else "right",
                fontsize=8, fontweight="bold", color=B.XP_BLACK)
    ax.set_title("Retorno no mês — Ações (apurado)", fontsize=9.5, fontweight="bold",
                 color=B.XP_BLACK, loc="left")
    ax.margins(x=0.22)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    return _save(fig, "stock_returns.png")


def benchmark_bar(facts: dict) -> str:
    p = facts["performance"]
    b = facts["benchmarks"]
    items = [
        ("Ações\n(apurado)", p["equities_return_pct"], B.XP_YELLOW),
        ("Carteira\n(estim.)", p["total_return_pct"], B.XP_YELLOW_DK),
        ("Ibovespa", b["ibov_month_pct"], B.XP_GRAPHITE),
        ("CDI", b["cdi_month_pct"], B.XP_BLACK),
        ("IPCA", b["ipca_month_pct"], B.XP_GRAY),
    ]
    labels = [i[0] for i in items]
    vals = [i[1] for i in items]
    colors = [i[2] for i in items]
    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    bars = ax.bar(labels, vals, color=colors, width=0.62, edgecolor="white")
    ax.axhline(0, color=B.XP_GRAY, linewidth=0.8)
    ax.yaxis.set_major_formatter(_PCT)
    ax.tick_params(labelsize=8.2)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.12,
                f"{v:+.1f}%", ha="center", va="bottom", fontsize=8, fontweight="bold",
                color=B.XP_BLACK)
    ax.set_title("Desempenho no mês vs. benchmarks", fontsize=9.5, fontweight="bold",
                 color=B.XP_BLACK, loc="left")
    ax.margins(y=0.20)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    return _save(fig, "benchmark_bar.png")


def build_all(facts: dict) -> dict[str, str]:
    return {
        "allocation": allocation_donut(facts),
        "stock_returns": monthly_stock_returns(facts),
        "benchmark": benchmark_bar(facts),
    }


if __name__ == "__main__":
    from .facts import build_facts
    paths = build_all(build_facts())
    for k, v in paths.items():
        print(f"{k}: {v}")
