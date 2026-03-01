# TRON Payment System API - Monitoring & Alerting

## Document Control

| Attribute | Value |
|-----------|-------|
| Document ID | TRON-API-MON-010 |
| Version | 1.0.0 |
| Status | IN PROGRESS |
| Last Updated | 2025-10-12 |
| Owner | Lucid RDP Development Team |

---

## Overview

This document defines comprehensive monitoring and alerting strategies for the TRON Payment System API, covering Prometheus metrics, Grafana dashboards, health checks, log aggregation, and alert management according to SPEC-1B-v2 requirements.

### Monitoring Principles

- **Observability**: Complete visibility into system behavior
- **Proactive Monitoring**: Early detection of issues
- **Business Metrics**: Payment-specific KPIs and SLAs
- **Security Monitoring**: Threat detection and response
- **Performance Tracking**: Latency, throughput, and resource usage

---

## Prometheus Metrics Endpoint

### Metrics Implementation

```python
# payment_systems/tron_payment_service/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response
import time
from typing import Dict, Any

# Payment-specific metrics
payout_requests_total = Counter(
    'tron_payment_requests_total',
    'Total payout requests',
    ['router_type', 'priority', 'status']
)

payout_amount_usdt_total = Counter(
    'tron_payout_amount_usdt_total',
    'Total payout amount in USDT',
    ['router_type']
)

payout_processing_duration_seconds = Histogram(
    'tron_payout_processing_duration_seconds',
    'Time spent processing payouts',
    ['router_type', 'status'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]
)

circuit_breaker_status = Gauge(
    'tron_circuit_breaker_status',
    'Circuit breaker status (0=closed, 1=open, 2=half_open)'
)

daily_limit_usage_usdt = Gauge(
    'tron_daily_limit_usage_usdt',
    'Current daily limit usage in USDT'
)

hourly_limit_usage_usdt = Gauge(
    'tron_hourly_limit_usage_usdt',
    'Current hourly limit usage in USDT'
)

pending_payouts_count = Gauge(
    'tron_pending_payouts_count',
    'Number of pending payouts'
)

confirmed_payouts_count = Gauge(
    'tron_confirmed_payouts_count',
    'Number of confirmed payouts'
)

failed_payouts_count = Gauge(
    'tron_failed_payouts_count',
    'Number of failed payouts'
)

tron_network_latency_seconds = Histogram(
    'tron_network_latency_seconds',
    'TRON network request latency',
    ['operation'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

tron_network_errors_total = Counter(
    'tron_network_errors_total',
    'Total TRON network errors',
    ['error_type', 'operation']
)

database_connections_active = Gauge(
    'tron_database_connections_active',
    'Number of active database connections'
)

database_operations_duration_seconds = Histogram(
    'tron_database_operations_duration_seconds',
    'Database operation duration',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0]
)

authentication_failures_total = Counter(
    'tron_authentication_failures_total',
    'Total authentication failures',
    ['failure_type']
)

rate_limit_violations_total = Counter(
    'tron_rate_limit_violations_total',
    'Total rate limit violations',
    ['endpoint', 'user_type']
)

# System metrics
memory_usage_bytes = Gauge(
    'tron_memory_usage_bytes',
    'Memory usage in bytes'
)

cpu_usage_percent = Gauge(
    'tron_cpu_usage_percent',
    'CPU usage percentage'
)

disk_usage_bytes = Gauge(
    'tron_disk_usage_bytes',
    'Disk usage in bytes'
)

class MetricsCollector:
    """Metrics collection and management"""
    
    def __init__(self):
        self.start_time = time.time()
    
    def record_payout_request(
        self,
        router_type: str,
        priority: str,
        status: str,
        amount_usdt: float,
        duration: float
    ):
        """Record payout request metrics"""
        payout_requests_total.labels(
            router_type=router_type,
            priority=priority,
            status=status
        ).inc()
        
        payout_amount_usdt_total.labels(router_type=router_type).inc(amount_usdt)
        
        payout_processing_duration_seconds.labels(
            router_type=router_type,
            status=status
        ).observe(duration)
    
    def update_circuit_breaker_status(self, status: str):
        """Update circuit breaker status"""
        status_map = {"closed": 0, "open": 1, "half_open": 2}
        circuit_breaker_status.set(status_map.get(status, 0))
    
    def update_limit_usage(self, daily_usage: float, hourly_usage: float):
        """Update limit usage metrics"""
        daily_limit_usage_usdt.set(daily_usage)
        hourly_limit_usage_usdt.set(hourly_usage)
    
    def update_payout_counts(self, pending: int, confirmed: int, failed: int):
        """Update payout count metrics"""
        pending_payouts_count.set(pending)
        confirmed_payouts_count.set(confirmed)
        failed_payouts_count.set(failed)
    
    def record_tron_network_request(self, operation: str, duration: float, success: bool):
        """Record TRON network request metrics"""
        tron_network_latency_seconds.labels(operation=operation).observe(duration)
        
        if not success:
            tron_network_errors_total.labels(
                error_type="request_failed",
                operation=operation
            ).inc()
    
    def update_database_metrics(self, active_connections: int, operation: str, duration: float):
        """Update database metrics"""
        database_connections_active.set(active_connections)
        database_operations_duration_seconds.labels(operation=operation).observe(duration)
    
    def record_auth_failure(self, failure_type: str):
        """Record authentication failure"""
        authentication_failures_total.labels(failure_type=failure_type).inc()
    
    def record_rate_limit_violation(self, endpoint: str, user_type: str):
        """Record rate limit violation"""
        rate_limit_violations_total.labels(endpoint=endpoint, user_type=user_type).inc()
    
    def update_system_metrics(self):
        """Update system resource metrics"""
        import psutil
        import os
        
        # Memory usage
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_usage_bytes.set(memory_info.rss)
        
        # CPU usage
        cpu_percent = process.cpu_percent()
        cpu_usage_percent.set(cpu_percent)
        
        # Disk usage
        disk_usage = psutil.disk_usage('/')
        disk_usage_bytes.set(disk_usage.used)

# Global metrics collector instance
metrics_collector = MetricsCollector()

# FastAPI endpoint for metrics
async def get_metrics() -> Response:
    """Prometheus metrics endpoint"""
    # Update system metrics
    metrics_collector.update_system_metrics()
    
    # Generate metrics output
    metrics_output = generate_latest()
    
    return Response(
        content=metrics_output,
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )
```

