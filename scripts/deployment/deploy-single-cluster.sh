#!/bin/bash
# Lucid Single Cluster Deployment Script
# Deploys a specific cluster for focused development and testing
# Based on Step 50 requirements from BUILD_REQUIREMENTS_GUIDE.md

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"
DATA_DIR="${PROJECT_ROOT}/data"

# Default parameters
CLUSTER="${1:-}"
ACTION="${2:-deploy}"
ENVIRONMENT="${3:-dev}"

# Cluster definitions
declare -A CLUSTERS=(
    [01-api-gateway]="API Gateway Cluster"
    [02-blockchain-core]="Blockchain Core Cluster"
    [03-session-management]="Session Management Cluster"
    [04-rdp-services]="RDP Services Cluster"
    [05-node-management]="Node Management Cluster"
    [06-admin-interface]="Admin Interface Cluster"
    [07-tron-payment]="TRON Payment Cluster"
    [08-storage-database]="Storage Database Cluster"
    [09-authentication]="Authentication Cluster"
    [10-cross-cluster]="Cross-Cluster Integration"
)

# Service definitions per cluster
declare -A CLUSTER_SERVICES=(
    [01-api-gateway]="lucid-api-gateway:8080"
    [02-blockchain-core]="lucid-blockchain-engine:8084,lucid-session-anchoring:8085,lucid-block-manager:8086,lucid-data-chain:8087"
    [03-session-management]="lucid-session-pipeline:8083,lucid-session-recorder:8088,lucid-session-processor:8089,lucid-session-storage:8090,lucid-session-api:8091"
    [04-rdp-services]="lucid-rdp-server-manager:8092,lucid-xrdp:8093,lucid-session-controller:8094,lucid-resource-monitor:8095"
    [05-node-management]="lucid-node-management:8096"
    [06-admin-interface]="lucid-admin-interface:8083"
    [07-tron-payment]="lucid-tron-client:8085,lucid-payout-router:8086,lucid-wallet-manager:8087,lucid-usdt-manager:8088,lucid-trx-staking:8089,lucid-payment-gateway:8090"
    [08-storage-database]="lucid-mongodb:27017,lucid-redis:6379,lucid-elasticsearch:9200"
    [09-authentication]="lucid-auth-service:8089"
    [10-cross-cluster]="lucid-service-mesh:8500"
)

# Utility functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "${CYAN}===== $1 =====${NC}"
}

# Validate cluster
validate_cluster() {
    if [[ -z "$CLUSTER" ]]; then
        log_error "Cluster not specified"
        return 1
    fi
    
    if [[ ! "${CLUSTERS[$CLUSTER]:-}" ]]; then
        log_error "Invalid cluster: $CLUSTER"
        log_info "Available clusters:"
        for cluster in "${!CLUSTERS[@]}"; do
            echo -e "  ${YELLOW}-${NC} $cluster: ${CLUSTERS[$cluster]}"
        done
        return 1
    fi
    
    log_success "Cluster validated: $CLUSTER - ${CLUSTERS[$CLUSTER]}"
    return 0
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites for cluster deployment..."
    
    local prereq_errors=()
    
    # Check Docker
    if ! command -v docker >/dev/null 2>&1; then
        prereq_errors+=("Docker not installed")
    elif ! docker --version >/dev/null 2>&1; then
        prereq_errors+=("Docker not working")
    else
        log_success "Docker is available"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose >/dev/null 2>&1; then
        prereq_errors+=("Docker Compose not installed")
    else
        log_success "Docker Compose is available"
    fi
    
    # Check cluster-specific prerequisites
    case "$CLUSTER" in
        "08-storage-database")
            # Check for database-specific requirements
            if ! docker volume ls | grep -q lucid-mongo-data; then
                log_warning "MongoDB data volume not found, will be created"
            fi
            ;;
        "09-authentication")
            # Check for auth-specific requirements
            if [[ ! -f "${PROJECT_ROOT}/auth/Dockerfile" ]]; then
                prereq_errors+=("Authentication Dockerfile not found")
            fi
            ;;
        "02-blockchain-core")
            # Check for blockchain-specific requirements
            if [[ ! -f "${PROJECT_ROOT}/blockchain/Dockerfile.engine" ]]; then
                prereq_errors+=("Blockchain Dockerfile not found")
            fi
            ;;
    esac
    
    if [[ ${#prereq_errors[@]} -gt 0 ]]; then
        log_error "Prerequisites check failed:"
        for error in "${prereq_errors[@]}"; do
            echo -e "  ${RED}-${NC} $error"
        done
        return 1
    fi
    
    log_success "All prerequisites met"
    return 0
}

# Initialize environment
initialize_environment() {
    log_info "Initializing environment for cluster: $CLUSTER"
    
    # Create directories
    for dir in "$LOG_DIR" "$DATA_DIR"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_success "Created directory: $dir"
        fi
    done
    
    # Set environment variables
    export LUCID_ENV="$ENVIRONMENT"
    export LUCID_CLUSTER="$CLUSTER"
    export LUCID_NETWORK="lucid-dev"
    export LUCID_LOG_LEVEL="DEBUG"
    export LUCID_DEBUG="true"
    
    # Create Docker networks
    log_info "Creating Docker networks..."
    docker network create lucid-dev --subnet 172.20.0.0/16 --driver bridge 2>/dev/null || true
    docker network create lucid-internal --subnet 172.21.0.0/16 --driver bridge --internal 2>/dev/null || true
    
    # Cluster-specific network setup
    case "$CLUSTER" in
        "02-blockchain-core")
            docker network create lucid-blockchain --subnet 172.22.0.0/16 --driver bridge 2>/dev/null || true
            ;;
        "07-tron-payment")
            docker network create lucid-payment --subnet 172.23.0.0/16 --driver bridge 2>/dev/null || true
            ;;
    esac
    
    log_success "Environment initialized"
    return 0
}

