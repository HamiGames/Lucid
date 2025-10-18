# LUCID DISTROLESS TESTING & DEPLOYMENT PROCEDURES
## Comprehensive Testing and Multi-Staged Deployment Guide

### **Executive Summary**
This document provides detailed testing procedures and multi-staged deployment strategies for the Lucid distroless container ecosystem, ensuring reliable operation across Windows development and Raspberry Pi production environments.

---

## **PHASE 1: PRE-DEPLOYMENT TESTING**

### **1.1 Image Validation Testing**

#### **Build Verification**
```powershell
# Verify all images are built and pushed
docker buildx imagetools inspect pickme/lucid:server-tools
docker buildx imagetools inspect pickme/lucid:tor-proxy
docker buildx imagetools inspect pickme/lucid:api-server
docker buildx imagetools inspect pickme/lucid:api-gateway

# Check image sizes (should be significantly smaller than standard images)
docker images | grep pickme/lucid
```

#### **Multi-Platform Verification**
```bash
# Test ARM64 compatibility (Pi architecture)
docker run --rm --platform linux/arm64 pickme/lucid:server-tools --version
docker run --rm --platform linux/arm64 pickme/lucid:tor-proxy --version

# Test AMD64 compatibility (Windows development)
docker run --rm --platform linux/amd64 pickme/lucid:api-server --version
docker run --rm --platform linux/amd64 pickme/lucid:api-gateway --version
```

### **1.2 Security Validation**

#### **Distroless Security Checks**
```bash
# Verify no shell access (should fail)
docker run --rm pickme/lucid:api-server /bin/bash
docker run --rm pickme/lucid:tor-proxy /bin/sh

# Verify minimal attack surface
docker run --rm pickme/lucid:api-server /usr/bin/curl --version
docker run --rm pickme/lucid:tor-proxy /usr/bin/nc --version

# Check running as non-root user
docker run --rm pickme/lucid:api-server id
# Should show: uid=1000(lucid) gid=1000(lucid)
```

#### **Vulnerability Scanning**
```bash
# Scan for vulnerabilities (if trivy is available)
trivy image pickme/lucid:api-server
trivy image pickme/lucid:tor-proxy

# Compare with standard images
trivy image python:3.12-slim
trivy image nginx:alpine
```

---

## **PHASE 2: SINGLE-SERVICE TESTING**

### **2.1 Core Services Testing**

#### **MongoDB Service Test**
```bash
# Start MongoDB
docker-compose -f infrastructure/compose/docker-compose.core.yaml up -d lucid_mongo

# Wait for health check
sleep 30

# Test connection
docker exec lucid_mongo mongosh --eval "db.runCommand({ ping: 1 })"

# Test authentication
docker exec lucid_mongo mongosh -u lucid -p lucid --authenticationDatabase admin --eval "db.adminCommand('listCollections')"

# Cleanup
docker-compose -f infrastructure/compose/docker-compose.core.yaml down
```

#### **Tor Proxy Service Test**
```bash
# Start Tor proxy
docker-compose -f infrastructure/compose/docker-compose.core.yaml up -d tor-proxy

# Wait for onion creation
sleep 60

# Test SOCKS5 proxy
curl --socks5 localhost:9050 http://httpbin.org/ip

# Test HTTP proxy
curl --proxy localhost:8888 http://httpbin.org/ip

# Check onion addresses
docker exec tor-proxy ls -la /run/lucid/onion/

# Cleanup
docker-compose -f infrastructure/compose/docker-compose.core.yaml down
```

#### **API Server Test**
```bash
# Start API server with dependencies
docker-compose -f infrastructure/compose/docker-compose.core.yaml up -d

# Wait for all services to be healthy
sleep 60

# Test API endpoints
curl -f http://localhost:8081/health
curl -f http://localhost:8081/docs
curl -f http://localhost:8080/health

# Test API functionality
curl -X POST http://localhost:8081/api/test \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Cleanup
docker-compose -f infrastructure/compose/docker-compose.core.yaml down
```

### **2.2 Session Pipeline Testing**

