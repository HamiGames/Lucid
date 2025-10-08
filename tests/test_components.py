# Path: tests/test_components.py

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

def test_imports():
    """Test that all components can be imported."""
    try:
        from node import NodeManager, PeerDiscovery
        from sessions import SessionRecorder, ChunkManager, EncryptionManager
        from wallet import WalletManager  
        from admin import AdminManager
        from user import UserManager
        from vm import VMManager
        from storage import MongoVolumeManager
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import components: {e}")


@pytest.mark.asyncio
async def test_node_manager():
    """Test node manager initialization."""
    from node import create_node_config, NodeManager
    
    # Mock database
    mock_db = MagicMock()
    
    # Create test config
    config = create_node_config(role="worker")
    
    # Test node manager creation
    node_manager = NodeManager(config, mock_db)
    assert node_manager.config.role == "worker"
    assert not node_manager.running


@pytest.mark.asyncio 
async def test_session_recorder():
    """Test session recorder."""
    from sessions import SessionRecorder
    
    # Mock database
    mock_db = AsyncMock()
    
    recorder = SessionRecorder(mock_db)
    assert recorder.db is mock_db
    assert len(recorder.active_sessions) == 0
