# Phase 1 Deployment to Pi

## Overview
Deploy Phase 1 foundation services to Raspberry Pi via SSH, including database initialization and health verification.

## Location
`scripts/deployment/deploy-phase1-pi.sh`

## Deployment Actions

### 1. Copy Phase 1 Compose File to Pi
```bash
# Copy Docker Compose file to Pi
scp configs/docker/docker-compose.foundation.yml pickme@192.168.0.75:/opt/lucid/production/

# Copy environment file to Pi
scp configs/environment/.env.foundation pickme@192.168.0.75:/opt/lucid/production/
```

### 2. Create Required Directories on Pi
```bash
# Create data directories
ssh pickme@192.168.0.75 "sudo mkdir -p /opt/lucid/data/{mongodb,redis,elasticsearch}"
ssh pickme@192.168.0.75 "sudo mkdir -p /opt/lucid/config/{mongodb,redis,elasticsearch}"
ssh pickme@192.168.0.75 "sudo mkdir -p /opt/lucid/logs/auth"

# Set proper permissions
ssh pickme@192.168.0.75 "sudo chown -R 999:999 /opt/lucid/data/mongodb"
ssh pickme@192.168.0.75 "sudo chown -R 999:999 /opt/lucid/data/redis"
ssh pickme@192.168.0.75 "sudo chown -R 1000:1000 /opt/lucid/data/elasticsearch"
ssh pickme@192.168.0.75 "sudo chown -R 999:999 /opt/lucid/config/mongodb"
ssh pickme@192.168.0.75 "sudo chown -R 999:999 /opt/lucid/config/redis"
ssh pickme@192.168.0.75 "sudo chown -R 1000:1000 /opt/lucid/config/elasticsearch"
ssh pickme@192.168.0.75 "sudo chown -R 65532:65532 /opt/lucid/logs/auth"
```

### 3. Pull ARM64 Images on Pi
```bash
# Pull all Phase 1 images
ssh pickme@192.168.0.75 "cd /opt/lucid/production && docker-compose -f docker-compose.foundation.yml pull"
```

### 4. Deploy Services with Dependency Awareness
```bash
# Deploy Phase 1 services
ssh pickme@192.168.0.75 "cd /opt/lucid/production && docker-compose -f docker-compose.foundation.yml up -d"
```

### 5. Wait for Health Checks
```bash
# Wait for all services to be healthy (90 seconds)
ssh pickme@192.168.0.75 "cd /opt/lucid/production && docker-compose -f docker-compose.foundation.yml ps"
```

### 6. Initialize Databases
```bash
# Initialize MongoDB with required collections and indexes
ssh pickme@192.168.0.75 "docker exec lucid-mongodb mongosh --eval \"
  use lucid;
  db.createCollection('users');
  db.createCollection('sessions');
  db.createCollection('blocks');
  db.createCollection('transactions');
  db.users.createIndex({username: 1}, {unique: true});
  db.users.createIndex({email: 1}, {unique: true});
  db.sessions.createIndex({session_id: 1}, {unique: true});
  db.sessions.createIndex({user_id: 1});
  db.sessions.createIndex({created_at: 1});
  db.blocks.createIndex({height: 1}, {unique: true});
  db.blocks.createIndex({hash: 1}, {unique: true});
  db.blocks.createIndex({timestamp: 1});
  db.transactions.createIndex({tx_id: 1}, {unique: true});
  db.transactions.createIndex({block_height: 1});
  db.transactions.createIndex({timestamp: 1});
\""

# Initialize Redis with required keys
ssh pickme@192.168.0.75 "docker exec lucid-redis redis-cli SET 'lucid:system:status' 'initialized'"
ssh pickme@192.168.0.75 "docker exec lucid-redis redis-cli SET 'lucid:system:version' '1.0.0'"

# Initialize Elasticsearch with required indices
ssh pickme@192.168.0.75 "docker exec lucid-elasticsearch curl -X PUT 'localhost:9200/lucid-sessions' -H 'Content-Type: application/json' -d '{
  \"mappings\": {
    \"properties\": {
      \"session_id\": {\"type\": \"keyword\"},
      \"user_id\": {\"type\": \"keyword\"},
      \"created_at\": {\"type\": \"date\"},
      \"status\": {\"type\": \"keyword\"},
      \"metadata\": {\"type\": \"object\"}
    }
  }
}'"
```

### 7. Verify All Services Running
```bash
# Check service status
ssh pickme@192.168.0.75 "cd /opt/lucid/production && docker-compose -f docker-compose.foundation.yml ps"

# Check service health
ssh pickme@192.168.0.75 "docker exec lucid-mongodb mongosh --eval 'db.adminCommand(\"ping\")'"
ssh pickme@192.168.0.75 "docker exec lucid-redis redis-cli ping"
ssh pickme@192.168.0.75 "docker exec lucid-elasticsearch curl -f http://localhost:9200/_cluster/health"
ssh pickme@192.168.0.75 "curl -f http://localhost:8089/health"
```

