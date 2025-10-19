#!/bin/bash
# Phase 3 Application Services Deployment Script
# Step 25: Phase 3 Deployment
# Deploys session management, RDP services, and node management to Raspberry Pi
# Target: Raspberry Pi 5 (192.168.0.75) via SSH

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_phase() {
    echo -e "${PURPLE}[PHASE 3]${NC} $1"
}

# Configuration
PI_HOST="192.168.0.75"
PI_USER="pickme"
PI_DEPLOY_PATH="/opt/lucid/production"
PI_DATA_PATH="/mnt/myssd/Lucid"
COMPOSE_FILE="docker-compose.application.yml"
ENV_FILE=".env.application"

# Function to check SSH connection
check_ssh_connection() {
    print_status "Checking SSH connection to Pi..."
    if ssh -o ConnectTimeout=10 -o BatchMode=yes "$PI_USER@$PI_HOST" "echo 'SSH connection successful'" >/dev/null 2>&1; then
        print_success "SSH connection to $PI_HOST successful"
        return 0
    else
        print_error "SSH connection to $PI_HOST failed"
        return 1
    fi
}

# Function to check Pi disk space
check_pi_disk_space() {
    print_status "Checking Pi disk space..."
    local available_space=$(ssh "$PI_USER@$PI_HOST" "df -h /mnt/myssd | tail -1 | awk '{print \$4}'")
    print_status "Available space on Pi: $available_space"
    
    # Check if we have at least 20GB free
    if ssh "$PI_USER@$PI_HOST" "df -BG /mnt/myssd | tail -1 | awk '{print \$4}' | sed 's/G//'" | awk '{if($1 < 20) exit 1}'; then
        print_success "Sufficient disk space available on Pi"
        return 0
    else
        print_error "Insufficient disk space on Pi (need at least 20GB)"
        return 1
    fi
}

# Function to create Pi directories
create_pi_directories() {
    print_status "Creating Pi directories..."
    ssh "$PI_USER@$PI_HOST" "
        sudo mkdir -p $PI_DEPLOY_PATH
        sudo mkdir -p $PI_DATA_PATH/{logs,data,recordings,sessions}
        sudo mkdir -p $PI_DATA_PATH/logs/{session-pipeline,session-recorder,chunk-processor,session-storage,session-api,rdp-server-manager,xrdp-integration,session-controller,resource-monitor,node-management}
        sudo mkdir -p $PI_DATA_PATH/data/{session-pipeline,session-recorder,chunk-processor,session-storage,session-api,rdp-server-manager,xrdp-integration,session-controller,resource-monitor,node-management}
        sudo chown -R $PI_USER:$PI_USER $PI_DEPLOY_PATH
        sudo chown -R $PI_USER:$PI_USER $PI_DATA_PATH
    "
    print_success "Pi directories created successfully"
}

# Function to copy files to Pi
copy_files_to_pi() {
    print_status "Copying files to Pi..."
    
    # Copy compose file
    scp "configs/docker/$COMPOSE_FILE" "$PI_USER@$PI_HOST:$PI_DEPLOY_PATH/"
    
    # Copy environment file if it exists
    if [[ -f "configs/environment/$ENV_FILE" ]]; then
        scp "configs/environment/$ENV_FILE" "$PI_USER@$PI_HOST:$PI_DEPLOY_PATH/"
    else
        print_warning "Environment file $ENV_FILE not found, using defaults"
    fi
    
    print_success "Files copied to Pi successfully"
}

# Function to pull images on Pi
pull_images_on_pi() {
    print_status "Pulling Phase 3 images on Pi..."
    
    local images=(
        "pickme/lucid-session-pipeline:latest-arm64"
        "pickme/lucid-session-recorder:latest-arm64"
        "pickme/lucid-chunk-processor:latest-arm64"
        "pickme/lucid-session-storage:latest-arm64"
        "pickme/lucid-session-api:latest-arm64"
        "pickme/lucid-rdp-server-manager:latest-arm64"
        "pickme/lucid-xrdp-integration:latest-arm64"
        "pickme/lucid-session-controller:latest-arm64"
        "pickme/lucid-resource-monitor:latest-arm64"
        "pickme/lucid-node-management:latest-arm64"
    )
    
    for image in "${images[@]}"; do
        print_status "Pulling $image..."
        if ssh "$PI_USER@$PI_HOST" "docker pull $image"; then
            print_success "Successfully pulled $image"
        else
            print_error "Failed to pull $image"
            return 1
        fi
    done
    
    print_success "All Phase 3 images pulled successfully"
}

