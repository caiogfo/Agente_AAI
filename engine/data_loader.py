"""Load and normalize the case inputs into a structured client model.

Sources of truth:
  - data/albert_portfolio.json  -> holdings, allocations, totals (transcribed
    from the XP portfolio statement; a production system would extract this from
    the PDF via OCR/LLM — see REPORT.md roadmap).
  - Input/profitability_calc_wip.csv -> per-stock current and last-month prices
    (THE source of truth for monthly stock returns).
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from typing import Optional

from . import config


@dataclass
class Position:
    asset_class: str
    name: str
    position_brl: float
    alloc_pct: float
    ticker: Optional[str] = None
    since_inception_return_pct: Optional[float] = None
    fund_category: Optional[str] = None
    # stock prices merged from the CSV
    current_price: Optional[float] = None
    last_month_price: Optional[float] = None
    # fixed income
    index: Optional[str] = None
    spread_pct: Optional[float] = None
    raw: dict = field(default_factory=dict)

    @property
    def monthly_return_pct(self) -> Optional[float]:
        """Last-month price return for priced assets (stocks). None otherwise."""
        if self.current_price and self.last_month_price:
            return (self.current_price / self.last_month_price - 1.0) * 100.0
        return None


@dataclass
class ClientModel:
    client: dict
    advisor: dict
    totals: dict
    positions: list[Position]
    risk_profile_text: str = ""
    macro_text: str = ""

    def by_class(self, asset_class: str) -> list[Position]:
        return [p for p in self.positions if p.asset_class == asset_class]

    @property
    def invested(self) -> float:
        return float(self.totals["total_investido"])

    @property
    def patrimony(self) -> float:
        return float(self.totals["patrimonio_total"])

    @property
    def cash(self) -> float:
        return float(self.totals["saldo_disponivel"])


def load_price_csv(path=config.PRICE_CSV) -> dict[str, dict[str, float]]:
    """ticker -> {'current': float, 'last_month': float}."""
    prices: dict[str, dict[str, float]] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            ticker = (row.get("Asset") or "").strip()
            if not ticker:
                continue
            prices[ticker] = {
                "current": float(row["Current price"]),
                "last_month": float(row["Last month price"]),
            }
    return prices


def _read_text(path) -> str:
    try:
        return open(path, encoding="utf-8").read()
    except FileNotFoundError:
        return ""


def load_client(portfolio_json=config.PORTFOLIO_JSON) -> ClientModel:
    data = json.loads(open(portfolio_json, encoding="utf-8").read())
    prices = load_price_csv()

    positions: list[Position] = []
    for raw in data["positions"]:
        pos = Position(
            asset_class=raw["asset_class"],
            name=raw["name"],
            position_brl=float(raw["position_brl"]),
            alloc_pct=float(raw["alloc_pct"]),
            ticker=raw.get("ticker"),
            since_inception_return_pct=raw.get("since_inception_return_pct"),
            fund_category=raw.get("fund_category"),
            index=raw.get("index"),
            spread_pct=raw.get("spread_pct"),
            raw=raw,
        )
        if pos.ticker and pos.ticker in prices:
            pos.current_price = prices[pos.ticker]["current"]
            pos.last_month_price = prices[pos.ticker]["last_month"]
        positions.append(pos)

    return ClientModel(
        client=data["client"],
        advisor=data["advisor"],
        totals=data["totals"],
        positions=positions,
        risk_profile_text=_read_text(config.RISK_PROFILE_TXT),
        macro_text=_read_text(config.MACRO_TXT),
    )


if __name__ == "__main__":  # quick manual check
    m = load_client()
    print(f"Client: {m.client['full_name']}  Advisor: {m.advisor['name']} ({m.advisor['code']})")
    print(f"Patrimony R${m.patrimony:,.2f} | Invested R${m.invested:,.2f} | Cash R${m.cash:,.2f}")
    for p in m.positions:
        mr = p.monthly_return_pct
        mr_s = f"{mr:+.2f}%/mes" if mr is not None else "s/ preco mensal"
        print(f"  [{p.asset_class:10}] {p.name[:42]:42} {p.alloc_pct:5.2f}%  {mr_s}")
