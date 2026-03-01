# **LUCID DOCKERFILE ALIGNMENT FIX GUIDE**

**Document Purpose:** Single reference guide to fix all Dockerfile alignment errors across 24 available Dockerfiles  
**Target:** All Dockerfiles listed in `plan/disto/LUCID_35_IMAGES_DOCKERFILE_MAPPING.md`  
**Reference Pattern:** `auth/Dockerfile` (fully compliant)  
**Compliance Source:** `plan/constants/` directory requirements

---

## **QUICK REFERENCE: COMPLIANT FILES**

Use these as reference patterns:
- ✅ `auth/Dockerfile` - Python service pattern
- ✅ `02-network-security/tor/Dockerfile` - System service pattern
- ✅ `infrastructure/containers/storage/Dockerfile.mongodb` - Database service pattern
- ✅ `infrastructure/containers/storage/Dockerfile.redis` - Cache service pattern
- ✅ `infrastructure/containers/storage/Dockerfile.elasticsearch` - Search service pattern

---

## **ERROR CATEGORIES & FIXES**

### **ERROR CATEGORY 1: Using `python` instead of `python3`**

**Problem:** Distroless images only have `python3`, not `python`. Using `python` causes runtime failures.

**Affected Locations:**
- `CMD` instructions
- `HEALTHCHECK` instructions

**Fix Pattern:**
```dockerfile
# ❌ WRONG
CMD ["python", "-m", "module.main"]
HEALTHCHECK ... CMD ["python", "-c", "..."]

# ✅ CORRECT
CMD ["python3", "-m", "module.main"]
HEALTHCHECK ... CMD ["python3", "-c", "..."]
```

**Special Cases:**
- Virtual environment paths: Use `/opt/venv/bin/python3` instead of `/opt/venv/bin/python`
- Admin Dockerfile: Change line 123 from `/opt/venv/bin/python` to `/opt/venv/bin/python3`

**Files to Fix:**
1. `sessions/Dockerfile.pipeline` (lines 70, 76)
2. `sessions/Dockerfile.processor` (lines 185, 191)
3. `sessions/Dockerfile.api` (lines 112, 118)
4. `RDP/Dockerfile.server-manager` (lines 115, 121)
5. `RDP/Dockerfile.xrdp` (lines 116, 122)
6. `RDP/Dockerfile.controller` (lines 108, 114)
7. `RDP/Dockerfile.monitor` (lines 110, 116)
8. `node/Dockerfile` (lines 121, 127)
9. `admin/Dockerfile` (line 123)

---

### **ERROR CATEGORY 2: Hardcoded ENV Values**

**Problem:** Configuration values are hardcoded in Dockerfile instead of coming from `.env` files via docker-compose. This prevents Pi console configuration.

**What to Remove:**
All hardcoded ENV values except these essential ones:
- `ENV PATH` (required for runtime)
- `ENV PYTHONUNBUFFERED=1` (Python behavior)
- `ENV PYTHONDONTWRITEBYTECODE=1` (Python optimization)
- `ENV PYTHONPATH` (Python module path)

**What Must Be Removed:**
```dockerfile
# ❌ REMOVE ALL OF THESE:
ENV SERVICE_NAME=...
ENV CONTAINER_NAME=...
ENV HOSTNAME=...
ENV PORT=...
ENV HOST=...
ENV LOG_LEVEL=...
ENV DEBUG=...
ENV MONGODB_URI=...
ENV REDIS_URL=...
ENV HEALTHCHECK_PORT=...
ENV HEALTHCHECK_PATH=...
ENV LUCID_ENV=...
ENV LUCID_PLATFORM=...
ENV PROJECT_ROOT=...
ENV PROJECT_NAME=...
ENV PROJECT_VERSION=...
ENV LUCID_ARCHITECTURE=...
ENV LUCID_PI_NETWORK=...
ENV LUCID_PI_SUBNET=...
ENV LUCID_PI_GATEWAY=...
ENV LUCID_GUI_NETWORK=...
ENV LUCID_GUI_SUBNET=...
ENV LUCID_GUI_GATEWAY=...
ENV ELECTRON_GUI_ENDPOINT=...
ENV API_GATEWAY_URL=...
ENV API_GATEWAY_HOST=...
ENV BLOCKCHAIN_ENGINE_URL=...
ENV DATA_CHAIN_URL=...
ENV BLOCK_MANAGER_URL=...
# ... and any other service-specific configuration ENV variables
```

**What to Keep:**
```dockerfile
# ✅ KEEP ONLY THESE:
ENV PATH=/root/.local/bin:/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/root/.local/lib/python3.11/site-packages
```

