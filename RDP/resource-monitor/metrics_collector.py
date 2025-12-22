"""
RDP Metrics Collector - Metrics Collection Service

This module provides metrics collection functionality for RDP sessions,
including Prometheus metrics integration and custom metrics collection.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID
import json

try:
    from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
except ImportError:
    # Prometheus client not available, use mock classes
    class MockMetric:
        def __init__(self, *args, **kwargs):
            pass
        def inc(self, *args, **kwargs):
            pass
        def set(self, *args, **kwargs):
            pass
        def observe(self, *args, **kwargs):
            pass
    
    Counter = Gauge = Histogram = MockMetric
    CollectorRegistry = lambda: None
    generate_latest = lambda: b""

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collects and exposes metrics for RDP sessions"""
    
    def __init__(self, config=None):
        """
        Initialize MetricsCollector with configuration.
        
        Args:
            config: MonitorConfig instance (optional, will create default if not provided)
        """
        from .config import MonitorConfig, MonitorSettings
        
        self.config = config or MonitorConfig()
        self.settings = self.config.settings
        
        self.registry = CollectorRegistry()
        self.metrics = self._initialize_metrics()
        
        # Get collection interval from config
        self.collection_interval = self.config.settings.COLLECTION_INTERVAL
        
        self.collection_active = False
        
        logger.info(f"MetricsCollector initialized with collection interval: {self.collection_interval}s")
    
    def _initialize_metrics(self):
        """Initialize Prometheus metrics"""
        try:
            metrics = {
                # Session metrics
                'sessions_total': Counter(
                    'rdp_sessions_total',
                    'Total number of RDP sessions',
                    ['status'],
                    registry=self.registry
                ),
                'sessions_active': Gauge(
                    'rdp_sessions_active',
                    'Number of active RDP sessions',
                    registry=self.registry
                ),
                'session_duration': Histogram(
                    'rdp_session_duration_seconds',
                    'Duration of RDP sessions',
                    ['session_id'],
                    registry=self.registry
                ),
                
                # Resource metrics
                'cpu_usage': Gauge(
                    'rdp_cpu_usage_percent',
                    'CPU usage percentage',
                    ['session_id'],
                    registry=self.registry
                ),
                'memory_usage': Gauge(
                    'rdp_memory_usage_bytes',
                    'Memory usage in bytes',
                    ['session_id'],
                    registry=self.registry
                ),
                'memory_percent': Gauge(
                    'rdp_memory_usage_percent',
                    'Memory usage percentage',
                    ['session_id'],
                    registry=self.registry
                ),
                'disk_usage': Gauge(
                    'rdp_disk_usage_bytes',
                    'Disk usage in bytes',
                    ['session_id'],
                    registry=self.registry
                ),
                'disk_percent': Gauge(
                    'rdp_disk_usage_percent',
                    'Disk usage percentage',
                    ['session_id'],
                    registry=self.registry
                ),
                
                # Network metrics
                'network_bytes_sent': Counter(
                    'rdp_network_bytes_sent_total',
                    'Total network bytes sent',
                    ['session_id'],
                    registry=self.registry
                ),
                'network_bytes_recv': Counter(
                    'rdp_network_bytes_recv_total',
                    'Total network bytes received',
                    ['session_id'],
                    registry=self.registry
                ),
                'network_packets_sent': Counter(
                    'rdp_network_packets_sent_total',
                    'Total network packets sent',
                    ['session_id'],
                    registry=self.registry
                ),
                'network_packets_recv': Counter(
                    'rdp_network_packets_recv_total',
                    'Total network packets received',
                    ['session_id'],
                    registry=self.registry
                ),
                
                # Connection metrics
                'connections_active': Gauge(
                    'rdp_connections_active',
                    'Number of active connections',
                    registry=self.registry
                ),
                'connection_duration': Histogram(
                    'rdp_connection_duration_seconds',
                    'Duration of RDP connections',
                    ['connection_id'],
                    registry=self.registry
                ),
                
                # Error metrics
                'errors_total': Counter(
                    'rdp_errors_total',
                    'Total number of errors',
                    ['error_type', 'session_id'],
                    registry=self.registry
                ),
                'alerts_total': Counter(
                    'rdp_alerts_total',
                    'Total number of alerts',
                    ['alert_type', 'severity'],
                    registry=self.registry
                )
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to initialize metrics: {e}")
            return {}
    
    async def record_session_created(self, session_id: UUID, user_id: str):
        """Record session creation"""
        try:
            if 'sessions_total' in self.metrics:
                self.metrics['sessions_total'].labels(status='created').inc()
            logger.info(f"Recorded session creation: {session_id}")
        except Exception as e:
            logger.error(f"Failed to record session creation: {e}", exc_info=True)
            raise RuntimeError(f"Failed to record session creation: {str(e)}") from e
    
    async def record_session_terminated(self, session_id: UUID, duration: float):
        """Record session termination"""
        try:
            if 'sessions_total' in self.metrics:
                self.metrics['sessions_total'].labels(status='terminated').inc()
            if 'session_duration' in self.metrics:
                self.metrics['session_duration'].labels(session_id=str(session_id)).observe(duration)
            logger.info(f"Recorded session termination: {session_id}, duration: {duration}s")
        except Exception as e:
            logger.error(f"Failed to record session termination: {e}", exc_info=True)
            raise RuntimeError(f"Failed to record session termination: {str(e)}") from e
    
    async def record_session_active(self, session_id: UUID):
        """Record active session"""
        try:
            self.metrics['sessions_active'].set(1)
            logger.debug(f"Recorded active session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to record active session: {e}")
    
    async def record_resource_metrics(self, session_id: UUID, metrics_data: Dict[str, Any]):
        """Record resource metrics for a session"""
        try:
            session_id_str = str(session_id)
            
            # CPU metrics
            if 'cpu_percent' in metrics_data and 'cpu_usage' in self.metrics:
                self.metrics['cpu_usage'].labels(session_id=session_id_str).set(
                    metrics_data['cpu_percent']
                )
            
            # Memory metrics
            if 'memory_usage' in metrics_data and 'memory_usage' in self.metrics:
                self.metrics['memory_usage'].labels(session_id=session_id_str).set(
                    metrics_data['memory_usage']
                )
            if 'memory_percent' in metrics_data and 'memory_percent' in self.metrics:
                self.metrics['memory_percent'].labels(session_id=session_id_str).set(
                    metrics_data['memory_percent']
                )
            
            # Disk metrics
            if 'disk_usage' in metrics_data and 'disk_usage' in self.metrics:
                self.metrics['disk_usage'].labels(session_id=session_id_str).set(
                    metrics_data['disk_usage']
                )
            if 'disk_percent' in metrics_data and 'disk_percent' in self.metrics:
                self.metrics['disk_percent'].labels(session_id=session_id_str).set(
                    metrics_data['disk_percent']
                )
            
            # Network metrics
            if 'network_bytes_sent' in metrics_data and 'network_bytes_sent' in self.metrics:
                self.metrics['network_bytes_sent'].labels(session_id=session_id_str).inc(
                    metrics_data['network_bytes_sent']
                )
            if 'network_bytes_recv' in metrics_data and 'network_bytes_recv' in self.metrics:
                self.metrics['network_bytes_recv'].labels(session_id=session_id_str).inc(
                    metrics_data['network_bytes_recv']
                )
            if 'network_packets_sent' in metrics_data and 'network_packets_sent' in self.metrics:
                self.metrics['network_packets_sent'].labels(session_id=session_id_str).inc(
                    metrics_data['network_packets_sent']
                )
            if 'network_packets_recv' in metrics_data and 'network_packets_recv' in self.metrics:
                self.metrics['network_packets_recv'].labels(session_id=session_id_str).inc(
                    metrics_data['network_packets_recv']
                )
            
        except Exception as e:
            logger.error(f"Failed to record resource metrics: {e}", exc_info=True)
            raise RuntimeError(f"Failed to record resource metrics: {str(e)}") from e
    
    async def record_connection_created(self, connection_id: UUID):
        """Record connection creation"""
        try:
            self.metrics['connections_active'].inc()
            logger.info(f"Recorded connection creation: {connection_id}")
        except Exception as e:
            logger.error(f"Failed to record connection creation: {e}")
    
    async def record_connection_closed(self, connection_id: UUID, duration: float):
        """Record connection closure"""
        try:
            self.metrics['connections_active'].dec()
            self.metrics['connection_duration'].labels(connection_id=str(connection_id)).observe(duration)
            logger.info(f"Recorded connection closure: {connection_id}, duration: {duration}s")
        except Exception as e:
            logger.error(f"Failed to record connection closure: {e}")
    
    async def record_error(self, error_type: str, session_id: UUID, error_message: str):
        """Record an error"""
        try:
            self.metrics['errors_total'].labels(
                error_type=error_type,
                session_id=str(session_id)
            ).inc()
            logger.error(f"Recorded error: {error_type} for session {session_id}: {error_message}")
        except Exception as e:
            logger.error(f"Failed to record error: {e}")
    
    async def record_alert(self, alert_type: str, severity: str, session_id: UUID):
        """Record an alert"""
        try:
            self.metrics['alerts_total'].labels(
                alert_type=alert_type,
                severity=severity
            ).inc()
            logger.warning(f"Recorded alert: {alert_type} ({severity}) for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to record alert: {e}")
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        try:
            summary = {
                "timestamp": datetime.utcnow().isoformat(),
                "metrics_available": len(self.metrics) > 0,
                "collection_active": self.collection_active,
                "registry_size": len(self.registry._names_to_collectors) if hasattr(self.registry, '_names_to_collectors') else 0
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {}
    
    async def export_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        try:
            if hasattr(self, 'registry') and self.registry:
                return generate_latest().decode('utf-8')
            else:
                return "# No metrics available\n"
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            return f"# Error exporting metrics: {e}\n"
    
    async def start_collection(self):
        """Start metrics collection"""
        self.collection_active = True
        logger.info("Started metrics collection")
    
    async def stop_collection(self):
        """Stop metrics collection"""
        self.collection_active = False
        logger.info("Stopped metrics collection")
    
    async def collect_session_metrics(self, session_id: UUID, metrics_data: Dict[str, Any]):
        """Collect metrics for a specific session"""
        try:
            if not self.collection_active:
                return
            
            # Record resource metrics
            await self.record_resource_metrics(session_id, metrics_data)
            
            # Check for alerts and record them
            alerts = await self._check_metrics_alerts(session_id, metrics_data)
            for alert in alerts:
                await self.record_alert(
                    alert['type'],
                    alert['severity'],
                    session_id
                )
            
        except Exception as e:
            logger.error(f"Failed to collect session metrics: {e}")
    
    async def _check_metrics_alerts(self, session_id: UUID, metrics_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Check metrics for alert conditions"""
        alerts = []
        
        try:
            # Get thresholds from config
            thresholds = self.config.get_alert_thresholds()
            cpu_threshold = thresholds.get("cpu_percent", 80.0)
            memory_threshold = thresholds.get("memory_percent", 80.0)
            disk_threshold = thresholds.get("disk_percent", 90.0)
            
            # CPU alert
            if metrics_data.get('cpu_percent', 0) > cpu_threshold:
                alerts.append({
                    'type': 'cpu_high',
                    'severity': 'warning'
                })
            
            # Memory alert
            if metrics_data.get('memory_percent', 0) > memory_threshold:
                alerts.append({
                    'type': 'memory_high',
                    'severity': 'warning'
                })
            
            # Disk alert
            if metrics_data.get('disk_percent', 0) > disk_threshold:
                alerts.append({
                    'type': 'disk_high',
                    'severity': 'critical'
                })
            
        except Exception as e:
            logger.error(f"Failed to check metrics alerts: {e}", exc_info=True)
            # Don't raise here, just return empty alerts
        
        return alerts