#### **Session Chunker Test**
```bash
# Start core services first
docker-compose -f infrastructure/compose/docker-compose.core.yaml up -d

# Start session chunker
docker-compose -f infrastructure/compose/docker-compose.sessions.yaml up -d session-chunker

# Wait for health check
sleep 30

# Test chunker endpoint
curl -f http://localhost:8090/health
curl -f http://localhost:8090/status

# Test chunking functionality
curl -X POST http://localhost:8090/chunk \
  -H "Content-Type: application/json" \
  -d '{"data": "test session data", "size": 1024}'

# Cleanup
docker-compose -f infrastructure/compose/docker-compose.sessions.yaml down
docker-compose -f infrastructure/compose/docker-compose.core.yaml down
```

#### **Session Encryptor Test**
```bash
# Start dependencies
docker-compose -f infrastructure/compose/docker-compose.core.yaml up -d
docker-compose -f infrastructure/compose/docker-compose.sessions.yaml up -d session-chunker

# Start encryptor
docker-compose -f infrastructure/compose/docker-compose.sessions.yaml up -d session-encryptor

# Wait for health check
sleep 30

# Test encryption endpoint
curl -f http://localhost:8091/health
curl -f http://localhost:8091/status

# Test encryption functionality
curl -X POST http://localhost:8091/encrypt \
  -H "Content-Type: application/json" \
  -d '{"data": "sensitive data", "key": "test-key"}'

# Cleanup
docker-compose -f infrastructure/compose/docker-compose.sessions.yaml down
docker-compose -f infrastructure/compose/docker-compose.core.yaml down
```

### **2.3 Blockchain Services Testing**

#### **Blockchain API Test**
```bash
# Start core services
docker-compose -f infrastructure/compose/docker-compose.core.yaml up -d

# Start blockchain API
docker-compose -f infrastructure/compose/docker-compose.blockchain.yaml up -d blockchain_api

# Wait for health check
sleep 30

# Test blockchain endpoints
curl -f http://localhost:8084/health
curl -f http://localhost:8084/status

# Test blockchain functionality
curl -X GET http://localhost:8084/blockchain/status
curl -X POST http://localhost:8084/blockchain/transaction \
  -H "Content-Type: application/json" \
  -d '{"to": "0x123", "value": "1000"}'

# Cleanup
docker-compose -f infrastructure/compose/docker-compose.blockchain.yaml down
docker-compose -f infrastructure/compose/docker-compose.core.yaml down
```

---

## **PHASE 3: INTEGRATION TESTING**

### **3.1 Multi-Service Integration Tests**

#### **Core + Session Pipeline Integration**
```bash
# Start core services
docker-compose -f infrastructure/compose/docker-compose.core.yaml up -d

# Wait for core services to be healthy
sleep 60

# Start session pipeline
docker-compose -f infrastructure/compose/docker-compose.sessions.yaml up -d

# Wait for session services to be healthy
sleep 60

# Test end-to-end session processing
curl -X POST http://localhost:8093/orchestrator/process \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-001",
    "data": "test session data for processing",
    "chunk_size": 1024,
    "encrypt": true,
    "merkle": true
  }'

# Verify data flow
curl -f http://localhost:8090/status
curl -f http://localhost:8091/status
curl -f http://localhost:8092/status
curl -f http://localhost:8093/status

# Cleanup
docker-compose -f infrastructure/compose/docker-compose.sessions.yaml down
docker-compose -f infrastructure/compose/docker-compose.core.yaml down
```

#### **Core + Blockchain Integration**
```bash
# Start core services
docker-compose -f infrastructure/compose/docker-compose.core.yaml up -d

# Wait for core services to be healthy
sleep 60

# Start blockchain services
docker-compose -f infrastructure/compose/docker-compose.blockchain.yaml up -d

# Wait for blockchain services to be healthy
sleep 60

# Test blockchain integration
curl -X POST http://localhost:8084/blockchain/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "contract": "test-contract",
    "network": "shasta",
    "gas_limit": 1000000
  }'

# Test governance
curl -X POST http://localhost:8085/governance/proposal \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Proposal",
    "description": "Test governance proposal",
    "votes_required": 1
  }'

# Cleanup
docker-compose -f infrastructure/compose/docker-compose.blockchain.yaml down
docker-compose -f infrastructure/compose/docker-compose.core.yaml down
```

