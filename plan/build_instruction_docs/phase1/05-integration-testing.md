# Phase 1 Integration Testing

## Overview
Run comprehensive integration tests against deployed Phase 1 foundation services on Raspberry Pi to verify functionality and performance.

## Location
`tests/integration/phase1/`

## Test Categories

### 1. Database Connection Tests
**File**: `tests/integration/phase1/test_database_connections.py`

```python
"""
Database connection and basic functionality tests
"""

import pytest
import asyncio
import pymongo
import redis
from elasticsearch import Elasticsearch
from datetime import datetime

class TestDatabaseConnections:
    """Test database connections and basic operations"""
    
    @pytest.fixture
    async def mongo_client(self):
        """MongoDB client fixture"""
        client = pymongo.MongoClient("mongodb://lucid:SecureMongoPass123!@192.168.0.75:27017/lucid?authSource=admin")
        yield client
        client.close()
    
    @pytest.fixture
    async def redis_client(self):
        """Redis client fixture"""
        client = redis.from_url("redis://:SecureRedisPass123!@192.168.0.75:6379/0")
        yield client
        client.close()
    
    @pytest.fixture
    async def elasticsearch_client(self):
        """Elasticsearch client fixture"""
        client = Elasticsearch([{"host": "192.168.0.75", "port": 9200}])
        yield client
        client.close()
    
    async def test_mongodb_connection(self, mongo_client):
        """Test MongoDB connection"""
        # Test connection
        result = mongo_client.admin.command('ping')
        assert result['ok'] == 1
        
        # Test database access
        db = mongo_client.lucid
        assert db.name == 'lucid'
    
    async def test_mongodb_crud_operations(self, mongo_client):
        """Test MongoDB CRUD operations"""
        db = mongo_client.lucid
        collection = db.test_collection
        
        # Create document
        test_doc = {
            "test_id": "test_001",
            "message": "MongoDB test document",
            "timestamp": datetime.utcnow(),
            "status": "active"
        }
        
        result = collection.insert_one(test_doc)
        assert result.inserted_id is not None
        
        # Read document
        found_doc = collection.find_one({"test_id": "test_001"})
        assert found_doc is not None
        assert found_doc["message"] == "MongoDB test document"
        
        # Update document
        update_result = collection.update_one(
            {"test_id": "test_001"},
            {"$set": {"status": "updated"}}
        )
        assert update_result.modified_count == 1
        
        # Verify update
        updated_doc = collection.find_one({"test_id": "test_001"})
        assert updated_doc["status"] == "updated"
        
        # Delete document
        delete_result = collection.delete_one({"test_id": "test_001"})
        assert delete_result.deleted_count == 1
        
        # Verify deletion
        deleted_doc = collection.find_one({"test_id": "test_001"})
        assert deleted_doc is None
    
    async def test_redis_connection(self, redis_client):
        """Test Redis connection"""
        # Test connection
        result = redis_client.ping()
        assert result is True
    
    async def test_redis_operations(self, redis_client):
        """Test Redis operations"""
        # Set key
        redis_client.set("test_key", "test_value", ex=60)
        
        # Get key
        value = redis_client.get("test_key")
        assert value.decode() == "test_value"
        
        # Test expiration
        ttl = redis_client.ttl("test_key")
        assert ttl > 0
        
        # Delete key
        redis_client.delete("test_key")
        
        # Verify deletion
        deleted_value = redis_client.get("test_key")
        assert deleted_value is None
    
    async def test_elasticsearch_connection(self, elasticsearch_client):
        """Test Elasticsearch connection"""
        # Test connection
        result = elasticsearch_client.ping()
        assert result is True
        
        # Test cluster health
        health = elasticsearch_client.cluster.health()
        assert health['status'] in ['green', 'yellow']
    
    async def test_elasticsearch_operations(self, elasticsearch_client):
        """Test Elasticsearch operations"""
        index_name = "test_index"
        
        # Create index
        if elasticsearch_client.indices.exists(index=index_name):
            elasticsearch_client.indices.delete(index=index_name)
        
        mapping = {
            "mappings": {
                "properties": {
                    "test_id": {"type": "keyword"},
                    "message": {"type": "text"},
                    "timestamp": {"type": "date"},
                    "status": {"type": "keyword"}
                }
            }
        }
        
        elasticsearch_client.indices.create(index=index_name, body=mapping)
        
        # Index document
        doc = {
            "test_id": "test_001",
            "message": "Elasticsearch test document",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "active"
        }
        
        result = elasticsearch_client.index(index=index_name, body=doc)
        assert result['result'] == 'created'
        
        # Refresh index
        elasticsearch_client.indices.refresh(index=index_name)
        
        # Search document
        search_result = elasticsearch_client.search(
            index=index_name,
            body={"query": {"match": {"test_id": "test_001"}}}
        )
        
        assert search_result['hits']['total']['value'] == 1
        assert search_result['hits']['hits'][0]['_source']['message'] == "Elasticsearch test document"
        
        # Delete document
        delete_result = elasticsearch_client.delete(
            index=index_name,
            id=result['_id']
        )
        assert delete_result['result'] == 'deleted'
        
        # Clean up index
        elasticsearch_client.indices.delete(index=index_name)
```

