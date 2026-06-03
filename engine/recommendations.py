"""Rule-based buy/sell/rebalance engine for the moderate profile.

Every recommendation is deterministic and explainable (carries the numbers that
triggered it). The macro overlay is grounded in config.MACRO_FACTS (the XP report),
not invented. This module answers the case's "Buy/Sell Recommendation Logic".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from . import config
from .data_loader import ClientModel
from .profitability import ProfitabilityResult

# Blue-chip dividend payers present in the provided price universe (CSV) that fit
# a moderate profile's "consolidated dividend-paying equities" preference.
DIVIDEND_BLUECHIPS = ["ITUB4", "BBAS3", "VALE3", "PETR4", "ABEV3", "WEGE3"]

# Consolidated, dividend-paying names that FIT the moderate profile. A deep
# drawdown in one of these is treated as a discount on a quality core (trim/hold),
# NOT as a "profile misfit" to be liquidated.
QUALITY_DIVIDEND_PAYERS = {
    "LREN3", "ITUB4", "BBAS3", "VALE3", "PETR4", "ABEV3", "WEGE3", "B3SA3", "BBSE3",
}


@dataclass
class Recommendation:
    action: str          # INVESTIR | DESINVESTIR | REBALANCEAR | REVISAR | MANTER
    target: str          # asset / class the rec applies to
    headline: str
    rationale: str
    priority: int        # 1 = highest
    amount_brl: Optional[float] = None
    tags: list[str] = field(default_factory=list)


@dataclass
class RebalanceRow:
    asset_class: str
    current_pct: float
    target_pct: float
    delta_pct: float     # current - target (positive = overweight)
    delta_brl: float     # how much to move (negative = reduce)


@dataclass
class RecommendationSet:
    recommendations: list[Recommendation]
    rebalance: list[RebalanceRow]
    cash_ratio_pct: float
    deployable_cash_brl: float


def _alloc_by_class(model: ClientModel) -> dict[str, float]:
    out: dict[str, float] = {}
    for p in model.positions:
        out[p.asset_class] = out.get(p.asset_class, 0.0) + p.alloc_pct
    return out


def analyze(model: ClientModel, prof: ProfitabilityResult) -> RecommendationSet:
    pol = config.MODERATE_POLICY
    invested = model.invested
    patrimony = model.patrimony
    recs: list[Recommendation] = []

    # --- 1) Idle cash / cash drag -------------------------------------------
    cash_ratio = model.cash / patrimony * 100.0
    liquidity_buffer = 0.05 * patrimony
    deployable = max(0.0, model.cash - liquidity_buffer)
    if cash_ratio > pol["cash_drag_threshold_pct"]:
        recs.append(Recommendation(
            action="INVESTIR", target="Caixa", priority=1, amount_brl=deployable,
            headline=f"Alocar o caixa ocioso (~R${deployable:,.0f})",
            rationale=(
                f"O saldo em conta (R${model.cash:,.2f}, {cash_ratio:.1f}% do patrimonio) "
                f"esta acima do colchao de liquidez sugerido (~5%). Com a Selic em "
                f"{config.MACRO_FACTS['selic_terminal_pct']:.2f}%, manter caixa parado tem "
                f"alto custo de oportunidade: aplicar em pos-fixado/DI (CDI) captura ~"
                f"{prof.cdi_month_pct:.2f}% ao mes sem fugir do perfil conservador."),
            tags=["cash-drag", "macro:selic-alta"],
        ))

    # --- 2) Rebalancing vs target allocation --------------------------------
    current = _alloc_by_class(model)
    target = pol["target_allocation_pct"]
    rebalance: list[RebalanceRow] = []
    for cls, tgt in target.items():
        cur = current.get(cls, 0.0)
        delta = cur - tgt
        rebalance.append(RebalanceRow(cls, cur, tgt, delta, -delta / 100.0 * invested))

    over = max(rebalance, key=lambda r: r.delta_pct)
    under = min(rebalance, key=lambda r: r.delta_pct)
    if over.delta_pct > 5.0 and under.delta_pct < -5.0:
        recs.append(Recommendation(
            action="REBALANCEAR", target=f"{over.asset_class} -> {under.asset_class}",
            priority=2, amount_brl=min(over.delta_brl * -1, under.delta_brl),
            headline=(f"Rebalancear: reduzir {over.asset_class} "
                      f"(+{over.delta_pct:.1f}p.p.) e reforcar {under.asset_class} "
                      f"({under.delta_pct:.1f}p.p.)"),
            rationale=(
                f"A carteira esta sobrealocada em {over.asset_class} "
                f"({over.current_pct:.1f}% vs alvo {over.target_pct:.0f}%) e subalocada "
                f"em {under.asset_class} ({under.current_pct:.1f}% vs {under.target_pct:.0f}%). "
                f"Migrar ~R${min(abs(over.delta_brl), under.delta_brl):,.0f} aproxima a "
                f"carteira do alvo do perfil conservador e, no ciclo de juros altos, eleva o "
                f"carrego em renda fixa BB+ ou superior."),
            tags=["rebalance", "macro:selic-alta"],
        ))

    # --- 2b) Reduce volatile funds (conservative tilt) ----------------------
    risky = [p for p in model.by_class("Fundos")
             if (p.fund_category or "") not in config.SAFE_FUND_CATEGORIES]
    risky_pct = sum(p.alloc_pct for p in risky)
    cap_risky = pol.get("max_risky_funds_pct", 15.0)
    if risky_pct > cap_risky:
        reduce_brl = (risky_pct - cap_risky) / 100.0 * invested
        recs.append(Recommendation(
            action="DESINVESTIR", target="Fundos de maior volatilidade", priority=2,
            amount_brl=reduce_brl,
            headline=f"Reduzir fundos de maior volatilidade ({risky_pct:.1f}% > {cap_risky:.0f}%)",
            rationale=(
                f"Para o perfil conservador, a exposicao a fundos mais volateis (acoes, long "
                f"bias e multimercado) soma {risky_pct:.1f}% do investido, acima do limite "
                f"sugerido de {cap_risky:.0f}%. Migrar ~R${reduce_brl:,.0f} para fundos pos-fixados "
                f"e renda fixa de qualidade reduz a oscilacao da carteira e preserva o carrego "
                f"elevado da Selic."),
            tags=["conservative", "risky-funds"],
        ))

    # --- 3) Single-stock concentration guardrail ----------------------------
    cap = pol["max_single_stock_pct"]
    for p in model.by_class("Acoes"):
        if p.alloc_pct > cap:
            trim = (p.alloc_pct - cap) / 100.0 * invested
            recs.append(Recommendation(
                action="DESINVESTIR", target=p.ticker, priority=3, amount_brl=trim,
                headline=f"Reduzir concentracao em {p.ticker} ({p.alloc_pct:.2f}% > {cap:.0f}%)",
                rationale=(
                    f"{p.ticker} representa {p.alloc_pct:.2f}% do investido, acima do limite "
                    f"de {cap:.0f}% por ativo individual recomendado para o perfil conservador. "
                    f"Aparar ~R${trim:,.0f} reduz risco idiossincratico."),
                tags=["concentration"],
            ))

    # --- 4) Deeply impaired holdings ----------------------------------------
    # Quality dividend payers at a deep drawdown = discounted core (trim/hold).
    # Impaired names that do not fit the profile = exit candidates.
    for p in model.by_class("Acoes"):
        sir = p.since_inception_return_pct or 0.0
        mret = p.monthly_return_pct or 0.0
        if sir > pol["deep_loss_threshold_pct"]:
            continue
        if p.ticker in QUALITY_DIVIDEND_PAYERS:
            recs.append(Recommendation(
                action="MANTER", target=p.ticker, priority=4,
                headline=f"Manter o nucleo de {p.ticker}, apenas ajustando tamanho",
                rationale=(
                    f"{p.ticker} acumula {sir:.1f}% desde a compra, mas e uma empresa "
                    f"consolidada e pagadora de dividendos — compativel com o perfil conservador. "
                    f"Tratamos a queda como desconto sobre um nucleo de qualidade: manter a "
                    f"posicao e apenas calibrar o tamanho (ver concentracao)."),
                tags=["deep-loss", "profile-fit", "hold-core"],
            ))
        else:
            opportune = (" A alta de %.0f%% no mes abre uma janela para reduzir com menos "
                         "perda." % mret) if mret > 10 else ""
            recs.append(Recommendation(
                action="DESINVESTIR", target=p.ticker, priority=2, amount_brl=p.position_brl,
                headline=f"Revisar/realizar {p.ticker} (perda de {sir:.0f}% desde a compra)",
                rationale=(
                    f"{p.ticker} acumula {sir:.1f}% desde a compra e nao se enquadra no perfil "
                    f"de 'empresas consolidadas pagadoras de dividendos'.{opportune} "
                    f"Reciclar o capital para ativos alinhados ao perfil tende a melhorar a "
                    f"relacao risco-retorno."),
                tags=["deep-loss", "profile-misfit"],
            ))

    # --- 5) Tilt equities toward dividend blue chips ------------------------
    recs.append(Recommendation(
        action="INVESTIR", target="Acoes (dividendos)", priority=4,
        headline="Direcionar a parcela de acoes a blue chips pagadoras de dividendos",
        rationale=(
            "O perfil conservador privilegia acoes de empresas consolidadas com historico de "
            "dividendos. Candidatos no universo coberto: " + ", ".join(DIVIDEND_BLUECHIPS) +
            ". Esses nomes adicionam renda recorrente e menor volatilidade ao sleeve de acoes."),
        tags=["profile-fit", "equities"],
    ))

    # --- 6) Operational: matured CDB still on the statement -----------------
    for p in model.by_class("Renda Fixa"):
        mat = p.raw.get("maturity_date")
        if mat and mat < config.SNAPSHOT_DATE.isoformat():
            recs.append(Recommendation(
                action="REVISAR", target=p.name, priority=3,
                headline="Conferir reinvestimento do CDB vencido",
                rationale=(
                    f"O {p.name} consta com vencimento em {mat}, anterior a data do extrato "
                    f"({config.SNAPSHOT_DATE.isoformat()}). Confirmar liquidacao/reinvestimento "
                    f"para evitar recursos sem remuneracao adequada."),
                tags=["operational", "data-quality"],
            ))

    recs.sort(key=lambda r: r.priority)
    return RecommendationSet(recs, rebalance, cash_ratio, deployable)


if __name__ == "__main__":
    from .data_loader import load_client
    from .market_data import get_monthly_benchmark
    from .profitability import compute
    m = load_client()
    prof = compute(m, get_monthly_benchmark("cdi_month"), get_monthly_benchmark("ipca_month"))
    rs = analyze(m, prof)
    print(f"Caixa: {rs.cash_ratio_pct:.1f}% do patrimonio | aplicavel ~R${rs.deployable_cash_brl:,.0f}\n")
    print("Plano de rebalanceamento (atual vs alvo):")
    for r in rs.rebalance:
        print(f"  {r.asset_class:11} {r.current_pct:5.1f}% -> {r.target_pct:4.0f}%  "
              f"({r.delta_pct:+5.1f}p.p. | mover R${r.delta_brl:+,.0f})")
    print("\nRecomendacoes (prioridade):")
    for r in rs.recommendations:
        amt = f" [~R${r.amount_brl:,.0f}]" if r.amount_brl else ""
        print(f"  P{r.priority} {r.action:12} {r.headline}{amt}")
