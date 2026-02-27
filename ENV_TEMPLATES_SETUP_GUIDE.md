# Environment Templates Setup Guide

**Date**: 2026-02-27  
**Status**: ✅ Complete  
**Purpose**: Create service-specific `.env` files from templates

---

## Overview

Environment template files (`.template` suffix) have been created for all 7 GUI services in docker-compose.gui-integration.yml. These templates provide:

- ✅ All required configuration variables
- ✅ Proper variable references to parent `.env` files
- ✅ Real-world values and defaults
- ✅ Comprehensive documentation
- ✅ No placeholder values

---

## Available Templates

| Template File | Service | Purpose |
|---------------|---------|---------|
| `env.gui-api-bridge.template` | gui-api-bridge:8102 | API Bridge service |
| `env.gui-docker-manager.template` | gui-docker-manager:8098 | Docker manager |
| `env.gui-tor-manager.template` | gui-tor-manager:8097 | Tor integration |
| `env.gui-hardware-manager.template` | gui-hardware-manager:8099 | Hardware wallets |
| `env.admin-interface.template` | admin-interface:8120 | Admin Electron GUI |
| `env.user-interface.template` | user-interface:3001 | User Electron GUI |
| `env.node-interface.template` | node-interface:3002 | Node operator GUI |

---

## Quick Setup

### Method 1: Copy and Use Directly

```bash
cd /mnt/myssd/Lucid/Lucid/configs/environment

# Copy all templates to actual .env files
cp env.gui-api-bridge.template .env.gui-api-bridge
cp env.gui-docker-manager.template .env.gui-docker-manager
cp env.gui-tor-manager.template .env.gui-tor-manager
cp env.gui-hardware-manager.template .env.gui-hardware-manager
cp env.admin-interface.template .env.admin-interface
cp env.user-interface.template .env.user-interface
cp env.node-interface.template .env.node-interface

# Verify files created
ls -la .env.gui-* .env.admin-* .env.user-* .env.node-*
```

### Method 2: Create Individual Files

```bash
cd /mnt/myssd/Lucid/Lucid/configs/environment

# Create specific service configuration
cp env.gui-hardware-manager.template .env.gui-hardware-manager

# Edit if needed (all defaults are already set)
vim .env.gui-hardware-manager
```

---

## Variable References

All templates use **proper variable references** to parent `.env` files instead of placeholders:

### From `.env.secrets` (Layer 1)

These variables are defined in `.env.secrets` and referenced here:

```bash
# Database URIs (from .env.secrets)
MONGODB_URL=${MONGODB_URI}
REDIS_URL=${REDIS_URI}

# Security (from .env.secrets)
JWT_SECRET_KEY=${JWT_SECRET_KEY}

# API Keys (from .env.secrets)
TRON_API_KEY=${TRON_API_KEY}
```

### From Other Layers

The hierarchy is maintained:

```
Layer 1: .env.secrets     ← Database passwords, security keys
Layer 2: .env.core        ← Core services
Layer 3: .env.application ← Application settings
Layer 4: .env.foundation  ← Foundation layer
Layer 5: .env.gui         ← GUI shared settings
Layer 6: .env.<service>   ← Service-specific (THIS FILE)
```

---

## Template Contents by Service

### GUI API Bridge (.env.gui-api-bridge)

```bash
SERVICE_NAME=lucid-gui-api-bridge
PORT=8102
HOST=0.0.0.0
LOG_LEVEL=INFO
LUCID_ENV=production
LUCID_PLATFORM=arm64

# Integration service URLs
API_GATEWAY_URL=http://api-gateway:8080
BLOCKCHAIN_ENGINE_URL=http://blockchain-engine:8084
AUTH_SERVICE_URL=http://lucid-auth-service:8089
SESSION_API_URL=http://lucid-session-api:8113
NODE_MANAGEMENT_URL=http://lucid-node-management:8095
ADMIN_INTERFACE_URL=http://lucid-admin-interface:8083
TRON_PAYMENT_URL=http://lucid-tron-client:8091

# Database (from .env.secrets)
MONGODB_URL=${MONGODB_URI}
REDIS_URL=${REDIS_URI}
JWT_SECRET_KEY=${JWT_SECRET_KEY}
```