### **3.2 Full Stack Integration Test**
```bash
# Start all services in order
docker-compose -f infrastructure/compose/docker-compose.core.yaml up -d
sleep 60

docker-compose -f infrastructure/compose/docker-compose.sessions.yaml up -d
sleep 60

docker-compose -f infrastructure/compose/docker-compose.blockchain.yaml up -d
sleep 60

docker-compose -f infrastructure/compose/docker-compose.integration.yaml up -d
sleep 60

# Test complete workflow
echo "Testing complete Lucid workflow..."

# 1. Test API Gateway
curl -f http://localhost:8080/health

# 2. Test session processing
curl -X POST http://localhost:8093/orchestrator/process \
  -H "Content-Type: application/json" \
  -d '{"session_id": "full-test", "data": "complete test data"}'

# 3. Test blockchain operations
curl -X GET http://localhost:8084/blockchain/status

# 4. Test OpenAPI
curl -f http://localhost:8095/health
curl -f http://localhost:8096/health

# 5. Test Admin UI
curl -f http://localhost:8097/health

# Cleanup all services
docker-compose -f infrastructure/compose/docker-compose.integration.yaml down
docker-compose -f infrastructure/compose/docker-compose.blockchain.yaml down
docker-compose -f infrastructure/compose/docker-compose.sessions.yaml down
docker-compose -f infrastructure/compose/docker-compose.core.yaml down
```

---

## **PHASE 4: MULTI-STAGED DEPLOYMENT TESTING**

### **4.1 Staged Deployment Procedure**

#### **Stage 1: Core Infrastructure**
```bash
# Deploy core services
docker-compose -f infrastructure/compose/docker-compose.core.yaml up -d

# Wait and verify
sleep 60
docker-compose -f infrastructure/compose/docker-compose.core.yaml ps

# Health checks
curl -f http://localhost:8080/health  # API Gateway
curl -f http://localhost:8081/health  # API Server
curl --socks5 localhost:9050 http://httpbin.org/ip  # Tor Proxy

echo "Stage 1: Core services deployed and healthy"
```

#### **Stage 2: Session Pipeline**
```bash
# Deploy session services
docker-compose -f infrastructure/compose/docker-compose.sessions.yaml up -d

# Wait and verify
sleep 60
docker-compose -f infrastructure/compose/docker-compose.sessions.yaml ps

# Health checks
curl -f http://localhost:8090/health  # Session Chunker
curl -f http://localhost:8091/health  # Session Encryptor
curl -f http://localhost:8092/health  # Merkle Builder
curl -f http://localhost:8093/health  # Session Orchestrator

echo "Stage 2: Session pipeline deployed and healthy"
```

#### **Stage 3: Blockchain Services**
```bash
# Deploy blockchain services
docker-compose -f infrastructure/compose/docker-compose.blockchain.yaml up -d

# Wait and verify
sleep 60
docker-compose -f infrastructure/compose/docker-compose.blockchain.yaml ps

# Health checks
curl -f http://localhost:8084/health  # Blockchain API
curl -f http://localhost:8085/health  # Blockchain Governance
curl -f http://localhost:8086/health  # Blockchain Sessions Data
curl -f http://localhost:8087/health  # Blockchain VM
curl -f http://localhost:8088/health  # Blockchain Ledger

echo "Stage 3: Blockchain services deployed and healthy"
```

#### **Stage 4: Integration Services**
```bash
# Deploy integration services
docker-compose -f infrastructure/compose/docker-compose.integration.yaml up -d

# Wait and verify
sleep 60
docker-compose -f infrastructure/compose/docker-compose.integration.yaml ps

# Health checks
curl -f http://localhost:8095/health  # OpenAPI Gateway
curl -f http://localhost:8096/health  # OpenAPI Server
curl -f http://localhost:8097/health  # Admin UI

echo "Stage 4: Integration services deployed and healthy"
```

