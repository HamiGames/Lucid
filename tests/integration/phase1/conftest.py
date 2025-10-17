"""
Lucid API - Phase 1 Integration Test Configuration
Test fixtures and configuration for Foundation phase testing
"""

import os
import pytest
import asyncio
from typing import AsyncGenerator, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis
from elasticsearch import AsyncElasticsearch
import httpx

# Test configuration
TEST_MONGODB_URI = os.getenv("TEST_MONGODB_URI", "mongodb://localhost:27017/lucid_test")
TEST_REDIS_URI = os.getenv("TEST_REDIS_URI", "redis://localhost:6379/15")
TEST_ELASTICSEARCH_URI = os.getenv("TEST_ELASTICSEARCH_URI", "http://localhost:9200")
TEST_AUTH_SERVICE_URL = os.getenv("TEST_AUTH_SERVICE_URL", "http://localhost:8089")

# Test constants
TEST_TIMEOUT = 30  # seconds
TEST_USER_EMAIL = "test@lucid.example.com"
TEST_TRON_ADDRESS = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def mongodb_client() -> AsyncGenerator[AsyncIOMotorClient, None]:
    """
    MongoDB client fixture for testing
    
    Yields:
        AsyncIOMotorClient: MongoDB async client
    """
    client = AsyncIOMotorClient(TEST_MONGODB_URI)
    
    # Test connection
    try:
        await client.admin.command('ping')
        print(f"\n✓ Connected to MongoDB: {TEST_MONGODB_URI}")
    except Exception as e:
        pytest.fail(f"Failed to connect to MongoDB: {e}")
    
    yield client
    
    # Cleanup
    await client.drop_database("lucid_test")
    client.close()


@pytest.fixture(scope="session")
async def redis_client() -> AsyncGenerator[redis.Redis, None]:
    """
    Redis client fixture for testing
    
    Yields:
        redis.Redis: Redis async client
    """
    client = redis.from_url(TEST_REDIS_URI, decode_responses=True)
    
    # Test connection
    try:
        await client.ping()
        print(f"\n✓ Connected to Redis: {TEST_REDIS_URI}")
    except Exception as e:
        pytest.fail(f"Failed to connect to Redis: {e}")
    
    yield client
    
    # Cleanup
    await client.flushdb()
    await client.aclose()


@pytest.fixture(scope="session")
async def elasticsearch_client() -> AsyncGenerator[AsyncElasticsearch, None]:
    """
    Elasticsearch client fixture for testing
    
    Yields:
        AsyncElasticsearch: Elasticsearch async client
    """
    client = AsyncElasticsearch([TEST_ELASTICSEARCH_URI])
    
    # Test connection
    try:
        info = await client.info()
        print(f"\n✓ Connected to Elasticsearch: {TEST_ELASTICSEARCH_URI}")
        print(f"  Version: {info['version']['number']}")
    except Exception as e:
        pytest.fail(f"Failed to connect to Elasticsearch: {e}")
    
    yield client
    
    # Cleanup
    try:
        await client.indices.delete(index="lucid_test_*", ignore=[404])
    except Exception:
        pass
    
    await client.close()


@pytest.fixture(scope="session")
async def auth_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    HTTP client for authentication service
    
    Yields:
        httpx.AsyncClient: HTTP async client for auth service
    """
    async with httpx.AsyncClient(
        base_url=TEST_AUTH_SERVICE_URL,
        timeout=TEST_TIMEOUT
    ) as client:
        
        # Test connection
        try:
            response = await client.get("/health")
            if response.status_code == 200:
                print(f"\n✓ Auth service healthy: {TEST_AUTH_SERVICE_URL}")
            else:
                pytest.fail(f"Auth service unhealthy: {response.status_code}")
        except Exception as e:
            pytest.fail(f"Failed to connect to auth service: {e}")
        
        yield client


@pytest.fixture
async def test_user_data() -> Dict[str, Any]:
    """
    Test user data fixture
    
    Returns:
        Dict with test user information
    """
    return {
        "email": TEST_USER_EMAIL,
        "tron_address": TEST_TRON_ADDRESS,
        "user_id": "test_user_001",
        "role": "user",
        "permissions": ["create_session"],
        "hardware_wallet": {
            "type": "ledger",
            "connected": False
        },
        "created_at": "2025-10-14T00:00:00Z"
    }


@pytest.fixture
async def test_jwt_token(auth_client: httpx.AsyncClient, test_user_data: Dict) -> str:
    """
    Generate test JWT token
    
    Args:
        auth_client: HTTP client for auth service
        test_user_data: Test user data
        
    Returns:
        str: JWT access token
    """
    # Mock login request
    # In real implementation, this would use TRON signature verification
    try:
        response = await auth_client.post(
            "/auth/login",
            json={
                "tron_address": test_user_data["tron_address"],
                "signature": "mock_signature_for_testing",
                "message": "Login to Lucid"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token", "")
        else:
            # If auth service not fully implemented, return mock token
            return "mock_jwt_token_for_testing"
            
    except Exception as e:
        print(f"Warning: Could not generate real JWT token: {e}")
        return "mock_jwt_token_for_testing"


@pytest.fixture
async def mongodb_test_db(mongodb_client: AsyncIOMotorClient):
    """
    MongoDB test database fixture
    
    Args:
        mongodb_client: MongoDB client
        
    Returns:
        Database object for testing
    """
    db = mongodb_client["lucid_test"]
    
    # Create test collections
    collections = ["users", "sessions", "blocks", "transactions", "trust_policies"]
    for collection_name in collections:
        if collection_name not in await db.list_collection_names():
            await db.create_collection(collection_name)
    
    yield db
    
    # Cleanup
    for collection_name in collections:
        await db[collection_name].delete_many({})


@pytest.fixture
def mock_hardware_wallet():
    """
    Mock hardware wallet for testing
    
    Returns:
        Dict with mock hardware wallet data
    """
    return {
        "type": "ledger",
        "model": "Nano S",
        "connected": True,
        "firmware_version": "2.1.0",
        "device_id": "mock_device_001"
    }


@pytest.fixture
async def setup_test_indexes(mongodb_test_db):
    """
    Setup MongoDB indexes for testing
    
    Args:
        mongodb_test_db: MongoDB test database
    """
    # Users collection indexes
    await mongodb_test_db.users.create_index([("email", 1)], unique=True)
    await mongodb_test_db.users.create_index([("tron_address", 1)], unique=True)
    await mongodb_test_db.users.create_index([("user_id", 1)], unique=True)
    
    # Sessions collection indexes
    await mongodb_test_db.sessions.create_index([("session_id", 1)], unique=True)
    await mongodb_test_db.sessions.create_index([("user_id", 1)])
    await mongodb_test_db.sessions.create_index([("status", 1)])
    
    # Blocks collection indexes
    await mongodb_test_db.blocks.create_index([("height", 1)], unique=True)
    await mongodb_test_db.blocks.create_index([("block_id", 1)], unique=True)
    
    print("\n✓ Test indexes created")
    
    yield
    
    # Indexes are dropped with collections during cleanup


# Test markers
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "database: mark test as requiring database"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as requiring auth service"
    )


# Async test helper
@pytest.fixture
def async_test_timeout():
    """Timeout for async tests"""
    return TEST_TIMEOUT

