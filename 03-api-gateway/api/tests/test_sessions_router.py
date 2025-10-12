# Unit tests for sessions router
# Tests session lifecycle management endpoints

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.main import create_app
from app.schemas.sessions import SessionResponse, SessionState


@pytest.fixture
def client():
    """Create test client"""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_session_service():
    """Mock session service"""
    with patch('app.routes.sessions.get_session_service') as mock:
        service = Mock()
        service.create_session = AsyncMock()
        service.list_sessions = AsyncMock()
        service.get_session_detail = AsyncMock()
        service.start_session_recording = AsyncMock()
        service.finalize_session = AsyncMock()
        service.cancel_session = AsyncMock()
        service.get_session_state = AsyncMock()
        mock.return_value = service
        yield service


class TestSessionCreation:
    """Test session creation endpoint"""
    
    def test_create_session_success(self, client, mock_session_service):
        """Test successful session creation"""
        # Mock service response
        mock_session_service.create_session.return_value = SessionResponse(
            session_id="test-session-123",
            user_id="user-123",
            owner_address="TTest123456789012345678901234567890",
            node_id="node-001",
            state=SessionState.INITIALIZING,
            created_at=datetime.utcnow(),
            policy_hash=None
        )
        
        # Test request
        response = client.post("/sessions/", json={
            "user_id": "user-123",
            "owner_address": "TTest123456789012345678901234567890",
            "node_id": "node-001"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["session_id"] == "test-session-123"
        assert data["state"] == "initializing"
    
    def test_create_session_invalid_address(self, client, mock_session_service):
        """Test session creation with invalid TRON address"""
        response = client.post("/sessions/", json={
            "user_id": "user-123",
            "owner_address": "invalid-address",
            "node_id": "node-001"
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_create_session_missing_fields(self, client, mock_session_service):
        """Test session creation with missing required fields"""
        response = client.post("/sessions/", json={
            "user_id": "user-123"
        })
        
        assert response.status_code == 422  # Validation error


class TestSessionList:
    """Test session listing endpoint"""
    
    def test_list_sessions_success(self, client, mock_session_service):
        """Test successful session listing"""
        from app.schemas.sessions import SessionList, SessionResponse
        
        # Mock service response
        mock_session_service.list_sessions.return_value = SessionList(
            items=[
                SessionResponse(
                    session_id="test-session-123",
                    user_id="user-123",
                    owner_address="TTest123456789012345678901234567890",
                    node_id="node-001",
                    state=SessionState.INITIALIZING,
                    created_at=datetime.utcnow()
                )
            ],
            total=1,
            page=1,
            page_size=20,
            has_next=False
        )
        
        # Test request
        response = client.get("/sessions/?user_id=user-123")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1
    
    def test_list_sessions_with_filters(self, client, mock_session_service):
        """Test session listing with state filter"""
        from app.schemas.sessions import SessionList
        
        mock_session_service.list_sessions.return_value = SessionList(
            items=[],
            total=0,
            page=1,
            page_size=20,
            has_next=False
        )
        
        response = client.get("/sessions/?user_id=user-123&state=recording")
        
        assert response.status_code == 200
        mock_session_service.list_sessions.assert_called_once()


class TestSessionDetail:
    """Test session detail endpoint"""
    
    def test_get_session_detail_success(self, client, mock_session_service):
        """Test successful session detail retrieval"""
        from app.schemas.sessions import SessionDetail
        
        mock_session_service.get_session_detail.return_value = SessionDetail(
            session_id="test-session-123",
            user_id="user-123",
            owner_address="TTest123456789012345678901234567890",
            node_id="node-001",
            state=SessionState.INITIALIZING,
            created_at=datetime.utcnow()
        )
        
        response = client.get("/sessions/test-session-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-123"
    
    def test_get_session_detail_not_found(self, client, mock_session_service):
        """Test session detail retrieval for non-existent session"""
        mock_session_service.get_session_detail.return_value = None
        
        response = client.get("/sessions/non-existent")
        
        assert response.status_code == 404


class TestSessionStateTransitions:
    """Test session state transition endpoints"""
    
    def test_start_session_recording_success(self, client, mock_session_service):
        """Test successful session recording start"""
        mock_session_service.start_session_recording.return_value = SessionResponse(
            session_id="test-session-123",
            user_id="user-123",
            owner_address="TTest123456789012345678901234567890",
            node_id="node-001",
            state=SessionState.RECORDING,
            created_at=datetime.utcnow(),
            started_at=datetime.utcnow()
        )
        
        response = client.put("/sessions/test-session-123/start")
        
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "recording"
    
    def test_finalize_session_success(self, client, mock_session_service):
        """Test successful session finalization"""
        from app.schemas.sessions import SessionDetail
        
        mock_session_service.finalize_session.return_value = SessionDetail(
            session_id="test-session-123",
            user_id="user-123",
            owner_address="TTest123456789012345678901234567890",
            node_id="node-001",
            state=SessionState.ANCHORING,
            created_at=datetime.utcnow(),
            started_at=datetime.utcnow(),
            manifest_hash="test-manifest-hash",
            merkle_root="test-merkle-root"
        )
        
        response = client.put("/sessions/test-session-123/finalize")
        
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "anchoring"
        assert data["manifest_hash"] == "test-manifest-hash"
    
    def test_cancel_session_success(self, client, mock_session_service):
        """Test successful session cancellation"""
        mock_session_service.cancel_session.return_value = True
        
        response = client.delete("/sessions/test-session-123")
        
        assert response.status_code == 204
    
    def test_cancel_session_failed(self, client, mock_session_service):
        """Test session cancellation failure"""
        mock_session_service.cancel_session.return_value = False
        
        response = client.delete("/sessions/test-session-123")
        
        assert response.status_code == 400


class TestSessionState:
    """Test session state endpoint"""
    
    def test_get_session_state_success(self, client, mock_session_service):
        """Test successful session state retrieval"""
        mock_session_service.get_session_state.return_value = {
            "session_id": "test-session-123",
            "state": "recording",
            "created_at": "2024-01-01T00:00:00Z",
            "recording_started_at": "2024-01-01T00:05:00Z"
        }
        
        response = client.get("/sessions/test-session-123/state")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-123"
        assert data["state"] == "recording"
    
    def test_get_session_state_not_found(self, client, mock_session_service):
        """Test session state retrieval for non-existent session"""
        mock_session_service.get_session_state.return_value = None
        
        response = client.get("/sessions/non-existent/state")
        
        assert response.status_code == 404
