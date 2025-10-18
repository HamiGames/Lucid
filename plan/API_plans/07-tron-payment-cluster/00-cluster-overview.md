# TRON Payment Cluster Overview

## Cluster Information

**Cluster ID**: 07-tron-payment-cluster  
**Cluster Name**: TRON Payment System Cluster (ISOLATED)  
**Primary Port**: 8085 (isolated)  
**Service Type**: Payment operations and TRON network integration

## Architecture Overview

The TRON Payment Cluster is **completely isolated** from the core `lucid_blocks` blockchain system and handles all TRON network operations including USDT-TRC20 transfers, payout routing, wallet integration, and TRX staking. This cluster operates in a separate network plane with strict isolation boundaries.

```
┌─────────────────────────────────────────────────────────────┐
│                TRON Payment Cluster (ISOLATED)              │
│                     Payment Operations Only                 │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   TRON      │  │   Payout    │  │   Wallet    │         │
│  │   Client    │  │   Router    │  │   Manager   │         │
│  │   Service   │  │   Service   │  │   Service   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   USDT      │  │   TRX       │  │   Payment   │         │
│  │   Manager   │  │   Staking   │  │   Gateway   │         │
│  │   Service   │  │   Service   │  │   Service   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│              External TRON Network Integration              │
│  TRON Mainnet, TRON Testnet, TronLink, Hardware Wallets    │
└─────────────────────────────────────────────────────────────┘
```

## Services in Cluster

### 1. TRON Client Service
- **Container**: `lucid-tron-client`
- **Base Image**: `gcr.io/distroless/python3-debian12`
- **Port**: 8085
- **Responsibilities**:
  - TRON network connectivity
  - TRON transaction broadcasting
  - TRON block synchronization
  - TRON network status monitoring

### 2. Payout Router Service
- **Container**: `lucid-payout-router`
- **Base Image**: `gcr.io/distroless/python3-debian12`
- **Port**: 8086
- **Responsibilities**:
  - PayoutRouterV0 contract interactions
  - PRKYC (Payout Router Know Your Customer) operations
  - Batch payout processing
  - Payout status tracking

### 3. Wallet Manager Service
- **Container**: `lucid-wallet-manager`
- **Base Image**: `gcr.io/distroless/python3-debian12`
- **Port**: 8087
- **Responsibilities**:
  - User wallet management
  - Hardware wallet integration
  - Wallet balance queries
  - Wallet transaction history

### 4. USDT Manager Service
- **Container**: `lucid-usdt-manager`
- **Base Image**: `gcr.io/distroless/python3-debian12`
- **Port**: 8088
- **Responsibilities**:
  - USDT-TRC20 token operations
  - USDT balance management
  - USDT transfer processing
  - USDT transaction validation

### 5. TRX Staking Service
- **Container**: `lucid-trx-staking`
- **Base Image**: `gcr.io/distroless/python3-debian12`
- **Port**: 8089
- **Responsibilities**:
  - TRX staking operations
  - Staking rewards calculation
  - Staking status monitoring
  - Staking withdrawal processing

### 6. Payment Gateway Service
- **Container**: `lucid-payment-gateway`
- **Base Image**: `gcr.io/distroless/python3-debian12`
- **Port**: 8090
- **Responsibilities**:
  - Payment request processing
  - Payment status tracking
  - Payment reconciliation
  - Payment reporting

## API Endpoints

### TRON Network Endpoints
- `GET /api/v1/tron/network/info` - TRON network information
- `GET /api/v1/tron/network/status` - TRON network status
- `GET /api/v1/tron/network/height` - TRON network height
- `GET /api/v1/tron/network/fees` - TRON network fees

### Wallet Management Endpoints
- `GET /api/v1/wallets` - List user wallets
- `POST /api/v1/wallets` - Create new wallet
- `GET /api/v1/wallets/{wallet_id}` - Get wallet details
- `PUT /api/v1/wallets/{wallet_id}` - Update wallet
- `DELETE /api/v1/wallets/{wallet_id}` - Delete wallet
- `GET /api/v1/wallets/{wallet_id}/balance` - Get wallet balance
- `GET /api/v1/wallets/{wallet_id}/transactions` - Get wallet transactions

