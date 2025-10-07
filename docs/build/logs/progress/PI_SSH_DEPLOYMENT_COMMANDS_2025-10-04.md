# PI SSH DEPLOYMENT COMMANDS - LUCID-DEV REBUILD
**Generated:** 2025-10-04 11:33:18 UTC  
**Target:** pickme@192.168.0.75  
**Path:** /mnt/myssd/Lucid  
**Mode:** LUCID-STRICT compliant  

---

## COMMAND SEQUENCE FOR PI DEPLOYMENT

### 🔗 **Step 1: SSH Connection & Git Update**
```bash
# Connect to Pi
ssh pickme@192.168.0.75

# Navigate to project directory
cd /mnt/myssd/Lucid

# Pull latest changes
git pull origin main

# Verify current branch and status
git status
git log --oneline -5
```

### 🏗️ **Step 2: Rebuild lucid-dev.yaml Services**
```bash
# Stop existing services
docker-compose -f infrastructure/compose/lucid-dev.yaml down

# Pull latest images
docker-compose -f infrastructure/compose/lucid-dev.yaml pull

# Rebuild services with fresh images
docker-compose -f infrastructure/compose/lucid-dev.yaml build --no-cache

# Start services with orchestration
docker-compose -f infrastructure/compose/lucid-dev.yaml up -d --remove-orphans
```

### 🔍 **Step 3: Health Check & Verification**
```bash
# Check service status
docker-compose -f infrastructure/compose/lucid-dev.yaml ps

# Verify network connectivity
docker network ls | grep lucid

# Check service logs
docker-compose -f infrastructure/compose/lucid-dev.yaml logs --tail=50

# Health check for core services
docker-compose -f infrastructure/compose/lucid-dev.yaml exec lucid_mongo mongosh --eval "db.runCommand({ ping: 1 })"
docker-compose -f infrastructure/compose/lucid-dev.yaml exec tor-proxy curl -s --socks5-hostname localhost:9050 http://httpbin.org/ip
```

### 📤 **Step 4: Push Services to Docker Hub**
```bash
# Tag services for repository push
docker tag lucid-core_tor-proxy:latest pickme/lucid:tor-proxy-services
docker tag lucid-core_mongo:latest pickme/lucid:mongo-services
docker tag lucid-core_api-server:latest pickme/lucid:api-services
docker tag lucid-core_api-gateway:latest pickme/lucid:gateway-services
docker tag lucid-core_tunnel-tools:latest pickme/lucid:tunnel-services
docker tag lucid-core_server-tools:latest pickme/lucid:server-services

# Push services_cores aggregate
docker push pickme/lucid:services_cores

# Push individual service images
docker push pickme/lucid:tor-proxy-services
docker push pickme/lucid:mongo-services
docker push pickme/lucid:api-services
docker push pickme/lucid:gateway-services
docker push pickme/lucid:tunnel-services
docker push pickme/lucid:server-services
```

### 🎯 **Step 5: Final Verification**
```bash
# Verify all services are healthy
docker ps --filter "label=org.lucid.plane=ops" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check onion services
docker exec tor_proxy cat /var/lib/tor/onion_services/*/hostname

# Verify API endpoints
curl -s http://localhost:8080/health
curl -s http://localhost:8081/health

# Check MongoDB replica set status
docker exec lucid_mongo mongosh --eval "rs.status()"

# Exit SSH session
exit
```

---

## EXPECTED OUTPUTS

### ✅ **Successful Service Status**
```
NAME                    STATUS                   PORTS
lucid_mongo             Up X minutes (healthy)   0.0.0.0:27017->27017/tcp
tor_proxy               Up X minutes (healthy)   0.0.0.0:8888->8888/tcp, 0.0.0.0:9050->9050/tcp, 0.0.0.0:9051->9051/tcp
lucid_api               Up X minutes (healthy)   0.0.0.0:8081->8081/tcp
lucid_api_gateway       Up X minutes (healthy)   0.0.0.0:8080->8080/tcp
lucid_tunnel_tools      Up X minutes (healthy)   7000/tcp
lucid_server_tools      Up X minutes (healthy)
```

### ✅ **Health Check Responses**
```json
// http://localhost:8080/health
{"status": "healthy", "services": ["api", "mongo", "tor"]}

// http://localhost:8081/health  
{"status": "healthy", "database": "connected", "tor": "accessible"}
```

---

## TROUBLESHOOTING COMMANDS

### 🔧 **If Services Fail to Start**
```bash
# Check detailed logs
docker-compose -f infrastructure/compose/lucid-dev.yaml logs <service_name>

# Restart specific service
docker-compose -f infrastructure/compose/lucid-dev.yaml restart <service_name>

# Check disk space
df -h /mnt/myssd

# Check Docker daemon
sudo systemctl status docker

# Network diagnostics
docker network inspect lucid_core_net
```

### 🔧 **If MongoDB Issues**
```bash
# Reset MongoDB replica set
docker exec lucid_mongo mongosh --eval "rs.initiate({_id: 'rs0', members: [{_id: 0, host: 'lucid_mongo:27017'}]})"

# Check MongoDB logs
docker logs lucid_mongo --tail=100

# Verify MongoDB authentication
docker exec lucid_mongo mongosh -u lucid -p lucid --authenticationDatabase admin
```

### 🔧 **If Tor Proxy Issues**
```bash
# Check Tor configuration
docker exec tor_proxy cat /etc/tor/torrc

# Test SOCKS proxy
docker exec tor_proxy curl --socks5 127.0.0.1:9050 http://httpbin.org/ip

# Restart Tor service
docker-compose -f infrastructure/compose/lucid-dev.yaml restart tor-proxy
```

---

## ROLLBACK PROCEDURE

### 🔄 **If Deployment Fails**
```bash
# Stop all services
docker-compose -f infrastructure/compose/lucid-dev.yaml down

# Revert to previous Git commit
git log --oneline -10
git reset --hard <previous_commit_hash>

# Restore previous service state
docker-compose -f infrastructure/compose/lucid-dev.yaml up -d

# Verify rollback success
docker-compose -f infrastructure/compose/lucid-dev.yaml ps
```

---

## POST-DEPLOYMENT VALIDATION

### ✅ **Service Connectivity Matrix**
| Service | Internal Port | External Port | Health Endpoint | Status |
|---------|---------------|---------------|-----------------|--------|
| MongoDB | 27017 | 27017 | N/A (direct connection) | ✅ |
| Tor Proxy | 9050/9051 | 9050/9051 | SOCKS test | ✅ |
| API Server | 8081 | 8081 | /health | ✅ |
| API Gateway | 8080 | 8080 | /health | ✅ |
| Tunnel Tools | 7000 | Internal only | netcat test | ✅ |
| Server Tools | N/A | N/A | Process check | ✅ |

---

## NETWORK TOPOLOGY VERIFICATION

### 🌐 **SPEC-4 Compliance Check**
```bash
# Verify plane isolation
docker network inspect lucid_core_net | grep -A5 "IPAM"
docker network inspect lucid-dev_lucid_net | grep -A5 "IPAM"

# Check service labels
docker ps --filter "label=org.lucid.plane" --format "table {{.Names}}\t{{.Labels}}"

# Verify multi-onion support
docker exec tor_proxy ls -la /var/lib/tor/onion_services/
```

---

**End of Pi SSH Deployment Commands**