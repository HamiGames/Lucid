# Node Management Cluster Testing & Validation

## Testing Strategy Overview

The Node Management Cluster implements comprehensive testing at multiple levels: unit tests, integration tests, performance benchmarks, and security validation. All tests follow the Lucid project standards with consistent naming conventions and distroless compliance.

## Unit Testing Framework

### Test Structure
```
node/tests/
├── __init__.py
├── test_node_service.py          # Node lifecycle tests
├── test_pool_service.py          # Pool management tests
├── test_poot_validator.py        # PoOT validation tests
├── test_payout_processor.py      # Payout processing tests
├── test_resource_monitor.py      # Resource monitoring tests
├── test_node_auth.py             # Authentication tests
├── test_rate_limiter.py          # Rate limiting tests
├── test_validators.py            # Input validation tests
├── fixtures/
│   ├── __init__.py
│   ├── node_fixtures.py          # Test node data
│   ├── pool_fixtures.py          # Test pool data
│   ├── poot_fixtures.py          # Test PoOT data
│   └── payout_fixtures.py        # Test payout data
└── conftest.py                   # Pytest configuration
```

### Node Service Tests

#### NodeServiceTest Class
```python
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from node.worker.node_service import NodeService
from node.models.node_models import Node, NodeCreateRequest, NodeUpdateRequest
from node.utils.exceptions import NodeNotFoundError, InvalidNodeStatusError
from tests.fixtures.node_fixtures import (
    sample_node_create_request,
    sample_node_data,
    sample_hardware_info
)

class TestNodeService:
    @pytest.fixture
    async def node_service(self):
        """Create NodeService instance with mocked dependencies."""
        mock_repository = AsyncMock()
        mock_resource_monitor = AsyncMock()
        mock_validator = AsyncMock()
        
        service = NodeService(
            node_repository=mock_repository,
            resource_monitor=mock_resource_monitor,
            validator=mock_validator
        )
        
        return service, mock_repository, mock_resource_monitor, mock_validator
    
    @pytest.mark.asyncio
    async def test_create_node_success(self, node_service):
        """Test successful node creation."""
        service, mock_repo, mock_monitor, mock_validator = node_service
        
        # Setup mocks
        mock_validator.validate_create_request.return_value = None
        mock_repo.create.return_value = None
        mock_monitor.initialize_node.return_value = None
        
        # Create test request
        request = NodeCreateRequest(
            name="test-node-001",
            node_type="worker",
            hardware_info=sample_hardware_info(),
            location={"country": "US", "region": "CA"},
            initial_pool_id="pool_workers",
            configuration={"max_sessions": 10}
        )
        
        # Execute
        result = await service.create_node(request)
        
        # Verify
        assert result.name == "test-node-001"
        assert result.node_type == "worker"
        assert result.status == "inactive"
        assert result.pool_id == "pool_workers"
        
        # Verify interactions
        mock_validator.validate_create_request.assert_called_once_with(request)
        mock_repo.create.assert_called_once()
        mock_monitor.initialize_node.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_node_validation_failure(self, node_service):
        """Test node creation with validation failure."""
        service, mock_repo, mock_monitor, mock_validator = node_service
        
        # Setup validation failure
        mock_validator.validate_create_request.side_effect = ValidationError("Invalid hardware info")
        
        request = sample_node_create_request()
        
        # Execute and verify
        with pytest.raises(ValidationError):
            await service.create_node(request)
        
        # Verify repository not called
        mock_repo.create.assert_not_called()
        mock_monitor.initialize_node.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_node_success(self, node_service):
        """Test successful node retrieval."""
        service, mock_repo, mock_monitor, mock_validator = node_service
        
        # Setup mocks
        expected_node = Node(**sample_node_data())
        mock_validator.validate_node_id.return_value = None
        mock_repo.get_by_id.return_value = expected_node
        
        # Execute
        result = await service.get_node("node_test_001")
        
        # Verify
        assert result == expected_node
        mock_validator.validate_node_id.assert_called_once_with("node_test_001")
        mock_repo.get_by_id.assert_called_once_with("node_test_001")
    
    @pytest.mark.asyncio
    async def test_get_node_not_found(self, node_service):
        """Test node retrieval when node doesn't exist."""
        service, mock_repo, mock_monitor, mock_validator = node_service
        
        # Setup mocks
        mock_validator.validate_node_id.return_value = None
        mock_repo.get_by_id.return_value = None
        
        # Execute and verify
        with pytest.raises(NodeNotFoundError):
            await service.get_node("node_nonexistent")
    
    @pytest.mark.asyncio
    async def test_start_node_success(self, node_service):
        """Test successful node start."""
        service, mock_repo, mock_monitor, mock_validator = node_service
        
        # Setup existing node
        existing_node = Node(**sample_node_data())
        existing_node.status = "inactive"
        
        # Setup mocks
        mock_repo.get_by_id.return_value = existing_node
        mock_repo.update.return_value = None
        mock_monitor.start_monitoring.return_value = None
        
        # Execute
        result = await service.start_node("node_test_001")
        
        # Verify
        assert result["node_id"] == "node_test_001"
        assert result["status"] == "active"
        assert "started_at" in result
        
        # Verify status changes
        assert existing_node.status == "active"
        assert existing_node.last_heartbeat is not None
        
        # Verify interactions
        mock_monitor.start_monitoring.assert_called_once_with("node_test_001")
        assert mock_repo.update.call_count == 2  # Once for starting, once for active
    
    @pytest.mark.asyncio
    async def test_start_node_already_active(self, node_service):
        """Test starting already active node."""
        service, mock_repo, mock_monitor, mock_validator = node_service
        
        # Setup active node
        existing_node = Node(**sample_node_data())
        existing_node.status = "active"
        mock_repo.get_by_id.return_value = existing_node
        
        # Execute
        result = await service.start_node("node_test_001")
        
        # Verify
        assert result["status"] == "active"
        assert result["message"] == "Node is already active"
        
        # Verify no monitoring start called
        mock_monitor.start_monitoring.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_start_node_invalid_status(self, node_service):
        """Test starting node in invalid status."""
        service, mock_repo, mock_monitor, mock_validator = node_service
        
        # Setup node in error status
        existing_node = Node(**sample_node_data())
        existing_node.status = "error"
        mock_repo.get_by_id.return_value = existing_node
        
        # Execute and verify
        with pytest.raises(InvalidNodeStatusError):
            await service.start_node("node_test_001")
    
    @pytest.mark.asyncio
    async def test_list_nodes_with_pagination(self, node_service):
        """Test node listing with pagination."""
        service, mock_repo, mock_monitor, mock_validator = node_service
        
        # Setup mock data
        mock_nodes = [
            Node(**sample_node_data()),
            Node(**sample_node_data()),
            Node(**sample_node_data())
        ]
        mock_repo.list.return_value = mock_nodes
        mock_repo.count.return_value = 50
        
        # Execute
        result = await service.list_nodes(page=2, limit=10, status="active")
        
        # Verify
        assert len(result["nodes"]) == 3
        assert result["pagination"]["page"] == 2
        assert result["pagination"]["limit"] == 10
        assert result["pagination"]["total"] == 50
        assert result["pagination"]["pages"] == 5
        
        # Verify repository calls
        mock_repo.list.assert_called_once_with(
            offset=10, limit=10, status="active", pool_id=None
        )
        mock_repo.count.assert_called_once_with(status="active", pool_id=None)
```

