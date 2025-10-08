# PI MANUAL CONFIGURATION ALIGNMENT GUIDE
**Generated:** 2025-10-04 22:45:56 UTC  
**Mode:** LUCID-STRICT compliant - DISTROLESS METHOD  
**Target:** pickme@192.168.0.75 (/mnt/myssd/Lucid)  

---

## DISTROLESS METHOD OVERVIEW

This guide implements the **DISTROLESS METHOD** for enhanced security and minimal attack surface:

### **🔒 Distroless Security Benefits:**
- **Minimal Attack Surface:** No shell, package manager, or unnecessary binaries
- **Reduced Vulnerabilities:** Only application-specific dependencies included
- **Immutable Runtime:** No ability to install additional packages at runtime
- **Smaller Images:** Significantly reduced image sizes for faster deployment
- **Enhanced Security:** Containers run as non-root users with minimal privileges

### **🏗️ Distroless Implementation:**
- **Base Images:** `gcr.io/distroless/python3-debian12` and `gcr.io/distroless/base-debian12`
- **Multi-stage Builds:** Builder stage for dependencies, distroless stage for runtime
- **Static Binaries:** Only required executables copied to final image
- **Security Scanning:** Minimal CVE exposure due to reduced components

---

## CRITICAL PRE-DEPLOYMENT STEPS

### **🔴 STEP 1: Pi Environment Verification**
**Location:** SSH to `pickme@192.168.0.75`

```bash
# Connect to Pi
ssh pickme@192.168.0.75

# Verify project path exists and is writable
ls -la /mnt/myssd/Lucid
df -h /mnt/myssd

# Verify Docker is running and accessible
docker --version
docker network ls
docker ps
```

**Expected Results:**
- `/mnt/myssd/Lucid` directory exists and is accessible
- Docker version 20.10+ is running
- Sufficient disk space (>8GB available)

### **🔴 STEP 2: Git Repository Sync**
**Location:** Pi console (`/mnt/myssd/Lucid`)

```bash
cd /mnt/myssd/Lucid

# Pull latest changes from GitHub
git pull origin main

# Verify all fixes were applied
git log --oneline -3

# Check critical directories exist
ls -la 03-api-gateway/
ls -la 02-network-security/
ls -la infrastructure/compose/
```

**Expected Results:**
- Latest commits include service reference fixes
- No `03-api-gateways` directory exists (only `03-api-gateway`)
- All required directories present

### **🔴 STEP 3: Docker Network Pre-configuration**
**Location:** Pi console

```bash
# Check if external network exists
docker network ls | grep lucid

# Create external network if missing
docker network create \
  --driver bridge \
  --subnet=172.20.0.0/16 \
  --gateway=172.20.0.1 \
  lucid-dev_lucid_net

# Verify network creation
docker network inspect lucid-dev_lucid_net
```

**Expected Results:**
- `lucid-dev_lucid_net` network exists with correct subnet
- Network is attachable and accessible

### **🔴 STEP 4: Distroless Build Context Validation**
**Location:** Pi console (`/mnt/myssd/Lucid`)

```bash
# Verify all distroless build contexts exist and are accessible
test -d /mnt/myssd/Lucid/02-network-security/tor && echo "✅ Tor context OK" || echo "❌ Tor context MISSING"
test -d /mnt/myssd/Lucid/03-api-gateway/api && echo "✅ API context OK" || echo "❌ API context MISSING"
test -d /mnt/myssd/Lucid/03-api-gateway/gateway && echo "✅ Gateway context OK" || echo "❌ Gateway context MISSING"
test -d /mnt/myssd/Lucid/02-network-security/tunnels && echo "✅ Tunnels context OK" || echo "❌ Tunnels context MISSING"
test -d /mnt/myssd/Lucid/common/server-tools && echo "✅ Server-tools context OK" || echo "❌ Server-tools context MISSING"

# Verify distroless Dockerfiles exist (primary build method)
test -f 02-network-security/tor/Dockerfile.distroless && echo "✅ Tor distroless Dockerfile OK" || echo "❌ Tor distroless Dockerfile MISSING"
test -f 03-api-gateway/api/Dockerfile.distroless && echo "✅ API distroless Dockerfile OK" || echo "❌ API distroless Dockerfile MISSING"
test -f 03-api-gateway/gateway/Dockerfile.distroless && echo "✅ Gateway distroless Dockerfile OK" || echo "❌ Gateway distroless Dockerfile MISSING"
test -f 02-network-security/tunnels/Dockerfile.distroless && echo "✅ Tunnels distroless Dockerfile OK" || echo "❌ Tunnels distroless Dockerfile MISSING"

# Verify required application files exist
test -f 03-api-gateway/api/requirements.txt && echo "✅ API requirements OK"
test -f 02-network-security/tunnels/entrypoint.sh && echo "✅ Tunnels entrypoint OK"
test -f infrastructure/compose/lucid-dev.yaml && echo "✅ Compose file OK"

# Verify distroless base images are available
docker pull gcr.io/distroless/python3-debian12:latest && echo "✅ Python distroless base OK" || echo "❌ Python distroless base MISSING"
docker pull gcr.io/distroless/base-debian12:latest && echo "✅ Base distroless OK" || echo "❌ Base distroless MISSING"
```

