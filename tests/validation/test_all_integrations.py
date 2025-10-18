"""
Test All Integrations

Validates that all integrations between the 10 Lucid clusters are working correctly.
Tests cross-cluster communication, data flow, and integration points.

Integration Points Tested:
- API Gateway → Authentication → Database
- API Gateway → Blockchain Core → Database
- Session Management → Blockchain Anchoring
- Node Management → TRON Payment (isolated)
- Admin Interface → All Clusters
- Cross-Cluster Service Mesh → All Services
"""

import asyncio
import aiohttp
import pytest
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class IntegrationTest:
    """Integration test configuration"""
    name: str
    description: str
    test_type: str  # "auth_flow", "data_flow", "service_mesh", "cross_cluster"
    steps: List[Dict[str, Any]]
    expected_result: Any
    timeout: int = 60


@dataclass
class IntegrationResult:
    """Integration test result"""
    test_name: str
    is_successful: bool
    execution_time_ms: float
    steps_completed: int
    total_steps: int
    error_message: Optional[str] = None
    step_results: List[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.step_results is None:
            self.step_results = []


class IntegrationValidator:
    """Validates integrations between Lucid clusters"""
    
    def __init__(self, auth_token: Optional[str] = None):
        self.auth_token = auth_token
        self.tests = self._initialize_integration_tests()
        self.session: Optional[aiohttp.ClientSession] = None
    
    def _initialize_integration_tests(self) -> List[IntegrationTest]:
        """Initialize all integration tests"""
        tests = []
        
        # Test 1: Authentication Flow Integration
        tests.append(IntegrationTest(
            name="auth_flow_integration",
            description="Test complete authentication flow through API Gateway → Auth → Database",
            test_type="auth_flow",
            steps=[
                {
                    "step": 1,
                    "action": "login_request",
                    "method": "POST",
                    "url": "http://localhost:8080/api/v1/auth/login",
                    "data": {
                        "username": "test_user",
                        "password": "test_password",
                        "tron_signature": "test_signature"
                    },
                    "expected_status": 200
                },
                {
                    "step": 2,
                    "action": "verify_token",
                    "method": "POST",
                    "url": "http://localhost:8080/api/v1/auth/verify",
                    "headers": {"Authorization": "Bearer {token}"},
                    "expected_status": 200
                },
                {
                    "step": 3,
                    "action": "access_protected_endpoint",
                    "method": "GET",
                    "url": "http://localhost:8080/api/v1/users",
                    "headers": {"Authorization": "Bearer {token}"},
                    "expected_status": 200
                }
            ],
            expected_result={"auth_flow_complete": True, "token_valid": True}
        ))
        
        # Test 2: Session Management → Blockchain Integration
        tests.append(IntegrationTest(
            name="session_blockchain_integration",
            description="Test session anchoring to blockchain",
            test_type="data_flow",
            steps=[
                {
                    "step": 1,
                    "action": "create_session",
                    "method": "POST",
                    "url": "http://localhost:8083/api/v1/sessions",
                    "data": {
                        "user_id": "test_user",
                        "session_type": "rdp",
                        "metadata": {"test": True}
                    },
                    "expected_status": 201
                },
                {
                    "step": 2,
                    "action": "anchor_session",
                    "method": "POST",
                    "url": "http://localhost:8085/api/v1/anchoring/session",
                    "data": {"session_id": "{session_id}"},
                    "expected_status": 200
                },
                {
                    "step": 3,
                    "action": "verify_anchoring",
                    "method": "GET",
                    "url": "http://localhost:8085/api/v1/anchoring/session/{session_id}",
                    "expected_status": 200
                }
            ],
            expected_result={"session_anchored": True, "blockchain_confirmed": True}
        ))
        
        # Test 3: Node Management → TRON Payment Integration
        tests.append(IntegrationTest(
            name="node_tron_integration",
            description="Test node payout processing through TRON payment system",
            test_type="cross_cluster",
            steps=[
                {
                    "step": 1,
                    "action": "get_node_info",
                    "method": "GET",
                    "url": "http://localhost:8095/api/v1/nodes",
                    "expected_status": 200
                },
                {
                    "step": 2,
                    "action": "calculate_payout",
                    "method": "POST",
                    "url": "http://localhost:8095/api/v1/payouts/calculate",
                    "data": {"node_id": "test_node", "period": "daily"},
                    "expected_status": 200
                },
                {
                    "step": 3,
                    "action": "submit_payout",
                    "method": "POST",
                    "url": "http://localhost:8085/api/v1/payouts/submit",
                    "data": {"node_id": "test_node", "amount": 100, "currency": "USDT"},
                    "expected_status": 200
                }
            ],
            expected_result={"payout_submitted": True, "tron_processing": True}
        ))
        
        # Test 4: Admin Interface → All Clusters Integration
        tests.append(IntegrationTest(
            name="admin_cluster_integration",
            description="Test admin interface access to all clusters",
            test_type="cross_cluster",
            steps=[
                {
                    "step": 1,
                    "action": "admin_dashboard",
                    "method": "GET",
                    "url": "http://localhost:8083/api/v1/dashboard",
                    "expected_status": 200
                },
                {
                    "step": 2,
                    "action": "admin_blockchain_stats",
                    "method": "GET",
                    "url": "http://localhost:8083/api/v1/admin/blockchain",
                    "expected_status": 200
                },
                {
                    "step": 3,
                    "action": "admin_session_stats",
                    "method": "GET",
                    "url": "http://localhost:8083/api/v1/admin/sessions",
                    "expected_status": 200
                },
                {
                    "step": 4,
                    "action": "admin_node_stats",
                    "method": "GET",
                    "url": "http://localhost:8083/api/v1/admin/nodes",
                    "expected_status": 200
                }
            ],
            expected_result={"admin_access": True, "all_clusters_accessible": True}
        ))
        
        # Test 5: Service Mesh Integration
        tests.append(IntegrationTest(
            name="service_mesh_integration",
            description="Test service mesh communication between all services",
            test_type="service_mesh",
            steps=[
                {
                    "step": 1,
                    "action": "consul_health",
                    "method": "GET",
                    "url": "http://localhost:8500/v1/status/leader",
                    "expected_status": 200
                },
                {
                    "step": 2,
                    "action": "service_discovery",
                    "method": "GET",
                    "url": "http://localhost:8500/v1/catalog/services",
                    "expected_status": 200
                },
                {
                    "step": 3,
                    "action": "service_health_checks",
                    "method": "GET",
                    "url": "http://localhost:8500/v1/health/service/api-gateway",
                    "expected_status": 200
                }
            ],
            expected_result={"service_mesh_operational": True, "all_services_registered": True}
        ))
        
        # Test 6: Database Integration
        tests.append(IntegrationTest(
            name="database_integration",
            description="Test database integration across all clusters",
            test_type="data_flow",
            steps=[
                {
                    "step": 1,
                    "action": "mongodb_health",
                    "method": "GET",
                    "url": "http://localhost:27017/",
                    "expected_status": 200
                },
                {
                    "step": 2,
                    "action": "redis_health",
                    "method": "GET",
                    "url": "http://localhost:6379/",
                    "expected_status": 200
                },
                {
                    "step": 3,
                    "action": "elasticsearch_health",
                    "method": "GET",
                    "url": "http://localhost:9200/_cluster/health",
                    "expected_status": 200
                },
                {
                    "step": 4,
                    "action": "database_api_health",
                    "method": "GET",
                    "url": "http://localhost:8088/health",
                    "expected_status": 200
                }
            ],
            expected_result={"all_databases_operational": True}
        ))
        
        # Test 7: RDP Service Integration
        tests.append(IntegrationTest(
            name="rdp_service_integration",
            description="Test RDP service integration with session management",
            test_type="data_flow",
            steps=[
                {
                    "step": 1,
                    "action": "rdp_server_health",
                    "method": "GET",
                    "url": "http://localhost:8090/health",
                    "expected_status": 200
                },
                {
                    "step": 2,
                    "action": "create_rdp_session",
                    "method": "POST",
                    "url": "http://localhost:8090/api/v1/servers",
                    "data": {"user_id": "test_user", "port": 13389},
                    "expected_status": 201
                },
                {
                    "step": 3,
                    "action": "monitor_rdp_session",
                    "method": "GET",
                    "url": "http://localhost:8093/api/v1/metrics",
                    "expected_status": 200
                }
            ],
            expected_result={"rdp_integration_working": True}
        ))
        
        # Test 8: Cross-Cluster Data Flow
        tests.append(IntegrationTest(
            name="cross_cluster_data_flow",
            description="Test data flow across multiple clusters",
            test_type="data_flow",
            steps=[
                {
                    "step": 1,
                    "action": "create_user",
                    "method": "POST",
                    "url": "http://localhost:8089/api/v1/users",
                    "data": {"username": "integration_test_user", "email": "test@example.com"},
                    "expected_status": 201
                },
                {
                    "step": 2,
                    "action": "create_session",
                    "method": "POST",
                    "url": "http://localhost:8083/api/v1/sessions",
                    "data": {"user_id": "{user_id}", "session_type": "test"},
                    "expected_status": 201
                },
                {
                    "step": 3,
                    "action": "anchor_to_blockchain",
                    "method": "POST",
                    "url": "http://localhost:8085/api/v1/anchoring/session",
                    "data": {"session_id": "{session_id}"},
                    "expected_status": 200
                },
                {
                    "step": 4,
                    "action": "verify_admin_access",
                    "method": "GET",
                    "url": "http://localhost:8083/api/v1/admin/sessions",
                    "expected_status": 200
                }
            ],
            expected_result={"cross_cluster_data_flow": True}
        ))
        
        return tests
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            connector=aiohttp.TCPConnector(limit=100)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def execute_integration_test(self, test: IntegrationTest) -> IntegrationResult:
        """Execute a single integration test"""
        start_time = datetime.utcnow()
        step_results = []
        steps_completed = 0
        
        try:
            # Execute each step in sequence
            for step_config in test.steps:
                step_result = await self._execute_step(step_config, step_results)
                step_results.append(step_result)
                
                if step_result["success"]:
                    steps_completed += 1
                else:
                    # Stop execution if step fails
                    break
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            is_successful = steps_completed == len(test.steps)
            
            return IntegrationResult(
                test_name=test.name,
                is_successful=is_successful,
                execution_time_ms=execution_time,
                steps_completed=steps_completed,
                total_steps=len(test.steps),
                step_results=step_results,
                timestamp=start_time
            )
        
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            return IntegrationResult(
                test_name=test.name,
                is_successful=False,
                execution_time_ms=execution_time,
                steps_completed=steps_completed,
                total_steps=len(test.steps),
                error_message=str(e),
                step_results=step_results,
                timestamp=start_time
            )
    
    async def _execute_step(self, step_config: Dict[str, Any], previous_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute a single step in an integration test"""
        try:
            # Prepare URL with variable substitution
            url = step_config["url"]
            for result in previous_results:
                if "data" in result:
                    for key, value in result["data"].items():
                        url = url.replace(f"{{{key}}}", str(value))
            
            # Prepare headers
            headers = step_config.get("headers", {})
            if self.auth_token:
                for key, value in headers.items():
                    if "{token}" in value:
                        headers[key] = value.replace("{token}", self.auth_token)
            
            # Prepare data
            data = step_config.get("data", {})
            if isinstance(data, dict):
                for result in previous_results:
                    if "data" in result:
                        for key, value in result["data"].items():
                            if f"{{{key}}}" in str(data):
                                data = json.loads(json.dumps(data).replace(f"{{{key}}}", str(value)))
            
            # Make request
            async with self.session.request(
                method=step_config["method"],
                url=url,
                headers=headers,
                json=data if isinstance(data, dict) else None,
                data=data if isinstance(data, (str, bytes)) else None
            ) as response:
                response_data = await response.read()
                
                # Check status code
                expected_status = step_config.get("expected_status", 200)
                success = response.status == expected_status
                
                step_result = {
                    "step": step_config["step"],
                    "action": step_config["action"],
                    "success": success,
                    "status_code": response.status,
                    "expected_status": expected_status,
                    "response_data": response_data.decode('utf-8') if response_data else None,
                    "url": url
                }
                
                if success and response_data:
                    try:
                        step_result["data"] = json.loads(response_data.decode('utf-8'))
                    except json.JSONDecodeError:
                        step_result["data"] = {"raw_response": response_data.decode('utf-8')}
                
                return step_result
        
        except Exception as e:
            return {
                "step": step_config["step"],
                "action": step_config["action"],
                "success": False,
                "error": str(e),
                "url": step_config["url"]
            }
    
    async def test_all_integrations(self) -> List[IntegrationResult]:
        """Test all integrations"""
        if not self.session:
            raise RuntimeError("IntegrationValidator must be used as async context manager")
        
        tasks = [self.execute_integration_test(test) for test in self.tests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and convert to IntegrationResult
        integration_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                integration_results.append(IntegrationResult(
                    test_name=self.tests[i].name,
                    is_successful=False,
                    execution_time_ms=0,
                    steps_completed=0,
                    total_steps=len(self.tests[i].steps),
                    error_message=str(result)
                ))
            else:
                integration_results.append(result)
        
        return integration_results
    
    def generate_integration_report(self, results: List[IntegrationResult]) -> Dict[str, Any]:
        """Generate comprehensive integration test report"""
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.is_successful)
        failed_tests = total_tests - successful_tests
        
        # Group by test type
        test_types = {}
        for result in results:
            test_type = next(t.test_type for t in self.tests if t.name == result.test_name)
            if test_type not in test_types:
                test_types[test_type] = {"total": 0, "successful": 0}
            test_types[test_type]["total"] += 1
            if result.is_successful:
                test_types[test_type]["successful"] += 1
        
        # Calculate success rates
        for test_type in test_types:
            total = test_types[test_type]["total"]
            successful = test_types[test_type]["successful"]
            test_types[test_type]["success_rate"] = (successful / total) * 100
        
        # Calculate average execution time
        avg_execution_time = 0
        if results:
            avg_execution_time = sum(r.execution_time_ms for r in results) / len(results)
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate_percentage": (successful_tests / total_tests) * 100,
                "average_execution_time_ms": round(avg_execution_time, 2)
            },
            "test_type_breakdown": test_types,
            "successful_tests": [
                {
                    "name": r.test_name,
                    "execution_time_ms": round(r.execution_time_ms, 2),
                    "steps_completed": r.steps_completed,
                    "total_steps": r.total_steps
                }
                for r in results if r.is_successful
            ],
            "failed_tests": [
                {
                    "name": r.test_name,
                    "error": r.error_message,
                    "execution_time_ms": round(r.execution_time_ms, 2),
                    "steps_completed": r.steps_completed,
                    "total_steps": r.total_steps,
                    "step_results": r.step_results
                }
                for r in results if not r.is_successful
            ]
        }
        
        return report


class TestIntegration:
    """Pytest test class for integration validation"""
    
    @pytest.fixture
    async def integration_validator(self):
        """Fixture for IntegrationValidator"""
        async with IntegrationValidator() as validator:
            yield validator
    
    @pytest.mark.asyncio
    async def test_all_integrations(self, integration_validator):
        """Test that all integrations are working correctly"""
        results = await integration_validator.test_all_integrations()
        report = integration_validator.generate_integration_report(results)
        
        # Log the integration report
        logger.info(f"Integration Report: {report['summary']}")
        
        # Assert all integrations are successful
        failed_tests = [r for r in results if not r.is_successful]
        
        if failed_tests:
            failed_names = [r.test_name for r in failed_tests]
            pytest.fail(f"Failed integrations: {failed_names}")
        
        # Assert 100% success rate
        assert report["summary"]["success_rate_percentage"] == 100.0
        assert report["summary"]["failed_tests"] == 0
    
    @pytest.mark.asyncio
    async def test_auth_flow_integration(self, integration_validator):
        """Test authentication flow integration"""
        auth_test = next(t for t in integration_validator.tests if t.name == "auth_flow_integration")
        result = await integration_validator.execute_integration_test(auth_test)
        
        assert result.is_successful, f"Auth flow integration failed: {result.error_message}"
        assert result.steps_completed == result.total_steps
    
    @pytest.mark.asyncio
    async def test_session_blockchain_integration(self, integration_validator):
        """Test session to blockchain integration"""
        session_test = next(t for t in integration_validator.tests if t.name == "session_blockchain_integration")
        result = await integration_validator.execute_integration_test(session_test)
        
        assert result.is_successful, f"Session blockchain integration failed: {result.error_message}"
    
    @pytest.mark.asyncio
    async def test_service_mesh_integration(self, integration_validator):
        """Test service mesh integration"""
        mesh_test = next(t for t in integration_validator.tests if t.name == "service_mesh_integration")
        result = await integration_validator.execute_integration_test(mesh_test)
        
        assert result.is_successful, f"Service mesh integration failed: {result.error_message}"
    
    @pytest.mark.asyncio
    async def test_database_integration(self, integration_validator):
        """Test database integration"""
        db_test = next(t for t in integration_validator.tests if t.name == "database_integration")
        result = await integration_validator.execute_integration_test(db_test)
        
        assert result.is_successful, f"Database integration failed: {result.error_message}"
    
    @pytest.mark.asyncio
    async def test_cross_cluster_data_flow(self, integration_validator):
        """Test cross-cluster data flow"""
        data_flow_test = next(t for t in integration_validator.tests if t.name == "cross_cluster_data_flow")
        result = await integration_validator.execute_integration_test(data_flow_test)
        
        assert result.is_successful, f"Cross-cluster data flow failed: {result.error_message}"


if __name__ == "__main__":
    """Run integration validation standalone"""
    import json
    
    async def main():
        async with IntegrationValidator() as validator:
            results = await validator.test_all_integrations()
            report = validator.generate_integration_report(results)
            
            print(json.dumps(report, indent=2))
            
            # Exit with error code if any integrations failed
            if report["summary"]["failed_tests"] > 0:
                exit(1)
    
    asyncio.run(main())
