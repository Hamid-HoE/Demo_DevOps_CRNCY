from __future__ import annotations

import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

APP_TITLE = "CRNCY - USD FX Dashboard"
BASE_CCY = "USD"

# Monedas demo (todas soportadas por Frankfurter/ECB normalmente)
# Si agregas una no soportada, el sistema la marcará como unsupported automáticamente.
CURRENCIES: List[Dict[str, str]] = [
    {"country": "United States", "flag": "🇺🇸", "currency": "USD"},
    {"country": "Eurozone", "flag": "🇪🇺", "currency": "EUR"},
    {"country": "United Kingdom", "flag": "🇬🇧", "currency": "GBP"},
    {"country": "Japan", "flag": "🇯🇵", "currency": "JPY"},
    {"country": "Mexico", "flag": "🇲🇽", "currency": "MXN"},
    {"country": "Brazil", "flag": "🇧🇷", "currency": "BRL"},
    {"country": "Canada", "flag": "🇨🇦", "currency": "CAD"},
    {"country": "Australia", "flag": "🇦🇺", "currency": "AUD"},
    {"country": "Switzerland", "flag": "🇨🇭", "currency": "CHF"},
    {"country": "South Africa", "flag": "🇿🇦", "currency": "ZAR"},
]

FRANKFURTER_LATEST_URL = "https://api.frankfurter.dev/v1/latest"
FRANKFURTER_CCY_URL = "https://api.frankfurter.dev/v1/currencies"

# Cache
_RATES_TTL_SECONDS = 600
_CCY_TTL_SECONDS = 24 * 3600
_cache: Dict[str, Any] = {
    "rates_ts": 0.0,
    "rates_payload": None,
    "ccy_ts": 0.0,
    "ccy_payload": None,
    "trend": {},  # key: (base, sym, days) -> (ts, payload)
}

# ---- Paths robustos ----
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title=APP_TITLE)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), shows_directory=False, name="static")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


async def _get_supported_currencies() -> Dict[str, str]:
    now = time.time()
    if _cache["ccy_payload"] is not None and (now - float(_cache["ccy_ts"])) < _CCY_TTL_SECONDS:
        return _cache["ccy_payload"]

    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(FRANKFURTER_CCY_URL)
        r.raise_for_status()
        payload = r.json()

    if not isinstance(payload, dict):
        payload = {}

    _cache["ccy_ts"] = now
    _cache["ccy_payload"] = payload
    return payload


def _symbols_from_config(supported: Dict[str, str]) -> List[str]:
    desired = sorted({c["currency"] for c in CURRENCIES if c["currency"] != BASE_CCY})
    return [ccy for ccy in desired if (ccy in supported)]


async def fetch_rates() -> Dict[str, Any]:
    now = time.time()
    if _cache["rates_payload"] is not None and (now - float(_cache["rates_ts"])) < _RATES_TTL_SECONDS:
        payload = dict(_cache["rates_payload"])
        payload["_meta"] = {"cached": True, "cache_ttl_seconds": _RATES_TTL_SECONDS, "source": "frankfurter.dev/v1/latest"}
        return payload

    supported = await _get_supported_currencies()
    symbols = _symbols_from_config(supported)

    params: Dict[str, str] = {"base": BASE_CCY}
    if symbols:
        params["symbols"] = ",".join(symbols)

    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(FRANKFURTER_LATEST_URL, params=params)
        # Si por alguna razón falla con symbols, hacemos fallback sin symbols
        if r.status_code >= 400 and "symbols" in params:
            r = await client.get(FRANKFURTER_LATEST_URL, params={"base": BASE_CCY})
        r.raise_for_status()
        payload = r.json()

    if not isinstance(payload, dict):
        payload = {"base": BASE_CCY, "date": None, "rates": {}}

    # Filtra a lo que usamos
    rates = payload.get("rates", {}) if isinstance(payload.get("rates"), dict) else {}
    if symbols:
        rates = {k: v for k, v in rates.items() if k in set(symbols)}

    payload["rates"] = rates
    payload["_meta"] = {"cached": False, "cache_ttl_seconds": _RATES_TTL_SECONDS, "source": "frankfurter.dev/v1/latest"}

    _cache["rates_ts"] = now
    _cache["rates_payload"] = payload
    return payload