### USDT Operations Endpoints
- `POST /api/v1/usdt/transfer` - Transfer USDT
- `GET /api/v1/usdt/balance/{address}` - Get USDT balance
- `GET /api/v1/usdt/transactions/{address}` - Get USDT transactions
- `POST /api/v1/usdt/approve` - Approve USDT spending
- `GET /api/v1/usdt/allowance` - Check USDT allowance

### Payout Operations Endpoints
- `POST /api/v1/payouts/initiate` - Initiate payout
- `GET /api/v1/payouts/{payout_id}` - Get payout status
- `POST /api/v1/payouts/batch` - Process batch payout
- `GET /api/v1/payouts/history` - Get payout history
- `POST /api/v1/payouts/cancel` - Cancel payout

### TRX Staking Endpoints
- `POST /api/v1/staking/stake` - Stake TRX
- `POST /api/v1/staking/unstake` - Unstake TRX
- `GET /api/v1/staking/status/{address}` - Get staking status
- `GET /api/v1/staking/rewards/{address}` - Get staking rewards
- `POST /api/v1/staking/withdraw` - Withdraw staking rewards

### Payment Gateway Endpoints
- `POST /api/v1/payments/process` - Process payment
- `GET /api/v1/payments/{payment_id}` - Get payment status
- `POST /api/v1/payments/refund` - Process refund
- `GET /api/v1/payments/reconciliation` - Get payment reconciliation
- `POST /api/v1/payments/webhook` - Payment webhook endpoint

## Dependencies

### External Dependencies
- **TRON Mainnet**: Primary TRON network for production operations
- **TRON Testnet**: TRON test network for development and testing
- **TronLink**: TRON wallet integration
- **Hardware Wallets**: Ledger, Trezor integration
- **MongoDB**: Payment data, wallet metadata, transaction logs

### **CRITICAL**: Isolation from Blockchain Core
- **NO lucid_blocks dependencies** in this cluster
- **NO blockchain consensus operations** in this cluster
- **NO session anchoring** in this cluster
- **NO Merkle tree operations** in this cluster
- All blockchain operations handled by separate `lucid-blocks` cluster

## Configuration

### Environment Variables
```bash
# Service Configuration
SERVICE_NAME=tron-payment-service
TRON_NETWORK=mainnet
DEBUG=false

# Port Configuration
TRON_CLIENT_PORT=8085
PAYOUT_ROUTER_PORT=8086
WALLET_MANAGER_PORT=8087
USDT_MANAGER_PORT=8088
TRX_STAKING_PORT=8089
PAYMENT_GATEWAY_PORT=8090

# TRON Network Configuration
TRON_NODE_URL=https://api.trongrid.io
TRON_NODE_API_KEY=your-tron-api-key
TRON_NETWORK_ID=mainnet
TRON_CHAIN_ID=0x2b6653dc

# USDT Contract Configuration
USDT_CONTRACT_ADDRESS=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
USDT_CONTRACT_ABI_PATH=/app/contracts/usdt_abi.json

# Payout Router Configuration
PAYOUT_ROUTER_CONTRACT_ADDRESS=your-payout-router-address
PAYOUT_ROUTER_PRIVATE_KEY=your-private-key
PAYOUT_BATCH_SIZE=100
PAYOUT_TIMEOUT=300

# Wallet Configuration
WALLET_ENCRYPTION_KEY=your-wallet-encryption-key
HARDWARE_WALLET_ENABLED=true
LEDGER_ENABLED=true
TREZOR_ENABLED=true

# Database Configuration
MONGODB_URI=mongodb://mongodb:27017/lucid_payments
PAYMENT_DB_NAME=lucid_payments

# Security Configuration
TRON_PRIVATE_KEY_ENCRYPTION=true
WALLET_SEED_ENCRYPTION=true
TRANSACTION_SIGNING_ENABLED=true
```

