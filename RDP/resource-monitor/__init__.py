"""
Lucid RDP Resource Monitor Service
Cluster: RDP Resource Monitoring
Port: 8093

Features:
- CPU, memory, disk, and network monitoring
- Session resource usage tracking
- Performance metrics collection
- Resource alerts and notifications
- Prometheus metrics integration
- Real-time resource monitoring
"""

from .resource_monitor import ResourceMonitor, ResourceMetrics
from .metrics_collector import MetricsCollector

__all__ = [
    'ResourceMonitor',
    'ResourceMetrics',
    'MetricsCollector'
]

__version__ = "1.0.0"
__cluster__ = "rdp-resource-monitor"
__port__ = 8093
