# TRON Payout Router vs Payment Gateway - Configuration Comparison

## Service Comparison Matrix

| Aspect | Payout Router | Payment Gateway | Status |
|--------|---------------|-----------------|--------|
| **Entrypoint File** | ❌ MISSING: `payout_router_entrypoint.py` | ✅ EXISTS: `payment_gateway_entrypoint.py` | MISMATCH |
| **Environment File** | ❌ MISSING: `.env.tron-payout-router` | ✅ EXISTS: `.env.tron-payment-gateway.template` | MISSING |
| **Dockerfile Pattern** | ❌ WRONG: `-m payout_router_main` | ✅ CORRECT: Direct entrypoint | PATTERN ERROR |
| **Main Script** | ✅ EXISTS: `payout_router_main.py` | ✅ EXISTS: `main.py` | OK |
| **Services** | ✅ EXISTS: `services/payout_router.py` | ✅ EXISTS: `services/payment_gateway.py` | OK |
| **API Routes** | ✅ EXISTS: `api/payouts.py` | ✅ EXISTS: `api/payments.py` | OK |
| **Requirements** | ✅ COMPLETE: `requirements.txt` | ✅ COMPLETE: `requirements.txt` | OK |
| **Operational Docs** | ❌ MISSING: `PAYOUT_ROUTER_OPERATIONAL_FILES.md` | ✅ EXISTS: `PAYMENT_GATEWAY_OPERATIONAL_FILES.md` | MISSING |
| **Config Files** | ✅ COMPLETE: config/ directory | ✅ COMPLETE: config/ directory | OK |
| **Health Endpoints** | ✅ DEFINED: `/health`, `/health/live`, `/health/ready` | ✅ DEFINED: `/health`, `/health/live`, `/health/ready` | OK |

---

## File Structure Comparison

### Payment Gateway (WORKING) ✅
```
payment-systems/tron/
├── payment_gateway_entrypoint.py        ✅ Exists - Sets SERVICE_NAME
├── main.py                               ✅ Exists - FastAPI app
├── services/
│   └── payment_gateway.py               ✅ Exists
├── api/
│   └── payments.py                      ✅ Exists
├── Dockerfile.payment-gateway           ✅ Exists - Correct pattern
├── requirements.txt                     ✅ Complete
├── PAYMENT_GATEWAY_OPERATIONAL_FILES.md ✅ Exists - Checklist

configs/environment/
├── .env.tron-payment-gateway.template   ✅ Exists in template
└── (actual .env.tron-payment-gateway)   ✅ Should exist
```

### Payout Router (BROKEN) ❌
```
payment-systems/tron/
├── payout_router_entrypoint.py          ❌ MISSING - NOT CREATED
├── payout_router_main.py                ✅ Exists - FastAPI app
├── services/
│   └── payout_router.py                 ✅ Exists
├── api/
│   └── payouts.py                       ✅ Exists
├── Dockerfile.payout-router             ✅ Exists - WRONG PATTERN (Line 175)
├── requirements.txt                     ✅ Complete
├── env.payout-router.template           ✅ Exists - WRONG LOCATION
├── PAYOUT_ROUTER_OPERATIONAL_FILES.md   ❌ MISSING - NOT CREATED

configs/environment/
├── .env.tron-payout-router              ❌ MISSING - NOT CREATED
```

---

## Dockerfile Command Comparison

### Payment Gateway (CORRECT) ✅
```dockerfile
# File: Dockerfile.payment-gateway
ENTRYPOINT []
CMD ["/opt/venv/bin/python3", "payment_gateway_entrypoint.py"]
```

**How it works**:
1. Entrypoint is empty array (no override)
2. CMD calls the entrypoint file directly
3. Python executes the file
4. Entrypoint file initializes uvicorn and FastAPI

### Payout Router (INCORRECT) ❌
```dockerfile
# File: Dockerfile.payout-router - LINE 175
ENTRYPOINT []
CMD ["/opt/venv/bin/python3", "-m", "payout_router_main"]
```

**Problem**:
1. `-m` flag tells Python to treat argument as module
2. `payout_router_main` is not a Python module (no `__main__.py`)
3. Python looks for module in sys.path - fails
4. Container exits with ModuleNotFoundError

**Should be**:
```dockerfile
ENTRYPOINT []
CMD ["/opt/venv/bin/python3", "payout_router_entrypoint.py"]
```

---

## Environment Configuration Comparison

### Payment Gateway (CORRECT STRUCTURE) ✅