### PoOT Validator Tests

#### PoOTValidatorTest Class
```python
class TestPoOTValidator:
    @pytest.fixture
    async def poot_validator(self):
        """Create PoOTValidator instance with mocked dependencies."""
        mock_repository = AsyncMock()
        validator = PoOTValidator(mock_repository)
        return validator, mock_repository
    
    @pytest.mark.asyncio
    async def test_validate_poot_success(self, poot_validator):
        """Test successful PoOT validation."""
        validator, mock_repo = poot_validator
        
        # Setup mocks
        mock_repo.get_by_id.return_value = Node(status="active")
        mock_repo.get_by_nonce.return_value = None  # Nonce not used recently
        mock_repo.get_recent_validations.return_value = []
        mock_repo.save_validation.return_value = None
        
        # Test data
        node_id = "node_test_001"
        output_data = "base64_encoded_output_data"
        timestamp = datetime.utcnow()
        nonce = "unique_nonce_12345"
        
        # Execute
        result = await validator.validate_poot(node_id, output_data, timestamp, nonce)
        
        # Verify
        assert result.node_id == node_id
        assert result.output_data == output_data
        assert result.is_valid is True
        assert result.score > 0
        assert result.confidence > 0
        assert result.validation_time_ms > 0
        
        # Verify repository interactions
        mock_repo.save_validation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_poot_timestamp_out_of_range(self, poot_validator):
        """Test PoOT validation with timestamp out of range."""
        validator, mock_repo = poot_validator
        
        # Test data with old timestamp
        node_id = "node_test_001"
        output_data = "base64_encoded_output_data"
        timestamp = datetime.utcnow() - timedelta(hours=25)  # Too old
        nonce = "unique_nonce_12345"
        
        # Execute and verify
        with pytest.raises(InvalidPoOTError, match="Timestamp out of valid range"):
            await validator.validate_poot(node_id, output_data, timestamp, nonce)
    
    @pytest.mark.asyncio
    async def test_validate_poot_large_output_data(self, poot_validator):
        """Test PoOT validation with oversized output data."""
        validator, mock_repo = poot_validator
        
        # Test data with large output
        node_id = "node_test_001"
        output_data = "A" * (1024 * 1024 + 1)  # Exceeds 1MB limit
        timestamp = datetime.utcnow()
        nonce = "unique_nonce_12345"
        
        # Execute and verify
        with pytest.raises(InvalidPoOTError, match="Output data too large"):
            await validator.validate_poot(node_id, output_data, timestamp, nonce)
    
    @pytest.mark.asyncio
    async def test_validate_poot_node_inactive(self, poot_validator):
        """Test PoOT validation for inactive node."""
        validator, mock_repo = poot_validator
        
        # Setup inactive node
        mock_repo.get_by_id.return_value = Node(status="inactive")
        
        # Test data
        node_id = "node_test_001"
        output_data = "base64_encoded_output_data"
        timestamp = datetime.utcnow()
        nonce = "unique_nonce_12345"
        
        # Execute and verify
        with pytest.raises(InvalidPoOTError, match="Node not found or inactive"):
            await validator.validate_poot(node_id, output_data, timestamp, nonce)
    
    @pytest.mark.asyncio
    async def test_batch_validate_poot_success(self, poot_validator):
        """Test successful batch PoOT validation."""
        validator, mock_repo = poot_validator
        
        # Setup mocks
        mock_repo.get_by_id.return_value = Node(status="active")
        mock_repo.get_by_nonce.return_value = None
        mock_repo.get_recent_validations.return_value = []
        mock_repo.save_validation.return_value = None
        
        # Test data
        validations = [
            {
                "node_id": "node_test_001",
                "output_data": "data1",
                "timestamp": datetime.utcnow(),
                "nonce": "nonce1"
            },
            {
                "node_id": "node_test_002",
                "output_data": "data2",
                "timestamp": datetime.utcnow(),
                "nonce": "nonce2"
            }
        ]
        
        # Execute
        result = await validator.batch_validate_poot(validations)
        
        # Verify
        assert "batch_id" in result
        assert len(result["results"]) == 2
        assert result["summary"]["total"] == 2
        assert result["summary"]["valid"] == 2
        assert result["summary"]["invalid"] == 0
        assert result["summary"]["errors"] == 0
    
    @pytest.mark.asyncio
    async def test_batch_validate_poot_mixed_results(self, poot_validator):
        """Test batch PoOT validation with mixed results."""
        validator, mock_repo = poot_validator
        
        # Setup mocks for mixed results
        def mock_get_by_id(node_id):
            if node_id == "node_test_001":
                return Node(status="active")
            else:
                return Node(status="inactive")
        
        mock_repo.get_by_id.side_effect = mock_get_by_id
        mock_repo.get_by_nonce.return_value = None
        mock_repo.get_recent_validations.return_value = []
        mock_repo.save_validation.return_value = None
        
        # Test data
        validations = [
            {
                "node_id": "node_test_001",
                "output_data": "data1",
                "timestamp": datetime.utcnow(),
                "nonce": "nonce1"
            },
            {
                "node_id": "node_test_002",  # Inactive node
                "output_data": "data2",
                "timestamp": datetime.utcnow(),
                "nonce": "nonce2"
            }
        ]
        
        # Execute
        result = await validator.batch_validate_poot(validations)
        
        # Verify
        assert result["summary"]["total"] == 2
        assert result["summary"]["valid"] == 1
        assert result["summary"]["invalid"] == 0
        assert result["summary"]["errors"] == 1
```

