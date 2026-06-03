"""Brand-consistent, polished charts (matplotlib, headless) for the letter.

Each function returns the path to a PNG saved under build/. Charts are rendered
at a shared height so the allocation donut and the benchmark bar line up cleanly
side by side in the PDF.
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
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "axes.edgecolor": B.XP_GRAY,
    "axes.linewidth": 0.8,
    "figure.dpi": 240,
    "savefig.dpi": 240,
    "text.color": B.XP_BLACK,
    "axes.titlecolor": B.XP_BLACK,
})

_PCT = FuncFormatter(lambda v, _: f"{v:+.1f}%".replace(".", ","))
_H = 3.5  # shared figure height (inches) for visual symmetry

CLASS_LABELS = {"Acoes": "Ações", "Fundos": "Fundos", "Renda Fixa": "Renda Fixa"}


def _save(fig, name: str, prefix: str = "") -> str:
    config.BUILD_DIR.mkdir(parents=True, exist_ok=True)
    path = config.BUILD_DIR / f"{prefix}{name}"
    fig.savefig(path, bbox_inches="tight", facecolor="white", pad_inches=0.06)
    plt.close(fig)
    return str(path)


def _title(ax, text):
    ax.set_title(text, fontsize=11, fontweight="bold", color=B.XP_BLACK,
                 loc="left", pad=12)


def allocation_donut(facts: dict, prefix: str = "") -> str:
    items = sorted(facts["allocation"], key=lambda a: -a["pct"])
    labels = [CLASS_LABELS.get(a["asset_class"], a["asset_class"]) for a in items]
    sizes = [a["pct"] for a in items]
    colors = [B.XP_YELLOW, B.XP_BLACK, B.XP_GRAPHITE][: len(sizes)]

    fig, ax = plt.subplots(figsize=(_H, _H))
    wedges, _ = ax.pie(
        sizes, colors=colors, startangle=90, counterclock=False,
        wedgeprops=dict(width=0.40, edgecolor="white", linewidth=2.4),
    )
    # percentage labels just outside each wedge
    for w, s in zip(wedges, sizes):
        ang = (w.theta2 + w.theta1) / 2
        import math
        x, y = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        ax.annotate(f"{s:.1f}%".replace(".", ","), xy=(x * 0.8, y * 0.8),
                    xytext=(x * 1.16, y * 1.16), ha="center", va="center",
                    fontsize=9.5, fontweight="bold", color=B.XP_BLACK)
    inv = facts["totals"]["invested_brl"]
    ax.text(0, 0.14, "Investido", ha="center", va="center", fontsize=8.5, color=B.XP_GRAY)
    ax.text(0, -0.12, f"R$ {inv:,.0f}".replace(",", "."), ha="center", va="center",
            fontsize=12.5, fontweight="bold", color=B.XP_BLACK)
    # clean centered legend below
    ax.legend(wedges, labels, loc="upper center", bbox_to_anchor=(0.5, 0.02),
              ncol=3, frameon=False, fontsize=9, handlelength=1.1,
              columnspacing=1.3, handletextpad=0.5)
    _title(ax, "Composição da carteira")
    ax.set_aspect("equal")
    return _save(fig, "alloc_donut.png", prefix)


def benchmark_bar(facts: dict, prefix: str = "") -> str:
    p = facts["performance"]
    b = facts["benchmarks"]
    items = [
        ("Carteira", p["total_return_pct"], B.XP_YELLOW),
        ("Ações", p["equities_return_pct"], B.XP_YELLOW_DK),
        ("Ibovespa", b["ibov_month_pct"], B.XP_GRAPHITE),
        ("CDI", b["cdi_month_pct"], B.XP_BLACK),
        ("IPCA", b["ipca_month_pct"], B.XP_GRAY),
    ]
    labels = [i[0] for i in items]
    vals = [i[1] for i in items]
    colors = [i[2] for i in items]

    fig, ax = plt.subplots(figsize=(4.7, _H))
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=B.XP_GRAY_LT, linewidth=0.9)
    bars = ax.bar(labels, vals, color=colors, width=0.62, edgecolor="white", linewidth=0.8,
                  zorder=3)
    ax.axhline(0, color=B.XP_GRAY, linewidth=1.0)
    ax.yaxis.set_major_formatter(_PCT)
    ax.tick_params(labelsize=9.5, length=0)
    top = max(vals)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v + top * 0.03,
                f"{v:+.1f}%".replace(".", ","), ha="center", va="bottom",
                fontsize=9, fontweight="bold", color=B.XP_BLACK)
    ax.margins(y=0.22)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    _title(ax, f"Desempenho em {facts['meta']['reference_month_label']} vs. referências")
    return _save(fig, "benchmark_bar.png", prefix)


def accumulated_bar(facts: dict, prefix: str = "") -> str:
    acc = facts["accumulated"]["by_class"]
    order = ["Renda Fixa", "Fundos", "Acoes"]
    labels = [CLASS_LABELS.get(c, c) for c in order if c in acc]
    vals = [acc[c]["return_pct"] for c in order if c in acc]
    colors = [B.signed_color(v) for v in vals]

    fig, ax = plt.subplots(figsize=(4.7, _H))
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, color=B.XP_GRAY_LT, linewidth=0.9)
    bars = ax.barh(labels, vals, color=colors, height=0.55, edgecolor="white",
                   linewidth=0.8, zorder=3)
    ax.axvline(0, color=B.XP_GRAY, linewidth=1.0)
    ax.xaxis.set_major_formatter(_PCT)
    ax.tick_params(labelsize=9.5, length=0)
    for bar, v in zip(bars, vals):
        ax.text(v + (1.5 if v >= 0 else -1.5), bar.get_y() + bar.get_height() / 2,
                f"{v:+.1f}%".replace(".", ","), va="center",
                ha="left" if v >= 0 else "right", fontsize=9, fontweight="bold",
                color=B.XP_BLACK)
    ax.margins(x=0.20)
    for s in ("top", "right", "bottom"):
        ax.spines[s].set_visible(False)
    _title(ax, "Retorno acumulado por classe")
    return _save(fig, "accumulated_bar.png", prefix)


def build_all(facts: dict, prefix: str = "") -> dict[str, str]:
    # prefix namespaces the PNGs per client so batch runs never collide
    return {
        "allocation": allocation_donut(facts, prefix),
        "benchmark": benchmark_bar(facts, prefix),
        "accumulated": accumulated_bar(facts, prefix),
    }


if __name__ == "__main__":
    from .facts import build_facts
    for k, v in build_all(build_facts()).items():
        print(f"{k}: {v}")
