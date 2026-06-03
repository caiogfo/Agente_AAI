"""CLI orchestrator: inputs -> facts -> charts -> narrative -> branded PDF.

Examples:
    python -m engine.run                 # full pipeline for Albert
    python -m engine.run --no-llm        # force deterministic narration
    python -m engine.run --emit-facts    # also (re)write build/facts.json for Rivet
    python -m engine.run --live          # append a current-quote market snapshot
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import config, llm
from .charts import build_all
from .facts import build_facts
from .market_data import get_live_quotes
from .narrate import build_narrative
from .render import render_letter


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="XP monthly advisor letter generator")
    ap.add_argument("--client", default="Albert", help="client first name (label only)")
    ap.add_argument("--no-llm", action="store_true", help="force deterministic narration")
    ap.add_argument("--emit-facts", action="store_true", help="write build/facts.json")
    ap.add_argument("--live", action="store_true", help="append live quote snapshot")
    ap.add_argument("--out", default=None, help="output PDF path")
    args = ap.parse_args(argv)

    print("• Building grounded facts…")
    facts = build_facts()

    if args.live:
        tickers = [l["name"] for l in facts["performance"]["legs"]
                   if l["asset_class"] == "Acoes"]
        print(f"• Fetching live quotes for {tickers} (context only)…")
        facts["live_snapshot"] = get_live_quotes(tickers)

    if args.emit_facts:
        fp = config.BUILD_DIR / "facts.json"
        config.BUILD_DIR.mkdir(parents=True, exist_ok=True)
        fp.write_text(json.dumps(facts, indent=2, ensure_ascii=False))
        print(f"• facts.json -> {fp}")

    print("• Rendering charts…")
    charts = build_all(facts)

    use_llm = (not args.no_llm) and llm.have_key()
    label = (llm.provider() or "none") if use_llm else "deterministic fallback"
    print(f"• Narrating ({label})…")
    narrative = build_narrative(facts, use_llm=use_llm)
    print(f"  source: {narrative.get('_source')}")

    out = Path(args.out) if args.out else (config.OUTPUT_DIR / "Albert_relatorio_mensal.pdf")
    print("• Building PDF…")
    render_letter(facts, narrative, charts, out)

    p = facts["performance"]
    print("\n✓ Done.")
    print(f"  Letter : {out}")
    print(f"  Client : {facts['client']['full_name']}  |  Advisor: {facts['advisor']['name']}")
    print(f"  Month  : {facts['meta']['reference_month_label']}  |  "
          f"equities {p['equities_return_pct']:+.2f}% (measured), "
          f"total {p['total_return_pct']:+.2f}% (est.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
