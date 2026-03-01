# API Gateway - Container Endpoints Mapping

## Overview

Complete mapping of all Docker containers from `docker-compose.gui-integration.yml` and `docker-compose.support.yml` to their API Gateway proxy endpoints.

## Environment Variables Required

Add these to your `.env.core` or deployment environment:

```bash
# GUI Services
GUI_API_BRIDGE_URL=http://gui-api-bridge:8102
GUI_DOCKER_MANAGER_URL=http://gui-docker-manager:8098
GUI_TOR_MANAGER_URL=http://gui-tor-manager:8097
GUI_HARDWARE_MANAGER_URL=http://gui-hardware-manager:8099

# TRON Support Services
TRON_PAYOUT_ROUTER_URL=http://tron-payout-router:8092
TRON_WALLET_MANAGER_URL=http://tron-wallet-manager:8093
TRON_USDT_MANAGER_URL=http://tron-usdt-manager:8094
```

## Endpoint Structure

All endpoints follow the pattern: `/api/v1/{service}/{endpoint}`

### GUI Integration Services

#### 1. GUI API Bridge (Port 8102)
**Container:** `gui-api-bridge`  
**Router:** `gui.py`  
**Prefix:** `/api/v1/gui`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/gui/info` | Get GUI Bridge service information |
| GET | `/api/v1/gui/health` | Check GUI Bridge service health |
| GET | `/api/v1/gui/status` | Get GUI Bridge connection status |
| POST | `/api/v1/gui/electron/connect` | Handle Electron GUI connection |
| POST | `/api/v1/gui/electron/disconnect` | Handle Electron GUI disconnection |
| GET | `/api/v1/gui/electron/routes` | List available GUI routes |

#### 2. GUI Docker Manager (Port 8098)
**Container:** `gui-docker-manager`  
**Router:** `gui_docker.py`  
**Prefix:** `/api/v1/gui/docker`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/gui/docker/info` | Get Docker Manager service info |
| GET | `/api/v1/gui/docker/health` | Check Docker Manager health |
| GET | `/api/v1/gui/docker/containers` | List Docker containers |
| GET | `/api/v1/gui/docker/containers/{container_id}` | Get container details |
| POST | `/api/v1/gui/docker/containers/{container_id}/start` | Start container |
| POST | `/api/v1/gui/docker/containers/{container_id}/stop` | Stop container |

#### 3. GUI Tor Manager (Port 8097)
**Container:** `gui-tor-manager`  
**Router:** `gui_tor.py`  
**Prefix:** `/api/v1/gui/tor`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/gui/tor/info` | Get Tor Manager service info |
| GET | `/api/v1/gui/tor/health` | Check Tor Manager health |
| GET | `/api/v1/gui/tor/status` | Get Tor proxy status |
| GET | `/api/v1/gui/tor/circuits` | List active Tor circuits |
| POST | `/api/v1/gui/tor/circuits/new` | Request new Tor circuit |
| GET | `/api/v1/gui/tor/onion/address` | Get Tor onion address |

#### 4. GUI Hardware Manager (Port 8099)
**Container:** `gui-hardware-manager`  
**Router:** `gui_hardware.py`  
**Prefix:** `/api/v1/gui/hardware`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/gui/hardware/info` | Get Hardware Manager service info |
| GET | `/api/v1/gui/hardware/health` | Check Hardware Manager health |
| GET | `/api/v1/gui/hardware/devices` | List connected hardware wallet devices |
| GET | `/api/v1/gui/hardware/devices/{device_id}` | Get hardware device details |
| POST | `/api/v1/gui/hardware/devices/{device_id}/verify` | Verify hardware device connection |
| GET | `/api/v1/gui/hardware/wallets` | List hardware wallet accounts |
| POST | `/api/v1/gui/hardware/wallets/{wallet_id}/sign` | Sign transaction with hardware wallet |

### Support Services - TRON

#### 5. TRON Payout Router (Port 8092)
**Container:** `tron-payout-router`  
**Router:** `tron_support.py`  
**Prefix:** `/api/v1/tron`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/tron/payout/info` | Get Payout Router service info |
| GET | `/api/v1/tron/payout/health` | Check Payout Router health |
| GET | `/api/v1/tron/payout/status` | Get payout routing status |

#### 6. TRON Wallet Manager (Port 8093)
**Container:** `tron-wallet-manager`  
**Router:** `tron_support.py`  
**Prefix:** `/api/v1/tron`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/tron/wallets/info` | Get Wallet Manager service info |
| GET | `/api/v1/tron/wallets/health` | Check Wallet Manager health |
| GET | `/api/v1/tron/wallets` | List TRON wallets |

