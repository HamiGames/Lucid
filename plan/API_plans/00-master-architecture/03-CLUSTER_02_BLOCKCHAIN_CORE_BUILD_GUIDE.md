# Cluster 02: Blockchain Core - Detailed Build Guide

## Document Control

| Attribute | Value |
|-----------|-------|
| Cluster ID | 02-BLOCKCHAIN-CORE |
| Build Phase | Phase 2 (Weeks 3-4) |
| Parallel Track | Track C |
| Version | 1.0.0 |
| Last Updated | 2025-01-14 |

---

## Cluster Overview

### Service Information

| Attribute | Value |
|-----------|-------|
| Cluster Name | Blockchain Core Cluster (`lucid_blocks`) |
| Primary Ports | 8084-8087 |
| Service Type | Core blockchain operations and consensus |
| Container Base | `gcr.io/distroless/python3-debian12` |
| Language | Python 3.11+ |

### Services

1. **Blockchain Engine** (Port 8084) - Consensus and block creation
2. **Session Anchoring** (Port 8085) - Session manifest anchoring
3. **Block Manager** (Port 8086) - Block storage and retrieval
4. **Data Chain** (Port 8087) - Data chain operations

### **CRITICAL**: TRON Isolation

- ✅ Handles: `lucid_blocks` blockchain, consensus (PoOT), session anchoring
- ❌ NEVER handles: TRON network, USDT, TRX staking, payments

### Dependencies

| Dependency | Type | Purpose |
|-----------|------|---------|
| Cluster 08 (Storage-Database) | Critical | Block metadata, transaction logs |
| File System | Critical | Chunk storage, Merkle tree data |

---

## MVP Files List

### Priority 1: Core Implementation (12 files, ~2,500 lines)

| # | File Path | Lines | Purpose | Dependencies |
|---|-----------|-------|---------|--------------|
| 1 | `blockchain/core/__init__.py` | 30 | Package init | - |
| 2 | `blockchain/core/blockchain_engine.py` | 400 | Main blockchain engine | hashlib, time |
| 3 | `blockchain/core/consensus_engine.py` | 350 | PoOT consensus mechanism | asyncio, typing |
| 4 | `blockchain/core/block_manager.py` | 300 | Block creation and validation | models.block |
| 5 | `blockchain/core/transaction_processor.py` | 280 | Transaction processing | models.transaction |
| 6 | `blockchain/core/merkle_tree_builder.py` | 320 | Merkle tree construction | hashlib |
| 7 | `blockchain/api/app/main.py` | 150 | FastAPI entry point | FastAPI, uvicorn |
| 8 | `blockchain/api/app/config.py` | 200 | Configuration | pydantic, os |
| 9 | `blockchain/api/app/__init__.py` | 30 | Package init | - |
| 10 | `blockchain/utils/__init__.py` | 30 | Utils package init | - |
| 11 | `blockchain/utils/crypto.py` | 250 | Cryptographic utilities | cryptography |
| 12 | `blockchain/utils/validation.py` | 160 | Block/transaction validation | Pydantic |

**Subtotal**: ~2,500 lines

---

### Priority 1: API Layer (12 files, ~2,400 lines)

| # | File Path | Lines | Purpose | Dependencies |
|---|-----------|-------|---------|--------------|
| 13 | `blockchain/api/app/routers/__init__.py` | 30 | Routers package init | - |
| 14 | `blockchain/api/app/routers/blockchain.py` | 250 | Blockchain info endpoints | services |
| 15 | `blockchain/api/app/routers/blocks.py` | 280 | Block management endpoints | services |
| 16 | `blockchain/api/app/routers/transactions.py` | 260 | Transaction endpoints | services |
| 17 | `blockchain/api/app/routers/anchoring.py` | 300 | Session anchoring endpoints | services |
| 18 | `blockchain/api/app/routers/consensus.py` | 220 | Consensus endpoints | services |
| 19 | `blockchain/api/app/routers/merkle.py` | 240 | Merkle tree endpoints | services |
| 20 | `blockchain/api/app/middleware/auth.py` | 180 | Authentication middleware | JWT |
| 21 | `blockchain/api/app/middleware/rate_limit.py` | 150 | Rate limiting | Redis |
| 22 | `blockchain/api/app/middleware/logging.py` | 140 | Request logging | logging |
| 23 | `blockchain/api/app/middleware/__init__.py` | 30 | Middleware package init | - |
| 24 | `blockchain/api/app/routes.py` | 120 | Route aggregation | FastAPI |

