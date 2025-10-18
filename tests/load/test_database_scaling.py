"""
Database Scaling Load Testing

Tests the system's ability to handle database operations under load
including connection pooling, query performance, and data consistency.

Performance Targets:
- Database queries: <50ms per query
- Connection pool: <100ms per connection
- Write operations: <100ms per write
- Read operations: <25ms per read
"""

import asyncio
import aiohttp
import pytest
import time
import json
import random
from typing import List, Dict, Any
from dataclasses import dataclass
import statistics
import motor.motor_asyncio
from pymongo import MongoClient

@dataclass
class DatabaseMetrics:
    """Metrics for database operations"""
    operation_id: str
    query_time: float
    connection_time: float
    write_time: float
    read_time: float
    total_time: float
    success: bool
    error_message: str = ""

class DatabaseScalingTest:
    """Load testing for database scaling operations"""
    
    def __init__(self, mongodb_url: str = "mongodb://localhost:27017/lucid"):
        self.mongodb_url = mongodb_url
        self.db_metrics: List[DatabaseMetrics] = []
        
    async def simulate_database_operations(self, operation_id: int) -> DatabaseMetrics:
        """Simulate database operations under load"""
        start_time = time.time()
        metrics = DatabaseMetrics(
            operation_id=f"db_op_{operation_id}",
            query_time=0,
            connection_time=0,
            write_time=0,
            read_time=0,
            total_time=0,
            success=False
        )
        
        try:
            # Step 1: Database Connection
            connection_start = time.time()
            client = motor.motor_asyncio.AsyncIOMotorClient(self.mongodb_url)
            db = client.lucid
            metrics.connection_time = (time.time() - connection_start) * 1000
            
            # Step 2: Write Operations
            write_start = time.time()
            test_data = {
                "operation_id": f"loadtest_op_{operation_id}",
                "timestamp": time.time(),
                "user_id": f"user_{random.randint(1, 1000)}",
                "session_id": f"session_{random.randint(1, 100)}",
                "data": {
                    "chunk_id": f"chunk_{random.randint(1, 1000)}",
                    "size_bytes": random.randint(1024, 10485760),  # 1KB to 10MB
                    "compression_ratio": random.uniform(0.1, 0.9),
                    "encryption_key": f"key_{random.randint(1, 1000)}"
                },
                "metadata": {
                    "source": "load_test",
                    "priority": random.choice(["low", "medium", "high"]),
                    "retention_days": random.randint(30, 365)
                }
            }
            
            # Insert test document
            await db.test_load.insert_one(test_data)
            
            # Update document
            await db.test_load.update_one(
                {"operation_id": f"loadtest_op_{operation_id}"},
                {"$set": {"updated_at": time.time()}}
            )
            
            metrics.write_time = (time.time() - write_start) * 1000
            
            # Step 3: Read Operations
            read_start = time.time()
            
            # Simple query
            doc = await db.test_load.find_one({"operation_id": f"loadtest_op_{operation_id}"})
            
            # Complex aggregation query
            pipeline = [
                {"$match": {"user_id": test_data["user_id"]}},
                {"$group": {
                    "_id": "$user_id",
                    "total_sessions": {"$sum": 1},
                    "avg_size": {"$avg": "$data.size_bytes"},
                    "max_size": {"$max": "$data.size_bytes"}
                }}
            ]
            result = await db.test_load.aggregate(pipeline).to_list(1)
            
            # Index query
            await db.test_load.find({"timestamp": {"$gte": time.time() - 3600}}).to_list(10)
            
            metrics.read_time = (time.time() - read_start) * 1000
            
            # Step 4: Complex Query Operations
            query_start = time.time()
            
            # Range query
            await db.test_load.find({
                "data.size_bytes": {"$gte": 1024, "$lte": 1048576}
            }).to_list(100)
            
            # Text search (if index exists)
            await db.test_load.find({
                "metadata.source": "load_test"
            }).to_list(50)
            
            # Sort and limit
            await db.test_load.find().sort("timestamp", -1).limit(20).to_list(20)
            
            metrics.query_time = (time.time() - query_start) * 1000
            
            # Cleanup
            await db.test_load.delete_one({"operation_id": f"loadtest_op_{operation_id}"})
            
            metrics.total_time = (time.time() - start_time) * 1000
            metrics.success = True
            
            # Close connection
            client.close()
            
        except Exception as e:
            metrics.total_time = (time.time() - start_time) * 1000
            metrics.error_message = str(e)
            metrics.success = False
            
        return metrics
    
    async def run_database_scaling_test(self, num_operations: int = 1000) -> Dict[str, Any]:
        """Run database scaling load test"""
        print(f"Starting database scaling test with {num_operations} operations...")
        
        start_time = time.time()
        
        # Create semaphore to limit concurrent database connections
        semaphore = asyncio.Semaphore(100)  # Limit to 100 concurrent connections
        
        async def limited_db_operation(operation_id):
            async with semaphore:
                return await self.simulate_database_operations(operation_id)
        
        # Run concurrent database operations
        tasks = [limited_db_operation(i) for i in range(num_operations)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Process results
        successful_operations = [r for r in results if isinstance(r, DatabaseMetrics) and r.success]
        failed_operations = [r for r in results if isinstance(r, DatabaseMetrics) and not r.success]
        
        # Calculate metrics
        if successful_operations:
            query_times = [o.query_time for o in successful_operations]
            connection_times = [o.connection_time for o in successful_operations]
            write_times = [o.write_time for o in successful_operations]
            read_times = [o.read_time for o in successful_operations]
            total_times = [o.total_time for o in successful_operations]
            
            metrics = {
                "total_operations": num_operations,
                "successful_operations": len(successful_operations),
                "failed_operations": len(failed_operations),
                "success_rate": len(successful_operations) / num_operations * 100,
                "total_test_time": total_time,
                "operations_per_second": num_operations / total_time,
                "query_time": {
                    "mean": statistics.mean(query_times),
                    "median": statistics.median(query_times),
                    "p95": sorted(query_times)[int(len(query_times) * 0.95)],
                    "max": max(query_times)
                },
                "connection_time": {
                    "mean": statistics.mean(connection_times),
                    "median": statistics.median(connection_times),
                    "p95": sorted(connection_times)[int(len(connection_times) * 0.95)],
                    "max": max(connection_times)
                },
                "write_time": {
                    "mean": statistics.mean(write_times),
                    "median": statistics.median(write_times),
                    "p95": sorted(write_times)[int(len(write_times) * 0.95)],
                    "max": max(write_times)
                },
                "read_time": {
                    "mean": statistics.mean(read_times),
                    "median": statistics.median(read_times),
                    "p95": sorted(read_times)[int(len(read_times) * 0.95)],
                    "max": max(read_times)
                },
                "total_time": {
                    "mean": statistics.mean(total_times),
                    "median": statistics.median(total_times),
                    "p95": sorted(total_times)[int(len(total_times) * 0.95)],
                    "max": max(total_times)
                }
            }
        else:
            metrics = {
                "total_operations": num_operations,
                "successful_operations": 0,
                "failed_operations": len(failed_operations),
                "success_rate": 0,
                "total_test_time": total_time,
                "operations_per_second": 0,
                "error": "No successful operations"
            }
        
        return metrics

@pytest.mark.asyncio
async def test_database_scaling_load():
    """Test database scaling with 1000 operations"""
    test = DatabaseScalingTest()
    metrics = await test.run_database_scaling_test(1000)
    
    # Assertions
    assert metrics["success_rate"] >= 95.0, f"Success rate {metrics['success_rate']}% below 95%"
    assert metrics["query_time"]["p95"] <= 50, f"Query time p95 {metrics['query_time']['p95']}ms exceeds 50ms"
    assert metrics["connection_time"]["p95"] <= 100, f"Connection time p95 {metrics['connection_time']['p95']}ms exceeds 100ms"
    assert metrics["write_time"]["p95"] <= 100, f"Write time p95 {metrics['write_time']['p95']}ms exceeds 100ms"
    assert metrics["read_time"]["p95"] <= 25, f"Read time p95 {metrics['read_time']['p95']}ms exceeds 25ms"
    
    print(f"Database Scaling Test Results:")
    print(f"  Success Rate: {metrics['success_rate']:.1f}%")
    print(f"  Operations/sec: {metrics['operations_per_second']:.1f}")
    print(f"  Query Time p95: {metrics['query_time']['p95']:.1f}ms")
    print(f"  Connection Time p95: {metrics['connection_time']['p95']:.1f}ms")
    print(f"  Write Time p95: {metrics['write_time']['p95']:.1f}ms")
    print(f"  Read Time p95: {metrics['read_time']['p95']:.1f}ms")

@pytest.mark.asyncio
async def test_database_connection_pooling():
    """Test database connection pooling under load"""
    test = DatabaseScalingTest()
    
    # Test connection pooling with rapid connections
    async with motor.motor_asyncio.AsyncIOMotorClient(test.mongodb_url) as client:
        db = client.lucid
        
        # Test concurrent connections
        tasks = []
        for i in range(200):  # 200 concurrent connections
            async def db_operation(op_id):
                try:
                    # Simple operation to test connection
                    result = await db.test_pool.find_one({"test": f"connection_{op_id}"})
                    return True
                except Exception:
                    return False
            
            tasks.append(db_operation(i))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful = [r for r in results if r is True]
        
        assert len(successful) >= 180, f"Only {len(successful)}/200 connection pool operations succeeded"
        
        print(f"Connection Pool Test Results:")
        print(f"  Successful connections: {len(successful)}/200")
        print(f"  Success rate: {len(successful)/200*100:.1f}%")

@pytest.mark.asyncio
async def test_database_write_throughput():
    """Test database write throughput"""
    test = DatabaseScalingTest()
    
    # Test write throughput
    async with motor.motor_asyncio.AsyncIOMotorClient(test.mongodb_url) as client:
        db = client.lucid
        
        start_time = time.time()
        tasks = []
        
        for i in range(500):  # 500 write operations
            async def write_operation(op_id):
                try:
                    doc = {
                        "test_id": f"throughput_{op_id}",
                        "timestamp": time.time(),
                        "data": f"test_data_{op_id}"
                    }
                    await db.test_throughput.insert_one(doc)
                    return True
                except Exception:
                    return False
            
            tasks.append(write_operation(i))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful = [r for r in results if r is True]
        total_time = time.time() - start_time
        
        # Cleanup
        await db.test_throughput.delete_many({"test_id": {"$regex": "throughput_"}})
        
        assert len(successful) >= 450, f"Only {len(successful)}/500 write operations succeeded"
        assert total_time <= 10, f"Write throughput test took {total_time:.1f}s, exceeds 10s"
        
        print(f"Write Throughput Test Results:")
        print(f"  Successful writes: {len(successful)}/500")
        print(f"  Total time: {total_time:.1f}s")
        print(f"  Writes/sec: {len(successful)/total_time:.1f}")

if __name__ == "__main__":
    # Run the test directly
    asyncio.run(test_database_scaling_load())
