# Path: tests/test_mongo_service.py
import pytest
from ..api.app.services import mongo_service


@pytest.mark.asyncio
async def test_ping(monkeypatch):
    async def fake_command(cmd):
        return {"ok": 1}

    client = mongo_service.get_client()
    monkeypatch.setattr(client.admin, "command", fake_command)
    ok, latency = await mongo_service.ping()
    assert ok is True
    assert latency >= 0
