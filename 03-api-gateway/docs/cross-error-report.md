# Cross-Error Report: Distroless Container Module Resolution Failures

**Document Created:** 2025-01-XX  
**Containers Analyzed:** `block-manager`, `api-gateway`  
**Common Error Type:** `ModuleNotFoundError` in Python distroless runtime

---

## Executive Summary

Both the `block-manager` and `api-gateway` containers experienced `ModuleNotFoundError` exceptions during runtime startup. While the specific missing modules differed, the root cause was identical: **Python module resolution failing in distroless containers due to incorrect path configuration**.

---

## Error Comparison

| Attribute | block-manager | api-gateway |
|-----------|--------------|-------------|
| **Error Message** | `No module named uvicorn` | `No module named 'app'` |
| **Error Type** | `ModuleNotFoundError` | `ModuleNotFoundError` |
| **Stage** | Container runtime startup | Container runtime startup |
| **Python Version** | 3.11 | 3.11 |
| **Base Image** | `gcr.io/distroless/python3-debian12` | `gcr.io/distroless/python3-debian12` |

---

## Common Error Factors

### 1. PYTHONPATH Misconfiguration

**Description:** The `PYTHONPATH` environment variable did not include all directories required for Python to locate modules.

| Container | Missing Path | Required Path |
|-----------|--------------|---------------|
| block-manager | Site-packages location | `/usr/local/lib/python3.11/site-packages` |
| api-gateway | Application source | `/app/api` |

**Resolution Pattern:**
```dockerfile
ENV PYTHONPATH=/app/api:/app:/usr/local/lib/python3.11/site-packages
```

### 2. Distroless Runtime Limitations

**Description:** Distroless containers have no shell, no package managers, and minimal filesystem. This means:
- No automatic path discovery
- No shell environment to resolve paths
- Python must be explicitly told where to find modules

**Impact:**
- Standard Python path discovery mechanisms don't work
- All module locations must be explicitly declared in `PYTHONPATH`
- Builder stage paths don't automatically transfer to runtime

### 3. Multi-Stage Build Path Disconnection

**Description:** Packages installed in the builder stage at one path must be explicitly mapped to the runtime stage path.

| Stage | Package Location |
|-------|------------------|
| Builder | `/root/.local/lib/python3.11/site-packages` |
| Runtime | `/usr/local/lib/python3.11/site-packages` |

**Resolution Pattern:**
```dockerfile
# Copy packages from builder to runtime
COPY --from=builder /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Ensure PYTHONPATH includes the runtime location
ENV PYTHONPATH=/app:/usr/local/lib/python3.11/site-packages
```

### 4. Python Binary Path Differences

**Description:** The Python binary location differs between builder and distroless images.

| Image | Python Binary |
|-------|---------------|
| `python:3.11-slim-bookworm` | `python3` (in PATH) |
| `gcr.io/distroless/python3-debian12` | `/usr/bin/python3` or `/usr/bin/python3.11` |

**block-manager specific:** Used `python3` in CMD which failed; required `/usr/bin/python3.11`.

### 5. Application Source Directory Structure

**Description:** The application directory structure affects import paths.

| Container | App Structure | Import Statement | Required PYTHONPATH |
|-----------|---------------|------------------|---------------------|
| block-manager | `/app/api/app/*.py` | `from api.app.config` | `/app` |
| api-gateway | `/app/api/app/*.py` | `from app.config` | `/app/api` |

**Key Insight:** The import style (`from app.*` vs `from api.app.*`) determines which directory must be in `PYTHONPATH`.

---

## Diagnostic Pattern

When encountering `ModuleNotFoundError` in distroless containers:

### Step 1: Identify the Missing Module
```
ModuleNotFoundError: No module named 'XXX'
```

### Step 2: Determine Module Type
- **Third-party package** (uvicorn, fastapi) → Check site-packages path
- **Application module** (app, api) → Check application source path

### Step 3: Verify PYTHONPATH
```dockerfile
ENV PYTHONPATH=/path/to/app:/path/to/site-packages
```

### Step 4: Verify Directory Structure
Ensure the module exists at the expected location in the container:
```dockerfile
RUN ["python3", "-c", "import os; assert os.path.exists('/app/api/app/main.py')"]
```

---

## Prevention Checklist

When creating new distroless Python containers:

- [ ] `PYTHONPATH` includes `/usr/local/lib/python3.11/site-packages`
- [ ] `PYTHONPATH` includes application source directory (e.g., `/app/api`)
- [ ] All import statements align with `PYTHONPATH` configuration
- [ ] Builder stage packages are copied to correct runtime location
- [ ] Runtime verification step checks critical imports
- [ ] CMD uses correct Python binary path for distroless

---

## Dockerfile Pattern (Correct)

```dockerfile
# Runtime stage
FROM gcr.io/distroless/python3-debian12:latest

ENV PYTHONPATH=/app/api:/app:/usr/local/lib/python3.11/site-packages \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy packages
COPY --from=builder /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy application
COPY --from=builder /build/api /app/api

# Verify imports work
RUN ["python3", "-c", "from app.config import get_settings; print('OK')"]

CMD ["python3", "-m", "api.app.main"]
```

---

## References

- `blockchain/docs/block-manager-design.md` - Block Manager error resolution
- `build/docs/dockerfile-design.md` - Canonical Dockerfile pattern
- `plan/constants/Dockerfile-copy-pattern.md` - COPY pattern guide

---

**Status:** Active Reference  
**Maintained By:** Lucid Development Team

