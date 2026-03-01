# Lucid Project Deployment Factors Summary

## Document Control

| Attribute | Value |
|-----------|-------|
| Document Type | Deployment Configuration Summary |
| Created Date | 2025-01-14 |
| Based On | Network Configs, Distroless Deployment Plans, Docker Compose Analysis |
| Target Platform | Raspberry Pi 5 (ARM64) |
| Deployment Host | 192.168.0.75 |

---

## Overview

This document provides a comprehensive summary of Docker Compose files used to launch, run, and maintain the Lucid project according to the network configurations, distroless images, and environment files found throughout the project structure.

## Docker Compose Files for Lucid Project Deployment

### **Core Production Deployment Files**

#### **Phase-Based Deployment Files**

##### 1. Foundation Services (Phase 1)
**File**: `configs/docker/docker-compose.foundation.yml`
- **Purpose**: Phase 1 Foundation Services (MongoDB, Redis, Elasticsearch, Auth Service)
- **Network**: `lucid-pi-network` (172.20.0.0/16)
- **Images**: `pickme/lucid-*:latest-arm64`
- **Environment**: `.env.foundation`
- **Services**: 4 containers
  - `lucid-mongodb` (Port 27017)
  - `lucid-redis` (Port 6379)
  - `lucid-elasticsearch` (Ports 9200, 9300)
  - `lucid-auth-service` (Port 8089)

##### 2. Core Services (Phase 2)
**File**: `configs/docker/docker-compose.core.yml`
- **Purpose**: Phase 2 Core Services (API Gateway, Blockchain Engine, Service Mesh, Session Anchoring, Block Manager, Data Chain)
- **Network**: `lucid-pi-network` (172.20.0.0/16)
- **Images**: `pickme/lucid-*:latest-arm64`
- **Environment**: `.env.foundation` + `.env.core`
- **Services**: 6 containers
  - `api-gateway` (Port 8080)
  - `blockchain-engine` (Port 8084)
  - `service-mesh` (Port 8500)
  - `session-anchoring` (Port 8086)
  - `block-manager` (Port 8087)
  - `data-chain` (Port 8088)

##### 3. Application Services (Phase 3)
**File**: `configs/docker/docker-compose.application.yml`
- **Purpose**: Phase 3 Application Services (Session Management, RDP Services, Node Management)
- **Network**: `lucid-pi-network` (172.20.0.0/16)
- **Images**: `pickme/lucid-*:latest-arm64`
- **Environment**: `.env.foundation` + `.env.core` + `.env.application`
- **Services**: 10 containers
  - Session Management (5): `session-pipeline`, `session-recorder`, `session-processor`, `session-storage`, `session-api`
  - RDP Services (4): `rdp-server-manager`, `rdp-xrdp`, `rdp-controller`, `rdp-monitor`
  - Node Management (1): `node-management`

##### 4. Support Services (Phase 4)
**File**: `configs/docker/docker-compose.support.yml`
- **Purpose**: Phase 4 Support Services (Admin Interface, TRON Payment Services)
- **Networks**: `lucid-pi-network` (Admin), `lucid-tron-isolated` (TRON services)
- **Images**: `pickme/lucid-*:latest-arm64`
- **Environment**: `.env.foundation` + `.env.core` + `.env.application` + `.env.support`
- **Services**: 7 containers
  - `admin-interface` (Port 8120)
  - TRON Services (6): `tron-client`, `tron-payout-router`, `tron-wallet-manager`, `tron-usdt-manager`, `tron-staking`, `tron-payment-gateway`

#### **Master Orchestration File**

##### 5. Complete System Deployment
**File**: `configs/docker/docker-compose.all.yml`
- **Purpose**: Master file combining all phases (Foundation + Core + Application + Support)
- **Networks**: `lucid-pi-network`, `lucid-tron-isolated`
- **Images**: `pickme/lucid-*:latest-arm64`
- **Environment**: All phase environment files
- **Services**: 27 total containers across all phases

### **Distroless Infrastructure Files**

##### 6. Distroless Base Configuration
**File**: `configs/docker/distroless/distroless-config.yml`
- **Purpose**: Distroless base infrastructure (base, minimal-base, arm64-base)
- **Network**: `lucid-distroless-production` (172.23.0.0/16)
- **Images**: `pickme/lucid-base:latest-arm64`
- **Services**: 3 base containers

##### 7. Distroless Runtime Configuration
**File**: `configs/docker/distroless/distroless-runtime-config.yml`
- **Purpose**: Distroless runtime infrastructure (distroless-runtime, minimal-runtime, arm64-runtime)
- **Network**: `lucid-distroless-production` (172.23.0.0/16)
- **Images**: `pickme/lucid-base:latest-arm64`
- **Services**: 3 runtime containers

