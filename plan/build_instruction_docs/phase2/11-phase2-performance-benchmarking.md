# Phase 2 Performance Benchmarking

## Overview
Benchmark Phase 2 core services on Raspberry Pi hardware to verify performance meets requirements.

## Location
`tests/performance/phase2/`

## Performance Targets

### API Gateway Performance
- **Sustained throughput**: >500 req/s
- **Response time**: <100ms p95
- **Rate limiting**: 100 req/min (free tier)
- **Concurrent connections**: >1000

### Blockchain Performance
- **Block creation**: 1 block per 10 seconds
- **Transaction throughput**: >100 tx/s
- **Consensus latency**: <5 seconds
- **Block validation**: <1 second

### Service Mesh Performance
- **Service discovery**: <1 second
- **mTLS handshake**: <500ms
- **Load balancing**: <10ms overhead
- **Health check**: <100ms

### Database Performance
- **Query latency**: <10ms p95
- **Write throughput**: >1000 ops/s
- **Index performance**: <5ms
- **Connection pool**: >100 connections

## Benchmark Implementation

### File: `tests/performance/phase2/benchmark_api_gateway.py`

```python
"""
API Gateway Performance Benchmarks
"""

import asyncio
import time
import statistics
import httpx
from typing import List, Dict, Any
import json

class APIGatewayBenchmark:
    """API Gateway performance benchmarks"""
    
    def __init__(self, base_url: str = "http://192.168.0.75:8080"):
        self.base_url = base_url
        self.results = {}
    
    async def benchmark_health_endpoint(self, num_requests: int = 1000) -> Dict[str, Any]:
        """Benchmark health endpoint performance"""
        print(f"Benchmarking health endpoint with {num_requests} requests...")
        
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            response_times = []
            errors = 0
            
            for i in range(num_requests):
                try:
                    request_start = time.time()
                    response = await client.get(f"{self.base_url}/health")
                    request_end = time.time()
                    
                    if response.status_code == 200:
                        response_times.append(request_end - request_start)
                    else:
                        errors += 1
                        
                except Exception as e:
                    errors += 1
                    print(f"Request {i} failed: {e}")
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Calculate metrics
            if response_times:
                avg_response_time = statistics.mean(response_times)
                p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
                p99_response_time = statistics.quantiles(response_times, n=100)[98]  # 99th percentile
                min_response_time = min(response_times)
                max_response_time = max(response_times)
            else:
                avg_response_time = p95_response_time = p99_response_time = 0
                min_response_time = max_response_time = 0
            
            throughput = len(response_times) / total_time
            error_rate = errors / num_requests * 100
            
            results = {
                "endpoint": "health",
                "total_requests": num_requests,
                "successful_requests": len(response_times),
                "errors": errors,
                "error_rate": error_rate,
                "total_time": total_time,
                "throughput": throughput,
                "avg_response_time": avg_response_time,
                "p95_response_time": p95_response_time,
                "p99_response_time": p99_response_time,
                "min_response_time": min_response_time,
                "max_response_time": max_response_time
            }
            
            self.results["health_endpoint"] = results
            return results
    
    async def benchmark_rate_limiting(self, num_requests: int = 150) -> Dict[str, Any]:
        """Benchmark rate limiting performance"""
        print(f"Benchmarking rate limiting with {num_requests} requests...")
        
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            response_times = []
            rate_limited_requests = 0
            successful_requests = 0
            
            for i in range(num_requests):
                try:
                    request_start = time.time()
                    response = await client.get(f"{self.base_url}/health")
                    request_end = time.time()
                    
                    if response.status_code == 200:
                        successful_requests += 1
                        response_times.append(request_end - request_start)
                    elif response.status_code == 429:
                        rate_limited_requests += 1
                    else:
                        print(f"Unexpected status code: {response.status_code}")
                        
                except Exception as e:
                    print(f"Request {i} failed: {e}")
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Calculate metrics
            if response_times:
                avg_response_time = statistics.mean(response_times)
                p95_response_time = statistics.quantiles(response_times, n=20)[18]
            else:
                avg_response_time = p95_response_time = 0
            
            throughput = successful_requests / total_time
            rate_limit_effectiveness = rate_limited_requests / num_requests * 100
            
            results = {
                "endpoint": "rate_limiting",
                "total_requests": num_requests,
                "successful_requests": successful_requests,
                "rate_limited_requests": rate_limited_requests,
                "rate_limit_effectiveness": rate_limit_effectiveness,
                "total_time": total_time,
                "throughput": throughput,
                "avg_response_time": avg_response_time,
                "p95_response_time": p95_response_time
            }
            
            self.results["rate_limiting"] = results
            return results
    
    async def benchmark_concurrent_connections(self, num_connections: int = 100) -> Dict[str, Any]:
        """Benchmark concurrent connections"""
        print(f"Benchmarking {num_connections} concurrent connections...")
        
        async def make_request(client, request_id):
            try:
                start_time = time.time()
                response = await client.get(f"{self.base_url}/health")
                end_time = time.time()
                
                return {
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "success": response.status_code == 200
                }
            except Exception as e:
                return {
                    "request_id": request_id,
                    "status_code": 0,
                    "response_time": 0,
                    "success": False,
                    "error": str(e)
                }
        
        async with httpx.AsyncClient(limits=httpx.Limits(max_connections=num_connections)) as client:
            start_time = time.time()
            
            # Create concurrent requests
            tasks = [make_request(client, i) for i in range(num_connections)]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Calculate metrics
            successful_requests = sum(1 for r in results if r["success"])
            response_times = [r["response_time"] for r in results if r["success"]]
            
            if response_times:
                avg_response_time = statistics.mean(response_times)
                p95_response_time = statistics.quantiles(response_times, n=20)[18]
            else:
                avg_response_time = p95_response_time = 0
            
            throughput = successful_requests / total_time
            success_rate = successful_requests / num_connections * 100
            
            results_dict = {
                "endpoint": "concurrent_connections",
                "total_connections": num_connections,
                "successful_connections": successful_requests,
                "success_rate": success_rate,
                "total_time": total_time,
                "throughput": throughput,
                "avg_response_time": avg_response_time,
                "p95_response_time": p95_response_time
            }
            
            self.results["concurrent_connections"] = results_dict
            return results_dict
    
    def generate_report(self) -> str:
        """Generate performance report"""
        report = []
        report.append("API Gateway Performance Benchmark Report")
        report.append("=" * 50)
        report.append("")
        
        for test_name, results in self.results.items():
            report.append(f"Test: {test_name}")
            report.append("-" * 30)
            for key, value in results.items():
                report.append(f"{key}: {value}")
            report.append("")
        
        return "\n".join(report)

# Example usage
async def main():
    benchmark = APIGatewayBenchmark()
    
    # Run benchmarks
    await benchmark.benchmark_health_endpoint(1000)
    await benchmark.benchmark_rate_limiting(150)
    await benchmark.benchmark_concurrent_connections(100)
    
    # Generate report
    report = benchmark.generate_report()
    print(report)

if __name__ == "__main__":
    asyncio.run(main())
```

