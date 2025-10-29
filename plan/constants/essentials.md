#deployment_conditions
## all the context in this document is to help with validation of configurations for the files responsible for the deployment and running of the Lucid project.

*Key aspects* 
**Goal:** to ensure all files required for the launch and running of the project (identified in the plan/constants/Core_plan.md file) are fulfilled, and all constants required by the project are met 100%.
**Deployment:** deployment will be done directly from the pi-consoles project root (/mnt/myssd/Lucid/Lucid/), and all volumes will stem from the projects root path.
**Env files:** all env files will be created on the pi console and used in the deployment and running of the operation services that make up the "Lucid" project. 

*Deployment constants criteria:*
**Env file paths:**
'''
/mnt/myssd/Lucid/Lucid/03-api-gateway/api/.env.api
/mnt/myssd/Lucid/Lucid/03-api-gateway/api/.env.api.secrets
/mnt/myssd/Lucid/Lucid/03-api-gateway/env.template
/mnt/myssd/Lucid/Lucid/admin/env.example
/mnt/myssd/Lucid/Lucid/auth/.env.authentication
/mnt/myssd/Lucid/Lucid/auth/env.example
/mnt/myssd/Lucid/Lucid/blockchain/api/env.example
/mnt/myssd/Lucid/Lucid/build/config/session-images.env
/mnt/myssd/Lucid/Lucid/compose/.env.example
/mnt/myssd/Lucid/Lucid/configs/docker/distroless/distroless.env
/mnt/myssd/Lucid/Lucid/configs/docker/distroless/production.env
/mnt/myssd/Lucid/Lucid/configs/docker/docker.env
/mnt/myssd/Lucid/Lucid/configs/docker/multi-stage/multi-stage.env
/mnt/myssd/Lucid/Lucid/configs/environment/.env.api
/mnt/myssd/Lucid/Lucid/configs/environment/.env.api-gateway
/mnt/myssd/Lucid/Lucid/configs/environment/.env.application
/mnt/myssd/Lucid/Lucid/configs/environment/.env.application.template
/mnt/myssd/Lucid/Lucid/configs/environment/.env.authentication
/mnt/myssd/Lucid/Lucid/configs/environment/.env.authentication-service-distroless
/mnt/myssd/Lucid/Lucid/configs/environment/.env.blockchain-api
/mnt/myssd/Lucid/Lucid/configs/environment/.env.blockchain-governance
/mnt/myssd/Lucid/Lucid/configs/environment/.env.core
/mnt/myssd/Lucid/Lucid/configs/environment/.env.development
/mnt/myssd/Lucid/Lucid/configs/environment/.env.distroless
/mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
/mnt/myssd/Lucid/Lucid/configs/environment/.env.gui
/mnt/myssd/Lucid/Lucid/configs/environment/.env.master
/mnt/myssd/Lucid/Lucid/configs/environment/.env.openapi-gateway
/mnt/myssd/Lucid/Lucid/configs/environment/.env.openapi-server
/mnt/myssd/Lucid/Lucid/configs/environment/.env.pi
/mnt/myssd/Lucid/Lucid/configs/environment/.env.pi-build
/mnt/myssd/Lucid/Lucid/configs/environment/.env.production
/mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
/mnt/myssd/Lucid/Lucid/configs/environment/.env.secure
/mnt/myssd/Lucid/Lucid/configs/environment/.env.secure.template
/mnt/myssd/Lucid/Lucid/configs/environment/.env.server-tools
/mnt/myssd/Lucid/Lucid/configs/environment/.env.staging
/mnt/myssd/Lucid/Lucid/configs/environment/.env.support
/mnt/myssd/Lucid/Lucid/configs/environment/.env.test
/mnt/myssd/Lucid/Lucid/configs/environment/.env.tor-proxy
/mnt/myssd/Lucid/Lucid/configs/environment/.env.tron-client
/mnt/myssd/Lucid/Lucid/configs/environment/.env.tron-payment-gateway
/mnt/myssd/Lucid/Lucid/configs/environment/.env.tron-payout-router
/mnt/myssd/Lucid/Lucid/configs/environment/.env.tron-secrets
/mnt/myssd/Lucid/Lucid/configs/environment/.env.tron-staking
/mnt/myssd/Lucid/Lucid/configs/environment/.env.tron-usdt-manager
/mnt/myssd/Lucid/Lucid/configs/environment/.env.tron-wallet-manager
/mnt/myssd/Lucid/Lucid/configs/environment/.env.tunnel-tools
/mnt/myssd/Lucid/Lucid/configs/environment/.env.user
/mnt/myssd/Lucid/Lucid/configs/environment/env.coordination.yml
/mnt/myssd/Lucid/Lucid/configs/environment/env.development
/mnt/myssd/Lucid/Lucid/configs/environment/env.foundation
/mnt/myssd/Lucid/Lucid/configs/environment/env.gui
/mnt/myssd/Lucid/Lucid/configs/environment/env.production
/mnt/myssd/Lucid/Lucid/configs/environment/env.staging
/mnt/myssd/Lucid/Lucid/configs/environment/env.test
/mnt/myssd/Lucid/Lucid/configs/environment/layer2-simple.env
/mnt/myssd/Lucid/Lucid/configs/environment/layer2.env
/mnt/myssd/Lucid/Lucid/electron-gui/.env.development
/mnt/myssd/Lucid/Lucid/electron-gui/.env.production
/mnt/myssd/Lucid/Lucid/electron-gui/configs/env.development.json
/mnt/myssd/Lucid/Lucid/electron-gui/configs/env.production.json
/mnt/myssd/Lucid/Lucid/infrastructure/containers/base/env.template
/mnt/myssd/Lucid/Lucid/infrastructure/docker/blockchain/env/.env.blockchain-api
/mnt/myssd/Lucid/Lucid/infrastructure/docker/blockchain/env/.env.blockchain-governance
/mnt/myssd/Lucid/Lucid/infrastructure/docker/blockchain/env/.env.blockchain-ledger
/mnt/myssd/Lucid/Lucid/infrastructure/docker/blockchain/env/.env.blockchain-sessions-data
/mnt/myssd/Lucid/Lucid/infrastructure/docker/blockchain/env/.env.blockchain-vm
/mnt/myssd/Lucid/Lucid/infrastructure/docker/blockchain/env/.env.contract-compiler
/mnt/myssd/Lucid/Lucid/infrastructure/docker/blockchain/env/.env.contract-deployment
/mnt/myssd/Lucid/Lucid/infrastructure/docker/blockchain/env/.env.deployment-orchestrator
/mnt/myssd/Lucid/Lucid/infrastructure/docker/blockchain/env/.env.on-system-chain-client
/mnt/myssd/Lucid/Lucid/infrastructure/docker/blockchain/env/.env.tron-node-client
/mnt/myssd/Lucid/Lucid/infrastructure/docker/blockchain/env/blockchain-api.env
/mnt/myssd/Lucid/Lucid/infrastructure/docker/blockchain/env/blockchain-governance.env
/mnt/myssd/Lucid/Lucid/infrastructure/docker/blockchain/env/blockchain-ledger.env
/mnt/myssd/Lucid/Lucid/infrastructure/docker/blockchain/env/blockchain-sessions-data.env
/mnt/myssd/Lucid/Lucid/infrastructure/docker/blockchain/env/blockchain-vm.env
/mnt/myssd/Lucid/Lucid/infrastructure/docker/blockchain/env/contract-compiler.env
/mnt/myssd/Lucid/Lucid/infrastructure/docker/blockchain/env/contract-deployment.env
/mnt/myssd/Lucid/Lucid/infrastructure/docker/blockchain/env/deployment-orchestrator.env
/mnt/myssd/Lucid/Lucid/infrastructure/docker/blockchain/env/on-system-chain-client.env
/mnt/myssd/Lucid/Lucid/infrastructure/docker/blockchain/env/tron-node-client.env
/mnt/myssd/Lucid/Lucid/infrastructure/docker/databases/env/.env.database-backup
/mnt/myssd/Lucid/Lucid/infrastructure/docker/databases/env/.env.database-migration
/mnt/myssd/Lucid/Lucid/infrastructure/docker/databases/env/.env.database-monitoring
/mnt/myssd/Lucid/Lucid/infrastructure/docker/databases/env/.env.database-restore
/mnt/myssd/Lucid/Lucid/infrastructure/docker/databases/env/.env.mongodb
/mnt/myssd/Lucid/Lucid/infrastructure/docker/databases/env/.env.mongodb-init
/mnt/myssd/Lucid/Lucid/infrastructure/docker/databases/env/database-backup.env
/mnt/myssd/Lucid/Lucid/infrastructure/docker/databases/env/database-migration.env
/mnt/myssd/Lucid/Lucid/infrastructure/docker/databases/env/database-monitoring.env
/mnt/myssd/Lucid/Lucid/infrastructure/docker/databases/env/database-restore.env
/mnt/myssd/Lucid/Lucid/infrastructure/docker/databases/env/mongodb-init.env
/mnt/myssd/Lucid/Lucid/infrastructure/docker/databases/env/mongodb.env
/mnt/myssd/Lucid/Lucid/node/env.example
/mnt/myssd/Lucid/Lucid/payment-systems/tron/env.example
/mnt/myssd/Lucid/Lucid/sessions/core/.env.chunker
/mnt/myssd/Lucid/Lucid/sessions/core/.env.merkle_builder
/mnt/myssd/Lucid/Lucid/sessions/core/.env.orchestrator
/mnt/myssd/Lucid/Lucid/sessions/core/.env.sessions.secrets
/mnt/myssd/Lucid/Lucid/sessions/encryption/.env.encryptor
'''
*Network configurations:*
1. **lucid-pi-network**: `172.20.0.0/16` (Gateway: 172.20.0.1) - Primary network
2. **lucid-tron-isolated**: `172.21.0.0/16` (Gateway: 172.21.0.1) - TRON payment isolation
3. **lucid-gui-network**: `172.22.0.0/16` (Gateway: 172.22.0.1) - GUI services
4. **lucid-distroless-production**: `172.23.0.0/16` - Production distroless
5. **lucid-distroless-dev**: `172.24.0.0/16` - Development distroless
6. **lucid-multi-stage-network**: `172.25.0.0/16` - Multi-stage builds

