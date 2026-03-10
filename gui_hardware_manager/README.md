# GUI Hardware Manager Service - README

## Overview

The GUI Hardware Manager is a FastAPI-based service that manages hardware wallets (Ledger, Trezor, KeepKey) for the Lucid Electron GUI. It provides REST API endpoints for device discovery, wallet connection, and transaction signing.

## Features

- **Hardware Wallet Support**: Ledger, Trezor, KeepKey
- **TRON Blockchain**: Full support for TRON wallet operations
- **REST API**: Complete API for hardware wallet management
- **Secure**: JWT authentication, non-root user, hardened container
- **Monitoring**: Health checks and metrics endpoints
- **Rate Limiting**: Request rate limiting for protection
- **Cross-Container Integration**: Integrated with Lucid ecosystem

## Architecture

```
gui-hardware-manager/
├── main.py                 # FastAPI application
├── entrypoint.py          # Container entrypoint
├── config.py              # Configuration management
├── routers/               # API endpoint routers
│   ├── health.py         # Health check endpoints
│   ├── devices.py        # Device management
│   ├── wallets.py        # Wallet connection
│   └── sign.py           # Transaction signing
├── middleware/            # HTTP middleware
│   ├── auth.py           # JWT authentication
│   ├── logging.py        # Request logging
│   └── rate_limit.py     # Rate limiting
├── services/             # Business logic
│   ├── hardware_service.py
│   └── device_manager.py
├── integration/          # Hardware wallet clients
│   ├── service_base.py
│   ├── ledger_client.py
│   ├── trezor_client.py
│   └── keepkey_client.py
├── models/               # Data models
├── utils/                # Utilities
└── config/               # Configuration templates
```

## API Endpoints

### Health
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed service status

### Devices
- `GET /api/v1/hardware/devices` - List connected devices
- `GET /api/v1/hardware/devices/{device_id}` - Device information
- `POST /api/v1/hardware/devices/{device_id}/disconnect` - Disconnect device
- `GET /api/v1/hardware/status` - Hardware system status

### Wallets
- `GET /api/v1/hardware/wallets` - List connected wallets
- `POST /api/v1/hardware/wallets` - Connect wallet
- `GET /api/v1/hardware/wallets/{wallet_id}` - Wallet information
- `DELETE /api/v1/hardware/wallets/{wallet_id}` - Disconnect wallet

### Signing
- `POST /api/v1/hardware/sign` - Request transaction signature
- `GET /api/v1/hardware/sign/{signature_id}` - Get signature status
- `POST /api/v1/hardware/sign/{signature_id}/approve` - Approve signature
- `POST /api/v1/hardware/sign/{signature_id}/reject` - Reject signature

## Configuration

Environment variables from `.env.gui-hardware-manager`:

```bash
# Service
GUI_HARDWARE_MANAGER_HOST=0.0.0.0
GUI_HARDWARE_MANAGER_PORT=8099
GUI_HARDWARE_MANAGER_URL=http://gui-hardware-manager:8099

# Database
MONGODB_URL=mongodb://lucid:password@lucid-mongodb:27017/lucid
REDIS_URL=redis://lucid-redis:6379/0

# Integration
API_GATEWAY_URL=http://api-gateway:8080
AUTH_SERVICE_URL=http://lucid-auth-service:8089
GUI_API_BRIDGE_URL=http://gui-api-bridge:8102

# Hardware
LEDGER_ENABLED=true
TREZOR_ENABLED=true
KEEPKEY_ENABLED=true
TRON_WALLET_SUPPORT=true
```

## Docker Deployment

Build the image:
```bash
docker build -f Dockerfile.gui-hardware-manager -t pickme/lucid-gui-hardware-manager:latest-arm64 .
```

Run the container:
```bash
docker-compose -f configs/docker/docker-compose.gui-integration.yml up -d gui-hardware-manager
```

## Health Checks

The service includes built-in health checks:

```bash
# Basic health check
curl http://localhost:8099/health

# Detailed health check
curl http://localhost:8099/health/detailed
```

## Dependencies

### Hardware Wallet Libraries
- ledgerblue: Ledger hardware wallet support
- trezor: Trezor hardware wallet support
- keepkey: KeepKey hardware wallet support

### Web Framework
- FastAPI: Modern async web framework
- Uvicorn: ASGI server

### Database & Cache
- Motor: Async MongoDB driver
- aioredis: Async Redis client

## Security

- **Non-root user**: Runs as uid 65532
- **Read-only filesystem**: Enhanced security posture
- **Capability dropping**: All capabilities dropped except NET_BIND_SERVICE
- **No privileged mode**: Runs as unprivileged container
- **JWT authentication**: Token-based API security

## Development

Run tests:
```bash
pytest --cov=gui_hardware_manager
```

Run linting:
```bash
black gui_hardware_manager/
flake8 gui_hardware_manager/
mypy gui_hardware_manager/
```

## License

Part of the Lucid project. See LICENSE file in project root.
