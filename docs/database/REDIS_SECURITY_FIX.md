# Redis Container Security Fix - Hardcoded Passwords Removed

## Date: 2025-01-24

## Summary

**ALL hardcoded passwords have been removed from the Redis container and all services that use Redis.** All components now use environment variables from `.env.*` files for secure password configuration.

## Files Fixed

### Redis Container Core Files

1. **`infrastructure/containers/database/Dockerfile.redis`**
   - **Before**: Hardcoded `requirepass lucid_redis_password` in redis.conf (line 19)
   - **Before**: Hardcoded `ENV REDIS_PASSWORD=lucid_redis_password` (line 47)
   - **Before**: Hardcoded password in healthcheck (line 57)
   - **After**: Uses Python entrypoint script that reads `REDIS_PASSWORD` from environment
   - **After**: Healthcheck uses Python script that reads `REDIS_PASSWORD` from environment
   - **After**: Template redis.conf (no password) + command-line `--requirepass` override

2. **`database/redis/start-redis.py`**
   - **Before**: Default password `'changeme'` (line 38)
   - **After**: Reads `REDIS_PASSWORD` from environment, fails fast if not set
   - **After**: Validates password is set before starting Redis

3. **`database/redis/healthcheck.py`**
   - **Before**: Default password `'changeme'` (line 24)
   - **After**: Reads `REDIS_PASSWORD` from environment
   - **After**: Proper error handling for authentication failures