**Add Configuration Comment:**
```dockerfile
# =============================================================================
# ENVIRONMENT VARIABLES - MINIMAL DEFAULTS ONLY
# All configuration should come from .env.foundation, .env.secrets, .env.core,
# .env.application, .env.support via docker-compose env_file directive.
# These are fallback defaults only.
# =============================================================================
# Essential PATH for runtime (aligned with distroless best practices)
ENV PATH=/root/.local/bin:/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/root/.local/lib/python3.11/site-packages

# Minimal runtime defaults (will be overridden by docker-compose env_file)
# DO NOT hardcode production values here - use .env files on Pi console
# All service configuration comes from docker-compose.yml environment section:
#   - SERVICE_NAME (from docker-compose)
#   - PORT (from docker-compose)
#   - HOST (from docker-compose)
#   - MONGODB_URI (from docker-compose via .env.secrets)
#   - REDIS_URL (from docker-compose)
#   - LOG_LEVEL (from docker-compose)
#   - DEBUG (from docker-compose)
#   - ... (all other configuration from .env files)
```

**Files to Fix:**
1. `03-api-gateway/Dockerfile` (lines 98-157)
2. `blockchain/Dockerfile.engine` (lines 90-117)
3. `blockchain/Dockerfile.manager` (lines 97-138)
4. `blockchain/Dockerfile.data` (lines 97-139)
5. `sessions/Dockerfile.recorder` (lines 58-62)
6. `sessions/Dockerfile.processor` (lines 158-180)
7. `sessions/Dockerfile.api` (lines 74-107)
8. `sessions/Dockerfile.storage` (lines 79-102)
9. `sessions/Dockerfile.pipeline` (lines 54-58)
10. `blockchain/Dockerfile.anchoring` (lines 93-116)
11. `RDP/Dockerfile.server-manager` (lines 88-110)
12. `RDP/Dockerfile.xrdp` (lines 90-111)
13. `RDP/Dockerfile.controller` (lines 81-103)
14. `RDP/Dockerfile.monitor` (lines 83-105)
15. `node/Dockerfile` (lines 93-116)
16. `admin/Dockerfile` (lines 71-100)

---

### **ERROR CATEGORY 3: Missing Build Arguments in LABEL Metadata**

**Problem:** LABEL metadata doesn't use build arguments (BUILD_DATE, VCS_REF, VERSION), making images untraceable.

**Fix Pattern:**

**Step 1: Add ARG declarations at top (after FROM in runtime stage):**
```dockerfile
# Build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
```

**Step 2: Add complete LABEL section:**
```dockerfile
# Metadata for professional container management (aligned with constants)
LABEL maintainer="Lucid Development Team" \
      version="${VERSION}" \
      description="Distroless [Service Name] for Lucid [service type] support" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.title="Lucid [Service Name]" \
      org.opencontainers.image.description="Distroless [service description] for Lucid project" \
      com.lucid.plane="[ops/core/application/support]" \
      com.lucid.service="[service-name]" \
      com.lucid.platform="arm64" \
      com.lucid.architecture="linux/arm64" \
      com.lucid.security="distroless" \
      com.lucid.vulnerabilities="zero" \
      com.lucid.expose="[port]" \
      com.lucid.cluster="[foundation/core/application/support]" \
      com.lucid.tor.compatible="true" \
      com.lucid.env.config=".env.foundation,.env.secrets"
```

**Reference:** See `auth/Dockerfile` lines 17-19 (ARG) and lines 78-96 (LABEL)

**Files to Fix:**
1. `sessions/Dockerfile.recorder` - Add ARG and LABEL
2. `sessions/Dockerfile.processor` - Add LABEL (has ARG)
3. `sessions/Dockerfile.api` - Add ARG and LABEL
4. `sessions/Dockerfile.storage` - Add ARG and LABEL
5. `sessions/Dockerfile.pipeline` - Add ARG and LABEL
6. `RDP/Dockerfile.server-manager` - Add LABEL (has ARG)
7. `RDP/Dockerfile.xrdp` - Add LABEL (has ARG)
8. `RDP/Dockerfile.controller` - Add LABEL (has ARG)
9. `RDP/Dockerfile.monitor` - Add LABEL (has ARG)
10. `node/Dockerfile` - Add LABEL (has ARG)

---

### **ERROR CATEGORY 4: Missing USER Directive**

**Problem:** Container runs as root instead of non-root user (65532:65532), violating security best practices.

**Fix Pattern:**
```dockerfile
# Run as non-root user (distroless default: 65532:65532, aligned with docker-compose)
USER 65532:65532
```

