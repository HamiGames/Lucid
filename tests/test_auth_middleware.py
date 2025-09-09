import pytest
from starlette.testclient import TestClient
from api.app.main import create_app


def test_auth_blocked(monkeypatch):
    # Simulate an API key required by the environment
    monkeypatch.setenv("API_KEY", "secret")

    app = create_app()
    client = TestClient(app)

    # Without the x-api-key header, should be blocked
    r = client.get("/secure")
    assert r.status_code == 401
    assert r.json() == {"detail": "Unauthorized"}


def test_auth_success(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret")

    app = create_app()
    client = TestClient(app)

    # With the correct header, request should pass
    r = client.get("/secure", headers={"x-api-key": "secret"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
