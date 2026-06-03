"""Automated statement ingestion: PDF/text -> structured portfolio JSON.

This closes the last manual step (transcription) so the pipeline can scale to a
base of clients. The design keeps the project's anti-hallucination principle even
during ingestion:

    LLM proposes STRUCTURE  ->  deterministic RECONCILIATION verifies the MONEY

The model reads the messy, layout-broken statement text and emits structured JSON.
Then `reconcile()` checks, to the cent, that the parts tie to the statement's own
totals (sum of positions == total invested; invested + cash == patrimony; each
position's % == its share of invested). If anything fails to tie, the record is
REJECTED for human review and never silently accepted. We validate the extractor
against the hand-transcribed golden JSON (engine/tests/test_ingest.py).

What the statement does NOT contain (fund strategy category, the CDB's index/spread,
credit rating) is left out here and added by an explicit enrichment step; we never
invent it during extraction.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import config, llm

# Tolerances for reconciliation (the statement reconciles exactly; allow only rounding).
TOL_BRL = 1.00      # R$ tolerance on monetary sums
TOL_PAT = 0.10      # R$ tolerance on invested + cash == patrimony
TOL_PP = 0.10       # percentage-point tolerance on each position's allocation


# --------------------------------------------------------------- number parsing
def parse_brl(text: str) -> float:
    """Parse a BRL amount in either US ('R$386,858.82') or PT ('R$ 30.000,00') form."""
    s = re.sub(r"[R$\s]", "", str(text))
    if not s:
        raise ValueError("empty BRL value")
    last_dot, last_comma = s.rfind("."), s.rfind(",")
    if last_dot > last_comma:                 # dot is the decimal separator (US)
        s = s.replace(",", "")
    else:                                     # comma is the decimal separator (PT)
        s = s.replace(".", "").replace(",", ".")
    return float(s)


def parse_pct(text: str) -> float:
    """Parse a percentage like '-41,7%' or '19.32%' -> float."""
    s = re.sub(r"[%\s]", "", str(text)).replace(",", ".")
    return float(s)


# --------------------------------------------------------------- LLM extraction
_SCHEMA_HINT = """Return ONLY a JSON object (no prose, no code fences) shaped exactly like:
{
  "client": {"full_name": str, "first_name": str, "account": str,
             "statement_datetime": str|null},
  "advisor": {"code": str, "name": str},
  "totals": {"patrimonio_total": number, "total_investido": number,
             "saldo_disponivel": number},
  "positions": [
    {"asset_class": "Acoes", "name": str, "ticker": str, "position_brl": number,
     "alloc_pct": number, "since_inception_return_pct": number,
     "avg_price": number|null, "last_price": number|null, "qty": number|null},
    {"asset_class": "Fundos", "name": str, "position_brl": number,
     "alloc_pct": number, "since_inception_return_pct": number},
    {"asset_class": "Renda Fixa", "name": str, "position_brl": number,
     "alloc_pct": number, "applied_brl": number|null}
  ]
}"""

_SYSTEM = (
    "You extract structured data from a Brazilian (XP) brokerage statement whose "
    "PDF-to-text export has a SCRAMBLED layout (labels and values are often on "
    "separate lines, and a fund/stock name may appear right AFTER its numbers). "
    "Read carefully and associate each value with the correct holding.\n"
    "RULES:\n"
    "- Copy every number EXACTLY as printed. Do NOT compute, round or invent any "
    "value. If a field is not present, use null.\n"
    "- Normalize monetary values to a plain number with a dot decimal (e.g. "
    "'R$386,858.82' -> 386858.82, 'R$ 30.000,00' -> 30000.00). Normalize percentages "
    "to a number (e.g. '-41,7%' -> -41.7).\n"
    "- The stock detail block (Data do investimento / Preço médio / Último preço / "
    "Qtd) lists the stocks in the SAME ORDER as the equities section; map them "
    "positionally.\n"
    "- Do not include risk profile or fund strategy category (they are not in this "
    "document).\n" + _SCHEMA_HINT
)


def extract(statement_text: str) -> dict:
    """Use the LLM to turn statement text into structured JSON (structure only)."""
    raw = llm.complete(_SYSTEM, statement_text, temperature=0, max_tokens=2000)
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        raise ValueError("extractor returned no JSON object")
    return json.loads(m.group(0))


# --------------------------------------------------------------- reconciliation
def reconcile(data: dict) -> list[str]:
    """Deterministic guardrail. Returns a list of discrepancies (empty == OK)."""
    issues: list[str] = []
    t = data.get("totals", {})
    inv = float(t.get("total_investido", 0) or 0)
    pat = float(t.get("patrimonio_total", 0) or 0)
    cash = float(t.get("saldo_disponivel", 0) or 0)
    positions = data.get("positions", []) or []

    pos_sum = sum(float(p.get("position_brl", 0) or 0) for p in positions)
    if abs(pos_sum - inv) > TOL_BRL:
        issues.append(f"soma das posições ({pos_sum:.2f}) != total investido ({inv:.2f})")
    if abs(inv + cash - pat) > TOL_PAT:
        issues.append(f"investido+caixa ({inv + cash:.2f}) != patrimônio ({pat:.2f})")

    alloc_sum = sum(float(p.get("alloc_pct", 0) or 0) for p in positions)
    if abs(alloc_sum - 100.0) > 0.5:
        issues.append(f"soma das alocações ({alloc_sum:.2f}%) != 100%")

    for p in positions:
        pos = float(p.get("position_brl", 0) or 0)
        alloc = float(p.get("alloc_pct", 0) or 0)
        if inv and abs(pos / inv * 100.0 - alloc) > TOL_PP:
            issues.append(
                f"{p.get('name', '?')}: alocação informada {alloc:.2f}% != "
                f"{pos / inv * 100.0:.2f}% (posição/investido)")
    return issues


# ----------------------------------------------------------------------- ingest
def ingest(statement_path: str | Path, strict: bool = True) -> dict:
    """Read a statement, extract structured JSON, and reconcile it.

    Raises ValueError listing the discrepancies if reconciliation fails (strict),
    so a mis-read statement is never accepted silently.
    """
    text = Path(statement_path).read_text(encoding="utf-8")
    data = extract(text)
    issues = reconcile(data)
    data["_reconciliation"] = {"ok": not issues, "issues": issues}
    if issues and strict:
        raise ValueError("Reconciliação falhou (registro rejeitado para revisão):\n  - "
                         + "\n  - ".join(issues))
    return data


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else str(
        config.INPUT_DIR / "XP - Albert_s portfolio.txt")
    print(f"• Ingerindo {path} …")
    out = ingest(path, strict=False)
    rec = out["_reconciliation"]
    print(f"• Reconciliação: {'OK' if rec['ok'] else 'FALHOU'}")
    for i in rec["issues"]:
        print("   -", i)
    print(json.dumps({k: v for k, v in out.items() if k != "_reconciliation"},
                     ensure_ascii=False, indent=2)[:1200])
