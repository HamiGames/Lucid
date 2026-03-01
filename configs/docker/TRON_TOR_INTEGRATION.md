# LUCID TRON Services - Tor Proxy Integration Guide

## Overview

This document describes the integration between TRON payment services and the tor-proxy service for privacy-preserving network operations.

**Last Updated:** 2026-02-27
**Status:** Fully Implemented

---

## Changes Summary

### 1. Network Architecture Updates

#### Problem Fixed
- TRON services were on isolated network (`lucid-tron-isolated`)
- tor-proxy was on foundation network (`lucid-pi-network`)
- Cross-network communication was impossible

#### Solution Implemented
All TRON services now connect to BOTH networks:
- **Primary:** `lucid-tron-isolated` (internal TRON service communication)
- **Secondary:** `lucid-pi-network` (access to tor-proxy, MongoDB, Redis)

**Static IP Assignments:**
```yaml
lucid-tron-client:        172.20.1.91  # TRON Client
tron-payout-router:       172.20.1.92  # Payout Router
tron-wallet-manager:      172.20.1.93  # Wallet Manager
tron-usdt-manager:        172.20.1.94  # USDT Manager
tron-staking:             172.20.1.96  # TRX Staking
tron-payment-gateway:     172.20.1.97  # Payment Gateway
tron-relay:               172.20.1.98  # TRON Relay
```

**Benefits:**
- Services can now reach tor-proxy on `lucid-pi-network`
- Services can reach MongoDB and Redis
- Internal service communication still uses container names
- Static IPs enable predictable network topology

### 2. Dependency Chain Improvements

#### Before
```yaml
depends_on:
  tor-proxy:
    condition: service_started  # ❌ Couldn't reach across networks
```

#### After
```yaml
depends_on:
  tor-proxy:
    condition: service_healthy      # ✅ Wait for health check
  lucid-mongodb:
    condition: service_healthy      # ✅ Database is ready
  lucid-redis:
    condition: service_healthy      # ✅ Cache is ready
```

**Benefits:**
- Services wait for dependencies to be healthy
- Cross-network communication is validated
- Database initialization is complete

### 3. Environment Configuration

#### New File: `.env.tron-proxy`

All TRON services now load `env.tron-proxy.template`:

**Location:** `configs/environment/env.tron-proxy.template`

**Key Variables:**
```bash
# Tor Proxy Connection
TOR_PROXY_HOST=tor-proxy
TOR_PROXY_SOCKS_PORT=9050
TOR_PROXY_CONTROL_PORT=9051
TOR_PROXY_HTTP_PORT=8888

# HTTP Proxy Configuration
HTTP_PROXY=http://tor-proxy:8888
HTTPS_PROXY=http://tor-proxy:8888
NO_PROXY=lucid-tron-client,tron-wallet-manager,...

# Integration Settings
USE_TOR_FOR_EXTERNAL_CALLS=true
TOR_ROUTE_RPC=true
TOR_CIRCUIT_ROTATION_ENABLED=true
TOR_CIRCUIT_ROTATION_INTERVAL=3600

# Privacy Settings
TOR_PREVENT_DNS_LEAKS=true
TOR_MONITOR_EXIT_NODES=true
TOR_DETECT_CIRCUIT_FAILURES=true
```

#### Updated docker-compose.support.yml

Each TRON service now loads the tor-proxy config:

```yaml
lucid-tron-client:
  env_file:
    - .env.foundation
    - .env.support
    - .env.tron-client
    - .env.tron-proxy        # ← NEW
    - .env.secrets
    - .env.core
```

### 4. Python Configuration Updates

#### File: `payment-systems/tron/config.py`

Added tor-proxy configuration fields:

```python
class TRONPaymentConfig(BaseSettings):
    # Tor Proxy Configuration
    tor_proxy_host: str = "tor-proxy"
    tor_proxy_socks_port: int = 9050
    tor_proxy_control_port: int = 9051
    tor_proxy_http_port: int = 8888
    
    # Feature Toggles
    use_tor_for_external_calls: bool = True
    tor_route_rpc: bool = True
    tor_circuit_rotation_enabled: bool = True
    
    # Monitoring
    tor_health_check_interval: int = 60
    tor_connectivity_timeout: int = 30
    tor_max_latency_ms: int = 5000
```

