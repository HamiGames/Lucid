#!/bin/bash
# Path: scripts/deployment/deploy-lucid-services.sh
# Deploy Lucid Services Using Pre-Built Distroless Images
# Deploys Foundation → Core → Application → Support → GUI in order
# MUST RUN ON PI CONSOLE

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Project root
PROJECT_ROOT="${PROJECT_ROOT:-/mnt/myssd/Lucid/Lucid}"

echo ""
log_info "========================================"
log_info "Deploying Lucid Services (Distroless)"
log_info "========================================"
echo ""

# Check if we're in the right directory
if [ ! -f "configs/docker/docker-compose.foundation.yml" ]; then
    log_error "Not in project root directory!"
    log_error "Please run from: $PROJECT_ROOT"
    exit 1
fi

# Check if .env files exist
for env_file in "configs/environment/.env.foundation" "configs/environment/.env.core" "configs/environment/.env.application" "configs/environment/.env.support"; do
    if [ ! -f "$env_file" ]; then
        log_error "Required .env file not found: $env_file"
        log_error "Please run first: bash scripts/config/generate-all-env-complete.sh"
        exit 1
    fi
done

log_info "Found all required .env files"
echo ""

# Function to deploy phase
deploy_phase() {
    local phase_name=$1
    local compose_file=$2
    local env_files=$3
    local description=$4
    local wait_time=${5:-60}
    
    log_info "Deploying $phase_name..."
    log_info "Description: $description"
    log_info "Compose file: $compose_file"
    log_info "Environment files: $env_files"
    echo ""
    
    # Check if compose file exists
    if [ ! -f "$compose_file" ]; then
        log_error "Compose file not found: $compose_file"
        return 1
    fi
    
    # Build docker-compose command
    local docker_compose_cmd="docker-compose"
    
    # Add environment files
    for env_file in $env_files; do
        if [ -f "$env_file" ]; then
            docker_compose_cmd="$docker_compose_cmd --env-file $env_file"
        else
            log_warning "Environment file not found: $env_file"
        fi
    done
    
    # Add compose file and command
    docker_compose_cmd="$docker_compose_cmd -f $compose_file up -d"
    
    log_info "Running: $docker_compose_cmd"
    echo ""
    
    # Execute deployment
    eval $docker_compose_cmd
    
    if [ $? -eq 0 ]; then
        log_success "$phase_name deployed successfully"
        
        # Wait for services to initialize
        log_info "Waiting for $phase_name services to initialize ($wait_time seconds)..."
        sleep $wait_time
        
        # Check container health
        local containers=$(docker-compose -f "$compose_file" ps -q 2>/dev/null || true)
        if [ -n "$containers" ]; then
            local healthy_count=0
            local total_count=0
            
            for container in $containers; do
                local container_name=$(docker inspect --format '{{.Name}}' "$container" | sed 's/^\///')
                local health=$(docker inspect --format '{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no-healthcheck")
                local status=$(docker inspect --format '{{.State.Status}}' "$container")
                
                total_count=$((total_count + 1))
                
                if [ "$status" = "running" ]; then
                    if [ "$health" = "healthy" ]; then
                        log_success "Container $container_name is healthy"
                        healthy_count=$((healthy_count + 1))
                    elif [ "$health" = "no-healthcheck" ]; then
                        log_info "Container $container_name is running (no health check)"
                        healthy_count=$((healthy_count + 1))
                    else
                        log_warning "Container $container_name health status: $health"
                    fi
                else
                    log_error "Container $container_name status: $status"
                fi
            done
            
            log_info "Health summary: $healthy_count/$total_count containers healthy"
        fi
        
        return 0
    else
        log_error "Failed to deploy $phase_name"
        return 1
    fi
}

# Function to test service health
test_service_health() {
    local service_name=$1
    local health_url=$2
    local expected_response=${3:-"healthy"}
    
    log_info "Testing $service_name health..."
    
    if curl -f -s "$health_url" > /dev/null 2>&1; then
        log_success "$service_name: Healthy"
        return 0
    else
        log_warning "$service_name: Health check failed or service not ready"
        return 1
    fi
}

# Main deployment process

# Step 1: Deploy Phase 1 - Foundation Services
log_info "Step 1: Deploying Phase 1 - Foundation Services"
echo ""

if ! deploy_phase \
    "Phase 1 - Foundation" \
    "configs/docker/docker-compose.foundation.yml" \
    "configs/environment/.env.foundation" \
    "MongoDB, Redis, Elasticsearch, and Auth Service using pre-built distroless images" \
    90; then
    log_error "Failed to deploy Phase 1 - Foundation"
    exit 1
fi

# Test foundation services
log_info "Testing foundation services..."
test_service_health "Auth Service" "http://localhost:8089/health"
echo ""

# Step 2: Deploy Phase 2 - Core Services
log_info "Step 2: Deploying Phase 2 - Core Services"
echo ""

if ! deploy_phase \
    "Phase 2 - Core" \
    "configs/docker/docker-compose.core.yml" \
    "configs/environment/.env.foundation configs/environment/.env.core" \
    "API Gateway, Blockchain Core, and Service Mesh using pre-built distroless images" \
    60; then
    log_error "Failed to deploy Phase 2 - Core"
    exit 1
fi

# Test core services
log_info "Testing core services..."
test_service_health "API Gateway" "http://localhost:8080/health"
test_service_health "Blockchain Core" "http://localhost:8084/health"
echo ""

# Step 3: Deploy Phase 3 - Application Services
log_info "Step 3: Deploying Phase 3 - Application Services"
echo ""

if ! deploy_phase \
    "Phase 3 - Application" \
    "configs/docker/docker-compose.application.yml" \
    "configs/environment/.env.foundation configs/environment/.env.application" \
    "Session Management, RDP Services, and Node Management using pre-built distroless images" \
    60; then
    log_error "Failed to deploy Phase 3 - Application"
    exit 1
fi

# Test application services
log_info "Testing application services..."
test_service_health "Session Pipeline" "http://localhost:8083/health"
test_service_health "Node Management" "http://localhost:8095/health"
echo ""

# Step 4: Deploy Phase 4 - Support Services
log_info "Step 4: Deploying Phase 4 - Support Services"
echo ""

if ! deploy_phase \
    "Phase 4 - Support" \
    "configs/docker/docker-compose.support.yml" \
    "configs/environment/.env.foundation configs/environment/.env.support" \
    "Admin Interface and TRON Payment System (isolated) using pre-built distroless images" \
    60; then
    log_error "Failed to deploy Phase 4 - Support"
    exit 1
fi

# Test support services
log_info "Testing support services..."
test_service_health "Admin Interface" "http://localhost:8120/health"
test_service_health "TRON Client" "http://localhost:8091/health"
echo ""

# Step 5: Deploy GUI Integration (Optional)
read -p "Deploy GUI Integration services? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Step 5: Deploying GUI Integration Services"
    echo ""
    
    if ! deploy_phase \
        "GUI Integration" \
        "configs/docker/docker-compose.gui-integration.yml" \
        "configs/environment/.env.foundation configs/environment/.env.gui" \
        "Electron GUI integration services using pre-built distroless images" \
        60; then
        log_warning "Failed to deploy GUI Integration (continuing...)"
    fi
    
    echo ""
fi

# Step 6: Final verification
log_info "Step 6: Final verification and health checks"
echo ""

# Show all running containers
log_info "All Lucid containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep lucid || log_info "No Lucid containers found"

echo ""

# Test database connections
log_info "Testing database connections..."

# Test MongoDB requires password
if docker exec lucid-mongodb mongosh -u lucid -p wrongpassword --authenticationDatabase admin --eval "db.runCommand('ping')" 2>&1 | grep -q "Authentication failed"; then
    log_success "MongoDB: Password required (secure)"
else
    log_warning "MongoDB: Password test inconclusive"
fi

# Test Redis requires password
if docker exec lucid-redis redis-cli ping 2>&1 | grep -q "NOAUTH"; then
    log_success "Redis: Password required (secure)"
else
    log_warning "Redis: Password test inconclusive"
fi

echo ""

# Test network isolation
log_info "Testing network isolation..."

# Verify TRON services are on isolated network
if docker inspect lucid-tron-client 2>/dev/null | grep -q "lucid-tron-isolated"; then
    log_success "TRON services: Properly isolated on lucid-tron-isolated network"
else
    log_warning "TRON services: Network isolation check failed"
fi

# Verify main services are on pi-network
if docker inspect lucid-api-gateway 2>/dev/null | grep -q "lucid-pi-network"; then
    log_success "Main services: Correctly on lucid-pi-network"
else
    log_warning "Main services: Network assignment check failed"
fi

echo ""

# Show network assignments
log_info "Network assignments:"
docker network ls | grep lucid | while read line; do
    local network_name=$(echo "$line" | awk '{print $2}')
    local network_id=$(echo "$line" | awk '{print $1}')
    echo "  • $network_name (ID: $network_id)"
done

echo ""

log_success "========================================"
log_success "Lucid services deployed successfully!"
log_success "========================================"
echo ""
log_info "Deployed phases:"
log_info "  • Phase 1 - Foundation: MongoDB, Redis, Elasticsearch, Auth"
log_info "  • Phase 2 - Core: API Gateway, Blockchain, Service Mesh"
log_info "  • Phase 3 - Application: Sessions, RDP, Node Management"
log_info "  • Phase 4 - Support: Admin Interface, TRON Payment System"
log_info "  • GUI Integration: Electron GUI services (if selected)"
echo ""
log_info "Key endpoints:"
log_info "  • API Gateway: http://localhost:8080"
log_info "  • Admin Interface: http://localhost:8120"
log_info "  • Auth Service: http://localhost:8089"
log_info "  • Blockchain Core: http://localhost:8084"
echo ""
log_info "Network isolation:"
log_info "  • Main services: lucid-pi-network (172.20.0.0/16)"
log_info "  • TRON services: lucid-tron-isolated (172.21.0.0/16)"
log_info "  • GUI services: lucid-gui-network (172.22.0.0/16)"
echo ""
log_info "Next steps:"
log_info "  1. Test service endpoints manually"
log_info "  2. Configure monitoring and logging"
log_info "  3. Set up backup procedures"
log_info "  4. Deploy multi-stage build infrastructure (optional):"
log_info "     bash scripts/deployment/deploy-multi-stage-build.sh"
echo ""