# Build cluster services
build_cluster_services() {
    log_info "Building services for cluster: $CLUSTER"
    
    local services="${CLUSTER_SERVICES[$CLUSTER]}"
    IFS=',' read -ra SERVICE_LIST <<< "$services"
    
    for service_info in "${SERVICE_LIST[@]}"; do
        local service_name="${service_info%%:*}"
        local service_port="${service_info#*:}"
        
        log_info "Building service: $service_name"
        
        # Determine Dockerfile path based on service
        local dockerfile_path=""
        case "$service_name" in
            "lucid-api-gateway")
                dockerfile_path="${PROJECT_ROOT}/03-api-gateway/Dockerfile"
                ;;
            "lucid-blockchain-engine")
                dockerfile_path="${PROJECT_ROOT}/blockchain/Dockerfile.engine"
                ;;
            "lucid-session-anchoring")
                dockerfile_path="${PROJECT_ROOT}/blockchain/Dockerfile.anchoring"
                ;;
            "lucid-block-manager")
                dockerfile_path="${PROJECT_ROOT}/blockchain/Dockerfile.manager"
                ;;
            "lucid-data-chain")
                dockerfile_path="${PROJECT_ROOT}/blockchain/Dockerfile.data"
                ;;
            "lucid-session-pipeline")
                dockerfile_path="${PROJECT_ROOT}/sessions/Dockerfile.pipeline"
                ;;
            "lucid-session-recorder")
                dockerfile_path="${PROJECT_ROOT}/sessions/Dockerfile.recorder"
                ;;
            "lucid-session-processor")
                dockerfile_path="${PROJECT_ROOT}/sessions/Dockerfile.processor"
                ;;
            "lucid-session-storage")
                dockerfile_path="${PROJECT_ROOT}/sessions/Dockerfile.storage"
                ;;
            "lucid-session-api")
                dockerfile_path="${PROJECT_ROOT}/sessions/Dockerfile.api"
                ;;
            "lucid-rdp-server-manager")
                dockerfile_path="${PROJECT_ROOT}/RDP/Dockerfile.server-manager"
                ;;
            "lucid-xrdp")
                dockerfile_path="${PROJECT_ROOT}/RDP/Dockerfile.xrdp"
                ;;
            "lucid-session-controller")
                dockerfile_path="${PROJECT_ROOT}/RDP/Dockerfile.controller"
                ;;
            "lucid-resource-monitor")
                dockerfile_path="${PROJECT_ROOT}/RDP/Dockerfile.monitor"
                ;;
            "lucid-node-management")
                dockerfile_path="${PROJECT_ROOT}/node/Dockerfile"
                ;;
            "lucid-admin-interface")
                dockerfile_path="${PROJECT_ROOT}/admin/Dockerfile"
                ;;
            "lucid-tron-client")
                dockerfile_path="${PROJECT_ROOT}/payment-systems/tron/Dockerfile.tron-client"
                ;;
            "lucid-payout-router")
                dockerfile_path="${PROJECT_ROOT}/payment-systems/tron/Dockerfile.payout-router"
                ;;
            "lucid-wallet-manager")
                dockerfile_path="${PROJECT_ROOT}/payment-systems/tron/Dockerfile.wallet-manager"
                ;;
            "lucid-usdt-manager")
                dockerfile_path="${PROJECT_ROOT}/payment-systems/tron/Dockerfile.usdt-manager"
                ;;
            "lucid-trx-staking")
                dockerfile_path="${PROJECT_ROOT}/payment-systems/tron/Dockerfile.trx-staking"
                ;;
            "lucid-payment-gateway")
                dockerfile_path="${PROJECT_ROOT}/payment-systems/tron/Dockerfile.payment-gateway"
                ;;
            "lucid-mongodb")
                dockerfile_path="${PROJECT_ROOT}/infrastructure/containers/storage/Dockerfile.mongodb"
                ;;
            "lucid-redis")
                dockerfile_path="${PROJECT_ROOT}/infrastructure/containers/storage/Dockerfile.redis"
                ;;
            "lucid-elasticsearch")
                dockerfile_path="${PROJECT_ROOT}/infrastructure/containers/storage/Dockerfile.elasticsearch"
                ;;
            "lucid-auth-service")
                dockerfile_path="${PROJECT_ROOT}/auth/Dockerfile"
                ;;
            "lucid-service-mesh")
                dockerfile_path="${PROJECT_ROOT}/infrastructure/service-mesh/Dockerfile.controller"
                ;;
        esac
        
        if [[ -f "$dockerfile_path" ]]; then
            docker build -t "$service_name:latest" -f "$dockerfile_path" "${PROJECT_ROOT}"
            if [[ $? -eq 0 ]]; then
                log_success "Built $service_name successfully"
            else
                log_error "Failed to build $service_name"
                return 1
            fi
        else
            log_warning "Dockerfile not found for $service_name: $dockerfile_path"
        fi
    done
    
    log_success "All cluster services built successfully"
    return 0
}

