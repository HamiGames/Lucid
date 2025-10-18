"""
API Gateway Throughput Performance Tests

Tests API Gateway performance benchmarks:
- Throughput: >1000 requests/second
- Latency: <50ms p95, <100ms p99
- Concurrent connections: >500

Uses asyncio and aiohttp for high-performance testing.
"""

import asyncio
import aiohttp
import pytest
import time
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance test results container"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time: float
    requests_per_second: float
    avg_latency: float
    p95_latency: float
    p99_latency: float
    min_latency: float
    max_latency: float

class APIGatewayPerformanceTester:
    """High-performance API Gateway tester"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=1000, limit_per_host=1000)
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def make_request(self, endpoint: str, method: str = "GET", 
                          data: Dict[str, Any] = None) -> tuple:
        """Make a single HTTP request and return (success, latency)"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            if method == "GET":
                async with self.session.get(url) as response:
                    await response.text()
                    success = response.status == 200
            elif method == "POST":
                async with self.session.post(url, json=data) as response:
                    await response.text()
                    success = response.status in [200, 201]
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            latency = (time.time() - start_time) * 1000  # Convert to ms
            return success, latency
            
        except Exception as e:
            logger.warning(f"Request failed: {e}")
            latency = (time.time() - start_time) * 1000
            return False, latency
    
    async def run_concurrent_requests(self, endpoint: str, 
                                    concurrent_users: int = 100,
                                    requests_per_user: int = 10,
                                    method: str = "GET") -> PerformanceMetrics:
        """Run concurrent requests and measure performance"""
        
        async def user_simulation():
            """Simulate a single user making requests"""
            user_results = []
            for _ in range(requests_per_user):
                success, latency = await self.make_request(endpoint, method)
                user_results.append((success, latency))
                # Small delay between requests to simulate realistic usage
                await asyncio.sleep(0.01)
            return user_results
        
        # Start all concurrent users
        start_time = time.time()
        tasks = [user_simulation() for _ in range(concurrent_users)]
        all_results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Flatten results
        flat_results = []
        for user_results in all_results:
            flat_results.extend(user_results)
        
        # Calculate metrics
        successful_requests = sum(1 for success, _ in flat_results if success)
        failed_requests = len(flat_results) - successful_requests
        latencies = [latency for _, latency in flat_results]
        
        requests_per_second = len(flat_results) / total_time
        avg_latency = statistics.mean(latencies) if latencies else 0
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
        p99_latency = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies)
        
        return PerformanceMetrics(
            total_requests=len(flat_results),
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            total_time=total_time,
            requests_per_second=requests_per_second,
            avg_latency=avg_latency,
            p95_latency=p95_latency,
            p99_latency=p99_latency,
            min_latency=min(latencies) if latencies else 0,
            max_latency=max(latencies) if latencies else 0
        )

