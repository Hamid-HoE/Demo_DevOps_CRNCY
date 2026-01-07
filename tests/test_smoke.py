import sys
sys.path.append("src")

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_rates_ok():
    r = client.get("/api/rates")
    assert r.status_code == 200
    body = r.json()
    assert body["base"] == "USD"
    assert "rates" in body
