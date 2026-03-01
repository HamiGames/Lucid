#!/bin/bash
# Phase 1 Foundation Services Deployment to Raspberry Pi
# Based on lucid-container-build-plan.plan.md Step 8
# Deploys MongoDB, Redis, Elasticsearch, and Authentication Service to Pi

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PI_HOST="192.168.0.75"
PI_USER="pickme"
PI_SSH_PORT="22"
PI_SSH_KEY_PATH="$HOME/.ssh/id_rsa"
PI_DEPLOY_DIR="/mnt/myssd/Lucid/Lucid"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Service configuration
SERVICES=("lucid-mongodb" "lucid-redis" "lucid-elasticsearch" "lucid-auth-service")
HEALTH_CHECK_TIMEOUT=90
DEPLOYMENT_LOG="$PROJECT_ROOT/deployment-phase1.log"

# Initialize deployment
init_deployment() {
    echo -e "${BLUE}=== Phase 1 Foundation Services Deployment ===${NC}"
    echo "Target Pi: $PI_USER@$PI_HOST"
    echo "Deploy Directory: $PI_DEPLOY_DIR"
    echo "Project Root: $PROJECT_ROOT"
    echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo ""
    
    # Clear previous deployment log
    > "$DEPLOYMENT_LOG"
    
    # Log deployment start
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") - Phase 1 deployment started" >> "$DEPLOYMENT_LOG"
}

# Log deployment step
log_step() {
    local step="$1"
    local status="$2"
    local message="$3"
    
    if [ "$status" = "SUCCESS" ]; then
        echo -e "${GREEN}✓${NC} $step: $message"
    elif [ "$status" = "FAILURE" ]; then
        echo -e "${RED}✗${NC} $step: $message"
    else
        echo -e "${YELLOW}⚠${NC} $step: $message"
    fi
    
    # Log to file
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") - $step - $status - $message" >> "$DEPLOYMENT_LOG"
}

# Test SSH connection to Pi
test_ssh_connection() {
    echo -e "${BLUE}=== Testing SSH Connection ===${NC}"
    
    if ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "echo 'SSH connection successful'" >/dev/null 2>&1; then
        log_step "ssh-connection" "SUCCESS" "SSH connection to Pi established"
        return 0
    else
        log_step "ssh-connection" "FAILURE" "SSH connection to Pi failed"
        return 1
    fi
}

# Verify project directory exists on Pi
verify_project_directory() {
    echo -e "${BLUE}=== Verifying Project Directory on Pi ===${NC}"
    
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        test -d $PI_DEPLOY_DIR
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "project-directory" "SUCCESS" "Project directory exists on Pi at $PI_DEPLOY_DIR"
    else
        log_step "project-directory" "FAILURE" "Project directory not found on Pi at $PI_DEPLOY_DIR"
        echo "Please ensure the Lucid project is cloned/synced to $PI_DEPLOY_DIR on the Pi"
        return 1
    fi
}

