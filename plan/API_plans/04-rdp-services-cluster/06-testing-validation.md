# RDP Services Cluster - Testing & Validation

## Overview
This document defines testing strategies, test cases, validation procedures, and performance benchmarks for the RDP Services Cluster.

## Testing Strategy

### Test Pyramid

```
           ┌─────────┐
           │   E2E   │  10%
           └─────────┘
         ┌─────────────┐
         │ Integration │  30%
         └─────────────┘
       ┌─────────────────┐
       │  Unit Tests     │  60%
       └─────────────────┘
```

### Testing Scope

| Test Level | Coverage Target | Tools |
|------------|----------------|-------|
| Unit Tests | 80%+ | pytest, pytest-asyncio, pytest-cov |
| Integration Tests | 70%+ | pytest, testcontainers |
| E2E Tests | Critical paths | pytest, playwright |
| Performance Tests | All endpoints | locust, k6 |

## Unit Testing

### RDP Server Manager Tests

**File**: `tests/unit/test_rdp_server_manager.py`

```python
import pytest
from uuid import uuid4
from datetime import datetime

from services.rdp_server_manager.core.rdp_server_manager import RdpServerManager
from services.rdp_server_manager.core.models import (
    RdpServerCreateRequest,
    RdpServerConfiguration,
    RdpServerResources,
)
from shared.utils.exceptions import RdpServerNotFoundError, ResourceLimitExceededError

@pytest.fixture
def server_manager(test_db):
    """Create RDP Server Manager instance"""
    return RdpServerManager(db=test_db)

@pytest.fixture
def sample_server_request():
    """Sample server creation request"""
    return RdpServerCreateRequest(
        name="Test Server",
        description="Test RDP server instance",
        user_id=uuid4(),
        configuration=RdpServerConfiguration(
            desktop_environment="xfce",
            resolution="1920x1080",
            color_depth=24,
        ),
        resources=RdpServerResources(
            cpu_limit=2.0,
            memory_limit=4096,
            disk_limit=20480,
            network_bandwidth=1000,
        ),
    )

@pytest.fixture
def mock_user():
    """Mock user for testing"""
    return {
        "user_id": str(uuid4()),
        "username": "testuser",
        "roles": ["user"],
    }

@pytest.mark.asyncio
async def test_create_rdp_server_success(server_manager, sample_server_request, mock_user):
    """Test successful RDP server creation"""
    server = await server_manager.create_server(sample_server_request, mock_user)
    
    assert server is not None
    assert server.name == "Test Server"
    assert server.status == "stopped"
    assert server.port >= 33890
    assert server.port <= 33999
    assert server.user_id == sample_server_request.user_id

@pytest.mark.asyncio
async def test_create_rdp_server_resource_limit(server_manager, sample_server_request, mock_user):
    """Test RDP server creation with exceeded resource limits"""
    sample_server_request.resources.cpu_limit = 10.0  # Exceeds limit
    
    with pytest.raises(ResourceLimitExceededError):
        await server_manager.create_server(sample_server_request, mock_user)

@pytest.mark.asyncio
async def test_get_rdp_server_not_found(server_manager, mock_user):
    """Test getting non-existent RDP server"""
    server_id = uuid4()
    
    with pytest.raises(RdpServerNotFoundError):
        await server_manager.get_server(server_id, mock_user)

@pytest.mark.asyncio
async def test_update_rdp_server_success(server_manager, sample_server_request, mock_user):
    """Test successful RDP server update"""
    # Create server
    server = await server_manager.create_server(sample_server_request, mock_user)
    
    # Update server
    update_request = RdpServerUpdateRequest(
        name="Updated Server",
        description="Updated description",
    )
    
    updated_server = await server_manager.update_server(
        server.server_id,
        update_request,
        mock_user
    )
    
    assert updated_server.name == "Updated Server"
    assert updated_server.description == "Updated description"

@pytest.mark.asyncio
async def test_delete_rdp_server_success(server_manager, sample_server_request, mock_user):
    """Test successful RDP server deletion"""
    # Create server
    server = await server_manager.create_server(sample_server_request, mock_user)
    
    # Delete server
    result = await server_manager.delete_server(server.server_id, mock_user)
    
    assert result is True
    
    # Verify deletion
    with pytest.raises(RdpServerNotFoundError):
        await server_manager.get_server(server.server_id, mock_user)

@pytest.mark.asyncio
async def test_list_rdp_servers_pagination(server_manager, sample_server_request, mock_user):
    """Test RDP server list pagination"""
    # Create multiple servers
    for i in range(5):
        req = sample_server_request.copy()
        req.name = f"Server {i}"
        await server_manager.create_server(req, mock_user)
    
    # Test pagination
    servers, total = await server_manager.list_servers(
        page=1,
        limit=2,
        requesting_user=mock_user
    )
    
    assert len(servers) == 2
    assert total == 5
```

