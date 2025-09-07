# Path: tests/test_logging_middleware.py
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.app.middleware.logging import LoggingMiddleware


def create_app():
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/ping")
    def ping():
        return {"pong": True}

    return app


def test_logging_request(capsys):
    app = create_app()
    client = TestClient(app)
    r = client.get("/ping")
    assert r.status_code == 200
