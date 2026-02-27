# GUI Hardware Manager - Deployment & Integration Guide

**Service**: lucid-gui-hardware-manager  
**Port**: 8099  
**Status**: ✅ Production Ready  
**Date**: 2026-02-27  

---

## Overview

The `gui-hardware-manager` service is a FastAPI-based hardware wallet management service for the Lucid Electron GUI. It provides:

- **Hardware Wallet Integration**: Support for Ledger, Trezor, and KeepKey
- **Tor Integration**: Anonymous transaction routing through tor-proxy
- **Transaction Signing**: Secure transaction signing with hardware wallets
- **TRON Support**: Full TRON blockchain support with hardware wallets
- **REST API**: Complete REST API with proper error handling

---

## System Architecture

### Component Dependencies

```
┌─────────────────────────────────────┐
│   GUI Interfaces (Electron)         │
│ - user-interface:3001               │
│ - node-interface:3002               │
│ - admin-interface:8120              │
└──────────────────┬──────────────────┘
                   │ (HTTP Requests)
                   ▼
┌─────────────────────────────────────┐
│   gui-hardware-manager:8099         │
│ ✓ Distroless Python 3.11            │
│ ✓ Async/Await Architecture          │
│ ✓ Full Tor Integration              │
└──┬──────────┬────────────┬──────────┘
   │          │            │
   ▼          ▼            ▼
┌──────┐ ┌────────┐ ┌───────────────┐
│ Tor  │ │MongoDB │ │ Redis & Cache │
│Proxy │ │ lucid  │ │   Service     │
└──────┘ └────────┘ └───────────────┘
```

### Service Communication Flow

```
1. Electron GUI Issues Hardware Operation Request
   ↓
2. gui-hardware-manager Receives Request
   ├─ Validates Request (CORS, Rate Limiting, Auth)
   ├─ Routes to Appropriate Handler
   └─ Initializes Hardware Device Connection
   ↓
3. Hardware Device Communication
   ├─ For USB Devices: Direct USB Communication
   ├─ For Signing: Waits for User Confirmation on Device
   └─ For Tor Routes: Uses tor-proxy Service
   ↓
4. Response Returned to Electron GUI
   └─ With Anonymity Metadata (if Tor used)
```

---

## Configuration

### Environment Files

The service uses a tiered environment configuration approach:

```
configs/environment/
├── .env.secrets              (Database passwords, JWT keys)
├── .env.core                 (Core service configuration)
├── .env.application          (Application settings)
├── .env.foundation           (Foundation layer settings)
├── .env.gui                  (GUI services configuration)
└── .env.gui-hardware-manager (Hardware manager specific)
```

### Critical Environment Variables

```bash
# Service Configuration
SERVICE_NAME=lucid-gui-hardware-manager
PORT=8099                          # Must match docker-compose port
HOST=0.0.0.0                       # Listen on all interfaces

# Logging
LOG_LEVEL=INFO                     # DEBUG/INFO/WARNING/ERROR
DEBUG=false                        # Enable debug mode

# Environment
LUCID_ENV=production               # production/staging/development
LUCID_PLATFORM=arm64               # Target platform

# Database Access
MONGODB_URL=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URL=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0

# Integration Services
API_GATEWAY_URL=http://api-gateway:8080
AUTH_SERVICE_URL=http://lucid-auth-service:8089
GUI_API_BRIDGE_URL=http://gui-api-bridge:8102
TOR_PROXY_URL=http://tor-proxy:9051              # ✅ NEW

# Hardware Wallet Configuration
HARDWARE_WALLET_ENABLED=true
LEDGER_ENABLED=true
LEDGER_VENDOR_ID=0x2c97
TREZOR_ENABLED=true
KEEPKEY_ENABLED=true
TRON_WALLET_SUPPORT=true
TRON_RPC_URL=https://api.trongrid.io

# CORS Configuration  # ✅ NEW
CORS_ENABLED=true
CORS_ORIGINS=http://user-interface:3001,http://node-interface:3002,http://admin-interface:8120,http://localhost:3001,http://localhost:3002,http://localhost:8120
CORS_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_HEADERS=*
CORS_ALLOW_CREDENTIALS=true

# Rate Limiting  # ✅ NEW
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_BURST=200

# Security
JWT_SECRET_KEY=${JWT_SECRET_KEY}  # From .env.secrets
```

---

## Docker Compose Configuration

### Service Definition

