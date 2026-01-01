"""
LUCID Payment Systems - TRON Client Metrics Module
Prometheus metrics collection and export for tron-client service
Following architecture patterns from build/docs/
"""

import os
import time
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.core import CollectorRegistry, REGISTRY
from fastapi import Response

logger = logging.getLogger(__name__)

# Create custom registry for tron-client metrics
TRON_CLIENT_REGISTRY = CollectorRegistry()

# Network Metrics
tron_network_requests_total = Counter(
    'tron_network_requests_total',
    'Total number of TRON network requests',
    ['method', 'endpoint', 'status'],
    registry=TRON_CLIENT_REGISTRY
)

tron_network_latency_seconds = Histogram(
    'tron_network_latency_seconds',
    'TRON network request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=TRON_CLIENT_REGISTRY
)

tron_network_errors_total = Counter(
    'tron_network_errors_total',
    'Total number of TRON network errors',
    ['error_type', 'endpoint'],
    registry=TRON_CLIENT_REGISTRY
)

# Transaction Metrics
tron_transactions_total = Counter(
    'tron_transactions_total',
    'Total number of transactions processed',
    ['type', 'status'],
    registry=TRON_CLIENT_REGISTRY
)

tron_transaction_duration_seconds = Histogram(
    'tron_transaction_duration_seconds',
    'Transaction processing duration in seconds',
    ['type'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 300.0],
    registry=TRON_CLIENT_REGISTRY
)

tron_transaction_amount = Histogram(
    'tron_transaction_amount_sun',
    'Transaction amount in SUN',
    ['type'],
    buckets=[1000, 10000, 100000, 1000000, 10000000, 100000000, 1000000000],
    registry=TRON_CLIENT_REGISTRY
)

tron_pending_transactions = Gauge(
    'tron_pending_transactions',
    'Number of pending transactions',
    registry=TRON_CLIENT_REGISTRY
)

tron_confirmed_transactions = Gauge(
    'tron_confirmed_transactions',
    'Number of confirmed transactions',
    registry=TRON_CLIENT_REGISTRY
)

# Account Metrics
tron_account_operations_total = Counter(
    'tron_account_operations_total',
    'Total number of account operations',
    ['operation', 'status'],
    registry=TRON_CLIENT_REGISTRY
)

tron_account_cache_size = Gauge(
    'tron_account_cache_size',
    'Number of accounts in cache',
    registry=TRON_CLIENT_REGISTRY
)

tron_account_balance_requests_total = Counter(
    'tron_account_balance_requests_total',
    'Total number of balance requests',
    ['status'],
    registry=TRON_CLIENT_REGISTRY
)

# Network Status Metrics
tron_network_status = Gauge(
    'tron_network_status',
    'TRON network connection status (1=connected, 0=disconnected)',
    registry=TRON_CLIENT_REGISTRY
)

tron_network_latest_block = Gauge(
    'tron_network_latest_block',
    'Latest block number',
    registry=TRON_CLIENT_REGISTRY
)

tron_network_sync_progress = Gauge(
    'tron_network_sync_progress',
    'Network sync progress percentage',
    registry=TRON_CLIENT_REGISTRY
)

# Connection Pool Metrics
tron_connection_pool_size = Gauge(
    'tron_connection_pool_size',
    'Connection pool size',
    ['state'],
    registry=TRON_CLIENT_REGISTRY
)

tron_connection_pool_active = Gauge(
    'tron_connection_pool_active',
    'Active connections in pool',
    registry=TRON_CLIENT_REGISTRY
)

tron_connection_pool_idle = Gauge(
    'tron_connection_pool_idle',
    'Idle connections in pool',
    registry=TRON_CLIENT_REGISTRY
)

# Circuit Breaker Metrics
tron_circuit_breaker_state = Gauge(
    'tron_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half_open)',
    ['breaker_name'],
    registry=TRON_CLIENT_REGISTRY
)

tron_circuit_breaker_failures_total = Counter(
    'tron_circuit_breaker_failures_total',
    'Total circuit breaker failures',
    ['breaker_name'],
    registry=TRON_CLIENT_REGISTRY
)

# Retry Metrics
tron_retry_attempts_total = Counter(
    'tron_retry_attempts_total',
    'Total retry attempts',
    ['operation', 'status'],
    registry=TRON_CLIENT_REGISTRY
)