### Payout Processor Tests

#### PayoutProcessorTest Class
```python
class TestPayoutProcessor:
    @pytest.fixture
    async def payout_processor(self):
        """Create PayoutProcessor instance with mocked dependencies."""
        mock_repository = AsyncMock()
        mock_tron_client = AsyncMock()
        mock_audit_logger = AsyncMock()
        
        processor = PayoutProcessor(
            repository=mock_repository,
            tron_client=mock_tron_client,
            audit_logger=mock_audit_logger
        )
        
        return processor, mock_repository, mock_tron_client, mock_audit_logger
    
    @pytest.mark.asyncio
    async def test_process_single_payout_success(self, payout_processor):
        """Test successful single payout processing."""
        processor, mock_repo, mock_tron, mock_audit = payout_processor
        
        # Setup mocks
        payout_request = {
            "node_id": "node_test_001",
            "amount": 100.50,
            "currency": "USDT",
            "wallet_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        }
        
        mock_repo.get_node_by_id.return_value = Node(**sample_node_data())
        mock_tron.transfer_usdt.return_value = {
            "transaction_hash": "0x1234567890abcdef",
            "success": True
        }
        mock_repo.save_payout.return_value = None
        mock_audit.log_payout_operation.return_value = None
        
        # Execute
        result = await processor.process_payout(payout_request)
        
        # Verify
        assert result["status"] == "completed"
        assert result["transaction_hash"] == "0x1234567890abcdef"
        assert result["amount"] == 100.50
        
        # Verify interactions
        mock_tron.transfer_usdt.assert_called_once_with(
            to_address="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
            amount=100.50
        )
        mock_audit.log_payout_operation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_batch_payouts_success(self, payout_processor):
        """Test successful batch payout processing."""
        processor, mock_repo, mock_tron, mock_audit = payout_processor
        
        # Setup batch data
        batch_requests = [
            {
                "node_id": "node_test_001",
                "amount": 50.0,
                "currency": "USDT",
                "wallet_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
            },
            {
                "node_id": "node_test_002",
                "amount": 75.0,
                "currency": "USDT",
                "wallet_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
            }
        ]
        
        # Setup mocks
        mock_repo.get_node_by_id.return_value = Node(**sample_node_data())
        mock_tron.transfer_usdt.return_value = {
            "transaction_hash": "0x1234567890abcdef",
            "success": True
        }
        mock_repo.save_payout.return_value = None
        mock_audit.log_payout_operation.return_value = None
        
        # Execute
        result = await processor.process_batch_payouts(batch_requests)
        
        # Verify
        assert result["batch_id"] is not None
        assert result["total_processed"] == 2
        assert result["successful"] == 2
        assert result["failed"] == 0
        assert len(result["results"]) == 2
        
        # Verify all payouts processed
        assert mock_tron.transfer_usdt.call_count == 2
    
    @pytest.mark.asyncio
    async def test_process_payout_insufficient_balance(self, payout_processor):
        """Test payout processing with insufficient balance."""
        processor, mock_repo, mock_tron, mock_audit = payout_processor
        
        # Setup mocks
        payout_request = {
            "node_id": "node_test_001",
            "amount": 1000000.0,  # Very large amount
            "currency": "USDT",
            "wallet_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        }
        
        mock_repo.get_node_by_id.return_value = Node(**sample_node_data())
        mock_tron.transfer_usdt.return_value = {
            "success": False,
            "error": "Insufficient balance"
        }
        
        # Execute
        result = await processor.process_payout(payout_request)
        
        # Verify
        assert result["status"] == "failed"
        assert "Insufficient balance" in result["error_message"]
    
    @pytest.mark.asyncio
    async def test_process_payout_invalid_wallet_address(self, payout_processor):
        """Test payout processing with invalid wallet address."""
        processor, mock_repo, mock_tron, mock_audit = payout_processor
        
        # Setup mocks
        payout_request = {
            "node_id": "node_test_001",
            "amount": 100.0,
            "currency": "USDT",
            "wallet_address": "invalid_address"
        }
        
        mock_repo.get_node_by_id.return_value = Node(**sample_node_data())
        
        # Execute and verify
        with pytest.raises(ValidationError, match="Invalid wallet address"):
            await processor.process_payout(payout_request)
```

