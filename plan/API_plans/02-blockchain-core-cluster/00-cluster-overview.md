# Blockchain Core Cluster Overview

## Cluster Information

**Cluster ID**: 02-blockchain-core-cluster  
**Cluster Name**: Blockchain Core Cluster (Cluster B) - lucid_blocks  
**Primary Port**: 8084  
**Service Type**: Core blockchain operations and consensus

## Architecture Overview

The Blockchain Core Cluster implements the `lucid_blocks` blockchain system, providing core blockchain functionality including consensus mechanisms, session anchoring, data chain operations, and block management. This cluster is **completely isolated** from TRON payment operations.

```
┌─────────────────────────────────────────────────────────────┐
│                Blockchain Core Cluster (B)                 │
│                     lucid_blocks System                    │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Consensus  │  │   Session   │  │   Block     │         │
│  │  Engine     │  │  Anchoring  │  │  Manager    │         │
│  │  (PoOT)     │  │   Service   │  │   Service   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Merkle    │  │   Chunk     │  │   Data      │         │
│  │   Tree      │  │  Storage    │  │   Chain     │         │
│  │  Builder    │  │  Service    │  │   Service   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│              External Integrations                          │
│  MongoDB (metadata), File System (chunks), Tor Network      │
└─────────────────────────────────────────────────────────────┘
```

## Services in Cluster

### 1. Blockchain Engine Service
- **Container**: `lucid-lucid-blocks-engine`
- **Base Image**: `gcr.io/distroless/python3-debian12`
- **Port**: 8084
- **Responsibilities**:
  - Consensus mechanism implementation (PoOT - Proof of Observation Time)
  - Block creation and validation
  - Transaction processing
  - Network synchronization

### 2. Session Anchoring Service
- **Container**: `lucid-session-anchoring`
- **Base Image**: `gcr.io/distroless/python3-debian12`
- **Port**: 8085
- **Responsibilities**:
  - Session manifest anchoring to blockchain
  - Merkle tree validation
  - Data integrity verification
  - Chunk reference management

### 3. Block Manager Service
- **Container**: `lucid-block-manager`
- **Base Image**: `gcr.io/distroless/python3-debian12`
- **Port**: 8086
- **Responsibilities**:
  - Block storage and retrieval
  - Block height management
  - Block validation and verification
  - Blockchain state management

### 4. Data Chain Service
- **Container**: `lucid-data-chain`
- **Base Image**: `gcr.io/distroless/python3-debian12`
- **Port**: 8087
- **Responsibilities**:
  - Data chain operations
  - Chunk metadata management
  - Storage coordination
  - Data integrity monitoring

## API Endpoints

### Blockchain Information Endpoints
- `GET /api/v1/chain/info` - Blockchain network information
- `GET /api/v1/chain/status` - Blockchain status and health
- `GET /api/v1/chain/height` - Current block height
- `GET /api/v1/chain/network` - Network topology information

### Block Management Endpoints
- `GET /api/v1/blocks` - List blocks with pagination
- `GET /api/v1/blocks/{block_id}` - Get specific block details
- `GET /api/v1/blocks/height/{height}` - Get block by height
- `GET /api/v1/blocks/latest` - Get latest block
- `POST /api/v1/blocks/validate` - Validate block structure

### Transaction Endpoints
- `POST /api/v1/transactions` - Submit transaction to blockchain
- `GET /api/v1/transactions/{tx_id}` - Get transaction details
- `GET /api/v1/transactions/pending` - List pending transactions
- `POST /api/v1/transactions/batch` - Submit batch of transactions

### Session Anchoring Endpoints
- `POST /api/v1/anchoring/session` - Anchor session manifest to blockchain
- `GET /api/v1/anchoring/session/{session_id}` - Get session anchoring status
- `POST /api/v1/anchoring/verify` - Verify session anchoring
- `GET /api/v1/anchoring/status` - Get anchoring service status

### Consensus Endpoints
- `GET /api/v1/consensus/status` - Get consensus status
- `GET /api/v1/consensus/participants` - List consensus participants
- `POST /api/v1/consensus/vote` - Submit consensus vote
- `GET /api/v1/consensus/history` - Get consensus history

