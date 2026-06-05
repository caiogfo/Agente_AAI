"""The letter's speech must tell the truth about the funds' data source:
'estimado' when proxied (no CNPJ), 'apurado' when the real CVM quote was used.
This flips automatically the day a fund brings a CNPJ. Offline (no LLM)."""
from engine import narrate
from engine.facts import build_facts


def _cov(total, cvm, prox):
    return {"performance": {"funds_coverage": {"total": total, "via_cvm": cvm, "proxied": prox}}}


def test_funds_basis_all_proxied():
    fb = narrate._funds_basis(_cov(3, 0, 3))
    assert fb["real"] is False
    assert "estimad" in fb["pt"] and "apurad" not in fb["pt"]


def test_funds_basis_all_from_cvm():
    fb = narrate._funds_basis(_cov(3, 3, 0))
    assert fb["real"] is True
    assert "apurad" in fb["pt"] and "CVM" in fb["pt"]


def test_funds_basis_mixed():
    fb = narrate._funds_basis(_cov(3, 1, 2))
    assert fb["real"] is True
    assert "apurad" in fb["pt"] and "estimad" in fb["pt"]


def test_speech_says_estimated_when_funds_proxied():
    # Albert (and Beatriz) carry no fund CNPJ today -> all proxied -> 'estimado'.
    nar = narrate.build_narrative(build_facts(), use_llm=False)
    perf = nar["performance"].lower()
    assert "estimad" in perf
    assert "apurados pela cota" not in perf       # no false 'measured from CVM' claim


def test_speech_says_measured_when_funds_from_cvm():
    # Simulate the day every fund brings a CNPJ and the real CVM quote is used.
    f = build_facts()
    f["performance"]["funds_coverage"] = {"total": 7, "via_cvm": 7, "proxied": 0}
    f["performance"]["total_is_estimate"] = False
    perf = narrate.build_narrative(f, use_llm=False)["performance"].lower()
    assert "apurad" in perf and "cvm" in perf
    assert "retorno estimado de" not in perf      # total no longer flagged as an estimate
