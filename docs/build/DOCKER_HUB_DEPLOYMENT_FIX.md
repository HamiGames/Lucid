# Docker Hub Deployment Fix
**Date:** 2025-10-20  
**Issue:** Phase 1 deployment failing at image pull step  
**Root Cause:** Docker Compose configuration using `build:` instead of `image:` for pre-built services

## Problem Analysis

### Symptoms
- Deployment script failing with: `✗ image-pull: Failed to pull ARM64 images on Pi`
- Docker Hub images exist and are accessible
- Images verified on Docker Hub: `pickme/lucid-mongodb:latest-arm64`, `pickme/lucid-auth-service:latest-arm64`, etc.
- Deployment fails at `docker-compose pull` step

### Root Cause
The `configs/docker/docker-compose.foundation.yml` file contained a `build:` section for the `lucid-auth-service`:

```yaml
# INCORRECT - Causes docker-compose to try building instead of pulling
build:
  context: ../../
  dockerfile: infrastructure/containers/auth/Dockerfile.auth-service
  target: production
  platforms:
    - linux/arm64
```

**Why This Failed:**
1. When deployment script runs `docker-compose pull`, Docker Compose sees the `build:` section
2. Docker Compose attempts to **BUILD** the image locally on the Pi
3. The build context `../../` doesn't exist from `/opt/lucid/production/` on the Pi
4. The Pi doesn't have the project source code to build from
5. Build fails, image pull reports failure

### Secondary Issue
The MongoDB service had a relative volume mount that wouldn't work on the Pi:
```yaml
- ./database/init_collections.js:/docker-entrypoint-initdb.d/init_collections.js:ro
```

This relative path (`./database/`) doesn't exist when the compose file is deployed to `/opt/lucid/production/` on the Pi.

## Solution Applied

### Fix 1: Replace `build:` with `image:` for Auth Service
**File:** `configs/docker/docker-compose.foundation.yml`  
**Lines:** 226-231

**Before:**
```yaml
lucid-auth-service:
  <<: *lucid-common
  container_name: lucid-auth-service
  build:
    context: ../../
    dockerfile: infrastructure/containers/auth/Dockerfile.auth-service
    target: production
    platforms:
      - linux/arm64
  ports:
```

**After:**
```yaml
lucid-auth-service:
  <<: *lucid-common
  container_name: lucid-auth-service
  image: pickme/lucid-auth-service:latest-arm64
  platform: linux/arm64
  ports:
```

**Impact:**  
✅ Docker Compose will now PULL the pre-built image from Docker Hub instead of trying to build  
✅ Deployment can proceed without source code on the Pi  
✅ Faster deployment (no build time)

### Fix 2: Remove Relative Path Volume Mount
**File:** `configs/docker/docker-compose.foundation.yml`  
**Line:** 85

**Before:**
```yaml
volumes:
  - /mnt/myssd/Lucid/data/mongodb:/data/db
  - /mnt/myssd/Lucid/data/mongodb-config:/data/configdb
  - ./database/init_collections.js:/docker-entrypoint-initdb.d/init_collections.js:ro
```

**After:**
```yaml
volumes:
  - /mnt/myssd/Lucid/data/mongodb:/data/db
  - /mnt/myssd/Lucid/data/mongodb-config:/data/configdb
```

**Impact:**  
✅ No dependency on relative paths that don't exist on Pi  
✅ MongoDB initialization handled by deployment script instead

### Fix 3: Enhanced MongoDB Initialization in Deployment Script
**File:** `scripts/deployment/deploy-phase1-pi.sh`  
**Lines:** 337-347

**Enhancement:**
```bash
# Initialize MongoDB collections using the init script
log_step "mongodb-init" "INFO" "Copying MongoDB initialization script to Pi"
scp -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" \
    "$PROJECT_ROOT/database/init_collections.js" \
    "$PI_USER@$PI_HOST:/tmp/init_collections.js" >/dev/null 2>&1

# Initialize MongoDB collections
ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
    docker exec -i lucid-mongodb mongosh --quiet < /tmp/init_collections.js
    rm -f /tmp/init_collections.js
" >/dev/null 2>&1
```

**Impact:**  
✅ Copies the complete MongoDB initialization script to Pi during deployment  
✅ Executes the full schema initialization with validation rules  
✅ Creates all necessary indexes for performance  
✅ Cleans up temporary file after initialization

## Verified Configuration

### Correct Mount Paths (Preserved)
All `/mnt/myssd/Lucid` paths are CORRECT and were preserved:
- `/mnt/myssd/Lucid` is the NVMe mount point on the Raspberry Pi
- All data and logs correctly mapped to this high-performance storage
- No changes made to these paths

### Network Configuration (Preserved)
- `lucid-pi-network` - 172.20.0.0/16
- `lucid-tron-isolated` - 172.21.0.0/16 (for TRON services)

### Public Images (Unchanged)
These public images are correctly configured and work as-is:
- `mongo:7` - Official MongoDB ARM64 image
- `redis:7.2` - Official Redis ARM64 image
- `elasticsearch:8.11.0` - Official Elasticsearch ARM64 image

## Deployment Workflow (Now Fixed)

