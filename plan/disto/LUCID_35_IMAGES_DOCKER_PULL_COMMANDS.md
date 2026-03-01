# Lucid Project - 35 Images Docker Pull Commands

## Overview

This document provides comprehensive Docker pull commands for all 35 required Docker images in the Lucid project. These commands are designed for Pi-side deployment using pre-built images from Docker Hub.

**Total Required Images**: 35  
**Target Architecture**: linux/arm64 (Raspberry Pi 5)  
**Registry**: Docker Hub (pickme/lucid namespace)  
**Deployment Environment**: Raspberry Pi 5 (192.168.0.75)  
**Pull Method**: SSH-based remote deployment to Pi

---

## 📋 **PHASE 1: BASE INFRASTRUCTURE (3 images)**

### **Base Infrastructure Images**
```bash
# 1. Python Distroless Base
docker pull pickme/lucid-base:python-distroless-arm64

# 2. Java Distroless Base  
docker pull pickme/lucid-base:java-distroless-arm64

# 3. Latest Base
docker pull pickme/lucid-base:latest-arm64
```

### **SSH-Based Pi Deployment Commands**
```bash
# Pull base infrastructure images on Pi
ssh pickme@192.168.0.75 "docker pull pickme/lucid-base:python-distroless-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-base:java-distroless-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-base:latest-arm64"
```

---

## 📋 **PHASE 2: FOUNDATION SERVICES (4 images)**

### **Foundation Service Images**
```bash
# 4. MongoDB Container
docker pull pickme/lucid-mongodb:latest-arm64

# 5. Redis Container
docker pull pickme/lucid-redis:latest-arm64

# 6. Elasticsearch Container
docker pull pickme/lucid-elasticsearch:latest-arm64

# 7. Auth Service
docker pull pickme/lucid-auth-service:latest-arm64
```

### **SSH-Based Pi Deployment Commands**
```bash
# Pull foundation service images on Pi
ssh pickme@192.168.0.75 "docker pull pickme/lucid-mongodb:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-redis:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-elasticsearch:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-auth-service:latest-arm64"
```

---

## 📋 **PHASE 3: CORE SERVICES (6 images)**

### **Core Service Images**
```bash
# 8. API Gateway
docker pull pickme/lucid-api-gateway:latest-arm64

# 9. Service Mesh Controller
docker pull pickme/lucid-service-mesh-controller:latest-arm64

# 10. Blockchain Engine
docker pull pickme/lucid-blockchain-engine:latest-arm64

# 11. Session Anchoring
docker pull pickme/lucid-session-anchoring:latest-arm64

# 12. Block Manager
docker pull pickme/lucid-block-manager:latest-arm64

# 13. Data Chain
docker pull pickme/lucid-data-chain:latest-arm64
```

### **SSH-Based Pi Deployment Commands**
```bash
# Pull core service images on Pi
ssh pickme@192.168.0.75 "docker pull pickme/lucid-api-gateway:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-service-mesh-controller:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-blockchain-engine:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-session-anchoring:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-block-manager:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-data-chain:latest-arm64"
```

---

## 📋 **PHASE 4: APPLICATION SERVICES (10 images)**

### **Session Service Images**
```bash
# 14. Session Pipeline
docker pull pickme/lucid-session-pipeline:latest-arm64

# 15. Session Recorder
docker pull pickme/lucid-session-recorder:latest-arm64

# 16. Chunk Processor
docker pull pickme/lucid-chunk-processor:latest-arm64

# 17. Session Storage
docker pull pickme/lucid-session-storage:latest-arm64

# 18. Session API
docker pull pickme/lucid-session-api:latest-arm64
```

### **RDP Service Images**
```bash
# 19. RDP Server Manager
docker pull pickme/lucid-rdp-server-manager:latest-arm64

# 20. RDP XRDP
docker pull pickme/lucid-rdp-xrdp:latest-arm64

# 21. RDP Controller
docker pull pickme/lucid-rdp-controller:latest-arm64

# 22. RDP Monitor
docker pull pickme/lucid-rdp-monitor:latest-arm64
```

### **Node Management Image**
```bash
# 23. Node Management
docker pull pickme/lucid-node-management:latest-arm64
```

### **SSH-Based Pi Deployment Commands**
```bash
# Pull session service images on Pi
ssh pickme@192.168.0.75 "docker pull pickme/lucid-session-pipeline:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-session-recorder:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-chunk-processor:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-session-storage:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-session-api:latest-arm64"

# Pull RDP service images on Pi
ssh pickme@192.168.0.75 "docker pull pickme/lucid-rdp-server-manager:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-rdp-xrdp:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-rdp-controller:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-rdp-monitor:latest-arm64"

# Pull node management image on Pi
ssh pickme@192.168.0.75 "docker pull pickme/lucid-node-management:latest-arm64"
```