### **4.2 Rollback Testing**

#### **Service Rollback Procedure**
```bash
# Test rollback of individual service
docker-compose -f infrastructure/compose/docker-compose.sessions.yaml stop session-encryptor
docker-compose -f infrastructure/compose/docker-compose.sessions.yaml up -d session-encryptor

# Verify service recovery
sleep 30
curl -f http://localhost:8091/health

echo "Service rollback test completed"
```

#### **Full Stack Rollback**
```bash
# Rollback entire stack
docker-compose -f infrastructure/compose/docker-compose.integration.yaml down
docker-compose -f infrastructure/compose/docker-compose.blockchain.yaml down
docker-compose -f infrastructure/compose/docker-compose.sessions.yaml down
docker-compose -f infrastructure/compose/docker-compose.core.yaml down

# Verify cleanup
docker ps | grep lucid
docker volume ls | grep lucid

echo "Full stack rollback completed"
```

---

## **PHASE 5: PERFORMANCE TESTING**

### **5.1 Resource Usage Testing**

#### **Memory Usage Monitoring**
```bash
# Monitor memory usage during deployment
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Test under load
for i in {1..100}; do
  curl -s http://localhost:8081/health > /dev/null &
done
wait

# Check memory usage after load
docker stats --no-stream
```

#### **Network Performance Testing**
```bash
# Test network connectivity
docker network ls
docker network inspect lucid_core_net

# Test inter-service communication
docker exec lucid_api curl -f http://lucid_mongo:27017
docker exec session_chunker curl -f http://lucid_mongo:27017
docker exec blockchain_api curl -f http://lucid_mongo:27017
```

### **5.2 Storage Performance Testing**

#### **Volume Performance**
```bash
# Test volume performance
docker run --rm -v lucid_mongo_data:/data alpine sh -c "dd if=/dev/zero of=/data/test bs=1M count=100"

# Check volume usage
docker system df -v
```

---

## **PHASE 6: PRODUCTION DEPLOYMENT VALIDATION**

### **6.1 Pi Deployment Testing**

#### **Pi Environment Validation**
```bash
# SSH into Pi
ssh pi@<pi-ip-address>

# Verify Pi environment
uname -a
docker --version
docker-compose --version

# Check available resources
free -h
df -h
```

#### **Pi Deployment Procedure**
```bash
# Navigate to project directory
cd /mnt/myssd/Lucid

# Pull latest images
docker-compose -f infrastructure/compose/docker-compose.core.yaml pull
docker-compose -f infrastructure/compose/docker-compose.sessions.yaml pull
docker-compose -f infrastructure/compose/docker-compose.blockchain.yaml pull
docker-compose -f infrastructure/compose/docker-compose.integration.yaml pull

# Deploy in stages
docker-compose -f infrastructure/compose/docker-compose.core.yaml up -d
sleep 60

docker-compose -f infrastructure/compose/docker-compose.sessions.yaml up -d
sleep 60

docker-compose -f infrastructure/compose/docker-compose.blockchain.yaml up -d
sleep 60

docker-compose -f infrastructure/compose/docker-compose.integration.yaml up -d
sleep 60

# Verify deployment
docker-compose -f infrastructure/compose/docker-compose.core.yaml ps
docker-compose -f infrastructure/compose/docker-compose.sessions.yaml ps
docker-compose -f infrastructure/compose/docker-compose.blockchain.yaml ps
docker-compose -f infrastructure/compose/docker-compose.integration.yaml ps
```

### **6.2 Production Health Monitoring**

