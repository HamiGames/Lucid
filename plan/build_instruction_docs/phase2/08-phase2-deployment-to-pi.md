# Phase 2 Deployment to Pi

## Overview
Deploy Phase 2 core services to Raspberry Pi via SSH with proper dependency management and health verification.

## Location
`scripts/deployment/deploy-phase2-pi.sh`

## Deployment Strategy

### Prerequisites
- Phase 1 services running on Pi
- SSH connection to pickme@192.168.0.75
- Docker daemon running on Pi
- Required environment variables set

### Deployment Steps
1. Copy Phase 2 compose file to Pi
2. Merge with Phase 1 compose file
3. Pull arm64 images
4. Deploy with dependency awareness
5. Wait for service mesh registration
6. Verify blockchain creating blocks

## Deployment Script

### File: `scripts/deployment/deploy-phase2-pi.sh`

```bash
#!/bin/bash
# scripts/deployment/deploy-phase2-pi.sh
# Deploy Phase 2 core services to Raspberry Pi

set -e

# Configuration
PI_HOST="192.168.0.75"
PI_USER="pickme"
PI_DEPLOY_DIR="/opt/lucid/production"
COMPOSE_FILE="docker-compose.core.yml"
ENV_FILE=".env.core"

echo "Starting Phase 2 deployment to Pi..."

# Check SSH connection
echo "Checking SSH connection to Pi..."
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes ${PI_USER}@${PI_HOST} exit; then
    echo "ERROR: Cannot connect to Pi via SSH"
    exit 1
fi
echo "SSH connection successful"

# Check Phase 1 services
echo "Checking Phase 1 services..."
PHASE1_STATUS=$(ssh ${PI_USER}@${PI_HOST} "cd ${PI_DEPLOY_DIR} && docker-compose -f docker-compose.foundation.yml ps --services --filter status=running")
if [ -z "$PHASE1_STATUS" ]; then
    echo "ERROR: Phase 1 services not running"
    exit 1
fi
echo "Phase 1 services running: $PHASE1_STATUS"

# Copy Phase 2 compose file to Pi
echo "Copying Phase 2 compose file to Pi..."
scp configs/docker/${COMPOSE_FILE} ${PI_USER}@${PI_HOST}:${PI_DEPLOY_DIR}/

# Copy environment file to Pi
echo "Copying environment file to Pi..."
scp configs/environment/${ENV_FILE} ${PI_USER}@${PI_HOST}:${PI_DEPLOY_DIR}/

# Deploy Phase 2 services
echo "Deploying Phase 2 services..."
ssh ${PI_USER}@${PI_HOST} << 'EOF'
cd /opt/lucid/production

# Stop any existing Phase 2 services
echo "Stopping existing Phase 2 services..."
docker-compose -f docker-compose.foundation.yml -f docker-compose.core.yml down

# Pull Phase 2 images
echo "Pulling Phase 2 images..."
docker-compose -f docker-compose.foundation.yml -f docker-compose.core.yml pull

# Start Phase 2 services
echo "Starting Phase 2 services..."
docker-compose -f docker-compose.foundation.yml -f docker-compose.core.yml up -d

# Wait for services to start
echo "Waiting for services to start..."
sleep 30

# Check service status
echo "Checking service status..."
docker-compose -f docker-compose.foundation.yml -f docker-compose.core.yml ps
EOF

# Verify deployment
echo "Verifying Phase 2 deployment..."

# Check API Gateway
echo "Checking API Gateway..."
API_GATEWAY_STATUS=$(ssh ${PI_USER}@${PI_HOST} "curl -s http://localhost:8080/health | jq -r '.status'")
if [ "$API_GATEWAY_STATUS" != "healthy" ]; then
    echo "ERROR: API Gateway not healthy"
    exit 1
fi
echo "API Gateway healthy"

# Check Service Mesh Controller
echo "Checking Service Mesh Controller..."
SERVICE_MESH_STATUS=$(ssh ${PI_USER}@${PI_HOST} "curl -s http://localhost:8081/health | jq -r '.status'")
if [ "$SERVICE_MESH_STATUS" != "healthy" ]; then
    echo "ERROR: Service Mesh Controller not healthy"
    exit 1
fi
echo "Service Mesh Controller healthy"

# Check Blockchain Engine
echo "Checking Blockchain Engine..."
BLOCKCHAIN_STATUS=$(ssh ${PI_USER}@${PI_HOST} "curl -s http://localhost:8084/health | jq -r '.status'")
if [ "$BLOCKCHAIN_STATUS" != "healthy" ]; then
    echo "ERROR: Blockchain Engine not healthy"
    exit 1
fi
echo "Blockchain Engine healthy"

# Check Session Anchoring
echo "Checking Session Anchoring..."
ANCHORING_STATUS=$(ssh ${PI_USER}@${PI_HOST} "curl -s http://localhost:8086/health | jq -r '.status'")
if [ "$ANCHORING_STATUS" != "healthy" ]; then
    echo "ERROR: Session Anchoring not healthy"
    exit 1
fi
echo "Session Anchoring healthy"

# Check Block Manager
echo "Checking Block Manager..."
BLOCK_MANAGER_STATUS=$(ssh ${PI_USER}@${PI_HOST} "curl -s http://localhost:8088/health | jq -r '.status'")
if [ "$BLOCK_MANAGER_STATUS" != "healthy" ]; then
    echo "ERROR: Block Manager not healthy"
    exit 1
fi
echo "Block Manager healthy"

# Check Data Chain
echo "Checking Data Chain..."
DATA_CHAIN_STATUS=$(ssh ${PI_USER}@${PI_HOST} "curl -s http://localhost:8090/health | jq -r '.status'")
if [ "$DATA_CHAIN_STATUS" != "healthy" ]; then
    echo "ERROR: Data Chain not healthy"
    exit 1
fi
echo "Data Chain healthy"

# Wait for service mesh registration
echo "Waiting for service mesh registration..."
sleep 60

# Check service mesh registration
echo "Checking service mesh registration..."
SERVICES_REGISTERED=$(ssh ${PI_USER}@${PI_HOST} "curl -s http://localhost:8500/v1/agent/services | jq -r 'keys | length'")
if [ "$SERVICES_REGISTERED" -lt 6 ]; then
    echo "WARNING: Not all services registered with service mesh"
fi
echo "Services registered: $SERVICES_REGISTERED"

# Verify blockchain creating blocks
echo "Verifying blockchain creating blocks..."
sleep 30

# Check blockchain status
echo "Checking blockchain status..."
BLOCKCHAIN_INFO=$(ssh ${PI_USER}@${PI_HOST} "curl -s http://localhost:8084/api/v1/chain/info")
echo "Blockchain info: $BLOCKCHAIN_INFO"

# Check if blocks are being created
BLOCK_COUNT=$(ssh ${PI_USER}@${PI_HOST} "curl -s http://localhost:8084/api/v1/blocks | jq -r 'length'")
if [ "$BLOCK_COUNT" -eq 0 ]; then
    echo "WARNING: No blocks created yet"
else
    echo "Blocks created: $BLOCK_COUNT"
fi

# Final status check
echo "Final status check..."
ssh ${PI_USER}@${PI_HOST} << 'EOF'
cd /opt/lucid/production

echo "=== Phase 2 Service Status ==="
docker-compose -f docker-compose.foundation.yml -f docker-compose.core.yml ps

echo "=== Service Health Checks ==="
echo "API Gateway: $(curl -s http://localhost:8080/health | jq -r '.status')"
echo "Service Mesh: $(curl -s http://localhost:8081/health | jq -r '.status')"
echo "Blockchain Engine: $(curl -s http://localhost:8084/health | jq -r '.status')"
echo "Session Anchoring: $(curl -s http://localhost:8086/health | jq -r '.status')"
echo "Block Manager: $(curl -s http://localhost:8088/health | jq -r '.status')"
echo "Data Chain: $(curl -s http://localhost:8090/health | jq -r '.status')"

echo "=== Service Mesh Services ==="
curl -s http://localhost:8500/v1/agent/services | jq -r 'keys[]'

echo "=== Blockchain Status ==="
curl -s http://localhost:8084/api/v1/chain/info | jq
EOF

echo "Phase 2 deployment completed successfully!"
echo "All core services are running on Pi"
```

