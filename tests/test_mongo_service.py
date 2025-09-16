# Path: tests/test_mongo_service.py

from __future__ import annotations
import importlib


def test_mongo_service_api_surface():
    svc = importlib.import_module("app.services.mongo_service")
    assert hasattr(svc, "get_client")
    assert hasattr(svc, "get_db")
    assert hasattr(svc, "ping")
