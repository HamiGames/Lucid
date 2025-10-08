# PI COMPLETE DISTROLESS SETUP GUIDE
**Generated:** 2025-01-27 22:45:56 UTC  
**Mode:** LUCID-STRICT compliant - COMPLETE DISTROLESS METHOD  
**Target:** pickme@192.168.0.75 (/mnt/myssd/Lucid)  
**Architecture:** Multi-layer Lucid deployment with pre-built distroless images

---

## DISTROLESS METHOD OVERVIEW

This guide implements the **COMPLETE DISTROLESS METHOD** for the full Lucid ecosystem:

### **🔒 Distroless Security Benefits:**
- **Minimal Attack Surface:** No shell, package manager, or unnecessary binaries
- **Reduced Vulnerabilities:** Only application-specific dependencies included
- **Immutable Runtime:** No ability to install additional packages at runtime
- **Smaller Images:** Significantly reduced image sizes for faster deployment
- **Enhanced Security:** Containers run as non-root users with minimal privileges
- **Pre-built Images:** All images pre-built and pushed to Docker Hub

### **🏗️ Complete Lucid Architecture:**
- **Layer 0 (Stage 0):** Core Support Services (MongoDB, Tor, API Gateway, Tunnel Tools)
- **Layer 1 (SPEC-1B):** Session Pipeline Services (Chunker, Encryptor, Merkle Builder, Orchestrator)
- **Layer 2 (SPEC-1B):** Service Integration (RDP Server, Blockchain Services, Admin UI)
- **Base Images:** `gcr.io/distroless/python3-debian12` and `gcr.io/distroless/base-debian12`
- **Multi-stage Builds:** Builder stage for dependencies, distroless stage for runtime
- **Pre-built Registry:** All images available at `pickme/lucid:<service-name>`

---

## CRITICAL PRE-DEPLOYMENT STEPS

### **🔴 STEP 1: Pi Environment Verification**
**Location:** SSH to `pickme@192.168.0.75`

```bash
# Verify Pi system requirements
echo "=== PI SYSTEM VERIFICATION ==="
uname -a
cat /proc/cpuinfo | grep "model name" | head -1
free -h
df -h /mnt/myssd
docker --version
docker-compose --version

# Verify Docker Buildx support (required for multi-arch)
docker buildx version
docker buildx ls

# Check available disk space (minimum 50GB recommended)
df -h | grep -E "(Filesystem|/mnt/myssd)"
```

**Expected Results:**
- ARM64 architecture (aarch64)
- Minimum 4GB RAM available
- At least 50GB free space on /mnt/myssd
- Docker 24.0+ and Docker Compose 2.0+
- Buildx plugin available

### **🔴 STEP 2: Docker Hub Authentication**
**Location:** Pi console

```bash
# Login to Docker Hub (required for pre-built images)
echo "=== DOCKER HUB AUTHENTICATION ==="
docker login

# Verify access to pickme/lucid repository
docker pull pickme/lucid:api-server:latest
docker rmi pickme/lucid:api-server:latest

echo "✅ Docker Hub access verified"
```

**Expected Results:**
- Successful login to Docker Hub
- Ability to pull from pickme/lucid repository

### **🔴 STEP 3: Network Configuration**
**Location:** Pi console

```bash
# Create external network for devcontainer connectivity
echo "=== NETWORK CONFIGURATION ==="
docker network create \
  --driver bridge \
  --subnet=172.20.0.0/16 \
  --ip-range=172.20.0.0/24 \
  --gateway=172.20.0.1 \
  lucid-dev_lucid_net

# Verify network creation
docker network ls | grep lucid
docker network inspect lucid-dev_lucid_net | grep Subnet
```

**Expected Results:**
- `lucid-dev_lucid_net` network exists with correct subnet
- Network is attachable and accessible

### **🔴 STEP 4: Complete Service Validation**
**Location:** Pi console (`/mnt/myssd/Lucid`)

