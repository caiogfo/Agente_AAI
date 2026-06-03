"""Scalability: many clients × many advisors × many risk profiles, automated.

Proves the calculations AND the analyses adapt per client from the data alone,
with no code changes, so a base of N clients can be processed in batch.
"""
from engine import config
from engine.data_loader import load_client
from engine.facts import build_facts
from engine.market_data import get_benchmarks
from engine.profitability import compute
from engine.recommendations import analyze

DEMO = config.DATA_DIR / "beatriz_almeida_portfolio.json"


def _analyze(path):
    m = load_client(portfolio_json=path)
    b = get_benchmarks()
    prof = compute(m, b["cdi_month_pct"], b["ipca_month_pct"], b["ibov_month_pct"])
    return m, analyze(m, prof)


def test_policy_is_selected_by_each_client_profile():
    assert config.policy_for("Conservador")["target_allocation_pct"]["Renda Fixa"] == 60.0
    assert config.policy_for("Moderado")["target_allocation_pct"]["Acoes"] == 25.0
    assert config.policy_for("Agressivo")["max_single_stock_pct"] == 12.0
    # unknown profile falls back to the conservative policy
    assert config.policy_for("Desconhecido")["profile"] == "Conservador"


def test_second_client_carries_its_own_advisor_and_profile():
    f = build_facts(load_client(portfolio_json=DEMO))
    assert f["client"]["first_name"] == "Beatriz"
    assert f["advisor"]["name"] == "Carla Menezes"          # different advisor
    assert f["client"]["risk_profile"] == "Moderado"        # different profile


def test_analyses_adapt_to_the_moderate_profile():
    m, rs = _analyze(DEMO)
    # moderate cap is 8% (not the conservative 5%): a 18% single stock is flagged
    conc = [r for r in rs.recommendations if "concentracao" in r.headline]
    assert any("ABEV3" in r.headline and "8%" in r.headline for r in conc)
    # cash at 5.6% is below the moderate 12% threshold -> no cash-drag rec
    assert not any(r.target == "Caixa" for r in rs.recommendations)
    # rationales speak the client's profile, not a hardcoded "conservador"
    blob = " ".join(r.rationale for r in rs.recommendations)
    assert "moderado" in blob and "conservador" not in blob


def test_narration_speaks_the_client_profile():
    f = build_facts(load_client(portfolio_json=DEMO))
    from engine.narrate import build_narrative
    nar = build_narrative(f, use_llm=False)
    blob = " ".join(v for v in nar.values() if isinstance(v, str))
    assert "moderado" in blob and "conservador" not in blob
