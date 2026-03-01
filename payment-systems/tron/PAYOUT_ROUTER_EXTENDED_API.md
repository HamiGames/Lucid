# TRON Payout Router - Extended API Support Files Documentation

**Status: ✅ API SUPPORT COMPLETE**

## Overview

The TRON Payout Router provides comprehensive routing and management for payout operations across multiple routing channels (V0, KYC, Direct, Smart). This document describes the extended API support modules and files.

## API Support Files

### 1. Payout Router API Module
**File:** `api/payout_router.py` (400+ lines)

**Purpose:** Extended FastAPI router for payout routing operations

**Key Endpoints:**

**Health & Status:**
- `GET /api/v1/payout-router/health` - Router health status
- `GET /api/v1/payout-router/routes/health` - Individual route health statuses
- `GET /api/v1/payout-router/routes/analytics` - Route analytics

**Payout Routing:**
- `POST /api/v1/payout-router/assign-route` - Assign single payout route
- `POST /api/v1/payout-router/assign-batch` - Batch route assignment
- `POST /api/v1/payout-router/optimize-routes` - Route optimization

**Request Models:**

```python
PayoutRouterRequest:
  - payout_id: str
  - recipient_address: str
  - amount: float (>0, ≤1B)
  - asset_type: str (TRX, USDT, etc)
  - preferred_route: PayoutRouteType (optional)
  - priority: RoutingPriority (low, normal, high, critical)
  - metadata: Dict (optional)

PayoutRouterBatchRequest:
  - payouts: List[PayoutRouterRequest] (1-1000 items)
  - batch_id: str (optional)
  - strategy: str (optimal, balanced, fast, cost-efficient)

RouteOptimizationRequest:
  - payouts: List[Dict]
  - optimization_criteria: str (cost, speed, reliability)
  - max_routes: int (1-10)
```

**Response Models:**

```python
PayoutRouterResponse:
  - payout_id: str
  - assigned_route: str
  - route_status: str
  - estimated_fee: float
  - estimated_time_minutes: int
  - confidence_score: float (0-100)
  - priority: str
  - assigned_at: str
  - expires_at: str

RouteHealthResponse:
  - route_type: str
  - status: str (operational, unavailable, degraded, offline)
  - success_rate: float (0-100)
  - average_time_minutes: float
  - current_queue_size: int
  - estimated_wait_time_minutes: int
  - last_checked: str

RouteAnalyticsResponse:
  - route_type: str
  - total_payouts: int
  - total_amount: float
  - success_count: int
  - failed_count: int
  - average_time_minutes: float
  - p95_time_minutes: float
  - p99_time_minutes: float
```

**Features:**
- Smart route selection based on amount, priority, and load
- Batch processing with multiple strategies
- Route health monitoring
- Analytics and performance metrics
- Route optimization recommendations
- Background task processing

---

### 2. Payout Router Service Module
**File:** `services/payout_router.py` (450+ lines)

**Purpose:** Core payout routing business logic

**Key Functionality:**

**Route Management:**
- `route_payout()` - Route individual payout
- `route_batch()` - Batch routing
- `_select_optimal_route()` - Route selection algorithm
- `_route_available()` - Route availability check
- `_calculate_fee()` - Fee calculation

**Payout Tracking:**
- `get_payout_status()` - Get payout status
- `get_batch_status()` - Get batch status
- `complete_payout()` - Mark payout as completed
- `cancel_payout()` - Cancel payout

**Monitoring:**
- `get_route_health()` - Route health status
- `get_metrics()` - Service metrics

**Available Routes:**

| Route | Capacity | Min/Max | Time | Fee | KYC |
|---|---|---|---|---|---|
| V0 | 1000 | 100/1M | 5.2m | 0.1% | No |
| KYC | 500 | 100/500K | 7.1m | 0.15% | Yes |
| Direct | 100 | 1K/100K | 3.5m | 0.2% | No |

**Route Selection Algorithm:**
1. If preferred route specified and available → use it
2. If critical priority → prioritize Direct route
3. If amount > 50K → use V0 router
4. If amount > 10K → use KYC router
5. Load-balance across available routes

**Configuration Parameters:**
```python
routes[route_type] = {
    "name": str,
    "status": str,
    "capacity": int,
    "active_payouts": int,
    "success_rate": float,
    "average_time_minutes": float,
    "fee_percentage": float,
}
```

---

### 3. Configuration File
**File:** `config/payout-router-extended-config.yaml` (350+ lines)

**Purpose:** Comprehensive payout router configuration

**Configuration Sections:**

**Route Configuration:**
```yaml
router:
  routes:
    v0:
      name: V0 Router
      capacity: 1000
      max_amount: 1000000
      fee_percentage: 0.1
      success_rate_target: 99.5
    
    kyc:
      name: KYC Router
      capacity: 500
      fee_percentage: 0.15
      requires_kyc: true
    
    direct:
      name: Direct Router
      capacity: 100
      fee_percentage: 0.2
```

**Routing Strategies:**
```yaml
strategies:
  optimal: "Select best route"
  balanced: "Balance cost & speed"
  fast: "Prioritize speed"
  cost_efficient: "Prioritize cost"
```

**Priority Levels:**
```yaml
priorities:
  critical:
    timeout_hours: 1
    retry_attempts: 10
    fee_discount_percent: -10
  high:
    timeout_hours: 2
    retry_attempts: 5
  normal:
    timeout_hours: 6
    retry_attempts: 3
  low:
    timeout_hours: 24
    retry_attempts: 1
```

**Batch Processing:**
```yaml
batch_processing:
  enabled: true
  max_batch_size: 1000
  concurrent_processing: true
  max_concurrent_batches: 10
```

