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
ROOT = Path(__file__).resolve().parent.parent          # 02_Projeto/ (pacote do projeto)
REPO_ROOT = ROOT.parent                                 # raiz do repositório (entregável)
# Case inputs live in a sibling folder at the repo root (kept apart from the project)
INPUT_DIR = REPO_ROOT / "01_Insumos_do_case"
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "Output"
BUILD_DIR = ROOT / "build"          # generated charts / intermediate artifacts
ASSETS_DIR = ROOT / "assets"
# Rivet graphs (final + v1 backup) live in their own folder at the repo root
RIVET_DIR = REPO_ROOT / "03_Rivet"
RIVET_PROJECT = RIVET_DIR / "enter_challenge.rivet-project"

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
# Letter issue date: a few business days after the statement (07/05/2025), when
# the April report would actually be sent. Pinned to the case timeline on purpose
# (NOT datetime.now()), so re-running the build never anachronistically stamps the
# letter with the current year.
ISSUE_DATE = dt.date(2025, 5, 12)
ISSUE_PLACE = "São Paulo"

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
# Risk-profile policy — drives the rule-based recommendation engine.
# Albert is treated with a CONSERVATIVE tilt (per advisor guidance): preserve
# capital first, lower exposure to volatility (equities and risky funds), and
# privilege fixed income and safe (post-fixed) funds in a high-Selic regime.
# Target allocation below is the documented objective for this profile.
# ----------------------------------------------------------------------------
# Policy per risk profile. The recommendation engine picks the policy that
# matches each client's `risk_profile`, so the ANALYSES (target allocation,
# guardrails) adapt per client, not just the numbers. This is what makes the
# pipeline scale to a base with many clients and many advisors.
POLICIES = {
    "Conservador": {
        "profile": "Conservador",
        "min_credit_rating": "BB+",
        "equity_preference": "empresas consolidadas pagadoras de dividendos",
        # capital-preservation tilt, fixed income as the core
        "target_allocation_pct": {"Acoes": 10.0, "Fundos": 30.0, "Renda Fixa": 60.0},
        "max_single_stock_pct": 5.0,       # of total invested
        "deep_loss_threshold_pct": -30.0,  # since-inception loss that warrants review
        "cash_drag_threshold_pct": 10.0,   # idle cash worth deploying
        "max_risky_funds_pct": 15.0,       # cap on volatile funds
    },
    "Moderado": {
        "profile": "Moderado",
        "min_credit_rating": "BB",
        "equity_preference": "empresas consolidadas com bom histórico de resultados",
        "target_allocation_pct": {"Acoes": 25.0, "Fundos": 35.0, "Renda Fixa": 40.0},
        "max_single_stock_pct": 8.0,
        "deep_loss_threshold_pct": -35.0,
        "cash_drag_threshold_pct": 12.0,
        "max_risky_funds_pct": 35.0,
    },
    "Agressivo": {
        "profile": "Agressivo",
        "min_credit_rating": "B",
        "equity_preference": "teses de crescimento com maior potencial de retorno",
        "target_allocation_pct": {"Acoes": 45.0, "Fundos": 35.0, "Renda Fixa": 20.0},
        "max_single_stock_pct": 12.0,
        "deep_loss_threshold_pct": -45.0,
        "cash_drag_threshold_pct": 15.0,
        "max_risky_funds_pct": 60.0,
    },
}


def policy_for(profile: str | None) -> dict:
    """Pick the policy for a client's risk profile (default: Conservador)."""
    return POLICIES.get((profile or "").strip().title(), POLICIES["Conservador"])


# Backwards-compatible aliases (default profile used by single-client runs/tests)
POLICY = POLICIES["Conservador"]
MODERATE_POLICY = POLICY

# Which fund strategies are "safe" (post-fixed / fixed income) vs volatile, and
# the market benchmark used to estimate each strategy's monthly return.
SAFE_FUND_CATEGORIES = {"Renda Fixa / DI", "Renda Fixa"}
FUND_BENCHMARK_BY_CATEGORY = {
    "Renda Fixa / DI": "cdi",
    "Renda Fixa": "cdi",
    "Multimercado": "cdi",          # hedge funds ~ CDI carry (conservative anchor)
    "Long Bias": "ibov",
    "Acoes / Long Biased": "ibov",
    "Acoes": "ibov",
}

# Benchmarks (BCB SGS series codes). CDI/IPCA accumulated in the month (% a.m.).
BCB_SGS = {
    "cdi_month": 4391,   # CDI acumulado no mes (% a.m.)
    "ipca_month": 433,   # IPCA mensal (% a.m.)
    "selic_meta_aa": 432,
}