**Template Location**: `configs/environment/.env.tron-payment-gateway.template`
**Final Location**: `configs/environment/.env.tron-payment-gateway`
**Docker Compose Reference**: Line 831 (CORRECT)

```yaml
env_file:
  - ${PROJECT_ROOT}/configs/environment/.env.tron-payment-gateway  ✅
```

**Template Contains**: 239 lines with all service variables

### Payout Router (INCORRECT STRUCTURE) ❌

**Template Location**: `payment-systems/tron/env.payout-router.template` (WRONG PLACE)
**Final Location**: Should be `configs/environment/.env.tron-payout-router` (MISSING)
**Docker Compose Reference**: Line 254 (CORRECT - but file missing!)

```yaml
env_file:
  - ${PROJECT_ROOT}/configs/environment/.env.tron-payout-router  ❌ REFERENCED BUT MISSING
```

**Template Contains**: 65 lines - exists but not in right place

---

## Entrypoint File Comparison

### Payment Gateway Entrypoint (REFERENCE) ✅
```python
# File: payment-systems/tron/payment_gateway_entrypoint.py

#!/usr/bin/env python3

import os
import sys
import uvicorn

# Set service name for main.py detection
os.environ['SERVICE_NAME'] = 'payment_gateway'

# Get configuration from environment
PORT = int(os.getenv('PAYMENT_GATEWAY_PORT', '8097'))
HOST = os.getenv('SERVICE_HOST', '0.0.0.0')
WORKERS = int(os.getenv('WORKERS', '1'))

# Import the FastAPI app
from main import app

# Run the server
if __name__ == '__main__':
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        workers=WORKERS,
        log_level='info'
    )
```

**Key Features**:
- ✅ Sets SERVICE_NAME for service detection
- ✅ Reads environment variables
- ✅ Imports from main.py directly
- ✅ Configures uvicorn with host/port/workers
- ✅ Uses if __name__ == '__main__' guard

### Payout Router Entrypoint (SHOULD BE CREATED) ❌
```python
# File: payment-systems/tron/payout_router_entrypoint.py
# DOES NOT EXIST - NEEDS TO BE CREATED

#!/usr/bin/env python3

import os
import sys
import uvicorn

# Set service name for payout_router_main.py detection
os.environ['SERVICE_NAME'] = 'tron-payout-router'

# Get configuration from environment
PORT = int(os.getenv('PAYOUT_ROUTER_PORT', '8092'))
HOST = os.getenv('SERVICE_HOST', '0.0.0.0')
WORKERS = int(os.getenv('WORKERS', '1'))

# Import the FastAPI app
from payout_router_main import app

# Run the server
if __name__ == '__main__':
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        workers=WORKERS,
        log_level='info'
    )
```

---

## Docker Compose Dependencies

### Payment Gateway Dependencies ✅
```yaml
tron-payment-gateway:
  depends_on:
    lucid-mongodb:
      condition: service_started      ✅
    lucid-redis:
      condition: service_started      ✅
    lucid-tron-client:
      condition: service_started      ✅
    tron-payout-router:
      condition: service_started      ✅ Depends on payout-router!
    tron-wallet-manager:
      condition: service_started      ✅
    tron-usdt-manager:
      condition: service_started      ✅
```

### Payout Router Dependencies ✅
```yaml
tron-payout-router:
  depends_on:
    lucid-mongodb:
      condition: service_started      ✅
    lucid-redis:
      condition: service_started      ✅
```

**Note**: Payment gateway depends on payout-router, so payout-router MUST start first!

---

## Health Check Comparison