##### 8. Distroless Development Configuration
**File**: `configs/docker/distroless/distroless-development-config.yml`
- **Purpose**: Development distroless containers
- **Network**: `lucid-distroless-dev` (172.24.0.0/16)

##### 9. Distroless Security Configuration
**File**: `configs/docker/distroless/distroless-security-config.yml`
- **Purpose**: Security-hardened distroless containers

##### 10. Distroless Testing Configuration
**File**: `configs/docker/distroless/test-runtime-config.yml`
- **Purpose**: Testing distroless runtime containers

### **Multi-Stage Build Files**

##### 11. Multi-Stage Build Configuration
**File**: `configs/docker/multi-stage/multi-stage-config.yml`
- **Purpose**: Multi-stage build configuration
- **Network**: `lucid-multi-stage-network` (172.25.0.0/16)

##### 12. Multi-Stage Development Configuration
**File**: `configs/docker/multi-stage/multi-stage-development-config.yml`
- **Purpose**: Development multi-stage builds

##### 13. Multi-Stage Runtime Configuration
**File**: `configs/docker/multi-stage/multi-stage-runtime-config.yml`
- **Purpose**: Runtime multi-stage containers

##### 14. Multi-Stage Testing Configuration
**File**: `configs/docker/multi-stage/multi-stage-testing-config.yml`
- **Purpose**: Testing multi-stage builds

### **GUI Integration Files**

##### 15. GUI Integration Configuration
**File**: `configs/docker/docker-compose.gui-integration.yml`
- **Purpose**: GUI services integration
- **Network**: `lucid-gui-network` (172.22.0.0/16)

##### 16. GUI Docker Manager Service
**File**: `configs/services/gui-docker-manager.yml`
- **Purpose**: GUI Docker management service configuration
- **Access Control**: Role-based permissions for container management
- **Features**: User/Developer/Admin role-based access control

### **Infrastructure Base Files**

##### 17. Base Container Development
**File**: `infrastructure/containers/base/docker-compose.base.yml`
- **Purpose**: Base container development environment
- **Network**: `lucid-base-net` (172.21.0.0/16)
- **Images**: `lucid-python-base:latest`, `lucid-java-base:latest`
- **Services**: Python and Java base containers

## Network Configuration Summary

The Docker Compose files use the following networks as defined in `network-configs.md`:

### **Primary Networks**

| Network Name | Subnet | Gateway | Purpose |
|--------------|--------|---------|---------|
| `lucid-pi-network` | 172.20.0.0/16 | 172.20.0.1 | Main network for Foundation, Core, Application, and Admin services |
| `lucid-tron-isolated` | 172.21.0.0/16 | 172.21.0.1 | Isolated network for TRON payment services |
| `lucid-gui-network` | 172.22.0.0/16 | 172.22.0.1 | GUI services network |
| `lucid-distroless-production` | 172.23.0.0/16 | 172.23.0.1 | Distroless production containers |
| `lucid-distroless-dev` | 172.24.0.0/16 | 172.24.0.1 | Distroless development containers |
| `lucid-multi-stage-network` | 172.25.0.0/16 | 172.25.0.1 | Multi-stage build network |

### **Network Security Features**

- **ICC Enabled**: Inter-container communication enabled
- **IP Masquerade**: Enabled for external connectivity
- **Host Binding**: Bound to 0.0.0.0 for external access
- **MTU**: 1500 bytes for optimal performance
- **Attachable**: Networks can be attached to external containers

## Environment Files Configuration

### **Phase-Specific Environment Files**

| Environment File | Purpose | Used By |
|------------------|---------|---------|
| `.env.foundation` | Foundation services configuration | Phase 1, All phases |
| `.env.core` | Core services configuration | Phase 2, 3, 4 |
| `.env.application` | Application services configuration | Phase 3, 4 |
| `.env.support` | Support services configuration | Phase 4 |

### **Specialized Environment Files**

| Environment File | Purpose | Used By |
|------------------|---------|---------|
| `distroless.env` | Distroless-specific environment | Distroless containers |
| `production.env` | Production environment settings | Production deployments |
| `multi-stage.env` | Multi-stage build environment | Multi-stage builds |

## Image Configuration Summary

### **Image Naming Convention**

All production images follow the pattern: `pickme/lucid-[service]:latest-arm64`

### **Image Types**

| Image Type | Base Image | Purpose |
|------------|------------|---------|
| **Distroless Services** | `gcr.io/distroless/python3-debian12` | Production services |
| **Distroless Base** | `gcr.io/distroless/base-debian12` | Base infrastructure |
| **Multi-Stage** | Custom multi-stage builds | Optimized builds |
| **GUI Services** | `gcr.io/distroless/nodejs18-debian12` | Electron GUI |

### **Security Features**

