# TRON Payment System API - API Specifications

## Document Control

| Attribute | Value |
|-----------|-------|
| Document ID | TRON-API-SPEC-004 |
| Version | 1.0.0 |
| Status | IN PROGRESS |
| Last Updated | 2025-10-12 |
| Owner | Lucid RDP Development Team |

---

## Overview

This document defines the complete REST API specification for the TRON Payment System. All endpoints are accessed through the API Gateway at `/api/payment/*` with JWT authentication and rate limiting applied.

### Base URL

```
Production: https://gateway.onion/api/payment
Development: http://localhost:8080/api/payment
```

### Authentication

All endpoints require JWT authentication via API Gateway. Internal service communication uses header-based validation.

---

## Endpoint Catalog

### 1. Payout Management

#### Create Payout
```http
POST /api/payment/payouts
```

**Purpose**: Create a new USDT payout request

**Authentication**: JWT Required (via API Gateway)

**Rate Limit**: 10 requests/minute per user

**Request Schema**:
```json
{
  "recipient_address": "TYour33CharacterTRONAddressHere1234",
  "amount_usdt": 5.50,
  "reason": "Session completion reward",
  "router_type": "PayoutRouterV0",
  "priority": "NORMAL",
  "batch_type": "IMMEDIATE",
  "session_id": "session_abc123",
  "node_id": "node_xyz789",
  "custom_data": {
    "work_credits": 150,
    "session_duration": 3600
  }
}
```