### Metrics Middleware

```python
# payment_systems/tron_payment_service/middleware.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import psutil
import os

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect request metrics"""
    
    def __init__(self, app, metrics_collector):
        super().__init__(app)
        self.metrics_collector = metrics_collector
    
    async def dispatch(self, request: Request, call_next):
        # Record request start time
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate request duration
        duration = time.time() - start_time
        
        # Extract metrics from request
        endpoint = request.url.path
        method = request.method
        status_code = response.status_code
        
        # Record metrics based on endpoint
        if endpoint.startswith("/api/payment/payouts"):
            if method == "POST":
                # This would be enhanced with actual payout data
                self.metrics_collector.record_payout_request(
                    router_type="unknown",  # Would be extracted from request
                    priority="normal",      # Would be extracted from request
                    status="success" if status_code < 400 else "failed",
                    amount_usdt=0.0,       # Would be extracted from request
                    duration=duration
                )
        
        # Record authentication failures
        if status_code == 401:
            self.metrics_collector.record_auth_failure("unauthorized")
        elif status_code == 403:
            self.metrics_collector.record_auth_failure("forbidden")
        
        # Record rate limit violations
        if status_code == 429:
            user_type = request.headers.get("X-User-Role", "unknown")
            self.metrics_collector.record_rate_limit_violation(endpoint, user_type)
        
        return response
```

---

## Key Metrics Catalog

### Business Metrics

| Metric Name | Type | Description | Labels |
|-------------|------|-------------|---------|
| `tron_payment_requests_total` | Counter | Total payout requests | `router_type`, `priority`, `status` |
| `tron_payout_amount_usdt_total` | Counter | Total payout amount in USDT | `router_type` |
| `tron_pending_payouts_count` | Gauge | Number of pending payouts | - |
| `tron_confirmed_payouts_count` | Gauge | Number of confirmed payouts | - |
| `tron_failed_payouts_count` | Gauge | Number of failed payouts | - |

