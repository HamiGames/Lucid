"""
Phase 3 Integration Tests - Session Lifecycle

This module tests the complete session lifecycle from creation to anchoring:
1. Session creation
2. Recording start
3. Chunk processing
4. Blockchain anchoring
5. Session completion

Tests validate the full workflow across session management, RDP services,
and blockchain integration.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List

@pytest.mark.phase3_integration
@pytest.mark.session_lifecycle
class TestSessionLifecycle:
    """Test complete session lifecycle workflow."""
    
    @pytest.mark.asyncio
    async def test_full_session_lifecycle(
        self,
        session_client,
        rdp_client,
        auth_headers,
        sample_session_data,
        sample_rdp_server_data,
        test_db,
        mock_services,
        integration_test_config
    ):
        """Test complete session lifecycle from creation to anchoring."""
        
        # Step 1: Create RDP Server
        rdp_response = rdp_client.post(
            "/api/v1/rdp/servers",
            json=sample_rdp_server_data,
            headers=auth_headers
        )
        assert rdp_response.status_code == 201
        rdp_server = rdp_response.json()
        server_id = rdp_server["server_id"]
        
        # Step 2: Start RDP Server
        start_response = rdp_client.post(
            f"/api/v1/rdp/servers/{server_id}/start",
            headers=auth_headers
        )
        assert start_response.status_code == 200
        assert start_response.json()["status"] == "running"
        
        # Step 3: Create Session
        session_response = session_client.post(
            "/api/v1/sessions",
            json=sample_session_data,
            headers=auth_headers
        )
        assert session_response.status_code == 201
        session = session_response.json()
        session_id = session["session_id"]
        
        # Step 4: Start Recording
        start_recording_response = session_client.post(
            f"/api/v1/sessions/{session_id}/start",
            headers=auth_headers
        )
        assert start_recording_response.status_code == 200
        assert start_recording_response.json()["status"] == "recording"
        
        # Step 5: Verify Pipeline is Active
        pipeline_response = session_client.get(
            f"/api/v1/sessions/{session_id}/pipeline",
            headers=auth_headers
        )
        assert pipeline_response.status_code == 200
        pipeline = pipeline_response.json()
        assert pipeline["pipeline_status"] == "active"
        assert len(pipeline["stages"]) == 4  # recording, processing, storage, anchoring
        
        # Step 6: Simulate Recording for a few seconds
        await asyncio.sleep(5)
        
        # Step 7: Verify Chunks are Being Created
        chunks_response = session_client.get(
            f"/api/v1/sessions/{session_id}/chunks",
            headers=auth_headers
        )
        assert chunks_response.status_code == 200
        chunks = chunks_response.json()
        assert len(chunks["chunks"]) > 0
        
        # Step 8: Verify Chunk Processing
        for chunk in chunks["chunks"]:
            chunk_id = chunk["chunk_id"]
            chunk_detail_response = session_client.get(
                f"/api/v1/sessions/{session_id}/chunks/{chunk_id}",
                headers=auth_headers
            )
            assert chunk_detail_response.status_code == 200
            chunk_detail = chunk_detail_response.json()
            assert chunk_detail["status"] in ["processed", "stored"]
            assert "merkle_hash" in chunk_detail
            assert "encryption_key_id" in chunk_detail
        
        # Step 9: Stop Recording
        stop_response = session_client.post(
            f"/api/v1/sessions/{session_id}/stop",
            headers=auth_headers
        )
        assert stop_response.status_code == 200
        assert stop_response.json()["status"] == "stopped"
        
        # Step 10: Verify Final Statistics
        stats_response = session_client.get(
            f"/api/v1/sessions/{session_id}/statistics",
            headers=auth_headers
        )
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats["recording_stats"]["total_duration_seconds"] >= 5
        assert stats["storage_stats"]["chunks_count"] > 0
        assert stats["storage_stats"]["total_size_bytes"] > 0
        
        # Step 11: Verify Blockchain Anchoring
        anchoring_response = session_client.get(
            f"/api/v1/sessions/{session_id}/anchoring",
            headers=auth_headers
        )
        assert anchoring_response.status_code == 200
        anchoring = anchoring_response.json()
        assert anchoring["status"] == "anchored"
        assert "transaction_hash" in anchoring
        assert "block_height" in anchoring
        assert "merkle_root" in anchoring
        
        # Step 12: Cleanup - Stop RDP Server
        stop_rdp_response = rdp_client.post(
            f"/api/v1/rdp/servers/{server_id}/stop",
            headers=auth_headers
        )
        assert stop_rdp_response.status_code == 200
        
        # Step 13: Delete RDP Server
        delete_rdp_response = rdp_client.delete(
            f"/api/v1/rdp/servers/{server_id}",
            headers=auth_headers
        )
        assert delete_rdp_response.status_code == 204
    
    @pytest.mark.asyncio
    async def test_session_lifecycle_with_errors(
        self,
        session_client,
        rdp_client,
        auth_headers,
        sample_session_data,
        test_db,
        integration_test_config
    ):
        """Test session lifecycle with error handling."""
        
        # Create session with invalid RDP config
        invalid_session_data = sample_session_data.copy()
        invalid_session_data["rdp_config"]["host"] = "invalid_host"
        
        session_response = session_client.post(
            "/api/v1/sessions",
            json=invalid_session_data,
            headers=auth_headers
        )
        assert session_response.status_code == 400
        
        # Create valid session
        valid_session_response = session_client.post(
            "/api/v1/sessions",
            json=sample_session_data,
            headers=auth_headers
        )
        assert valid_session_response.status_code == 201
        session = valid_session_response.json()
        session_id = session["session_id"]
        
        # Try to start recording without RDP server
        start_response = session_client.post(
            f"/api/v1/sessions/{session_id}/start",
            headers=auth_headers
        )
        assert start_response.status_code == 400
        
        # Verify error handling
        error_response = session_client.get(
            f"/api/v1/sessions/{session_id}/errors",
            headers=auth_headers
        )
        assert error_response.status_code == 200
        errors = error_response.json()
        assert len(errors["errors"]) > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_sessions_lifecycle(
        self,
        session_client,
        rdp_client,
        auth_headers,
        sample_session_data,
        sample_rdp_server_data,
        test_db,
        integration_test_config
    ):
        """Test multiple concurrent sessions lifecycle."""
        
        # Create multiple RDP servers
        server_ids = []
        for i in range(3):
            rdp_data = sample_rdp_server_data.copy()
            rdp_data["name"] = f"Concurrent Test Server {i}"
            
            rdp_response = rdp_client.post(
                "/api/v1/rdp/servers",
                json=rdp_data,
                headers=auth_headers
            )
            assert rdp_response.status_code == 201
            server_ids.append(rdp_response.json()["server_id"])
        
        # Start all RDP servers
        for server_id in server_ids:
            start_response = rdp_client.post(
                f"/api/v1/rdp/servers/{server_id}/start",
                headers=auth_headers
            )
            assert start_response.status_code == 200
        
        # Create multiple sessions
        session_ids = []
        for i in range(3):
            session_data = sample_session_data.copy()
            session_data["name"] = f"Concurrent Test Session {i}"
            
            session_response = session_client.post(
                "/api/v1/sessions",
                json=session_data,
                headers=auth_headers
            )
            assert session_response.status_code == 201
            session_ids.append(session_response.json()["session_id"])
        
        # Start all sessions concurrently
        start_tasks = []
        for session_id in session_ids:
            task = asyncio.create_task(
                self._start_session_async(session_client, session_id, auth_headers)
            )
            start_tasks.append(task)
        
        start_results = await asyncio.gather(*start_tasks)
        for result in start_results:
            assert result["status_code"] == 200
            assert result["status"] == "recording"
        
        # Wait for recording
        await asyncio.sleep(10)
        
        # Verify all sessions are recording
        for session_id in session_ids:
            status_response = session_client.get(
                f"/api/v1/sessions/{session_id}",
                headers=auth_headers
            )
            assert status_response.status_code == 200
            assert status_response.json()["status"] == "recording"
        
        # Stop all sessions
        stop_tasks = []
        for session_id in session_ids:
            task = asyncio.create_task(
                self._stop_session_async(session_client, session_id, auth_headers)
            )
            stop_tasks.append(task)
        
        stop_results = await asyncio.gather(*stop_tasks)
        for result in stop_results:
            assert result["status_code"] == 200
            assert result["status"] == "stopped"
        
        # Cleanup RDP servers
        for server_id in server_ids:
            rdp_client.post(
                f"/api/v1/rdp/servers/{server_id}/stop",
                headers=auth_headers
            )
            rdp_client.delete(
                f"/api/v1/rdp/servers/{server_id}",
                headers=auth_headers
            )
    
    @pytest.mark.asyncio
    async def test_session_pipeline_stages(
        self,
        session_client,
        auth_headers,
        sample_session_data,
        test_db,
        integration_test_config
    ):
        """Test individual pipeline stages."""
        
        # Create session
        session_response = session_client.post(
            "/api/v1/sessions",
            json=sample_session_data,
            headers=auth_headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["session_id"]
        
        # Test recording stage
        recording_response = session_client.get(
            f"/api/v1/sessions/{session_id}/pipeline/stages/recording",
            headers=auth_headers
        )
        assert recording_response.status_code == 200
        recording_stage = recording_response.json()
        assert recording_stage["stage_name"] == "recording"
        assert recording_stage["status"] in ["inactive", "active"]
        
        # Test processing stage
        processing_response = session_client.get(
            f"/api/v1/sessions/{session_id}/pipeline/stages/processing",
            headers=auth_headers
        )
        assert processing_response.status_code == 200
        processing_stage = processing_response.json()
        assert processing_stage["stage_name"] == "processing"
        
        # Test storage stage
        storage_response = session_client.get(
            f"/api/v1/sessions/{session_id}/pipeline/stages/storage",
            headers=auth_headers
        )
        assert storage_response.status_code == 200
        storage_stage = storage_response.json()
        assert storage_stage["stage_name"] == "storage"
        
        # Test anchoring stage
        anchoring_response = session_client.get(
            f"/api/v1/sessions/{session_id}/pipeline/stages/anchoring",
            headers=auth_headers
        )
        assert anchoring_response.status_code == 200
        anchoring_stage = anchoring_response.json()
        assert anchoring_stage["stage_name"] == "anchoring"
    
    @pytest.mark.asyncio
    async def test_session_metadata_persistence(
        self,
        session_client,
        auth_headers,
        sample_session_data,
        test_db
    ):
        """Test session metadata persistence across lifecycle."""
        
        # Create session
        session_response = session_client.post(
            "/api/v1/sessions",
            json=sample_session_data,
            headers=auth_headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["session_id"]
        
        # Verify metadata persistence
        metadata_response = session_client.get(
            f"/api/v1/sessions/{session_id}/metadata",
            headers=auth_headers
        )
        assert metadata_response.status_code == 200
        metadata = metadata_response.json()
        
        assert metadata["project"] == "lucid-phase3-test"
        assert metadata["environment"] == "integration"
        assert "test" in metadata["tags"]
        assert metadata["owner"] == "test-user-123"
        assert metadata["priority"] == "normal"
        
        # Update metadata
        updated_metadata = {
            "project": "lucid-phase3-test-updated",
            "tags": ["test", "integration", "updated"],
            "priority": "high"
        }
        
        update_response = session_client.put(
            f"/api/v1/sessions/{session_id}/metadata",
            json=updated_metadata,
            headers=auth_headers
        )
        assert update_response.status_code == 200
        
        # Verify updated metadata
        updated_response = session_client.get(
            f"/api/v1/sessions/{session_id}/metadata",
            headers=auth_headers
        )
        assert updated_response.status_code == 200
        updated_metadata_response = updated_response.json()
        
        assert updated_metadata_response["project"] == "lucid-phase3-test-updated"
        assert "updated" in updated_metadata_response["tags"]
        assert updated_metadata_response["priority"] == "high"
    
    async def _start_session_async(self, client, session_id: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """Helper method to start session asynchronously."""
        response = client.post(
            f"/api/v1/sessions/{session_id}/start",
            headers=headers
        )
        return {
            "status_code": response.status_code,
            "status": response.json().get("status") if response.status_code == 200 else None
        }
    
    async def _stop_session_async(self, client, session_id: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """Helper method to stop session asynchronously."""
        response = client.post(
            f"/api/v1/sessions/{session_id}/stop",
            headers=headers
        )
        return {
            "status_code": response.status_code,
            "status": response.json().get("status") if response.status_code == 200 else None
        }