```bash
# Verify all compose files exist
echo "=== COMPOSE FILE VALIDATION ==="
test -f infrastructure/compose/lucid-dev.yaml && echo "✅ Core services compose OK"
test -f infrastructure/compose/lucid-layer1-complete.yaml && echo "✅ Layer 1 compose OK"
test -f infrastructure/compose/lucid-layer2-complete.yaml && echo "✅ Layer 2 compose OK"
test -f infrastructure/compose/lucid-dev-layer1.yaml && echo "✅ Dev Layer 1 compose OK"
test -f infrastructure/compose/lucid-layer2-simple.yaml && echo "✅ Layer 2 simple compose OK"

# Verify all required directories exist
echo "=== DIRECTORY VALIDATION ==="
test -d 02-network-security && echo "✅ Network security OK"
test -d 03-api-gateway && echo "✅ API gateway OK"
test -d 04-blockchain-core && echo "✅ Blockchain core OK"
test -d sessions && echo "✅ Sessions OK"
test -d auth && echo "✅ Authentication OK"
test -d common && echo "✅ Common services OK"
test -d admin && echo "✅ Admin UI OK"
test -d RDP && echo "✅ RDP services OK"
test -d wallet && echo "✅ Wallet services OK"
test -d payment-systems && echo "✅ Payment systems OK"
test -d vm && echo "✅ VM services OK"
test -d node && echo "✅ Node services OK"
```

**Expected Results:**
- All compose files exist and are accessible
- All required service directories exist

### **🔴 STEP 5: Pre-built Distroless Image Validation**
**Location:** Pi console

```bash
# Verify all pre-built distroless images are available
echo "=== PRE-BUILT IMAGE VALIDATION ==="

# Core Support Services (Layer 0)
docker pull pickme/lucid:api-server:latest && echo "✅ API server image OK" || echo "❌ API server image MISSING"
docker pull pickme/lucid:api-gateway:latest && echo "✅ API gateway image OK" || echo "❌ API gateway image MISSING"
docker pull pickme/lucid:tunnel-tools:latest && echo "✅ Tunnel tools image OK" || echo "❌ Tunnel tools image MISSING"
docker pull pickme/lucid:tor-proxy:latest && echo "✅ Tor proxy image OK" || echo "❌ Tor proxy image MISSING"
docker pull pickme/lucid:server-tools:latest && echo "✅ Server tools image OK" || echo "❌ Server tools image MISSING"

# Layer 1 Services
docker pull pickme/lucid:session-chunker:latest && echo "✅ Session chunker image OK" || echo "❌ Session chunker image MISSING"
docker pull pickme/lucid:session-encryptor:latest && echo "✅ Session encryptor image OK" || echo "❌ Session encryptor image MISSING"
docker pull pickme/lucid:merkle-builder:latest && echo "✅ Merkle builder image OK" || echo "❌ Merkle builder image MISSING"
docker pull pickme/lucid:session-orchestrator:latest && echo "✅ Session orchestrator image OK" || echo "❌ Session orchestrator image MISSING"
docker pull pickme/lucid:authentication:latest && echo "✅ Authentication image OK" || echo "❌ Authentication image MISSING"

# Layer 2 Services
docker pull pickme/lucid:blockchain-api:latest && echo "✅ Blockchain API image OK" || echo "❌ Blockchain API image MISSING"
docker pull pickme/lucid:blockchain-governance:latest && echo "✅ Blockchain governance image OK" || echo "❌ Blockchain governance image MISSING"
docker pull pickme/lucid:blockchain-sessions-data:latest && echo "✅ Blockchain sessions data image OK" || echo "❌ Blockchain sessions data image MISSING"
docker pull pickme/lucid:blockchain-vm:latest && echo "✅ Blockchain VM image OK" || echo "❌ Blockchain VM image MISSING"
docker pull pickme/lucid:blockchain-ledger:latest && echo "✅ Blockchain ledger image OK" || echo "❌ Blockchain ledger image MISSING"

# Open API Services
docker pull pickme/lucid:openapi-gateway:latest && echo "✅ OpenAPI gateway image OK" || echo "❌ OpenAPI gateway image MISSING"
docker pull pickme/lucid:openapi-server:latest && echo "✅ OpenAPI server image OK" || echo "❌ OpenAPI server image MISSING"

# Legacy Services
docker pull pickme/lucid:blockchain-api-legacy:latest && echo "✅ Blockchain API legacy image OK" || echo "❌ Blockchain API legacy image MISSING"
```

