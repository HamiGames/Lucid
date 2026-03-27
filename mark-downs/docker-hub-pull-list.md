# Docker Hub Pull List for Lucid Project

**Registry:** Docker Hub (pickme/lucid namespace)  
**Platform:** linux/arm64 (aarch64)  
**Target Host:** Raspberry Pi 5 (192.168.0.75)

## Pre-Build Phase - Base Images

### Distroless Base Images
```bash
# Python Distroless Base
docker pull pickme/lucid-base:python-distroless-arm64

# Java Distroless Base  
docker pull pickme/lucid-base:java-distroless-arm64
```

## Phase 1: Foundation Services

### Storage Database Containers
```bash
# MongoDB Container
docker pull pickme/lucid-mongodb:latest-arm64

# Redis Container
docker pull pickme/lucid-redis:latest-arm64

# Elasticsearch Container
docker pull pickme/lucid-elasticsearch:latest-arm64
```

### Authentication Service
```bash
# Auth Service Container
docker pull pickme/lucid-auth-service:latest-arm64
```

## Phase 2: Core Services

### API Gateway & Service Mesh (Group B)
```bash
# API Gateway Container
docker pull pickme/lucid-api-gateway:latest-arm64

# Service Mesh Controller Container
docker pull pickme/lucid-service-mesh-controller:latest-arm64
```

### Blockchain Core Containers (Group C)
```bash
# Blockchain Engine Container
docker pull pickme/lucid-blockchain-engine:latest-arm64

# Session Anchoring Container
docker pull pickme/lucid-session-anchoring:latest-arm64

# Block Manager Container
docker pull pickme/lucid-block-manager:latest-arm64

# Data Chain Container
docker pull pickme/lucid-data-chain:latest-arm64
```

## Phase 3: Application Services

### Session Management Containers
```bash
# Session Pipeline Container
docker pull pickme/lucid-session-pipeline:latest-arm64

# Session Recorder Container
docker pull pickme/lucid-session-recorder:latest-arm64

# Chunk Processor Container
docker pull pickme/lucid-chunk-processor:latest-arm64

# Session Storage Container
docker pull pickme/lucid-session-storage:latest-arm64

# Session API Container
docker pull pickme/lucid-session-api:latest-arm64
```

### RDP Services Containers
```bash
# RDP Server Manager Container
docker pull pickme/lucid-rdp-server-manager:latest-arm64

# XRDP Integration Container
docker pull pickme/lucid-xrdp-integration:latest-arm64

# Session Controller Container
docker pull pickme/lucid-session-controller:latest-arm64

# Resource Monitor Container
docker pull pickme/lucid-resource-monitor:latest-arm64
```

### Node Management
```bash
# Node Management Container
docker pull pickme/lucid-node-management:latest-arm64
```

## Phase 4: Support Services

### Admin Interface
```bash
# Admin Interface Container
docker pull pickme/lucid-admin-interface:latest-arm64
```

### TRON Payment Containers (ISOLATED NETWORK)
```bash
# TRON Client Container
docker pull pickme/lucid-tron-client:latest-arm64

# Payout Router Container
docker pull pickme/lucid-payout-router:latest-arm64

# Wallet Manager Container
docker pull pickme/lucid-wallet-manager:latest-arm64

# USDT Manager Container
docker pull pickme/lucid-usdt-manager:latest-arm64

# TRX Staking Container
docker pull pickme/lucid-trx-staking:latest-arm64

# Payment Gateway Container
docker pull pickme/lucid-payment-gateway:latest-arm64
```

## Complete Pull Script

### All-in-One Pull Script
```bash
#!/bin/bash
set -e

echo "===== Pulling All Lucid Containers for Raspberry Pi ====="
echo "Platform: linux/arm64"
echo "Registry: pickme/lucid"

# Pre-Build Phase - Base Images
echo "Pulling base images..."
docker pull pickme/lucid-base:python-distroless-arm64
docker pull pickme/lucid-base:java-distroless-arm64

# Phase 1: Foundation Services
echo "Pulling Phase 1 - Foundation Services..."
docker pull pickme/lucid-mongodb:latest-arm64
docker pull pickme/lucid-redis:latest-arm64
docker pull pickme/lucid-elasticsearch:latest-arm64
docker pull pickme/lucid-auth-service:latest-arm64

# Phase 2: Core Services
echo "Pulling Phase 2 - Core Services..."
docker pull pickme/lucid-api-gateway:latest-arm64
docker pull pickme/lucid-service-mesh-controller:latest-arm64
docker pull pickme/lucid-blockchain-engine:latest-arm64
docker pull pickme/lucid-session-anchoring:latest-arm64
docker pull pickme/lucid-block-manager:latest-arm64
docker pull pickme/lucid-data-chain:latest-arm64

# Phase 3: Application Services
echo "Pulling Phase 3 - Application Services..."
docker pull pickme/lucid-session-pipeline:latest-arm64
docker pull pickme/lucid-session-recorder:latest-arm64
docker pull pickme/lucid-chunk-processor:latest-arm64
docker pull pickme/lucid-session-storage:latest-arm64
docker pull pickme/lucid-session-api:latest-arm64
docker pull pickme/lucid-rdp-server-manager:latest-arm64
docker pull pickme/lucid-xrdp-integration:latest-arm64
docker pull pickme/lucid-session-controller:latest-arm64
docker pull pickme/lucid-resource-monitor:latest-arm64
docker pull pickme/lucid-node-management:latest-arm64

# Phase 4: Support Services
echo "Pulling Phase 4 - Support Services..."
docker pull pickme/lucid-admin-interface:latest-arm64
docker pull pickme/lucid-tron-client:latest-arm64
docker pull pickme/lucid-payout-router:latest-arm64
docker pull pickme/lucid-wallet-manager:latest-arm64
docker pull pickme/lucid-usdt-manager:latest-arm64
docker pull pickme/lucid-trx-staking:latest-arm64
docker pull pickme/lucid-payment-gateway:latest-arm64

echo "===== All Containers Pulled Successfully ====="
echo "Total containers: 32"
echo "Ready for deployment on Raspberry Pi 5"
```

