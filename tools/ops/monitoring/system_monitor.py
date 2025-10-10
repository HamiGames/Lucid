"""
System monitoring for Lucid RDP.

This module provides comprehensive system resource monitoring, metrics collection,
performance tracking, and integration with the LUCID-STRICT security model.
"""

import asyncio
import logging
import os
import platform
import psutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Union
import aiofiles
import json

from ...common.security.trust_nothing_engine import (
    TrustNothingEngine, SecurityContext, SecurityAssessment,
    TrustLevel, RiskLevel, ActionType, PolicyLevel
)


class MetricType(Enum):
    """Types of system metrics"""
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_IO = "network_io"
    PROCESS_COUNT = "process_count"
    LOAD_AVERAGE = "load_average"
    TEMPERATURE = "temperature"
    POWER_USAGE = "power_usage"
    UPTIME = "uptime"
    CUSTOM = "custom"


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SystemStatus(Enum):
    """System status states"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class MetricThreshold:
    """Metric threshold configuration"""
    metric_type: MetricType
    warning_threshold: float
    critical_threshold: float
    unit: str = "percent"
    enabled: bool = True
    description: str = ""


@dataclass
class SystemMetric:
    """System metric data point"""
    metric_id: str
    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime
    source: str = "system"
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemAlert:
    """System alert"""
    alert_id: str
    metric_type: MetricType
    alert_level: AlertLevel
    message: str
    value: float
    threshold: float
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealth:
    """System health summary"""
    status: SystemStatus
    overall_score: float
    metrics: Dict[MetricType, SystemMetric]
    alerts: List[SystemAlert]
    timestamp: datetime
    uptime: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessInfo:
    """Process information"""
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_rss: int
    memory_vms: int
    status: str
    create_time: float
    num_threads: int
    username: str
    cmdline: List[str] = field(default_factory=list)


@dataclass
class NetworkInterface:
    """Network interface information"""
    name: str
    is_up: bool
    speed: int
    mtu: int
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    errors_in: int
    errors_out: int
    drops_in: int
    drops_out: int


class SystemMonitor:
    """
    Comprehensive system monitoring for Lucid RDP.
    
    Provides system resource monitoring, metrics collection, alerting,
    and integration with the LUCID-STRICT security model.
    """
    
    def __init__(self, trust_engine: Optional[TrustNothingEngine] = None):
        self.trust_engine = trust_engine or TrustNothingEngine()
        self.logger = logging.getLogger(__name__)
        
        # Monitoring state
        self.metrics: Dict[str, SystemMetric] = {}
        self.alerts: Dict[str, SystemAlert] = {}
        self.thresholds: Dict[MetricType, MetricThreshold] = {}
        self.health_history: List[SystemHealth] = []
        
        # Configuration
        self.monitoring_interval = 30  # seconds
        self.metrics_retention_hours = 24
        self.alert_retention_hours = 168  # 1 week
        self.max_metrics_count = 10000
        self.max_alerts_count = 1000
        
        # Monitoring tasks
        self.monitoring_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # System information
        self.system_info = self._get_system_info()
        
        # Security integration
        self.security_context_cache: Dict[str, SecurityContext] = {}
        self.rate_limits: Dict[str, Tuple[datetime, int]] = {}
        
        # Initialize default thresholds
        self._initialize_default_thresholds()
        
        self.logger.info("SystemMonitor initialized")
    
    async def initialize(self, auto_start: bool = True) -> bool:
        """Initialize system monitor"""
        try:
            if auto_start:
                # Start monitoring
                self.monitoring_task = asyncio.create_task(self._monitoring_loop())
                
                # Start cleanup task
                self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self.logger.info("SystemMonitor initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize SystemMonitor: {e}")
            return False
    
    async def start_monitoring(self) -> bool:
        """Start system monitoring"""
        try:
            if self.monitoring_task and not self.monitoring_task.done():
                self.logger.warning("Monitoring is already running")
                return True
            
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self.logger.info("System monitoring started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
            return False
    
    async def stop_monitoring(self) -> bool:
        """Stop system monitoring"""
        try:
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
                self.monitoring_task = None
            
            if self.cleanup_task:
                self.cleanup_task.cancel()
                try:
                    await self.cleanup_task
                except asyncio.CancelledError:
                    pass
                self.cleanup_task = None
            
            self.logger.info("System monitoring stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop monitoring: {e}")
            return False
    
    async def collect_metrics(self) -> Dict[MetricType, SystemMetric]:
        """Collect current system metrics"""
        try:
            current_time = datetime.now(timezone.utc)
            collected_metrics = {}
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_metric = SystemMetric(
                metric_id=f"cpu_{int(current_time.timestamp())}",
                metric_type=MetricType.CPU_USAGE,
                value=cpu_percent,
                unit="percent",
                timestamp=current_time,
                tags={"core": "all"}
            )
            collected_metrics[MetricType.CPU_USAGE] = cpu_metric
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_metric = SystemMetric(
                metric_id=f"memory_{int(current_time.timestamp())}",
                metric_type=MetricType.MEMORY_USAGE,
                value=memory.percent,
                unit="percent",
                timestamp=current_time,
                metadata={
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "free": memory.free
                }
            )
            collected_metrics[MetricType.MEMORY_USAGE] = memory_metric
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_metric = SystemMetric(
                metric_id=f"disk_{int(current_time.timestamp())}",
                metric_type=MetricType.DISK_USAGE,
                value=(disk.used / disk.total) * 100,
                unit="percent",
                timestamp=current_time,
                metadata={
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free
                }
            )
            collected_metrics[MetricType.DISK_USAGE] = disk_metric
            
            # Network metrics
            network = psutil.net_io_counters()
            network_metric = SystemMetric(
                metric_id=f"network_{int(current_time.timestamp())}",
                metric_type=MetricType.NETWORK_IO,
                value=0,  # Will be calculated as rate
                unit="bytes_per_second",
                timestamp=current_time,
                metadata={
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            )
            collected_metrics[MetricType.NETWORK_IO] = network_metric
            
            # Process count
            process_count = len(psutil.pids())
            process_metric = SystemMetric(
                metric_id=f"processes_{int(current_time.timestamp())}",
                metric_type=MetricType.PROCESS_COUNT,
                value=process_count,
                unit="count",
                timestamp=current_time
            )
            collected_metrics[MetricType.PROCESS_COUNT] = process_metric
            
            # Load average (Unix-like systems)
            if hasattr(os, 'getloadavg'):
                load_avg = os.getloadavg()
                load_metric = SystemMetric(
                    metric_id=f"load_{int(current_time.timestamp())}",
                    metric_type=MetricType.LOAD_AVERAGE,
                    value=load_avg[0],  # 1-minute load average
                    unit="load",
                    timestamp=current_time,
                    metadata={
                        "1min": load_avg[0],
                        "5min": load_avg[1],
                        "15min": load_avg[2]
                    }
                )
                collected_metrics[MetricType.LOAD_AVERAGE] = load_metric
            
            # Uptime
            uptime = time.time() - psutil.boot_time()
            uptime_metric = SystemMetric(
                metric_id=f"uptime_{int(current_time.timestamp())}",
                metric_type=MetricType.UPTIME,
                value=uptime,
                unit="seconds",
                timestamp=current_time
            )
            collected_metrics[MetricType.UPTIME] = uptime_metric
            
            # Store metrics
            for metric in collected_metrics.values():
                self.metrics[metric.metric_id] = metric
            
            # Check thresholds and generate alerts
            await self._check_thresholds(collected_metrics)
            
            return collected_metrics
            
        except Exception as e:
            self.logger.error(f"Failed to collect metrics: {e}")
            return {}
    
    async def get_system_health(self) -> SystemHealth:
        """Get current system health summary"""
        try:
            # Collect current metrics
            current_metrics = await self.collect_metrics()
            
            # Calculate overall health score
            health_score = await self._calculate_health_score(current_metrics)
            
            # Determine system status
            status = self._determine_system_status(health_score, current_metrics)
            
            # Get active alerts
            active_alerts = [alert for alert in self.alerts.values() if not alert.resolved]
            
            # Get system uptime
            uptime = time.time() - psutil.boot_time()
            
            health = SystemHealth(
                status=status,
                overall_score=health_score,
                metrics=current_metrics,
                alerts=active_alerts,
                timestamp=datetime.now(timezone.utc),
                uptime=uptime,
                metadata={
                    "system_info": self.system_info,
                    "monitoring_interval": self.monitoring_interval,
                    "metrics_count": len(self.metrics),
                    "alerts_count": len(active_alerts)
                }
            )
            
            # Store in history
            self.health_history.append(health)
            
            # Limit history size
            if len(self.health_history) > 1000:
                self.health_history = self.health_history[-1000:]
            
            return health
            
        except Exception as e:
            self.logger.error(f"Failed to get system health: {e}")
            return SystemHealth(
                status=SystemStatus.UNKNOWN,
                overall_score=0.0,
                metrics={},
                alerts=[],
                timestamp=datetime.now(timezone.utc),
                uptime=0.0
            )
    
    async def get_top_processes(self, limit: int = 10, sort_by: str = "cpu") -> List[ProcessInfo]:
        """Get top processes by resource usage"""
        try:
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 
                                           'memory_info', 'status', 'create_time', 'num_threads', 
                                           'username', 'cmdline']):
                try:
                    proc_info = proc.info
                    
                    process = ProcessInfo(
                        pid=proc_info['pid'],
                        name=proc_info['name'],
                        cpu_percent=proc_info['cpu_percent'] or 0.0,
                        memory_percent=proc_info['memory_percent'] or 0.0,
                        memory_rss=proc_info['memory_info'].rss if proc_info['memory_info'] else 0,
                        memory_vms=proc_info['memory_info'].vms if proc_info['memory_info'] else 0,
                        status=proc_info['status'],
                        create_time=proc_info['create_time'],
                        num_threads=proc_info['num_threads'],
                        username=proc_info['username'],
                        cmdline=proc_info['cmdline']
                    )
                    
                    processes.append(process)
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            # Sort by specified criteria
            if sort_by == "cpu":
                processes.sort(key=lambda p: p.cpu_percent, reverse=True)
            elif sort_by == "memory":
                processes.sort(key=lambda p: p.memory_percent, reverse=True)
            elif sort_by == "memory_rss":
                processes.sort(key=lambda p: p.memory_rss, reverse=True)
            
            return processes[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to get top processes: {e}")
            return []
    
    async def get_network_interfaces(self) -> List[NetworkInterface]:
        """Get network interface information"""
        try:
            interfaces = []
            
            for interface_name, interface_stats in psutil.net_if_stats().items():
                io_counters = psutil.net_io_counters(pernic=True).get(interface_name)
                
                interface = NetworkInterface(
                    name=interface_name,
                    is_up=interface_stats.isup,
                    speed=interface_stats.speed,
                    mtu=interface_stats.mtu,
                    bytes_sent=io_counters.bytes_sent if io_counters else 0,
                    bytes_recv=io_counters.bytes_recv if io_counters else 0,
                    packets_sent=io_counters.packets_sent if io_counters else 0,
                    packets_recv=io_counters.packets_recv if io_counters else 0,
                    errors_in=io_counters.errin if io_counters else 0,
                    errors_out=io_counters.errout if io_counters else 0,
                    drops_in=io_counters.dropin if io_counters else 0,
                    drops_out=io_counters.dropout if io_counters else 0
                )
                
                interfaces.append(interface)
            
            return interfaces
            
        except Exception as e:
            self.logger.error(f"Failed to get network interfaces: {e}")
            return []
    
    async def set_metric_threshold(
        self,
        metric_type: MetricType,
        warning_threshold: float,
        critical_threshold: float,
        unit: str = "percent",
        description: str = ""
    ) -> bool:
        """Set metric threshold"""
        try:
            threshold = MetricThreshold(
                metric_type=metric_type,
                warning_threshold=warning_threshold,
                critical_threshold=critical_threshold,
                unit=unit,
                description=description
            )
            
            self.thresholds[metric_type] = threshold
            
            self.logger.info(f"Set threshold for {metric_type.value}: warning={warning_threshold}, critical={critical_threshold}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set metric threshold: {e}")
            return False
    
    async def get_alerts(self, resolved: Optional[bool] = None) -> List[SystemAlert]:
        """Get system alerts"""
        if resolved is None:
            return list(self.alerts.values())
        else:
            return [alert for alert in self.alerts.values() if alert.resolved == resolved]
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        try:
            if alert_id not in self.alerts:
                self.logger.error(f"Alert {alert_id} not found")
                return False
            
            alert = self.alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.now(timezone.utc)
            
            self.logger.info(f"Resolved alert {alert_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to resolve alert {alert_id}: {e}")
            return False
    
    async def get_metrics_history(
        self,
        metric_type: Optional[MetricType] = None,
        hours: int = 24
    ) -> List[SystemMetric]:
        """Get metrics history"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            filtered_metrics = []
            for metric in self.metrics.values():
                if metric.timestamp >= cutoff_time:
                    if metric_type is None or metric.metric_type == metric_type:
                        filtered_metrics.append(metric)
            
            # Sort by timestamp
            filtered_metrics.sort(key=lambda m: m.timestamp)
            
            return filtered_metrics
            
        except Exception as e:
            self.logger.error(f"Failed to get metrics history: {e}")
            return []
    
    async def export_metrics(self, file_path: str, hours: int = 24) -> bool:
        """Export metrics to file"""
        try:
            metrics_history = await self.get_metrics_history(hours=hours)
            
            export_data = {
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "hours": hours,
                "metrics_count": len(metrics_history),
                "metrics": []
            }
            
            for metric in metrics_history:
                metric_data = {
                    "metric_id": metric.metric_id,
                    "metric_type": metric.metric_type.value,
                    "value": metric.value,
                    "unit": metric.unit,
                    "timestamp": metric.timestamp.isoformat(),
                    "source": metric.source,
                    "tags": metric.tags,
                    "metadata": metric.metadata
                }
                export_data["metrics"].append(metric_data)
            
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(json.dumps(export_data, indent=2))
            
            self.logger.info(f"Exported {len(metrics_history)} metrics to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export metrics: {e}")
            return False
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            return {
                "platform": platform.platform(),
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "hostname": platform.node(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "cpu_count_logical": psutil.cpu_count(logical=True),
                "memory_total": psutil.virtual_memory().total,
                "boot_time": psutil.boot_time()
            }
        except Exception as e:
            self.logger.error(f"Failed to get system info: {e}")
            return {}
    
    def _initialize_default_thresholds(self) -> None:
        """Initialize default metric thresholds"""
        default_thresholds = [
            (MetricType.CPU_USAGE, 80.0, 95.0, "percent", "CPU usage threshold"),
            (MetricType.MEMORY_USAGE, 85.0, 95.0, "percent", "Memory usage threshold"),
            (MetricType.DISK_USAGE, 85.0, 95.0, "percent", "Disk usage threshold"),
            (MetricType.LOAD_AVERAGE, 2.0, 4.0, "load", "Load average threshold"),
            (MetricType.PROCESS_COUNT, 500, 1000, "count", "Process count threshold")
        ]
        
        for metric_type, warning, critical, unit, description in default_thresholds:
            self.thresholds[metric_type] = MetricThreshold(
                metric_type=metric_type,
                warning_threshold=warning,
                critical_threshold=critical,
                unit=unit,
                description=description
            )
    
    async def _check_thresholds(self, metrics: Dict[MetricType, SystemMetric]) -> None:
        """Check metrics against thresholds and generate alerts"""
        try:
            for metric_type, metric in metrics.items():
                if metric_type not in self.thresholds:
                    continue
                
                threshold = self.thresholds[metric_type]
                if not threshold.enabled:
                    continue
                
                # Check for critical threshold
                if metric.value >= threshold.critical_threshold:
                    await self._create_alert(
                        metric_type=metric_type,
                        alert_level=AlertLevel.CRITICAL,
                        message=f"{metric_type.value} is critical: {metric.value:.2f}{threshold.unit} (threshold: {threshold.critical_threshold}{threshold.unit})",
                        value=metric.value,
                        threshold=threshold.critical_threshold
                    )
                
                # Check for warning threshold
                elif metric.value >= threshold.warning_threshold:
                    await self._create_alert(
                        metric_type=metric_type,
                        alert_level=AlertLevel.WARNING,
                        message=f"{metric_type.value} is high: {metric.value:.2f}{threshold.unit} (threshold: {threshold.warning_threshold}{threshold.unit})",
                        value=metric.value,
                        threshold=threshold.warning_threshold
                    )
                
        except Exception as e:
            self.logger.error(f"Failed to check thresholds: {e}")
    
    async def _create_alert(
        self,
        metric_type: MetricType,
        alert_level: AlertLevel,
        message: str,
        value: float,
        threshold: float
    ) -> None:
        """Create a new alert"""
        try:
            alert_id = f"alert_{metric_type.value}_{int(time.time())}"
            
            # Check if similar alert already exists
            existing_alert = None
            for alert in self.alerts.values():
                if (alert.metric_type == metric_type and 
                    alert.alert_level == alert_level and 
                    not alert.resolved):
                    existing_alert = alert
                    break
            
            if existing_alert:
                # Update existing alert
                existing_alert.value = value
                existing_alert.timestamp = datetime.now(timezone.utc)
                existing_alert.message = message
            else:
                # Create new alert
                alert = SystemAlert(
                    alert_id=alert_id,
                    metric_type=metric_type,
                    alert_level=alert_level,
                    message=message,
                    value=value,
                    threshold=threshold,
                    timestamp=datetime.now(timezone.utc)
                )
                
                self.alerts[alert_id] = alert
                
                self.logger.warning(f"Created alert: {message}")
                
                # Limit alerts count
                if len(self.alerts) > self.max_alerts_count:
                    # Remove oldest resolved alerts
                    resolved_alerts = [a for a in self.alerts.values() if a.resolved]
                    if resolved_alerts:
                        oldest_alert = min(resolved_alerts, key=lambda a: a.timestamp)
                        del self.alerts[oldest_alert.alert_id]
                
        except Exception as e:
            self.logger.error(f"Failed to create alert: {e}")
    
    async def _calculate_health_score(self, metrics: Dict[MetricType, SystemMetric]) -> float:
        """Calculate overall system health score"""
        try:
            if not metrics:
                return 0.0
            
            total_score = 0.0
            metric_count = 0
            
            for metric_type, metric in metrics.items():
                if metric_type in self.thresholds:
                    threshold = self.thresholds[metric_type]
                    
                    # Calculate score based on threshold
                    if metric.value < threshold.warning_threshold:
                        score = 100.0
                    elif metric.value < threshold.critical_threshold:
                        # Linear interpolation between 100 and 50
                        ratio = (metric.value - threshold.warning_threshold) / (threshold.critical_threshold - threshold.warning_threshold)
                        score = 100.0 - (ratio * 50.0)
                    else:
                        # Linear interpolation between 50 and 0
                        ratio = min(1.0, (metric.value - threshold.critical_threshold) / threshold.critical_threshold)
                        score = 50.0 - (ratio * 50.0)
                    
                    total_score += max(0.0, score)
                    metric_count += 1
            
            return total_score / metric_count if metric_count > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"Failed to calculate health score: {e}")
            return 0.0
    
    def _determine_system_status(self, health_score: float, metrics: Dict[MetricType, SystemMetric]) -> SystemStatus:
        """Determine system status based on health score and metrics"""
        try:
            # Check for critical alerts
            critical_alerts = [alert for alert in self.alerts.values() 
                             if alert.alert_level == AlertLevel.CRITICAL and not alert.resolved]
            
            if critical_alerts:
                return SystemStatus.CRITICAL
            
            # Check health score
            if health_score >= 80.0:
                return SystemStatus.HEALTHY
            elif health_score >= 60.0:
                return SystemStatus.WARNING
            else:
                return SystemStatus.CRITICAL
                
        except Exception as e:
            self.logger.error(f"Failed to determine system status: {e}")
            return SystemStatus.UNKNOWN
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while True:
            try:
                # Collect metrics
                await self.collect_metrics()
                
                # Get system health
                health = await self.get_system_health()
                
                # Log health status
                if health.status == SystemStatus.CRITICAL:
                    self.logger.critical(f"System health critical: score={health.overall_score:.2f}")
                elif health.status == SystemStatus.WARNING:
                    self.logger.warning(f"System health warning: score={health.overall_score:.2f}")
                
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def _cleanup_loop(self) -> None:
        """Cleanup old metrics and alerts"""
        while True:
            try:
                current_time = datetime.now(timezone.utc)
                
                # Cleanup old metrics
                metrics_cutoff = current_time - timedelta(hours=self.metrics_retention_hours)
                metrics_to_remove = [
                    metric_id for metric_id, metric in self.metrics.items()
                    if metric.timestamp < metrics_cutoff
                ]
                
                for metric_id in metrics_to_remove:
                    del self.metrics[metric_id]
                
                # Cleanup old alerts
                alerts_cutoff = current_time - timedelta(hours=self.alert_retention_hours)
                alerts_to_remove = [
                    alert_id for alert_id, alert in self.alerts.items()
                    if alert.resolved and alert.resolved_at and alert.resolved_at < alerts_cutoff
                ]
                
                for alert_id in alerts_to_remove:
                    del self.alerts[alert_id]
                
                if metrics_to_remove or alerts_to_remove:
                    self.logger.info(f"Cleaned up {len(metrics_to_remove)} metrics and {len(alerts_to_remove)} alerts")
                
                await asyncio.sleep(3600)  # Run cleanup every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)