## Integration Testing

### API Integration Tests

#### NodeManagementAPITest Class
```python
import httpx
import pytest
from fastapi.testclient import TestClient

from node.main import app

class TestNodeManagementAPI:
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers."""
        return {"Authorization": "Bearer test_jwt_token"}
    
    def test_create_node_endpoint(self, client, auth_headers):
        """Test node creation endpoint."""
        node_data = {
            "name": "test-node-api",
            "node_type": "worker",
            "hardware_info": sample_hardware_info(),
            "location": {"country": "US", "region": "CA"},
            "initial_pool_id": "pool_workers",
            "configuration": {"max_sessions": 10}
        }
        
        response = client.post(
            "/api/v1/nodes",
            json=node_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test-node-api"
        assert data["node_type"] == "worker"
        assert data["status"] == "inactive"
    
    def test_get_node_endpoint(self, client, auth_headers):
        """Test node retrieval endpoint."""
        response = client.get(
            "/api/v1/nodes/node_test_001",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["node_id"] == "node_test_001"
    
    def test_start_node_endpoint(self, client, auth_headers):
        """Test node start endpoint."""
        response = client.post(
            "/api/v1/nodes/node_test_001/start",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["node_id"] == "node_test_001"
        assert data["status"] == "active"
    
    def test_list_nodes_with_pagination(self, client, auth_headers):
        """Test node listing with pagination."""
        response = client.get(
            "/api/v1/nodes?page=1&limit=10&status=active",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "pagination" in data
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 10
    
    def test_poot_validation_endpoint(self, client, auth_headers):
        """Test PoOT validation endpoint."""
        poot_data = {
            "output_data": "base64_encoded_data",
            "timestamp": datetime.utcnow().isoformat(),
            "nonce": "unique_nonce_12345"
        }
        
        response = client.post(
            "/api/v1/nodes/node_test_001/poot/validate",
            json=poot_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "is_valid" in data
        assert "score" in data
        assert "confidence" in data
    
    def test_batch_payout_endpoint(self, client, auth_headers):
        """Test batch payout endpoint."""
        payout_data = {
            "batch_id": "batch_test_001",
            "payout_requests": [
                {
                    "node_id": "node_test_001",
                    "amount": 100.0,
                    "currency": "USDT",
                    "wallet_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
                }
            ]
        }
        
        response = client.post(
            "/api/v1/nodes/payouts/batch",
            json=payout_data,
            headers=auth_headers
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["batch_id"] == "batch_test_001"
        assert data["status"] in ["processing", "queued"]
    
    def test_unauthorized_access(self, client):
        """Test unauthorized access to protected endpoints."""
        response = client.get("/api/v1/nodes")
        assert response.status_code == 401
    
    def test_rate_limiting(self, client, auth_headers):
        """Test rate limiting functionality."""
        # Send multiple requests quickly
        responses = []
        for i in range(150):  # Exceed rate limit
            response = client.get("/api/v1/nodes", headers=auth_headers)
            responses.append(response.status_code)
        
        # Should have some 429 responses
        assert 429 in responses
```

