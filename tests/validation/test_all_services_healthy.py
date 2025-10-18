"""
Test All Services Healthy

Validates that all 10 Lucid clusters are healthy and operational.
Tests health check endpoints and service status for each cluster.

Clusters Tested:
- Cluster 01: API Gateway (Port 8080)
- Cluster 02: Blockchain Core (Ports 8084-8087)
- Cluster 03: Session Management (Ports 8083-8087)
- Cluster 04: RDP Services (Ports 8090-8093)
- Cluster 05: Node Management (Port 8095)
- Cluster 06: Admin Interface (Port 8083)
- Cluster 07: TRON Payment (Port 8085, isolated)
- Cluster 08: Storage Database (Port 8088)
- Cluster 09: Authentication (Port 8089)
- Cluster 10: Cross-Cluster Integration (Service Mesh)
"""

import asyncio
import aiohttp
import pytest
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ServiceEndpoint:
    """Service endpoint configuration"""
    name: str
    url: str
    port: int
    health_path: str = "/health"
    expected_status: int = 200
    timeout: int = 30


@dataclass
class ServiceHealthResult:
    """Service health check result"""
    service_name: str
    is_healthy: bool
    response_time_ms: float
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class ServiceHealthValidator:
    """Validates health of all Lucid services"""
    
    def __init__(self):
        self.services = self._initialize_services()
        self.session: Optional[aiohttp.ClientSession] = None
    
    def _initialize_services(self) -> List[ServiceEndpoint]:
        """Initialize service endpoints for all clusters"""
        return [
            # Cluster 01: API Gateway
            ServiceEndpoint(
                name="api-gateway",
                url="http://localhost:8080",
                port=8080,
                health_path="/health"
            ),
            
            # Cluster 02: Blockchain Core
            ServiceEndpoint(
                name="blockchain-engine",
                url="http://localhost:8084",
                port=8084,
                health_path="/health"
            ),
            ServiceEndpoint(
                name="session-anchoring",
                url="http://localhost:8085",
                port=8085,
                health_path="/health"
            ),
            ServiceEndpoint(
                name="block-manager",
                url="http://localhost:8086",
                port=8086,
                health_path="/health"
            ),
            ServiceEndpoint(
                name="data-chain",
                url="http://localhost:8087",
                port=8087,
                health_path="/health"
            ),
            
            # Cluster 03: Session Management
            ServiceEndpoint(
                name="session-pipeline",
                url="http://localhost:8083",
                port=8083,
                health_path="/health"
            ),
            ServiceEndpoint(
                name="session-recorder",
                url="http://localhost:8083",
                port=8083,
                health_path="/health"
            ),
            ServiceEndpoint(
                name="session-processor",
                url="http://localhost:8083",
                port=8083,
                health_path="/health"
            ),
            ServiceEndpoint(
                name="session-storage",
                url="http://localhost:8083",
                port=8083,
                health_path="/health"
            ),
            ServiceEndpoint(
                name="session-api",
                url="http://localhost:8087",
                port=8087,
                health_path="/health"
            ),
            
            # Cluster 04: RDP Services
            ServiceEndpoint(
                name="rdp-server-manager",
                url="http://localhost:8090",
                port=8090,
                health_path="/health"
            ),
            ServiceEndpoint(
                name="xrdp-service",
                url="http://localhost:8091",
                port=8091,
                health_path="/health"
            ),
            ServiceEndpoint(
                name="rdp-controller",
                url="http://localhost:8092",
                port=8092,
                health_path="/health"
            ),
            ServiceEndpoint(
                name="rdp-monitor",
                url="http://localhost:8093",
                port=8093,
                health_path="/health"
            ),
            
            # Cluster 05: Node Management
            ServiceEndpoint(
                name="node-management",
                url="http://localhost:8095",
                port=8095,
                health_path="/health"
            ),
            
            # Cluster 06: Admin Interface
            ServiceEndpoint(
                name="admin-interface",
                url="http://localhost:8083",
                port=8083,
                health_path="/health"
            ),
            
            # Cluster 07: TRON Payment (Isolated)
            ServiceEndpoint(
                name="tron-client",
                url="http://localhost:8085",
                port=8085,
                health_path="/health"
            ),
            ServiceEndpoint(
                name="payout-router",
                url="http://localhost:8085",
                port=8085,
                health_path="/health"
            ),
            ServiceEndpoint(
                name="wallet-manager",
                url="http://localhost:8085",
                port=8085,
                health_path="/health"
            ),
            ServiceEndpoint(
                name="usdt-manager",
                url="http://localhost:8085",
                port=8085,
                health_path="/health"
            ),
            ServiceEndpoint(
                name="trx-staking",
                url="http://localhost:8085",
                port=8085,
                health_path="/health"
            ),
            ServiceEndpoint(
                name="payment-gateway",
                url="http://localhost:8085",
                port=8085,
                health_path="/health"
            ),
            
            # Cluster 08: Storage Database
            ServiceEndpoint(
                name="mongodb",
                url="http://localhost:27017",
                port=27017,
                health_path="/",
                expected_status=200
            ),
            ServiceEndpoint(
                name="redis",
                url="http://localhost:6379",
                port=6379,
                health_path="/",
                expected_status=200
            ),
            ServiceEndpoint(
                name="elasticsearch",
                url="http://localhost:9200",
                port=9200,
                health_path="/_cluster/health"
            ),
            
            # Cluster 09: Authentication
            ServiceEndpoint(
                name="auth-service",
                url="http://localhost:8089",
                port=8089,
                health_path="/health"
            ),
            
            # Cluster 10: Cross-Cluster Integration
            ServiceEndpoint(
                name="service-mesh-controller",
                url="http://localhost:8500",
                port=8500,
                health_path="/v1/status/leader",
                expected_status=200
            ),
            ServiceEndpoint(
                name="consul",
                url="http://localhost:8500",
                port=8500,
                health_path="/v1/status/leader",
                expected_status=200
            )
        ]
    
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
    
    async def check_service_health(self, service: ServiceEndpoint) -> ServiceHealthResult:
        """Check health of a single service"""
        start_time = datetime.utcnow()
        
        try:
            health_url = f"{service.url}{service.health_path}"
            
            async with self.session.get(health_url) as response:
                end_time = datetime.utcnow()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                is_healthy = response.status == service.expected_status
                
                return ServiceHealthResult(
                    service_name=service.name,
                    is_healthy=is_healthy,
                    response_time_ms=response_time,
                    status_code=response.status,
                    timestamp=start_time
                )
        
        except Exception as e:
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            return ServiceHealthResult(
                service_name=service.name,
                is_healthy=False,
                response_time_ms=response_time,
                error_message=str(e),
                timestamp=start_time
            )
    
    async def check_all_services(self) -> List[ServiceHealthResult]:
        """Check health of all services concurrently"""
        if not self.session:
            raise RuntimeError("ServiceHealthValidator must be used as async context manager")
        
        tasks = [self.check_service_health(service) for service in self.services]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and convert to ServiceHealthResult
        health_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                health_results.append(ServiceHealthResult(
                    service_name=self.services[i].name,
                    is_healthy=False,
                    response_time_ms=0,
                    error_message=str(result)
                ))
            else:
                health_results.append(result)
        
        return health_results
    
    def generate_health_report(self, results: List[ServiceHealthResult]) -> Dict:
        """Generate comprehensive health report"""
        total_services = len(results)
        healthy_services = sum(1 for r in results if r.is_healthy)
        unhealthy_services = total_services - healthy_services
        
        # Group by service status
        healthy = [r for r in results if r.is_healthy]
        unhealthy = [r for r in results if not r.is_healthy]
        
        # Calculate average response time for healthy services
        avg_response_time = 0
        if healthy:
            avg_response_time = sum(r.response_time_ms for r in healthy) / len(healthy)
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_services": total_services,
                "healthy_services": healthy_services,
                "unhealthy_services": unhealthy_services,
                "health_percentage": (healthy_services / total_services) * 100,
                "average_response_time_ms": round(avg_response_time, 2)
            },
            "healthy_services": [
                {
                    "name": r.service_name,
                    "response_time_ms": round(r.response_time_ms, 2),
                    "status_code": r.status_code
                }
                for r in healthy
            ],
            "unhealthy_services": [
                {
                    "name": r.service_name,
                    "error": r.error_message,
                    "response_time_ms": round(r.response_time_ms, 2),
                    "status_code": r.status_code
                }
                for r in unhealthy
            ]
        }
        
        return report