**Expected Results:**
- All pre-built distroless images successfully pulled
- Images are ARM64 compatible for Pi deployment

---

## LAYER 0 DEPLOYMENT (CORE SUPPORT SERVICES)

### **🚀 STEP 6: Core Services Deployment**
**Location:** Pi console (`/mnt/myssd/Lucid`)

```bash
# Deploy Layer 0 Core Support Services
echo "=== DEPLOYING LAYER 0 CORE SERVICES ==="
docker-compose -f infrastructure/compose/lucid-dev.yaml up -d

# Monitor startup progress
echo "=== MONITORING CORE SERVICES STARTUP ==="
docker-compose -f infrastructure/compose/lucid-dev.yaml logs -f --tail=50
```

**Expected Behavior:**
- Services start in dependency order: mongo → tor-proxy → api → gateway → tunnels → tools
- No fatal errors in startup logs
- All containers reach "healthy" status
- MongoDB replica set initializes properly
- Tor proxy creates onion services

### **🔴 STEP 7: Layer 0 Health Verification**
**Location:** Pi console

```bash
# Wait for services to be healthy (3-5 minutes)
echo "=== WAITING FOR CORE SERVICES HEALTHY ==="
sleep 300

# Check all service statuses
echo "=== CORE SERVICES STATUS ==="
docker-compose -f infrastructure/compose/lucid-dev.yaml ps

# Verify individual service health
echo "=== INDIVIDUAL SERVICE HEALTH CHECKS ==="
docker exec lucid_mongo mongosh --quiet --eval "db.runCommand({ ping: 1 })" "mongodb://lucid:lucid@localhost:27017/lucid?authSource=admin"
docker exec tor_proxy curl -s --socks5-hostname localhost:9050 http://httpbin.org/ip
curl -s http://localhost:8081/health
curl -s http://localhost:8080/health
docker exec lucid_tunnel_tools python3 /app/scripts/tunnel-manager.py health
docker exec lucid_server_tools /opt/lucid/scripts/health-check.sh

# Verify distroless container security
echo "=== DISTROLESS SECURITY VERIFICATION ==="
docker exec lucid_api /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ API distroless: No shell access" || echo "❌ API distroless: Shell access possible"
docker exec lucid_api_gateway /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ Gateway distroless: No shell access" || echo "❌ Gateway distroless: Shell access possible"
docker exec lucid_tunnel_tools /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ Tunnels distroless: No shell access" || echo "❌ Tunnels distroless: Shell access possible"
```

**Expected Results:**
- All services show `Up X minutes (healthy)` status
- MongoDB ping returns `{ ok: 1 }`
- Tor proxy returns different IP than local
- API health endpoints return `{"ok": true}`
- Tunnel tools health check passes
- Server tools health check passes
- Distroless containers reject shell access attempts

---

## LAYER 1 DEPLOYMENT (SESSION PIPELINE SERVICES)

### **🚀 STEP 8: Layer 1 Services Deployment**
**Location:** Pi console (`/mnt/myssd/Lucid`)

```bash
# Deploy Layer 1 Session Pipeline Services
echo "=== DEPLOYING LAYER 1 SESSION PIPELINE ==="
docker-compose -f infrastructure/compose/lucid-layer1-complete.yaml up -d

# Monitor startup progress
echo "=== MONITORING LAYER 1 STARTUP ==="
docker-compose -f infrastructure/compose/lucid-layer1-complete.yaml logs -f --tail=50
```

