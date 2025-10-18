# Integration tests for session lifecycle
# End-to-end tests for session creation → anchoring flow

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.main import create_app
from app.schemas.sessions import (
    SessionResponse, SessionDetail, SessionState, 
    ManifestResponse, TrustPolicy, PolicyValidationResponse
)


@pytest.fixture
def client():
    """Create test client"""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_session_service():
    """Mock session service for integration tests"""
    with patch('app.routes.sessions.get_session_service') as mock:
        service = Mock()
        service.create_session = AsyncMock()
        service.list_sessions = AsyncMock()
        service.get_session_detail = AsyncMock()
        service.start_session_recording = AsyncMock()
        service.finalize_session = AsyncMock()
        service.cancel_session = AsyncMock()
        service.get_session_state = AsyncMock()
        service.get_session_manifest = AsyncMock()
        service.get_merkle_proof = AsyncMock()
        service.get_anchor_receipt = AsyncMock()
        service.set_session_policy = AsyncMock()
        service.get_session_policy = AsyncMock()
        service.validate_session_policy = AsyncMock()
        mock.return_value = service
        yield service


class TestSessionLifecycleIntegration:
    """Integration tests for complete session lifecycle"""
    
    def test_complete_session_lifecycle(self, client, mock_session_service):
        """Test complete session lifecycle: create → policy → start → finalize → manifest"""
        
        # Step 1: Create session
        session_id = "integration-test-session-123"
        user_id = "user-123"
        owner_address = "TTest123456789012345678901234567890"
        node_id = "node-001"
        
        mock_session_service.create_session.return_value = SessionResponse(
            session_id=session_id,
            user_id=user_id,
            owner_address=owner_address,
            node_id=node_id,
            state=SessionState.INITIALIZING,
            created_at=datetime.utcnow()
        )
        
        create_response = client.post("/sessions/", json={
            "user_id": user_id,
            "owner_address": owner_address,
            "node_id": node_id
        })
        
        assert create_response.status_code == 201
        session_data = create_response.json()
        assert session_data["session_id"] == session_id
        assert session_data["state"] == "initializing"
        
        # Step 2: Set trust policy
        trust_policy = {
            "policy_id": "policy-123",
            "session_id": session_id,
            "input_controls": {
                "mouse_enabled": True,
                "keyboard_enabled": True,
                "mouse_blocklist": [],
                "keyboard_blocklist": []
            },
            "clipboard_controls": {
                "host_to_remote": True,
                "remote_to_host": True,
                "max_bytes": 1048576
            },
            "file_transfer_controls": {
                "upload_enabled": True,
                "download_enabled": True,
                "allowed_dirs": ["/tmp"],
                "blocked_dirs": [],
                "allowed_extensions": [],
                "blocked_extensions": [".exe", ".bat"],
                "max_file_size": 104857600
            },
            "system_controls": {
                "screenshare_enabled": True,
                "audio_enabled": False,
                "camera_enabled": False,
                "printing_enabled": False,
                "shell_channels": False,
                "system_commands": False
            },
            "policy_hash": "sha256-test-policy-hash"
        }
        
        mock_session_service.set_session_policy.return_value = PolicyValidationResponse(
            valid=True,
            errors=[],
            warnings=[],
            accepted_at=datetime.utcnow()
        )
        
        policy_response = client.post(f"/sessions/{session_id}/policy", json=trust_policy)
        assert policy_response.status_code == 201
        policy_data = policy_response.json()
        assert policy_data["valid"] is True
        
        # Step 3: Start session recording
        mock_session_service.start_session_recording.return_value = SessionResponse(
            session_id=session_id,
            user_id=user_id,
            owner_address=owner_address,
            node_id=node_id,
            state=SessionState.RECORDING,
            created_at=datetime.utcnow(),
            started_at=datetime.utcnow()
        )
        
        start_response = client.put(f"/sessions/{session_id}/start")
        assert start_response.status_code == 200
        start_data = start_response.json()
        assert start_data["state"] == "recording"
        
        # Step 4: Finalize session and trigger anchoring
        mock_session_service.finalize_session.return_value = SessionDetail(
            session_id=session_id,
            user_id=user_id,
            owner_address=owner_address,
            node_id=node_id,
            state=SessionState.COMPLETED,
            created_at=datetime.utcnow(),
            started_at=datetime.utcnow(),
            ended_at=datetime.utcnow(),
            manifest_hash="test-manifest-hash-123",
            merkle_root="test-merkle-root-456",
            anchor_txid="0x1234567890abcdef",
            total_chunks=15,
            total_size=45678901
        )
        
        finalize_response = client.put(f"/sessions/{session_id}/finalize")
        assert finalize_response.status_code == 200
        finalize_data = finalize_response.json()
        assert finalize_data["state"] == "completed"
        assert finalize_data["manifest_hash"] == "test-manifest-hash-123"
        assert finalize_data["anchor_txid"] == "0x1234567890abcdef"
        
        # Step 5: Retrieve session manifest
        mock_session_service.get_session_manifest.return_value = ManifestResponse(
            session_id=session_id,
            manifest_hash="test-manifest-hash-123",
            merkle_root="test-merkle-root-456",
            chunk_count=15,
            total_size=45678901,
            created_at=datetime.utcnow(),
            anchor_txid="0x1234567890abcdef"
        )
        
        manifest_response = client.get(f"/sessions/{session_id}/manifest")
        assert manifest_response.status_code == 200
        manifest_data = manifest_response.json()
        assert manifest_data["session_id"] == session_id
        assert manifest_data["chunk_count"] == 15
        assert manifest_data["total_size"] == 45678901
        
        # Step 6: Get anchor receipt
        mock_session_service.get_anchor_receipt.return_value = {
            "session_id": session_id,
            "anchor_txid": "0x1234567890abcdef",
            "block_number": 12345,
            "gas_used": 21000,
            "status": "confirmed",
            "confirmed_at": datetime.utcnow().isoformat()
        }
        
        receipt_response = client.get(f"/sessions/{session_id}/anchor-receipt")
        assert receipt_response.status_code == 200
        receipt_data = receipt_response.json()
        assert receipt_data["anchor_txid"] == "0x1234567890abcdef"
        assert receipt_data["status"] == "confirmed"
    
    def test_session_lifecycle_with_policy_validation_failure(self, client, mock_session_service):
        """Test session lifecycle when policy validation fails"""
        
        session_id = "policy-fail-test-session-123"
        
        # Create session
        mock_session_service.create_session.return_value = SessionResponse(
            session_id=session_id,
            user_id="user-123",
            owner_address="TTest123456789012345678901234567890",
            node_id="node-001",
            state=SessionState.INITIALIZING,
            created_at=datetime.utcnow()
        )
        
        create_response = client.post("/sessions/", json={
            "user_id": "user-123",
            "owner_address": "TTest123456789012345678901234567890",
            "node_id": "node-001"
        })
        assert create_response.status_code == 201
        
        # Try to set invalid policy
        invalid_policy = {
            "policy_id": "invalid-policy-123",
            "session_id": session_id,
            "input_controls": {
                "mouse_enabled": True,
                "keyboard_enabled": True,
                "mouse_blocklist": [],
                "keyboard_blocklist": []
            },
            "clipboard_controls": {
                "host_to_remote": True,
                "remote_to_host": True,
                "max_bytes": -1  # Invalid negative value
            },
            "file_transfer_controls": {
                "upload_enabled": True,
                "download_enabled": True,
                "allowed_dirs": [],
                "blocked_dirs": [],
                "allowed_extensions": [],
                "blocked_extensions": [],
                "max_file_size": 104857600
            },
            "system_controls": {
                "screenshare_enabled": True,
                "audio_enabled": False,
                "camera_enabled": False,
                "printing_enabled": False,
                "shell_channels": False,
                "system_commands": False
            },
            "policy_hash": "sha256-invalid-policy-hash"
        }
        
        mock_session_service.set_session_policy.return_value = PolicyValidationResponse(
            valid=False,
            errors=["Invalid max_bytes value: must be positive"],
            warnings=[],
            accepted_at=None
        )
        
        policy_response = client.post(f"/sessions/{session_id}/policy", json=invalid_policy)
        assert policy_response.status_code == 201  # Policy endpoint returns validation result
        policy_data = policy_response.json()
        assert policy_data["valid"] is False
        assert len(policy_data["errors"]) > 0
    
    def test_session_state_transitions(self, client, mock_session_service):
        """Test session state transitions and error handling"""
        
        session_id = "state-transition-test-123"
        
        # Create session
        mock_session_service.create_session.return_value = SessionResponse(
            session_id=session_id,
            user_id="user-123",
            owner_address="TTest123456789012345678901234567890",
            node_id="node-001",
            state=SessionState.INITIALIZING,
            created_at=datetime.utcnow()
        )
        
        create_response = client.post("/sessions/", json={
            "user_id": "user-123",
            "owner_address": "TTest123456789012345678901234567890",
            "node_id": "node-001"
        })
        assert create_response.status_code == 201
        
        # Try to finalize before starting (should fail)
        mock_session_service.finalize_session.side_effect = ValueError("Cannot finalize session in INITIALIZING state")
        
        finalize_response = client.put(f"/sessions/{session_id}/finalize")
        assert finalize_response.status_code == 400
        
        # Start session
        mock_session_service.start_session_recording.return_value = SessionResponse(
            session_id=session_id,
            user_id="user-123",
            owner_address="TTest123456789012345678901234567890",
            node_id="node-001",
            state=SessionState.RECORDING,
            created_at=datetime.utcnow(),
            started_at=datetime.utcnow()
        )
        
        start_response = client.put(f"/sessions/{session_id}/start")
        assert start_response.status_code == 200
        
        # Try to start again (should fail)
        mock_session_service.start_session_recording.side_effect = ValueError("Cannot start session in RECORDING state")
        
        start_again_response = client.put(f"/sessions/{session_id}/start")
        assert start_again_response.status_code == 400
    
    def test_session_cancellation(self, client, mock_session_service):
        """Test session cancellation before recording starts"""
        
        session_id = "cancellation-test-123"
        
        # Create session
        mock_session_service.create_session.return_value = SessionResponse(
            session_id=session_id,
            user_id="user-123",
            owner_address="TTest123456789012345678901234567890",
            node_id="node-001",
            state=SessionState.INITIALIZING,
            created_at=datetime.utcnow()
        )
        
        create_response = client.post("/sessions/", json={
            "user_id": "user-123",
            "owner_address": "TTest123456789012345678901234567890",
            "node_id": "node-001"
        })
        assert create_response.status_code == 201
        
        # Cancel session
        mock_session_service.cancel_session.return_value = True
        
        cancel_response = client.delete(f"/sessions/{session_id}")
        assert cancel_response.status_code == 204
        
        # Try to start cancelled session (should fail)
        mock_session_service.start_session_recording.side_effect = ValueError("Session not found")
        
        start_response = client.put(f"/sessions/{session_id}/start")
        assert start_response.status_code == 400