## Environment Configuration

### File: `configs/environment/.env.core`

```bash
# Phase 2 Core Services Configuration

# Database Configuration
MONGODB_URI=mongodb://lucid:${GENERATED_MONGODB_PASSWORD}@192.168.0.75:27017/lucid?authSource=admin&retryWrites=false
REDIS_URL=redis://:${GENERATED_REDIS_PASSWORD}@192.168.0.75:6379/0
ELASTICSEARCH_URL=http://192.168.0.75:9200

# Network Configuration
LUCID_NETWORK=lucid-pi-network
PI_HOST=192.168.0.75
PI_USER=pickme
PI_DEPLOY_DIR=/opt/lucid/production

# Service Ports
API_GATEWAY_PORT=8080
SERVICE_MESH_PORT=8081
BLOCKCHAIN_CORE_PORT=8084
SESSION_ANCHORING_PORT=8086
BLOCK_MANAGER_PORT=8088
DATA_CHAIN_PORT=8090

# Security
JWT_SECRET_KEY=${GENERATED_JWT_SECRET}
ENCRYPTION_KEY=${GENERATED_ENCRYPTION_KEY}

# API Gateway Configuration
RATE_LIMIT_FREE=100
RATE_LIMIT_PREMIUM=1000
RATE_LIMIT_ENTERPRISE=10000

# Service Mesh Configuration
CONSUL_DATACENTER=lucid-dc
CONSUL_BIND_ADDR=0.0.0.0
CONSUL_CLIENT_ADDR=0.0.0.0
CONSUL_UI_ENABLED=true
CONSUL_BOOTSTRAP_EXPECT=1

# Blockchain Configuration
BLOCK_INTERVAL=10
CONSENSUS_PARTICIPANTS=3
BLOCK_SIZE_LIMIT=1048576
TRANSACTION_LIMIT=1000

# Session Anchoring Configuration
MERKLE_TREE_DEPTH=10
ANCHORING_BATCH_SIZE=100
PROOF_GENERATION_TIMEOUT=30

# Block Manager Configuration
MAX_BLOCKS_TO_KEEP=10000
BLOCK_VALIDATION_ENABLED=true
CHAIN_MAINTENANCE_INTERVAL=60

# Data Chain Configuration
INDEXING_BATCH_SIZE=1000
QUERY_CACHE_SIZE=10000
DATA_SYNC_INTERVAL=30
```

