# TRON USDT Manager - Operational Files Guide

**Container Name:** `tron-usdt-manager`  
**Port:** `8094`  
**Image:** `arm64/lucid-usdt-manager:latest`

---

## 📋 Overview

The TRON USDT Manager service provides comprehensive token management capabilities for USDT-TRC20, including:

- **Token Transfers** - Fast and secure USDT transactions
- **Staking Operations** - Earn rewards on USDT holdings (8.5% base APY)
- **Token Swaps** - Exchange USDT for other supported tokens
- **Cross-Chain Bridge** - Bridge USDT across multiple blockchains
- **Balance Queries** - Real-time balance and holdings information
- **Reward Management** - Claim and track staking rewards

---

## 📁 Operational Files

### 1. **Entrypoint: `usdt_manager_entrypoint.py`**

**Purpose:** Python script that bootstraps the USDT Manager FastAPI service

**Location:** `/app/usdt_manager_entrypoint.py` (in container)

**Key Functions:**
- Validates environment variables (`SERVICE_PORT`, `SERVICE_HOST`, `WORKERS`)
- Sets up Python path for service-packages and app directory
- Initializes uvicorn server with FastAPI application
- Handles graceful startup/shutdown

**Environment Variables:**
- `SERVICE_PORT` (default: 8094) - Service port
- `SERVICE_HOST` (default: 0.0.0.0) - Service host
- `WORKERS` (default: 1) - Number of uvicorn workers
- `SERVICE_NAME` - Service identifier (auto-set: `tron-usdt-manager`)

---

### 2. **Main Application: `usdt_manager_main.py`**

**Purpose:** FastAPI application entry point with lifecycle management

**Location:** `/app/usdt_manager_main.py` (in container)

**Key Components:**

#### Initialization
- Configures structured logging (JSON format)
- Creates FastAPI application with lifespan context manager
- Initializes CORS middleware
- Includes all API routers

#### Lifecycle Management
- **Startup:** Initializes `USDTManagerService` instance
- **Shutdown:** Gracefully closes service connections and cleanup

#### API Endpoints
- **Root:** `GET /`
- **Health:** `GET /health`, `GET /health/live`, `GET /health/ready`
- **Status:** `GET /status`
- **Metrics:** `GET /metrics`
- **USDT Operations:** `GET/POST /api/v1/usdt/*`

#### Global Service Instance
- `usdt_service: Optional[USDTManagerService]` - Shared service for all requests

**Error Handling:**
- Structured exception catching at all lifecycle stages
- Graceful degradation on service failures
- Detailed error logging with tracebacks

---

### 3. **Service Module: `services/usdt_manager.py`**

**Purpose:** Core business logic for USDT token operations

**Location:** `/app/services/usdt_manager.py`

**Class:** `USDTManagerService`

#### Key Methods

##### Transfers
```python
async def transfer_usdt(
    from_address: str,
    to_address: str,
    amount: float,
    memo: Optional[str] = None
) -> Dict[str, Any]
```
- Validates sender and recipient addresses
- Calculates transaction fee (0.1%)
- Creates pending transaction record
- Updates operation metrics

##### Staking
```python
async def stake_usdt(
    address: str,
    amount: float,
    duration_days: int,
    auto_renew: bool = False
) -> Dict[str, Any]
```
- Calculates APY based on staking tier
- Supports 4 tier levels (100 → 100k+ USDT)
- Bonus APY: 0% → 1.5% depending on tier
- Returns staking position with expected rewards

##### Swaps
```python
async def swap_tokens(
    from_token: str,
    to_token: str,
    input_amount: float,
    min_output: float
) -> Dict[str, Any]
```
- Retrieves exchange rates
- Calculates output amount
- Applies 0.3% swap fee
- Validates minimum output threshold

##### Bridge Operations
```python
async def bridge_usdt(
    from_chain: str,
    to_chain: str,
    amount: float,
    recipient_address: str
) -> Dict[str, Any]
```
- Supports: Ethereum, Polygon, Binance, Solana
- Applies 0.5% bridge fee
- Estimates completion time per chain
- Creates bridge transaction record

##### Balance Queries
```python
async def get_balance(address: str) -> Dict[str, Any]
```
- Returns total, locked, and available balance
- Includes token decimals (6)
- Timestamp of last update

##### Reward Claims
```python
async def claim_staking_rewards(stake_id: str) -> Dict[str, Any]
```
- Validates stake maturation
- Calculates final reward
- Updates stake status to "claimed"
- Updates total rewards distributed metric

#### Internal Methods

- `_validate_address(address: str) -> bool` - Validates TRON address format
- `_calculate_apy(amount: float) -> float` - Calculates APY by tier
- `_get_exchange_rate(from_token, to_token) -> float` - Retrieves swap rate

#### Data Structures
- `transfers: Dict[str, Dict]` - Transfer records
- `stakes: Dict[str, Dict]` - Staking positions
- `swaps: Dict[str, Dict]` - Swap transactions
- `bridges: Dict[str, Dict]` - Bridge transactions
- `metrics: Dict` - Operation metrics

