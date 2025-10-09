# Path: tests/test_models.py

from __future__ import annotations
import importlib


def test_models_importable():
    user_mod = importlib.import_module("app.db.models.user")
    session_mod = importlib.import_module("app.db.models.session")
    assert user_mod is not None and session_mod is not None
