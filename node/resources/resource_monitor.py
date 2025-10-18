# Path: node/resources/resource_monitor.py
# Lucid Resource Monitor - System resource monitoring and management
# Based on LUCID-STRICT requirements per Spec-1c

from __future__ import annotations

import asyncio
import logging
import psutil
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ResourceStatus(Enum):
    """Resource status levels"""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class ResourceMetrics:
    """System resource metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_bandwidth_mbps: float
    active_sessions: int
    total_sessions: int
    uptime_seconds: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "disk_percent": self.disk_percent,
            "network_bandwidth_mbps": self.network_bandwidth_mbps,
            "active_sessions": self.active_sessions,
            "total_sessions": self.total_sessions,
            "uptime_seconds": self.uptime_seconds
        }


@dataclass
class ResourceThresholds:
    """Resource monitoring thresholds"""
    cpu_warning: float = 70.0
    cpu_critical: float = 90.0
    memory_warning: float = 70.0
    memory_critical: float = 90.0
    disk_warning: float = 80.0
    disk_critical: float = 95.0
    network_warning: float = 80.0
    network_critical: float = 95.0
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "cpu_warning": self.cpu_warning,
            "cpu_critical": self.cpu_critical,
            "memory_warning": self.memory_warning,
            "memory_critical": self.memory_critical,
            "disk_warning": self.disk_warning,
            "disk_critical": self.disk_critical,
            "network_warning": self.network_warning,
            "network_critical": self.network_critical
        }


@dataclass
class ResourceAlert:
    """Resource alert information"""
    alert_id: str
    resource_type: str
    status: ResourceStatus
    value: float
    threshold: float
    message: str
    timestamp: datetime
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "resource_type": self.resource_type,
            "status": self.status.value,
            "value": self.value,
            "threshold": self.threshold,
            "message": self.message,
            "timestamp": self.timestamp,
            "resolved": self.resolved
        }


class ResourceMonitor:
    """
    Resource monitor for system resource tracking and alerting.
    
    Handles:
    - CPU, memory, disk, and network monitoring
    - Resource threshold management
    - Alert generation and management
    - Performance metrics collection
    - Resource allocation tracking
    """
    
    def __init__(self, node_id: str, monitoring_interval: int = 30):
        self.node_id = node_id
        self.monitoring_interval = monitoring_interval
        self.running = False
        
        # Resource state
        self.current_metrics: Optional[ResourceMetrics] = None
        self.metrics_history: List[ResourceMetrics] = []
        self.thresholds = ResourceThresholds()
        self.active_alerts: Dict[str, ResourceAlert] = {}
        
        # Background tasks
        self._tasks: List[asyncio.Task] = []
        
        # Alert handlers
        self._alert_handlers: List[Callable[[ResourceAlert], None]] = []
        
        # Network monitoring
        self._last_net_io = None
        self._start_time = datetime.now(timezone.utc)
        
        logger.info(f"Resource monitor initialized: {node_id}")
    
    async def start(self):
        """Start resource monitoring"""
        try:
            logger.info(f"Starting resource monitor {self.node_id}...")
            self.running = True
            
            # Start monitoring task
            self._tasks.append(asyncio.create_task(self._monitoring_loop()))
            
            logger.info(f"Resource monitor {self.node_id} started")
            
        except Exception as e:
            logger.error(f"Failed to start resource monitor: {e}")
            raise
    
    async def stop(self):
        """Stop resource monitoring"""
        try:
            logger.info(f"Stopping resource monitor {self.node_id}...")
            self.running = False
            
            # Cancel background tasks
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            
            logger.info(f"Resource monitor {self.node_id} stopped")
            
        except Exception as e:
            logger.error(f"Error stopping resource monitor: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get resource monitor status"""
        try:
            return {
                "node_id": self.node_id,
                "running": self.running,
                "monitoring_interval": self.monitoring_interval,
                "current_metrics": self.current_metrics.to_dict() if self.current_metrics else None,
                "active_alerts": len(self.active_alerts),
                "metrics_history_count": len(self.metrics_history),
                "thresholds": self.thresholds.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Failed to get resource status: {e}")
            return {"error": str(e)}
    
    async def update_metrics(self):
        """Update current resource metrics"""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Calculate network bandwidth
            network_bandwidth = await self._calculate_network_bandwidth()
            
            # Calculate uptime
            uptime_seconds = int((datetime.now(timezone.utc) - self._start_time).total_seconds())
            
            # Create metrics
            metrics = ResourceMetrics(
                timestamp=datetime.now(timezone.utc),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=(disk.used / disk.total) * 100,
                network_bandwidth_mbps=network_bandwidth,
                active_sessions=0,  # Would be updated by node worker
                total_sessions=0,   # Would be updated by node worker
                uptime_seconds=uptime_seconds
            )
            
            # Update current metrics
            self.current_metrics = metrics
            
            # Add to history
            self.metrics_history.append(metrics)
            
            # Keep only last 1000 metrics
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]
            
            # Check for alerts
            await self._check_resource_alerts(metrics)
            
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")
    
    async def get_metrics(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get resource metrics for specified time period"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Filter metrics by time
            recent_metrics = [
                metric for metric in self.metrics_history
                if metric.timestamp >= cutoff_time
            ]
            
            return [metric.to_dict() for metric in recent_metrics]
            
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return []
    
    async def get_alerts(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get resource alerts"""
        try:
            alerts = list(self.active_alerts.values())
            
            if active_only:
                alerts = [alert for alert in alerts if not alert.resolved]
            
            return [alert.to_dict() for alert in alerts]
            
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve a resource alert"""
        try:
            alert = self.active_alerts.get(alert_id)
            if not alert:
                return False
            
            alert.resolved = True
            logger.info(f"Alert resolved: {alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve alert: {e}")
            return False
    
    async def update_thresholds(self, thresholds: Dict[str, float]):
        """Update resource thresholds"""
        try:
            for key, value in thresholds.items():
                if hasattr(self.thresholds, key):
                    setattr(self.thresholds, key, value)
            
            logger.info(f"Resource thresholds updated: {thresholds}")
            
        except Exception as e:
            logger.error(f"Failed to update thresholds: {e}")
    
    def add_alert_handler(self, handler: Callable[[ResourceAlert], None]):
        """Add alert handler"""
        self._alert_handlers.append(handler)
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                await self.update_metrics()
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)
    
    async def _calculate_network_bandwidth(self) -> float:
        """Calculate current network bandwidth usage"""
        try:
            current_net_io = psutil.net_io_counters()
            
            if self._last_net_io is None:
                self._last_net_io = current_net_io
                return 0.0
            
            # Calculate bytes per second
            bytes_sent = current_net_io.bytes_sent - self._last_net_io.bytes_sent
            bytes_recv = current_net_io.bytes_recv - self._last_net_io.bytes_recv
            total_bytes = bytes_sent + bytes_recv
            
            # Convert to Mbps
            bandwidth_mbps = (total_bytes * 8) / (1024 * 1024)  # Convert to Mbps
            
            self._last_net_io = current_net_io
            return bandwidth_mbps
            
        except Exception as e:
            logger.error(f"Failed to calculate network bandwidth: {e}")
            return 0.0
    
    async def _check_resource_alerts(self, metrics: ResourceMetrics):
        """Check for resource alerts"""
        try:
            # Check CPU
            await self._check_cpu_alert(metrics)
            
            # Check Memory
            await self._check_memory_alert(metrics)
            
            # Check Disk
            await self._check_disk_alert(metrics)
            
            # Check Network
            await self._check_network_alert(metrics)
            
        except Exception as e:
            logger.error(f"Failed to check resource alerts: {e}")
    
    async def _check_cpu_alert(self, metrics: ResourceMetrics):
        """Check CPU usage alerts"""
        cpu_percent = metrics.cpu_percent
        
        if cpu_percent >= self.thresholds.cpu_critical:
            await self._create_alert(
                "cpu",
                ResourceStatus.CRITICAL,
                cpu_percent,
                self.thresholds.cpu_critical,
                f"CPU usage critical: {cpu_percent:.1f}%"
            )
        elif cpu_percent >= self.thresholds.cpu_warning:
            await self._create_alert(
                "cpu",
                ResourceStatus.WARNING,
                cpu_percent,
                self.thresholds.cpu_warning,
                f"CPU usage warning: {cpu_percent:.1f}%"
            )
        else:
            await self._resolve_alert("cpu")
    
    async def _check_memory_alert(self, metrics: ResourceMetrics):
        """Check memory usage alerts"""
        memory_percent = metrics.memory_percent
        
        if memory_percent >= self.thresholds.memory_critical:
            await self._create_alert(
                "memory",
                ResourceStatus.CRITICAL,
                memory_percent,
                self.thresholds.memory_critical,
                f"Memory usage critical: {memory_percent:.1f}%"
            )
        elif memory_percent >= self.thresholds.memory_warning:
            await self._create_alert(
                "memory",
                ResourceStatus.WARNING,
                memory_percent,
                self.thresholds.memory_warning,
                f"Memory usage warning: {memory_percent:.1f}%"
            )
        else:
            await self._resolve_alert("memory")
    
    async def _check_disk_alert(self, metrics: ResourceMetrics):
        """Check disk usage alerts"""
        disk_percent = metrics.disk_percent
        
        if disk_percent >= self.thresholds.disk_critical:
            await self._create_alert(
                "disk",
                ResourceStatus.CRITICAL,
                disk_percent,
                self.thresholds.disk_critical,
                f"Disk usage critical: {disk_percent:.1f}%"
            )
        elif disk_percent >= self.thresholds.disk_warning:
            await self._create_alert(
                "disk",
                ResourceStatus.WARNING,
                disk_percent,
                self.thresholds.disk_warning,
                f"Disk usage warning: {disk_percent:.1f}%"
            )
        else:
            await self._resolve_alert("disk")
    
    async def _check_network_alert(self, metrics: ResourceMetrics):
        """Check network usage alerts"""
        network_bandwidth = metrics.network_bandwidth_mbps
        
        if network_bandwidth >= self.thresholds.network_critical:
            await self._create_alert(
                "network",
                ResourceStatus.CRITICAL,
                network_bandwidth,
                self.thresholds.network_critical,
                f"Network usage critical: {network_bandwidth:.1f} Mbps"
            )
        elif network_bandwidth >= self.thresholds.network_warning:
            await self._create_alert(
                "network",
                ResourceStatus.WARNING,
                network_bandwidth,
                self.thresholds.network_warning,
                f"Network usage warning: {network_bandwidth:.1f} Mbps"
            )
        else:
            await self._resolve_alert("network")
    
    async def _create_alert(self, resource_type: str, status: ResourceStatus, 
                           value: float, threshold: float, message: str):
        """Create a resource alert"""
        try:
            alert_id = f"{resource_type}_{status.value}"
            
            # Check if alert already exists
            if alert_id in self.active_alerts:
                existing_alert = self.active_alerts[alert_id]
                if not existing_alert.resolved:
                    return  # Alert already active
            
            # Create new alert
            alert = ResourceAlert(
                alert_id=alert_id,
                resource_type=resource_type,
                status=status,
                value=value,
                threshold=threshold,
                message=message,
                timestamp=datetime.now(timezone.utc)
            )
            
            self.active_alerts[alert_id] = alert
            
            # Notify alert handlers
            for handler in self._alert_handlers:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"Alert handler error: {e}")
            
            logger.warning(f"Resource alert created: {message}")
            
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
    
    async def _resolve_alert(self, resource_type: str):
        """Resolve alerts for a resource type"""
        try:
            alert_id = f"{resource_type}_warning"
            if alert_id in self.active_alerts:
                await self.resolve_alert(alert_id)
            
            alert_id = f"{resource_type}_critical"
            if alert_id in self.active_alerts:
                await self.resolve_alert(alert_id)
            
        except Exception as e:
            logger.error(f"Failed to resolve alert: {e}")


