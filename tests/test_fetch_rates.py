import asyncio
import app.main as main


class _DummyResp:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _DummyAsyncClient:
    def __init__(self, payload):
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None):
        return _DummyResp(self._payload, 200)


def test_fetch_rates_first_call_not_cached(monkeypatch):
    # Reduce el set para que el filtrado sea estable en test
    monkeypatch.setattr(
        main,
        "CURRENCIES",
        [
            {"country": "US", "flag": "x", "currency": "USD"},
            {"country": "EU", "flag": "x", "currency": "EUR"},
            {"country": "JP", "flag": "x", "currency": "JPY"},
        ],
    )

    async def fake_supported():
        return {"USD": "US Dollar", "EUR": "Euro", "JPY": "Yen"}

    monkeypatch.setattr(main, "_get_supported_currencies", fake_supported)

    payload = {"base": "USD", "date": "2026-01-19", "rates": {"EUR": 0.9, "JPY": 160.0}}
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout=10.0: _DummyAsyncClient(payload))

    out = asyncio.run(main.fetch_rates())
    assert out["base"] == "USD"
    assert out["rates"]["EUR"] == 0.9
    assert out["_meta"]["cached"] is False


def test_fetch_rates_second_call_cached(monkeypatch):
    # Pre-carga cache como si ya hubiera corrido
    main._cache["rates_ts"] = 9999999999.0  # en el futuro, para forzar "cached"
    main._cache["rates_payload"] = {"base": "USD", "date": "2026-01-19", "rates": {"EUR": 0.9}}

    out = asyncio.run(main.fetch_rates())
    assert out["_meta"]["cached"] is True
    assert out["rates"]["EUR"] == 0.9
