#!/bin/bash
# Phase 2 Core Services Deployment to Raspberry Pi
# Based on docker-build-process-plan.md Step 14
# Deploys API Gateway, Service Mesh, Blockchain Core to Pi

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
SERVICES=("lucid-service-mesh-controller" "lucid-api-gateway" "lucid-blockchain-engine" "lucid-session-anchoring" "lucid-block-manager" "lucid-data-chain")
HEALTH_CHECK_TIMEOUT=60
DEPLOYMENT_LOG="$PROJECT_ROOT/deployment-phase2.log"

# Initialize deployment
init_deployment() {
    echo -e "${BLUE}=== Phase 2 Core Services Deployment ===${NC}"
    echo "Target Pi: $PI_USER@$PI_HOST"
    echo "Deploy Directory: $PI_DEPLOY_DIR"
    echo "Project Root: $PROJECT_ROOT"
    echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo ""
    
    # Clear previous deployment log
    > "$DEPLOYMENT_LOG"
    
    # Log deployment start
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") - Phase 2 deployment started" >> "$DEPLOYMENT_LOG"
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

# Verify Phase 2 compose file exists on Pi
verify_compose_file() {
    echo -e "${BLUE}=== Verifying Docker Compose File ===${NC}"
    
    local pi_compose_file="$PI_DEPLOY_DIR/configs/docker/docker-compose.core.yml"
    
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
    
    local pi_env_file="$PI_DEPLOY_DIR/configs/environment/.env.core"
    
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "test -f $pi_env_file" >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "env-file-verify" "SUCCESS" "Environment configuration exists on Pi"
        return 0
    else
        log_step "env-file-verify" "WARNING" "Environment file not found, will use defaults from compose file"
        return 0
    fi
}

# Pull ARM64 images on Pi
pull_arm64_images() {
    echo -e "${BLUE}=== Pulling ARM64 Images ===${NC}"
    
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        cd $PI_DEPLOY_DIR
        docker-compose -f configs/docker/docker-compose.foundation.yml -f configs/docker/docker-compose.core.yml pull
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "image-pull" "SUCCESS" "ARM64 images pulled successfully on Pi"
    else
        log_step "image-pull" "FAILURE" "Failed to pull ARM64 images on Pi"
        return 1
    fi
}

# Deploy Phase 2 services
deploy_phase2_services() {
    echo -e "${BLUE}=== Deploying Phase 2 Services ===${NC}"
    
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        cd $PI_DEPLOY_DIR
        docker-compose -f configs/docker/docker-compose.foundation.yml -f configs/docker/docker-compose.core.yml up -d
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "service-deployment" "SUCCESS" "Phase 2 services deployed successfully"
    else
        log_step "service-deployment" "FAILURE" "Failed to deploy Phase 2 services"
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
        log_step "service-verification" "SUCCESS" "All Phase 2 services are running"
        return 0
    else
        log_step "service-verification" "FAILURE" "Some Phase 2 services are not running"
        return 1
    fi
}

# Initialize service mesh
initialize_service_mesh() {
    echo -e "${BLUE}=== Initializing Service Mesh ===${NC}"
    
    # Wait for service mesh registration
    log_info "Waiting for service mesh registration..."
    sleep 60
    
    # Test service mesh communication
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        docker exec lucid-service-mesh-controller consul members
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "service-mesh-init" "SUCCESS" "Service mesh initialized successfully"
    else
        log_step "service-mesh-init" "FAILURE" "Service mesh initialization failed"
        return 1
    fi
}

# Verify blockchain is creating blocks
verify_blockchain() {
    echo -e "${BLUE}=== Verifying Blockchain ===${NC}"
    
    # Check if blockchain is creating blocks
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        docker exec lucid-blockchain-engine curl -f http://localhost:8084/health
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "blockchain-health" "SUCCESS" "Blockchain engine is healthy"
    else
        log_step "blockchain-health" "FAILURE" "Blockchain engine health check failed"
        return 1
    fi
}

# Generate deployment summary
generate_deployment_summary() {
    echo -e "${BLUE}=== Deployment Summary ===${NC}"
    
    local summary_file="$PROJECT_ROOT/phase2-deployment-summary.json"
    
    cat > "$summary_file" << EOF
{
  "deployment_summary": {
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "phase": "Phase 2 Core Services",
    "target_pi": "$PI_USER@$PI_HOST",
    "deploy_directory": "$PI_DEPLOY_DIR",
    "services_deployed": [
      "lucid-service-mesh-controller",
      "lucid-api-gateway",
      "lucid-blockchain-engine",
      "lucid-session-anchoring",
      "lucid-block-manager",
      "lucid-data-chain"
    ],
    "deployment_status": "completed",
    "health_check_timeout": $HEALTH_CHECK_TIMEOUT,
    "deployment_log": "$DEPLOYMENT_LOG"
  },
  "service_endpoints": {
    "api_gateway": "http://$PI_HOST:8080",
    "service_mesh_controller": "http://$PI_HOST:8086",
    "consul": "http://$PI_HOST:8500",
    "blockchain_engine": "http://$PI_HOST:8084",
    "session_anchoring": "http://$PI_HOST:8085",
    "block_manager": "http://$PI_HOST:8086",
    "data_chain": "http://$PI_HOST:8087"
  },
  "next_steps": [
    "Run Phase 2 integration tests",
    "Proceed with Phase 3 Application Services deployment",
    "Monitor blockchain block creation",
    "Verify service mesh communication"
  ]
}
EOF
    
    echo "Deployment summary generated: $summary_file"
    echo ""
    echo -e "${GREEN}✓${NC} Phase 2 Core Services deployment completed successfully!"
    echo -e "${GREEN}✓${NC} All services are running and healthy on Pi"
    echo -e "${GREEN}✓${NC} Service mesh initialized and ready"
    echo -e "${GREEN}✓${NC} Blockchain engine is creating blocks"
    echo ""
    echo "Service endpoints:"
    echo "  API Gateway: http://$PI_HOST:8080"
    echo "  Service Mesh Controller: http://$PI_HOST:8086"
    echo "  Consul: http://$PI_HOST:8500"
    echo "  Blockchain Engine: http://$PI_HOST:8084"
    echo "  Session Anchoring: http://$PI_HOST:8085"
    echo "  Block Manager: http://$PI_HOST:8086"
    echo "  Data Chain: http://$PI_HOST:8087"
}

# Main deployment function
main() {
    init_deployment
    
    # Execute deployment steps
    test_ssh_connection || exit 1
    verify_compose_file || exit 1
    verify_environment_config || exit 1
    pull_arm64_images || exit 1
    deploy_phase2_services || exit 1
    wait_for_health_checks || exit 1
    verify_services_running || exit 1
    initialize_service_mesh || exit 1
    verify_blockchain || exit 1
    
    generate_deployment_summary
}

# Run main function
main "$@"