### Database Integration Tests

#### DatabaseIntegrationTest Class
```python
class TestDatabaseIntegration:
    @pytest.fixture
    async def test_db(self):
        """Create test database connection."""
        # Use test database
        test_client = AsyncIOMotorClient("mongodb://localhost:27017/lucid_test")
        yield test_client.lucid_test
        # Cleanup after tests
        await test_client.drop_database("lucid_test")
    
    @pytest.mark.asyncio
    async def test_node_crud_operations(self, test_db):
        """Test complete CRUD operations for nodes."""
        # Create node
        node_data = sample_node_data()
        result = await test_db.nodes.insert_one(node_data)
        assert result.inserted_id is not None
        
        # Read node
        retrieved_node = await test_db.nodes.find_one(
            {"node_id": node_data["node_id"]}
        )
        assert retrieved_node["name"] == node_data["name"]
        
        # Update node
        await test_db.nodes.update_one(
            {"node_id": node_data["node_id"]},
            {"$set": {"status": "active"}}
        )
        
        updated_node = await test_db.nodes.find_one(
            {"node_id": node_data["node_id"]}
        )
        assert updated_node["status"] == "active"
        
        # Delete node
        delete_result = await test_db.nodes.delete_one(
            {"node_id": node_data["node_id"]}
        )
        assert delete_result.deleted_count == 1
    
    @pytest.mark.asyncio
    async def test_pool_node_relationship(self, test_db):
        """Test pool-node relationship integrity."""
        # Create pool
        pool_data = {
            "pool_id": "pool_test_001",
            "name": "Test Pool",
            "node_count": 0,
            "created_at": datetime.utcnow()
        }
        await test_db.node_pools.insert_one(pool_data)
        
        # Create node in pool
        node_data = sample_node_data()
        node_data["pool_id"] = "pool_test_001"
        await test_db.nodes.insert_one(node_data)
        
        # Update pool node count
        await test_db.node_pools.update_one(
            {"pool_id": "pool_test_001"},
            {"$inc": {"node_count": 1}}
        )
        
        # Verify relationship
        pool = await test_db.node_pools.find_one({"pool_id": "pool_test_001"})
        assert pool["node_count"] == 1
        
        nodes_in_pool = await test_db.nodes.count_documents(
            {"pool_id": "pool_test_001"}
        )
        assert nodes_in_pool == 1
    
    @pytest.mark.asyncio
    async def test_poot_validation_storage(self, test_db):
        """Test PoOT validation data storage."""
        validation_data = {
            "validation_id": "poot_val_001",
            "node_id": "node_test_001",
            "output_data": "base64_data",
            "output_hash": "sha256_hash",
            "timestamp": datetime.utcnow(),
            "score": 85.5,
            "confidence": 0.95,
            "is_valid": True,
            "validation_time_ms": 150
        }
        
        # Store validation
        result = await test_db.poot_validations.insert_one(validation_data)
        assert result.inserted_id is not None
        
        # Query by node_id
        validations = await test_db.poot_validations.find(
            {"node_id": "node_test_001"}
        ).to_list(10)
        
        assert len(validations) == 1
        assert validations[0]["score"] == 85.5
        
        # Query by score range
        high_score_validations = await test_db.poot_validations.find(
            {"score": {"$gte": 80}}
        ).to_list(10)
        
        assert len(high_score_validations) == 1
```

