# 05. Testing and Validation

## Overview

This document provides comprehensive testing specifications and validation procedures for the Session Management Cluster. It covers unit testing, integration testing, performance testing, security testing, and continuous integration practices to ensure system reliability, performance, and security compliance.

## Testing Philosophy

### Core Principles

1. **Test-Driven Development (TDD)**: Write tests before implementation where feasible
2. **Comprehensive Coverage**: Minimum 80% code coverage, 100% for critical paths
3. **Automated Testing**: All tests must be automated and run in CI/CD pipelines
4. **Realistic Test Data**: Use production-like data and scenarios
5. **Isolation**: Tests should be independent and not rely on external state
6. **Performance Validation**: All tests must validate performance against SLA benchmarks

### Testing Pyramid

```
         /\
        /  \  E2E Tests (10%)
       /    \
      /------\  Integration Tests (30%)
     /        \
    /----------\  Unit Tests (60%)
   /____________\
```

## Unit Testing

### Test Framework Setup

#### pytest Configuration
```python
# sessions/tests/conftest.py
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
import fakeredis

from app.api.session_api import app
from app.core.config import settings
from app.core.database import Base, get_db
from app.models.session import Session, SessionStatus
from app.models.chunk import Chunk, ChunkStatus

# Test database configuration
TEST_DATABASE_URL = "mongodb://localhost:27017/lucid_session_test"
TEST_REDIS_URL = "redis://localhost:6379/15"

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def test_db():
    """Create test database connection."""
    client = AsyncIOMotorClient(TEST_DATABASE_URL)
    db = client.get_default_database()
    
    yield db
    
    # Cleanup
    await client.drop_database(db.name)
    client.close()

@pytest.fixture(scope="function")
def test_redis():
    """Create test Redis connection."""
    redis_client = fakeredis.FakeRedis()
    yield redis_client
    redis_client.flushall()

@pytest.fixture(scope="function")
def test_client():
    """Create FastAPI test client."""
    client = TestClient(app)
    yield client

@pytest.fixture
def sample_session_data():
    """Sample session data for testing."""
    return {
        "name": "Test Session",
        "description": "Test session description",
        "rdp_config": {
            "host": "192.168.1.100",
            "port": 3389,
            "username": "testuser",
            "domain": "TESTDOMAIN",
            "use_tls": True,
            "ignore_cert": False
        },
        "recording_config": {
            "frame_rate": 30,
            "resolution": "1920x1080",
            "quality": "high",
            "compression": "zstd",
            "audio_enabled": True,
            "cursor_enabled": True
        },
        "storage_config": {
            "retention_days": 30,
            "max_size_gb": 10,
            "encryption_enabled": True,
            "compression_enabled": True,
            "backup_enabled": False,
            "archive_enabled": False
        },
        "metadata": {
            "project": "lucid-rdp",
            "environment": "test",
            "tags": ["test", "automated"],
            "owner": "test-user-123",
            "priority": "normal"
        }
    }

@pytest.fixture
def mock_jwt_token():
    """Generate mock JWT token for testing."""
    from app.core.security import AuthenticationService
    
    auth_service = AuthenticationService()
    token = auth_service.create_access_token({
        "user_id": "test-user-123",
        "roles": ["session_manager"],
        "permissions": ["sessions:create", "sessions:read", "sessions:update"]
    })
    
    return token

@pytest.fixture
def auth_headers(mock_jwt_token):
    """Generate authentication headers."""
    return {
        "Authorization": f"Bearer {mock_jwt_token}"
    }
```

#### pytest.ini Configuration
```ini
# sessions/pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    security: Security tests
    slow: Slow running tests
addopts = 
    -v
    --tb=short
    --strict-markers
    --cov=app
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
```

### Session API Tests