## Phase-Based Pull Scripts

### Phase 1 Pull Script
```bash
#!/bin/bash
# scripts/pull/phase1-foundation.sh

echo "Pulling Phase 1 - Foundation Services..."
docker pull pickme/lucid-mongodb:latest-arm64
docker pull pickme/lucid-redis:latest-arm64
docker pull pickme/lucid-elasticsearch:latest-arm64
docker pull pickme/lucid-auth-service:latest-arm64
echo "Phase 1 containers ready"
```

### Phase 2 Pull Script
```bash
#!/bin/bash
# scripts/pull/phase2-core.sh

echo "Pulling Phase 2 - Core Services..."
docker pull pickme/lucid-api-gateway:latest-arm64
docker pull pickme/lucid-service-mesh-controller:latest-arm64
docker pull pickme/lucid-blockchain-engine:latest-arm64
docker pull pickme/lucid-session-anchoring:latest-arm64
docker pull pickme/lucid-block-manager:latest-arm64
docker pull pickme/lucid-data-chain:latest-arm64
echo "Phase 2 containers ready"
```

### Phase 3 Pull Script
```bash
#!/bin/bash
# scripts/pull/phase3-application.sh

echo "Pulling Phase 3 - Application Services..."
docker pull pickme/lucid-session-pipeline:latest-arm64
docker pull pickme/lucid-session-recorder:latest-arm64
docker pull pickme/lucid-chunk-processor:latest-arm64
docker pull pickme/lucid-session-storage:latest-arm64
docker pull pickme/lucid-session-api:latest-arm64
docker pull pickme/lucid-rdp-server-manager:latest-arm64
docker pull pickme/lucid-xrdp-integration:latest-arm64
docker pull pickme/lucid-session-controller:latest-arm64
docker pull pickme/lucid-resource-monitor:latest-arm64
docker pull pickme/lucid-node-management:latest-arm64
echo "Phase 3 containers ready"
```

### Phase 4 Pull Script
```bash
#!/bin/bash
# scripts/pull/phase4-support.sh

echo "Pulling Phase 4 - Support Services..."
docker pull pickme/lucid-admin-interface:latest-arm64
docker pull pickme/lucid-tron-client:latest-arm64
docker pull pickme/lucid-payout-router:latest-arm64
docker pull pickme/lucid-wallet-manager:latest-arm64
docker pull pickme/lucid-usdt-manager:latest-arm64
docker pull pickme/lucid-trx-staking:latest-arm64
docker pull pickme/lucid-payment-gateway:latest-arm64
echo "Phase 4 containers ready"
```

## Container Summary

| Phase | Container Count | Purpose |
|-------|----------------|---------|
| Pre-Build | 2 | Base distroless images |
| Phase 1 | 4 | Foundation services (DB, Auth) |
| Phase 2 | 6 | Core services (Gateway, Blockchain) |
| Phase 3 | 10 | Application services (Session, RDP, Node) |
| Phase 4 | 7 | Support services (Admin, TRON) |
| **Total** | **29** | **Complete Lucid Stack** |

## Network Configuration

### Primary Network
- **Network Name:** lucid-pi-network
- **Type:** bridge
- **Subnet:** 172.20.0.0/16

### Isolated Network
- **Network Name:** lucid-tron-isolated
- **Purpose:** TRON payment containers isolation

## Port Assignments

| Service | Port | Purpose |
|---------|------|---------|
| API Gateway | 8080 | Main API entry point |
| RDP Server Manager | 8081 | RDP session management |
| Session Controller | 8082 | Session control |
| Admin Interface | 8083 | Admin dashboard |
| Blockchain Engine | 8084 | Blockchain consensus |
| Session Anchoring | 8085 | Blockchain anchoring |
| Service Mesh | 8086 | Service discovery |
| Session API | 8087 | Session management API |
| Auth Service | 8089 | Authentication |
| Resource Monitor | 8090 | System monitoring |
| TRON Client | 8091 | TRON network client |
| Payout Router | 8092 | Payment routing |
| Wallet Manager | 8093 | Wallet management |
| USDT Manager | 8094 | USDT operations |
| Node Management | 8095 | Node pool management |
| TRX Staking | 8096 | TRX staking operations |
| Payment Gateway | 8097 | Payment gateway |
| MongoDB | 27017 | Database |
| Redis | 6379 | Cache |
| Elasticsearch | 9200 | Search engine |
| XRDP | 3389 | RDP connections |
| Consul | 8500 | Service discovery |

## Deployment Notes

1. **Platform:** All images built for linux/arm64 (Raspberry Pi 5)
2. **Registry:** Docker Hub with pickme/lucid namespace
3. **Security:** All containers use distroless base images
4. **Isolation:** TRON services on separate network
5. **Order:** Pull in phase sequence for proper dependency resolution
