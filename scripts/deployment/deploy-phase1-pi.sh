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
PI_DEPLOY_DIR="/opt/lucid/production"
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

# Create deployment directory on Pi
create_deploy_directory() {
    echo -e "${BLUE}=== Creating Deployment Directory ===${NC}"
    
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        sudo mkdir -p $PI_DEPLOY_DIR
        sudo chown $PI_USER:$PI_USER $PI_DEPLOY_DIR
        sudo chmod 755 $PI_DEPLOY_DIR
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "deploy-directory" "SUCCESS" "Deployment directory created on Pi"
    else
        log_step "deploy-directory" "FAILURE" "Failed to create deployment directory on Pi"
        return 1
    fi
}

# Create data storage directories on Pi
create_data_directories() {
    echo -e "${BLUE}=== Creating Data Storage Directories ===${NC}"
    
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        # Create main data directory structure for all phases
        sudo mkdir -p /mnt/myssd/Lucid/data/mongodb
        sudo mkdir -p /mnt/myssd/Lucid/data/mongodb-config
        sudo mkdir -p /mnt/myssd/Lucid/data/redis
        sudo mkdir -p /mnt/myssd/Lucid/data/elasticsearch
        sudo mkdir -p /mnt/myssd/Lucid/data/auth
        sudo mkdir -p /mnt/myssd/Lucid/data/blockchain
        sudo mkdir -p /mnt/myssd/Lucid/data/blockchain-engine
        sudo mkdir -p /mnt/myssd/Lucid/data/anchoring
        sudo mkdir -p /mnt/myssd/Lucid/data/block-manager
        sudo mkdir -p /mnt/myssd/Lucid/data/data-chain
        sudo mkdir -p /mnt/myssd/Lucid/data/consul
        sudo mkdir -p /mnt/myssd/Lucid/data/session-pipeline
        sudo mkdir -p /mnt/myssd/Lucid/data/session-recorder
        sudo mkdir -p /mnt/myssd/Lucid/data/session-processor
        sudo mkdir -p /mnt/myssd/Lucid/data/session-storage
        sudo mkdir -p /mnt/myssd/Lucid/data/rdp-server-manager
        sudo mkdir -p /mnt/myssd/Lucid/data/rdp-xrdp
        sudo mkdir -p /mnt/myssd/Lucid/data/rdp-controller
        sudo mkdir -p /mnt/myssd/Lucid/data/rdp-monitor
        sudo mkdir -p /mnt/myssd/Lucid/data/node-management
        sudo mkdir -p /mnt/myssd/Lucid/data/admin-interface
        sudo mkdir -p /mnt/myssd/Lucid/data/tron-client
        sudo mkdir -p /mnt/myssd/Lucid/data/tron-payout-router
        sudo mkdir -p /mnt/myssd/Lucid/data/tron-wallet-manager
        sudo mkdir -p /mnt/myssd/Lucid/data/tron-usdt-manager
        sudo mkdir -p /mnt/myssd/Lucid/data/tron-staking
        sudo mkdir -p /mnt/myssd/Lucid/data/tron-payment-gateway
        sudo mkdir -p /mnt/myssd/Lucid/data/storage
        sudo mkdir -p /mnt/myssd/Lucid/backups
        
        # Create log directory structure
        sudo mkdir -p /mnt/myssd/Lucid/logs/auth
        sudo mkdir -p /mnt/myssd/Lucid/logs/api-gateway
        sudo mkdir -p /mnt/myssd/Lucid/logs/blockchain
        sudo mkdir -p /mnt/myssd/Lucid/logs/blockchain-engine
        sudo mkdir -p /mnt/myssd/Lucid/logs/anchoring
        sudo mkdir -p /mnt/myssd/Lucid/logs/block-manager
        sudo mkdir -p /mnt/myssd/Lucid/logs/data-chain
        sudo mkdir -p /mnt/myssd/Lucid/logs/consul
        sudo mkdir -p /mnt/myssd/Lucid/logs/session-pipeline
        sudo mkdir -p /mnt/myssd/Lucid/logs/session-recorder
        sudo mkdir -p /mnt/myssd/Lucid/logs/session-processor
        sudo mkdir -p /mnt/myssd/Lucid/logs/session-storage
        sudo mkdir -p /mnt/myssd/Lucid/logs/session-api
        sudo mkdir -p /mnt/myssd/Lucid/logs/rdp-server-manager
        sudo mkdir -p /mnt/myssd/Lucid/logs/rdp-xrdp
        sudo mkdir -p /mnt/myssd/Lucid/logs/rdp-controller
        sudo mkdir -p /mnt/myssd/Lucid/logs/rdp-monitor
        sudo mkdir -p /mnt/myssd/Lucid/logs/node-management
        sudo mkdir -p /mnt/myssd/Lucid/logs/admin-interface
        sudo mkdir -p /mnt/myssd/Lucid/logs/tron-client
        sudo mkdir -p /mnt/myssd/Lucid/logs/tron-payout-router
        sudo mkdir -p /mnt/myssd/Lucid/logs/tron-wallet-manager
        sudo mkdir -p /mnt/myssd/Lucid/logs/tron-usdt-manager
        sudo mkdir -p /mnt/myssd/Lucid/logs/tron-staking
        sudo mkdir -p /mnt/myssd/Lucid/logs/tron-payment-gateway
        sudo mkdir -p /mnt/myssd/Lucid/logs/storage
        
        # Set proper ownership and permissions
        sudo chown -R $PI_USER:$PI_USER /mnt/myssd/Lucid
        sudo chmod -R 755 /mnt/myssd/Lucid
        
        # Ensure MongoDB directories have proper permissions
        sudo chmod 755 /mnt/myssd/Lucid/data/mongodb
        sudo chmod 755 /mnt/myssd/Lucid/data/mongodb-config
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "data-directories" "SUCCESS" "All data storage directories created on Pi"
    else
        log_step "data-directories" "FAILURE" "Failed to create data storage directories on Pi"
        return 1
    fi
}