### Performance Metrics

| Metric Name | Type | Description | Labels |
|-------------|------|-------------|---------|
| `tron_payout_processing_duration_seconds` | Histogram | Payout processing time | `router_type`, `status` |
| `tron_network_latency_seconds` | Histogram | TRON network latency | `operation` |
| `tron_database_operations_duration_seconds` | Histogram | Database operation time | `operation` |

### Security Metrics

| Metric Name | Type | Description | Labels |
|-------------|------|-------------|---------|
| `tron_circuit_breaker_status` | Gauge | Circuit breaker status | - |
| `tron_daily_limit_usage_usdt` | Gauge | Daily limit usage | - |
| `tron_hourly_limit_usage_usdt` | Gauge | Hourly limit usage | - |
| `tron_authentication_failures_total` | Counter | Authentication failures | `failure_type` |
| `tron_rate_limit_violations_total` | Counter | Rate limit violations | `endpoint`, `user_type` |

### System Metrics

| Metric Name | Type | Description | Labels |
|-------------|------|-------------|---------|
| `tron_memory_usage_bytes` | Gauge | Memory usage | - |
| `tron_cpu_usage_percent` | Gauge | CPU usage percentage | - |
| `tron_disk_usage_bytes` | Gauge | Disk usage | - |
| `tron_database_connections_active` | Gauge | Active DB connections | - |

---

## Grafana Dashboard JSON Specifications

### Main Dashboard

```json
{
  "dashboard": {
    "id": null,
    "title": "TRON Payment System API",
    "tags": ["tron", "payment", "api"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Payout Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(tron_payment_requests_total{status=\"confirmed\"}[5m]) / rate(tron_payment_requests_total[5m]) * 100",
            "legendFormat": "Success Rate %"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "min": 0,
            "max": 100,
            "thresholds": {
              "steps": [
                {"color": "red", "value": null},
                {"color": "yellow", "value": 90},
                {"color": "green", "value": 95}
              ]
            }
          }
        },
        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "Daily Payout Volume (USDT)",
        "type": "stat",
        "targets": [
          {
            "expr": "increase(tron_payout_amount_usdt_total[24h])",
            "legendFormat": "Daily Volume"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "currencyUSD",
            "decimals": 2
          }
        },
        "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0}
      },
      {
        "id": 3,
        "title": "Circuit Breaker Status",
        "type": "stat",
        "targets": [
          {
            "expr": "tron_circuit_breaker_status",
            "legendFormat": "Status"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "mappings": [
              {"options": {"0": {"text": "Closed"}}, "type": "value"},
              {"options": {"1": {"text": "Open"}}, "type": "value"},
              {"options": {"2": {"text": "Half Open"}}, "type": "value"}
            ],
            "thresholds": {
              "steps": [
                {"color": "green", "value": null},
                {"color": "yellow", "value": 1},
                {"color": "red", "value": 2}
              ]
            }
          }
        },
        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0}
      },
      {
        "id": 4,
        "title": "Pending Payouts",
        "type": "stat",
        "targets": [
          {
            "expr": "tron_pending_payouts_count",
            "legendFormat": "Pending"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "short",
            "thresholds": {
              "steps": [
                {"color": "green", "value": null},
                {"color": "yellow", "value": 50},
                {"color": "red", "value": 100}
              ]
            }
          }
        },
        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0}
      },
      {
        "id": 5,
        "title": "Payout Processing Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(tron_payout_processing_duration_seconds_bucket[5m]))",
            "legendFormat": "P50"
          },
          {
            "expr": "histogram_quantile(0.95, rate(tron_payout_processing_duration_seconds_bucket[5m]))",
            "legendFormat": "P95"
          },
          {
            "expr": "histogram_quantile(0.99, rate(tron_payout_processing_duration_seconds_bucket[5m]))",
            "legendFormat": "P99"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "s"
          }
        },
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
      },
      {
        "id": 6,
        "title": "TRON Network Latency",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(tron_network_latency_seconds_bucket[5m]))",
            "legendFormat": "P50"
          },
          {
            "expr": "histogram_quantile(0.95, rate(tron_network_latency_seconds_bucket[5m]))",
            "legendFormat": "P95"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "s"
          }
        },
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
      },
      {
        "id": 7,
        "title": "Payout Requests by Router Type",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(tron_payment_requests_total[5m])",
            "legendFormat": "{{router_type}}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "reqps"
          }
        },
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16}
      },
      {
        "id": 8,
        "title": "Daily Limit Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "tron_daily_limit_usage_usdt",
            "legendFormat": "Daily Usage"
          },
          {
            "expr": "tron_hourly_limit_usage_usdt",
            "legendFormat": "Hourly Usage"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "currencyUSD"
          }
        },
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16}
      },
      {
        "id": 9,
        "title": "Authentication Failures",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(tron_authentication_failures_total[5m])",
            "legendFormat": "{{failure_type}}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "reqps"
          }
        },
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 24}
      },
      {
        "id": 10,
        "title": "Rate Limit Violations",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(tron_rate_limit_violations_total[5m])",
            "legendFormat": "{{endpoint}}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "reqps"
          }
        },
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 24}
      },
      {
        "id": 11,
        "title": "System Resources",
        "type": "graph",
        "targets": [
          {
            "expr": "tron_memory_usage_bytes / 1024 / 1024",
            "legendFormat": "Memory (MB)"
          },
          {
            "expr": "tron_cpu_usage_percent",
            "legendFormat": "CPU %"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "short"
          }
        },
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 32}
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
```