### GUI Docker Manager (.env.gui-docker-manager)

```bash
SERVICE_NAME=lucid-gui-docker-manager
PORT=8098
HOST=0.0.0.0
LOG_LEVEL=INFO
LUCID_ENV=production
LUCID_PLATFORM=arm64

# Docker configuration
DOCKER_HOST=unix:///var/run/docker.sock
DOCKER_API_VERSION=1.40

# GUI access control
GUI_ACCESS_LEVELS_ENABLED=true
USER_SERVICES=foundation,core
DEVELOPER_SERVICES=foundation,core,application
ADMIN_SERVICES=foundation,core,application,support

# Database (from .env.secrets)
MONGODB_URL=${MONGODB_URI}
REDIS_URL=${REDIS_URI}
JWT_SECRET_KEY=${JWT_SECRET_KEY}

# Monitoring
DOCKER_MONITOR_INTERVAL=30
DOCKER_STARTUP_TIMEOUT=60
DOCKER_STOP_TIMEOUT=30
```

### GUI Tor Manager (.env.gui-tor-manager)

```bash
SERVICE_NAME=lucid-gui-tor-manager
PORT=8097
HOST=0.0.0.0
SERVICE_URL=http://lucid-gui-tor-manager:8097
LOG_LEVEL=INFO
LUCID_ENV=production

# Tor proxy configuration
TOR_PROXY_URL=http://tor-proxy:9051
TOR_PROXY_HOST=tor-proxy
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051
TOR_DATA_DIR=/app/tor-data
TOR_LOG_LEVEL=notice

# Tor integration
GUI_TOR_INTEGRATION=true
ONION_ADDRESS_MASKING=true

# Circuit configuration
TOR_CIRCUIT_ROTATION_INTERVAL=3600
TOR_REUSE_EXIT_NODES=false

# Transaction routing
GUI_HARDWARE_MANAGER_TOR_ROUTING=true
GUI_API_BRIDGE_TOR_ROUTING=false
TOR_ANONYMITY_LEVEL=high

# Monitoring
TOR_HEALTH_CHECK_INTERVAL=60
TOR_CONNECTIVITY_TIMEOUT=30
TOR_MAX_LATENCY_MS=5000

# Security
TOR_MONITOR_EXIT_NODES=true
TOR_DETECT_CIRCUIT_FAILURES=true
TOR_PREVENT_DNS_LEAKS=true

# Database (from .env.secrets)
MONGODB_URL=${MONGODB_URI}
REDIS_URL=${REDIS_URI}
```

### GUI Hardware Manager (.env.gui-hardware-manager)

```bash
SERVICE_NAME=lucid-gui-hardware-manager
PORT=8099
HOST=0.0.0.0
LOG_LEVEL=INFO
LUCID_ENV=production

# Hardware wallet support
HARDWARE_WALLET_ENABLED=true
LEDGER_ENABLED=true
LEDGER_VENDOR_ID=0x2c97
TREZOR_ENABLED=true
TREZOR_VENDOR_ID=0x534c
KEEPKEY_ENABLED=true
KEEPKEY_VENDOR_ID=0x2b24

# Blockchain support
TRON_WALLET_SUPPORT=true
TRON_RPC_URL=https://api.trongrid.io
TRON_API_KEY=${TRON_API_KEY}

# Integration services
API_GATEWAY_URL=http://api-gateway:8080
AUTH_SERVICE_URL=http://lucid-auth-service:8089
GUI_API_BRIDGE_URL=http://gui-api-bridge:8102
TOR_PROXY_URL=http://tor-proxy:9051

# Database (from .env.secrets)
MONGODB_URL=${MONGODB_URI}
REDIS_URL=${REDIS_URI}

# CORS configuration
CORS_ENABLED=true
CORS_ORIGINS=http://user-interface:3001,http://node-interface:3002,http://admin-interface:8120,http://localhost:3001,http://localhost:3002,http://localhost:8120
CORS_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_HEADERS=*
CORS_ALLOW_CREDENTIALS=true

# Rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_BURST=200

# Device management
USB_DEVICE_SCAN_INTERVAL=5
USB_DEVICE_TIMEOUT=30
DEVICE_CONNECTION_TIMEOUT=60
MAX_CONCURRENT_DEVICES=5

# Signing configuration
SIGN_REQUEST_TIMEOUT=300
MAX_PENDING_SIGN_REQUESTS=100

# Security (from .env.secrets)
JWT_SECRET_KEY=${JWT_SECRET_KEY}

# Monitoring
METRICS_ENABLED=true
HEALTH_CHECK_INTERVAL=60

# Hardware derivation paths
VALIDATE_DERIVATION_PATHS=true
BIP44_ETHEREUM_PATH=m/44'/60'/0'/0/0
BIP44_TRON_PATH=m/44'/195'/0'/0/0
BIP44_BITCOIN_PATH=m/44'/0'/0'/0/0
```

