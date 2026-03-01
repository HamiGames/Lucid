# TRON USDT Manager - Extended API Reference

**Service:** `tron-usdt-manager`  
**Port:** `8094`  
**Base URL:** `/api/v1/usdt`  

---

## 📌 Quick Reference

| Endpoint | Method | Purpose | Status Code |
|----------|--------|---------|-------------|
| `/transfer` | POST | Transfer USDT | 201 |
| `/balance` | POST | Check balance | 200 |
| `/stake` | POST | Stake USDT | 201 |
| `/swap` | POST | Swap tokens | 201 |
| `/history` | GET | Transaction history | 200 |
| `/holdings` | GET | Holdings summary | 200 |
| `/bridge` | POST | Bridge USDT | 201 |
| `/contract-info` | GET | Contract details | 200 |
| `/health` | GET | Health check | 200 |

---

## 🔄 Transfer Operations

### POST /transfer

Transfer USDT tokens between addresses.

**Request Body:**
```json
{
  "from_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
  "to_address": "TRPdriAmjHSeH4tSQrSqVnqGY7pXW7wQMx",
  "amount": 1000.0,
  "memo": "Payment for services"
}
```

**Parameters:**
- `from_address` (string, required) - Sender TRON address (starts with 'T')
- `to_address` (string, required) - Recipient TRON address
- `amount` (float, required) - Amount of USDT to transfer (>0, ≤1B)
- `memo` (string, optional) - Transaction memo (max 200 chars)

**Response (201 Created):**
```json
{
  "transaction_id": "tx_1234567890abcdef",
  "from_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
  "to_address": "TRPdriAmjHSeH4tSQrSqVnqGY7pXW7wQMx",
  "amount": 1000.0,
  "status": "pending",
  "fee": 1.0,
  "created_at": "2026-01-25T10:30:00Z",
  "estimated_confirmation_time": 5
}
```

**Error Responses:**

400 Bad Request:
```json
{
  "detail": "Amount must be greater than 0"
}
```

500 Internal Server Error:
```json
{
  "detail": "Error transferring USDT"
}
```

**Fee Structure:** 0.1% of transfer amount

**Validation Rules:**
- From address must be valid TRON format
- To address must be valid TRON format
- Amount must be > 0 and ≤ 1,000,000,000
- Cannot transfer to same address

---

## 💰 Balance Operations

### POST /balance

Query USDT balance and holdings for an address.

**Request Body:**
```json
{
  "address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
}
```

**Parameters:**
- `address` (string, required) - TRON address to check

**Response (200 OK):**
```json
{
  "address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
  "balance": 50000.0,
  "locked_balance": 10000.0,
  "available_balance": 40000.0,
  "decimals": 6,
  "last_updated": "2026-01-25T10:30:00Z"
}
```

**Response Fields:**
- `address` - The queried address
- `balance` - Total USDT balance
- `locked_balance` - USDT locked in staking
- `available_balance` - Available for transfer
- `decimals` - Token decimals (always 6)
- `last_updated` - Query timestamp

---

## 🏦 Staking Operations

### POST /stake

Stake USDT tokens to earn rewards.

**Request Body:**
```json
{
  "address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
  "amount": 10000.0,
  "duration_days": 90,
  "auto_renew": true
}
```

**Parameters:**
- `address` (string, required) - Staker TRON address
- `amount` (float, required) - Amount to stake (≥100)
- `duration_days` (integer, required) - Staking duration (1-365 days)
- `auto_renew` (boolean, optional) - Auto-renew after expiration (default: false)

**Response (201 Created):**
```json
{
  "stake_id": "stake_1234567890abcdef",
  "address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
  "amount": 10000.0,
  "duration_days": 90,
  "annual_yield_percent": 9.5,
  "expected_reward": 232.88,
  "staking_start": "2026-01-25T10:30:00Z",
  "staking_end": "2026-04-25T10:30:00Z",
  "auto_renew": true
}
```

**Response Fields:**
- `stake_id` - Unique stake identifier
- `address` - Staker address
- `amount` - Staked amount
- `duration_days` - Staking period
- `annual_yield_percent` - APY (based on tier)
- `expected_reward` - Expected USDT reward
- `staking_start` - Stake creation timestamp
- `staking_end` - Reward maturation date
- `auto_renew` - Auto-renewal setting

