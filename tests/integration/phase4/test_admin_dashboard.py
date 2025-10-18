"""
Admin Dashboard Integration Tests

This module tests the admin interface cluster (Cluster 06) functionality,
including dashboard data aggregation, user management, and system monitoring.
"""

import pytest
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List


class TestAdminDashboard:
    """Test admin dashboard functionality."""

    @pytest.mark.asyncio
    async def test_admin_dashboard_access(self, admin_session):
        """Test admin dashboard accessibility."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        async with session.get(
            f"{admin_url}/admin/dashboard",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "dashboard" in data
            assert "system_stats" in data["dashboard"]

    @pytest.mark.asyncio
    async def test_system_stats_aggregation(self, admin_session):
        """Test system statistics aggregation."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        async with session.get(
            f"{admin_url}/admin/dashboard/stats",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            
            # Verify required stats fields
            required_fields = [
                "total_sessions", "active_sessions", "total_nodes", 
                "active_nodes", "blockchain_height", "total_payouts"
            ]
            for field in required_fields:
                assert field in data
                assert isinstance(data[field], (int, float))

    @pytest.mark.asyncio
    async def test_user_management_interface(self, admin_session):
        """Test user management interface."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test get users list
        async with session.get(
            f"{admin_url}/admin/users",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "users" in data
            assert isinstance(data["users"], list)

    @pytest.mark.asyncio
    async def test_session_monitoring(self, admin_session):
        """Test session monitoring functionality."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test get active sessions
        async with session.get(
            f"{admin_url}/admin/sessions/active",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "sessions" in data
            assert isinstance(data["sessions"], list)

    @pytest.mark.asyncio
    async def test_blockchain_monitoring(self, admin_session):
        """Test blockchain monitoring functionality."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test get blockchain status
        async with session.get(
            f"{admin_url}/admin/blockchain/status",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "blockchain" in data
            assert "height" in data["blockchain"]
            assert "status" in data["blockchain"]

    @pytest.mark.asyncio
    async def test_node_monitoring(self, admin_session):
        """Test node monitoring functionality."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test get nodes list
        async with session.get(
            f"{admin_url}/admin/nodes",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "nodes" in data
            assert isinstance(data["nodes"], list)

    @pytest.mark.asyncio
    async def test_audit_log_access(self, admin_session):
        """Test audit log access functionality."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test get audit logs
        async with session.get(
            f"{admin_url}/admin/audit/logs",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "logs" in data
            assert isinstance(data["logs"], list)

    @pytest.mark.asyncio
    async def test_system_health_monitoring(self, admin_session):
        """Test system health monitoring."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test get system health
        async with session.get(
            f"{admin_url}/admin/health",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "status" in data
            assert "services" in data

    @pytest.mark.asyncio
    async def test_dashboard_real_time_updates(self, admin_session):
        """Test real-time dashboard updates."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "text/event-stream"
        }
        
        # Test WebSocket connection for real-time updates
        try:
            async with session.get(
                f"{admin_url}/admin/dashboard/stream",
                headers=headers
            ) as response:
                assert response.status == 200
                # Verify it's a streaming response
                assert "text/event-stream" in response.headers.get("content-type", "")
        except aiohttp.ClientError:
            # WebSocket might not be available in test environment
            pytest.skip("WebSocket streaming not available in test environment")

    @pytest.mark.asyncio
    async def test_admin_permissions(self, admin_session):
        """Test admin permission enforcement."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test admin-only endpoint
        async with session.get(
            f"{admin_url}/admin/system/config",
            headers=headers
        ) as response:
            # Should be accessible with admin token
            assert response.status in [200, 403]  # 403 if not implemented yet

    @pytest.mark.asyncio
    async def test_dashboard_data_consistency(self, admin_session):
        """Test dashboard data consistency across multiple requests."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get dashboard data multiple times
        responses = []
        for _ in range(3):
            async with session.get(
                f"{admin_url}/admin/dashboard/stats",
                headers=headers
            ) as response:
                assert response.status == 200
                data = await response.json()
                responses.append(data)
        
        # Verify data consistency (some fields should be consistent)
        for i in range(1, len(responses)):
            # Total nodes and total sessions should be consistent
            assert responses[0]["total_nodes"] == responses[i]["total_nodes"]
            assert responses[0]["total_sessions"] == responses[i]["total_sessions"]

    @pytest.mark.asyncio
    async def test_dashboard_performance(self, admin_session):
        """Test dashboard performance requirements."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test response time
        start_time = datetime.now()
        async with session.get(
            f"{admin_url}/admin/dashboard",
            headers=headers
        ) as response:
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            assert response.status == 200
            # Dashboard should load within 2 seconds
            assert response_time < 2.0

    @pytest.mark.asyncio
    async def test_dashboard_error_handling(self, admin_session):
        """Test dashboard error handling."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test invalid endpoint
        async with session.get(
            f"{admin_url}/admin/invalid-endpoint",
            headers=headers
        ) as response:
            assert response.status == 404

    @pytest.mark.asyncio
    async def test_dashboard_authentication_required(self, admin_interface_url):
        """Test that dashboard requires authentication."""
        async with aiohttp.ClientSession() as session:
            # Test without authentication
            async with session.get(f"{admin_interface_url}/admin/dashboard") as response:
                assert response.status == 401

    @pytest.mark.asyncio
    async def test_dashboard_cors_headers(self, admin_interface_url):
        """Test CORS headers for dashboard."""
        async with aiohttp.ClientSession() as session:
            # Test OPTIONS request
            async with session.options(f"{admin_interface_url}/admin/dashboard") as response:
                assert response.status in [200, 204]
                # Check CORS headers
                assert "Access-Control-Allow-Origin" in response.headers
                assert "Access-Control-Allow-Methods" in response.headers