#### Session Creation Tests
```python
# sessions/tests/test_api/test_session_create.py
import pytest
from fastapi import status
from app.models.session import SessionStatus

@pytest.mark.unit
class TestSessionCreate:
    """Test session creation endpoint."""
    
    def test_create_session_success(self, test_client, auth_headers, sample_session_data):
        """Test successful session creation."""
        response = test_client.post(
            "/api/v1/sessions",
            json=sample_session_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "session_id" in data
        assert data["status"] == SessionStatus.CREATED.value
        assert data["name"] == sample_session_data["name"]
        assert data["rdp_config"]["host"] == sample_session_data["rdp_config"]["host"]
    
    def test_create_session_invalid_rdp_config(self, test_client, auth_headers, sample_session_data):
        """Test session creation with invalid RDP configuration."""
        sample_session_data["rdp_config"]["port"] = 99999  # Invalid port
        
        response = test_client.post(
            "/api/v1/sessions",
            json=sample_session_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "LUCID_ERR_3002"
    
    def test_create_session_unauthorized(self, test_client, sample_session_data):
        """Test session creation without authentication."""
        response = test_client.post(
            "/api/v1/sessions",
            json=sample_session_data
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_create_session_rate_limit(self, test_client, auth_headers, sample_session_data):
        """Test session creation rate limiting."""
        # Create 10 sessions (rate limit)
        for i in range(10):
            sample_session_data["name"] = f"Test Session {i}"
            response = test_client.post(
                "/api/v1/sessions",
                json=sample_session_data,
                headers=auth_headers
            )
            assert response.status_code == status.HTTP_200_OK
        
        # 11th request should be rate limited
        response = test_client.post(
            "/api/v1/sessions",
            json=sample_session_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "X-RateLimit-Limit" in response.headers
        assert "Retry-After" in response.headers
    
    def test_create_session_invalid_resolution(self, test_client, auth_headers, sample_session_data):
        """Test session creation with invalid resolution."""
        sample_session_data["recording_config"]["resolution"] = "invalid"
        
        response = test_client.post(
            "/api/v1/sessions",
            json=sample_session_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_create_session_missing_required_fields(self, test_client, auth_headers):
        """Test session creation with missing required fields."""
        response = test_client.post(
            "/api/v1/sessions",
            json={},
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
```

#### Session Retrieval Tests
```python
# sessions/tests/test_api/test_session_retrieve.py
import pytest
from fastapi import status

@pytest.mark.unit
class TestSessionRetrieve:
    """Test session retrieval endpoints."""
    
    @pytest.fixture
    async def created_session(self, test_client, auth_headers, sample_session_data):
        """Create a test session."""
        response = test_client.post(
            "/api/v1/sessions",
            json=sample_session_data,
            headers=auth_headers
        )
        return response.json()
    
    def test_get_session_success(self, test_client, auth_headers, created_session):
        """Test successful session retrieval."""
        session_id = created_session["session_id"]
        
        response = test_client.get(
            f"/api/v1/sessions/{session_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == session_id
    
    def test_get_session_not_found(self, test_client, auth_headers):
        """Test session retrieval for non-existent session."""
        response = test_client.get(
            "/api/v1/sessions/nonexistent-session",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["error"]["code"] == "LUCID_ERR_3001"
    
    def test_list_sessions_success(self, test_client, auth_headers):
        """Test successful session listing."""
        response = test_client.get(
            "/api/v1/sessions",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "sessions" in data
        assert "pagination" in data
    
    def test_list_sessions_pagination(self, test_client, auth_headers):
        """Test session listing with pagination."""
        response = test_client.get(
            "/api/v1/sessions?limit=10&offset=0",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["pagination"]["limit"] == 10
        assert data["pagination"]["offset"] == 0
    
    def test_list_sessions_filtering(self, test_client, auth_headers):
        """Test session listing with filters."""
        response = test_client.get(
            "/api/v1/sessions?status=recording&project=lucid-rdp",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
```

### Service Layer Tests

#### Session Service Tests
```python
# sessions/tests/test_services/test_session_service.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.services.session_service import SessionService
from app.models.session import Session, SessionStatus

@pytest.mark.unit
class TestSessionService:
    """Test SessionService business logic."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def mock_pipeline_service(self):
        """Mock pipeline service."""
        service = Mock()
        service.create_pipeline = AsyncMock(return_value=None)
        service.start_pipeline = AsyncMock(return_value=None)
        service.stop_pipeline = AsyncMock(return_value=None)
        return service
    
    @pytest.fixture
    def mock_storage_service(self):
        """Mock storage service."""
        service = Mock()
        service.initialize_session_storage = AsyncMock(return_value=None)
        return service
    
    @pytest.fixture
    def session_service(self, mock_db, mock_pipeline_service, mock_storage_service):
        """Create SessionService instance with mocks."""
        return SessionService(
            db=mock_db,
            pipeline_service=mock_pipeline_service,
            storage_service=mock_storage_service
        )
    
    @pytest.mark.asyncio
    async def test_create_session_success(self, session_service, sample_session_data):
        """Test successful session creation."""
        session = await session_service.create_session(
            session_id="test-session-123",
            name=sample_session_data["name"],
            description=sample_session_data.get("description"),
            rdp_config=sample_session_data["rdp_config"],
            recording_config=sample_session_data["recording_config"],
            storage_config=sample_session_data["storage_config"],
            metadata=sample_session_data["metadata"],
            user_id="test-user-123"
        )
        
        assert session is not None
        assert session.session_id == "test-session-123"
        assert session.status == SessionStatus.CREATED
    
    @pytest.mark.asyncio
    async def test_start_recording_success(self, session_service, mock_db):
        """Test successful recording start."""
        mock_session = Mock()
        mock_session.session_id = "test-session-123"
        mock_session.status = SessionStatus.CREATED
        mock_db.query().filter().first.return_value = mock_session
        
        result = await session_service.start_recording("test-session-123")
        
        assert result.status == SessionStatus.RECORDING
        assert result.started_at is not None
    
    @pytest.mark.asyncio
    async def test_start_recording_invalid_state(self, session_service, mock_db):
        """Test recording start from invalid state."""
        mock_session = Mock()
        mock_session.session_id = "test-session-123"
        mock_session.status = SessionStatus.RECORDING  # Already recording
        mock_db.query().filter().first.return_value = mock_session
        
        with pytest.raises(ValueError, match="not in created state"):
            await session_service.start_recording("test-session-123")
    
    @pytest.mark.asyncio
    async def test_stop_recording_success(self, session_service, mock_db):
        """Test successful recording stop."""
        mock_session = Mock()
        mock_session.session_id = "test-session-123"
        mock_session.status = SessionStatus.RECORDING
        mock_db.query().filter().first.return_value = mock_session
        
        result = await session_service.stop_recording("test-session-123")
        
        assert result.status == SessionStatus.STOPPED
        assert result.stopped_at is not None
```