### Session Controller Tests

**File**: `tests/unit/test_session_controller.py`

```python
import pytest
from uuid import uuid4

from services.rdp_session_controller.core.session_manager import SessionManager
from services.rdp_session_controller.core.models import (
    RdpSessionCreateRequest,
    RdpClientInfo,
)
from shared.utils.exceptions import SessionNotFoundError

@pytest.fixture
def session_manager(test_db):
    """Create Session Manager instance"""
    return SessionManager(db=test_db)

@pytest.fixture
def sample_session_request():
    """Sample session creation request"""
    return RdpSessionCreateRequest(
        server_id=uuid4(),
        user_id=uuid4(),
        client_info=RdpClientInfo(
            client_name="Test Client",
            client_version="1.0.0",
            client_ip="192.168.1.100",
            resolution="1920x1080",
            color_depth=24,
        ),
    )

@pytest.mark.asyncio
async def test_create_session_success(session_manager, sample_session_request, mock_user):
    """Test successful session creation"""
    session = await session_manager.create_session(sample_session_request, mock_user)
    
    assert session is not None
    assert session.status == "active"
    assert session.server_id == sample_session_request.server_id
    assert session.user_id == sample_session_request.user_id

@pytest.mark.asyncio
async def test_connect_session_success(session_manager, sample_session_request, mock_user):
    """Test successful session connection"""
    session = await session_manager.create_session(sample_session_request, mock_user)
    
    connection_info = await session_manager.connect_session(
        session.session_id,
        sample_session_request.client_info,
        mock_user
    )
    
    assert connection_info is not None
    assert connection_info.get("access_token") is not None

@pytest.mark.asyncio
async def test_terminate_session_success(session_manager, sample_session_request, mock_user):
    """Test successful session termination"""
    session = await session_manager.create_session(sample_session_request, mock_user)
    
    result = await session_manager.terminate_session(session.session_id, mock_user)
    
    assert result is True
    
    # Verify session status
    terminated_session = await session_manager.get_session(session.session_id, mock_user)
    assert terminated_session.status == "terminated"

@pytest.mark.asyncio
async def test_session_timeout(session_manager, sample_session_request, mock_user):
    """Test session timeout handling"""
    session = await session_manager.create_session(sample_session_request, mock_user)
    
    # Simulate timeout
    await session_manager.check_session_timeouts()
    
    # Check if session is marked as disconnected
    # (implementation depends on timeout configuration)
```

### Resource Monitor Tests

**File**: `tests/unit/test_resource_monitor.py`

```python
import pytest
from uuid import uuid4

from services.rdp_resource_monitor.core.resource_monitor import ResourceMonitor
from services.rdp_resource_monitor.core.models import ResourceUsage

@pytest.fixture
def resource_monitor(test_db):
    """Create Resource Monitor instance"""
    return ResourceMonitor(db=test_db)

@pytest.mark.asyncio
async def test_collect_server_metrics(resource_monitor):
    """Test server resource metrics collection"""
    server_id = uuid4()
    
    metrics = await resource_monitor.collect_server_metrics(server_id)
    
    assert metrics is not None
    assert "cpu_percent" in metrics
    assert "memory_percent" in metrics
    assert 0 <= metrics["cpu_percent"] <= 100
    assert 0 <= metrics["memory_percent"] <= 100

@pytest.mark.asyncio
async def test_collect_session_metrics(resource_monitor):
    """Test session resource metrics collection"""
    session_id = uuid4()
    
    metrics = await resource_monitor.collect_session_metrics(session_id)
    
    assert metrics is not None
    assert "cpu_percent" in metrics
    assert "memory_percent" in metrics

@pytest.mark.asyncio
async def test_check_resource_limits(resource_monitor):
    """Test resource limit checking"""
    server_id = uuid4()
    
    # Create high resource usage scenario
    usage = ResourceUsage(
        cpu_percent=95.0,
        memory_percent=90.0,
        memory_used=8192,
        memory_total=8192,
        disk_usage_percent=85.0,
        disk_used=20000,
        disk_total=20480,
        network_in=5000,
        network_out=5000,
    )
    
    alerts = await resource_monitor.check_limits(server_id, usage)
    
    assert len(alerts) > 0
    assert any(alert.severity == "high" for alert in alerts)

@pytest.mark.asyncio
async def test_get_resource_usage_history(resource_monitor):
    """Test resource usage history retrieval"""
    server_id = uuid4()
    
    history = await resource_monitor.get_usage_history(
        server_id=server_id,
        time_range="1h"
    )
    
    assert isinstance(history, list)
```

