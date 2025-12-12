# Entrypoint Analysis for docker-compose.core.yml Containers

**Analysis Date:** 2025-01-24  
**File:** `configs/docker/docker-compose.core.yml`

## Summary

All 7 containers in docker-compose.core.yml **do not override entrypoint/command** - they use the CMD/ENTRYPOINT defined in their Dockerfiles. This is correct behavior.

## Container Entrypoint Details

### ✅ 1. api-gateway
- **Container Name:** `api-gateway`
- **Image:** `pickme/lucid-api-gateway:latest-arm64`
- **Dockerfile:** `03-api-gateway/Dockerfile`
- **CMD in Dockerfile:** `CMD ["python3", "-m", "api.app.main"]`
- **Docker Compose Override:** None (uses Dockerfile CMD)
- **Status:** ✅ Correct

### ✅ 2. blockchain-engine
- **Container Name:** `blockchain-engine`
- **Image:** `pickme/lucid-blockchain-engine:latest-arm64`
- **Dockerfile:** `blockchain/Dockerfile.engine`
- **CMD in Dockerfile:** `CMD ["python3", "/app/api/app/entrypoint.py"]`
- **Docker Compose Override:** None (uses Dockerfile CMD)
- **Status:** ⚠️ Note: Uses `python3` (should be `/usr/bin/python3` for consistency, but works if `python3` is in PATH)

### ✅ 3. service-mesh
- **Container Name:** `service-mesh`
- **Image:** `pickme/lucid-service-mesh-controller:latest-arm64`
- **Dockerfile:** `service-mesh/Dockerfile`
- **CMD in Dockerfile:** `CMD ["python3", "-c", "import asyncio; from controller.main import main; asyncio.run(main())"]`
- **Docker Compose Override:** None (uses Dockerfile CMD)
- **Status:** ⚠️ Note: Uses `python3` (should be `/usr/bin/python3` for consistency)

### ✅ 4. session-anchoring
- **Container Name:** `session-anchoring`
- **Image:** `pickme/lucid-session-anchoring:latest-arm64`
- **Dockerfile:** `blockchain/Dockerfile.anchoring`
- **CMD in Dockerfile:** `CMD ["/usr/bin/python3", "-c", "import os; import uvicorn; port = int(os.getenv('SESSION_ANCHORING_PORT', '8085')); host = os.getenv('SESSION_ANCHORING_HOST', '0.0.0.0'); uvicorn.run('api.app.main:app', host=host, port=port)"]`
- **Docker Compose Override:** None (uses Dockerfile CMD)
- **Status:** ✅ Correct (uses full path `/usr/bin/python3`)

### ✅ 5. block-manager
- **Container Name:** `block-manager`
- **Image:** `pickme/lucid-block-manager:latest-arm64`
- **Dockerfile:** `blockchain/Dockerfile.manager`
- **CMD in Dockerfile:** `CMD ["/usr/bin/python3", "-c", "import os; import uvicorn; port = int(os.getenv('BLOCK_MANAGER_PORT', '8086')); host = os.getenv('BLOCK_MANAGER_HOST', '0.0.0.0'); uvicorn.run('api.app.main:app', host=host, port=port)"]`
- **Docker Compose Override:** None (uses Dockerfile CMD)
- **Status:** ✅ Correct (uses full path `/usr/bin/python3`)

### ✅ 6. data-chain
- **Container Name:** `data-chain`
- **Image:** `pickme/lucid-data-chain:latest-arm64`
- **Dockerfile:** `blockchain/Dockerfile.data`
- **CMD in Dockerfile:** `CMD ["/usr/bin/python3", "-c", "import os; import uvicorn; port = int(os.getenv('DATA_CHAIN_PORT', '8087')); host = os.getenv('DATA_CHAIN_HOST', '0.0.0.0'); uvicorn.run('blockchain.data.api.main:app', host=host, port=port)"]`
- **Docker Compose Override:** None (uses Dockerfile CMD)
- **Status:** ✅ Correct (uses full path `/usr/bin/python3`)

### ✅ 7. lucid-tunnel-tools
- **Container Name:** `lucid-tunnel-tools`
- **Image:** `pickme/lucid-tunnel-tools:latest-arm64`
- **Dockerfile:** `02-network-security/tunnels/Dockerfile`
- **ENTRYPOINT in Dockerfile:** `ENTRYPOINT ["/usr/bin/tini", "--", "python3", "/app/entrypoint.py"]`
- **CMD in Dockerfile:** None (ENTRYPOINT only)
- **Docker Compose Override:** None (uses Dockerfile ENTRYPOINT)
- **Status:** ✅ Correct (uses tini for signal handling)

## Issues Found

### ⚠️ Inconsistency: Python3 Path Usage

**Issue:** Some Dockerfiles use `python3` while others use `/usr/bin/python3`.

**Affected Containers:**
1. `blockchain-engine` - Uses `python3` (should be `/usr/bin/python3`)
2. `service-mesh` - Uses `python3` (should be `/usr/bin/python3`)
3. `api-gateway` - Uses `python3` (should be `/usr/bin/python3`)

**Recommendation:** For consistency and explicit path resolution in distroless containers, all should use `/usr/bin/python3`.

**Note:** This is not a critical issue if `python3` is correctly symlinked to `/usr/bin/python3` in the distroless base image, but using full paths is more explicit and reliable.

## Recommendations

1. **All containers correctly use Dockerfile CMD/ENTRYPOINT** - No overrides needed in docker-compose
2. **Consider standardizing Python3 paths** to `/usr/bin/python3` for all containers
3. **All containers are on correct network** (`lucid-pi-network`)
4. **Health checks are correctly configured** in docker-compose.yml

## Network Configuration

All containers are correctly configured on `lucid-pi-network`:
- ✅ api-gateway
- ✅ blockchain-engine
- ✅ service-mesh
- ✅ session-anchoring
- ✅ block-manager
- ✅ data-chain
- ✅ lucid-tunnel-tools

## Endpoint References

All service URLs correctly reference container names:
- ✅ `API_GATEWAY_URL=http://api-gateway:8080`
- ✅ `BLOCKCHAIN_ENGINE_URL=http://blockchain-engine:8084`
- ✅ `SERVICE_MESH_URL=http://service-mesh:8500`
- ✅ `SESSION_ANCHORING_URL=http://session-anchoring:8085`
- ✅ `BLOCK_MANAGER_URL=http://block-manager:8086`
- ✅ `DATA_CHAIN_URL=http://data-chain:8087`
- ✅ `TOR_PROXY=tor-proxy:9050`

---

**Status:** ✅ All containers have correct entrypoint/CMD configuration  
**Action Required:** Consider standardizing Python3 paths (optional improvement)

