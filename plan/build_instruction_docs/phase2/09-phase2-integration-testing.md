# Phase 2 Integration Testing

## Overview
Run comprehensive integration tests against deployed Phase 2 core services on Raspberry Pi to verify functionality and performance.

## Location
`tests/integration/phase2/`

## Test Categories

### 1. API Gateway Integration Tests
- Authentication flow
- Rate limiting enforcement
- Service routing
- Health monitoring

### 2. Service Mesh Integration Tests
- Service discovery
- mTLS communication
- Load balancing
- Health checks

### 3. Blockchain Integration Tests
- Consensus mechanism
- Block creation
- Transaction processing
- Chain validation

### 4. Cross-Service Integration Tests
- API Gateway → Auth Service
- API Gateway → Blockchain Engine
- Service Mesh → All services
- Blockchain → Database

## Test Implementation

### File: `tests/integration/phase2/test_api_gateway_integration.py`

```python
"""
API Gateway Integration Tests
"""

import pytest
import asyncio
import httpx
from typing import Dict, Any
import json

class TestAPIGatewayIntegration:
    """API Gateway integration tests"""
    
    @pytest.fixture
    async def api_client(self):
        """Create API Gateway client"""
        async with httpx.AsyncClient(base_url="http://192.168.0.75:8080") as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_health_check(self, api_client):
        """Test API Gateway health check"""
        response = await api_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "lucid-api-gateway"
        assert "services" in data
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, api_client):
        """Test API Gateway root endpoint"""
        response = await api_client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Lucid API Gateway"
        assert "services" in data
        assert "/auth" in data["services"]
        assert "/blockchain" in data["services"]
    
    @pytest.mark.asyncio
    async def test_auth_service_routing(self, api_client):
        """Test authentication service routing"""
        # Test auth service health through API Gateway
        response = await api_client.get("/auth/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_blockchain_service_routing(self, api_client):
        """Test blockchain service routing"""
        # Test blockchain service health through API Gateway
        response = await api_client.get("/blockchain/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, api_client):
        """Test rate limiting enforcement"""
        # Make multiple requests to test rate limiting
        responses = []
        for i in range(110):  # Exceed free tier limit
            response = await api_client.get("/health")
            responses.append(response)
        
        # Check if rate limiting is enforced
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        assert len(rate_limited_responses) > 0, "Rate limiting not enforced"
    
    @pytest.mark.asyncio
    async def test_service_health_monitoring(self, api_client):
        """Test service health monitoring"""
        response = await api_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        services = data["services"]
        
        # Check all services are healthy
        for service_name, is_healthy in services.items():
            assert is_healthy, f"Service {service_name} not healthy"
    
    @pytest.mark.asyncio
    async def test_cors_headers(self, api_client):
        """Test CORS headers"""
        response = await api_client.options("/health")
        assert response.status_code == 200
        
        # Check CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers
```

### File: `tests/integration/phase2/test_service_mesh_integration.py`

```python
"""
Service Mesh Integration Tests
"""

import pytest
import asyncio
import httpx
from typing import Dict, Any
import json

class TestServiceMeshIntegration:
    """Service mesh integration tests"""
    
    @pytest.fixture
    async def service_mesh_client(self):
        """Create service mesh client"""
        async with httpx.AsyncClient(base_url="http://192.168.0.75:8081") as client:
            yield client
    
    @pytest.fixture
    async def consul_client(self):
        """Create Consul client"""
        async with httpx.AsyncClient(base_url="http://192.168.0.75:8500") as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_service_mesh_health(self, service_mesh_client):
        """Test service mesh controller health"""
        response = await service_mesh_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "lucid-service-mesh-controller"
        assert "consul" in data
        assert "certificates" in data
        assert "envoy" in data
    
    @pytest.mark.asyncio
    async def test_consul_health(self, consul_client):
        """Test Consul health"""
        response = await consul_client.get("/v1/status/leader")
        assert response.status_code == 200
        
        leader = response.text.strip('"')
        assert leader is not None
    
    @pytest.mark.asyncio
    async def test_service_registration(self, consul_client):
        """Test service registration"""
        response = await consul_client.get("/v1/agent/services")
        assert response.status_code == 200
        
        services = response.json()
        assert len(services) >= 6  # At least 6 services should be registered
        
        # Check specific services are registered
        service_names = [service["Service"] for service in services.values()]
        assert "lucid-api-gateway" in service_names
        assert "lucid-blockchain-engine" in service_names
        assert "lucid-auth-service" in service_names
    
    @pytest.mark.asyncio
    async def test_service_discovery(self, consul_client):
        """Test service discovery"""
        # Test discovering specific service
        response = await consul_client.get("/v1/health/service/lucid-api-gateway")
        assert response.status_code == 200
        
        services = response.json()
        assert len(services) > 0
        
        service = services[0]
        assert service["Service"]["Service"] == "lucid-api-gateway"
        assert service["Service"]["Port"] == 8080
    
    @pytest.mark.asyncio
    async def test_certificate_generation(self, service_mesh_client):
        """Test certificate generation"""
        # Test generating certificate for a service
        response = await service_mesh_client.post("/certificates/test-service")
        assert response.status_code == 200
        
        data = response.json()
        assert "service_name" in data
        assert "cert_path" in data
        assert "key_path" in data
        assert data["service_name"] == "test-service"
    
    @pytest.mark.asyncio
    async def test_envoy_config_generation(self, service_mesh_client):
        """Test Envoy configuration generation"""
        # Test generating Envoy config for a service
        response = await service_mesh_client.post("/envoy/configs/test-service", json={
            "service_address": "192.168.0.75",
            "service_port": 8080
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "config_path" in data
        assert "service_address" in data
        assert "service_port" in data
```

### File: `tests/integration/phase2/test_blockchain_integration.py`

```python
"""
Blockchain Integration Tests
"""

import pytest
import asyncio
import httpx
from typing import Dict, Any
import json
import time

class TestBlockchainIntegration:
    """Blockchain integration tests"""
    
    @pytest.fixture
    async def blockchain_client(self):
        """Create blockchain engine client"""
        async with httpx.AsyncClient(base_url="http://192.168.0.75:8084") as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_blockchain_health(self, blockchain_client):
        """Test blockchain engine health"""
        response = await blockchain_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "lucid-blockchain-engine"
        assert "consensus" in data
        assert "block_creator" in data
        assert "transaction_processor" in data
        assert "network" in data
    
    @pytest.mark.asyncio
    async def test_chain_info(self, blockchain_client):
        """Test blockchain chain info"""
        response = await blockchain_client.get("/api/v1/chain/info")
        assert response.status_code == 200
        
        data = response.json()
        assert "height" in data
        assert "state" in data
        assert "last_updated" in data
    
    @pytest.mark.asyncio
    async def test_block_creation(self, blockchain_client):
        """Test block creation"""
        # Wait for block creation
        await asyncio.sleep(15)  # Wait for block interval
        
        response = await blockchain_client.get("/api/v1/blocks")
        assert response.status_code == 200
        
        blocks = response.json()
        assert len(blocks) > 0
        
        # Check block structure
        block = blocks[0]
        assert "index" in block
        assert "timestamp" in block
        assert "transactions" in block
        assert "previous_hash" in block
        assert "merkle_root" in block
        assert "hash" in block
    
    @pytest.mark.asyncio
    async def test_transaction_submission(self, blockchain_client):
        """Test transaction submission"""
        transaction = {
            "id": "test-tx-1",
            "type": "test_transaction",
            "data": {"test": "data"},
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        response = await blockchain_client.post("/api/v1/transactions", json=transaction)
        assert response.status_code == 200
        
        data = response.json()
        assert "transaction_id" in data
        assert "status" in data
    
    @pytest.mark.asyncio
    async def test_consensus_status(self, blockchain_client):
        """Test consensus status"""
        response = await blockchain_client.get("/api/v1/consensus/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "state" in data
        assert "participants" in data
        assert "current_block" in data
    
    @pytest.mark.asyncio
    async def test_block_validation(self, blockchain_client):
        """Test block validation"""
        # Get a block
        response = await blockchain_client.get("/api/v1/blocks")
        assert response.status_code == 200
        
        blocks = response.json()
        if len(blocks) > 0:
            block = blocks[0]
            
            # Validate block
            response = await blockchain_client.post("/api/v1/blocks/validate", json=block)
            assert response.status_code == 200
            
            data = response.json()
            assert "valid" in data
            assert "results" in data
```

### File: `tests/integration/phase2/test_cross_service_integration.py`

```python
"""
Cross-Service Integration Tests
"""

import pytest
import asyncio
import httpx
from typing import Dict, Any
import json

class TestCrossServiceIntegration:
    """Cross-service integration tests"""
    
    @pytest.fixture
    async def api_gateway_client(self):
        """Create API Gateway client"""
        async with httpx.AsyncClient(base_url="http://192.168.0.75:8080") as client:
            yield client
    
    @pytest.fixture
    async def blockchain_client(self):
        """Create blockchain engine client"""
        async with httpx.AsyncClient(base_url="http://192.168.0.75:8084") as client:
            yield client
    
    @pytest.fixture
    async def session_anchoring_client(self):
        """Create session anchoring client"""
        async with httpx.AsyncClient(base_url="http://192.168.0.75:8086") as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_api_gateway_to_auth_service(self, api_gateway_client):
        """Test API Gateway to Auth Service communication"""
        response = await api_gateway_client.get("/auth/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "lucid-auth-service"
    
    @pytest.mark.asyncio
    async def test_api_gateway_to_blockchain_service(self, api_gateway_client):
        """Test API Gateway to Blockchain Service communication"""
        response = await api_gateway_client.get("/blockchain/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "lucid-blockchain-engine"
    
    @pytest.mark.asyncio
    async def test_session_anchoring_to_blockchain(self, session_anchoring_client):
        """Test Session Anchoring to Blockchain communication"""
        # Test anchoring a session
        session_data = {
            "session_id": "test-session-1",
            "merkle_root": "test-merkle-root",
            "metadata": {"test": "data"}
        }
        
        response = await session_anchoring_client.post("/api/v1/anchoring/anchor", json=session_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "session_id" in data
        assert "merkle_root" in data
        assert "block_hash" in data
        assert "transaction_id" in data
    
    @pytest.mark.asyncio
    async def test_blockchain_to_database(self, blockchain_client):
        """Test Blockchain to Database communication"""
        # Test blockchain can access database
        response = await blockchain_client.get("/api/v1/chain/info")
        assert response.status_code == 200
        
        data = response.json()
        assert "height" in data
        assert "state" in data
    
    @pytest.mark.asyncio
    async def test_service_mesh_discovery(self, api_gateway_client):
        """Test service mesh service discovery"""
        # Test that API Gateway can discover and route to services
        services_to_test = [
            "/auth/health",
            "/blockchain/health"
        ]
        
        for service_path in services_to_test:
            response = await api_gateway_client.get(service_path)
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, api_gateway_client, blockchain_client, session_anchoring_client):
        """Test end-to-end workflow"""
        # 1. Create a transaction through API Gateway
        transaction = {
            "id": "e2e-tx-1",
            "type": "session_anchoring",
            "session_id": "e2e-session-1",
            "data": {"test": "end-to-end"}
        }
        
        response = await api_gateway_client.post("/blockchain/api/v1/transactions", json=transaction)
        assert response.status_code == 200
        
        # 2. Wait for block creation
        await asyncio.sleep(15)
        
        # 3. Verify transaction is in blockchain
        response = await blockchain_client.get("/api/v1/transactions")
        assert response.status_code == 200
        
        transactions = response.json()
        transaction_ids = [tx["id"] for tx in transactions]
        assert "e2e-tx-1" in transaction_ids
        
        # 4. Verify block contains transaction
        response = await blockchain_client.get("/api/v1/blocks")
        assert response.status_code == 200
        
        blocks = response.json()
        assert len(blocks) > 0
        
        # Check if transaction is in any block
        transaction_found = False
        for block in blocks:
            if "e2e-tx-1" in [tx["id"] for tx in block.get("transactions", [])]:
                transaction_found = True
                break
        
        assert transaction_found, "Transaction not found in any block"
```

## Test Execution Script

### File: `scripts/testing/run-phase2-integration-tests.sh`

```bash
#!/bin/bash
# scripts/testing/run-phase2-integration-tests.sh
# Run Phase 2 integration tests

set -e

echo "Running Phase 2 integration tests..."

# Check if Pi is accessible
echo "Checking Pi connectivity..."
if ! curl -s http://192.168.0.75:8080/health > /dev/null; then
    echo "ERROR: Cannot connect to Pi services"
    exit 1
fi

# Install test dependencies
echo "Installing test dependencies..."
pip install pytest pytest-asyncio httpx

# Run API Gateway tests
echo "Running API Gateway integration tests..."
python -m pytest tests/integration/phase2/test_api_gateway_integration.py -v

# Run Service Mesh tests
echo "Running Service Mesh integration tests..."
python -m pytest tests/integration/phase2/test_service_mesh_integration.py -v

# Run Blockchain tests
echo "Running Blockchain integration tests..."
python -m pytest tests/integration/phase2/test_blockchain_integration.py -v

# Run Cross-Service tests
echo "Running Cross-Service integration tests..."
python -m pytest tests/integration/phase2/test_cross_service_integration.py -v

echo "Phase 2 integration tests completed successfully!"
```

## Test Results Validation

### Success Criteria
- All health checks passing
- Service mesh registration complete
- Blockchain creating blocks
- API Gateway routing traffic
- Cross-service communication working
- End-to-end workflow functional

### Performance Criteria
- API Gateway response time < 100ms
- Blockchain block creation every 10 seconds
- Service mesh discovery < 1 second
- Cross-service communication < 50ms

## Troubleshooting

### Test Failures
```bash
# Check service logs
ssh pickme@192.168.0.75 "docker logs lucid-api-gateway"
ssh pickme@192.168.0.75 "docker logs lucid-service-mesh-controller"
ssh pickme@192.168.0.75 "docker logs lucid-blockchain-engine"

# Check service health
curl http://192.168.0.75:8080/health
curl http://192.168.0.75:8081/health
curl http://192.168.0.75:8084/health
```

### Network Issues
```bash
# Check network connectivity
ssh pickme@192.168.0.75 "docker network inspect lucid-pi-network"

# Test service connectivity
ssh pickme@192.168.0.75 "docker exec lucid-api-gateway ping lucid-auth-service"
```

### Service Mesh Issues
```bash
# Check Consul status
curl http://192.168.0.75:8500/v1/status/leader

# Check registered services
curl http://192.168.0.75:8500/v1/agent/services
```

## Next Steps
After successful Phase 2 integration testing, proceed to TRON isolation security scan.
