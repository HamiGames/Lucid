"""
Metrics Module

This module contains metrics collection and reporting utilities for the Blockchain API.
Handles Prometheus metrics, custom metrics, and performance monitoring.
"""

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict, deque
import threading

logger = logging.getLogger(__name__)

@dataclass
class MetricValue:
    """Metric value with timestamp."""
    value: float
    timestamp: datetime
    labels: Optional[Dict[str, str]] = None

@dataclass
class CounterMetric:
    """Counter metric."""
    name: str
    value: int
    labels: Optional[Dict[str, str]] = None
    timestamp: datetime = None

@dataclass
class GaugeMetric:
    """Gauge metric."""
    name: str
    value: float
    labels: Optional[Dict[str, str]] = None
    timestamp: datetime = None

@dataclass
class HistogramMetric:
    """Histogram metric."""
    name: str
    value: float
    labels: Optional[Dict[str, str]] = None
    timestamp: datetime = None

class MetricsCollector:
    """Metrics collector for various system and API metrics."""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(list)
        self.metric_history = defaultdict(lambda: deque(maxlen=max_history))
        self.lock = threading.Lock()
    
    def increment_counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        with self.lock:
            key = self._get_metric_key(name, labels)
            self.counters[key] += value
            
            # Store in history
            metric = CounterMetric(name, self.counters[key], labels, datetime.now())
            self.metric_history[f"counter_{name}"].append(metric)
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric value."""
        with self.lock:
            key = self._get_metric_key(name, labels)
            self.gauges[key] = value
            
            # Store in history
            metric = GaugeMetric(name, value, labels, datetime.now())
            self.metric_history[f"gauge_{name}"].append(metric)
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Observe a histogram metric value."""
        with self.lock:
            key = self._get_metric_key(name, labels)
            self.histograms[key].append(value)
            
            # Store in history
            metric = HistogramMetric(name, value, labels, datetime.now())
            self.metric_history[f"histogram_{name}"].append(metric)
    
    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> int:
        """Get counter metric value."""
        with self.lock:
            key = self._get_metric_key(name, labels)
            return self.counters.get(key, 0)
    
    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get gauge metric value."""
        with self.lock:
            key = self._get_metric_key(name, labels)
            return self.gauges.get(key, 0.0)
    
    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get histogram statistics."""
        with self.lock:
            key = self._get_metric_key(name, labels)
            values = self.histograms.get(key, [])
            
            if not values:
                return {
                    "count": 0,
                    "sum": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "mean": 0.0,
                    "p50": 0.0,
                    "p95": 0.0,
                    "p99": 0.0
                }
            
            values.sort()
            count = len(values)
            total = sum(values)
            mean = total / count
            
            # Calculate percentiles
            p50_idx = int(count * 0.5)
            p95_idx = int(count * 0.95)
            p99_idx = int(count * 0.99)
            
            return {
                "count": count,
                "sum": total,
                "min": values[0],
                "max": values[-1],
                "mean": mean,
                "p50": values[p50_idx] if p50_idx < count else values[-1],
                "p95": values[p95_idx] if p95_idx < count else values[-1],
                "p99": values[p99_idx] if p99_idx < count else values[-1]
            }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics."""
        with self.lock:
            metrics = {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {
                    name: self.get_histogram_stats(name.split("_", 1)[1] if "_" in name else name)
                    for name in self.histograms.keys()
                }
            }
            
            return metrics
    
    def _get_metric_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Get metric key with labels."""
        if not labels:
            return name
        
        label_str = ",".join([f"{k}={v}" for k, v in sorted(labels.items())])
        return f"{name}{{{label_str}}}"
    
    def clear_old_metrics(self, max_age: int = 3600):
        """Clear old metrics from history."""
        cutoff_time = datetime.now() - timedelta(seconds=max_age)
        
        with self.lock:
            for metric_type, history in self.metric_history.items():
                # Remove old metrics
                while history and history[0].timestamp < cutoff_time:
                    history.popleft()

# Global metrics collector
metrics_collector = MetricsCollector()