#### Pipeline Service Tests
```python
# sessions/tests/test_services/test_pipeline_service.py
import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.pipeline.pipeline_manager import PipelineManager
from app.models.pipeline import PipelineStatus, StageStatus

@pytest.mark.unit
class TestPipelineManager:
    """Test PipelineManager functionality."""
    
    @pytest.fixture
    def pipeline_manager(self):
        """Create PipelineManager instance."""
        return PipelineManager()
    
    @pytest.mark.asyncio
    async def test_create_pipeline(self, pipeline_manager):
        """Test pipeline creation."""
        pipeline = await pipeline_manager.create_pipeline("test-session-123")
        
        assert pipeline.session_id == "test-session-123"
        assert pipeline.pipeline_status == PipelineStatus.INACTIVE
        assert len(pipeline.stages) == 4
        assert pipeline.stages[0].stage_name == "recording"
    
    @pytest.mark.asyncio
    async def test_start_pipeline(self, pipeline_manager):
        """Test pipeline start."""
        await pipeline_manager.create_pipeline("test-session-123")
        await pipeline_manager.start_pipeline("test-session-123")
        
        pipeline = pipeline_manager.active_pipelines["test-session-123"]
        assert pipeline.pipeline_status == PipelineStatus.ACTIVE
        assert all(stage.status == StageStatus.ACTIVE for stage in pipeline.stages)
    
    @pytest.mark.asyncio
    async def test_process_chunk(self, pipeline_manager):
        """Test chunk processing through pipeline."""
        await pipeline_manager.create_pipeline("test-session-123")
        await pipeline_manager.start_pipeline("test-session-123")
        
        chunk_data = b"test chunk data"
        result = await pipeline_manager.process_chunk("test-session-123", chunk_data)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_stop_pipeline(self, pipeline_manager):
        """Test pipeline stop."""
        await pipeline_manager.create_pipeline("test-session-123")
        await pipeline_manager.start_pipeline("test-session-123")
        await pipeline_manager.stop_pipeline("test-session-123")
        
        pipeline = pipeline_manager.active_pipelines["test-session-123"]
        assert pipeline.pipeline_status == PipelineStatus.STOPPED
```

### Data Model Validation Tests

#### Session Model Tests
```python
# sessions/tests/test_models/test_session.py
import pytest
from pydantic import ValidationError
from app.models.session import (
    Session, RDPConfig, RecordingConfig, 
    StorageConfig, SessionMetadata, SessionStatus
)

@pytest.mark.unit
class TestSessionModels:
    """Test session data models."""
    
    def test_rdp_config_valid(self):
        """Test valid RDP configuration."""
        config = RDPConfig(
            host="192.168.1.100",
            port=3389,
            username="testuser",
            domain="TESTDOMAIN"
        )
        
        assert config.host == "192.168.1.100"
        assert config.port == 3389
        assert config.use_tls is True
    
    def test_rdp_config_invalid_port(self):
        """Test RDP configuration with invalid port."""
        with pytest.raises(ValidationError):
            RDPConfig(
                host="192.168.1.100",
                port=99999,  # Invalid port
                username="testuser"
            )
    
    def test_rdp_config_invalid_host(self):
        """Test RDP configuration with invalid host."""
        with pytest.raises(ValidationError):
            RDPConfig(
                host="invalid@host#name",
                port=3389,
                username="testuser"
            )
    
    def test_recording_config_valid(self):
        """Test valid recording configuration."""
        config = RecordingConfig(
            frame_rate=30,
            resolution="1920x1080",
            quality="high",
            compression="zstd"
        )
        
        assert config.frame_rate == 30
        assert config.resolution == "1920x1080"
    
    def test_recording_config_invalid_resolution(self):
        """Test recording configuration with invalid resolution."""
        with pytest.raises(ValidationError):
            RecordingConfig(
                frame_rate=30,
                resolution="invalid",
                quality="high"
            )
    
    def test_recording_config_invalid_quality(self):
        """Test recording configuration with invalid quality."""
        with pytest.raises(ValidationError):
            RecordingConfig(
                frame_rate=30,
                resolution="1920x1080",
                quality="invalid_quality"
            )
    
    def test_session_metadata_max_tags(self):
        """Test session metadata with too many tags."""
        with pytest.raises(ValidationError, match="Maximum 10 tags allowed"):
            SessionMetadata(
                tags=[f"tag{i}" for i in range(11)]  # 11 tags
            )
    
    def test_session_metadata_tag_length(self):
        """Test session metadata with tag exceeding length."""
        with pytest.raises(ValidationError, match="Tag length cannot exceed 50"):
            SessionMetadata(
                tags=["a" * 51]  # 51 characters
            )
```