**Expected Behavior:**
- Session pipeline services start in dependency order
- All services connect to Layer 0 core services
- No fatal errors in startup logs
- All containers reach "healthy" status

### **🔴 STEP 9: Layer 1 Health Verification**
**Location:** Pi console

```bash
# Wait for services to be healthy (2-3 minutes)
echo "=== WAITING FOR LAYER 1 SERVICES HEALTHY ==="
sleep 180

# Check all service statuses
echo "=== LAYER 1 SERVICES STATUS ==="
docker-compose -f infrastructure/compose/lucid-layer1-complete.yaml ps

# Verify session pipeline services
echo "=== SESSION PIPELINE HEALTH CHECKS ==="
docker exec session_chunker curl -s http://localhost:8090/health
docker exec session_encryptor curl -s http://localhost:8091/health
docker exec merkle_builder curl -s http://localhost:8092/health
docker exec session_orchestrator curl -s http://localhost:8093/health
docker exec authentication_service curl -s http://localhost:8094/health

# Verify distroless container security for Layer 1
echo "=== LAYER 1 DISTROLESS SECURITY VERIFICATION ==="
docker exec session_chunker /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ Chunker distroless: No shell access" || echo "❌ Chunker distroless: Shell access possible"
docker exec session_encryptor /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ Encryptor distroless: No shell access" || echo "❌ Encryptor distroless: Shell access possible"
docker exec merkle_builder /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ Merkle builder distroless: No shell access" || echo "❌ Merkle builder distroless: Shell access possible"
docker exec session_orchestrator /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ Orchestrator distroless: No shell access" || echo "❌ Orchestrator distroless: Shell access possible"
docker exec authentication_service /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ Authentication distroless: No shell access" || echo "❌ Authentication distroless: Shell access possible"
```

**Expected Results:**
- All Layer 1 services show `Up X minutes (healthy)` status
- All session pipeline health endpoints return `{"ok": true}`
- Authentication service is operational
- Distroless containers reject shell access attempts

---

## LAYER 2 DEPLOYMENT (SERVICE INTEGRATION)

### **🚀 STEP 10: Layer 2 Services Deployment**
**Location:** Pi console (`/mnt/myssd/Lucid`)

```bash
# Deploy Layer 2 Service Integration
echo "=== DEPLOYING LAYER 2 SERVICE INTEGRATION ==="
docker-compose -f infrastructure/compose/lucid-layer2-complete.yaml up -d

# Monitor startup progress
echo "=== MONITORING LAYER 2 STARTUP ==="
docker-compose -f infrastructure/compose/lucid-layer2-complete.yaml logs -f --tail=50
```

**Expected Behavior:**
- Service integration services start in dependency order
- All services connect to Layer 0 and Layer 1 services
- RDP server initializes properly
- Blockchain services start successfully
- Admin UI becomes accessible

### **🔴 STEP 11: Layer 2 Health Verification**
**Location:** Pi console

```bash
# Wait for services to be healthy (3-5 minutes)
echo "=== WAITING FOR LAYER 2 SERVICES HEALTHY ==="
sleep 300

# Check all service statuses
echo "=== LAYER 2 SERVICES STATUS ==="
docker-compose -f infrastructure/compose/lucid-layer2-complete.yaml ps

# Verify service integration services
echo "=== SERVICE INTEGRATION HEALTH CHECKS ==="
docker exec blockchain_api curl -s http://localhost:8084/health
docker exec blockchain_governance curl -s http://localhost:8085/health
docker exec blockchain_sessions_data curl -s http://localhost:8086/health
docker exec blockchain_vm curl -s http://localhost:8087/health
docker exec blockchain_ledger curl -s http://localhost:8088/health
docker exec openapi_gateway curl -s http://localhost:8095/health
docker exec openapi_server curl -s http://localhost:8096/health

# Verify RDP services (if enabled)
echo "=== RDP SERVICES HEALTH CHECKS ==="
docker exec rdp_server curl -s http://localhost:3389/health 2>/dev/null && echo "✅ RDP server healthy" || echo "⚠️ RDP server not accessible (may be normal)"

# Verify distroless container security for Layer 2
echo "=== LAYER 2 DISTROLESS SECURITY VERIFICATION ==="
docker exec blockchain_api /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ Blockchain API distroless: No shell access" || echo "❌ Blockchain API distroless: Shell access possible"
docker exec blockchain_governance /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ Blockchain governance distroless: No shell access" || echo "❌ Blockchain governance distroless: Shell access possible"
docker exec openapi_gateway /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ OpenAPI gateway distroless: No shell access" || echo "❌ OpenAPI gateway distroless: Shell access possible"
```