#### Metrics Tracked
- `total_transfers` - Total transfer operations
- `total_transfer_volume` - Total USDT transferred
- `total_stakes` - Total staking operations
- `total_staked_amount` - Total USDT staked
- `total_rewards_distributed` - Total rewards claimed
- `total_swaps` - Total swap operations
- `total_swap_volume` - Total swap volume

---

### 4. **API Module: `api/usdt_manager.py`**

**Purpose:** FastAPI router with USDT token operation endpoints

**Location:** `/app/api/usdt_manager.py`

**Router Prefix:** `/api/v1/usdt`

#### Endpoints

##### Transfer Operations
```
POST /transfer
- Transfer USDT between addresses
- Request: USDTTransferRequest (from, to, amount, memo)
- Response: USDTTransferResponse
- Status Code: 201 Created
```

##### Balance Operations
```
POST /balance
- Query USDT balance for address
- Request: USDTBalanceRequest (address)
- Response: USDTBalanceResponse
- Status Code: 200 OK
```

##### Staking Operations
```
POST /stake
- Stake USDT for rewards
- Request: USDTStakingRequest (address, amount, duration_days, auto_renew)
- Response: USDTStakingResponse
- Status Code: 201 Created
```

##### Token Swaps
```
POST /swap
- Swap tokens using USDT pairs
- Request: USDTSwapRequest (from_token, to_token, amount, min_output, slippage)
- Response: USDTSwapResponse
- Status Code: 201 Created
```

##### Transaction History
```
GET /history?address=<addr>&days=<30>
- Get transaction history
- Query Params: address (required), days (default: 30)
- Response: USDTTransactionHistoryResponse
- Status Code: 200 OK
```

##### Holdings Summary
```
GET /holdings?address=<addr>
- Get comprehensive holdings and staking info
- Query Params: address (required)
- Response: USDTHoldingsResponse
- Status Code: 200 OK
```

##### Bridge Operations
```
POST /bridge
- Bridge USDT across blockchains
- Request: USDTBridgeRequest (from_chain, to_chain, amount, recipient)
- Response: USDTBridgeResponse
- Status Code: 201 Created
```

##### Contract Information
```
GET /contract-info
- Get USDT contract information
- Response: Contract details (address, symbol, decimals, supply)
- Status Code: 200 OK
```

##### Health Check
```
GET /health
- Health check for USDT operations
- Response: Health status and contract status
- Status Code: 200 OK
```

#### Pydantic Models

**Request Models:**
- `USDTTransferRequest` - Transfer parameters
- `USDTBalanceRequest` - Balance query
- `USDTStakingRequest` - Staking parameters
- `USDTSwapRequest` - Swap parameters
- `USDTBridgeRequest` - Bridge parameters

**Response Models:**
- `USDTTransferResponse` - Transfer result
- `USDTBalanceResponse` - Balance information
- `USDTStakingResponse` - Staking position
- `USDTSwapResponse` - Swap result
- `USDTTransactionHistoryResponse` - History
- `USDTHoldingsResponse` - Holdings summary
- `USDTBridgeResponse` - Bridge result

**Enums:**
- `TransactionType` - transfer, mint, burn, swap, stake, unstake
- `TransactionStatus` - pending, confirmed, failed, cancelled

---

### 5. **Configuration: `config/usdt-manager-config.yaml`**

**Purpose:** Centralized YAML configuration for USDT Manager

**Location:** `/app/config/usdt-manager-config.yaml`

**Key Sections:**

#### Token Configuration
- Contract address, symbol, decimals
- Total and circulating supply
- Supported networks (TRON, Ethereum, Polygon, Binance, Solana)

#### Operations Configuration
- **Transfers:** Fee (0.1%), limits, confirmation time
- **Staking:** Min/max amounts, APY tiers (4 levels)
- **Swaps:** Fee (0.3%), slippage configuration
- **Bridge:** Fee (0.5%), per-chain settings

#### Transaction Limits
- Single transaction max: 1B USDT
- Daily limit: 100B USDT
- Monthly limit: 1T USDT
- Rate limiting: 1000 tx/min, 100 concurrent

#### Compliance
- AML checks enabled
- Suspicious activity monitoring (>1M USDT)
- Address validation and blacklist checking

#### Monitoring
- Metrics collection every 60 seconds
- Alerts for high-volume transfers and suspicious activity
- Network status monitoring

#### Health Checks
- Contract availability
- Network connectivity
- Database connectivity
- Cache availability

#### Security
- Rate limiting enabled
- Input validation (amounts, addresses)
- Prevent zero and self-transfers

#### Caching
- Memory backend
- TTL: 300 seconds
- Cached: exchange rates, balances, contract info

---

## 🚀 Usage Examples

### Transfer USDT
```bash
curl -X POST http://localhost:8094/api/v1/usdt/transfer \
  -H "Content-Type: application/json" \
  -d '{
    "from_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
    "to_address": "TRPdriAmjHSeH4tSQrSqVnqGY7pXW7wQMx",
    "amount": 1000.0,
    "memo": "Payment for services"
  }'
```

