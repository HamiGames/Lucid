# Dockerfile COPY Pattern Guide
## Working Pattern from Dockerfile.elasticsearch and Dockerfile.java-base

**Purpose:** This document outlines the proven working pattern for copying files and directories in multi-stage Docker builds, specifically for distroless containers. This pattern ensures reliable package and file copying by creating directories with actual content before the COPY operation.

**Last Updated:** 2025-01-21  
**Reference Files:** 
- `infrastructure/containers/database/Dockerfile.elasticsearch`
- `infrastructure/containers/base/Dockerfile.java-base`
- `auth/Dockerfile` (updated to follow this pattern)

---

## Core Principle

**The Problem:** Docker's COPY command can fail silently in distroless images when copying to directories that don't exist. The directory structure may be "closed" or not properly created before files are copied, resulting in empty or missing directories in the final image.

**The Solution:** Create files with **actual content** (not empty placeholders) in the builder stage to ensure the directory structure is "locked in" before copying. This pattern ensures Docker recognizes the directory as populated and properly creates the structure.

---

## Pattern Overview

### 1. Builder Stage: Create Content-Filled Files

**Key Pattern:** After installing packages or creating directories, create marker files with **actual content strings** (not empty files).

#### Example from Dockerfile.elasticsearch (lines 25-36):
```dockerfile
# Create custom Elasticsearch configuration
RUN echo "cluster.name: lucid-cluster\n\
node.name: lucid-node\n\
discovery.type: single-node\n\
xpack.security.enabled: false\n\
xpack.security.enrollment.enabled: false\n\
xpack.security.http.ssl.enabled: false\n\
xpack.security.transport.ssl.enabled: false\n\
bootstrap.memory_lock: true\n\
ES_JAVA_OPTS: \"-Xms512m -Xmx512m\"\n\
network.host: 0.0.0.0\n\
http.port: 9200\n\
transport.port: 9300" > /usr/share/elasticsearch/config/elasticsearch.yml
```

**Why this works:** The file contains actual configuration data, not just an empty placeholder. This ensures the directory structure exists with real content.

#### Example from Dockerfile.java-base (lines 37-39):
```dockerfile
# Create placeholder files in system directories (ensures they're baked into image)
RUN echo "LUCID_AUTH_SERVICE_RUNTIME_DIRECTORY" > /var/run/.keep && \
    echo "LUCID_AUTH_SERVICE_LIB_DIRECTORY" > /var/lib/.keep && \
    chown -R 65532:65532 /var/run /var/lib
```

**Why this works:** The files contain actual string content ("LUCID_AUTH_SERVICE_RUNTIME_DIRECTORY"), not empty files. This locks in the directory structure.

#### Example from auth/Dockerfile (lines 79-82):
```dockerfile
# Create placeholder files with actual content (ensures directory structure is locked in)
RUN echo "LUCID_AUTH_PACKAGES_INSTALLED_$(date +%s)" > /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    echo "LUCID_AUTH_BINARIES_INSTALLED_$(date +%s)" > /root/.local/bin/.lucid-marker && \
    chown -R 65532:65532 /root/.local
```

**Why this works:** Creates marker files with timestamp content after pip install, ensuring the directory structure is populated and locked in before COPY.

---

## Complete Pattern for Python Packages

### Step 1: Install Packages in Builder Stage

```dockerfile
# Ensure directory structure exists before pip install
RUN mkdir -p /root/.local/lib/python3.11/site-packages && \
    mkdir -p /root/.local/bin

# Install packages
RUN pip install --user --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --user --no-cache-dir -r requirements.txt
```

### Step 2: Create Marker Files with Content (CRITICAL)

```dockerfile
# Create placeholder files with actual content (ensures directory structure is locked in)
RUN echo "LUCID_SERVICE_PACKAGES_INSTALLED_$(date +%s)" > /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    echo "LUCID_SERVICE_BINARIES_INSTALLED_$(date +%s)" > /root/.local/bin/.lucid-marker && \
    chown -R 65532:65532 /root/.local
```

**Key Points:**
- Use `echo` with actual string content (not empty `> file`)
- Include timestamp or unique identifier to ensure content is present
- Set proper ownership (`chown`) for non-root user
- Place this **AFTER** pip install but **BEFORE** verification