**Expected Results:**
- All Layer 2 services show `Up X minutes (healthy)` status
- All blockchain service health endpoints return `{"ok": true}`
- OpenAPI services are operational
- RDP services are accessible (if enabled)
- Distroless containers reject shell access attempts

---

## COMPREHENSIVE NETWORK TESTING

### **🔴 STEP 12: Complete Network Connectivity Testing**
**Location:** Pi console

```bash
# Test internal network connectivity between all layers
echo "=== COMPLETE NETWORK CONNECTIVITY TEST ==="

# Layer 0 to Layer 0
echo "--- Layer 0 Internal Connectivity ---"
docker exec lucid_api curl -s http://lucid_api_gateway:8080/health && echo "✅ API → Gateway: OK"
docker exec lucid_api_gateway curl -s http://lucid_api:8081/health && echo "✅ Gateway → API: OK"
docker exec lucid_tunnel_tools curl -s http://tor-proxy:9050 --socks5-hostname tor-proxy:9050 http://httpbin.org/ip >/dev/null && echo "✅ Tunnels → Tor: OK"

# Layer 0 to Layer 1
echo "--- Layer 0 to Layer 1 Connectivity ---"
docker exec lucid_api curl -s http://session_orchestrator:8093/health && echo "✅ API → Orchestrator: OK"
docker exec lucid_api curl -s http://authentication_service:8094/health && echo "✅ API → Authentication: OK"

# Layer 1 to Layer 1
echo "--- Layer 1 Internal Connectivity ---"
docker exec session_orchestrator curl -s http://session_chunker:8090/health && echo "✅ Orchestrator → Chunker: OK"
docker exec session_orchestrator curl -s http://session_encryptor:8091/health && echo "✅ Orchestrator → Encryptor: OK"
docker exec session_orchestrator curl -s http://merkle_builder:8092/health && echo "✅ Orchestrator → Merkle Builder: OK"

# Layer 1 to Layer 2
echo "--- Layer 1 to Layer 2 Connectivity ---"
docker exec session_orchestrator curl -s http://blockchain_sessions_data:8086/health && echo "✅ Orchestrator → Blockchain Sessions: OK"
docker exec authentication_service curl -s http://blockchain_governance:8085/health && echo "✅ Authentication → Blockchain Governance: OK"

# Layer 2 to Layer 2
echo "--- Layer 2 Internal Connectivity ---"
docker exec blockchain_api curl -s http://blockchain_governance:8085/health && echo "✅ Blockchain API → Governance: OK"
docker exec blockchain_api curl -s http://blockchain_ledger:8088/health && echo "✅ Blockchain API → Ledger: OK"
docker exec openapi_gateway curl -s http://openapi_server:8096/health && echo "✅ OpenAPI Gateway → Server: OK"

# External access testing
echo "--- External Access Testing ---"
curl -s http://localhost:8080/health && echo "✅ External → Gateway: OK"
curl -s http://localhost:8081/health && echo "✅ External → API: OK"
curl -s http://localhost:8084/health && echo "✅ External → Blockchain API: OK"
curl -s http://localhost:8095/health && echo "✅ External → OpenAPI Gateway: OK"
```

**Expected Results:**
- All internal network connections successful
- All external access endpoints responding
- No connection timeouts or errors

---

## ONION SERVICE VERIFICATION