---

## Alerting Rules

### Prometheus Alerting Rules

```yaml
# alerting-rules.yml
groups:
  - name: tron-payment-api
    rules:
      # Critical alerts
      - alert: CircuitBreakerOpen
        expr: tron_circuit_breaker_status == 1
        for: 0m
        labels:
          severity: critical
          service: tron-payment-api
        annotations:
          summary: "Circuit breaker is open"
          description: "TRON Payment API circuit breaker is open, blocking all requests"
          runbook_url: "https://docs.lucid-rdp.onion/runbooks/circuit-breaker-open"
      
      - alert: HighFailureRate
        expr: rate(tron_payment_requests_total{status="failed"}[5m]) / rate(tron_payment_requests_total[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
          service: tron-payment-api
        annotations:
          summary: "High payout failure rate"
          description: "Payout failure rate is {{ $value | humanizePercentage }} over the last 5 minutes"
          runbook_url: "https://docs.lucid-rdp.onion/runbooks/high-failure-rate"
      
      - alert: DailyLimitExceeded
        expr: tron_daily_limit_usage_usdt > 9000
        for: 0m
        labels:
          severity: critical
          service: tron-payment-api
        annotations:
          summary: "Daily limit usage exceeded 90%"
          description: "Daily limit usage is {{ $value }} USDT (90% of 10,000 USDT limit)"
          runbook_url: "https://docs.lucid-rdp.onion/runbooks/daily-limit-exceeded"
      
      # Warning alerts
      - alert: HighPendingPayouts
        expr: tron_pending_payouts_count > 50
        for: 5m
        labels:
          severity: warning
          service: tron-payment-api
        annotations:
          summary: "High number of pending payouts"
          description: "{{ $value }} payouts are pending for more than 5 minutes"
          runbook_url: "https://docs.lucid-rdp.onion/runbooks/high-pending-payouts"
      
      - alert: SlowPayoutProcessing
        expr: histogram_quantile(0.95, rate(tron_payout_processing_duration_seconds_bucket[5m])) > 30
        for: 5m
        labels:
          severity: warning
          service: tron-payment-api
        annotations:
          summary: "Slow payout processing"
          description: "P95 payout processing time is {{ $value }}s"
          runbook_url: "https://docs.lucid-rdp.onion/runbooks/slow-payout-processing"
      
      - alert: HighTRONNetworkLatency
        expr: histogram_quantile(0.95, rate(tron_network_latency_seconds_bucket[5m])) > 10
        for: 5m
        labels:
          severity: warning
          service: tron-payment-api
        annotations:
          summary: "High TRON network latency"
          description: "P95 TRON network latency is {{ $value }}s"
          runbook_url: "https://docs.lucid-rdp.onion/runbooks/high-tron-latency"
      
      - alert: HighAuthenticationFailures
        expr: rate(tron_authentication_failures_total[5m]) > 10
        for: 2m
        labels:
          severity: warning
          service: tron-payment-api
        annotations:
          summary: "High authentication failure rate"
          description: "Authentication failure rate is {{ $value }} failures/sec"
          runbook_url: "https://docs.lucid-rdp.onion/runbooks/high-auth-failures"
      
      - alert: HighRateLimitViolations
        expr: rate(tron_rate_limit_violations_total[5m]) > 5
        for: 2m
        labels:
          severity: warning
          service: tron-payment-api
        annotations:
          summary: "High rate limit violation rate"
          description: "Rate limit violation rate is {{ $value }} violations/sec"
          runbook_url: "https://docs.lucid-rdp.onion/runbooks/high-rate-limit-violations"
      
      # Info alerts
      - alert: ServiceDown
        expr: up{job="tron-payment-api"} == 0
        for: 1m
        labels:
          severity: critical
          service: tron-payment-api
        annotations:
          summary: "TRON Payment API service is down"
          description: "TRON Payment API service has been down for more than 1 minute"
          runbook_url: "https://docs.lucid-rdp.onion/runbooks/service-down"
      
      - alert: HighMemoryUsage
        expr: tron_memory_usage_bytes / 1024 / 1024 > 800
        for: 5m
        labels:
          severity: warning
          service: tron-payment-api
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value }}MB (80% of 1GB limit)"
          runbook_url: "https://docs.lucid-rdp.onion/runbooks/high-memory-usage"
      
      - alert: HighCPUUsage
        expr: tron_cpu_usage_percent > 80
        for: 5m
        labels:
          severity: warning
          service: tron-payment-api
        annotations:
          summary: "High CPU usage"
          description: "CPU usage is {{ $value }}%"
          runbook_url: "https://docs.lucid-rdp.onion/runbooks/high-cpu-usage"
```

