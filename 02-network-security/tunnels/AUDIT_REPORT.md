# Lucid Tunnel Tools Container - Audit Report

**Date:** 2025-01-27  
**Container:** `lucid-tunnel-tools`  
**Image:** `pickme/lucid-tunnel-tools:latest-arm64`  
**Status:** ⚠️ **ISSUES FOUND**

---

## Executive Summary

The `lucid-tunnel-tools` container has been audited for hardcoded defaults, import errors, incorrect syntax, and missing files. **8 critical issues** and **5 warnings** were identified that need to be addressed.

---

## ✅ Files Verified as Existing

All required files exist in the container:

- ✅ `entrypoint.py` - Main Python entrypoint
- ✅ `scripts/_lib.sh` - Shared library functions
- ✅ `scripts/create_ephemeral_onion.sh` - Onion creation script
- ✅ `scripts/create_tunnel.sh` - Tunnel creation script
- ✅ `scripts/list_tunnels.sh` - List tunnels script
- ✅ `scripts/refresh_tunnel.sh` - Refresh tunnel script
- ✅ `scripts/rotate_onion.sh` - Rotate onion script
- ✅ `scripts/teardown_tunnel.sh` - Teardown tunnel script
- ✅ `scripts/tunnel_status.sh` - Tunnel status script
- ✅ `scripts/verify_tunnel.sh` - Verify tunnel script
- ✅ `config/tunnel-config.yaml` - Configuration file
- ✅ `Dockerfile` - Container build file

**Note:** There is a duplicate `verify_tunnel.sh` file in the root directory (`02-network-security/tunnels/verify_tunnel.sh`) that is NOT copied by the Dockerfile. Only `scripts/verify_tunnel.sh` is used.

---

## ❌ Critical Issues

### 1. **Hardcoded Container Name in `_lib.sh`**

**File:** `02-network-security/tunnels/scripts/_lib.sh`  
**Lines:** 34, 39, 44  
**Issue:** Hardcoded container name `lucid_tor` should use environment variable

**Current Code:**
```bash
hex_from_cookie_in_container() {
  local container="${1:-lucid_tor}"  # ❌ Hardcoded
  ...
}

tor_ctl() {
  local container="${1:-lucid_tor}"  # ❌ Hardcoded
  ...
}

wait_bootstrap() {
  local container="${1:-lucid_tor}"  # ❌ Hardcoded
  ...
}
```

**Expected:** Container name should be `tor-proxy` (as per docker-compose.core.yml line 414) or use `TOR_CONTAINER_NAME` environment variable.

**Fix Required:**
```bash
TOR_CONTAINER_NAME="${TOR_CONTAINER_NAME:-tor-proxy}"

hex_from_cookie_in_container() {
  local container="${1:-${TOR_CONTAINER_NAME}}"
  ...
}
```

---

### 2. **Hardcoded Container Name in `create_tunnel.sh`**

**File:** `02-network-security/tunnels/scripts/create_tunnel.sh`  
**Line:** 10  
**Issue:** Hardcoded container name `lucid_tor` and default ports

**Current Code:**
```bash
CONTAINER="${1:-lucid_tor}"  # ❌ Should be tor-proxy
PORTS="${2:-80 lucid_api:4000}"  # ❌ Hardcoded service and port
```

**Expected:** Should use `tor-proxy` container name and environment variables for service/port.

**Fix Required:**
```bash
CONTAINER="${1:-${TOR_CONTAINER_NAME:-tor-proxy}}"
UPSTREAM_SERVICE="${UPSTREAM_SERVICE:-api-gateway}"
UPSTREAM_PORT="${UPSTREAM_PORT:-8080}"
PORTS="${2:-80 ${UPSTREAM_SERVICE}:${UPSTREAM_PORT}}"
```

---

### 3. **Hardcoded Authentication in `teardown_tunnel.sh`**

**File:** `02-network-security/tunnels/scripts/teardown_tunnel.sh`  
**Line:** 24  
**Issue:** Hardcoded empty authentication string `AUTHENTICATE ""`

**Current Code:**
```bash
REPLY=$(docker exec "$CONTAINER" sh -c "echo -e 'AUTHENTICATE \"\"\n$CMD\nQUIT' | nc localhost 9051")
```

**Expected:** Should use cookie-based authentication like other scripts.

**Fix Required:** Use cookie file authentication similar to `create_ephemeral_onion.sh`.

---

### 4. **Hardcoded Localhost IP in `tunnel_status.sh`**