### Stake USDT
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

### Check Balance
```bash
curl -X POST http://localhost:8094/api/v1/usdt/balance \
  -H "Content-Type: application/json" \
  -d '{
    "address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
  }'
```

### Get Holdings Summary
```bash
curl -X GET "http://localhost:8094/api/v1/usdt/holdings?address=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
```

### Swap Tokens
```bash
curl -X POST http://localhost:8094/api/v1/usdt/swap \
  -H "Content-Type: application/json" \
  -d '{
    "from_token": "USDT",
    "to_token": "TRX",
    "amount": 1000.0,
    "min_output": 10000.0,
    "slippage_percent": 0.5
  }'
```

### Bridge USDT
```bash
curl -X POST http://localhost:8094/api/v1/usdt/bridge \
  -H "Content-Type: application/json" \
  -d '{
    "from_chain": "tron",
    "to_chain": "ethereum",
    "amount": 10000.0,
    "recipient_address": "0x1234567890123456789012345678901234567890"
  }'
```

---

## 📊 Staking Tiers

| Tier | Min Amount | Max Amount | APY Bonus | Total APY |
|------|-----------|-----------|-----------|-----------|
| 1    | 100       | 999       | 0%        | 8.5%      |
| 2    | 1,000     | 9,999     | 0.5%      | 9.0%      |
| 3    | 10,000    | 99,999    | 1.0%      | 9.5%      |
| 4    | 100,000+  | ∞         | 1.5%      | 10.0%     |

---

## 🔍 Health Check Endpoints

### Service Health
```
GET /health
```
Returns: Overall service health, service initialized status, metrics

### Liveness Probe
```
GET /health/live
```
Returns: Is the service running? (Used by Kubernetes)

### Readiness Probe
```
GET /health/ready
```
Returns: Is the service ready to serve requests? (Used by Kubernetes)

---

## 📈 Metrics Endpoint

```
GET /metrics
```

Available metrics:
- `total_transfers` - Total transfer operations
- `total_transfer_volume` - Total volume transferred
- `total_stakes` - Total staking operations
- `total_staked_amount` - Total amount staked
- `total_rewards_distributed` - Total rewards claimed
- `total_swaps` - Total swap operations
- `total_swap_volume` - Total swap volume

---

## 🐳 Docker Integration

### Build Command
```bash
docker buildx build --platform linux/arm64 \
  -t lucid-usdt-manager:latest \
  -f payment-systems/tron/Dockerfile.usdt-manager \
  payment-systems/tron
```

### Run Command
```bash
docker run -d \
  --name tron-usdt-manager \
  -p 8094:8094 \
  -e SERVICE_PORT=8094 \
  -e SERVICE_HOST=0.0.0.0 \
  -e WORKERS=4 \
  -e LOG_LEVEL=INFO \
  lucid-usdt-manager:latest
```

### Docker Compose
```yaml
tron-usdt-manager:
  image: lucid-usdt-manager:latest
  container_name: tron-usdt-manager
  ports:
    - "8094:8094"
  environment:
    SERVICE_PORT: 8094
    SERVICE_HOST: 0.0.0.0
    WORKERS: 4
    LOG_LEVEL: INFO
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8094/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 10s
```

---

## 🔒 Security Features

- **Input Validation:** All addresses and amounts validated
- **Rate Limiting:** 1000 tx/min, 100 concurrent
- **AML Checks:** Suspicious activity monitoring
- **Zero Transfer Prevention:** Prevents invalid transfers
- **Self-Transfer Prevention:** Users cannot transfer to themselves

---

## 🐛 Troubleshooting

### Service Not Starting
- Check logs: `docker logs tron-usdt-manager`
- Verify port 8094 is not in use
- Check environment variables

### Balance Query Fails
- Verify address format (must be TRON address, starts with 'T')
- Check network connectivity
- Review service logs

### Staking Not Working
- Verify minimum amount (100 USDT)
- Check duration (1-365 days)
- Ensure address has sufficient balance

### Swap Failures
- Verify exchange rate availability
- Check slippage tolerance
- Ensure output meets minimum threshold

### Bridge Issues
- Verify destination chain is supported
- Check recipient address format for target chain
- Review bridge fee calculation

---

## 📝 Logging

All logs are structured (JSON format) and include:
- Timestamp
- Service name
- Log level (INFO, ERROR, WARNING, DEBUG)
- Message
- Optional context/stack traces

Default log level: `INFO`

---

## ✅ Service Status

The USDT Manager service provides full operational capabilities with:

✅ Token transfer management  
✅ Staking with tiered APY  
✅ Token swaps with rate calculation  
✅ Cross-chain bridge support  
✅ Real-time balance queries  
✅ Reward management  
✅ Comprehensive metrics  
✅ Health check endpoints  
✅ Error handling & validation  
✅ Security & compliance features  

---

**Last Updated:** January 2026  
**Status:** Production Ready  
**Version:** 1.0.0