### Alert Severity Levels

| Severity | Description | Response Time | Escalation |
|----------|-------------|---------------|------------|
| **Critical** | Service unavailable, circuit breaker open, limit exceeded | 5 minutes | Immediate escalation |
| **Warning** | Performance degradation, high error rates | 15 minutes | Team notification |
| **Info** | Operational notifications, maintenance windows | 1 hour | Logged for review |

---

## Health Check Endpoints

### Comprehensive Health Check

```python
# payment_systems/tron_payment_service/health.py
from fastapi import APIRouter, status
from typing import Dict, Any
import asyncio
import httpx
import time
from datetime import datetime

router = APIRouter(tags=["health"])

class HealthChecker:
    """Comprehensive health check implementation"""
    
    def __init__(self, mongo_client, tron_service, circuit_breaker):
        self.mongo_client = mongo_client
        self.tron_service = tron_service
        self.circuit_breaker = circuit_breaker
    
    async def check_tron_network(self) -> Dict[str, Any]:
        """Check TRON network connectivity"""
        try:
            start_time = time.time()
            # Test TRON network connection
            balance = await self.tron_service.get_balance("TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH")
            duration = time.time() - start_time
            
            return {
                "status": "healthy",
                "network": "mainnet",
                "response_time": duration,
                "balance_check": "success"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "network": "mainnet",
                "error": str(e),
                "response_time": None
            }
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            start_time = time.time()
            # Test database connection
            await self.mongo_client.admin.command('ping')
            duration = time.time() - start_time
            
            return {
                "status": "healthy",
                "connection": "active",
                "response_time": duration
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connection": "failed",
                "error": str(e),
                "response_time": None
            }
    
    async def check_circuit_breaker(self) -> Dict[str, Any]:
        """Check circuit breaker status"""
        return {
            "status": self.circuit_breaker.state,
            "daily_limit_remaining": 10000 - self.circuit_breaker.daily_usage,
            "hourly_limit_remaining": 1000 - self.circuit_breaker.hourly_usage,
            "failure_count": self.circuit_breaker.failure_count
        }
    
    async def check_dependencies(self) -> Dict[str, Any]:
        """Check external dependencies"""
        dependencies = {}
        
        # Check Tor proxy
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://httpbin.org/ip",
                    proxies={"http://": "socks5://tor-proxy:9050"},
                    timeout=10.0
                )
                dependencies["tor_proxy"] = {
                    "status": "healthy",
                    "response_time": response.elapsed.total_seconds()
                }
        except Exception as e:
            dependencies["tor_proxy"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        return dependencies

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check for TRON Payment Service
    """
    health_checker = HealthChecker(mongo_client, tron_service, circuit_breaker)
    
    # Run all health checks in parallel
    tron_check, db_check, cb_check, deps_check = await asyncio.gather(
        health_checker.check_tron_network(),
        health_checker.check_database(),
        health_checker.check_circuit_breaker(),
        health_checker.check_dependencies(),
        return_exceptions=True
    )
    
    # Determine overall health status
    overall_status = "healthy"
    if any([
        tron_check.get("status") == "unhealthy",
        db_check.get("status") == "unhealthy",
        cb_check.get("status") == "open"
    ]):
        overall_status = "unhealthy"
    
    return {
        "status": overall_status,
        "service": "tron-payment-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "tron": tron_check,
            "mongo": db_check,
            "circuit_breaker": cb_check,
            "dependencies": deps_check
        }
    }

@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check for Kubernetes/Docker
    """
    try:
        # Check critical dependencies
        await mongo_client.admin.command('ping')
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "not_ready",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check for Kubernetes/Docker
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

## Log Aggregation Strategy

### Structured JSON Logging

```python
# payment_systems/tron_payment_service/logging.py
import structlog
import logging
import json
from datetime import datetime
from typing import Dict, Any

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Create logger
logger = structlog.get_logger()

