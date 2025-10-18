"""
Test All Containers Running

Validates that all Docker containers for the 10 Lucid clusters are running correctly.
Tests container status, health checks, and resource utilization.

Containers Tested:
- Cluster 01: API Gateway (lucid-api-gateway)
- Cluster 02: Blockchain Core (lucid-blockchain-engine, lucid-session-anchoring, lucid-block-manager, lucid-data-chain)
- Cluster 03: Session Management (lucid-session-pipeline, lucid-session-recorder, lucid-session-processor, lucid-session-storage, lucid-session-api)
- Cluster 04: RDP Services (lucid-rdp-server-manager, lucid-xrdp-service, lucid-rdp-controller, lucid-rdp-monitor)
- Cluster 05: Node Management (lucid-node-management)
- Cluster 06: Admin Interface (lucid-admin-interface)
- Cluster 07: TRON Payment (lucid-tron-client, lucid-payout-router, lucid-wallet-manager, lucid-usdt-manager, lucid-trx-staking, lucid-payment-gateway)
- Cluster 08: Storage Database (lucid-mongodb, lucid-redis, lucid-elasticsearch)
- Cluster 09: Authentication (lucid-auth-service)
- Cluster 10: Cross-Cluster Integration (lucid-consul, lucid-service-mesh-controller)
"""

import asyncio
import subprocess
import json
import pytest
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ContainerInfo:
    """Container information"""
    name: str
    image: str
    status: str
    cluster: str
    port: Optional[int] = None
    health_status: Optional[str] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    uptime: Optional[str] = None