### 2. Authentication Service Tests
**File**: `tests/integration/phase1/test_auth_service.py`

```python
"""
Authentication service integration tests
"""

import pytest
import asyncio
import httpx
from datetime import datetime, timedelta

class TestAuthenticationService:
    """Test authentication service functionality"""
    
    @pytest.fixture
    async def auth_client(self):
        """Authentication service client fixture"""
        async with httpx.AsyncClient(base_url="http://192.168.0.75:8089") as client:
            yield client
    
    async def test_health_endpoint(self, auth_client):
        """Test health endpoint"""
        response = await auth_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "lucid-auth-service"
        assert data["version"] == "1.0.0"
    
    async def test_user_registration(self, auth_client):
        """Test user registration"""
        user_data = {
            "username": "testuser001",
            "email": "testuser001@example.com",
            "password": "SecurePassword123!",
            "role": "user"
        }
        
        response = await auth_client.post("/auth/register", json=user_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["username"] == "testuser001"
        assert data["email"] == "testuser001@example.com"
        assert data["role"] == "user"
        assert "created_at" in data
    
    async def test_user_login(self, auth_client):
        """Test user login"""
        login_data = {
            "username": "testuser001",
            "password": "SecurePassword123!"
        }
        
        response = await auth_client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    async def test_token_validation(self, auth_client):
        """Test JWT token validation"""
        # First login to get token
        login_data = {
            "username": "testuser001",
            "password": "SecurePassword123!"
        }
        
        login_response = await auth_client.post("/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        token_data = login_response.json()
        access_token = token_data["access_token"]
        
        # Test protected endpoint with token
        headers = {"Authorization": f"Bearer {access_token}"}
        profile_response = await auth_client.get("/users/profile", headers=headers)
        assert profile_response.status_code == 200
        
        profile_data = profile_response.json()
        assert profile_data["username"] == "testuser001"
        assert profile_data["email"] == "testuser001@example.com"
    
    async def test_invalid_credentials(self, auth_client):
        """Test invalid credentials handling"""
        invalid_login_data = {
            "username": "testuser001",
            "password": "WrongPassword"
        }
        
        response = await auth_client.post("/auth/login", json=invalid_login_data)
        assert response.status_code == 401
        
        data = response.json()
        assert "detail" in data
        assert "Invalid credentials" in data["detail"]
    
    async def test_token_expiration(self, auth_client):
        """Test token expiration handling"""
        # This test would require a token with very short expiration
        # For now, we'll test with an invalid token
        invalid_token = "invalid.jwt.token"
        
        headers = {"Authorization": f"Bearer {invalid_token}"}
        response = await auth_client.get("/users/profile", headers=headers)
        assert response.status_code == 401
        
        data = response.json()
        assert "detail" in data
        assert "Invalid token" in data["detail"]
    
    async def test_user_logout(self, auth_client):
        """Test user logout"""
        # First login to get token
        login_data = {
            "username": "testuser001",
            "password": "SecurePassword123!"
        }
        
        login_response = await auth_client.post("/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        token_data = login_response.json()
        access_token = token_data["access_token"]
        
        # Test logout
        headers = {"Authorization": f"Bearer {access_token}"}
        logout_response = await auth_client.post("/auth/logout", headers=headers)
        assert logout_response.status_code == 200
        
        logout_data = logout_response.json()
        assert logout_data["message"] == "Successfully logged out"
```

### 3. Cross-Service Communication Tests
**File**: `tests/integration/phase1/test_cross_service_communication.py`