```yaml
gui-hardware-manager:
  image: pickme/lucid-gui-hardware-manager:latest-arm64
  container_name: lucid-gui-hardware-manager
  restart: unless-stopped
  
  # Environment Configuration
  env_file:
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.core
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.application
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.gui
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.gui-hardware-manager
  
  ports:
    - "8099:8099"
  
  # Service Dependencies (startup order)
  depends_on:
    tor-proxy:
      condition: service_started
    lucid-mongodb:
      condition: service_healthy
    lucid-redis:
      condition: service_healthy
    lucid-auth-service:
      condition: service_healthy
    api-gateway:
      condition: service_healthy
    gui-api-bridge:
      condition: service_healthy
  
  # Network Configuration
  networks:
    - lucid-pi-network         # Access tor-proxy and core services
    - lucid-gui-network        # Access GUI interfaces
  
  # Volume Mounts
  volumes:
    - /mnt/myssd/Lucid/Lucid/logs/gui-hardware-manager:/app/logs
    - /mnt/myssd/Lucid/Lucid/data/gui-hardware-manager:/app/data
    - /run/usb-devices:/run/usb:rw
  
  # Security Configuration
  user: "65532:65532"          # Unprivileged user
  read_only: true              # Read-only filesystem
  security_opt:
    - no-new-privileges:true
    - seccomp:unconfined
  cap_drop:
    - ALL
  cap_add:
    - NET_BIND_SERVICE
  
  tmpfs:
    - /tmp:noexec,nosuid,size=100m
  
  # Health Check
  healthcheck:
    test: ["CMD", "python3", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', 8099)); s.close(); exit(0 if result == 0 else 1)"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] All environment files created and populated
  - [ ] `.env.secrets` with database passwords
  - [ ] `.env.gui-hardware-manager` with service-specific settings
  
- [ ] Docker image available
  - [ ] `pickme/lucid-gui-hardware-manager:latest-arm64`
  - [ ] Image verified on target platform

- [ ] Required services running
  - [ ] tor-proxy service started
  - [ ] lucid-mongodb service healthy
  - [ ] lucid-redis service healthy
  - [ ] lucid-auth-service service healthy
  - [ ] api-gateway service healthy
  - [ ] gui-api-bridge service healthy

- [ ] Network configuration
  - [ ] lucid-pi-network exists
  - [ ] lucid-gui-network exists

- [ ] Storage paths
  - [ ] `/mnt/myssd/Lucid/Lucid/logs/gui-hardware-manager/` writable
  - [ ] `/mnt/myssd/Lucid/Lucid/data/gui-hardware-manager/` writable

### Deployment Steps

```bash
# 1. Navigate to project directory
cd /mnt/myssd/Lucid/Lucid

# 2. Validate docker-compose configuration
docker-compose -f configs/docker/docker-compose.gui-integration.yml config --quiet

# 3. Start the service
docker-compose -f configs/docker/docker-compose.gui-integration.yml up -d gui-hardware-manager

# 4. Monitor startup logs
docker logs -f lucid-gui-hardware-manager

# 5. Verify service health
curl http://localhost:8099/health

# 6. Check detailed status
curl http://localhost:8099/api/v1/health/detailed

# 7. Test Tor integration
curl http://localhost:8099/api/v1/tor/status
```

### Post-Deployment Verification

```bash
# 1. Service is running
docker ps | grep gui-hardware-manager

# 2. Service is healthy
docker inspect lucid-gui-hardware-manager | grep -A 5 '"Health"'

# 3. Service logs contain no errors
docker logs lucid-gui-hardware-manager | grep -i error

# 4. Service is responding
curl -v http://localhost:8099/health

# 5. Tor integration is working
curl http://localhost:8099/api/v1/tor/status | jq '.status'

# 6. API endpoints are accessible
curl http://localhost:8099/api/v1/hardware/status

# 7. Rate limiting is active
for i in {1..5}; do curl -s http://localhost:8099/api/v1/health | jq '.status'; done
```

---

## API Endpoints

### Health & Status

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Basic health check |
| GET | `/api/v1/health` | Service health status |
| GET | `/api/v1/health/detailed` | Comprehensive component status |
| GET | `/` | Root service info |
| GET | `/version` | Version information |

### Hardware Devices

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/hardware/devices` | List connected devices |
| GET | `/api/v1/hardware/devices/{device_id}` | Get device info |
| GET | `/api/v1/hardware/status` | Hardware subsystem status |
| POST | `/api/v1/hardware/devices/{device_id}/disconnect` | Disconnect device |