# Function to deploy services on Pi
deploy_services_on_pi() {
    print_status "Deploying Phase 3 services on Pi..."
    
    ssh "$PI_USER@$PI_HOST" "
        cd $PI_DEPLOY_PATH
        
        # Stop any existing Phase 3 services
        docker-compose -f $COMPOSE_FILE down || true
        
        # Start Phase 3 services
        docker-compose -f $COMPOSE_FILE up -d
        
        # Wait for services to start
        echo 'Waiting for services to start...'
        sleep 30
        
        # Check service status
        docker-compose -f $COMPOSE_FILE ps
    "
    
    print_success "Phase 3 services deployed successfully"
}

# Function to verify deployment
verify_deployment() {
    print_status "Verifying Phase 3 deployment..."
    
    # Check if all services are running
    local services=(
        "lucid-session-pipeline"
        "lucid-session-recorder"
        "lucid-chunk-processor"
        "lucid-session-storage"
        "lucid-session-api"
        "lucid-rdp-server-manager"
        "lucid-xrdp-integration"
        "lucid-session-controller"
        "lucid-resource-monitor"
        "lucid-node-management"
    )
    
    for service in "${services[@]}"; do
        if ssh "$PI_USER@$PI_HOST" "docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -q '$service.*Up'"; then
            print_success "$service is running"
        else
            print_error "$service is not running"
            return 1
        fi
    done
    
    # Check health endpoints
    print_status "Checking health endpoints..."
    local health_checks=(
        "8083:lucid-session-pipeline"
        "8084:lucid-session-recorder"
        "8085:lucid-chunk-processor"
        "8086:lucid-session-storage"
        "8087:lucid-session-api"
        "8081:lucid-rdp-server-manager"
        "8082:lucid-session-controller"
        "8090:lucid-resource-monitor"
        "8095:lucid-node-management"
    )
    
    for check in "${health_checks[@]}"; do
        local port=$(echo $check | cut -d: -f1)
        local service=$(echo $check | cut -d: -f2)
        
        if ssh "$PI_USER@$PI_HOST" "curl -f http://localhost:$port/health >/dev/null 2>&1"; then
            print_success "$service health check passed"
        else
            print_warning "$service health check failed (may still be starting)"
        fi
    done
    
    print_success "Phase 3 deployment verification completed"
}

# Function to show deployment summary
show_deployment_summary() {
    echo ""
    echo "=========================================="
    print_success "Phase 3 Application Services Deployment Complete!"
    echo "=========================================="
    echo ""
    print_success "Deployed Services:"
    echo "Session Management:"
    echo "  - lucid-session-pipeline:8083"
    echo "  - lucid-session-recorder:8084"
    echo "  - lucid-chunk-processor:8085"
    echo "  - lucid-session-storage:8086"
    echo "  - lucid-session-api:8087"
    echo ""
    echo "RDP Services:"
    echo "  - lucid-rdp-server-manager:8081"
    echo "  - lucid-xrdp-integration:3389"
    echo "  - lucid-session-controller:8082"
    echo "  - lucid-resource-monitor:8090"
    echo ""
    echo "Node Management:"
    echo "  - lucid-node-management:8095"
    echo ""
    print_status "Next: Run Phase 3 integration tests"
    print_status "Access Pi: ssh $PI_USER@$PI_HOST"
    print_status "View logs: docker logs <container-name>"
    echo ""
}

# Main deployment function
main() {
    echo "=========================================="
    print_phase "Deploying Phase 3 Application Services to Pi"
    echo "=========================================="
    echo "Target: $PI_USER@$PI_HOST"
    echo "Deploy Path: $PI_DEPLOY_PATH"
    echo "Data Path: $PI_DATA_PATH"
    echo "Deploy Date: $(date)"
    echo ""
    
    # Pre-deployment checks
    print_status "Performing pre-deployment checks..."
    check_ssh_connection || exit 1
    check_pi_disk_space || exit 1
    print_success "Pre-deployment checks passed"
    echo ""
    
    # Deployment steps
    print_status "Starting Phase 3 deployment..."
    create_pi_directories
    copy_files_to_pi
    pull_images_on_pi
    deploy_services_on_pi
    verify_deployment
    
    # Show summary
    show_deployment_summary
    
    print_success "Phase 3 deployment completed successfully!"
}

# Run main function
main "$@"
