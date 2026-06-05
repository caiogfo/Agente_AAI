"""Real fund quotes from CVM's public 'informe diário': measured fund returns by CNPJ.

Why this exists: a fund can diverge sharply from any benchmark proxy. In April/2025, real
funds in the CVM base ranged from about -8.7% to +13.6% in the month while the CDI was only
+1.06%. Pricing every fund off CDI/Ibovespa would therefore attribute a wrong number to a
specific product, exactly the kind of hallucination this project removes.

So the engine resolves each fund's monthly return REAL-FIRST:

  1. If the position carries a CNPJ, fetch the fund's official daily quota (VL_QUOTA) from CVM
     and compute the calendar-month return = quota(last day of month) / quota(last day of the
     previous month) - 1. This is a MEASURED figure.
  2. Only when the CNPJ is absent (the data we don't have for Albert's advisory share classes)
     or the fund is not found in the base do we fall back to the strategy proxy (CDI/Ibovespa),
     flagged as an estimate.

The pipeline always checks first whether the CNPJ is available (`has_cnpj`) before deciding.

Network calls are cached to build/ and fall back to documented (real, verified) values so a run
stays reproducible offline, the same pattern used for the BCB/Yahoo benchmarks.

CVM dataset: https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_YYYYMM.zip
(columns: CNPJ_FUNDO_CLASSE [legacy CNPJ_FUNDO], DT_COMPTC, VL_QUOTA; ';'-separated, latin-1).
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import re
import zipfile
from typing import Callable, Optional

import requests

from . import config

_CACHE = config.BUILD_DIR / "cvm_cache.json"
_TIMEOUT = 90
_URL = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{ym}.zip"

# Documented offline fallback with REAL values verified against the CVM informe, so a run with a
# CNPJ stays reproducible offline. Keyed "<14-digit cnpj>:YYYY-MM".
# 28.047.174/0001-29, April/2025: quota 13.444799 (31/03) -> 12.274216 (30/04) = -8.707%.
_FALLBACK = {
    "28047174000129:2025-04": -8.707,
}

_NON_DIGIT = re.compile(r"\D")


def normalize_cnpj(cnpj: str | None) -> Optional[str]:
    """Return the 14-digit CNPJ, or None if absent/malformed.

    Accepts both '17.372.737/0001-38' and '17372737000138'. This is the single
    data-availability gate: no valid CNPJ -> the caller proxies the fund.
    """
    if not cnpj:
        return None
    digits = _NON_DIGIT.sub("", str(cnpj))
    return digits if len(digits) == 14 else None


def has_cnpj(position) -> bool:
    """True when a position carries a usable CNPJ (always checked before fetching)."""
    return normalize_cnpj(getattr(position, "cnpj", None)) is not None


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


def last_quota_in_csv(csv_text: str, cnpj14: str) -> Optional[tuple[str, float]]:
    """(last DT_COMPTC, VL_QUOTA) for a fund within one monthly informe, or None.

    Streams the rows (the file holds ~500k lines) keeping only the target CNPJ, and
    returns the quote of its latest available business day in the file.
    """
    reader = csv.reader(io.StringIO(csv_text), delimiter=";")
    header = next(reader, None)
    if not header:
        return None
    cnpj_col = "CNPJ_FUNDO_CLASSE" if "CNPJ_FUNDO_CLASSE" in header else "CNPJ_FUNDO"
    ci, di, qi = header.index(cnpj_col), header.index("DT_COMPTC"), header.index("VL_QUOTA")
    best: Optional[tuple[str, float]] = None
    for row in reader:
        if len(row) <= qi or normalize_cnpj(row[ci]) != cnpj14:
            continue
        quota = row[qi].strip()
        if not quota:
            continue
        when = row[di]
        if best is None or when > best[0]:
            best = (when, float(quota))
    return best


def monthly_return_from_quotas(prev: tuple[str, float] | None,
                               curr: tuple[str, float] | None) -> Optional[float]:
    """Calendar-month % return from the two month-end quotes (None if either is missing)."""
    if not prev or not curr or not prev[1]:
        return None
    return (curr[1] / prev[1] - 1.0) * 100.0


def _fetch_month_csv(ym: str) -> str:
    """Download and unzip one monthly informe to its CSV text (latin-1)."""
    r = requests.get(_URL.format(ym=ym), timeout=_TIMEOUT)
    r.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
    return zf.read(name).decode("latin-1")


def fund_monthly_return(cnpj: str | None, month: dt.date = config.REFERENCE_MONTH,
                        use_cache: bool = True) -> Optional[float]:
    """Measured month return (%) for a fund by CNPJ, from CVM quotas. None -> caller proxies.

    Returns None when the CNPJ is absent/malformed or the fund is not found in the base
    (and there is no documented fallback). Any value returned is a MEASURED figure.
    """
    cnpj14 = normalize_cnpj(cnpj)
    if cnpj14 is None:                      # the data we simply don't have -> proxy
        return None
    key = f"{cnpj14}:{month:%Y-%m}"
    cache = _load_cache()
    if use_cache and key in cache:
        return cache[key]
    try:
        prev_month = (month.replace(day=1) - dt.timedelta(days=1))
        curr = last_quota_in_csv(_fetch_month_csv(f"{month:%Y%m}"), cnpj14)
        prev = last_quota_in_csv(_fetch_month_csv(f"{prev_month:%Y%m}"), cnpj14)
        ret = monthly_return_from_quotas(prev, curr)
        if ret is None:
            raise ValueError("CNPJ not present in CVM informe for the month")
        cache[key] = round(ret, 4)
        _save_cache(cache)
        return cache[key]
    except Exception:
        return _FALLBACK.get(key)           # documented real value, or None -> proxy


def resolver(use_cache: bool = True) -> Callable[[object], Optional[float]]:
    """A position -> measured-return resolver for the profitability engine (real-first)."""
    def _resolve(position) -> Optional[float]:
        return fund_monthly_return(getattr(position, "cnpj", None), use_cache=use_cache)
    return _resolve


if __name__ == "__main__":
    demo = "28.047.174/0001-29"
    print(f"{demo} {config.REFERENCE_MONTH:%Y-%m} -> {fund_monthly_return(demo):+.3f}% (CVM)")