**File:** `02-network-security/tunnels/scripts/tunnel_status.sh`  
**Line:** 21-22  
**Issue:** Hardcoded `127.0.0.1:9050` should use environment variable

**Current Code:**
```bash
echo "[tunnel_status] Testing ${URL} via SOCKS5 127.0.0.1:9050"
if curl -sS --max-time 10 --socks5-hostname 127.0.0.1:9050 "$URL" > /dev/null; then
```

**Expected:** Should use `TOR_PROXY` environment variable (set to `tor-proxy:9050` in docker-compose).

**Fix Required:**
```bash
TOR_PROXY="${TOR_PROXY:-tor-proxy:9050}"
TOR_PROXY_HOST="${TOR_PROXY%%:*}"
TOR_PROXY_PORT="${TOR_PROXY##*:}"
echo "[tunnel_status] Testing ${URL} via SOCKS5 ${TOR_PROXY_HOST}:${TOR_PROXY_PORT}"
if curl -sS --max-time 10 --socks5-hostname "${TOR_PROXY_HOST}:${TOR_PROXY_PORT}" "$URL" > /dev/null; then
```

---

### 5. **Hardcoded Defaults in `refresh_tunnel.sh`**

**File:** `02-network-security/tunnels/scripts/refresh_tunnel.sh`  
**Lines:** 10-11  
**Issue:** Hardcoded IP and service/port

**Current Code:**
```bash
HOST_IP="${HOST_IP:-127.0.0.1}"  # ❌ Should use CONTROL_HOST
PORTS="${PORTS:-80 lucid_api:8080}"  # ❌ Hardcoded service
```

**Expected:** Should use environment variables from docker-compose.

**Fix Required:**
```bash
CONTROL_HOST="${CONTROL_HOST:-tor-proxy}"
UPSTREAM_SERVICE="${UPSTREAM_SERVICE:-api-gateway}"
UPSTREAM_PORT="${UPSTREAM_PORT:-8080}"
PORTS="${PORTS:-80 ${UPSTREAM_SERVICE}:${UPSTREAM_PORT}}"
```

---

### 6. **Incorrect Path Reference in `rotate_onion.sh`**

**File:** `02-network-security/tunnels/scripts/rotate_onion.sh`  
**Line:** 8  
**Issue:** References non-existent path `../../tor/scripts/create_ephemeral_onion.sh`

**Current Code:**
```bash
CREATE_SCRIPT="${SCRIPT_DIR}/../../tor/scripts/create_ephemeral_onion.sh"
```

**Expected:** Should reference `./create_ephemeral_onion.sh` in the same directory.

**Fix Required:**
```bash
CREATE_SCRIPT="${SCRIPT_DIR}/create_ephemeral_onion.sh"
```

---

### 7. **Missing File References in `_lib.sh` and `refresh_tunnel.sh`**

**Files:** 
- `02-network-security/tunnels/scripts/_lib.sh` (line 7)
- `02-network-security/tunnels/scripts/refresh_tunnel.sh` (line 17)

**Issue:** References to `06-orchestration-runtime/compose/.env` which doesn't exist in container

**Current Code:**
```bash
# _lib.sh
ENV_FILE="$REPO_ROOT/06-orchestration-runtime/compose/.env"

# refresh_tunnel.sh
source "${ROOT_DIR}/06-orchestration-runtime/compose/.env"
```

**Expected:** Should use `WRITE_ENV` environment variable (set to `/run/lucid/onion/.onion.env` in docker-compose).

**Fix Required:**
```bash
# _lib.sh
ENV_FILE="${WRITE_ENV:-/run/lucid/onion/.onion.env}"

# refresh_tunnel.sh
ENV_FILE="${WRITE_ENV:-/run/lucid/onion/.onion.env}"
if [[ -f "$ENV_FILE" ]]; then
  source "$ENV_FILE"
fi
```

---

### 8. **Hardcoded Localhost in `create_ephemeral_onion.sh` and `rotate_onion.sh`**

**Files:**
- `02-network-security/tunnels/scripts/create_ephemeral_onion.sh` (line 8)
- `02-network-security/tunnels/scripts/rotate_onion.sh` (line 10)

**Issue:** Default `CONTROL_HOST` is `127.0.0.1` but should be `tor-proxy`

**Current Code:**
```bash
CONTROL_HOST="${CONTROL_HOST:-127.0.0.1}"  # ❌ Should be tor-proxy
```

**Expected:** Should default to `tor-proxy` as per docker-compose configuration.

**Fix Required:**
```bash
CONTROL_HOST="${CONTROL_HOST:-tor-proxy}"
```

---

## ⚠️ Warnings

