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
# month). CDI/IPCA accrued in April 2025 per BCB SGS.
_FALLBACK = {
    "cdi_month:2025-04": 1.06,
    "ipca_month:2025-04": 0.43,
}


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