# Rate Limiting Metrics
tron_rate_limit_hits_total = Counter(
    'tron_rate_limit_hits_total',
    'Total rate limit hits',
    ['endpoint'],
    registry=TRON_CLIENT_REGISTRY
)

# Service Health Metrics
tron_service_health = Gauge(
    'tron_service_health',
    'Service health status (1=healthy, 0=unhealthy)',
    ['component'],
    registry=TRON_CLIENT_REGISTRY
)

tron_service_uptime_seconds = Gauge(
    'tron_service_uptime_seconds',
    'Service uptime in seconds',
    registry=TRON_CLIENT_REGISTRY
)

# Monitoring Tasks Metrics
tron_monitoring_tasks = Gauge(
    'tron_monitoring_tasks',
    'Number of active monitoring tasks',
    registry=TRON_CLIENT_REGISTRY
)


class MetricsCollector:
    """Metrics collector for TRON client service"""
    
    def __init__(self):
        self.registry = TRON_CLIENT_REGISTRY
        self.start_time = time.time()
        self._update_uptime()
    
    def _update_uptime(self):
        """Update service uptime metric"""
        uptime = time.time() - self.start_time
        tron_service_uptime_seconds.set(uptime)
    
    def record_network_request(self, method: str, endpoint: str, status: str, duration: float):
        """Record network request metrics"""
        tron_network_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        tron_network_latency_seconds.labels(method=method, endpoint=endpoint).observe(duration)
    
    def record_network_error(self, error_type: str, endpoint: str):
        """Record network error"""
        tron_network_errors_total.labels(error_type=error_type, endpoint=endpoint).inc()
    
    def record_transaction(self, tx_type: str, status: str, duration: float, amount: Optional[int] = None):
        """Record transaction metrics"""
        tron_transactions_total.labels(type=tx_type, status=status).inc()
        tron_transaction_duration_seconds.labels(type=tx_type).observe(duration)
        if amount is not None:
            tron_transaction_amount.labels(type=tx_type).observe(amount)
    
    def update_pending_transactions(self, count: int):
        """Update pending transactions count"""
        tron_pending_transactions.set(count)
    
    def update_confirmed_transactions(self, count: int):
        """Update confirmed transactions count"""
        tron_confirmed_transactions.set(count)
    
    def record_account_operation(self, operation: str, status: str):
        """Record account operation"""
        tron_account_operations_total.labels(operation=operation, status=status).inc()
    
    def update_account_cache_size(self, size: int):
        """Update account cache size"""
        tron_account_cache_size.set(size)
    
    def update_network_status(self, connected: bool, latest_block: Optional[int] = None, sync_progress: Optional[float] = None):
        """Update network status metrics"""
        tron_network_status.set(1 if connected else 0)
        if latest_block is not None:
            tron_network_latest_block.set(latest_block)
        if sync_progress is not None:
            tron_network_sync_progress.set(sync_progress)
    
    def update_connection_pool(self, size: int, active: int, idle: int):
        """Update connection pool metrics"""
        tron_connection_pool_size.labels(state='total').set(size)
        tron_connection_pool_active.set(active)
        tron_connection_pool_idle.set(idle)
    
    def update_circuit_breaker_state(self, breaker_name: str, state: int):
        """Update circuit breaker state (0=closed, 1=open, 2=half_open)"""
        tron_circuit_breaker_state.labels(breaker_name=breaker_name).set(state)
    
    def record_circuit_breaker_failure(self, breaker_name: str):
        """Record circuit breaker failure"""
        tron_circuit_breaker_failures_total.labels(breaker_name=breaker_name).inc()
    
    def record_retry_attempt(self, operation: str, status: str):
        """Record retry attempt"""
        tron_retry_attempts_total.labels(operation=operation, status=status).inc()
    
    def record_rate_limit_hit(self, endpoint: str):
        """Record rate limit hit"""
        tron_rate_limit_hits_total.labels(endpoint=endpoint).inc()
    
    def update_service_health(self, component: str, healthy: bool):
        """Update service health status"""
        tron_service_health.labels(component=component).set(1 if healthy else 0)
    
    def update_monitoring_tasks(self, count: int):
        """Update monitoring tasks count"""
        tron_monitoring_tasks.set(count)
    
    def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus format"""
        self._update_uptime()
        return generate_latest(self.registry)
    
    def get_metrics_response(self) -> Response:
        """Get metrics as FastAPI Response"""
        return Response(
            content=self.get_prometheus_metrics(),
            media_type=CONTENT_TYPE_LATEST
        )


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector

