"""
Database Query Performance Tests

Tests database query performance benchmarks:
- Query latency: <10ms p95 query latency
- Connection pooling: Efficient connection management
- Index performance: Optimized query execution
- Concurrent queries: Multiple simultaneous operations
- Data retrieval: Fast data access patterns

Tests MongoDB, Redis, and Elasticsearch performance.
"""

import asyncio
import aiohttp
import pytest
import time
import statistics
import random
import string
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
import json
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis
from elasticsearch import AsyncElasticsearch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class QueryMetrics:
    """Database query performance metrics"""
    query_type: str
    execution_time: float
    result_count: int
    success: bool
    error_message: Optional[str] = None

@dataclass
class DatabaseMetrics:
    """Database performance metrics"""
    database_type: str
    total_queries: int
    successful_queries: int
    failed_queries: int
    avg_latency: float
    p95_latency: float
    p99_latency: float
    min_latency: float
    max_latency: float

class DatabasePerformanceTester:
    """Database performance tester"""
    
    def __init__(self, 
                 mongodb_uri: str = "mongodb://localhost:27017/lucid_perf_test",
                 redis_uri: str = "redis://localhost:6379/0",
                 elasticsearch_uri: str = "http://localhost:9200"):
        self.mongodb_uri = mongodb_uri
        self.redis_uri = redis_uri
        self.elasticsearch_uri = elasticsearch_uri
        
        self.mongo_client = None
        self.redis_client = None
        self.elasticsearch_client = None
        
    async def __aenter__(self):
        # Initialize MongoDB client
        self.mongo_client = AsyncIOMotorClient(self.mongodb_uri)
        
        # Initialize Redis client
        self.redis_client = redis.from_url(self.redis_uri)
        
        # Initialize Elasticsearch client
        self.elasticsearch_client = AsyncElasticsearch([self.elasticsearch_uri])
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.mongo_client:
            self.mongo_client.close()
        if self.redis_client:
            await self.redis_client.close()
        if self.elasticsearch_client:
            await self.elasticsearch_client.close()
    
    def generate_test_data(self, count: int = 1000) -> List[Dict[str, Any]]:
        """Generate test data for performance testing"""
        test_data = []
        
        for i in range(count):
            data = {
                "id": f"test_doc_{i}",
                "user_id": f"user_{i % 100}",
                "session_id": f"session_{i % 50}",
                "timestamp": int(time.time()) + i,
                "data": {
                    "value": random.randint(1, 1000),
                    "text": ''.join(random.choices(string.ascii_letters, k=50)),
                    "nested": {
                        "level1": {
                            "level2": f"nested_value_{i}"
                        }
                    }
                },
                "tags": [f"tag_{j}" for j in range(random.randint(1, 5))],
                "status": random.choice(["active", "inactive", "pending"])
            }
            test_data.append(data)
        
        return test_data
    
    async def setup_test_data(self):
        """Setup test data in all databases"""
        logger.info("Setting up test data...")
        
        # Generate test data
        test_data = self.generate_test_data(1000)
        
        # Setup MongoDB test data
        try:
            db = self.mongo_client.lucid_perf_test
            collection = db.test_documents
            
            # Clear existing data
            await collection.delete_many({})
            
            # Insert test data
            await collection.insert_many(test_data)
            
            # Create indexes for performance testing
            await collection.create_index("user_id")
            await collection.create_index("session_id")
            await collection.create_index("timestamp")
            await collection.create_index("status")
            await collection.create_index([("user_id", 1), ("timestamp", -1)])
            
            logger.info(f"Inserted {len(test_data)} documents into MongoDB")
            
        except Exception as e:
            logger.error(f"Error setting up MongoDB test data: {e}")
        
        # Setup Redis test data
        try:
            # Clear existing test keys
            keys = await self.redis_client.keys("perf_test:*")
            if keys:
                await self.redis_client.delete(*keys)
            
            # Insert test data
            for i, data in enumerate(test_data[:100]):  # Limit Redis data
                key = f"perf_test:doc:{i}"
                await self.redis_client.set(key, json.dumps(data))
            
            logger.info(f"Inserted {min(100, len(test_data))} documents into Redis")
            
        except Exception as e:
            logger.error(f"Error setting up Redis test data: {e}")
        
        # Setup Elasticsearch test data
        try:
            index_name = "lucid_perf_test"
            
            # Delete index if exists
            if await self.elasticsearch_client.indices.exists(index=index_name):
                await self.elasticsearch_client.indices.delete(index=index_name)
            
            # Create index
            await self.elasticsearch_client.indices.create(
                index=index_name,
                body={
                    "mappings": {
                        "properties": {
                            "user_id": {"type": "keyword"},
                            "session_id": {"type": "keyword"},
                            "timestamp": {"type": "date"},
                            "status": {"type": "keyword"},
                            "data.value": {"type": "integer"},
                            "data.text": {"type": "text"},
                            "tags": {"type": "keyword"}
                        }
                    }
                }
            )
            
            # Bulk insert test data
            bulk_data = []
            for doc in test_data:
                bulk_data.append({
                    "_index": index_name,
                    "_source": doc
                })
            
            if bulk_data:
                await self.elasticsearch_client.bulk(body=bulk_data)
            
            # Refresh index
            await self.elasticsearch_client.indices.refresh(index=index_name)
            
            logger.info(f"Inserted {len(test_data)} documents into Elasticsearch")
            
        except Exception as e:
            logger.error(f"Error setting up Elasticsearch test data: {e}")
    
    async def test_mongodb_query(self, query_type: str, query_params: Dict[str, Any]) -> QueryMetrics:
        """Test MongoDB query performance"""
        start_time = time.time()
        
        try:
            db = self.mongo_client.lucid_perf_test
            collection = db.test_documents
            
            if query_type == "find_by_user":
                result = await collection.find({"user_id": query_params["user_id"]}).to_list(length=100)
                result_count = len(result)
                
            elif query_type == "find_by_session":
                result = await collection.find({"session_id": query_params["session_id"]}).to_list(length=100)
                result_count = len(result)
                
            elif query_type == "find_by_timestamp_range":
                result = await collection.find({
                    "timestamp": {
                        "$gte": query_params["start_time"],
                        "$lte": query_params["end_time"]
                    }
                }).to_list(length=100)
                result_count = len(result)
                
            elif query_type == "find_by_status":
                result = await collection.find({"status": query_params["status"]}).to_list(length=100)
                result_count = len(result)
                
            elif query_type == "aggregate_by_user":
                pipeline = [
                    {"$match": {"user_id": query_params["user_id"]}},
                    {"$group": {"_id": "$status", "count": {"$sum": 1}}}
                ]
                result = await collection.aggregate(pipeline).to_list(length=100)
                result_count = len(result)
                
            elif query_type == "complex_query":
                result = await collection.find({
                    "user_id": query_params["user_id"],
                    "status": {"$in": ["active", "pending"]},
                    "timestamp": {"$gte": query_params["start_time"]}
                }).sort("timestamp", -1).limit(50).to_list(length=100)
                result_count = len(result)
                
            else:
                raise ValueError(f"Unknown query type: {query_type}")
            
            execution_time = time.time() - start_time
            
            return QueryMetrics(
                query_type=query_type,
                execution_time=execution_time,
                result_count=result_count,
                success=True
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return QueryMetrics(
                query_type=query_type,
                execution_time=execution_time,
                result_count=0,
                success=False,
                error_message=str(e)
            )
    
    async def test_redis_query(self, query_type: str, query_params: Dict[str, Any]) -> QueryMetrics:
        """Test Redis query performance"""
        start_time = time.time()
        
        try:
            if query_type == "get_by_key":
                key = f"perf_test:doc:{query_params['doc_id']}"
                result = await self.redis_client.get(key)
                result_count = 1 if result else 0
                
            elif query_type == "get_multiple_keys":
                keys = [f"perf_test:doc:{i}" for i in range(query_params["count"])]
                results = await self.redis_client.mget(keys)
                result_count = len([r for r in results if r is not None])
                
            elif query_type == "set_key":
                key = f"perf_test:temp:{query_params['key_id']}"
                value = json.dumps({"data": f"test_value_{query_params['key_id']}"})
                await self.redis_client.set(key, value, ex=60)  # Expire in 60 seconds
                result_count = 1
                
            elif query_type == "hash_operations":
                hash_key = f"perf_test:hash:{query_params['hash_id']}"
                # Set multiple hash fields
                for i in range(10):
                    await self.redis_client.hset(hash_key, f"field_{i}", f"value_{i}")
                
                # Get all hash fields
                result = await self.redis_client.hgetall(hash_key)
                result_count = len(result)
                
            else:
                raise ValueError(f"Unknown query type: {query_type}")
            
            execution_time = time.time() - start_time
            
            return QueryMetrics(
                query_type=query_type,
                execution_time=execution_time,
                result_count=result_count,
                success=True
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return QueryMetrics(
                query_type=query_type,
                execution_time=execution_time,
                result_count=0,
                success=False,
                error_message=str(e)
            )
    
    async def test_elasticsearch_query(self, query_type: str, query_params: Dict[str, Any]) -> QueryMetrics:
        """Test Elasticsearch query performance"""
        start_time = time.time()
        
        try:
            index_name = "lucid_perf_test"
            
            if query_type == "search_by_user":
                query = {
                    "query": {
                        "term": {
                            "user_id": query_params["user_id"]
                        }
                    }
                }
                result = await self.elasticsearch_client.search(
                    index=index_name,
                    body=query,
                    size=100
                )
                result_count = result["hits"]["total"]["value"]
                
            elif query_type == "search_by_status":
                query = {
                    "query": {
                        "term": {
                            "status": query_params["status"]
                        }
                    }
                }
                result = await self.elasticsearch_client.search(
                    index=index_name,
                    body=query,
                    size=100
                )
                result_count = result["hits"]["total"]["value"]
                
            elif query_type == "search_by_timestamp_range":
                query = {
                    "query": {
                        "range": {
                            "timestamp": {
                                "gte": query_params["start_time"],
                                "lte": query_params["end_time"]
                            }
                        }
                    }
                }
                result = await self.elasticsearch_client.search(
                    index=index_name,
                    body=query,
                    size=100
                )
                result_count = result["hits"]["total"]["value"]
                
            elif query_type == "text_search":
                query = {
                    "query": {
                        "match": {
                            "data.text": query_params["search_text"]
                        }
                    }
                }
                result = await self.elasticsearch_client.search(
                    index=index_name,
                    body=query,
                    size=100
                )
                result_count = result["hits"]["total"]["value"]
                
            elif query_type == "aggregation_query":
                query = {
                    "size": 0,
                    "aggs": {
                        "status_counts": {
                            "terms": {
                                "field": "status"
                            }
                        }
                    }
                }
                result = await self.elasticsearch_client.search(
                    index=index_name,
                    body=query
                )
                result_count = len(result["aggregations"]["status_counts"]["buckets"])
                
            else:
                raise ValueError(f"Unknown query type: {query_type}")
            
            execution_time = time.time() - start_time
            
            return QueryMetrics(
                query_type=query_type,
                execution_time=execution_time,
                result_count=result_count,
                success=True
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return QueryMetrics(
                query_type=query_type,
                execution_time=execution_time,
                result_count=0,
                success=False,
                error_message=str(e)
            )
    
    async def run_database_benchmark(self, database_type: str, query_count: int = 100) -> DatabaseMetrics:
        """Run comprehensive database benchmark"""
        query_metrics = []
        
        if database_type == "mongodb":
            # MongoDB query types and parameters
            query_types = [
                ("find_by_user", {"user_id": f"user_{i % 100}"}),
                ("find_by_session", {"session_id": f"session_{i % 50}"}),
                ("find_by_status", {"status": random.choice(["active", "inactive", "pending"])}),
                ("find_by_timestamp_range", {
                    "start_time": int(time.time()) - 1000,
                    "end_time": int(time.time())
                }),
                ("aggregate_by_user", {"user_id": f"user_{i % 100}"}),
                ("complex_query", {
                    "user_id": f"user_{i % 100}",
                    "start_time": int(time.time()) - 500
                })
            ]
            
            for i in range(query_count):
                query_type, query_params = random.choice(query_types)
                metrics = await self.test_mongodb_query(query_type, query_params)
                query_metrics.append(metrics)
                
        elif database_type == "redis":
            # Redis query types and parameters
            query_types = [
                ("get_by_key", {"doc_id": i % 100}),
                ("get_multiple_keys", {"count": 10}),
                ("set_key", {"key_id": i}),
                ("hash_operations", {"hash_id": i % 50})
            ]
            
            for i in range(query_count):
                query_type, query_params = random.choice(query_types)
                metrics = await self.test_redis_query(query_type, query_params)
                query_metrics.append(metrics)
                
        elif database_type == "elasticsearch":
            # Elasticsearch query types and parameters
            query_types = [
                ("search_by_user", {"user_id": f"user_{i % 100}"}),
                ("search_by_status", {"status": random.choice(["active", "inactive", "pending"])}),
                ("search_by_timestamp_range", {
                    "start_time": int(time.time()) - 1000,
                    "end_time": int(time.time())
                }),
                ("text_search", {"search_text": "test"}),
                ("aggregation_query", {})
            ]
            
            for i in range(query_count):
                query_type, query_params = random.choice(query_types)
                metrics = await self.test_elasticsearch_query(query_type, query_params)
                query_metrics.append(metrics)
        
        # Calculate metrics
        successful_queries = [m for m in query_metrics if m.success]
        failed_queries = [m for m in query_metrics if not m.success]
        
        if not successful_queries:
            raise Exception(f"No successful queries for {database_type}")
        
        latencies = [m.execution_time * 1000 for m in successful_queries]  # Convert to ms
        
        return DatabaseMetrics(
            database_type=database_type,
            total_queries=len(query_metrics),
            successful_queries=len(successful_queries),
            failed_queries=len(failed_queries),
            avg_latency=statistics.mean(latencies),
            p95_latency=statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies),
            p99_latency=statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies),
            min_latency=min(latencies),
            max_latency=max(latencies)
        )

@pytest.mark.asyncio
class TestDatabaseQueryPerformance:
    """Database query performance tests"""
    
    @pytest.fixture
    async def db_tester(self):
        """Database performance tester fixture"""
        async with DatabasePerformanceTester() as tester:
            # Setup test data
            await tester.setup_test_data()
            yield tester
    
    async def test_mongodb_query_performance(self, db_tester):
        """Test MongoDB query performance with <10ms p95 latency"""
        metrics = await db_tester.run_database_benchmark("mongodb", query_count=100)
        
        logger.info(f"MongoDB performance metrics: {metrics}")
        
        # Assert p95 latency < 10ms
        assert metrics.p95_latency < 10, \
            f"MongoDB p95 latency {metrics.p95_latency:.2f}ms exceeds 10ms threshold"
        
        # Assert p99 latency < 20ms
        assert metrics.p99_latency < 20, \
            f"MongoDB p99 latency {metrics.p99_latency:.2f}ms exceeds 20ms threshold"
        
        # Assert high success rate
        success_rate = metrics.successful_queries / metrics.total_queries
        assert success_rate > 0.95, \
            f"MongoDB success rate {success_rate:.2%} below 95% threshold"
    
    async def test_redis_query_performance(self, db_tester):
        """Test Redis query performance with <10ms p95 latency"""
        metrics = await db_tester.run_database_benchmark("redis", query_count=100)
        
        logger.info(f"Redis performance metrics: {metrics}")
        
        # Assert p95 latency < 10ms
        assert metrics.p95_latency < 10, \
            f"Redis p95 latency {metrics.p95_latency:.2f}ms exceeds 10ms threshold"
        
        # Assert p99 latency < 15ms
        assert metrics.p99_latency < 15, \
            f"Redis p99 latency {metrics.p99_latency:.2f}ms exceeds 15ms threshold"
        
        # Assert high success rate
        success_rate = metrics.successful_queries / metrics.total_queries
        assert success_rate > 0.95, \
            f"Redis success rate {success_rate:.2%} below 95% threshold"
    
    async def test_elasticsearch_query_performance(self, db_tester):
        """Test Elasticsearch query performance with <10ms p95 latency"""
        metrics = await db_tester.run_database_benchmark("elasticsearch", query_count=100)
        
        logger.info(f"Elasticsearch performance metrics: {metrics}")
        
        # Assert p95 latency < 10ms
        assert metrics.p95_latency < 10, \
            f"Elasticsearch p95 latency {metrics.p95_latency:.2f}ms exceeds 10ms threshold"
        
        # Assert p99 latency < 20ms
        assert metrics.p99_latency < 20, \
            f"Elasticsearch p99 latency {metrics.p99_latency:.2f}ms exceeds 20ms threshold"
        
        # Assert high success rate
        success_rate = metrics.successful_queries / metrics.total_queries
        assert success_rate > 0.95, \
            f"Elasticsearch success rate {success_rate:.2%} below 95% threshold"
    
    async def test_concurrent_database_queries(self, db_tester):
        """Test concurrent database query performance"""
        concurrent_queries = 50
        
        async def run_mongodb_queries():
            return await db_tester.run_database_benchmark("mongodb", query_count=20)
        
        async def run_redis_queries():
            return await db_tester.run_database_benchmark("redis", query_count=20)
        
        async def run_elasticsearch_queries():
            return await db_tester.run_database_benchmark("elasticsearch", query_count=20)
        
        # Run concurrent queries across all databases
        start_time = time.time()
        tasks = [
            run_mongodb_queries(),
            run_redis_queries(),
            run_elasticsearch_queries()
        ]
        
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Analyze concurrent performance
        for result in results:
            logger.info(f"Concurrent {result.database_type} metrics: {result}")
            
            # Assert performance remains good under concurrent load
            assert result.p95_latency < 15, \
                f"Concurrent {result.database_type} p95 latency {result.p95_latency:.2f}ms exceeds 15ms threshold"
            
            # Assert high success rate maintained
            success_rate = result.successful_queries / result.total_queries
            assert success_rate > 0.9, \
                f"Concurrent {result.database_type} success rate {success_rate:.2%} below 90% threshold"
    
    async def test_database_connection_pooling(self, db_tester):
        """Test database connection pooling performance"""
        # Test multiple rapid connections
        connection_tests = 100
        
        async def test_connection():
            start_time = time.time()
            # Simulate a simple query that tests connection
            try:
                if hasattr(db_tester, 'mongo_client'):
                    await db_tester.mongo_client.admin.command('ping')
                connection_time = time.time() - start_time
                return connection_time, True
            except Exception as e:
                connection_time = time.time() - start_time
                return connection_time, False
        
        # Run connection tests concurrently
        tasks = [test_connection() for _ in range(connection_tests)]
        results = await asyncio.gather(*tasks)
        
        connection_times = [time for time, success in results if success]
        successful_connections = sum(1 for _, success in results if success)
        
        if connection_times:
            avg_connection_time = statistics.mean(connection_times) * 1000  # Convert to ms
            p95_connection_time = statistics.quantiles(connection_times, n=20)[18] * 1000 if len(connection_times) >= 20 else max(connection_times) * 1000
            
            logger.info(f"Connection pooling - Avg: {avg_connection_time:.2f}ms, p95: {p95_connection_time:.2f}ms")
            
            # Assert connection times are reasonable
            assert avg_connection_time < 5, \
                f"Average connection time {avg_connection_time:.2f}ms exceeds 5ms threshold"
            
            assert p95_connection_time < 10, \
                f"p95 connection time {p95_connection_time:.2f}ms exceeds 10ms threshold"
        
        # Assert high connection success rate
        connection_success_rate = successful_connections / connection_tests
        assert connection_success_rate > 0.95, \
            f"Connection success rate {connection_success_rate:.2%} below 95% threshold"

@pytest.mark.performance
@pytest.mark.slow
class TestDatabaseExtendedPerformance:
    """Extended database performance tests"""
    
    async def test_database_under_sustained_load(self):
        """Test database performance under sustained load"""
        async with DatabasePerformanceTester() as tester:
            await tester.setup_test_data()
            
            # Run sustained load test for 5 minutes
            duration_seconds = 300
            query_interval = 1  # Query every second
            
            start_time = time.time()
            all_metrics = []
            
            while time.time() - start_time < duration_seconds:
                # Run quick benchmark
                metrics = await tester.run_database_benchmark("mongodb", query_count=10)
                all_metrics.append(metrics)
                
                await asyncio.sleep(query_interval)
            
            # Analyze sustained performance
            p95_latencies = [m.p95_latency for m in all_metrics]
            avg_p95 = statistics.mean(p95_latencies)
            max_p95 = max(p95_latencies)
            
            logger.info(f"Sustained load - Avg p95: {avg_p95:.2f}ms, Max p95: {max_p95:.2f}ms")
            
            # Assert sustained performance remains good
            assert avg_p95 < 15, \
                f"Sustained average p95 latency {avg_p95:.2f}ms exceeds 15ms threshold"
            
            assert max_p95 < 25, \
                f"Sustained max p95 latency {max_p95:.2f}ms exceeds 25ms threshold"

if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "--tb=short"])