# Start cluster services
start_cluster_services() {
    log_info "Starting services for cluster: $CLUSTER"
    
    local services="${CLUSTER_SERVICES[$CLUSTER]}"
    IFS=',' read -ra SERVICE_LIST <<< "$services"
    
    for service_info in "${SERVICE_LIST[@]}"; do
        local service_name="${service_info%%:*}"
        local service_port="${service_info#*:}"
        
        log_info "Starting service: $service_name on port $service_port"
        
        # Start service based on cluster type
        case "$CLUSTER" in
            "08-storage-database")
                start_database_service "$service_name" "$service_port"
                ;;
            "09-authentication")
                start_auth_service "$service_name" "$service_port"
                ;;
            "02-blockchain-core")
                start_blockchain_service "$service_name" "$service_port"
                ;;
            "03-session-management")
                start_session_service "$service_name" "$service_port"
                ;;
            "04-rdp-services")
                start_rdp_service "$service_name" "$service_port"
                ;;
            "05-node-management")
                start_node_service "$service_name" "$service_port"
                ;;
            "06-admin-interface")
                start_admin_service "$service_name" "$service_port"
                ;;
            "07-tron-payment")
                start_payment_service "$service_name" "$service_port"
                ;;
            "10-cross-cluster")
                start_mesh_service "$service_name" "$service_port"
                ;;
        esac
    done
    
    log_success "All cluster services started successfully"
    return 0
}

# Service-specific start functions
start_database_service() {
    local service_name="$1"
    local service_port="$2"
    
    case "$service_name" in
        "lucid-mongodb")
            docker run -d --name "$service_name" \
                --network lucid-dev \
                -p "$service_port:$service_port" \
                -e MONGO_INITDB_ROOT_USERNAME=lucid \
                -e MONGO_INITDB_ROOT_PASSWORD=lucid \
                -v lucid-mongo-data:/data/db \
                mongo:7.0 --replSet rs0 --bind_ip_all
            ;;
        "lucid-redis")
            docker run -d --name "$service_name" \
                --network lucid-dev \
                -p "$service_port:$service_port" \
                redis:7.0
            ;;
        "lucid-elasticsearch")
            docker run -d --name "$service_name" \
                --network lucid-dev \
                -p "$service_port:$service_port" \
                -e "discovery.type=single-node" \
                -e "xpack.security.enabled=false" \
                elasticsearch:8.11.0
            ;;
    esac
}

start_auth_service() {
    local service_name="$1"
    local service_port="$2"
    
    docker run -d --name "$service_name" \
        --network lucid-dev \
        -p "$service_port:$service_port" \
        -e LUCID_ENV="$ENVIRONMENT" \
        -e PORT="$service_port" \
        lucid-auth-service:latest
}

