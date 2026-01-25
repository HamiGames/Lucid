# Electron-GUI Distroless Build Verification Guide

**Date:** 2025-01-25  
**Status:** Fixed and aligned with project standards  
**Reference:** `plan/constants/Dockerfile-copy-pattern.md` and `build/docs/dockerfile-design.md`

---

## Build Context Requirement

All three Dockerfiles (`Dockerfile.admin`, `Dockerfile.user`, `Dockerfile.node`) **MUST** be built from the **project root** with the project root as the Docker build context.

### ✅ CORRECT: Build from Project Root

```bash
cd /mnt/myssd/Lucid/Lucid

# Build Admin interface
docker build --no-cache -f electron-gui/distroless/Dockerfile.admin \
  -t pickme/lucid-admin-interface:latest-arm64 .

# Build User interface
docker build --no-cache -f electron-gui/distroless/Dockerfile.user \
  -t pickme/lucid-user-interface:latest-arm64 .

# Build Node Operator interface
docker build --no-cache -f electron-gui/distroless/Dockerfile.node \
  -t pickme/lucid-node-interface:latest-arm64 .
```

### ❌ INCORRECT: Do NOT build from electron-gui directory

```bash
# WRONG - Don't do this!
cd /mnt/myssd/Lucid/Lucid/electron-gui
docker build -f distroless/Dockerfile.admin -t pickme/lucid-admin-interface:latest-arm64 .
```

---

## Key Improvements Applied

### 1. **Correct Build Context Paths**

All `COPY` commands now use project-root-relative paths:

```dockerfile
# ✅ CORRECT - project root relative
COPY electron-gui/package*.json ./
COPY electron-gui/main/ ./main/
COPY electron-gui/shared/ ./shared/
```

### 2. **Marker Files for Directory Integrity** (Per Dockerfile-copy-pattern.md)

Each Dockerfile now creates **contentful marker files** after npm install to ensure directory structures are "locked in" before copying to distroless:

```dockerfile
# Create marker files with actual content (ensures directory structure is locked in)
RUN echo "LUCID_ELECTRON_GUI_ADMIN_BUILT_$(date +%s)" > /build/.build-marker && \
    echo "LUCID_ELECTRON_GUI_ADMIN_PACKAGES_INSTALLED_$(date +%s)" > /build/.packages-marker
```

**Why:** Distroless images are minimal and may have "closed" directory structures. Marker files with actual content ensure Docker recognizes directories as populated before COPY operations.

### 3. **Build-Stage Verification**

Source structure is verified in the builder stage to catch issues early:

```dockerfile
RUN test -d ./main && \
    test -d ./renderer/admin && \
    test -d ./renderer/common && \
    test -d ./shared && \
    test -f .build-marker && \
    test -f .packages-marker && \
    echo "✅ Source structure verified"
```

### 4. **Runtime-Stage Verification** (Per Dockerfile-copy-pattern.md)

Marker files are copied to runtime stage and verified to ensure COPY operations succeeded:

```dockerfile
# Copy marker files to verify COPY succeeded
COPY --from=builder --chown=65532:65532 /build/.build-marker /app/.build-marker
COPY --from=builder --chown=65532:65532 /build/.packages-marker /app/.packages-marker

# Verify markers and built output
RUN test -f /app/.build-marker && \
    test -f /app/.packages-marker && \
    test -d /app/dist && \
    echo "✅ Build artifacts verified"
```

### 5. **Proper Multi-Stage Arguments**

All Dockerfiles now properly declare and pass build arguments:

```dockerfile
ARG BUILDPLATFORM=linux/amd64
ARG TARGETPLATFORM=linux/arm64
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

FROM --platform=${TARGETPLATFORM} node:18-alpine AS builder
# Arguments properly available in stage
```

### 6. **Proper Directory Ownership** (Per Dockerfile-copy-pattern.md)

All COPY operations use `--chown=65532:65532` for distroless non-root user:

```dockerfile
COPY --from=builder --chown=65532:65532 /build/dist/ ./dist/
COPY --from=builder --chown=65532:65532 /build/configs/ ./configs/
```

### 7. **Consistent Entrypoint Pattern** (Per dockerfile-design.md)

- Proper CMD with JSON format: `CMD ["/app/dist/main/index.js"]`
- User correctly set: `USER nonroot:nonroot`
- No shell required in distroless

---

## Files Modified

### 1. `electron-gui/distroless/Dockerfile.admin`
- **Lines 1-6:** Added build context documentation
- **Lines 8-12:** Proper ARG declarations
- **Lines 17:** Fixed `--platform=${TARGETPLATFORM}` syntax
- **Lines 30-35:** Fixed COPY paths (project root relative)
- **Lines 41-42:** Added marker file creation
- **Lines 53-59:** Added build-stage verification
- **Lines 87-98:** Added runtime verification
- **Line 122:** Fixed CMD to absolute path