# Global resource monitor instance
_resource_monitor: Optional[ResourceMonitor] = None


def get_resource_monitor() -> Optional[ResourceMonitor]:
    """Get global resource monitor instance"""
    global _resource_monitor
    return _resource_monitor


def create_resource_monitor(node_id: str, monitoring_interval: int = 30) -> ResourceMonitor:
    """Create resource monitor instance"""
    global _resource_monitor
    _resource_monitor = ResourceMonitor(node_id, monitoring_interval)
    return _resource_monitor


async def cleanup_resource_monitor():
    """Cleanup resource monitor"""
    global _resource_monitor
    if _resource_monitor:
        await _resource_monitor.stop()
        _resource_monitor = None


if __name__ == "__main__":
    # Test resource monitor
    async def test_resource_monitor():
        print("Testing Lucid Resource Monitor...")
        
        monitor = create_resource_monitor("test_node", 5)
        
        try:
            await monitor.start()
            
            # Wait for some metrics
            await asyncio.sleep(10)
            
            # Get status
            status = await monitor.get_status()
            print(f"Monitor status: {status}")
            
            # Get metrics
            metrics = await monitor.get_metrics(1)
            print(f"Recent metrics: {len(metrics)} entries")
            
            # Get alerts
            alerts = await monitor.get_alerts()
            print(f"Active alerts: {len(alerts)}")
            
        finally:
            await monitor.stop()
        
        print("Test completed - resource monitor ready")
    
    asyncio.run(test_resource_monitor())
