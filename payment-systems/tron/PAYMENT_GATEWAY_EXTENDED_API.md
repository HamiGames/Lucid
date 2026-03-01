# TRON Payment Gateway - Extended API Reference

**Service:** `tron-payment-gateway`  
**Port:** `8097`  
**Base URL:** `/api/v1/payments`  

---

## 📌 Quick Reference

| Endpoint | Method | Purpose | Status Code |
|----------|--------|---------|-------------|
| `/create` | POST | Create payment | 201 |
| `/batch` | POST | Process batch | 201 |
| `/status/{id}` | GET | Get status | 200 |
| `/reconcile` | POST | Reconcile | 201 |
| `/refund` | POST | Refund | 201 |
| `/webhooks/register` | POST | Register webhook | 201 |
| `/webhooks` | GET | List webhooks | 200 |
| `/reports/generate` | POST | Generate report | 201 |
| `/analytics` | GET | Analytics | 200 |
| `/fees/calculate` | GET | Calculate fees | 200 |
| `/settlement/info` | GET | Settlement info | 200 |
| `/health` | GET | Health check | 200 |

---

## 💳 Payment Creation

### POST /create

Create a new payment transaction.

**Request Body:**
```json
{
  "payer_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
  "payee_address": "TRPdriAmjHSeH4tSQrSqVnqGY7pXW7wQMx",
  "amount": 1000.0,
  "payment_method": "payment_gateway",
  "priority": "normal",
  "reference_id": "ORDER-12345",
  "description": "Payment for services"
}
```

**Parameters:**
- `payer_address` (string, required) - TRON address of payer (34 chars, starts with T)
- `payee_address` (string, required) - TRON address of payee
- `amount` (float, required) - Payment amount (>0, ≤1B)
- `payment_method` (enum, optional) - direct_transfer, payment_gateway, swap, route
- `priority` (enum, optional) - low, normal, high, urgent (default: normal)
- `reference_id` (string, optional) - External reference ID
- `description` (string, optional) - Payment description (max 500 chars)

**Response (201 Created):**
```json
{
  "payment_id": "pay_1234567890abcdef",
  "payer_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
  "payee_address": "TRPdriAmjHSeH4tSQrSqVnqGY7pXW7wQMx",
  "amount": 1000.0,
  "fee": 1.5,
  "net_amount": 998.5,
  "payment_method": "payment_gateway",
  "priority": "normal",
  "status": "pending",
  "reference_id": "ORDER-12345",
  "created_at": "2026-01-25T10:30:00Z",
  "estimated_completion_time": 60
}
```

**Response Fields:**
- `payment_id` - Unique payment identifier
- `fee` - Transaction fee amount
- `net_amount` - Amount after fee deduction
- `status` - Current payment status
- `estimated_completion_time` - Estimated seconds to complete

**Fee Rates by Priority:**
- Low: 0.1% (120s processing time)
- Normal: 0.15% (60s processing time)
- High: 0.2% (30s processing time)
- Urgent: 0.3% (10s processing time)

---

## 📦 Batch Payment Processing

### POST /batch

Process multiple payments in batch.

**Request Body:**
```json
{
  "payments": [
    {
      "payer_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
      "payee_address": "TRPdriAmjHSeH4tSQrSqVnqGY7pXW7wQMx",
      "amount": 1000.0,
      "priority": "normal"
    },
    {
      "payer_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
      "payee_address": "TRPdriAmjHSeH4tSQrSqVnqGY7pXW7wQMx",
      "amount": 2000.0,
      "priority": "high"
    }
  ],
  "batch_reference": "BATCH-001"
}
```

**Parameters:**
- `payments` (array, required) - List of payment objects (min 1, max 1000)
- `batch_reference` (string, optional) - Batch identifier

**Response (201 Created):**
```json
{
  "batch_id": "batch_1234567890abcdef",
  "total_payments": 2,
  "successful": 2,
  "failed": 0,
  "status": "processing",
  "batch_reference": "BATCH-001",
  "created_at": "2026-01-25T10:30:00Z",
  "estimated_completion_time": 300
}
```

**Response Fields:**
- `batch_id` - Unique batch identifier
- `successful` - Number of successfully created payments
- `failed` - Number of failed payments
- `status` - Batch status (processing, partial_failure, completed)

---

## 🔍 Payment Status