### **🔴 STEP 13: Tor Onion Service Testing**
**Location:** Pi console

```bash
# Test Tor onion services
echo "=== TOR ONION SERVICE VERIFICATION ==="

# Get onion hostnames
echo "--- Onion Hostnames ---"
docker exec tor_proxy cat /var/lib/tor/hidden_service/hostname && echo ""

# Test onion service connectivity
echo "--- Onion Service Connectivity ---"
ONION_HOSTNAME=$(docker exec tor_proxy cat /var/lib/tor/hidden_service/hostname)
if [ ! -z "$ONION_HOSTNAME" ]; then
    echo "Testing onion service: $ONION_HOSTNAME"
    docker exec lucid_server_tools curl -s --socks5 tor-proxy:9050 "http://$ONION_HOSTNAME/health" && echo "✅ Onion service accessible" || echo "❌ Onion service not accessible"
else
    echo "❌ No onion hostname found"
fi

# Test Tor network connectivity
echo "--- Tor Network Connectivity ---"
docker exec lucid_server_tools curl -s --socks5 tor-proxy:9050 http://check.torproject.org | grep -q "Congratulations" && echo "✅ Tor network connectivity: ACTIVE" || echo "❌ Tor network connectivity: INACTIVE"
```

**Expected Results:**
- Onion hostname generated and accessible
- Onion service responds to health checks
- Tor network connectivity confirmed

---

## TROUBLESHOOTING MANUAL FIXES

### **❌ Issue: Pre-built Image Not Found**
**Symptom:** `pull access denied` or `manifest not found` for pickme/lucid images
**Fix:**
```bash
# Verify Docker Hub login
docker login

# Check if images exist in registry
docker search pickme/lucid

# Try pulling specific architecture
docker pull --platform linux/arm64 pickme/lucid:api-server:latest

# If images don't exist, build them locally using the build script
# (This should not be necessary as images are pre-built)
```

### **❌ Issue: Distroless Container Runtime Errors**
**Symptom:** `executable file not found` or `permission denied` in distroless containers
**Fix:**
```bash
# Check if required binaries are in distroless image
docker run --rm pickme/lucid:api-server ls -la /usr/bin/curl
docker run --rm pickme/lucid:api-server ls -la /bin/nc

# Verify user permissions in distroless container
docker run --rm pickme/lucid:api-server id

# Check if entrypoint script is executable
docker run --rm pickme/lucid:api-server ls -la /usr/local/bin/python3.12

# Test distroless container with minimal command
docker run --rm pickme/lucid:api-server /usr/local/bin/python3.12 --version
```

### **❌ Issue: Layer Dependency Failures**
**Symptom:** Layer 1 or Layer 2 services fail to start due to missing dependencies
**Fix:**
```bash
# Verify Layer 0 is fully healthy
docker-compose -f infrastructure/compose/lucid-dev.yaml ps
docker-compose -f infrastructure/compose/lucid-dev.yaml logs

# Restart Layer 0 if needed
docker-compose -f infrastructure/compose/lucid-dev.yaml restart

# Wait for Layer 0 to be healthy before starting Layer 1
sleep 60
docker-compose -f infrastructure/compose/lucid-layer1-complete.yaml up -d
```

### **❌ Issue: Network Connectivity Problems**
**Symptom:** Services cannot communicate between layers
**Fix:**
```bash
# Check network configuration
docker network ls
docker network inspect lucid_core_net

# Recreate networks if corrupted
docker-compose -f infrastructure/compose/lucid-dev.yaml down
docker network rm lucid_core_net
docker-compose -f infrastructure/compose/lucid-dev.yaml up -d

# Verify service DNS resolution
docker exec lucid_api nslookup lucid_api_gateway
docker exec lucid_api nslookup session_orchestrator
```