class PaymentLogger:
    """Structured logger for payment operations"""
    
    def __init__(self, service_name: str = "tron-payment-service"):
        self.service_name = service_name
        self.logger = logger.bind(service=service_name)
    
    def log_payout_request(
        self,
        payout_id: str,
        user_id: str,
        amount_usdt: float,
        router_type: str,
        request_id: str
    ):
        """Log payout request"""
        self.logger.info(
            "payout_request_created",
            payout_id=payout_id,
            user_id=user_id,
            amount_usdt=amount_usdt,
            router_type=router_type,
            request_id=request_id,
            event_type="payout_request"
        )
    
    def log_payout_success(
        self,
        payout_id: str,
        txid: str,
        duration: float,
        request_id: str
    ):
        """Log successful payout"""
        self.logger.info(
            "payout_successful",
            payout_id=payout_id,
            txid=txid,
            duration=duration,
            request_id=request_id,
            event_type="payout_success"
        )
    
    def log_payout_failure(
        self,
        payout_id: str,
        error: str,
        duration: float,
        request_id: str
    ):
        """Log failed payout"""
        self.logger.error(
            "payout_failed",
            payout_id=payout_id,
            error=error,
            duration=duration,
            request_id=request_id,
            event_type="payout_failure"
        )
    
    def log_circuit_breaker_event(
        self,
        event: str,
        reason: str,
        daily_usage: float,
        hourly_usage: float
    ):
        """Log circuit breaker events"""
        self.logger.warning(
            "circuit_breaker_event",
            event=event,
            reason=reason,
            daily_usage=daily_usage,
            hourly_usage=hourly_usage,
            event_type="circuit_breaker"
        )
    
    def log_security_event(
        self,
        event_type: str,
        user_id: str,
        ip_address: str,
        details: Dict[str, Any]
    ):
        """Log security events"""
        self.logger.warning(
            "security_event",
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            details=details,
            event_type="security"
        )

# Global logger instance
payment_logger = PaymentLogger()
```

### Log Rotation Configuration

```yaml
# /etc/logrotate.d/tron-payment-service
/opt/lucid/logs/tron-payment/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
    postrotate
        docker kill -s USR1 tron-payment-service
    endscript
}
```

---

## Performance Monitoring and SLOs

### Service Level Objectives (SLOs)

| Metric | SLO | Measurement Period | Alert Threshold |
|--------|-----|-------------------|-----------------|
| **Availability** | 99.9% | 30 days | < 99.5% |
| **Payout Success Rate** | 99.5% | 24 hours | < 99.0% |
| **Payout Processing Time** | P95 < 30s | 24 hours | P95 > 60s |
| **API Response Time** | P95 < 2s | 24 hours | P95 > 5s |
| **Circuit Breaker Uptime** | 99.9% | 30 days | < 99.0% |

### Performance Monitoring Implementation

```python
# payment_systems/tron_payment_service/slo_monitor.py
from prometheus_client import Counter, Histogram
from datetime import datetime, timedelta
import asyncio