## Integration Testing

### End-to-End Pipeline Tests

#### Complete Session Recording Test
```python
# sessions/tests/test_integration/test_session_pipeline.py
import pytest
import asyncio
from datetime import datetime

@pytest.mark.integration
class TestSessionPipeline:
    """Test complete session recording pipeline."""
    
    @pytest.mark.asyncio
    async def test_full_session_lifecycle(
        self, test_client, auth_headers, sample_session_data, test_db
    ):
        """Test complete session lifecycle from creation to completion."""
        
        # Step 1: Create session
        response = test_client.post(
            "/api/v1/sessions",
            json=sample_session_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        session = response.json()
        session_id = session["session_id"]
        
        # Step 2: Start recording
        response = test_client.post(
            f"/api/v1/sessions/{session_id}/start",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "recording"
        
        # Step 3: Verify pipeline is active
        response = test_client.get(
            f"/api/v1/sessions/{session_id}/pipeline",
            headers=auth_headers
        )
        assert response.status_code == 200
        pipeline = response.json()
        assert pipeline["pipeline_status"] == "active"
        
        # Step 4: Simulate recording for a few seconds
        await asyncio.sleep(5)
        
        # Step 5: Verify chunks are being created
        response = test_client.get(
            f"/api/v1/sessions/{session_id}/chunks",
            headers=auth_headers
        )
        assert response.status_code == 200
        chunks = response.json()
        assert len(chunks["chunks"]) > 0
        
        # Step 6: Stop recording
        response = test_client.post(
            f"/api/v1/sessions/{session_id}/stop",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "stopped"
        
        # Step 7: Verify final statistics
        response = test_client.get(
            f"/api/v1/sessions/{session_id}/statistics",
            headers=auth_headers
        )
        assert response.status_code == 200
        stats = response.json()
        assert stats["recording_stats"]["total_duration_seconds"] >= 5
        assert stats["storage_stats"]["chunks_count"] > 0
```

### Database Integration Tests

#### MongoDB Integration Tests
```python
# sessions/tests/test_integration/test_database.py
import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

@pytest.mark.integration
class TestMongoDBIntegration:
    """Test MongoDB integration."""
    
    @pytest.mark.asyncio
    async def test_session_crud_operations(self, test_db):
        """Test session CRUD operations in MongoDB."""
        
        # Create
        session_data = {
            "session_id": "test-session-123",
            "name": "Test Session",
            "status": "created",
            "created_at": datetime.utcnow()
        }
        
        result = await test_db.sessions.insert_one(session_data)
        assert result.inserted_id is not None
        
        # Read
        session = await test_db.sessions.find_one({"session_id": "test-session-123"})
        assert session is not None
        assert session["name"] == "Test Session"
        
        # Update
        await test_db.sessions.update_one(
            {"session_id": "test-session-123"},
            {"$set": {"status": "recording"}}
        )
        
        session = await test_db.sessions.find_one({"session_id": "test-session-123"})
        assert session["status"] == "recording"
        
        # Delete
        result = await test_db.sessions.delete_one({"session_id": "test-session-123"})
        assert result.deleted_count == 1
    
    @pytest.mark.asyncio
    async def test_session_indexes(self, test_db):
        """Test MongoDB indexes for sessions."""
        indexes = await test_db.sessions.index_information()
        
        assert "session_id_1" in indexes
        assert indexes["session_id_1"]["unique"] is True
```

### RDP Connection Tests

