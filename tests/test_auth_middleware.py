# Path: tests/test_auth_middleware.py
from fastapi import FastAPI
from fastapi.testclient import TestClient
from ..api.app.middleware.auth import AuthMiddleware


def create_app():
    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/secure")
    def secure():
        return {"ok": True}

    return app


def test_auth_blocked(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret")
    app = create_app()
    client = TestClient(app)
    r = client.get("/secure")
    assert r.status_code == 401
