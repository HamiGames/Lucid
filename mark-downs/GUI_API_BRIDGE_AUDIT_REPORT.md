# GUI API Bridge Service - Audit Report

**Date**: 2026-01-26  
**Status**: ⚠️ CRITICAL INCONSISTENCIES FOUND  
**Severity**: HIGH - Configuration will fail at runtime

---

## 🔴 Critical Issues Found

### Issue 1: BLOCKCHAIN_CORE_URL vs BLOCKCHAIN_ENGINE_URL
**Location**: `configs/docker/docker-compose.gui-integration.yml` (line 35)
**Severity**: CRITICAL ❌

**Problem**:
```yaml
# Line 35 in docker-compose.gui-integration.yml:
- BLOCKCHAIN_CORE_URL=http://lucid-blockchain-core:8084
```

**Issues**:
1. Uses **BLOCKCHAIN_CORE_URL** but code expects **BLOCKCHAIN_ENGINE_URL**
2. References **lucid-blockchain-core** but actual service is **lucid-blockchain-engine**
3. Config validator will reject this parameter (it's not in the Settings model)
4. Service will fail to initialize the BlockchainEngineClient

**Config.py Expects**:
```python
BLOCKCHAIN_ENGINE_URL: str = Field(default="", description="Blockchain Engine URL")
```

**Fix Required**:
```yaml
- BLOCKCHAIN_ENGINE_URL=http://lucid-blockchain-engine:8084
```

---

### Issue 2: SESSION_API_URL Port Mismatch
**Location**: `configs/docker/docker-compose.gui-integration.yml` (line 37)
**Severity**: CRITICAL ❌

**Problem**:
```yaml
# Line 37 in docker-compose.gui-integration.yml:
- SESSION_API_URL=http://lucid-session-api:8087
```

**Issues**:
1. Uses port **8087** but actual session-api service uses port **8113**
2. Connection attempts to wrong port will hang then timeout
3. Integration manager will fail to connect to session API

**Actual Session API Port**: 8113 (from infrastructure/compose/docker-compose.blockchain.yaml)

**Fix Required**:
```yaml
- SESSION_API_URL=http://lucid-session-api:8113
```

---

### Issue 3: Missing Environment Variables in docker-compose
**Location**: `configs/docker/docker-compose.gui-integration.yml` (lines 24-40)
**Severity**: HIGH ⚠️

**Missing Required Variables**:
The docker-compose file does NOT pass:
- ❌ `MONGODB_URL` - Required by config validator
- ❌ `REDIS_URL` - Required by config validator  
- ❌ `JWT_SECRET_KEY` - Required by config validator
- ❌ `BLOCKCHAIN_ENGINE_URL` - Critical for session recovery (has wrong name)

**What's Missing**:
```yaml
# These should be added to environment section:
- MONGODB_URL=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
- REDIS_URL=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0
- JWT_SECRET_KEY=${JWT_SECRET_KEY}
- BLOCKCHAIN_ENGINE_URL=http://lucid-blockchain-engine:8084
```

**Config Validator Result**: Will fail with "Missing required configuration"

---

### Issue 4: Extra/Unknown Environment Variables
**Location**: `configs/docker/docker-compose.gui-integration.yml` (lines 30-33)
**Severity**: MEDIUM ⚠️

**Problematic Variables**:
```yaml
- GUI_INTEGRATION_ENABLED=true       # Unknown to config
- TOR_PROXY_ENABLED=true             # Unknown to config
- TOR_SOCKS_PORT=9050               # Unknown to config
- TOR_CONTROL_PORT=9051             # Unknown to config
```

**Status**: These will be IGNORED by Pydantic (extra='ignore'), but indicate:
1. Configuration was written for a different service design
2. Not actually used by gui-api-bridge
3. Should be removed for clarity

---

### Issue 5: Health Check Command
**Location**: `configs/docker/docker-compose.gui-integration.yml` (line 51)
**Severity**: MEDIUM ⚠️

**Problem**:
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:8102/health || exit 1"]
```

**Issues**:
1. Uses `curl` which won't be available in distroless container
2. Uses `CMD-SHELL` which requires sh/bash (distroless doesn't have these)
3. Will always fail in distroless environment

**Correct for Distroless**:
```yaml
healthcheck:
  test: ["CMD", "python3", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', 8102)); s.close(); exit(0 if result == 0 else 1)"]
```

---

## ✅ Configuration Status Check

### What WORKS:
- ✅ Service name and port (8102)
- ✅ Volume mounts (logs/data)
- ✅ Networks configuration
- ✅ User/security settings (65532:65532)
- ✅ API Gateway URL
- ✅ Auth Service URL
- ✅ Node Management URL
- ✅ Admin Interface URL
- ✅ TRON Payment URL

### What FAILS:
- ❌ BLOCKCHAIN_CORE_URL (wrong name, wrong service)
- ❌ SESSION_API_URL (wrong port 8087 vs 8113)
- ❌ Missing MONGODB_URL
- ❌ Missing REDIS_URL
- ❌ Missing JWT_SECRET_KEY
- ❌ Health check (curl not in distroless)

---

## 📝 Required Fixes

### Fix 1: Update docker-compose.gui-integration.yml

**Remove these lines** (30-33):
```yaml
- GUI_INTEGRATION_ENABLED=true
- TOR_PROXY_ENABLED=true
- TOR_SOCKS_PORT=9050
- TOR_CONTROL_PORT=9051
```

**Fix these lines**:
```yaml
# Line 35 - WRONG:
- BLOCKCHAIN_CORE_URL=http://lucid-blockchain-core:8084
# CORRECT:
- BLOCKCHAIN_ENGINE_URL=http://lucid-blockchain-engine:8084

# Line 37 - WRONG:
- SESSION_API_URL=http://lucid-session-api:8087
# CORRECT:
- SESSION_API_URL=http://lucid-session-api:8113
```

**Add these lines** (after line 40):
```yaml
- MONGODB_URL=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
- REDIS_URL=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0
- JWT_SECRET_KEY=${JWT_SECRET_KEY}
```

**Fix health check** (lines 50-55):
```yaml
# WRONG:
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:8102/health || exit 1"]

# CORRECT:
healthcheck:
  test: ["CMD", "python3", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', 8102)); s.close(); exit(0 if result == 0 else 1)"]
```

---

## 🔍 Code-to-Config Mapping

### Code Expects (config.py):
```python
BLOCKCHAIN_ENGINE_URL: str          # Line 37
SESSION_API_URL: str               # Line 39
MONGODB_URL: str                   # Line 32
REDIS_URL: str                     # Line 33
JWT_SECRET_KEY: str                # Line 45
```

### docker-compose.gui-integration.yml Provides:
```yaml
BLOCKCHAIN_CORE_URL (WRONG)        # Line 35 ❌
SESSION_API_URL (WRONG PORT)       # Line 37 ❌
MONGODB_URL (MISSING)              # ❌
REDIS_URL (MISSING)                # ❌
JWT_SECRET_KEY (MISSING)           # ❌
```

---

## 📋 Service Dependency Matrix

| Service | URL | Port | Status | Config Name |
|---------|-----|------|--------|------------|
| Blockchain | lucid-blockchain-core | 8084 | ❌ WRONG NAME | BLOCKCHAIN_CORE_URL |
| Blockchain | lucid-blockchain-engine | 8084 | ✅ CORRECT | BLOCKCHAIN_ENGINE_URL |
| Session API | lucid-session-api | 8087 | ❌ WRONG PORT | SESSION_API_URL |
| Session API | lucid-session-api | 8113 | ✅ CORRECT | SESSION_API_URL |
| MongoDB | lucid-mongodb | 27017 | ❌ MISSING | MONGODB_URL |
| Redis | lucid-redis | 6379 | ❌ MISSING | REDIS_URL |

---

## 🚨 Runtime Impact

### What will happen when container starts with CURRENT config:

1. **Container fails to start** ❌
   - Config validation will reject BLOCKCHAIN_CORE_URL (unknown field)
   - Missing MONGODB_URL validation will fail
   - Missing REDIS_URL validation will fail
   - Missing JWT_SECRET_KEY validation will fail

2. **If somehow it got past validation**:
   - BlockchainEngineClient initialization would fail (no BLOCKCHAIN_ENGINE_URL)
   - Session API connection would timeout (wrong port 8087)
   - Health check would hang then fail (curl not available)

---

## 🔧 Corrected docker-compose.gui-integration.yml (gui-api-bridge section)

```yaml
gui-api-bridge:
    image: pickme/lucid-gui-api-bridge:latest-arm64
    container_name: lucid-gui-api-bridge
    restart: unless-stopped
    env_file:
      - /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
      - /mnt/myssd/Lucid/Lucid/configs/environment/.env.core
      - /mnt/myssd/Lucid/Lucid/configs/environment/.env.application
      - /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
      - /mnt/myssd/Lucid/Lucid/configs/environment/.env.gui
    ports:
      - "8102:8102"
    environment:
      - SERVICE_NAME=lucid-gui-api-bridge
      - PORT=8102
      - HOST=0.0.0.0
      - LOG_LEVEL=INFO
      - DEBUG=false
      - API_GATEWAY_URL=http://lucid-api-gateway:8080
      - BLOCKCHAIN_ENGINE_URL=http://lucid-blockchain-engine:8084  # FIXED
      - AUTH_SERVICE_URL=http://lucid-auth-service:8089
      - SESSION_API_URL=http://lucid-session-api:8113              # FIXED PORT
      - NODE_MANAGEMENT_URL=http://lucid-node-management:8095
      - ADMIN_INTERFACE_URL=http://lucid-admin-interface:8083
      - TRON_PAYMENT_URL=http://lucid-tron-client:8091
      - MONGODB_URL=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin  # ADDED
      - REDIS_URL=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0    # ADDED
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}                           # ADDED
    volumes:
      - /mnt/myssd/Lucid/Lucid/logs/gui-api-bridge:/app/logs
      - /mnt/myssd/Lucid/Lucid/data/gui-api-bridge:/app/data
    networks:
      - lucid-pi-network
      - lucid-gui-network
    depends_on:
      lucid-api-gateway:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python3", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', 8102)); s.close(); exit(0 if result == 0 else 1)"]  # FIXED
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    labels:
      - "com.lucid.phase=gui"
      - "com.lucid.service=gui-api-bridge"
      - "com.lucid.cluster=gui-integration"
    user: "65532:65532"
    security_opt:
      - no-new-privileges:true
      - seccomp:unconfined
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
```

---

## ✅ File Structure Check

**All Python modules present**: ✅
- 40 Python files found in gui-api-bridge/
- All routers, middleware, integration, models, services, utils present
- Main application components complete

**Missing/Issues**:
- ❌ gui_api_bridge_service.py (referenced in plan but not created)
- ⚠️ Config.py was updated by user with field_validator changes

---

## 📊 Summary of Issues

| Issue | Severity | Type | Impact |
|-------|----------|------|--------|
| BLOCKCHAIN_CORE_URL wrong | CRITICAL | Config | Container won't start |
| SESSION_API_URL wrong port | CRITICAL | Config | Session API unreachable |
| Missing MONGODB_URL | CRITICAL | Config | Config validation fails |
| Missing REDIS_URL | CRITICAL | Config | Config validation fails |
| Missing JWT_SECRET_KEY | CRITICAL | Config | Config validation fails |
| Health check uses curl | MEDIUM | Docker | Health check fails in distroless |
| Unknown env vars (TOR_*) | MEDIUM | Config | Ignored but confusing |

---

## 🎯 Action Items

### PRIORITY 1 (Do First):
1. Update docker-compose.gui-integration.yml line 35:
   - Change `BLOCKCHAIN_CORE_URL=http://lucid-blockchain-core:8084`
   - To `BLOCKCHAIN_ENGINE_URL=http://lucid-blockchain-engine:8084`

2. Update docker-compose.gui-integration.yml line 37:
   - Change `SESSION_API_URL=http://lucid-session-api:8087`
   - To `SESSION_API_URL=http://lucid-session-api:8113`

3. Add to docker-compose.gui-integration.yml environment:
   - `MONGODB_URL=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin`
   - `REDIS_URL=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0`
   - `JWT_SECRET_KEY=${JWT_SECRET_KEY}`

4. Update health check command (line 51)

### PRIORITY 2 (Clean up):
1. Remove TOR_* environment variables (lines 30-33)
2. Remove GUI_INTEGRATION_ENABLED variable

---

## 📁 Files Status

### ✅ Present & Correct:
- `Dockerfile.gui-api-bridge` - Updated with better multi-stage build
- `entrypoint.py` - Simplified and corrected
- `config.py` - Updated with field_validators
- `requirements.txt` - Correct dependencies
- All 40 Python modules present

### ❌ Configuration Issue:
- `configs/docker/docker-compose.gui-integration.yml` - Multiple errors

### ⚠️ Inconsistency:
- Config expects BLOCKCHAIN_ENGINE_URL but docker-compose provides BLOCKCHAIN_CORE_URL
- Config expects SESSION_API_URL port 8113 but docker-compose uses 8087

---

## 🔗 Related Files

- Main config: `gui-api-bridge/gui-api-bridge/config.py` (lines 37, 39, 32, 33, 45)
- Blockchain client: `gui-api-bridge/gui-api-bridge/integration/blockchain_client.py`
- Docker-compose: `configs/docker/docker-compose.gui-integration.yml` (lines 12-70)
- Requirements: `gui-api-bridge/requirements.txt` (11 dependencies)

---

## Conclusion

The GUI API Bridge service code is **complete and correct**, but the **docker-compose configuration has critical errors** that will prevent the service from starting:

1. ❌ Wrong blockchain service name and URL variable name
2. ❌ Wrong session API port (8087 vs 8113)
3. ❌ Missing 3 critical environment variables
4. ❌ Incompatible health check for distroless

**These must be fixed before attempting to run the container.**

---

*Report Generated: 2026-01-26*  
*Service: lucid-gui-api-bridge*  
*Container Name: lucid-gui-api-bridge*  
*Status: 🔴 FAILS - Configuration errors prevent startup*
