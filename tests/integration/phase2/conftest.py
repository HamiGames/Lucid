"""
Phase 2 Integration Test Configuration

This module provides shared fixtures and configuration for Phase 2 integration tests.
Tests API Gateway, Blockchain Core, and Cross-Cluster Integration services.
"""

import pytest
import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Test configuration
TEST_CONFIG = {
    "api_gateway_url": "http://localhost:8080",
    "blockchain_core_url": "http://localhost:8084",
    "auth_service_url": "http://localhost:8089",
    "database_url": "mongodb://localhost:27017/lucid_test",
    "redis_url": "redis://localhost:6379/1",
    "consul_url": "http://localhost:8500",
    "test_timeout": 30,
    "rate_limit_public": 100,
    "rate_limit_authenticated": 1000,
    "rate_limit_admin": 10000
}

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def http_client():
    """Create aiohttp client for test session."""
    async with aiohttp.ClientSession() as client:
        yield client

@pytest.fixture
async def api_gateway_client():
    """API Gateway client fixture."""
    async with aiohttp.ClientSession() as client:
        yield client

@pytest.fixture
async def blockchain_client():
    """Blockchain Core client fixture."""
    async with aiohttp.ClientSession() as client:
        yield client

@pytest.fixture
async def auth_client():
    """Authentication service client fixture."""
    async with aiohttp.ClientSession() as client:
        yield client

@pytest.fixture
def test_user_credentials():
    """Test user credentials for authentication."""
    return {
        "username": "test_user",
        "password": "test_password",
        "tron_address": "TTestAddress123456789",
        "tron_signature": "test_signature_12345"
    }

@pytest.fixture
def test_admin_credentials():
    """Test admin credentials for authentication."""
    return {
        "username": "admin_user",
        "password": "admin_password",
        "tron_address": "TAdminAddress123456789",
        "tron_signature": "admin_signature_12345"
    }

@pytest.fixture
async def auth_token(http_client, test_user_credentials):
    """Get authentication token for test user."""
    auth_url = f"{TEST_CONFIG['auth_service_url']}/auth/login"
    
    try:
        async with http_client.post(auth_url, json=test_user_credentials) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("access_token")
    except Exception:
        pass
    
    # Return mock token if auth service not available
    return "mock_jwt_token_for_testing"

@pytest.fixture
async def admin_token(http_client, test_admin_credentials):
    """Get authentication token for admin user."""
    auth_url = f"{TEST_CONFIG['auth_service_url']}/auth/login"
    
    try:
        async with http_client.post(auth_url, json=test_admin_credentials) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("access_token")
    except Exception:
        pass
    
    # Return mock admin token if auth service not available
    return "mock_admin_jwt_token_for_testing"

@pytest.fixture
def mock_consul_service():
    """Mock Consul service for service discovery tests."""
    consul_mock = AsyncMock()
    consul_mock.get_services.return_value = {
        "api-gateway": ["http://localhost:8080"],
        "blockchain-core": ["http://localhost:8084"],
        "auth-service": ["http://localhost:8089"],
        "session-management": ["http://localhost:8083"]
    }
    consul_mock.register_service.return_value = True
    consul_mock.deregister_service.return_value = True
    return consul_mock

@pytest.fixture
def mock_redis_client():
    """Mock Redis client for rate limiting tests."""
    redis_mock = AsyncMock()
    redis_mock.get.return_value = "0"
    redis_mock.set.return_value = True
    redis_mock.incr.return_value = 1
    redis_mock.expire.return_value = True
    return redis_mock

@pytest.fixture
def mock_mongodb_client():
    """Mock MongoDB client for database tests."""
    mongodb_mock = AsyncMock()
    mongodb_mock.find_one.return_value = {"_id": "test_id", "data": "test_data"}
    mongodb_mock.insert_one.return_value = {"inserted_id": "test_id"}
    mongodb_mock.update_one.return_value = {"modified_count": 1}
    mongodb_mock.delete_one.return_value = {"deleted_count": 1}
    return mongodb_mock

