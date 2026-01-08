from __future__ import annotations

import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

APP_TITLE = "CRNCY - USD FX Dashboard"
BASE_CCY = "USD"

CURRENCIES: List[Dict[str, str]] = [
    {"country": "United States", "flag": "🇺🇸", "currency": "USD"},
    {"country": "Chile", "flag": "🇨🇱", "currency": "CLP"},
    {"country": "Mexico", "flag": "🇲🇽", "currency": "MXN"},
    {"country": "Guatemala", "flag": "🇬🇹", "currency": "GTQ"},
    {"country": "Honduras", "flag": "🇭🇳", "currency": "HNL"},
    {"country": "Costa Rica", "flag": "🇨🇷", "currency": "CRC"},
    {"country": "Belize", "flag": "🇧🇿", "currency": "BZD"},
]

# Cache simple con TTL, pero por "clave" (latest/timeseries) para no pisarse.
_CACHE_TTL_SECONDS = 600
_cache: Dict[str, Dict[str, Any]] = {}

# Frankfurter (tu endpoint actual)
FRANKFURTER_LATEST_URL = "https://api.frankfurter.dev/v1/latest"
# Fallback para timeseries (por si /v1 no soporta rango en tu instancia)
FRANKFURTER_APP_BASE = "https://api.frankfurter.app"

# ---- Paths robustos ----
BASE_DIR = Path(__file__).resolve().parent  # .../src/app
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title=APP_TITLE)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


def _cache_get(key: str) -> Optional[Dict[str, Any]]:
    entry = _cache.get(key)
    if not entry:
        return None
    now = time.time()
    if (now - float(entry["ts"])) < _CACHE_TTL_SECONDS:
        return entry["payload"]
    return None


def _cache_get_stale(key: str) -> Optional[Dict[str, Any]]:
    entry = _cache.get(key)
    return entry["payload"] if entry else None


def _cache_set(key: str, payload: Dict[str, Any]) -> None:
    _cache[key] = {"ts": time.time(), "payload": payload}


def _symbols_from_currencies() -> List[str]:
    return sorted({c["currency"] for c in CURRENCIES if c["currency"] != BASE_CCY})


async def _http_get_json(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict):
            raise HTTPException(status_code=502, detail="Upstream returned invalid payload")
        return data