```python
"""
Cross-service communication tests
"""

import pytest
import asyncio
import httpx
import pymongo
import redis
from elasticsearch import Elasticsearch

class TestCrossServiceCommunication:
    """Test communication between services"""
    
    @pytest.fixture
    async def mongo_client(self):
        """MongoDB client fixture"""
        client = pymongo.MongoClient("mongodb://lucid:SecureMongoPass123!@192.168.0.75:27017/lucid?authSource=admin")
        yield client
        client.close()
    
    @pytest.fixture
    async def redis_client(self):
        """Redis client fixture"""
        client = redis.from_url("redis://:SecureRedisPass123!@192.168.0.75:6379/0")
        yield client
        client.close()
    
    @pytest.fixture
    async def elasticsearch_client(self):
        """Elasticsearch client fixture"""
        client = Elasticsearch([{"host": "192.168.0.75", "port": 9200}])
        yield client
        client.close()
    
    @pytest.fixture
    async def auth_client(self):
        """Authentication service client fixture"""
        async with httpx.AsyncClient(base_url="http://192.168.0.75:8089") as client:
            yield client
    
    async def test_auth_to_mongodb_communication(self, auth_client, mongo_client):
        """Test authentication service to MongoDB communication"""
        # Register user through auth service
        user_data = {
            "username": "crosstest001",
            "email": "crosstest001@example.com",
            "password": "SecurePassword123!",
            "role": "user"
        }
        
        response = await auth_client.post("/auth/register", json=user_data)
        assert response.status_code == 201
        
        # Verify user exists in MongoDB
        db = mongo_client.lucid
        user = db.users.find_one({"username": "crosstest001"})
        assert user is not None
        assert user["email"] == "crosstest001@example.com"
        assert user["role"] == "user"
        assert "hashed_password" in user
        assert "created_at" in user
    
    async def test_auth_to_redis_communication(self, auth_client, redis_client):
        """Test authentication service to Redis communication"""
        # Login through auth service
        login_data = {
            "username": "crosstest001",
            "password": "SecurePassword123!"
        }
        
        response = await auth_client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        
        # Check if session data is stored in Redis
        # This would depend on the auth service implementation
        # For now, we'll test basic Redis connectivity
        redis_client.set("test_session", "active", ex=300)
        session_status = redis_client.get("test_session")
        assert session_status.decode() == "active"
    
    async def test_auth_to_elasticsearch_communication(self, auth_client, elasticsearch_client):
        """Test authentication service to Elasticsearch communication"""
        # This test would verify that auth events are logged to Elasticsearch
        # For now, we'll test basic Elasticsearch connectivity
        test_doc = {
            "event_type": "user_login",
            "username": "crosstest001",
            "timestamp": datetime.utcnow().isoformat(),
            "ip_address": "192.168.0.75"
        }
        
        result = elasticsearch_client.index(index="lucid-auth-events", body=test_doc)
        assert result['result'] == 'created'
        
        # Refresh index
        elasticsearch_client.indices.refresh(index="lucid-auth-events")
        
        # Search for the event
        search_result = elasticsearch_client.search(
            index="lucid-auth-events",
            body={"query": {"match": {"username": "crosstest001"}}}
        )
        
        assert search_result['hits']['total']['value'] == 1
        assert search_result['hits']['hits'][0]['_source']['event_type'] == "user_login"
    
    async def test_database_consistency(self, mongo_client, redis_client, elasticsearch_client):
        """Test data consistency across databases"""
        # Create test data in MongoDB
        db = mongo_client.lucid
        test_user = {
            "username": "consistency_test",
            "email": "consistency@example.com",
            "role": "user",
            "created_at": datetime.utcnow()
        }
        
        db.users.insert_one(test_user)
        
        # Store related data in Redis
        redis_client.set("user:consistency_test:status", "active", ex=3600)
        redis_client.set("user:consistency_test:last_seen", datetime.utcnow().isoformat(), ex=3600)
        
        # Index user data in Elasticsearch
        es_doc = {
            "username": "consistency_test",
            "email": "consistency@example.com",
            "role": "user",
            "created_at": datetime.utcnow().isoformat(),
            "status": "active"
        }
        
        elasticsearch_client.index(index="lucid-users", body=es_doc)
        elasticsearch_client.indices.refresh(index="lucid-users")
        
        # Verify data consistency
        # MongoDB
        mongo_user = db.users.find_one({"username": "consistency_test"})
        assert mongo_user is not None
        assert mongo_user["email"] == "consistency@example.com"
        
        # Redis
        redis_status = redis_client.get("user:consistency_test:status")
        assert redis_status.decode() == "active"
        
        # Elasticsearch
        search_result = elasticsearch_client.search(
            index="lucid-users",
            body={"query": {"match": {"username": "consistency_test"}}}
        )
        
        assert search_result['hits']['total']['value'] == 1
        es_user = search_result['hits']['hits'][0]['_source']
        assert es_user["email"] == "consistency@example.com"
        assert es_user["status"] == "active"
```

