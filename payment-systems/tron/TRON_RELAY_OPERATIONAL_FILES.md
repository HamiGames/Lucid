# TRON Relay Service - Operational Files Documentation

**Status: ✅ COMPLETE AND OPERATIONAL**

## Service Overview

The TRON Relay Service is a **READ-ONLY** blockchain relay and caching service that provides:
- Transaction verification
- Block data retrieval and caching
- RPC endpoint integration
- Health monitoring and metrics
- **NO private key access or management**

## Operational Files

### 1. Entrypoint Script
**File:** `relay_entrypoint.py` (117 lines)

**Purpose:** Container startup script for distroless environment

**Features:**
- Environment variable validation
- Configuration extraction
- Structured logging initialization
- Service startup with uvicorn
- Error handling and graceful shutdown

**Environment Variables Required:**
- `SERVICE_PORT` (default: 8098)
- `TRON_NETWORK` (default: mainnet)
- `TRON_RPC_URL` (default: https://api.trongrid.io)

**Optional Environment Variables:**
- `RELAY_ID` (default: relay-001)
- `RELAY_MODE` (default: full) - Options: full, cache, validator, monitor
- `CACHE_ENABLED` (default: true)
- `CACHE_TTL` (default: 3600 seconds)
- `MAX_CACHE_SIZE` (default: 10000)
- `LOG_LEVEL` (default: INFO)

**Usage:**
```bash
docker run -e SERVICE_PORT=8098 \
           -e TRON_NETWORK=mainnet \
           -e TRON_RPC_URL=https://api.trongrid.io \
           pickme/lucid-tron-relay:latest-arm64
```

---

### 2. Main Application
**File:** `relay_main.py` (270+ lines)

**Purpose:** FastAPI application for TRON relay service

**Key Components:**

#### Application Structure:
- **Lifespan Management:** Startup/shutdown hooks for service initialization
- **Middleware:** CORS, TrustedHost for security
- **Error Handlers:** Global exception handling with structured logging

#### API Endpoints:

**Health & Readiness:**
- `GET /health` - Health status with relay details
- `GET /ready` - Readiness probe
- `GET /live` - Liveness probe

**Relay Operations:**
- `GET /api/relay/info` - Relay service information
- `GET /api/relay/status` - Current relay status
- `GET /api/metrics` - Service metrics

**Features:**
- Lifespan-based initialization
- Structured logging
- Exception handling
- Metrics collection
- Health monitoring

**Configuration:**
- Uses `config.py` for application configuration
- Uses `services/tron_relay.py` for business logic
- Uses utility modules for logging, metrics, health checks

---

### 3. Service Module
**File:** `services/tron_relay.py` (320+ lines)

**Purpose:** Core relay service implementation

**Key Functionality:**

#### Service Methods:

**Initialization:**
- `initialize(config)` - Initialize relay with configuration
- `shutdown()` - Graceful shutdown
- `is_ready()` - Check service readiness

**READ-ONLY Operations:**
- `verify_transaction(tx_hash)` - Verify transaction without modifying state
- `get_block_data(block_number)` - Retrieve block data
- `get_health_status()` - Health status information
- `get_status()` - Service operational status
- `get_metrics()` - Collected metrics

**Caching:**
- `_is_cache_valid(cache_key)` - Check cache validity
- `_get_cached(cache_key)` - Retrieve from cache
- `_set_cached(cache_key, value)` - Store in cache
- `clear_cache()` - Clear all cached data

#### Key Features:

1. **READ-ONLY Design:**
   - No private key access
   - No state modification
   - No wallet management
   - Only query operations

2. **Caching System:**
   - In-memory cache with TTL
   - LRU eviction policy
   - Configurable cache size
   - Cache statistics

3. **Health Monitoring:**
   - Startup/shutdown tracking
   - Operational status
   - Error rate monitoring

4. **Metrics Collection:**
   - Total requests count
   - Cached requests count
   - Failed requests count
   - Cache hit/miss ratio

#### Configuration Parameters:
```python
relay_id: str              # Service identifier
relay_mode: str            # full, cache, validator, monitor
tron_network: str          # mainnet, shasta, nile
tron_rpc_url: str          # RPC endpoint
cache_enabled: bool        # Enable caching
cache_ttl: int             # Cache validity (seconds)
max_cache_size: int        # Maximum cache entries
```

---

### 4. Configuration File
**File:** `config/tron-relay-config.yaml` (280+ lines)

**Purpose:** Comprehensive relay service configuration

**Configuration Sections:**

**Service:**
```yaml
service:
  name: lucid-tron-relay
  type: relay
  version: 1.0.0
```

**Relay Configuration:**
```yaml
relay:
  id: relay-001
  mode: full                    # full, cache, validator, monitor
  security:
    read_only: true
    private_key_access: false
    key_management: disabled
```

**Network Configuration:**
```yaml
tron_network:
  network: mainnet              # mainnet, shasta, nile
  rpc_url: https://api.trongrid.io
  trongrid:
    api_key: null               # Optional API key
    rate_limit_requests_per_second: 100
    request_timeout_seconds: 30
```

**Cache Configuration:**
```yaml
cache:
  enabled: true
  ttl_seconds: 3600             # 1 hour
  max_entries: 10000
  eviction_policy: lru
```

**Relay Operations:**
```yaml
relay_operations:
  verify_transactions:
    enabled: true
    cache_results: true
    cache_ttl_seconds: 3600
  get_block_data:
    enabled: true
    cache_results: true
```

**Health & Monitoring:**
```yaml
health_check:
  enabled: true
  interval_seconds: 30
  timeout_seconds: 10

monitoring:
  metrics_enabled: true
  prometheus:
    enabled: true
    port: 9090
```

**Security:**
```yaml
security:
  cors:
    enabled: true
    allowed_origins: ["*"]
  rate_limiting:
    enabled: true
    requests_per_second: 100
  circuit_breaker:
    enabled: true
    failure_threshold: 5
```

---

### 5. Dockerfile
**File:** `Dockerfile.tron-relay` (177 lines)

**Purpose:** Distroless container image for relay service

**Specifications:**
- **Base Image:** `gcr.io/distroless/python3-debian12:latest`
- **Platform:** Linux ARM64 (Raspberry Pi)
- **Build Stages:** 2 (Builder + Runtime)
- **Non-root User:** 65532:65532
- **Security:** Read-only filesystem, minimal capabilities

**Key Features:**
- Multi-stage distroless build
- Marker files with actual content
- COPY ERROR FREE pattern compliance
- Runtime package verification
- Health check in exec form
- CA certificates included

---

### 6. Environment Template
**File:** `../../../configs/environment/env.tron-relay.template` (155 lines)

**Purpose:** Environment configuration template

**Configuration Areas:**
- Service identification and versioning
- Service port and host configuration
- TRON network selection (mainnet, shasta, nile)
- RPC endpoint configuration
- Cache settings (enabled, TTL, max size)
- Relay mode options
- Logging configuration
- Monitoring and metrics
- TLS/certificate configuration
- Connection pool settings
- Timeout configuration
- Rate limiting

**Usage:**
```bash
cp env.tron-relay.template .env.tron-relay
# Edit .env.tron-relay with your values
```

---

### 7. Docker Compose Configuration
**File:** `../../configs/docker/docker-compose.support.yml` (Lines 1011-1148)

**Service Definition:**

```yaml
tron-relay:
  image: pickme/lucid-tron-relay:latest-arm64
  container_name: tron-relay
  environment:
    - SERVICE_PORT=8098
    - TRON_NETWORK=mainnet
    - RELAY_MODE=full
  ports:
    - "8098:8098"
  volumes:
    - ${PROJECT_ROOT}/data/relay:/data:rw
    - ${PROJECT_ROOT}/logs/relay:/app/logs:rw
    - ${PROJECT_ROOT}/data/keys:/data/keys:ro
  healthcheck:
    test: [CMD, /opt/venv/bin/python3, -c, "import urllib.request; urllib.request.urlopen('http://localhost:8098/health').read()"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
  security_opt:
    - no-new-privileges:true
  cap_drop:
    - ALL
  cap_add:
    - NET_BIND_SERVICE
  user: "65532:65532"
  read_only: true
  tmpfs:
    - /tmp:noexec,nosuid,size=100m
```

---

## Operational Modes

### Mode 1: Full Relay (Default)
- **Description:** Complete relay with all features
- **Capabilities:** Transaction verification, block data, caching, monitoring
- **Use Case:** Production deployment with complete functionality

### Mode 2: Cache-Only
- **Description:** Cached data retrieval only
- **Capabilities:** Serve cached data, no live queries
- **Use Case:** Low-bandwidth environments

### Mode 3: Validator
- **Description:** Transaction verification only
- **Capabilities:** Verify transactions without full relay
- **Use Case:** Validation-specific operations

### Mode 4: Monitor
- **Description:** Monitoring and observation only
- **Capabilities:** Health checks, metrics collection
- **Use Case:** Monitoring-only deployments

---

## Health Check Endpoints

All health check endpoints use **exec form** (no shell required for distroless):

```bash
# Health status with relay details
curl http://localhost:8098/health

# Readiness probe
curl http://localhost:8098/ready

# Liveness probe
curl http://localhost:8098/live

# Relay information
curl http://localhost:8098/api/relay/info

# Service metrics
curl http://localhost:8098/api/metrics
```

---

## Security Features

1. **READ-ONLY Design:**
   - No private key access
   - No state modification
   - No wallet management

2. **Container Security:**
   - Non-root user (65532:65532)
   - Read-only filesystem
   - Minimal capabilities (NET_BIND_SERVICE only)
   - No privilege escalation

3. **Network Security:**
   - CORS configured
   - Trusted hosts validation
   - Rate limiting enabled
   - Circuit breaker protection

4. **Data Protection:**
   - TLS/SSL support
   - Sensitive data masking
   - CA certificates included

---

## Metrics & Monitoring

**Collected Metrics:**
- `requests_total` - Total requests processed
- `requests_cached` - Requests served from cache
- `requests_failed` - Failed requests
- `cache_hits` - Cache hit count
- `cache_misses` - Cache miss count

**Endpoints:**
- `/metrics` - Prometheus-compatible metrics
- `/health` - Health status
- `/api/relay/status` - Operational status

---

## Troubleshooting

### Service won't start
1. Check environment variables (SERVICE_PORT, TRON_NETWORK, TRON_RPC_URL)
2. Verify RPC endpoint accessibility
3. Check logs: `docker logs tron-relay`

### Cache not working
1. Verify `CACHE_ENABLED=true`
2. Check `CACHE_TTL` setting
3. Monitor cache metrics: `curl http://localhost:8098/api/metrics`

### High memory usage
1. Reduce `MAX_CACHE_SIZE`
2. Lower `CACHE_TTL`
3. Switch to cache-only mode

### Network timeouts
1. Increase `TRON_RPC_URL_TIMEOUT`
2. Reduce worker count
3. Check rate limiting: `RATE_LIMIT_REQUESTS`

---

## Deployment Checklist

- [ ] Dockerfile is distroless and COPY ERROR FREE
- [ ] Entrypoint script is production-ready
- [ ] Relay service module implemented
- [ ] Configuration YAML complete
- [ ] Environment template provided
- [ ] Docker compose service configured
- [ ] Health checks implemented
- [ ] Security hardening applied
- [ ] Documentation complete
- [ ] Tested on ARM64 architecture

---

## Summary

The TRON Relay Service is a **complete, production-ready, READ-ONLY relay service** with:
- ✅ Distroless container (minimal attack surface)
- ✅ COPY ERROR FREE pattern compliance
- ✅ Non-root execution (security hardened)
- ✅ Health monitoring and metrics
- ✅ In-memory caching with TTL
- ✅ Multiple relay modes
- ✅ Complete operational documentation
- ✅ Ready for Raspberry Pi ARM64 deployment