class APIMetrics:
    """API-specific metrics collection."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
    
    def record_request(self, method: str, endpoint: str, status_code: int, response_time: float):
        """Record API request metrics."""
        labels = {
            "method": method,
            "endpoint": endpoint,
            "status_code": str(status_code)
        }
        
        # Increment request counter
        self.metrics_collector.increment_counter("api_requests_total", labels=labels)
        
        # Record response time histogram
        self.metrics_collector.observe_histogram("api_request_duration_seconds", response_time, labels=labels)
        
        # Record status code counter
        self.metrics_collector.increment_counter("api_status_codes_total", labels={"status_code": str(status_code)})
        
        # Record endpoint counter
        self.metrics_collector.increment_counter("api_endpoints_total", labels={"endpoint": endpoint})
    
    def record_error(self, error_type: str, endpoint: str, error_message: str):
        """Record API error metrics."""
        labels = {
            "error_type": error_type,
            "endpoint": endpoint
        }
        
        self.metrics_collector.increment_counter("api_errors_total", labels=labels)
    
    def record_authentication(self, success: bool, method: str):
        """Record authentication metrics."""
        labels = {
            "success": str(success).lower(),
            "method": method
        }
        
        self.metrics_collector.increment_counter("api_authentication_total", labels=labels)
    
    def record_rate_limit(self, endpoint: str, client_ip: str):
        """Record rate limiting metrics."""
        labels = {
            "endpoint": endpoint,
            "client_ip": client_ip
        }
        
        self.metrics_collector.increment_counter("api_rate_limits_total", labels=labels)
    
    def set_active_connections(self, count: int):
        """Set active connections gauge."""
        self.metrics_collector.set_gauge("api_active_connections", count)
    
    def set_response_time_percentile(self, percentile: str, value: float):
        """Set response time percentile gauge."""
        self.metrics_collector.set_gauge(f"api_response_time_{percentile}", value)

class BlockchainMetrics:
    """Blockchain-specific metrics collection."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
    
    def record_block_creation(self, block_height: int, block_time: float, validator: str):
        """Record block creation metrics."""
        labels = {
            "validator": validator
        }
        
        self.metrics_collector.increment_counter("blockchain_blocks_total", labels=labels)
        self.metrics_collector.set_gauge("blockchain_current_height", block_height)
        self.metrics_collector.observe_histogram("blockchain_block_creation_time", block_time, labels=labels)
    
    def record_transaction(self, tx_type: str, status: str):
        """Record transaction metrics."""
        labels = {
            "type": tx_type,
            "status": status
        }
        
        self.metrics_collector.increment_counter("blockchain_transactions_total", labels=labels)
    
    def record_session_anchoring(self, status: str, processing_time: float):
        """Record session anchoring metrics."""
        labels = {
            "status": status
        }
        
        self.metrics_collector.increment_counter("blockchain_session_anchorings_total", labels=labels)
        self.metrics_collector.observe_histogram("blockchain_session_anchoring_time", processing_time, labels=labels)
    
    def record_consensus_vote(self, vote: str, node_id: str):
        """Record consensus vote metrics."""
        labels = {
            "vote": vote,
            "node_id": node_id
        }
        
        self.metrics_collector.increment_counter("blockchain_consensus_votes_total", labels=labels)
    
    def record_merkle_operation(self, operation: str, processing_time: float):
        """Record Merkle tree operation metrics."""
        labels = {
            "operation": operation
        }
        
        self.metrics_collector.increment_counter("blockchain_merkle_operations_total", labels=labels)
        self.metrics_collector.observe_histogram("blockchain_merkle_operation_time", processing_time, labels=labels)
    
    def set_network_hash_rate(self, hash_rate: float):
        """Set network hash rate gauge."""
        self.metrics_collector.set_gauge("blockchain_network_hash_rate", hash_rate)
    
    def set_difficulty(self, difficulty: float):
        """Set difficulty gauge."""
        self.metrics_collector.set_gauge("blockchain_difficulty", difficulty)
    
    def set_active_validators(self, count: int):
        """Set active validators gauge."""
        self.metrics_collector.set_gauge("blockchain_active_validators", count)
    
    def set_consensus_round(self, round_number: int):
        """Set consensus round gauge."""
        self.metrics_collector.set_gauge("blockchain_consensus_round", round_number)