## **PHASE 1: FOUNDATION SERVICES**

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

## **PHASE 2: CORE SERVICES**

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

## **PHASE 3: APPLICATION SERVICES**

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

## **PHASE 4: SUPPORT SERVICES**

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

## **PHASE 5: SPECIALIZED SERVICES**

**Note:** The following services (GUI, RDP, VM, Database, Storage) are available as images but are not included in the main IP allocation scheme from path_plan.md. They can be deployed separately if needed.

##  **ELECTRON-GUI CONFIGURATION**

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
**API Gateway Security**
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

 **MONITORING & HEALTH CHECKS**

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

**QUICK REFERENCE**

**Most Critical Services for Electron-GUI**

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

**Network Quick Reference**

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

#### **USAGE NOTES**

1. **Network Isolation**: The TRON network (172.21.0.0/16) is isolated for security
2. **GUI Access**: GUI network (172.22.0.0/16) provides admin access
3. **Main Network**: Most services run on the main network (172.20.0.0/16)
4. **Health Checks**: All services provide `/health` endpoints
5. **API Versioning**: All APIs use `/api/v1` prefix


# **PORTS in use: images and service names**
## **Ports by Category**
### **Database & Cache:**
'''
27017: MongoDB primary
27018: MongoDB (RDP services)
6379: Redis primary
9200: Elasticsearch HTTP
9300: Elasticsearch transport
'''
### **Core Application (8080-8089):**
'''
8080, 8081: API Gateway
8082: Session Storage
8083: Admin Interface
8084: Blockchain Engine
8085: Session Anchoring
8086: Block Manager
8087: Data Chain / Session Pipeline / Session API
8088: Admin Interface (staging) / Service Mesh
8089: Auth Service
'''
## **Application & RDP (8090-8099):**
'''
8090: Session Recorder / RDP Server Manager
8091: Chunk Processor / TRON Client
8092: Session Controller / RDP Controller / Payout Router
8093: RDP Monitor / Wallet Manager
8094: USDT Manager / RDP Controller
8095: Node Management / TRX Staking
8096: TRX Staking / Node Management
8097: Payment Gateway
8099: Node Management (staging)
'''
### ** Monitoring & Extended (8100-8107):**
'''
8100: Admin Interface (monitoring)
8101-8106: TRON Payment services (monitoring)
8107: Service Mesh (monitoring)
Special Ports:
3389: XRDP Integration (RDP protocol)
8000: GUI base application
8500-8502, 8600: Service Mesh Controller (Consul)
'''
## PHASE 1: FOUNDATION SERVICES (4 images)