#### Mock RDP Server Tests
```python
# sessions/tests/test_integration/test_rdp.py
import pytest
from unittest.mock import Mock, AsyncMock, patch

@pytest.mark.integration
class TestRDPIntegration:
    """Test RDP connection and recording."""
    
    @pytest.fixture
    def mock_rdp_server(self):
        """Mock RDP server for testing."""
        server = Mock()
        server.host = "localhost"
        server.port = 3389
        server.connect = AsyncMock(return_value=True)
        server.disconnect = AsyncMock(return_value=True)
        server.capture_frame = AsyncMock(return_value=b"frame_data")
        return server
    
    @pytest.mark.asyncio
    async def test_rdp_connection(self, mock_rdp_server):
        """Test RDP connection establishment."""
        from app.recorder.rdp_client import RDPClient
        
        with patch('app.recorder.rdp_client.RDPClient.connect', mock_rdp_server.connect):
            client = RDPClient(
                host="localhost",
                port=3389,
                username="test",
                password="test"
            )
            
            result = await client.connect()
            assert result is True
            mock_rdp_server.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_frame_capture(self, mock_rdp_server):
        """Test frame capture from RDP connection."""
        from app.recorder.frame_capture import FrameCapture
        
        with patch('app.recorder.rdp_client.RDPClient.capture_frame', mock_rdp_server.capture_frame):
            capture = FrameCapture(
                rdp_client=mock_rdp_server,
                frame_rate=30,
                resolution="1920x1080",
                quality="high"
            )
            
            frame_data = await capture.capture_frame()
            assert frame_data == b"frame_data"
```

## Performance Testing

### Load Testing Specifications

#### Concurrent Session Load Test
```python
# sessions/tests/test_performance/test_load.py
import pytest
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

@pytest.mark.performance
class TestLoadPerformance:
    """Test system performance under load."""
    
    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, test_client, auth_headers, sample_session_data):
        """Test concurrent session creation and recording."""
        
        async def create_and_record_session(session_num):
            """Create and start recording a session."""
            data = sample_session_data.copy()
            data["name"] = f"Load Test Session {session_num}"
            
            # Create session
            start_time = time.time()
            response = test_client.post(
                "/api/v1/sessions",
                json=data,
                headers=auth_headers
            )
            create_time = time.time() - start_time
            
            assert response.status_code == 200
            assert create_time < 0.1  # Should be < 100ms
            
            session_id = response.json()["session_id"]
            
            # Start recording
            start_time = time.time()
            response = test_client.post(
                f"/api/v1/sessions/{session_id}/start",
                headers=auth_headers
            )
            start_recording_time = time.time() - start_time
            
            assert response.status_code == 200
            assert start_recording_time < 0.2  # Should be < 200ms
            
            return {
                "session_id": session_id,
                "create_time": create_time,
                "start_recording_time": start_recording_time
            }
        
        # Test with 25 concurrent sessions (SLA: up to 100)
        tasks = [create_and_record_session(i) for i in range(25)]
        results = await asyncio.gather(*tasks)
        
        # Verify performance metrics
        avg_create_time = sum(r["create_time"] for r in results) / len(results)
        avg_start_time = sum(r["start_recording_time"] for r in results) / len(results)
        
        assert avg_create_time < 0.1  # Average < 100ms
        assert avg_start_time < 0.2   # Average < 200ms
        assert len(results) == 25
    
    @pytest.mark.asyncio
    async def test_chunk_processing_throughput(self):
        """Test chunk processing throughput."""
        from app.pipeline.pipeline_manager import PipelineManager
        
        pipeline_manager = PipelineManager()
        await pipeline_manager.create_pipeline("perf-test-session")
        await pipeline_manager.start_pipeline("perf-test-session")
        
        # Process 1000 chunks
        chunk_data = b"test chunk data" * 1000  # ~15KB chunk
        start_time = time.time()
        
        for i in range(1000):
            await pipeline_manager.process_chunk("perf-test-session", chunk_data)
        
        elapsed_time = time.time() - start_time
        throughput = 1000 / elapsed_time  # chunks per second
        
        # SLA: 1000+ chunks per minute (16.67 per second)
        assert throughput > 16.67
```

#### Storage I/O Performance Test
```python
# sessions/tests/test_performance/test_storage_io.py
import pytest
import time
import os
from pathlib import Path

@pytest.mark.performance
class TestStoragePerformance:
    """Test storage I/O performance."""
    
    def test_chunk_write_performance(self, tmp_path):
        """Test chunk write performance."""
        from app.storage.chunk_storage import ChunkStorage
        
        storage = ChunkStorage(base_path=str(tmp_path))
        
        # Generate 100MB of test data
        chunk_size = 1024 * 1024  # 1MB chunks
        num_chunks = 100
        
        start_time = time.time()
        
        for i in range(num_chunks):
            chunk_data = os.urandom(chunk_size)
            storage.write_chunk(f"test-session", f"chunk-{i}", chunk_data)
        
        elapsed_time = time.time() - start_time
        throughput_mbps = (chunk_size * num_chunks) / (1024 * 1024 * elapsed_time)
        
        # SLA: 100+ MB/s sustained throughput
        assert throughput_mbps > 100
    
    def test_chunk_read_performance(self, tmp_path):
        """Test chunk read performance."""
        from app.storage.chunk_storage import ChunkStorage
        
        storage = ChunkStorage(base_path=str(tmp_path))
        
        # Write test chunks
        chunk_size = 1024 * 1024  # 1MB chunks
        num_chunks = 100
        
        for i in range(num_chunks):
            chunk_data = os.urandom(chunk_size)
            storage.write_chunk(f"test-session", f"chunk-{i}", chunk_data)
        
        # Read chunks
        start_time = time.time()
        
        for i in range(num_chunks):
            data = storage.read_chunk(f"test-session", f"chunk-{i}")
            assert len(data) == chunk_size
        
        elapsed_time = time.time() - start_time
        throughput_mbps = (chunk_size * num_chunks) / (1024 * 1024 * elapsed_time)
        
        # SLA: 100+ MB/s sustained throughput
        assert throughput_mbps > 100
```