**Subtotal**: ~2,400 lines

---

### Priority 1: Service Layer (6 files, ~1,500 lines)

| # | File Path | Lines | Purpose | Dependencies |
|---|-----------|-------|---------|--------------|
| 25 | `blockchain/api/app/services/__init__.py` | 30 | Services package init | - |
| 26 | `blockchain/api/app/services/blockchain_service.py` | 280 | Blockchain operations | core.blockchain_engine |
| 27 | `blockchain/api/app/services/block_service.py` | 250 | Block operations | core.block_manager |
| 28 | `blockchain/api/app/services/transaction_service.py` | 240 | Transaction operations | core.transaction_processor |
| 29 | `blockchain/api/app/services/anchoring_service.py` | 300 | Anchoring operations | core.merkle_tree_builder |
| 30 | `blockchain/api/app/services/merkle_service.py` | 280 | Merkle tree operations | core.merkle_tree_builder |

**Subtotal**: ~1,500 lines

---

### Priority 1: Data Models (6 files, ~1,000 lines)

| # | File Path | Lines | Purpose | Dependencies |
|---|-----------|-------|---------|--------------|
| 31 | `blockchain/api/app/models/__init__.py` | 30 | Models package init | - |
| 32 | `blockchain/api/app/models/block.py` | 220 | Block data model | Pydantic |
| 33 | `blockchain/api/app/models/transaction.py` | 200 | Transaction model | Pydantic |
| 34 | `blockchain/api/app/models/anchoring.py` | 180 | Session anchoring model | Pydantic |
| 35 | `blockchain/api/app/models/consensus.py` | 160 | Consensus model | Pydantic |
| 36 | `blockchain/api/app/models/common.py` | 140 | Common models | Pydantic |

**Subtotal**: ~1,000 lines

---

### Priority 1: Database Layer (6 files, ~900 lines)

| # | File Path | Lines | Purpose | Dependencies |
|---|-----------|-------|---------|--------------|
| 37 | `blockchain/api/app/database/__init__.py` | 30 | Database package init | - |
| 38 | `blockchain/api/app/database/connection.py` | 150 | MongoDB connection | motor |
| 39 | `blockchain/api/app/database/repositories/block_repository.py` | 200 | Block data access | motor |
| 40 | `blockchain/api/app/database/repositories/transaction_repository.py` | 180 | Transaction data access | motor |
| 41 | `blockchain/api/app/database/repositories/anchoring_repository.py` | 180 | Anchoring data access | motor |
| 42 | `blockchain/api/app/database/repositories/__init__.py` | 30 | Repositories package init | - |

**Subtotal**: ~900 lines

---

### Priority 1: Container Configuration (8 files, ~600 lines)

| # | File Path | Lines | Purpose | Dependencies |
|---|-----------|-------|---------|--------------|
| 43 | `blockchain/Dockerfile.engine` | 90 | Blockchain engine container | - |
| 44 | `blockchain/Dockerfile.anchoring` | 85 | Anchoring service container | - |
| 45 | `blockchain/Dockerfile.manager` | 85 | Block manager container | - |
| 46 | `blockchain/Dockerfile.data` | 85 | Data chain container | - |
| 47 | `blockchain/docker-compose.yml` | 150 | Production deployment | - |
| 48 | `blockchain/docker-compose.dev.yml` | 120 | Development environment | - |
| 49 | `blockchain/requirements.txt` | 60 | Python dependencies | - |
| 50 | `blockchain/.env.example` | 45 | Environment variables | - |

