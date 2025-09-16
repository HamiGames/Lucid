# Path: tests/test_db_connection.py

from __future__ import annotations
import asyncio
import importlib


def test_mongo_ping_returns_bool():
    svc = importlib.import_module("app.services.mongo_service")
    ok = asyncio.run(svc.ping())
    assert isinstance(ok, bool)
