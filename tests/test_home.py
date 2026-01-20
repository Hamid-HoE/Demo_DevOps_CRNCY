from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

import app.main as main

client = TestClient(main.app)


def test_home_renders_context_ok(monkeypatch):
    captured = {}

    def fake_template_response(name, context, status_code=200):
        captured["name"] = name
        captured["context"] = context
        return HTMLResponse("OK", status_code=status_code)

    async def fake_supported():
        return {"USD": "US Dollar", "EUR": "Euro", "JPY": "Yen"}

    async def fake_fetch_rates():
        return {"date": "2026-01-19", "rates": {"EUR": 0.9, "JPY": 160.0}}

    monkeypatch.setattr(main.templates, "TemplateResponse", fake_template_response)
    monkeypatch.setattr(main, "_get_supported_currencies", fake_supported)
    monkeypatch.setattr(main, "fetch_rates", fake_fetch_rates)

    r = client.get("/")
    assert r.status_code == 200
    ctx = captured["context"]
    assert "rows" in ctx
    assert "dropdown" in ctx
    assert ctx["base"] == main.BASE_CCY


def test_home_handles_exception(monkeypatch):
    captured = {}

    def fake_template_response(name, context, status_code=200):
        captured["context"] = context
        return HTMLResponse("OK", status_code=status_code)

    async def fake_supported():
        return {"USD": "US Dollar"}

    async def boom():
        raise Exception("boom")

    monkeypatch.setattr(main.templates, "TemplateResponse", fake_template_response)
    monkeypatch.setattr(main, "_get_supported_currencies", fake_supported)
    monkeypatch.setattr(main, "fetch_rates", boom)

    r = client.get("/")
    assert r.status_code == 200
    assert captured["context"]["error"] is not None