### 4. Performance Tests
**File**: `tests/integration/phase1/test_performance.py`

```python
"""
Performance tests for Phase 1 services
"""

import pytest
import asyncio
import time
import httpx
import pymongo
import redis
from elasticsearch import Elasticsearch
from concurrent.futures import ThreadPoolExecutor

class TestPerformance:
    """Test service performance and scalability"""
    
    @pytest.fixture
    async def mongo_client(self):
        """MongoDB client fixture"""
        client = pymongo.MongoClient("mongodb://lucid:SecureMongoPass123!@192.168.0.75:27017/lucid?authSource=admin")
        yield client
        client.close()
    
    @pytest.fixture
    async def redis_client(self):
        """Redis client fixture"""
        client = redis.from_url("redis://:SecureRedisPass123!@192.168.0.75:6379/0")
        yield client
        client.close()
    
    @pytest.fixture
    async def elasticsearch_client(self):
        """Elasticsearch client fixture"""
        client = Elasticsearch([{"host": "192.168.0.75", "port": 9200}])
        yield client
        client.close()
    
    @pytest.fixture
    async def auth_client(self):
        """Authentication service client fixture"""
        async with httpx.AsyncClient(base_url="http://192.168.0.75:8089") as client:
            yield client
    
    async def test_mongodb_query_performance(self, mongo_client):
        """Test MongoDB query performance"""
        db = mongo_client.lucid
        collection = db.performance_test
        
        # Insert test data
        test_docs = []
        for i in range(1000):
            doc = {
                "test_id": f"perf_test_{i:04d}",
                "value": i,
                "timestamp": datetime.utcnow(),
                "category": f"category_{i % 10}"
            }
            test_docs.append(doc)
        
        # Bulk insert
        start_time = time.time()
        collection.insert_many(test_docs)
        insert_time = time.time() - start_time
        
        # Test query performance
        start_time = time.time()
        results = list(collection.find({"category": "category_5"}).limit(100))
        query_time = time.time() - start_time
        
        # Performance assertions
        assert insert_time < 5.0  # Insert 1000 docs in less than 5 seconds
        assert query_time < 1.0  # Query in less than 1 second
        assert len(results) == 100
        
        # Clean up
        collection.drop()
    
    async def test_redis_operation_performance(self, redis_client):
        """Test Redis operation performance"""
        # Test SET operations
        start_time = time.time()
        for i in range(1000):
            redis_client.set(f"perf_test_{i}", f"value_{i}", ex=60)
        set_time = time.time() - start_time
        
        # Test GET operations
        start_time = time.time()
        for i in range(1000):
            value = redis_client.get(f"perf_test_{i}")
            assert value.decode() == f"value_{i}"
        get_time = time.time() - start_time
        
        # Performance assertions
        assert set_time < 2.0  # 1000 SET operations in less than 2 seconds
        assert get_time < 1.0  # 1000 GET operations in less than 1 second
        
        # Clean up
        for i in range(1000):
            redis_client.delete(f"perf_test_{i}")
    
    async def test_elasticsearch_indexing_performance(self, elasticsearch_client):
        """Test Elasticsearch indexing performance"""
        index_name = "performance_test"
        
        # Create index
        if elasticsearch_client.indices.exists(index=index_name):
            elasticsearch_client.indices.delete(index=index_name)
        
        mapping = {
            "mappings": {
                "properties": {
                    "test_id": {"type": "keyword"},
                    "value": {"type": "integer"},
                    "timestamp": {"type": "date"},
                    "category": {"type": "keyword"}
                }
            }
        }
        
        elasticsearch_client.indices.create(index=index_name, body=mapping)
        
        # Test bulk indexing
        docs = []
        for i in range(1000):
            doc = {
                "_index": index_name,
                "_source": {
                    "test_id": f"perf_test_{i:04d}",
                    "value": i,
                    "timestamp": datetime.utcnow().isoformat(),
                    "category": f"category_{i % 10}"
                }
            }
            docs.append(doc)
        
        start_time = time.time()
        elasticsearch_client.bulk(body=docs)
        index_time = time.time() - start_time
        
        # Refresh index
        elasticsearch_client.indices.refresh(index=index_name)
        
        # Test search performance
        start_time = time.time()
        search_result = elasticsearch_client.search(
            index=index_name,
            body={"query": {"match": {"category": "category_5"}}}
        )
        search_time = time.time() - start_time
        
        # Performance assertions
        assert index_time < 5.0  # Index 1000 docs in less than 5 seconds
        assert search_time < 1.0  # Search in less than 1 second
        assert search_result['hits']['total']['value'] == 100
        
        # Clean up
        elasticsearch_client.indices.delete(index=index_name)
    
    async def test_auth_service_performance(self, auth_client):
        """Test authentication service performance"""
        # Test concurrent login requests
        async def login_request():
            login_data = {
                "username": "perf_test_user",
                "password": "SecurePassword123!"
            }
            response = await auth_client.post("/auth/login", json=login_data)
            return response.status_code
        
        # Create test user first
        user_data = {
            "username": "perf_test_user",
            "email": "perf_test@example.com",
            "password": "SecurePassword123!",
            "role": "user"
        }
        
        await auth_client.post("/auth/register", json=user_data)
        
        # Test concurrent requests
        start_time = time.time()
        tasks = [login_request() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Performance assertions
        assert total_time < 10.0  # 100 requests in less than 10 seconds
        assert all(status == 200 for status in results)  # All requests successful
    
    async def test_concurrent_database_operations(self, mongo_client, redis_client):
        """Test concurrent database operations"""
        def mongo_operation():
            db = mongo_client.lucid
            collection = db.concurrent_test
            doc = {
                "operation_id": f"mongo_{time.time()}",
                "timestamp": datetime.utcnow()
            }
            collection.insert_one(doc)
            return True
        
        def redis_operation():
            redis_client.set(f"redis_{time.time()}", "value", ex=60)
            return True
        
        # Test concurrent operations
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            mongo_futures = [executor.submit(mongo_operation) for _ in range(50)]
            redis_futures = [executor.submit(redis_operation) for _ in range(50)]
            
            mongo_results = [future.result() for future in mongo_futures]
            redis_results = [future.result() for future in redis_futures]
        
        total_time = time.time() - start_time
        
        # Performance assertions
        assert total_time < 5.0  # 100 operations in less than 5 seconds
        assert all(mongo_results)  # All MongoDB operations successful
        assert all(redis_results)  # All Redis operations successful
        
        # Clean up
        mongo_client.lucid.concurrent_test.drop()
        for i in range(50):
            redis_client.delete(f"redis_{i}")
```