## Performance Testing

### Load Testing

#### LoadTestSuite Class
```python
import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor

class LoadTestSuite:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results = []
    
    async def test_concurrent_node_creation(self, concurrent_requests: int = 100):
        """Test concurrent node creation performance."""
        async def create_node(node_id: int):
            start_time = time.time()
            
            node_data = {
                "name": f"load_test_node_{node_id}",
                "node_type": "worker",
                "hardware_info": sample_hardware_info(),
                "location": {"country": "US", "region": "CA"},
                "initial_pool_id": "pool_workers"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/nodes",
                    json=node_data,
                    headers={"Authorization": "Bearer test_token"}
                )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            return {
                "node_id": node_id,
                "status_code": response.status_code,
                "response_time": response_time,
                "success": response.status_code == 201
            }
        
        # Execute concurrent requests
        tasks = [create_node(i) for i in range(concurrent_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_requests = [r for r in results if isinstance(r, dict) and r["success"]]
        response_times = [r["response_time"] for r in successful_requests]
        
        return {
            "total_requests": concurrent_requests,
            "successful_requests": len(successful_requests),
            "failed_requests": concurrent_requests - len(successful_requests),
            "success_rate": len(successful_requests) / concurrent_requests,
            "avg_response_time": statistics.mean(response_times) if response_times else 0,
            "p95_response_time": statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else 0,
            "max_response_time": max(response_times) if response_times else 0
        }
    
    async def test_poot_validation_throughput(self, duration_seconds: int = 60):
        """Test PoOT validation throughput over time."""
        start_time = time.time()
        validation_count = 0
        response_times = []
        
        async def validate_poot():
            nonlocal validation_count
            request_start = time.time()
            
            poot_data = {
                "output_data": "base64_encoded_data",
                "timestamp": datetime.utcnow().isoformat(),
                "nonce": f"nonce_{validation_count}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/nodes/node_test_001/poot/validate",
                    json=poot_data,
                    headers={"Authorization": "Bearer test_token"}
                )
            
            request_end = time.time()
            response_times.append(request_end - request_start)
            validation_count += 1
            
            return response.status_code == 200
        
        # Run validation requests for specified duration
        while time.time() - start_time < duration_seconds:
            await validate_poot()
            await asyncio.sleep(0.1)  # Small delay between requests
        
        total_duration = time.time() - start_time
        throughput = validation_count / total_duration
        
        return {
            "duration_seconds": total_duration,
            "total_validations": validation_count,
            "throughput_per_second": throughput,
            "avg_response_time": statistics.mean(response_times) if response_times else 0,
            "p95_response_time": statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else 0
        }
    
    async def test_batch_payout_performance(self, batch_sizes: list = [10, 50, 100, 500]):
        """Test batch payout performance with different batch sizes."""
        results = {}
        
        for batch_size in batch_sizes:
            start_time = time.time()
            
            # Prepare batch data
            payout_requests = []
            for i in range(batch_size):
                payout_requests.append({
                    "node_id": f"node_test_{i:03d}",
                    "amount": 100.0,
                    "currency": "USDT",
                    "wallet_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
                })
            
            batch_data = {
                "batch_id": f"batch_load_test_{batch_size}",
                "payout_requests": payout_requests
            }
            
            # Execute batch request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/nodes/payouts/batch",
                    json=batch_data,
                    headers={"Authorization": "Bearer test_token"}
                )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            results[batch_size] = {
                "batch_size": batch_size,
                "response_time": response_time,
                "throughput": batch_size / response_time,
                "status_code": response.status_code,
                "success": response.status_code == 202
            }
        
        return results

# Performance Test Execution
async def run_performance_tests():
    """Run comprehensive performance tests."""
    load_tester = LoadTestSuite("http://localhost:8083")
    
    print("Running concurrent node creation test...")
    node_creation_results = await load_tester.test_concurrent_node_creation(100)
    print(f"Node Creation Results: {node_creation_results}")
    
    print("Running PoOT validation throughput test...")
    poot_throughput_results = await load_tester.test_poot_validation_throughput(60)
    print(f"PoOT Throughput Results: {poot_throughput_results}")
    
    print("Running batch payout performance test...")
    payout_performance_results = await load_tester.test_batch_payout_performance()
    print(f"Payout Performance Results: {payout_performance_results}")
```

