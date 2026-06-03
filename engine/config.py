"""Central configuration: case anchoring dates, paths and reference parameters.

The whole pipeline is anchored to the *case's own dates* (no live/anachronistic
data leaks into the historical return):
  - Portfolio snapshot: 2025-05-07 (from XP - Albert's portfolio)
  - Macro report:       2025-02-06 (XP - Macro analysis)
  - Reference month for "last month's profitability": April 2025
    (the month that closed immediately before the snapshot).
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "Input"
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "Output"
BUILD_DIR = ROOT / "build"          # generated charts / intermediate artifacts
ASSETS_DIR = ROOT / "assets"

PORTFOLIO_JSON = DATA_DIR / "albert_portfolio.json"
PRICE_CSV = INPUT_DIR / "profitability_calc_wip.csv"
RISK_PROFILE_TXT = INPUT_DIR / "XP - Albert_s risk profile.txt"
MACRO_TXT = INPUT_DIR / "XP - Macro analysis.txt"

# ----------------------------------------------------------------------------
# Case anchoring
# ----------------------------------------------------------------------------
SNAPSHOT_DATE = dt.date(2025, 5, 7)
MACRO_DATE = dt.date(2025, 2, 6)
# "Last month" = the month that closed right before the snapshot.
REFERENCE_MONTH = dt.date(2025, 4, 1)   # April 2025
REFERENCE_MONTH_LABEL_PT = "abril de 2025"

# ----------------------------------------------------------------------------
# Macro reference figures (transcribed verbatim from the XP macro report so the
# narration is grounded and cannot drift). Source: "XP - Macro analysis.txt".
# ----------------------------------------------------------------------------
MACRO_FACTS = {
    "source": "XP Macro Research – Brasil Macro Mensal, 06/02/2025 (Caio Megale et al.)",
    "selic_terminal_pct": 15.50,
    "selic_end_2025_pct": 15.50,
    "selic_end_2026_pct": 12.50,
    "ipca_2025_pct": 6.1,
    "ipca_2026_pct": 4.5,
    "pib_2025_pct": 2.0,
    "pib_2026_pct": 1.0,
    "fx_end_2025": 6.20,
    "fx_end_2026": 6.40,
    "fed_cuts_2025": False,
    "headline_pt": (
        "Cenario de 'calmaria antes de outra tempestade': inflacao pressionada, "
        "juros altos por bom tempo e incerteza fiscal/eleitoral elevada."
    ),
}

# ----------------------------------------------------------------------------
# Risk-profile policy (moderate) — drives the rule-based recommendation engine.
# Derived from "XP - Albert's risk profile.txt".
# ----------------------------------------------------------------------------
MODERATE_POLICY = {
    "profile": "Moderado",
    "min_credit_rating": "BB+",
    "equity_preference": "empresas consolidadas pagadoras de dividendos",
    # Indicative target allocation for a moderate Brazilian investor.
    "target_allocation_pct": {"Acoes": 20.0, "Fundos": 50.0, "Renda Fixa": 30.0},
    # Guardrails
    "max_single_stock_pct": 7.0,       # of total invested
    "deep_loss_threshold_pct": -40.0,  # since-inception loss that warrants review
    "cash_drag_threshold_pct": 15.0,   # idle cash as % of patrimony worth deploying
}

# Benchmarks (BCB SGS series codes). CDI/IPCA accumulated in the month (% a.m.).
BCB_SGS = {
    "cdi_month": 4391,   # CDI acumulado no mes (% a.m.)
    "ipca_month": 433,   # IPCA mensal (% a.m.)
    "selic_meta_aa": 432,
}
