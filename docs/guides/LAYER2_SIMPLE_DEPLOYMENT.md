# LUCID Layer 2 Simple Deployment Guide

# Service Integration Layer - RDP Server & Blockchain Deployment

# Using Pre-built Images

**Generated:** 2025-10-05T06:31:54Z
**Mode:** LUCID-STRICT Simple Deployment
**Purpose:** Deploy Layer 2 using pre-built images
**Target:** Pi 5 ARM64 with existing images

---

## **OVERVIEW**

Layer 2 deployment uses **pre-built images** from the registry instead of building locally. This approach is more reliable and faster.

### **Pre-built Images Available**

- `pickme/lucid:rdp-server-manager` - RDP session management

- `pickme/lucid:contract-deployment` - Smart contract deployment

- `pickme/lucid:tor-proxy` - Tor proxy service

- `pickme/lucid:api-server` - API server

- `pickme/lucid:api-gateway` - API gateway

- `pickme/lucid:tunnel-tools` - Tunnel tools

- `pickme/lucid:server-tools` - Server utilities

---

## **DEPLOYMENT PROCESS**

### **1. Verify Images Exist**

```bash

# Check if images are available locally

docker images | grep pickme/lucid

# Pull latest images

docker pull pickme/lucid:rdp-server-manager
docker pull pickme/lucid:contract-deployment
docker pull pickme/lucid:tor-proxy
docker pull pickme/lucid:api-server
docker pull pickme/lucid:api-gateway
docker pull pickme/lucid:tunnel-tools
docker pull pickme/lucid:server-tools

```

### **2. Deploy Layer 2 Services**

#### **Layer 2 Only**

```bash

# Deploy Layer 2 services using pre-built images

docker-compose -f infrastructure/compose/lucid-layer2-simple.yaml \
  --profile rdp-server \
  --profile blockchain-deployment \
  --env-file configs/environment/layer2-simple.env \
  up -d

```

#### **Full Stack (All Layers)**

```bash

# Deploy complete stack using pre-built images

docker-compose -f infrastructure/compose/lucid-dev.yaml \
  -f infrastructure/compose/lucid-dev-layer1.yaml \
  -f infrastructure/compose/lucid-layer2-simple.yaml \
  --profile blockchain \
  --profile session-core \
  --profile rdp-server \
  --profile blockchain-deployment \
  --env-file configs/environment/layer2-simple.env \
  up -d

```bash

### **3. Verify Deployment**

```bash

# Check running containers

docker ps | grep lucid

# Check service health

curl -f http://localhost:8087/health  # RDP Server Manager
curl -f http://localhost:8090/health  # Contract Deployment
curl -f http://localhost:8080/health  # API Gateway
curl -f http://localhost:8081/health  # API Server

```bash

---

## **PI 5 DEPLOYMENT**

### **1. SSH to Pi 5**

```bash

ssh pickme@192.168.0.75
cd /mnt/myssd/Lucid

```

### **2. Pull Latest Images**

```bash

# Pull all required images

docker pull pickme/lucid:rdp-server-manager
docker pull pickme/lucid:contract-deployment
docker pull pickme/lucid:tor-proxy
docker pull pickme/lucid:api-server
docker pull pickme/lucid:api-gateway
docker pull pickme/lucid:tunnel-tools
docker pull pickme/lucid:server-tools

```

### **3. Deploy Services**

```bash

# Deploy Layer 2 services

docker-compose -f infrastructure/compose/lucid-layer2-simple.yaml \
  --profile rdp-server \
  --profile blockchain-deployment \
  up -d

# Verify deployment

docker ps | grep lucid
docker logs lucid_rdp_server_manager
docker logs lucid_contract_deployment

```ini

---

## **SERVICE CONFIGURATION**

### **RDP Server Manager**

- **Image**: `pickme/lucid:rdp-server-manager`

- **Port**: 8087

- **Health**: `http://localhost:8087/health`

- **Dependencies**: MongoDB

- **Volumes**: `/data/sessions`, `/data/recordings`

### **Contract Deployment**