### GET /status/{payment_id}

Get payment status and details.

**Path Parameters:**
- `payment_id` (string, required) - Payment ID

**Response (200 OK):**
```json
{
  "payment_id": "pay_1234567890abcdef",
  "payer_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
  "payee_address": "TRPdriAmjHSeH4tSQrSqVnqGY7pXW7wQMx",
  "amount": 1000.0,
  "fee": 1.5,
  "status": "confirmed",
  "transaction_id": "txid_abc123",
  "confirmations": 5,
  "created_at": "2026-01-25T10:00:00Z",
  "completed_at": "2026-01-25T10:02:00Z"
}
```

**Status Values:**
- `pending` - Payment created, awaiting processing
- `processing` - Payment being processed
- `confirmed` - Blockchain confirmed
- `completed` - Payment complete
- `failed` - Payment failed
- `cancelled` - Payment cancelled
- `refunded` - Payment refunded
- `disputed` - Payment under dispute

---

## ✅ Payment Reconciliation

### POST /reconcile

Reconcile payment with blockchain transaction.

**Request Body:**
```json
{
  "payment_id": "pay_1234567890abcdef",
  "external_transaction_id": "txid_abc123",
  "notes": "Verified on blockchain"
}
```

**Parameters:**
- `payment_id` (string, required) - Payment to reconcile
- `external_transaction_id` (string, optional) - Blockchain transaction ID
- `notes` (string, optional) - Reconciliation notes

**Response (201 Created):**
```json
{
  "reconciliation_id": "recon_1234567890abcdef",
  "payment_id": "pay_1234567890abcdef",
  "status": "completed",
  "verified": true,
  "verified_at": "2026-01-25T10:30:00Z",
  "notes": "Verified on blockchain"
}
```

---

## 💸 Refund Processing

### POST /refund

Issue refund for a payment.

**Query Parameters:**
- `payment_id` (string, required) - Payment ID to refund
- `reason` (string, optional) - Refund reason

**Response (201 Created):**
```json
{
  "refund_id": "refund_1234567890abcdef",
  "payment_id": "pay_1234567890abcdef",
  "status": "initiated",
  "amount": 1000.0,
  "reason": "User request",
  "created_at": "2026-01-25T10:30:00Z",
  "estimated_completion_time": 60
}
```

**Allowed Refund Reasons:**
- user_request
- payment_failure
- duplicate_payment
- merchant_initiated
- system_error

---

## 🔔 Webhook Management

### POST /webhooks/register

Register a payment webhook.

**Request Body:**
```json
{
  "url": "https://example.com/payments/webhook",
  "events": ["payment.completed", "payment.failed"],
  "headers": {
    "X-Custom-Header": "value"
  },
  "active": true
}
```

**Parameters:**
- `url` (string, required) - Webhook URL
- `events` (array, required) - Events to subscribe to
- `headers` (object, optional) - Custom headers
- `active` (boolean, optional) - Webhook active status (default: true)

**Response (201 Created):**
```json
{
  "webhook_id": "webhook_1234567890abcdef",
  "url": "https://example.com/payments/webhook",
  "events": ["payment.completed", "payment.failed"],
  "active": true,
  "secret": "secret_abc123xyz",
  "created_at": "2026-01-25T10:30:00Z"
}
```

**Supported Webhook Events:**
- `payment.created` - Payment created
- `payment.started` - Processing started
- `payment.confirmed` - Blockchain confirmed
- `payment.completed` - Payment completed
- `payment.failed` - Payment failed
- `payment.refunded` - Payment refunded
- `payment.disputed` - Payment disputed
- `batch.created` - Batch created
- `batch.completed` - Batch complete
- `settlement.initiated` - Settlement started
- `settlement.completed` - Settlement complete

### GET /webhooks

List all registered webhooks.

**Response (200 OK):**
```json
{
  "webhooks": [
    {
      "webhook_id": "webhook_abc123",
      "url": "https://example.com/payments",
      "events": ["payment.completed", "payment.failed"],
      "active": true,
      "created_at": "2026-01-25T10:30:00Z"
    }
  ],
  "total": 1
}
```

---

## 📊 Payment Reports

### POST /reports/generate

Generate payment report for date range.

