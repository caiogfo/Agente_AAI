"""CLI orchestrator: inputs -> facts -> charts -> narrative -> branded PDF.

Single client (default) or a whole base in batch. Each client is a portfolio JSON
in data/ (same schema), carrying its own client AND advisor, so the pipeline scales
to many clients and many advisors without code changes.

Examples:
    python -m engine.run                     # Albert (default)
    python -m engine.run --portfolio data/x.json
    python -m engine.run --all               # every data/*.json (batch)
    python -m engine.run --all --no-llm      # batch, deterministic narration
    python -m engine.run --emit-facts        # also (re)write build/facts.json for Rivet
    python -m engine.run --live              # append a current-quote market snapshot
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path


def _preset_report_month(argv: list[str]) -> None:
    """Honor `--month YYYY-MM` by setting REPORT_MONTH BEFORE config is imported,
    so the parameterized month flows into every config-derived default."""
    for i, a in enumerate(argv):
        if a == "--month" and i + 1 < len(argv):
            os.environ["REPORT_MONTH"] = argv[i + 1]
        elif a.startswith("--month="):
            os.environ["REPORT_MONTH"] = a.split("=", 1)[1]


_preset_report_month(sys.argv)

from . import config, llm                       # noqa: E402  (after month pre-parse)
from .charts import build_all
from .data_loader import load_client
from .facts import build_facts
from .market_data import get_live_quotes
from .narrate import build_narrative
from .render import render_letter


def _slug(name: str) -> str:
    """File-safe slug from a client name (e.g. 'Albert da Silva' -> 'albert_da_silva')."""
    norm = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", norm.lower()).strip("_") or "cliente"


def generate_one(portfolio_json: Path, use_llm: bool, emit_facts: bool = False,
                 live: bool = False, out: Path | None = None) -> Path:
    """Run the full pipeline for a single client portfolio JSON."""
    model = load_client(portfolio_json=portfolio_json)
    facts = build_facts(model)
    slug = _slug(facts["client"]["full_name"])

    if live:
        tickers = [l["name"] for l in facts["performance"]["legs"]
                   if l["asset_class"] == "Acoes"]
        facts["live_snapshot"] = get_live_quotes(tickers)

    if emit_facts:
        config.BUILD_DIR.mkdir(parents=True, exist_ok=True)
        fp = config.BUILD_DIR / f"facts_{slug}.json"
        fp.write_text(json.dumps(facts, indent=2, ensure_ascii=False))
        # also keep the canonical build/facts.json (Rivet's default input)
        (config.BUILD_DIR / "facts.json").write_text(
            json.dumps(facts, indent=2, ensure_ascii=False))

    charts = build_all(facts, prefix=f"{slug}_")          # namespaced per client
    narrative = build_narrative(facts, use_llm=use_llm)
    month = config.REFERENCE_MONTH_SLUG                    # 'abr25' (parameterized)
    out = Path(out) if out else (config.OUTPUT_DIR / f"{slug}_relatorio_{month}.pdf")
    render_letter(facts, narrative, charts, out)

    p = facts["performance"]
    print(f"  ✓ {facts['client']['full_name']:22} | Assessor {facts['advisor']['name']:18} "
          f"| {facts['client']['risk_profile']:12} | mês {p['total_return_pct']:+.2f}% "
          f"| narração: {narrative.get('_source')}")
    print(f"    -> {out}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="XP monthly advisor letter generator")
    ap.add_argument("--portfolio", default=None, help="path to a client portfolio JSON")
    ap.add_argument("--all", action="store_true",
                    help="process every portfolio JSON in data/ (batch)")
    ap.add_argument("--clients-dir", default=str(config.DATA_DIR),
                    help="directory scanned by --all (default: data/)")
    ap.add_argument("--no-llm", action="store_true", help="force deterministic narration")
    ap.add_argument("--emit-facts", action="store_true", help="write build/facts.json")
    ap.add_argument("--live", action="store_true", help="append live quote snapshot")
    ap.add_argument("--out", default=None, help="output PDF path (single-client only)")
    ap.add_argument("--month", default=None, metavar="YYYY-MM",
                    help="reported month (default: case month 2025-04). Also via REPORT_MONTH env. "
                         "Drives the label, the file suffix (e.g. abr25), the benchmark window and "
                         "the letter dates.")
    args = ap.parse_args(argv)

    use_llm = (not args.no_llm) and llm.have_key()
    label = (llm.provider() or "none") if use_llm else "deterministic fallback"
    print(f"• Mês reportado: {config.REFERENCE_MONTH_LABEL_PT} "
          f"(sufixo {config.REFERENCE_MONTH_SLUG}); emissão {config.ISSUE_DATE:%d/%m/%Y}")

    if args.all:
        portfolios = sorted(Path(args.clients_dir).glob("*.json"))
        if not portfolios:
            print(f"Nenhum portfolio JSON em {args.clients_dir}")
            return 1
        print(f"• Lote: {len(portfolios)} cliente(s) | narração: {label}\n")
        for pf in portfolios:
            generate_one(pf, use_llm=use_llm, emit_facts=args.emit_facts, live=args.live)
        print(f"\n✓ Lote concluído: {len(portfolios)} carta(s) em {config.OUTPUT_DIR}")
        return 0

    portfolio = Path(args.portfolio) if args.portfolio else config.PORTFOLIO_JSON
    print(f"• Cliente único: {portfolio.name} | narração: {label}\n")
    out = generate_one(portfolio, use_llm=use_llm, emit_facts=args.emit_facts,
                       live=args.live, out=Path(args.out) if args.out else None)
    print(f"\n✓ Done. Letter: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