**Limits:**
```yaml
payout_limits:
  min_amount: 1
  max_single_payout: 1000000
  max_daily_total: 100000000
  max_concurrent_payouts: 10000
```

**Monitoring & Metrics:**
```yaml
monitoring:
  metrics_enabled: true
  collect_metrics:
    - total_routed_count
    - total_routed_amount
    - success_count
    - average_routing_time
    - route_distribution
```

---

## Payout Routing Workflow

### Single Payout Routing

1. **Request Reception**
   - Receive `PayoutRouterRequest` with payout details
   - Validate amount, recipient, and priority

2. **Route Selection**
   - Analyze payout characteristics (amount, priority)
   - Check route availability and capacity
   - Select optimal route based on criteria

3. **Assignment**
   - Assign route and calculate fees
   - Create payout record
   - Return assignment details with timing/cost

4. **Background Processing**
   - Process payout on assigned route
   - Track status and completion

### Batch Routing

1. **Batch Reception**
   - Receive `PayoutRouterBatchRequest`
   - Validate batch size (1-1000 items)

2. **Parallel Processing**
   - Route each payout using single payout logic
   - Apply batch strategy if specified

3. **Aggregation**
   - Combine results
   - Calculate batch-level metrics

4. **Return Results**
   - Return batch processing summary

## Route Health & Monitoring

**Health Status Indicators:**
- `operational` - Route functioning normally
- `degraded` - Route with reduced capacity/performance
- `unavailable` - Route temporarily offline
- `offline` - Route not operational

**Health Check Metrics:**
- Success rate (0-100%)
- Average processing time
- Queue size and wait times
- Current capacity utilization

**Analytics Metrics:**
- Total payouts processed
- Total amount routed
- Success/failure counts
- Performance percentiles (p50, p95, p99)

## Route Optimization

**Optimization Criteria:**
- `cost` - Minimize fees
- `speed` - Minimize processing time
- `reliability` - Maximize success rate

**Optimization Output:**
- Recommended route assignments
- Potential savings (cost, time)
- Confidence score
- Reasoning/recommendation

## Error Handling & Retry

**Failure Handling:**
- Automatic retry with exponential backoff
- Max retry attempts: 3
- Initial delay: 5 seconds
- Max delay: 300 seconds

**Circuit Breaker:**
- Enabled: true
- Failure threshold: 50%
- Recovery timeout: 5 minutes

## Metrics & Monitoring

**Collected Metrics:**
- `total_routed` - Total payouts routed
- `total_amount` - Total amount routed
- `successful_routes` - Successful routing operations
- `failed_routes` - Failed routing operations
- `average_route_time` - Average routing time

**Performance Metrics:**
- p50 latency (median)
- p95 latency (95th percentile)
- p99 latency (99th percentile)
- Success rate by route

## API Usage Examples

### Assign Single Route

```bash
curl -X POST http://localhost:8092/api/v1/payout-router/assign-route \
  -H "Content-Type: application/json" \
  -d '{
    "payout_id": "payout_123",
    "recipient_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
    "amount": 5000.0,
    "asset_type": "TRX",
    "priority": "normal"
  }'
```

### Batch Routing

```bash
curl -X POST http://localhost:8092/api/v1/payout-router/assign-batch \
  -H "Content-Type: application/json" \
  -d '{
    "payouts": [
      {
        "payout_id": "payout_1",
        "recipient_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
        "amount": 1000.0,
        "asset_type": "TRX"
      },
      ...
    ],
    "strategy": "optimal"
  }'
```

### Route Health Check

```bash
curl http://localhost:8092/api/v1/payout-router/routes/health
```

### Route Optimization

```bash
curl -X POST http://localhost:8092/api/v1/payout-router/optimize-routes \
  -H "Content-Type: application/json" \
  -d '{
    "payouts": [...],
    "optimization_criteria": "cost",
    "max_routes": 5
  }'
```

## Configuration Examples

### High Priority Payout

```python
PayoutRouterRequest(
    payout_id="critical_123",
    amount=50000.0,
    priority=RoutingPriority.CRITICAL,  # Uses Direct route
    preferred_route=PayoutRouteType.DIRECT_ROUTER,
)
```

### Batch Cost Optimization

```python
PayoutRouterBatchRequest(
    payouts=[...100 payouts...],
    strategy="cost_efficient",  # Minimizes fees
)
```

### Route Reliability Optimization

```python
RouteOptimizationRequest(
    payouts=[...],
    optimization_criteria="reliability",  # Maximizes success rate
)
```

## Troubleshooting

### Route Unavailable
- Check route health: `GET /routes/health`
- Verify route capacity not exceeded
- Check for circuit breaker activation

### High Fees
- Use `cost_efficient` strategy
- Consider batch processing (15% discount)
- Check peak hour surcharges (5%)

### Slow Processing
- Check queue size
- Consider `fast` strategy
- Use `high` priority if urgent

### Batch Processing Failures
- Verify batch size (max 1000)
- Check individual payout validity
- Monitor failed_payouts count

## Summary

The TRON Payout Router API support provides:
- ✅ Smart multi-route payout routing
- ✅ Batch processing with strategies
- ✅ Route health monitoring
- ✅ Performance analytics
- ✅ Cost optimization
- ✅ Automatic retry and recovery
- ✅ Comprehensive metrics collection
- ✅ Production-ready reliability

**Total Implementation:**
- API Module: 400+ lines
- Service Module: 450+ lines
- Configuration: 350+ lines
- Complete feature set for enterprise-grade payout routing