---

## 📋 **PHASE 5: SUPPORT SERVICES (7 images)**

### **Admin Interface Image**
```bash
# 24. Admin Interface
docker pull pickme/lucid-admin-interface:latest-arm64
```

### **Payment System Images**
```bash
# 25. TRON Client
docker pull pickme/lucid-tron-client:latest-arm64

# 26. Payout Router
docker pull pickme/lucid-payout-router:latest-arm64

# 27. Wallet Manager
docker pull pickme/lucid-wallet-manager:latest-arm64

# 28. USDT Manager
docker pull pickme/lucid-usdt-manager:latest-arm64

# 29. TRX Staking
docker pull pickme/lucid-trx-staking:latest-arm64

# 30. Payment Gateway
docker pull pickme/lucid-payment-gateway:latest-arm64
```

### **SSH-Based Pi Deployment Commands**
```bash
# Pull admin interface image on Pi
ssh pickme@192.168.0.75 "docker pull pickme/lucid-admin-interface:latest-arm64"

# Pull payment system images on Pi
ssh pickme@192.168.0.75 "docker pull pickme/lucid-tron-client:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-payout-router:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-wallet-manager:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-usdt-manager:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-trx-staking:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-payment-gateway:latest-arm64"
```

---

## 📋 **PHASE 6: SPECIALIZED SERVICES (5 images)**

### **Specialized Service Images**
```bash
# 31. GUI Services
docker pull pickme/lucid-gui:latest-arm64

# 32. RDP Services
docker pull pickme/lucid-rdp:latest-arm64

# 33. VM Services
docker pull pickme/lucid-vm:latest-arm64

# 34. Database Services
docker pull pickme/lucid-database:latest-arm64

# 35. Storage Services
docker pull pickme/lucid-storage:latest-arm64
```

### **SSH-Based Pi Deployment Commands**
```bash
# Pull specialized service images on Pi
ssh pickme@192.168.0.75 "docker pull pickme/lucid-gui:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-rdp:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-vm:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-database:latest-arm64"
ssh pickme@192.168.0.75 "docker pull pickme/lucid-storage:latest-arm64"
```

---

## 🚀 **COMPLETE PULL SCRIPT FOR ALL 35 IMAGES**

### **Single Command Script for Pi Deployment**
```bash
#!/bin/bash
# Complete Docker pull script for all 35 Lucid images
# Target: Raspberry Pi 5 (192.168.0.75)

PI_HOST="192.168.0.75"
PI_USER="pickme"

echo "🚀 Starting complete Lucid image pull on Pi ($PI_HOST)..."

# Phase 1: Base Infrastructure (3 images)
echo "📋 Phase 1: Pulling Base Infrastructure Images..."
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-base:python-distroless-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-base:java-distroless-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-base:latest-arm64"

# Phase 2: Foundation Services (4 images)
echo "📋 Phase 2: Pulling Foundation Service Images..."
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-mongodb:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-redis:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-elasticsearch:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-auth-service:latest-arm64"

# Phase 3: Core Services (6 images)
echo "📋 Phase 3: Pulling Core Service Images..."
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-api-gateway:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-service-mesh-controller:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-blockchain-engine:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-session-anchoring:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-block-manager:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-data-chain:latest-arm64"

# Phase 4: Application Services (10 images)
echo "📋 Phase 4: Pulling Application Service Images..."
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-session-pipeline:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-session-recorder:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-chunk-processor:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-session-storage:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-session-api:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-rdp-server-manager:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-rdp-xrdp:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-rdp-controller:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-rdp-monitor:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-node-management:latest-arm64"

# Phase 5: Support Services (7 images)
echo "📋 Phase 5: Pulling Support Service Images..."
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-admin-interface:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-tron-client:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-payout-router:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-wallet-manager:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-usdt-manager:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-trx-staking:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-payment-gateway:latest-arm64"

# Phase 6: Specialized Services (5 images)
echo "📋 Phase 6: Pulling Specialized Service Images..."
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-gui:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-rdp:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-vm:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-database:latest-arm64"
ssh $PI_USER@$PI_HOST "docker pull pickme/lucid-storage:latest-arm64"

echo "✅ Complete! All 35 Lucid images pulled successfully on Pi ($PI_HOST)"
```

---

## 📊 **SUMMARY STATISTICS**