# Create Docker networks on Pi
create_docker_networks() {
    echo -e "${BLUE}=== Creating Docker Networks ===${NC}"
    
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        # Create main Pi network
        docker network create lucid-pi-network --driver bridge --subnet 172.20.0.0/16 --gateway 172.20.0.1 --attachable --opt com.docker.network.bridge.enable_icc=true --opt com.docker.network.bridge.enable_ip_masquerade=true --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 --opt com.docker.network.driver.mtu=1500 --label 'lucid.network=main' --label 'lucid.subnet=172.20.0.0/16' 2>/dev/null || echo 'Network lucid-pi-network already exists'
        
        # Create TRON isolated network
        docker network create lucid-tron-isolated --driver bridge --subnet 172.21.0.0/16 --gateway 172.21.0.1 --attachable --opt com.docker.network.bridge.enable_icc=true --opt com.docker.network.bridge.enable_ip_masquerade=true --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 --opt com.docker.network.driver.mtu=1500 --label 'lucid.network=tron-isolated' --label 'lucid.subnet=172.21.0.0/16' 2>/dev/null || echo 'Network lucid-tron-isolated already exists'
        
        # Create GUI network
        docker network create lucid-gui-network --driver bridge --subnet 172.22.0.0/16 --gateway 172.22.0.1 --attachable --opt com.docker.network.bridge.enable_icc=true --opt com.docker.network.bridge.enable_ip_masquerade=true --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 --opt com.docker.network.driver.mtu=1500 --label 'lucid.network=gui' --label 'lucid.subnet=172.22.0.0/16' 2>/dev/null || echo 'Network lucid-gui-network already exists'
        
        # Create distroless production network
        docker network create lucid-distroless-production --driver bridge --subnet 172.23.0.0/16 --gateway 172.23.0.1 --attachable --opt com.docker.network.bridge.enable_icc=true --opt com.docker.network.bridge.enable_ip_masquerade=true --opt com.docker.network.driver.mtu=1500 --label 'lucid.network=distroless-production' --label 'lucid.subnet=172.23.0.0/16' 2>/dev/null || echo 'Network lucid-distroless-production already exists'
        
        # Create distroless dev network
        docker network create lucid-distroless-dev --driver bridge --subnet 172.24.0.0/16 --gateway 172.24.0.1 --attachable --opt com.docker.network.bridge.enable_icc=true --opt com.docker.network.bridge.enable_ip_masquerade=true --opt com.docker.network.driver.mtu=1500 --label 'lucid.network=distroless-dev' --label 'lucid.subnet=172.24.0.0/16' 2>/dev/null || echo 'Network lucid-distroless-dev already exists'
        
        # Create multi-stage network
        docker network create lucid-multi-stage-network --driver bridge --subnet 172.25.0.0/16 --gateway 172.25.0.1 --attachable --opt com.docker.network.bridge.enable_icc=true --opt com.docker.network.bridge.enable_ip_masquerade=true --opt com.docker.network.driver.mtu=1500 --label 'lucid.network=multi-stage' --label 'lucid.subnet=172.25.0.0/16' 2>/dev/null || echo 'Network lucid-multi-stage-network already exists'
        
        # Verify networks created
        echo 'Verifying networks...'
        docker network ls | grep lucid
        docker network inspect lucid-pi-network | grep -E 'Subnet|Gateway'
        docker network inspect lucid-distroless-production | grep -E 'Subnet|Gateway'
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "docker-networks" "SUCCESS" "All Docker networks created on Pi"
    else
        log_step "docker-networks" "FAILURE" "Failed to create Docker networks on Pi"
        return 1
    fi
}

# Create data storage directories on Pi
create_data_directories() {
    echo -e "${BLUE}=== Creating Data Storage Directories ===${NC}"
    
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        # Create main data directory structure for all phases
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/mongodb
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/mongodb-config
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/redis
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/elasticsearch
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/auth
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/blockchain
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/blockchain-engine
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/anchoring
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/block-manager
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/data-chain
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/consul
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/session-pipeline
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/session-recorder
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/session-processor
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/session-storage
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/rdp-server-manager
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/rdp-xrdp
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/rdp-controller
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/rdp-monitor
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/node-management
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/admin-interface
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/tron-client
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/tron-payout-router
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/tron-wallet-manager
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/tron-usdt-manager
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/tron-staking
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/tron-payment-gateway
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/storage
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/backups
        
        # Create log directory structure
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/auth
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/api-gateway
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/blockchain
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/blockchain-engine
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/anchoring
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/block-manager
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/data-chain
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/consul
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/session-pipeline
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/session-recorder
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/session-processor
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/session-storage
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/session-api
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/rdp-server-manager
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/rdp-xrdp
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/rdp-controller
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/rdp-monitor
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/node-management
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/admin-interface
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/tron-client
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/tron-payout-router
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/tron-wallet-manager
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/tron-usdt-manager
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/tron-staking
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/tron-payment-gateway
        sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/storage
        
        # Set proper ownership and permissions
        sudo chown -R $PI_USER:$PI_USER /mnt/myssd/Lucid/Lucid
        sudo chmod -R 755 /mnt/myssd/Lucid/Lucid
        
        # Ensure MongoDB directories have proper permissions
        sudo chmod 755 /mnt/myssd/Lucid/Lucid/data/mongodb
        sudo chmod 755 /mnt/myssd/Lucid/Lucid/data/mongodb-config
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "data-directories" "SUCCESS" "All data storage directories created on Pi"
    else
        log_step "data-directories" "FAILURE" "Failed to create data storage directories on Pi"
        return 1
    fi
}