- **Non-root User**: All containers run as user `65532:65532`
- **Read-only Filesystem**: Immutable runtime environment
- **No Shell Access**: Distroless containers have no shell
- **Capability Dropping**: All capabilities dropped except `NET_BIND_SERVICE`
- **Security Options**: `no-new-privileges:true`, `seccomp:unconfined`

## Deployment Order and Dependencies

### **Phase Deployment Sequence**

1. **Prerequisites**: Deploy distroless infrastructure
   - `distroless-config.yml`
   - `distroless-runtime-config.yml`

2. **Phase 1**: Foundation Services
   - `docker-compose.foundation.yml`
   - Dependencies: MongoDB, Redis, Elasticsearch, Auth Service

3. **Phase 2**: Core Services
   - `docker-compose.core.yml`
   - Dependencies: Phase 1 + API Gateway, Blockchain, Service Mesh

4. **Phase 3**: Application Services
   - `docker-compose.application.yml`
   - Dependencies: Phase 1 & 2 + Session Management, RDP, Node Management

5. **Phase 4**: Support Services
   - `docker-compose.support.yml`
   - Dependencies: Phase 1, 2 & 3 + Admin Interface, TRON Services

6. **Complete Deployment**: Master orchestration
   - `docker-compose.all.yml`
   - All 27 services across all phases

### **Service Dependencies**

#### **Phase 1 Dependencies**
- MongoDB → Redis → Elasticsearch → Auth Service

#### **Phase 2 Dependencies**
- API Gateway → MongoDB, Redis, Auth Service
- Blockchain Engine → MongoDB, Redis
- Service Mesh → MongoDB, Redis
- Session Anchoring → MongoDB, Redis, Blockchain Engine
- Block Manager → MongoDB, Redis, Blockchain Engine
- Data Chain → MongoDB, Redis, Blockchain Engine

#### **Phase 3 Dependencies**
- Session Services → MongoDB, Redis, Elasticsearch, API Gateway
- RDP Services → MongoDB, Redis, API Gateway, Auth Service
- Node Management → MongoDB, Redis, API Gateway, Blockchain Engine

#### **Phase 4 Dependencies**
- Admin Interface → All previous phases
- TRON Services → MongoDB, Redis, TRON Network (isolated)

## Volume Management

### **Volume Types**

| Volume Type | Purpose | Location |
|-------------|---------|----------|
| **Host Volumes** | Persistent data storage | `/mnt/myssd/Lucid/data/[service]` |
| **Log Volumes** | Application logs | `/mnt/myssd/Lucid/logs/[service]` |
| **Named Volumes** | Cache and temporary data | Docker-managed volumes |

### **Volume Security**

- **Read-Write Access**: Only for data and logs directories
- **Cache Volumes**: Temporary storage with automatic cleanup
- **Log Rotation**: Implemented at application level
- **Backup Strategy**: Host volumes backed up to external storage

## Port Mapping Summary

### **External Access Ports**

| Port | Service | Purpose |
|------|---------|---------|
| 27017 | MongoDB | Database access |
| 6379 | Redis | Cache access |
| 8080 | API Gateway | Main API endpoint |
| 8089 | Auth Service | Authentication |
| 8120 | Admin Interface | Administrative access |
| 8097 | TRON Payment Gateway | Payment processing |

### **Internal Service Ports**

| Port Range | Services | Purpose |
|------------|----------|---------|
| 8083-8088 | Session & Blockchain | Internal service communication |
| 8090-8096 | RDP & TRON Services | Specialized service communication |
| 8500-8502 | Service Mesh | Service discovery and routing |

## Health Check Configuration

### **Health Check Standards**

- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3 attempts
- **Start Period**: 40-60 seconds (depending on service)

### **Health Check Types**

| Check Type | Command | Purpose |
|------------|---------|---------|
| **Python Services** | `python3 -c "import sys; sys.exit(0)"` | Basic Python runtime check |
| **HTTP Services** | `curl -f http://localhost:[port]/health` | HTTP endpoint check |
| **Database Services** | `mongosh --eval "db.adminCommand('ping')"` | Database connectivity check |
| **Cache Services** | `redis-cli ping` | Cache connectivity check |

## Security Configuration

### **Container Security**

- **User**: Non-root user `65532:65532`
- **Capabilities**: Only `NET_BIND_SERVICE` allowed
- **Security Options**: `no-new-privileges:true`
- **Read-only**: Filesystem mounted read-only
- **Tmpfs**: Temporary filesystems with size limits

### **Network Security**

- **TRON Isolation**: Payment services on isolated network
- **Firewall Rules**: UFW rules for network access
- **SSL/TLS**: Enabled for external communications
- **Authentication**: JWT-based authentication system

### **Data Security**

- **Encryption**: Environment variables encrypted
- **Secrets Management**: Secure key generation and rotation
- **Access Control**: Role-based access control (RBAC)
- **Audit Logging**: Comprehensive logging for security events

