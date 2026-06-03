"""Integration tests: Rivet graph integrity + end-to-end pipeline grounding."""
import re

import pytest

from engine import config
from engine.facts import build_facts
from engine.narrate import build_narrative

yaml = pytest.importorskip("yaml")


# ------------------------------------------------------------------- Rivet file
def _graph():
    doc = yaml.safe_load(open(config.ROOT / "enter_challenge.rivet-project"))
    return doc["data"]["graphs"]["main_challenge_v2"]


def test_rivet_parses_and_has_no_hardcoded_windows_paths():
    raw = open(config.ROOT / "enter_challenge.rivet-project").read()
    assert "C:\\Users" not in raw and "blope" not in raw       # v1 bug fixed
    assert "build/facts.json" in raw                            # grounded on facts
    assert "claude" in raw.lower()                              # Anthropic, not gpt


def test_rivet_connections_reference_existing_nodes():
    g = _graph()
    nodes = g["nodes"]
    ids = {}
    for key in nodes:
        m = re.match(r"\[(.+?)\]:(\w+) \"(.+)\"", key)
        ids[m.group(1)] = m.group(3)
    for key, node in nodes.items():
        for conn in (node.get("outgoingConnections") or []):
            m = re.match(r'(\w+)->"(.+?)" (\S+?)/(\w+)', conn)
            assert m, f"bad connection: {conn}"
            _, ttitle, tid, _ = m.groups()
            assert tid in ids, f"missing target {tid}"
            assert ids[tid] == ttitle, f"title mismatch for {tid}"


def test_rivet_prompt_inputs_have_placeholders():
    """Every prompt-input connection target must exist as {{port}} in its text."""
    g = _graph()
    nodes = g["nodes"]
    text_by_id = {}
    for key, node in nodes.items():
        m = re.match(r"\[(.+?)\]:(\w+) ", key)
        if m.group(2) == "prompt":
            text_by_id[m.group(1)] = node["data"]["promptText"]
    for key, node in nodes.items():
        for conn in (node.get("outgoingConnections") or []):
            m = re.match(r'(\w+)->"(.+?)" (\S+?)/(\w+)', conn)
            _, _, tid, tport = m.groups()
            if tid in text_by_id and tport not in ("prompt",):
                assert "{{" + tport + "}}" in text_by_id[tid], \
                    f"port {tport} not found as placeholder in {tid}"


# ---------------------------------------------------------------- pipeline facts
def test_facts_client_is_albert_not_joao():
    f = build_facts()
    assert f["client"]["first_name"] == "Albert"
    assert f["advisor"]["name"] == "Antonio Bicudo"


def test_macro_facts_match_source_not_v1_hallucination():
    f = build_facts()["macro"]
    assert f["selic_terminal_pct"] == 15.50      # not the v1 "9%"
    assert f["fx_end_2025"] == 6.20              # not the v1 "4.70"
    assert f["fed_cuts_2025"] is False


def test_fallback_narrative_has_all_sections_and_no_joao():
    f = build_facts()
    nar = build_narrative(f, use_llm=False)
    for k in ("greeting", "performance", "macro", "recommendations", "closing"):
        assert isinstance(nar[k], str) and len(nar[k]) > 40
    blob = " ".join(nar[k] for k in nar if isinstance(nar[k], str))
    assert "João" not in blob and "Joao" not in blob


def test_period_disclaimer_present_in_facts():
    f = build_facts()
    assert "extrato" in f["period_disclaimer"]
    assert any("Janela de comparacao" in n for n in f["methodology_notes"])
