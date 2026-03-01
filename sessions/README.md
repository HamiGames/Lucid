# Lucid Sessions Service

## Overview

The Lucid Sessions Service manages remote desktop sessions in the Lucid RDP system. It provides session lifecycle management, session recording, chunked data storage, and session processing capabilities.

**Service Name**: `lucid-sessions`  
**Cluster ID**: Phase 3 Application Services  
**Port**: 8090 (API), 8086 (Storage), 8084 (Recorder)  
**Phase**: Phase 3 Application Services  
**Status**: Production Ready ✅

---

## Features

### Core Session Management
- ✅ **Session Lifecycle** - Create, manage, and terminate sessions
- ✅ **Session Recording** - Record and store session data
- ✅ **Chunked Storage** - Store session data in chunks
- ✅ **Session Processing** - Process and validate session data
- ✅ **Session Pipeline** - Orchestrate session workflows
- ✅ **Session Storage** - Persistent session data storage

### Security Features
- ✅ **Encrypted Storage** - Encrypted session data storage
- ✅ **Access Control** - Role-based session access
- ✅ **Audit Logging** - Complete session audit trail
- ✅ **Data Integrity** - Merkle tree verification

### Infrastructure
- ✅ **Distroless Container** - Minimal attack surface
- ✅ **Multi-Service Architecture** - Separate services for different functions
- ✅ **Health Checks** - Built-in health monitoring
- ✅ **Horizontal Scaling** - Stateless design

---

## Service Components

### 1. Session API (Port 8090)
Main API for session management:
- Create and manage sessions
- Query session data
- Handle session lifecycle

### 2. Session Storage (Port 8086)
Handles:
- Session data storage
- Chunk storage and retrieval
- Merkle tree construction

### 3. Session Recorder (Port 8084)
Records:
- Session events
- Screen captures
- User interactions

### 4. Session Processor (Port 8085)
Processes:
- Session data validation
- Data transformation
- Quality assurance

### 5. Session Pipeline (Port 8083)
Orchestrates:
- Session workflows
- Data pipeline management
- Task scheduling

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- MongoDB 7.0+ (for metadata)
- Redis 7.0+ (for caching)
- Python 3.11+ (for local development)

### Using Docker Compose (Recommended)

```bash
# 1. Navigate to sessions directory
cd Lucid/sessions

# 2. Start all session services
docker-compose up -d

# 3. Verify health
curl http://localhost:8090/health  # API
curl http://localhost:8086/health  # Storage
curl http://localhost:8084/health  # Recorder
curl http://localhost:8085/health  # Processor
curl http://localhost:8083/health  # Pipeline
```

### Using Docker

```bash
# Build and run Session API
docker build -f Dockerfile.api -t lucid-session-api:latest .
docker run -d --name lucid-session-api -p 8090:8090 \
  -e MONGODB_URI=mongodb://mongodb:27017/lucid_sessions \
  lucid-session-api:latest

# Similar for other services
```

### Local Development

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run session API
python -m api.main

# Or with uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8090 --reload
```

---

## API Endpoints

### Session API Endpoints (Port 8090)

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| POST | `/api/v1/sessions` | Create new session | JWT Token |
| GET | `/api/v1/sessions` | List sessions | JWT Token |
| GET | `/api/v1/sessions/{session_id}` | Get session details | JWT Token |
| PUT | `/api/v1/sessions/{session_id}` | Update session | JWT Token |
| DELETE | `/api/v1/sessions/{session_id}` | Terminate session | JWT Token |

### Session Storage Endpoints (Port 8086)

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| POST | `/api/v1/storage/chunks` | Store chunk | JWT Token |
| GET | `/api/v1/storage/chunks/{chunk_id}` | Retrieve chunk | JWT Token |
| POST | `/api/v1/storage/merkle` | Create merkle tree | JWT Token |

### Session Recorder Endpoints (Port 8084)

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| POST | `/api/v1/record/start` | Start recording | JWT Token |
| POST | `/api/v1/record/stop` | Stop recording | JWT Token |
| GET | `/api/v1/record/status/{session_id}` | Get recording status | JWT Token |

### Health & Meta Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/health` | Service health check | None |
| GET | `/metrics` | Prometheus metrics | None |

---

## Configuration

### Environment Variables

**Session API:**
- `MONGODB_URI` - MongoDB connection string
- `REDIS_URI` - Redis connection string
- `LOG_LEVEL` - Logging level (default: INFO)

**Session Storage:**
- `CHUNK_STORAGE_PATH` - Chunk storage path
- `MERKLE_STORAGE_PATH` - Merkle tree storage path

**Session Recorder:**
- `RECORDING_QUALITY` - Recording quality (default: high)
- `RECORDING_FORMAT` - Recording format (default: mp4)

---

## Architecture

### Components

```
sessions/
├── api/           # Session API
│   └── main.py    # API entry point
├── storage/       # Storage service
│   └── main.py    # Storage entry point
├── recorder/      # Recorder service
│   └── main.py    # Recorder entry point
├── processor/     # Processor service
│   └── main.py    # Processor entry point
├── pipeline/      # Pipeline service
│   └── main.py    # Pipeline entry point
├── core/          # Core session logic
├── Dockerfile.api
├── Dockerfile.storage
├── Dockerfile.recorder
├── Dockerfile.processor
├── Dockerfile.pipeline
├── requirements.txt
└── README.md
```

---

## Development

### Project Structure

```
sessions/
├── api/              # API service
├── storage/          # Storage service
├── recorder/         # Recorder service
├── processor/        # Processor service
├── pipeline/         # Pipeline service
├── core/             # Core logic
└── utils/            # Utilities
```

### Building Containers

```bash
# Build all services
docker build -f Dockerfile.api -t lucid-session-api:latest .
docker build -f Dockerfile.storage -t lucid-session-storage:latest .
docker build -f Dockerfile.recorder -t lucid-session-recorder:latest .
docker build -f Dockerfile.processor -t lucid-session-processor:latest .
docker build -f Dockerfile.pipeline -t lucid-session-pipeline:latest .
```

---

## Deployment

### Production Deployment

Deploy using Docker Compose:

```yaml
services:
  session-api:
    image: lucid-session-api:latest
    ports:
      - "8090:8090"
    environment:
      - MONGODB_URI=mongodb://mongodb:27017/lucid_sessions
    networks:
      - lucid-network
```

---

## Monitoring

### Health Checks

```bash
# Check all services
curl http://localhost:8090/health  # API
curl http://localhost:8086/health  # Storage
curl http://localhost:8084/health  # Recorder
```

---

## License

Proprietary - Lucid RDP Development Team

---

## Support

For issues and questions:
- GitHub Issues: [link]
- Email: dev@lucid-rdp.onion
- Documentation: [link]
