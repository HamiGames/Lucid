# Configuration Files Requirements for docker-compose.core.yml Containers

**Analysis Date:** 2025-01-24  
**File:** `configs/docker/docker-compose.core.yml`

## Summary

Only **1 container** requires external YAML/JSON configuration files mounted as volumes:
- **service-mesh** (requires config files to be mounted)

All other containers have their configuration files baked into the Docker images during build.

---

## Container Analysis

### ✅ 1. api-gateway
- **Container Name:** `api-gateway`
- **Config Files Required:** ❌ None
- **Configuration Method:** Environment variables only (`.env.foundation`, `.env.core`)
- **Status:** ✅ No external config files needed

### ✅ 2. blockchain-engine
- **Container Name:** `blockchain-engine`
- **Config Files Required:** ✅ YAML files (baked into image)
- **Config Files:**
  - `blockchain/config/consensus-config.yaml`
  - `blockchain/config/data-chain-config.yaml`
  - `blockchain/config/anchoring-policies.yaml`
  - `blockchain/config/block-storage-policies.yaml`
- **Location in Container:** `/app/config/` (copied during build)
- **Dockerfile:** Copies `blockchain/config/` → `/app/config/`
- **Status:** ✅ Config files are baked into image - no external mount needed
- **Note:** Files are loaded by `blockchain/config/config.py` via `yaml_loader.py`

### ✅ 3. service-mesh
- **Container Name:** `service-mesh`
- **Config Files Required:** ✅ **YES - REQUIRES EXTERNAL MOUNT**
- **Config Files:**
  - `/config/service-mesh.yaml` (main config - optional, has defaults)
  - `/config/services/` (service configurations - optional)
  - `/config/policies/` (policy configurations - optional)
- **Location in Container:** `/app/config/` (from volume mount)
- **Volume Mount:** `/mnt/myssd/Lucid/Lucid/data/service-mesh/config:/app/config:rw`
- **Environment Variable:** `SERVICE_MESH_CONFIG_PATH=/app/config`
- **Source Files:** `infrastructure/service-mesh/config/`
- **Status:** ⚠️ **REQUIRES CONFIG FILES TO BE PRESENT AT MOUNT POINT**
- **Config Manager:** `infrastructure/service-mesh/controller/config_manager.py`
- **Note:** Service has default config if files are missing, but requires mount point to exist

### ✅ 4. session-anchoring
- **Container Name:** `session-anchoring`
- **Config Files Required:** ✅ YAML files (baked into image)
- **Config Files:** Same as blockchain-engine
- **Location in Container:** `/app/config/` (copied during build)
- **Dockerfile:** Copies `blockchain/config/` → `/app/config/`
- **Status:** ✅ Config files are baked into image - no external mount needed

### ✅ 5. block-manager
- **Container Name:** `block-manager`
- **Config Files Required:** ✅ YAML files (baked into image)
- **Config Files:** Same as blockchain-engine
- **Location in Container:** `/app/config/` (copied during build)
- **Dockerfile:** Copies `blockchain/config/` → `/app/config/`
- **Status:** ✅ Config files are baked into image - no external mount needed

### ✅ 6. data-chain
- **Container Name:** `data-chain`
- **Config Files Required:** ✅ YAML files (baked into image)
- **Config Files:** Same as blockchain-engine
- **Location in Container:** `/app/blockchain/config/` (copied during build)
- **Dockerfile:** Copies `blockchain/config/` → `/app/blockchain/config/`
- **Status:** ✅ Config files are baked into image - no external mount needed

### ✅ 7. lucid-tunnel-tools
- **Container Name:** `lucid-tunnel-tools`
- **Config Files Required:** ❌ None
- **Configuration Method:** Environment variables only
- **Status:** ✅ No external config files needed

---

## Required Actions

### ⚠️ CRITICAL: service-mesh Configuration

The **service-mesh** container requires configuration files to be present at the mount point:

**Mount Path:** `/mnt/myssd/Lucid/Lucid/data/service-mesh/config`

**Required Structure:**
```
/mnt/myssd/Lucid/Lucid/data/service-mesh/config/
├── service-mesh.yaml          # Main config (optional - has defaults)
├── services/                   # Service configurations (optional)
│   └── *.yaml
└── policies/                   # Policy configurations (optional)
    └── *.yaml
```

**Source Files Location:**
- Source: `infrastructure/service-mesh/config/`
- Files should be copied to mount point before starting container

**Verification:**
```bash
# Check if config directory exists and is accessible
ls -la /mnt/myssd/Lucid/Lucid/data/service-mesh/config/

# Verify service-mesh.yaml exists (optional but recommended)
test -f /mnt/myssd/Lucid/Lucid/data/service-mesh/config/service-mesh.yaml
```

---

## Configuration File Details

### Blockchain Services Config Files

All blockchain services (blockchain-engine, session-anchoring, block-manager, data-chain) use these YAML files baked into the image:

1. **consensus-config.yaml**
   - Location: `blockchain/config/consensus-config.yaml`
   - Purpose: Consensus algorithm configuration
   - Loaded by: `blockchain/config/config.py`

2. **data-chain-config.yaml**
   - Location: `blockchain/config/data-chain-config.yaml`
   - Purpose: Data chain service configuration
   - Loaded by: `blockchain/config/config.py`

3. **anchoring-policies.yaml**
   - Location: `blockchain/config/anchoring-policies.yaml`
   - Purpose: Session anchoring policies
   - Loaded by: `blockchain/config/config.py`

4. **block-storage-policies.yaml**
   - Location: `blockchain/config/block-storage-policies.yaml`
   - Purpose: Block storage policies
   - Loaded by: `blockchain/config/config.py`

**Note:** These files support environment variable substitution via `yaml_loader.py` but are not required to be mounted externally.

### Service Mesh Config Files

1. **service-mesh.yaml**
   - Location: `/app/config/service-mesh.yaml` (from volume mount)
   - Source: `infrastructure/service-mesh/config/service-mesh.yaml`
   - Purpose: Main service mesh configuration
   - Loaded by: `infrastructure/service-mesh/controller/config_manager.py`
   - Status: Optional (has defaults if missing)

2. **services/** directory
   - Location: `/app/config/services/` (from volume mount)
   - Purpose: Individual service configurations
   - Status: Optional

3. **policies/** directory
   - Location: `/app/config/policies/` (from volume mount)
   - Purpose: Service mesh policies
   - Status: Optional

---

## Recommendations

1. **✅ service-mesh**: Ensure config directory exists and contains required files before container start
2. **✅ Blockchain services**: Config files are in images - no action needed
3. **✅ Other services**: No config files required

---

**Status:** ✅ Analysis complete  
**Action Required:** Ensure service-mesh config files are present at mount point before deployment