start_blockchain_service() {
    local service_name="$1"
    local service_port="$2"
    
    docker run -d --name "$service_name" \
        --network lucid-blockchain \
        -p "$service_port:$service_port" \
        -e LUCID_ENV="$ENVIRONMENT" \
        -e PORT="$service_port" \
        -e BLOCKCHAIN_NETWORK="lucid_blocks" \
        "$service_name:latest"
}

start_session_service() {
    local service_name="$1"
    local service_port="$2"
    
    docker run -d --name "$service_name" \
        --network lucid-dev \
        -p "$service_port:$service_port" \
        -e LUCID_ENV="$ENVIRONMENT" \
        -e PORT="$service_port" \
        "$service_name:latest"
}

start_rdp_service() {
    local service_name="$1"
    local service_port="$2"
    
    docker run -d --name "$service_name" \
        --network lucid-dev \
        -p "$service_port:$service_port" \
        -e LUCID_ENV="$ENVIRONMENT" \
        -e PORT="$service_port" \
        --privileged \
        "$service_name:latest"
}

start_node_service() {
    local service_name="$1"
    local service_port="$2"
    
    docker run -d --name "$service_name" \
        --network lucid-dev \
        -p "$service_port:$service_port" \
        -e LUCID_ENV="$ENVIRONMENT" \
        -e PORT="$service_port" \
        "$service_name:latest"
}

start_admin_service() {
    local service_name="$1"
    local service_port="$2"
    
    docker run -d --name "$service_name" \
        --network lucid-dev \
        -p "$service_port:$service_port" \
        -e LUCID_ENV="$ENVIRONMENT" \
        -e PORT="$service_port" \
        "$service_name:latest"
}

start_payment_service() {
    local service_name="$1"
    local service_port="$2"
    
    docker run -d --name "$service_name" \
        --network lucid-payment \
        -p "$service_port:$service_port" \
        -e LUCID_ENV="$ENVIRONMENT" \
        -e PORT="$service_port" \
        -e TRON_NETWORK="shasta" \
        "$service_name:latest"
}

start_mesh_service() {
    local service_name="$1"
    local service_port="$2"
    
    docker run -d --name "$service_name" \
        --network lucid-dev \
        -p "$service_port:$service_port" \
        -e LUCID_ENV="$ENVIRONMENT" \
        -e PORT="$service_port" \
        "$service_name:latest"
}

# Stop cluster services
stop_cluster_services() {
    log_info "Stopping services for cluster: $CLUSTER"
    
    local services="${CLUSTER_SERVICES[$CLUSTER]}"
    IFS=',' read -ra SERVICE_LIST <<< "$services"
    
    for service_info in "${SERVICE_LIST[@]}"; do
        local service_name="${service_info%%:*}"
        
        log_info "Stopping service: $service_name"
        docker stop "$service_name" 2>/dev/null || true
        docker rm "$service_name" 2>/dev/null || true
    done
    
    log_success "All cluster services stopped successfully"
    return 0
}

