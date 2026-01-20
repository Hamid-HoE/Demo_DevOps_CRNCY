from fastapi.testclient import TestClient

import app.main as main

client = TestClient(main.app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_api_version_has_expected_keys():
    r = client.get("/api/version")
    assert r.status_code == 200
    data = r.json()
    for k in ["app", "base", "build_tag", "git_sha", "build_time_utc"]:
        assert k in data


def test_api_convert_success(monkeypatch):
    async def fake_fetch_rates():
        return {"date": "2026-01-19", "rates": {"EUR": 0.8, "JPY": 160.0}}

    async def fake_supported():
        return {"USD": "US Dollar", "EUR": "Euro", "JPY": "Yen"}

    monkeypatch.setattr(main, "fetch_rates", fake_fetch_rates)
    monkeypatch.setattr(main, "_get_supported_currencies", fake_supported)

    r = client.get("/api/convert?amount=8&from=EUR&to=JPY")
    assert r.status_code == 200
    assert r.json()["result"] == 1600.0


def test_api_convert_unsupported_currency(monkeypatch):
    async def fake_fetch_rates():
        return {"date": "2026-01-19", "rates": {"EUR": 0.8}}

    async def fake_supported():
        return {"USD": "US Dollar", "EUR": "Euro"}  # JPY no soportada

    monkeypatch.setattr(main, "fetch_rates", fake_fetch_rates)
    monkeypatch.setattr(main, "_get_supported_currencies", fake_supported)

    r = client.get("/api/convert?amount=10&from=JPY&to=USD")
    assert r.status_code == 400


def test_api_convert_same_currency_returns_amount(monkeypatch):
    async def fake_fetch_rates():
        return {"date": "2026-01-19", "rates": {"EUR": 0.8}}

    async def fake_supported():
        return {"USD": "US Dollar", "EUR": "Euro"}

    monkeypatch.setattr(main, "fetch_rates", fake_fetch_rates)
    monkeypatch.setattr(main, "_get_supported_currencies", fake_supported)

    r = client.get("/api/convert?amount=10&from=USD&to=USD")
    assert r.status_code == 200
    assert r.json()["result"] == 10.0


def test_api_convert_rate_not_available_returns_422(monkeypatch):
    async def fake_fetch_rates():
        return {"date": "2026-01-19", "rates": {"EUR": 0.8}}  # no JPY

    async def fake_supported():
        return {"USD": "US Dollar", "EUR": "Euro", "JPY": "Yen"}

    monkeypatch.setattr(main, "fetch_rates", fake_fetch_rates)
    monkeypatch.setattr(main, "_get_supported_currencies", fake_supported)

    r = client.get("/api/convert?amount=10&from=EUR&to=JPY")
    assert r.status_code == 422
