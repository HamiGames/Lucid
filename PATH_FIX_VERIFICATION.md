# Pi Deployment Path Fix Verification

**Date:** 2025-10-20  
**Issue:** Deployment scripts and configs using `/mnt/myssd/Lucid/` instead of `/mnt/myssd/Lucid/Lucid/`  
**Impact:** All deployments would fail due to incorrect paths

## Problem Identified

**Pi Directory Structure:**
```
/mnt/myssd/
├── Lucid/                    <- Base mount
│   └── Lucid/               <- ACTUAL PROJECT ROOT (all files here)
│       ├── configs/
│       ├── scripts/
│       ├── database/
│       └── ... (all project files)
```

**Original Incorrect Paths:**
- Scripts referenced: `/mnt/myssd/Lucid/`
- Compose files referenced: `/mnt/myssd/Lucid/`
- Data volumes pointed to: `/mnt/myssd/Lucid/data/*`

**Result:** Docker compose would run from wrong directory, relative paths would fail

---

## Files Fixed

### ✅ Deployment Scripts (7 files)

#### scripts/deployment/deploy-phase1-pi.sh
- **Changed:** `PI_DEPLOY_DIR="/opt/lucid/production"` → `/mnt/myssd/Lucid/Lucid`
- **Changed:** Removed file copying, now verifies files exist in project dir
- **Changed:** docker-compose commands now use `configs/docker/docker-compose.foundation.yml`
- **Changed:** All hardcoded `/mnt/myssd/Lucid/` → `/mnt/myssd/Lucid/Lucid/`

#### scripts/deployment/deploy-phase2-pi.sh
- **Changed:** `PI_DEPLOY_DIR="/opt/lucid/production"` → `/mnt/myssd/Lucid/Lucid`
- **Changed:** Removed file copying, now verifies files exist
- **Changed:** docker-compose commands use full paths: `configs/docker/docker-compose.*.yml`

#### scripts/deployment/deploy-phase3-pi.sh
- **Changed:** `PI_DEPLOY_PATH="/opt/lucid/production"` → `/mnt/myssd/Lucid/Lucid`
- **Changed:** `PI_DATA_PATH="/mnt/myssd/Lucid"` → `/mnt/myssd/Lucid/Lucid`
- **Changed:** `copy_files_to_pi()` → `verify_files_on_pi()`
- **Changed:** docker-compose uses `configs/docker/$COMPOSE_FILE`

#### scripts/deployment/deploy-phase4-pi.sh
- **Changed:** `PI_DEPLOY_DIR="/opt/lucid/production"` → `/mnt/myssd/Lucid/Lucid`
- **Changed:** Removed file copying, now verifies files exist
- **Changed:** docker-compose commands use full paths

#### scripts/deployment/setup-pi-volumes.sh
- **Changed:** `LUCID_ROOT="/mnt/myssd/Lucid"` → `/mnt/myssd/Lucid/Lucid`

#### scripts/deployment/deploy-with-volumes.sh
- **Changed:** `LUCID_ROOT="/mnt/myssd/Lucid"` → `/mnt/myssd/Lucid/Lucid`

#### scripts/deployment/test-deployment-fix.sh
- **Changed:** Test path `/mnt/myssd/Lucid` → `/mnt/myssd/Lucid/Lucid`

### ✅ Foundation Scripts (2 files)

#### scripts/foundation/fix-pi-permissions.sh
- **Changed:** `PI_PATH="/mnt/myssd/Lucid"` → `/mnt/myssd/Lucid/Lucid`

#### scripts/foundation/fix-pi-ssh-permissions.sh
- **Changed:** `PI_PATH="/mnt/myssd/Lucid"` → `/mnt/myssd/Lucid/Lucid`

### ✅ Docker Compose Files (5 files)

All volume mounts updated: `/mnt/myssd/Lucid/` → `/mnt/myssd/Lucid/Lucid/`

#### configs/docker/docker-compose.foundation.yml
- MongoDB data: `/mnt/myssd/Lucid/Lucid/data/mongodb`
- Redis data: `/mnt/myssd/Lucid/Lucid/data/redis`
- Elasticsearch data: `/mnt/myssd/Lucid/Lucid/data/elasticsearch`
- Auth logs/data: `/mnt/myssd/Lucid/Lucid/logs/auth`, `/mnt/myssd/Lucid/Lucid/data/auth`

#### configs/docker/docker-compose.core.yml
- All service data directories: `/mnt/myssd/Lucid/Lucid/data/*`
- All service log directories: `/mnt/myssd/Lucid/Lucid/logs/*`

#### configs/docker/docker-compose.application.yml
- All session service paths: `/mnt/myssd/Lucid/Lucid/data/session-*`
- All RDP service paths: `/mnt/myssd/Lucid/Lucid/data/rdp-*`
- Recording paths: `/mnt/myssd/Lucid/Lucid/recordings`

#### configs/docker/docker-compose.support.yml
- Admin interface paths: `/mnt/myssd/Lucid/Lucid/data/admin-interface`
- TRON service paths: `/mnt/myssd/Lucid/Lucid/data/tron-*`

#### configs/docker/docker-compose.all.yml
- All combined service paths updated

---

## How Deployment Now Works

### Correct Flow:
1. **SSH to Pi** from Windows
2. **Navigate to:** `cd /mnt/myssd/Lucid/Lucid/` (project root on Pi)
3. **Run compose from there:** `docker-compose -f configs/docker/docker-compose.foundation.yml up -d`
4. **Relative paths work:** `./database/init_collections.js` resolves correctly
5. **Volume mounts work:** `/mnt/myssd/Lucid/Lucid/data/mongodb` is correct path

### Scripts No Longer:
- ❌ Copy files to `/opt/lucid/production/`
- ❌ Run docker-compose from `/opt/lucid/production/`
- ❌ Break on relative path references

### Scripts Now:
- ✅ Verify project exists at `/mnt/myssd/Lucid/Lucid/`
- ✅ Verify compose files exist
- ✅ Run docker-compose from project directory
- ✅ Use full paths: `configs/docker/docker-compose.*.yml`
- ✅ Relative paths in compose files work correctly

---

## Verification Commands

### On Pi (SSH: pickme@192.168.0.75)

```bash
# Verify project structure
ls -la /mnt/myssd/Lucid/Lucid/

# Verify compose files exist
ls -la /mnt/myssd/Lucid/Lucid/configs/docker/

# Verify data directories (created by scripts)
ls -la /mnt/myssd/Lucid/Lucid/data/

# Test deployment (Phase 1)
cd /mnt/myssd/Lucid/Lucid/
docker-compose -f configs/docker/docker-compose.foundation.yml pull
```

### From Windows

```bash
# Run deployment script
bash scripts/deployment/deploy-phase1-pi.sh

# Setup volume structure
bash scripts/deployment/setup-pi-volumes.sh

# Deploy with volumes
bash scripts/deployment/deploy-with-volumes.sh configs/docker/docker-compose.foundation.yml
```

---

## What Was NOT Changed

- `.devcontainer/devcontainer.json` - Updated for reference but user is NOT using devcontainer
- Documentation files (not critical for deployment)
- GitHub workflow files (those run in GitHub runners, not on Pi)

---

## Next Steps

1. ✅ **Paths are now correct** - All scripts use `/mnt/myssd/Lucid/Lucid/`
2. **Sync project to Pi** - Ensure latest code is on Pi at correct path
3. **Run deployment** - Phase deployment scripts will now work correctly

---

**Status:** ✅ PATH FIX COMPLETE  
**All deployment scripts now use:** `/mnt/myssd/Lucid/Lucid/` (correct nested path)