**APY Calculation:**
```
Base APY: 8.5%
Tier Bonus: 0% - 1.5% (based on amount)

Tier 1: 100-999 USDT       → 8.5% APY
Tier 2: 1,000-9,999 USDT   → 9.0% APY
Tier 3: 10,000-99,999 USDT → 9.5% APY
Tier 4: 100,000+ USDT      → 10.0% APY
```

---

## 🔀 Token Swaps

### POST /swap

Swap USDT for other supported tokens.

**Request Body:**
```json
{
  "from_token": "USDT",
  "to_token": "TRX",
  "amount": 1000.0,
  "min_output": 10000.0,
  "slippage_percent": 0.5
}
```

**Parameters:**
- `from_token` (string, required) - Source token (USDT, TRX, USDC)
- `to_token` (string, required) - Target token
- `amount` (float, required) - Amount to swap (>0, ≤1B)
- `min_output` (float, required) - Minimum acceptable output
- `slippage_percent` (float, optional) - Max slippage (0.1-5.0%, default: 0.5%)

**Response (201 Created):**
```json
{
  "swap_id": "swap_1234567890abcdef",
  "from_token": "USDT",
  "to_token": "TRX",
  "input_amount": 1000.0,
  "output_amount": 9700.0,
  "exchange_rate": 9.7,
  "price_impact_percent": 0.1,
  "fee": 30.0,
  "status": "completed",
  "created_at": "2026-01-25T10:30:00Z"
}
```

**Response Fields:**
- `swap_id` - Unique swap identifier
- `from_token` - Source token
- `to_token` - Target token
- `input_amount` - Amount swapped
- `output_amount` - Amount received (after fees)
- `exchange_rate` - Conversion rate used
- `price_impact_percent` - Market impact
- `fee` - Fee charged (0.3%)
- `status` - Swap status
- `created_at` - Swap timestamp

**Supported Pairs:**
- USDT ↔ TRX
- USDT ↔ USDC
- USDC ↔ USDT

**Fee Structure:** 0.3% of output amount

---

## 📜 Transaction History

### GET /history?address={address}&days={days}

Retrieve transaction history for an address.

**Query Parameters:**
- `address` (string, required) - TRON address
- `days` (integer, optional) - Number of days to query (1-365, default: 30)

**Response (200 OK):**
```json
{
  "address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
  "transactions": [
    {
      "tx_id": "tx_0",
      "type": "transfer",
      "amount": 100.0,
      "timestamp": "2026-01-20T10:30:00Z",
      "status": "confirmed"
    },
    {
      "tx_id": "tx_1",
      "type": "transfer",
      "amount": 110.0,
      "timestamp": "2026-01-19T10:30:00Z",
      "status": "confirmed"
    }
  ],
  "total_transactions": 2,
  "period_days": 30
}
```

**Response Fields:**
- `address` - Queried address
- `transactions` - List of transaction records
- `total_transactions` - Number of transactions
- `period_days` - Period queried

---

## 🎯 Holdings Summary

### GET /holdings?address={address}

Get comprehensive holdings and staking information.

**Query Parameters:**
- `address` (string, required) - TRON address

**Response (200 OK):**
```json
{
  "address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
  "total_balance": 50000.0,
  "locked_in_staking": 25000.0,
  "available_balance": 25000.0,
  "staking_rewards_earned": 1234.56,
  "staking_positions": [
    {
      "stake_id": "stake_1",
      "amount": 10000.0,
      "duration_days": 90,
      "start_date": "2025-12-26T10:30:00Z",
      "end_date": "2026-03-26T10:30:00Z",
      "expected_reward": 206.58
    },
    {
      "stake_id": "stake_2",
      "amount": 15000.0,
      "duration_days": 180,
      "start_date": "2025-12-11T10:30:00Z",
      "end_date": "2026-06-09T10:30:00Z",
      "expected_reward": 620.75
    }
  ]
}
```

**Response Fields:**
- `address` - Address queried
- `total_balance` - Total USDT balance
- `locked_in_staking` - Amount in active stakes
- `available_balance` - Available for withdrawal/transfer
- `staking_rewards_earned` - Total claimed rewards
- `staking_positions` - Array of active stakes

