# Lucid Project - Service IP Configuration

**Document Purpose:** Complete IP address, port, and network configuration for all 35 Lucid services  
**Target Platform:** Raspberry Pi (linux/arm64)  
**Deployment Date:** 2025-01-24  
**Network Architecture:** Multi-network isolated design with dedicated subnets

---

## 📋 **EXECUTIVE SUMMARY**

### **Network Architecture Overview**
```
┌─────────────────────────────────────────────────────────────┐
│              LUCID PRODUCTION DEPLOYMENT                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Main Network:        172.20.0.0/16                          │
│  TRON Isolated:       172.21.0.0/16                          │
│  GUI Network:         172.22.0.0/16                          │
│                                                               │
│  Total Services:      35 containers                          │
│  Total Networks:      4 networks                             │
│  Total IPs Allocated: 35+ service IPs                        │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### **Network Segments**

| Network Name | Subnet | Gateway | Purpose | Status |
|-------------|---------|---------|---------|--------|
| `lucid-pi-network` | 172.20.0.0/16 | 172.20.0.1 | Main production services | **IN USE** |
| `lucid-tron-isolated` | 172.21.0.0/16 | 172.21.0.1 | TRON payment isolation | Available |
| `lucid-gui-network` | 172.22.0.0/16 | 172.22.0.1 | GUI and admin access | Available |
| `lucid-distroless-production` | 172.23.0.0/16 | 172.23.0.1 | Distroless containers | Available |
| `lucid-distroless-dev` | 172.24.0.0/16 | 172.24.0.1 | Distroless development | Available |
| `lucid-multi-stage-network` | 172.25.0.0/16 | 172.25.0.1 | Multi-stage builds | Available |

---

## 🏗️ **PHASE 1: FOUNDATION SERVICES**

### **1. MongoDB**
```ini
[service]
name=mongodb
container_name=lucid-mongodb
image=pickme/lucid-mongodb:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.11
hostname=lucid-mongodb
ports=27017:27017
environment=MONGODB_URI=mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
healthcheck_port=27017
```

### **2. Redis**
```ini
[service]
name=redis
container_name=lucid-redis
image=pickme/lucid-redis:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.12
hostname=lucid-redis
ports=6379:6379
environment=REDIS_URL=redis://lucid-redis:6379/0
healthcheck_port=6379
```

### **3. Elasticsearch**
```ini
[service]
name=elasticsearch
container_name=lucid-elasticsearch
image=pickme/lucid-elasticsearch:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.13
hostname=lucid-elasticsearch
ports=9200:9200,9300:9300
environment=ELASTICSEARCH_URI=http://lucid-elasticsearch:9200
healthcheck_port=9200
```

### **4. Auth Service**
```ini
[service]
name=auth-service
container_name=lucid-auth-service
image=pickme/lucid-auth-service:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.14
hostname=lucid-auth-service
ports=8089:8089
api_url=http://lucid-auth-service:8089
environment=AUTH_SERVICE_URL=http://lucid-auth-service:8089
healthcheck_port=8089
healthcheck_path=/health
```

---

## 🎯 **PHASE 2: CORE SERVICES**

### **5. API Gateway**
```ini
[service]
name=api-gateway
container_name=lucid-api-gateway
image=pickme/lucid-api-gateway:latest-arm64
network=lucid-pi-network,lucid-gui-network
ipv4_address=172.20.0.10,172.22.0.10
hostname=lucid-api-gateway
ports=8080:8080,8081:8081
api_url=http://lucid-api-gateway:8080
environment=API_GATEWAY_URL=http://lucid-api-gateway:8080
healthcheck_port=8080
healthcheck_path=/health
electron_gui_endpoint=http://172.20.0.10:8080/api/v1
```

### **6. Service Mesh Controller**
```ini
[service]
name=service-mesh-controller
container_name=lucid-service-mesh-controller
image=pickme/lucid-service-mesh-controller:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.19
hostname=lucid-service-mesh-controller
ports=8500:8500,8501:8501,8502:8502
environment=SERVICE_MESH_CONTROLLER_PORT=8500
healthcheck_port=8500
healthcheck_path=/v1/status/leader
```

### **7. Blockchain Engine**
```ini
[service]
name=blockchain-engine
container_name=lucid-blockchain-engine
image=pickme/lucid-blockchain-engine:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.15
hostname=lucid-blockchain-engine
ports=8084:8084
api_url=http://lucid-blockchain-engine:8084
environment=BLOCKCHAIN_ENGINE_URL=http://lucid-blockchain-engine:8084
healthcheck_port=8084
healthcheck_path=/health
electron_gui_endpoint=http://172.20.0.15:8084/api/v1
```

### **8. Session Anchoring**
```ini
[service]
name=session-anchoring
container_name=lucid-session-anchoring
image=pickme/lucid-session-anchoring:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.16
hostname=lucid-session-anchoring
ports=8085:8085
api_url=http://lucid-session-anchoring:8085
environment=SESSION_ANCHORING_URL=http://lucid-session-anchoring:8085
healthcheck_port=8085
healthcheck_path=/health
```

### **9. Block Manager**
```ini
[service]
name=block-manager
container_name=lucid-block-manager
image=pickme/lucid-block-manager:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.17
hostname=lucid-block-manager
ports=8086:8086
api_url=http://lucid-block-manager:8086
environment=BLOCK_MANAGER_URL=http://lucid-block-manager:8086
healthcheck_port=8086
healthcheck_path=/health
```

### **10. Data Chain**
```ini
[service]
name=data-chain
container_name=lucid-data-chain
image=pickme/lucid-data-chain:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.18
hostname=lucid-data-chain
ports=8087:8087
api_url=http://lucid-data-chain:8087
environment=DATA_CHAIN_URL=http://lucid-data-chain:8087
healthcheck_port=8087
healthcheck_path=/health
```

---

## 🚀 **PHASE 3: APPLICATION SERVICES**

### **11. Session Pipeline**
```ini
[service]
name=session-pipeline
container_name=lucid-session-pipeline
image=pickme/lucid-session-pipeline:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.20
hostname=lucid-session-pipeline
ports=8087:8087
api_url=http://lucid-session-pipeline:8087
environment=SESSION_PIPELINE_URL=http://lucid-session-pipeline:8087
healthcheck_port=8087
healthcheck_path=/health
electron_gui_endpoint=http://172.20.0.20:8087/api/v1
```

### **12. Session Recorder**
```ini
[service]
name=session-recorder
container_name=lucid-session-recorder
image=pickme/lucid-session-recorder:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.20
hostname=lucid-session-recorder
ports=8090:8090
api_url=http://lucid-session-recorder:8090
environment=SESSION_RECORDER_URL=http://lucid-session-recorder:8090
healthcheck_port=8090
```

### **13. Chunk Processor**
```ini
[service]
name=chunk-processor
container_name=lucid-chunk-processor
image=pickme/lucid-chunk-processor:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.20
hostname=lucid-chunk-processor
ports=8091:8091
api_url=http://lucid-chunk-processor:8091
environment=CHUNK_PROCESSOR_URL=http://lucid-chunk-processor:8091
healthcheck_port=8091
```

### **14. Session Storage**
```ini
[service]
name=session-storage
container_name=lucid-session-storage
image=pickme/lucid-session-storage:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.20
hostname=lucid-session-storage
ports=8082:8082
api_url=http://lucid-session-storage:8082
environment=SESSION_STORAGE_URL=http://lucid-session-storage:8082
healthcheck_port=8082
healthcheck_path=/health
```

### **15. Session API**
```ini
[service]
name=session-api
container_name=lucid-session-api
image=pickme/lucid-session-api:latest-arm64
network=lucid-pi-network,lucid-gui-network
ipv4_address=172.20.0.20
hostname=lucid-session-api
ports=8087:8087
api_url=http://lucid-session-api:8087
environment=SESSION_API_URL=http://lucid-session-api:8087
healthcheck_port=8087
healthcheck_path=/health
electron_gui_endpoint=http://172.20.0.20:8087/api/v1
```

### **16. RDP Server Manager**
```ini
[service]
name=rdp-server-manager
container_name=lucid-rdp-server-manager
image=pickme/lucid-rdp-server-manager:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.21
hostname=lucid-rdp-server-manager
ports=8081:8081,8090:8090
api_url=http://lucid-rdp-server-manager:8081
environment=RDP_SERVER_MANAGER_URL=http://lucid-rdp-server-manager:8081
healthcheck_port=8081
```

### **17. RDP XRDP**
```ini
[service]
name=rdp-xrdp
container_name=lucid-rdp-xrdp
image=pickme/lucid-rdp-xrdp:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.22
hostname=lucid-rdp-xrdp
ports=3389:3389
api_url=http://lucid-rdp-xrdp:3389
environment=XRDP_PORT=3389
healthcheck_port=3389
```

### **18. RDP Controller**
```ini
[service]
name=rdp-controller
container_name=lucid-rdp-controller
image=pickme/lucid-rdp-controller:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.23
hostname=lucid-rdp-controller
ports=8092:8092
api_url=http://lucid-rdp-controller:8092
environment=RDP_CONTROLLER_URL=http://lucid-rdp-controller:8092
healthcheck_port=8092
```

### **19. RDP Monitor**
```ini
[service]
name=rdp-monitor
container_name=lucid-rdp-monitor
image=pickme/lucid-rdp-monitor:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.24
hostname=lucid-rdp-monitor
ports=8093:8093
api_url=http://lucid-rdp-monitor:8093
environment=RDP_MONITOR_URL=http://lucid-rdp-monitor:8093
healthcheck_port=8093
```

### **20. Node Management**
```ini
[service]
name=node-management
container_name=lucid-node-management
image=pickme/lucid-node-management:latest-arm64
network=lucid-pi-network,lucid-gui-network
ipv4_address=172.20.0.25
hostname=lucid-node-management
ports=8095:8095,8099:8099
api_url=http://lucid-node-management:8095
environment=NODE_MANAGEMENT_URL=http://lucid-node-management:8095
healthcheck_port=8095
healthcheck_path=/health
electron_gui_endpoint=http://172.20.0.25:8095/api/v1
```

---

## 💼 **PHASE 4: SUPPORT SERVICES**

### **21. Admin Interface**
```ini
[service]
name=admin-interface
container_name=lucid-admin-interface
image=pickme/lucid-admin-interface:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.26
hostname=lucid-admin-interface
ports=8083:8083,8088:8088,8100:8100
api_url=http://lucid-admin-interface:8083
environment=ADMIN_INTERFACE_URL=http://lucid-admin-interface:8083
healthcheck_port=8083
healthcheck_path=/health
electron_gui_endpoint=http://172.20.0.26:8083/api/v1
```

### **22. TRON Client**
```ini
[service]
name=tron-client
container_name=lucid-tron-client
image=pickme/lucid-tron-client:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.27
hostname=lucid-tron-client
ports=8091:8091,8101:8101
api_url=http://lucid-tron-client:8091
environment=TRON_CLIENT_URL=http://lucid-tron-client:8091
healthcheck_port=8091
healthcheck_path=/health
electron_gui_endpoint=http://172.20.0.27:8091/api/v1
```

### **23. Payout Router**
```ini
[service]
name=payout-router
container_name=lucid-payout-router
image=pickme/lucid-payout-router:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.28
hostname=lucid-payout-router
ports=8092:8092,8102:8102
api_url=http://lucid-payout-router:8092
environment=PAYOUT_ROUTER_URL=http://lucid-payout-router:8092
healthcheck_port=8092
```

### **24. Wallet Manager**
```ini
[service]
name=wallet-manager
container_name=lucid-wallet-manager
image=pickme/lucid-wallet-manager:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.29
hostname=lucid-wallet-manager
ports=8093:8093,8103:8103
api_url=http://lucid-wallet-manager:8093
environment=WALLET_MANAGER_URL=http://lucid-wallet-manager:8093
healthcheck_port=8093
electron_gui_endpoint=http://172.20.0.29:8093/api/v1
```

### **25. USDT Manager**
```ini
[service]
name=usdt-manager
container_name=lucid-usdt-manager
image=pickme/lucid-usdt-manager:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.30
hostname=lucid-usdt-manager
ports=8094:8094,8104:8104
api_url=http://lucid-usdt-manager:8094
environment=USDT_MANAGER_URL=http://lucid-usdt-manager:8094
healthcheck_port=8094
```

### **26. TRX Staking**
```ini
[service]
name=trx-staking
container_name=lucid-trx-staking
image=pickme/lucid-trx-staking:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.31
hostname=lucid-trx-staking
ports=8096:8096,8105:8105
api_url=http://lucid-trx-staking:8096
environment=TRX_STAKING_URL=http://lucid-trx-staking:8096
healthcheck_port=8096
```

### **27. Payment Gateway**
```ini
[service]
name=payment-gateway
container_name=lucid-payment-gateway
image=pickme/lucid-payment-gateway:latest-arm64
network=lucid-pi-network
ipv4_address=172.20.0.32
hostname=lucid-payment-gateway
ports=8097:8097,8106:8106
api_url=http://lucid-payment-gateway:8097
environment=PAYMENT_GATEWAY_URL=http://lucid-payment-gateway:8097
healthcheck_port=8097
electron_gui_endpoint=http://172.20.0.32:8097/api/v1
```

---

## 🎨 **PHASE 5: SPECIALIZED SERVICES**

**Note:** The following services (GUI, RDP, VM, Database, Storage) are available as images but are not included in the main IP allocation scheme from path_plan.md. They can be deployed separately if needed.

## 🔧 **ELECTRON-GUI CONFIGURATION**

### **Service Endpoints for Electron-GUI**

#### **API Gateway Configuration**
```json
{
  "api": {
    "baseURL": "http://172.20.0.10:8080/api/v1",
    "timeout": 30000,
    "retries": 3,
    "healthCheckInterval": 30000
  },
  "services": {
    "auth": "http://172.20.0.14:8089",
    "blockchain": "http://172.20.0.15:8084",
    "sessions": "http://172.20.0.20:8087",
    "nodes": "http://172.20.0.25:8095",
    "admin": "http://172.20.0.26:8083",
    "tron": "http://172.20.0.27:8091",
    "wallet": "http://172.20.0.29:8093",
    "payment": "http://172.20.0.32:8097"
  }
}
```

#### **Network Connection Settings**
```ini
[network]
primary_network=lucid-pi-network
primary_subnet=172.20.0.0/16
primary_gateway=172.20.0.1