@dataclass
class ContainerValidationResult:
    """Container validation result"""
    container_name: str
    is_running: bool
    is_healthy: bool
    cluster: str
    status: str
    health_status: Optional[str] = None
    resource_usage: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class ContainerValidator:
    """Validates Docker container status across all Lucid clusters"""
    
    def __init__(self):
        self.expected_containers = self._initialize_expected_containers()
    
    def _initialize_expected_containers(self) -> List[Dict[str, Any]]:
        """Initialize expected containers for all clusters"""
        return [
            # Cluster 01: API Gateway
            {
                "name": "lucid-api-gateway",
                "image": "lucid-api-gateway:latest",
                "cluster": "01-api-gateway",
                "port": 8080,
                "health_check": True
            },
            
            # Cluster 02: Blockchain Core
            {
                "name": "lucid-blockchain-engine",
                "image": "lucid-blockchain-engine:latest",
                "cluster": "02-blockchain-core",
                "port": 8084,
                "health_check": True
            },
            {
                "name": "lucid-session-anchoring",
                "image": "lucid-session-anchoring:latest",
                "cluster": "02-blockchain-core",
                "port": 8085,
                "health_check": True
            },
            {
                "name": "lucid-block-manager",
                "image": "lucid-block-manager:latest",
                "cluster": "02-blockchain-core",
                "port": 8086,
                "health_check": True
            },
            {
                "name": "lucid-data-chain",
                "image": "lucid-data-chain:latest",
                "cluster": "02-blockchain-core",
                "port": 8087,
                "health_check": True
            },
            
            # Cluster 03: Session Management
            {
                "name": "lucid-session-pipeline",
                "image": "lucid-session-pipeline:latest",
                "cluster": "03-session-management",
                "port": 8083,
                "health_check": True
            },
            {
                "name": "lucid-session-recorder",
                "image": "lucid-session-recorder:latest",
                "cluster": "03-session-management",
                "port": 8083,
                "health_check": True
            },
            {
                "name": "lucid-session-processor",
                "image": "lucid-session-processor:latest",
                "cluster": "03-session-management",
                "port": 8083,
                "health_check": True
            },
            {
                "name": "lucid-session-storage",
                "image": "lucid-session-storage:latest",
                "cluster": "03-session-management",
                "port": 8083,
                "health_check": True
            },
            {
                "name": "lucid-session-api",
                "image": "lucid-session-api:latest",
                "cluster": "03-session-management",
                "port": 8087,
                "health_check": True
            },
            
            # Cluster 04: RDP Services
            {
                "name": "lucid-rdp-server-manager",
                "image": "lucid-rdp-server-manager:latest",
                "cluster": "04-rdp-services",
                "port": 8090,
                "health_check": True
            },
            {
                "name": "lucid-xrdp-service",
                "image": "lucid-xrdp-service:latest",
                "cluster": "04-rdp-services",
                "port": 8091,
                "health_check": True
            },
            {
                "name": "lucid-rdp-controller",
                "image": "lucid-rdp-controller:latest",
                "cluster": "04-rdp-services",
                "port": 8092,
                "health_check": True
            },
            {
                "name": "lucid-rdp-monitor",
                "image": "lucid-rdp-monitor:latest",
                "cluster": "04-rdp-services",
                "port": 8093,
                "health_check": True
            },
            
            # Cluster 05: Node Management
            {
                "name": "lucid-node-management",
                "image": "lucid-node-management:latest",
                "cluster": "05-node-management",
                "port": 8095,
                "health_check": True
            },
            
            # Cluster 06: Admin Interface
            {
                "name": "lucid-admin-interface",
                "image": "lucid-admin-interface:latest",
                "cluster": "06-admin-interface",
                "port": 8083,
                "health_check": True
            },
            
            # Cluster 07: TRON Payment (Isolated)
            {
                "name": "lucid-tron-client",
                "image": "lucid-tron-client:latest",
                "cluster": "07-tron-payment",
                "port": 8085,
                "health_check": True
            },
            {
                "name": "lucid-payout-router",
                "image": "lucid-payout-router:latest",
                "cluster": "07-tron-payment",
                "port": 8085,
                "health_check": True
            },
            {
                "name": "lucid-wallet-manager",
                "image": "lucid-wallet-manager:latest",
                "cluster": "07-tron-payment",
                "port": 8085,
                "health_check": True
            },
            {
                "name": "lucid-usdt-manager",
                "image": "lucid-usdt-manager:latest",
                "cluster": "07-tron-payment",
                "port": 8085,
                "health_check": True
            },
            {
                "name": "lucid-trx-staking",
                "image": "lucid-trx-staking:latest",
                "cluster": "07-tron-payment",
                "port": 8085,
                "health_check": True
            },
            {
                "name": "lucid-payment-gateway",
                "image": "lucid-payment-gateway:latest",
                "cluster": "07-tron-payment",
                "port": 8085,
                "health_check": True
            },
            
            # Cluster 08: Storage Database
            {
                "name": "lucid-mongodb",
                "image": "mongo:7.0",
                "cluster": "08-storage-database",
                "port": 27017,
                "health_check": True
            },
            {
                "name": "lucid-redis",
                "image": "redis:7.0",
                "cluster": "08-storage-database",
                "port": 6379,
                "health_check": True
            },
            {
                "name": "lucid-elasticsearch",
                "image": "elasticsearch:8.11.0",
                "cluster": "08-storage-database",
                "port": 9200,
                "health_check": True
            },
            
            # Cluster 09: Authentication
            {
                "name": "lucid-auth-service",
                "image": "lucid-auth-service:latest",
                "cluster": "09-authentication",
                "port": 8089,
                "health_check": True
            },
            
            # Cluster 10: Cross-Cluster Integration
            {
                "name": "lucid-consul",
                "image": "consul:1.17",
                "cluster": "10-cross-cluster-integration",
                "port": 8500,
                "health_check": True
            },
            {
                "name": "lucid-service-mesh-controller",
                "image": "lucid-service-mesh-controller:latest",
                "cluster": "10-cross-cluster-integration",
                "port": 8500,
                "health_check": True
            }
        ]
    
    async def get_container_status(self) -> List[ContainerInfo]:
        """Get status of all containers using docker ps"""
        try:
            # Run docker ps command
            result = subprocess.run(
                ["docker", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                check=True
            )
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    container_data = json.loads(line)
                    containers.append(ContainerInfo(
                        name=container_data.get("Names", ""),
                        image=container_data.get("Image", ""),
                        status=container_data.get("Status", ""),
                        cluster=self._get_cluster_from_name(container_data.get("Names", "")),
                        port=self._extract_port_from_status(container_data.get("Status", ""))
                    ))
            
            return containers
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get container status: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse docker ps output: {e}")
            return []
    
    def _get_cluster_from_name(self, container_name: str) -> str:
        """Get cluster name from container name"""
        for expected in self.expected_containers:
            if expected["name"] in container_name:
                return expected["cluster"]
        return "unknown"
    
    def _extract_port_from_status(self, status: str) -> Optional[int]:
        """Extract port from container status"""
        # This is a simplified extraction - in practice, you might need more sophisticated parsing
        if "8080" in status:
            return 8080
        elif "8084" in status:
            return 8084
        elif "8085" in status:
            return 8085
        elif "8086" in status:
            return 8086
        elif "8087" in status:
            return 8087
        elif "8089" in status:
            return 8089
        elif "8090" in status:
            return 8090
        elif "8091" in status:
            return 8091
        elif "8092" in status:
            return 8092
        elif "8093" in status:
            return 8093
        elif "8095" in status:
            return 8095
        elif "27017" in status:
            return 27017
        elif "6379" in status:
            return 6379
        elif "9200" in status:
            return 9200
        elif "8500" in status:
            return 8500
        return None
    
    async def get_container_health(self, container_name: str) -> Optional[str]:
        """Get container health status"""
        try:
            result = subprocess.run(
                ["docker", "inspect", container_name, "--format", "{{.State.Health.Status}}"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    async def get_container_stats(self, container_name: str) -> Optional[Dict[str, Any]]:
        """Get container resource usage statistics"""
        try:
            result = subprocess.run(
                ["docker", "stats", container_name, "--no-stream", "--format", "json"],
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.stdout.strip():
                stats = json.loads(result.stdout.strip())
                return {
                    "cpu_usage": self._parse_cpu_usage(stats.get("CPUPerc", "0%")),
                    "memory_usage": self._parse_memory_usage(stats.get("MemUsage", "0B / 0B")),
                    "memory_limit": stats.get("MemLimit", "0B"),
                    "network_io": stats.get("NetIO", "0B / 0B"),
                    "block_io": stats.get("BlockIO", "0B / 0B")
                }
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            pass
        return None
    
    def _parse_cpu_usage(self, cpu_str: str) -> float:
        """Parse CPU usage percentage from string"""
        try:
            return float(cpu_str.replace("%", ""))
        except ValueError:
            return 0.0
    
    def _parse_memory_usage(self, memory_str: str) -> float:
        """Parse memory usage from string"""
        try:
            # Format: "123.4MiB / 1.5GiB"
            usage_part = memory_str.split(" / ")[0]
            return float(usage_part.replace("MiB", "").replace("GiB", "").replace("B", ""))
        except (ValueError, IndexError):
            return 0.0
    
    async def validate_container(self, expected_container: Dict[str, Any]) -> ContainerValidationResult:
        """Validate a single container"""
        container_name = expected_container["name"]
        
        try:
            # Get container status
            containers = await self.get_container_status()
            running_container = next(
                (c for c in containers if expected_container["name"] in c.name), 
                None
            )
            
            if not running_container:
                return ContainerValidationResult(
                    container_name=container_name,
                    is_running=False,
                    is_healthy=False,
                    cluster=expected_container["cluster"],
                    status="not_running",
                    error_message="Container not found in docker ps"
                )
            
            # Check if container is running
            is_running = "Up" in running_container.status
            
            # Get health status if health check is enabled
            health_status = None
            is_healthy = is_running  # Default to running status
            
            if expected_container.get("health_check", False):
                health_status = await self.get_container_health(container_name)
                if health_status:
                    is_healthy = health_status == "healthy"
            
            # Get resource usage
            resource_usage = await self.get_container_stats(container_name)
            
            return ContainerValidationResult(
                container_name=container_name,
                is_running=is_running,
                is_healthy=is_healthy,
                cluster=expected_container["cluster"],
                status=running_container.status,
                health_status=health_status,
                resource_usage=resource_usage
            )
        
        except Exception as e:
            return ContainerValidationResult(
                container_name=container_name,
                is_running=False,
                is_healthy=False,
                cluster=expected_container["cluster"],
                status="error",
                error_message=str(e)
            )
    
    async def validate_all_containers(self) -> List[ContainerValidationResult]:
        """Validate all expected containers"""
        tasks = [self.validate_container(container) for container in self.expected_containers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and convert to ContainerValidationResult
        validation_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                validation_results.append(ContainerValidationResult(
                    container_name=self.expected_containers[i]["name"],
                    is_running=False,
                    is_healthy=False,
                    cluster=self.expected_containers[i]["cluster"],
                    status="error",
                    error_message=str(result)
                ))
            else:
                validation_results.append(result)
        
        return validation_results
    
    def generate_container_report(self, results: List[ContainerValidationResult]) -> Dict[str, Any]:
        """Generate comprehensive container validation report"""
        total_containers = len(results)
        running_containers = sum(1 for r in results if r.is_running)
        healthy_containers = sum(1 for r in results if r.is_healthy)
        stopped_containers = total_containers - running_containers
        
        # Group by cluster
        cluster_stats = {}
        for result in results:
            cluster = result.cluster
            if cluster not in cluster_stats:
                cluster_stats[cluster] = {
                    "total": 0, "running": 0, "healthy": 0, "stopped": 0
                }
            cluster_stats[cluster]["total"] += 1
            if result.is_running:
                cluster_stats[cluster]["running"] += 1
            if result.is_healthy:
                cluster_stats[cluster]["healthy"] += 1
            if not result.is_running:
                cluster_stats[cluster]["stopped"] += 1
        
        # Calculate cluster health percentages
        for cluster in cluster_stats:
            total = cluster_stats[cluster]["total"]
            running = cluster_stats[cluster]["running"]
            healthy = cluster_stats[cluster]["healthy"]
            cluster_stats[cluster]["running_percentage"] = (running / total) * 100
            cluster_stats[cluster]["healthy_percentage"] = (healthy / total) * 100
        
        # Group by status
        running = [r for r in results if r.is_running]
        stopped = [r for r in results if not r.is_running]
        unhealthy = [r for r in results if r.is_running and not r.is_healthy]
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_containers": total_containers,
                "running_containers": running_containers,
                "healthy_containers": healthy_containers,
                "stopped_containers": stopped_containers,
                "running_percentage": (running_containers / total_containers) * 100,
                "healthy_percentage": (healthy_containers / total_containers) * 100
            },
            "cluster_breakdown": cluster_stats,
            "running_containers": [
                {
                    "name": r.container_name,
                    "cluster": r.cluster,
                    "status": r.status,
                    "health_status": r.health_status,
                    "resource_usage": r.resource_usage
                }
                for r in running
            ],
            "stopped_containers": [
                {
                    "name": r.container_name,
                    "cluster": r.cluster,
                    "status": r.status,
                    "error": r.error_message
                }
                for r in stopped
            ],
            "unhealthy_containers": [
                {
                    "name": r.container_name,
                    "cluster": r.cluster,
                    "status": r.status,
                    "health_status": r.health_status,
                    "error": r.error_message
                }
                for r in unhealthy
            ]
        }
        
        return report


class TestContainerValidation:
    """Pytest test class for container validation"""
    
    @pytest.fixture
    def container_validator(self):
        """Fixture for ContainerValidator"""
        return ContainerValidator()
    
    @pytest.mark.asyncio
    async def test_all_containers_running(self, container_validator):
        """Test that all containers are running"""
        results = await container_validator.validate_all_containers()
        report = container_validator.generate_container_report(results)
        
        # Log the container report
        logger.info(f"Container Report: {report['summary']}")
        
        # Assert all containers are running
        stopped_containers = [r for r in results if not r.is_running]
        
        if stopped_containers:
            stopped_names = [r.container_name for r in stopped_containers]
            pytest.fail(f"Stopped containers: {stopped_names}")
        
        # Assert 100% running rate
        assert report["summary"]["running_percentage"] == 100.0
        assert report["summary"]["stopped_containers"] == 0
    
    @pytest.mark.asyncio
    async def test_all_containers_healthy(self, container_validator):
        """Test that all containers are healthy"""
        results = await container_validator.validate_all_containers()
        report = container_validator.generate_container_report(results)
        
        # Assert all containers are healthy
        unhealthy_containers = [r for r in results if r.is_running and not r.is_healthy]
        
        if unhealthy_containers:
            unhealthy_names = [r.container_name for r in unhealthy_containers]
            pytest.fail(f"Unhealthy containers: {unhealthy_names}")
        
        # Assert 100% healthy rate
        assert report["summary"]["healthy_percentage"] == 100.0
    
    @pytest.mark.asyncio
    async def test_api_gateway_container(self, container_validator):
        """Test API Gateway container"""
        api_gateway = next(c for c in container_validator.expected_containers if c["name"] == "lucid-api-gateway")
        result = await container_validator.validate_container(api_gateway)
        
        assert result.is_running, f"API Gateway container not running: {result.error_message}"
        assert result.is_healthy, f"API Gateway container not healthy: {result.health_status}"
    
    @pytest.mark.asyncio
    async def test_blockchain_containers(self, container_validator):
        """Test Blockchain Core containers"""
        blockchain_containers = [
            "lucid-blockchain-engine", "lucid-session-anchoring", 
            "lucid-block-manager", "lucid-data-chain"
        ]
        
        for container_name in blockchain_containers:
            container = next(c for c in container_validator.expected_containers if c["name"] == container_name)
            result = await container_validator.validate_container(container)
            
            assert result.is_running, f"{container_name} not running: {result.error_message}"
            assert result.is_healthy, f"{container_name} not healthy: {result.health_status}"
    
    @pytest.mark.asyncio
    async def test_database_containers(self, container_validator):
        """Test database containers"""
        db_containers = ["lucid-mongodb", "lucid-redis", "lucid-elasticsearch"]
        
        for container_name in db_containers:
            container = next(c for c in container_validator.expected_containers if c["name"] == container_name)
            result = await container_validator.validate_container(container)
            
            assert result.is_running, f"{container_name} not running: {result.error_message}"
            assert result.is_healthy, f"{container_name} not healthy: {result.health_status}"
    
    @pytest.mark.asyncio
    async def test_container_resource_usage(self, container_validator):
        """Test that containers are not using excessive resources"""
        results = await container_validator.validate_all_containers()
        running_containers = [r for r in results if r.is_running and r.resource_usage]
        
        for result in running_containers:
            resource_usage = result.resource_usage
            
            # Check CPU usage (should be less than 80% under normal load)
            if resource_usage.get("cpu_usage"):
                assert resource_usage["cpu_usage"] < 80.0, \
                    f"{result.container_name} CPU usage {resource_usage['cpu_usage']}% exceeds 80%"
            
            # Check memory usage (should be reasonable - this is more complex to validate)
            if resource_usage.get("memory_usage"):
                # This is a simplified check - in practice, you might want more sophisticated memory validation
                assert resource_usage["memory_usage"] > 0, \
                    f"{result.container_name} has invalid memory usage"


if __name__ == "__main__":
    """Run container validation standalone"""
    import json
    
    async def main():
        validator = ContainerValidator()
        results = await validator.validate_all_containers()
        report = validator.generate_container_report(results)
        
        print(json.dumps(report, indent=2))
        
        # Exit with error code if any containers are not running
        if report["summary"]["stopped_containers"] > 0:
            exit(1)
    
    asyncio.run(main())