### Stress Testing

#### System Stress Test
```python
# sessions/tests/test_performance/test_stress.py
import pytest
import asyncio
import psutil
import time

@pytest.mark.performance
@pytest.mark.slow
class TestSystemStress:
    """Test system under stress conditions."""
    
    @pytest.mark.asyncio
    async def test_maximum_concurrent_sessions(self, test_client, auth_headers):
        """Test system with maximum concurrent sessions."""
        
        # SLA: Up to 100 simultaneous sessions
        max_sessions = 100
        
        # Monitor system resources
        process = psutil.Process()
        
        sessions = []
        
        for i in range(max_sessions):
            response = test_client.post(
                "/api/v1/sessions",
                json={
                    "name": f"Stress Test Session {i}",
                    "rdp_config": {
                        "host": "localhost",
                        "port": 3389,
                        "username": "test"
                    }
                },
                headers=auth_headers
            )
            
            if response.status_code == 200:
                sessions.append(response.json()["session_id"])
        
        # Check CPU and memory usage
        cpu_percent = process.cpu_percent()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)
        
        print(f"Created {len(sessions)} sessions")
        print(f"CPU Usage: {cpu_percent}%")
        print(f"Memory Usage: {memory_mb:.2f} MB")
        
        # System should remain responsive
        assert len(sessions) >= 100
        assert cpu_percent < 80  # CPU under 80%
        assert memory_mb < 4096  # Memory under 4GB
    
    @pytest.mark.asyncio
    async def test_rapid_session_creation_deletion(self, test_client, auth_headers):
        """Test rapid session creation and deletion."""
        
        for cycle in range(10):
            # Create 10 sessions
            session_ids = []
            for i in range(10):
                response = test_client.post(
                    "/api/v1/sessions",
                    json={
                        "name": f"Rapid Test Session {cycle}-{i}",
                        "rdp_config": {
                            "host": "localhost",
                            "port": 3389,
                            "username": "test"
                        }
                    },
                    headers=auth_headers
                )
                if response.status_code == 200:
                    session_ids.append(response.json()["session_id"])
            
            # Delete all sessions
            for session_id in session_ids:
                response = test_client.delete(
                    f"/api/v1/sessions/{session_id}",
                    headers=auth_headers
                )
                assert response.status_code == 200
        
        # System should remain stable
        response = test_client.get("/health")
        assert response.status_code == 200
```

## Security Testing

### Authentication Tests

#### JWT Token Tests
```python
# sessions/tests/test_security/test_authentication.py
import pytest
from fastapi import status
from datetime import datetime, timedelta
from jose import jwt

@pytest.mark.security
class TestAuthentication:
    """Test authentication mechanisms."""
    
    def test_access_without_token(self, test_client):
        """Test API access without authentication token."""
        response = test_client.get("/api/v1/sessions")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_access_with_invalid_token(self, test_client):
        """Test API access with invalid token."""
        headers = {"Authorization": "Bearer invalid-token"}
        response = test_client.get("/api/v1/sessions", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_access_with_expired_token(self, test_client):
        """Test API access with expired token."""
        from app.core.security import AuthenticationService
        
        auth_service = AuthenticationService()
        
        # Create expired token
        payload = {
            "user_id": "test-user",
            "exp": datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
        }
        
        expired_token = jwt.encode(
            payload,
            auth_service.secret_key,
            algorithm=auth_service.algorithm
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = test_client.get("/api/v1/sessions", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_token_revocation(self, test_client, mock_jwt_token):
        """Test token revocation."""
        from app.core.security import AuthenticationService
        
        auth_service = AuthenticationService()
        
        # Token should work initially
        headers = {"Authorization": f"Bearer {mock_jwt_token}"}
        response = test_client.get("/api/v1/sessions", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        
        # Revoke token
        auth_service.revoke_token(mock_jwt_token)
        
        # Token should no longer work
        response = test_client.get("/api/v1/sessions", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

### Authorization Tests

#### RBAC Tests
```python
# sessions/tests/test_security/test_authorization.py
import pytest
from fastapi import status