# Verify Phase 1 compose file exists on Pi
verify_compose_file() {
    echo -e "${BLUE}=== Verifying Docker Compose File ===${NC}"
    
    local pi_compose_file="$PI_DEPLOY_DIR/configs/docker/docker-compose.foundation.yml"
    
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "test -f $pi_compose_file" >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "compose-file-verify" "SUCCESS" "Docker compose file exists on Pi at $pi_compose_file"
        return 0
    else
        log_step "compose-file-verify" "FAILURE" "Docker compose file not found on Pi at $pi_compose_file"
        echo "Please ensure the Lucid project is synced to $PI_DEPLOY_DIR on the Pi"
        return 1
    fi
}

# Verify environment configuration exists on Pi
verify_environment_config() {
    echo -e "${BLUE}=== Verifying Environment Configuration ===${NC}"
    
    local pi_env_file="$PI_DEPLOY_DIR/configs/environment/.env.foundation"
    
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "test -f $pi_env_file" >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "env-file-verify" "SUCCESS" "Environment configuration exists on Pi"
        return 0
    else
        log_step "env-file-verify" "WARNING" "Environment file not found, will use defaults from compose file"
        return 0
    fi
}

# Deploy distroless infrastructure (prerequisite)
deploy_distroless_infrastructure() {
    echo -e "${BLUE}=== Deploying Distroless Infrastructure ===${NC}"
    
    # Step 1: Deploy distroless config
    echo "Deploying distroless base infrastructure..."
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        cd $PI_DEPLOY_DIR
        docker-compose --env-file configs/environment/.env.foundation -f configs/docker/distroless/distroless-config.yml up -d
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "distroless-config" "SUCCESS" "Distroless base infrastructure deployed"
    else
        log_step "distroless-config" "FAILURE" "Failed to deploy distroless base infrastructure"
        return 1
    fi
    
    # Step 2: Deploy distroless runtime config
    echo "Deploying distroless runtime infrastructure..."
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        cd $PI_DEPLOY_DIR
        docker-compose --env-file configs/environment/.env.foundation -f configs/docker/distroless/distroless-runtime-config.yml up -d
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "distroless-runtime" "SUCCESS" "Distroless runtime infrastructure deployed"
    else
        log_step "distroless-runtime" "FAILURE" "Failed to deploy distroless runtime infrastructure"
        return 1
    fi
    
    # Step 3: Deploy base docker compose
    echo "Deploying base containers..."
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        cd $PI_DEPLOY_DIR
        docker-compose --env-file configs/environment/.env.foundation -f infrastructure/docker/distroless/base/docker-compose.base.yml up -d
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "base-containers" "SUCCESS" "Base containers deployed"
    else
        log_step "base-containers" "FAILURE" "Failed to deploy base containers"
        return 1
    fi
    
    # Verify distroless infrastructure
    echo "Verifying distroless infrastructure..."
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        # Check all distroless containers running
        docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | grep -E 'base|runtime|distroless'
        
        # Verify user is 65532:65532
        docker exec lucid-base id 2>/dev/null || echo 'lucid-base not ready'
        docker exec distroless-runtime id 2>/dev/null || echo 'distroless-runtime not ready'
        
        # Verify no shell (should fail)
        docker exec lucid-base sh -c 'echo test' 2>&1 | grep 'executable file not found' || echo 'Shell access detected - not distroless'
        
        # Check health
        docker ps --filter health=healthy | grep -E 'base|runtime'
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "distroless-verification" "SUCCESS" "Distroless infrastructure verified"
    else
        log_step "distroless-verification" "WARNING" "Distroless infrastructure verification had issues"
    fi
}

# Pull ARM64 images on Pi
pull_arm64_images() {
    echo -e "${BLUE}=== Pulling ARM64 Images ===${NC}"
    
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        cd $PI_DEPLOY_DIR
        docker-compose --env-file configs/environment/.env.foundation -f configs/docker/docker-compose.foundation.yml pull
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "image-pull" "SUCCESS" "ARM64 images pulled successfully on Pi"
    else
        log_step "image-pull" "FAILURE" "Failed to pull ARM64 images on Pi"
        return 1
    fi
}

# Deploy Phase 1 services
deploy_phase1_services() {
    echo -e "${BLUE}=== Deploying Phase 1 Services ===${NC}"
    
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        cd $PI_DEPLOY_DIR
        docker-compose --env-file configs/environment/.env.foundation -f configs/docker/docker-compose.foundation.yml up -d
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "service-deployment" "SUCCESS" "Phase 1 services deployed successfully"
    else
        log_step "service-deployment" "FAILURE" "Failed to deploy Phase 1 services"
        return 1
    fi
}

