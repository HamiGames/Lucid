# Data Health Check Script

## Overview

The `data-health.py` script provides comprehensive health checking for `session-anchoring` and `data-chain` services. It bypasses basic socket checks and verifies actual service operational status via HTTP `/health` endpoints.

## Location

**Script Path:** `blockchain/scripts/data-health.py`

## Usage

### Standalone Execution

```bash
# Check all services
python3 blockchain/scripts/data-health.py

# Check specific service
python3 blockchain/scripts/data-health.py session-anchoring
python3 blockchain/scripts/data-health.py data-chain
```

### Docker Healthcheck

The script is automatically mounted into containers and used for healthchecks in `docker-compose.core.yml`:

- **session-anchoring**: Uses script to check HTTP `/health` endpoint on port 8085
- **data-chain**: Uses script to check HTTP `/health` endpoint on port 8087

## Features

1. **Port Listening Check**: Verifies the service port is listening (quick check)
2. **HTTP Health Check**: Verifies the service responds correctly to `/health` endpoint (comprehensive check)
3. **Environment Variable Configuration**: Configurable via environment variables
4. **Fallback Support**: Falls back to socket check if HTTP check fails

## Configuration

The script reads configuration from environment variables:

### Session Anchoring
- `SESSION_ANCHORING_HOST` (default: `127.0.0.1`)
- `SESSION_ANCHORING_PORT` (default: `8085`)
- `SESSION_ANCHORING_HEALTH_PATH` (default: `/health`)
- `SESSION_ANCHORING_HEALTH_CHECK_TIMEOUT` (default: `10`)

### Data Chain
- `DATA_CHAIN_HOST` (default: `127.0.0.1`)
- `DATA_CHAIN_PORT` (default: `8087`)
- `DATA_CHAIN_HEALTH_PATH` (default: `/health`)
- `DATA_CHAIN_HEALTH_CHECK_TIMEOUT` (default: `10`)

## Exit Codes

- `0`: Service is healthy
- `1`: Service is unhealthy or error occurred

## Benefits

1. **No Container Rebuild Required**: Script is mounted as a volume, so updates don't require rebuilding containers
2. **Comprehensive Checking**: Verifies actual service operation, not just port listening
3. **Flexible**: Can check individual services or all services
4. **Distroless Compatible**: Works with distroless containers (no shell required)

## Integration with Docker Compose

The script is mounted to `/tmp/data-health.py` in both containers and executed via Python's `exec()` function to work around distroless container limitations (noexec on /tmp).

## Troubleshooting

### Healthcheck Failing

1. Verify the service is running:
   ```bash
   docker ps | grep -E "session-anchoring|data-chain"
   ```

2. Check service logs:
   ```bash
   docker logs session-anchoring
   docker logs data-chain
   ```

3. Test health endpoint manually:
   ```bash
   docker exec session-anchoring curl -f http://127.0.0.1:8085/health
   docker exec data-chain curl -f http://127.0.0.1:8087/health
   ```

4. Verify script is mounted:
   ```bash
   docker exec session-anchoring ls -la /tmp/data-health.py
   docker exec data-chain ls -la /tmp/data-health.py
   ```

### Script Not Found

If the script is not found, verify the mount path in `docker-compose.core.yml`:
- Host path: `/mnt/myssd/Lucid/Lucid/blockchain/scripts/data-health.py`
- Container path: `/tmp/data-health.py`

## Maintenance

To update the healthcheck logic:
1. Edit `blockchain/scripts/data-health.py`
2. Restart the affected containers:
   ```bash
   docker compose -f configs/docker/docker-compose.core.yml restart session-anchoring data-chain
   ```

No container rebuild is required!

