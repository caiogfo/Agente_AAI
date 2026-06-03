"""Deterministic monthly profitability — the audited core of the report.

Design principle: be explicit about what is *measured* vs *estimated*.

  - Equities      : MEASURED from prices (current / last_month - 1).
  - Fixed income  : MEASURED-ish accrual from the contractual index + spread
                    using the REAL IPCA of the month (IPCA + 5.45% a.a.).
  - Funds         : monthly NAV not present in the provided data -> ESTIMATED
                    with a conservative CDI proxy, flagged is_estimate=True, and
                    the since-inception return is carried separately (correctly
                    labelled, fixing the v1 horizon-mixing bug).

Every figure is rounded only for display; math runs in full precision and is
unit-tested to the cent in engine/tests.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from . import config
from .data_loader import ClientModel, Position


@dataclass
class Leg:
    name: str
    asset_class: str
    alloc_pct: float                 # of total invested
    monthly_return_pct: float        # last-month return
    is_estimate: bool                # True when proxied (funds)
    contribution_pp: float           # contribution to total invested return (pp)
    since_inception_return_pct: Optional[float] = None
    basis: str = ""                  # short methodology note


@dataclass
class ProfitabilityResult:
    reference_month_label: str
    legs: list[Leg]
    # sleeve (per asset class) measured/estimated monthly returns
    class_returns_pct: dict[str, float] = field(default_factory=dict)
    class_is_estimate: dict[str, bool] = field(default_factory=dict)
    equities_return_pct: float = 0.0          # MEASURED
    fixed_income_return_pct: float = 0.0      # MEASURED accrual
    total_return_pct: float = 0.0             # weighted total (contains estimates)
    total_is_estimate: bool = True
    # benchmarks (real, BCB)
    cdi_month_pct: float = 0.0
    ipca_month_pct: float = 0.0
    real_return_pct: float = 0.0              # total - IPCA
    excess_cdi_pp: float = 0.0                # total - CDI
    covered_alloc_pct: float = 0.0            # share priced w/ measured data


def _fixed_income_monthly(pos: Position, ipca_month_pct: float) -> float:
    """IPCA(real, month) compounded with the annual spread -> monthly %."""
    spread = (pos.spread_pct or 0.0) / 100.0
    monthly_spread = (1.0 + spread) ** (1.0 / 12.0) - 1.0
    return ((1.0 + ipca_month_pct / 100.0) * (1.0 + monthly_spread) - 1.0) * 100.0


def compute(model: ClientModel, cdi_month_pct: float, ipca_month_pct: float) -> ProfitabilityResult:
    invested = model.invested
    legs: list[Leg] = []
    measured_alloc = 0.0

    for p in model.positions:
        w = p.position_brl / invested            # weight of total invested
        if p.asset_class == "Acoes":
            r = p.monthly_return_pct
            est = r is None
            if r is None:                        # safety; all stocks are priced
                r = cdi_month_pct
            else:
                measured_alloc += p.alloc_pct
            basis = "preco atual / preco mes anterior (CSV)"
        elif p.asset_class == "Renda Fixa":
            r = _fixed_income_monthly(p, ipca_month_pct)
            est = False
            measured_alloc += p.alloc_pct
            basis = f"IPCA {ipca_month_pct:.2f}% + {p.spread_pct:.2f}%a.a. (pro-rata)"
        else:                                     # Fundos -> proxy
            r = cdi_month_pct
            est = True
            basis = "estimativa: proxy CDI (cota mensal nao fornecida nos dados)"

        legs.append(Leg(
            name=p.name, asset_class=p.asset_class, alloc_pct=p.alloc_pct,
            monthly_return_pct=r, is_estimate=est, contribution_pp=w * r,
            since_inception_return_pct=p.since_inception_return_pct, basis=basis,
        ))

    # sleeve aggregation (weight within each class)
    class_returns: dict[str, float] = {}
    class_is_est: dict[str, bool] = {}
    for cls in ("Acoes", "Fundos", "Renda Fixa"):
        members = [l for l in legs if l.asset_class == cls]
        if not members:
            continue
        wsum = sum(l.alloc_pct for l in members)
        cret = sum(l.monthly_return_pct * l.alloc_pct for l in members) / wsum
        class_returns[cls] = cret
        class_is_est[cls] = any(l.is_estimate for l in members)

    total_return = sum(l.contribution_pp for l in legs)
    total_is_est = any(l.is_estimate for l in legs)

    return ProfitabilityResult(
        reference_month_label=config.REFERENCE_MONTH_LABEL_PT,
        legs=legs,
        class_returns_pct=class_returns,
        class_is_estimate=class_is_est,
        equities_return_pct=class_returns.get("Acoes", 0.0),
        fixed_income_return_pct=class_returns.get("Renda Fixa", 0.0),
        total_return_pct=total_return,
        total_is_estimate=total_is_est,
        cdi_month_pct=cdi_month_pct,
        ipca_month_pct=ipca_month_pct,
        real_return_pct=total_return - ipca_month_pct,
        excess_cdi_pp=total_return - cdi_month_pct,
        covered_alloc_pct=measured_alloc,
    )


if __name__ == "__main__":
    from .data_loader import load_client
    from .market_data import get_monthly_benchmark
    m = load_client()
    cdi = get_monthly_benchmark("cdi_month")
    ipca = get_monthly_benchmark("ipca_month")
    res = compute(m, cdi, ipca)
    print(f"Mes ref: {res.reference_month_label}")
    print(f"Acoes (apurado):      {res.equities_return_pct:+.2f}%")
    print(f"Renda Fixa (apurado): {res.fixed_income_return_pct:+.2f}%")
    print(f"Fundos (estimativa):  {res.class_returns_pct.get('Fundos'):+.2f}%")
    print(f"TOTAL carteira:       {res.total_return_pct:+.2f}%  (estimativa={res.total_is_estimate})")
    print(f"CDI {res.cdi_month_pct:.2f}% | IPCA {res.ipca_month_pct:.2f}% | "
          f"real {res.real_return_pct:+.2f}% | vs CDI {res.excess_cdi_pp:+.2f}pp")
    print(f"Cobertura apurada: {res.covered_alloc_pct:.2f}% do investido")
    print("\nContribuicoes por ativo (pp):")
    for l in sorted(res.legs, key=lambda x: x.contribution_pp, reverse=True):
        tag = "est" if l.is_estimate else "ap "
        print(f"  [{tag}] {l.name[:40]:40} {l.monthly_return_pct:+7.2f}%  -> {l.contribution_pp:+.3f}pp")
