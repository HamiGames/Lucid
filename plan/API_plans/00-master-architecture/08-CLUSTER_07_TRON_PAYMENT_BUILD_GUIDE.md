# Cluster 07: TRON Payment - Detailed Build Guide

## Document Control

| Attribute | Value |
|-----------|-------|
| Cluster ID | 07-TRON-PAYMENT |
| Build Phase | Phase 4 (Weeks 8-9) OR Early (Week 3-4) |
| Parallel Track | Track H (Isolated) |
| Version | 1.0.0 |

---

## Cluster Overview

### Services (Port 8085 base)
1. **TRON Client** (8085) - TRON network operations
2. **Payout Router** (8086) - V0 & KYC routing
3. **Wallet Manager** (8087) - Wallet operations
4. **USDT Manager** (8088) - USDT-TRC20 operations
5. **TRX Staking** (8089) - Staking operations
6. **Payment Gateway** (8090) - Payment orchestration

### **CRITICAL**: Complete Isolation
This cluster is completely isolated from blockchain core (Cluster 02).
Only handles TRON payments - NO lucid_blocks operations.

### Dependencies
- Cluster 08 (Database): Payment records
- Cluster 09 (Authentication): User verification

---

## MVP Files (40 files, ~5,500 lines)

### Core Services (18 files, ~3,000 lines)
1. `tron/services/tron_client.py` (350) - TRON network client
2. `tron/services/payout_router.py` (300) - Payout routing
3. `tron/services/wallet_manager.py` (280) - Wallet management
4. `tron/services/usdt_manager.py` (300) - USDT operations
5. `tron/services/trx_staking.py` (280) - TRX staking
6. `tron/services/payment_gateway.py` (320) - Payment gateway
7-18. Supporting services, models

### API Routes (10 files, ~1,500 lines)
- TRON network endpoints
- Wallet endpoints
- USDT endpoints
- Payout endpoints
- Staking endpoints

### Configuration (12 files, ~1,000 lines)
- 6 Dockerfiles (one per service)
- docker-compose files
- Contract ABIs
- Environment configs

---

## Build Sequence (10 days)

### Days 1-3: TRON Client & Wallet Manager
- Connect to TRON network (mainnet/testnet)
- Implement wallet creation
- Test TRON connectivity

### Days 4-6: USDT & Payout Router
- Implement USDT-TRC20 transfers
- Build payout router (V0 + KYC)
- Test payout flow

### Days 7-8: TRX Staking & Payment Gateway
- Implement TRX staking
- Build payment gateway
- Integration

### Days 9-10: Testing & Containerization
- Full payment flow testing
- Security testing
- Container deployment

---

## Key Implementations

### TRON Client
```python
# tron/services/tron_client.py (350 lines)
from tronpy import Tron

class TronClient:
    def __init__(self, network='mainnet'):
        self.client = Tron(network=network)
        
    async def get_balance(self, address: str) -> float:
        # Get TRX balance
        
    async def get_usdt_balance(self, address: str) -> float:
        # Get USDT-TRC20 balance
```

### Payout Router
```python
# tron/services/payout_router.py (300 lines)
class PayoutRouter:
    async def route_payout(
        self, 
        user_id: str, 
        amount: float, 
        kyc_verified: bool
    ):
        if kyc_verified:
            return await self.payout_router_kyc.process(...)
        else:
            return await self.payout_router_v0.process(...)
```

### USDT Manager
```python
# tron/services/usdt_manager.py (300 lines)
class USDTManager:
    async def transfer_usdt(
        self, 
        from_address: str, 
        to_address: str, 
        amount: float,
        private_key: str
    ):
        # Build USDT-TRC20 transaction
        # Sign with private key
        # Broadcast to TRON network
```

---

## Environment Variables
```bash
# TRON Network
TRON_NETWORK=mainnet  # or testnet
TRON_FULL_NODE_URL=https://api.trongrid.io
TRON_SOLIDITY_NODE_URL=https://api.trongrid.io
TRON_EVENT_SERVER_URL=https://api.trongrid.io

# Contract Addresses
USDT_CONTRACT_ADDRESS=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
PAYOUT_ROUTER_V0_ADDRESS=...
PAYOUT_ROUTER_KYC_ADDRESS=...

# Wallet Configuration
HOT_WALLET_ADDRESS=...
HOT_WALLET_PRIVATE_KEY=${ENCRYPTED_KEY}

# Payout Configuration
MIN_PAYOUT_AMOUNT=10.0
MAX_PAYOUT_AMOUNT=10000.0
PAYOUT_FEE_TRX=5.0

# Service Ports
TRON_CLIENT_PORT=8085
PAYOUT_ROUTER_PORT=8086
WALLET_MANAGER_PORT=8087
USDT_MANAGER_PORT=8088
TRX_STAKING_PORT=8089
PAYMENT_GATEWAY_PORT=8090
```

---

## Docker Compose
```yaml
version: '3.8'
services:
  tron-client:
    build:
      dockerfile: Dockerfile.tron-client
    ports: ["8085:8085"]
    environment:
      - TRON_NETWORK=mainnet
    networks:
      - lucid-network-isolated  # Separate network!

  payout-router:
    build:
      dockerfile: Dockerfile.payout-router
    ports: ["8086:8086"]
    depends_on:
      - tron-client
    networks:
      - lucid-network-isolated

  wallet-manager:
    build:
      dockerfile: Dockerfile.wallet-manager
    ports: ["8087:8087"]
    networks:
      - lucid-network-isolated

  # ... other services
```

---

## TRON Isolation Compliance

### ✅ What This Cluster Handles
- TRON network operations
- USDT-TRC20 transfers
- TRX staking
- Payout processing
- Wallet management
- Payment gateway

### ❌ What This Cluster NEVER Handles
- lucid_blocks blockchain
- Consensus mechanisms
- Session anchoring
- Merkle trees
- Block creation
- Any blockchain core operations

### Isolation Enforcement
- Separate directory: `payment-systems/tron-payment-service/`
- Separate network: `lucid-network-isolated`
- No imports from `blockchain/` directory
- No shared code with Cluster 02 (Blockchain Core)

---

## Success Criteria

- [ ] TRON client connects to network
- [ ] Wallets created and managed
- [ ] USDT transfers successful
- [ ] Payout router operational (V0 + KYC)
- [ ] TRX staking working
- [ ] Payment gateway processing payments
- [ ] All 6 services containerized
- [ ] Complete isolation from Cluster 02 verified

---

**Build Time**: 10 days (2 developers)  
**Can Start**: After Phase 1 (anytime from Week 3)

