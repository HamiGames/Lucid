# Block Manager Container - Design & Corrections Summary

**Document Created:** 2025-12-17  
**Container:** `block-manager`  
**Image:** `pickme/lucid-block-manager:latest-arm64`  
**Port:** 8086

---

## Overview

This document summarizes the errors found and corrections applied to the `block-manager` container during the debugging and alignment process with the Lucid Dockerfile design patterns.

---

## Errors Found & Solutions Applied

### 1. Missing Module: `uvicorn`

**Error:**
```
/usr/bin/python3: No module named uvicorn
```

**Root Cause:**  
The Dockerfile was using the shared `blockchain/requirements.txt` which installed packages, but the Python path in distroless wasn't finding them. Additionally, the runtime verification and CMD used `python3` instead of `/usr/bin/python3.11`.

**Solution:**
- Created dedicated `blockchain/manager/requirements.txt` with minimal dependencies
- Updated `Dockerfile.manager` to use `/usr/bin/python3.11` for all Python commands
- Updated COPY path: `COPY blockchain/manager/requirements.txt ./requirements.txt`

**Files Modified:**
- `blockchain/manager/requirements.txt` (created)
- `blockchain/Dockerfile.manager` (line 57)

---

### 2. Dockerfile Not Following Design Pattern

**Error:**  
Multiple deviations from `dockerfile-design.md` and `Dockerfile-copy-pattern.md`

**Root Causes:**
- Builder stage used `python:3.11-slim` instead of `python:3.11-slim-bookworm`
- Builder stage used `$BUILDPLATFORM` instead of `$TARGETPLATFORM`
- Missing `async_timeout` in builder verification
- Missing directory listing in builder verification
- Runtime verification used `python3` instead of `/usr/bin/python3.11`
- HEALTHCHECK used `python3` instead of `/usr/bin/python3.11`
- CMD used `python3` instead of `/usr/bin/python3.11`
- Missing `ENTRYPOINT []` before CMD
- Missing `PYTHONIOENCODING`, `LANG`, `LC_ALL` env vars
- Copied system linkers (violates "Never" rule in design doc)

**Solution:**  
Complete rewrite of `Dockerfile.manager` to align with design patterns:

```dockerfile
# Builder stage
FROM --platform=$TARGETPLATFORM python:3.11-slim-bookworm AS builder

# Runtime stage  
FROM --platform=$TARGETPLATFORM gcr.io/distroless/python3-debian12:latest

# All Python commands use full path
RUN ["/usr/bin/python3.11", "-c", "..."]
CMD ["/usr/bin/python3.11", "/app/api/app/entrypoint_manager.py"]
```

**Files Modified:**
- `blockchain/Dockerfile.manager` (complete rewrite)

---

### 3. Missing Module: `psutil`

**Error:**
```
ModuleNotFoundError: No module named 'psutil'
```

**Root Cause:**  
The `blockchain/api/app/monitoring.py` imports `psutil` but it wasn't in the dedicated requirements file.

**Solution:**  
Added `psutil` and `prometheus-client` to `blockchain/manager/requirements.txt`:

```
# Monitoring
psutil>=5.9.0
prometheus-client>=0.19.0
```

**Files Modified:**
- `blockchain/manager/requirements.txt`

---

### 4. Health Check Failing - Connection Refused

**Error:**
```
ConnectionRefusedError: [Errno 111] Connection refused
urllib.error.URLError: <urlopen error [Errno 111] Connection refused>
```

**Root Cause:**  
The `docker-compose.core.yml` set `BLOCK_MANAGER_HOST=block-manager` which caused uvicorn to bind to the hostname instead of all interfaces. The log showed:
```
Uvicorn running on http://block-manager:8086
```

But the healthcheck tried to connect to `localhost:8086` which wasn't bound.

**Solution:**  
Changed `BLOCK_MANAGER_HOST` from `block-manager` to `0.0.0.0` in `docker-compose.core.yml`:

```yaml
# Before (incorrect)
- BLOCK_MANAGER_HOST=block-manager

# After (correct)
- BLOCK_MANAGER_HOST=0.0.0.0
```

**Explanation:**
- `BLOCK_MANAGER_HOST` is the **bind address** for uvicorn (should be `0.0.0.0`)
- `BLOCK_MANAGER_URL` is the **service URL** for external access (uses `block-manager`)

**Files Modified:**
- `configs/docker/docker-compose.core.yml` (line 282)

---

## Final Configuration

### Dockerfile.manager Key Settings

| Setting | Value |
|---------|-------|
| Builder Base | `python:3.11-slim-bookworm` |
| Runtime Base | `gcr.io/distroless/python3-debian12:latest` |
| Platform | `linux/arm64` |
| Python Path | `/usr/bin/python3.11` |
| Site Packages | `/usr/local/lib/python3.11/site-packages` |
| User | `65532:65532` |
| Entrypoint | `/app/api/app/entrypoint_manager.py` |

### docker-compose.core.yml Key Settings

| Setting | Value |
|---------|-------|
| `BLOCK_MANAGER_HOST` | `0.0.0.0` (bind address) |
| `BLOCK_MANAGER_PORT` | `8086` |
| `BLOCK_MANAGER_URL` | `http://block-manager:8086` (service URL) |

### Required Directories (Host)

| Host Path | Container Mount |
|-----------|-----------------|
| `/mnt/myssd/Lucid/Lucid/data/block-manager` | `/app/data:rw` |
| `/mnt/myssd/Lucid/Lucid/logs/block-manager` | `/app/logs:rw` |

### Required .env Files

1. `.env.secrets`
2. `.env.foundation`
3. `.env.core`

---

## Build & Launch Commands

### Rebuild Image
```bash
cd /mnt/myssd/Lucid/Lucid
docker build -f blockchain/Dockerfile.manager -t pickme/lucid-block-manager:latest-arm64 --no-cache .
```

### Launch Container
```bash
docker compose -p lucid-foundation \
  --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets \
  --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation \
  --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.core \
  -f /mnt/myssd/Lucid/Lucid/configs/docker/docker-compose.foundation.yml \
  -f /mnt/myssd/Lucid/Lucid/configs/docker/docker-compose.core.yml \
  up -d block-manager
```

### Verify Health
```bash
docker ps | grep block-manager
docker inspect --format='{{json .State.Health}}' block-manager | python3 -m json.tool
```

---

## Files Created/Modified

| File | Action | Description |
|------|--------|-------------|
| `blockchain/manager/requirements.txt` | Created | Dedicated requirements for block-manager |
| `blockchain/Dockerfile.manager` | Modified | Aligned with design patterns |
| `configs/docker/docker-compose.core.yml` | Modified | Fixed BLOCK_MANAGER_HOST |
| `blockchain/config/block-manager-config.yaml` | Existing | Configuration file |
| `blockchain/config/block-manager-config.json` | Existing | JSON configuration |
| `blockchain/config/block-manager-errors.yaml` | Existing | Error handling config |
| `blockchain/config/block-manager-logging.yaml` | Existing | Logging config |

---

## Reference Documents

- `build/docs/dockerfile-design.md` - Canonical Dockerfile pattern
- `plan/constants/Dockerfile-copy-pattern.md` - COPY pattern guide
- `blockchain/config/README-block-manager.md` - Configuration documentation

---

**Status:** ✅ Container operational  
**Maintained By:** Lucid Development Team

