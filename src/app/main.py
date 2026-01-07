from __future__ import annotations

import time
from typing import Any, Dict, List

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

APP_TITLE = "CRNCY - USD FX Dashboard"
BASE_CCY = "USD"

# Lista “demo” (puedes ajustar países/monedas)
CURRENCIES: List[Dict[str, str]] = [
    {"country": "United States", "flag": "🇺🇸", "currency": "USD"},
    {"country": "Chile", "flag": "🇨🇱", "currency": "CLP"},
    {"country": "Mexico", "flag": "🇲🇽", "currency": "MXN"},
    {"country": "Guatemala", "flag": "🇬🇹", "currency": "GTQ"},
    {"country": "Honduras", "flag": "🇭🇳", "currency": "HNL"},
    {"country": "Costa Rica", "flag": "🇨🇷", "currency": "CRC"},
    {"country": "Belize", "flag": "🇧🇿", "currency": "BZD"},
]

# Cache simple para reducir consumo
_CACHE_TTL_SECONDS = 600
_cache: Dict[str, Any] = {"ts": 0.0, "payload": None}

FRANKFURTER_URL = "https://api.frankfurter.dev/v1/latest"  # API pública 

app = FastAPI(title=APP_TITLE)

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


async def fetch_rates() -> Dict[str, Any]:
    now = time.time()
    if _cache["payload"] is not None and (now - float(_cache["ts"])) < _CACHE_TTL_SECONDS:
        return _cache["payload"]

    symbols = ",".join(sorted({c["currency"] for c in CURRENCIES if c["currency"] != BASE_CCY}))
    params = {"base": BASE_CCY, "symbols": symbols}

    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(FRANKFURTER_URL, params=params)
        r.raise_for_status()
        payload = r.json()

    _cache["ts"] = now
    _cache["payload"] = payload
    return payload


@app.get("/api/rates")
async def api_rates() -> JSONResponse:
    payload = await fetch_rates()
    return JSONResponse(payload)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    error = None
    data = None
    try:
        data = await fetch_rates()
    except Exception as ex:
        error = str(ex)

    # Normalizamos para el template
    rates = (data or {}).get("rates", {}) if isinstance(data, dict) else {}
    date = (data or {}).get("date") if isinstance(data, dict) else None

    rows = []
    for c in CURRENCIES:
        code = c["currency"]
        if code == BASE_CCY:
            rate = 1.0
        else:
            rate = rates.get(code)
        rows.append({**c, "rate": rate})

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": APP_TITLE,
            "base": BASE_CCY,
            "date": date,
            "rows": rows,
            "error": error,
        },
    )
