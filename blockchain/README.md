# Lucid Blockchain Service

## Overview

The Lucid Blockchain Service provides the core blockchain functionality for the Lucid RDP system. It implements a custom EVM-compatible blockchain with PoOT (Proof of Operational Time) consensus, session anchoring, block management, and data chain services.

**Service Name**: `lucid-blockchain-api`  
**Cluster ID**: 02-BLOCKCHAIN-CORE  
**Port**: 8084 (Engine), 8085 (Anchoring), 8086 (Manager), 8087 (Data)  
**Phase**: Phase 2 Core Services  
**Status**: Production Ready ✅

---

## Features

### Core Blockchain
- ✅ **Custom EVM-Compatible Blockchain** - Custom blockchain implementation
- ✅ **PoOT Consensus** - Proof of Operational Time consensus algorithm
- ✅ **Session Anchoring** - Blockchain anchoring of session data
- ✅ **Block Management** - Efficient block creation and management
- ✅ **Data Chain** - Separate data chain for session chunks
- ✅ **Merkle Tree Support** - Merkle tree implementation for data integrity

### Security Features
- ✅ **Cryptographic Security** - Strong cryptographic primitives
- ✅ **Data Integrity** - Merkle tree verification
- ✅ **Audit Trail** - Immutable blockchain record
- ✅ **Distributed Storage** - Distributed data storage

### Infrastructure
- ✅ **Distroless Container** - Minimal attack surface
- ✅ **Multi-Service Architecture** - Separate services for different functions
- ✅ **Health Checks** - Built-in health monitoring
- ✅ **Horizontal Scaling** - Stateless design

---

## Service Components

### 1. Blockchain Engine (Port 8084)
Core blockchain engine handling:
- Block creation and validation
- Transaction processing
- Consensus algorithm execution
- Chain state management

### 2. Session Anchoring Service (Port 8085)
Handles blockchain anchoring of:
- Session metadata
- Session chunks
- Merkle tree roots
- Verification proofs

### 3. Block Manager Service (Port 8086)
Manages:
- Block storage
- Block retrieval
- Block validation
- Chain synchronization

### 4. Data Chain Service (Port 8087)
Handles:
- Data chunk storage
- Merkle tree construction
- Data retrieval
- Integrity verification

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- MongoDB 7.0+ (for metadata)
- Redis 7.0+ (for caching)
- Python 3.11+ (for local development)

### Using Docker Compose (Recommended)

```bash
# 1. Navigate to blockchain directory
cd Lucid/blockchain

# 2. Start all blockchain services
docker-compose up -d

# 3. Verify health
curl http://localhost:8084/health  # Engine
curl http://localhost:8085/health  # Anchoring
curl http://localhost:8086/health  # Manager
curl http://localhost:8087/health  # Data Chain
```

### Using Docker

```bash
# Build and run Blockchain Engine
docker build -f Dockerfile.engine -t lucid-blockchain-engine:latest .
docker run -d --name lucid-blockchain-engine -p 8084:8084 \
  -e MONGODB_URI=mongodb://mongodb:27017/lucid_blockchain \
  lucid-blockchain-engine:latest

# Build and run Session Anchoring
docker build -f Dockerfile.anchoring -t lucid-session-anchoring:latest .
docker run -d --name lucid-session-anchoring -p 8085:8085 \
  -e BLOCKCHAIN_ENGINE_URL=http://lucid-blockchain-engine:8084 \
  lucid-session-anchoring:latest

# Similar for Block Manager and Data Chain services
```

### Local Development

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run blockchain engine
python -m api.app.main

# Or with uvicorn
uvicorn api.app.main:app --host 0.0.0.0 --port 8084 --reload
```

---

## API Endpoints

### Blockchain Engine Endpoints (Port 8084)

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| POST | `/api/v1/blockchain/blocks` | Create new block | Internal |
| GET | `/api/v1/blockchain/blocks` | List blocks | JWT Token |
| GET | `/api/v1/blockchain/blocks/{block_id}` | Get block details | JWT Token |
| POST | `/api/v1/blockchain/transactions` | Submit transaction | JWT Token |
| GET | `/api/v1/blockchain/transactions/{tx_id}` | Get transaction | JWT Token |
| GET | `/api/v1/blockchain/status` | Get blockchain status | JWT Token |

### Session Anchoring Endpoints (Port 8085)

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| POST | `/api/v1/anchoring/anchor` | Anchor session data | JWT Token |
| GET | `/api/v1/anchoring/verify/{proof_id}` | Verify proof | JWT Token |
| GET | `/api/v1/anchoring/session/{session_id}` | Get session anchor | JWT Token |

### Block Manager Endpoints (Port 8086)

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/api/v1/blocks` | List blocks | JWT Token |
| GET | `/api/v1/blocks/{block_id}` | Get block | JWT Token |
| POST | `/api/v1/blocks/validate` | Validate block | Internal |