@pytest.fixture
def sample_block_data():
    """Sample block data for blockchain tests."""
    return {
        "block_id": "block_12345",
        "height": 1,
        "previous_hash": "0" * 64,
        "merkle_root": "merkle_root_hash_12345",
        "timestamp": 1640995200,
        "transactions": [
            {
                "tx_id": "tx_12345",
                "type": "session_anchoring",
                "data": {"session_id": "session_12345"}
            }
        ],
        "consensus_data": {
            "algorithm": "PoOT",
            "participants": ["node_1", "node_2", "node_3"],
            "votes": {"node_1": "approve", "node_2": "approve", "node_3": "approve"}
        }
    }

@pytest.fixture
def sample_session_data():
    """Sample session data for session management tests."""
    return {
        "session_id": "session_12345",
        "user_id": "user_12345",
        "status": "active",
        "created_at": "2025-01-10T19:08:00Z",
        "chunks": [
            {"chunk_id": "chunk_1", "hash": "hash_1", "size": 1024},
            {"chunk_id": "chunk_2", "hash": "hash_2", "size": 2048}
        ],
        "merkle_tree": {
            "root": "merkle_root_hash",
            "leaves": ["hash_1", "hash_2"],
            "height": 1
        }
    }

@pytest.fixture
def rate_limit_headers():
    """Rate limiting headers for testing."""
    return {
        "X-RateLimit-Limit": "100",
        "X-RateLimit-Remaining": "99",
        "X-RateLimit-Reset": "1640995260"
    }

@pytest.fixture
def service_health_status():
    """Service health status for testing."""
    return {
        "api-gateway": {"status": "healthy", "version": "1.0.0"},
        "blockchain-core": {"status": "healthy", "version": "1.0.0"},
        "auth-service": {"status": "healthy", "version": "1.0.0"},
        "database": {"status": "healthy", "version": "7.0.0"},
        "redis": {"status": "healthy", "version": "7.0.0"},
        "consul": {"status": "healthy", "version": "1.15.0"}
    }

# Test utilities
class TestHelper:
    """Helper class for common test operations."""
    
    @staticmethod
    async def make_request(client, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request and return response data."""
        async with client.request(method, url, **kwargs) as response:
            data = await response.json() if response.content_type == 'application/json' else await response.text()
            return {
                "status": response.status,
                "headers": dict(response.headers),
                "data": data
            }
    
    @staticmethod
    def assert_response_success(response: Dict[str, Any], expected_status: int = 200):
        """Assert response is successful."""
        assert response["status"] == expected_status, f"Expected status {expected_status}, got {response['status']}"
    
    @staticmethod
    def assert_rate_limit_headers(response: Dict[str, Any]):
        """Assert rate limiting headers are present."""
        headers = response["headers"]
        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers
        assert "X-RateLimit-Reset" in headers

@pytest.fixture
def test_helper():
    """Test helper fixture."""
    return TestHelper()

# Pytest configuration
def pytest_configure(config):
    """Configure pytest for Phase 2 integration tests."""
    config.addinivalue_line("markers", "gateway: API Gateway integration tests")
    config.addinivalue_line("markers", "blockchain: Blockchain Core integration tests")
    config.addinivalue_line("markers", "auth: Authentication integration tests")
    config.addinivalue_line("markers", "consensus: Consensus mechanism tests")
    config.addinivalue_line("markers", "service_mesh: Service mesh integration tests")
    config.addinivalue_line("markers", "rate_limiting: Rate limiting tests")
    config.addinivalue_line("markers", "slow: Slow running tests")

def pytest_collection_modifyitems(config, items):
    """Modify test collection for Phase 2 integration tests."""
    for item in items:
        # Add slow marker to integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.slow)
        
        # Add specific markers based on test file names
        if "gateway_auth" in str(item.fspath):
            item.add_marker(pytest.mark.gateway)
            item.add_marker(pytest.mark.auth)
        elif "gateway_blockchain" in str(item.fspath):
            item.add_marker(pytest.mark.gateway)
            item.add_marker(pytest.mark.blockchain)
        elif "blockchain_consensus" in str(item.fspath):
            item.add_marker(pytest.mark.blockchain)
            item.add_marker(pytest.mark.consensus)
        elif "service_mesh" in str(item.fspath):
            item.add_marker(pytest.mark.service_mesh)
        elif "rate_limiting" in str(item.fspath):
            item.add_marker(pytest.mark.rate_limiting)