**Expected Results:**
- All build contexts report "OK"
- All distroless Dockerfiles exist and are accessible
- Distroless base images successfully pulled
- All required application files exist

### **🔴 STEP 5: Distroless Service Configuration Validation**
**Location:** Pi console (`/mnt/myssd/Lucid`)

```bash
# Check torrc configuration for distroless compatibility
cat 02-network-security/tor/torrc | grep -A2 "HiddenServicePort"

# Verify API gateway requirements for distroless build
head -5 03-api-gateway/api/requirements.txt

# Check tunnel scripts directory for distroless entrypoint
ls -la 02-network-security/tunnels/scripts/

# Validate distroless Dockerfile syntax
docker build --dry-run -f 03-api-gateway/api/Dockerfile.distroless 03-api-gateway/api/ && echo "✅ API distroless Dockerfile OK" || echo "❌ API distroless Dockerfile ERROR"
docker build --dry-run -f 03-api-gateway/gateway/Dockerfile.distroless 03-api-gateway/gateway/ && echo "✅ Gateway distroless Dockerfile OK" || echo "❌ Gateway distroless Dockerfile ERROR"
docker build --dry-run -f 02-network-security/tunnels/Dockerfile.distroless 02-network-security/tunnels/ && echo "✅ Tunnels distroless Dockerfile OK" || echo "❌ Tunnels distroless Dockerfile ERROR"

# Validate compose file syntax with distroless images
docker-compose -f infrastructure/compose/lucid-dev.yaml config --quiet && echo "✅ Compose syntax OK" || echo "❌ Compose syntax ERROR"

# Verify distroless image references in compose file
grep -E "image: pickme/lucid:" infrastructure/compose/lucid-dev.yaml && echo "✅ Distroless images configured" || echo "❌ Distroless images MISSING"
```

**Expected Results:**
- `HiddenServicePort 80 lucid_api:8081` in torrc
- FastAPI dependencies in requirements.txt
- Tunnel scripts directory contains .sh files
- All distroless Dockerfiles pass dry-run validation
- Compose file syntax is valid
- Distroless images properly referenced in compose file

---

## STAGE 0 DEPLOYMENT EXECUTION

### **🚀 STEP 6: Distroless Image Build & Core Services Deployment**
**Location:** Pi console (`/mnt/myssd/Lucid`)

```bash
# Build distroless images for core services
echo "[distroless] Building API server distroless image..."
docker build -f 03-api-gateway/api/Dockerfile.distroless -t pickme/lucid:api-server 03-api-gateway/api/

echo "[distroless] Building API gateway distroless image..."
docker build -f 03-api-gateway/gateway/Dockerfile.distroless -t pickme/lucid:api-gateway 03-api-gateway/gateway/

echo "[distroless] Building tunnel tools distroless image..."
docker build -f 02-network-security/tunnels/Dockerfile.distroless -t pickme/lucid:tunnel-tools 02-network-security/tunnels/

echo "[distroless] Building server tools distroless image..."
docker build -f common/server-tools/Dockerfile.distroless -t pickme/lucid:server-tools common/server-tools/

# Verify distroless images were built successfully
docker images | grep "pickme/lucid" && echo "✅ Distroless images built successfully" || echo "❌ Distroless image build FAILED"

# Start Stage 0 core support services with distroless images
docker-compose -f infrastructure/compose/lucid-dev.yaml up -d

# Monitor startup progress
docker-compose -f infrastructure/compose/lucid-dev.yaml logs -f --tail=50
```

**Expected Behavior:**
- All distroless images build successfully without errors
- Services start in dependency order: mongo → tor-proxy → api → gateway → tunnels → tools
- No fatal errors in startup logs
- All containers reach "healthy" status
- Distroless containers show minimal attack surface in security scans

### **🔴 STEP 7: Distroless Service Health Verification**
**Location:** Pi console

