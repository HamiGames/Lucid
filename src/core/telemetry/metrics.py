"""
Metrics collection and aggregation for Lucid telemetry system.

This module provides comprehensive metrics collection functionality including:
- Counter metrics
- Gauge metrics
- Histogram metrics
- Summary metrics
- Custom metrics
- Metrics aggregation
- Export to various formats (Prometheus, JSON, etc.)
"""

import asyncio
import logging
import time
import json
import threading
from typing import Any, Dict, List, Optional, Union, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
import statistics
import math

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Metric type enumeration."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    CUSTOM = "custom"


class AggregationType(Enum):
    """Aggregation type enumeration."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    MEDIAN = "median"
    PERCENTILE = "percentile"


@dataclass
class MetricLabel:
    """Metric label information."""
    name: str
    value: str


@dataclass
class MetricSample:
    """Single metric sample."""
    value: Union[int, float]
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricConfig:
    """Metric configuration."""
    name: str
    type: MetricType
    description: str
    labels: List[str] = field(default_factory=list)
    buckets: Optional[List[float]] = None
    quantiles: Optional[List[float]] = None
    help_text: Optional[str] = None
    unit: Optional[str] = None
    retention_period: Optional[timedelta] = None


class Counter:
    """Counter metric implementation."""
    
    def __init__(self, name: str, description: str = "", labels: List[str] = None):
        self.name = name
        self.description = description
        self.labels = labels or []
        self._values: Dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()
    
    def inc(self, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment counter value."""
        labels = labels or {}
        key = tuple(sorted(labels.items()))
        
        with self._lock:
            self._values[key] += value
    
    def get(self, labels: Dict[str, str] = None) -> float:
        """Get counter value."""
        labels = labels or {}
        key = tuple(sorted(labels.items()))
        
        with self._lock:
            return self._values.get(key, 0.0)
    
    def get_all(self) -> Dict[tuple, float]:
        """Get all counter values."""
        with self._lock:
            return dict(self._values)
    
    def reset(self, labels: Dict[str, str] = None):
        """Reset counter value."""
        labels = labels or {}
        key = tuple(sorted(labels.items()))
        
        with self._lock:
            if labels:
                self._values.pop(key, None)
            else:
                self._values.clear()