### XRDP Integration Tests

**File**: `tests/unit/test_xrdp_integration.py`

```python
import pytest
from unittest.mock import Mock, patch

from services.xrdp_integration.system.xrdp_controller import XrdpController

@pytest.fixture
def xrdp_controller():
    """Create XRDP Controller instance"""
    return XrdpController()

@pytest.mark.asyncio
@patch('subprocess.run')
async def test_start_xrdp_service_success(mock_run, xrdp_controller):
    """Test successful XRDP service start"""
    mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
    
    result = await xrdp_controller.start_service()
    
    assert result["status"] == "success"
    assert result["action"] == "start"
    mock_run.assert_called_once()

@pytest.mark.asyncio
@patch('subprocess.run')
async def test_stop_xrdp_service_success(mock_run, xrdp_controller):
    """Test successful XRDP service stop"""
    mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
    
    result = await xrdp_controller.stop_service()
    
    assert result["status"] == "success"
    assert result["action"] == "stop"

@pytest.mark.asyncio
@patch('subprocess.run')
async def test_get_xrdp_service_status(mock_run, xrdp_controller):
    """Test XRDP service status retrieval"""
    mock_run.return_value = Mock(
        returncode=0,
        stdout="active (running)",
        stderr=""
    )
    
    status = await xrdp_controller.get_service_status()
    
    assert status["status"] == "running"
```

## Integration Testing

### API Endpoint Tests

**File**: `tests/integration/test_api_endpoints.py`

```python
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from services.rdp_server_manager.app import create_app

@pytest.fixture
def client():
    """Create test client"""
    app = create_app()
    return TestClient(app)

def test_list_rdp_servers(client, test_jwt_token):
    """Test listing RDP servers"""
    response = client.get(
        "/api/v1/rdp/servers",
        headers={"Authorization": test_jwt_token}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "servers" in data
    assert "pagination" in data

def test_create_rdp_server(client, test_jwt_token):
    """Test creating RDP server"""
    payload = {
        "name": "Integration Test Server",
        "description": "Test server for integration testing",
        "user_id": str(uuid4()),
        "configuration": {
            "desktop_environment": "xfce",
            "resolution": "1920x1080",
            "color_depth": 24,
        },
        "resources": {
            "cpu_limit": 2.0,
            "memory_limit": 4096,
            "disk_limit": 20480,
            "network_bandwidth": 1000,
        },
    }
    
    response = client.post(
        "/api/v1/rdp/servers",
        json=payload,
        headers={"Authorization": test_jwt_token}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Integration Test Server"
    assert data["status"] == "stopped"

def test_get_rdp_server(client, test_jwt_token):
    """Test getting RDP server details"""
    # Create server first
    create_response = client.post(
        "/api/v1/rdp/servers",
        json={
            "name": "Test Server",
            "user_id": str(uuid4()),
        },
        headers={"Authorization": test_jwt_token}
    )
    server_id = create_response.json()["server_id"]
    
    # Get server details
    response = client.get(
        f"/api/v1/rdp/servers/{server_id}",
        headers={"Authorization": test_jwt_token}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["server_id"] == server_id

def test_update_rdp_server(client, test_jwt_token):
    """Test updating RDP server"""
    # Create server first
    create_response = client.post(
        "/api/v1/rdp/servers",
        json={
            "name": "Test Server",
            "user_id": str(uuid4()),
        },
        headers={"Authorization": test_jwt_token}
    )
    server_id = create_response.json()["server_id"]
    
    # Update server
    response = client.put(
        f"/api/v1/rdp/servers/{server_id}",
        json={"name": "Updated Server Name"},
        headers={"Authorization": test_jwt_token}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Server Name"

def test_delete_rdp_server(client, test_jwt_token):
    """Test deleting RDP server"""
    # Create server first
    create_response = client.post(
        "/api/v1/rdp/servers",
        json={
            "name": "Test Server",
            "user_id": str(uuid4()),
        },
        headers={"Authorization": test_jwt_token}
    )
    server_id = create_response.json()["server_id"]
    
    # Delete server
    response = client.delete(
        f"/api/v1/rdp/servers/{server_id}",
        headers={"Authorization": test_jwt_token}
    )
    
    assert response.status_code == 204

def test_unauthorized_access(client):
    """Test unauthorized access"""
    response = client.get("/api/v1/rdp/servers")
    
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
```