class SystemMetrics:
    """System resource metrics collection."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
    
    def record_cpu_usage(self, cpu_percent: float):
        """Record CPU usage gauge."""
        self.metrics_collector.set_gauge("system_cpu_usage_percent", cpu_percent)
    
    def record_memory_usage(self, memory_percent: float, memory_used_mb: float):
        """Record memory usage gauges."""
        self.metrics_collector.set_gauge("system_memory_usage_percent", memory_percent)
        self.metrics_collector.set_gauge("system_memory_used_mb", memory_used_mb)
    
    def record_disk_usage(self, disk_percent: float, disk_used_gb: float):
        """Record disk usage gauges."""
        self.metrics_collector.set_gauge("system_disk_usage_percent", disk_percent)
        self.metrics_collector.set_gauge("system_disk_used_gb", disk_used_gb)
    
    def record_network_io(self, bytes_sent: int, bytes_recv: int):
        """Record network I/O counters."""
        self.metrics_collector.increment_counter("system_network_bytes_sent", bytes_sent)
        self.metrics_collector.increment_counter("system_network_bytes_recv", bytes_recv)
    
    def record_database_connections(self, active: int, idle: int):
        """Record database connection gauges."""
        self.metrics_collector.set_gauge("system_database_connections_active", active)
        self.metrics_collector.set_gauge("system_database_connections_idle", idle)
    
    def record_redis_connections(self, active: int):
        """Record Redis connection gauge."""
        self.metrics_collector.set_gauge("system_redis_connections_active", active)

# Global metrics instances
api_metrics = APIMetrics(metrics_collector)
blockchain_metrics = BlockchainMetrics(metrics_collector)
system_metrics = SystemMetrics(metrics_collector)

class MetricsService:
    """Service for managing and reporting metrics."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.start_time = datetime.now()
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        try:
            all_metrics = self.metrics_collector.get_all_metrics()
            uptime = datetime.now() - self.start_time
            
            return {
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": uptime.total_seconds(),
                "uptime_formatted": str(uptime),
                "metrics": all_metrics
            }
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        try:
            all_metrics = self.metrics_collector.get_all_metrics()
            prometheus_lines = []
            
            # Add timestamp
            prometheus_lines.append(f"# HELP blockchain_api_uptime_seconds Total uptime in seconds")
            prometheus_lines.append(f"# TYPE blockchain_api_uptime_seconds gauge")
            uptime = (datetime.now() - self.start_time).total_seconds()
            prometheus_lines.append(f"blockchain_api_uptime_seconds {uptime}")
            prometheus_lines.append("")
            
            # Add counters
            for metric_name, value in all_metrics["counters"].items():
                prometheus_lines.append(f"# HELP {metric_name} Counter metric")
                prometheus_lines.append(f"# TYPE {metric_name} counter")
                prometheus_lines.append(f"{metric_name} {value}")
                prometheus_lines.append("")
            
            # Add gauges
            for metric_name, value in all_metrics["gauges"].items():
                prometheus_lines.append(f"# HELP {metric_name} Gauge metric")
                prometheus_lines.append(f"# TYPE {metric_name} gauge")
                prometheus_lines.append(f"{metric_name} {value}")
                prometheus_lines.append("")
            
            # Add histograms
            for metric_name, stats in all_metrics["histograms"].items():
                prometheus_lines.append(f"# HELP {metric_name} Histogram metric")
                prometheus_lines.append(f"# TYPE {metric_name} histogram")
                prometheus_lines.append(f"{metric_name}_count {stats['count']}")
                prometheus_lines.append(f"{metric_name}_sum {stats['sum']}")
                prometheus_lines.append(f"{metric_name}_min {stats['min']}")
                prometheus_lines.append(f"{metric_name}_max {stats['max']}")
                prometheus_lines.append(f"{metric_name}_mean {stats['mean']}")
                prometheus_lines.append(f"{metric_name}_p50 {stats['p50']}")
                prometheus_lines.append(f"{metric_name}_p95 {stats['p95']}")
                prometheus_lines.append(f"{metric_name}_p99 {stats['p99']}")
                prometheus_lines.append("")
            
            return "\n".join(prometheus_lines)
        except Exception as e:
            logger.error(f"Failed to get Prometheus metrics: {e}")
            return f"# ERROR: {str(e)}"
    
    def get_metrics_for_dashboard(self) -> Dict[str, Any]:
        """Get metrics formatted for dashboard display."""
        try:
            all_metrics = self.metrics_collector.get_all_metrics()
            
            # Extract key metrics for dashboard
            dashboard_metrics = {
                "api": {
                    "total_requests": all_metrics["counters"].get("api_requests_total", 0),
                    "active_connections": all_metrics["gauges"].get("api_active_connections", 0),
                    "error_rate": self._calculate_error_rate(all_metrics)
                },
                "blockchain": {
                    "current_height": all_metrics["gauges"].get("blockchain_current_height", 0),
                    "active_validators": all_metrics["gauges"].get("blockchain_active_validators", 0),
                    "network_hash_rate": all_metrics["gauges"].get("blockchain_network_hash_rate", 0),
                    "difficulty": all_metrics["gauges"].get("blockchain_difficulty", 0)
                },
                "system": {
                    "cpu_usage": all_metrics["gauges"].get("system_cpu_usage_percent", 0),
                    "memory_usage": all_metrics["gauges"].get("system_memory_usage_percent", 0),
                    "disk_usage": all_metrics["gauges"].get("system_disk_usage_percent", 0)
                }
            }
            
            return {
                "timestamp": datetime.now().isoformat(),
                "metrics": dashboard_metrics
            }
        except Exception as e:
            logger.error(f"Failed to get dashboard metrics: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def _calculate_error_rate(self, all_metrics: Dict[str, Any]) -> float:
        """Calculate error rate from metrics."""
        try:
            total_requests = all_metrics["counters"].get("api_requests_total", 0)
            error_requests = all_metrics["counters"].get("api_errors_total", 0)
            
            if total_requests == 0:
                return 0.0
            
            return (error_requests / total_requests) * 100
        except Exception:
            return 0.0

# Global metrics service
metrics_service = MetricsService(metrics_collector)