**Subtotal**: ~600 lines

---

### Priority 1: Service-Specific Files (5 files, ~600 lines)

| # | File Path | Lines | Purpose | Dependencies |
|---|-----------|-------|---------|--------------|
| 51 | `blockchain/anchoring/main.py` | 120 | Anchoring service entry | FastAPI |
| 52 | `blockchain/anchoring/anchoring_service.py` | 180 | Anchoring logic | core |
| 53 | `blockchain/manager/main.py` | 120 | Manager service entry | FastAPI |
| 54 | `blockchain/data/main.py` | 120 | Data chain entry | FastAPI |
| 55 | `blockchain/data/chunk_manager.py` | 160 | Chunk management | os, hashlib |

**Subtotal**: ~700 lines

---

### **Total MVP Files**: 55 files, ~10,200 lines

---

## Build Order Sequence

### Step 1: Core Blockchain Engine (Days 1-2)

**Files**: 1-6, 11-12

**Actions**:
- Implement blockchain engine with block creation
- Build PoOT consensus mechanism
- Create Merkle tree builder
- Implement crypto utilities

**Testing**: Create blocks, validate consensus, build Merkle trees

---

### Step 2: Data Models (Day 2)

**Files**: 31-36

**Actions**:
- Define Pydantic models for blocks, transactions
- Add validation rules
- Test serialization

**Testing**: Models validate, serialize to JSON

---

### Step 3: Database Layer (Day 3)

**Files**: 37-42

**Actions**:
- Setup MongoDB connection
- Implement repositories for blocks, transactions
- Test CRUD operations

**Testing**: Database queries successful

---

### Step 4: Service Layer (Day 3-4)

**Files**: 25-30

**Actions**:
- Implement blockchain service
- Build block and transaction services
- Create anchoring service

**Testing**: Services interact with core engine

---

### Step 5: API Layer (Day 4-6)

**Files**: 7-9, 13-24

**Actions**:
- Create FastAPI application
- Implement all routers
- Add middleware (auth, rate limit, logging)
- Mount routes

**Testing**: All endpoints respond, OpenAPI docs generated

---

### Step 6: Additional Services (Day 6-7)

**Files**: 51-55

**Actions**:
- Build session anchoring service
- Implement block manager service
- Create data chain service

**Testing**: Services operational, health checks pass

---

### Step 7: Container Configuration (Day 8-9)

**Files**: 43-50

**Actions**:
- Create Dockerfiles for all 4 services
- Use distroless base images
- Setup Docker Compose

**Testing**: All containers build and run

---

### Step 8: Integration Testing (Day 9-10)

**Actions**:
- Test full blockchain lifecycle
- Test session anchoring workflow
- Test consensus mechanism
- Load testing

**Testing**: All integration tests pass

---

## File-by-File Specifications

### File 2: `blockchain/core/blockchain_engine.py` (400 lines)

**Purpose**: Main blockchain engine implementation

**Key Imports**:
```python
import hashlib
import time
from typing import List, Dict, Optional
from .block_manager import BlockManager
from .consensus_engine import ConsensusEngine
from ..api/app/models.block import Block
```

**Critical Classes**:
- `BlockchainEngine`: Main blockchain class
  - `create_block(transactions, previous_hash)` → Block
  - `validate_block(block)` → bool
  - `add_block_to_chain(block)` → bool
  - `get_latest_block()` → Block
  - `get_chain()` → List[Block]

**Integration Points**:
- ConsensusEngine for block validation
- BlockManager for block storage
- Database for persistence

---

### File 3: `blockchain/core/consensus_engine.py` (350 lines)

**Purpose**: PoOT (Proof of Observation Time) consensus

**Key Imports**:
```python
import asyncio
import time
from typing import List, Dict
from ..api/app/models.consensus import ConsensusVote, ConsensusRound
```