### Payment Gateway Health Check ✅
```yaml
healthcheck:
  test:
    [
      "CMD",
      "/opt/venv/bin/python3",
      "-c",
      "import os; import urllib.request; port = os.getenv('PAYMENT_GATEWAY_PORT', '8097'); urllib.request.urlopen(f'http://127.0.0.1:{port}/health').read(); exit(0)",
    ]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Payout Router Health Check ✅ (But will fail if container doesn't start)
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

**Difference**: 
- Payment Gateway uses variable: `PAYMENT_GATEWAY_PORT`
- Payout Router uses variable: `SERVICE_PORT` (more generic)

---

## Module Import Path Comparison

### Payment Gateway Imports ✅
```python
# File: payment_gateway_entrypoint.py
from main import app  # Direct import - CORRECT
```

```python
# File: main.py (within payment-systems/tron/)
# Can import from relative paths or sys.path
from services.payment_gateway import PayoutGatewayService
```

### Payout Router Imports ❌
```python
# File: payout_router_main.py - CURRENT (BROKEN)
payment_systems_dir = Path(__file__).parent.parent  # Wrong!
sys.path.insert(0, str(payment_systems_dir))
from tron.services.payout_router import PayoutRouterService  # Fails in distroless
```

**Fix**:
```python
# File: payout_router_main.py - SHOULD BE
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))
from services.payout_router import PayoutRouterService  # Correct relative import
```

---

## Operational Documentation Comparison

### Payment Gateway Docs ✅
```
File: PAYMENT_GATEWAY_OPERATIONAL_FILES.md
- 121 lines
- Complete checklist format
- Verifies all components
- References build documentation
- Lists all required and optional files
```

**Sections**:
- ✅ Core Application Files
- ✅ API Modules
- ✅ Service Modules
- ✅ Utility Modules
- ✅ Model Modules
- ✅ Configuration Files
- ✅ Docker Configuration
- ✅ Entrypoint File Details
- ✅ Health Check
- ✅ Environment Variables
- ✅ Service Detection
- ✅ Compliance

### Payout Router Docs ❌
```
File: PAYOUT_ROUTER_OPERATIONAL_FILES.md
DOES NOT EXIST - NEEDS TO BE CREATED
```

---

## Issue Resolution Path

### Step 1: Create Entrypoint File
```
Source: payment-systems/tron/payment_gateway_entrypoint.py (TEMPLATE)
Destination: payment-systems/tron/payout_router_entrypoint.py (CREATE NEW)
Changes: Update SERVICE_NAME, port variables, import statement
Time: ~5 minutes
```

### Step 2: Create Environment File
```
Source: payment-systems/tron/env.payout-router.template (EXISTS - WRONG PLACE)
Destination: configs/environment/.env.tron-payout-router (CREATE NEW)
Changes: Copy template content, fill placeholders
Time: ~5 minutes
```

### Step 3: Fix Dockerfile
```
File: payment-systems/tron/Dockerfile.payout-router
Line: 175
Before: CMD ["/opt/venv/bin/python3", "-m", "payout_router_main"]
After:  CMD ["/opt/venv/bin/python3", "payout_router_entrypoint.py"]
Time: ~2 minutes
```

### Step 4: Fix Import Paths
```
File: payment-systems/tron/payout_router_main.py
Lines: 18-30
Changes: Correct sys.path manipulation and imports
Time: ~10 minutes
```

### Step 5: Create Operational Docs
```
Source: payment-systems/tron/PAYMENT_GATEWAY_OPERATIONAL_FILES.md (TEMPLATE)
Destination: payment-systems/tron/PAYOUT_ROUTER_OPERATIONAL_FILES.md (CREATE NEW)
Changes: Update service name, file references, sections
Time: ~10 minutes
```

**Total Time**: ~35 minutes

---

## Verification Checklist

After fixes, verify:

```
[ ] Container builds successfully
[ ] Docker image has no build errors
[ ] Container starts without exit code
[ ] Port 8092 is accessible
[ ] /health endpoint returns 200 OK
[ ] /health/live endpoint responds
[ ] /health/ready endpoint responds
[ ] Environment variables are loaded
[ ] MongoDB connection works
[ ] Redis connection works
[ ] Payout API endpoints accessible
[ ] Logs show no errors
[ ] Health check succeeds in docker-compose
[ ] Payment gateway can connect to payout router
[ ] Service name detected as 'tron-payout-router'
```

---

## Summary Table

| Fix # | Component | Issue | Solution | File(s) | Time |
|-------|-----------|-------|----------|---------|------|
| 1 | Entrypoint | Missing | Create file from payment_gateway template | `payout_router_entrypoint.py` | 5 min |
| 2 | Environment | Missing | Copy template to configs/environment | `.env.tron-payout-router` | 5 min |
| 3 | Dockerfile | Wrong pattern | Update CMD on line 175 | `Dockerfile.payout-router` | 2 min |
| 4 | Imports | Path error | Fix sys.path in main file | `payout_router_main.py` | 10 min |
| 5 | Docs | Missing | Create checklist doc | `PAYOUT_ROUTER_OPERATIONAL_FILES.md` | 10 min |

**Total**: 32 minutes

---

**Generated**: 2026-01-25  
**Type**: Configuration Audit  
**Reference**: Payment Gateway (working implementation)  
**Status**: Ready for implementation
