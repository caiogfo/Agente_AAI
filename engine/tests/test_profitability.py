"""Zero-tolerance arithmetic tests for the profitability engine.

Every expected value here was computed by hand from the provided inputs.
"""
import math

import pytest

from engine import config
from engine.data_loader import load_client
from engine.profitability import compute, _fixed_income_monthly

# Fixed, reproducible benchmarks for the case month (real BCB values, April 2025)
CDI = 1.06
IPCA = 0.43


@pytest.fixture(scope="module")
def model():
    return load_client()


@pytest.fixture(scope="module")
def result(model):
    return compute(model, CDI, IPCA)


# ---------------------------------------------------------------- loader sanity
def test_totals_reconcile(model):
    assert math.isclose(model.invested + model.cash, model.patrimony, abs_tol=0.01)


def test_positions_sum_to_invested(model):
    s = sum(p.position_brl for p in model.positions)
    # statement rounds allocations; positions reconcile to invested within R$1
    assert math.isclose(s, model.invested, abs_tol=1.0)


# ---------------------------------------------------------- stock monthly return
@pytest.mark.parametrize("ticker,cur,prev", [
    ("LREN3", 16.94, 15.55),
    ("MRFG3", 10.26, 12.27),
    ("ARZZ3", 56.58, 56.55),
    ("HAPV3", 3.97, 2.25),
])
def test_stock_monthly_return(model, ticker, cur, prev):
    pos = next(p for p in model.positions if p.ticker == ticker)
    expected = (cur / prev - 1.0) * 100.0
    assert math.isclose(pos.monthly_return_pct, expected, abs_tol=1e-9)


def test_hapv3_recovered_last_month_despite_deep_loss(model):
    """The v1 bug: presenting since-inception loss as if it were the month."""
    pos = next(p for p in model.positions if p.ticker == "HAPV3")
    assert pos.monthly_return_pct > 70          # +76.4% in the month
    assert pos.since_inception_return_pct < -70  # -74.6% since purchase


# ------------------------------------------------------------- sleeve aggregates
def test_equities_sleeve_measured(result):
    # weighted by allocation within equities (8.91,4.94,3.50,1.97)
    assert math.isclose(result.equities_return_pct, 7.7382, abs_tol=1e-3)
    assert result.class_is_estimate["Acoes"] is False


def test_fixed_income_accrual(result):
    expected = ((1 + IPCA / 100) * (1.0545) ** (1 / 12) - 1) * 100
    assert math.isclose(result.fixed_income_return_pct, expected, abs_tol=1e-9)
    assert math.isclose(result.fixed_income_return_pct, 0.8751, abs_tol=1e-3)


def test_funds_proxied_to_cdi_and_flagged(result):
    assert math.isclose(result.class_returns_pct["Fundos"], CDI, abs_tol=1e-9)
    assert result.class_is_estimate["Fundos"] is True


# ----------------------------------------------------------------- total & marks
def test_total_equals_sum_of_contributions(result):
    s = sum(l.contribution_pp for l in result.legs)
    assert math.isclose(result.total_return_pct, s, abs_tol=1e-9)


def test_total_is_flagged_estimate(result):
    assert result.total_is_estimate is True       # because funds are proxied


def test_total_value_handcheck(result):
    assert math.isclose(result.total_return_pct, 2.3239, abs_tol=2e-3)


def test_benchmark_context(result):
    assert math.isclose(result.excess_cdi_pp, result.total_return_pct - CDI, abs_tol=1e-9)
    assert math.isclose(result.real_return_pct, result.total_return_pct - IPCA, abs_tol=1e-9)


def test_measured_coverage(result):
    # equities (19.32) + fixed income (12.97) measured; funds estimated
    assert math.isclose(result.covered_alloc_pct, 32.29, abs_tol=0.01)


def test_fixed_income_helper_pure():
    # IPCA 0% -> just the monthly-equivalent of the annual spread
    only_spread = _fixed_income_monthly(_Stub(5.45), 0.0)
    assert math.isclose(only_spread, ((1.0545) ** (1 / 12) - 1) * 100, abs_tol=1e-9)


class _Stub:
    def __init__(self, spread):
        self.spread_pct = spread
