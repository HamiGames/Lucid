# Path: tests/test_utils_config.py

from __future__ import annotations
import importlib


def test_utils_importable():
    mod = importlib.import_module("app.utils")
    assert mod is not None
