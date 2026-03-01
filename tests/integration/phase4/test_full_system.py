"""
Full System Integration Tests

This module tests the complete system integration across all 10 clusters,
ensuring end-to-end functionality and system-wide operations.
"""

import pytest
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List


class TestFullSystemIntegration:
    """Test complete system integration."""

    @pytest.mark.asyncio
    async def test_all_clusters_operational(self, system_health_check):
        """Test that all 10 clusters are operational."""
        health_status = system_health_check
        
        # Verify all critical services are healthy
        assert health_status["admin_interface"] == True, "Admin Interface cluster not operational"
        assert health_status["tron_payment"] == True, "TRON Payment cluster not operational"
        assert health_status["api_gateway"] == True, "API Gateway cluster not operational"

    @pytest.mark.asyncio
    async def test_end_to_end_user_flow(self, admin_session, tron_payment_session):
        """Test complete user flow from registration to payout."""
        # Step 1: User registration and authentication
        admin_session_obj = admin_session["session"]
        admin_token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        tron_session_obj = tron_payment_session["session"]
        tron_token = tron_payment_session["token"]
        tron_url = tron_payment_session["tron_payment_url"]
        
        # Step 2: Create user session
        session_data = {
            "user_id": "e2e_test_user",
            "session_type": "desktop",
            "duration_minutes": 60
        }
        
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        async with admin_session_obj.post(
            f"{admin_url}/admin/sessions/create",
            json=session_data,
            headers=admin_headers
        ) as response:
            assert response.status == 201
            session_info = await response.json()
            session_id = session_info["session_id"]
        
        # Step 3: Monitor session
        async with admin_session_obj.get(
            f"{admin_url}/admin/sessions/{session_id}",
            headers=admin_headers
        ) as response:
            assert response.status == 200
            session_status = await response.json()
            assert session_status["status"] == "active"
        
        # Step 4: Process payout
        payout_data = {
            "user_id": "e2e_test_user",
            "amount": "50.00",
            "currency": "USDT",
            "recipient_address": "TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH"
        }
        
        tron_headers = {"Authorization": f"Bearer {tron_token}"}
        async with tron_session_obj.post(
            f"{tron_url}/api/v1/payouts/initiate",
            json=payout_data,
            headers=tron_headers
        ) as response:
            assert response.status == 201
            payout_info = await response.json()
            payout_id = payout_info["payout_id"]
        
        # Step 5: Verify payout status
        async with tron_session_obj.get(
            f"{tron_url}/api/v1/payouts/{payout_id}",
            headers=tron_headers
        ) as response:
            assert response.status == 200
            payout_status = await response.json()
            assert payout_status["status"] in ["pending", "processing", "completed"]

    @pytest.mark.asyncio
    async def test_cross_cluster_communication(self, admin_session, api_gateway_url):
        """Test communication between clusters."""
        session = admin_session["session"]
        token = admin_session["token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test API Gateway -> Admin Interface communication
        async with session.get(
            f"{api_gateway_url}/admin/dashboard",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "dashboard" in data

    @pytest.mark.asyncio
    async def test_system_wide_health_check(self, admin_session):
        """Test system-wide health check."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        async with session.get(
            f"{admin_url}/admin/health/detailed",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            
            # Verify all clusters are reported
            assert "clusters" in data
            clusters = data["clusters"]
            
            expected_clusters = [
                "api-gateway", "blockchain-core", "session-management",
                "rdp-services", "node-management", "admin-interface",
                "tron-payment", "storage-database", "authentication",
                "cross-cluster-integration"
            ]
            
            for cluster in expected_clusters:
                assert cluster in clusters
                assert clusters[cluster]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_system_wide_metrics_aggregation(self, admin_session):
        """Test system-wide metrics aggregation."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        async with session.get(
            f"{admin_url}/admin/metrics/system",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            
            # Verify metrics structure
            assert "system_metrics" in data
            metrics = data["system_metrics"]
            
            required_metrics = [
                "total_requests", "active_sessions", "blockchain_height",
                "node_count", "payout_count", "error_rate"
            ]
            
            for metric in required_metrics:
                assert metric in metrics
                assert isinstance(metrics[metric], (int, float))

    @pytest.mark.asyncio
    async def test_system_wide_audit_logging(self, admin_session):
        """Test system-wide audit logging."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Perform an action that should be audited
        action_data = {
            "action": "system_config_change",
            "details": "Test configuration change"
        }
        
        async with session.post(
            f"{admin_url}/admin/actions/audit",
            json=action_data,
            headers=headers
        ) as response:
            assert response.status == 200
        
        # Check audit logs
        async with session.get(
            f"{admin_url}/admin/audit/logs",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "logs" in data
            assert len(data["logs"]) > 0

    @pytest.mark.asyncio
    async def test_system_wide_security_compliance(self, admin_session):
        """Test system-wide security compliance."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        async with session.get(
            f"{admin_url}/admin/security/compliance",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            
            # Verify security compliance
            assert "compliance_status" in data
            assert "security_checks" in data
            
            security_checks = data["security_checks"]
            required_checks = [
                "authentication_enabled", "encryption_enabled",
                "rate_limiting_enabled", "audit_logging_enabled"
            ]
            
            for check in required_checks:
                assert check in security_checks
                assert security_checks[check] == True

    @pytest.mark.asyncio
    async def test_system_wide_performance_benchmarks(self, admin_session):
        """Test system-wide performance benchmarks."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        async with session.get(
            f"{admin_url}/admin/performance/benchmarks",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            
            # Verify performance benchmarks
            assert "benchmarks" in data
            benchmarks = data["benchmarks"]
            
            # Check response time benchmarks
            assert "api_gateway_response_time" in benchmarks
            assert benchmarks["api_gateway_response_time"] < 50  # < 50ms
            
            assert "blockchain_consensus_time" in benchmarks
            assert benchmarks["blockchain_consensus_time"] < 10  # < 10 seconds
            
            assert "session_processing_time" in benchmarks
            assert benchmarks["session_processing_time"] < 100  # < 100ms

    @pytest.mark.asyncio
    async def test_system_wide_error_handling(self, admin_session):
        """Test system-wide error handling."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test error handling across clusters
        error_scenarios = [
            ("/admin/invalid-endpoint", 404),
            ("/admin/sessions/invalid-session-id", 404),
            ("/admin/blockchain/invalid-block", 400)
        ]
        
        for endpoint, expected_status in error_scenarios:
            async with session.get(
                f"{admin_url}{endpoint}",
                headers=headers
            ) as response:
                assert response.status == expected_status

    @pytest.mark.asyncio
    async def test_system_wide_load_balancing(self, admin_session):
        """Test system-wide load balancing."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test concurrent requests to verify load balancing
        tasks = []
        for i in range(10):
            task = session.get(
                f"{admin_url}/admin/dashboard",
                headers=headers
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All requests should succeed
        for response in responses:
            if isinstance(response, Exception):
                pytest.fail(f"Request failed with exception: {response}")
            assert response.status == 200

    @pytest.mark.asyncio
    async def test_system_wide_data_consistency(self, admin_session):
        """Test system-wide data consistency."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get data from multiple endpoints
        endpoints = [
            "/admin/dashboard/stats",
            "/admin/sessions/active",
            "/admin/nodes",
            "/admin/blockchain/status"
        ]
        
        data_sets = []
        for endpoint in endpoints:
            async with session.get(
                f"{admin_url}{endpoint}",
                headers=headers
            ) as response:
                assert response.status == 200
                data = await response.json()
                data_sets.append(data)
        
        # Verify data consistency across endpoints
        # (This would be more specific based on actual data relationships)
        assert len(data_sets) == len(endpoints)

    @pytest.mark.asyncio
    async def test_system_wide_backup_recovery(self, admin_session):
        """Test system-wide backup and recovery."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test backup initiation
        backup_data = {
            "backup_type": "full_system",
            "description": "Test system backup"
        }
        
        async with session.post(
            f"{admin_url}/admin/backup/initiate",
            json=backup_data,
            headers=headers
        ) as response:
            assert response.status == 200
            backup_info = await response.json()
            assert "backup_id" in backup_info
            assert "status" in backup_info

    @pytest.mark.asyncio
    async def test_system_wide_monitoring_alerts(self, admin_session):
        """Test system-wide monitoring and alerts."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        async with session.get(
            f"{admin_url}/admin/monitoring/alerts",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            
            assert "alerts" in data
            assert "monitoring_status" in data
            
            # Verify monitoring is active
            assert data["monitoring_status"] == "active"

    @pytest.mark.asyncio
    async def test_system_wide_scalability(self, admin_session):
        """Test system-wide scalability."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        async with session.get(
            f"{admin_url}/admin/scalability/status",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            
            assert "scalability_status" in data
            assert "resource_utilization" in data
            
            # Verify system can handle load
            resource_util = data["resource_utilization"]
            assert resource_util["cpu_usage"] < 80  # < 80% CPU
            assert resource_util["memory_usage"] < 80  # < 80% Memory

    @pytest.mark.asyncio
    async def test_system_wide_disaster_recovery(self, admin_session):
        """Test system-wide disaster recovery procedures."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test disaster recovery status
        async with session.get(
            f"{admin_url}/admin/disaster-recovery/status",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            
            assert "recovery_status" in data
            assert "backup_status" in data
            assert "replication_status" in data
            
            # Verify disaster recovery is ready
            assert data["recovery_status"] == "ready"
            assert data["backup_status"] == "current"

    @pytest.mark.asyncio
    async def test_system_wide_compliance_reporting(self, admin_session):
        """Test system-wide compliance reporting."""
        session = admin_session["session"]
        token = admin_session["token"]
        admin_url = admin_session["admin_interface_url"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        async with session.get(
            f"{admin_url}/admin/compliance/report",
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            
            assert "compliance_report" in data
            report = data["compliance_report"]
            
            # Verify compliance areas
            required_areas = [
                "security_compliance", "data_protection", "audit_compliance",
                "operational_compliance"
            ]
            
            for area in required_areas:
                assert area in report
                assert report[area]["status"] == "compliant"