### Memory and Resource Testing

#### ResourceMonitoringTest Class
```python
import psutil
import asyncio
from memory_profiler import profile

class ResourceMonitoringTest:
    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss
    
    def test_memory_usage_during_operations(self):
        """Test memory usage during various operations."""
        memory_samples = []
        
        # Sample memory at different operation stages
        memory_samples.append(("initial", self.process.memory_info().rss))
        
        # Create nodes
        for i in range(1000):
            # Simulate node creation
            pass
        memory_samples.append(("after_1000_nodes", self.process.memory_info().rss))
        
        # Process PoOT validations
        for i in range(10000):
            # Simulate PoOT validation
            pass
        memory_samples.append(("after_10000_poot", self.process.memory_info().rss))
        
        # Process payouts
        for i in range(100):
            # Simulate payout processing
            pass
        memory_samples.append(("after_100_payouts", self.process.memory_info().rss))
        
        return memory_samples
    
    def test_memory_leak_detection(self, iterations: int = 1000):
        """Test for memory leaks during repeated operations."""
        memory_values = []
        
        for i in range(iterations):
            # Perform operation that might leak memory
            self._simulate_node_operation()
            
            if i % 100 == 0:
                memory_values.append(self.process.memory_info().rss)
        
        # Check for consistent memory growth
        if len(memory_values) >= 3:
            growth_rate = (memory_values[-1] - memory_values[0]) / len(memory_values)
            return {
                "initial_memory": memory_values[0],
                "final_memory": memory_values[-1],
                "growth_rate": growth_rate,
                "potential_leak": growth_rate > 1024 * 1024  # 1MB growth per 100 iterations
            }
        
        return {"error": "Insufficient data for leak detection"}
    
    def _simulate_node_operation(self):
        """Simulate a node operation that might cause memory issues."""
        # Create and destroy objects to test garbage collection
        data = [{"node_id": f"node_{i}", "data": "x" * 1000} for i in range(100)]
        # Process data
        processed = [d for d in data if d["node_id"].startswith("node_")]
        # Data should be garbage collected here
        del data, processed
```

## Security Testing

### SecurityTestSuite Class
```python
class SecurityTestSuite:
    def __init__(self, test_client):
        self.client = test_client
    
    async def test_authentication_bypass(self):
        """Test for authentication bypass vulnerabilities."""
        endpoints = [
            "/api/v1/nodes",
            "/api/v1/nodes/payouts",
            "/api/v1/nodes/poot/validate",
            "/api/v1/nodes/pools"
        ]
        
        results = []
        for endpoint in endpoints:
            response = await self.client.get(endpoint)
            results.append({
                "endpoint": endpoint,
                "status_code": response.status_code,
                "protected": response.status_code == 401
            })
        
        return results
    
    async def test_sql_injection_attempts(self):
        """Test for SQL injection vulnerabilities."""
        malicious_inputs = [
            "'; DROP TABLE nodes; --",
            "1' OR '1'='1",
            "'; INSERT INTO nodes VALUES ('hacked', 'admin'); --",
            "admin'/**/OR/**/1=1#",
            "1' UNION SELECT * FROM users --"
        ]
        
        results = []
        for payload in malicious_inputs:
            response = await self.client.get(f"/api/v1/nodes?name={payload}")
            results.append({
                "payload": payload,
                "status_code": response.status_code,
                "safe": response.status_code != 500 and "error" not in response.text.lower()
            })
        
        return results
    
    async def test_xss_prevention(self):
        """Test for XSS prevention."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<svg onload=alert('xss')>",
            "';alert('xss');//"
        ]
        
        results = []
        for payload in xss_payloads:
            response = await self.client.post(
                "/api/v1/nodes",
                json={"name": payload, "node_type": "worker"},
                headers={"Authorization": "Bearer test_token"}
            )
            
            # Check if payload is properly escaped in response
            response_text = response.text
            escaped_payload = payload.replace("<", "&lt;").replace(">", "&gt;")
            
            results.append({
                "payload": payload,
                "status_code": response.status_code,
                "properly_escaped": escaped_payload in response_text or payload not in response_text
            })
        
        return results
    
    async def test_rate_limiting_enforcement(self):
        """Test rate limiting enforcement."""
        # Send requests exceeding rate limit
        responses = []
        for i in range(150):  # Exceed 100 req/min limit
            response = await self.client.get("/api/v1/nodes")
            responses.append(response.status_code)
        
        rate_limited_count = responses.count(429)
        return {
            "total_requests": len(responses),
            "rate_limited_requests": rate_limited_count,
            "rate_limiting_working": rate_limited_count > 0
        }
    
    async def test_input_validation(self):
        """Test input validation and sanitization."""
        invalid_inputs = [
            {"node_id": "<script>alert('xss')</script>"},
            {"amount": -1000},
            {"wallet_address": "invalid_address_format"},
            {"output_data": "A" * (1024 * 1024 + 1)},  # Exceed size limit
            {"pool_id": "'; DROP TABLE pools; --"}
        ]
        
        results = []
        for invalid_input in invalid_inputs:
            response = await self.client.post("/api/v1/nodes", json=invalid_input)
            results.append({
                "input": invalid_input,
                "status_code": response.status_code,
                "properly_rejected": response.status_code == 400
            })
        
        return results
```