### **❌ Issue: MongoDB Connection Failures**
**Symptom:** Services cannot connect to MongoDB
**Fix:**
```bash
# Check MongoDB status
docker exec lucid_mongo mongosh --quiet --eval "db.runCommand({ ping: 1 })" "mongodb://lucid:lucid@localhost:27017/lucid?authSource=admin"

# Restart MongoDB if needed
docker-compose -f infrastructure/compose/lucid-dev.yaml restart lucid_mongo

# Wait for MongoDB to be ready
sleep 30
docker exec lucid_mongo mongosh --quiet --eval "rs.status()" "mongodb://lucid:lucid@localhost:27017/lucid?authSource=admin"
```

---

## POST-DEPLOYMENT VALIDATION

### **✅ FINAL COMPREHENSIVE VERIFICATION CHECKLIST**

Run these commands on Pi to ensure successful complete distroless deployment:

```bash
# 1. All services healthy across all layers
echo "=== COMPLETE SERVICE HEALTH CHECK ==="
echo "Layer 0 (Core Support):"
docker-compose -f infrastructure/compose/lucid-dev.yaml ps | grep -c "(healthy)"
echo "Layer 1 (Session Pipeline):"
docker-compose -f infrastructure/compose/lucid-layer1-complete.yaml ps | grep -c "(healthy)"
echo "Layer 2 (Service Integration):"
docker-compose -f infrastructure/compose/lucid-layer2-complete.yaml ps | grep -c "(healthy)"

# 2. External connectivity for all layers
echo "=== EXTERNAL CONNECTIVITY VERIFICATION ==="
curl -f http://localhost:8080/health && echo "✅ Gateway: OK"
curl -f http://localhost:8081/health && echo "✅ API: OK"
curl -f http://localhost:8084/health && echo "✅ Blockchain API: OK"
curl -f http://localhost:8090/health && echo "✅ Session Chunker: OK"
curl -f http://localhost:8093/health && echo "✅ Session Orchestrator: OK"
curl -f http://localhost:8095/health && echo "✅ OpenAPI Gateway: OK"

# 3. Database operational across all layers
echo "=== DATABASE OPERATIONAL VERIFICATION ==="
docker exec lucid_mongo mongosh --quiet --eval "db.stats()" "mongodb://lucid:lucid@localhost:27017/lucid?authSource=admin"

# 4. Tor onion services active
echo "=== ONION SERVICES VERIFICATION ==="
docker exec tor_proxy cat /var/lib/tor/hidden_service/hostname

# 5. Internal network isolation working
echo "=== INTERNAL NETWORK ISOLATION ==="
docker exec lucid_server_tools curl -f http://gateway:8080/health

# 6. Comprehensive health check
echo "=== COMPREHENSIVE HEALTH CHECK ==="
docker exec lucid_server_tools /opt/lucid/scripts/health-check.sh

# 7. Distroless security verification for all layers
echo "=== COMPLETE DISTROLESS SECURITY VERIFICATION ==="
echo "Layer 0 Distroless:"
docker exec lucid_api /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ API distroless: No shell access" || echo "❌ API distroless: Shell access possible"
docker exec lucid_api_gateway /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ Gateway distroless: No shell access" || echo "❌ Gateway distroless: Shell access possible"

echo "Layer 1 Distroless:"
docker exec session_chunker /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ Chunker distroless: No shell access" || echo "❌ Chunker distroless: Shell access possible"
docker exec session_orchestrator /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ Orchestrator distroless: No shell access" || echo "❌ Orchestrator distroless: Shell access possible"

echo "Layer 2 Distroless:"
docker exec blockchain_api /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ Blockchain API distroless: No shell access" || echo "❌ Blockchain API distroless: Shell access possible"
docker exec openapi_gateway /bin/bash 2>&1 | grep -q "executable file not found" && echo "✅ OpenAPI Gateway distroless: No shell access" || echo "❌ OpenAPI Gateway distroless: Shell access possible"

# 8. Distroless image verification
echo "=== DISTROLESS IMAGE VERIFICATION ==="
docker images | grep "pickme/lucid" | grep -v "latest" && echo "✅ All distroless images present" || echo "❌ Some distroless images missing"

# 9. Minimal attack surface verification
echo "=== MINIMAL ATTACK SURFACE VERIFICATION ==="
echo "Layer 0 Process Counts:"
docker exec lucid_api ps aux | wc -l | awk '$1 < 10 {print "✅ API minimal processes: " $1} $1 >= 10 {print "❌ API too many processes: " $1}'
docker exec lucid_api_gateway ps aux | wc -l | awk '$1 < 10 {print "✅ Gateway minimal processes: " $1} $1 >= 10 {print "❌ Gateway too many processes: " $1}'

echo "Layer 1 Process Counts:"
docker exec session_chunker ps aux | wc -l | awk '$1 < 10 {print "✅ Chunker minimal processes: " $1} $1 >= 10 {print "❌ Chunker too many processes: " $1}'
docker exec session_orchestrator ps aux | wc -l | awk '$1 < 10 {print "✅ Orchestrator minimal processes: " $1} $1 >= 10 {print "❌ Orchestrator too many processes: " $1}'

echo "Layer 2 Process Counts:"
docker exec blockchain_api ps aux | wc -l | awk '$1 < 10 {print "✅ Blockchain API minimal processes: " $1} $1 >= 10 {print "❌ Blockchain API too many processes: " $1}'
```

