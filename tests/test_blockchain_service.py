# Path: tests/test_blockchain_service.py

from __future__ import annotations

import asyncio
from blockchain.core.storage import Storage
from blockchain.core.node import Node


def test_storage_api_surface():
    s = Storage(db=None)  # explicit for strict type checkers
    assert hasattr(s, "is_ready")
    assert hasattr(s, "save_block")
    assert hasattr(s, "get_block_by_hash")


def test_node_constructs_without_db():
    n = Node()  # uses Storage(None) internally
    assert isinstance(n.is_ready(), bool)


def test_node_methods_are_coroutines():
    n = Node()
    assert asyncio.iscoroutinefunction(n.bootstrap)
    assert asyncio.iscoroutinefunction(n.submit_block)
    assert asyncio.iscoroutinefunction(n.get_block)