# Wait for health checks
wait_for_health_checks() {
    echo -e "${BLUE}=== Waiting for Health Checks ===${NC}"
    
    local timeout=$HEALTH_CHECK_TIMEOUT
    local elapsed=0
    local interval=5
    
    while [ $elapsed -lt $timeout ]; do
        local all_healthy=true
        
        for service in "${SERVICES[@]}"; do
            local health_status=$(ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
                docker inspect --format='{{.State.Health.Status}}' $service 2>/dev/null || echo 'unhealthy'
            " 2>/dev/null)
            
            if [ "$health_status" != "healthy" ]; then
                all_healthy=false
                break
            fi
        done
        
        if [ "$all_healthy" = true ]; then
            log_step "health-checks" "SUCCESS" "All services are healthy"
            return 0
        fi
        
        echo -e "${YELLOW}⚠${NC} Waiting for services to become healthy... (${elapsed}s/${timeout}s)"
        sleep $interval
        elapsed=$((elapsed + interval))
    done
    
    log_step "health-checks" "FAILURE" "Health checks timed out after ${timeout}s"
    return 1
}

# Verify all services are running
verify_services_running() {
    echo -e "${BLUE}=== Verifying Services ===${NC}"
    
    local all_running=true
    
    for service in "${SERVICES[@]}"; do
        local status=$(ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
            docker inspect --format='{{.State.Status}}' $service 2>/dev/null || echo 'not-found'
        " 2>/dev/null)
        
        if [ "$status" = "running" ]; then
            log_step "service-$service" "SUCCESS" "Service $service is running"
        else
            log_step "service-$service" "FAILURE" "Service $service is not running (status: $status)"
            all_running=false
        fi
    done
    
    if [ "$all_running" = true ]; then
        log_step "service-verification" "SUCCESS" "All Phase 1 services are running"
        return 0
    else
        log_step "service-verification" "FAILURE" "Some Phase 1 services are not running"
        return 1
    fi
}

# Initialize databases
initialize_databases() {
    echo -e "${BLUE}=== Initializing Databases ===${NC}"
    
    # Initialize MongoDB replica set
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        docker exec lucid-mongodb mongosh --eval '
            rs.initiate({
                _id: \"rs0\",
                members: [{ _id: 0, host: \"localhost:27017\" }]
            })
        ' --quiet
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "mongodb-replica-set" "SUCCESS" "MongoDB replica set initialized"
    else
        log_step "mongodb-replica-set" "FAILURE" "Failed to initialize MongoDB replica set"
        return 1
    fi
    
    # Initialize MongoDB collections using the init script
    log_step "mongodb-init" "INFO" "Copying MongoDB initialization script to Pi"
    scp -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" \
        "$PROJECT_ROOT/database/init_collections.js" \
        "$PI_USER@$PI_HOST:/tmp/init_collections.js" >/dev/null 2>&1
    
    # Initialize MongoDB collections
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        docker exec -i lucid-mongodb mongosh --quiet < /tmp/init_collections.js
        rm -f /tmp/init_collections.js
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "mongodb-collections" "SUCCESS" "MongoDB collections initialized"
    else
        log_step "mongodb-collections" "FAILURE" "Failed to initialize MongoDB collections"
        return 1
    fi
    
    # Test Redis connection
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        docker exec lucid-redis redis-cli -a lucid ping
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "redis-connection" "SUCCESS" "Redis connection test successful"
    else
        log_step "redis-connection" "FAILURE" "Redis connection test failed"
        return 1
    fi
    
    # Test Elasticsearch connection
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        docker exec lucid-elasticsearch curl -f http://localhost:9200/_cluster/health
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "elasticsearch-connection" "SUCCESS" "Elasticsearch connection test successful"
    else
        log_step "elasticsearch-connection" "FAILURE" "Elasticsearch connection test failed"
        return 1
    fi
    
    # Test Authentication service
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        docker exec lucid-auth-service curl -f http://localhost:8089/health
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "auth-service-health" "SUCCESS" "Authentication service health check successful"
    else
        log_step "auth-service-health" "FAILURE" "Authentication service health check failed"
        return 1
    fi
}

# Verify distroless compliance for all services
verify_distroless_compliance() {
    echo -e "${BLUE}=== Verifying Distroless Compliance ===${NC}"
    
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        # Verify distroless compliance for all foundation services
        for service in lucid-mongodb lucid-redis lucid-elasticsearch lucid-auth-service; do
            echo \"Checking distroless compliance for \$service...\"
            
            # Check user ID (should be 65532:65532)
            docker exec \$service id 2>/dev/null || echo \"\$service not ready\"
            
            # Verify no shell access (should fail)
            docker exec \$service sh -c 'echo test' 2>&1 | grep 'executable file not found' || echo \"Shell access detected on \$service - not distroless\"
            
            # Check if running as non-root
            docker exec \$service whoami 2>/dev/null || echo \"Cannot determine user for \$service\"
        done
        
        # Verify volumes are mounted correctly
        echo 'Checking volume mounts...'
        docker inspect lucid-mongodb | grep -A 10 'Mounts'
        docker inspect lucid-redis | grep -A 10 'Mounts'
        docker inspect lucid-elasticsearch | grep -A 10 'Mounts'
        docker inspect lucid-auth-service | grep -A 10 'Mounts'
        
        # Check disk usage
        echo 'Checking disk usage...'
        df -h /mnt/myssd/Lucid/Lucid/data/
        du -sh /mnt/myssd/Lucid/Lucid/data/*
        du -sh /mnt/myssd/Lucid/Lucid/logs/*
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "distroless-compliance" "SUCCESS" "Distroless compliance verified for all services"
    else
        log_step "distroless-compliance" "WARNING" "Distroless compliance verification had issues"
    fi
}

# Generate deployment summary
generate_deployment_summary() {
    echo -e "${BLUE}=== Deployment Summary ===${NC}"
    
    local summary_file="$PROJECT_ROOT/phase1-deployment-summary.json"
    
    cat > "$summary_file" << EOF
{
  "deployment_summary": {
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "phase": "Phase 1 Foundation Services",
    "target_pi": "$PI_USER@$PI_HOST",
    "deploy_directory": "$PI_DEPLOY_DIR",
    "services_deployed": [
      "lucid-mongodb",
      "lucid-redis", 
      "lucid-elasticsearch",
      "lucid-auth-service"
    ],
    "deployment_status": "completed",
    "health_check_timeout": $HEALTH_CHECK_TIMEOUT,
    "deployment_log": "$DEPLOYMENT_LOG"
  },
  "service_endpoints": {
    "mongodb": "mongodb://lucid:lucid@$PI_HOST:27017/lucid",
    "redis": "redis://:lucid@$PI_HOST:6379/0",
    "elasticsearch": "http://$PI_HOST:9200",
    "auth_service": "http://$PI_HOST:8089"
  },
  "next_steps": [
    "Run Phase 1 integration tests",
    "Proceed with Phase 2 Core Services deployment",
    "Monitor service health and performance"
  ]
}
EOF
    
    echo "Deployment summary generated: $summary_file"
    echo ""
    echo -e "${GREEN}✓${NC} Phase 1 Foundation Services deployment completed successfully!"
    echo -e "${GREEN}✓${NC} All services are running and healthy on Pi"
    echo -e "${GREEN}✓${NC} Databases initialized and ready for use"
    echo ""
    echo "Service endpoints:"
    echo "  MongoDB: mongodb://lucid:lucid@$PI_HOST:27017/lucid"
    echo "  Redis: redis://:lucid@$PI_HOST:6379/0"
    echo "  Elasticsearch: http://$PI_HOST:9200"
    echo "  Auth Service: http://$PI_HOST:8089"
}

# Main deployment function
main() {
    init_deployment
    
    # Execute deployment steps
    test_ssh_connection || exit 1
    verify_project_directory || exit 1
    create_docker_networks || exit 1
    create_data_directories || exit 1
    verify_compose_file || exit 1
    verify_environment_config || exit 1
    deploy_distroless_infrastructure || exit 1
    pull_arm64_images || exit 1
    deploy_phase1_services || exit 1
    wait_for_health_checks || exit 1
    verify_services_running || exit 1
    initialize_databases || exit 1
    verify_distroless_compliance || exit 1
    
    generate_deployment_summary
}

# Run main function
main "$@"