**Response Schema**:
```json
{
  "payout_id": "payout_12345",
  "status": "pending",
  "recipient_address": "TYour33CharacterTRONAddressHere1234",
  "amount_usdt": 5.50,
  "router_type": "PayoutRouterV0",
  "priority": "NORMAL",
  "batch_type": "IMMEDIATE",
  "estimated_completion": "2025-10-12T15:30:00Z",
  "created_at": "2025-10-12T15:25:00Z",
  "request_id": "req_uuid_here"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid recipient address or amount
- `401 Unauthorized`: Missing or invalid JWT token
- `403 Forbidden`: Insufficient permissions
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Service unavailable

#### Get Payout Status
```http
GET /api/payment/payouts/{payout_id}
```

**Purpose**: Retrieve status of a specific payout

**Authentication**: JWT Required (via API Gateway)

**Rate Limit**: 60 requests/minute per user

**Path Parameters**:
- `payout_id` (string): Unique payout identifier

**Response Schema**:
```json
{
  "payout_id": "payout_12345",
  "status": "confirmed",
  "recipient_address": "TYour33CharacterTRONAddressHere1234",
  "amount_usdt": 5.50,
  "router_type": "PayoutRouterV0",
  "txid": "0x1234567890abcdef...",
  "confirmations": 19,
  "block_number": 12345678,
  "block_timestamp": "2025-10-12T15:32:00Z",
  "fee_trx": 0.001,
  "created_at": "2025-10-12T15:25:00Z",
  "confirmed_at": "2025-10-12T15:32:00Z"
}
```

#### List Payouts
```http
GET /api/payment/payouts
```

**Purpose**: List payouts with filtering and pagination

**Authentication**: JWT Required (via API Gateway)

**Rate Limit**: 30 requests/minute per user

**Query Parameters**:
- `status` (string, optional): Filter by status (pending, confirmed, failed)
- `router_type` (string, optional): Filter by router (PayoutRouterV0, PayoutRouterKYC)
- `limit` (integer, optional): Number of results (default: 20, max: 100)
- `offset` (integer, optional): Pagination offset (default: 0)
- `start_date` (string, optional): ISO 8601 date filter
- `end_date` (string, optional): ISO 8601 date filter

**Response Schema**:
```json
{
  "payouts": [
    {
      "payout_id": "payout_12345",
      "status": "confirmed",
      "recipient_address": "TYour33CharacterTRONAddressHere1234",
      "amount_usdt": 5.50,
      "created_at": "2025-10-12T15:25:00Z"
    }
  ],
  "pagination": {
    "total": 150,
    "limit": 20,
    "offset": 0,
    "has_next": true,
    "has_previous": false
  },
  "filters": {
    "status": "confirmed",
    "router_type": "PayoutRouterV0"
  }
}
```

### 2. Batch Operations

#### Create Batch Payout
```http
POST /api/payment/payouts/batch
```

**Purpose**: Create multiple payouts in a single request

**Authentication**: JWT Required (via API Gateway)

**Rate Limit**: 5 requests/minute per user

**Request Schema**:
```json
{
  "payouts": [
    {
      "recipient_address": "TYour33CharacterTRONAddressHere1234",
      "amount_usdt": 5.50,
      "reason": "Session reward",
      "session_id": "session_abc123"
    },
    {
      "recipient_address": "TAnother33CharacterTRONAddressHere567",
      "amount_usdt": 3.25,
      "reason": "Node worker reward",
      "node_id": "node_xyz789"
    }
  ],
  "router_type": "PayoutRouterV0",
  "priority": "NORMAL",
  "batch_type": "HOURLY"
}
```

**Response Schema**:
```json
{
  "batch_id": "batch_67890",
  "total_payouts": 2,
  "total_amount_usdt": 8.75,
  "status": "processing",
  "payout_ids": ["payout_12345", "payout_12346"],
  "estimated_completion": "2025-10-12T16:00:00Z",
  "created_at": "2025-10-12T15:45:00Z"
}
```

#### Get Batch Status
```http
GET /api/payment/payouts/batch/{batch_id}
```

**Purpose**: Get status of a batch payout operation

**Authentication**: JWT Required (via API Gateway)

**Rate Limit**: 30 requests/minute per user

**Path Parameters**:
- `batch_id` (string): Unique batch identifier

**Response Schema**:
```json
{
  "batch_id": "batch_67890",
  "total_payouts": 2,
  "completed_payouts": 1,
  "failed_payouts": 0,
  "pending_payouts": 1,
  "status": "processing",
  "total_amount_usdt": 8.75,
  "completed_amount_usdt": 5.50,
  "created_at": "2025-10-12T15:45:00Z",
  "estimated_completion": "2025-10-12T16:00:00Z"
}
```

### 3. Statistics and Monitoring

#### Get Payment Statistics
```http
GET /api/payment/stats
```

**Purpose**: Retrieve payment system statistics

**Authentication**: JWT Required (via API Gateway)

**Rate Limit**: 20 requests/minute per user

**Query Parameters**:
- `period` (string, optional): Time period (hour, day, week, month)
- `router_type` (string, optional): Filter by router type

**Response Schema**:
```json
{
  "period": "day",
  "router_type": "all",
  "total_payouts": 150,
  "total_amount_usdt": 1250.75,
  "success_rate": 98.5,
  "average_amount_usdt": 8.34,
  "payouts_by_router": {
    "PayoutRouterV0": {
      "count": 120,
      "amount_usdt": 950.50
    },
    "PayoutRouterKYC": {
      "count": 30,
      "amount_usdt": 300.25
    }
  },
  "circuit_breaker_status": "closed",
  "daily_limit_usage": 1250.75,
  "hourly_limit_usage": 125.50,
  "generated_at": "2025-10-12T16:00:00Z"
}
```

#### Health Check
```http
GET /api/payment/health
```

**Purpose**: Check service health status

**Authentication**: None (public endpoint)

**Rate Limit**: 120 requests/minute per IP

**Response Schema**:
```json
{
  "status": "healthy",
  "service": "tron-payment-service",
  "version": "1.0.0",
  "timestamp": "2025-10-12T16:00:00Z",
  "checks": {
    "tron": {
      "status": "healthy",
      "network": "mainnet",
      "latest_block": 12345678
    },
    "mongo": {
      "status": "healthy",
      "connection": "active"
    },
    "circuit_breaker": {
      "status": "closed",
      "daily_limit_remaining": 8749.25
    }
  }
}
```

#### Prometheus Metrics
```http
GET /api/payment/metrics
```

**Purpose**: Expose Prometheus metrics for monitoring

**Authentication**: Internal only (service-to-service)

**Rate Limit**: None

**Response Format**: Prometheus exposition format

**Key Metrics**:
```
# HELP tron_payment_requests_total Total payout requests
# TYPE tron_payment_requests_total counter
tron_payment_requests_total{router_type="PayoutRouterV0",status="success"} 150

