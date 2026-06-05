"""Real-first fund pricing: CVM quote by CNPJ, with proxy fallback.

These tests run fully offline (network is monkeypatched), and prove three things:
  1. the CNPJ availability gate (we always check whether we have the data);
  2. the real monthly-return computation from CVM daily quotas;
  3. the engine wiring (a fund with a CNPJ is MEASURED, one without is PROXIED).
"""
import datetime as dt

import pytest

from engine import cvm, config
from engine.data_loader import ClientModel, Position
from engine.profitability import compute

# A minimal synthetic CVM 'informe diário' (current layout, ';'-separated, latin-1 in prod).
_HEADER = ("TP_FUNDO_CLASSE;CNPJ_FUNDO_CLASSE;ID_SUBCLASSE;DT_COMPTC;VL_TOTAL;"
           "VL_QUOTA;VL_PATRIM_LIQ;CAPTC_DIA;RESG_DIA;NR_COTST")
CNPJ = "11.111.111/0001-11"


def _informe(rows):
    return "\n".join([_HEADER] + [f"FI;{c};;{d};0;{q};0;0;0;1" for c, d, q in rows])


# Two months for the same fund: last day Mar 10.0 -> last day Apr 11.0 = +10%.
_MAR = _informe([(CNPJ, "2025-03-28", "9.9"), (CNPJ, "2025-03-31", "10.0")])
_APR = _informe([(CNPJ, "2025-04-29", "10.8"), (CNPJ, "2025-04-30", "11.0")])


# ----------------------------------------------------------- CNPJ availability gate
@pytest.mark.parametrize("raw,expected", [
    ("11.111.111/0001-11", "11111111000111"),
    ("11111111000111", "11111111000111"),
    (None, None), ("", None), ("123", None), ("not-a-cnpj", None),
])
def test_normalize_cnpj(raw, expected):
    assert cvm.normalize_cnpj(raw) == expected


def test_has_cnpj_checks_the_position():
    assert cvm.has_cnpj(Position("Fundos", "X", 1.0, 1.0, cnpj=CNPJ)) is True
    assert cvm.has_cnpj(Position("Fundos", "Y", 1.0, 1.0)) is False


# ----------------------------------------------------------------- parsing & math
def test_last_quota_picks_latest_business_day():
    assert cvm.last_quota_in_csv(_APR, "11111111000111") == ("2025-04-30", 11.0)


def test_last_quota_supports_legacy_column_name():
    legacy = _APR.replace("CNPJ_FUNDO_CLASSE", "CNPJ_FUNDO")
    assert cvm.last_quota_in_csv(legacy, "11111111000111") == ("2025-04-30", 11.0)


def test_last_quota_absent_cnpj_returns_none():
    assert cvm.last_quota_in_csv(_APR, "99999999000199") is None


def test_monthly_return_from_quotas():
    r = cvm.monthly_return_from_quotas(("2025-03-31", 10.0), ("2025-04-30", 11.0))
    assert r == pytest.approx(10.0)
    assert cvm.monthly_return_from_quotas(None, ("2025-04-30", 11.0)) is None


# ----------------------------------------------------- fund_monthly_return (offline)
def test_fund_monthly_return_computes_real_value(monkeypatch):
    monkeypatch.setattr(cvm, "_fetch_month_csv",
                        lambda ym: _APR if ym == "202504" else _MAR)
    r = cvm.fund_monthly_return(CNPJ, month=dt.date(2025, 4, 1), use_cache=False)
    assert r == pytest.approx(10.0, abs=1e-3)


def test_fund_monthly_return_none_without_cnpj():
    # No network should be touched when there is no CNPJ (the gate short-circuits).
    assert cvm.fund_monthly_return(None) is None
    assert cvm.fund_monthly_return("123") is None


def test_fund_monthly_return_falls_back_when_network_fails(monkeypatch):
    def _boom(ym):
        raise RuntimeError("offline")
    monkeypatch.setattr(cvm, "_fetch_month_csv", _boom)
    # documented real fallback exists for this CNPJ/month
    r = cvm.fund_monthly_return("28.047.174/0001-29", month=dt.date(2025, 4, 1), use_cache=False)
    assert r == pytest.approx(-8.707, abs=1e-3)
    # an unknown CNPJ with no fallback simply yields None -> caller proxies
    assert cvm.fund_monthly_return(CNPJ, month=dt.date(2025, 4, 1), use_cache=False) is None


# ---------------------------------------------------- engine wiring (real vs proxy)
def _model_two_funds():
    positions = [
        Position("Fundos", "Fundo COM CNPJ", 100.0, 50.0,
                 fund_category="Multimercado", cnpj=CNPJ),
        Position("Fundos", "Fundo SEM CNPJ", 100.0, 50.0,
                 fund_category="Multimercado"),
    ]
    totals = {"total_investido": 200.0, "patrimonio_total": 200.0, "saldo_disponivel": 0.0}
    return ClientModel(client={}, advisor={}, totals=totals, positions=positions)


def test_compute_uses_real_quote_when_cnpj_present():
    model = _model_two_funds()
    # resolver returns a measured value only for the fund that carries a CNPJ
    res = compute(model, cdi_month_pct=1.06, ipca_month_pct=0.43, ibov_month_pct=3.69,
                  fund_return_resolver=lambda p: 7.5 if cvm.has_cnpj(p) else None)
    by_name = {l.name: l for l in res.legs}
    real = by_name["Fundo COM CNPJ"]
    proxied = by_name["Fundo SEM CNPJ"]
    assert real.data_source == "cvm" and real.is_estimate is False
    assert real.monthly_return_pct == pytest.approx(7.5)
    assert proxied.data_source == "proxy" and proxied.is_estimate is True
    assert proxied.monthly_return_pct == pytest.approx(1.06)   # CDI proxy
    assert res.funds_coverage == {"total": 2, "with_cnpj": 1, "via_cvm": 1, "proxied": 1}


def test_compute_proxies_everything_without_resolver():
    """Legacy behaviour: no resolver -> all funds proxied, none measured."""
    res = compute(_model_two_funds(), 1.06, 0.43, 3.69)
    assert all(l.data_source == "proxy" for l in res.legs)
    assert res.funds_coverage["via_cvm"] == 0
