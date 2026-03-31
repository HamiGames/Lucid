"""
File: /app/tests/test_auth_middleware.py
x-lucid-file-path: /app/tests/test_auth_middleware.py
x-lucid-file-directory: /app/tests
x-lucid-file-type: python
"""

from __future__ import annotations

import importlib
from fastapi.testclient import TestClient

# No top-level `import pytest` to avoid Pylance missing-import noise


def test_app_health_ok():
    # Import via string to avoid static analysis import errors
    main = importlib.import_module("app.main")
    client = TestClient(main.app)
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "service" in data and "status" in data