```bash
# Wait for services to be healthy (2-3 minutes)
sleep 180

# Check all service statuses
docker-compose -f infrastructure/compose/lucid-dev.yaml ps

# Verify individual service health (distroless containers)
docker exec lucid_mongo mongosh --quiet --eval "db.runCommand({ ping: 1 })" "mongodb://lucid:lucid@localhost:27017/lucid?authSource=admin"
docker exec tor_proxy curl -s --socks5-hostname localhost:9050 http://httpbin.org/ip

# Test API health endpoints (distroless containers)
curl -s http://localhost:8081/health
curl -s http://localhost:8080/health

# Test tunnel tools health (distroless container with minimal shell)
docker exec lucid_tunnel_tools python3 /app/scripts/tunnel-manager.py health

# Verify distroless container security (no shell access)
docker exec lucid_api /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ API distroless security OK" || echo "❌ API distroless security FAILED"
docker exec lucid_api_gateway /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ Gateway distroless security OK" || echo "❌ Gateway distroless security FAILED"

# Check distroless container processes (minimal process list)
docker exec lucid_api ps aux && echo "✅ API distroless processes minimal" || echo "❌ API distroless process check FAILED"
```

**Expected Results:**
- All services show `Up X minutes (healthy)` status
- MongoDB ping returns `{ ok: 1 }`
- Tor proxy returns different IP than local
- API health endpoints return `{"ok": true}`
- Tunnel tools health check passes
- Distroless containers reject shell access attempts
- Distroless containers show minimal process lists

### **🔴 STEP 8: Network Connectivity Testing**
**Location:** Pi console

```bash
# Test internal network connectivity
docker exec lucid_server_tools /opt/lucid/scripts/network-test.sh

# Verify onion services
docker exec tor_proxy ls -la /var/lib/tor/hidden_service/
docker exec tor_proxy cat /var/lib/tor/hidden_service/hostname

# Test API through gateway
curl -s http://localhost:8080/ | jq '.'
curl -s http://localhost:8080/docs
```

**Expected Results:**
- All internal services reachable
- Onion hostname generated and accessible
- API documentation available through gateway

---

## TROUBLESHOOTING MANUAL FIXES

### **❌ Issue: Distroless Build Context Not Found**
**Symptom:** `context path does not exist` error during distroless image build
**Fix:**
```bash
# Verify you're in the correct directory
pwd  # Should be /mnt/myssd/Lucid
ls -la infrastructure/compose/lucid-dev.yaml

# Check distroless Dockerfile paths
ls -la 03-api-gateway/api/Dockerfile.distroless
ls -la 03-api-gateway/gateway/Dockerfile.distroless
ls -la 02-network-security/tunnels/Dockerfile.distroless

# Verify distroless base images are available
docker pull gcr.io/distroless/python3-debian12:latest
docker pull gcr.io/distroless/base-debian12:latest
```

### **❌ Issue: Distroless Image Build Failure**
**Symptom:** `distroless image build failed` or `executable file not found`
**Fix:**
```bash
# Check distroless Dockerfile syntax
docker build --dry-run -f 03-api-gateway/api/Dockerfile.distroless 03-api-gateway/api/

# Verify all required files are present in build context
ls -la 03-api-gateway/api/requirements.txt
ls -la 03-api-gateway/api/app/

# Check for missing dynamic libraries in distroless build
docker build -f 03-api-gateway/api/Dockerfile.distroless 03-api-gateway/api/ 2>&1 | grep -i "library"

# Rebuild with verbose output
docker build --progress=plain -f 03-api-gateway/api/Dockerfile.distroless 03-api-gateway/api/
```

### **❌ Issue: Distroless Container Runtime Errors**
**Symptom:** `executable file not found` or `permission denied` in distroless containers
**Fix:**
```bash
# Check if required binaries are copied to distroless image
docker run --rm pickme/lucid:api-server ls -la /usr/bin/curl
docker run --rm pickme/lucid:api-server ls -la /bin/nc

# Verify user permissions in distroless container
docker run --rm pickme/lucid:api-server id

# Check if entrypoint script is executable
docker run --rm pickme/lucid:api-server ls -la /usr/local/bin/python3.12

# Test distroless container with minimal command
docker run --rm pickme/lucid:api-server /usr/local/bin/python3.12 --version
```

### **❌ Issue: Network Already Exists**
**Symptom:** `network with name X already exists`
**Fix:**
```bash
# Remove existing network and recreate
docker network rm lucid-dev_lucid_net
docker network create --driver bridge --subnet=172.20.0.0/16 lucid-dev_lucid_net
```

