"""
LUCID Payment Systems - TRON Client Health Check Module
Comprehensive health checking for service dependencies
Following architecture patterns from build/docs/
"""

import asyncio
import logging
import os
import time
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Health check result"""
    component: str
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class HealthChecker:
    """
    Health checker for service components
    
    Supports:
    - Dependency health checks (MongoDB, Redis, TRON network)
    - Readiness vs liveness probes
    - Health check aggregation
    - Degraded state detection
    """
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.cache: Dict[str, HealthCheckResult] = {}
        self.cache_ttl = 5.0  # Cache results for 5 seconds
        self._lock = asyncio.Lock()
    
    def register_check(self, name: str, check_func: Callable):
        """Register a health check function"""
        self.checks[name] = check_func
        logger.info(f"Registered health check: {name}")
    
    async def check_component(self, name: str, use_cache: bool = True) -> HealthCheckResult:
        """
        Check health of a specific component
        
        Args:
            name: Component name
            use_cache: Use cached result if available
            
        Returns:
            HealthCheckResult
        """
        # Check cache
        if use_cache and name in self.cache:
            cached = self.cache[name]
            age = (datetime.now() - cached.timestamp).total_seconds()
            if age < self.cache_ttl:
                return cached
        
        # Run check
        if name not in self.checks:
            return HealthCheckResult(
                component=name,
                status=HealthStatus.UNKNOWN,
                message=f"Health check not registered: {name}",
                timestamp=datetime.now()
            )
        
        start_time = time.time()
        try:
            check_func = self.checks[name]
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()
            
            response_time = (time.time() - start_time) * 1000
            
            # Handle different result types
            if isinstance(result, HealthCheckResult):
                health_result = result
            elif isinstance(result, dict):
                health_result = HealthCheckResult(
                    component=name,
                    status=HealthStatus(result.get("status", "unknown")),
                    message=result.get("message", ""),
                    timestamp=datetime.now(),
                    response_time_ms=response_time,
                    details=result.get("details")
                )
            elif isinstance(result, bool):
                health_result = HealthCheckResult(
                    component=name,
                    status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                    message="Check completed",
                    timestamp=datetime.now(),
                    response_time_ms=response_time
                )
            else:
                health_result = HealthCheckResult(
                    component=name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Unexpected result type: {type(result)}",
                    timestamp=datetime.now(),
                    response_time_ms=response_time
                )
            
            # Update cache
            async with self._lock:
                self.cache[name] = health_result
            
            return health_result
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Health check failed for {name}: {e}")
            
            result = HealthCheckResult(
                component=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check error: {str(e)}",
                timestamp=datetime.now(),
                response_time_ms=response_time
            )
            
            async with self._lock:
                self.cache[name] = result
            
            return result
    
    async def check_all(self) -> Dict[str, HealthCheckResult]:
        """Check all registered components"""
        results = {}
        for name in self.checks.keys():
            results[name] = await self.check_component(name)
        return results
    
    async def get_overall_health(self) -> Dict[str, Any]:
        """
        Get overall health status
        
        Returns:
            Dictionary with overall status and component details
        """
        results = await self.check_all()
        
        # Determine overall status
        statuses = [r.status for r in results.values()]
        
        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall_status = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall_status = HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.UNKNOWN
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "components": {
                name: {
                    "status": result.status.value,
                    "message": result.message,
                    "response_time_ms": result.response_time_ms,
                    "details": result.details
                }
                for name, result in results.items()
            }
        }
    
    async def liveness_check(self) -> bool:
        """
        Liveness check - is the service running?
        
        Returns:
            True if service is alive
        """
        # Basic check - service is responding
        return True
    
    async def readiness_check(self) -> bool:
        """
        Readiness check - is the service ready to serve requests?
        
        Returns:
            True if service is ready
        """
        overall = await self.get_overall_health()
        return overall["status"] in ["healthy", "degraded"]


# MongoDB health check
async def check_mongodb() -> HealthCheckResult:
    """Check MongoDB connection health"""
    try:
        mongodb_url = os.getenv("MONGODB_URL") or os.getenv("MONGODB_URI")
        if not mongodb_url:
            return HealthCheckResult(
                component="mongodb",
                status=HealthStatus.UNHEALTHY,
                message="MONGODB_URL not configured",
                timestamp=datetime.now()
            )
        
        # Try to import motor (async MongoDB driver)
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
        except ImportError:
            return HealthCheckResult(
                component="mongodb",
                status=HealthStatus.UNKNOWN,
                message="Motor not available",
                timestamp=datetime.now()
            )
        
        # Quick connection test
        client = AsyncIOMotorClient(mongodb_url, serverSelectionTimeoutMS=2000)
        await client.admin.command('ping')
        client.close()
        
        return HealthCheckResult(
            component="mongodb",
            status=HealthStatus.HEALTHY,
            message="MongoDB connection successful",
            timestamp=datetime.now()
        )
        
    except Exception as e:
        return HealthCheckResult(
            component="mongodb",
            status=HealthStatus.UNHEALTHY,
            message=f"MongoDB connection failed: {str(e)}",
            timestamp=datetime.now()
        )


# Redis health check
async def check_redis() -> HealthCheckResult:
    """Check Redis connection health"""
    try:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            return HealthCheckResult(
                component="redis",
                status=HealthStatus.UNHEALTHY,
                message="REDIS_URL not configured",
                timestamp=datetime.now()
            )
        
        # Try to import redis
        try:
            import redis.asyncio as redis
        except ImportError:
            return HealthCheckResult(
                component="redis",
                status=HealthStatus.UNKNOWN,
                message="Redis async client not available",
                timestamp=datetime.now()
            )
        
        # Quick connection test
        client = redis.from_url(redis_url, socket_connect_timeout=2)
        await client.ping()
        await client.aclose()
        
        return HealthCheckResult(
            component="redis",
            status=HealthStatus.HEALTHY,
            message="Redis connection successful",
            timestamp=datetime.now()
        )
        
    except Exception as e:
        return HealthCheckResult(
            component="redis",
            status=HealthStatus.UNHEALTHY,
            message=f"Redis connection failed: {str(e)}",
            timestamp=datetime.now()
        )


# TRON network health check
async def check_tron_network() -> HealthCheckResult:
    """Check TRON network connectivity"""
    try:
        # Import tron_client_service
        from ..services.tron_client import tron_client_service
        
        # Check connection status
        if hasattr(tron_client_service, 'connection_status'):
            status = tron_client_service.connection_status
            if status.value == "connected":
                return HealthCheckResult(
                    component="tron_network",
                    status=HealthStatus.HEALTHY,
                    message="TRON network connected",
                    timestamp=datetime.now(),
                    details={
                        "network": tron_client_service.network,
                        "node_url": tron_client_service.node_url
                    }
                )
            else:
                return HealthCheckResult(
                    component="tron_network",
                    status=HealthStatus.UNHEALTHY,
                    message=f"TRON network status: {status.value}",
                    timestamp=datetime.now()
                )
        else:
            return HealthCheckResult(
                component="tron_network",
                status=HealthStatus.UNKNOWN,
                message="TRON client service not initialized",
                timestamp=datetime.now()
            )
            
    except Exception as e:
        return HealthCheckResult(
            component="tron_network",
            status=HealthStatus.UNHEALTHY,
            message=f"TRON network check failed: {str(e)}",
            timestamp=datetime.now()
        )


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get or create global health checker instance"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
        # Register default checks
        _health_checker.register_check("mongodb", check_mongodb)
        _health_checker.register_check("redis", check_redis)
        _health_checker.register_check("tron_network", check_tron_network)
    return _health_checker