| Phase | Category | Images | Pull Commands |
|-------|----------|--------|---------------|
| **Phase 1** | Base Infrastructure | 3 | 3 pull commands |
| **Phase 2** | Foundation Services | 4 | 4 pull commands |
| **Phase 3** | Core Services | 6 | 6 pull commands |
| **Phase 4** | Application Services | 10 | 10 pull commands |
| **Phase 5** | Support Services | 7 | 7 pull commands |
| **Phase 6** | Specialized Services | 5 | 5 pull commands |
| **TOTAL** | **All Phases** | **35** | **35 pull commands** |

---

## 🔧 **DEPLOYMENT CONFIGURATION**

### **Pi-Side Network Requirements**
```bash
# Create lucid-pi-network on Pi before pulling images
ssh pickme@192.168.0.75 "docker network create lucid-pi-network \
  --driver bridge \
  --subnet 172.20.0.0/16 \
  --gateway 172.20.0.1 \
  --attachable \
  --opt com.docker.network.bridge.enable_icc=true \
  --opt com.docker.network.bridge.enable_ip_masquerade=true \
  --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 \
  --opt com.docker.network.driver.mtu=1500 \
  --label 'lucid.network=main' \
  --label 'lucid.subnet=172.20.0.0/16'"
```

### **SSH Configuration Requirements**
```bash
# Ensure SSH access to Pi
ssh-keygen -t rsa -b 4096 -C "lucid-deployment"
ssh-copy-id pickme@192.168.0.75

# Test SSH connection
ssh pickme@192.168.0.75 "docker --version"
```

### **Pi Storage Requirements**
```bash
# Ensure sufficient storage on Pi
ssh pickme@192.168.0.75 "df -h /mnt/myssd"
ssh pickme@192.168.0.75 "docker system df"
```

---

## 🎯 **VERIFICATION COMMANDS**

### **Verify All Images Pulled Successfully**
```bash
# Check all images on Pi
ssh pickme@192.168.0.75 "docker images | grep pickme/lucid"

# Count pulled images
ssh pickme@192.168.0.75 "docker images | grep pickme/lucid | wc -l"

# Verify image sizes
ssh pickme@192.168.0.75 "docker images | grep pickme/lucid | awk '{print \$1\":\"\$2, \$7}'"
```

### **Test Image Functionality**
```bash
# Test base image functionality
ssh pickme@192.168.0.75 "docker run --rm pickme/lucid-base:latest-arm64 /usr/bin/python3 --version"

# Test service image functionality
ssh pickme@192.168.0.75 "docker run --rm pickme/lucid-auth-service:latest-arm64 /usr/bin/python3 --version"
```

---

## 📁 **FILE LOCATIONS**

### **Pull Commands Document**
- **This Document**: `plan/disto/LUCID_35_IMAGES_DOCKER_PULL_COMMANDS.md`
- **Mapping Document**: `plan/disto/LUCID_35_IMAGES_DOCKERFILE_MAPPING.md`
- **Status Analysis**: `plan/disto/LUCID_DOCKER_IMAGES_STATUS_ANALYSIS.md`

### **Deployment Scripts**
- **Complete Pull Script**: `scripts/deployment/complete-image-pull.sh`
- **Phase-by-Phase Scripts**: `scripts/deployment/phase-*-pull.sh`
- **Verification Scripts**: `scripts/deployment/verify-images.sh`

---

## 🚀 **DEPLOYMENT READINESS**

### **✅ Pi-Side Deployment Ready**
The pull commands are ready for:
- **Raspberry Pi 5** deployment (192.168.0.75)
- **SSH-based** remote image pulling
- **Network binding** with `lucid-pi-network` (172.20.0.0/16)
- **Distroless security** compliance
- **Health monitoring** and verification

### **✅ Complete Image Coverage**
All 35 required images have pull commands:
- **Base Infrastructure**: 3 images
- **Foundation Services**: 4 images  
- **Core Services**: 6 images
- **Application Services**: 10 images
- **Support Services**: 7 images
- **Specialized Services**: 5 images

---

## 🎯 **NEXT STEPS**

### **Immediate Actions**
1. **Execute Pull Commands**: Run all 35 pull commands on Pi
2. **Verify Images**: Confirm all images pulled successfully
3. **Test Functionality**: Test image functionality and health checks
4. **Deploy Services**: Deploy services using pulled images

### **Verification Steps**
1. **Image Count**: Verify all 35 images are present on Pi
2. **Image Integrity**: Test image functionality and security
3. **Network Binding**: Test network connectivity with `lucid-pi-network`
4. **Service Integration**: Test service integration and communication

---

**Generated**: 2025-01-24  
**Total Images**: 35  
**Pull Commands**: 35  
**Target**: Raspberry Pi 5 (192.168.0.75)  
**Registry**: Docker Hub (pickme/lucid)  
**Status**: 🚀 **READY FOR PI-SIDE DEPLOYMENT**