**Placement:** Add immediately before `CMD` instruction (after `WORKDIR` and `ENV`)

**Files to Fix:**
1. `sessions/Dockerfile.recorder` - Add before CMD
2. `sessions/Dockerfile.processor` - Add before CMD
3. `sessions/Dockerfile.api` - Add before CMD
4. `sessions/Dockerfile.storage` - Add before CMD
5. `sessions/Dockerfile.pipeline` - Add before CMD
6. `RDP/Dockerfile.server-manager` - Add before CMD
7. `RDP/Dockerfile.xrdp` - Add before CMD
8. `RDP/Dockerfile.controller` - Add before CMD
9. `RDP/Dockerfile.monitor` - Add before CMD
10. `node/Dockerfile` - Add before CMD

---

### **ERROR CATEGORY 5: Missing ENV PATH**

**Problem:** PATH doesn't include Python package locations, causing import failures.

**Fix Pattern:**
```dockerfile
# Essential PATH for runtime (aligned with distroless best practices)
ENV PATH=/root/.local/bin:/usr/local/bin:/usr/bin:/bin
```

**For Virtual Environment Services (admin, payment-systems):**
```dockerfile
ENV PATH="/opt/venv/bin:/usr/local/bin:/usr/bin:/bin"
```

**Placement:** Add in ENV section after LABEL, before WORKDIR

**Files to Fix:**
1. `sessions/Dockerfile.recorder` - Add PATH
2. `sessions/Dockerfile.processor` - Add PATH
3. `sessions/Dockerfile.api` - Add PATH
4. `sessions/Dockerfile.storage` - Add PATH
5. `sessions/Dockerfile.pipeline` - Add PATH
6. `RDP/Dockerfile.server-manager` - Add PATH
7. `RDP/Dockerfile.xrdp` - Add PATH
8. `RDP/Dockerfile.controller` - Add PATH
9. `RDP/Dockerfile.monitor` - Add PATH
10. `node/Dockerfile` - Add PATH

---

### **ERROR CATEGORY 6: Missing Build Context Comments**

**Problem:** Build context not documented, causing confusion about COPY path requirements.

**Fix Pattern:**
Add at the top of Dockerfile (after initial comments, before ARG):
```dockerfile
# Build Context: . (project root) - paths must be relative to project root
# Deployment: Pi console at /mnt/myssd/Lucid/Lucid/
# Env Files: /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation, .env.secrets, etc.
```

**Reference:** See `auth/Dockerfile` lines 10-12

**Files to Fix:**
1. `sessions/Dockerfile.recorder`
2. `sessions/Dockerfile.processor`
3. `sessions/Dockerfile.api`
4. `sessions/Dockerfile.storage`
5. `sessions/Dockerfile.pipeline`
6. `RDP/Dockerfile.server-manager`
7. `RDP/Dockerfile.xrdp`
8. `RDP/Dockerfile.controller`
9. `RDP/Dockerfile.monitor`
10. `node/Dockerfile`

---

## **COMPLETE FIX CHECKLIST**

For each Dockerfile, apply fixes in this order:

### **Step 1: Header Section**
- [ ] Add build context comment
- [ ] Add tor-proxy compatibility comment
- [ ] Add .env configuration comment

### **Step 2: Build Arguments**
- [ ] Add `ARG BUILD_DATE`
- [ ] Add `ARG VCS_REF`
- [ ] Add `ARG VERSION=1.0.0`

### **Step 3: LABEL Metadata**
- [ ] Add complete LABEL section using ARG values
- [ ] Include `com.lucid.tor.compatible="true"`
- [ ] Include `com.lucid.env.config` with appropriate .env files

### **Step 4: ENV Variables**
- [ ] Remove ALL hardcoded configuration ENV values
- [ ] Keep only: `PATH`, `PYTHONUNBUFFERED`, `PYTHONDONTWRITEBYTECODE`, `PYTHONPATH`
- [ ] Add configuration comment explaining .env file usage

### **Step 5: USER Directive**
- [ ] Add `USER 65532:65532` before CMD

### **Step 6: CMD/HEALTHCHECK**
- [ ] Change `python` to `python3` in CMD
- [ ] Change `python` to `python3` in HEALTHCHECK

### **Step 7: Configuration Notes**
- [ ] Add comment section explaining .env file locations
- [ ] Add comment explaining docker-compose deployment

---

## **FILE-BY-FILE FIX SUMMARY**

### **Phase 3: Core Services**