## Deployment Script Implementation

**File**: `scripts/deployment/deploy-phase1-pi.sh`

```bash
#!/bin/bash
# scripts/deployment/deploy-phase1-pi.sh
# Deploy Phase 1 foundation services to Raspberry Pi

set -e

echo "Starting Phase 1 deployment to Pi..."

# Configuration
PI_HOST="192.168.0.75"
PI_USER="pickme"
PI_DEPLOY_DIR="/opt/lucid/production"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

# Function to wait for service health
wait_for_service() {
    local service_name=$1
    local max_attempts=30
    local attempt=1
    
    echo "Waiting for $service_name to be healthy..."
    
    while [ $attempt -le $max_attempts ]; do
        if ssh $PI_USER@$PI_HOST "docker exec $service_name healthcheck" &> /dev/null; then
            print_status 0 "$service_name is healthy"
            return 0
        fi
        
        echo "Attempt $attempt/$max_attempts: $service_name not ready yet..."
        sleep 3
        attempt=$((attempt + 1))
    done
    
    print_status 1 "$service_name failed to become healthy"
    return 1
}

echo "=== Phase 1 Deployment to Pi ==="

# Step 1: Copy files to Pi
echo "Copying Phase 1 files to Pi..."
scp configs/docker/docker-compose.foundation.yml $PI_USER@$PI_HOST:$PI_DEPLOY_DIR/
scp configs/environment/.env.foundation $PI_USER@$PI_HOST:$PI_DEPLOY_DIR/

if [ $? -eq 0 ]; then
    print_status 0 "Files copied to Pi"
else
    print_status 1 "Failed to copy files to Pi"
    exit 1
fi

# Step 2: Create required directories
echo "Creating required directories on Pi..."
ssh $PI_USER@$PI_HOST "sudo mkdir -p /opt/lucid/data/{mongodb,redis,elasticsearch}"
ssh $PI_USER@$PI_HOST "sudo mkdir -p /opt/lucid/config/{mongodb,redis,elasticsearch}"
ssh $PI_USER@$PI_HOST "sudo mkdir -p /opt/lucid/logs/auth"

# Set proper permissions
ssh $PI_USER@$PI_HOST "sudo chown -R 999:999 /opt/lucid/data/mongodb"
ssh $PI_USER@$PI_HOST "sudo chown -R 999:999 /opt/lucid/data/redis"
ssh $PI_USER@$PI_HOST "sudo chown -R 1000:1000 /opt/lucid/data/elasticsearch"
ssh $PI_USER@$PI_HOST "sudo chown -R 999:999 /opt/lucid/config/mongodb"
ssh $PI_USER@$PI_HOST "sudo chown -R 999:999 /opt/lucid/config/redis"
ssh $PI_USER@$PI_HOST "sudo chown -R 1000:1000 /opt/lucid/config/elasticsearch"
ssh $PI_USER@$PI_HOST "sudo chown -R 65532:65532 /opt/lucid/logs/auth"

if [ $? -eq 0 ]; then
    print_status 0 "Directories created and permissions set"
else
    print_status 1 "Failed to create directories"
    exit 1
fi

# Step 3: Pull ARM64 images
echo "Pulling ARM64 images on Pi..."
ssh $PI_USER@$PI_HOST "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.foundation.yml pull"

if [ $? -eq 0 ]; then
    print_status 0 "Images pulled successfully"
else
    print_status 1 "Failed to pull images"
    exit 1
fi

# Step 4: Deploy services
echo "Deploying Phase 1 services..."
ssh $PI_USER@$PI_HOST "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.foundation.yml up -d"

if [ $? -eq 0 ]; then
    print_status 0 "Services deployed successfully"
else
    print_status 1 "Failed to deploy services"
    exit 1
fi

# Step 5: Wait for health checks
echo "Waiting for services to become healthy..."
sleep 30

# Check MongoDB health
wait_for_service "lucid-mongodb"
if [ $? -ne 0 ]; then
    echo "MongoDB health check failed"
    exit 1
fi

# Check Redis health
wait_for_service "lucid-redis"
if [ $? -ne 0 ]; then
    echo "Redis health check failed"
    exit 1
fi

# Check Elasticsearch health
wait_for_service "lucid-elasticsearch"
if [ $? -ne 0 ]; then
    echo "Elasticsearch health check failed"
    exit 1
fi

# Check Authentication Service health
wait_for_service "lucid-auth-service"
if [ $? -ne 0 ]; then
    echo "Authentication Service health check failed"
    exit 1
fi

# Step 6: Initialize databases
echo "Initializing databases..."

# Initialize MongoDB
echo "Initializing MongoDB..."
ssh $PI_USER@$PI_HOST "docker exec lucid-mongodb mongosh --eval \"
  use lucid;
  db.createCollection('users');
  db.createCollection('sessions');
  db.createCollection('blocks');
  db.createCollection('transactions');
  db.users.createIndex({username: 1}, {unique: true});
  db.users.createIndex({email: 1}, {unique: true});
  db.sessions.createIndex({session_id: 1}, {unique: true});
  db.sessions.createIndex({user_id: 1});
  db.sessions.createIndex({created_at: 1});
  db.blocks.createIndex({height: 1}, {unique: true});
  db.blocks.createIndex({hash: 1}, {unique: true});
  db.blocks.createIndex({timestamp: 1});
  db.transactions.createIndex({tx_id: 1}, {unique: true});
  db.transactions.createIndex({block_height: 1});
  db.transactions.createIndex({timestamp: 1});
\""

if [ $? -eq 0 ]; then
    print_status 0 "MongoDB initialized successfully"
else
    print_status 1 "MongoDB initialization failed"
    exit 1
fi

# Initialize Redis
echo "Initializing Redis..."
ssh $PI_USER@$PI_HOST "docker exec lucid-redis redis-cli SET 'lucid:system:status' 'initialized'"
ssh $PI_USER@$PI_HOST "docker exec lucid-redis redis-cli SET 'lucid:system:version' '1.0.0'"

if [ $? -eq 0 ]; then
    print_status 0 "Redis initialized successfully"
else
    print_status 1 "Redis initialization failed"
    exit 1
fi

# Initialize Elasticsearch
echo "Initializing Elasticsearch..."
ssh $PI_USER@$PI_HOST "docker exec lucid-elasticsearch curl -X PUT 'localhost:9200/lucid-sessions' -H 'Content-Type: application/json' -d '{
  \"mappings\": {
    \"properties\": {
      \"session_id\": {\"type\": \"keyword\"},
      \"user_id\": {\"type\": \"keyword\"},
      \"created_at\": {\"type\": \"date\"},
      \"status\": {\"type\": \"keyword\"},
      \"metadata\": {\"type\": \"object\"}
    }
  }
}'"

if [ $? -eq 0 ]; then
    print_status 0 "Elasticsearch initialized successfully"
else
    print_status 1 "Elasticsearch initialization failed"
    exit 1
fi

# Step 7: Final verification
echo "Performing final verification..."

# Check service status
echo "Checking service status..."
ssh $PI_USER@$PI_HOST "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.foundation.yml ps"

# Test service connectivity
echo "Testing service connectivity..."
ssh $PI_USER@$PI_HOST "docker exec lucid-mongodb mongosh --eval 'db.adminCommand(\"ping\")'"
ssh $PI_USER@$PI_HOST "docker exec lucid-redis redis-cli ping"
ssh $PI_USER@$PI_HOST "docker exec lucid-elasticsearch curl -f http://localhost:9200/_cluster/health"
ssh $PI_USER@$PI_HOST "curl -f http://localhost:8089/health"

if [ $? -eq 0 ]; then
    print_status 0 "All services are running and healthy"
else
    print_status 1 "Service verification failed"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Phase 1 deployment completed successfully!${NC}"
echo "Services deployed:"
echo "- MongoDB (port 27017)"
echo "- Redis (port 6379)"
echo "- Elasticsearch (port 9200)"
echo "- Authentication Service (port 8089)"
echo ""
echo "All databases initialized and services are healthy."
```

