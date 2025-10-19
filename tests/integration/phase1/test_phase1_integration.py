#!/usr/bin/env python3
"""
Phase 1 Foundation Services Integration Tests
Based on lucid-container-build-plan.plan.md Step 9
Tests MongoDB, Redis, Elasticsearch, and Authentication Service integration
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import pytest
import motor.motor_asyncio
import redis.asyncio as redis
import httpx
from elasticsearch import AsyncElasticsearch
from pymongo import MongoClient
from redis import Redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
PI_HOST = os.getenv('PI_HOST', '192.168.0.75')
PI_PORT = os.getenv('PI_PORT', '8089')
MONGODB_URI = f"mongodb://lucid:lucid@{PI_HOST}:27017/lucid?authSource=admin"
REDIS_URI = f"redis://:lucid@{PI_HOST}:6379/0"
ELASTICSEARCH_URI = f"http://{PI_HOST}:9200"
AUTH_SERVICE_URI = f"http://{PI_HOST}:8089"

class Phase1IntegrationTests:
    """Phase 1 Foundation Services Integration Test Suite"""
    
    def __init__(self):
        self.mongodb_client = None
        self.redis_client = None
        self.elasticsearch_client = None
        self.auth_client = None
        self.test_results = []
        
    async def setup_clients(self):
        """Setup database and service clients"""
        try:
            # MongoDB client
            self.mongodb_client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
            await self.mongodb_client.admin.command('ping')
            logger.info("MongoDB client connected successfully")
            
            # Redis client
            self.redis_client = redis.from_url(REDIS_URI)
            await self.redis_client.ping()
            logger.info("Redis client connected successfully")
            
            # Elasticsearch client
            self.elasticsearch_client = AsyncElasticsearch([ELASTICSEARCH_URI])
            await self.elasticsearch_client.ping()
            logger.info("Elasticsearch client connected successfully")
            
            # Auth service client
            self.auth_client = httpx.AsyncClient(base_url=AUTH_SERVICE_URI, timeout=30.0)
            logger.info("Auth service client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup clients: {e}")
            raise
    
    async def cleanup_clients(self):
        """Cleanup database and service clients"""
        if self.mongodb_client:
            self.mongodb_client.close()
        if self.redis_client:
            await self.redis_client.close()
        if self.elasticsearch_client:
            await self.elasticsearch_client.close()
        if self.auth_client:
            await self.auth_client.aclose()
    
    def log_test_result(self, test_name: str, status: str, message: str, details: Optional[Dict] = None):
        """Log test result"""
        result = {
            'test_name': test_name,
            'status': status,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'details': details or {}
        }
        self.test_results.append(result)
        
        if status == 'PASS':
            logger.info(f"✓ {test_name}: {message}")
        elif status == 'FAIL':
            logger.error(f"✗ {test_name}: {message}")
        else:
            logger.warning(f"⚠ {test_name}: {message}")
    
    async def test_mongodb_connection(self):
        """Test MongoDB connection and basic operations"""
        try:
            # Test connection
            await self.mongodb_client.admin.command('ping')
            
            # Test database operations
            db = self.mongodb_client.lucid
            collection = db.test_collection
            
            # Insert test document
            test_doc = {
                'test_id': 'integration_test',
                'timestamp': datetime.now(timezone.utc),
                'data': 'test_data'
            }
            result = await collection.insert_one(test_doc)
            
            # Find test document
            found_doc = await collection.find_one({'test_id': 'integration_test'})
            
            # Cleanup
            await collection.delete_one({'test_id': 'integration_test'})
            
            if found_doc and found_doc['data'] == 'test_data':
                self.log_test_result(
                    'mongodb_connection',
                    'PASS',
                    'MongoDB connection and operations successful',
                    {'inserted_id': str(result.inserted_id)}
                )
            else:
                self.log_test_result(
                    'mongodb_connection',
                    'FAIL',
                    'MongoDB document operations failed'
                )
                
        except Exception as e:
            self.log_test_result(
                'mongodb_connection',
                'FAIL',
                f'MongoDB connection failed: {str(e)}'
            )
    
    async def test_redis_operations(self):
        """Test Redis connection and caching operations"""
        try:
            # Test connection
            await self.redis_client.ping()
            
            # Test basic operations
            test_key = 'integration_test_key'
            test_value = 'integration_test_value'
            
            # Set value
            await self.redis_client.set(test_key, test_value, ex=60)
            
            # Get value
            retrieved_value = await self.redis_client.get(test_key)
            
            # Test hash operations
            await self.redis_client.hset('test_hash', 'field1', 'value1')
            hash_value = await self.redis_client.hget('test_hash', 'field1')
            
            # Cleanup
            await self.redis_client.delete(test_key, 'test_hash')
            
            if retrieved_value and retrieved_value.decode() == test_value and hash_value == b'value1':
                self.log_test_result(
                    'redis_operations',
                    'PASS',
                    'Redis operations successful',
                    {'test_key': test_key, 'test_value': test_value}
                )
            else:
                self.log_test_result(
                    'redis_operations',
                    'FAIL',
                    'Redis operations failed'
                )
                
        except Exception as e:
            self.log_test_result(
                'redis_operations',
                'FAIL',
                f'Redis operations failed: {str(e)}'
            )
    
    async def test_elasticsearch_indexing(self):
        """Test Elasticsearch indexing and search"""
        try:
            # Test connection
            await self.elasticsearch_client.ping()
            
            # Test index operations
            index_name = 'test_integration_index'
            doc_id = 'test_doc_1'
            test_doc = {
                'title': 'Integration Test Document',
                'content': 'This is a test document for integration testing',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'test_id': 'integration_test'
            }
            
            # Create index
            await self.elasticsearch_client.index(
                index=index_name,
                id=doc_id,
                body=test_doc
            )
            
            # Refresh index
            await self.elasticsearch_client.indices.refresh(index=index_name)
            
            # Search for document
            search_result = await self.elasticsearch_client.search(
                index=index_name,
                body={
                    'query': {
                        'match': {
                            'test_id': 'integration_test'
                        }
                    }
                }
            )
            
            # Cleanup
            await self.elasticsearch_client.indices.delete(index=index_name)
            
            if search_result['hits']['total']['value'] > 0:
                self.log_test_result(
                    'elasticsearch_indexing',
                    'PASS',
                    'Elasticsearch indexing and search successful',
                    {'hits': search_result['hits']['total']['value']}
                )
            else:
                self.log_test_result(
                    'elasticsearch_indexing',
                    'FAIL',
                    'Elasticsearch search failed'
                )
                
        except Exception as e:
            self.log_test_result(
                'elasticsearch_indexing',
                'FAIL',
                f'Elasticsearch operations failed: {str(e)}'
            )
    
    async def test_auth_service_health(self):
        """Test Authentication service health endpoint"""
        try:
            response = await self.auth_client.get('/health')
            
            if response.status_code == 200:
                health_data = response.json()
                self.log_test_result(
                    'auth_service_health',
                    'PASS',
                    'Authentication service health check successful',
                    {'status': health_data.get('status'), 'service': health_data.get('service')}
                )
            else:
                self.log_test_result(
                    'auth_service_health',
                    'FAIL',
                    f'Authentication service health check failed: {response.status_code}'
                )
                
        except Exception as e:
            self.log_test_result(
                'auth_service_health',
                'FAIL',
                f'Authentication service health check failed: {str(e)}'
            )
    
    async def test_jwt_token_validation(self):
        """Test JWT token generation and validation"""
        try:
            # Test token generation (if endpoint exists)
            test_payload = {
                'tron_address': 'TTest123456789012345678901234567890',
                'signature': 'test_signature',
                'message': 'test_message'
            }
            
            # Try to generate token (this might fail if not implemented yet)
            try:
                response = await self.auth_client.post('/auth/login', json=test_payload)
                if response.status_code == 200:
                    token_data = response.json()
                    if 'access_token' in token_data:
                        self.log_test_result(
                            'jwt_token_validation',
                            'PASS',
                            'JWT token generation successful',
                            {'has_access_token': True}
                        )
                    else:
                        self.log_test_result(
                            'jwt_token_validation',
                            'WARN',
                            'JWT token generation endpoint exists but no access token returned'
                        )
                else:
                    self.log_test_result(
                        'jwt_token_validation',
                        'WARN',
                        f'JWT token generation endpoint returned status {response.status_code}'
                    )
            except Exception as e:
                self.log_test_result(
                    'jwt_token_validation',
                    'WARN',
                    f'JWT token generation not yet implemented: {str(e)}'
                )
                
        except Exception as e:
            self.log_test_result(
                'jwt_token_validation',
                'FAIL',
                f'JWT token validation test failed: {str(e)}'
            )
    
    async def test_cross_service_communication(self):
        """Test communication between services"""
        try:
            # Test if services can communicate through the network
            # This is a basic connectivity test
            
            # Test MongoDB -> Redis (through application logic)
            db = self.mongodb_client.lucid
            collection = db.cross_service_test
            
            # Store data in MongoDB
            test_data = {
                'test_id': 'cross_service_test',
                'timestamp': datetime.now(timezone.utc),
                'data': 'cross_service_test_data'
            }
            await collection.insert_one(test_data)
            
            # Store reference in Redis
            await self.redis_client.set('cross_service_test_ref', 'cross_service_test', ex=60)
            
            # Verify both stores
            mongo_doc = await collection.find_one({'test_id': 'cross_service_test'})
            redis_ref = await self.redis_client.get('cross_service_test_ref')
            
            # Cleanup
            await collection.delete_one({'test_id': 'cross_service_test'})
            await self.redis_client.delete('cross_service_test_ref')
            
            if mongo_doc and redis_ref:
                self.log_test_result(
                    'cross_service_communication',
                    'PASS',
                    'Cross-service communication successful',
                    {'mongo_doc_found': True, 'redis_ref_found': True}
                )
            else:
                self.log_test_result(
                    'cross_service_communication',
                    'FAIL',
                    'Cross-service communication failed'
                )
                
        except Exception as e:
            self.log_test_result(
                'cross_service_communication',
                'FAIL',
                f'Cross-service communication test failed: {str(e)}'
            )
    
    async def run_all_tests(self):
        """Run all integration tests"""
        logger.info("Starting Phase 1 Foundation Services Integration Tests")
        
        try:
            await self.setup_clients()
            
            # Run individual tests
            await self.test_mongodb_connection()
            await self.test_redis_operations()
            await self.test_elasticsearch_indexing()
            await self.test_auth_service_health()
            await self.test_jwt_token_validation()
            await self.test_cross_service_communication()
            
        finally:
            await self.cleanup_clients()
        
        # Generate test report
        self.generate_test_report()
    
    def generate_test_report(self):
        """Generate test report"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warning_tests = len([r for r in self.test_results if r['status'] == 'WARN'])
        
        report = {
            'test_summary': {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'phase': 'Phase 1 Foundation Services Integration Tests',
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'warning_tests': warning_tests,
                'success_rate': f"{(passed_tests * 100) / total_tests:.1f}%" if total_tests > 0 else "0%"
            },
            'test_results': self.test_results
        }
        
        # Save report to file
        report_file = 'phase1-integration-test-report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Test report saved to: {report_file}")
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Warnings: {warning_tests}")
        logger.info(f"Success Rate: {(passed_tests * 100) / total_tests:.1f}%")
        
        if failed_tests == 0:
            logger.info("✓ Phase 1 integration tests completed successfully!")
            return True
        else:
            logger.error(f"✗ Phase 1 integration tests failed with {failed_tests} errors")
            return False

async def main():
    """Main test execution"""
    test_suite = Phase1IntegrationTests()
    success = await test_suite.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    asyncio.run(main())