### Docker Compose Configuration
```yaml
version: '3.8'
services:
  tron-client:
    build:
      context: ./payment-systems/tron-payment-service
      dockerfile: Dockerfile.tron-client
    image: lucid-tron-client:latest
    container_name: lucid-tron-client
    ports:
      - "8085:8085"
    environment:
      - SERVICE_NAME=tron-client
      - TRON_NODE_URL=https://api.trongrid.io
      - TRON_NETWORK=mainnet
      - MONGODB_URI=mongodb://mongodb:27017/lucid_payments
    depends_on:
      - mongodb
    networks:
      - tron-payment-network
    volumes:
      - tron_data:/data/tron
    restart: unless-stopped

  payout-router:
    build:
      context: ./payment-systems/tron-payment-service
      dockerfile: Dockerfile.payout-router
    image: lucid-payout-router:latest
    container_name: lucid-payout-router
    ports:
      - "8086:8086"
    environment:
      - SERVICE_NAME=payout-router
      - PAYOUT_ROUTER_CONTRACT_ADDRESS=${PAYOUT_ROUTER_CONTRACT_ADDRESS}
      - PAYOUT_ROUTER_PRIVATE_KEY=${PAYOUT_ROUTER_PRIVATE_KEY}
      - TRON_CLIENT_URL=http://tron-client:8085
    depends_on:
      - tron-client
    networks:
      - tron-payment-network
    restart: unless-stopped

  wallet-manager:
    build:
      context: ./payment-systems/tron-payment-service
      dockerfile: Dockerfile.wallet-manager
    image: lucid-wallet-manager:latest
    container_name: lucid-wallet-manager
    ports:
      - "8087:8087"
    environment:
      - SERVICE_NAME=wallet-manager
      - WALLET_ENCRYPTION_KEY=${WALLET_ENCRYPTION_KEY}
      - HARDWARE_WALLET_ENABLED=true
      - TRON_CLIENT_URL=http://tron-client:8085
    depends_on:
      - tron-client
    networks:
      - tron-payment-network
    restart: unless-stopped

  usdt-manager:
    build:
      context: ./payment-systems/tron-payment-service
      dockerfile: Dockerfile.usdt-manager
    image: lucid-usdt-manager:latest
    container_name: lucid-usdt-manager
    ports:
      - "8088:8088"
    environment:
      - SERVICE_NAME=usdt-manager
      - USDT_CONTRACT_ADDRESS=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
      - TRON_CLIENT_URL=http://tron-client:8085
    depends_on:
      - tron-client
    networks:
      - tron-payment-network
    restart: unless-stopped

  trx-staking:
    build:
      context: ./payment-systems/tron-payment-service
      dockerfile: Dockerfile.trx-staking
    image: lucid-trx-staking:latest
    container_name: lucid-trx-staking
    ports:
      - "8089:8089"
    environment:
      - SERVICE_NAME=trx-staking
      - TRON_CLIENT_URL=http://tron-client:8085
    depends_on:
      - tron-client
    networks:
      - tron-payment-network
    restart: unless-stopped

  payment-gateway:
    build:
      context: ./payment-systems/tron-payment-service
      dockerfile: Dockerfile.payment-gateway
    image: lucid-payment-gateway:latest
    container_name: lucid-payment-gateway
    ports:
      - "8090:8090"
    environment:
      - SERVICE_NAME=payment-gateway
      - TRON_CLIENT_URL=http://tron-client:8085
      - PAYOUT_ROUTER_URL=http://payout-router:8086
      - WALLET_MANAGER_URL=http://wallet-manager:8087
      - USDT_MANAGER_URL=http://usdt-manager:8088
    depends_on:
      - tron-client
      - payout-router
      - wallet-manager
      - usdt-manager
    networks:
      - tron-payment-network
    restart: unless-stopped

networks:
  tron-payment-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.21.0.0/16

volumes:
  tron_data:
    driver: local
```

## Performance Characteristics

### Expected Load
- **USDT Transfers**: 1000+ transfers per hour
- **Payout Processing**: 100+ payouts per hour
- **Wallet Operations**: 5000+ operations per hour
- **TRX Staking**: 100+ staking operations per hour