### File: `tests/performance/phase2/benchmark_blockchain.py`

```python
"""
Blockchain Performance Benchmarks
"""

import asyncio
import time
import statistics
import httpx
from typing import List, Dict, Any
import json

class BlockchainBenchmark:
    """Blockchain performance benchmarks"""
    
    def __init__(self, base_url: str = "http://192.168.0.75:8084"):
        self.base_url = base_url
        self.results = {}
    
    async def benchmark_block_creation(self, duration: int = 60) -> Dict[str, Any]:
        """Benchmark block creation performance"""
        print(f"Benchmarking block creation for {duration} seconds...")
        
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            blocks_created = 0
            block_times = []
            
            # Get initial block count
            response = await client.get(f"{self.base_url}/api/v1/blocks")
            initial_blocks = len(response.json()) if response.status_code == 200 else 0
            
            # Monitor block creation
            while time.time() - start_time < duration:
                await asyncio.sleep(1)
                
                response = await client.get(f"{self.base_url}/api/v1/blocks")
                if response.status_code == 200:
                    current_blocks = len(response.json())
                    if current_blocks > initial_blocks + blocks_created:
                        blocks_created += 1
                        block_times.append(time.time())
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Calculate metrics
            if block_times:
                avg_block_interval = statistics.mean([block_times[i] - block_times[i-1] for i in range(1, len(block_times))])
                min_block_interval = min([block_times[i] - block_times[i-1] for i in range(1, len(block_times))])
                max_block_interval = max([block_times[i] - block_times[i-1] for i in range(1, len(block_times))])
            else:
                avg_block_interval = min_block_interval = max_block_interval = 0
            
            blocks_per_second = blocks_created / total_time
            blocks_per_minute = blocks_per_second * 60
            
            results = {
                "test": "block_creation",
                "duration": duration,
                "blocks_created": blocks_created,
                "total_time": total_time,
                "blocks_per_second": blocks_per_second,
                "blocks_per_minute": blocks_per_minute,
                "avg_block_interval": avg_block_interval,
                "min_block_interval": min_block_interval,
                "max_block_interval": max_block_interval
            }
            
            self.results["block_creation"] = results
            return results
    
    async def benchmark_transaction_throughput(self, num_transactions: int = 100) -> Dict[str, Any]:
        """Benchmark transaction throughput"""
        print(f"Benchmarking transaction throughput with {num_transactions} transactions...")
        
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            successful_transactions = 0
            transaction_times = []
            
            for i in range(num_transactions):
                transaction = {
                    "id": f"benchmark-tx-{i}",
                    "type": "benchmark_transaction",
                    "data": {"test": f"data-{i}"},
                    "timestamp": time.time()
                }
                
                try:
                    tx_start = time.time()
                    response = await client.post(f"{self.base_url}/api/v1/transactions", json=transaction)
                    tx_end = time.time()
                    
                    if response.status_code == 200:
                        successful_transactions += 1
                        transaction_times.append(tx_end - tx_start)
                    
                except Exception as e:
                    print(f"Transaction {i} failed: {e}")
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Calculate metrics
            if transaction_times:
                avg_transaction_time = statistics.mean(transaction_times)
                p95_transaction_time = statistics.quantiles(transaction_times, n=20)[18]
            else:
                avg_transaction_time = p95_transaction_time = 0
            
            throughput = successful_transactions / total_time
            success_rate = successful_transactions / num_transactions * 100
            
            results = {
                "test": "transaction_throughput",
                "total_transactions": num_transactions,
                "successful_transactions": successful_transactions,
                "success_rate": success_rate,
                "total_time": total_time,
                "throughput": throughput,
                "avg_transaction_time": avg_transaction_time,
                "p95_transaction_time": p95_transaction_time
            }
            
            self.results["transaction_throughput"] = results
            return results
    
    async def benchmark_consensus_latency(self, num_rounds: int = 10) -> Dict[str, Any]:
        """Benchmark consensus latency"""
        print(f"Benchmarking consensus latency with {num_rounds} rounds...")
        
        async with httpx.AsyncClient() as client:
            consensus_times = []
            
            for i in range(num_rounds):
                try:
                    start_time = time.time()
                    response = await client.get(f"{self.base_url}/api/v1/consensus/status")
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        consensus_times.append(end_time - start_time)
                    
                    # Wait between rounds
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"Consensus round {i} failed: {e}")
            
            # Calculate metrics
            if consensus_times:
                avg_consensus_time = statistics.mean(consensus_times)
                p95_consensus_time = statistics.quantiles(consensus_times, n=20)[18]
                min_consensus_time = min(consensus_times)
                max_consensus_time = max(consensus_times)
            else:
                avg_consensus_time = p95_consensus_time = 0
                min_consensus_time = max_consensus_time = 0
            
            results = {
                "test": "consensus_latency",
                "rounds": num_rounds,
                "avg_consensus_time": avg_consensus_time,
                "p95_consensus_time": p95_consensus_time,
                "min_consensus_time": min_consensus_time,
                "max_consensus_time": max_consensus_time
            }
            
            self.results["consensus_latency"] = results
            return results
    
    def generate_report(self) -> str:
        """Generate performance report"""
        report = []
        report.append("Blockchain Performance Benchmark Report")
        report.append("=" * 50)
        report.append("")
        
        for test_name, results in self.results.items():
            report.append(f"Test: {test_name}")
            report.append("-" * 30)
            for key, value in results.items():
                report.append(f"{key}: {value}")
            report.append("")
        
        return "\n".join(report)

# Example usage
async def main():
    benchmark = BlockchainBenchmark()
    
    # Run benchmarks
    await benchmark.benchmark_block_creation(60)
    await benchmark.benchmark_transaction_throughput(100)
    await benchmark.benchmark_consensus_latency(10)
    
    # Generate report
    report = benchmark.generate_report()
    print(report)

if __name__ == "__main__":
    asyncio.run(main())
```