### **❌ Issue: Service Dependencies Failed**
**Symptom:** Services exit with dependency errors
**Fix:**
```bash
# Stop all services
docker-compose -f infrastructure/compose/lucid-dev.yaml down

# Remove volumes if corrupted
docker volume rm lucid-core_mongo_data lucid-core_tor_data

# Restart with fresh volumes
docker-compose -f infrastructure/compose/lucid-dev.yaml up -d
```

### **❌ Issue: Tor Proxy Health Check Failing**
**Symptom:** `tor_proxy` container unhealthy
**Fix:**
```bash
# Check Tor logs
docker logs tor_proxy --tail=50

# Verify torrc configuration
docker exec tor_proxy cat /etc/tor/torrc

# Restart Tor service
docker-compose -f infrastructure/compose/lucid-dev.yaml restart tor-proxy
```

### **❌ Issue: API Server Not Responding**
**Symptom:** API health check returns connection refused
**Fix:**
```bash
# Check API logs for startup errors
docker logs lucid_api --tail=100

# Verify database connectivity
docker exec lucid_api curl -f http://lucid_mongo:27017/

# Check API dependencies
docker exec lucid_api python -c "import pymongo; print('MongoDB OK')"
```

---

## POST-DEPLOYMENT VALIDATION

### **✅ FINAL DISTROLESS VERIFICATION CHECKLIST**

Run these commands on Pi to ensure successful distroless deployment:

```bash
# 1. All services healthy
docker-compose -f infrastructure/compose/lucid-dev.yaml ps | grep -c "(healthy)"
# Expected: 6 (all services healthy)

# 2. External connectivity (distroless containers)
curl -f http://localhost:8080/health && echo "Gateway: OK"
curl -f http://localhost:8081/health && echo "API: OK"

# 3. Database operational
docker exec lucid_mongo mongosh --quiet --eval "db.stats()" "mongodb://lucid:lucid@localhost:27017/lucid?authSource=admin"

# 4. Tor onion services active
docker exec tor_proxy cat /var/lib/tor/hidden_service/hostname
# Expected: <16-char>.onion address

# 5. Internal network isolation
docker exec lucid_server_tools curl -f http://gateway:8080/health

# 6. Comprehensive health check
docker exec lucid_server_tools /opt/lucid/scripts/health-check.sh

# 7. Distroless security verification
echo "=== DISTROLESS SECURITY VERIFICATION ==="
docker exec lucid_api /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ API distroless: No shell access" || echo "❌ API distroless: Shell access possible"
docker exec lucid_api_gateway /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ Gateway distroless: No shell access" || echo "❌ Gateway distroless: Shell access possible"
docker exec lucid_tunnel_tools /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ Tunnels distroless: No shell access" || echo "❌ Tunnels distroless: Shell access possible"

# 8. Distroless image verification
docker images | grep "pickme/lucid" | grep -v "latest" && echo "✅ Distroless images present" || echo "❌ Distroless images missing"

# 9. Minimal attack surface verification
docker exec lucid_api ps aux | wc -l | awk '$1 < 10 {print "✅ API minimal processes: " $1} $1 >= 10 {print "❌ API too many processes: " $1}'
```

**Success Criteria:**
- 6 services showing healthy status
- Both API endpoints responding with `{"ok": true}`
- MongoDB stats return without errors
- Onion hostname generated (*.onion)
- Internal network connectivity confirmed
- All health checks pass
- **Distroless containers reject shell access attempts**
- **Distroless images are present and running**
- **Minimal process counts in distroless containers**

---

## NEXT STEPS AFTER SUCCESSFUL DEPLOYMENT

### **🎯 Ready for Stage 1 - Blockchain Group**

Once Stage 0 is verified healthy:

```bash
# Deploy Stage 1 Blockchain services
# Use the generated Pi deployment commands from:
cat progress/STAGE1_BLOCKCHAIN_PI_DEPLOYMENT_20251005-062023.md

# Execute blockchain deployment
docker-compose -f infrastructure/compose/lucid-dev.yaml --profile blockchain up -d
```

### **🔧 Monitoring Commands**

```bash
# Monitor all services
watch -n 5 'docker-compose -f infrastructure/compose/lucid-dev.yaml ps'

# View aggregated logs
docker-compose -f infrastructure/compose/lucid-dev.yaml logs -f

# Check resource usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

---

**END OF MANUAL CONFIGURATION GUIDE**

**⚠️ IMPORTANT:** Execute these steps in order. Do not proceed to Stage 1 until Stage 0 is fully validated and healthy.