## Monitoring and Maintenance

### **Logging Configuration**

- **Log Levels**: INFO, DEBUG, ERROR
- **Log Rotation**: Automatic rotation and cleanup
- **Centralized Logging**: All logs collected in `/mnt/myssd/Lucid/logs/`
- **Structured Logging**: JSON format for easy parsing

### **Monitoring Services**

- **Health Checks**: Automated health monitoring
- **Resource Monitoring**: CPU, memory, disk usage tracking
- **Service Discovery**: Consul-based service mesh
- **Alerting**: Automated alerts for service failures

### **Backup Strategy**

- **Data Backups**: Daily backups of persistent volumes
- **Configuration Backups**: Environment and compose file backups
- **Image Backups**: Container image registry backups
- **Recovery Procedures**: Documented rollback procedures

## Deployment Commands Reference

### **Phase Deployment Commands**

```bash
# Phase 1: Foundation Services
docker-compose --env-file configs/environment/.env.foundation -f configs/docker/docker-compose.foundation.yml up -d

# Phase 2: Core Services
docker-compose --env-file configs/environment/.env.foundation --env-file configs/environment/.env.core -f configs/docker/docker-compose.core.yml up -d

# Phase 3: Application Services
docker-compose --env-file configs/environment/.env.foundation --env-file configs/environment/.env.core --env-file configs/environment/.env.application -f configs/docker/docker-compose.application.yml up -d

# Phase 4: Support Services
docker-compose --env-file configs/environment/.env.foundation --env-file configs/environment/.env.core --env-file configs/environment/.env.application --env-file configs/environment/.env.support -f configs/docker/docker-compose.support.yml up -d

# Complete Deployment
docker-compose --env-file configs/environment/.env.foundation --env-file configs/environment/.env.core --env-file configs/environment/.env.application --env-file configs/environment/.env.support -f configs/docker/docker-compose.all.yml up -d
```

### **Distroless Infrastructure Commands**

```bash
# Deploy Distroless Base Infrastructure
docker-compose --env-file configs/environment/.env.foundation -f configs/docker/distroless/distroless-config.yml up -d

# Deploy Distroless Runtime Infrastructure
docker-compose --env-file configs/environment/.env.foundation -f configs/docker/distroless/distroless-runtime-config.yml up -d
```

### **Network Creation Commands**

```bash
# Create all required networks
docker network create lucid-pi-network --driver bridge --subnet 172.20.0.0/16 --gateway 172.20.0.1 --attachable
docker network create lucid-tron-isolated --driver bridge --subnet 172.21.0.0/16 --gateway 172.21.0.1 --attachable
docker network create lucid-gui-network --driver bridge --subnet 172.22.0.0/16 --gateway 172.22.0.1 --attachable
docker network create lucid-distroless-production --driver bridge --subnet 172.23.0.0/16 --gateway 172.23.0.1 --attachable
docker network create lucid-distroless-dev --driver bridge --subnet 172.24.0.0/16 --gateway 172.24.0.1 --attachable
docker network create lucid-multi-stage-network --driver bridge --subnet 172.25.0.0/16 --gateway 172.25.0.1 --attachable
```

## Troubleshooting Guide

### **Common Issues**

| Issue | Cause | Solution |
|-------|-------|----------|
| **Container Startup Failures** | Missing dependencies | Check service dependencies and startup order |
| **Network Connectivity** | Network configuration | Verify network creation and container attachment |
| **Volume Mount Failures** | Permission issues | Check directory ownership and permissions |
| **Health Check Failures** | Service not ready | Increase start_period or check service logs |
| **Distroless Compliance** | Shell access attempts | Verify no shell commands in health checks |

### **Verification Commands**

```bash
# Check all containers running
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check health status
docker ps --filter health=healthy

# Verify network connectivity
docker network inspect lucid-pi-network

# Check volume mounts
docker inspect [container-name] | grep -A 10 "Mounts"

# Verify distroless compliance
docker exec [container-name] id
docker exec [container-name] sh -c "echo test" 2>&1 | grep "executable file not found"
```

## Summary

The Lucid project uses a comprehensive Docker Compose-based deployment system with:

- **27 Total Services** across 4 deployment phases
- **6 Specialized Networks** for service isolation and security
- **Distroless Container Architecture** for enhanced security
- **Phase-based Deployment** with proper dependency management
- **Comprehensive Environment Management** with phase-specific configurations
- **Security-hardened Configuration** with non-root users and read-only filesystems
- **Automated Health Monitoring** and service discovery
- **Persistent Volume Management** for data and log storage

This deployment architecture ensures a secure, scalable, and maintainable production environment for the Lucid project on Raspberry Pi 5 infrastructure.
