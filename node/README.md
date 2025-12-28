# Lucid Node Management Service

## Overview

The Lucid Node Management Service manages the network node pool for the Lucid RDP system. It implements PoOT (Proof of Operational Time) consensus, node registration, work credits, and payout management.

**Service Name**: `node-management`  
**Container Name**: `node-management`  
**Image Name**: `pickme/lucid-node-management:latest-arm64`  
**Cluster ID**: Phase 3 Application Services  
**Port**: 8095  
**Phase**: Phase 3 Application Services  
**Status**: Production Ready ✅

---

## Features

### Core Node Management
- ✅ **Node Pool Management** - Manage network node pool (max 100 nodes)
- ✅ **PoOT Calculation** - Proof of Operational Time consensus
- ✅ **Node Registration** - Register and authenticate nodes
- ✅ **Work Credits** - Track node work credits
- ✅ **Payout Management** - Automatic payout processing (threshold: 10 USDT)
- ✅ **Node Monitoring** - Monitor node status and health

### Security Features
- ✅ **Node Authentication** - Authenticate node connections
- ✅ **Access Control** - Role-based node access
- ✅ **Audit Logging** - Complete node activity logging
- ✅ **Data Integrity** - Cryptographic verification

### Infrastructure
- ✅ **Distroless Container** - Minimal attack surface
- ✅ **Health Checks** - Built-in health monitoring
- ✅ **Horizontal Scaling** - Stateless design

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- MongoDB 7.0+ (for node data)
- Redis 7.0+ (for caching)
- Python 3.11+ (for local development)

### Using Docker Compose (Recommended)

```bash
# 1. Navigate to node directory
cd Lucid/node

# 2. Start node management service
docker-compose up -d

# 3. Verify health
curl http://localhost:8095/health
```

### Using Docker

```bash
# Build container (image name includes lucid- prefix)
docker build -t pickme/lucid-node-management:latest-arm64 -f Dockerfile.node-management .

# Run container (container name does NOT include lucid- prefix)
docker run -d \
  --name node-management \
  --network lucid-network \
  -p 8095:8095 \
  -e MONGODB_URI=mongodb://mongodb:27017/lucid_nodes \
  pickme/lucid-node-management:latest-arm64

# Check logs
docker logs node-management
```

### Local Development

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
export MONGODB_URI=mongodb://localhost:27017/lucid_nodes
export NODE_MANAGEMENT_PORT=8095

# 4. Run service
python main.py

# Or with uvicorn
uvicorn node.main:app --host 0.0.0.0 --port 8095 --reload
```

---

## API Endpoints

### Node Management Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| POST | `/api/v1/nodes` | Register node | JWT Token |
| GET | `/api/v1/nodes` | List nodes | JWT Token |
| GET | `/api/v1/nodes/{node_id}` | Get node details | JWT Token |
| PUT | `/api/v1/nodes/{node_id}` | Update node | JWT Token |
| DELETE | `/api/v1/nodes/{node_id}` | Deregister node | JWT Token |

### Pool Management Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/api/v1/pools` | List pools | JWT Token |
| GET | `/api/v1/pools/{pool_id}` | Get pool details | JWT Token |
| POST | `/api/v1/pools/{pool_id}/join` | Join pool | JWT Token |

### PoOT Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/api/v1/poot/{node_id}` | Get PoOT proof | JWT Token |
| POST | `/api/v1/poot/calculate` | Calculate PoOT | JWT Token |

### Payout Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/api/v1/payouts/{node_id}` | Get payout info | JWT Token |
| POST | `/api/v1/payouts/process` | Process payouts | Admin Token |

### Health & Meta Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/health` | Service health check | None |
| GET | `/metrics` | Prometheus metrics | None |

---

## Configuration

### Environment Variables

**Required:**
- `MONGODB_URI` - MongoDB connection string
- `NODE_MANAGEMENT_PORT` - Service port (default: 8095)

**Optional but Recommended:**
- `MAX_NODES_PER_POOL` - Max nodes per pool (default: 100)
- `PAYOUT_THRESHOLD_USDT` - Payout threshold in USDT (default: 10.0)
- `POOT_CALCULATION_INTERVAL` - PoOT calculation interval in seconds (default: 300)
- `PAYOUT_PROCESSING_INTERVAL` - Payout processing interval in seconds (default: 3600)
- `LOG_LEVEL` - Logging level (default: INFO)

---

## Architecture

### Components

```
node/
├── main.py                    # Application entry point
├── node_manager.py            # Node manager
├── poot_calculator.py         # PoOT calculator
├── payout_manager.py          # Payout manager
├── node_pool_manager.py       # Pool manager
├── database_adapter.py        # Database adapter
├── models.py                  # Data models
├── Dockerfile                 # Container definition
├── requirements.txt           # Python dependencies
└── README.md                 # This file
```

### PoOT Consensus Algorithm

Proof of Operational Time (PoOT):
- Rewards nodes for operational time
- Configurable node pool (max 100 nodes)
- Payout threshold: 10 USDT
- Automatic payout processing
- Work credit system

### Node Lifecycle

1. **Registration**: Node registers with the network
2. **Authentication**: Node authenticates and joins a pool
3. **Operational Time**: Node accrues operational time credits
4. **PoOT Calculation**: System calculates proof of operational time
5. **Payout**: When threshold is reached, automatic payout occurs
6. **Monitoring**: Continuous monitoring of node health and status

---

## Development

### Project Structure

```
node/
├── main.py                 # FastAPI application
├── node_manager.py         # Node management logic
├── poot_calculator.py      # PoOT consensus implementation
├── payout_manager.py       # Payout processing
├── node_pool_manager.py    # Pool management
├── database_adapter.py     # Database interface
└── models.py              # Data models
```

### Building the Container

```bash
# Build using distroless base image (image name includes lucid- prefix)
docker build -t pickme/lucid-node-management:latest-arm64 -f Dockerfile.node-management .

# Build for specific platform
docker buildx build --platform linux/arm64 -t pickme/lucid-node-management:latest-arm64 -f Dockerfile.node-management .
```

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=node --cov-report=html
```

---

## Deployment

### Production Deployment

Deploy using Docker Compose:

```yaml
# docker-compose.yml
services:
  node-management:
    image: lucid-node-management:latest
    ports:
      - "8095:8095"
    environment:
      - MONGODB_URI=mongodb://mongodb:27017/lucid_nodes
      - MAX_NODES_PER_POOL=100
      - PAYOUT_THRESHOLD_USDT=10.0
    networks:
      - lucid-network
```

---

## Monitoring

### Health Checks

```bash
# Basic health check
curl http://localhost:8095/health

# Expected response
{
  "status": "healthy",
  "service": "lucid-node-management",
  "version": "1.0.0"
}
```

### Metrics

Prometheus metrics available at `/metrics`:
- Node count
- Pool statistics
- Payout information
- PoOT calculations

---

## Troubleshooting

### Common Issues

**Service won't start:**
- Check MongoDB connection
- Verify environment variables
- Review network connectivity

**Node registration failures:**
- Verify node authentication
- Check pool capacity (max 100 nodes)
- Review database connectivity

**PoOT calculation errors:**
- Check node operational time tracking
- Verify database integrity
- Review calculation interval settings

---

## License

Proprietary - Lucid RDP Development Team

---

## Support

For issues and questions:
- GitHub Issues: [link]
- Email: dev@lucid-rdp.onion
- Documentation: [link]
