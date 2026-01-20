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


class _DummyAsyncClientTrend:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None):
        self.calls += 1
        return _DummyResp(self.payload, 200)


def test_fetch_trend_clamps_days_and_caches(monkeypatch):
    payload = {
        "rates": {
            "2026-01-18": {"EUR": 1.1},
            "2026-01-19": {"EUR": 1.2},
        }
    }
    dummy = _DummyAsyncClientTrend(payload)
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout=10.0: dummy)

    out1 = asyncio.run(main._fetch_trend("USD", "EUR", 1))  # clamp => 7
    assert out1["base"] == "USD"
    assert out1["symbol"] == "EUR"
    assert out1["days"] == 7
    assert len(out1["points"]) == 2
    assert dummy.calls == 1

    out2 = asyncio.run(main._fetch_trend("USD", "EUR", 1))
    assert out2["days"] == 7
    assert dummy.calls == 1  # cache hit

    out3 = asyncio.run(main._fetch_trend("USD", "EUR", 999))  # clamp => 180
    assert out3["days"] == 180