### 5. New Utility Module: Tor Proxy Client Manager

#### File: `payment-systems/tron/utils/tor_proxy_client.py`

Provides HTTP client configuration for tor-proxy integration:

**Key Classes:**
- `TorProxyClientManager` - Manages proxy configuration
- `get_tor_proxy_client_manager()` - Get global instance
- `initialize_tor_proxy_client(config)` - Initialize from config

**Usage Examples:**

```python
# Get manager instance
tor_manager = get_tor_proxy_client_manager()

# Create httpx client routed through tor-proxy
async_client = tor_manager.create_httpx_client(timeout=30.0)

# Get proxy URL for specific protocol
socks5_url = tor_manager.get_proxy_url("socks5")
http_url = tor_manager.get_proxy_url("http")

# Get environment variables for subprocesses
env = tor_manager.get_environment_variables()

# Test tor-proxy connectivity
is_healthy = await tor_manager.test_tor_connectivity()
```

### 6. Docker Compose Network Configuration

#### File: `configs/docker/docker-compose.support.yml`

Added explicit network definitions:

```yaml
networks:
  lucid-pi-network:
    external: true
    name: lucid-pi-network
  lucid-tron-isolated:
    external: true
    name: lucid-tron-isolated
```

**Why this matters:**
- Explicitly declares both networks are external
- Prevents docker-compose from creating new networks
- Ensures IP addressing is consistent

---

## Implementation Details

### TRON RPC Call Flow

**With Tor Proxy Integration:**

```
TRON Service
    ↓
Config (use_tor_for_external_calls=true)
    ↓
TorProxyClientManager
    ↓
HTTP Client (httpx) configured with:
  proxies = "http://tor-proxy:8888"
    ↓
tor-proxy (HTTP proxy on port 8888)
    ↓
Tor Network
    ↓
External TRON RPC Endpoint
  (e.g., api.trongrid.io)
```

### Service-to-Service Communication

**Internal (no tor):**
```
tron-payment-gateway
  ↓
lucid-tron-client:8091      ← Direct via lucid-tron-isolated network
NO_PROXY=lucid-tron-client  ← Bypasses tor-proxy
```

**External (through tor):**
```
lucid-tron-client
  ↓
HTTP Client (tor enabled)
  ↓
tor-proxy:8888              ← Routes TRON RPC through tor
  ↓
https://api.trongrid.io     ← External endpoint
```

---

## Configuration Files

### Load Order

1. `.env.foundation` - Foundation layer (network, platform)
2. `.env.support` - Support services layer
3. `.env.tron-*` - Service-specific config
4. `.env.tron-proxy` - **NEW** Tor proxy integration
5. `.env.secrets` - Sensitive data (keys, passwords)
6. `.env.core` - Core system variables

### Required Files

These files must exist in `configs/environment/`:

```
✅ .env.foundation       (exists - foundation layer)
✅ .env.support         (should exist - support layer)
✅ .env.tron-client     (should exist - tron-client specific)
✅ .env.tron-proxy      (NEW - tor proxy config)
✅ .env.secrets         (exists - secrets)
✅ .env.core            (exists - core)
```

**To setup .env.tron-proxy:**
```bash
cp configs/environment/env.tron-proxy.template \
   configs/environment/.env.tron-proxy

# Edit .env.tron-proxy with your values
# Defaults work for most installations
```

---

## Environment Variables Reference

### Tor Proxy Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TOR_PROXY_HOST` | `tor-proxy` | Tor proxy hostname |
| `TOR_PROXY_SOCKS_PORT` | `9050` | SOCKS5 port |
| `TOR_PROXY_CONTROL_PORT` | `9051` | Control port |
| `TOR_PROXY_HTTP_PORT` | `8888` | HTTP proxy port |

### HTTP Proxy Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `HTTP_PROXY` | `http://tor-proxy:8888` | HTTP proxy URL |
| `HTTPS_PROXY` | `http://tor-proxy:8888` | HTTPS proxy URL |
| `NO_PROXY` | (list) | Services to bypass proxy |
| `SOCKS5_PROXY` | `tor-proxy:9050` | SOCKS5 proxy |