### lucid-mongodb
- **Image**: `pickme/lucid-mongodb:latest-arm64`
- **Port(s)**: 27017

### lucid-redis
- **Image**: `pickme/lucid-redis:latest-arm64`
- **Port(s)**: 6379

### lucid-elasticsearch
- **Image**: `pickme/lucid-elasticsearch:latest-arm64`
- **Port(s)**: 9200, 9300

### lucid-auth-service
- **Image**: `pickme/lucid-auth-service:latest-arm64`
- **Port(s)**: 8089

---
# Port(s) in use: **Images**
## PHASE 2: CORE SERVICES (6 images)

### lucid-api-gateway
- **Image**: `pickme/lucid-api-gateway:latest-arm64`
- **Port(s)**: 8080, 8081

### lucid-service-mesh-controller
- **Image**: `pickme/lucid-service-mesh-controller:latest-arm64`
- **Port(s)**: 8500, 8501, 8502, 8600, 8088

### lucid-blockchain-engine
- **Image**: `pickme/lucid-blockchain-engine:latest-arm64`
- **Port(s)**: 8084

### lucid-session-anchoring
- **Image**: `pickme/lucid-session-anchoring:latest-arm64`
- **Port(s)**: 8085

### lucid-block-manager
- **Image**: `pickme/lucid-block-manager:latest-arm64`
- **Port(s)**: 8086

