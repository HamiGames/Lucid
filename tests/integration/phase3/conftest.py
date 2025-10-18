"""
Phase 3 Integration Test Configuration

This module provides shared fixtures and configuration for Phase 3 integration tests.
It sets up test environments for session management, RDP services, and node management.
"""

import pytest
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, Mock, patch
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.testclient import TestClient

# Import application modules
from sessions.api.main import app as session_app
from RDP.server_manager.main import app as rdp_app
from node.main import app as node_app

# Test database configuration
TEST_DATABASE_URL = "mongodb://localhost:27017/lucid_phase3_test"
TEST_REDIS_URL = "redis://localhost:6379/15"

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def test_db():
    """Create test database connection."""
    client = AsyncIOMotorClient(TEST_DATABASE_URL)
    db = client.get_default_database()
    
    yield db
    
    # Cleanup
    await client.drop_database(db.name)
    client.close()

@pytest.fixture(scope="function")
def test_redis():
    """Create test Redis connection."""
    import fakeredis
    redis_client = fakeredis.FakeRedis()
    yield redis_client
    redis_client.flushall()

@pytest.fixture
def session_client():
    """Create session management test client."""
    return TestClient(session_app)

@pytest.fixture
def rdp_client():
    """Create RDP services test client."""
    return TestClient(rdp_app)

@pytest.fixture
def node_client():
    """Create node management test client."""
    return TestClient(node_app)

@pytest.fixture
def auth_headers():
    """Generate authentication headers for testing."""
    return {
        "Authorization": "Bearer test_jwt_token_phase3",
        "X-User-ID": "test-user-123",
        "X-User-Roles": "session_manager,rdp_operator,node_operator"
    }

@pytest.fixture
def sample_session_data():
    """Sample session data for testing."""
    return {
        "name": "Phase 3 Integration Test Session",
        "description": "Test session for Phase 3 integration testing",
        "rdp_config": {
            "host": "192.168.1.100",
            "port": 3389,
            "username": "testuser",
            "domain": "TESTDOMAIN",
            "use_tls": True,
            "ignore_cert": False
        },
        "recording_config": {
            "frame_rate": 30,
            "resolution": "1920x1080",
            "quality": "high",
            "compression": "zstd",
            "audio_enabled": True,
            "cursor_enabled": True
        },
        "storage_config": {
            "retention_days": 30,
            "max_size_gb": 10,
            "encryption_enabled": True,
            "compression_enabled": True,
            "backup_enabled": False,
            "archive_enabled": False
        },
        "metadata": {
            "project": "lucid-phase3-test",
            "environment": "integration",
            "tags": ["test", "integration", "phase3"],
            "owner": "test-user-123",
            "priority": "normal"
        }
    }

@pytest.fixture
def sample_rdp_server_data():
    """Sample RDP server data for testing."""
    return {
        "name": "Phase 3 Integration Test Server",
        "description": "Test RDP server for Phase 3 integration testing",
        "user_id": "test-user-123",
        "configuration": {
            "desktop_environment": "xfce",
            "resolution": "1920x1080",
            "color_depth": 24,
            "use_tls": True
        },
        "resources": {
            "cpu_limit": 2.0,
            "memory_limit": 4096,
            "disk_limit": 20480,
            "network_bandwidth": 1000
        }
    }

@pytest.fixture
def sample_node_data():
    """Sample node data for testing."""
    return {
        "name": "phase3-test-node-001",
        "node_type": "worker",
        "hardware_info": {
            "cpu": {
                "cores": 8,
                "frequency_mhz": 3200,
                "architecture": "x86_64"
            },
            "memory": {
                "total_bytes": 17179869184,  # 16GB
                "type": "DDR4"
            },
            "storage": {
                "total_bytes": 1099511627776,  # 1TB
                "type": "SSD",
                "interface": "NVMe"
            },
            "network": [
                {
                    "interface": "eth0",
                    "speed_mbps": 1000,
                    "mac_address": "00:11:22:33:44:55"
                }
            ]
        },
        "location": {
            "country": "US",
            "region": "CA",
            "city": "San Francisco",
            "timezone": "America/Los_Angeles"
        },
        "initial_pool_id": "pool_workers",
        "configuration": {
            "max_sessions": 10,
            "resource_limits": {
                "cpu_percent": 80,
                "memory_bytes": 8589934592,  # 8GB
                "disk_bytes": 107374182400   # 100GB
            }
        }
    }

@pytest.fixture
def sample_poot_data():
    """Sample PoOT validation data for testing."""
    return {
        "output_data": "base64_encoded_test_output_data",
        "timestamp": datetime.utcnow().isoformat(),
        "nonce": "phase3_test_nonce_12345"
    }

@pytest.fixture
def sample_payout_data():
    """Sample payout data for testing."""
    return {
        "node_id": "phase3-test-node-001",
        "amount": 100.50,
        "currency": "USDT",
        "wallet_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    }

@pytest.fixture
async def mock_services():
    """Mock external services for testing."""
    with patch('sessions.services.blockchain_service.BlockchainService') as mock_blockchain, \
         patch('RDP.services.resource_monitor.ResourceMonitor') as mock_resource_monitor, \
         patch('node.services.tron_client.TronClient') as mock_tron_client:
        
        # Configure blockchain service mock
        mock_blockchain.return_value.anchor_session = AsyncMock(return_value={
            "transaction_hash": "0x1234567890abcdef",
            "block_height": 12345,
            "success": True
        })
        
        # Configure resource monitor mock
        mock_resource_monitor.return_value.collect_metrics = AsyncMock(return_value={
            "cpu_percent": 45.5,
            "memory_percent": 60.2,
            "disk_percent": 30.1,
            "network_in": 1000,
            "network_out": 2000
        })
        
        # Configure TRON client mock
        mock_tron_client.return_value.transfer_usdt = AsyncMock(return_value={
            "transaction_hash": "0xabcdef1234567890",
            "success": True,
            "gas_used": 21000
        })
        
        yield {
            "blockchain": mock_blockchain,
            "resource_monitor": mock_resource_monitor,
            "tron_client": mock_tron_client
        }

@pytest.fixture
def integration_test_config():
    """Configuration for integration tests."""
    return {
        "session_timeout": 30,  # seconds
        "rdp_connection_timeout": 10,  # seconds
        "node_heartbeat_interval": 5,  # seconds
        "poot_validation_timeout": 15,  # seconds
        "payout_processing_timeout": 60,  # seconds
        "max_concurrent_sessions": 10,
        "max_concurrent_rdp_servers": 5,
        "max_concurrent_nodes": 20
    }

@pytest.fixture
async def cleanup_test_data(test_db):
    """Cleanup test data after each test."""
    yield
    
    # Cleanup collections
    collections_to_clean = [
        "sessions", "session_chunks", "session_metadata",
        "rdp_servers", "rdp_sessions", "rdp_resources",
        "nodes", "node_pools", "poot_validations", "payouts"
    ]
    
    for collection_name in collections_to_clean:
        try:
            await test_db[collection_name].drop()
        except Exception:
            pass  # Collection might not exist

# Test markers
pytest.mark.phase3_integration = pytest.mark.phase3_integration
pytest.mark.session_lifecycle = pytest.mark.session_lifecycle
pytest.mark.rdp_creation = pytest.mark.rdp_creation
pytest.mark.node_registration = pytest.mark.node_registration
pytest.mark.poot_calculation = pytest.mark.poot_calculation
pytest.mark.end_to_end = pytest.mark.end_to_end