### 2. `electron-gui/distroless/Dockerfile.user`
- Same improvements as Dockerfile.admin
- Profile-specific marker file content
- Correct port (3001) in health check

### 3. `electron-gui/distroless/Dockerfile.node`
- Same improvements as Dockerfile.admin
- Profile-specific marker file content
- Correct port (3002) in health check

---

## Alignment with Project Standards

### ✅ Aligns with `plan/constants/Dockerfile-copy-pattern.md`

- [x] Marker files created with **actual content** (not empty)
- [x] Marker files created **AFTER** package installation
- [x] Proper ownership set (`--chown=65532:65532`)
- [x] Builder stage verification includes critical checks
- [x] Runtime stage verification checks marker file existence
- [x] COPY commands use `--chown` flag
- [x] COPY commands copy entire directories
- [x] No empty placeholder files

### ✅ Aligns with `build/docs/dockerfile-design.md`

- [x] Multi-stage build pattern (builder + distroless)
- [x] Proper argument passing between stages
- [x] Selective directory COPY (not entire monorepo)
- [x] Verification in both stages
- [x] Non-root user (65532:65532)
- [x] Proper CMD format (JSON array, no shell)
- [x] ARM64-first design (`--platform=${TARGETPLATFORM}`)

---

## Build Command Reference

**File Path:** `electron-gui/distroless/build-distroless.sh`  
**Working Directory:** `/mnt/myssd/Lucid/Lucid` (project root)

### Single Container Build

```bash
# Admin interface
docker build --no-cache \
  -f electron-gui/distroless/Dockerfile.admin \
  -t pickme/lucid-admin-interface:latest-arm64 .

# User interface
docker build --no-cache \
  -f electron-gui/distroless/Dockerfile.user \
  -t pickme/lucid-user-interface:latest-arm64 .

# Node operator interface
docker build --no-cache \
  -f electron-gui/distroless/Dockerfile.node \
  -t pickme/lucid-node-interface:latest-arm64 .
```

### All Containers (via build script)

```bash
cd /mnt/myssd/Lucid/Lucid
bash electron-gui/distroless/build-distroless.sh
```

---

## Expected Build Output

### ✅ Should See

```
[builder  6/15] COPY electron-gui/jest.config.js ./
[builder  9/15] COPY electron-gui/main/ ./main/
[builder 10/15] COPY electron-gui/renderer/admin/ ./renderer/admin/
[builder 11/15] COPY electron-gui/renderer/common/ ./renderer/common/
[builder 12/15] COPY electron-gui/shared/ ./shared/
...
✅ Source structure verified
...
✅ Build artifacts verified
```

### ❌ Should NOT See

```
"/shared": not found
"failed to compute cache key"
UndefinedVar: Usage of undefined variable
```

---

## Troubleshooting

### Error: COPY fails with "not found"

**Cause:** Build context is not project root  
**Fix:** Ensure building from `/mnt/myssd/Lucid/Lucid` with `.` (dot) as context:

```bash
cd /mnt/myssd/Lucid/Lucid
docker build -f electron-gui/distroless/Dockerfile.admin -t ... .
```

### Error: "Build artifacts verified" fails

**Cause:** npm build didn't generate dist directory  
**Fix:** Check npm build script in `electron-gui/package.json`:

```bash
cat electron-gui/package.json | grep '"build'
```

### Error: Distroless base image not found

**Cause:** Network issue or registry timeout  
**Fix:** Pull the base image first:

```bash
docker pull gcr.io/distroless/nodejs18-debian11
```

---

## Verification Checklist

Before running production builds, verify:

- [ ] Building from project root (`/mnt/myssd/Lucid/Lucid`)
- [ ] All three Dockerfiles present and readable
- [ ] `electron-gui/package.json` exists and is readable
- [ ] `electron-gui/main/`, `electron-gui/shared/`, `electron-gui/renderer/` directories exist
- [ ] `electron-gui/configs/api-services*.conf` files exist
- [ ] `npm ci --only=production` completes successfully
- [ ] Build-stage verification prints "✅ Source structure verified"
- [ ] Runtime-stage verification prints "✅ Build artifacts verified"
- [ ] Final image runs and responds to health checks

---

## References

- **Build Pattern Guide:** `plan/constants/Dockerfile-copy-pattern.md`
- **Dockerfile Design:** `build/docs/dockerfile-design.md`
- **Build Script:** `electron-gui/distroless/build-distroless.sh`
- **Electron GUI Package:** `electron-gui/package.json`

---

**Maintained By:** Lucid Development Team  
**Last Updated:** 2025-01-25  
**Status:** Ready for production builds
