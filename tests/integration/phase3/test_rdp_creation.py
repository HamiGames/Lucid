"""
Phase 3 Integration Tests - RDP Server Dynamic Creation

This module tests RDP server dynamic creation and management:
1. RDP server creation with resource allocation
2. Dynamic port assignment
3. XRDP service integration
4. Resource monitoring
5. Session management integration

Tests validate the complete RDP server lifecycle and integration
with session management services.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List

@pytest.mark.phase3_integration
@pytest.mark.rdp_creation
class TestRDPCreation:
    """Test RDP server dynamic creation and management."""
    
    @pytest.mark.asyncio
    async def test_rdp_server_dynamic_creation(
        self,
        rdp_client,
        session_client,
        auth_headers,
        sample_rdp_server_data,
        test_db,
        integration_test_config
    ):
        """Test dynamic RDP server creation with resource allocation."""
        
        # Step 1: Create RDP Server
        create_response = rdp_client.post(
            "/api/v1/rdp/servers",
            json=sample_rdp_server_data,
            headers=auth_headers
        )
        assert create_response.status_code == 201
        server = create_response.json()
        server_id = server["server_id"]
        
        # Verify server creation
        assert server["name"] == sample_rdp_server_data["name"]
        assert server["status"] == "stopped"
        assert server["port"] >= 33890
        assert server["port"] <= 33999
        assert server["user_id"] == sample_rdp_server_data["user_id"]
        
        # Step 2: Start RDP Server
        start_response = rdp_client.post(
            f"/api/v1/rdp/servers/{server_id}/start",
            headers=auth_headers
        )
        assert start_response.status_code == 200
        start_result = start_response.json()
        assert start_result["status"] == "running"
        assert "started_at" in start_result
        
        # Step 3: Verify XRDP Service Status
        service_status_response = rdp_client.get(
            f"/api/v1/rdp/servers/{server_id}/service-status",
            headers=auth_headers
        )
        assert service_status_response.status_code == 200
        service_status = service_status_response.json()
        assert service_status["xrdp_status"] == "active"
        assert service_status["xrdp_sesman_status"] == "active"
        
        # Step 4: Verify Resource Allocation
        resources_response = rdp_client.get(
            f"/api/v1/rdp/servers/{server_id}/resources",
            headers=auth_headers
        )
        assert resources_response.status_code == 200
        resources = resources_response.json()
        
        assert resources["cpu_limit"] == sample_rdp_server_data["resources"]["cpu_limit"]
        assert resources["memory_limit"] == sample_rdp_server_data["resources"]["memory_limit"]
        assert resources["disk_limit"] == sample_rdp_server_data["resources"]["disk_limit"]
        assert resources["network_bandwidth"] == sample_rdp_server_data["resources"]["network_bandwidth"]
        
        # Step 5: Test RDP Connection
        connection_test_response = rdp_client.post(
            f"/api/v1/rdp/servers/{server_id}/test-connection",
            headers=auth_headers
        )
        assert connection_test_response.status_code == 200
        connection_test = connection_test_response.json()
        assert connection_test["connection_available"] is True
        assert connection_test["port_open"] is True
        
        # Step 6: Stop RDP Server
        stop_response = rdp_client.post(
            f"/api/v1/rdp/servers/{server_id}/stop",
            headers=auth_headers
        )
        assert stop_response.status_code == 200
        stop_result = stop_response.json()
        assert stop_result["status"] == "stopped"
        assert "stopped_at" in stop_result
        
        # Step 7: Delete RDP Server
        delete_response = rdp_client.delete(
            f"/api/v1/rdp/servers/{server_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 204
    
    @pytest.mark.asyncio
    async def test_rdp_server_port_allocation(
        self,
        rdp_client,
        auth_headers,
        sample_rdp_server_data,
        test_db
    ):
        """Test dynamic port allocation for multiple RDP servers."""
        
        # Create multiple RDP servers
        server_ids = []
        allocated_ports = set()
        
        for i in range(5):
            server_data = sample_rdp_server_data.copy()
            server_data["name"] = f"Port Test Server {i}"
            
            create_response = rdp_client.post(
                "/api/v1/rdp/servers",
                json=server_data,
                headers=auth_headers
            )
            assert create_response.status_code == 201
            server = create_response.json()
            server_ids.append(server["server_id"])
            allocated_ports.add(server["port"])
        
        # Verify all ports are unique
        assert len(allocated_ports) == 5
        
        # Verify ports are in valid range
        for port in allocated_ports:
            assert 33890 <= port <= 33999
        
        # Test port conflict handling
        conflict_response = rdp_client.post(
            "/api/v1/rdp/servers",
            json=sample_rdp_server_data,
            headers=auth_headers
        )
        # Should still succeed with different port
        assert conflict_response.status_code == 201
        
        # Cleanup
        for server_id in server_ids:
            rdp_client.delete(
                f"/api/v1/rdp/servers/{server_id}",
                headers=auth_headers
            )
    
    @pytest.mark.asyncio
    async def test_rdp_server_resource_monitoring(
        self,
        rdp_client,
        auth_headers,
        sample_rdp_server_data,
        test_db,
        integration_test_config
    ):
        """Test RDP server resource monitoring."""
        
        # Create and start RDP server
        create_response = rdp_client.post(
            "/api/v1/rdp/servers",
            json=sample_rdp_server_data,
            headers=auth_headers
        )
        assert create_response.status_code == 201
        server_id = create_response.json()["server_id"]
        
        start_response = rdp_client.post(
            f"/api/v1/rdp/servers/{server_id}/start",
            headers=auth_headers
        )
        assert start_response.status_code == 200
        
        # Wait for resource monitoring to collect data
        await asyncio.sleep(2)
        
        # Get resource usage
        usage_response = rdp_client.get(
            f"/api/v1/rdp/servers/{server_id}/usage",
            headers=auth_headers
        )
        assert usage_response.status_code == 200
        usage = usage_response.json()
        
        assert "cpu_percent" in usage
        assert "memory_percent" in usage
        assert "disk_percent" in usage
        assert "network_in" in usage
        assert "network_out" in usage
        assert "timestamp" in usage
        
        # Verify resource limits are respected
        assert usage["cpu_percent"] <= sample_rdp_server_data["resources"]["cpu_limit"] * 100
        assert usage["memory_percent"] <= 100  # Should be percentage
        
        # Get resource history
        history_response = rdp_client.get(
            f"/api/v1/rdp/servers/{server_id}/usage/history?duration=1h",
            headers=auth_headers
        )
        assert history_response.status_code == 200
        history = history_response.json()
        
        assert "usage_history" in history
        assert len(history["usage_history"]) > 0
        
        # Test resource alerts
        alerts_response = rdp_client.get(
            f"/api/v1/rdp/servers/{server_id}/alerts",
            headers=auth_headers
        )
        assert alerts_response.status_code == 200
        alerts = alerts_response.json()
        
        assert "active_alerts" in alerts
        assert "alert_history" in alerts
        
        # Cleanup
        rdp_client.post(
            f"/api/v1/rdp/servers/{server_id}/stop",
            headers=auth_headers
        )
        rdp_client.delete(
            f"/api/v1/rdp/servers/{server_id}",
            headers=auth_headers
        )
    
    @pytest.mark.asyncio
    async def test_rdp_server_session_integration(
        self,
        rdp_client,
        session_client,
        auth_headers,
        sample_rdp_server_data,
        sample_session_data,
        test_db
    ):
        """Test RDP server integration with session management."""
        
        # Create RDP server
        rdp_response = rdp_client.post(
            "/api/v1/rdp/servers",
            json=sample_rdp_server_data,
            headers=auth_headers
        )
        assert rdp_response.status_code == 201
        server_id = rdp_response.json()["server_id"]
        
        # Start RDP server
        rdp_client.post(
            f"/api/v1/rdp/servers/{server_id}/start",
            headers=auth_headers
        )
        
        # Create session with RDP server
        session_data = sample_session_data.copy()
        session_data["rdp_config"]["host"] = "localhost"  # Use localhost for testing
        session_data["rdp_config"]["port"] = rdp_response.json()["port"]
        
        session_response = session_client.post(
            "/api/v1/sessions",
            json=session_data,
            headers=auth_headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["session_id"]
        
        # Start session recording
        start_response = session_client.post(
            f"/api/v1/sessions/{session_id}/start",
            headers=auth_headers
        )
        assert start_response.status_code == 200
        
        # Verify RDP server shows active session
        rdp_sessions_response = rdp_client.get(
            f"/api/v1/rdp/servers/{server_id}/sessions",
            headers=auth_headers
        )
        assert rdp_sessions_response.status_code == 200
        rdp_sessions = rdp_sessions_response.json()
        
        assert len(rdp_sessions["active_sessions"]) > 0
        assert rdp_sessions["active_sessions"][0]["session_id"] == session_id
        
        # Stop session
        session_client.post(
            f"/api/v1/sessions/{session_id}/stop",
            headers=auth_headers
        )
        
        # Verify RDP server shows no active sessions
        rdp_sessions_response = rdp_client.get(
            f"/api/v1/rdp/servers/{server_id}/sessions",
            headers=auth_headers
        )
        assert rdp_sessions_response.status_code == 200
        rdp_sessions = rdp_sessions_response.json()
        assert len(rdp_sessions["active_sessions"]) == 0
        
        # Cleanup
        rdp_client.post(
            f"/api/v1/rdp/servers/{server_id}/stop",
            headers=auth_headers
        )
        rdp_client.delete(
            f"/api/v1/rdp/servers/{server_id}",
            headers=auth_headers
        )
    
    @pytest.mark.asyncio
    async def test_rdp_server_concurrent_creation(
        self,
        rdp_client,
        auth_headers,
        sample_rdp_server_data,
        test_db
    ):
        """Test concurrent RDP server creation."""
        
        # Create multiple RDP servers concurrently
        create_tasks = []
        for i in range(10):
            server_data = sample_rdp_server_data.copy()
            server_data["name"] = f"Concurrent Server {i}"
            
            task = asyncio.create_task(
                self._create_rdp_server_async(rdp_client, server_data, auth_headers)
            )
            create_tasks.append(task)
        
        create_results = await asyncio.gather(*create_tasks)
        
        # Verify all servers were created successfully
        server_ids = []
        for result in create_results:
            assert result["status_code"] == 201
            server_ids.append(result["server_id"])
        
        # Verify all servers have unique ports
        ports = []
        for server_id in server_ids:
            get_response = rdp_client.get(
                f"/api/v1/rdp/servers/{server_id}",
                headers=auth_headers
            )
            assert get_response.status_code == 200
            server = get_response.json()
            ports.append(server["port"])
        
        assert len(set(ports)) == len(ports)  # All ports are unique
        
        # Start all servers concurrently
        start_tasks = []
        for server_id in server_ids:
            task = asyncio.create_task(
                self._start_rdp_server_async(rdp_client, server_id, auth_headers)
            )
            start_tasks.append(task)
        
        start_results = await asyncio.gather(*start_tasks)
        
        # Verify all servers started successfully
        for result in start_results:
            assert result["status_code"] == 200
            assert result["status"] == "running"
        
        # Cleanup all servers
        cleanup_tasks = []
        for server_id in server_ids:
            task = asyncio.create_task(
                self._cleanup_rdp_server_async(rdp_client, server_id, auth_headers)
            )
            cleanup_tasks.append(task)
        
        await asyncio.gather(*cleanup_tasks)
    
    @pytest.mark.asyncio
    async def test_rdp_server_configuration_management(
        self,
        rdp_client,
        auth_headers,
        sample_rdp_server_data,
        test_db
    ):
        """Test RDP server configuration management."""
        
        # Create RDP server
        create_response = rdp_client.post(
            "/api/v1/rdp/servers",
            json=sample_rdp_server_data,
            headers=auth_headers
        )
        assert create_response.status_code == 201
        server_id = create_response.json()["server_id"]
        
        # Get current configuration
        config_response = rdp_client.get(
            f"/api/v1/rdp/servers/{server_id}/configuration",
            headers=auth_headers
        )
        assert config_response.status_code == 200
        config = config_response.json()
        
        assert config["desktop_environment"] == sample_rdp_server_data["configuration"]["desktop_environment"]
        assert config["resolution"] == sample_rdp_server_data["configuration"]["resolution"]
        assert config["color_depth"] == sample_rdp_server_data["configuration"]["color_depth"]
        
        # Update configuration
        updated_config = {
            "desktop_environment": "gnome",
            "resolution": "2560x1440",
            "color_depth": 32,
            "use_tls": True
        }
        
        update_response = rdp_client.put(
            f"/api/v1/rdp/servers/{server_id}/configuration",
            json=updated_config,
            headers=auth_headers
        )
        assert update_response.status_code == 200
        
        # Verify updated configuration
        updated_config_response = rdp_client.get(
            f"/api/v1/rdp/servers/{server_id}/configuration",
            headers=auth_headers
        )
        assert updated_config_response.status_code == 200
        updated_config_result = updated_config_response.json()
        
        assert updated_config_result["desktop_environment"] == "gnome"
        assert updated_config_result["resolution"] == "2560x1440"
        assert updated_config_result["color_depth"] == 32
        assert updated_config_result["use_tls"] is True
        
        # Test configuration validation
        invalid_config = {
            "desktop_environment": "invalid_desktop",
            "resolution": "invalid_resolution",
            "color_depth": 999
        }
        
        invalid_response = rdp_client.put(
            f"/api/v1/rdp/servers/{server_id}/configuration",
            json=invalid_config,
            headers=auth_headers
        )
        assert invalid_response.status_code == 400
        
        # Cleanup
        rdp_client.delete(
            f"/api/v1/rdp/servers/{server_id}",
            headers=auth_headers
        )
    
    @pytest.mark.asyncio
    async def test_rdp_server_error_handling(
        self,
        rdp_client,
        auth_headers,
        test_db
    ):
        """Test RDP server error handling."""
        
        # Test creating server with invalid data
        invalid_server_data = {
            "name": "",  # Empty name
            "user_id": "invalid_user",
            "configuration": {
                "desktop_environment": "invalid_desktop",
                "resolution": "invalid_resolution"
            },
            "resources": {
                "cpu_limit": -1,  # Invalid CPU limit
                "memory_limit": 0,  # Invalid memory limit
                "disk_limit": -100  # Invalid disk limit
            }
        }
        
        invalid_response = rdp_client.post(
            "/api/v1/rdp/servers",
            json=invalid_server_data,
            headers=auth_headers
        )
        assert invalid_response.status_code == 400
        
        # Test accessing non-existent server
        non_existent_response = rdp_client.get(
            "/api/v1/rdp/servers/non-existent-server",
            headers=auth_headers
        )
        assert non_existent_response.status_code == 404
        
        # Test starting non-existent server
        start_invalid_response = rdp_client.post(
            "/api/v1/rdp/servers/non-existent-server/start",
            headers=auth_headers
        )
        assert start_invalid_response.status_code == 404
    
    async def _create_rdp_server_async(
        self,
        client,
        server_data: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Helper method to create RDP server asynchronously."""
        response = client.post(
            "/api/v1/rdp/servers",
            json=server_data,
            headers=headers
        )
        return {
            "status_code": response.status_code,
            "server_id": response.json().get("server_id") if response.status_code == 201 else None
        }
    
    async def _start_rdp_server_async(
        self,
        client,
        server_id: str,
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Helper method to start RDP server asynchronously."""
        response = client.post(
            f"/api/v1/rdp/servers/{server_id}/start",
            headers=headers
        )
        return {
            "status_code": response.status_code,
            "status": response.json().get("status") if response.status_code == 200 else None
        }
    
    async def _cleanup_rdp_server_async(
        self,
        client,
        server_id: str,
        headers: Dict[str, str]
    ) -> None:
        """Helper method to cleanup RDP server asynchronously."""
        # Stop server
        client.post(
            f"/api/v1/rdp/servers/{server_id}/stop",
            headers=headers
        )
        # Delete server
        client.delete(
            f"/api/v1/rdp/servers/{server_id}",
            headers=headers
        )
