"""
Test All APIs Responding

Validates that all 47+ API endpoints across all 10 Lucid clusters are responding correctly.
Tests API availability, response formats, and basic functionality.

API Categories Tested:
- Authentication APIs (Cluster 09)
- User Management APIs (Cluster 01)
- Session Management APIs (Cluster 03)
- Blockchain APIs (Cluster 02)
- RDP Service APIs (Cluster 04)
- Node Management APIs (Cluster 05)
- Admin Interface APIs (Cluster 06)
- TRON Payment APIs (Cluster 07, isolated)
- Database APIs (Cluster 08)
- Cross-Cluster APIs (Cluster 10)
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
class APIEndpoint:
    """API endpoint configuration"""
    name: str
    method: str
    url: str
    headers: Dict[str, str] = None
    expected_status: int = 200
    expected_content_type: str = "application/json"
    timeout: int = 30
    requires_auth: bool = False
    auth_token: Optional[str] = None


@dataclass
class APIResponseResult:
    """API response validation result"""
    endpoint_name: str
    is_responding: bool
    response_time_ms: float
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    response_size_bytes: Optional[int] = None
    error_message: Optional[str] = None
    validation_errors: List[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.validation_errors is None:
            self.validation_errors = []


class APIResponseValidator:
    """Validates API responses across all Lucid clusters"""
    
    def __init__(self, auth_token: Optional[str] = None):
        self.auth_token = auth_token
        self.endpoints = self._initialize_api_endpoints()
        self.session: Optional[aiohttp.ClientSession] = None
    
    def _initialize_api_endpoints(self) -> List[APIEndpoint]:
        """Initialize all API endpoints across clusters"""
        endpoints = []
        
        # Cluster 01: API Gateway Endpoints
        base_url = "http://localhost:8080"
        endpoints.extend([
            APIEndpoint("api-gateway-health", "GET", f"{base_url}/health"),
            APIEndpoint("api-gateway-docs", "GET", f"{base_url}/docs"),
            APIEndpoint("api-gateway-openapi", "GET", f"{base_url}/openapi.json"),
            APIEndpoint("api-gateway-meta", "GET", f"{base_url}/api/v1/meta/info"),
            APIEndpoint("api-gateway-auth-login", "POST", f"{base_url}/api/v1/auth/login", requires_auth=False),
            APIEndpoint("api-gateway-auth-verify", "POST", f"{base_url}/api/v1/auth/verify", requires_auth=True),
            APIEndpoint("api-gateway-users-list", "GET", f"{base_url}/api/v1/users", requires_auth=True),
            APIEndpoint("api-gateway-sessions-list", "GET", f"{base_url}/api/v1/sessions", requires_auth=True),
            APIEndpoint("api-gateway-manifests-list", "GET", f"{base_url}/api/v1/manifests", requires_auth=True),
            APIEndpoint("api-gateway-trust-policies", "GET", f"{base_url}/api/v1/trust", requires_auth=True),
            APIEndpoint("api-gateway-chain-info", "GET", f"{base_url}/api/v1/chain/info", requires_auth=True),
        ])
        
        # Cluster 02: Blockchain Core Endpoints
        blockchain_base = "http://localhost:8084"
        endpoints.extend([
            APIEndpoint("blockchain-health", "GET", f"{blockchain_base}/health"),
            APIEndpoint("blockchain-info", "GET", f"{blockchain_base}/api/v1/blockchain/info"),
            APIEndpoint("blockchain-blocks-latest", "GET", f"{blockchain_base}/api/v1/blocks/latest"),
            APIEndpoint("blockchain-blocks-list", "GET", f"{blockchain_base}/api/v1/blocks"),
            APIEndpoint("blockchain-transactions-list", "GET", f"{blockchain_base}/api/v1/transactions"),
            APIEndpoint("blockchain-consensus-status", "GET", f"{blockchain_base}/api/v1/consensus/status"),
        ])
        
        # Session Anchoring Endpoints
        anchoring_base = "http://localhost:8085"
        endpoints.extend([
            APIEndpoint("anchoring-health", "GET", f"{anchoring_base}/health"),
            APIEndpoint("anchoring-status", "GET", f"{anchoring_base}/api/v1/anchoring/status"),
        ])
        
        # Block Manager Endpoints
        manager_base = "http://localhost:8086"
        endpoints.extend([
            APIEndpoint("block-manager-health", "GET", f"{manager_base}/health"),
            APIEndpoint("block-manager-stats", "GET", f"{manager_base}/api/v1/blocks/stats"),
        ])
        
        # Data Chain Endpoints
        data_base = "http://localhost:8087"
        endpoints.extend([
            APIEndpoint("data-chain-health", "GET", f"{data_base}/health"),
            APIEndpoint("data-chain-chunks", "GET", f"{data_base}/api/v1/chunks"),
        ])
        
        # Cluster 03: Session Management Endpoints
        session_base = "http://localhost:8083"
        endpoints.extend([
            APIEndpoint("session-pipeline-health", "GET", f"{session_base}/health"),
            APIEndpoint("session-pipeline-status", "GET", f"{session_base}/api/v1/pipeline/status"),
            APIEndpoint("session-recorder-health", "GET", f"{session_base}/health"),
            APIEndpoint("session-processor-health", "GET", f"{session_base}/health"),
            APIEndpoint("session-storage-health", "GET", f"{session_base}/health"),
            APIEndpoint("session-api-health", "GET", f"{session_base}/health"),
            APIEndpoint("session-api-sessions", "GET", f"{session_base}/api/v1/sessions"),
        ])
        
        # Cluster 04: RDP Services Endpoints
        endpoints.extend([
            APIEndpoint("rdp-server-manager-health", "GET", "http://localhost:8090/health"),
            APIEndpoint("rdp-server-manager-servers", "GET", "http://localhost:8090/api/v1/servers"),
            APIEndpoint("xrdp-service-health", "GET", "http://localhost:8091/health"),
            APIEndpoint("rdp-controller-health", "GET", "http://localhost:8092/health"),
            APIEndpoint("rdp-controller-sessions", "GET", "http://localhost:8092/api/v1/sessions"),
            APIEndpoint("rdp-monitor-health", "GET", "http://localhost:8093/health"),
            APIEndpoint("rdp-monitor-metrics", "GET", "http://localhost:8093/api/v1/metrics"),
        ])
        
        # Cluster 05: Node Management Endpoints
        node_base = "http://localhost:8095"
        endpoints.extend([
            APIEndpoint("node-management-health", "GET", f"{node_base}/health"),
            APIEndpoint("node-management-nodes", "GET", f"{node_base}/api/v1/nodes"),
            APIEndpoint("node-management-pools", "GET", f"{node_base}/api/v1/pools"),
            APIEndpoint("node-management-payouts", "GET", f"{node_base}/api/v1/payouts"),
            APIEndpoint("node-management-poot", "GET", f"{node_base}/api/v1/poot/status"),
        ])
        
        # Cluster 06: Admin Interface Endpoints
        admin_base = "http://localhost:8083"
        endpoints.extend([
            APIEndpoint("admin-interface-health", "GET", f"{admin_base}/health"),
            APIEndpoint("admin-dashboard", "GET", f"{admin_base}/api/v1/dashboard"),
            APIEndpoint("admin-users", "GET", f"{admin_base}/api/v1/admin/users"),
            APIEndpoint("admin-sessions", "GET", f"{admin_base}/api/v1/admin/sessions"),
            APIEndpoint("admin-blockchain", "GET", f"{admin_base}/api/v1/admin/blockchain"),
            APIEndpoint("admin-nodes", "GET", f"{admin_base}/api/v1/admin/nodes"),
        ])
        
        # Cluster 07: TRON Payment Endpoints (Isolated)
        tron_base = "http://localhost:8085"
        endpoints.extend([
            APIEndpoint("tron-client-health", "GET", f"{tron_base}/health"),
            APIEndpoint("tron-network-info", "GET", f"{tron_base}/api/v1/tron/network"),
            APIEndpoint("tron-wallets-list", "GET", f"{tron_base}/api/v1/wallets"),
            APIEndpoint("tron-usdt-balance", "GET", f"{tron_base}/api/v1/usdt/balance"),
            APIEndpoint("tron-payouts-list", "GET", f"{tron_base}/api/v1/payouts"),
            APIEndpoint("tron-staking-status", "GET", f"{tron_base}/api/v1/staking/status"),
            APIEndpoint("payment-gateway-health", "GET", f"{tron_base}/health"),
        ])
        
        # Cluster 08: Storage Database Endpoints
        endpoints.extend([
            APIEndpoint("mongodb-health", "GET", "http://localhost:27017/", expected_status=200),
            APIEndpoint("redis-health", "GET", "http://localhost:6379/", expected_status=200),
            APIEndpoint("elasticsearch-health", "GET", "http://localhost:9200/_cluster/health"),
            APIEndpoint("database-health", "GET", "http://localhost:8088/health"),
            APIEndpoint("database-stats", "GET", "http://localhost:8088/api/v1/stats"),
            APIEndpoint("database-backups", "GET", "http://localhost:8088/api/v1/backups"),
            APIEndpoint("cache-stats", "GET", "http://localhost:8088/api/v1/cache/stats"),
            APIEndpoint("volume-stats", "GET", "http://localhost:8088/api/v1/volumes/stats"),
            APIEndpoint("search-indices", "GET", "http://localhost:8088/api/v1/search/indices"),
        ])
        
        # Cluster 09: Authentication Endpoints
        auth_base = "http://localhost:8089"
        endpoints.extend([
            APIEndpoint("auth-service-health", "GET", f"{auth_base}/health"),
            APIEndpoint("auth-login", "POST", f"{auth_base}/api/v1/auth/login", requires_auth=False),
            APIEndpoint("auth-verify", "POST", f"{auth_base}/api/v1/auth/verify", requires_auth=True),
            APIEndpoint("auth-refresh", "POST", f"{auth_base}/api/v1/auth/refresh", requires_auth=True),
            APIEndpoint("auth-users", "GET", f"{auth_base}/api/v1/users", requires_auth=True),
            APIEndpoint("auth-sessions", "GET", f"{auth_base}/api/v1/sessions", requires_auth=True),
            APIEndpoint("auth-permissions", "GET", f"{auth_base}/api/v1/permissions", requires_auth=True),
        ])
        
        # Cluster 10: Cross-Cluster Integration Endpoints
        endpoints.extend([
            APIEndpoint("consul-health", "GET", "http://localhost:8500/v1/status/leader", expected_status=200),
            APIEndpoint("consul-services", "GET", "http://localhost:8500/v1/catalog/services"),
            APIEndpoint("service-mesh-health", "GET", "http://localhost:8500/v1/status/leader", expected_status=200),
        ])
        
        return endpoints
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def test_endpoint_response(self, endpoint: APIEndpoint) -> APIResponseResult:
        """Test a single API endpoint response"""
        start_time = datetime.utcnow()
        validation_errors = []
        
        try:
            # Prepare headers
            headers = endpoint.headers or {}
            if endpoint.requires_auth and self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            # Make request
            async with self.session.request(
                method=endpoint.method,
                url=endpoint.url,
                headers=headers
            ) as response:
                end_time = datetime.utcnow()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                # Read response content
                content = await response.read()
                response_size = len(content)
                
                # Validate status code
                if response.status != endpoint.expected_status:
                    validation_errors.append(
                        f"Expected status {endpoint.expected_status}, got {response.status}"
                    )
                
                # Validate content type
                content_type = response.headers.get('content-type', '')
                if endpoint.expected_content_type and endpoint.expected_content_type not in content_type:
                    validation_errors.append(
                        f"Expected content type {endpoint.expected_content_type}, got {content_type}"
                    )
                
                # Validate JSON response for JSON endpoints
                if endpoint.expected_content_type == "application/json" and content:
                    try:
                        json.loads(content.decode('utf-8'))
                    except json.JSONDecodeError as e:
                        validation_errors.append(f"Invalid JSON response: {str(e)}")
                
                is_responding = len(validation_errors) == 0
                
                return APIResponseResult(
                    endpoint_name=endpoint.name,
                    is_responding=is_responding,
                    response_time_ms=response_time,
                    status_code=response.status,
                    content_type=content_type,
                    response_size_bytes=response_size,
                    validation_errors=validation_errors,
                    timestamp=start_time
                )
        
        except Exception as e:
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            return APIResponseResult(
                endpoint_name=endpoint.name,
                is_responding=False,
                response_time_ms=response_time,
                error_message=str(e),
                validation_errors=[str(e)],
                timestamp=start_time
            )
    
    async def test_all_endpoints(self) -> List[APIResponseResult]:
        """Test all API endpoints concurrently"""
        if not self.session:
            raise RuntimeError("APIResponseValidator must be used as async context manager")
        
        tasks = [self.test_endpoint_response(endpoint) for endpoint in self.endpoints]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and convert to APIResponseResult
        api_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                api_results.append(APIResponseResult(
                    endpoint_name=self.endpoints[i].name,
                    is_responding=False,
                    response_time_ms=0,
                    error_message=str(result)
                ))
            else:
                api_results.append(result)
        
        return api_results
    
    def generate_api_report(self, results: List[APIResponseResult]) -> Dict[str, Any]:
        """Generate comprehensive API response report"""
        total_endpoints = len(results)
        responding_endpoints = sum(1 for r in results if r.is_responding)
        non_responding_endpoints = total_endpoints - responding_endpoints
        
        # Group by response status
        responding = [r for r in results if r.is_responding]
        non_responding = [r for r in results if not r.is_responding]
        
        # Calculate statistics
        avg_response_time = 0
        if responding:
            avg_response_time = sum(r.response_time_ms for r in responding) / len(responding)
        
        # Group by cluster
        cluster_stats = {}
        for result in results:
            cluster_name = result.endpoint_name.split('-')[0] + '-cluster'
            if cluster_name not in cluster_stats:
                cluster_stats[cluster_name] = {"total": 0, "responding": 0}
            cluster_stats[cluster_name]["total"] += 1
            if result.is_responding:
                cluster_stats[cluster_name]["responding"] += 1
        
        # Calculate cluster health percentages
        for cluster in cluster_stats:
            total = cluster_stats[cluster]["total"]
            responding = cluster_stats[cluster]["responding"]
            cluster_stats[cluster]["health_percentage"] = (responding / total) * 100
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_endpoints": total_endpoints,
                "responding_endpoints": responding_endpoints,
                "non_responding_endpoints": non_responding_endpoints,
                "response_rate_percentage": (responding_endpoints / total_endpoints) * 100,
                "average_response_time_ms": round(avg_response_time, 2)
            },
            "cluster_health": cluster_stats,
            "responding_endpoints": [
                {
                    "name": r.endpoint_name,
                    "response_time_ms": round(r.response_time_ms, 2),
                    "status_code": r.status_code,
                    "content_type": r.content_type,
                    "response_size_bytes": r.response_size_bytes
                }
                for r in responding
            ],
            "non_responding_endpoints": [
                {
                    "name": r.endpoint_name,
                    "error": r.error_message,
                    "validation_errors": r.validation_errors,
                    "response_time_ms": round(r.response_time_ms, 2),
                    "status_code": r.status_code
                }
                for r in non_responding
            ]
        }
        
        return report


class TestAPIResponse:
    """Pytest test class for API response validation"""
    
    @pytest.fixture
    async def api_validator(self):
        """Fixture for APIResponseValidator"""
        async with APIResponseValidator() as validator:
            yield validator
    
    @pytest.mark.asyncio
    async def test_all_apis_responding(self, api_validator):
        """Test that all APIs are responding correctly"""
        results = await api_validator.test_all_endpoints()
        report = api_validator.generate_api_report(results)
        
        # Log the API report
        logger.info(f"API Report: {report['summary']}")
        
        # Assert all APIs are responding
        non_responding = [r for r in results if not r.is_responding]
        
        if non_responding:
            non_responding_names = [r.endpoint_name for r in non_responding]
            pytest.fail(f"Non-responding APIs: {non_responding_names}")
        
        # Assert 100% response rate
        assert report["summary"]["response_rate_percentage"] == 100.0
        assert report["summary"]["non_responding_endpoints"] == 0
    
    @pytest.mark.asyncio
    async def test_api_gateway_endpoints(self, api_validator):
        """Test API Gateway endpoints"""
        api_gateway_endpoints = [
            "api-gateway-health", "api-gateway-docs", "api-gateway-openapi",
            "api-gateway-meta"
        ]
        
        for endpoint_name in api_gateway_endpoints:
            endpoint = next(e for e in api_validator.endpoints if e.name == endpoint_name)
            result = await api_validator.test_endpoint_response(endpoint)
            
            assert result.is_responding, f"{endpoint_name} not responding: {result.error_message}"
            assert result.response_time_ms < 1000, f"{endpoint_name} response time too high"
    
    @pytest.mark.asyncio
    async def test_blockchain_core_endpoints(self, api_validator):
        """Test Blockchain Core endpoints"""
        blockchain_endpoints = [
            "blockchain-health", "blockchain-info", "blockchain-blocks-latest",
            "blockchain-consensus-status"
        ]
        
        for endpoint_name in blockchain_endpoints:
            endpoint = next(e for e in api_validator.endpoints if e.name == endpoint_name)
            result = await api_validator.test_endpoint_response(endpoint)
            
            assert result.is_responding, f"{endpoint_name} not responding: {result.error_message}"
    
    @pytest.mark.asyncio
    async def test_database_endpoints(self, api_validator):
        """Test database service endpoints"""
        db_endpoints = [
            "mongodb-health", "redis-health", "elasticsearch-health",
            "database-health", "database-stats"
        ]
        
        for endpoint_name in db_endpoints:
            endpoint = next(e for e in api_validator.endpoints if e.name == endpoint_name)
            result = await api_validator.test_endpoint_response(endpoint)
            
            assert result.is_responding, f"{endpoint_name} not responding: {result.error_message}"
    
    @pytest.mark.asyncio
    async def test_authentication_endpoints(self, api_validator):
        """Test Authentication service endpoints"""
        auth_endpoints = [
            "auth-service-health", "auth-login"
        ]
        
        for endpoint_name in auth_endpoints:
            endpoint = next(e for e in api_validator.endpoints if e.name == endpoint_name)
            result = await api_validator.test_endpoint_response(endpoint)
            
            assert result.is_responding, f"{endpoint_name} not responding: {result.error_message}"
    
    @pytest.mark.asyncio
    async def test_api_response_times(self, api_validator):
        """Test that all APIs respond within acceptable time limits"""
        results = await api_validator.test_all_endpoints()
        responding_results = [r for r in results if r.is_responding]
        
        # Define acceptable response times (in milliseconds)
        max_response_times = {
            "api-gateway": 100,
            "blockchain": 200,
            "session": 150,
            "rdp": 200,
            "node": 150,
            "admin": 150,
            "tron": 300,
            "database": 100,
            "auth": 100,
            "consul": 50
        }
        
        for result in responding_results:
            # Get cluster prefix for time limit lookup
            cluster_prefix = result.endpoint_name.split('-')[0]
            max_time = max_response_times.get(cluster_prefix, 1000)  # Default 1 second
            
            assert result.response_time_ms <= max_time, \
                f"{result.endpoint_name} response time {result.response_time_ms}ms exceeds limit {max_time}ms"


if __name__ == "__main__":
    """Run API response validation standalone"""
    import json
    
    async def main():
        async with APIResponseValidator() as validator:
            results = await validator.test_all_endpoints()
            report = validator.generate_api_report(results)
            
            print(json.dumps(report, indent=2))
            
            # Exit with error code if any APIs are not responding
            if report["summary"]["non_responding_endpoints"] > 0:
                exit(1)
    
    asyncio.run(main())