#### 7. TRON USDT Manager (Port 8094)
**Container:** `tron-usdt-manager`  
**Router:** `tron_support.py`  
**Prefix:** `/api/v1/tron`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/tron/usdt/info` | Get USDT Manager service info |
| GET | `/api/v1/tron/usdt/health` | Check USDT Manager health |
| GET | `/api/v1/tron/usdt/balance/{wallet_id}` | Get USDT balance for wallet |
| POST | `/api/v1/tron/usdt/transfer` | Transfer USDT |

## Files Added

### Routers
- `03-api-gateway/api/app/routers/gui.py` - GUI API Bridge endpoints
- `03-api-gateway/api/app/routers/gui_docker.py` - GUI Docker Manager endpoints
- `03-api-gateway/api/app/routers/gui_tor.py` - GUI Tor Manager endpoints
- `03-api-gateway/api/app/routers/gui_hardware.py` - GUI Hardware Manager endpoints
- `03-api-gateway/api/app/routers/tron_support.py` - TRON support service endpoints

### Services
- `03-api-gateway/services/gui_bridge_service.py` - GUI API Bridge proxy service
- `03-api-gateway/services/gui_docker_manager_service.py` - Docker Manager proxy service
- `03-api-gateway/services/gui_tor_manager_service.py` - Tor Manager proxy service
- `03-api-gateway/services/gui_hardware_manager_service.py` - Hardware Manager proxy service
- `03-api-gateway/services/tron_support_service.py` - TRON services proxy

### Configuration Updates
- `03-api-gateway/api/app/config.py` - Added 7 new service URLs with validators
- `03-api-gateway/api/app/main.py` - Registered all new routers and startup logging
- `03-api-gateway/services/proxy_service.py` - Updated with all services
- `03-api-gateway/api/app/routers/meta.py` - Updated health check dependencies

## Health Check Dependencies

The meta health endpoint now monitors:
- mongodb
- redis
- blockchain_core
- tron_payment
- gui_api_bridge
- gui_docker_manager
- gui_tor_manager
- gui_hardware_manager
- tron_payout_router
- tron_wallet_manager
- tron_usdt_manager

## Complete Endpoint Summary

**Total Endpoints:** 33
- GUI API Bridge: 6 endpoints
- GUI Docker Manager: 6 endpoints
- GUI Tor Manager: 6 endpoints
- GUI Hardware Manager: 7 endpoints
- TRON Support Services: 8 endpoints

## Usage Examples

### Test GUI API Bridge Health
```bash
curl http://api-gateway:8080/api/v1/gui/health
```

### List Docker Containers
```bash
curl http://api-gateway:8080/api/v1/gui/docker/containers
```

### Get Tor Status
```bash
curl http://api-gateway:8080/api/v1/gui/tor/status
```

### List Hardware Devices
```bash
curl http://api-gateway:8080/api/v1/gui/hardware/devices
```

### Get USDT Balance
```bash
curl http://api-gateway:8080/api/v1/tron/usdt/balance/{wallet_id}
```

## Integration Architecture

```
┌─────────────────────────────────────────────────────────┐
│         Electron GUI Application                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │    API Gateway             │
        │  (Unified Proxy Layer)     │
        └────────────────────────────┘
         │    │    │    │    │    │    │
         ↓    ↓    ↓    ↓    ↓    ↓    ↓
       ┌──────────────────────────────────────┐
       │ GUI Services (GUI Integration)       │
       ├──────────────────────────────────────┤
       │ • gui-api-bridge (8102)              │
       │ • gui-docker-manager (8098)          │
       │ • gui-tor-manager (8097)             │
       │ • gui-hardware-manager (8099)        │
       └──────────────────────────────────────┘
       
       ┌──────────────────────────────────────┐
       │ TRON Support Services (Support)      │
       ├──────────────────────────────────────┤
       │ • tron-payout-router (8092)          │
       │ • tron-wallet-manager (8093)         │
       │ • tron-usdt-manager (8094)           │
       │ • tron-client (8091) [Already added] │
       └──────────────────────────────────────┘
```

## Service References in Configuration

All services reference each other through the API Gateway:
- GUI services reference backend API via `API_GATEWAY_URL`
- TRON services reference API Gateway for transaction routing
- Docker management flows through GUI Docker Manager
- Tor management flows through GUI Tor Manager
- Hardware wallet operations through GUI Hardware Manager

## Notes

- All endpoints support proper error handling with HTTP status codes
- Circuit breaker pattern available via proxy service
- Health checks integrated with meta health endpoint
- All services configured as optional (no crash if not set)
- Warnings logged if services misconfigured
