# API Gateway Setup Guide

**File**: 03-api-gateway/SETUP.md  
**Purpose**: Quick setup and deployment instructions  
**Build Host**: Windows 11 console  
**Target Host**: Raspberry Pi (via SSH)

## Initial Setup Complete

The following files and directories have been created according to the planning documents:

### ✅ Core Files Created (First 5)

1. **Dockerfile** - Distroless multi-stage build for security
2. **docker-compose.yml** - Complete Docker Compose configuration
3. **requirements.txt** - Python dependencies for the API
4. **api/app/main.py** - FastAPI application entry point
5. **api/app/config.py** - Centralized configuration management

### ✅ Directory Structure

```
03-api-gateway/
├── Dockerfile                    ✅ Distroless container build
├── docker-compose.yml           ✅ Docker Compose config
├── requirements.txt             ✅ Python dependencies
├── env.template                 ✅ Environment template
├── README.md                    ✅ Project documentation
├── SETUP.md                     ✅ This file
├── .gitignore                   ✅ Git ignore rules
│
├── api/
│   └── app/
│       ├── main.py              ✅ Application entry point
│       ├── config.py            ✅ Configuration
│       ├── __init__.py          ✅ Package init
│       │
│       ├── middleware/          ✅ Custom middleware
│       │   ├── __init__.py
│       │   ├── auth.py          ✅ Authentication
│       │   ├── rate_limit.py    ✅ Rate limiting
│       │   ├── logging.py       ✅ Request logging
│       │   └── cors.py          ✅ CORS config
│       │
│       ├── routers/             ✅ API route handlers
│       │   ├── __init__.py
│       │   ├── meta.py          ✅ Meta endpoints
│       │   ├── auth.py          ✅ Authentication
│       │   ├── users.py         ✅ User management
│       │   ├── sessions.py      ✅ Session management
│       │   ├── manifests.py     ✅ Manifest ops
│       │   ├── trust.py         ✅ Trust policies
│       │   ├── chain.py         ✅ Blockchain proxy
│       │   └── wallets.py       ✅ TRON wallet proxy
│       │
│       ├── models/              ✅ Data models
│       │   ├── __init__.py
│       │   └── common.py        ✅ Common models
│       │
│       ├── database/            ✅ Database layer
│       │   ├── __init__.py
│       │   └── connection.py    ✅ DB connections
│       │
│       └── utils/               ✅ Utilities
│           ├── __init__.py
│           └── logging.py       ✅ Logging setup
│
├── scripts/                     ✅ Deployment scripts
│   ├── build.sh                 ✅ Build script
│   └── deploy.sh                ✅ Deployment script
│
├── certs/                       ✅ SSL certificates directory
│   └── .gitkeep
│
├── logs/                        ✅ Application logs directory
│   └── .gitkeep
│
├── gateway/                     ✅ Gateway config directory
│   └── .gitkeep
│
└── database/                    ✅ DB init scripts directory
    └── .gitkeep
```

## Architecture Notes

### 🔗 Service Connections

**lucid_blocks** (On-Chain Blockchain System)
- Purpose: Main blockchain for session data, manifests, and consensus
- Connection: `BLOCKCHAIN_CORE_URL=http://lucid-blocks:8084`
- Used for: Session anchoring, manifest storage, blockchain queries

**TRON** (Isolated Payment Service)
- Purpose: Payment processing for USDT/TRX transactions
- Connection: `TRON_PAYMENT_URL=http://tron-payment:8087`
- Status: **ISOLATED** - NOT part of lucid_blocks
- Used for: Wallet operations, payment transactions

### 🔒 Distroless Container Benefits

- **Minimal attack surface**: No shell, package manager, or unnecessary tools
- **Security**: Runs as non-root user (UID 65532)
- **Size**: Smaller image size
- **Base**: `gcr.io/distroless/python3-debian12`

## Quick Start

### 1. Configure Environment

```bash
# Copy environment template
cp env.template .env

# Edit .env with your values
# REQUIRED: Set JWT_SECRET_KEY, MONGO_PASSWORD, REDIS_PASSWORD
```

### 2. Build Container

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Build distroless container
./scripts/build.sh
```

### 3. Deploy Services

```bash
# Deploy with Docker Compose
./scripts/deploy.sh
```

### 4. Verify Deployment

```bash
# Check health
curl http://localhost:8080/api/v1/meta/health

# Check version
curl http://localhost:8080/api/v1/meta/version

# View logs
docker-compose logs -f api-gateway
```

## Windows 11 to Raspberry Pi Deployment

### Prerequisites

- PowerShell 7+ on Windows 11
- SSH access to Raspberry Pi
- Docker installed on Raspberry Pi

### Deployment Process

```powershell
# From Windows 11 (PowerShell)

# 1. Build for ARM architecture
$env:BUILDPLATFORM="linux/arm64"
./scripts/build.sh

# 2. Save image
docker save lucid-api-gateway:latest | gzip > api-gateway.tar.gz

# 3. Copy to Raspberry Pi
scp api-gateway.tar.gz pi@raspberrypi.local:~/

# 4. SSH to Pi and load image
ssh pi@raspberrypi.local
docker load < api-gateway.tar.gz
cd ~/lucid/03-api-gateway
docker-compose up -d
```

## Development Workflow

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run locally (without Docker)
cd api
export $(cat ../.env | xargs)  # Load env vars
python -m app.main
```

### Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Run tests
pytest api/tests/

# With coverage
pytest --cov=api api/tests/
```

## Next Steps

### To Complete Implementation

1. **Implement Authentication** (`api/app/middleware/auth.py`)
   - JWT token validation
   - Magic link authentication
   - TOTP verification

2. **Implement Rate Limiting** (`api/app/middleware/rate_limit.py`)
   - Redis-based rate limiting
   - Tiered limits by endpoint type
   - DDoS protection

3. **Implement Routers** (all files in `api/app/routers/`)
   - Complete endpoint implementations
   - Request/response validation
   - Error handling

4. **Add Database Repositories** (`api/app/database/repositories/`)
   - User repository
   - Session repository
   - Auth token repository

5. **Add Services** (`api/app/services/`)
   - Authentication service
   - User service
   - Session service
   - Proxy service

6. **Add Tests** (`api/tests/`)
   - Unit tests
   - Integration tests
   - End-to-end tests

## Troubleshooting

### Container Build Fails

```bash
# Check Docker version
docker --version  # Should be 24.0+

# Clean build
docker system prune -a
./scripts/build.sh
```

### Database Connection Issues

```bash
# Check MongoDB
docker-compose logs mongodb

# Check Redis
docker-compose logs redis

# Verify environment variables
docker-compose config
```

### Port Conflicts

```bash
# Check ports in use (Windows PowerShell)
netstat -ano | findstr :8080
netstat -ano | findstr :8081

# Change ports in .env if needed
HTTP_PORT=8090
HTTPS_PORT=8091
```

## Support & Documentation

- **Planning Docs**: `plan/API_plans/01-api-gateway-cluster/`
- **GitHub**: [HamiGames/Lucid](https://github.com/HamiGames/Lucid)
- **Issues**: GitHub Issues

---

**Status**: ✅ Initial structure complete, ready for implementation  
**Created**: 2025-01-14  
**Version**: 1.0.0