### Admin Interface (.env.admin-interface)

```bash
NODE_ENV=production
ELECTRON_GUI_PROFILE=admin
ELECTRON_GUI_NETWORK=lucid-pi-network
ELECTRON_GUI_API_BASE_URL=http://lucid-gui-api-bridge:8102/api/v1
ELECTRON_GUI_CONFIG_FILE=/app/configs/api-services.conf
ADMIN_INTERFACE_HOST=0.0.0.0
ADMIN_INTERFACE_PORT=8120
LOG_LEVEL=INFO
LUCID_ENV=production
```

### User Interface (.env.user-interface)

```bash
NODE_ENV=production
ELECTRON_GUI_PROFILE=user
ELECTRON_GUI_NETWORK=lucid-pi-network
ELECTRON_GUI_API_BASE_URL=http://lucid-gui-api-bridge:8102/api/v1
ELECTRON_GUI_CONFIG_FILE=/app/configs/api-services-user.conf
LOG_LEVEL=INFO
LUCID_ENV=production
```

### Node Interface (.env.node-interface)

```bash
NODE_ENV=production
ELECTRON_GUI_PROFILE=node_operator
ELECTRON_GUI_NETWORK=lucid-pi-network
ELECTRON_GUI_API_BASE_URL=http://lucid-gui-api-bridge:8102/api/v1
ELECTRON_GUI_CONFIG_FILE=/app/configs/api-services-node.conf
LOG_LEVEL=INFO
LUCID_ENV=production
```

---

## Environment Variable References

### Standard References Used in All Templates

```bash
# Database URIs (from .env.secrets)
${MONGODB_URI}    # MongoDB connection URL with credentials
${REDIS_URI}      # Redis connection URL with credentials

# Security (from .env.secrets)
${JWT_SECRET_KEY} # JWT signing key for token generation

# API Keys (from .env.secrets)
${TRON_API_KEY}   # TRON API key for tronGrid requests
```

### Real-World Values

All templates use production-ready values:

- **Service URLs**: Use container hostnames (e.g., `http://api-gateway:8080`)
- **Ports**: Match docker-compose mappings (8102, 8098, 8097, 8099, etc.)
- **USB Vendor IDs**: Actual Ledger (0x2c97), Trezor (0x534c), KeepKey (0x2b24)
- **Derivation Paths**: BIP44 standard paths for various blockchains
- **Tor Ports**: Standard Tor ports (9050 for SOCKS, 9051 for control)

---

## Verification & Testing

### Verify Template Syntax

```bash
# Check no placeholders remain
grep -r "\[VALUE\]" configs/environment/*.template
# Should return: (no output = good)

# Verify variable references
grep -r "\${" configs/environment/*.template
# Should show proper references like: ${MONGODB_URI}, ${JWT_SECRET_KEY}
```

### Test Configuration Loading

```bash
# After creating .env files, validate docker-compose configuration
cd /mnt/myssd/Lucid/Lucid
docker-compose -f configs/docker/docker-compose.gui-integration.yml config --quiet

# Should produce no errors and output complete configuration
```

### Verify Environment Variables

```bash
# Check specific service environment
docker-compose -f configs/docker/docker-compose.gui-integration.yml config | \
  grep -A 30 "gui-hardware-manager:"

# Should show all environment variables loaded from .env files
```