4. **`configs/docker/docker-compose.foundation.yml`** (lucid-redis service)
   - **Before**: Healthcheck used `${REDIS_PASSWORD}` expansion (doesn't work in distroless)
   - **After**: Healthcheck uses Python script that reads environment variable
   - **After**: Explicit `environment` section to ensure `REDIS_PASSWORD` is passed

### Services Using Redis (RDP Services)

5. **`RDP/Dockerfile.xrdp`**
   - **Before**: `REDIS_URL=redis://lucid-redis:6379/0` (no password, line 107)
   - **After**: Removed hardcoded ENV, uses docker-compose environment variables

6. **`RDP/Dockerfile.controller`**
   - **Before**: `REDIS_URL=redis://lucid-redis:6379/0` (no password, line 93)
   - **After**: Removed hardcoded ENV, uses docker-compose environment variables

7. **`RDP/Dockerfile.server-manager`**
   - **Before**: `REDIS_URL=redis://lucid-redis:6379/0` (no password, line 97)
   - **After**: Removed hardcoded ENV, uses docker-compose environment variables

8. **`RDP/Dockerfile.monitor`**
   - **Before**: `REDIS_URL=redis://lucid-redis:6379/0` (no password, line 94)
   - **After**: Removed hardcoded ENV, uses docker-compose environment variables

9. **`RDP/Dockerfile.rdp`**
   - **Before**: `REDIS_URL=redis://lucid-redis:6379/0` (no password, line 127)
   - **After**: Removed hardcoded ENV, uses docker-compose environment variables

10. **`RDP/xrdp/main.py`**
    - **Before**: Default `REDIS_URL="redis://lucid_redis:6379/0"` (no password, line 31)
    - **After**: Empty string default, fails fast if not set via environment

11. **`RDP/server-manager/main.py`**
    - **Before**: Default `REDIS_URL="redis://lucid_redis:6379/0"` (no password, line 32)
    - **After**: Empty string default, fails fast if not set via environment

### Services Using Redis (Sessions Services)

12. **`sessions/api/Dockerfile`**
    - **Before**: `REDIS_URL=redis://lucid_redis:6379/0` (no password, line 58)
    - **After**: Removed hardcoded ENV, uses docker-compose environment variables

## Configuration Requirements

### Redis Container (`lucid-redis`)

**Environment Variables Required** (from `.env.secrets`):
- `REDIS_PASSWORD` - Password for Redis authentication (REQUIRED)

**Optional Environment Variables**:
- `REDIS_MAX_MEMORY` - Max memory limit (default: `512mb`)
- `REDIS_MAX_MEMORY_POLICY` - Eviction policy (default: `allkeys-lru`)
- `REDIS_PORT` - Redis port (default: `6379`)
- `REDIS_HOST` - Bind address (default: `0.0.0.0`)

### Services Using Redis

**All services using Redis must have `REDIS_URL` or `REDIS_URI` set in docker-compose environment:**
```yaml
environment:
  - REDIS_URL=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0
```

**Services that require this:**
- `lucid-auth-service` ✅ (already configured)
- `lucid-api-gateway` ✅ (already configured)
- RDP services (xrdp, controller, server-manager, monitor) ✅ (docker-compose.yml configured)
- Sessions services (api, processor, pipeline, storage) ✅ (docker-compose.yml configured)

## Verification

### Check Redis Password is Set

```bash
# On Pi console
grep "^REDIS_PASSWORD=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
```

### Test Redis Connection with Password

```bash
# On Pi console (get password from .env.secrets)
REDIS_PASSWORD=$(grep "^REDIS_PASSWORD=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets | cut -d= -f2)
docker exec lucid-redis /usr/bin/python3.11 /usr/local/bin/healthcheck.py
```

### Verify Services Use Environment Variables

All services should connect using `REDIS_URL` from docker-compose environment, which includes `${REDIS_PASSWORD}` from `.env.secrets`.

## Build Commands

### Rebuild Redis Container (Pi Console)

```bash
docker build --no-cache -f /mnt/myssd/Lucid/Lucid/infrastructure/containers/database/Dockerfile.redis -t pickme/lucid-redis:latest-arm64 --platform linux/arm64 /mnt/myssd/Lucid/Lucid
```

### Rebuild RDP Services (if needed)

```bash
# XRDP
docker build --no-cache -f /mnt/myssd/Lucid/Lucid/RDP/Dockerfile.xrdp -t pickme/lucid-rdp-xrdp:latest-arm64 --platform linux/arm64 /mnt/myssd/Lucid/Lucid

# Controller
docker build --no-cache -f /mnt/myssd/Lucid/Lucid/RDP/Dockerfile.controller -t pickme/lucid-rdp-controller:latest-arm64 --platform linux/arm64 /mnt/myssd/Lucid/Lucid

# Server Manager
docker build --no-cache -f /mnt/myssd/Lucid/Lucid/RDP/Dockerfile.server-manager -t pickme/lucid-rdp-server-manager:latest-arm64 --platform linux/arm64 /mnt/myssd/Lucid/Lucid

# Monitor
docker build --no-cache -f /mnt/myssd/Lucid/Lucid/RDP/Dockerfile.monitor -t pickme/lucid-rdp-monitor:latest-arm64 --platform linux/arm64 /mnt/myssd/Lucid/Lucid
```

### Rebuild Sessions API (if needed)

```bash
docker build --no-cache -f /mnt/myssd/Lucid/Lucid/sessions/api/Dockerfile -t pickme/lucid-sessions-api:latest-arm64 --platform linux/arm64 /mnt/myssd/Lucid/Lucid
```

## Status

✅ **COMPLETED**: All hardcoded Redis passwords removed  
✅ **COMPLETED**: All services use environment variables from `.env.secrets`  
✅ **COMPLETED**: Redis container uses Python entrypoint for dynamic password configuration  
✅ **COMPLETED**: All RDP Dockerfiles fixed  
✅ **COMPLETED**: All Sessions Dockerfiles fixed  
✅ **COMPLETED**: Python defaults updated to fail fast if environment variables not set

## Notes

- **No temporary fixes**: All changes are permanent and use `.env.*` file configuration
- **Fail-fast**: Services will error on startup if required environment variables are not set
- **Distroless compatible**: Redis entrypoint uses Python (distroless/python3-debian12) to handle environment variable substitution
- **Healthcheck**: Uses Python script instead of redis-cli to properly read environment variables in distroless

## Related Files

- `infrastructure/containers/database/Dockerfile.redis` - Main Redis container definition
- `database/redis/start-redis.py` - Redis entrypoint script
- `database/redis/healthcheck.py` - Redis healthcheck script
- `configs/docker/docker-compose.foundation.yml` - Docker Compose configuration
- `configs/environment/.env.secrets` - Secrets file (must exist on Pi console)