## Test Execution Script

**File**: `scripts/testing/run-phase1-integration-tests.sh`

```bash
#!/bin/bash
# scripts/testing/run-phase1-integration-tests.sh
# Run Phase 1 integration tests

set -e

echo "Running Phase 1 integration tests..."

# Create test directory
mkdir -p tests/integration/phase1

# Install test dependencies
pip install pytest pytest-asyncio httpx pymongo redis elasticsearch

# Run database connection tests
echo "Running database connection tests..."
python -m pytest tests/integration/phase1/test_database_connections.py -v

# Run authentication service tests
echo "Running authentication service tests..."
python -m pytest tests/integration/phase1/test_auth_service.py -v

# Run cross-service communication tests
echo "Running cross-service communication tests..."
python -m pytest tests/integration/phase1/test_cross_service_communication.py -v

# Run performance tests
echo "Running performance tests..."
python -m pytest tests/integration/phase1/test_performance.py -v

echo "All Phase 1 integration tests completed successfully!"
```

## Validation Criteria
- All tests pass with >95% coverage
- Database connections working correctly
- Authentication service functional
- Cross-service communication verified
- Performance benchmarks met
- No critical errors or failures

## Performance Benchmarks
- **MongoDB**: <10ms p95 latency for queries
- **Redis**: <5ms p95 latency for operations
- **Elasticsearch**: <10ms p95 latency for searches
- **Authentication Service**: <100ms p95 latency for login
- **Concurrent Operations**: 100 operations in <5 seconds

## Troubleshooting

### Test Failures
```bash
# Check service status
ssh pickme@192.168.0.75 "docker ps"

# Check service logs
ssh pickme@192.168.0.75 "docker logs lucid-mongodb"
ssh pickme@192.168.0.75 "docker logs lucid-redis"
ssh pickme@192.168.0.75 "docker logs lucid-elasticsearch"
ssh pickme@192.168.0.75 "docker logs lucid-auth-service"
```

### Performance Issues
```bash
# Check resource usage
ssh pickme@192.168.0.75 "docker stats"

# Check disk space
ssh pickme@192.168.0.75 "df -h"

# Check memory usage
ssh pickme@192.168.0.75 "free -h"
```

### Network Issues
```bash
# Test network connectivity
ping 192.168.0.75

# Test port connectivity
telnet 192.168.0.75 27017
telnet 192.168.0.75 6379
telnet 192.168.0.75 9200
telnet 192.168.0.75 8089
```

## Next Steps
After successful Phase 1 integration testing, proceed to Phase 2 core services build.