**Critical Functions**:
- `validate_poot_score(node_id, session_time)` → float
- `conduct_consensus_round(block, participants)` → bool
- `count_votes(votes)` → Dict[str, int]
- `reach_consensus(votes, threshold)` → bool

**Integration Points**:
- Requires multiple validator nodes
- Uses session observation time for scoring

---

### File 6: `blockchain/core/merkle_tree_builder.py` (320 lines)

**Purpose**: Build and validate Merkle trees for session chunks

**Key Imports**:
```python
import hashlib
from typing import List, Tuple, Optional
from ..api/app/models.anchoring import MerkleTree, MerkleProof
```

**Critical Functions**:
- `build_merkle_tree(chunk_hashes)` → MerkleTree
- `get_merkle_root(tree)` → str
- `generate_merkle_proof(tree, chunk_index)` → MerkleProof
- `verify_merkle_proof(proof, root_hash)` → bool

**Integration Points**:
- Session Management cluster for chunk hashes
- Anchoring service for tree storage

---

### File 17: `blockchain/api/app/routers/anchoring.py` (300 lines)

**Purpose**: Session anchoring API endpoints

**Key Endpoints**:
- `POST /api/v1/anchoring/session`: Anchor session manifest
- `GET /api/v1/anchoring/session/{session_id}`: Get anchoring status
- `POST /api/v1/anchoring/verify`: Verify session anchoring
- `GET /api/v1/anchoring/status`: Service status

**Key Imports**:
```python
from fastapi import APIRouter, Depends, HTTPException
from ..models.anchoring import AnchorRequest, AnchorResponse
from ..services.anchoring_service import AnchoringService
```

**Integration Points**:
- Session Management cluster for session manifests
- Merkle tree builder for tree construction
- Database for anchoring records

---

## Testing Strategy

### Unit Tests (Priority 2)

**Coverage Areas**:
- Blockchain engine: Block creation, validation, chain management
- Consensus engine: PoOT scoring, voting, consensus rounds
- Merkle tree: Tree building, proof generation, verification
- Transaction processor: Transaction validation, processing

**Coverage Target**: >95%

---

### Integration Tests (Priority 2)

**Test Scenarios**:
1. **Full Block Lifecycle**: Create → Validate → Add to chain → Store
2. **Consensus Round**: Submit block → Conduct voting → Reach consensus
3. **Session Anchoring**: Receive session → Build Merkle tree → Anchor to blockchain
4. **Block Retrieval**: Query blocks by height, ID, latest

---

## Deployment Configuration

### Environment Variables

```bash
# Service Configuration
SERVICE_NAME=lucid-blocks
BLOCKCHAIN_NETWORK=lucid_blocks
CONSENSUS_ALGORITHM=PoOT
DEBUG=false

# Port Configuration
BLOCKCHAIN_ENGINE_PORT=8084
SESSION_ANCHORING_PORT=8085
BLOCK_MANAGER_PORT=8086
DATA_CHAIN_PORT=8087

# Database Configuration
MONGODB_URI=mongodb://mongodb:27017/lucid_blocks
BLOCKCHAIN_DB_NAME=lucid_blocks

# Consensus Configuration
CONSENSUS_TIMEOUT=30
CONSENSUS_PARTICIPANTS_MIN=3
CONSENSUS_VALIDATION_REQUIRED=true

# Block Configuration
BLOCK_TIME_SECONDS=10
BLOCK_SIZE_LIMIT_MB=1
MAX_TRANSACTIONS_PER_BLOCK=1000

# Session Anchoring
ANCHORING_BATCH_SIZE=10
ANCHORING_TIMEOUT=60
MERKLE_TREE_HEIGHT_MAX=20

# Storage Configuration
CHUNK_STORAGE_PATH=/data/chunks
MERKLE_STORAGE_PATH=/data/merkle
BLOCK_STORAGE_PATH=/data/blocks
```

---

