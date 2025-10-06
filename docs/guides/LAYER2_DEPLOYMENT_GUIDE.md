# LUCID Layer 2 Deployment Guide
# Service Integration Layer - RDP Server & Blockchain Deployment
# LUCID-STRICT Distroless Implementation

**Generated:** 2025-10-05T06:31:54Z  
**Mode:** LUCID-STRICT Layer 2 Service Integration  
**Purpose:** Complete deployment guide for Layer 2 missing components  
**Target:** Pi 5 ARM64 with distroless security  

---

## **LAYER 2 OVERVIEW**

Layer 2 implements **Service Integration** components including:
- **RDP Server Management**: Session hosting, xrdp integration, session recording
- **Blockchain Deployment**: Smart contract compilation, deployment, verification

### **Architecture Components**

```
Layer 2 Service Integration
├── RDP Server Cluster
│   ├── rdp-server-manager (Port 8087)
│   ├── xrdp-integration (Port 8088)
│   └── session-host-manager (Port 8089)
└── Blockchain Deployment Cluster
    ├── contract-deployment (Port 8090)
    ├── contract-compiler (Port 8091)
    └── deployment-orchestrator (Port 8092)
```

---

## **PREREQUISITES**

### **System Requirements**
- Docker with buildx support
- Multi-platform build capability
- Pi 5 ARM64 target support
- Network connectivity to TRON blockchain

### **Dependencies**
- Layer 1 services running (MongoDB, Session Pipeline)
- TRON network access (Shasta testnet or Mainnet)
- xrdp service installation on Pi 5

---

## **BUILD PROCESS**

### **1. Build Layer 2 Distroless Images**

#### **Windows PowerShell**
```powershell
# Build all Layer 2 components
.\scripts\build-layer2-distroless.ps1 -Registry pickme -Tag latest -Push

# Build without cache
.\scripts\build-layer2-distroless.ps1 -NoCache -Push
```

#### **Linux/macOS**
```bash
# Build all Layer 2 components
./scripts/build-layer2-distroless.sh

# Build and push
REGISTRY=pickme TAG=latest PUSH=true ./scripts/build-layer2-distroless.sh

# Build without cache
NO_CACHE=true ./scripts/build-layer2-distroless.sh
```

### **2. Individual Component Builds**

#### **RDP Server Manager**
```bash
docker buildx build --platform linux/amd64,linux/arm64 \
  -t pickme/lucid:rdp-server-manager \
  -f RDP/server/Dockerfile.server-manager \
  --push .
```

#### **xrdp Integration**
```bash
docker buildx build --platform linux/amd64,linux/arm64 \
  -t pickme/lucid:xrdp-integration \
  -f RDP/server/Dockerfile.xrdp-integration \
  --push .
```

#### **Contract Deployment**
```bash
docker buildx build --platform linux/amd64,linux/arm64 \
  -t pickme/lucid:contract-deployment \
  -f blockchain/deployment/Dockerfile.contract-deployment \
  --push .
```

---

## **DEPLOYMENT CONFIGURATION**

### **1. Environment Setup**

Copy the Layer 2 environment configuration:
```bash
cp configs/environment/layer2.env .env.layer2
```

Edit `.env.layer2` with your specific configuration:
```bash
# TRON Network Configuration
TRON_NETWORK=shasta
TRON_RPC_URL=https://api.shasta.trongrid.io
TRON_PRIVATE_KEY=your_private_key_here
TRON_ADDRESS=your_tron_address_here

# RDP Server Configuration
XRDP_PORT=3389
DISPLAY_SERVER=wayland
HARDWARE_ACCELERATION=true
MAX_CONCURRENT_SESSIONS=5
```

### **2. Docker Compose Deployment**

#### **Layer 2 Only**
```bash
# Deploy Layer 2 services
docker-compose -f infrastructure/compose/lucid-dev-layer2.yaml \
  --profile rdp-server \
  --profile blockchain-deployment \
  --env-file .env.layer2 \
  up -d
```

#### **Full Stack (Layer 1 + Layer 2)**
```bash
# Deploy complete stack
docker-compose -f infrastructure/compose/lucid-dev.yaml \
  -f infrastructure/compose/lucid-dev-layer1.yaml \
  -f infrastructure/compose/lucid-dev-layer2.yaml \
  --profile blockchain \
  --profile session-core \
  --profile rdp-server \
  --profile blockchain-deployment \
  --env-file .env.layer2 \
  up -d
```

---

## **PI 5 DEPLOYMENT**

### **1. Pi 5 Setup**

#### **Install xrdp on Pi 5**
```bash
# SSH to Pi 5
ssh pickme@192.168.0.75

# Install xrdp
sudo apt update
sudo apt install -y xrdp xrdp-pulseaudio-installer

# Enable xrdp service
sudo systemctl enable xrdp
sudo systemctl start xrdp

# Configure Wayland support
sudo apt install -y wayland-protocols
```

#### **Hardware Acceleration Setup**
```bash
# Enable GPU acceleration
sudo raspi-config
# Navigate to Advanced Options > GL Driver > Enable

# Verify V4L2 support
lsmod | grep v4l2_m2m
```

### **2. Pi 5 Deployment**