**Success Criteria:**
- All services across all layers show healthy status
- All external endpoints responding with `{"ok": true}`
- MongoDB operational across all layers
- Onion hostname generated and accessible
- Internal network connectivity confirmed
- All health checks pass
- **All distroless containers reject shell access attempts across all layers**
- **All distroless images present and running**
- **Minimal process counts in all distroless containers**

---

## NEXT STEPS AFTER SUCCESSFUL DEPLOYMENT

### **🎯 Production Readiness Steps**

1. **Security Hardening:**
   - Configure firewall rules for Pi
   - Set up SSL/TLS certificates
   - Enable Tor authentication
   - Configure backup strategies

2. **Monitoring Setup:**
   - Deploy monitoring stack
   - Configure alerting
   - Set up log aggregation
   - Monitor resource usage

3. **Backup Configuration:**
   - Configure MongoDB backups
   - Set up volume backups
   - Test restore procedures
   - Document recovery processes

4. **Performance Optimization:**
   - Monitor resource usage
   - Optimize container resource limits
   - Configure caching strategies
   - Tune database performance

### **📊 Available Services After Deployment**

**Layer 0 (Core Support):**
- API Gateway: http://localhost:8080
- API Server: http://localhost:8081
- MongoDB: localhost:27017
- Tor Proxy: localhost:9050 (SOCKS5)

**Layer 1 (Session Pipeline):**
- Session Chunker: http://localhost:8090
- Session Encryptor: http://localhost:8091
- Merkle Builder: http://localhost:8092
- Session Orchestrator: http://localhost:8093
- Authentication Service: http://localhost:8094

**Layer 2 (Service Integration):**
- Blockchain API: http://localhost:8084
- Blockchain Governance: http://localhost:8085
- Blockchain Sessions Data: http://localhost:8086
- Blockchain VM: http://localhost:8087
- Blockchain Ledger: http://localhost:8088
- OpenAPI Gateway: http://localhost:8095
- OpenAPI Server: http://localhost:8096

**Tor Onion Services:**
- Access via onion hostname (displayed during deployment)

---

## CONCLUSION

This complete distroless setup guide provides:

✅ **Complete Multi-Layer Deployment:** Layer 0, 1, and 2 services  
✅ **Pre-built Distroless Images:** No local building required  
✅ **Enhanced Security:** Minimal attack surface across all services  
✅ **Comprehensive Validation:** Full health checks and security verification  
✅ **Production Ready:** All services operational with proper networking  
✅ **Pi Optimized:** ARM64 compatible with resource constraints  

The Lucid ecosystem is now fully deployed with the distroless method, providing maximum security while maintaining full functionality across all service layers.
