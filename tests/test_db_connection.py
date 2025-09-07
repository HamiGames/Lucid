# Path: tests/test_db_connection.py
import pytest
from ..api.app.db import connection


@pytest.mark.asyncio
async def test_ping_returns_tuple(monkeypatch):
    async def fake_command(cmd):
        return {"ok": 1}

    client = connection.get_client()
    monkeypatch.setattr(client.admin, "command", fake_command)
    ok, latency = await connection.ping()
    assert isinstance(ok, bool)
    assert isinstance(latency, float)