### Docker Compose (Production)

```yaml
version: '3.8'
services:
  blockchain-engine:
    build:
      context: .
      dockerfile: Dockerfile.engine
    image: lucid-blockchain-engine:latest
    container_name: lucid-blockchain-engine
    ports:
      - "8084:8084"
    environment:
      - SERVICE_NAME=blockchain-engine
      - CONSENSUS_ALGORITHM=PoOT
      - BLOCK_TIME_SECONDS=10
    depends_on:
      - mongodb
    networks:
      - lucid-network
    volumes:
      - blockchain_data:/data/blocks
    restart: unless-stopped

  session-anchoring:
    build:
      context: .
      dockerfile: Dockerfile.anchoring
    image: lucid-session-anchoring:latest
    container_name: lucid-session-anchoring
    ports:
      - "8085:8085"
    environment:
      - SERVICE_NAME=session-anchoring
      - BLOCKCHAIN_ENGINE_URL=http://blockchain-engine:8084
    depends_on:
      - mongodb
      - blockchain-engine
    networks:
      - lucid-network
    volumes:
      - merkle_data:/data/merkle
    restart: unless-stopped

  block-manager:
    build:
      context: .
      dockerfile: Dockerfile.manager
    image: lucid-block-manager:latest
    container_name: lucid-block-manager
    ports:
      - "8086:8086"
    depends_on:
      - blockchain-engine
    networks:
      - lucid-network
    restart: unless-stopped

  data-chain:
    build:
      context: .
      dockerfile: Dockerfile.data
    image: lucid-data-chain:latest
    container_name: lucid-data-chain
    ports:
      - "8087:8087"
    depends_on:
      - mongodb
    networks:
      - lucid-network
    volumes:
      - chunk_data:/data/chunks
    restart: unless-stopped

volumes:
  blockchain_data:
  merkle_data:
  chunk_data:
```

---

## Integration Points

### Upstream Dependencies

| Cluster | Integration Type | Purpose |
|---------|-----------------|---------|
| 08-Storage-Database | MongoDB | Block metadata, transaction logs, consensus state |
| File System | Direct I/O | Chunk storage, Merkle tree data |

### Downstream Consumers

| Cluster | Integration Type | Purpose |
|---------|-----------------|---------|
| 03-Session-Management | HTTP | Session anchoring requests |
| 01-API-Gateway | HTTP Proxy | Blockchain queries |
| 05-Node-Management | HTTP | PoOT consensus participation |

---

## Success Criteria

### Functional

- [ ] Blockchain engine creates blocks every 10 seconds
- [ ] Consensus mechanism validates blocks
- [ ] Session anchoring operational
- [ ] Merkle tree validation passing
- [ ] Block retrieval by height/ID working
- [ ] Transaction processing functional

### Performance

- [ ] Block creation time <10 seconds
- [ ] Transaction throughput >100/block
- [ ] Merkle tree generation <5 seconds
- [ ] Consensus round <30 seconds

### Quality

- [ ] Unit test coverage >95%
- [ ] Integration tests passing
- [ ] All 4 distroless containers building
- [ ] NO TRON code anywhere in cluster

---

## TRON Isolation Compliance

### ✅ What This Cluster Handles
- `lucid_blocks` blockchain operations
- Consensus mechanism (PoOT)
- Session anchoring
- Merkle tree validation
- Block management

### ❌ What This Cluster NEVER Handles
- TRON network operations
- USDT-TRC20 transactions
- TRX staking
- Payout processing
- Any payment operations

---

## References

- [Blockchain Core Overview](../02-blockchain-core-cluster/00-cluster-overview.md)
- [API Specification](../02-blockchain-core-cluster/01-api-specification.md)
- [Data Models](../02-blockchain-core-cluster/02-data-models.md)

---

**Build Guide Version**: 1.0.0  
**Status**: READY FOR IMPLEMENTATION  
**Estimated Build Time**: 10 days (3 developers)