# HELP tron_payout_amount_usdt_total Total payout amount in USDT
# TYPE tron_payout_amount_usdt_total counter
tron_payout_amount_usdt_total{router_type="PayoutRouterV0"} 1250.75

# HELP tron_circuit_breaker_open Circuit breaker status
# TYPE tron_circuit_breaker_open gauge
tron_circuit_breaker_open 0

# HELP tron_daily_limit_usage_usdt Current daily limit usage
# TYPE tron_daily_limit_usage_usdt gauge
tron_daily_limit_usage_usdt 1250.75
```

---

## Request/Response Schemas

### Pydantic Models

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

class PayoutRouterType(str, Enum):
    PAYOUT_ROUTER_V0 = "PayoutRouterV0"
    PAYOUT_ROUTER_KYC = "PayoutRouterKYC"

class PayoutPriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"

class PayoutBatchType(str, Enum):
    IMMEDIATE = "IMMEDIATE"
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"

class PayoutStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PayoutRequestModel(BaseModel):
    recipient_address: str = Field(
        ..., 
        pattern=r'^T[1-9A-HJ-NP-Za-km-z]{33}$',
        description="TRON address (33 characters starting with T)"
    )
    amount_usdt: float = Field(
        ..., 
        gt=0.01, 
        le=10000,
        description="Amount in USDT (0.01 to 10,000)"
    )
    reason: str = Field(..., min_length=1, max_length=200)
    router_type: PayoutRouterType
    priority: PayoutPriority = PayoutPriority.NORMAL
    batch_type: PayoutBatchType = PayoutBatchType.IMMEDIATE
    session_id: Optional[str] = Field(None, max_length=50)
    node_id: Optional[str] = Field(None, max_length=50)
    custom_data: Optional[Dict[str, Any]] = Field(None, max_length=1000)

    @validator('amount_usdt')
    def validate_amount_precision(cls, v):
        if round(v, 2) != v:
            raise ValueError('Amount must have at most 2 decimal places')
        return v

class PayoutResponseModel(BaseModel):
    payout_id: str
    status: PayoutStatus
    recipient_address: str
    amount_usdt: float
    router_type: PayoutRouterType
    priority: PayoutPriority
    batch_type: PayoutBatchType
    txid: Optional[str] = None
    confirmations: Optional[int] = None
    block_number: Optional[int] = None
    block_timestamp: Optional[datetime] = None
    fee_trx: Optional[float] = None
    estimated_completion: Optional[datetime] = None
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    request_id: str

class BatchPayoutItem(BaseModel):
    recipient_address: str = Field(..., pattern=r'^T[1-9A-HJ-NP-Za-km-z]{33}$')
    amount_usdt: float = Field(..., gt=0.01, le=10000)
    reason: str = Field(..., min_length=1, max_length=200)
    session_id: Optional[str] = None
    node_id: Optional[str] = None

class BatchPayoutRequestModel(BaseModel):
    payouts: List[BatchPayoutItem] = Field(..., min_items=1, max_items=100)
    router_type: PayoutRouterType
    priority: PayoutPriority = PayoutPriority.NORMAL
    batch_type: PayoutBatchType = PayoutBatchType.HOURLY

class BatchPayoutResponseModel(BaseModel):
    batch_id: str
    total_payouts: int
    total_amount_usdt: float
    status: str
    payout_ids: List[str]
    estimated_completion: datetime
    created_at: datetime

class PaginationModel(BaseModel):
    total: int
    limit: int
    offset: int
    has_next: bool
    has_previous: bool

class PayoutListResponseModel(BaseModel):
    payouts: List[PayoutResponseModel]
    pagination: PaginationModel
    filters: Optional[Dict[str, Any]] = None
```

