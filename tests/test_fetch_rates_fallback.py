import asyncio

import app.main as main


class _DummyResp:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _DummyAsyncClientFallback:
    """
    Simula:
      - /currencies -> OK
      - /latest con symbols -> 400
      - /latest sin symbols -> 200
    """
    def __init__(self):
        self.latest_calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None):
        params = params or {}

        if "currencies" in url:
            return _DummyResp({"USD": "US Dollar", "EUR": "Euro", "JPY": "Yen"}, 200)

        if "latest" in url:
            self.latest_calls += 1
            if "symbols" in params:
                return _DummyResp({"error": "bad symbols"}, 400)
            return _DummyResp({"base": "USD", "date": "2026-01-19", "rates": {"EUR": 0.9, "JPY": 160.0}}, 200)

        return _DummyResp({}, 404)


class _DummyAsyncClientInvalidPayload:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None):
        if "currencies" in url:
            return _DummyResp(["NOT_A_DICT"], 200)  # payload inválido => {}
        if "latest" in url:
            return _DummyResp(["NOT_A_DICT"], 200)  # payload inválido => default dict
        return _DummyResp({}, 404)


def test_fetch_rates_fallback_when_symbols_call_fails(monkeypatch):
    # fuerza que haya symbols (para entrar al branch)
    monkeypatch.setattr(
        main,
        "CURRENCIES",
        [
            {"country": "US", "flag": "x", "currency": "USD"},
            {"country": "EU", "flag": "x", "currency": "EUR"},
            {"country": "JP", "flag": "x", "currency": "JPY"},
        ],
    )

    dummy = _DummyAsyncClientFallback()
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout=10.0: dummy)

    out = asyncio.run(main.fetch_rates())
    assert out["base"] == "USD"
    assert out["rates"]["EUR"] == 0.9
    assert out["_meta"]["cached"] is False
    assert dummy.latest_calls >= 2  # 1 con symbols (400) + 1 sin symbols (200)


def test_get_supported_currencies_and_fetch_rates_handle_invalid_payload(monkeypatch):
    dummy = _DummyAsyncClientInvalidPayload()
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout=10.0: dummy)

    supported = asyncio.run(main._get_supported_currencies())
    assert supported == {}  # porque payload no era dict

    out = asyncio.run(main.fetch_rates())
    assert isinstance(out, dict)
    assert out.get("base") == main.BASE_CCY
    assert isinstance(out.get("rates"), dict)
