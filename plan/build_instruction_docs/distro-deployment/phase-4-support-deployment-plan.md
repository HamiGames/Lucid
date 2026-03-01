# Phase 4: Support Services Distroless Deployment Plan

## Overview

Deploy Support Services (Phase 4) with true distroless containers on Raspberry Pi 5 at 192.168.0.75. This phase includes Admin Interface and TRON Payment Services (TRON Client, Payout Router, Wallet Manager, USDT Manager, Staking, Payment Gateway) with proper volume management, environment configuration, and security hardening.

**PREREQUISITES:** Phase 1 Foundation, Phase 2 Core, AND Phase 3 Application Services must be deployed and healthy before proceeding.

## Prerequisites

- Phase 1 Foundation Services deployed and running healthy
- Phase 2 Core Services deployed and running healthy
- Phase 3 Application Services deployed and running healthy
- SSH access: `ssh pickme@192.168.0.75`
- Project root: `/mnt/myssd/Lucid/Lucid`
- Docker and Docker Compose installed on Pi
- Pre-built images on Docker Hub: `pickme/lucid-*:latest-arm64`
- Networks already created (from Phase 1): `lucid-pi-network` and `lucid-tron-isolated`
- Foundation services running: MongoDB, Redis, Elasticsearch, Auth Service
- Core services running: API Gateway, Blockchain Engine, Service Mesh
- Application services running: Session API, RDP Services, Node Management

## File Updates Required

### 1. Update Support Docker Compose with Volumes

**File:** `configs/docker/docker-compose.support.yml`

Add volume configurations and port mappings to all services:

**Admin Interface volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/admin-interface:/app/data:rw
  - /mnt/myssd/Lucid/logs/admin-interface:/app/logs:rw
  - admin-interface-cache:/tmp/admin
ports:
  - "8083:8083"
```

**TRON Client volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/tron-client:/app/data:rw
  - /mnt/myssd/Lucid/logs/tron-client:/app/logs:rw
  - tron-client-cache:/tmp/tron
ports:
  - "8091:8091"
```

**TRON Payout Router volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/tron-payout-router:/app/data:rw
  - /mnt/myssd/Lucid/logs/tron-payout-router:/app/logs:rw
  - tron-payout-router-cache:/tmp/payouts
ports:
  - "8092:8092"
```

**TRON Wallet Manager volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/tron-wallet-manager:/app/data:rw
  - /mnt/myssd/Lucid/logs/tron-wallet-manager:/app/logs:rw
  - tron-wallet-manager-cache:/tmp/wallets
ports:
  - "8093:8093"
```

**TRON USDT Manager volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/tron-usdt-manager:/app/data:rw
  - /mnt/myssd/Lucid/logs/tron-usdt-manager:/app/logs:rw
  - tron-usdt-manager-cache:/tmp/usdt
ports:
  - "8094:8094"
```

**TRON Staking volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/tron-staking:/app/data:rw
  - /mnt/myssd/Lucid/logs/tron-staking:/app/logs:rw
  - tron-staking-cache:/tmp/staking
ports:
  - "8096:8096"
```

**TRON Payment Gateway volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/tron-payment-gateway:/app/data:rw
  - /mnt/myssd/Lucid/logs/tron-payment-gateway:/app/logs:rw
  - tron-payment-gateway-cache:/tmp/gateway
ports:
  - "8097:8097"
```

Add named volumes section at end:

```yaml
volumes:
  admin-interface-cache:
    driver: local
    name: lucid-admin-interface-cache
  tron-client-cache:
    driver: local
    name: lucid-tron-client-cache
  tron-payout-router-cache:
    driver: local
    name: lucid-tron-payout-router-cache
  tron-wallet-manager-cache:
    driver: local
    name: lucid-tron-wallet-manager-cache
  tron-usdt-manager-cache:
    driver: local
    name: lucid-tron-usdt-manager-cache
  tron-staking-cache:
    driver: local
    name: lucid-tron-staking-cache
  tron-payment-gateway-cache:
    driver: local
    name: lucid-tron-payment-gateway-cache
