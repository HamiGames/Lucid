# Node-Management Container Errors Analysis

**Date:** 2025-01-27  
**Scope:** All files defining `lucid-node-management` or `node-management` containers

---

## Files Analyzed

1. `configs/docker/docker-compose.application.yml` - ✅ Already fixed
2. `node/docker-compose.yml` - ❌ Multiple errors found
3. `infrastructure/docker/compose/docker-compose.yml` - ❌ Major errors found

---

## Error Summary by File

### 1. `infrastructure/docker/compose/docker-compose.yml` (Lines 527-557)

#### ❌ CRITICAL ERRORS:

1. **Wrong Port**
   - Current: `8096:8096`
   - Should be: `8095:8095`
   - Health check also uses wrong port: `8096`

2. **Wrong Health Check Pattern**
   - Current: `["CMD", "curl", "-f", "http://localhost:8096/health"]`
   - Should be: Socket-based pattern (per master-docker-design.md)
   - Issue: `curl` doesn't work in distroless containers

3. **Missing Security Configuration**
   - Missing: `user: "65532:65532"`
   - Missing: `security_opt: ["no-new-privileges:true", "seccomp:unconfined"]`
   - Missing: `cap_drop: ["ALL"]`
   - Missing: `read_only: true`
   - Missing: `tmpfs`

4. **Missing Required Environment Variables** (per mod-design-template.md)
   - Missing: `LUCID_ENV=production`
   - Missing: `LUCID_PLATFORM=arm64`
   - Missing: `PROJECT_ROOT=/mnt/myssd/Lucid/Lucid`
   - Missing: `NODE_MANAGEMENT_HOST`
   - Missing: `NODE_MANAGEMENT_PORT`
   - Missing: `NODE_MANAGEMENT_URL`

5. **Missing Labels** (per mod-design-template.md lines 579-586)
   - Missing: `lucid.service=node-management`
   - Missing: `lucid.type=distroless`
   - Missing: `lucid.platform=arm64`
   - Missing: `lucid.security=hardened`
   - Missing: `lucid.cluster=application` (or `support`)

6. **Missing Dependencies**
   - Missing: `tor-proxy` dependency (per template line 555-556)

7. **Wrong Database URL Variable Names**
   - Uses: `MONGODB_URI` (should be `MONGODB_URL` per template)

---

### 2. `node/docker-compose.yml` (Lines 5-96)

#### ❌ ERRORS FOUND:

1. **Missing Required Environment Variables** (per mod-design-template.md lines 434-438)
   - Missing: `LUCID_ENV=production`
   - Missing: `LUCID_PLATFORM=arm64`
   - Missing: `PROJECT_ROOT=/mnt/myssd/Lucid/Lucid`

2. **Missing Standard Labels** (per mod-design-template.md lines 579-586)
   - Has: `lucid.service=node-management` ✅
   - Missing: `lucid.type=distroless` (has `lucid.security=distroless` but not standard)
   - Missing: `lucid.platform=arm64`
   - Missing: `lucid.security=hardened`
   - Missing: `lucid.cluster=support` (or `application`)

3. **Missing Dependency**
   - Missing: `tor-proxy` dependency (per template line 555-556)

4. **Wrong Database URL Variable Names**
   - Uses: `MONGODB_URI` (should also have `MONGODB_URL` per template)
   - Template uses: `MONGODB_URL` (line 446)

---

## Priority Fix Order

1. **infrastructure/docker/compose/docker-compose.yml** - CRITICAL (multiple major issues)
2. **node/docker-compose.yml** - HIGH (missing required env vars and labels)

---

## Reference Standards

- `build/docs/mod-design-template.md` - Template for all service configurations
- `build/docs/master-docker-design.md` - Universal patterns (health checks, env vars, etc.)

