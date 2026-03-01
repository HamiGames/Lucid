"""
Endpoint management and service discovery for Lucid networking.

This module provides comprehensive endpoint management functionality including:
- Service registry and discovery
- Health checks and monitoring
- Load balancing
- Endpoint validation
- Service mesh integration
- Circuit breaker patterns
- Connection pooling
"""

import asyncio
import logging
import time
import hashlib
import json
import random
from typing import Optional, Dict, List, Tuple, Any, Union, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse, urljoin
import aiohttp
import aiofiles
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Configure logging
logger = logging.getLogger(__name__)

class EndpointStatus(Enum):
    """Endpoint status enumeration."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"
    OVERLOADED = "overloaded"

class LoadBalancingStrategy(Enum):
    """Load balancing strategy enumeration."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RANDOM = "random"
    IP_HASH = "ip_hash"
    LEAST_RESPONSE_TIME = "least_response_time"

class CircuitBreakerState(Enum):
    """Circuit breaker state enumeration."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass
class EndpointInfo:
    """Information about a service endpoint."""
    id: str
    name: str
    url: str
    port: int
    protocol: str
    weight: int = 1
    priority: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'port': self.port,
            'protocol': self.protocol,
            'weight': self.weight,
            'priority': self.priority,
            'tags': self.tags,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EndpointInfo':
        """Create from dictionary."""
        data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        data['updated_at'] = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
        return cls(**data)

@dataclass
class EndpointHealth:
    """Endpoint health information."""
    endpoint_id: str
    status: EndpointStatus
    response_time: float
    last_check: datetime
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    error_rate: float = 0.0
    availability: float = 100.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'endpoint_id': self.endpoint_id,
            'status': self.status.value,
            'response_time': self.response_time,
            'last_check': self.last_check.isoformat(),
            'consecutive_failures': self.consecutive_failures,
            'consecutive_successes': self.consecutive_successes,
            'error_rate': self.error_rate,
            'availability': self.availability,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EndpointHealth':
        """Create from dictionary."""
        data['status'] = EndpointStatus(data['status'])
        data['last_check'] = datetime.fromisoformat(data['last_check'].replace('Z', '+00:00'))
        return cls(**data)

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    half_open_max_calls: int = 3
    success_threshold: int = 2

class CircuitBreaker:
    """Circuit breaker implementation for endpoint protection."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        """Check if requests can be executed."""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if (self.last_failure_time and 
                time.time() - self.last_failure_time >= self.config.recovery_timeout):
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return self.half_open_calls < self.config.half_open_max_calls
        return False
    
    def on_success(self):
        """Handle successful request."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            self.half_open_calls += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.half_open_calls = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0
    
    def on_failure(self):
        """Handle failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.config.half_open_max_calls:
                self.state = CircuitBreakerState.OPEN
                self.success_count = 0
                self.half_open_calls = 0
        elif self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN

class LoadBalancer:
    """Load balancer for endpoint distribution."""
    
    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self.endpoints: List[EndpointInfo] = []
        self.health_status: Dict[str, EndpointHealth] = {}
        self.current_index = 0
        self.connection_counts: Dict[str, int] = {}
        self.response_times: Dict[str, List[float]] = {}
    
    def add_endpoint(self, endpoint: EndpointInfo):
        """Add endpoint to load balancer."""
        self.endpoints.append(endpoint)
        self.connection_counts[endpoint.id] = 0
        self.response_times[endpoint.id] = []
        logger.info(f"Added endpoint {endpoint.name} ({endpoint.id}) to load balancer")
    
    def remove_endpoint(self, endpoint_id: str):
        """Remove endpoint from load balancer."""
        self.endpoints = [ep for ep in self.endpoints if ep.id != endpoint_id]
        self.connection_counts.pop(endpoint_id, None)
        self.response_times.pop(endpoint_id, None)
        logger.info(f"Removed endpoint {endpoint_id} from load balancer")
    
    def update_health(self, endpoint_id: str, health: EndpointHealth):
        """Update endpoint health status."""
        self.health_status[endpoint_id] = health
        if health.response_time > 0:
            self.response_times[endpoint_id].append(health.response_time)
            # Keep only last 100 response times
            if len(self.response_times[endpoint_id]) > 100:
                self.response_times[endpoint_id] = self.response_times[endpoint_id][-100:]
    
    def get_healthy_endpoints(self) -> List[EndpointInfo]:
        """Get list of healthy endpoints."""
        healthy_endpoints = []
        for endpoint in self.endpoints:
            health = self.health_status.get(endpoint.id)
            if (health and 
                health.status == EndpointStatus.HEALTHY and 
                health.availability > 95.0):
                healthy_endpoints.append(endpoint)
        return healthy_endpoints
    
    def select_endpoint(self, client_ip: Optional[str] = None) -> Optional[EndpointInfo]:
        """Select endpoint based on load balancing strategy."""
        healthy_endpoints = self.get_healthy_endpoints()
        if not healthy_endpoints:
            return None
        
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_selection(healthy_endpoints)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_selection(healthy_endpoints)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_selection(healthy_endpoints)
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return self._random_selection(healthy_endpoints)
        elif self.strategy == LoadBalancingStrategy.IP_HASH:
            return self._ip_hash_selection(healthy_endpoints, client_ip)
        elif self.strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
            return self._least_response_time_selection(healthy_endpoints)
        else:
            return healthy_endpoints[0]
    
    def _round_robin_selection(self, endpoints: List[EndpointInfo]) -> EndpointInfo:
        """Round robin selection."""
        endpoint = endpoints[self.current_index % len(endpoints)]
        self.current_index = (self.current_index + 1) % len(endpoints)
        return endpoint
    
    def _least_connections_selection(self, endpoints: List[EndpointInfo]) -> EndpointInfo:
        """Least connections selection."""
        min_connections = min(self.connection_counts.get(ep.id, 0) for ep in endpoints)
        for endpoint in endpoints:
            if self.connection_counts.get(endpoint.id, 0) == min_connections:
                return endpoint
        return endpoints[0]
    
    def _weighted_round_robin_selection(self, endpoints: List[EndpointInfo]) -> EndpointInfo:
        """Weighted round robin selection."""
        total_weight = sum(ep.weight for ep in endpoints)
        if total_weight == 0:
            return endpoints[0]
        
        current_weight = 0
        for endpoint in endpoints:
            current_weight += endpoint.weight
            if self.current_index % total_weight < current_weight:
                self.current_index = (self.current_index + 1) % total_weight
                return endpoint
        
        return endpoints[0]
    
    def _random_selection(self, endpoints: List[EndpointInfo]) -> EndpointInfo:
        """Random selection."""
        return random.choice(endpoints)
    
    def _ip_hash_selection(self, endpoints: List[EndpointInfo], client_ip: Optional[str]) -> EndpointInfo:
        """IP hash selection."""
        if not client_ip:
            return self._random_selection(endpoints)
        
        hash_value = int(hashlib.md5(client_ip.encode()).hexdigest(), 16)
        index = hash_value % len(endpoints)
        return endpoints[index]
    
    def _least_response_time_selection(self, endpoints: List[EndpointInfo]) -> EndpointInfo:
        """Least response time selection."""
        best_endpoint = endpoints[0]
        best_avg_time = float('inf')
        
        for endpoint in endpoints:
            times = self.response_times.get(endpoint.id, [])
            if times:
                avg_time = sum(times) / len(times)
                if avg_time < best_avg_time:
                    best_avg_time = avg_time
                    best_endpoint = endpoint
        
        return best_endpoint
    
    def increment_connections(self, endpoint_id: str):
        """Increment connection count for endpoint."""
        self.connection_counts[endpoint_id] = self.connection_counts.get(endpoint_id, 0) + 1
    
    def decrement_connections(self, endpoint_id: str):
        """Decrement connection count for endpoint."""
        count = self.connection_counts.get(endpoint_id, 0)
        if count > 0:
            self.connection_counts[endpoint_id] = count - 1

class ServiceRegistry:
    """Service registry for endpoint management."""
    
    def __init__(self, registry_file: Optional[str] = None):
        self.endpoints: Dict[str, EndpointInfo] = {}
        self.health_status: Dict[str, EndpointHealth] = {}
        self.registry_file = registry_file or "service_registry.json"
        self.load_balancers: Dict[str, LoadBalancer] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.health_check_interval = 30
        self.health_check_timeout = 5
        self._health_check_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the service registry."""
        await self.load_registry()
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Service registry started")
    
    async def stop(self):
        """Stop the service registry."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        await self.save_registry()
        logger.info("Service registry stopped")
    
    async def register_endpoint(self, endpoint: EndpointInfo) -> bool:
        """Register a new endpoint."""
        try:
            self.endpoints[endpoint.id] = endpoint
            await self._initialize_endpoint_health(endpoint)
            await self.save_registry()
            logger.info(f"Registered endpoint {endpoint.name} ({endpoint.id})")
            return True
        except Exception as e:
            logger.error(f"Failed to register endpoint {endpoint.id}: {e}")
            return False
    
    async def unregister_endpoint(self, endpoint_id: str) -> bool:
        """Unregister an endpoint."""
        try:
            if endpoint_id in self.endpoints:
                del self.endpoints[endpoint_id]
                self.health_status.pop(endpoint_id, None)
                self.circuit_breakers.pop(endpoint_id, None)
                await self.save_registry()
                logger.info(f"Unregistered endpoint {endpoint_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to unregister endpoint {endpoint_id}: {e}")
            return False
    
    async def get_endpoint(self, endpoint_id: str) -> Optional[EndpointInfo]:
        """Get endpoint by ID."""
        return self.endpoints.get(endpoint_id)
    
    async def list_endpoints(self, tags: Optional[List[str]] = None) -> List[EndpointInfo]:
        """List endpoints, optionally filtered by tags."""
        endpoints = list(self.endpoints.values())
        if tags:
            filtered_endpoints = []
            for endpoint in endpoints:
                if any(tag in endpoint.tags for tag in tags):
                    filtered_endpoints.append(endpoint)
            return filtered_endpoints
        return endpoints
    
    async def discover_services(self, service_name: str) -> List[EndpointInfo]:
        """Discover services by name."""
        return [ep for ep in self.endpoints.values() if ep.name == service_name]
    
    async def get_load_balancer(self, service_name: str, 
                              strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN) -> LoadBalancer:
        """Get or create load balancer for service."""
        if service_name not in self.load_balancers:
            lb = LoadBalancer(strategy)
            endpoints = await self.discover_services(service_name)
            for endpoint in endpoints:
                lb.add_endpoint(endpoint)
            self.load_balancers[service_name] = lb
        
        return self.load_balancers[service_name]
    
    async def _initialize_endpoint_health(self, endpoint: EndpointInfo):
        """Initialize health status for endpoint."""
        health = EndpointHealth(
            endpoint_id=endpoint.id,
            status=EndpointStatus.UNKNOWN,
            response_time=0.0,
            last_check=datetime.now(timezone.utc)
        )
        self.health_status[endpoint.id] = health
        
        # Initialize circuit breaker
        circuit_config = CircuitBreakerConfig()
        self.circuit_breakers[endpoint.id] = CircuitBreaker(circuit_config)
    
    async def _health_check_loop(self):
        """Background health check loop."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
    
    async def _perform_health_checks(self):
        """Perform health checks on all endpoints."""
        tasks = []
        for endpoint in self.endpoints.values():
            task = asyncio.create_task(self._check_endpoint_health(endpoint))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_endpoint_health(self, endpoint: EndpointInfo):
        """Check health of a specific endpoint."""
        start_time = time.time()
        health_url = f"{endpoint.protocol}://{endpoint.url}:{endpoint.port}/health"
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.health_check_timeout)) as session:
                async with session.get(health_url) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        await self._update_health_success(endpoint, response_time)
                    else:
                        await self._update_health_failure(endpoint, response_time)
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            await self._update_health_failure(endpoint, response_time)
            logger.debug(f"Health check failed for {endpoint.id}: {e}")
    
    async def _update_health_success(self, endpoint: EndpointInfo, response_time: float):
        """Update health status on successful check."""
        health = self.health_status.get(endpoint.id)
        if health:
            health.status = EndpointStatus.HEALTHY
            health.response_time = response_time
            health.last_check = datetime.now(timezone.utc)
            health.consecutive_successes += 1
            health.consecutive_failures = 0
            
            # Update load balancers
            for lb in self.load_balancers.values():
                lb.update_health(endpoint.id, health)
            
            # Update circuit breaker
            circuit_breaker = self.circuit_breakers.get(endpoint.id)
            if circuit_breaker:
                circuit_breaker.on_success()
    
    async def _update_health_failure(self, endpoint: EndpointInfo, response_time: float):
        """Update health status on failed check."""
        health = self.health_status.get(endpoint.id)
        if health:
            health.consecutive_failures += 1
            health.consecutive_successes = 0
            health.last_check = datetime.now(timezone.utc)
            health.response_time = response_time
            
            # Update status based on failure count
            if health.consecutive_failures >= 3:
                health.status = EndpointStatus.UNHEALTHY
            elif health.consecutive_failures >= 2:
                health.status = EndpointStatus.OVERLOADED
            
            # Update load balancers
            for lb in self.load_balancers.values():
                lb.update_health(endpoint.id, health)
            
            # Update circuit breaker
            circuit_breaker = self.circuit_breakers.get(endpoint.id)
            if circuit_breaker:
                circuit_breaker.on_failure()
    
    async def load_registry(self):
        """Load registry from file."""
        try:
            if Path(self.registry_file).exists():
                async with aiofiles.open(self.registry_file, 'r') as f:
                    data = json.loads(await f.read())
                    
                    # Load endpoints
                    for endpoint_data in data.get('endpoints', []):
                        endpoint = EndpointInfo.from_dict(endpoint_data)
                        self.endpoints[endpoint.id] = endpoint
                        await self._initialize_endpoint_health(endpoint)
                    
                    # Load health status
                    for health_data in data.get('health_status', []):
                        health = EndpointHealth.from_dict(health_data)
                        self.health_status[health.endpoint_id] = health
                    
                    logger.info(f"Loaded {len(self.endpoints)} endpoints from registry")
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
    
    async def save_registry(self):
        """Save registry to file."""
        try:
            data = {
                'endpoints': [ep.to_dict() for ep in self.endpoints.values()],
                'health_status': [h.to_dict() for h in self.health_status.values()],
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            async with aiofiles.open(self.registry_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
            
            logger.debug(f"Saved registry with {len(self.endpoints)} endpoints")
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")

class EndpointManager:
    """Main endpoint manager class."""
    
    def __init__(self, registry_file: Optional[str] = None):
        self.registry = ServiceRegistry(registry_file)
        self.http_session: Optional[aiohttp.ClientSession] = None
    
    async def start(self):
        """Start the endpoint manager."""
        await self.registry.start()
        self.http_session = aiohttp.ClientSession()
        logger.info("Endpoint manager started")
    
    async def stop(self):
        """Stop the endpoint manager."""
        await self.registry.stop()
        if self.http_session:
            await self.http_session.close()
        logger.info("Endpoint manager stopped")
    
    async def register_service(self, name: str, url: str, port: int, 
                             protocol: str = "http", **kwargs) -> str:
        """Register a new service endpoint."""
        endpoint_id = f"{name}_{hashlib.md5(f'{url}:{port}'.encode()).hexdigest()[:8]}"
        
        endpoint = EndpointInfo(
            id=endpoint_id,
            name=name,
            url=url,
            port=port,
            protocol=protocol,
            **kwargs
        )
        
        success = await self.registry.register_endpoint(endpoint)
        return endpoint_id if success else ""
    
    async def unregister_service(self, endpoint_id: str) -> bool:
        """Unregister a service endpoint."""
        return await self.registry.unregister_endpoint(endpoint_id)
    
    async def discover_service(self, service_name: str) -> List[EndpointInfo]:
        """Discover service endpoints."""
        return await self.registry.discover_services(service_name)
    
    async def get_service_endpoint(self, service_name: str, 
                                 strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
                                 client_ip: Optional[str] = None) -> Optional[EndpointInfo]:
        """Get a service endpoint using load balancing."""
        load_balancer = await self.registry.get_load_balancer(service_name, strategy)
        return load_balancer.select_endpoint(client_ip)
    
    async def make_request(self, service_name: str, path: str, method: str = "GET",
                          headers: Optional[Dict[str, str]] = None,
                          data: Optional[Any] = None,
                          client_ip: Optional[str] = None) -> Optional[aiohttp.ClientResponse]:
        """Make a request to a service endpoint."""
        endpoint = await self.get_service_endpoint(service_name, client_ip=client_ip)
        if not endpoint:
            logger.error(f"No healthy endpoints found for service {service_name}")
            return None
        
        circuit_breaker = self.registry.circuit_breakers.get(endpoint.id)
        if circuit_breaker and not circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker open for endpoint {endpoint.id}")
            return None
        
        url = f"{endpoint.protocol}://{endpoint.url}:{endpoint.port}{path}"
        
        try:
            # Increment connection count
            load_balancer = await self.registry.get_load_balancer(service_name)
            load_balancer.increment_connections(endpoint.id)
            
            response = await self.http_session.request(
                method=method,
                url=url,
                headers=headers,
                data=data
            )
            
            # Update circuit breaker
            if circuit_breaker:
                if response.status < 500:
                    circuit_breaker.on_success()
                else:
                    circuit_breaker.on_failure()
            
            return response
            
        except Exception as e:
            # Update circuit breaker
            if circuit_breaker:
                circuit_breaker.on_failure()
            logger.error(f"Request failed to {endpoint.id}: {e}")
            return None
        finally:
            # Decrement connection count
            load_balancer.decrement_connections(endpoint.id)
    
    async def get_service_health(self, service_name: str) -> Dict[str, Any]:
        """Get health information for a service."""
        endpoints = await self.discover_service(service_name)
        health_info = {
            'service_name': service_name,
            'total_endpoints': len(endpoints),
            'healthy_endpoints': 0,
            'unhealthy_endpoints': 0,
            'endpoints': []
        }
        
        for endpoint in endpoints:
            health = self.registry.health_status.get(endpoint.id)
            endpoint_info = {
                'id': endpoint.id,
                'url': f"{endpoint.protocol}://{endpoint.url}:{endpoint.port}",
                'status': health.status.value if health else 'unknown',
                'response_time': health.response_time if health else 0.0,
                'availability': health.availability if health else 0.0
            }
            health_info['endpoints'].append(endpoint_info)
            
            if health and health.status == EndpointStatus.HEALTHY:
                health_info['healthy_endpoints'] += 1
            else:
                health_info['unhealthy_endpoints'] += 1
        
        return health_info

# Global instance
_endpoint_manager: Optional[EndpointManager] = None

async def get_endpoint_manager() -> EndpointManager:
    """Get the global endpoint manager instance."""
    global _endpoint_manager
    if _endpoint_manager is None:
        _endpoint_manager = EndpointManager()
        await _endpoint_manager.start()
    return _endpoint_manager

async def initialize_endpoint_manager(registry_file: Optional[str] = None) -> EndpointManager:
    """Initialize the global endpoint manager."""
    global _endpoint_manager
    if _endpoint_manager is None:
        _endpoint_manager = EndpointManager(registry_file)
        await _endpoint_manager.start()
    return _endpoint_manager

def create_endpoint_info(name: str, url: str, port: int, 
                        protocol: str = "http", **kwargs) -> EndpointInfo:
    """Create an endpoint info object."""
    endpoint_id = f"{name}_{hashlib.md5(f'{url}:{port}'.encode()).hexdigest()[:8]}"
    return EndpointInfo(
        id=endpoint_id,
        name=name,
        url=url,
        port=port,
        protocol=protocol,
        **kwargs
    )

def create_load_balancer(strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN) -> LoadBalancer:
    """Create a load balancer instance."""
    return LoadBalancer(strategy)

def create_circuit_breaker(config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """Create a circuit breaker instance."""
    if config is None:
        config = CircuitBreakerConfig()
    return CircuitBreaker(config)