async def fetch_latest(base: str = BASE_CCY, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
    if symbols is None:
        symbols = _symbols_from_currencies()

    symbols = sorted(set([s.upper() for s in symbols if s and s.upper() != base.upper()]))
    key = f"latest:{base.upper()}:{','.join(symbols)}"

    cached = _cache_get(key)
    if cached:
        return cached

    params = {"base": base.upper(), "symbols": ",".join(symbols)} if symbols else {"base": base.upper()}

    try:
        payload = await _http_get_json(FRANKFURTER_LATEST_URL, params=params)
        payload["_meta"] = {
            "cached": False,
            "cache_ttl_seconds": _CACHE_TTL_SECONDS,
            "source": "frankfurter.dev/v1/latest",
        }
        _cache_set(key, payload)
        return payload
    except Exception as ex:
        stale = _cache_get_stale(key)
        if stale:
            stale = dict(stale)
            stale["_meta"] = {
                "cached": True,
                "stale": True,
                "cache_ttl_seconds": _CACHE_TTL_SECONDS,
                "source": "cache_fallback",
                "error": str(ex),
            }
            return stale
        raise HTTPException(status_code=502, detail=f"Unable to fetch latest FX rates: {ex}")


def _get_rate_for(code: str, base: str, latest_payload: Dict[str, Any]) -> float:
    code = code.upper()
    base = base.upper()
    if code == base:
        return 1.0
    rates = latest_payload.get("rates", {})
    rate = rates.get(code)
    if rate is None:
        raise HTTPException(status_code=400, detail=f"Rate not available for {code}")
    try:
        return float(rate)
    except Exception:
        raise HTTPException(status_code=502, detail=f"Invalid rate for {code}")


def _convert(amount: float, from_ccy: str, to_ccy: str, base: str, latest_payload: Dict[str, Any]) -> Tuple[float, float, float]:
    """
    Conversión cross usando base. latest_payload está en 'base'.
      - rate(X) = 1 base -> X
      - amount from -> base -> to
    """
    from_ccy = from_ccy.upper()
    to_ccy = to_ccy.upper()
    base = base.upper()

    if amount < 0:
        raise HTTPException(status_code=400, detail="amount must be >= 0")

    rate_from = _get_rate_for(from_ccy, base, latest_payload)
    rate_to = _get_rate_for(to_ccy, base, latest_payload)

    # Si from es base: base->to = amount * rate_to
    if from_ccy == base:
        converted = amount * rate_to
        fx = rate_to
        return converted, fx, 1.0

    # Si to es base: from->base = amount / rate_from
    if to_ccy == base:
        converted = amount / rate_from
        fx = 1.0 / rate_from
        return converted, fx, rate_from

    # Cross: from->base -> to
    amount_in_base = amount / rate_from
    converted = amount_in_base * rate_to
    fx = rate_to / rate_from  # 1 from -> to
    return converted, fx, rate_from


async def fetch_timeseries(base: str, symbol: str, days: int = 30) -> Dict[str, Any]:
    base = base.upper()
    symbol = symbol.upper()
    if days < 2 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 2 and 365")

    end = date.today()
    start = end - timedelta(days=days)

    key = f"ts:{base}:{symbol}:{start.isoformat()}:{end.isoformat()}"
    cached = _cache_get(key)
    if cached:
        return cached

    # Intento 1: frankfurter.app (histórico por rango conocido)
    # GET /YYYY-MM-DD..YYYY-MM-DD?from=USD&to=CLP
    url1 = f"{FRANKFURTER_APP_BASE}/{start.isoformat()}..{end.isoformat()}"
    params1 = {"from": base, "to": symbol}

    # Intento 2 (fallback): algunos despliegues usan base/symbols
    url2 = f"{FRANKFURTER_APP_BASE}/{start.isoformat()}..{end.isoformat()}"
    params2 = {"base": base, "symbols": symbol}

    last_err: Optional[Exception] = None
    for url, params in [(url1, params1), (url2, params2)]:
        try:
            payload = await _http_get_json(url, params=params)
            payload["_meta"] = {
                "cached": False,
                "cache_ttl_seconds": _CACHE_TTL_SECONDS,
                "source": "frankfurter.app/timeseries",
            }
            _cache_set(key, payload)
            return payload
        except Exception as ex:
            last_err = ex

    stale = _cache_get_stale(key)
    if stale:
        stale = dict(stale)
        stale["_meta"] = {
            "cached": True,
            "stale": True,
            "cache_ttl_seconds": _CACHE_TTL_SECONDS,
            "source": "cache_fallback",
            "error": str(last_err),
        }
        return stale

    raise HTTPException(status_code=502, detail=f"Unable to fetch timeseries: {last_err}")


@app.get("/api/currencies")
def api_currencies() -> JSONResponse:
    return JSONResponse({"base": BASE_CCY, "currencies": CURRENCIES})


@app.get("/api/rates")
async def api_rates() -> JSONResponse:
    payload = await fetch_latest()
    return JSONResponse(payload)


@app.get("/api/convert")
async def api_convert(
    amount: float = Query(..., ge=0),
    from_ccy: str = Query(..., min_length=3, max_length=3),
    to_ccy: str = Query(..., min_length=3, max_length=3),
) -> JSONResponse:
    latest = await fetch_latest(symbols=list({from_ccy.upper(), to_ccy.upper()} - {BASE_CCY}))
    converted, fx, rate_from = _convert(amount, from_ccy, to_ccy, BASE_CCY, latest)

    return JSONResponse(
        {
            "base": BASE_CCY,
            "from": from_ccy.upper(),
            "to": to_ccy.upper(),
            "amount": amount,
            "converted": round(converted, 6),
            "fx_rate": round(fx, 10),          # 1 FROM -> TO
            "rate_from_vs_base": round(rate_from, 10),  # 1 BASE -> FROM
            "date": latest.get("date"),
            "meta": latest.get("_meta", {}),
        }
    )


@app.get("/api/timeseries")
async def api_timeseries(
    symbol: str = Query(..., min_length=3, max_length=3),
    days: int = Query(30, ge=2, le=365),
) -> JSONResponse:
    symbol = symbol.upper()
    if symbol == BASE_CCY:
        raise HTTPException(status_code=400, detail="symbol must be different from base")

    payload = await fetch_timeseries(base=BASE_CCY, symbol=symbol, days=days)

    rates_by_day = payload.get("rates", {})
    # Normalizamos a lista ordenada: [{"date": "...", "value": ...}]
    points = []
    for d, obj in rates_by_day.items():
        try:
            value = obj.get(symbol)
        except Exception:
            value = None
        if value is None:
            continue
        points.append({"date": d, "value": float(value)})

    points.sort(key=lambda x: x["date"])
    return JSONResponse(
        {
            "base": BASE_CCY,
            "symbol": symbol,
            "days": days,
            "points": points,
            "meta": payload.get("_meta", {}),
        }
    )


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    error = None
    data: Optional[Dict[str, Any]] = None

    try:
        data = await fetch_latest()
    except Exception as ex:
        error = str(ex)

    rates = (data or {}).get("rates", {}) if isinstance(data, dict) else {}
    fx_date = (data or {}).get("date") if isinstance(data, dict) else None
    meta = (data or {}).get("_meta", {}) if isinstance(data, dict) else {}

    rows = []
    for c in CURRENCIES:
        code = c["currency"]
        rate = 1.0 if code == BASE_CCY else rates.get(code)
        rows.append({**c, "rate": rate})

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": APP_TITLE,
            "base": BASE_CCY,
            "date": fx_date,
            "rows": rows,
            "error": error,
            "meta": meta,
            "currencies": CURRENCIES,
        },
    )