```

### 2. Verify Environment Variable Consistency

**Files to check:**

- `configs/environment/env.foundation` (for cross-references)
- `configs/environment/env.core` (for cross-references)
- `configs/environment/env.application` (for cross-references)
- Create `configs/environment/env.support` if missing

Ensure naming conventions match:

- Container names: `admin-interface`, `tron-client`, `tron-payout-router`, `tron-wallet-manager`, `tron-usdt-manager`, `tron-staking`, `tron-payment-gateway`
- Service hosts: Same as container names
- Networks: `lucid-pi-network` (for Admin), `lucid-tron-isolated` (for TRON services)
- User: `65532:65532` (distroless standard)
- Image names: `pickme/lucid-[service]:latest-arm64`
- Environment variable references from Phase 1, 2 & 3: `${MONGODB_URL}`, `${REDIS_URL}`, `${AUTH_SERVICE_URL}`, `${API_GATEWAY_URL}`, `${NODE_MANAGEMENT_URL}`
- TRON-specific variables: `${TRON_NETWORK}`, `${TRON_NODE_URL}`, `${TRON_PRIVATE_KEY}`, `${TRON_ADDRESS}`, `${USDT_CONTRACT_ADDRESS}`

### 3. Create/Verify Support Environment Generation Script

**File:** `scripts/config/generate-support-env.sh` (if missing)

Should follow same pattern as previous generation scripts and include Support service-specific variables including TRON configuration.

## Deployment Steps (SSH to Pi)

### Phase 4A: Verify Phase 1, 2 & 3 Services

```bash
# SSH to Pi
ssh pickme@192.168.0.75
cd /mnt/myssd/Lucid/Lucid

# Verify Phase 1 services are healthy
docker ps | grep -E "lucid-mongodb|lucid-redis|lucid-elasticsearch|lucid-auth-service"
docker ps --filter health=healthy | grep -E "lucid-mongodb|lucid-redis|lucid-auth-service"

# Verify Phase 2 services are healthy
docker ps | grep -E "api-gateway|blockchain-engine|service-mesh"
docker ps --filter health=healthy | grep -E "api-gateway|blockchain-engine|service-mesh"

# Verify Phase 3 services are healthy
docker ps | grep -E "session-api|rdp-server-manager|node-management"
docker ps --filter health=healthy | grep -E "session-api|rdp-server-manager|node-management"

# Test Phase 1, 2, 3 connectivity
docker exec lucid-mongodb mongosh --eval "db.adminCommand('ping')"
docker exec lucid-redis redis-cli ping
curl -f http://localhost:8089/health || echo "Auth service not ready"
curl -f http://localhost:8080/health || echo "API Gateway not ready"
curl -f http://localhost:8087/health || echo "Session API not ready"
curl -f http://localhost:8095/health || echo "Node Management not ready"

# Verify both networks exist
docker network ls | grep -E "lucid-pi-network|lucid-tron-isolated"
docker network inspect lucid-pi-network | grep -E "Subnet|Gateway"
docker network inspect lucid-tron-isolated | grep -E "Subnet|Gateway"
```

### Phase 4B: Directory Structure

```bash
# Create Phase 4 data directories
sudo mkdir -p /mnt/myssd/Lucid/data/{admin-interface,tron-client,tron-payout-router,tron-wallet-manager,tron-usdt-manager,tron-staking,tron-payment-gateway}
sudo mkdir -p /mnt/myssd/Lucid/logs/{admin-interface,tron-client,tron-payout-router,tron-wallet-manager,tron-usdt-manager,tron-staking,tron-payment-gateway}

# Set ownership
sudo chown -R pickme:pickme /mnt/myssd/Lucid/data
sudo chown -R pickme:pickme /mnt/myssd/Lucid/logs

