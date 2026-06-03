"""Statement ingestion: deterministic reconciliation guardrail + (optional) live LLM.

The reconciliation tests run always and are the real guarantee: the golden
(hand-transcribed) statement passes, and any tampered figure is rejected. The live
extraction test runs only when an LLM key is present.
"""
import json

import pytest

from engine import config, llm
from engine.ingest import extract, ingest, parse_brl, parse_pct, reconcile

GOLDEN = json.loads((config.DATA_DIR / "albert_portfolio.json").read_text())


# --------------------------------------------------------------- number parsing
def test_parse_brl_handles_us_and_pt_formats():
    assert parse_brl("R$386,858.82") == 386858.82      # US export
    assert parse_brl("R$ 30.000,00") == 30000.00       # PT export
    assert parse_brl("R$305.44") == 305.44


def test_parse_pct_handles_pt_and_dot():
    assert parse_pct("-41,7%") == -41.7
    assert parse_pct("19.32%") == 19.32


# --------------------------------------------------------------- reconciliation
def test_reconcile_accepts_the_golden_statement():
    assert reconcile(GOLDEN) == []                     # ties to the cent


def test_reconcile_rejects_a_tampered_position():
    bad = json.loads(json.dumps(GOLDEN))
    bad["positions"][0]["position_brl"] += 1000.0      # mis-read one holding
    issues = reconcile(bad)
    assert issues and any("posições" in i or "alocação" in i for i in issues)


def test_reconcile_rejects_broken_patrimony():
    bad = json.loads(json.dumps(GOLDEN))
    bad["totals"]["patrimonio_total"] += 500.0
    assert any("patrimônio" in i for i in reconcile(bad))


# --------------------------------------------------------------- live extraction
@pytest.mark.skipif(not llm.have_key(), reason="no LLM key set")
def test_llm_extraction_reproduces_golden_totals():
    data = ingest(config.INPUT_DIR / "XP - Albert_s portfolio.txt", strict=True)
    assert reconcile(data) == []
    for k in ("patrimonio_total", "total_investido", "saldo_disponivel"):
        assert abs(data["totals"][k] - GOLDEN["totals"][k]) < 1.0
    assert len(data["positions"]) == len(GOLDEN["positions"])