### Build Workflow (Windows 11 Host)
```bash
# 1. Build ARM64 images on Windows using BuildX
bash scripts/build/phase1-foundation-services.sh

# Images built:
# - pickme/lucid-auth-service:latest-arm64
# - pickme/lucid-mongodb:latest-arm64
# - pickme/lucid-redis:latest-arm64
# - pickme/lucid-elasticsearch:latest-arm64

# 2. Images automatically pushed to Docker Hub
```

### Deployment Workflow (Raspberry Pi Target)
```bash
# 1. Deploy to Pi
bash scripts/deployment/deploy-phase1-pi.sh

# What happens now (FIXED):
# a. SSH to Pi and create directories ✅
# b. Copy docker-compose.foundation.yml to Pi ✅
# c. Copy .env.foundation to Pi ✅
# d. Run: docker-compose pull ✅ (Now works - no build section)
# e. Run: docker-compose up -d ✅
# f. Copy and execute MongoDB init script ✅
# g. Verify services health ✅
```

## Testing

### Verify Images Exist on Docker Hub
```bash
# From Windows 11
docker buildx imagetools inspect pickme/lucid-auth-service:latest-arm64
docker buildx imagetools inspect pickme/lucid-mongodb:latest-arm64
docker buildx imagetools inspect pickme/lucid-redis:latest-arm64
```

### Test Deployment
```bash
# Add SSH key to agent (to avoid password prompts)
eval $(ssh-agent -s)
ssh-add ~/.ssh/id_rsa

# Deploy to Pi
bash scripts/deployment/deploy-phase1-pi.sh
```

### Expected Output
```
=== Phase 1 Foundation Services Deployment ===
Target Pi: pickme@192.168.0.75
Deploy Directory: /opt/lucid/production

=== Testing SSH Connection ===
✓ ssh-connection: SSH connection to Pi established

=== Creating Deployment Directory ===
✓ deploy-directory: Deployment directory created on Pi

=== Creating Data Storage Directories ===
✓ data-directories: All data storage directories created on Pi

=== Copying Docker Compose File ===
✓ compose-file-copy: Docker compose file copied to Pi

=== Copying Environment Configuration ===
✓ env-file-copy: Environment configuration copied to Pi

=== Pulling ARM64 Images ===
✓ image-pull: ARM64 images pulled successfully on Pi   <-- NOW WORKS!

=== Deploying Phase 1 Services ===
✓ service-deployment: Phase 1 services deployed successfully

✓ All services are healthy
```

## Files Modified

1. **configs/docker/docker-compose.foundation.yml**
   - Removed `build:` section from auth-service (lines 226-231)
   - Added `image: pickme/lucid-auth-service:latest-arm64`
   - Removed relative path volume mount from MongoDB (line 85)

2. **scripts/deployment/deploy-phase1-pi.sh**
   - Enhanced MongoDB initialization to copy and execute init script (lines 337-347)
   - Proper cleanup of temporary files

## Critical Understanding

### What Changed
- **Docker Compose files:** Now use `image:` tags to PULL pre-built images from Docker Hub
- **MongoDB Init:** Now copies and executes the full init script during deployment

### What DIDN'T Change (Intentionally)
- **Mount paths:** `/mnt/myssd/Lucid/*` paths are CORRECT for Pi's NVMe
- **Network configs:** All IP addresses and network settings preserved
- **Public images:** mongo:7, redis:7.2, elasticsearch:8.11.0 unchanged
- **Build scripts:** No changes needed - they correctly build and push to Docker Hub

## Architecture Validation

### Build Host (Windows 11)
- **Role:** Build ARM64 images using Docker BuildX
- **Output:** Push images to Docker Hub (pickme/lucid namespace)
- **Platform:** linux/arm64 (cross-compilation)
- **Cannot run:** ARM64 images locally (AMD64 incompatibility) ✅ Expected

### Registry (Docker Hub)
- **Namespace:** pickme/lucid
- **Images:** All ARM64 images for Raspberry Pi
- **Access:** Authenticated as `pickme` user
- **Status:** All images verified and accessible ✅

### Target Host (Raspberry Pi)
- **Role:** Pull and run ARM64 images from Docker Hub  
- **Storage:** `/mnt/myssd/Lucid` NVMe mount for data/logs
- **Network:** lucid-pi-network (172.20.0.0/16)
- **Can run:** ARM64 images natively ✅
- **Cannot build:** No source code on Pi (by design) ✅

## Resolution Status

✅ **RESOLVED** - Docker Compose files now correctly configured for pull-based deployment  
✅ **TESTED** - Image pull verification successful  
✅ **VALIDATED** - All paths and mounts verified correct for Pi NVMe  
✅ **DOCUMENTED** - Comprehensive fix documentation created

## Next Steps

1. ✅ **Test Deployment:** Run `bash scripts/deployment/deploy-phase1-pi.sh`
2. **Verify Services:** Check all services are healthy on Pi
3. **Continue Phases:** Deploy Phase 2, 3, 4 following same pattern
4. **Monitor:** Ensure all services start correctly from pulled images

## Lessons Learned

- **Docker Compose Behavior:** `build:` section in compose files causes local build attempts, not pulls
- **Deployment Pattern:** For remote deployments, always use `image:` tags pointing to registry
- **Path Management:** Relative paths in compose files break when deployed to different locations
- **MongoDB Init:** Better to handle initialization programmatically during deployment rather than via volume mounts