---

## Customization Guide

### Changing Service Port

```bash
# Edit .env file
vim configs/environment/.env.gui-hardware-manager

# Update PORT variable
PORT=9000  # Changed from 8099

# Also update docker-compose.yml port mapping
# ports:
#   - "9000:9000"  # Changed from "8099:8099"

# Restart service
docker-compose -f configs/docker/docker-compose.gui-integration.yml \
  restart gui-hardware-manager
```

### Enabling Debug Mode

```bash
# Edit .env file
vim configs/environment/.env.gui-hardware-manager

# Change DEBUG value
DEBUG=true     # Changed from false
LOG_LEVEL=DEBUG

# Restart service
docker-compose -f configs/docker/docker-compose.gui-integration.yml \
  restart gui-hardware-manager
```

### Changing Logging Level

```bash
# Development (verbose)
LOG_LEVEL=DEBUG

# Production (minimal)
LOG_LEVEL=INFO

# Troubleshooting
LOG_LEVEL=DEBUG
```

---

## File Locations

```
configs/environment/
├─ env.gui-api-bridge.template           (Template - keep in git)
├─ .env.gui-api-bridge                   (Created from template - .gitignore)
│
├─ env.gui-docker-manager.template       (Template - keep in git)
├─ .env.gui-docker-manager               (Created from template - .gitignore)
│
├─ env.gui-tor-manager.template          (Template - keep in git)
├─ .env.gui-tor-manager                  (Created from template - .gitignore)
│
├─ env.gui-hardware-manager.template     (Template - keep in git)
├─ .env.gui-hardware-manager             (Created from template - .gitignore)
│
├─ env.admin-interface.template          (Template - keep in git)
├─ .env.admin-interface                  (Created from template - .gitignore)
│
├─ env.user-interface.template           (Template - keep in git)
├─ .env.user-interface                   (Created from template - .gitignore)
│
├─ env.node-interface.template           (Template - keep in git)
├─ .env.node-interface                   (Created from template - .gitignore)
│
├─ .env.secrets                          (Master secrets - .gitignore)
├─ .env.core                             (Core config - .gitignore)
├─ .env.application                      (App config - .gitignore)
├─ .env.foundation                       (Foundation config - .gitignore)
└─ .env.gui                              (GUI config - .gitignore)
```

---

## Security Notes

- ✅ Templates use variable references (`${VAR_NAME}`) not hardcoded values
- ✅ Secrets are loaded from `.env.secrets` layer
- ✅ All `.env*` files are git-ignored
- ✅ Templates can be safely committed (no secrets)
- ✅ No placeholders in production files

---

## Troubleshooting

### "Environment variable not found" error

**Cause**: Variable reference not resolved  
**Solution**:
```bash
# Verify parent .env file has the variable
grep MONGODB_URI configs/environment/.env.secrets

# If missing, add to appropriate parent .env file
echo "MONGODB_URI=mongodb://..." >> configs/environment/.env.secrets

# Restart service
docker-compose -f configs/docker/docker-compose.gui-integration.yml restart gui-hardware-manager
```

### Service not picking up new environment

**Cause**: Docker has cached old configuration  
**Solution**:
```bash
# Force container recreation
docker-compose -f configs/docker/docker-compose.gui-integration.yml \
  up -d --force-recreate gui-hardware-manager
```

### Can't find variable in logs

**Cause**: Debugging which .env file a variable came from  
**Solution**:
```bash
# Show resolved configuration
docker-compose -f configs/docker/docker-compose.gui-integration.yml \
  config | grep -A 5 "environment:"

# Check specific .env file
cat configs/environment/.env.gui-hardware-manager | grep VAR_NAME
```

---

## Summary

| Item | Status |
|------|--------|
| Templates created | ✅ 7/7 |
| Variable references | ✅ All use ${VAR} format |
| Placeholders | ✅ None remaining |
| Real-world values | ✅ All included |
| Documentation | ✅ Complete |

---

**Document**: Environment Templates Setup Guide  
**Date**: 2026-02-27  
**Status**: ✅ Complete  
**Templates**: 7 files ready for use  
