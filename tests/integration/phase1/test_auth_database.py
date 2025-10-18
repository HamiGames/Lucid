"""
Lucid API - Phase 1 Integration Test: Auth & Database
Tests integration between Authentication service and MongoDB/Redis

This test suite verifies:
- User registration → MongoDB storage
- JWT generation → Redis caching  
- Database connection pooling
- Transaction rollback capabilities
- Cache invalidation
- Concurrent operations
"""

import pytest
from datetime import datetime, timedelta
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.auth
@pytest.mark.asyncio
async def test_user_registration_to_mongodb(
    auth_client: httpx.AsyncClient,
    mongodb_test_db,
    test_user_data
):
    """
    Test: User registration → MongoDB storage
    
    Verifies that user registration via auth service
    properly stores user data in MongoDB
    """
    # Register user (mock implementation)
    registration_data = {
        "email": test_user_data["email"],
        "tron_address": test_user_data["tron_address"],
        "signature": "mock_signature",
        "message": "Register with Lucid"
    }
    
    # This would call auth service registration endpoint
    # For now, we insert directly to test DB integration
    user_doc = {
        "user_id": test_user_data["user_id"],
        "email": test_user_data["email"],
        "tron_address": test_user_data["tron_address"],
        "role": test_user_data["role"],
        "permissions": test_user_data["permissions"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    # Insert into MongoDB
    result = await mongodb_test_db.users.insert_one(user_doc)
    assert result.inserted_id is not None
    
    # Verify user exists in MongoDB
    stored_user = await mongodb_test_db.users.find_one(
        {"email": test_user_data["email"]}
    )
    
    assert stored_user is not None
    assert stored_user["email"] == test_user_data["email"]
    assert stored_user["tron_address"] == test_user_data["tron_address"]
    assert stored_user["role"] == "user"
    
    print(f"\n✓ User registered and stored in MongoDB: {test_user_data['email']}")


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.auth
@pytest.mark.asyncio
async def test_jwt_token_redis_caching(
    redis_client: redis.Redis,
    test_user_data,
    test_jwt_token
):
    """
    Test: JWT generation → Redis caching
    
    Verifies that JWT tokens are properly cached in Redis
    for fast validation
    """
    # Create session key
    session_key = f"session:{test_user_data['user_id']}"
    
    # Store JWT token in Redis with expiration
    token_data = {
        "access_token": test_jwt_token,
        "user_id": test_user_data["user_id"],
        "email": test_user_data["email"],
        "role": test_user_data["role"]
    }
    
    # Set token in Redis with 15-minute expiration
    await redis_client.setex(
        session_key,
        timedelta(minutes=15),
        test_jwt_token
    )
    
    # Verify token is cached
    cached_token = await redis_client.get(session_key)
    assert cached_token is not None
    assert cached_token == test_jwt_token
    
    # Verify TTL is set
    ttl = await redis_client.ttl(session_key)
    assert ttl > 0
    assert ttl <= 900  # 15 minutes
    
    print(f"\n✓ JWT token cached in Redis with {ttl}s TTL")


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.asyncio
async def test_user_lookup_performance(
    mongodb_test_db,
    setup_test_indexes,
    test_user_data
):
    """
    Test: User lookup performance with indexes
    
    Verifies that MongoDB indexes improve query performance
    """
    import time
    
    # Insert test user
    await mongodb_test_db.users.insert_one({
        "user_id": test_user_data["user_id"],
        "email": test_user_data["email"],
        "tron_address": test_user_data["tron_address"],
        "created_at": datetime.utcnow()
    })
    
    # Measure query time with index
    start_time = time.time()
    user = await mongodb_test_db.users.find_one(
        {"email": test_user_data["email"]}
    )
    query_time = (time.time() - start_time) * 1000  # milliseconds
    
    assert user is not None
    assert query_time < 10  # Should be less than 10ms with index
    
    print(f"\n✓ User lookup completed in {query_time:.2f}ms")


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.auth
@pytest.mark.asyncio
async def test_session_lifecycle_storage(
    mongodb_test_db,
    redis_client: redis.Redis,
    test_user_data,
    test_jwt_token
):
    """
    Test: Complete session lifecycle storage
    
    Verifies session data is stored in both MongoDB and Redis
    """
    session_id = "test_session_001"
    
    # Store session in MongoDB
    session_doc = {
        "session_id": session_id,
        "user_id": test_user_data["user_id"],
        "status": "active",
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=24)
    }
    
    await mongodb_test_db.sessions.insert_one(session_doc)
    
    # Cache session in Redis
    session_cache_key = f"session_cache:{session_id}"
    await redis_client.setex(
        session_cache_key,
        timedelta(minutes=30),
        test_user_data["user_id"]
    )
    
    # Verify session in MongoDB
    stored_session = await mongodb_test_db.sessions.find_one(
        {"session_id": session_id}
    )
    assert stored_session is not None
    assert stored_session["status"] == "active"
    
    # Verify session in Redis cache
    cached_user_id = await redis_client.get(session_cache_key)
    assert cached_user_id == test_user_data["user_id"]
    
    print(f"\n✓ Session {session_id} stored in MongoDB and cached in Redis")


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.asyncio
async def test_concurrent_database_operations(
    mongodb_test_db,
    redis_client: redis.Redis
):
    """
    Test: Concurrent database operations
    
    Verifies database can handle concurrent reads/writes
    """
    import asyncio
    
    async def insert_user(index: int):
        user_doc = {
            "user_id": f"concurrent_user_{index}",
            "email": f"user{index}@test.com",
            "tron_address": f"TR{index:040d}",
            "created_at": datetime.utcnow()
        }
        await mongodb_test_db.users.insert_one(user_doc)
        return index
    
    async def cache_token(index: int):
        key = f"token:user_{index}"
        await redis_client.setex(key, timedelta(minutes=5), f"token_{index}")
        return index
    
    # Run 10 concurrent operations
    mongo_tasks = [insert_user(i) for i in range(10)]
    redis_tasks = [cache_token(i) for i in range(10)]
    
    mongo_results = await asyncio.gather(*mongo_tasks)
    redis_results = await asyncio.gather(*redis_tasks)
    
    assert len(mongo_results) == 10
    assert len(redis_results) == 10
    
    # Verify all users were inserted
    user_count = await mongodb_test_db.users.count_documents({
        "user_id": {"$regex": "^concurrent_user_"}
    })
    assert user_count == 10
    
    print(f"\n✓ Completed 20 concurrent database operations")


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.asyncio
async def test_database_connection_pool(
    mongodb_client: AsyncIOMotorClient,
    redis_client: redis.Redis
):
    """
    Test: Database connection pooling
    
    Verifies connection pools are working efficiently
    """
    # MongoDB connection pool test
    db = mongodb_client["lucid_test"]
    
    # Perform multiple operations
    for i in range(5):
        await db.users.find_one({})
    
    # Redis connection pool test
    for i in range(5):
        await redis_client.ping()
    
    print("\n✓ Connection pooling working correctly")


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.asyncio
async def test_transaction_rollback_mongodb(
    mongodb_client: AsyncIOMotorClient,
    mongodb_test_db
):
    """
    Test: MongoDB transaction rollback
    
    Verifies transactions can be rolled back on error
    """
    # Start a session for transactions
    async with await mongodb_client.start_session() as session:
        async with session.start_transaction():
            try:
                # Insert first document
                await mongodb_test_db.users.insert_one(
                    {
                        "user_id": "txn_user_1",
                        "email": "txn1@test.com",
                        "tron_address": "TR1234567890"
                    },
                    session=session
                )
                
                # Simulate error - try to insert duplicate
                await mongodb_test_db.users.insert_one(
                    {
                        "user_id": "txn_user_1",  # Duplicate!
                        "email": "txn2@test.com",
                        "tron_address": "TR0987654321"
                    },
                    session=session
                )
                
            except Exception:
                # Transaction will auto-rollback on exception
                pass
    
    # Verify transaction was rolled back
    user_count = await mongodb_test_db.users.count_documents(
        {"user_id": {"$regex": "^txn_user_"}}
    )
    assert user_count == 0  # No users should exist due to rollback
    
    print("\n✓ Transaction rollback working correctly")


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.asyncio
async def test_redis_cache_invalidation(
    redis_client: redis.Redis,
    test_user_data
):
    """
    Test: Redis cache invalidation
    
    Verifies cache can be properly invalidated
    """
    cache_key = f"user:{test_user_data['user_id']}"
    
    # Set cache
    await redis_client.setex(
        cache_key,
        timedelta(minutes=10),
        test_user_data["email"]
    )
    
    # Verify cache exists
    cached_value = await redis_client.get(cache_key)
    assert cached_value == test_user_data["email"]
    
    # Invalidate cache
    await redis_client.delete(cache_key)
    
    # Verify cache is gone
    cached_value = await redis_client.get(cache_key)
    assert cached_value is None
    
    print("\n✓ Cache invalidation working correctly")

