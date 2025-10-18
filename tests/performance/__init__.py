"""
Performance Testing Package for Lucid API System

This package contains performance tests to validate system benchmarks:
- API Gateway throughput: >1000 req/s
- Blockchain consensus: 1 block per 10 seconds
- Session processing: <100ms per chunk
- Database queries: <10ms p95 query latency

Tests use pytest, locust, and custom benchmarking utilities.
"""

__version__ = "1.0.0"
__author__ = "Lucid Development Team"

# Performance test categories
PERFORMANCE_CATEGORIES = [
    "api_gateway_throughput",
    "blockchain_consensus", 
    "session_processing",
    "database_queries"
]

# Benchmark thresholds
BENCHMARK_THRESHOLDS = {
    "api_gateway_throughput": 1000,  # requests per second
    "blockchain_block_time": 10,     # seconds per block
    "session_chunk_processing": 100, # milliseconds per chunk
    "database_query_p95": 10        # milliseconds p95 latency
}