### Merkle Tree Endpoints
- `POST /api/v1/merkle/build` - Build Merkle tree for session
- `GET /api/v1/merkle/{root_hash}` - Get Merkle tree details
- `POST /api/v1/merkle/verify` - Verify Merkle tree proof
- `GET /api/v1/merkle/validation/{session_id}` - Get validation status

## Dependencies

### Internal Dependencies
- **API Gateway Cluster**: Request routing and authentication
- **Session Management Cluster**: Session lifecycle coordination
- **Storage Database Cluster**: Metadata storage and retrieval

### External Dependencies
- **MongoDB**: Block metadata, transaction logs, consensus state
- **File System**: Chunk storage and Merkle tree data
- **Tor Network**: Secure peer-to-peer communication

### **CRITICAL**: TRON Isolation
- **NO TRON dependencies** in this cluster
- **NO payment processing** in this cluster
- **NO TRON network access** from this cluster
- All TRON operations handled by separate `tron-payment-service`

## Configuration

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

# Session Anchoring Configuration
ANCHORING_BATCH_SIZE=10
ANCHORING_TIMEOUT=60
MERKLE_TREE_HEIGHT_MAX=20

# Storage Configuration
CHUNK_STORAGE_PATH=/data/chunks
MERKLE_STORAGE_PATH=/data/merkle
BLOCK_STORAGE_PATH=/data/blocks

# Network Configuration
PEER_DISCOVERY_ENABLED=true
PEER_SYNC_INTERVAL=30
TOR_NETWORK_REQUIRED=true

# Security Configuration
BLOCK_SIGNATURE_REQUIRED=true
TRANSACTION_SIGNATURE_REQUIRED=true
MERKLE_PROOF_VALIDATION=true
```

### Docker Compose Configuration
```yaml
version: '3.8'
services:
  lucid-blocks-engine:
    build:
      context: ./blockchain
      dockerfile: Dockerfile.engine
    image: lucid-lucid-blocks-engine:latest
    container_name: lucid-lucid-blocks-engine
    ports:
      - "8084:8084"
    environment:
      - SERVICE_NAME=lucid-blocks-engine
      - MONGODB_URI=mongodb://mongodb:27017/lucid_blocks
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
      context: ./blockchain
      dockerfile: Dockerfile.anchoring
    image: lucid-session-anchoring:latest
    container_name: lucid-session-anchoring
    ports:
      - "8085:8085"
    environment:
      - SERVICE_NAME=session-anchoring
      - MONGODB_URI=mongodb://mongodb:27017/lucid_blocks
      - BLOCKCHAIN_ENGINE_URL=http://lucid-blocks-engine:8084
    depends_on:
      - mongodb
      - lucid-blocks-engine
    networks:
      - lucid-network
    volumes:
      - merkle_data:/data/merkle
    restart: unless-stopped

  block-manager:
    build:
      context: ./blockchain
      dockerfile: Dockerfile.manager
    image: lucid-block-manager:latest
    container_name: lucid-block-manager
    ports:
      - "8086:8086"
    environment:
      - SERVICE_NAME=block-manager
      - MONGODB_URI=mongodb://mongodb:27017/lucid_blocks
      - BLOCKCHAIN_ENGINE_URL=http://lucid-blocks-engine:8084
    depends_on:
      - mongodb
      - lucid-blocks-engine
    networks:
      - lucid-network
    volumes:
      - blockchain_data:/data/blocks
    restart: unless-stopped

  data-chain:
    build:
      context: ./blockchain
      dockerfile: Dockerfile.data
    image: lucid-data-chain:latest
    container_name: lucid-data-chain
    ports:
      - "8087:8087"
    environment:
      - SERVICE_NAME=data-chain
      - MONGODB_URI=mongodb://mongodb:27017/lucid_blocks
      - CHUNK_STORAGE_PATH=/data/chunks
    depends_on:
      - mongodb
    networks:
      - lucid-network
    volumes:
      - chunk_data:/data/chunks
    restart: unless-stopped

volumes:
  blockchain_data:
    driver: local
  merkle_data:
    driver: local
  chunk_data:
    driver: local
