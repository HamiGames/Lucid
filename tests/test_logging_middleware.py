# Path: tests/test_logging_middleware.py

from __future__ import annotations
import importlib


def test_logging_middleware_importable():
    mod = importlib.import_module("app.middleware.logging")
    assert mod is not None
