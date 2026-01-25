# TRON Payment Gateway - Operational Files Guide

**Container Name:** `tron-payment-gateway`  
**Port:** `8097`  
**Image:** `arm64/lucid-payment-gateway:latest`

---

## 📋 Overview

The TRON Payment Gateway service provides comprehensive payment processing capabilities, including:

- **Payment Processing** - Create, process, and track payments
- **Batch Processing** - Process multiple payments efficiently
- **Payment Reconciliation** - Verify payments against blockchain
- **Refund Management** - Issue and track refunds
- **Webhook Management** - Real-time payment notifications
- **Settlement Operations** - Automated payment settlement
- **Analytics & Reporting** - Payment metrics and reports
- **Fee Management** - Dynamic fee calculation

---

## 📁 Operational Files

### 1. **Entrypoint: `payment_gateway_entrypoint.py`**

**Purpose:** Python script that bootstraps the Payment Gateway FastAPI service

**Location:** `/app/payment_gateway_entrypoint.py` (in container)

**Key Functions:**
- Validates environment variables (`SERVICE_PORT`, `SERVICE_HOST`, `WORKERS`)
- Sets up Python path for service-packages and app directory
- Initializes uvicorn server with FastAPI application
- Handles graceful startup/shutdown

**Environment Variables:**
- `SERVICE_PORT` (default: 8097) - Service port
- `SERVICE_HOST` (default: 0.0.0.0) - Service host
- `WORKERS` (default: 1) - Number of uvicorn workers
- `PAYMENT_GATEWAY_PORT` - Alternative port variable
- `SERVICE_NAME` - Service identifier (auto-set: `payment_gateway`)

---

### 2. **Main Application: `payment_gateway_main.py`**

**Purpose:** FastAPI application entry point with lifecycle management

**Location:** `/app/payment_gateway_main.py` (in container)

**Key Components:**

#### Initialization
- Configures structured logging (JSON format)
- Creates FastAPI application with lifespan context manager
- Initializes CORS middleware
- Includes all API routers

#### Lifecycle Management
- **Startup:** Initializes `PaymentGatewayService` instance
- **Shutdown:** Gracefully closes service connections and cleanup

#### API Endpoints
- **Root:** `GET /`
- **Health:** `GET /health`, `GET /health/live`, `GET /health/ready`
- **Status:** `GET /status`
- **Metrics:** `GET /metrics`
- **Payment Operations:** `GET/POST /api/v1/payments/*`

#### Global Service Instance
- `payment_service: Optional[PaymentGatewayService]` - Shared service for all requests

---

### 3. **Service Module: `services/payment_gateway_extended.py`**

**Purpose:** Core business logic for payment gateway operations

**Location:** `/app/services/payment_gateway_extended.py`

**Class:** `PaymentGatewayService`

#### Key Methods

##### Payment Creation
```python
async def create_payment(
    payer_address: str,
    payee_address: str,
    amount: float,
    payment_method: str = "payment_gateway",
    priority: str = "normal",
    reference_id: Optional[str] = None,
    description: Optional[str] = None
) -> Dict[str, Any]
```
- Validates TRON addresses (34 chars, starts with 'T')
- Calculates fees based on priority level
- Creates payment record with status tracking
- Updates operation metrics

##### Batch Payment Processing
```python
async def process_batch_payments(
    payments: List[Dict[str, Any]],
    batch_reference: Optional[str] = None
) -> Dict[str, Any]
```
- Processes multiple payments concurrently
- Tracks success/failure per payment
- Creates batch record with results
- Handles partial failures gracefully

##### Payment Reconciliation
```python
async def reconcile_payment(
    payment_id: str,
    external_transaction_id: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]
```
- Verifies payment against blockchain
- Updates payment status to confirmed
- Tracks confirmations (requires 5)
- Queues webhook events

##### Refund Processing
```python
async def refund_payment(
    payment_id: str,
    reason: Optional[str] = None
) -> Dict[str, Any]
```
- Creates refund record
- Updates payment status to refunded
- Tracks refunded volume
- Notifies via webhook

##### Webhook Management
```python
async def register_webhook(
    url: str,
    events: List[str],
    headers: Optional[Dict[str, str]] = None,
    active: bool = True
) -> Dict[str, Any]
```
- Registers webhook with secret
- Configures event subscriptions
- Tracks webhook usage

#### Data Structures
- `payments: Dict[str, Dict]` - Payment records
- `batches: Dict[str, Dict]` - Batch records
- `refunds: Dict[str, Dict]` - Refund records
- `webhooks: Dict[str, Dict]` - Webhook subscriptions
- `webhook_queue: List` - Pending webhook events
- `settlements: Dict[str, Dict]` - Settlement records
- `metrics: Dict` - Operation metrics