class Gauge:
    """Gauge metric implementation."""
    
    def __init__(self, name: str, description: str = "", labels: List[str] = None):
        self.name = name
        self.description = description
        self.labels = labels or []
        self._values: Dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()
    
    def set(self, value: float, labels: Dict[str, str] = None):
        """Set gauge value."""
        labels = labels or {}
        key = tuple(sorted(labels.items()))
        
        with self._lock:
            self._values[key] = value
    
    def inc(self, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment gauge value."""
        labels = labels or {}
        key = tuple(sorted(labels.items()))
        
        with self._lock:
            self._values[key] += value
    
    def dec(self, value: float = 1.0, labels: Dict[str, str] = None):
        """Decrement gauge value."""
        labels = labels or {}
        key = tuple(sorted(labels.items()))
        
        with self._lock:
            self._values[key] -= value
    
    def get(self, labels: Dict[str, str] = None) -> float:
        """Get gauge value."""
        labels = labels or {}
        key = tuple(sorted(labels.items()))
        
        with self._lock:
            return self._values.get(key, 0.0)
    
    def get_all(self) -> Dict[tuple, float]:
        """Get all gauge values."""
        with self._lock:
            return dict(self._values)


class Histogram:
    """Histogram metric implementation."""
    
    def __init__(self, name: str, description: str = "", labels: List[str] = None,
                 buckets: List[float] = None):
        self.name = name
        self.description = description
        self.labels = labels or []
        self.buckets = buckets or [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float('inf')]
        self._observations: Dict[tuple, List[float]] = defaultdict(list)
        self._counts: Dict[tuple, int] = defaultdict(int)
        self._sums: Dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()
    
    def observe(self, value: float, labels: Dict[str, str] = None):
        """Observe a value."""
        labels = labels or {}
        key = tuple(sorted(labels.items()))
        
        with self._lock:
            self._observations[key].append(value)
            self._counts[key] += 1
            self._sums[key] += value
    
    def get_count(self, labels: Dict[str, str] = None) -> int:
        """Get observation count."""
        labels = labels or {}
        key = tuple(sorted(labels.items()))
        
        with self._lock:
            return self._counts.get(key, 0)
    
    def get_sum(self, labels: Dict[str, str] = None) -> float:
        """Get sum of observations."""
        labels = labels or {}
        key = tuple(sorted(labels.items()))
        
        with self._lock:
            return self._sums.get(key, 0.0)
    
    def get_bucket_counts(self, labels: Dict[str, str] = None) -> Dict[float, int]:
        """Get bucket counts."""
        labels = labels or {}
        key = tuple(sorted(labels.items()))
        
        with self._lock:
            observations = self._observations.get(key, [])
            bucket_counts = {}
            
            for bucket in self.buckets:
                count = sum(1 for obs in observations if obs <= bucket)
                bucket_counts[bucket] = count
            
            return bucket_counts
    
    def get_percentile(self, percentile: float, labels: Dict[str, str] = None) -> float:
        """Get percentile value."""
        labels = labels or {}
        key = tuple(sorted(labels.items()))
        
        with self._lock:
            observations = self._observations.get(key, [])
            if not observations:
                return 0.0
            
            sorted_obs = sorted(observations)
            index = int(len(sorted_obs) * percentile / 100.0)
            return sorted_obs[min(index, len(sorted_obs) - 1)]


class Summary:
    """Summary metric implementation."""
    
    def __init__(self, name: str, description: str = "", labels: List[str] = None,
                 quantiles: List[float] = None):
        self.name = name
        self.description = description
        self.labels = labels or []
        self.quantiles = quantiles or [0.5, 0.9, 0.95, 0.99]
        self._observations: Dict[tuple, List[float]] = defaultdict(list)
        self._counts: Dict[tuple, int] = defaultdict(int)
        self._sums: Dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()
    
    def observe(self, value: float, labels: Dict[str, str] = None):
        """Observe a value."""
        labels = labels or {}
        key = tuple(sorted(labels.items()))
        
        with self._lock:
            self._observations[key].append(value)
            self._counts[key] += 1
            self._sums[key] += value
    
    def get_count(self, labels: Dict[str, str] = None) -> int:
        """Get observation count."""
        labels = labels or {}
        key = tuple(sorted(labels.items()))
        
        with self._lock:
            return self._counts.get(key, 0)
    
    def get_sum(self, labels: Dict[str, str] = None) -> float:
        """Get sum of observations."""
        labels = labels or {}
        key = tuple(sorted(labels.items()))
        
        with self._lock:
            return self._sums.get(key, 0.0)
    
    def get_quantiles(self, labels: Dict[str, str] = None) -> Dict[float, float]:
        """Get quantile values."""
        labels = labels or {}
        key = tuple(sorted(labels.items()))
        
        with self._lock:
            observations = self._observations.get(key, [])
            if not observations:
                return {q: 0.0 for q in self.quantiles}
            
            sorted_obs = sorted(observations)
            quantile_values = {}
            
            for quantile in self.quantiles:
                index = int(len(sorted_obs) * quantile)
                quantile_values[quantile] = sorted_obs[min(index, len(sorted_obs) - 1)]
            
            return quantile_values


class CustomMetric:
    """Custom metric implementation."""
    
    def __init__(self, name: str, description: str = "", labels: List[str] = None):
        self.name = name
        self.description = description
        self.labels = labels or []
        self._values: Dict[tuple, Any] = defaultdict(lambda: None)
        self._lock = threading.Lock()
    
    def set(self, value: Any, labels: Dict[str, str] = None):
        """Set custom value."""
        labels = labels or {}
        key = tuple(sorted(labels.items()))
        
        with self._lock:
            self._values[key] = value
    
    def get(self, labels: Dict[str, str] = None) -> Any:
        """Get custom value."""
        labels = labels or {}
        key = tuple(sorted(labels.items()))
        
        with self._lock:
            return self._values.get(key)
    
    def get_all(self) -> Dict[tuple, Any]:
        """Get all custom values."""
        with self._lock:
            return dict(self._values)


class MetricsCollector:
    """Main metrics collector class."""
    
    def __init__(self):
        self._metrics: Dict[str, Union[Counter, Gauge, Histogram, Summary, CustomMetric]] = {}
        self._lock = threading.Lock()
        self._exporters: List[Callable] = []
        self._aggregation_rules: Dict[str, List[AggregationType]] = {}
        self._retention_periods: Dict[str, timedelta] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def register_counter(self, name: str, description: str = "", labels: List[str] = None) -> Counter:
        """Register a counter metric."""
        with self._lock:
            if name in self._metrics:
                return self._metrics[name]
            
            counter = Counter(name, description, labels)
            self._metrics[name] = counter
            logger.info(f"Registered counter metric: {name}")
            return counter
    
    def register_gauge(self, name: str, description: str = "", labels: List[str] = None) -> Gauge:
        """Register a gauge metric."""
        with self._lock:
            if name in self._metrics:
                return self._metrics[name]
            
            gauge = Gauge(name, description, labels)
            self._metrics[name] = gauge
            logger.info(f"Registered gauge metric: {name}")
            return gauge
    
    def register_histogram(self, name: str, description: str = "", labels: List[str] = None,
                          buckets: List[float] = None) -> Histogram:
        """Register a histogram metric."""
        with self._lock:
            if name in self._metrics:
                return self._metrics[name]
            
            histogram = Histogram(name, description, labels, buckets)
            self._metrics[name] = histogram
            logger.info(f"Registered histogram metric: {name}")
            return histogram
    
    def register_summary(self, name: str, description: str = "", labels: List[str] = None,
                        quantiles: List[float] = None) -> Summary:
        """Register a summary metric."""
        with self._lock:
            if name in self._metrics:
                return self._metrics[name]
            
            summary = Summary(name, description, labels, quantiles)
            self._metrics[name] = summary
            logger.info(f"Registered summary metric: {name}")
            return summary
    
    def register_custom(self, name: str, description: str = "", labels: List[str] = None) -> CustomMetric:
        """Register a custom metric."""
        with self._lock:
            if name in self._metrics:
                return self._metrics[name]
            
            custom = CustomMetric(name, description, labels)
            self._metrics[name] = custom
            logger.info(f"Registered custom metric: {name}")
            return custom
    
    def get_metric(self, name: str) -> Optional[Union[Counter, Gauge, Histogram, Summary, CustomMetric]]:
        """Get a metric by name."""
        with self._lock:
            return self._metrics.get(name)
    
    def list_metrics(self) -> List[str]:
        """List all registered metrics."""
        with self._lock:
            return list(self._metrics.keys())
    
    def remove_metric(self, name: str) -> bool:
        """Remove a metric."""
        with self._lock:
            if name in self._metrics:
                del self._metrics[name]
                logger.info(f"Removed metric: {name}")
                return True
            return False
    
    def add_exporter(self, exporter: Callable):
        """Add a metrics exporter."""
        self._exporters.append(exporter)
    
    def remove_exporter(self, exporter: Callable):
        """Remove a metrics exporter."""
        if exporter in self._exporters:
            self._exporters.remove(exporter)
    
    def export_metrics(self, format_type: str = "json") -> str:
        """Export metrics in specified format."""
        if format_type.lower() == "json":
            return self._export_json()
        elif format_type.lower() == "prometheus":
            return self._export_prometheus()
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def _export_json(self) -> str:
        """Export metrics as JSON."""
        export_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {}
        }
        
        with self._lock:
            for name, metric in self._metrics.items():
                metric_data = {
                    "name": name,
                    "type": type(metric).__name__.lower(),
                    "description": getattr(metric, 'description', ''),
                    "values": {}
                }
                
                if hasattr(metric, 'get_all'):
                    metric_data["values"] = metric.get_all()
                elif hasattr(metric, 'get_count') and hasattr(metric, 'get_sum'):
                    metric_data["values"] = {
                        "count": metric.get_count(),
                        "sum": metric.get_sum()
                    }
                
                export_data["metrics"][name] = metric_data
        
        return json.dumps(export_data, indent=2)
    
    def _export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        with self._lock:
            for name, metric in self._metrics.items():
                # Add help text
                if hasattr(metric, 'description') and metric.description:
                    lines.append(f"# HELP {name} {metric.description}")
                
                # Add type
                metric_type = type(metric).__name__.lower()
                lines.append(f"# TYPE {name} {metric_type}")
                
                # Add values
                if hasattr(metric, 'get_all'):
                    values = metric.get_all()
                    for label_tuple, value in values.items():
                        labels_str = ""
                        if label_tuple:
                            label_pairs = [f'{k}="{v}"' for k, v in label_tuple]
                            labels_str = "{" + ",".join(label_pairs) + "}"
                        lines.append(f"{name}{labels_str} {value}")
                
                elif hasattr(metric, 'get_count') and hasattr(metric, 'get_sum'):
                    count = metric.get_count()
                    sum_val = metric.get_sum()
                    lines.append(f"{name}_count {count}")
                    lines.append(f"{name}_sum {sum_val}")
        
        return "\n".join(lines)
    
    def aggregate_metrics(self, metric_name: str, aggregation_types: List[AggregationType]) -> Dict[str, float]:
        """Aggregate metrics using specified aggregation types."""
        metric = self.get_metric(metric_name)
        if not metric:
            return {}
        
        aggregations = {}
        
        if hasattr(metric, 'get_all'):
            values = list(metric.get_all().values())
            if values:
                if AggregationType.SUM in aggregation_types:
                    aggregations['sum'] = sum(values)
                if AggregationType.AVG in aggregation_types:
                    aggregations['avg'] = sum(values) / len(values)
                if AggregationType.MIN in aggregation_types:
                    aggregations['min'] = min(values)
                if AggregationType.MAX in aggregation_types:
                    aggregations['max'] = max(values)
                if AggregationType.COUNT in aggregation_types:
                    aggregations['count'] = len(values)
                if AggregationType.MEDIAN in aggregation_types:
                    aggregations['median'] = statistics.median(values)
        
        return aggregations
    
    def set_aggregation_rule(self, metric_name: str, aggregation_types: List[AggregationType]):
        """Set aggregation rule for a metric."""
        self._aggregation_rules[metric_name] = aggregation_types
    
    def set_retention_period(self, metric_name: str, period: timedelta):
        """Set retention period for a metric."""
        self._retention_periods[metric_name] = period
    
    async def start_cleanup_task(self, interval: int = 300):
        """Start cleanup task for old metrics."""
        if self._cleanup_task:
            return
        
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(interval)
                    await self._cleanup_old_metrics()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Cleanup task error: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    async def stop_cleanup_task(self):
        """Stop cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
    
    async def _cleanup_old_metrics(self):
        """Clean up old metrics based on retention periods."""
        # This is a placeholder for cleanup logic
        # In a real implementation, you would clean up old observations
        # based on timestamps and retention periods
        pass


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def initialize_metrics_collector() -> MetricsCollector:
    """Initialize the global metrics collector."""
    global _metrics_collector
    _metrics_collector = MetricsCollector()
    return _metrics_collector


# Convenience functions
def counter(name: str, description: str = "", labels: List[str] = None) -> Counter:
    """Get or create a counter metric."""
    return get_metrics_collector().register_counter(name, description, labels)


def gauge(name: str, description: str = "", labels: List[str] = None) -> Gauge:
    """Get or create a gauge metric."""
    return get_metrics_collector().register_gauge(name, description, labels)


def histogram(name: str, description: str = "", labels: List[str] = None,
              buckets: List[float] = None) -> Histogram:
    """Get or create a histogram metric."""
    return get_metrics_collector().register_histogram(name, description, labels, buckets)


def summary(name: str, description: str = "", labels: List[str] = None,
            quantiles: List[float] = None) -> Summary:
    """Get or create a summary metric."""
    return get_metrics_collector().register_summary(name, description, labels, quantiles)


def custom_metric(name: str, description: str = "", labels: List[str] = None) -> CustomMetric:
    """Get or create a custom metric."""
    return get_metrics_collector().register_custom(name, description, labels)


def export_metrics(format_type: str = "json") -> str:
    """Export all metrics."""
    return get_metrics_collector().export_metrics(format_type)


def aggregate_metrics(metric_name: str, aggregation_types: List[AggregationType]) -> Dict[str, float]:
    """Aggregate metrics."""
    return get_metrics_collector().aggregate_metrics(metric_name, aggregation_types)