**Request Body:**
```json
{
  "start_date": "2026-01-01T00:00:00Z",
  "end_date": "2026-01-31T23:59:59Z",
  "status_filter": "completed",
  "include_failed": false
}
```

**Parameters:**
- `start_date` (string, required) - Report start date (ISO format)
- `end_date` (string, required) - Report end date (ISO format)
- `status_filter` (string, optional) - Filter by status
- `include_failed` (boolean, optional) - Include failed payments

**Response (201 Created):**
```json
{
  "report_id": "report_1234567890abcdef",
  "period_start": "2026-01-01T00:00:00Z",
  "period_end": "2026-01-31T23:59:59Z",
  "total_payments": 1250,
  "successful_payments": 1187,
  "failed_payments": 63,
  "total_volume": 5000000.0,
  "total_fees": 7500.0,
  "net_volume": 4992500.0,
  "generated_at": "2026-01-25T10:30:00Z"
}
```

---

## 📈 Payment Analytics

### GET /analytics?period_days=30

Get payment analytics and statistics.

**Query Parameters:**
- `period_days` (integer, optional) - Number of days to analyze (default: 30, min: 1, max: 365)

**Response (200 OK):**
```json
{
  "period_days": 30,
  "total_payments": 1250,
  "total_volume": 5000000.0,
  "average_payment_size": 4000.0,
  "success_rate_percent": 94.96,
  "failed_payments": 63,
  "average_processing_time_seconds": 45,
  "peak_hour": "14:00-15:00",
  "most_common_amount": 1000.0,
  "total_fees_collected": 7500.0,
  "timestamp": "2026-01-25T10:30:00Z"
}
```

---

## 💰 Fee Calculation

### GET /fees/calculate?amount=1000&priority=normal

Calculate fees for a payment.

**Query Parameters:**
- `amount` (float, required) - Payment amount
- `priority` (enum, optional) - Payment priority (default: normal)
- `payment_method` (enum, optional) - Payment method

**Response (200 OK):**
```json
{
  "amount": 1000.0,
  "priority": "normal",
  "fee_rate_percent": 0.15,
  "transaction_fee": 1.5,
  "net_amount": 998.5,
  "payment_method": "payment_gateway",
  "timestamp": "2026-01-25T10:30:00Z"
}
```

---

## 🏦 Settlement Information

### GET /settlement/info

Get payment settlement information.

**Response (200 OK):**
```json
{
  "settlement_frequency": "daily",
  "settlement_time_utc": "23:00",
  "next_settlement": "2026-01-26T23:00:00Z",
  "pending_settlement_amount": 145000.0,
  "last_settlement": {
    "amount": 2345000.0,
    "timestamp": "2026-01-24T23:00:00Z",
    "status": "completed"
  },
  "settlement_threshold": 100000.0
}
```

**Response Fields:**
- `settlement_frequency` - Settlement schedule (daily)
- `settlement_time_utc` - Settlement time in UTC
- `next_settlement` - Next scheduled settlement
- `pending_settlement_amount` - Amount awaiting settlement
- `settlement_threshold` - Minimum settlement amount

---

## ❤️ Health Check

### GET /health

Check payment gateway health.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "payment-gateway",
  "timestamp": "2026-01-25T10:30:00Z",
  "gateway_status": "operational"
}
```

---

## 🔒 Error Handling

### Standard Error Response

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created (POST operations) |
| 400 | Bad Request (validation error) |
| 404 | Not Found |
| 500 | Internal Server Error |

---

## 📋 Integration Examples

### Complete Payment Flow

1. **Create Payment**
```bash
curl -X POST http://localhost:8097/api/v1/payments/create \
  -H "Content-Type: application/json" \
  -d '{
    "payer_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
    "payee_address": "TRPdriAmjHSeH4tSQrSqVnqGY7pXW7wQMx",
    "amount": 1000.0,
    "priority": "normal"
  }'
```

2. **Check Status**
```bash
curl -X GET "http://localhost:8097/api/v1/payments/status/pay_1234567890abcdef"
```

3. **Reconcile**
```bash
curl -X POST http://localhost:8097/api/v1/payments/reconcile \
  -H "Content-Type: application/json" \
  -d '{
    "payment_id": "pay_1234567890abcdef",
    "external_transaction_id": "txid_abc123"
  }'
```

---

**API Version:** 1.0.0  
**Last Updated:** January 2026  
**Status:** Production Ready