```

## Performance Characteristics

### Expected Load
- **Block Creation**: 1 block every 10 seconds
- **Transaction Throughput**: 100+ transactions per block
- **Session Anchoring**: 10+ sessions per block
- **Consensus Operations**: 3+ participants per consensus round

### Resource Requirements
- **CPU**: 4 cores minimum, 8 cores recommended
- **Memory**: 8GB minimum, 16GB recommended
- **Storage**: 100GB minimum for blockchain data
- **Network**: 1Gbps minimum bandwidth

## Security Considerations

### Blockchain Security
- **Consensus Security**: PoOT algorithm with multiple validators
- **Cryptographic Signatures**: All blocks and transactions signed
- **Merkle Tree Validation**: Complete data integrity verification
- **Network Security**: Tor-only communication between peers

### Data Integrity
- **Block Validation**: Complete block structure validation
- **Transaction Verification**: Signature and format verification
- **Merkle Proof Validation**: Mathematical proof verification
- **Chain Continuity**: Block chain validation and verification

### Access Control
- **Node Authentication**: Cryptographic node identity verification
- **Consensus Participation**: Restricted to authorized nodes
- **API Access**: Token-based authentication for API endpoints
- **Data Access**: Role-based access control for blockchain data

## Monitoring & Observability

### Health Checks
- **Blockchain Health**: `/api/v1/chain/status`
- **Consensus Health**: `/api/v1/consensus/status`
- **Service Health**: Individual service health endpoints
- **Network Health**: Peer connectivity and synchronization status

### Metrics Collection
- **Block Metrics**: Block creation rate, block size, validation time
- **Transaction Metrics**: Transaction throughput, confirmation time
- **Consensus Metrics**: Consensus participation, voting patterns
- **Network Metrics**: Peer count, synchronization status, latency

### Logging
- **Block Events**: Block creation, validation, and consensus events
- **Transaction Events**: Transaction submission, validation, and confirmation
- **Consensus Events**: Voting, participation, and consensus outcomes
- **Error Events**: Validation failures, network errors, consensus failures

## Scaling Strategy

### Horizontal Scaling
- **Consensus Scaling**: Multiple consensus participants
- **Block Processing**: Distributed block validation
- **Data Storage**: Distributed chunk and Merkle tree storage
- **Network Scaling**: Peer-to-peer network expansion

### Vertical Scaling
- **CPU Optimization**: Consensus algorithm optimization
- **Memory Optimization**: Blockchain state caching
- **Storage Optimization**: Block and transaction compression
- **Network Optimization**: Connection pooling and batching

## Deployment Strategy

### Container Deployment
- **Distroless Images**: All services use distroless base images
- **Multi-stage Builds**: Optimized container images
- **Health Checks**: Comprehensive health monitoring
- **Rolling Updates**: Zero-downtime deployments

### Configuration Management
- **Environment-specific**: Configuration per deployment environment
- **Secret Management**: Secure handling of cryptographic keys
- **Configuration Validation**: Startup configuration validation
- **Hot Reloading**: Non-critical configuration updates

## Troubleshooting

### Common Issues
1. **Consensus Failures**: Check participant connectivity and voting patterns
2. **Block Validation Errors**: Verify block structure and signatures
3. **Session Anchoring Failures**: Check Merkle tree construction and validation
4. **Network Synchronization Issues**: Verify peer connectivity and block propagation

### Debugging Tools
- **Block Explorer**: Web interface for blockchain exploration
- **Consensus Monitor**: Real-time consensus status monitoring
- **Network Analyzer**: Peer connectivity and synchronization analysis
- **Transaction Tracer**: End-to-end transaction tracking

## TRON Isolation Compliance

### **CRITICAL**: Complete Separation from TRON

**What this cluster handles**:
- ✅ `lucid_blocks` blockchain operations
- ✅ Session anchoring and Merkle tree validation
- ✅ Consensus mechanism (PoOT)
- ✅ Block creation and validation
- ✅ Data chain operations
- ✅ Transaction processing

**What this cluster NEVER handles**:
- ❌ TRON network operations
- ❌ USDT-TRC20 transactions
- ❌ TRON wallet operations
- ❌ TRON payout processing
- ❌ TRX staking operations
- ❌ TRON contract interactions

### Isolation Enforcement
- **Code Review**: All code reviewed for TRON contamination
- **Dependency Scanning**: No TRON-related dependencies allowed
- **Network Isolation**: No TRON network access configured
- **Service Boundaries**: Clear separation from payment services

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