### Integration Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_TOR_FOR_EXTERNAL_CALLS` | `true` | Enable tor routing |
| `TOR_ROUTE_RPC` | `true` | Route RPC through tor |
| `TOR_CIRCUIT_ROTATION_ENABLED` | `true` | Enable rotation |
| `TOR_CIRCUIT_ROTATION_INTERVAL` | `3600` | Rotation interval (seconds) |

### Privacy Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `TOR_PREVENT_DNS_LEAKS` | `true` | Route DNS through tor |
| `TOR_MONITOR_EXIT_NODES` | `true` | Monitor exit nodes |
| `TOR_DETECT_CIRCUIT_FAILURES` | `true` | Detect failures |

### Monitoring & Health

| Variable | Default | Description |
|----------|---------|-------------|
| `TOR_HEALTH_CHECK_INTERVAL` | `60` | Health check interval (seconds) |
| `TOR_CONNECTIVITY_TIMEOUT` | `30` | Connection timeout (seconds) |
| `TOR_MAX_LATENCY_MS` | `5000` | Max latency (milliseconds) |

---

## Usage in TRON Services

### Example: Using Tor-Routed HTTP Client

```python
from payment_systems.tron.utils.tor_proxy_client import get_tor_proxy_client_manager

# Get manager instance
tor_manager = get_tor_proxy_client_manager()

# Create HTTP client routed through tor
async_client = tor_manager.create_httpx_client()

# Make TRON RPC calls through tor
response = await async_client.get(
    "https://api.trongrid.io/wallet/getaccount",
    params={"address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"}
)
```

### Example: Checking Tor Connectivity

```python
# In startup event
@app.on_event("startup")
async def startup_event():
    tor_manager = get_tor_proxy_client_manager()
    is_healthy = await tor_manager.test_tor_connectivity()
    if not is_healthy:
        logger.error("Tor-proxy is not reachable!")
        # Fail fast or retry
```

### Example: Using Environment Variables in Subprocesses

```python
import subprocess
from payment_systems.tron.utils.tor_proxy_client import get_tor_proxy_client_manager

tor_manager = get_tor_proxy_client_manager()
env = tor_manager.get_environment_variables()

# Subprocess inherits tor proxy settings
result = subprocess.run(
    ["curl", "https://api.trongrid.io/"],
    env=env
)
```

---

## Verification & Testing

### 1. Check Network Connectivity

```bash
# Verify TRON services can reach tor-proxy
docker exec tron-wallet-manager curl -v http://tor-proxy:9051/

# Verify TRON services can reach MongoDB
docker exec tron-wallet-manager python3 -c \
  "import pymongo; print(pymongo.MongoClient('mongodb://lucid-mongodb:27017'))"

# Verify TRON services can reach Redis
docker exec tron-wallet-manager redis-cli -h lucid-redis ping
```

### 2. Check Tor Routing

```bash
# Verify HTTP proxy is working
docker exec tron-payment-gateway curl -x http://tor-proxy:8888 \
  https://api.trongrid.io/wallet/getnowblock

# Check TRON RPC calls use tor
docker logs tron-wallet-manager | grep -i "tor\|proxy"
```

### 3. Verify Dependencies

```bash
# Check compose file syntax
docker-compose -f configs/docker/docker-compose.support.yml config --quiet

# Test with dry-run
docker-compose -f configs/docker/docker-compose.support.yml \
  up --no-start --dry-run
```

### 4. Monitor Health Checks

```bash
# Check service health
docker ps --format "table {{.Names}}\t{{.Status}}" | grep tron

# View health check logs
docker logs tron-payment-gateway | grep -i "health\|tor"
```

---

## Troubleshooting

### Issue: "Cannot reach tor-proxy"

**Symptoms:**
```
ERROR: Failed to connect to tor-proxy:9051
```

**Solution:**
1. Verify tor-proxy service is running:
   ```bash
   docker ps | grep tor-proxy
   ```

2. Verify network connectivity:
   ```bash
   docker exec tron-wallet-manager ping -c 3 tor-proxy
   ```

3. Check if tor-proxy is healthy:
   ```bash
   docker logs tor-proxy | tail -20
   ```

### Issue: "Cannot reach MongoDB/Redis"

