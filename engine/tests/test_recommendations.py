"""Tests for the rule-based recommendation engine."""
import math

import pytest

from engine.data_loader import load_client
from engine.profitability import compute
from engine.recommendations import analyze, QUALITY_DIVIDEND_PAYERS

CDI, IPCA = 1.06, 0.43


@pytest.fixture(scope="module")
def rs():
    m = load_client()
    prof = compute(m, CDI, IPCA)
    return analyze(m, prof)


def test_cash_drag_detected(rs):
    assert math.isclose(rs.cash_ratio_pct, 19.30, abs_tol=0.05)
    assert math.isclose(rs.deployable_cash_brl, 55330, abs_tol=5)
    top = rs.recommendations[0]
    assert top.priority == 1 and top.action == "INVESTIR" and "cash-drag" in top.tags


def test_rebalance_overweight_funds_underweight_fixed_income(rs):
    by_cls = {r.asset_class: r for r in rs.rebalance}
    assert by_cls["Fundos"].delta_pct > 15      # overweight
    assert by_cls["Renda Fixa"].delta_pct < -15  # underweight
    assert math.isclose(by_cls["Acoes"].current_pct, 19.32, abs_tol=0.01)


def test_hapv3_is_an_exit_candidate(rs):
    hapv3 = [r for r in rs.recommendations if r.target == "HAPV3"]
    assert any(r.action == "DESINVESTIR" and "profile-misfit" in r.tags for r in hapv3)


def test_quality_payer_lren3_is_not_exited(rs):
    # LREN3 is deeply down but a quality dividend payer: hold core + trim only.
    lren3 = [r for r in rs.recommendations if r.target == "LREN3"]
    assert any(r.action == "MANTER" for r in lren3)
    # the only DESINVESTIR on LREN3 must be the concentration trim, never a full exit
    sells = [r for r in lren3 if r.action == "DESINVESTIR"]
    assert all("concentration" in r.tags for r in sells)


def test_no_quality_payer_is_flagged_profile_misfit(rs):
    for r in rs.recommendations:
        if "profile-misfit" in r.tags:
            assert r.target not in QUALITY_DIVIDEND_PAYERS


def test_concentration_only_for_lren3(rs):
    conc = [r for r in rs.recommendations if "concentration" in r.tags]
    assert len(conc) == 1 and conc[0].target == "LREN3"


def test_matured_cdb_flagged(rs):
    assert any("data-quality" in r.tags and r.action == "REVISAR"
               for r in rs.recommendations)


def test_recommendations_sorted_by_priority(rs):
    prios = [r.priority for r in rs.recommendations]
    assert prios == sorted(prios)