- **Image**: `pickme/lucid:contract-deployment`

- **Port**: 8090

- **Health**: `http://localhost:8090/health`

- **Dependencies**: MongoDB, TRON network

- **Volumes**: `/data/contracts`, `/data/logs`

---

## **ENVIRONMENT CONFIGURATION**

### **Layer 2 Environment File**

```bash

# Copy environment configuration

cp configs/environment/layer2-simple.env .env.layer2

# Edit configuration as needed

nano .env.layer2

```ini

### **Key Configuration Variables**

```bash

# RDP Server Configuration

RDP_SESSIONS_PATH=/data/sessions
RDP_RECORDINGS_PATH=/data/recordings
XRDP_PORT=3389
MAX_CONCURRENT_SESSIONS=5

# Blockchain Configuration

TRON_NETWORK=shasta
TRON_RPC_URL=https://api.shasta.trongrid.io
CONTRACT_ARTIFACTS_PATH=/data/contracts
DEPLOYMENT_LOG_PATH=/data/logs

# Database Configuration

MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin

```

---

## **NETWORK CONFIGURATION**

### **Network Topology**

```

lucid_core_net (172.21.0.0/24)
├── Core Services
│   ├── lucid_mongo: 172.21.0.10
│   ├── tor-proxy: 172.21.0.11
│   ├── lucid_api: 172.21.0.12
│   └── lucid_api_gateway: 172.21.0.13
└── Layer 2 Services
    ├── rdp-server-manager: 172.23.0.10
    └── contract-deployment: 172.24.0.10

```

### **Service Communication**

- All services communicate through `lucid_core_net`

- External access via `lucid-dev_lucid_net`

- MongoDB shared across all services

- TRON network access for blockchain services

---

## **MONITORING AND HEALTH CHECKS**

### **Service Health Monitoring**

```bash

# Check all services

curl -f http://localhost:8080/health  # API Gateway
curl -f http://localhost:8081/health  # API Server
curl -f http://localhost:8087/health  # RDP Server Manager
curl -f http://localhost:8090/health  # Contract Deployment

```

### **Log Monitoring**

```bash

# View service logs

docker logs lucid_rdp_server_manager
docker logs lucid_contract_deployment
docker logs lucid_api_gateway

# Follow logs in real-time

docker logs -f lucid_rdp_server_manager

```

### **Resource Monitoring**

```bash

# Check resource usage

docker stats lucid_rdp_server_manager lucid_contract_deployment

# Check disk usage

docker system df
df -h /mnt/myssd

```

---

## **TROUBLESHOOTING**

### **Common Issues**

#### **1. Image Pull Failures**

```bash

# Check Docker registry access

docker pull hello-world

# Check specific image

docker pull pickme/lucid:rdp-server-manager

# Check Docker Hub access

curl -f https://hub.docker.com

```

#### **2. Service Startup Issues**

```bash

# Check service logs

docker logs lucid_rdp_server_manager
docker logs lucid_contract_deployment

# Check service status

docker ps -a | grep lucid

```

#### **3. Network Connectivity Issues**

```bash

# Check network connectivity

docker network ls | grep lucid
docker network inspect lucid_core_net

# Test service communication

docker exec lucid_rdp_server_manager curl -f http://lucid_mongo:27017

```

### **Performance Optimization**

#### **Pi 5 Hardware Optimization**

```bash

# Check available resources

free -h
df -h /mnt/myssd

# Optimize Docker resources

docker system prune -f
docker volume prune -f

```

---

## **ADVANTAGES OF PRE-BUILT IMAGES**

### **1. Reliability**

- No build failures

- Consistent images across environments

- Pre-tested and verified

### **2. Speed**

- Faster deployment

- No compilation time

- Immediate startup

### **3. Simplicity**

- No build dependencies

- No network issues

- Easy troubleshooting

### **4. Consistency**

- Same images on all systems

- Version control

- Reproducible deployments

---

**This deployment guide provides simple, reliable instructions for deploying Layer 2 using pre-built images instead of building locally.**
