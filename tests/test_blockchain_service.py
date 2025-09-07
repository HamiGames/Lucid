# Path: tests/test_blockchain_service.py
import pytest
from ..api.app.services import blockchain_service


@pytest.mark.asyncio
async def test_node_health_disabled(monkeypatch):
    monkeypatch.setenv("BLOCK_RPC_URL", "")
    result = await blockchain_service.node_health()
    assert result["status"] == "disabled"