### Resource Requirements
- **CPU**: 8 cores minimum, 16 cores recommended
- **Memory**: 16GB minimum, 32GB recommended
- **Storage**: 500GB minimum for TRON data
- **Network**: 2Gbps minimum bandwidth for TRON connectivity

## Security Considerations

### TRON Network Security
- **Private Key Management**: Encrypted private key storage
- **Transaction Signing**: Secure transaction signing process
- **Network Security**: TLS encryption for TRON API calls
- **Wallet Security**: Hardware wallet integration for enhanced security

### Payment Security
- **Payout Validation**: Multi-signature payout validation
- **Transaction Monitoring**: Real-time transaction monitoring
- **Fraud Detection**: Automated fraud detection systems
- **Audit Logging**: Comprehensive audit trail for all operations

### Data Protection
- **Encryption at Rest**: All sensitive data encrypted at rest
- **Encryption in Transit**: All data encrypted in transit
- **Access Control**: Role-based access control for payment operations
- **Secure Storage**: Secure storage for private keys and sensitive data

## Monitoring & Observability

### Health Checks
- **TRON Network Health**: `/api/v1/tron/network/status`
- **Service Health**: Individual service health endpoints
- **Payment Health**: Payment processing health monitoring
- **Wallet Health**: Wallet service health monitoring

### Metrics Collection
- **Payment Metrics**: Payment success rate, processing time
- **TRON Metrics**: TRON network connectivity, transaction fees
- **Wallet Metrics**: Wallet operations, balance queries
- **Payout Metrics**: Payout success rate, processing time

### Logging
- **Payment Events**: Payment processing, success, failures
- **TRON Events**: TRON transactions, network events
- **Wallet Events**: Wallet operations, balance changes
- **Security Events**: Security incidents, fraud attempts

## Scaling Strategy

### Horizontal Scaling
- **Service Replication**: Multiple instances of each service
- **Load Balancing**: Distributed load across service instances
- **Database Sharding**: Sharded database for payment data
- **Network Scaling**: Multiple TRON node connections

### Vertical Scaling
- **CPU Optimization**: Optimized TRON transaction processing
- **Memory Optimization**: Efficient memory usage for wallet operations
- **Storage Optimization**: Optimized storage for TRON data
- **Network Optimization**: Optimized TRON network communication

## Deployment Strategy

### Container Deployment
- **Distroless Images**: All services use distroless base images
- **Multi-stage Builds**: Optimized container images
- **Health Checks**: Comprehensive health monitoring
- **Rolling Updates**: Zero-downtime deployments

### Configuration Management
- **Environment-specific**: Configuration per deployment environment
- **Secret Management**: Secure handling of private keys and API keys
- **Configuration Validation**: Startup configuration validation
- **Hot Reloading**: Non-critical configuration updates

## Troubleshooting

### Common Issues
1. **TRON Network Connectivity**: Check TRON node connectivity and API keys
2. **USDT Transfer Failures**: Verify USDT contract address and balance
3. **Payout Processing Errors**: Check payout router contract and private keys
4. **Wallet Integration Issues**: Verify hardware wallet connectivity

### Debugging Tools
- **TRON Explorer**: TRON network transaction explorer
- **Payment Monitor**: Real-time payment processing monitoring
- **Wallet Debugger**: Wallet operation debugging tools
- **Transaction Tracer**: End-to-end transaction tracking

## TRON Isolation Compliance

### **CRITICAL**: Complete Separation from lucid_blocks

**What this cluster handles**:
- ✅ TRON network operations
- ✅ USDT-TRC20 transfers
- ✅ Payout routing and processing
- ✅ Wallet management
- ✅ TRX staking operations
- ✅ Payment gateway operations

**What this cluster NEVER handles**:
- ❌ `lucid_blocks` blockchain operations
- ❌ Session anchoring
- ❌ Consensus mechanisms
- ❌ Merkle tree operations
- ❌ Block creation or validation
- ❌ Data chain operations

### Isolation Enforcement
- **Network Isolation**: Separate network plane for TRON operations
- **Code Review**: All code reviewed for blockchain core contamination
- **Dependency Scanning**: No blockchain core dependencies allowed
- **Service Boundaries**: Clear separation from blockchain services

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