gui_network=lucid-gui-network
gui_subnet=172.22.0.0/16
gui_gateway=172.22.0.1

tron_network=lucid-tron-isolated
tron_subnet=172.21.0.0/16
tron_gateway=172.21.0.1
```

#### **Database Connections**
```ini
[mongodb]
host=172.20.0.11
port=27017
database=lucid_gateway
uri=mongodb://lucid:{MONGODB_PASSWORD}@172.20.0.11:27017/lucid?authSource=admin

[redis]
host=172.20.0.12
port=6379
database=0
uri=redis://172.20.0.12:6379/0

[elasticsearch]
host=172.20.0.13
port=9200
uri=http://172.20.0.13:9200
```

---

## 🔐 **SECURITY CONFIGURATION**

### **Network Isolation Rules**

```yaml
# Service Mesh Rules - Current Configuration (All on main network)
network_rules:
  - source: "172.20.0.0/16"  # Main Network (all services)
    destination: "172.20.0.0/16"  # Internal communication
    allowed_ports: [8080, 8081, 8082, 8083, 8084, 8085, 8086, 8087, 8088, 8089, 8090, 8091, 8092, 8093, 8094, 8095, 8096, 8097, 27017, 6379, 9200, 9300, 3389]
    protocol: "tcp"
    
# Future Isolation Rules (when TRON network is used):
  # - source: "172.21.0.0/16"  # TRON Network (isolated)
  #   destination: "172.20.0.0/16"  # Main Network
  #   allowed_ports: [8091, 8092, 8093, 8094, 8096, 8097]  # TRON services only
  #   protocol: "tcp"