@pytest.mark.security
class TestAuthorization:
    """Test role-based access control."""
    
    @pytest.fixture
    def viewer_token(self):
        """Generate token for session viewer role."""
        from app.core.security import AuthenticationService
        
        auth_service = AuthenticationService()
        return auth_service.create_access_token({
            "user_id": "viewer-user",
            "roles": ["session_viewer"],
            "permissions": ["sessions:read"]
        })
    
    @pytest.fixture
    def operator_token(self):
        """Generate token for session operator role."""
        from app.core.security import AuthenticationService
        
        auth_service = AuthenticationService()
        return auth_service.create_access_token({
            "user_id": "operator-user",
            "roles": ["session_operator"],
            "permissions": ["sessions:read", "sessions:start", "sessions:stop"]
        })
    
    def test_viewer_cannot_create_session(self, test_client, viewer_token, sample_session_data):
        """Test that viewer cannot create sessions."""
        headers = {"Authorization": f"Bearer {viewer_token}"}
        response = test_client.post(
            "/api/v1/sessions",
            json=sample_session_data,
            headers=headers
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_viewer_can_read_session(self, test_client, viewer_token):
        """Test that viewer can read sessions."""
        headers = {"Authorization": f"Bearer {viewer_token}"}
        response = test_client.get("/api/v1/sessions", headers=headers)
        assert response.status_code == status.HTTP_200_OK
    
    def test_operator_can_start_session(self, test_client, operator_token, created_session):
        """Test that operator can start sessions."""
        headers = {"Authorization": f"Bearer {operator_token}"}
        session_id = created_session["session_id"]
        
        response = test_client.post(
            f"/api/v1/sessions/{session_id}/start",
            headers=headers
        )
        assert response.status_code == status.HTTP_200_OK
```

### Encryption Tests

#### Data Encryption Tests
```python
# sessions/tests/test_security/test_encryption.py
import pytest
import os

@pytest.mark.security
class TestEncryption:
    """Test data encryption."""
    
    def test_chunk_encryption_decryption(self):
        """Test chunk encryption and decryption."""
        from app.core.encryption import EncryptionService
        
        encryption_service = EncryptionService()
        
        # Original data
        original_data = b"sensitive session data"
        
        # Encrypt
        encrypted_data = encryption_service.encrypt_data(original_data)
        assert encrypted_data != original_data
        assert len(encrypted_data) > len(original_data)
        
        # Decrypt
        decrypted_data = encryption_service.decrypt_data(encrypted_data)
        assert decrypted_data == original_data
    
    def test_file_encryption(self, tmp_path):
        """Test file encryption."""
        from app.core.encryption import EncryptionService
        
        encryption_service = EncryptionService()
        
        # Create test file
        input_file = tmp_path / "test_chunk.dat"
        original_data = os.urandom(1024 * 1024)  # 1MB
        input_file.write_bytes(original_data)
        
        # Encrypt file
        encrypted_file = tmp_path / "test_chunk.encrypted"
        encryption_service.encrypt_file(str(input_file), str(encrypted_file))
        
        # Verify encrypted file is different
        encrypted_data = encrypted_file.read_bytes()
        assert encrypted_data != original_data
        
        # Decrypt file
        decrypted_file = tmp_path / "test_chunk.decrypted"
        encryption_service.decrypt_file(str(encrypted_file), str(decrypted_file))
        
        # Verify decrypted data matches original
        decrypted_data = decrypted_file.read_bytes()
        assert decrypted_data == original_data
```

### Audit Logging Tests

#### Audit Trail Tests
```python
# sessions/tests/test_security/test_audit.py
import pytest
from app.core.audit import AuditLogger, AuditEventType

@pytest.mark.security
class TestAuditLogging:
    """Test audit logging functionality."""
    
    @pytest.mark.asyncio
    async def test_session_creation_logged(self, test_client, auth_headers, sample_session_data, test_db):
        """Test that session creation is logged."""
        # Create session
        response = test_client.post(
            "/api/v1/sessions",
            json=sample_session_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Verify audit log entry
        audit_entry = await test_db.audit_logs.find_one({
            "event_type": AuditEventType.SESSION_CREATED.value,
            "resource_id": response.json()["session_id"]
        })
        
        assert audit_entry is not None
        assert audit_entry["user_id"] == "test-user-123"
        assert audit_entry["success"] is True
    
    @pytest.mark.asyncio
    async def test_permission_denied_logged(self, test_client, viewer_token, sample_session_data, test_db):
        """Test that permission denied events are logged."""
        headers = {"Authorization": f"Bearer {viewer_token}"}
        
        # Attempt unauthorized action
        response = test_client.post(
            "/api/v1/sessions",
            json=sample_session_data,
            headers=headers
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # Verify audit log entry
        audit_entry = await test_db.audit_logs.find_one({
            "event_type": AuditEventType.PERMISSION_DENIED.value,
            "user_id": "viewer-user"
        })
        
        assert audit_entry is not None
        assert audit_entry["success"] is False
```

## Test Infrastructure

### Docker Test Containers

#### Docker Compose for Testing
```yaml
# sessions/tests/docker-compose.test.yml
version: '3.8'

services:
  mongodb-test:
    image: mongo:6.0
    container_name: lucid-test-mongodb
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_DATABASE: lucid_session_test
    tmpfs:
      - /data/db
    networks:
      - test-network

  redis-test:
    image: redis:7-alpine
    container_name: lucid-test-redis
    ports:
      - "6379:6379"
    tmpfs:
      - /data
    networks:
      - test-network

networks:
  test-network:
    driver: bridge
```

### Test Data Management

#### Test Data Factory
```python
# sessions/tests/factories.py
import factory
from faker import Faker
from datetime import datetime
from app.models.session import Session, SessionStatus

fake = Faker()

class RDPConfigFactory(factory.Factory):
    """Factory for RDP configuration."""
    
    class Meta:
        model = dict
    
    host = factory.LazyFunction(lambda: fake.ipv4())
    port = 3389
    username = factory.LazyFunction(lambda: fake.user_name())
    domain = "TESTDOMAIN"
    use_tls = True
    ignore_cert = False

class RecordingConfigFactory(factory.Factory):
    """Factory for recording configuration."""
    
    class Meta:
        model = dict
    
    frame_rate = 30
    resolution = "1920x1080"
    quality = "high"
    compression = "zstd"
    audio_enabled = True
    cursor_enabled = True

class SessionFactory(factory.Factory):
    """Factory for session objects."""
    
    class Meta:
        model = dict
    
    session_id = factory.LazyFunction(lambda: f"sess-{fake.uuid4()[:8]}")
    name = factory.LazyFunction(lambda: f"Test Session {fake.word()}")
    status = SessionStatus.CREATED
    created_at = factory.LazyFunction(datetime.utcnow)
    rdp_config = factory.SubFactory(RDPConfigFactory)
    recording_config = factory.SubFactory(RecordingConfigFactory)
```

## Code Coverage Requirements

### Coverage Configuration

#### Coverage Settings
```ini
# sessions/.coveragerc
[run]
source = app
omit =
    */tests/*
    */migrations/*
    */__pycache__/*
    */venv/*

[report]
precision = 2
show_missing = True
skip_covered = False

[html]
directory = htmlcov
```

### Coverage Targets

| Component | Minimum Coverage | Critical Path Coverage |
|-----------|-----------------|----------------------|
| API Endpoints | 90% | 100% |
| Service Layer | 85% | 100% |
| Data Models | 95% | 100% |
| Security | 100% | 100% |
| Encryption | 100% | 100% |
| Pipeline | 80% | 95% |
| Storage | 80% | 95% |
| **Overall** | **80%** | **100%** |

## CI/CD Integration

### GitHub Actions Workflow

#### Test Workflow
```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      mongodb:
        image: mongo:6.0
        ports:
          - 27017:27017
        options: >-
          --health-cmd "mongosh --eval 'db.runCommand({ping: 1})'"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run linting
        run: |
          flake8 app tests
          black --check app tests
          mypy app
      
      - name: Run unit tests
        run: |
          pytest tests/ -m unit --cov=app --cov-report=xml --cov-report=html
      
      - name: Run integration tests
        run: |
          pytest tests/ -m integration --cov=app --cov-append --cov-report=xml
      
      - name: Run security tests
        run: |
          pytest tests/ -m security
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          flags: unittests
          name: codecov-umbrella
      
      - name: Check coverage threshold
        run: |
          coverage report --fail-under=80
```

### Pre-commit Hooks

#### Pre-commit Configuration
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
      - id: check-merge-conflict
  
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11
  
  - repo: https://github.com/PyCQA/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=100']
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, types-redis]
  
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest
        args: ['-m', 'unit', '--tb=short']
        language: system
        pass_filenames: false
        always_run: true
```

## Test Execution

### Running Tests

#### Run All Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m performance
pytest -m security

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_api/test_session_create.py

# Run specific test function
pytest tests/test_api/test_session_create.py::TestSessionCreate::test_create_session_success
```

#### Parallel Test Execution
```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest -n auto

# Run tests with specific worker count
pytest -n 4
```

## Continuous Monitoring

### Performance Benchmarks

Track performance metrics over time:

- Session creation time: < 100ms (p95)
- Session start time: < 200ms (p95)
- Chunk processing: > 1000 chunks/minute
- Storage throughput: > 100 MB/s
- API response time: < 200ms (p95)
- Concurrent sessions: 100+ simultaneous

### Quality Metrics

Monitor code quality metrics:

- Code coverage: > 80% overall
- Test success rate: > 99%
- Flaky test rate: < 1%
- Test execution time: < 5 minutes
- Security vulnerabilities: 0 critical

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-XX  
**Next Review**: 2024-04-XX