def _to_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def _compute_cross(amount: float, from_ccy: str, to_ccy: str, rates: Dict[str, Any]) -> Optional[float]:
    from_ccy = from_ccy.upper().strip()
    to_ccy = to_ccy.upper().strip()

    if from_ccy == to_ccy:
        return amount

    # rates están como BASE_CCY -> X
    # USD->X = rate[X]
    # X->USD = 1/rate[X]
    if from_ccy == BASE_CCY:
        r_to = _to_float(rates.get(to_ccy))
        return amount * r_to if r_to else None

    if to_ccy == BASE_CCY:
        r_from = _to_float(rates.get(from_ccy))
        return (amount / r_from) if r_from else None

    r_from = _to_float(rates.get(from_ccy))
    r_to = _to_float(rates.get(to_ccy))
    if not r_from or not r_to:
        return None

    # amount(from)->USD -> to
    usd_amount = amount / r_from
    return usd_amount * r_to


@app.get("/api/rates")
async def api_rates() -> JSONResponse:
    payload = await fetch_rates()
    return JSONResponse(payload)


@app.get("/api/convert")
async def api_convert(
    amount: float = Query(..., gt=0),
    from_ccy: str = Query(..., alias="from"),
    to_ccy: str = Query(..., alias="to"),
) -> JSONResponse:
    data = await fetch_rates()
    rates = data.get("rates", {}) if isinstance(data, dict) else {}

    # En base USD, el USD no viene en rates. Lo manejamos.
    supported = await _get_supported_currencies()
    supported_set = set(supported.keys()) | {BASE_CCY}

    from_ccy_u = from_ccy.upper().strip()
    to_ccy_u = to_ccy.upper().strip()

    if from_ccy_u not in supported_set or to_ccy_u not in supported_set:
        return JSONResponse(
            {"error": "Unsupported currency by Frankfurter/ECB", "from": from_ccy_u, "to": to_ccy_u},
            status_code=400,
        )

    value = _compute_cross(amount, from_ccy_u, to_ccy_u, rates)
    if value is None:
        return JSONResponse(
            {"error": "Rate not available for selected pair", "from": from_ccy_u, "to": to_ccy_u},
            status_code=422,
        )

    return JSONResponse(
        {
            "amount": amount,
            "from": from_ccy_u,
            "to": to_ccy_u,
            "result": round(value, 6),
            "base": BASE_CCY,
            "fx_date": data.get("date"),
        }
    )


async def _fetch_trend(base: str, symbol: str, days: int) -> Dict[str, Any]:
    base = base.upper().strip()
    symbol = symbol.upper().strip()
    days = max(7, min(days, 180))

    key = (base, symbol, days)
    now = time.time()
    entry = _cache["trend"].get(key)
    if entry:
        ts, payload = entry
        if (now - float(ts)) < _RATES_TTL_SECONDS:
            return payload

    end = date.today()
    start = end - timedelta(days=days)

    url = f"https://api.frankfurter.dev/v1/{start.isoformat()}..{end.isoformat()}"
    params = {"base": base, "symbols": symbol}

    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        payload = r.json()

    if not isinstance(payload, dict):
        payload = {"rates": {}}

    rates_by_day = payload.get("rates", {}) if isinstance(payload.get("rates"), dict) else {}
    points: List[Tuple[str, float]] = []
    for d, v in rates_by_day.items():
        if isinstance(v, dict) and symbol in v:
            fv = _to_float(v.get(symbol))
            if fv is not None:
                points.append((d, fv))
    points.sort(key=lambda x: x[0])

    out = {
        "base": base,
        "symbol": symbol,
        "days": days,
        "points": [{"date": d, "rate": r} for d, r in points],
        "_meta": {"source": "frankfurter.dev/v1/timeseries"},
    }
    _cache["trend"][key] = (now, out)
    return out


@app.get("/api/trend")
async def api_trend(symbol: str, days: int = 30) -> JSONResponse:
    # base fijo USD para el dashboard
    out = await _fetch_trend(BASE_CCY, symbol, days)
    return JSONResponse(out)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    error = None
    data: Optional[Dict[str, Any]] = None
    supported: Dict[str, str] = {}

    try:
        supported = await _get_supported_currencies()
        data = await fetch_rates()
    except Exception as ex:
        error = str(ex)

    rates = (data or {}).get("rates", {}) if isinstance(data, dict) else {}
    fx_date = (data or {}).get("date") if isinstance(data, dict) else None
    supported_set = set(supported.keys()) | {BASE_CCY}

    rows = []
    for c in CURRENCIES:
        code = c["currency"]
        is_supported = code in supported_set
        rate = 1.0 if code == BASE_CCY else rates.get(code)
        rows.append({**c, "rate": rate, "supported": is_supported})

    # Dropdowns: sólo las soportadas (para que nunca explote el converter)
    dropdown = [r for r in rows if r["supported"]]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": APP_TITLE,
            "base": BASE_CCY,
            "date": fx_date,
            "rows": rows,
            "dropdown": dropdown,
            "error": error,
        },
    )