## Validation Criteria
- All Phase 1 services healthy on Pi
- Databases initialized with required schemas and indexes
- Service connectivity verified
- Health checks passing
- Proper file permissions set
- All services running in Docker containers

## Troubleshooting

### SSH Connection Issues
```bash
# Test SSH connection
ssh pickme@192.168.0.75 "echo 'SSH connection successful'"

# Check SSH key authentication
ssh-add -l
```

### Service Health Issues
```bash
# Check service logs
ssh pickme@192.168.0.75 "docker logs lucid-mongodb"
ssh pickme@192.168.0.75 "docker logs lucid-redis"
ssh pickme@192.168.0.75 "docker logs lucid-elasticsearch"
ssh pickme@192.168.0.75 "docker logs lucid-auth-service"
```

### Database Initialization Issues
```bash
# Check MongoDB status
ssh pickme@192.168.0.75 "docker exec lucid-mongodb mongosh --eval 'db.adminCommand(\"ping\")'"

# Check Redis status
ssh pickme@192.168.0.75 "docker exec lucid-redis redis-cli ping"

# Check Elasticsearch status
ssh pickme@192.168.0.75 "docker exec lucid-elasticsearch curl -f http://localhost:9200/_cluster/health"
```

### Permission Issues
```bash
# Check directory permissions
ssh pickme@192.168.0.75 "ls -la /opt/lucid/data/"
ssh pickme@192.168.0.75 "ls -la /opt/lucid/config/"
ssh pickme@192.168.0.75 "ls -la /opt/lucid/logs/"
```

## Security Considerations
- All services run as non-root users
- Proper file permissions set
- Database authentication enabled
- Network isolation configured
- Health checks configured

## Performance Considerations
- Resource limits set for Pi hardware
- Memory limits appropriate for services
- CPU limits configured
- Disk space monitored

## Next Steps
After successful Phase 1 deployment, proceed to Phase 1 integration testing.
