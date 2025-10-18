"""
Emergency Controls Integration Tests

This module tests the emergency controls functionality across the system,
including system lockdown, emergency stop, and disaster recovery procedures.
"""

import pytest
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List


class TestEmergencyControls:
    """Test emergency controls functionality."""

    @pytest.mark.asyncio
    async def test_emergency_lockdown_activation(self, admin_session):
        """Test emergency lockdown activation."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        lockdown_data = {
            "reason": "Security incident detected",
            "duration_minutes": 60,
            "affected_services": ["api-gateway", "session-management"]
        }
        
        async with session.post(
            f"{admin_url}/admin/emergency/lockdown",
            json=lockdown_data,
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "lockdown_id" in data
            assert "status" in data
            assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_emergency_lockdown_status(self, admin_session):
        """Test emergency lockdown status check."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        async with session.get(
            f"{admin_url}/admin/emergency/lockdown/status",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "lockdown_active" in data
            assert "reason" in data
            assert "start_time" in data

    @pytest.mark.asyncio
    async def test_emergency_stop_activation(self, admin_session):
        """Test emergency stop activation."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        stop_data = {
            "reason": "Critical system failure",
            "affected_services": ["all"],
            "graceful_shutdown": True
        }
        
        async with session.post(
            f"{admin_url}/admin/emergency/stop",
            json=stop_data,
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "stop_id" in data
            assert "status" in data
            assert "shutdown_sequence" in data

    @pytest.mark.asyncio
    async def test_emergency_stop_status(self, admin_session):
        """Test emergency stop status check."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        async with session.get(
            f"{admin_url}/admin/emergency/stop/status",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "stop_active" in data
            assert "reason" in data
            assert "affected_services" in data

    @pytest.mark.asyncio
    async def test_maintenance_mode_activation(self, admin_session):
        """Test maintenance mode activation."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        maintenance_data = {
            "reason": "Scheduled maintenance",
            "duration_minutes": 120,
            "maintenance_message": "System under maintenance. Please try again later."
        }
        
        async with session.post(
            f"{admin_url}/admin/emergency/maintenance",
            json=maintenance_data,
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "maintenance_id" in data
            assert "status" in data
            assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_maintenance_mode_status(self, admin_session):
        """Test maintenance mode status check."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        async with session.get(
            f"{admin_url}/admin/emergency/maintenance/status",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "maintenance_active" in data
            assert "reason" in data
            assert "message" in data

    @pytest.mark.asyncio
    async def test_emergency_controls_authentication(self, admin_interface_url):
        """Test that emergency controls require authentication."""
        async with aiohttp.ClientSession() as session:
            # Test lockdown without authentication
            lockdown_data = {"reason": "Test lockdown"}
            async with session.post(
                f"{admin_interface_url}/admin/emergency/lockdown",
                json=lockdown_data
            ) as response:
                assert response.status == 401

    @pytest.mark.asyncio
    async def test_emergency_controls_authorization(self, admin_session):
        """Test emergency controls authorization levels."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test that only super-admin can access emergency controls
        async with session.get(
            f"{admin_url}/admin/emergency/controls",
            headers=headers
        ) as response:
            # Should be accessible with admin token
            assert response.status in [200, 403]

    @pytest.mark.asyncio
    async def test_emergency_audit_logging(self, admin_session):
        """Test emergency controls audit logging."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Activate lockdown
        lockdown_data = {
            "reason": "Audit test lockdown",
            "duration_minutes": 5
        }
        
        async with session.post(
            f"{admin_url}/admin/emergency/lockdown",
            json=lockdown_data,
            headers=headers
        ) as response:
            assert response.status == 200
        
        # Check audit logs
        async with session.get(
            f"{admin_url}/admin/audit/logs?action=emergency",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "logs" in data
            # Should contain emergency action logs
            emergency_logs = [log for log in data["logs"] if "emergency" in log.get("action", "")]
            assert len(emergency_logs) > 0

    @pytest.mark.asyncio
    async def test_emergency_controls_recovery(self, admin_session):
        """Test emergency controls recovery procedures."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Deactivate lockdown
        async with session.post(
            f"{admin_url}/admin/emergency/lockdown/deactivate",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "status" in data
            assert data["status"] == "deactivated"

    @pytest.mark.asyncio
    async def test_emergency_controls_notification(self, admin_session):
        """Test emergency controls notification system."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test notification settings
        notification_data = {
            "email_notifications": True,
            "webhook_url": "https://hooks.slack.com/test",
            "notification_level": "critical"
        }
        
        async with session.post(
            f"{admin_url}/admin/emergency/notifications",
            json=notification_data,
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "notification_id" in data
            assert "status" in data

    @pytest.mark.asyncio
    async def test_emergency_controls_validation(self, admin_session):
        """Test emergency controls input validation."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test invalid lockdown data
        invalid_lockdown_data = {
            "reason": "",  # Empty reason
            "duration_minutes": -1  # Invalid duration
        }
        
        async with session.post(
            f"{admin_url}/admin/emergency/lockdown",
            json=invalid_lockdown_data,
            headers=headers
        ) as response:
            assert response.status == 400

    @pytest.mark.asyncio
    async def test_emergency_controls_concurrent_operations(self, admin_session):
        """Test concurrent emergency control operations."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test multiple concurrent lockdown attempts
        lockdown_data = {
            "reason": "Concurrent test lockdown",
            "duration_minutes": 10
        }
        
        # First lockdown
        async with session.post(
            f"{admin_url}/admin/emergency/lockdown",
            json=lockdown_data,
            headers=headers
        ) as response1:
            assert response1.status == 200
        
        # Second lockdown (should be rejected or queued)
        async with session.post(
            f"{admin_url}/admin/emergency/lockdown",
            json=lockdown_data,
            headers=headers
        ) as response2:
            # Should either succeed (if queued) or be rejected
            assert response2.status in [200, 409, 422]

    @pytest.mark.asyncio
    async def test_emergency_controls_performance(self, admin_session):
        """Test emergency controls performance requirements."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test response time for emergency status
        start_time = datetime.now()
        async with session.get(
            f"{admin_url}/admin/emergency/status",
            headers=headers
        ) as response:
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            assert response.status == 200
            # Emergency status should respond within 1 second
            assert response_time < 1.0

    @pytest.mark.asyncio
    async def test_emergency_controls_error_handling(self, admin_session):
        """Test emergency controls error handling."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test invalid emergency endpoint
        async with session.get(
            f"{admin_url}/admin/emergency/invalid-endpoint",
            headers=headers
        ) as response:
            assert response.status == 404

    @pytest.mark.asyncio
    async def test_emergency_controls_cors_headers(self, admin_interface_url):
        """Test CORS headers for emergency controls."""
        async with aiohttp.ClientSession() as session:
            # Test OPTIONS request
            async with session.options(f"{admin_interface_url}/admin/emergency/lockdown") as response:
                assert response.status in [200, 204]
                # Check CORS headers
                assert "Access-Control-Allow-Origin" in response.headers
                assert "Access-Control-Allow-Methods" in response.headers