## Deployment Validation

### Health Check Endpoints
- **API Gateway**: http://192.168.0.75:8080/health
- **Service Mesh Controller**: http://192.168.0.75:8081/health
- **Blockchain Engine**: http://192.168.0.75:8084/health
- **Session Anchoring**: http://192.168.0.75:8086/health
- **Block Manager**: http://192.168.0.75:8088/health
- **Data Chain**: http://192.168.0.75:8090/health

### Service Mesh Verification
- **Consul UI**: http://192.168.0.75:8500
- **Service Registry**: http://192.168.0.75:8500/v1/agent/services

### Blockchain Verification
- **Chain Info**: http://192.168.0.75:8084/api/v1/chain/info
- **Blocks**: http://192.168.0.75:8084/api/v1/blocks
- **Transactions**: http://192.168.0.75:8084/api/v1/transactions

## Troubleshooting

### Deployment Issues
```bash
# Check deployment logs
ssh pickme@192.168.0.75 "cd /opt/lucid/production && docker-compose -f docker-compose.foundation.yml -f docker-compose.core.yml logs"

# Check service status
ssh pickme@192.168.0.75 "cd /opt/lucid/production && docker-compose -f docker-compose.foundation.yml -f docker-compose.core.yml ps"

# Restart services
ssh pickme@192.168.0.75 "cd /opt/lucid/production && docker-compose -f docker-compose.foundation.yml -f docker-compose.core.yml restart"
```

### Service Issues
```bash
# Check individual service logs
ssh pickme@192.168.0.75 "docker logs lucid-api-gateway"
ssh pickme@192.168.0.75 "docker logs lucid-service-mesh-controller"
ssh pickme@192.168.0.75 "docker logs lucid-blockchain-engine"

# Check service health
ssh pickme@192.168.0.75 "curl http://localhost:8080/health"
ssh pickme@192.168.0.75 "curl http://localhost:8081/health"
ssh pickme@192.168.0.75 "curl http://localhost:8084/health"
```

### Network Issues
```bash
# Check network configuration
ssh pickme@192.168.0.75 "docker network ls"
ssh pickme@192.168.0.75 "docker network inspect lucid-pi-network"

# Check service connectivity
ssh pickme@192.168.0.75 "docker exec lucid-api-gateway ping lucid-auth-service"
ssh pickme@192.168.0.75 "docker exec lucid-blockchain-engine ping lucid-mongodb"
```

### Service Mesh Issues
```bash
# Check Consul status
ssh pickme@192.168.0.75 "curl http://localhost:8500/v1/status/leader"

# Check registered services
ssh pickme@192.168.0.75 "curl http://localhost:8500/v1/agent/services"

# Restart Consul
ssh pickme@192.168.0.75 "docker restart lucid-service-mesh-controller"
```

### Blockchain Issues
```bash
# Check blockchain status
ssh pickme@192.168.0.75 "curl http://localhost:8084/api/v1/chain/info"

# Check block creation
ssh pickme@192.168.0.75 "curl http://localhost:8084/api/v1/blocks"

# Check consensus status
ssh pickme@192.168.0.75 "curl http://localhost:8084/api/v1/consensus/status"
```

## Rollback Procedure

### Rollback Script
```bash
#!/bin/bash
# scripts/deployment/rollback-phase2-pi.sh
# Rollback Phase 2 deployment

set -e

PI_HOST="192.168.0.75"
PI_USER="pickme"
PI_DEPLOY_DIR="/opt/lucid/production"

echo "Rolling back Phase 2 deployment..."

# Stop Phase 2 services
echo "Stopping Phase 2 services..."
ssh ${PI_USER}@${PI_HOST} << 'EOF'
cd /opt/lucid/production
docker-compose -f docker-compose.foundation.yml -f docker-compose.core.yml down
EOF

# Verify rollback
echo "Verifying rollback..."
ssh ${PI_USER}@${PI_HOST} << 'EOF'
cd /opt/lucid/production
docker-compose -f docker-compose.foundation.yml ps
EOF

echo "Phase 2 rollback completed successfully!"
```

## Success Criteria
- All Phase 2 services running and healthy
- Service mesh registration complete
- Blockchain creating blocks
- API Gateway routing traffic
- All health checks passing
- No critical errors in logs

## Next Steps
After successful Phase 2 deployment, proceed to Phase 2 integration testing.