class TestServiceHealth:
    """Pytest test class for service health validation"""
    
    @pytest.fixture
    async def health_validator(self):
        """Fixture for ServiceHealthValidator"""
        async with ServiceHealthValidator() as validator:
            yield validator
    
    @pytest.mark.asyncio
    async def test_all_services_healthy(self, health_validator):
        """Test that all services are healthy"""
        results = await health_validator.check_all_services()
        report = health_validator.generate_health_report(results)
        
        # Log the health report
        logger.info(f"Health Report: {report['summary']}")
        
        # Assert all services are healthy
        unhealthy_services = [r for r in results if not r.is_healthy]
        
        if unhealthy_services:
            unhealthy_names = [r.service_name for r in unhealthy_services]
            pytest.fail(f"Unhealthy services: {unhealthy_names}")
        
        # Assert health percentage is 100%
        assert report["summary"]["health_percentage"] == 100.0
        assert report["summary"]["unhealthy_services"] == 0
    
    @pytest.mark.asyncio
    async def test_api_gateway_health(self, health_validator):
        """Test API Gateway service health"""
        api_gateway = next(s for s in health_validator.services if s.name == "api-gateway")
        result = await health_validator.check_service_health(api_gateway)
        
        assert result.is_healthy, f"API Gateway unhealthy: {result.error_message}"
        assert result.response_time_ms < 1000, "API Gateway response time too high"
    
    @pytest.mark.asyncio
    async def test_blockchain_core_health(self, health_validator):
        """Test Blockchain Core services health"""
        blockchain_services = [
            "blockchain-engine", "session-anchoring", "block-manager", "data-chain"
        ]
        
        for service_name in blockchain_services:
            service = next(s for s in health_validator.services if s.name == service_name)
            result = await health_validator.check_service_health(service)
            
            assert result.is_healthy, f"{service_name} unhealthy: {result.error_message}"
    
    @pytest.mark.asyncio
    async def test_database_services_health(self, health_validator):
        """Test database services health"""
        db_services = ["mongodb", "redis", "elasticsearch"]
        
        for service_name in db_services:
            service = next(s for s in health_validator.services if s.name == service_name)
            result = await health_validator.check_service_health(service)
            
            assert result.is_healthy, f"{service_name} unhealthy: {result.error_message}"
    
    @pytest.mark.asyncio
    async def test_authentication_service_health(self, health_validator):
        """Test Authentication service health"""
        auth_service = next(s for s in health_validator.services if s.name == "auth-service")
        result = await health_validator.check_service_health(auth_service)
        
        assert result.is_healthy, f"Authentication service unhealthy: {result.error_message}"
    
    @pytest.mark.asyncio
    async def test_service_response_times(self, health_validator):
        """Test that all services respond within acceptable time limits"""
        results = await health_validator.check_all_services()
        healthy_results = [r for r in results if r.is_healthy]
        
        # Define acceptable response times (in milliseconds)
        max_response_times = {
            "api-gateway": 100,
            "blockchain-engine": 200,
            "session-anchoring": 200,
            "block-manager": 200,
            "data-chain": 200,
            "mongodb": 50,
            "redis": 10,
            "elasticsearch": 100,
            "auth-service": 100,
            "consul": 50
        }
        
        for result in healthy_results:
            max_time = max_response_times.get(result.service_name, 1000)  # Default 1 second
            assert result.response_time_ms <= max_time, \
                f"{result.service_name} response time {result.response_time_ms}ms exceeds limit {max_time}ms"


if __name__ == "__main__":
    """Run service health validation standalone"""
    import json
    
    async def main():
        async with ServiceHealthValidator() as validator:
            results = await validator.check_all_services()
            report = validator.generate_health_report(results)
            
            print(json.dumps(report, indent=2))
            
            # Exit with error code if any services are unhealthy
            if report["summary"]["unhealthy_services"] > 0:
                exit(1)
    
    asyncio.run(main())