**Symptoms:**
```
ERROR: Failed to connect to lucid-mongodb:27017
ERROR: Failed to connect to lucid-redis:6379
```

**Solution:**
1. Verify services are on correct networks:
   ```bash
   docker network inspect lucid-pi-network | grep -i "name\|tron"
   ```

2. Check service IP addresses:
   ```bash
   docker inspect tron-wallet-manager --format='{{json .NetworkSettings.Networks}}'
   ```

3. Verify DNS resolution:
   ```bash
   docker exec tron-wallet-manager getent hosts lucid-mongodb
   ```

### Issue: "Tor-proxy health check failing"

**Symptoms:**
```
unhealthy - health check timed out
```

**Solution:**
1. Check tor-proxy startup time (may need 120s):
   ```yaml
   depends_on:
     tor-proxy:
       condition: service_started  # Change to service_healthy
   ```

2. Verify tor bootstrap is complete:
   ```bash
   docker logs tor-proxy | grep -i "bootstrap\|progress"
   ```

### Issue: "Database dependency timeout"

**Symptoms:**
```
ERROR: service "lucid-mongodb" didn't become healthy in time
```

**Solution:**
1. Increase start_period in health check:
   ```yaml
   healthcheck:
     start_period: 120s  # Increase from 40s
   ```

2. Check database startup logs:
   ```bash
   docker logs lucid-mongodb | tail -50
   ```

---

## Performance Considerations

### Tor Latency Impact

Expected latency overhead: **50-200ms per request**

- Direct TRON RPC: ~100ms
- Through tor-proxy: ~150-300ms

### Circuit Rotation

**Default:** Every 1 hour (3600 seconds)

For high-volume TRON operations, consider:
- Increasing rotation interval to 6+ hours
- Or disabling rotation for lower anonymity but higher performance

```yaml
TOR_CIRCUIT_ROTATION_INTERVAL=21600  # 6 hours
```

### Connection Pooling

Tor-proxy HTTP client maintains persistent connections:
- Reduces handshake overhead
- Reuses circuits efficiently
- Improves throughput

---

## Security Notes

### DNS Leak Prevention

**Enabled by default:**
```yaml
TOR_PREVENT_DNS_LEAKS=true
```

All DNS queries are routed through tor-proxy SOCKS5, preventing IP leaks.

### Exit Node Monitoring

**Enabled by default:**
```yaml
TOR_MONITOR_EXIT_NODES=true
```

Monitors tor exit nodes for suspicious patterns.

### Private Key Protection

Tor integration DOES NOT:
- ❌ Encrypt private keys in transit (use TLS separately)
- ❌ Protect against key theft on compromised host
- ❌ Hide transaction amounts from blockchain

Tor integration DOES:
- ✅ Hide your IP address from TRON network
- ✅ Hide which RPC endpoints you query
- ✅ Prevent ISP/network monitoring of TRON activity

---

## Related Documentation

- [TOR Proxy Service](../../02-network-security/tor/README.md)
- [TRON Payment Services](../payment-systems/README.md)
- [Docker Compose Configuration](./README.md)
- [Network Architecture](./NETWORK_ARCHITECTURE.md)

---

## File Summary

**New Files Created:**
- `configs/environment/env.tron-proxy.template` - Tor proxy configuration template
- `payment-systems/tron/utils/tor_proxy_client.py` - HTTP client manager

**Files Modified:**
- `configs/docker/docker-compose.support.yml` - Added networks, dependencies, env files
- `payment-systems/tron/config.py` - Added tor-proxy configuration fields
- `payment-systems/tron/main.py` - Initialize tor-proxy manager at startup

**Key Changes:**
1. ✅ All TRON services now on dual networks (lucid-tron-isolated + lucid-pi-network)
2. ✅ Static IP assignments for predictable topology
3. ✅ Complete dependency chains with health checks
4. ✅ Tor proxy configuration via environment variables
5. ✅ HTTP client manager for tor-proxy routing
6. ✅ Configuration fields for tor integration options

---

**Setup Instructions:**
1. Copy `env.tron-proxy.template` to `.env.tron-proxy`
2. Review and adjust settings as needed
3. Verify network definitions exist in docker-compose files
4. Test connectivity: `docker-compose config --quiet`
5. Deploy services: `docker-compose up -d`