# Global instance management
_system_monitor_instance: Optional[SystemMonitor] = None


def get_system_monitor() -> Optional[SystemMonitor]:
    """Get the global SystemMonitor instance"""
    return _system_monitor_instance


def create_system_monitor(trust_engine: Optional[TrustNothingEngine] = None) -> SystemMonitor:
    """Create a new SystemMonitor instance"""
    global _system_monitor_instance
    _system_monitor_instance = SystemMonitor(trust_engine)
    return _system_monitor_instance


async def main():
    """Example usage of SystemMonitor"""
    # Create system monitor
    system_monitor = create_system_monitor()
    
    # Initialize
    await system_monitor.initialize()
    
    # Collect metrics
    metrics = await system_monitor.collect_metrics()
    print(f"Collected {len(metrics)} metrics")
    
    # Get system health
    health = await system_monitor.get_system_health()
    print(f"System health: {health.status.value} (score: {health.overall_score:.2f})")
    
    # Get top processes
    top_processes = await system_monitor.get_top_processes(limit=5)
    print(f"Top processes: {len(top_processes)}")
    
    # Get network interfaces
    interfaces = await system_monitor.get_network_interfaces()
    print(f"Network interfaces: {len(interfaces)}")
    
    # Get alerts
    alerts = await system_monitor.get_alerts()
    print(f"Active alerts: {len(alerts)}")
    
    # Export metrics
    await system_monitor.export_metrics("system_metrics.json", hours=1)
    
    # Stop monitoring
    await system_monitor.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
