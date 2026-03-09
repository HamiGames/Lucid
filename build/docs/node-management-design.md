# Node Management Container Design Template

## Overview

This document provides a comprehensive design template for the **node-management** container, focusing on architecture, module structure, error handling patterns, and troubleshooting guides. This template serves as a reference for understanding container internals and resolving common issues.

**Container Name**: `node-management`  
**Image**: `pickme/lucid-node-management:latest-arm64`  
**Ports**: `8095` (main), `8099` (staging)  
**Base Image**: `gcr.io/distroless/python3-debian12:latest`  
**Python Version**: `3.11`  
**Platform**: `linux/arm64`

---

## Table of Contents

1. [Dockerfile Architecture](#dockerfile-architecture)
2. [Module Structure](#module-structure)
3. [Import Dependencies](#import-dependencies)
4. [Build Process](#build-process)
5. [Runtime Structure](#runtime-structure)
6. [Common Error Patterns](#common-error-patterns)
7. [Error Resolution Guide](#error-resolution-guide)
8. [Verification Checklist](#verification-checklist)
9. [Troubleshooting Procedures](#troubleshooting-procedures)

---

## Dockerfile Architecture

### Multi-Stage Build Pattern

The Dockerfile uses a **two-stage build** pattern for security and size optimization:

#### Stage 1: Builder (`python:3.11-slim-bookworm`)

**Purpose**: Install dependencies, compile packages, prepare artifacts

**Key Steps**:
1. **System Dependencies** (lines 35-49)
   - Build tools: `build-essential`, `gcc`, `g++`
   - SSL/TLS: `libffi-dev`, `libssl-dev`
   - Utilities: `pkg-config`, `curl`, `ca-certificates`

2. **Directory Structure** (lines 54-64)
   - System directories: `/var/run`, `/var/lib` (with marker files)
   - App directories: `/app-dirs/cache/node`, `/app-dirs/data/node`, `/app-dirs/logs/node`
   - Ownership: All set to `65532:65532` (non-root user)

3. **Python Package Installation** (lines 66-85)
   - Upgrade: `pip`, `wheel`, `setuptools`
   - Install: All packages from `requirements.txt` with `--user` flag
   - Critical: Explicit `setuptools>=65.0.0` installation (required for `pkg_resources`)
   - Verification: Builder-stage package import tests

4. **Source Code Copy** (lines 123-146)
   - Copy entire `node/` directory to `/build/node/`
   - Create marker files for verification
   - Verify all required files exist

**Working Directory**: `/build`

#### Stage 2: Runtime (`gcr.io/distroless/python3-debian12:latest`)

**Purpose**: Minimal runtime with only required artifacts

**Key Steps**:
1. **System Artifacts** (lines 181-183)
   - Copy system directories from builder
   - Copy SSL certificates

2. **Application Directories** (lines 188-190)
   - Copy cache, data, logs directories
   - Maintain ownership `65532:65532`

3. **Python Packages** (lines 193-194)
   - Copy from `/root/.local/lib/python3.11/site-packages` → `/usr/local/lib/python3.11/site-packages`
   - Copy binaries from `/root/.local/bin` → `/usr/local/bin`

4. **Runtime Verification** (lines 197-225)
   - Verify all packages exist and are importable
   - Check for critical dependencies: `setuptools`, `pkg_resources`, `socks`, `stem`, `web3`

5. **Application Code** (lines 228-248)
   - Copy `/build/node` → `/app/node`
   - Verify all source files and schemas exist
   - Verify `models.py` exists (critical for legacy model imports)

**Working Directory**: `/app`

**User**: `65532:65532` (non-root)

---

## Module Structure

### Core Application Modules

```
/app/node/
├── __init__.py                 # Package initialization
├── main.py                     # FastAPI application entry point
├── entrypoint.py               # Container entrypoint script
├── config.py                   # Configuration management (Pydantic Settings)
├── config.yaml                 # Default configuration file
├── models.py                   # Legacy models (PoOTProof, NodeInfo, etc.)
│
├── models/                     # New model package
│   ├── __init__.py            # Exports both new and legacy models
│   ├── node.py                # Node data models
│   ├── pool.py                # Pool data models
│   └── payout.py              # Payout data models
│
├── api/                        # FastAPI route handlers
│   ├── nodes.py               # Node CRUD endpoints
│   ├── pools.py               # Pool management endpoints
│   ├── payouts.py             # Payout processing endpoints
│   ├── poot.py                # PoOT proof endpoints
│   ├── resources.py           # Resource monitoring endpoints
│   └── routes.py              # Route registration
│
├── consensus/                  # Consensus mechanisms
│   ├── uptime_beacon.py       # Uptime tracking
│   ├── work_credits.py        # Work credit system
│   ├── task_proofs.py         # Task proof validation
│   └── leader_selection.py    # Leader selection algorithm
│
├── tor/                        # Tor integration
│   ├── tor_manager.py         # Tor daemon management
│   ├── onion_service.py       # Onion service creation
│   └── socks_proxy.py         # SOCKS proxy management
│
├── economy/                    # Economic systems
│   └── node_economy.py        # Node economics and rewards
│
├── pools/                      # Pool management
│   ├── node_pool_systems.py   # Pool system logic
│   └── pool_service.py        # Pool service implementation
│
├── payouts/                    # Payout processing
│   ├── payout_processor.py    # Payout processing logic
│   └── tron_client.py         # TRON blockchain client
│
├── worker/                     # Worker processes
│   ├── node_worker.py         # Main worker implementation
│   ├── node_service.py        # Service layer
│   └── node_routes.py         # Worker routes
│
├── repositories/               # Data access layer
│   ├── node_repository.py     # Node data repository
│   └── pool_repository.py     # Pool data repository
│
├── validation/                 # Validation logic
│   └── node_poot_validations.py
│
├── governance/                 # Governance systems
│   └── node_vote_systems.py
│
├── flags/                      # Feature flags
│   └── node_flag_systems.py
│
├── registration/               # Node registration
│   └── node_registration_protocol.py
│
├── sync/                       # Synchronization
│   └── node_operator_sync_systems.py
│
├── shards/                     # Shard management
│   ├── shard_host_creation.py
│   └── shard_host_management.py
│
├── dht_crdt/                   # DHT CRDT implementation
│   └── dht_node.py
│
├── resources/                  # Resource monitoring
│   └── resource_monitor.py
│
├── poot/                       # PoOT implementation
│   ├── poot_calculator.py     # PoOT calculation logic
│   └── poot_validator.py      # PoOT validation logic
│
└── Core files:
    ├── node_manager.py         # Node manager service
    ├── node_pool_manager.py   # Pool manager service
    ├── payout_manager.py      # Payout manager service
    ├── poot_calculator.py     # PoOT calculator (legacy)
    ├── database_adapter.py    # Database abstraction layer
    ├── peer_discovery.py      # Peer discovery service
    ├── work_credits.py        # Work credits (legacy)
    └── openapi.yaml           # OpenAPI specification
```

---

## Import Dependencies

### Critical Import Chain

```
entrypoint.py
  └── node.main (app)
      ├── node.node_manager
      ├── node.poot_calculator
      │   └── node.models (PoOTProof, NodeInfo) ⚠️ CRITICAL
      ├── node.payout_manager
      ├── node.node_pool_manager
      └── node.api.routes
          ├── node.api.nodes
          ├── node.api.pools
          ├── node.api.payouts
          ├── node.api.poot
          └── node.api.resources
```

### Model Import Resolution

**Problem**: Dual model system (legacy `models.py` + new `models/` package)

**Solution**: `models/__init__.py` dynamically imports legacy models:

```python
# node/models/__init__.py
from .node import Node, NodeCreateRequest, ...
from .pool import NodePool, ...
from .payout import Payout, ...

# Import legacy models from models.py file
import importlib.util
from pathlib import Path

_parent_dir = Path(__file__).parent.parent
_models_file = _parent_dir / "models.py"

# Strategy 1: Direct file import
if _models_file.exists():
    spec = importlib.util.spec_from_file_location("node_models_legacy", str(_models_file.resolve()))
    legacy_models = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy_models)
    
    # Export legacy models
    NodeInfo = legacy_models.NodeInfo
    PoOTProof = legacy_models.PoOTProof
    # ... etc
```

**Critical Models Exported**:
- `PoOTProof` - Used by `poot_calculator.py`
- `NodeInfo` - Used by multiple modules
- `PoolInfo`, `PayoutInfo` - Used by managers
- `NodeMetrics`, `PoolMetrics` - Used by API endpoints
- `ProofType`, `PoolStatus` - Enum types

---

## Build Process

### Builder Stage Flow

1. **System Setup** (lines 35-49)
   ```dockerfile
   RUN apt-get install build-essential gcc g++ libffi-dev libssl-dev ...
   ```

2. **Directory Creation** (lines 54-64)
   ```dockerfile
   RUN mkdir -p /app-dirs/{cache,data,logs}/node
   RUN chown -R 65532:65532 /app-dirs
   ```

3. **Python Environment** (lines 66-85)
   ```dockerfile
   RUN pip install --upgrade pip wheel setuptools
   RUN pip install --user --prefer-binary -r requirements.txt
   RUN pip install --user --force-reinstall --no-deps setuptools>=65.0.0
   ```

4. **Package Verification** (lines 94-120)
   - Verifies all packages exist in `/root/.local/lib/python3.11/site-packages`
   - Tests imports: `uvicorn`, `fastapi`, `pydantic_settings`, `blake3`, `stem`, `socks`, `tronpy`, `pkg_resources`, `web3`

5. **Source Copy** (lines 123-146)
   ```dockerfile
   COPY node/ ./node/
   ```

### Runtime Stage Flow

1. **Artifact Copy** (lines 181-194)
   ```dockerfile
   COPY --from=builder /var/run /var/run
   COPY --from=builder /app-dirs/cache /app/cache
   COPY --from=builder /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
   ```

2. **Runtime Verification** (lines 197-225)
   - Verifies packages in `/usr/local/lib/python3.11/site-packages`
   - Tests all critical imports

3. **Application Copy** (lines 228-248)
   ```dockerfile
   COPY --from=builder /build/node /app/node
   ```
   - Verifies `models.py` exists (line 244)

---

## Runtime Structure

### File System Layout

```
/app/                           # Application root
├── node/                       # Application code
│   ├── main.py                # FastAPI app
│   ├── entrypoint.py          # Entrypoint script
│   ├── models.py              # Legacy models ⚠️ CRITICAL
│   ├── models/                # New model package
│   │   └── __init__.py       # Exports legacy + new models
│   └── [all other modules]
│
├── cache/                      # Cache directory (tmpfs in compose)
│   └── node/
│
├── data/                       # Data directory (volume mount)
│   └── node/
│
├── logs/                       # Logs directory (volume mount)
│   └── node/
│
└── /usr/local/lib/python3.11/site-packages/  # Python packages
    ├── uvicorn/
    ├── fastapi/
    ├── pydantic/
    ├── setuptools/            # ⚠️ CRITICAL for pkg_resources
    ├── pkg_resources.py       # ⚠️ CRITICAL for web3
    ├── stem/                  # ⚠️ CRITICAL for Tor
    ├── socks/                 # ⚠️ CRITICAL for SOCKS proxy
    ├── web3/                  # ⚠️ CRITICAL for blockchain
    └── [other packages]
```

### Python Path Configuration

**Environment Variables**:
```dockerfile
ENV PYTHONPATH=/app:/usr/local/lib/python3.11/site-packages
```

**Entrypoint Path Setup** (`entrypoint.py` lines 16-29):
```python
site_packages = '/usr/local/lib/python3.11/site-packages'
app_path = '/app'

if app_path not in sys.path:
    sys.path.insert(0, app_path)
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)
```

---

## Common Error Patterns

### 1. Module Import Errors

**Pattern**: `ImportError: cannot import name 'X' from 'node.models'`

**Common Causes**:
- Legacy model not exported from `models/__init__.py`
- `models.py` file not copied to runtime
- Import path resolution failure

**Affected Modules**:
- `poot_calculator.py` → `PoOTProof`, `NodeInfo`
- `main.py` → `PoOTProof`, `NodeInfo`, `NodeMetrics`, `PoolMetrics`
- `node_pool_manager.py` → `NodeInfo`, `PoolInfo`
- `payout_manager.py` → `PayoutInfo`, `NodeInfo`

**Resolution**:
1. Verify `models.py` exists in `/app/node/models.py`
2. Check `models/__init__.py` exports the model
3. Verify import mechanism in `models/__init__.py` works

### 2. Package Missing Errors

**Pattern**: `ModuleNotFoundError: No module named 'X'`

**Common Missing Packages**:
- `pkg_resources` → Requires `setuptools>=65.0.0` explicitly installed
- `socks` → Requires `PySocks>=1.7.1` in requirements.txt
- `stem` → Requires `stem>=1.8.0` in requirements.txt

**Resolution**:
1. Check `requirements.txt` includes the package
2. Verify package installed in builder stage
3. Verify package copied to runtime stage
4. Check runtime verification step passes

### 3. Pydantic Version Compatibility

**Pattern**: `PydanticUserError: 'regex' is removed. use 'pattern' instead`

**Affected Files**:
- All files using `Field(regex=...)` or `Path(regex=...)` or `Query(regex=...)`

**Resolution**:
- Replace `regex=` with `pattern=` in all Pydantic Field/Path/Query definitions
- Files affected: `models/node.py`, `models/pool.py`, `models/payout.py`, `api/*.py`

### 4. File Not Found Errors

**Pattern**: `FileNotFoundError` or `assert os.path.exists(...) failed`

**Common Missing Files**:
- Schema files: `*-schema.json` files
- Config files: `config.yaml`
- Marker files: `.lucid-marker` files

**Resolution**:
1. Verify file exists in source `node/` directory
2. Check COPY command in Dockerfile includes the file
3. Verify runtime verification step

### 5. Permission Errors

**Pattern**: `PermissionError` or file write failures

**Common Causes**:
- Files owned by root instead of `65532:65532`
- Read-only filesystem without volume mounts

**Resolution**:
1. Verify `--chown=65532:65532` in COPY commands
2. Check volume mounts in docker-compose for writable directories
3. Verify `USER 65532:65532` is set

---

## Error Resolution Guide

### Step-by-Step Error Resolution Process

#### Step 1: Identify Error Type

**Check Error Message**:
```bash
docker logs node-management 2>&1 | grep -i "error\|exception\|traceback"
```

**Categorize**:
- Import errors → Check module structure
- Package errors → Check requirements.txt and installation
- File errors → Check COPY commands
- Permission errors → Check ownership and volumes

#### Step 2: Verify Build Stage

**Check Builder Verification**:
```dockerfile
# Line 94-120: Builder verification
RUN /usr/local/bin/python3 -c "import ...; assert ..."
```

**If builder fails**:
- Check `requirements.txt` for missing packages
- Verify system dependencies installed
- Check package installation commands

#### Step 3: Verify Runtime Stage

**Check Runtime Verification**:
```dockerfile
# Line 197-225: Runtime verification
RUN ["/usr/bin/python3.11", "-c", "import ...; assert ..."]
```

**If runtime fails**:
- Verify packages copied from builder
- Check COPY commands for site-packages
- Verify marker files exist

#### Step 4: Verify Application Files

**Check Application Verification**:
```dockerfile
# Line 231-248: Application verification
RUN ["/usr/bin/python3.11", "-c", "import os; assert os.path.exists(...)"]
```

**If application files missing**:
- Verify `COPY node/ ./node/` command
- Check source files exist in repository
- Verify marker files created

#### Step 5: Check Import Resolution

**For Import Errors**:

1. **Verify models.py exists**:
   ```dockerfile
   # Line 244: Explicit check
   assert os.path.exists('/app/node/models.py'), 'models.py not found'
   ```

2. **Check models/__init__.py**:
   - Verify legacy model import mechanism
   - Check all required models exported in `__all__`
   - Test import strategies work

3. **Verify Python path**:
   - Check `PYTHONPATH` environment variable
   - Verify `sys.path` setup in `entrypoint.py`
   - Check import statements use correct paths

#### Step 6: Rebuild and Test

**Rebuild Command**:
```bash
docker build --platform linux/arm64 \
  -f node/Dockerfile.node-management \
  -t pickme/lucid-node-management:latest-arm64 \
  . --no-cache
```

**Test Import**:
```bash
docker run --rm pickme/lucid-node-management:latest-arm64 \
  /usr/bin/python3.11 -c "from node.models import PoOTProof; print('OK')"
```

---

## Verification Checklist

### Pre-Build Verification

- [ ] `node/requirements.txt` includes all required packages
- [ ] `node/models.py` exists and contains legacy models
- [ ] `node/models/__init__.py` exports all legacy models
- [ ] All schema files (`*-schema.json`) exist
- [ ] `config.yaml` exists

### Build Verification

- [ ] Builder stage completes without errors
- [ ] All packages install successfully
- [ ] Builder verification passes (line 94-120)
- [ ] Source files copied correctly
- [ ] Source verification passes (line 130-146)

### Runtime Verification

- [ ] Runtime stage completes without errors
- [ ] Packages copied to `/usr/local/lib/python3.11/site-packages`
- [ ] Runtime verification passes (line 197-225)
- [ ] Application files copied to `/app/node`
- [ ] Application verification passes (line 231-248)
- [ ] `models.py` exists at `/app/node/models.py`

### Runtime Testing

- [ ] Container starts without errors
- [ ] Entrypoint script executes successfully
- [ ] `from node.main import app` succeeds
- [ ] All critical imports work:
  - [ ] `from node.models import PoOTProof`
  - [ ] `from node.models import NodeInfo`
  - [ ] `import pkg_resources`
  - [ ] `import socks`
  - [ ] `import stem`
  - [ ] `import web3`
- [ ] FastAPI application initializes
- [ ] Health check endpoint responds

---

## Troubleshooting Procedures

### Procedure 1: Import Error Resolution

**Symptoms**: `ImportError: cannot import name 'X' from 'node.models'`

**Actions**:

1. **Verify models.py exists**:
   ```bash
   docker exec node-management ls -la /app/node/models.py
   ```

2. **Check models/__init__.py exports**:
   ```bash
   docker exec node-management \
     /usr/bin/python3.11 -c "from node.models import __all__; print(__all__)"
   ```

3. **Test direct import**:
   ```bash
   docker exec node-management \
     /usr/bin/python3.11 -c "import sys; sys.path.insert(0, '/app'); from node.models import PoOTProof; print('OK')"
   ```

4. **Check import mechanism**:
   ```bash
   docker exec node-management \
     /usr/bin/python3.11 -c "import importlib.util; from pathlib import Path; print(Path('/app/node/models.py').exists())"
   ```

**Fix**: Update `models/__init__.py` import mechanism if needed

### Procedure 2: Package Missing Resolution

**Symptoms**: `ModuleNotFoundError: No module named 'X'`

**Actions**:

1. **Check requirements.txt**:
   ```bash
   grep -i "X" node/requirements.txt
   ```

2. **Verify package installed in builder**:
   ```bash
   docker build --target builder -t node-builder .
   docker run --rm node-builder \
     /usr/local/bin/python3 -c "import X; print('OK')"
   ```

3. **Check runtime package location**:
   ```bash
   docker exec node-management \
     ls -la /usr/local/lib/python3.11/site-packages/ | grep X
   ```

4. **Test import in runtime**:
   ```bash
   docker exec node-management \
     /usr/bin/python3.11 -c "import X; print('OK')"
   ```

**Fix**: Add package to `requirements.txt` or fix COPY command

### Procedure 3: Pydantic Compatibility Resolution

**Symptoms**: `PydanticUserError: 'regex' is removed`

**Actions**:

1. **Find all regex usage**:
   ```bash
   grep -r "regex=" node/
   ```

2. **Replace with pattern**:
   ```bash
   # Use search_replace tool to replace regex= with pattern=
   ```

3. **Verify replacement**:
   ```bash
   grep -r "regex=" node/  # Should return nothing
   grep -r "pattern=" node/  # Should show replacements
   ```

**Fix**: Replace all `regex=` with `pattern=` in Pydantic Field/Path/Query

### Procedure 4: File Missing Resolution

**Symptoms**: `FileNotFoundError` or verification assertion fails

**Actions**:

1. **Check source file exists**:
   ```bash
   ls -la node/[filename]
   ```

2. **Verify COPY command**:
   ```bash
   grep -A5 "COPY node" node/Dockerfile.node-management
   ```

3. **Check runtime file**:
   ```bash
   docker exec node-management ls -la /app/node/[filename]
   ```

4. **Verify verification step**:
   ```bash
   # Check Dockerfile verification assertion
   ```

**Fix**: Add file to COPY command or create missing file

### Procedure 5: Permission Error Resolution

**Symptoms**: `PermissionError` or write failures

**Actions**:

1. **Check file ownership**:
   ```bash
   docker exec node-management ls -la /app/node/
   ```

2. **Verify user**:
   ```bash
   docker exec node-management whoami
   # Should show error (distroless has no whoami)
   docker exec node-management id
   # Should show uid=65532 gid=65532
   ```

3. **Check volume mounts**:
   ```bash
   docker inspect node-management | grep -A10 "Mounts"
   ```

**Fix**: Add `--chown=65532:65532` to COPY commands or fix volume mounts

---

## Critical Dependencies Map

### Python Packages (requirements.txt)

**Core Framework**:
- `fastapi>=0.111,<1.0` - Web framework
- `uvicorn[standard]>=0.30` - ASGI server
- `pydantic==2.5.0` - Data validation (⚠️ v2.5.0 uses `pattern` not `regex`)
- `pydantic-settings==2.1.0` - Settings management

**Database**:
- `motor==3.3.2` - MongoDB async driver
- `redis==5.0.1` - Redis client

**Cryptography**:
- `cryptography>=42.0.0` - Cryptographic primitives
- `blake3>=0.3.0` - Blake3 hashing
- `pycryptodome==3.19.0` - Crypto library

**Tor Integration**:
- `stem>=1.8.0` - Tor control protocol ⚠️ CRITICAL
- `PySocks>=1.7.1` - SOCKS proxy support ⚠️ CRITICAL

**Blockchain**:
- `web3==6.11.3` - Ethereum/Web3 support ⚠️ Requires `pkg_resources`
- `tronpy==0.4.0` - TRON blockchain client

**System**:
- `setuptools>=65.0.0` - Package management ⚠️ CRITICAL for `pkg_resources`

### Dependency Chain Issues

**web3 → pkg_resources → setuptools**:
- `web3` imports `pkg_resources` at module level
- `pkg_resources` comes from `setuptools`
- Must explicitly install `setuptools>=65.0.0` AFTER requirements.txt
- Must verify `pkg_resources` importable in runtime

**socks_proxy.py → socks → PySocks**:
- `socks_proxy.py` imports `socks` module
- `socks` module comes from `PySocks` package
- Must be in `requirements.txt` and verified

**tor/onion_service.py → stem**:
- Tor integration requires `stem` package
- Must be in `requirements.txt` and verified

---

## Build Verification Points

### Builder Stage Checkpoints

1. **System Packages** (line 35-49)
   - ✅ Build tools installed
   - ✅ SSL libraries available

2. **Python Packages** (line 76-85)
   - ✅ All requirements.txt packages installed
   - ✅ setuptools explicitly installed
   - ✅ pkg_resources importable

3. **Package Verification** (line 94-120)
   - ✅ All packages exist in site-packages
   - ✅ All packages importable
   - ✅ Marker file created

4. **Source Verification** (line 130-146)
   - ✅ All source files copied
   - ✅ All schema files present
   - ✅ Marker file created

### Runtime Stage Checkpoints

1. **Artifact Copy** (line 181-194)
   - ✅ System directories copied
   - ✅ Python packages copied
   - ✅ Application directories copied

2. **Runtime Verification** (line 197-225)
   - ✅ All packages exist
   - ✅ All packages importable
   - ✅ Critical dependencies verified

3. **Application Verification** (line 231-248)
   - ✅ Application files copied
   - ✅ models.py exists ⚠️ CRITICAL
   - ✅ All schemas present

---

## Error Pattern Reference

### Pattern: Import Chain Failure

**Example**: `ImportError: cannot import name 'PoOTProof' from 'node.models'`

**Root Cause**: `models/__init__.py` failed to import from `models.py`

**Fix Location**: `node/models/__init__.py` lines 32-89

**Fix Strategy**:
1. Verify `models.py` path resolution
2. Test importlib.util import mechanism
3. Add fallback import strategies
4. Export in `__all__`

### Pattern: Package Not Found

**Example**: `ModuleNotFoundError: No module named 'pkg_resources'`

**Root Cause**: `setuptools` not installed or not copied correctly

**Fix Location**: `node/Dockerfile.node-management` lines 79-85

**Fix Strategy**:
1. Explicitly install setuptools AFTER requirements.txt
2. Use `--force-reinstall --no-deps` to ensure installation
3. Verify in builder stage
4. Verify in runtime stage

### Pattern: Pydantic Compatibility

**Example**: `PydanticUserError: 'regex' is removed. use 'pattern' instead`

**Root Cause**: Pydantic v2.5.0 removed `regex` parameter

**Fix Location**: All files using `Field(regex=...)`, `Path(regex=...)`, `Query(regex=...)`

**Fix Strategy**:
1. Search for all `regex=` occurrences
2. Replace with `pattern=`
3. Verify in all model files and API files

---

## Maintenance Notes

### When Adding New Models

1. **If adding to new package** (`models/`):
   - Add to appropriate file (`node.py`, `pool.py`, `payout.py`)
   - Export in `models/__init__.py`
   - Add to `__all__`

2. **If adding to legacy** (`models.py`):
   - Add to `models.py`
   - Export in `models/__init__.py` (legacy import section)
   - Add to `__all__`

### When Adding New Dependencies

1. **Add to requirements.txt**
2. **Verify installation in builder** (add to verification step)
3. **Verify import in runtime** (add to runtime verification)
4. **Update this document** (add to Critical Dependencies Map)

### When Fixing Import Errors

1. **Check import chain** (use Import Dependencies section)
2. **Verify module exists** (use Module Structure section)
3. **Check Python path** (use Runtime Structure section)
4. **Test import resolution** (use Troubleshooting Procedures)

---

## Quick Reference

### Critical Files

- `node/Dockerfile.node-management` - Build definition
- `node/entrypoint.py` - Container entrypoint
- `node/main.py` - Application entry point
- `node/models.py` - Legacy models ⚠️ CRITICAL
- `node/models/__init__.py` - Model exports ⚠️ CRITICAL
- `node/requirements.txt` - Python dependencies

### Critical Directories

- `/app/node/` - Application code
- `/app/node/models/` - Model package
- `/usr/local/lib/python3.11/site-packages/` - Python packages
- `/app/cache/node/` - Cache directory
- `/app/data/node/` - Data directory
- `/app/logs/node/` - Logs directory

### Critical Environment Variables

- `PYTHONPATH=/app:/usr/local/lib/python3.11/site-packages`
- `NODE_MANAGEMENT_PORT=8095`
- `NODE_MANAGEMENT_HOST=0.0.0.0`

### Critical User/Group

- User: `65532:65532` (non-root)

---

## Version History

- **v1.0.0** - Initial design template
  - Documented Dockerfile architecture
  - Mapped module structure
  - Created error resolution guide
  - Added troubleshooting procedures

---

**Last Updated**: 2024-12-19  
**Maintained By**: Lucid Development Team  
**Related Documents**: 
- `build/docs/master-docker-design.md` - Universal patterns
- `build/docs/node-management-errors-analysis.md` - Error analysis
- `build/docs/node-management-verification-report.md` - Verification report

