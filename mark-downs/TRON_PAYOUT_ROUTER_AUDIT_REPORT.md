# TRON Payout Router Container - Comprehensive Audit Report

**Report Date**: 2026-01-25  
**Service**: `tron-payout-router` (lucid-tron-payout-router:latest-arm64)  
**Container Port**: 8092  
**Status**: ⚠️ **CRITICAL ISSUES IDENTIFIED**

---

## Executive Summary

The `tron-payout-router` container has **CRITICAL OPERATIONAL DEFICIENCIES** preventing runtime execution:

1. **Missing Entrypoint File** - No `payout_router_entrypoint.py` exists
2. **Missing Environment Template** - No `.env.tron-payout-router` in configs/environment
3. **Module Import Path Issues** - Relative imports may fail in distroless container
4. **Inconsistent Configuration** - Dockerfile CMD doesn't match operational patterns
5. **Missing Operational Documentation** - No PAYOUT_ROUTER_OPERATIONAL_FILES.md

---

## Issue 1: MISSING ENTRYPOINT FILE ⛔ CRITICAL

### Problem
The Dockerfile CMD expects a module entrypoint:
```dockerfile
CMD ["/opt/venv/bin/python3", "-m", "payout_router_main"]
```

**However, `payout_router_main.py` is designed as a standalone script, NOT a Python module.**

### Current State
- ✅ File exists: `payment-systems/tron/payout_router_main.py`
- ❌ Missing: `payment-systems/tron/payout_router_entrypoint.py`
- ❌ Missing: Proper service initialization entry point

### What Should Exist
Based on the **PAYMENT_GATEWAY_OPERATIONAL_FILES.md** pattern, a dedicated entrypoint file should exist:

**File**: `payment-systems/tron/payout_router_entrypoint.py`

**Purpose**:
- Sets `SERVICE_NAME='tron-payout-router'` for service detection
- Reads `SERVICE_PORT`, `SERVICE_HOST`, `WORKERS` from environment
- Initializes uvicorn with proper host/port binding
- Imports FastAPI app from `payout_router_main` correctly
- Ensures site-packages and /app are in PYTHONPATH

### Impact
🔴 **Container will FAIL to start** - Python module import will fail in distroless environment

---

## Issue 2: MISSING ENVIRONMENT CONFIGURATION FILE ⛔ CRITICAL

### Problem
Docker Compose references a non-existent environment file:
```yaml
env_file:
  - ${PROJECT_ROOT:-/mnt/myssd/Lucid/Lucid}/configs/environment/.env.tron-payout-router  # ← MISSING
```

