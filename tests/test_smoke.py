from fastapi.testclient import TestClient

import app.main as main

client = TestClient(main.app)


class _DummyResp:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _DummyAsyncClient:
    def __init__(self):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None):
        self.calls.append((url, params))
        if "currencies" in url:
            return _DummyResp({"USD": "US Dollar", "EUR": "Euro", "JPY": "Yen"}, 200)
        if "latest" in url:
            return _DummyResp({"base": "USD", "date": "2026-01-19", "rates": {"EUR": 0.9, "JPY": 160.0}}, 200)
        return _DummyResp({}, 404)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_rates_ok_offline_and_cached(monkeypatch):
    dummy = _DummyAsyncClient()
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout=10.0: dummy)

    r1 = client.get("/api/rates")
    assert r1.status_code == 200
    b1 = r1.json()
    assert b1["base"] == "USD"
    assert "_meta" in b1
    assert b1["_meta"]["cached"] is False

    r2 = client.get("/api/rates")
    assert r2.status_code == 200
    b2 = r2.json()
    assert b2["_meta"]["cached"] is True