#### Metrics Tracked
- `total_payments` - Total payment operations
- `successful_payments` - Successful transactions
- `failed_payments` - Failed transactions
- `total_volume` - Total payment volume
- `total_fees` - Total fees collected
- `refunded_volume` - Total refunded amount
- `batches_processed` - Batches processed
- `avg_processing_time` - Average processing time

---

### 4. **API Module: `api/payment_gateway.py`**

**Purpose:** FastAPI router with payment gateway operation endpoints

**Location:** `/app/api/payment_gateway.py`

**Router Prefix:** `/api/v1/payments`

#### Endpoints

##### Payment Creation
```
POST /create
- Create new payment transaction
- Request: PaymentCreateRequest (payer, payee, amount, priority, method)
- Response: PaymentResponse
- Status Code: 201 Created
```

##### Batch Processing
```
POST /batch
- Process multiple payments in batch
- Request: PaymentBatchRequest (payments list)
- Response: PaymentBatchResponse
- Status Code: 201 Created
```

##### Payment Status
```
GET /status/{payment_id}
- Query payment status and details
- Path Params: payment_id (required)
- Response: PaymentStatusResponse
- Status Code: 200 OK
```

##### Reconciliation
```
POST /reconcile
- Reconcile payment with blockchain
- Request: PaymentReconciliationRequest (payment_id, tx_id, notes)
- Response: PaymentReconciliationResponse
- Status Code: 201 Created
```

##### Refund
```
POST /refund?payment_id=<id>&reason=<reason>
- Issue refund for payment
- Query Params: payment_id (required), reason (optional)
- Response: Refund details
- Status Code: 201 Created
```

##### Webhook Registration
```
POST /webhooks/register
- Register payment webhook
- Request: PaymentWebhookRequest (url, events, headers, active)
- Response: PaymentWebhookResponse
- Status Code: 201 Created
```

##### Webhook List
```
GET /webhooks
- List all registered webhooks
- Response: Webhook list
- Status Code: 200 OK
```

##### Report Generation
```
POST /reports/generate
- Generate payment report
- Request: PaymentReportRequest (start_date, end_date, filters)
- Response: PaymentReportResponse
- Status Code: 201 Created
```

##### Analytics
```
GET /analytics?period_days=<30>
- Get payment analytics
- Query Params: period_days (default: 30)
- Response: Analytics data
- Status Code: 200 OK
```

##### Fee Calculation
```
GET /fees/calculate?amount=<amt>&priority=<pri>
- Calculate payment fees
- Query Params: amount, priority, payment_method
- Response: Fee calculation
- Status Code: 200 OK
```

##### Settlement Info
```
GET /settlement/info
- Get settlement information
- Response: Settlement details
- Status Code: 200 OK
```

##### Health Check
```
GET /health
- Health check for payment gateway
- Response: Health status
- Status Code: 200 OK
```

#### Pydantic Models

**Request Models:**
- `PaymentCreateRequest` - Single payment parameters
- `PaymentBatchRequest` - Batch payment parameters
- `PaymentReconciliationRequest` - Reconciliation parameters
- `PaymentWebhookRequest` - Webhook registration
- `PaymentReportRequest` - Report generation
- `PaymentRefundRequest` - Refund parameters

**Response Models:**
- `PaymentResponse` - Payment result
- `PaymentStatusResponse` - Payment status
- `PaymentBatchResponse` - Batch result
- `PaymentReconciliationResponse` - Reconciliation result
- `PaymentWebhookResponse` - Webhook registration result
- `PaymentReportResponse` - Report data
- `PaymentRefundResponse` - Refund result

**Enums:**
- `PaymentMethodType` - direct_transfer, payment_gateway, swap, route
- `PaymentPriority` - low, normal, high, urgent
- `ReconciliationStatus` - pending, processing, completed, failed, disputed

---

### 5. **Configuration: `config/payment-gateway-config.yaml`**

**Purpose:** Centralized YAML configuration for Payment Gateway

**Location:** `/app/config/payment-gateway-config.yaml`

**Key Sections:**

#### Payment Processing
- Payment methods (direct, gateway, swap, route)
- Priority levels with fee rates (0.1% - 0.3%)
- Processing times (10s - 120s)
- Status tracking

#### Batch Processing
- Max batch size: 1000
- Concurrent batches: 10
- Batch timeout: 300 seconds

#### Fee Management
- Base fees: 0.1% - 0.3% by priority
- Volume discounts: 5% - 15%
- Dynamic fees enabled

#### Payment Reconciliation
- Auto-reconciliation enabled
- Confirmation threshold: 5 blocks
- Reconciliation interval: 300 seconds

#### Settlement
- Daily settlement at 23:00 UTC
- Min settlement: 100k USDT
- Retention: 30 days

#### Webhooks
- Webhook events (11 types)
- Max 100 webhooks
- Retry: 5 attempts with exponential backoff

#### Transaction Limits
- Max single payment: 1B USDT
- Daily limit: 100B USDT
- Rate limit: 1000 payments/min
- Concurrent: 100 payments