### Database Integration Tests

**File**: `tests/integration/test_database_integration.py`

```python
import pytest
from uuid import uuid4
from datetime import datetime

@pytest.mark.asyncio
async def test_create_and_retrieve_server(test_db):
    """Test creating and retrieving server from database"""
    collection = test_db["rdp_servers"]
    
    server_data = {
        "server_id": uuid4(),
        "user_id": uuid4(),
        "name": "Test Server",
        "status": "stopped",
        "port": 33890,
        "host": "localhost",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    # Insert
    result = await collection.insert_one(server_data)
    assert result.inserted_id is not None
    
    # Retrieve
    retrieved = await collection.find_one({"server_id": server_data["server_id"]})
    assert retrieved is not None
    assert retrieved["name"] == "Test Server"

@pytest.mark.asyncio
async def test_update_server_in_database(test_db):
    """Test updating server in database"""
    collection = test_db["rdp_servers"]
    
    server_id = uuid4()
    await collection.insert_one({
        "server_id": server_id,
        "name": "Original Name",
        "status": "stopped",
    })
    
    # Update
    result = await collection.update_one(
        {"server_id": server_id},
        {"$set": {"name": "Updated Name", "updated_at": datetime.utcnow()}}
    )
    
    assert result.modified_count == 1
    
    # Verify
    updated = await collection.find_one({"server_id": server_id})
    assert updated["name"] == "Updated Name"

@pytest.mark.asyncio
async def test_delete_server_from_database(test_db):
    """Test deleting server from database"""
    collection = test_db["rdp_servers"]
    
    server_id = uuid4()
    await collection.insert_one({
        "server_id": server_id,
        "name": "Test Server",
    })
    
    # Delete
    result = await collection.delete_one({"server_id": server_id})
    assert result.deleted_count == 1
    
    # Verify
    deleted = await collection.find_one({"server_id": server_id})
    assert deleted is None
```

## End-to-End Testing

### Complete RDP Workflow Test

**File**: `tests/e2e/test_rdp_workflow.py`

```python
import pytest
from uuid import uuid4

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_rdp_server_lifecycle(client, test_jwt_token):
    """Test complete RDP server lifecycle"""
    
    # 1. Create RDP server
    create_response = client.post(
        "/api/v1/rdp/servers",
        json={
            "name": "E2E Test Server",
            "description": "End-to-end test server",
            "user_id": str(uuid4()),
            "configuration": {
                "desktop_environment": "xfce",
                "resolution": "1920x1080",
            },
        },
        headers={"Authorization": test_jwt_token}
    )
    assert create_response.status_code == 201
    server_id = create_response.json()["server_id"]
    
    # 2. Start RDP server
    start_response = client.post(
        f"/api/v1/rdp/servers/{server_id}/start",
        headers={"Authorization": test_jwt_token}
    )
    assert start_response.status_code == 200
    
    # 3. Create session
    session_response = client.post(
        "/api/v1/sessions",
        json={
            "server_id": server_id,
            "user_id": str(uuid4()),
        },
        headers={"Authorization": test_jwt_token}
    )
    assert session_response.status_code == 201
    session_id = session_response.json()["session_id"]
    
    # 4. Check resource usage
    resources_response = client.get(
        f"/api/v1/resources/usage?server_id={server_id}",
        headers={"Authorization": test_jwt_token}
    )
    assert resources_response.status_code == 200
    
    # 5. Terminate session
    terminate_response = client.delete(
        f"/api/v1/sessions/{session_id}",
        headers={"Authorization": test_jwt_token}
    )
    assert terminate_response.status_code == 204
    
    # 6. Stop RDP server
    stop_response = client.post(
        f"/api/v1/rdp/servers/{server_id}/stop",
        headers={"Authorization": test_jwt_token}
    )
    assert stop_response.status_code == 200
    
    # 7. Delete RDP server
    delete_response = client.delete(
        f"/api/v1/rdp/servers/{server_id}",
        headers={"Authorization": test_jwt_token}
    )
    assert delete_response.status_code == 204
```