## Performance Test Execution

### File: `scripts/performance/run-phase2-benchmarks.sh`

```bash
#!/bin/bash
# scripts/performance/run-phase2-benchmarks.sh
# Run Phase 2 performance benchmarks

set -e

echo "Running Phase 2 performance benchmarks..."

# Check if Pi is accessible
echo "Checking Pi connectivity..."
if ! curl -s http://192.168.0.75:8080/health > /dev/null; then
    echo "ERROR: Cannot connect to Pi services"
    exit 1
fi

# Install benchmark dependencies
echo "Installing benchmark dependencies..."
pip install httpx asyncio statistics

# Create results directory
mkdir -p performance-results

# Run API Gateway benchmarks
echo "Running API Gateway benchmarks..."
python tests/performance/phase2/benchmark_api_gateway.py > performance-results/api-gateway-benchmark.txt

# Run Blockchain benchmarks
echo "Running Blockchain benchmarks..."
python tests/performance/phase2/benchmark_blockchain.py > performance-results/blockchain-benchmark.txt

# Run Service Mesh benchmarks
echo "Running Service Mesh benchmarks..."
python tests/performance/phase2/benchmark_service_mesh.py > performance-results/service-mesh-benchmark.txt

# Run Database benchmarks
echo "Running Database benchmarks..."
python tests/performance/phase2/benchmark_database.py > performance-results/database-benchmark.txt

# Generate combined report
echo "Generating combined performance report..."
cat > performance-results/phase2-performance-report.txt << EOF
Phase 2 Performance Benchmark Report
Generated: $(date)
Target: Raspberry Pi 5

API Gateway Performance:
=======================
$(cat performance-results/api-gateway-benchmark.txt)

Blockchain Performance:
======================
$(cat performance-results/blockchain-benchmark.txt)

Service Mesh Performance:
=========================
$(cat performance-results/service-mesh-benchmark.txt)

Database Performance:
====================
$(cat performance-results/database-benchmark.txt)

Performance Summary:
===================
- API Gateway: $(grep "throughput" performance-results/api-gateway-benchmark.txt | head -1)
- Blockchain: $(grep "blocks_per_second" performance-results/blockchain-benchmark.txt | head -1)
- Service Mesh: $(grep "discovery_time" performance-results/service-mesh-benchmark.txt | head -1)
- Database: $(grep "query_latency" performance-results/database-benchmark.txt | head -1)
EOF

echo "Phase 2 performance benchmarks completed!"
echo "Results saved to: performance-results/"
```

## Performance Validation

### Success Criteria
- **API Gateway**: >500 req/s sustained throughput
- **Blockchain**: 1 block per 10 seconds
- **Service Mesh**: <1 second service discovery
- **Database**: <10ms p95 query latency

### Performance Targets
- **Response Time**: <100ms p95
- **Throughput**: >500 req/s
- **Concurrency**: >1000 connections
- **Availability**: >99.9%

## Troubleshooting

### Performance Issues
```bash
# Check service logs
ssh pickme@192.168.0.75 "docker logs lucid-api-gateway"
ssh pickme@192.168.0.75 "docker logs lucid-blockchain-engine"

# Check resource usage
ssh pickme@192.168.0.75 "docker stats"

# Check network performance
ssh pickme@192.168.0.75 "ping -c 10 192.168.0.75"
```

### Benchmark Failures
```bash
# Check benchmark logs
cat performance-results/api-gateway-benchmark.txt
cat performance-results/blockchain-benchmark.txt

# Re-run specific benchmarks
python tests/performance/phase2/benchmark_api_gateway.py
```

## Next Steps
After successful Phase 2 performance benchmarking, proceed to Phase 3 application services build.