### Data Chain Endpoints (Port 8087)

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| POST | `/api/v1/data/store` | Store data chunk | JWT Token |
| GET | `/api/v1/data/retrieve/{chunk_id}` | Retrieve chunk | JWT Token |
| POST | `/api/v1/data/merkle` | Create merkle tree | JWT Token |
| GET | `/api/v1/data/verify/{proof_id}` | Verify proof | JWT Token |

### Health & Meta Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/health` | Service health check | None |
| GET | `/metrics` | Prometheus metrics | None |

---

## Configuration

### Environment Variables

**Blockchain Engine:**
- `MONGODB_URI` - MongoDB connection string
- `BLOCKCHAIN_NETWORK` - Network name (default: lucid_blocks)
- `CONSENSUS_ALGORITHM` - Consensus algorithm (default: PoOT)
- `LOG_LEVEL` - Logging level (default: INFO)

**Session Anchoring:**
- `BLOCKCHAIN_ENGINE_URL` - Blockchain engine URL
- `ANCHORING_BATCH_SIZE` - Batch size (default: 10)
- `ANCHORING_TIMEOUT` - Timeout seconds (default: 60)

**Block Manager:**
- `BLOCKCHAIN_ENGINE_URL` - Blockchain engine URL
- `BLOCK_STORAGE_PATH` - Storage path (default: /data/blocks)

**Data Chain:**
- `CHUNK_STORAGE_PATH` - Chunk storage path (default: /data/chunks)
- `MERKLE_STORAGE_PATH` - Merkle tree storage path (default: /data/merkle)

---

## Architecture

### Components

```
blockchain/
├── api/              # Blockchain API
│   └── app/          # Application entry points
├── core/             # Core blockchain logic
│   ├── consensus/    # Consensus algorithms
│   ├── blocks/       # Block management
│   └── transactions/ # Transaction processing
├── anchoring/        # Session anchoring service
├── manager/          # Block manager service
├── data/             # Data chain service
├── utils/            # Utility functions
├── config/           # Configuration files
├── Dockerfile.engine
├── Dockerfile.anchoring
├── Dockerfile.manager
├── Dockerfile.data
├── requirements.txt
└── README.md
```

### Consensus Algorithm: PoOT (Proof of Operational Time)

PoOT is designed specifically for the Lucid RDP system:
- Rewards nodes for operational time
- Configurable node pool (max 100 nodes)
- Payout threshold: 10 USDT
- Automatic payout processing
- Work credit system

---

## Development

### Project Structure

```
blockchain/
├── api/                 # API layer
│   ├── app/            # FastAPI application
│   ├── routes/         # API routes
│   ├── middleware/     # Middleware
│   └── models/         # Data models
├── core/               # Core blockchain
│   ├── consensus/      # Consensus implementation
│   ├── blocks/         # Block management
│   └── transactions/   # Transaction processing
├── anchoring/          # Anchoring service
├── manager/            # Manager service
├── data/               # Data chain service
├── utils/              # Utilities
└── config/             # Configuration
```

### Building Containers

```bash
# Build all services
docker build -f Dockerfile.engine -t lucid-blockchain-engine:latest .
docker build -f Dockerfile.anchoring -t lucid-session-anchoring:latest .
docker build -f Dockerfile.manager -t lucid-block-manager:latest .
docker build -f Dockerfile.data -t lucid-data-chain:latest .
```

### Testing

```bash
# Run blockchain tests
pytest tests/

# Run specific service tests
pytest tests/test_engine.py
pytest tests/test_anchoring.py
```

---

## Deployment

### Production Deployment

Deploy using Docker Compose:

```yaml
services:
  blockchain-engine:
    image: lucid-blockchain-engine:latest
    ports:
      - "8084:8084"
    environment:
      - MONGODB_URI=mongodb://mongodb:27017/lucid_blockchain
    networks:
      - lucid-network

  session-anchoring:
    image: lucid-session-anchoring:latest
    ports:
      - "8085:8085"
    environment:
      - BLOCKCHAIN_ENGINE_URL=http://blockchain-engine:8084
    networks:
      - lucid-network
```

---

## Monitoring

### Health Checks

```bash
# Check all services
curl http://localhost:8084/health  # Engine
curl http://localhost:8085/health  # Anchoring
curl http://localhost:8086/health  # Manager
curl http://localhost:8087/health  # Data Chain
```

### Metrics

Prometheus metrics available at `/metrics` for each service:
- Block creation rate
- Transaction throughput
- Anchoring success rate
- Storage utilization

---

## Troubleshooting

### Common Issues

**Service won't start:**
- Check MongoDB connection
- Verify network connectivity
- Review environment variables

**Blockchain not syncing:**
- Check consensus configuration
- Verify node connectivity
- Review logs for errors

**Anchoring failures:**
- Verify blockchain engine is running
- Check batch size configuration
- Review timeout settings

---

## License

Proprietary - Lucid RDP Development Team

---

## Support

For issues and questions:
- GitHub Issues: [link]
- Email: dev@lucid-rdp.onion
- Documentation: [link]