# Test cluster services
test_cluster_services() {
    log_info "Testing services for cluster: $CLUSTER"
    
    local services="${CLUSTER_SERVICES[$CLUSTER]}"
    IFS=',' read -ra SERVICE_LIST <<< "$services"
    
    local healthy_count=0
    local total_count=${#SERVICE_LIST[@]}
    
    for service_info in "${SERVICE_LIST[@]}"; do
        local service_name="${service_info%%:*}"
        local service_port="${service_info#*:}"
        
        if test_service_health "$service_name" "$service_port"; then
            log_success "$service_name is healthy"
            ((healthy_count++))
        else
            log_warning "$service_name is unhealthy"
        fi
    done
    
    log_info "$healthy_count/$total_count services are healthy"
    
    if [[ "$healthy_count" -eq "$total_count" ]]; then
        log_success "All cluster services are healthy"
        return 0
    else
        log_warning "Some cluster services are unhealthy"
        return 1
    fi
}

# Test service health
test_service_health() {
    local service_name="$1"
    local service_port="$2"
    
    # Check if container is running
    if ! docker ps --filter "name=$service_name" --format "{{.Names}}" | grep -q "$service_name"; then
        return 1
    fi
    
    # Test port connectivity
    if command -v nc >/dev/null 2>&1; then
        if ! nc -z localhost "$service_port" 2>/dev/null; then
            return 1
        fi
    elif command -v curl >/dev/null 2>&1; then
        if ! curl -f --connect-timeout 5 "http://localhost:$service_port/health" >/dev/null 2>&1; then
            return 1
        fi
    fi
    
    return 0
}

# Show cluster status
show_cluster_status() {
    log_header "Cluster Status: $CLUSTER - ${CLUSTERS[$CLUSTER]}"
    
    # Show Docker containers for this cluster
    echo -e "${YELLOW}Cluster Containers:${NC}"
    local services="${CLUSTER_SERVICES[$CLUSTER]}"
    IFS=',' read -ra SERVICE_LIST <<< "$services"
    
    for service_info in "${SERVICE_LIST[@]}"; do
        local service_name="${service_info%%:*}"
        local service_port="${service_info#*:}"
        
        if docker ps --filter "name=$service_name" --format "{{.Names}}" | grep -q "$service_name"; then
            echo -e "  ${GREEN}[+]${NC} $service_name: RUNNING (port $service_port)"
        else
            echo -e "  ${RED}[-]${NC} $service_name: STOPPED"
        fi
    done
    
    echo
    
    # Show Docker networks
    echo -e "${YELLOW}Docker Networks:${NC}"
    docker network ls --filter "name=lucid" --format "table {{.Name}}\t{{Driver}}\t{{Scope}}"
    
    echo
    
    # Show environment info
    echo -e "${YELLOW}Environment: $ENVIRONMENT${NC}"
    echo -e "Cluster: $CLUSTER"
    echo -e "Lucid Network: ${LUCID_NETWORK:-not set}"
    echo -e "Log Level: ${LUCID_LOG_LEVEL:-not set}"
}

# Clean cluster services
clean_cluster_services() {
    log_info "Cleaning services for cluster: $CLUSTER"
    
    # Stop services
    stop_cluster_services
    
    # Remove images
    local services="${CLUSTER_SERVICES[$CLUSTER]}"
    IFS=',' read -ra SERVICE_LIST <<< "$services"
    
    for service_info in "${SERVICE_LIST[@]}"; do
        local service_name="${service_info%%:*}"
        
        log_info "Removing image: $service_name"
        docker rmi "$service_name:latest" 2>/dev/null || true
    done
    
    # Remove cluster-specific networks
    case "$CLUSTER" in
        "02-blockchain-core")
            docker network rm lucid-blockchain 2>/dev/null || true
            ;;
        "07-tron-payment")
            docker network rm lucid-payment 2>/dev/null || true
            ;;
    esac
    
    log_success "Cluster cleanup completed"
    return 0
}

# Show usage
show_usage() {
    echo "Usage: $0 <cluster> <action> [environment]"
    echo
    echo "Clusters:"
    for cluster in "${!CLUSTERS[@]}"; do
        echo -e "  ${YELLOW}-${NC} $cluster: ${CLUSTERS[$cluster]}"
    done
    echo
    echo "Actions:"
    echo "  deploy    - Deploy cluster (default)"
    echo "  start     - Start cluster services"
    echo "  stop      - Stop cluster services"
    echo "  status    - Show cluster status"
    echo "  test      - Test cluster services"
    echo "  clean     - Clean cluster services"
    echo
    echo "Environment:"
    echo "  dev       - Development environment (default)"
    echo "  test      - Test environment"
    echo "  prod      - Production environment"
}

# Main execution
main() {
    log_header "Lucid Single Cluster Deployment"
    echo -e "${YELLOW}Cluster:${NC} $CLUSTER"
    echo -e "${YELLOW}Action:${NC} $ACTION"
    echo -e "${YELLOW}Environment:${NC} $ENVIRONMENT"
    echo
    
    # Validate cluster
    if ! validate_cluster; then
        exit 1
    fi
    
    # Check prerequisites
    if ! check_prerequisites; then
        exit 1
    fi
    
    # Execute action
    local success=false
    
    case "$ACTION" in
        "deploy")
            if initialize_environment && build_cluster_services && start_cluster_services; then
                success=true
                test_cluster_services || true  # Test but don't fail deployment on test failures
            fi
            ;;
        
        "start")
            if initialize_environment && start_cluster_services; then
                success=true
            fi
            ;;
        
        "stop")
            if stop_cluster_services; then
                success=true
            fi
            ;;
        
        "status")
            show_cluster_status
            success=true
            ;;
        
        "test")
            if test_cluster_services; then
                success=true
            fi
            ;;
        
        "clean")
            if clean_cluster_services; then
                success=true
            fi
            ;;
        
        *)
            log_error "Unknown action: $ACTION"
            show_usage
            exit 1
            ;;
    esac
    
    # Summary
    echo
    if [[ "$success" == "true" ]]; then
        log_header "$ACTION completed successfully for cluster $CLUSTER"
        exit 0
    else
        log_header "$ACTION failed for cluster $CLUSTER"
        exit 1
    fi
}

# Run main function
main "$@"