### Step 3: Verify Packages (Builder Stage)

```dockerfile
# Verify packages are installed and verify directory structure
RUN python -c "import fastapi, uvicorn, motor, pymongo, cryptography, redis, jwt, bcrypt, eth_account, web3, base58, async_timeout; print('✅ critical packages installed')" && \
    python -c "import uvicorn; print('uvicorn location:', uvicorn.__file__)" && \
    test -d /root/.local/lib/python3.11/site-packages && \
    echo "Directory exists: /root/.local/lib/python3.11/site-packages" && \
    ls -la /root/.local/lib/python3.11/site-packages/ | head -20 && \
    echo "Package count: $(ls -1 /root/.local/lib/python3.11/site-packages/ | wc -l)"
```

**Key Points:**
- Import all critical packages to verify they're installed
- Check directory exists
- List contents to verify packages are present
- Include all dependencies (e.g., `async_timeout` for redis.asyncio)

### Step 4: Copy to Runtime Stage

```dockerfile
# Copy Python packages to /usr/local (SAME PATTERN AS ELASTICSEARCH - exact directory structure)
# Directory already populated with packages + marker files from builder stage
COPY --from=builder --chown=65532:65532 /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder --chown=65532:65532 /root/.local/bin /usr/local/bin
```

**Key Points:**
- Copy entire directories (not individual files)
- Use `--chown` to set proper ownership
- Directory is already populated with packages + marker files
- No need to copy marker files separately - they're included in the directory

### Step 5: Verify in Runtime Stage (CRITICAL)

```dockerfile
# Verify packages were copied (this will fail the build if packages are missing)
RUN ["/usr/bin/python3.11", "-c", "import sys; import os; site_packages = '/usr/local/lib/python3.11/site-packages'; assert os.path.exists(site_packages), f'{site_packages} does not exist'; assert os.path.exists(os.path.join(site_packages, 'uvicorn')), 'uvicorn not found'; assert os.path.exists(os.path.join(site_packages, 'redis')), 'redis not found'; assert os.path.exists(os.path.join(site_packages, 'async_timeout')) or os.path.exists(os.path.join(site_packages, 'async_timeout.py')), 'async_timeout not found'; print('Packages verified in runtime stage')"]
```

**Key Points:**
- Use distroless-compatible verification (no shell, use Python)
- Check directory exists
- Check critical packages exist
- Fail build if packages are missing (assert statements)
- This catches COPY failures immediately

---

## Pattern for System Directories

### Example: /var/run and /var/lib

```dockerfile
# Create placeholder files in system directories (ensures they're baked into image)
RUN echo "LUCID_SERVICE_RUNTIME_DIRECTORY" > /var/run/.keep && \
    echo "LUCID_SERVICE_LIB_DIRECTORY" > /var/lib/.keep && \
    chown -R 65532:65532 /var/run /var/lib
```

Then in runtime stage:
```dockerfile
# Copy runtime directories from builder
COPY --from=builder --chown=65532:65532 /var/run /var/run
COPY --from=builder --chown=65532:65532 /var/lib /var/lib
```

---

## Pattern for Configuration Files

### Example: Elasticsearch Configuration

```dockerfile
# Create custom configuration with actual content
RUN echo "cluster.name: lucid-cluster\n\
node.name: lucid-node\n\
discovery.type: single-node\n\
xpack.security.enabled: false" > /usr/share/elasticsearch/config/elasticsearch.yml
```

**Why this works:** The file contains actual configuration data, ensuring the directory structure exists with real content before COPY.

---

## Common Mistakes to Avoid

### ❌ WRONG: Empty Placeholder Files

```dockerfile
# DON'T DO THIS
RUN touch /root/.local/lib/python3.11/site-packages/.keep
# or
RUN echo "" > /root/.local/lib/python3.11/site-packages/.keep
```

**Problem:** Empty files may not properly "lock in" the directory structure. Docker might not recognize the directory as populated.

### ❌ WRONG: Copying Before Creating Content

```dockerfile
# DON'T DO THIS - copying before directory is populated
COPY --from=builder /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
# Missing: No marker files created first
```

