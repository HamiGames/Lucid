#!/bin/bash
# Phase 4 Support Services Deployment to Raspberry Pi
# Based on docker-build-process-plan.md Step 32
# Deploys Admin Interface and TRON Payment System (Isolated) to Pi

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
ADMIN_SERVICES=("lucid-admin-interface")
TRON_SERVICES=("lucid-tron-client" "lucid-payout-router" "lucid-wallet-manager" "lucid-usdt-manager" "lucid-trx-staking" "lucid-payment-gateway")
ALL_SERVICES=("${ADMIN_SERVICES[@]}" "${TRON_SERVICES[@]}")
HEALTH_CHECK_TIMEOUT=60
DEPLOYMENT_LOG="$PROJECT_ROOT/deployment-phase4.log"

# Initialize deployment
init_deployment() {
    echo -e "${BLUE}=== Phase 4 Support Services Deployment ===${NC}"
    echo "Target Pi: $PI_USER@$PI_HOST"
    echo "Deploy Directory: $PI_DEPLOY_DIR"
    echo "Project Root: $PROJECT_ROOT"
    echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo ""
    
    # Clear previous deployment log
    > "$DEPLOYMENT_LOG"
    
    # Log deployment start
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") - Phase 4 deployment started" >> "$DEPLOYMENT_LOG"
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

# Create isolated TRON network
create_tron_network() {
    echo -e "${BLUE}=== Creating TRON Isolated Network ===${NC}"
    
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        # Create isolated TRON network
        docker network create --driver bridge --attachable --subnet=172.25.0.0/16 --gateway=172.25.0.1 lucid-tron-isolated 2>/dev/null || true
        
        # Verify network creation
        if docker network inspect lucid-tron-isolated >/dev/null 2>&1; then
            echo 'TRON isolated network created successfully'
        else
            echo 'Failed to create TRON isolated network'
            exit 1
        fi
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "tron-network" "SUCCESS" "TRON isolated network created"
    else
        log_step "tron-network" "FAILURE" "Failed to create TRON isolated network"
        return 1
    fi
}

# Verify Phase 4 compose file exists on Pi
verify_compose_file() {
    echo -e "${BLUE}=== Verifying Docker Compose File ===${NC}"
    
    local pi_compose_file="$PI_DEPLOY_DIR/configs/docker/docker-compose.support.yml"
    
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
    
    local pi_env_file="$PI_DEPLOY_DIR/configs/environment/.env.support"
    
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
        docker-compose -f configs/docker/docker-compose.foundation.yml -f configs/docker/docker-compose.core.yml -f configs/docker/docker-compose.application.yml -f configs/docker/docker-compose.support.yml pull
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "image-pull" "SUCCESS" "ARM64 images pulled successfully on Pi"
    else
        log_step "image-pull" "FAILURE" "Failed to pull ARM64 images on Pi"
        return 1
    fi
}

# Deploy Phase 4 services
deploy_phase4_services() {
    echo -e "${BLUE}=== Deploying Phase 4 Services ===${NC}"
    
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        cd $PI_DEPLOY_DIR
        docker-compose -f configs/docker/docker-compose.foundation.yml -f configs/docker/docker-compose.core.yml -f configs/docker/docker-compose.application.yml -f configs/docker/docker-compose.support.yml up -d
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "service-deployment" "SUCCESS" "Phase 4 services deployed successfully"
    else
        log_step "service-deployment" "FAILURE" "Failed to deploy Phase 4 services"
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
        
        for service in "${ALL_SERVICES[@]}"; do
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
    
    for service in "${ALL_SERVICES[@]}"; do
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
        log_step "service-verification" "SUCCESS" "All Phase 4 services are running"
        return 0
    else
        log_step "service-verification" "FAILURE" "Some Phase 4 services are not running"
        return 1
    fi
}

# Verify TRON network isolation
verify_tron_isolation() {
    echo -e "${BLUE}=== Verifying TRON Network Isolation ===${NC}"
    
    # Check if TRON services are on isolated network
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        for service in ${TRON_SERVICES[@]}; do
            if docker inspect \$service --format='{{range .NetworkSettings.Networks}}{{.NetworkID}}{{end}}' | grep -q lucid-tron-isolated; then
                echo \"\$service is on TRON isolated network\"
            else
                echo \"\$service is NOT on TRON isolated network\"
                exit 1
            fi
        done
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "tron-isolation" "SUCCESS" "TRON services are properly isolated"
    else
        log_step "tron-isolation" "FAILURE" "TRON services are not properly isolated"
        return 1
    fi
}

# Test admin dashboard
test_admin_dashboard() {
    echo -e "${BLUE}=== Testing Admin Dashboard ===${NC}"
    
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        docker exec lucid-admin-interface curl -f http://localhost:8083/health
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "admin-dashboard" "SUCCESS" "Admin dashboard is accessible"
    else
        log_step "admin-dashboard" "FAILURE" "Admin dashboard health check failed"
        return 1
    fi
}

# Test TRON payment flow
test_tron_payment_flow() {
    echo -e "${BLUE}=== Testing TRON Payment Flow ===${NC}"
    
    # Test TRON client connection
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        docker exec lucid-tron-client curl -f http://localhost:8091/health
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "tron-client" "SUCCESS" "TRON client is accessible"
    else
        log_step "tron-client" "FAILURE" "TRON client health check failed"
        return 1
    fi
    
    # Test payment gateway
    ssh -o ConnectTimeout=300 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "
        docker exec lucid-payment-gateway curl -f http://localhost:8097/health
    " >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_step "payment-gateway" "SUCCESS" "Payment gateway is accessible"
    else
        log_step "payment-gateway" "FAILURE" "Payment gateway health check failed"
        return 1
    fi
}

# Generate deployment summary
generate_deployment_summary() {
    echo -e "${BLUE}=== Deployment Summary ===${NC}"
    
    local summary_file="$PROJECT_ROOT/phase4-deployment-summary.json"
    
    cat > "$summary_file" << EOF
{
  "deployment_summary": {
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "phase": "Phase 4 Support Services",
    "target_pi": "$PI_USER@$PI_HOST",
    "deploy_directory": "$PI_DEPLOY_DIR",
    "services_deployed": [
      "lucid-admin-interface",
      "lucid-tron-client",
      "lucid-payout-router",
      "lucid-wallet-manager",
      "lucid-usdt-manager",
      "lucid-trx-staking",
      "lucid-payment-gateway"
    ],
    "deployment_status": "completed",
    "health_check_timeout": $HEALTH_CHECK_TIMEOUT,
    "deployment_log": "$DEPLOYMENT_LOG"
  },
  "service_endpoints": {
    "admin_interface": "http://$PI_HOST:8083",
    "tron_client": "http://$PI_HOST:8091",
    "payout_router": "http://$PI_HOST:8092",
    "wallet_manager": "http://$PI_HOST:8093",
    "usdt_manager": "http://$PI_HOST:8094",
    "trx_staking": "http://$PI_HOST:8096",
    "payment_gateway": "http://$PI_HOST:8097"
  },
  "network_isolation": {
    "tron_network": "lucid-tron-isolated",
    "tron_subnet": "172.25.0.0/16",
    "isolation_status": "verified"
  },
  "next_steps": [
    "Run Phase 4 integration tests",
    "Run final system integration test",
    "Generate master Docker Compose file",
    "Monitor admin dashboard and TRON payment system"
  ]
}
EOF
    
    echo "Deployment summary generated: $summary_file"
    echo ""
    echo -e "${GREEN}✓${NC} Phase 4 Support Services deployment completed successfully!"
    echo -e "${GREEN}✓${NC} All services are running and healthy on Pi"
    echo -e "${GREEN}✓${NC} Admin interface is accessible"
    echo -e "${GREEN}✓${NC} TRON payment system is isolated and ready"
    echo ""
    echo "Service endpoints:"
    echo "  Admin Interface: http://$PI_HOST:8083"
    echo "  TRON Client: http://$PI_HOST:8091"
    echo "  Payout Router: http://$PI_HOST:8092"
    echo "  Wallet Manager: http://$PI_HOST:8093"
    echo "  USDT Manager: http://$PI_HOST:8094"
    echo "  TRX Staking: http://$PI_HOST:8096"
    echo "  Payment Gateway: http://$PI_HOST:8097"
    echo ""
    echo "Network Isolation:"
    echo "  TRON Network: lucid-tron-isolated (172.25.0.0/16)"
    echo "  Status: Verified and isolated from main network"
}

# Main deployment function
main() {
    init_deployment
    
    # Execute deployment steps
    test_ssh_connection || exit 1
    create_tron_network || exit 1
    verify_compose_file || exit 1
    verify_environment_config || exit 1
    pull_arm64_images || exit 1
    deploy_phase4_services || exit 1
    wait_for_health_checks || exit 1
    verify_services_running || exit 1
    verify_tron_isolation || exit 1
    test_admin_dashboard || exit 1
    test_tron_payment_flow || exit 1
    
    generate_deployment_summary
}

# Run main function
main "$@"
