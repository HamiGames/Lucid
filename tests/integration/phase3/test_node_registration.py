"""
Phase 3 Integration Tests - Node Registration and Pool Assignment

This module tests node registration and pool assignment:
1. Node registration with hardware validation
2. Pool assignment and management
3. PoOT score calculation
4. Payout processing
5. Resource monitoring integration

Tests validate the complete node lifecycle and integration
with session management and RDP services.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List

@pytest.mark.phase3_integration
@pytest.mark.node_registration
class TestNodeRegistration:
    """Test node registration and pool assignment."""
    
    @pytest.mark.asyncio
    async def test_node_registration_and_pool_assignment(
        self,
        node_client,
        auth_headers,
        sample_node_data,
        test_db,
        integration_test_config
    ):
        """Test complete node registration and pool assignment workflow."""
        
        # Step 1: Register Node
        register_response = node_client.post(
            "/api/v1/nodes",
            json=sample_node_data,
            headers=auth_headers
        )
        assert register_response.status_code == 201
        node = register_response.json()
        node_id = node["node_id"]
        
        # Verify node registration
        assert node["name"] == sample_node_data["name"]
        assert node["node_type"] == sample_node_data["node_type"]
        assert node["status"] == "inactive"
        assert node["pool_id"] == sample_node_data["initial_pool_id"]
        assert node["hardware_info"]["cpu"]["cores"] == sample_node_data["hardware_info"]["cpu"]["cores"]
        
        # Step 2: Start Node
        start_response = node_client.post(
            f"/api/v1/nodes/{node_id}/start",
            headers=auth_headers
        )
        assert start_response.status_code == 200
        start_result = start_response.json()
        assert start_result["status"] == "active"
        assert "started_at" in start_result
        
        # Step 3: Verify Pool Assignment
        pool_response = node_client.get(
            f"/api/v1/nodes/{node_id}/pool",
            headers=auth_headers
        )
        assert pool_response.status_code == 200
        pool = pool_response.json()
        assert pool["pool_id"] == sample_node_data["initial_pool_id"]
        assert pool["node_count"] >= 1
        
        # Step 4: Verify Node Heartbeat
        heartbeat_response = node_client.post(
            f"/api/v1/nodes/{node_id}/heartbeat",
            json={"timestamp": datetime.utcnow().isoformat()},
            headers=auth_headers
        )
        assert heartbeat_response.status_code == 200
        heartbeat_result = heartbeat_response.json()
        assert heartbeat_result["status"] == "active"
        assert "last_heartbeat" in heartbeat_result
        
        # Step 5: Get Node Status
        status_response = node_client.get(
            f"/api/v1/nodes/{node_id}",
            headers=auth_headers
        )
        assert status_response.status_code == 200
        status = status_response.json()
        assert status["status"] == "active"
        assert status["last_heartbeat"] is not None
        
        # Step 6: Stop Node
        stop_response = node_client.post(
            f"/api/v1/nodes/{node_id}/stop",
            headers=auth_headers
        )
        assert stop_response.status_code == 200
        stop_result = stop_response.json()
        assert stop_result["status"] == "inactive"
        assert "stopped_at" in stop_result
        
        # Step 7: Delete Node
        delete_response = node_client.delete(
            f"/api/v1/nodes/{node_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 204
    
    @pytest.mark.asyncio
    async def test_node_pool_management(
        self,
        node_client,
        auth_headers,
        sample_node_data,
        test_db
    ):
        """Test node pool management and assignment."""
        
        # Create multiple nodes in different pools
        nodes = []
        pools = ["pool_workers", "pool_storage", "pool_compute"]
        
        for i, pool_id in enumerate(pools):
            node_data = sample_node_data.copy()
            node_data["name"] = f"Pool Test Node {i}"
            node_data["initial_pool_id"] = pool_id
            
            register_response = node_client.post(
                "/api/v1/nodes",
                json=node_data,
                headers=auth_headers
            )
            assert register_response.status_code == 201
            node = register_response.json()
            nodes.append(node["node_id"])
        
        # Start all nodes
        for node_id in nodes:
            start_response = node_client.post(
                f"/api/v1/nodes/{node_id}/start",
                headers=auth_headers
            )
            assert start_response.status_code == 200
        
        # List nodes by pool
        for pool_id in pools:
            pool_nodes_response = node_client.get(
                f"/api/v1/nodes?pool_id={pool_id}",
                headers=auth_headers
            )
            assert pool_nodes_response.status_code == 200
            pool_nodes = pool_nodes_response.json()
            assert len(pool_nodes["nodes"]) >= 1
        
        # Test pool reassignment
        node_id = nodes[0]
        reassign_response = node_client.put(
            f"/api/v1/nodes/{node_id}/pool",
            json={"pool_id": "pool_compute"},
            headers=auth_headers
        )
        assert reassign_response.status_code == 200
        
        # Verify reassignment
        node_response = node_client.get(
            f"/api/v1/nodes/{node_id}",
            headers=auth_headers
        )
        assert node_response.status_code == 200
        node = node_response.json()
        assert node["pool_id"] == "pool_compute"
        
        # Cleanup
        for node_id in nodes:
            node_client.post(
                f"/api/v1/nodes/{node_id}/stop",
                headers=auth_headers
            )
            node_client.delete(
                f"/api/v1/nodes/{node_id}",
                headers=auth_headers
            )
    
    @pytest.mark.asyncio
    async def test_node_resource_monitoring(
        self,
        node_client,
        auth_headers,
        sample_node_data,
        test_db,
        integration_test_config
    ):
        """Test node resource monitoring and metrics collection."""
        
        # Register and start node
        register_response = node_client.post(
            "/api/v1/nodes",
            json=sample_node_data,
            headers=auth_headers
        )
        assert register_response.status_code == 201
        node_id = register_response.json()["node_id"]
        
        start_response = node_client.post(
            f"/api/v1/nodes/{node_id}/start",
            headers=auth_headers
        )
        assert start_response.status_code == 200
        
        # Wait for resource monitoring to collect data
        await asyncio.sleep(2)
        
        # Get resource usage
        usage_response = node_client.get(
            f"/api/v1/nodes/{node_id}/usage",
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
        
        # Verify resource limits
        assert usage["cpu_percent"] <= 100
        assert usage["memory_percent"] <= 100
        assert usage["disk_percent"] <= 100
        
        # Get resource history
        history_response = node_client.get(
            f"/api/v1/nodes/{node_id}/usage/history?duration=1h",
            headers=auth_headers
        )
        assert history_response.status_code == 200
        history = history_response.json()
        
        assert "usage_history" in history
        assert len(history["usage_history"]) > 0
        
        # Test resource alerts
        alerts_response = node_client.get(
            f"/api/v1/nodes/{node_id}/alerts",
            headers=auth_headers
        )
        assert alerts_response.status_code == 200
        alerts = alerts_response.json()
        
        assert "active_alerts" in alerts
        assert "alert_history" in alerts
        
        # Cleanup
        node_client.post(
            f"/api/v1/nodes/{node_id}/stop",
            headers=auth_headers
        )
        node_client.delete(
            f"/api/v1/nodes/{node_id}",
            headers=auth_headers
        )
    
    @pytest.mark.asyncio
    async def test_node_concurrent_registration(
        self,
        node_client,
        auth_headers,
        sample_node_data,
        test_db
    ):
        """Test concurrent node registration."""
        
        # Register multiple nodes concurrently
        register_tasks = []
        for i in range(10):
            node_data = sample_node_data.copy()
            node_data["name"] = f"Concurrent Node {i}"
            
            task = asyncio.create_task(
                self._register_node_async(node_client, node_data, auth_headers)
            )
            register_tasks.append(task)
        
        register_results = await asyncio.gather(*register_tasks)
        
        # Verify all nodes were registered successfully
        node_ids = []
        for result in register_results:
            assert result["status_code"] == 201
            node_ids.append(result["node_id"])
        
        # Start all nodes concurrently
        start_tasks = []
        for node_id in node_ids:
            task = asyncio.create_task(
                self._start_node_async(node_client, node_id, auth_headers)
            )
            start_tasks.append(task)
        
        start_results = await asyncio.gather(*start_tasks)
        
        # Verify all nodes started successfully
        for result in start_results:
            assert result["status_code"] == 200
            assert result["status"] == "active"
        
        # Test concurrent heartbeat
        heartbeat_tasks = []
        for node_id in node_ids:
            task = asyncio.create_task(
                self._send_heartbeat_async(node_client, node_id, auth_headers)
            )
            heartbeat_tasks.append(task)
        
        heartbeat_results = await asyncio.gather(*heartbeat_tasks)
        
        # Verify all heartbeats were successful
        for result in heartbeat_results:
            assert result["status_code"] == 200
            assert result["status"] == "active"
        
        # Cleanup all nodes
        cleanup_tasks = []
        for node_id in node_ids:
            task = asyncio.create_task(
                self._cleanup_node_async(node_client, node_id, auth_headers)
            )
            cleanup_tasks.append(task)
        
        await asyncio.gather(*cleanup_tasks)
    
    @pytest.mark.asyncio
    async def test_node_hardware_validation(
        self,
        node_client,
        auth_headers,
        test_db
    ):
        """Test node hardware validation during registration."""
        
        # Test valid hardware info
        valid_node_data = {
            "name": "Valid Hardware Node",
            "node_type": "worker",
            "hardware_info": {
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
                }
            },
            "location": {
                "country": "US",
                "region": "CA"
            },
            "initial_pool_id": "pool_workers"
        }
        
        valid_response = node_client.post(
            "/api/v1/nodes",
            json=valid_node_data,
            headers=auth_headers
        )
        assert valid_response.status_code == 201
        
        # Test invalid hardware info
        invalid_node_data = {
            "name": "Invalid Hardware Node",
            "node_type": "worker",
            "hardware_info": {
                "cpu": {
                    "cores": -1,  # Invalid cores
                    "frequency_mhz": 0,  # Invalid frequency
                    "architecture": "invalid_arch"
                },
                "memory": {
                    "total_bytes": 0,  # Invalid memory
                    "type": "invalid_type"
                },
                "storage": {
                    "total_bytes": -1000,  # Invalid storage
                    "type": "invalid_type",
                    "interface": "invalid_interface"
                }
            },
            "location": {
                "country": "US",
                "region": "CA"
            },
            "initial_pool_id": "pool_workers"
        }
        
        invalid_response = node_client.post(
            "/api/v1/nodes",
            json=invalid_node_data,
            headers=auth_headers
        )
        assert invalid_response.status_code == 400
        
        # Cleanup valid node
        node_id = valid_response.json()["node_id"]
        node_client.delete(
            f"/api/v1/nodes/{node_id}",
            headers=auth_headers
        )
    
    @pytest.mark.asyncio
    async def test_node_error_handling(
        self,
        node_client,
        auth_headers,
        test_db
    ):
        """Test node error handling and edge cases."""
        
        # Test accessing non-existent node
        non_existent_response = node_client.get(
            "/api/v1/nodes/non-existent-node",
            headers=auth_headers
        )
        assert non_existent_response.status_code == 404
        
        # Test starting non-existent node
        start_invalid_response = node_client.post(
            "/api/v1/nodes/non-existent-node/start",
            headers=auth_headers
        )
        assert start_invalid_response.status_code == 404
        
        # Test invalid node data
        invalid_node_data = {
            "name": "",  # Empty name
            "node_type": "invalid_type",
            "hardware_info": {},  # Empty hardware info
            "location": {},  # Empty location
            "initial_pool_id": "invalid_pool"
        }
        
        invalid_response = node_client.post(
            "/api/v1/nodes",
            json=invalid_node_data,
            headers=auth_headers
        )
        assert invalid_response.status_code == 400
        
        # Test invalid heartbeat
        heartbeat_invalid_response = node_client.post(
            "/api/v1/nodes/non-existent-node/heartbeat",
            json={"timestamp": "invalid_timestamp"},
            headers=auth_headers
        )
        assert heartbeat_invalid_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_node_pool_statistics(
        self,
        node_client,
        auth_headers,
        sample_node_data,
        test_db
    ):
        """Test node pool statistics and reporting."""
        
        # Create nodes in different pools
        nodes = []
        pools = ["pool_workers", "pool_storage", "pool_compute"]
        
        for i, pool_id in enumerate(pools):
            node_data = sample_node_data.copy()
            node_data["name"] = f"Stats Test Node {i}"
            node_data["initial_pool_id"] = pool_id
            
            register_response = node_client.post(
                "/api/v1/nodes",
                json=node_data,
                headers=auth_headers
            )
            assert register_response.status_code == 201
            node_id = register_response.json()["node_id"]
            nodes.append(node_id)
            
            # Start node
            node_client.post(
                f"/api/v1/nodes/{node_id}/start",
                headers=auth_headers
            )
        
        # Get pool statistics
        for pool_id in pools:
            stats_response = node_client.get(
                f"/api/v1/nodes/pools/{pool_id}/statistics",
                headers=auth_headers
            )
            assert stats_response.status_code == 200
            stats = stats_response.json()
            
            assert "total_nodes" in stats
            assert "active_nodes" in stats
            assert "inactive_nodes" in stats
            assert "total_cpu_cores" in stats
            assert "total_memory_bytes" in stats
            assert "total_storage_bytes" in stats
            assert stats["total_nodes"] >= 1
            assert stats["active_nodes"] >= 1
        
        # Get overall statistics
        overall_stats_response = node_client.get(
            "/api/v1/nodes/statistics",
            headers=auth_headers
        )
        assert overall_stats_response.status_code == 200
        overall_stats = overall_stats_response.json()
        
        assert "total_nodes" in overall_stats
        assert "active_nodes" in overall_stats
        assert "total_pools" in overall_stats
        assert "total_cpu_cores" in overall_stats
        assert "total_memory_bytes" in overall_stats
        assert "total_storage_bytes" in overall_stats
        
        # Cleanup
        for node_id in nodes:
            node_client.post(
                f"/api/v1/nodes/{node_id}/stop",
                headers=auth_headers
            )
            node_client.delete(
                f"/api/v1/nodes/{node_id}",
                headers=auth_headers
            )
    
    async def _register_node_async(
        self,
        client,
        node_data: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Helper method to register node asynchronously."""
        response = client.post(
            "/api/v1/nodes",
            json=node_data,
            headers=headers
        )
        return {
            "status_code": response.status_code,
            "node_id": response.json().get("node_id") if response.status_code == 201 else None
        }
    
    async def _start_node_async(
        self,
        client,
        node_id: str,
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Helper method to start node asynchronously."""
        response = client.post(
            f"/api/v1/nodes/{node_id}/start",
            headers=headers
        )
        return {
            "status_code": response.status_code,
            "status": response.json().get("status") if response.status_code == 200 else None
        }
    
    async def _send_heartbeat_async(
        self,
        client,
        node_id: str,
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Helper method to send heartbeat asynchronously."""
        response = client.post(
            f"/api/v1/nodes/{node_id}/heartbeat",
            json={"timestamp": datetime.utcnow().isoformat()},
            headers=headers
        )
        return {
            "status_code": response.status_code,
            "status": response.json().get("status") if response.status_code == 200 else None
        }
    
    async def _cleanup_node_async(
        self,
        client,
        node_id: str,
        headers: Dict[str, str]
    ) -> None:
        """Helper method to cleanup node asynchronously."""
        # Stop node
        client.post(
            f"/api/v1/nodes/{node_id}/stop",
            headers=headers
        )
        # Delete node
        client.delete(
            f"/api/v1/nodes/{node_id}",
            headers=headers
        )
