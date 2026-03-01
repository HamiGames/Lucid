"""
Monitoring Module

This module contains monitoring and metrics utilities for the Blockchain API.
Handles health checks, performance metrics, and system monitoring.
"""

import logging
import time
import psutil
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict, deque
import threading

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """System performance metrics."""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_used_gb: float
    disk_free_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    timestamp: datetime

@dataclass
class APIMetrics:
    """API performance metrics."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    requests_per_second: float
    active_connections: int
    timestamp: datetime

@dataclass
class BlockchainMetrics:
    """Blockchain-specific metrics."""
    current_height: int
    blocks_per_hour: float
    transactions_per_hour: float
    average_block_time: float
    network_hash_rate: float
    difficulty: float
    active_validators: int
    consensus_health: str
    timestamp: datetime

class MetricsCollector:
    """Metrics collector for system and API monitoring."""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.system_metrics_history = deque(maxlen=max_history)
        self.api_metrics_history = deque(maxlen=max_history)
        self.blockchain_metrics_history = deque(maxlen=max_history)
        
        # Request tracking
        self.request_counts = defaultdict(int)
        self.response_times = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
        
        # Performance tracking
        self.start_time = time.time()
        self.last_metrics_time = time.time()
        
        # Thread safety
        self.lock = threading.Lock()
    
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect system performance metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_used_gb = disk.used / (1024 * 1024 * 1024)
            disk_free_gb = disk.free / (1024 * 1024 * 1024)
            
            # Network usage
            network = psutil.net_io_counters()
            network_bytes_sent = network.bytes_sent
            network_bytes_recv = network.bytes_recv
            
            metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                disk_usage_percent=disk_usage_percent,
                disk_used_gb=disk_used_gb,
                disk_free_gb=disk_free_gb,
                network_bytes_sent=network_bytes_sent,
                network_bytes_recv=network_bytes_recv,
                timestamp=datetime.now()
            )
            
            with self.lock:
                self.system_metrics_history.append(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return None
    
    def collect_api_metrics(self) -> APIMetrics:
        """Collect API performance metrics."""
        try:
            current_time = time.time()
            time_diff = current_time - self.last_metrics_time
            
            # Calculate metrics
            total_requests = sum(self.request_counts.values())
            successful_requests = self.request_counts.get('success', 0)
            failed_requests = self.request_counts.get('error', 0)
            
            # Average response time
            if self.response_times:
                average_response_time = sum(self.response_times) / len(self.response_times)
            else:
                average_response_time = 0.0
            
            # Requests per second
            if time_diff > 0:
                requests_per_second = total_requests / time_diff
            else:
                requests_per_second = 0.0
            
            # Active connections (approximation)
            active_connections = len(self.response_times)
            
            metrics = APIMetrics(
                total_requests=total_requests,
                successful_requests=successful_requests,
                failed_requests=failed_requests,
                average_response_time=average_response_time,
                requests_per_second=requests_per_second,
                active_connections=active_connections,
                timestamp=datetime.now()
            )
            
            with self.lock:
                self.api_metrics_history.append(metrics)
            
            self.last_metrics_time = current_time
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect API metrics: {e}")
            return None
    
    def collect_blockchain_metrics(self) -> BlockchainMetrics:
        """Collect blockchain-specific metrics."""
        try:
            # Placeholder implementation
            # In production, this would query the actual blockchain state
            
            metrics = BlockchainMetrics(
                current_height=12345,
                blocks_per_hour=360.0,
                transactions_per_hour=3600.0,
                average_block_time=10.0,
                network_hash_rate=1.23e12,  # 1.23 TH/s
                difficulty=1234567.89,
                active_validators=23,
                consensus_health="healthy",
                timestamp=datetime.now()
            )
            
            with self.lock:
                self.blockchain_metrics_history.append(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect blockchain metrics: {e}")
            return None
    
    def record_request(self, endpoint: str, method: str, status_code: int, response_time: float):
        """Record API request metrics."""
        with self.lock:
            # Count requests
            self.request_counts['total'] += 1
            
            if 200 <= status_code < 400:
                self.request_counts['success'] += 1
            else:
                self.request_counts['error'] += 1
                self.error_counts[f"{method} {endpoint}"] += 1
            
            # Record response time
            self.response_times.append(response_time)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        try:
            system_metrics = self.collect_system_metrics()
            api_metrics = self.collect_api_metrics()
            blockchain_metrics = self.collect_blockchain_metrics()
            
            uptime = time.time() - self.start_time
            
            return {
                "system": system_metrics.__dict__ if system_metrics else None,
                "api": api_metrics.__dict__ if api_metrics else None,
                "blockchain": blockchain_metrics.__dict__ if blockchain_metrics else None,
                "uptime_seconds": uptime,
                "uptime_formatted": str(timedelta(seconds=int(uptime))),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {"error": str(e)}
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        try:
            system_metrics = self.collect_system_metrics()
            api_metrics = self.collect_api_metrics()
            
            # Determine health status
            health_status = "healthy"
            issues = []
            
            if system_metrics:
                if system_metrics.cpu_percent > 90:
                    health_status = "warning"
                    issues.append("High CPU usage")
                
                if system_metrics.memory_percent > 90:
                    health_status = "warning"
                    issues.append("High memory usage")
                
                if system_metrics.disk_usage_percent > 90:
                    health_status = "warning"
                    issues.append("High disk usage")
            
            if api_metrics:
                if api_metrics.failed_requests > api_metrics.successful_requests * 0.1:
                    health_status = "warning"
                    issues.append("High error rate")
                
                if api_metrics.average_response_time > 5.0:
                    health_status = "warning"
                    issues.append("Slow response times")
            
            return {
                "status": health_status,
                "issues": issues,
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": time.time() - self.start_time
            }
            
        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return {
                "status": "error",
                "issues": [f"Health check failed: {str(e)}"],
                "timestamp": datetime.now().isoformat()
            }

# Global metrics collector
metrics_collector = MetricsCollector()

class HealthChecker:
    """Health checker for various system components."""
    
    def __init__(self):
        self.checks = {}
    
    def register_check(self, name: str, check_func):
        """Register a health check function."""
        self.checks[name] = check_func
    
    async def run_checks(self) -> Dict[str, Any]:
        """Run all registered health checks."""
        results = {}
        
        for name, check_func in self.checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                
                results[name] = {
                    "status": "healthy" if result else "unhealthy",
                    "result": result
                }
                
            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                results[name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return results
    
    def check_database(self) -> bool:
        """Check database connectivity."""
        # Placeholder implementation
        # In production, this would check actual database connection
        return True
    
    def check_redis(self) -> bool:
        """Check Redis connectivity."""
        # Placeholder implementation
        # In production, this would check actual Redis connection
        return True
    
    def check_blockchain_sync(self) -> bool:
        """Check blockchain synchronization status."""
        # Placeholder implementation
        # In production, this would check actual blockchain sync status
        return True
    
    def check_consensus_health(self) -> bool:
        """Check consensus mechanism health."""
        # Placeholder implementation
        # In production, this would check actual consensus health
        return True

# Global health checker
health_checker = HealthChecker()

# Register default health checks
health_checker.register_check("database", health_checker.check_database)
health_checker.register_check("redis", health_checker.check_redis)
health_checker.register_check("blockchain_sync", health_checker.check_blockchain_sync)
health_checker.register_check("consensus_health", health_checker.check_consensus_health)

class PerformanceMonitor:
    """Performance monitor for API endpoints."""
    
    def __init__(self):
        self.endpoint_metrics = defaultdict(lambda: {
            'total_requests': 0,
            'total_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0,
            'error_count': 0
        })
        self.lock = threading.Lock()
    
    def record_endpoint_performance(
        self,
        endpoint: str,
        method: str,
        response_time: float,
        status_code: int
    ):
        """Record performance metrics for an endpoint."""
        key = f"{method} {endpoint}"
        
        with self.lock:
            metrics = self.endpoint_metrics[key]
            metrics['total_requests'] += 1
            metrics['total_time'] += response_time
            metrics['min_time'] = min(metrics['min_time'], response_time)
            metrics['max_time'] = max(metrics['max_time'], response_time)
            
            if status_code >= 400:
                metrics['error_count'] += 1
    
    def get_endpoint_metrics(self, endpoint: str, method: str) -> Dict[str, Any]:
        """Get performance metrics for a specific endpoint."""
        key = f"{method} {endpoint}"
        
        with self.lock:
            metrics = self.endpoint_metrics[key]
            
            if metrics['total_requests'] == 0:
                return {
                    'endpoint': key,
                    'total_requests': 0,
                    'average_time': 0.0,
                    'min_time': 0.0,
                    'max_time': 0.0,
                    'error_rate': 0.0
                }
            
            return {
                'endpoint': key,
                'total_requests': metrics['total_requests'],
                'average_time': metrics['total_time'] / metrics['total_requests'],
                'min_time': metrics['min_time'] if metrics['min_time'] != float('inf') else 0.0,
                'max_time': metrics['max_time'],
                'error_rate': metrics['error_count'] / metrics['total_requests']
            }
    
    def get_all_endpoint_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for all endpoints."""
        with self.lock:
            return {
                endpoint: self.get_endpoint_metrics(*endpoint.split(' ', 1))
                for endpoint in self.endpoint_metrics.keys()
            }

# Global performance monitor
performance_monitor = PerformanceMonitor()