### lucid-data-chain
- **Image**: `pickme/lucid-data-chain:latest-arm64`
- **Port(s)**: 8087

---

## PHASE 3: APPLICATION SERVICES (10 images)

### lucid-session-pipeline
- **Image**: `pickme/lucid-session-pipeline:latest-arm64`
- **Port(s)**: 8087

### lucid-session-recorder
- **Image**: `pickme/lucid-session-recorder:latest-arm64`
- **Port(s)**: 8090

### lucid-chunk-processor
- **Image**: `pickme/lucid-chunk-processor:latest-arm64`
- **Port(s)**: 8091

### lucid-session-storage
- **Image**: `pickme/lucid-session-storage:latest-arm64`
- **Port(s)**: 8082

### lucid-session-api
- **Image**: `pickme/lucid-session-api:latest-arm64`
- **Port(s)**: 8087

### lucid-rdp-server-manager
- **Image**: `pickme/lucid-rdp-server-manager:latest-arm64`
- **Port(s)**: 8081, 8090

### lucid-rdp-xrdp
- **Image**: `pickme/lucid-rdp-xrdp:latest-arm64`
- **Port(s)**: 3389

### lucid-rdp-controller
- **Image**: `pickme/lucid-rdp-controller:latest-arm64`
- **Port(s)**: 8092

### lucid-rdp-monitor
- **Image**: `pickme/lucid-rdp-monitor:latest-arm64`
- **Port(s)**: 8093

### lucid-node-management
- **Image**: `pickme/lucid-node-management:latest-arm64`
- **Port(s)**: 8095, 8099

---

## PHASE 4: SUPPORT SERVICES (7 images)

### lucid-admin-interface
- **Image**: `pickme/lucid-admin-interface:latest-arm64`
- **Port(s)**: 8083, 8088, 8100

### lucid-tron-client
- **Image**: `pickme/lucid-tron-client:latest-arm64`
- **Port(s)**: 8091, 8101

### lucid-payout-router
- **Image**: `pickme/lucid-payout-router:latest-arm64`
- **Port(s)**: 8092, 8102

### lucid-wallet-manager
- **Image**: `pickme/lucid-wallet-manager:latest-arm64`
- **Port(s)**: 8093, 8103

### lucid-usdt-manager
- **Image**: `pickme/lucid-usdt-manager:latest-arm64`
- **Port(s)**: 8094, 8104

### lucid-trx-staking
- **Image**: `pickme/lucid-trx-staking:latest-arm64`
- **Port(s)**: 8096, 8105

### lucid-payment-gateway
- **Image**: `pickme/lucid-payment-gateway:latest-arm64`
- **Port(s)**: 8097, 8106

---

## PHASE 5: SPECIALIZED SERVICES (5 images)

### lucid-gui
- **Image**: `pickme/lucid-gui:latest-arm64`
- **Port(s)**: 8000

### lucid-vm
- **Image**: `pickme/lucid-vm:latest-arm64`
- **Port(s)**: 8103

### lucid-database
- **Image**: `pickme/lucid-database:latest-arm64`
- **Port(s)**: 27018

### lucid-storage
- **Image**: `pickme/lucid-storage:latest-arm64`
- **Port(s)**: 8104

### lucid-rdp
- **Image**: `pickme/lucid-rdp:latest-arm64`
- **Port(s)**: Not specified in constants

---

## PHASE 1: BASE INFRASTRUCTURE (3 images - build only, not runtime services)

### Base image (python-distroless)
- **Image**: `pickme/lucid-base:python-distroless-arm64`
- **Port(s)**: N/A

### Base image (java-distroless)
- **Image**: `pickme/lucid-base:java-distroless-arm64`
- **Port(s)**: N/A

### Base image (latest)
- **Image**: `pickme/lucid-base:latest-arm64`
- **Port(s)**: N/A

---

## **Lucid Project Directory files**
### **ALL file Project Tree:** "plan/constants/folder_tree.txt"
### **Folders only Project Tree:** " plan/constants/project_tree.txt"
### **Project PowerShell Root:** "C:\Users\surba\Desktop\personal\THE_FUCKER\lucid_2\Lucid" 
### **Project Bash Root:** "~/Desktop/personal/THE_FUCKER/lucid_2/Lucid"
### **Platform:** "linux/arm64"