```

### **API Gateway Security**
```ini
[api_gateway]
listen_address=172.20.0.10
listen_port=8080
https_port=8081
ssl_enabled=true
rate_limit_per_minute=1000
cors_allowed_origins=*
```

### **TRON Payment Configuration**
```ini
[tron_configuration]
tron_network=mainnet
tron_api_key=${TRON_API_KEY}
usdt_contract_address=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
tron_client_host=172.20.0.27
tron_client_port=8091
note=All TRON services run on main network (172.20.0.0/16)
```

---

## 📊 **MONITORING & HEALTH CHECKS**

### **Health Check Endpoints**

```ini
[health_checks]
api_gateway=http://172.20.0.10:8080/health
auth_service=http://172.20.0.14:8089/health
blockchain=http://172.20.0.15:8084/health
session_api=http://172.20.0.20:8087/health
node_management=http://172.20.0.25:8095/health
admin_interface=http://172.20.0.26:8083/health
tron_client=http://172.20.0.27:8091/health
wallet_manager=http://172.20.0.29:8093/health
payment_gateway=http://172.20.0.32:8097/health
```

---

## 🚀 **QUICK REFERENCE**

### **Most Critical Services for Electron-GUI**

| Service | IP Address | Port | Purpose |
|---------|------------|------|---------|
| API Gateway | 172.20.0.10 | 8080 | Main entry point |
| Auth Service | 172.20.0.14 | 8089 | Authentication |
| Session API | 172.20.0.20 | 8087 | Session management |
| Node Management | 172.20.0.25 | 8095 | Node operations |
| Admin Interface | 172.20.0.26 | 8083 | Admin dashboard |
| TRON Client | 172.20.0.27 | 8091 | TRON integration |
| Payout Router | 172.20.0.28 | 8092 | TRON payouts |
| Wallet Manager | 172.20.0.29 | 8093 | Wallet operations |
| USDT Manager | 172.20.0.30 | 8094 | USDT operations |
| TRX Staking | 172.20.0.31 | 8096 | TRX staking |
| Payment Gateway | 172.20.0.32 | 8097 | Payments |

### **Network Quick Reference**

```
Main Network (172.20.0.0/16) - lucid-pi-network:
  - Gateway: 172.20.0.1
  - All Services: 172.20.0.10 - 172.20.0.32
  - Total Services: 27 allocated IPs
  
Secondary Networks (Available but not used in current allocation):
  - TRON Network (172.21.0.0/16): Available for TRON isolation
  - GUI Network (172.22.0.0/16): Available for GUI services
  - Distroless Production (172.23.0.0/16): Available for distroless containers
  - Distroless Dev (172.24.0.0/16): Available for development
  - Multi-Stage Network (172.25.0.0/16): Available for multi-stage builds
```

---

## 📝 **USAGE NOTES**

1. **Network Isolation**: The TRON network (172.21.0.0/16) is isolated for security
2. **GUI Access**: GUI network (172.22.0.0/16) provides admin access
3. **Main Network**: Most services run on the main network (172.20.0.0/16)
4. **Health Checks**: All services provide `/health` endpoints
5. **API Versioning**: All APIs use `/api/v1` prefix

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-01-24  
**Maintained By:** HamiGames/Lucid Team