## Performance Testing

### Load Testing Configuration

**File**: `tests/performance/locustfile.py`

```python
from locust import HttpUser, task, between
from uuid import uuid4
import random

class RdpServicesUser(HttpUser):
    """Load testing user for RDP services"""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Setup before tests"""
        self.token = self.get_jwt_token()
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def get_jwt_token(self):
        """Get JWT token for authentication"""
        # Implementation depends on auth service
        return "test-token-123"
    
    @task(3)
    def list_servers(self):
        """List RDP servers"""
        self.client.get(
            "/api/v1/rdp/servers",
            headers=self.headers
        )
    
    @task(1)
    def create_server(self):
        """Create RDP server"""
        self.client.post(
            "/api/v1/rdp/servers",
            json={
                "name": f"Load Test Server {uuid4()}",
                "user_id": str(uuid4()),
            },
            headers=self.headers
        )
    
    @task(2)
    def get_resource_usage(self):
        """Get resource usage"""
        self.client.get(
            "/api/v1/resources/usage",
            headers=self.headers
        )
    
    @task(1)
    def create_session(self):
        """Create RDP session"""
        server_id = str(uuid4())  # Would be actual server ID
        self.client.post(
            "/api/v1/sessions",
            json={
                "server_id": server_id,
                "user_id": str(uuid4()),
            },
            headers=self.headers
        )
```

### Performance Benchmarks

| Operation | Target Response Time | Target Throughput |
|-----------|---------------------|-------------------|
| List Servers | < 100ms | 500 req/s |
| Create Server | < 500ms | 50 req/s |
| Get Server | < 50ms | 1000 req/s |
| Start Server | < 2000ms | 20 req/s |
| Stop Server | < 2000ms | 20 req/s |
| Create Session | < 300ms | 100 req/s |
| Get Resource Usage | < 100ms | 500 req/s |

### Load Testing Scenarios

**Scenario 1: Normal Load**
- 100 concurrent users
- Duration: 10 minutes
- Expected: All endpoints < 200ms p95

**Scenario 2: Peak Load**
- 500 concurrent users
- Duration: 5 minutes
- Expected: All endpoints < 500ms p95

**Scenario 3: Stress Test**
- 1000 concurrent users
- Duration: 3 minutes
- Expected: System remains stable, graceful degradation

## Test Execution

### Running Unit Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=services --cov-report=html

# Run specific test file
pytest tests/unit/test_rdp_server_manager.py -v
```

### Running Integration Tests

```bash
# Run integration tests
pytest tests/integration/ -v

# Run with testcontainers
pytest tests/integration/ --docker-compose-up
```

### Running E2E Tests

```bash
# Run E2E tests
pytest tests/e2e/ -v --e2e

# Run with specific markers
pytest -m e2e
```

### Running Performance Tests

```bash
# Run locust load tests
locust -f tests/performance/locustfile.py --host=http://localhost:8090

# Run with specific users
locust -f tests/performance/locustfile.py --users 100 --spawn-rate 10
```

## Continuous Integration

### GitHub Actions Workflow

**File**: `.github/workflows/test.yml`

```yaml
name: Test RDP Services Cluster

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run unit tests
        run: pytest tests/unit/ --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    services:
      mongodb:
        image: mongo:7
        ports:
          - 27017:27017
      redis:
        image: redis:7
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run integration tests
        run: pytest tests/integration/ -v
```

## Validation Checklist

### Pre-deployment Validation

- [ ] All unit tests passing (80%+ coverage)
- [ ] All integration tests passing
- [ ] E2E tests passing for critical paths
- [ ] Performance benchmarks met
- [ ] Security scanning passed
- [ ] Container scanning passed
- [ ] API documentation updated
- [ ] Database migrations tested
- [ ] Rollback procedure tested

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10