#### **Continuous Health Checks**
```bash
# Create health check script
cat > /mnt/myssd/Lucid/health-check.sh << 'EOF'
#!/bin/bash

echo "=== Lucid Health Check ==="
echo "Timestamp: $(date)"

# Core services
echo "Core Services:"
curl -s -f http://localhost:8080/health && echo " ✓ API Gateway" || echo " ✗ API Gateway"
curl -s -f http://localhost:8081/health && echo " ✓ API Server" || echo " ✗ API Server"
curl -s --socks5 localhost:9050 http://httpbin.org/ip > /dev/null && echo " ✓ Tor Proxy" || echo " ✗ Tor Proxy"

# Session services
echo "Session Services:"
curl -s -f http://localhost:8090/health && echo " ✓ Session Chunker" || echo " ✗ Session Chunker"
curl -s -f http://localhost:8091/health && echo " ✓ Session Encryptor" || echo " ✗ Session Encryptor"
curl -s -f http://localhost:8092/health && echo " ✓ Merkle Builder" || echo " ✗ Merkle Builder"
curl -s -f http://localhost:8093/health && echo " ✓ Session Orchestrator" || echo " ✗ Session Orchestrator"

# Blockchain services
echo "Blockchain Services:"
curl -s -f http://localhost:8084/health && echo " ✓ Blockchain API" || echo " ✗ Blockchain API"
curl -s -f http://localhost:8085/health && echo " ✓ Blockchain Governance" || echo " ✗ Blockchain Governance"
curl -s -f http://localhost:8086/health && echo " ✓ Blockchain Sessions Data" || echo " ✗ Blockchain Sessions Data"

# Integration services
echo "Integration Services:"
curl -s -f http://localhost:8095/health && echo " ✓ OpenAPI Gateway" || echo " ✗ OpenAPI Gateway"
curl -s -f http://localhost:8096/health && echo " ✓ OpenAPI Server" || echo " ✗ OpenAPI Server"
curl -s -f http://localhost:8097/health && echo " ✓ Admin UI" || echo " ✗ Admin UI"

echo "=== Health Check Complete ==="
EOF

chmod +x /mnt/myssd/Lucid/health-check.sh

# Run health check
/mnt/myssd/Lucid/health-check.sh
```

#### **Automated Monitoring Setup**
```bash
# Create cron job for health monitoring
echo "*/5 * * * * /mnt/myssd/Lucid/health-check.sh >> /mnt/myssd/Lucid/health.log 2>&1" | crontab -

# Create log rotation
cat > /etc/logrotate.d/lucid << 'EOF'
/mnt/myssd/Lucid/health.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

---

## **PHASE 7: TROUBLESHOOTING PROCEDURES**

### **7.1 Common Issues and Solutions**

#### **Container Startup Issues**
```bash
# Check container logs
docker logs lucid_api
docker logs tor-proxy
docker logs session_chunker

# Check container status
docker ps -a | grep lucid

# Restart failed containers
docker-compose -f infrastructure/compose/docker-compose.core.yaml restart lucid_api
```

#### **Network Connectivity Issues**
```bash
# Check network configuration
docker network ls
docker network inspect lucid_core_net

# Test inter-container communication
docker exec lucid_api ping lucid_mongo
docker exec session_chunker ping lucid_mongo

# Recreate network if needed
docker network rm lucid_core_net
docker-compose -f infrastructure/compose/docker-compose.core.yaml up -d
```

#### **Volume Mount Issues**
```bash
# Check volume status
docker volume ls | grep lucid
docker volume inspect lucid_mongo_data

# Check volume permissions
docker exec lucid_mongo ls -la /data/db
```

### **7.2 Performance Issues**

#### **High Memory Usage**
```bash
# Check memory usage
docker stats --no-stream

# Restart high-memory containers
docker-compose -f infrastructure/compose/docker-compose.core.yaml restart lucid_mongo

# Adjust resource limits in compose files
```

#### **Slow Response Times**
```bash
# Check network latency
docker exec lucid_api ping lucid_mongo
docker exec session_chunker ping lucid_mongo

# Check disk I/O
iostat -x 1 5
```

---

## **SUMMARY**

This comprehensive testing and deployment procedure ensures:

1. **Security**: Distroless containers provide minimal attack surface
2. **Reliability**: Multi-staged deployment with health checks
3. **Performance**: Optimized for Pi hardware constraints
4. **Maintainability**: Clear rollback and troubleshooting procedures
5. **Monitoring**: Continuous health monitoring and logging

The distroless deployment strategy provides a robust, secure, and efficient solution for deploying the Lucid project on Raspberry Pi while maintaining development flexibility on Windows.
