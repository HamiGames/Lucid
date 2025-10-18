# Path: tests/test_health.py

from __future__ import annotations
import importlib
from fastapi.testclient import TestClient


def test_health_endpoint_ok():
    main = importlib.import_module("app.main")  # via conftest sys.path
    client = TestClient(main.app)
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "service" in data and "status" in data and "db" in data
