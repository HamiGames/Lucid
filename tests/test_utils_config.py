# Path: tests/test_utils_config.py
from ..api.app.utils import config


def test_load_config(monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://test")
    cfg = config.load_config()
    assert cfg.mongo_uri == "mongodb://test"
