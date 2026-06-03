"""External market data (free, no API key).

  - BCB SGS  : real CDI / IPCA accrued in a given month (the benchmark anchor for
               the case month). Full history, free, no token.
  - brapi.dev: OPTIONAL current quote snapshot (used only by the `--live`
               appendix; never mixed into the case-month historical return).

All network calls are cached to build/ and fall back to documented values so the
pipeline is fully reproducible offline.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Optional

import requests

from . import config

_CACHE = config.BUILD_DIR / "market_cache.json"
_TIMEOUT = 20

# Documented fallbacks (real values, so offline runs stay correct for the case
# month). CDI/IPCA per BCB SGS; equity indices (calendar-month) per Yahoo Finance.
_FALLBACK = {
    "cdi_month:2025-04": 1.06,
    "ipca_month:2025-04": 0.43,
    "index_month:^BVSP:2025-04": 3.69,   # Ibovespa, April 2025
    "index_month:^GSPC:2025-04": -0.76,  # S&P 500 (USD), April 2025
}

# Friendly labels for indices.
INDEX_LABELS = {"^BVSP": "Ibovespa", "^GSPC": "S&P 500"}


def _load_cache() -> dict:
    if _CACHE.exists():
        try:
            return json.loads(_CACHE.read_text())
        except Exception:
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    config.BUILD_DIR.mkdir(parents=True, exist_ok=True)
    _CACHE.write_text(json.dumps(cache, indent=2, ensure_ascii=False))


def _bcb_series_month(series: int, month: dt.date) -> Optional[float]:
    """Value of a BCB monthly series for the month containing `month`."""
    first = month.replace(day=1)
    nxt = (first.replace(day=28) + dt.timedelta(days=10)).replace(day=1)
    last = nxt - dt.timedelta(days=1)
    url = (
        f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series}/dados"
        f"?formato=json&dataInicial={first:%d/%m/%Y}&dataFinal={last:%d/%m/%Y}"
    )
    r = requests.get(url, timeout=_TIMEOUT)
    r.raise_for_status()
    rows = r.json()
    if not rows:
        return None
    return float(str(rows[-1]["valor"]).replace(",", "."))


def get_monthly_benchmark(kind: str, month: dt.date = config.REFERENCE_MONTH,
                          use_cache: bool = True) -> float:
    """Return CDI/IPCA accrued (%) in `month`. kind in {'cdi_month','ipca_month'}."""
    key = f"{kind}:{month:%Y-%m}"
    cache = _load_cache()
    if use_cache and key in cache:
        return cache[key]
    try:
        series = config.BCB_SGS[kind]
        val = _bcb_series_month(series, month)
        if val is None:
            raise ValueError("empty BCB series")
        cache[key] = val
        _save_cache(cache)
        return val
    except Exception:
        if key in _FALLBACK:
            return _FALLBACK[key]
        raise


def get_index_month_return(symbol: str, month: dt.date = config.REFERENCE_MONTH,
                           use_cache: bool = True) -> float:
    """Calendar-month % return of an equity index via Yahoo Finance.

    April return = close(April bar) / close(March bar) - 1. Cached; falls back to
    documented real values so the pipeline stays reproducible offline.
    """
    key = f"index_month:{symbol}:{month:%Y-%m}"
    cache = _load_cache()
    if use_cache and key in cache:
        return cache[key]
    try:
        import yfinance as yf  # imported lazily; optional dependency

        prev = (month.replace(day=1) - dt.timedelta(days=1)).replace(day=1)
        start = (prev.replace(day=1) - dt.timedelta(days=10))
        end = (month.replace(day=28) + dt.timedelta(days=10))
        df = yf.download(symbol, start=f"{start:%Y-%m-%d}", end=f"{end:%Y-%m-%d}",
                         interval="1mo", progress=False, auto_adjust=False)
        closes = df["Close"].squeeze().dropna()      # -> 1-D Series
        tags = closes.index.strftime("%Y-%m")

        def _close_for(ym: str) -> float:
            vals = closes[tags == ym].to_numpy().ravel()
            return float(vals[-1])

        c_prev = _close_for(f"{prev:%Y-%m}")
        c_cur = _close_for(f"{month:%Y-%m}")
        val = (c_cur / c_prev - 1.0) * 100.0
        cache[key] = round(val, 4)
        _save_cache(cache)
        return cache[key]
    except Exception:
        if key in _FALLBACK:
            return _FALLBACK[key]
        raise


def get_benchmarks(month: dt.date = config.REFERENCE_MONTH) -> dict:
    """All benchmarks for the case month: CDI, IPCA (BCB) + Ibovespa, S&P500 (Yahoo)."""
    return {
        "cdi_month_pct": get_monthly_benchmark("cdi_month", month),
        "ipca_month_pct": get_monthly_benchmark("ipca_month", month),
        "ibov_month_pct": get_index_month_return("^BVSP", month),
        "sp500_month_pct": get_index_month_return("^GSPC", month),
        "month_label": config.REFERENCE_MONTH_LABEL_PT,
    }


def get_live_quotes(tickers: list[str]) -> dict[str, dict]:
    """OPTIONAL current quotes from brapi.dev (date-stamped, NOT case-month)."""
    out: dict[str, dict] = {}
    try:
        joined = ",".join(tickers)
        r = requests.get(f"https://brapi.dev/api/quote/{joined}", timeout=_TIMEOUT)
        r.raise_for_status()
        for res in r.json().get("results", []):
            out[res.get("symbol")] = {
                "price": res.get("regularMarketPrice"),
                "change_pct": res.get("regularMarketChangePercent"),
                "as_of": res.get("regularMarketTime"),
            }
    except Exception as exc:  # network/token issues are non-fatal
        out["_error"] = str(exc)
    return out


if __name__ == "__main__":
    for k in ("cdi_month", "ipca_month"):
        print(k, config.REFERENCE_MONTH, "->", get_monthly_benchmark(k), "%")