### 1. **Hardcoded Service Names in Configuration**

**File:** `02-network-security/tunnels/config/tunnel-config.yaml`  
**Lines:** 26, 36, 69-70  
**Issue:** Hardcoded `lucid_api:8081` should use environment variables

**Note:** This is a configuration file, so it's acceptable, but should be documented that these are defaults.

---

### 2. **Duplicate `verify_tunnel.sh` File**

**Files:**
- `02-network-security/tunnels/verify_tunnel.sh` (root)
- `02-network-security/tunnels/scripts/verify_tunnel.sh` (scripts/)

**Issue:** Two versions exist with different implementations. Only `scripts/verify_tunnel.sh` is copied by Dockerfile.

**Recommendation:** Remove the root-level file or document which one should be used.

---

### 3. **Hardcoded Upstream Service in `create_ephemeral_onion.sh`**

**File:** `02-network-security/tunnels/scripts/create_ephemeral_onion.sh`  
**Lines:** 12-13  
**Issue:** Defaults to `lucid_api:8081` but docker-compose uses `api-gateway:8080`

**Current Code:**
```bash
UPSTREAM_SERVICE="${UPSTREAM_SERVICE:-lucid_api}"
UPSTREAM_PORT="${UPSTREAM_PORT:-8081}"
```

**Note:** This is acceptable as a default, but should align with docker-compose defaults.

---

### 4. **Python Entrypoint Uses Hardcoded Defaults**

**File:** `02-network-security/tunnels/entrypoint.py`  
**Lines:** 18-23  
**Issue:** Hardcoded defaults, but these are acceptable fallbacks

**Current Code:**
```python
CONTROL_HOST = os.getenv("CONTROL_HOST", "tor-proxy")  # ✅ Correct default
CONTROL_PORT = int(os.getenv("CONTROL_PORT", "9051"))  # ✅ Correct default
ONION_PORTS = os.getenv("ONION_PORTS", "80 api-gateway:8080")  # ✅ Correct default
```

**Status:** ✅ **ACCEPTABLE** - These defaults align with docker-compose configuration.

---

### 5. **Dockerfile Hardcoded Defaults**

**File:** `02-network-security/tunnels/Dockerfile`  
**Lines:** 113-123  
**Issue:** Hardcoded ENV defaults, but these are acceptable as they align with docker-compose

**Status:** ✅ **ACCEPTABLE** - These are fallback defaults that match docker-compose configuration.

---

## ✅ Syntax Verification

### Python Syntax
- ✅ `entrypoint.py` - **PASSED** (verified with `python3 -m py_compile`)

### Shell Script Syntax
- ✅ All shell scripts use proper shebang and `set -euo pipefail`
- ✅ No syntax errors detected

---

## 📋 Summary of Required Fixes

### High Priority (Container Functionality)
1. Fix `rotate_onion.sh` path reference (line 8)
2. Fix `_lib.sh` and `refresh_tunnel.sh` ENV file paths
3. Fix `teardown_tunnel.sh` authentication method
4. Fix hardcoded container names (`lucid_tor` → `tor-proxy`)

### Medium Priority (Configuration Alignment)
5. Fix `tunnel_status.sh` hardcoded SOCKS5 proxy
6. Fix `create_ephemeral_onion.sh` and `rotate_onion.sh` default CONTROL_HOST
7. Fix `refresh_tunnel.sh` hardcoded defaults
8. Fix `create_tunnel.sh` hardcoded container and ports

### Low Priority (Documentation)
9. Document duplicate `verify_tunnel.sh` file
10. Align default service names with docker-compose

---

## 🔍 Verification Checklist

- ✅ All Python files exist and have valid syntax
- ✅ All shell scripts exist and have valid syntax
- ✅ Dockerfile copies all required files
- ✅ Configuration file exists
- ⚠️ Some scripts reference non-existent paths
- ⚠️ Some scripts use hardcoded values instead of environment variables
- ⚠️ Container name inconsistencies (`lucid_tor` vs `tor-proxy`)

---

## 📝 Recommendations

1. **Standardize Container Names:** Use `tor-proxy` consistently (as per docker-compose)
2. **Use Environment Variables:** Replace all hardcoded defaults with environment variables
3. **Fix Path References:** Update all relative paths to match container structure
4. **Remove Duplicate Files:** Clean up duplicate `verify_tunnel.sh` file
5. **Add Validation:** Add startup validation to ensure required environment variables are set

---

**Report Generated:** 2025-01-27  
**Auditor:** Auto (Cursor AI)  
**Next Steps:** Apply fixes to all identified issues