---

## Error Code Specifications

### Standard Error Response Format

```json
{
  "error": {
    "code": "LUCID_ERR_1001",
    "message": "Session size limit exceeded",
    "details": {
      "current": "105GB",
      "max": "100GB"
    },
    "request_id": "req-uuid-here",
    "timestamp": "2025-10-12T16:00:00Z"
  }
}
```

### Payment-Specific Error Codes

| Code | HTTP Status | Message | Description |
|------|-------------|---------|-------------|
| `LUCID_ERR_2001` | 400 | Invalid TRON address format | Recipient address validation failed |
| `LUCID_ERR_2002` | 400 | Amount exceeds daily limit | Payout amount exceeds circuit breaker limit |
| `LUCID_ERR_2003` | 400 | Circuit breaker open | Service temporarily unavailable |
| `LUCID_ERR_2004` | 400 | Invalid router type | Router selection failed |
| `LUCID_ERR_2005` | 404 | Payout not found | Payout ID does not exist |
| `LUCID_ERR_2006` | 500 | TRON network error | Failed to connect to TRON network |
| `LUCID_ERR_2007` | 500 | Insufficient balance | Not enough USDT for payout |
| `LUCID_ERR_2008` | 500 | Transaction failed | TRON transaction rejected |
| `LUCID_ERR_2009` | 429 | Rate limit exceeded | Too many requests |
| `LUCID_ERR_2010` | 403 | Insufficient permissions | User lacks payment permissions |

---

## Rate Limiting Policies

### Per-Endpoint Limits

| Endpoint | Limit | Window | Scope |
|----------|-------|--------|-------|
| `POST /payouts` | 10/min | 1 minute | Per user |
| `GET /payouts/{id}` | 60/min | 1 minute | Per user |
| `GET /payouts` | 30/min | 1 minute | Per user |
| `POST /payouts/batch` | 5/min | 1 minute | Per user |
| `GET /payouts/batch/{id}` | 30/min | 1 minute | Per user |
| `GET /stats` | 20/min | 1 minute | Per user |
| `GET /health` | 120/min | 1 minute | Per IP |
| `GET /metrics` | No limit | N/A | Internal only |

### Rate Limit Headers

```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1640995200
X-RateLimit-Retry-After: 30
```

---

## Pagination Standards

### Query Parameters

- `limit`: Number of results (default: 20, max: 100)
- `offset`: Starting position (default: 0)

### Response Format

```json
{
  "pagination": {
    "total": 150,
    "limit": 20,
    "offset": 0,
    "has_next": true,
    "has_previous": false
  }
}
```

### Cursor-Based Pagination (Future)

For large datasets, cursor-based pagination will be implemented:

```json
{
  "pagination": {
    "next_cursor": "eyJjcmVhdGVkX2F0IjoiMjAyNS0xMC0xMlQxNjowMDowMFoifQ==",
    "has_next": true
  }
}
```

---

## References

- [03_SOLUTION_ARCHITECTURE.md](03_SOLUTION_ARCHITECTURE.md) - Architecture overview
- [05_OPENAPI_SPEC.yaml](05_OPENAPI_SPEC.yaml) - Complete OpenAPI specification
- [07_SECURITY_COMPLIANCE.md](07_SECURITY_COMPLIANCE.md) - Authentication and authorization
- [TRON Address Format](https://developers.tron.network/docs/account) - TRON address validation
- [USDT-TRC20 Contract](https://tronscan.org/#/token20/TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t) - Contract details

---

**Document Status**: [IN PROGRESS]  
**Last Review**: 2025-10-12  
**Next Review**: 2025-11-12