```bash
# SSH to Pi 5
ssh pickme@192.168.0.75

# Navigate to Lucid directory
cd /mnt/myssd/Lucid

# Pull latest changes
git pull origin main

# Pull Layer 2 images
docker pull pickme/lucid:rdp-server-manager
docker pull pickme/lucid:xrdp-integration
docker pull pickme/lucid:contract-deployment

# Deploy Layer 2 services
docker-compose -f infrastructure/compose/lucid-dev-layer2.yaml \
  --profile rdp-server \
  --profile blockchain-deployment \
  up -d

# Verify deployment
docker ps | grep lucid
```

---

## **SERVICE CONFIGURATION**

### **1. RDP Server Services**

#### **RDP Server Manager**
- **Port**: 8087
- **Health Check**: `http://localhost:8087/health`
- **Dependencies**: MongoDB, Session Orchestrator
- **Volumes**: `/data/sessions`, `/data/recordings`, `/data/display`

#### **xrdp Integration**
- **Port**: 8088
- **Health Check**: `http://localhost:8088/health`
- **Dependencies**: RDP Server Manager
- **Configuration**: `/etc/xrdp/xrdp.ini`

#### **Session Host Manager**
- **Port**: 8089
- **Health Check**: `http://localhost:8089/health`
- **Dependencies**: RDP Server Manager, xrdp Integration
- **Features**: Session recording, resource management

### **2. Blockchain Deployment Services**

#### **Contract Deployment**
- **Port**: 8090
- **Health Check**: `http://localhost:8090/health`
- **Dependencies**: MongoDB, TRON network
- **Features**: Smart contract deployment, verification

#### **Contract Compiler**
- **Port**: 8091
- **Health Check**: `http://localhost:8091/health`
- **Dependencies**: Contract Deployment
- **Features**: Solidity compilation, artifact generation

#### **Deployment Orchestrator**
- **Port**: 8092
- **Health Check**: `http://localhost:8092/health`
- **Dependencies**: Contract Deployment, Contract Compiler
- **Features**: Deployment coordination, status tracking

---

## **NETWORK CONFIGURATION**

### **Network Topology**
```
lucid_core_net (172.21.0.0/24)
├── RDP Services (172.23.0.0/24)
│   ├── rdp-server-manager: 172.23.0.10
│   ├── xrdp-integration: 172.23.0.11
│   └── session-host-manager: 172.23.0.12
└── Blockchain Services (172.24.0.0/24)
    ├── contract-deployment: 172.24.0.10
    ├── contract-compiler: 172.24.0.11
    └── deployment-orchestrator: 172.24.0.12
```

### **Service Communication**
- All services communicate through `lucid_core_net`
- External access via `lucid-dev_lucid_net`
- MongoDB shared across all services
- TRON network access for blockchain services

---

## **MONITORING AND HEALTH CHECKS**

### **1. Service Health Monitoring**

```bash
# Check all Layer 2 services
curl -f http://localhost:8087/health  # RDP Server Manager
curl -f http://localhost:8088/health  # xrdp Integration
curl -f http://localhost:8089/health  # Session Host Manager
curl -f http://localhost:8090/health  # Contract Deployment
curl -f http://localhost:8091/health  # Contract Compiler
curl -f http://localhost:8092/health  # Deployment Orchestrator
```

### **2. Log Monitoring**

```bash
# View service logs
docker logs lucid_rdp_server_manager
docker logs lucid_xrdp_integration
docker logs lucid_contract_deployment

# Follow logs in real-time
docker logs -f lucid_rdp_server_manager
```

### **3. Resource Monitoring**

```bash
# Check resource usage
docker stats lucid_rdp_server_manager lucid_xrdp_integration lucid_contract_deployment

# Check disk usage
docker system df
df -h /mnt/myssd
```

---

## **TROUBLESHOOTING**

### **Common Issues**

#### **1. RDP Server Issues**
```bash
# Check xrdp service status
sudo systemctl status xrdp

# Restart xrdp service
sudo systemctl restart xrdp

# Check xrdp logs
sudo journalctl -u xrdp -f
```

#### **2. Blockchain Deployment Issues**
```bash
# Check TRON network connectivity
curl -f https://api.shasta.trongrid.io/wallet/getnowblock

# Verify TRON credentials
docker exec lucid_contract_deployment curl -f http://localhost:8090/health
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
# Enable GPU acceleration
echo 'gpu_mem=128' | sudo tee -a /boot/config.txt

# Optimize memory usage
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

# Enable hardware encoding
export HARDWARE_ACCELERATION=true
export PI5_GPU_ACCELERATION=true
```

---

## **SECURITY CONSIDERATIONS**

### **1. Distroless Security**
- All images use `gcr.io/distroless/python3-debian12:latest`
- No shell access in runtime containers
- Minimal attack surface
- Non-root user execution

### **2. Network Security**
- Internal service communication only
- External access through API Gateway
- TRON network communication encrypted
- MongoDB authentication required

### **3. Data Security**
- Session recordings encrypted
- Contract artifacts secured
- Private keys protected
- Audit logging enabled

---

## **NEXT STEPS**

### **Layer 3: User Interface**
- Frontend GUI development
- React/Next.js implementation
- TRON wallet integration
- Real-time session monitoring

### **Layer 4: Production Readiness**
- Comprehensive testing
- Performance optimization
- Security hardening
- Documentation completion

---

**This deployment guide provides complete instructions for implementing Layer 2 Service Integration components with distroless security and Pi 5 ARM64 support.**