@pytest.mark.asyncio
class TestAPIGatewayThroughput:
    """API Gateway throughput performance tests"""
    
    @pytest.fixture
    async def performance_tester(self):
        """Performance tester fixture"""
        async with APIGatewayPerformanceTester() as tester:
            yield tester
    
    async def test_health_endpoint_throughput(self, performance_tester):
        """Test health endpoint can handle >1000 req/s"""
        metrics = await performance_tester.run_concurrent_requests(
            endpoint="/health",
            concurrent_users=200,
            requests_per_user=10
        )
        
        logger.info(f"Health endpoint metrics: {metrics}")
        
        # Assert throughput > 1000 req/s
        assert metrics.requests_per_second > 1000, \
            f"Throughput {metrics.requests_per_second:.2f} req/s below threshold of 1000 req/s"
        
        # Assert p95 latency < 50ms
        assert metrics.p95_latency < 50, \
            f"p95 latency {metrics.p95_latency:.2f}ms above threshold of 50ms"
        
        # Assert p99 latency < 100ms
        assert metrics.p99_latency < 100, \
            f"p99 latency {metrics.p99_latency:.2f}ms above threshold of 100ms"
        
        # Assert success rate > 95%
        success_rate = metrics.successful_requests / metrics.total_requests
        assert success_rate > 0.95, \
            f"Success rate {success_rate:.2%} below threshold of 95%"
    
    async def test_auth_endpoint_throughput(self, performance_tester):
        """Test authentication endpoint performance"""
        # Test with mock login data
        login_data = {
            "username": "test_user",
            "password": "test_password"
        }
        
        metrics = await performance_tester.run_concurrent_requests(
            endpoint="/auth/login",
            concurrent_users=100,
            requests_per_user=10,
            method="POST"
        )
        
        logger.info(f"Auth endpoint metrics: {metrics}")
        
        # For auth endpoints, we expect lower throughput due to processing
        # But still should be reasonable
        assert metrics.requests_per_second > 500, \
            f"Auth throughput {metrics.requests_per_second:.2f} req/s below threshold of 500 req/s"
        
        assert metrics.p95_latency < 100, \
            f"Auth p95 latency {metrics.p95_latency:.2f}ms above threshold of 100ms"
    
    async def test_session_endpoint_throughput(self, performance_tester):
        """Test session management endpoint performance"""
        metrics = await performance_tester.run_concurrent_requests(
            endpoint="/sessions",
            concurrent_users=150,
            requests_per_user=8
        )
        
        logger.info(f"Session endpoint metrics: {metrics}")
        
        # Session endpoints should handle good throughput
        assert metrics.requests_per_second > 800, \
            f"Session throughput {metrics.requests_per_second:.2f} req/s below threshold of 800 req/s"
        
        assert metrics.p95_latency < 75, \
            f"Session p95 latency {metrics.p95_latency:.2f}ms above threshold of 75ms"
    
    async def test_high_concurrency_stability(self, performance_tester):
        """Test system stability under high concurrency"""
        metrics = await performance_tester.run_concurrent_requests(
            endpoint="/health",
            concurrent_users=500,
            requests_per_user=5
        )
        
        logger.info(f"High concurrency metrics: {metrics}")
        
        # Under high load, we should still maintain good performance
        assert metrics.requests_per_second > 800, \
            f"High concurrency throughput {metrics.requests_per_second:.2f} req/s below threshold of 800 req/s"
        
        # Error rate should remain low
        error_rate = metrics.failed_requests / metrics.total_requests
        assert error_rate < 0.05, \
            f"Error rate {error_rate:.2%} above threshold of 5%"
    
    async def test_mixed_workload_throughput(self, performance_tester):
        """Test mixed workload performance across different endpoints"""
        endpoints = ["/health", "/sessions", "/users", "/chain/info"]
        
        async def mixed_workload():
            results = []
            for endpoint in endpoints:
                success, latency = await performance_tester.make_request(endpoint)
                results.append((success, latency))
            return results
        
        # Run mixed workload with high concurrency
        concurrent_users = 100
        start_time = time.time()
        tasks = [mixed_workload() for _ in range(concurrent_users)]
        all_results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Calculate overall metrics
        flat_results = []
        for user_results in all_results:
            flat_results.extend(user_results)
        
        successful_requests = sum(1 for success, _ in flat_results if success)
        latencies = [latency for _, latency in flat_results]
        
        requests_per_second = len(flat_results) / total_time
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
        
        logger.info(f"Mixed workload - RPS: {requests_per_second:.2f}, p95: {p95_latency:.2f}ms")
        
        # Mixed workload should maintain good performance
        assert requests_per_second > 600, \
            f"Mixed workload throughput {requests_per_second:.2f} req/s below threshold of 600 req/s"
        
        assert p95_latency < 100, \
            f"Mixed workload p95 latency {p95_latency:.2f}ms above threshold of 100ms"

@pytest.mark.performance
@pytest.mark.slow
class TestAPIGatewayLoadTesting:
    """Extended load testing for API Gateway"""
    
    async def test_sustained_load_performance(self):
        """Test sustained load over extended period"""
        async with APIGatewayPerformanceTester() as tester:
            # Run sustained load test for 5 minutes
            duration_seconds = 300
            concurrent_users = 50
            
            start_time = time.time()
            all_metrics = []
            
            while time.time() - start_time < duration_seconds:
                metrics = await tester.run_concurrent_requests(
                    endpoint="/health",
                    concurrent_users=concurrent_users,
                    requests_per_user=2
                )
                all_metrics.append(metrics)
                
                # Small delay between test cycles
                await asyncio.sleep(10)
            
            # Analyze sustained performance
            avg_rps = statistics.mean([m.requests_per_second for m in all_metrics])
            avg_p95 = statistics.mean([m.p95_latency for m in all_metrics])
            
            logger.info(f"Sustained load - Avg RPS: {avg_rps:.2f}, Avg p95: {avg_p95:.2f}ms")
            
            # Should maintain performance over time
            assert avg_rps > 800, f"Sustained RPS {avg_rps:.2f} below threshold"
            assert avg_p95 < 75, f"Sustained p95 latency {avg_p95:.2f}ms above threshold"

if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "--tb=short"])