**Problem:** If the directory doesn't exist in distroless base, COPY may fail silently or create empty directory.

### ❌ WRONG: No Verification in Runtime Stage

```dockerfile
# DON'T DO THIS - no verification after COPY
COPY --from=builder /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
# Missing: No verification step
```

**Problem:** Build succeeds but runtime fails with `ModuleNotFoundError`. No way to catch the issue during build.

### ✅ CORRECT: Content-Filled Marker Files

```dockerfile
# DO THIS - create files with actual content
RUN echo "LUCID_SERVICE_PACKAGES_INSTALLED_$(date +%s)" > /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    chown -R 65532:65532 /root/.local
```

**Why:** Actual string content ensures Docker recognizes the directory as populated.

---

## Complete Example Template

```dockerfile
# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM --platform=$BUILDPLATFORM python:3.11-slim AS builder

# ... setup environment ...

# Install packages
RUN pip install --user --no-cache-dir -r requirements.txt

# Create placeholder files with actual content (ensures directory structure is locked in)
RUN echo "LUCID_SERVICE_PACKAGES_INSTALLED_$(date +%s)" > /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    echo "LUCID_SERVICE_BINARIES_INSTALLED_$(date +%s)" > /root/.local/bin/.lucid-marker && \
    chown -R 65532:65532 /root/.local

# Verify packages are installed
RUN python -c "import package1, package2, package3; print('✅ packages installed')" && \
    test -d /root/.local/lib/python3.11/site-packages

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM --platform=$TARGETPLATFORM gcr.io/distroless/python3-debian12:latest

# ... setup environment ...

# Copy Python packages (directory already populated with packages + marker files)
COPY --from=builder --chown=65532:65532 /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder --chown=65532:65532 /root/.local/bin /usr/local/bin

# Verify packages were copied (fails build if missing)
RUN ["/usr/bin/python3.11", "-c", "import os; site_packages = '/usr/local/lib/python3.11/site-packages'; assert os.path.exists(site_packages), 'site_packages missing'; assert os.path.exists(os.path.join(site_packages, 'package1')), 'package1 not found'; print('Packages verified')"]

# ... rest of Dockerfile ...
```

---

## Key Takeaways

1. **Always create files with actual content** - not empty placeholders
2. **Create marker files AFTER package installation** - ensures directory is populated
3. **Use descriptive content strings** - helps with debugging and verification
4. **Set proper ownership** - use `chown` for non-root users
5. **Verify in both stages** - builder stage (imports) and runtime stage (file existence)
6. **Copy entire directories** - not individual files
7. **Use `--chown` in COPY** - ensures proper ownership in distroless images
8. **Fail fast** - use assertions in runtime verification to catch issues during build

---

## When to Use This Pattern

Use this pattern when:
- Building distroless containers
- Copying Python packages from builder to runtime
- Creating directories that don't exist in the base image
- Copying configuration files to new directories
- Ensuring directory structure exists before COPY operations

**Do NOT use this pattern when:**
- Directories already exist in the base image (e.g., `/usr/bin`)
- Copying to directories that are guaranteed to exist
- Using non-distroless base images with full filesystem

---

## Verification Checklist

Before finalizing a Dockerfile, verify:

- [ ] Marker files created with actual content (not empty)
- [ ] Marker files created AFTER package installation
- [ ] Proper ownership set (`chown 65532:65532` for non-root)
- [ ] Builder stage verification includes all critical packages
- [ ] Runtime stage verification checks package existence
- [ ] COPY commands use `--chown` flag
- [ ] COPY commands copy entire directories (not individual files)
- [ ] No empty placeholder files (`touch` or `echo ""`)

---

## References

- **Dockerfile.elasticsearch**: `infrastructure/containers/database/Dockerfile.elasticsearch`
- **Dockerfile.java-base**: `infrastructure/containers/base/Dockerfile.java-base`
- **auth/Dockerfile**: `auth/Dockerfile` (updated to follow this pattern)

---

**Document Status:** Active Reference  
**Maintained By:** Lucid Development Team  
**Review Frequency:** When new Dockerfile patterns are discovered or issues arise

