"""
Health Check Module

This module contains health check utilities for the Blockchain API.
Handles health checks for various system components and services.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

@dataclass
class HealthCheckResult:
    """Health check result."""
    name: str
    status: str  # "healthy", "warning", "error"
    message: str
    response_time_ms: float
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None

class HealthChecker:
    """Health checker for various system components."""
    
    def __init__(self):
        self.checks = {}
        self.last_check_results = {}
        self.check_intervals = {}
        self.cache_duration = 30  # seconds
    
    def register_check(self, name: str, check_func, interval: int = 30):
        """Register a health check function."""
        self.checks[name] = check_func
        self.check_intervals[name] = interval
        logger.info(f"Registered health check: {name}")
    
    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check."""
        if name not in self.checks:
            return HealthCheckResult(
                name=name,
                status="error",
                message=f"Health check '{name}' not found",
                response_time_ms=0.0,
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
            
            if isinstance(result, dict):
                status = result.get("status", "healthy")
                message = result.get("message", "Check completed successfully")
                details = result.get("details")
            else:
                status = "healthy" if result else "error"
                message = "Check completed successfully" if result else "Check failed"
                details = None
            
            health_result = HealthCheckResult(
                name=name,
                status=status,
                message=message,
                response_time_ms=response_time,
                timestamp=datetime.now(),
                details=details
            )
            
            self.last_check_results[name] = health_result
            return health_result
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Health check '{name}' failed: {e}")
            
            health_result = HealthCheckResult(
                name=name,
                status="error",
                message=f"Check failed: {str(e)}",
                response_time_ms=response_time,
                timestamp=datetime.now()
            )
            
            self.last_check_results[name] = health_result
            return health_result
    
    async def run_all_checks(self) -> List[HealthCheckResult]:
        """Run all registered health checks."""
        results = []
        
        for name in self.checks:
            result = await self.run_check(name)
            results.append(result)
        
        return results
    
    async def run_cached_check(self, name: str) -> HealthCheckResult:
        """Run a health check with caching."""
        if name in self.last_check_results:
            last_result = self.last_check_results[name]
            time_since_last = (datetime.now() - last_result.timestamp).total_seconds()
            
            if time_since_last < self.cache_duration:
                return last_result
        
        return await self.run_check(name)
    
    def get_overall_status(self, results: List[HealthCheckResult]) -> str:
        """Get overall health status from check results."""
        if not results:
            return "unknown"
        
        statuses = [result.status for result in results]
        
        if "error" in statuses:
            return "error"
        elif "warning" in statuses:
            return "warning"
        else:
            return "healthy"
    
    def get_health_summary(self, results: List[HealthCheckResult]) -> Dict[str, Any]:
        """Get health summary from check results."""
        overall_status = self.get_overall_status(results)
        
        status_counts = {}
        for result in results:
            status_counts[result.status] = status_counts.get(result.status, 0) + 1
        
        total_checks = len(results)
        healthy_checks = status_counts.get("healthy", 0)
        warning_checks = status_counts.get("warning", 0)
        error_checks = status_counts.get("error", 0)
        
        return {
            "overall_status": overall_status,
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "warning_checks": warning_checks,
            "error_checks": error_checks,
            "health_percentage": (healthy_checks / total_checks * 100) if total_checks > 0 else 0
        }

# Global health checker instance
health_checker = HealthChecker()

# Default health check functions
async def check_database_health() -> Dict[str, Any]:
    """Check database connectivity and health."""
    try:
        # Placeholder implementation
        # In production, this would check actual database connection
        return {
            "status": "healthy",
            "message": "Database connection is healthy",
            "details": {
                "connection_pool_size": 10,
                "active_connections": 5,
                "query_response_time": 15.5
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Database health check failed: {str(e)}",
            "details": {"error": str(e)}
        }

async def check_redis_health() -> Dict[str, Any]:
    """Check Redis connectivity and health."""
    try:
        # Placeholder implementation
        # In production, this would check actual Redis connection
        return {
            "status": "healthy",
            "message": "Redis connection is healthy",
            "details": {
                "memory_usage": "45.2 MB",
                "connected_clients": 3,
                "uptime": "7 days, 12 hours"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Redis health check failed: {str(e)}",
            "details": {"error": str(e)}
        }

async def check_blockchain_sync_health() -> Dict[str, Any]:
    """Check blockchain synchronization health."""
    try:
        # Placeholder implementation
        # In production, this would check actual blockchain sync status
        return {
            "status": "healthy",
            "message": "Blockchain is synchronized",
            "details": {
                "current_height": 12345,
                "sync_status": "synced",
                "peer_count": 15,
                "last_block_time": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Blockchain sync health check failed: {str(e)}",
            "details": {"error": str(e)}
        }

async def check_consensus_health() -> Dict[str, Any]:
    """Check consensus mechanism health."""
    try:
        # Placeholder implementation
        # In production, this would check actual consensus health
        return {
            "status": "healthy",
            "message": "Consensus mechanism is healthy",
            "details": {
                "active_validators": 23,
                "consensus_round": 12345,
                "consensus_phase": "voting",
                "stake_distribution": "balanced"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Consensus health check failed: {str(e)}",
            "details": {"error": str(e)}
        }

async def check_api_performance() -> Dict[str, Any]:
    """Check API performance metrics."""
    try:
        # Placeholder implementation
        # In production, this would check actual API performance
        return {
            "status": "healthy",
            "message": "API performance is within normal ranges",
            "details": {
                "average_response_time": 150.5,
                "requests_per_second": 45.2,
                "error_rate": 0.02,
                "active_connections": 12
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"API performance check failed: {str(e)}",
            "details": {"error": str(e)}
        }

async def check_system_resources() -> Dict[str, Any]:
    """Check system resource usage."""
    try:
        import psutil
        
        # Get system metrics - use interval=None for non-blocking call (uses last measurement)
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Determine status based on thresholds
        status = "healthy"
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
            status = "warning"
        if cpu_percent > 95 or memory.percent > 95 or disk.percent > 95:
            status = "error"
        
        return {
            "status": status,
            "message": "System resources are within acceptable ranges",
            "details": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_mb": memory.used / (1024 * 1024),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024 * 1024 * 1024)
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"System resources check failed: {str(e)}",
            "details": {"error": str(e)}
        }

# Register default health checks
health_checker.register_check("database", check_database_health, interval=30)
health_checker.register_check("redis", check_redis_health, interval=30)
health_checker.register_check("blockchain_sync", check_blockchain_sync_health, interval=60)
health_checker.register_check("consensus", check_consensus_health, interval=60)
health_checker.register_check("api_performance", check_api_performance, interval=30)
health_checker.register_check("system_resources", check_system_resources, interval=60)

class HealthCheckService:
    """Service for managing health checks."""
    
    def __init__(self, health_checker: HealthChecker):
        self.health_checker = health_checker
        self.start_time = datetime.now()
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        try:
            # Run all health checks
            results = await self.health_checker.run_all_checks()
            
            # Get summary
            summary = self.health_checker.get_health_summary(results)
            
            # Calculate uptime
            uptime = datetime.now() - self.start_time
            
            return {
                "status": summary["overall_status"],
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": uptime.total_seconds(),
                "uptime_formatted": str(uptime),
                "summary": summary,
                "checks": [
                    {
                        "name": result.name,
                        "status": result.status,
                        "message": result.message,
                        "response_time_ms": result.response_time_ms,
                        "timestamp": result.timestamp.isoformat(),
                        "details": result.details
                    }
                    for result in results
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def get_quick_health_status(self) -> Dict[str, Any]:
        """Get quick health status using cached results."""
        try:
            # Run cached checks
            results = []
            for name in self.health_checker.checks:
                result = await self.health_checker.run_cached_check(name)
                results.append(result)
            
            # Get summary
            summary = self.health_checker.get_health_summary(results)
            
            return {
                "status": summary["overall_status"],
                "timestamp": datetime.now().isoformat(),
                "summary": summary
            }
        except Exception as e:
            logger.error(f"Failed to get quick health status: {e}")
            return {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def get_health_check_details(self, check_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific health check."""
        try:
            result = await self.health_checker.run_check(check_name)
            
            return {
                "name": result.name,
                "status": result.status,
                "message": result.message,
                "response_time_ms": result.response_time_ms,
                "timestamp": result.timestamp.isoformat(),
                "details": result.details
            }
        except Exception as e:
            logger.error(f"Failed to get health check details for {check_name}: {e}")
            return {
                "name": check_name,
                "status": "error",
                "message": f"Failed to run health check: {str(e)}",
                "response_time_ms": 0.0,
                "timestamp": datetime.now().isoformat(),
                "details": {"error": str(e)}
            }

# Global health check service
health_check_service = HealthCheckService(health_checker)