## Test Configuration

### Pytest Configuration
```python
# conftest.py
import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from node.main import app
from node.config.database import get_database

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_db():
    """Create test database."""
    client = AsyncIOMotorClient("mongodb://localhost:27017/lucid_test")
    db = client.lucid_test
    
    yield db
    
    # Cleanup
    await client.drop_database("lucid_test")
    client.close()

@pytest.fixture
def test_client():
    """Create test client."""
    return TestClient(app)

@pytest.fixture
def auth_headers():
    """Create authentication headers."""
    return {"Authorization": "Bearer test_jwt_token"}

# Test markers
pytest_plugins = ["pytest_asyncio"]

# Test configuration
pytest.mark.asyncio
pytest.mark.unit
pytest.mark.integration
pytest.mark.performance
pytest.mark.security
```

### Test Execution Commands
```bash
# Run all tests
pytest node/tests/ -v

# Run specific test types
pytest node/tests/ -m unit -v
pytest node/tests/ -m integration -v
pytest node/tests/ -m performance -v
pytest node/tests/ -m security -v

# Run with coverage
pytest node/tests/ --cov=node --cov-report=html

# Run performance tests
pytest node/tests/test_performance.py -v --tb=short

# Run security tests
pytest node/tests/test_security.py -v --tb=short

# Run specific test file
pytest node/tests/test_node_service.py -v

# Run with parallel execution
pytest node/tests/ -n 4 -v
```

## Test Data Fixtures

### Node Fixtures
```python
# tests/fixtures/node_fixtures.py
def sample_node_data():
    """Generate sample node data."""
    return {
        "node_id": "node_test_001",
        "name": "test-node-001",
        "status": "active",
        "node_type": "worker",
        "pool_id": "pool_workers",
        "hardware_info": sample_hardware_info(),
        "location": {
            "country": "US",
            "region": "CA",
            "city": "San Francisco",
            "timezone": "America/Los_Angeles"
        },
        "configuration": {
            "max_sessions": 10,
            "resource_limits": {
                "cpu_percent": 80,
                "memory_bytes": 8589934592,  # 8GB
                "disk_bytes": 107374182400   # 100GB
            }
        },
        "poot_score": 85.5,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "last_heartbeat": datetime.utcnow()
    }

def sample_hardware_info():
    """Generate sample hardware info."""
    return {
        "cpu": {
            "cores": 8,
            "frequency_mhz": 3200,
            "architecture": "x86_64"
        },
        "memory": {
            "total_bytes": 17179869184,  # 16GB
            "type": "DDR4"
        },
        "storage": {
            "total_bytes": 1099511627776,  # 1TB
            "type": "SSD",
            "interface": "NVMe"
        },
        "gpu": {
            "model": "NVIDIA RTX 3080",
            "memory_bytes": 10737418240,  # 10GB
            "compute_capability": "8.6"
        },
        "network": [
            {
                "interface": "eth0",
                "speed_mbps": 1000,
                "mac_address": "00:11:22:33:44:55"
            }
        ]
    }

def sample_node_create_request():
    """Generate sample node creation request."""
    return {
        "name": "test-node-create",
        "node_type": "worker",
        "hardware_info": sample_hardware_info(),
        "location": {
            "country": "US",
            "region": "CA",
            "city": "San Francisco",
            "timezone": "America/Los_Angeles"
        },
        "initial_pool_id": "pool_workers",
        "configuration": {
            "max_sessions": 10,
            "resource_limits": {
                "cpu_percent": 80,
                "memory_bytes": 8589934592,
                "disk_bytes": 107374182400
            }
        }
    }
```

This comprehensive testing and validation document ensures the Node Management Cluster meets all quality standards with thorough unit tests, integration tests, performance benchmarks, and security validation following the Lucid project standards.