#### **1. `03-api-gateway/Dockerfile`**
- [ ] Remove hardcoded ENV (lines 98-157)
- [ ] Add build context comment
- [ ] Verify LABEL uses ARG values
- [ ] Verify USER 65532:65532 exists
- [ ] Verify PATH exists

#### **2. `blockchain/Dockerfile.engine`**
- [ ] Remove hardcoded ENV (lines 90-117)
- [ ] Add build context comment
- [ ] Verify LABEL uses ARG values
- [ ] Verify USER 65532:65532 exists
- [ ] Verify PATH exists

#### **3. `blockchain/Dockerfile.manager`**
- [ ] Remove hardcoded ENV (lines 97-138)
- [ ] Add build context comment
- [ ] Verify LABEL uses ARG values
- [ ] Verify USER 65532:65532 exists
- [ ] Verify PATH exists

#### **4. `blockchain/Dockerfile.data`**
- [ ] Remove hardcoded ENV (lines 97-139)
- [ ] Add build context comment
- [ ] Verify LABEL uses ARG values
- [ ] Verify USER 65532:65532 exists
- [ ] Verify PATH exists

#### **5. `blockchain/Dockerfile.anchoring`**
- [ ] Remove hardcoded ENV (lines 93-116)
- [ ] Add build context comment
- [ ] Verify LABEL uses ARG values (already has)
- [ ] Verify USER 65532:65532 exists (already has)
- [ ] Verify PATH exists (already has)

### **Phase 4: Application Services**

#### **6. `sessions/Dockerfile.pipeline`**
- [ ] Fix `python` → `python3` (lines 70, 76)
- [ ] Remove hardcoded ENV (lines 54-58)
- [ ] Add ARG BUILD_DATE, VCS_REF, VERSION
- [ ] Add LABEL section
- [ ] Add USER 65532:65532
- [ ] Add ENV PATH
- [ ] Add build context comment

#### **7. `sessions/Dockerfile.recorder`**
- [ ] Remove hardcoded ENV (lines 58-62)
- [ ] Add ARG BUILD_DATE, VCS_REF, VERSION
- [ ] Add LABEL section
- [ ] Add USER 65532:65532
- [ ] Add ENV PATH
- [ ] Add build context comment

#### **8. `sessions/Dockerfile.processor`**
- [ ] Fix `python` → `python3` (lines 185, 191)
- [ ] Remove hardcoded ENV (lines 158-180)
- [ ] Add LABEL section (has ARG)
- [ ] Add USER 65532:65532
- [ ] Add ENV PATH
- [ ] Add build context comment

#### **9. `sessions/Dockerfile.storage`**
- [ ] Remove hardcoded ENV (lines 79-102)
- [ ] Add ARG BUILD_DATE, VCS_REF, VERSION
- [ ] Add LABEL section
- [ ] Add USER 65532:65532
- [ ] Add ENV PATH
- [ ] Add build context comment
- [ ] Fix `python` → `python3` if present

#### **10. `sessions/Dockerfile.api`**
- [ ] Fix `python` → `python3` (lines 112, 118)
- [ ] Remove hardcoded ENV (lines 74-107)
- [ ] Add ARG BUILD_DATE, VCS_REF, VERSION
- [ ] Add LABEL section
- [ ] Add USER 65532:65532
- [ ] Add ENV PATH
- [ ] Add build context comment

#### **11. `RDP/Dockerfile.server-manager`**
- [ ] Fix `python` → `python3` (lines 115, 121)
- [ ] Remove hardcoded ENV (lines 88-110)
- [ ] Add LABEL section (has ARG)
- [ ] Add USER 65532:65532
- [ ] Add ENV PATH
- [ ] Add build context comment

#### **12. `RDP/Dockerfile.xrdp`**
- [ ] Fix `python` → `python3` (lines 116, 122)
- [ ] Remove hardcoded ENV (lines 90-111)
- [ ] Add LABEL section (has ARG)
- [ ] Add USER 65532:65532
- [ ] Add ENV PATH
- [ ] Add build context comment

#### **13. `RDP/Dockerfile.controller`**
- [ ] Fix `python` → `python3` (lines 108, 114)
- [ ] Remove hardcoded ENV (lines 81-103)
- [ ] Add LABEL section (has ARG)
- [ ] Add USER 65532:65532
- [ ] Add ENV PATH
- [ ] Add build context comment

#### **14. `RDP/Dockerfile.monitor`**
- [ ] Fix `python` → `python3` (lines 110, 116)
- [ ] Remove hardcoded ENV (lines 83-105)
- [ ] Add LABEL section (has ARG)
- [ ] Add USER 65532:65532
- [ ] Add ENV PATH
- [ ] Add build context comment

