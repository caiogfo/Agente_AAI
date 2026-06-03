"""Build the grounded FACTS object — the single contract the narration consumes.

The LLM (and the Rivet graph) receive ONLY this object and must not introduce any
number that is not present here. This is what kills the v1 hallucinations.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import asdict

from . import config
from .data_loader import ClientModel, load_client
from .market_data import get_benchmarks
from .profitability import ProfitabilityResult, compute
from .recommendations import RecommendationSet, analyze


_PT_MONTHS = {1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril", 5: "maio",
              6: "junho", 7: "julho", 8: "agosto", 9: "setembro", 10: "outubro",
              11: "novembro", 12: "dezembro"}


def _round(x, n=2):
    return None if x is None else round(float(x), n)


# Fund/RF legal-structure tokens that add noise without identifying the product.
_FUND_NOISE = {"FIC", "FIM", "FIA", "FIRF", "FIDC", "REF", "DI", "CP", "RF",
               "SIMPLES", "ADVISORY"}


def _short_name(name: str, asset_class: str = "") -> str:
    """Reader-friendly display name (drops legal-structure suffixes from funds).

    'Riza Lotus Plus Advisory FIC FIRF REF DI CP' -> 'Riza Lotus Plus'
    'CDB BANCO C6 CONSIGNADO S.A. - SET/2024'      -> 'CDB Banco C6'
    Stock tickers and already-short names pass through unchanged.
    """
    if not name:
        return name
    if asset_class == "Renda Fixa" or name.upper().startswith("CDB"):
        base = re.split(r"\s+-\s+", name)[0]                 # drop "- SET/2024"
        base = re.sub(r"\bS\.?/?A\.?\b.*", "", base, flags=re.I).strip()
        kept = base.split()[:3]                              # "CDB BANCO C6"

        def _cap(t: str) -> str:                             # keep codes (CDB, C6, B3)
            if t.upper() in ("CDB", "LCI", "LCA", "CRI", "CRA", "LC"):
                return t.upper()
            if len(t) <= 3 and any(c.isdigit() for c in t):
                return t.upper()
            return t.capitalize()

        return " ".join(_cap(t) for t in kept)
    out: list[str] = []
    for tok in name.split():
        if tok.upper().strip(".") in _FUND_NOISE:
            break
        out.append(tok)
    return " ".join(out) if out else name


def build_facts(model: ClientModel | None = None) -> dict:
    model = model or load_client()
    bench = get_benchmarks()
    prof: ProfitabilityResult = compute(
        model, bench["cdi_month_pct"], bench["ipca_month_pct"], bench["ibov_month_pct"])
    recs: RecommendationSet = analyze(model, prof)

    # allocation by class (% and BRL)
    alloc: dict[str, dict] = {}
    for p in model.positions:
        a = alloc.setdefault(p.asset_class, {"pct": 0.0, "brl": 0.0})
        a["pct"] += p.alloc_pct
        a["brl"] += p.position_brl
    allocation = [{"asset_class": k, "pct": _round(v["pct"]), "brl": _round(v["brl"], 2)}
                  for k, v in alloc.items()]

    # measured stock legs -> month highlights
    stock_legs = [l for l in prof.legs if l.asset_class == "Acoes"]
    best = max(stock_legs, key=lambda l: l.monthly_return_pct)
    worst = min(stock_legs, key=lambda l: l.monthly_return_pct)

    legs = [{
        "name": l.name, "short_name": _short_name(l.name, l.asset_class),
        "asset_class": l.asset_class, "alloc_pct": _round(l.alloc_pct),
        "monthly_return_pct": _round(l.monthly_return_pct), "is_estimate": l.is_estimate,
        "contribution_pp": _round(l.contribution_pp, 3),
        "since_inception_return_pct": _round(l.since_inception_return_pct),
        "basis": l.basis,
    } for l in prof.legs]

    facts = {
        "meta": {
            "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
            "reference_month_label": prof.reference_month_label,
            "snapshot_date": config.SNAPSHOT_DATE.isoformat(),
            "macro_report_date": config.MACRO_DATE.isoformat(),
            # issue date is pinned to the case timeline (May 2025), never now()
            "issue_date": config.ISSUE_DATE.isoformat(),
            "issue_dateline_pt": (
                f"{config.ISSUE_PLACE}, {config.ISSUE_DATE.day} de "
                f"{_PT_MONTHS[config.ISSUE_DATE.month]} de {config.ISSUE_DATE.year}"),
            "currency": "BRL",
            "language_letter": "pt-BR",
        },
        "client": {
            "first_name": model.client["first_name"],
            "full_name": model.client["full_name"],
            "account": model.client["account"],
            "risk_profile": model.client.get("risk_profile", "Moderado"),
            # gender-aware salutation ("Prezada"/"Prezado"); default masculine
            "salutation": "Prezada" if model.client.get("gender") == "F" else "Prezado",
        },
        "advisor": {"name": model.advisor["name"], "code": model.advisor["code"]},
        "totals": {
            "patrimony_brl": _round(model.patrimony, 2),
            "invested_brl": _round(model.invested, 2),
            "cash_brl": _round(model.cash, 2),
            "cash_ratio_pct": _round(recs.cash_ratio_pct),
            # idle-cash carry: monthly yield foregone while the cash sits idle,
            # measured at the real CDI of the month (reinforces the deploy-cash rec).
            "cash_monthly_carry_brl": _round(
                model.cash * bench["cdi_month_pct"] / 100.0, 2),
            "cash_annual_carry_brl": _round(
                model.cash * ((1.0 + bench["cdi_month_pct"] / 100.0) ** 12 - 1.0), 2),
        },
        "allocation": allocation,
        "performance": {
            "total_return_pct": _round(prof.total_return_pct),
            "total_is_estimate": prof.total_is_estimate,
            "equities_return_pct": _round(prof.equities_return_pct),
            "fixed_income_return_pct": _round(prof.fixed_income_return_pct),
            "funds_return_pct_est": _round(prof.class_returns_pct.get("Fundos")),
            "real_return_pct": _round(prof.real_return_pct),
            "excess_cdi_pp": _round(prof.excess_cdi_pp),
            "covered_alloc_pct": _round(prof.covered_alloc_pct),
            "legs": legs,
            "highlight_best": {"ticker": best.name, "monthly_return_pct": _round(best.monthly_return_pct)},
            "highlight_worst": {"ticker": worst.name, "monthly_return_pct": _round(worst.monthly_return_pct)},
        },
        "accumulated": {
            "invested_cost_brl": _round(prof.accumulated_invested_brl, 2),
            "current_value_brl": _round(prof.accumulated_current_brl, 2),
            "return_pct": _round(prof.accumulated_return_pct),
            "gain_brl": _round(prof.accumulated_gain_brl, 2),
            "by_class": {
                cls: {"return_pct": _round(v["return_pct"]),
                      "cost_brl": _round(v["cost_brl"], 2),
                      "current_brl": _round(v["current_brl"], 2)}
                for cls, v in prof.accumulated_by_class.items()
            },
        },
        "benchmarks": {
            "cdi_month_pct": _round(bench["cdi_month_pct"]),
            "ipca_month_pct": _round(bench["ipca_month_pct"]),
            "ibov_month_pct": _round(bench["ibov_month_pct"]),
            "sp500_month_pct": _round(bench["sp500_month_pct"]),
            "equities_vs_ibov_pp": _round(prof.equities_return_pct - bench["ibov_month_pct"]),
        },
        "macro": dict(config.MACRO_FACTS),
        "recommendations": [{
            "action": r.action, "target": r.target, "headline": r.headline,
            "rationale": r.rationale, "priority": r.priority,
            "amount_brl": _round(r.amount_brl, 2), "tags": r.tags,
        } for r in recs.recommendations],
        "rebalance": [{
            "asset_class": rb.asset_class, "current_pct": _round(rb.current_pct),
            "target_pct": _round(rb.target_pct), "delta_pct": _round(rb.delta_pct),
            "delta_brl": _round(rb.delta_brl, 2),
        } for rb in recs.rebalance],
        "methodology_notes": [
            "Acoes: retorno do mes = preco atual / preco do mes anterior (CSV fornecido).",
            "Renda Fixa: IPCA real do mes (BCB) capitalizado com o spread contratual (pro-rata).",
            "Fundos: retorno do mes estimado pela referencia de mercado de cada estrategia "
            "(CDI para pos-fixados/multimercado; Ibovespa para fundos de acoes/long-biased). "
            "Retornos acumulados 'desde a compra' sao exibidos a parte.",
            "Acumulado: valor atual vs custo dos aportes (preco medio x quantidade nas acoes; "
            "valor aplicado nos fundos e na renda fixa).",
            "Benchmarks: CDI e IPCA do BCB (SGS); Ibovespa e S&P 500 do Yahoo Finance (mes-calendario).",
            "Macro: numeros transcritos do relatorio XP de 06/02/2025; ex.: cambio R$ 6,20/USD "
            "no fim de 2025 e projecao da XP, nao uma estimativa do modelo.",
            f"Janela de comparacao: os precos das acoes refletem o extrato de "
            f"{config.SNAPSHOT_DATE.strftime('%d/%m/%Y')}, enquanto os benchmarks usam o "
            f"fechamento do mes de referencia; por isso as janelas podem diferir ligeiramente.",
        ],
        "period_disclaimer": (
            f"Os precos das acoes refletem o extrato de "
            f"{config.SNAPSHOT_DATE.strftime('%d/%m/%Y')}; os indicadores de mercado (CDI, "
            f"IPCA, Ibovespa, S&P 500) usam o fechamento do mes de referencia. As janelas de "
            f"comparacao podem, portanto, diferir ligeiramente."
        ),
        "disclaimer": (
            "Material de carater informativo. Rentabilidade passada nao garante resultados "
            "futuros. Estimativas estao sinalizadas no relatorio. Em caso de duvidas, fale "
            "com o seu assessor."
        ),
    }
    return facts


def save_facts(path=None) -> dict:
    facts = build_facts()
    path = path or (config.BUILD_DIR / "facts.json")
    config.BUILD_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(facts, indent=2, ensure_ascii=False))
    return facts


if __name__ == "__main__":
    f = save_facts()
    print(json.dumps(f, indent=2, ensure_ascii=False)[:1600])
    print("...\n[facts.json saved to build/]")