### Current State
**Existing environment templates**:
- ✅ `.env.tron-client.template`
- ✅ `.env.tron-wallet-manager.template`
- ✅ `.env.tron-relay.template`
- ❌ `.env.tron-payout-router` (doesn't exist in configs/environment/)
- ✅ `env.payout-router.template` (EXISTS in payment-systems/tron/ - WRONG LOCATION)

### File Location Mismatch
```
❌ WRONG:  payment-systems/tron/env.payout-router.template
✅ RIGHT:  configs/environment/.env.tron-payout-router  (should be generated from template)
```

### What Should Exist
**File**: `configs/environment/.env.tron-payout-router`

Generated from template or copied from `payment-systems/tron/env.payout-router.template`

### Required Variables
```
# Service Configuration
SERVICE_NAME=tron-payout-router
SERVICE_PORT=8092
SERVICE_HOST=0.0.0.0
PAYOUT_ROUTER_PORT=8092
PAYOUT_ROUTER_HOST=0.0.0.0
PAYOUT_ROUTER_URL=http://tron-payout-router:8092
WORKERS=1
TIMEOUT=30
LOG_LEVEL=INFO

# TRON Configuration
TRON_NETWORK=mainnet
TRON_CLIENT_URL=http://lucid-tron-client:8091
TRON_TIMEOUT=30
TRON_RPC_URL=https://api.trongrid.io

# Payout Configuration
PAYOUT_BATCH_SIZE=50
PAYOUT_BATCH_INTERVAL=300
MAX_PAYOUT_AMOUNT=1000.0
MIN_PAYOUT_AMOUNT=0.01
DAILY_PAYOUT_LIMIT=10000.0

# Database (required)
MONGODB_URL=mongodb://lucid-mongodb:27017
MONGODB_DATABASE=lucid_payments
REDIS_URL=redis://lucid-redis:6379

# Security (required)
JWT_SECRET_KEY=<from .env.secrets>
WALLET_ENCRYPTION_KEY=<from .env.secrets>
```

### Impact
🔴 **Container will FAIL to start** - Missing required environment variables will cause configuration errors

---

## Issue 3: DOCKERFILE CMD PATTERN MISMATCH ⚠️ SEVERE

### Problem
```dockerfile
# Current (Line 175)
CMD ["/opt/venv/bin/python3", "-m", "payout_router_main"]
```

This attempts to:
1. Execute Python with `-m` flag (module mode)
2. Import module `payout_router_main`

**HOWEVER**: `payout_router_main.py` is a script file, NOT a module with `__main__.py`

### Correct Pattern (from container-design.md)
```dockerfile
# Should be:
CMD ["/opt/venv/bin/python3", "payout_router_entrypoint.py"]

# OR via entrypoint wrapper:
ENTRYPOINT []
CMD ["/opt/venv/bin/python3", "payout_router_entrypoint.py"]
```

### Comparison with Working Services
- ✅ Payment Gateway: Uses `payment_gateway_entrypoint.py` (exists)
- ❌ Payout Router: References missing `payout_router_main` as module

### Impact
🔴 **Container will FAIL to start** - Module import will fail with ModuleNotFoundError

---

## Issue 4: MISSING OPERATIONAL DOCUMENTATION ⚠️ SEVERE

### Problem
No operational checklist exists for payout-router service

### Existing Documentation
- ✅ `PAYMENT_GATEWAY_OPERATIONAL_FILES.md` - Complete checklist
- ✅ `WALLET_MANAGER_MODULES.md` - Module documentation
- ❌ `PAYOUT_ROUTER_OPERATIONAL_FILES.md` - MISSING

### Should Exist
**File**: `payment-systems/tron/PAYOUT_ROUTER_OPERATIONAL_FILES.md`

**Contents should verify**:
- ✅ All required service modules exist
- ✅ All required API endpoints defined
- ✅ All utility modules present
- ✅ Configuration files present
- ✅ Entrypoint file exists and correct
- ✅ Health check endpoints accessible
- ✅ Environment variables documented

### Impact
🟠 **Operational risk** - No verification checklist for deployment

---

## Issue 5: MODULE IMPORT PATH ISSUES ⚠️ MODERATE

### Current Problem in `payout_router_main.py` (Lines 18-21)
```python
payment_systems_dir = Path(__file__).parent.parent
if str(payment_systems_dir) not in sys.path:
    sys.path.insert(0, str(payment_systems_dir))

from tron.services.payout_router import PayoutRouterService
```

**Problem in distroless container**:
- File is at `/app/payout_router_main.py`
- Parent directory calculation gives `/app/..` (not payment-systems/)
- Import tries: `from tron.services.payout_router import ...` - FAILS in distroless

### Correct Approach
```python
# Method 1: Direct path insertion (CORRECT for distroless)
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

# Then import from within app:
from services.payout_router import PayoutRouterService
from api.payouts import router as payouts_router
```

### Impact
🟠 **Runtime failure** - Module imports may fail if app/ structure differs

---

## Issue 6: HEALTH CHECK ENDPOINT VERIFICATION ⚠️ MODERATE

### Dockerfile Health Check (Lines 360-371)
```yaml
healthcheck:
  test:
    [
      "CMD",
      "/opt/venv/bin/python3",
      "-c",
      "import os; import urllib.request; port = os.getenv('SERVICE_PORT', '8092'); urllib.request.urlopen(f'http://localhost:{port}/health').read(); exit(0)",
    ]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Verification Required
✅ **Health endpoint DOES exist** in `payout_router_main.py` (Lines 92-107):
```python
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    global payout_service
    try:
        health_status = {
            "status": "healthy",
            "service": "tron-payout-router",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
```

✅ Health check is properly implemented

---

## Issue 7: REQUIRED MODULES VERIFICATION

### Dockerfile Package Verification (Lines 82-92)
Dockerfile checks for critical packages:
```dockerfile
RUN /opt/venv/bin/python -c "import fastapi, uvicorn, tronpy, httpx, aiofiles, pydantic, pydantic_settings, motor; print('✅ critical packages installed')"
```

### All Required Packages Present in requirements.txt ✅
- ✅ `fastapi>=0.111,<1.0`
- ✅ `uvicorn[standard]>=0.30`
- ✅ `pydantic>=2.5.0`
- ✅ `pydantic-settings>=2.1.0`
- ✅ `httpx==0.25.2`
- ✅ `aiofiles==23.2.1`
- ✅ `tronpy==0.4.0`
- ✅ `motor==3.3.2`
- ✅ `cryptography>=42.0.0`
- ✅ `structlog==23.2.0`
- ✅ `prometheus-client==0.19.0`

**Status**: ✅ All dependencies present

---

## Issue 8: DOCKER COMPOSE CONFIGURATION VALIDATION

### Configuration Structure (docker-compose.support.yml Lines 246-384)

#### Service Definition
```yaml
tron-payout-router:
  image: pickme/lucid-tron-payout-router:latest-arm64  ✅ Correct
  container_name: tron-payout-router                    ✅ Correct
  hostname: tron-payout-router                          ✅ Correct
  restart: unless-stopped                               ✅ Correct
```

#### Environment Files
```yaml
env_file:
  - ${PROJECT_ROOT:-/mnt/myssd/Lucid/Lucid}/configs/environment/.env.foundation                ✅ Exists
  - ${PROJECT_ROOT:-/mnt/myssd/Lucid/Lucid}/configs/environment/.env.support                  ✅ Exists
  - ${PROJECT_ROOT:-/mnt/myssd/Lucid/Lucid}/configs/environment/.env.tron-payout-router       ❌ MISSING
  - ${PROJECT_ROOT:-/mnt/myssd/Lucid/Lucid}/configs/environment/.env.secrets                  ✅ Required
  - ${PROJECT_ROOT:-/mnt/myssd/Lucid/Lucid}/configs/environment/.env.core                     ✅ Exists
```

#### Port Configuration ✅
```yaml
ports:
  - "${PAYOUT_ROUTER_PORT:-8092}:${PAYOUT_ROUTER_PORT:-8092}"
```
Correctly uses environment variable

#### Volume Mounts ✅
```yaml
volumes:
  - ${PROJECT_ROOT:-/mnt/myssd/Lucid/Lucid}/data/payment-systems:/data/payment-systems:rw     ✅
  - ${PROJECT_ROOT:-/mnt/myssd/Lucid/Lucid}/data/payments:/data/payouts:rw                    ✅
  - ${PROJECT_ROOT:-/mnt/myssd/Lucid/Lucid}/data/batches:/data/batches:rw                     ✅
  - ${PROJECT_ROOT:-/mnt/myssd/Lucid/Lucid}/data/keys:/data/keys:ro                           ✅ Read-only
  - ${PROJECT_ROOT:-/mnt/myssd/Lucid/Lucid}/logs/payout-router:/app/logs:rw                   ✅
```

#### Security Configuration ✅
```yaml
user: "65532:65532"                                      ✅ Non-root
security_opt:
  - no-new-privileges:true                               ✅ Hardened
  - seccomp:unconfined                                   ✅ Allows syscalls
cap_drop:
  - ALL                                                  ✅ Drop all
cap_add:
  - NET_BIND_SERVICE                                     ✅ Only bind service
read_only: true                                          ✅ Read-only filesystem
tmpfs:
  - /tmp:noexec,nosuid,size=100m                        ✅ Secure tmpfs
```

#### Dependencies ✅
```yaml
depends_on:
  lucid-mongodb:
    condition: service_started                           ✅ Required
  lucid-redis:
    condition: service_started                           ✅ Required
```

---

## Summary of Issues

| # | Issue | Severity | Status | File(s) Affected |
|---|-------|----------|--------|------------------|
| 1 | Missing entrypoint file | 🔴 CRITICAL | ❌ Not Fixed | `payout_router_entrypoint.py` |
| 2 | Missing environment config | 🔴 CRITICAL | ❌ Not Fixed | `.env.tron-payout-router` |
| 3 | Dockerfile CMD pattern mismatch | 🔴 CRITICAL | ❌ Not Fixed | `Dockerfile.payout-router` L175 |
| 4 | Module import path issues | 🟠 SEVERE | ⚠️ Partial | `payout_router_main.py` L18-21 |
| 5 | Missing operational docs | 🟠 SEVERE | ❌ Not Fixed | `PAYOUT_ROUTER_OPERATIONAL_FILES.md` |
| 6 | Health check validation | ✅ OK | ✓ Working | Health endpoints defined |
| 7 | Required dependencies | ✅ OK | ✓ Complete | `requirements.txt` verified |
| 8 | Docker compose config | ✅ Mostly OK | ⚠️ Partial | Missing `.env.tron-payout-router` reference |

---

## Blocking Issues for Runtime

### 🔴 MUST FIX (Container will not start)
1. Create `payout_router_entrypoint.py` with proper service initialization
2. Create `.env.tron-payout-router` in `configs/environment/`
3. Update `Dockerfile.payout-router` CMD to use entrypoint file correctly

### 🟠 SHOULD FIX (May cause import failures)
4. Fix module import paths in `payout_router_main.py`
5. Create operational documentation file

### ✅ VERIFIED (No action needed)
6. Health check endpoints are properly defined
7. All dependencies are present in requirements.txt
8. Docker compose configuration is mostly correct

---

## Recommended Actions

### IMMEDIATE (Phase 1: Enable Runtime)
1. **Create entrypoint file** → `payment-systems/tron/payout_router_entrypoint.py`
2. **Create environment config** → `configs/environment/.env.tron-payout-router`
3. **Fix Dockerfile CMD** → Update to use entrypoint file

### FOLLOW-UP (Phase 2: Improve Reliability)
4. **Fix import paths** in `payout_router_main.py`
5. **Create operational docs** → `PAYOUT_ROUTER_OPERATIONAL_FILES.md`
6. **Test container startup** with full Docker Compose stack

### VERIFICATION (Phase 3: Validation)
7. Run health check endpoint validation
8. Verify environment variable binding
9. Test payout processing workflow

---

## Files Requiring Changes

### NEW FILES TO CREATE
```
✅ payment-systems/tron/payout_router_entrypoint.py
✅ configs/environment/.env.tron-payout-router
✅ payment-systems/tron/PAYOUT_ROUTER_OPERATIONAL_FILES.md
```

### FILES REQUIRING UPDATES
```
🔧 payment-systems/tron/Dockerfile.payout-router (LINE 175: CMD)
🔧 payment-systems/tron/payout_router_main.py (LINES 18-30: imports)
```

---

## Configuration Environment Variables Reference

### Required from `.env.tron-payout-router`
```
# Service
SERVICE_NAME=tron-payout-router
SERVICE_PORT=8092
SERVICE_HOST=0.0.0.0

# TRON
TRON_NETWORK=mainnet
TRON_CLIENT_URL=http://lucid-tron-client:8091

# Payout
PAYOUT_BATCH_SIZE=50
PAYOUT_BATCH_INTERVAL=300
MAX_PAYOUT_AMOUNT=1000.0
MIN_PAYOUT_AMOUNT=0.01
DAILY_PAYOUT_LIMIT=10000.0

# Database
MONGODB_URL=<required>
REDIS_URL=<required>

# Security (from .env.secrets)
JWT_SECRET_KEY=<required>
WALLET_ENCRYPTION_KEY=<required>
```

### Inherited from `.env.foundation`, `.env.support`, `.env.secrets`
- Core platform variables
- Security credentials
- Database connection strings

---

## References

### Related Documentation
- `build/docs/dockerfile-design.md` - Dockerfile patterns
- `build/docs/container-design.md` - Container standards (Section 4.2: Entrypoints)
- `build/docs/master-docker-design.md` - Universal patterns
- `PAYMENT_GATEWAY_OPERATIONAL_FILES.md` - Reference implementation
- `WALLET_MANAGER_MODULES.md` - Module documentation pattern

### Related Services
- `tron-payment-gateway` - Uses similar pattern (has entrypoint)
- `tron-wallet-manager` - Reference implementation
- `lucid-tron-client` - Base service

---

## Audit Conclusion

**Status**: ⛔ **NOT READY FOR DEPLOYMENT**

The `tron-payout-router` container has **3 critical blocking issues** preventing runtime execution:
1. Missing entrypoint file
2. Missing environment configuration  
3. Dockerfile CMD/module pattern mismatch

**Estimated Fix Time**: 30-45 minutes for experienced developer

**Risk Assessment**: CRITICAL - Container will fail immediately on startup without fixes

**Next Steps**: Implement recommended actions in Phase 1 (Immediate)

---

**Generated**: 2026-01-25  
**Status**: Audit Complete  
**Recommendation**: Create fixes following payment-gateway pattern as reference