### Hardware Wallets

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/hardware/wallets` | List wallets |
| POST | `/api/v1/hardware/wallets` | Connect wallet |
| GET | `/api/v1/hardware/wallets/{wallet_id}` | Get wallet info |
| DELETE | `/api/v1/hardware/wallets/{wallet_id}` | Disconnect wallet |

### Transaction Signing

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/hardware/sign` | Request signature |
| GET | `/api/v1/hardware/sign/{signature_id}` | Get signature status |
| POST | `/api/v1/hardware/sign/{signature_id}/approve` | Approve signing |
| POST | `/api/v1/hardware/sign/{signature_id}/reject` | Reject signing |

### Tor Integration ✅ NEW

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/tor/status` | Tor service status |
| GET | `/api/v1/tor/circuit/info` | Current circuit information |
| POST | `/api/v1/tor/circuit/rotate` | Rotate circuit (new exit node) |
| POST | `/api/v1/tor/transaction/route` | Route transaction through Tor |
| GET | `/api/v1/tor/anonymity/verify` | Verify anonymity status |
| GET | `/api/v1/tor/exit-ip` | Get current exit node IP |

---

## Troubleshooting

### Service Fails to Start

**Issue**: Container exits immediately  
**Diagnosis**:
```bash
docker logs lucid-gui-hardware-manager
```

**Common Causes**:
1. Missing environment files
   - Solution: Create all `.env.*` files in `configs/environment/`

2. Database connection failure
   - Solution: Verify MongoDB and Redis are running and healthy

3. Tor proxy unavailable
   - Solution: Service starts without Tor (non-blocking), check logs

4. Invalid environment variables
   - Solution: Review .env files for syntax errors

### Health Check Failing

**Issue**: Container marked as unhealthy  
**Diagnosis**:
```bash
docker ps --filter name=gui-hardware-manager --format "{{.Status}}"
```

**Solution**:
```bash
# Check service response time
time curl http://localhost:8099/health

# Increase health check start period in docker-compose
# Adjust: start_period: 120s  (increase from 60s)
```

### Tor Integration Not Working

**Issue**: Tor endpoints return 503 Service Unavailable  
**Diagnosis**:
```bash
# Check Tor proxy is running
docker ps | grep tor-proxy

# Check Tor integration logs
docker logs lucid-gui-hardware-manager | grep -i tor

# Test Tor proxy directly
curl http://localhost:9051/health
```

**Solution**:
1. Ensure tor-proxy service is running
2. Verify network connectivity between services
3. Check TOR_PROXY_URL configuration

### USB Device Not Detected

**Issue**: Hardware devices not showing up  
**Diagnosis**:
```bash
# Check USB mount
docker exec lucid-gui-hardware-manager ls -la /run/usb

# Check container capabilities
docker inspect lucid-gui-hardware-manager | grep -i cap
```

**Solution**:
1. Verify USB host devices are accessible
2. Check USB permissions on host
3. Restart docker daemon if needed

---

## Performance Tuning

### Rate Limiting Configuration

```bash
# Conservative (for API Gateway)
RATE_LIMIT_REQUESTS=50
RATE_LIMIT_BURST=100

# Standard (default)
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_BURST=200

# Aggressive (for GUI services)
RATE_LIMIT_REQUESTS=200
RATE_LIMIT_BURST=400
```

### CORS Configuration

```bash
# Production (restrictive)
CORS_ORIGINS=http://user-interface:3001,http://node-interface:3002,http://admin-interface:8120

# Development (permissive)
CORS_ORIGINS=*
CORS_ALLOW_CREDENTIALS=true
```

### Logging Configuration

```bash
# Production
LOG_LEVEL=INFO
DEBUG=false

# Staging
LOG_LEVEL=DEBUG
DEBUG=false

# Development
LOG_LEVEL=DEBUG
DEBUG=true
```

---

## Monitoring

### Key Metrics to Monitor

1. **Service Health**
   - Health check endpoint response time
   - Container uptime
   - Restart count

2. **Tor Integration**
   - Circuit rotation frequency
   - Exit node changes
   - Anonymity verification status

3. **Hardware Operations**
   - Device connection count
   - Wallet operation success rate
   - Signing request processing time

4. **API Performance**
   - Request latency
   - Rate limit hits
   - Error rates

### Log Monitoring

```bash
# Real-time logs
docker logs -f lucid-gui-hardware-manager

# Filter by log level
docker logs lucid-gui-hardware-manager | grep ERROR

# Filter Tor-related logs
docker logs lucid-gui-hardware-manager | grep -i tor

