"""
Load Testing Module for Lucid API System

This module contains load testing utilities and test cases for validating
system performance under various load conditions.

Test Categories:
- Concurrent Sessions: 100 concurrent session operations
- Concurrent Users: 1000 concurrent user operations  
- Node Scaling: 500 worker node operations
- Database Scaling: Connection pooling and query performance

Dependencies:
- pytest
- asyncio
- aiohttp
- k6 (for performance testing)
- locust (alternative load testing)
"""

__version__ = "1.0.0"
__author__ = "Lucid Development Team"

# Load testing configuration
DEFAULT_CONCURRENT_SESSIONS = 100
DEFAULT_CONCURRENT_USERS = 1000
DEFAULT_WORKER_NODES = 500
DEFAULT_TEST_DURATION = 300  # 5 minutes
DEFAULT_RAMP_UP_TIME = 60    # 1 minute

# Performance thresholds
SESSION_CREATION_THRESHOLD_MS = 1000
USER_AUTHENTICATION_THRESHOLD_MS = 500
NODE_REGISTRATION_THRESHOLD_MS = 2000
DATABASE_QUERY_THRESHOLD_MS = 100

# Test endpoints
API_GATEWAY_BASE_URL = "http://localhost:8080"
BLOCKCHAIN_CORE_URL = "http://localhost:8084"
SESSION_MANAGEMENT_URL = "http://localhost:8087"
NODE_MANAGEMENT_URL = "http://localhost:8095"
AUTH_SERVICE_URL = "http://localhost:8089"
DATABASE_URL = "mongodb://localhost:27017/lucid"

# Load testing utilities
from .test_concurrent_sessions import ConcurrentSessionsTest
from .test_concurrent_users import ConcurrentUsersTest
from .test_node_scaling import NodeScalingTest
from .test_database_scaling import DatabaseScalingTest

__all__ = [
    "ConcurrentSessionsTest",
    "ConcurrentUsersTest", 
    "NodeScalingTest",
    "DatabaseScalingTest",
    "DEFAULT_CONCURRENT_SESSIONS",
    "DEFAULT_CONCURRENT_USERS",
    "DEFAULT_WORKER_NODES",
    "DEFAULT_TEST_DURATION",
    "DEFAULT_RAMP_UP_TIME"
]