---

## 🌉 Bridge Operations

### POST /bridge

Bridge USDT across blockchains.

**Request Body:**
```json
{
  "from_chain": "tron",
  "to_chain": "ethereum",
  "amount": 10000.0,
  "recipient_address": "0x1234567890123456789012345678901234567890"
}
```

**Parameters:**
- `from_chain` (string, required) - Source chain (tron, ethereum, polygon, binance, solana)
- `to_chain` (string, required) - Destination chain
- `amount` (float, required) - Amount to bridge (>0, ≤1B)
- `recipient_address` (string, required) - Recipient address on destination chain

**Response (201 Created):**
```json
{
  "bridge_tx_id": "bridge_1234567890abcdef",
  "from_chain": "tron",
  "to_chain": "ethereum",
  "amount": 10000.0,
  "bridge_fee": 50.0,
  "estimated_time_minutes": 15,
  "status": "initiated"
}
```

**Response Fields:**
- `bridge_tx_id` - Unique bridge transaction ID
- `from_chain` - Source blockchain
- `to_chain` - Destination blockchain
- `amount` - Amount bridged
- `bridge_fee` - Fee charged (0.5%)
- `estimated_time_minutes` - Completion time estimate
- `status` - Bridge status

**Supported Chains & Times:**
- Ethereum: 15 minutes
- Polygon: 10 minutes
- Binance: 5 minutes
- Solana: 5 minutes

---

## ℹ️ Contract Information

### GET /contract-info

Get USDT contract details.

**Response (200 OK):**
```json
{
  "contract_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
  "token_name": "Tether USD",
  "token_symbol": "USDT",
  "decimals": 6,
  "total_supply": 40000000000.0,
  "current_circulating_supply": 39500000000.0,
  "contract_verification": "verified",
  "last_updated": "2026-01-25T10:30:00Z"
}
```

---

## ❤️ Health Check

### GET /health

Check USDT manager service health.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "usdt-manager",
  "timestamp": "2026-01-25T10:30:00Z",
  "contract_status": "operational"
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

### Common Error Scenarios

**Invalid Address:**
```json
{
  "detail": "Invalid from address: INVALID"
}
```

**Insufficient Balance:**
```json
{
  "detail": "Insufficient balance for transfer"
}
```

**Minimum Output Not Met:**
```json
{
  "detail": "Output 9500.0 below minimum 10000.0"
}
```

**Staking Period Invalid:**
```json
{
  "detail": "Duration must be between 1 and 365 days"
}
```

---

## 📊 Request/Response Examples

### Complete Transfer Flow

1. **Check Balance**
```bash
curl -X POST http://localhost:8094/api/v1/usdt/balance \
  -H "Content-Type: application/json" \
  -d '{"address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"}'
```

2. **Transfer USDT**
```bash
curl -X POST http://localhost:8094/api/v1/usdt/transfer \
  -H "Content-Type: application/json" \
  -d '{
    "from_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
    "to_address": "TRPdriAmjHSeH4tSQrSqVnqGY7pXW7wQMx",
    "amount": 1000.0
  }'
```

3. **Verify Transaction**
```bash
curl -X GET "http://localhost:8094/api/v1/usdt/history?address=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t&days=1"
```

### Complete Staking Flow

1. **Stake USDT**
```bash
curl -X POST http://localhost:8094/api/v1/usdt/stake \
  -H "Content-Type: application/json" \
  -d '{
    "address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
    "amount": 10000.0,
    "duration_days": 90,
    "auto_renew": true
  }'
```

2. **Check Holdings**
```bash
curl -X GET "http://localhost:8094/api/v1/usdt/holdings?address=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
```

---

## 🧪 Integration Testing

### Validate Integration
```bash
# Health check
curl http://localhost:8094/api/v1/usdt/health

# Check contract
curl http://localhost:8094/api/v1/usdt/contract-info

# Test balance query
curl -X POST http://localhost:8094/api/v1/usdt/balance \
  -H "Content-Type: application/json" \
  -d '{"address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"}'
```

---

**API Version:** 1.0.0  
**Last Updated:** January 2026  
**Status:** Production Ready
