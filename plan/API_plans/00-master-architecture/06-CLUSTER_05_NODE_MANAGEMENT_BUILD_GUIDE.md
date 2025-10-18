# Cluster 05: Node Management - Detailed Build Guide

## Document Control

| Attribute | Value |
|-----------|-------|
| Cluster ID | 05-NODE-MANAGEMENT |
| Build Phase | Phase 3 (Weeks 5-7) |
| Parallel Track | Track F |
| Version | 1.0.0 |

---

## Cluster Overview

### Service (Port 8095)
Single comprehensive node management service

### Key Responsibilities
- Worker node registration and management
- Pool management
- Resource monitoring
- PoOT (Proof of Observation Time) operations
- Payout management (TRON integration point)

### Dependencies
- Cluster 01 (API Gateway): Authentication
- Cluster 02 (Blockchain): PoOT consensus participation
- Cluster 07 (TRON Payment): Payout submission
- Cluster 08 (Database): Node metadata

---

## MVP Files (45 files, ~6,500 lines)

### Core Application (15 files, ~2,500 lines)
1. `node/main.py` (150) - FastAPI entry point
2. `node/config.py` (200) - Configuration
3. `node/worker/node_worker.py` (350) - Worker management
4. `node/worker/node_service.py` (300) - Business logic
5. `node/pools/pool_service.py` (280) - Pool management
6. `node/resources/resource_monitor.py` (300) - Resource tracking
7. `node/poot/poot_validator.py` (280) - PoOT validation
8. `node/poot/poot_calculator.py` (250) - Score calculation
9. `node/payouts/payout_processor.py` (300) - Payout processing
10. `node/payouts/tron_client.py` (220) - TRON integration
11-15. Models, utils, repositories (370)

### API Layer (15 files, ~2,000 lines)
- Route handlers for nodes, pools, resources
- Payout endpoints
- PoOT endpoints
- Monitoring endpoints

### Configuration (10 files, ~1,500 lines)
- Dockerfile
- docker-compose files
- Requirements
- Environment configs

### Testing & Monitoring (5 files, ~500 lines)
- Health checks
- Metrics collection

---

## Build Sequence (21 days)

### Week 1: Worker & Pool Management
**Days 1-4**: Worker node management
- Registration and authentication
- Node lifecycle (register, activate, deactivate)
- Node status tracking

**Days 5-7**: Pool management
- Pool creation and configuration
- Node assignment to pools
- Pool performance tracking

### Week 2: Resources & PoOT
**Days 8-11**: Resource monitoring
- CPU, memory, disk, network metrics
- Real-time resource tracking
- Historical data storage

**Days 12-14**: PoOT operations
- Observation time calculation
- Score validation
- Consensus participation

### Week 3: Payouts & Integration
**Days 15-17**: Payout management
- Payout calculation
- TRON integration (Cluster 07)
- Payout submission

**Days 18-21**: Integration & Testing
- Full system integration
- Performance testing
- Containerization

---

## Key Implementations

### Worker Node Management
```python
# node/worker/node_worker.py (350 lines)
class NodeWorker:
    async def register_node(self, node_data: NodeRegistration):
        # Validate hardware
        # Generate node ID
        # Store in database
        
    async def update_node_status(self, node_id: str, status: str):
        # Update status
        # Notify pool manager
```

### PoOT Operations
```python
# node/poot/poot_calculator.py (250 lines)
class PoOTCalculator:
    async def calculate_poot_score(
        self, 
        node_id: str, 
        observation_time: float
    ) -> float:
        # Calculate base score from observation time
        # Apply node multipliers
        # Submit to blockchain consensus
```

### Payout Processing
```python
# node/payouts/payout_processor.py (300 lines)
class PayoutProcessor:
    async def process_payout(self, node_id: str, amount: float):
        # Calculate payout amount
        # Submit to TRON Payment cluster (Cluster 07)
        # Record payout transaction
        # Update node earnings
```

---

## Environment Variables
```bash
NODE_MANAGEMENT_PORT=8095

# Database
MONGODB_URI=mongodb://mongodb:27017/lucid_nodes
REDIS_URI=redis://redis:6379/2

# Integration URLs
BLOCKCHAIN_URL=http://blockchain-core:8084
TRON_PAYMENT_URL=http://tron-payment:8085
API_GATEWAY_URL=http://api-gateway:8080

# PoOT Configuration
POOT_MIN_OBSERVATION_TIME=3600  # 1 hour minimum
POOT_SCORE_MULTIPLIER=1.5

# Payout Configuration
PAYOUT_MIN_AMOUNT_USDT=10.0
PAYOUT_FREQUENCY_HOURS=24
```

---

## Docker Compose
```yaml
version: '3.8'
services:
  node-management:
    build:
      context: .
      dockerfile: Dockerfile
    image: lucid-node-management:latest
    container_name: lucid-node-management
    ports:
      - "8095:8095"
    environment:
      - NODE_MANAGEMENT_PORT=8095
      - MONGODB_URI=mongodb://mongodb:27017/lucid_nodes
      - BLOCKCHAIN_URL=http://blockchain-core:8084
      - TRON_PAYMENT_URL=http://tron-payment:8085
    depends_on:
      - mongodb
      - redis
    networks:
      - lucid-network
    restart: unless-stopped
```

---

## Integration Points

### TRON Payment Integration (Cluster 07)
```python
# node/payouts/tron_client.py (220 lines)
class TronPaymentClient:
    async def submit_payout(
        self, 
        node_id: str, 
        wallet_address: str, 
        amount_usdt: float
    ):
        # Call TRON Payment cluster API
        # POST /api/v1/payouts
        # Track payout status
```

### Blockchain Integration (Cluster 02)
```python
# node/poot/blockchain_client.py (180 lines)
class BlockchainClient:
    async def submit_poot_vote(
        self, 
        node_id: str, 
        score: float, 
        block_id: str
    ):
        # Submit PoOT vote to consensus
        # POST /api/v1/consensus/vote
```

---

## Testing Strategy

### Unit Tests
- Worker registration and lifecycle
- Pool management operations
- PoOT score calculation
- Payout processing logic

### Integration Tests
- Node registration → Pool assignment → Resource monitoring
- PoOT calculation → Blockchain submission
- Payout calculation → TRON submission

### Performance Tests
- Concurrent node registrations: >100/second
- PoOT calculation latency: <100ms
- Resource metric collection: Every 30 seconds

---

## Success Criteria

- [ ] Worker nodes can register and authenticate
- [ ] Pools created and nodes assigned
- [ ] Resource metrics collected continuously
- [ ] PoOT scores calculated and validated
- [ ] Consensus votes submitted to blockchain
- [ ] Payouts calculated and submitted to TRON
- [ ] All APIs responding correctly
- [ ] Container deployed successfully

---

**Build Time**: 21 days (2 developers)