#### Refunds
- Auto-refund enabled
- Timeout: 72 hours
- Allowed reasons: 5 types

#### Monitoring
- Metrics collection every 60s
- 9 metric types tracked
- 3 alert conditions

---

## 🚀 Usage Examples

### Create Payment
```bash
curl -X POST http://localhost:8097/api/v1/payments/create \
  -H "Content-Type: application/json" \
  -d '{
    "payer_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
    "payee_address": "TRPdriAmjHSeH4tSQrSqVnqGY7pXW7wQMx",
    "amount": 1000.0,
    "priority": "normal",
    "reference_id": "ORDER-12345"
  }'
```

### Process Batch Payments
```bash
curl -X POST http://localhost:8097/api/v1/payments/batch \
  -H "Content-Type: application/json" \
  -d '{
    "payments": [
      {
        "payer_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
        "payee_address": "TRPdriAmjHSeH4tSQrSqVnqGY7pXW7wQMx",
        "amount": 1000.0
      },
      {
        "payer_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
        "payee_address": "TRPdriAmjHSeH4tSQrSqVnqGY7pXW7wQMx",
        "amount": 2000.0
      }
    ]
  }'
```

### Get Payment Status
```bash
curl -X GET "http://localhost:8097/api/v1/payments/status/pay_1234567890abcdef"
```

### Reconcile Payment
```bash
curl -X POST http://localhost:8097/api/v1/payments/reconcile \
  -H "Content-Type: application/json" \
  -d '{
    "payment_id": "pay_1234567890abcdef",
    "external_transaction_id": "txid_abc123"
  }'
```

### Register Webhook
```bash
curl -X POST http://localhost:8097/api/v1/payments/webhooks/register \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/payments/webhook",
    "events": ["payment.completed", "payment.failed"],
    "active": true
  }'
```

---

## 🔍 Health Check Endpoints

### Service Health
```
GET /health
```
Returns: Overall health, service status, metrics

### Liveness Probe
```
GET /health/live
```
Returns: Is service running? (for Kubernetes)

### Readiness Probe
```
GET /health/ready
```
Returns: Is service ready? (for Kubernetes)

---

## 💰 Fee Structure

| Priority | Fee Rate | Processing Time | Retries |
|----------|----------|-----------------|---------|
| Low      | 0.10%    | 120 seconds     | 3       |
| Normal   | 0.15%    | 60 seconds      | 5       |
| High     | 0.20%    | 30 seconds      | 5       |
| Urgent   | 0.30%    | 10 seconds      | 7       |

---

## 📊 Webhook Events

| Event | Trigger |
|-------|---------|
| `payment.created` | Payment created |
| `payment.started` | Payment processing started |
| `payment.confirmed` | Blockchain confirmed |
| `payment.completed` | Payment completed |
| `payment.failed` | Payment failed |
| `payment.refunded` | Payment refunded |
| `payment.disputed` | Payment disputed |
| `batch.created` | Batch created |
| `batch.completed` | Batch processing complete |
| `settlement.initiated` | Settlement started |
| `settlement.completed` | Settlement complete |

---

## 🐳 Docker Integration

### Build Command
```bash
docker buildx build --platform linux/arm64 \
  -t lucid-payment-gateway:latest \
  -f payment-systems/tron/Dockerfile.payment-gateway \
  payment-systems/tron
```

### Run Command
```bash
docker run -d \
  --name tron-payment-gateway \
  -p 8097:8097 \
  -e SERVICE_PORT=8097 \
  -e WORKERS=4 \
  -e LOG_LEVEL=INFO \
  lucid-payment-gateway:latest
```

---

## 🔒 Security Features

- **Input Validation:** Address and amount validation
- **Rate Limiting:** 1000 payments/min per service
- **Fraud Detection:** Suspicious activity monitoring
- **Webhook Security:** HMAC signing with secret
- **Transaction Validation:** All fields verified

---

## 🐛 Troubleshooting

### Payment Not Processing
- Check payment amount (min 1, max 1B)
- Verify address format (TRON = 34 chars, starts with T)
- Review payment status endpoint

### Webhook Not Firing
- Verify webhook is active
- Check webhook URL accessibility
- Review webhook event configuration

### Settlement Issues
- Check settlement threshold (min 100k)
- Verify settlement time (23:00 UTC)
- Review pending settlement amount

---

## ✅ Service Status

The Payment Gateway provides full operational capabilities:

✅ Payment creation and processing  
✅ Batch payment processing  
✅ Payment reconciliation  
✅ Refund management  
✅ Webhook notifications  
✅ Settlement operations  
✅ Payment analytics  
✅ Fee management  
✅ Health checks  
✅ Metrics collection  
✅ Error handling  
✅ Audit logging  

---

**Last Updated:** January 2026  
**Status:** Production Ready  
**Version:** 1.0.0