# Check startup sequence
docker logs lucid-gui-hardware-manager | grep "Starting\|Initialized\|ready"
```

---

## Security Considerations

### Authentication & Authorization

- ✅ JWT token validation for protected endpoints
- ✅ Role-based access control (from Auth Service)
- ✅ Secure token storage in header

### Network Security

- ✅ CORS properly configured
- ✅ All communication over HTTP (internal network)
- ✅ Tor integration for anonymous transactions
- ✅ Rate limiting to prevent abuse

### Data Security

- ✅ No credentials in logs
- ✅ Hardware wallet keys never leave device
- ✅ Distroless base image (minimal attack surface)
- ✅ Read-only filesystem
- ✅ Unprivileged user (65532:65532)

### Secrets Management

- ✅ JWT_SECRET_KEY from .env.secrets
- ✅ Database passwords from .env.secrets
- ✅ No hardcoded secrets in code
- ✅ Environment-variable driven configuration

---

## Integration Points

### With GUI Services

```
gui-hardware-manager
├─ Provides: Hardware wallet operations
└─ Consumed by: user-interface, node-interface, admin-interface
```

### With Backend Services

```
gui-hardware-manager
├─ Connects to: api-gateway (8080)
├─ Connects to: lucid-auth-service (8089)
├─ Connects to: gui-api-bridge (8102)
├─ Connects to: tor-proxy (9051)
├─ Connects to: lucid-mongodb (27017)
└─ Connects to: lucid-redis (6379)
```

### With Tor Network

```
gui-hardware-manager
└─ tor-proxy
    ├─ Manages Tor circuits
    ├─ Provides anonymity
    └─ Routes transactions anonymously
```

---

## Updates & Maintenance

### Updating Configuration

```bash
# Update environment variables
vim configs/environment/.env.gui-hardware-manager

# Restart service to apply changes
docker-compose -f configs/docker/docker-compose.gui-integration.yml restart gui-hardware-manager

# Verify changes applied
curl http://localhost:8099/api/v1/health/detailed | jq '.configuration'
```

### Updating Service Image

```bash
# Pull latest image
docker pull pickme/lucid-gui-hardware-manager:latest-arm64

# Restart container (automatic with `restart: unless-stopped`)
docker-compose -f configs/docker/docker-compose.gui-integration.yml up -d gui-hardware-manager

# Monitor logs during startup
docker logs -f lucid-gui-hardware-manager
```

### Cleaning Up

```bash
# Remove old images
docker image prune -a --filter "label=com.lucid.service=gui-hardware-manager"

# View logs before cleanup
docker logs lucid-gui-hardware-manager > /tmp/gui-hardware-manager-$(date +%s).log

# Complete cleanup
docker-compose -f configs/docker/docker-compose.gui-integration.yml down
```

---

## Testing

### Unit Tests

```bash
# Run tests in container
docker exec lucid-gui-hardware-manager python3 -m pytest tests/ -v

# Run with coverage
docker exec lucid-gui-hardware-manager python3 -m pytest tests/ --cov=gui_hardware_manager
```

### Integration Tests

```bash
# Run integration test script
bash gui-hardware-manager/test_tor_integration.sh

# Manual endpoint testing
curl -v http://localhost:8099/api/v1/health
curl -v http://localhost:8099/api/v1/tor/status
curl -v http://localhost:8099/api/v1/hardware/devices
```

---

## Support & Resources

### Log Files

- Container logs: `docker logs lucid-gui-hardware-manager`
- Application logs: `/mnt/myssd/Lucid/Lucid/logs/gui-hardware-manager/`
- Docker logs: `/var/lib/docker/containers/*/*/logs/`

### Configuration Files

- Service config: `gui-hardware-manager/gui-hardware-manager/config.py`
- Docker config: `configs/docker/docker-compose.gui-integration.yml`
- Environment: `configs/environment/.env.gui-hardware-manager`

### Documentation

- Architecture: `00-master-architecture/01-MASTER_BUILD_PLAN.md`
- Build Guide: `00-master-architecture/02-CLUSTER_*_BUILD_GUIDE.md`
- Audit Report: `gui-hardware-manager/AUDIT_AND_FIXES.md`

---

## Quick Reference

### Essential Commands

```bash
# Start service
docker-compose -f configs/docker/docker-compose.gui-integration.yml up -d gui-hardware-manager

# Check status
docker ps | grep gui-hardware-manager

# View logs
docker logs lucid-gui-hardware-manager

# Test health
curl http://localhost:8099/health

# Test Tor
curl http://localhost:8099/api/v1/tor/status

# Restart
docker-compose -f configs/docker/docker-compose.gui-integration.yml restart gui-hardware-manager

# Stop
docker-compose -f configs/docker/docker-compose.gui-integration.yml stop gui-hardware-manager

# Remove
docker-compose -f configs/docker/docker-compose.gui-integration.yml down
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2026-02-27  
**Service**: lucid-gui-hardware-manager  
**Status**: ✅ Production Ready