# Verify directories
ls -la /mnt/myssd/Lucid/data/
ls -la /mnt/myssd/Lucid/logs/
du -sh /mnt/myssd/Lucid/data/*
```

### Phase 4C: Environment Configuration

**Option 1: If not already generated**

```bash
# Generate support environment (requires Phase 1, 2 & 3 env files)
cd /mnt/myssd/Lucid/Lucid
chmod +x scripts/config/generate-support-env.sh
bash scripts/config/generate-support-env.sh

# Verify
ls -la configs/environment/env.support
grep -E "ADMIN_INTERFACE_HOST|TRON_CLIENT_HOST|TRON_NETWORK" configs/environment/env.support
```

**Option 2: If already configured**

```bash
# Verify file exists and has required variables
ls -la configs/environment/env.support
grep -E "ADMIN_INTERFACE_PORT|TRON_NODE_URL|USDT_CONTRACT_ADDRESS" configs/environment/env.support
```

### Phase 4D: Pull Docker Images

```bash
# Pull admin interface image
docker pull pickme/lucid-admin-interface:latest-arm64

# Pull TRON payment service images
docker pull pickme/lucid-tron-client:latest-arm64
docker pull pickme/lucid-tron-payout-router:latest-arm64
docker pull pickme/lucid-tron-wallet-manager:latest-arm64
docker pull pickme/lucid-tron-usdt-manager:latest-arm64
docker pull pickme/lucid-tron-staking:latest-arm64
docker pull pickme/lucid-tron-payment-gateway:latest-arm64

# Verify all images
docker images | grep pickme/lucid | grep -E "admin|tron"
```

### Phase 4E: Deploy Support Services

```bash
cd /mnt/myssd/Lucid/Lucid

# Deploy Support Services using all env files (Foundation + Core + Application + Support)
docker-compose \
  --env-file configs/environment/env.foundation \
  --env-file configs/environment/env.core \
  --env-file configs/environment/env.application \
  --env-file configs/environment/env.support \
  -f configs/docker/docker-compose.support.yml \
  up -d

# Verify services starting
docker ps | grep admin-interface
docker ps | grep -E "tron-client|tron-payout|tron-wallet|tron-usdt|tron-staking|tron-payment"
```

### Phase 4F: Verification & Health Checks

```bash
# Wait for services to initialize (90 seconds for TRON services)
sleep 90

# Check all Phase 4 containers running
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "admin|tron"

# Check health status
docker ps --filter health=healthy | grep -E "admin-interface|tron-client"

# Verify Admin Interface
curl http://localhost:8083/health || echo "Admin Interface not ready"

# Verify TRON Services
curl http://localhost:8091/health || echo "TRON Client not ready"
curl http://localhost:8092/health || echo "TRON Payout Router not ready"
curl http://localhost:8093/health || echo "TRON Wallet Manager not ready"
curl http://localhost:8094/health || echo "TRON USDT Manager not ready"
curl http://localhost:8096/health || echo "TRON Staking not ready"
curl http://localhost:8097/health || echo "TRON Payment Gateway not ready"

# Check logs for errors
docker logs admin-interface --tail 50
docker logs tron-client --tail 50
docker logs tron-payout-router --tail 50
docker logs tron-payment-gateway --tail 50

# Verify distroless compliance for all services
for service in admin-interface tron-client tron-payout-router tron-wallet-manager tron-usdt-manager tron-staking tron-payment-gateway; do
  echo "Checking $service..."
  docker exec $service id
  docker exec $service sh -c "echo test" 2>&1 | grep "executable file not found"
done

# Verify volumes mounted
docker inspect admin-interface | grep -A 10 "Mounts"
docker inspect tron-client | grep -A 10 "Mounts"
docker inspect tron-payment-gateway | grep -A 10 "Mounts"

# Check disk usage
df -h /mnt/myssd/Lucid/data/
du -sh /mnt/myssd/Lucid/data/*
du -sh /mnt/myssd/Lucid/logs/*
```

### Phase 4G: Integration Testing

```bash
# Verify network connectivity between Phase 4 and previous phases
# Test from Admin Interface to Phase 1 services
docker exec admin-interface python3 -c "import socket; socket.create_connection(('lucid-mongodb', 27017), timeout=5); print('MongoDB connection OK')"
docker exec admin-interface python3 -c "import socket; socket.create_connection(('lucid-redis', 6379), timeout=5); print('Redis connection OK')"
docker exec admin-interface python3 -c "import socket; socket.create_connection(('lucid-auth-service', 8089), timeout=5); print('Auth Service connection OK')"

# Test from Admin Interface to Phase 2 services
docker exec admin-interface python3 -c "import socket; socket.create_connection(('api-gateway', 8080), timeout=5); print('API Gateway connection OK')"
docker exec admin-interface python3 -c "import socket; socket.create_connection(('blockchain-engine', 8084), timeout=5); print('Blockchain Engine connection OK')"

# Test from Admin Interface to Phase 3 services
docker exec admin-interface python3 -c "import socket; socket.create_connection(('session-api', 8087), timeout=5); print('Session API connection OK')"
docker exec admin-interface python3 -c "import socket; socket.create_connection(('rdp-server-manager', 8090), timeout=5); print('RDP Server Manager connection OK')"
docker exec admin-interface python3 -c "import socket; socket.create_connection(('node-management', 8095), timeout=5); print('Node Management connection OK')"

# Test Admin Interface API endpoints
curl -X GET http://localhost:8083/api/v1/admin/system/status
curl -X GET http://localhost:8083/api/v1/admin/dashboard
curl -X GET http://localhost:8083/health

# Test TRON Client
curl -X GET http://localhost:8091/api/v1/tron/status
curl -X GET http://localhost:8091/api/v1/tron/balance
curl -X GET http://localhost:8091/health

# Test TRON Payout Router
curl -X GET http://localhost:8092/api/v1/payouts/status
curl -X GET http://localhost:8092/api/v1/payouts/queue

# Test TRON Payment Gateway
curl -X GET http://localhost:8097/api/v1/payments/status
curl -X GET http://localhost:8097/health

# Verify TRON network isolation
docker network inspect lucid-tron-isolated | grep -A 20 "Containers"

# Verify service registration in Service Mesh
curl -X GET http://localhost:8500/v1/catalog/service/admin-interface
curl -X GET http://localhost:8500/v1/catalog/service/tron-client
```

## Verification Checklist

- [ ] Phase 1 Foundation Services healthy and running
- [ ] Phase 2 Core Services healthy and running
- [ ] Phase 3 Application Services healthy and running
- [ ] Phase 4 data directories created with correct permissions
- [ ] Phase 4 log directories created with correct permissions
- [ ] Support environment file generated/verified
- [ ] All Phase 4 images pulled successfully
- [ ] Admin Interface container running and healthy
- [ ] TRON Client container running and healthy
- [ ] TRON Payout Router container running and healthy
- [ ] TRON Wallet Manager container running and healthy
- [ ] TRON USDT Manager container running and healthy
- [ ] TRON Staking container running and healthy
- [ ] TRON Payment Gateway container running and healthy
- [ ] All services using user 65532:65532
- [ ] No shell access verified on all containers
- [ ] Health checks passing on all services
- [ ] Volumes correctly mounted on all services
- [ ] Network connectivity verified between all phases
- [ ] Admin Interface responding and integrated with all services
- [ ] TRON services responding
- [ ] TRON network isolation verified
- [ ] Integration tests passing

## Rollback Procedure

```bash
# Stop and remove Support services only (keeps Phase 1, 2, and 3 running)
docker-compose -f configs/docker/docker-compose.support.yml down

# Remove named volumes (optional, keeps data)
docker volume ls | grep -E "admin|tron"
docker volume rm lucid-admin-interface-cache lucid-tron-client-cache lucid-tron-payout-router-cache lucid-tron-wallet-manager-cache lucid-tron-usdt-manager-cache lucid-tron-staking-cache lucid-tron-payment-gateway-cache

# Data remains in /mnt/myssd/Lucid/data/ for recovery
# Phase 1, 2, and 3 services continue running unaffected
```

## Key Files Modified

1. `configs/docker/docker-compose.support.yml` - Add volumes and ports
2. `configs/environment/env.support` - Verify consistency and TRON configuration
3. Create `scripts/config/generate-support-env.sh` if missing

## Naming Convention Standards

All naming follows these patterns:

- **Images**: `pickme/lucid-[service]:latest-arm64`
- **Containers**: `[service-name]` (e.g., `admin-interface`, `tron-client`, `tron-payment-gateway`)
- **Networks**: `lucid-pi-network` (for Admin), `lucid-tron-isolated` (for TRON services)
- **Volumes (named)**: `lucid-[service]-cache`
- **Volumes (host)**: `/mnt/myssd/Lucid/[type]/[service]`
- **User**: `65532:65532` (distroless standard)
- **Environment variables**: `[SERVICE]_[PROPERTY]` (e.g., `ADMIN_INTERFACE_HOST`, `TRON_CLIENT_PORT`)
- **Service URLs**: `http://[container-name]:[port]` (e.g., `http://admin-interface:8083`)

## Service Dependencies

Phase 4 services depend on Phase 1, 2, and 3:

**Admin Interface:**

- **Admin Interface** → MongoDB, Redis, Auth Service, API Gateway, Blockchain Engine, Session API, RDP Services, Node Management

**TRON Payment Services:**

- **TRON Client** → MongoDB, Redis, TRON Network (external)
- **TRON Payout Router** → MongoDB, Redis, TRON Client, Node Management
- **TRON Wallet Manager** → MongoDB, Redis, TRON Client
- **TRON USDT Manager** → MongoDB, Redis, TRON Client, USDT Contract (external)
- **TRON Staking** → MongoDB, Redis, TRON Client
- **TRON Payment Gateway** → MongoDB, Redis, TRON Client, All TRON Services

## Port Mapping

Phase 4 exposed ports:

**Admin Interface:**

- **8083**: Admin Interface (external access)

**TRON Payment Services:**

- **8091**: TRON Client (internal/isolated network)
- **8092**: TRON Payout Router (internal/isolated network)
- **8093**: TRON Wallet Manager (internal/isolated network)
- **8094**: TRON USDT Manager (internal/isolated network)
- **8096**: TRON Staking (internal/isolated network)
- **8097**: TRON Payment Gateway (external access to isolated network bridge)

## Network Isolation

**TRON Network Isolation:**

- All TRON services run on `lucid-tron-isolated` network (172.21.0.0/16)
- Admin Interface runs on `lucid-pi-network` (172.20.0.0/16)
- TRON Payment Gateway acts as bridge between networks
- Direct access to TRON services only via Payment Gateway
- Enhanced security for payment operations

## Security Considerations

**TRON Private Key Management:**

- `TRON_PRIVATE_KEY` must be securely stored and never logged
- Use environment variable encryption
- Rotate keys periodically
- Monitor for unauthorized transactions

**USDT Contract:**

- Verify contract address matches official USDT on TRON network
- Mainnet: `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t`
- Test network: Use appropriate testnet contract

## Deployment Complete

After Phase 4 verification complete, all Lucid distroless services are deployed:

- **Phase 1**: Foundation Services (4 services)
- **Phase 2**: Core Services (6 services)
- **Phase 3**: Application Services (10 services)
- **Phase 4**: Support Services (7 services)

**Total**: 27 distroless containers running on Raspberry Pi 5

## Next Steps

1. Configure Admin Interface user accounts and permissions
2. Set up TRON network connection and verify balance
3. Configure payout thresholds and schedules
4. Enable monitoring and alerting
5. Set up automated backups
6. Document operational procedures