#### **15. `node/Dockerfile`**
- [ ] Fix `python` → `python3` (lines 121, 127)
- [ ] Remove hardcoded ENV (lines 93-116)
- [ ] Add LABEL section (has ARG)
- [ ] Add USER 65532:65532
- [ ] Add ENV PATH
- [ ] Add build context comment

### **Phase 5: Support Services**

#### **16. `admin/Dockerfile`**
- [ ] Fix `/opt/venv/bin/python` → `/opt/venv/bin/python3` (line 123)
- [ ] Remove hardcoded ENV (lines 71-100)
- [ ] Verify LABEL uses ARG values
- [ ] Verify USER exists (uses nonroot)
- [ ] Verify PATH exists (has /opt/venv/bin)

---

## **VERIFICATION STEPS**

After applying fixes, verify each Dockerfile:

1. **Build Test:**
   ```bash
   docker buildx build --platform linux/arm64 \
     -f [Dockerfile-path] \
     --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
     --build-arg VCS_REF=$(git rev-parse --short HEAD) \
     --build-arg VERSION=1.0.0 \
     -t test-image:latest \
     .
   ```

2. **Check for:**
   - No `python` references (only `python3`)
   - No hardcoded ENV values (except PATH, PYTHON*)
   - LABEL metadata present with ARG values
   - USER 65532:65532 present
   - ENV PATH present
   - Build context comment present

3. **Spin-up Test:**
   - Verify service starts with docker-compose using .env files
   - Verify tor-proxy dependency works (depends_on: tor-proxy)
   - Verify all configuration comes from .env files

---

## **REFERENCE: COMPLIANT PATTERN**

See `auth/Dockerfile` for the complete compliant pattern:
- Lines 1-13: Header with build context
- Lines 17-19: ARG declarations
- Lines 78-96: Complete LABEL metadata
- Lines 99-123: Minimal ENV (only PATH, PYTHON*)
- Line 162: USER 65532:65532
- Line 159: HEALTHCHECK with python3
- Line 169: CMD with python3
- Lines 172-203: Configuration notes

---

## **TOR-PROXY COMPATIBILITY REQUIREMENTS**

**Critical:** All services must be compatible with `pickme/lucid-tor-proxy:latest-arm64` image.

**Requirements:**
1. **Use CMD (not ENTRYPOINT):** Allows docker-compose to override entrypoint/command
2. **Support depends_on:** Service must work with `depends_on: tor-proxy: condition: service_started`
3. **Configuration from .env:** All configuration must come from .env files, not hardcoded
4. **No hardcoded network values:** Network configuration comes from docker-compose

**Example docker-compose pattern:**
```yaml
services:
  service-name:
    image: pickme/lucid-service-name:latest-arm64
    depends_on:
      tor-proxy:
        condition: service_started
    env_file:
      - configs/environment/.env.foundation
      - configs/environment/.env.secrets
    environment:
      - SERVICE_NAME=${SERVICE_NAME}
      - PORT=${PORT}
      # ... all other config from .env files
```

---

## **ENV FILE CONFIGURATION PATHS**

All .env files are located at:
```
/mnt/myssd/Lucid/Lucid/configs/environment/
```

**Common .env files:**
- `.env.foundation` - Foundation services (mongodb, redis, elasticsearch, auth-service, tor-proxy)
- `.env.secrets` - Secrets and credentials
- `.env.core` - Core services (api-gateway, blockchain services)
- `.env.application` - Application services (sessions, RDP, node management)
- `.env.support` - Support services (admin, payment systems)

**Reference:** See `plan/constants/env_file-names.md` for complete list

---

## **BUILD COMMAND PATTERN**

All Dockerfiles should be built from project root with this pattern:

```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-[service-name]:latest-arm64 \
  -f [path/to/Dockerfile] \
  --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --build-arg VERSION=1.0.0 \
  --push \
  .
```

**Reference:** See `plan/constants/path_plan.md` lines 415-476 for examples

---

## **SUMMARY STATISTICS**

- **Total Dockerfiles to Fix:** 18
- **Critical Errors:** 6 categories
- **Priority 1 (Blocks Spin-up):** 3 categories
- **Priority 2 (Blocks .env Config):** 1 category
- **Priority 3 (Metadata Compliance):** 2 categories

**Estimated Fix Time:** 2-3 hours for all 18 files

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-01-25  
**Total Files to Fix:** 18 Dockerfiles  
**Priority:** Critical - All fixes required for Pi console deployment and tor-proxy compatibility  
**Status:** Ready for systematic application

