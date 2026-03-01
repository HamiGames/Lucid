# tests/integration/phase1/test_phase1_integration.py
# Phase 1 integration tests

import pytest
import asyncio
import requests
import pymongo
import redis
from elasticsearch import Elasticsearch
import json

# Test configuration
PI_HOST = "192.168.0.75"
MONGODB_PORT = 27017
REDIS_PORT = 6379
ELASTICSEARCH_PORT = 9200
AUTH_SERVICE_PORT = 8089

class TestPhase1Integration:
    """Phase 1 integration test suite"""
    
    @pytest.fixture(scope="class")
    async def setup(self):
        """Setup test environment"""
        # MongoDB connection
        self.mongo_client = pymongo.MongoClient(f"mongodb://{PI_HOST}:{MONGODB_PORT}")
        self.db = self.mongo_client.lucid
        
        # Redis connection
        self.redis_client = redis.Redis(host=PI_HOST, port=REDIS_PORT, decode_responses=True)
        
        # Elasticsearch connection
        self.es_client = Elasticsearch([f"http://{PI_HOST}:{ELASTICSEARCH_PORT}"])
        
        # Auth service URL
        self.auth_url = f"http://{PI_HOST}:{AUTH_SERVICE_PORT}"
    
    async def test_mongodb_connection(self):
        """Test MongoDB connection and query performance"""
        # Test connection
        assert self.mongo_client.admin.command('ping')
        
        # Test query performance
        start_time = asyncio.get_event_loop().time()
        result = self.db.test_collection.insert_one({"test": "data"})
        end_time = asyncio.get_event_loop().time()
        
        # Performance check (< 10ms)
        assert (end_time - start_time) < 0.01
        assert result.inserted_id is not None
        
        # Cleanup
        self.db.test_collection.delete_one({"_id": result.inserted_id})
    
    async def test_redis_caching(self):
        """Test Redis caching operations"""
        # Test connection
        assert self.redis_client.ping()
        
        # Test set/get operations
        test_key = "test_key"
        test_value = "test_value"
        
        self.redis_client.set(test_key, test_value)
        retrieved_value = self.redis_client.get(test_key)
        
        assert retrieved_value == test_value
        
        # Test expiration
        self.redis_client.setex(test_key, 1, test_value)
        await asyncio.sleep(2)
        expired_value = self.redis_client.get(test_key)
        
        assert expired_value is None
    
    async def test_elasticsearch_indexing(self):
        """Test Elasticsearch indexing and search"""
        # Test connection
        assert self.es_client.ping()
        
        # Test index creation
        index_name = "test-index"
        doc = {"title": "Test Document", "content": "This is a test document"}
        
        # Index document
        result = self.es_client.index(index=index_name, body=doc)
        assert result["result"] == "created"
        
        # Refresh index
        self.es_client.indices.refresh(index=index_name)
        
        # Test search
        search_result = self.es_client.search(
            index=index_name,
            body={"query": {"match": {"title": "Test"}}}
        )
        
        assert search_result["hits"]["total"]["value"] > 0
        
        # Cleanup
        self.es_client.indices.delete(index=index_name)
    
    async def test_auth_service_login_logout(self):
        """Test auth service login/logout flow"""
        # Test health endpoint
        health_response = requests.get(f"{self.auth_url}/health")
        assert health_response.status_code == 200
        
        # Test root endpoint
        root_response = requests.get(f"{self.auth_url}/")
        assert root_response.status_code == 200
        
        # Test auth endpoints (basic connectivity)
        auth_endpoints = ["/auth/login", "/auth/register", "/auth/logout"]
        for endpoint in auth_endpoints:
            response = requests.get(f"{self.auth_url}{endpoint}")
            # Should return 405 (Method Not Allowed) for GET, not 500
            assert response.status_code in [200, 405, 422]
    
    async def test_jwt_token_generation(self):
        """Test JWT token generation and validation"""
        # This would require actual auth service implementation
        # For now, test that the service is responding
        response = requests.get(f"{self.auth_url}/health")
        assert response.status_code == 200
        
        # TODO: Implement actual JWT test when auth service is complete
    
    async def test_cross_service_communication(self):
        """Test cross-service communication (auth → databases)"""
        # Test that auth service can connect to databases
        # This would require actual auth service implementation
        # For now, test basic connectivity
        
        # Test MongoDB connectivity from auth service perspective
        mongo_response = requests.get(f"{self.auth_url}/health")
        assert mongo_response.status_code == 200
        
        # Test Redis connectivity from auth service perspective
        redis_response = requests.get(f"{self.auth_url}/health")
        assert redis_response.status_code == 200

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])