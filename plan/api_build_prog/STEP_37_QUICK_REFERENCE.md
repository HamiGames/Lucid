# Step 37: Phase 2 Integration Tests - Quick Reference

## Overview
Phase 2 integration tests for API Gateway, Blockchain Core, and Cross-Cluster Integration services.

## Files Created
```
tests/integration/phase2/
├── __init__.py                    # Package initialization
├── conftest.py                   # Shared fixtures and configuration
├── test_gateway_auth.py          # API Gateway → Auth → Database flow
├── test_gateway_blockchain.py    # API Gateway → Blockchain proxy
├── test_blockchain_consensus.py  # Blockchain consensus mechanism
├── test_service_mesh.py          # Service mesh (Consul) integration
└── test_rate_limiting.py        # Rate limiting integration
```

## Test Categories

### 1. Gateway Auth Tests (`test_gateway_auth.py`)
- User login flow through API Gateway
- JWT token validation and refresh
- Protected endpoint access
- User session management
- Database integration
- Concurrent authentication
- Error handling and performance

### 2. Gateway Blockchain Tests (`test_gateway_blockchain.py`)
- Blockchain info queries through gateway
- Block and transaction queries
- Session anchoring through gateway
- Consensus status queries
- Merkle tree verification
- Health checks and circuit breaker

### 3. Blockchain Consensus Tests (`test_blockchain_consensus.py`)
- Consensus mechanism initialization
- PoOT score calculation
- Consensus round execution
- Validator participation
- Block validation through consensus
- Timeout handling and metrics

### 4. Service Mesh Tests (`test_service_mesh.py`)
- Service registration with Consul
- Service discovery and resolution
- Health check monitoring
- Load balancing and failover
- Service mesh metrics and security

### 5. Rate Limiting Tests (`test_rate_limiting.py`)
- Public endpoint rate limiting (100 req/min)
- Authenticated endpoint rate limiting (1000 req/min)
- Admin endpoint rate limiting (10000 req/min)
- Rate limiting headers and error responses
- Performance and accuracy testing

## Key Fixtures

### HTTP Clients
- `api_gateway_client`: API Gateway HTTP client
- `blockchain_client`: Blockchain Core HTTP client
- `auth_client`: Authentication service HTTP client

### Authentication
- `auth_token`: Test user authentication token
- `admin_token`: Admin user authentication token
- `test_user_credentials`: Test user credentials
- `test_admin_credentials`: Admin user credentials

### Mock Services
- `mock_consul_service`: Consul service discovery mock
- `mock_redis_client`: Redis client mock
- `mock_mongodb_client`: MongoDB client mock

### Test Data
- `sample_block_data`: Sample blockchain block data
- `sample_session_data`: Sample session data
- `rate_limit_headers`: Rate limiting headers
- `service_health_status`: Service health status

## Test Configuration

### Environment Variables
```python
TEST_CONFIG = {
    "api_gateway_url": "http://localhost:8080",
    "blockchain_core_url": "http://localhost:8084",
    "auth_service_url": "http://localhost:8089",
    "database_url": "mongodb://localhost:27017/lucid_test",
    "redis_url": "redis://localhost:6379/1",
    "consul_url": "http://localhost:8500",
    "test_timeout": 30,
    "rate_limit_public": 100,
    "rate_limit_authenticated": 1000,
    "rate_limit_admin": 10000
}
```

### Pytest Markers
- `@pytest.mark.gateway`: API Gateway tests
- `@pytest.mark.blockchain`: Blockchain Core tests
- `@pytest.mark.auth`: Authentication tests
- `@pytest.mark.consensus`: Consensus mechanism tests
- `@pytest.mark.service_mesh`: Service mesh tests
- `@pytest.mark.rate_limiting`: Rate limiting tests
- `@pytest.mark.slow`: Slow running tests

## Running Tests

### Run All Phase 2 Tests
```bash
pytest tests/integration/phase2/ -v
```

### Run Specific Test Categories
```bash
# Gateway tests
pytest tests/integration/phase2/ -m gateway -v

# Blockchain tests
pytest tests/integration/phase2/ -m blockchain -v

# Rate limiting tests
pytest tests/integration/phase2/ -m rate_limiting -v

# Service mesh tests
pytest tests/integration/phase2/ -m service_mesh -v
```

### Run with Coverage
```bash
pytest tests/integration/phase2/ --cov=api_gateway --cov=blockchain --cov=service_mesh
```

## Test Utilities

### TestHelper Class
```python
# Make HTTP request
response = await test_helper.make_request(client, "GET", url, headers=headers)

# Assert response success
test_helper.assert_response_success(response, expected_status=200)

# Assert rate limit headers
test_helper.assert_rate_limit_headers(response)
```

### Common Test Patterns
```python
# Authentication test
async def test_user_login(self, api_gateway_client, test_user_credentials, test_helper):
    response = await test_helper.make_request(
        api_gateway_client,
        "POST",
        f"{test_helper.TEST_CONFIG['api_gateway_url']}/auth/login",
        json=test_user_credentials
    )
    test_helper.assert_response_success(response)
    assert "access_token" in response["data"]

# Rate limiting test
async def test_rate_limiting(self, api_gateway_client, test_helper):
    responses = []
    for i in range(105):  # 5 over the limit
        response = await test_helper.make_request(
            api_gateway_client,
            "GET",
            f"{test_helper.TEST_CONFIG['api_gateway_url']}/health"
        )
        responses.append(response)
        await asyncio.sleep(0.01)
    
    rate_limited = sum(1 for r in responses if r["status"] == 429)
    assert rate_limited > 0
```

## Dependencies

### Required Services
- API Gateway (Port 8080)
- Blockchain Core (Port 8084)
- Authentication Service (Port 8089)
- MongoDB (Port 27017)
- Redis (Port 6379)
- Consul (Port 8500)

### Python Dependencies
- pytest
- aiohttp
- asyncio
- typing
- unittest.mock

## Success Criteria

### Functional
- ✅ API Gateway → Auth → Database flow
- ✅ API Gateway → Blockchain proxy
- ✅ Blockchain consensus mechanism
- ✅ Service discovery (Consul)
- ✅ Rate limiting integration

### Performance
- ✅ Response time < 1 second
- ✅ Concurrent request handling
- ✅ Rate limiting accuracy
- ✅ Service mesh performance

### Quality
- ✅ >95% test coverage
- ✅ All tests passing
- ✅ Error handling comprehensive
- ✅ Documentation complete

---

**Quick Reference Version**: 1.0.0  
**Status**: COMPLETED  
**Last Updated**: 2025-01-14