# Copy Phase 1 compose file to Pi
copy_compose_file() {
    echo -e "${BLUE}=== Copying Docker Compose File ===${NC}"
    
    local compose_file="$PROJECT_ROOT/configs/docker/docker-compose.foundation.yml"
    local pi_compose_file="$PI_DEPLOY_DIR/docker-compose.foundation.yml"
    
    if [ -f "$compose_file" ]; then
        scp -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$compose_file" "$PI_USER@$PI_HOST:$pi_compose_file" >/dev/null 2>&1
        
        if [ $? -eq 0 ]; then
            log_step "compose-file-copy" "SUCCESS" "Docker compose file copied to Pi"
        else
            log_step "compose-file-copy" "FAILURE" "Failed to copy Docker compose file to Pi"
            return 1
        fi
    else
        log_step "compose-file-copy" "FAILURE" "Docker compose file not found: $compose_file"
        return 1
    fi
}

# Copy environment configuration to Pi
copy_environment_config() {
    echo -e "${BLUE}=== Copying Environment Configuration ===${NC}"
    
    local env_file="$PROJECT_ROOT/configs/environment/.env.foundation"
    local pi_env_file="$PI_DEPLOY_DIR/.env.foundation"
    
    if [ -f "$env_file" ]; then
        scp -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$env_file" "$PI_USER@$PI_HOST:$pi_env_file" >/dev/null 2>&1
        
        if [ $? -eq 0 ]; then
            log_step "env-file-copy" "SUCCESS" "Environment configuration copied to Pi"
        else
            log_step "env-file-copy" "FAILURE" "Failed to copy environment configuration to Pi"
            return 1
        fi
    else
        log_step "env-file-copy" "FAILURE" "Environment configuration file not found: $env_file"
        return 1
    fi
}

# Pull ARM64 images on Pi
pull_arm64_images() {
    echo -e "${BLUE}=== Pulling ARM64 Images ===${NC}"
    
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        cd $PI_DEPLOY_DIR
        docker-compose -f docker-compose.foundation.yml pull
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
        docker-compose -f docker-compose.foundation.yml up -d
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
    
    # Initialize MongoDB collections
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        docker exec lucid-mongodb mongosh --eval '
            use lucid;
            db.createCollection(\"authentication\");
            db.createCollection(\"sessions\");
            db.createCollection(\"chunks\");
            db.createCollection(\"blocks\");
            db.createCollection(\"transactions\");
        ' --quiet
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
    create_deploy_directory || exit 1
    create_data_directories || exit 1
    copy_compose_file || exit 1
    copy_environment_config || exit 1
    pull_arm64_images || exit 1
    deploy_phase1_services || exit 1
    wait_for_health_checks || exit 1
    verify_services_running || exit 1
    initialize_databases || exit 1
    
    generate_deployment_summary
}

# Run main function
main "$@"