class SLOMonitor:
    """Service Level Objective monitoring"""
    
    def __init__(self):
        # SLO metrics
        self.total_requests = Counter(
            'slo_total_requests',
            'Total requests for SLO calculation'
        )
        
        self.successful_requests = Counter(
            'slo_successful_requests',
            'Successful requests for SLO calculation'
        )
        
        self.request_duration = Histogram(
            'slo_request_duration_seconds',
            'Request duration for SLO calculation',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )
        
        self.payout_duration = Histogram(
            'slo_payout_duration_seconds',
            'Payout duration for SLO calculation',
            buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
        )
    
    def record_request(self, success: bool, duration: float):
        """Record request for SLO calculation"""
        self.total_requests.inc()
        if success:
            self.successful_requests.inc()
        self.request_duration.observe(duration)
    
    def record_payout(self, success: bool, duration: float):
        """Record payout for SLO calculation"""
        self.payout_duration.observe(duration)
    
    async def calculate_slo_metrics(self) -> Dict[str, Any]:
        """Calculate current SLO metrics"""
        # This would typically query Prometheus for the last 24 hours
        # For now, return mock data
        return {
            "availability_24h": 99.95,
            "payout_success_rate_24h": 99.7,
            "p95_response_time_24h": 1.2,
            "p95_payout_time_24h": 15.5,
            "circuit_breaker_uptime_24h": 99.98
        }

# Global SLO monitor
slo_monitor = SLOMonitor()
```

---

## Alert Management and Response

### Alert Response Runbooks

```markdown
# Circuit Breaker Open Runbook

## Symptoms
- All payout requests are being rejected
- Circuit breaker status shows "open"
- High error rate in logs

## Immediate Actions
1. Check circuit breaker status: `curl http://localhost:8090/health`
2. Review recent error logs: `docker logs tron-payment-service --tail=100`
3. Check TRON network status
4. Verify daily/hourly limits

## Resolution Steps
1. If daily limit exceeded:
   - Wait for next day reset
   - Or increase daily limit (requires approval)
2. If hourly limit exceeded:
   - Wait for next hour reset
   - Or increase hourly limit (requires approval)
3. If TRON network issues:
   - Check TRON network status
   - Switch to backup TRON node if available
4. If service issues:
   - Restart service: `docker-compose restart tron-payment-service`
   - Check resource usage
   - Scale service if needed

## Prevention
- Monitor daily/hourly usage trends
- Set up proactive alerts at 80% usage
- Implement gradual limit increases
- Regular TRON network health checks
```

### Alert Escalation Matrix

| Alert Type | Level 1 | Level 2 | Level 3 | Response Time |
|------------|---------|---------|---------|---------------|
| Circuit Breaker Open | On-call Engineer | Team Lead | CTO | 5 minutes |
| High Failure Rate | On-call Engineer | Team Lead | - | 10 minutes |
| Service Down | On-call Engineer | Team Lead | CTO | 5 minutes |
| Security Incident | On-call Engineer | Security Team | CISO | Immediate |
| Performance Degradation | On-call Engineer | Team Lead | - | 15 minutes |

---

## References

- [09_DEPLOYMENT_PROCEDURES.md](09_DEPLOYMENT_PROCEDURES.md) - Deployment monitoring
- [07_SECURITY_COMPLIANCE.md](07_SECURITY_COMPLIANCE.md) - Security monitoring
- [Prometheus Documentation](https://prometheus.io/docs/) - Metrics collection
- [Grafana Documentation](https://grafana.com/docs/) - Dashboard creation
- [AlertManager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/) - Alert management

---

**Document Status**: [IN PROGRESS]  
**Last Review**: 2025-10-12  
**Next Review**: 2025-11-12
