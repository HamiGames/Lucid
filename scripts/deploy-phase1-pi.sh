#!/bin/bash
# Phase 1 Foundation Services Deployment Script
# Deploys: auth-service, storage-database, mongodb, redis, elasticsearch
# Target: Raspberry Pi 5 (192.168.0.75)
# User: pickme
# Network: lucid-pi-network (bridge, 172.20.0.0/16)

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PI_HOST="pickme@192.168.0.75"
PI_PORT="22"
PI_DEPLOY_PATH="/opt/lucid/production"
REGISTRY="pickme/lucid"
NETWORK_NAME="lucid-pi-network"
NETWORK_SUBNET="172.20.0.0/16"
NETWORK_GATEWAY="172.20.0.1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Setup SSH connection
setup_ssh_connection() {
    log_info "Setting up SSH connection..."
    
    # Test initial connection
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$PI_HOST" "echo 'SSH connection established'" >/dev/null 2>&1; then
        log_success "SSH connection established"
    else
        log_error "Failed to establish SSH connection"
        exit 1
    fi
}

# Cleanup SSH connections
cleanup_ssh_connections() {
    log_info "Cleaning up SSH connections..."
    # No cleanup needed for simple SSH connections
}

# SSH execution function
ssh_exec() {
    local cmd="$1"
    log_info "Executing on Pi: $cmd"
    ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=30 "$PI_HOST" "$cmd" 2>/dev/null
}

# SSH execution function with output capture
ssh_exec_capture() {
    local cmd="$1"
    ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=30 "$PI_HOST" "$cmd" 2>/dev/null
}

# SSH file copy function
ssh_copy() {
    local src="$1"
    local dst="$2"
    log_info "Copying to Pi: $src -> $dst"
    scp -P "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=30 "$src" "$PI_HOST:$dst"
}

# Validate deployment environment
validate_environment() {
    log_info "Validating deployment environment..."
    
    # Check SSH connectivity
    if ! ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$PI_HOST" "echo 'SSH connection successful'" >/dev/null 2>&1; then
        log_error "Cannot connect to Pi via SSH: $PI_HOST"
        exit 1
    fi
    
    # Check Pi architecture
    local pi_arch=$(ssh_exec_capture "uname -m")
    if [[ "$pi_arch" != "aarch64" ]]; then
        log_warning "Pi architecture is $pi_arch, expected aarch64"
    fi
    
    # Check Pi disk space
    local disk_space=$(ssh_exec_capture "df -h / | awk 'NR==2{print \$4}' | sed 's/G.*//'")
    # Clean the output and extract numeric value
    disk_space=$(echo "$disk_space" | tr -d '[:alpha:]' | head -1)
    if [[ "$disk_space" =~ ^[0-9]+$ ]] && [[ "$disk_space" -lt 20 ]]; then
        log_warning "Pi has less than 20GB free space: ${disk_space}GB"
    fi
    
    # Check Docker daemon
    if ! ssh_exec "docker info" >/dev/null 2>&1; then
        log_error "Docker daemon is not running on Pi"
        exit 1
    fi
    
    # Check if user can create directories
    if ! ssh_exec "mkdir -p /tmp/lucid-test && rmdir /tmp/lucid-test" >/dev/null 2>&1; then
        log_warning "User may not have sufficient permissions for directory creation"
    fi
    
    log_success "Environment validation complete"
}

# Create deployment directory on Pi
setup_deployment_directory() {
    log_info "Setting up deployment directory on Pi..."
    
    # Try to create directory structure
    if ! ssh_exec "mkdir -p $PI_DEPLOY_PATH/{configs,logs,data}"; then
        log_error "Failed to create deployment directory"
        log_info "Please run the following commands on the Pi manually:"
        log_info "  sudo mkdir -p $PI_DEPLOY_PATH"
        log_info "  sudo chown -R pickme:pickme $PI_DEPLOY_PATH"
        log_info "  mkdir -p $PI_DEPLOY_PATH/{configs,logs,data}"
        exit 1
    fi
    
    log_success "Deployment directory created: $PI_DEPLOY_PATH"
}

# Create Docker network on Pi
setup_docker_network() {
    log_info "Creating Docker network on Pi..."
    
    # Remove existing network if it exists
    ssh_exec "docker network rm $NETWORK_NAME" 2>/dev/null || true
    
    # Create new network
    ssh_exec "docker network create --driver bridge --attachable --subnet=$NETWORK_SUBNET --gateway=$NETWORK_GATEWAY $NETWORK_NAME"
    
    log_success "Docker network created: $NETWORK_NAME"
}

# Generate environment configuration
generate_environment_config() {
    log_info "Generating environment configuration..."
    
    local env_file="$PROJECT_ROOT/configs/environment/.env.foundation"
    
    # Create configs directory if it doesn't exist
    mkdir -p "$(dirname "$env_file")"
    
    # Generate secure values
    local mongo_password=$(openssl rand -base64 32)
    local redis_password=$(openssl rand -base64 32)
    local jwt_secret=$(openssl rand -base64 64)
    local encryption_key=$(openssl rand -base64 32)
    local tor_password=$(openssl rand -base64 32)
    
    # Create environment file
    cat > "$env_file" << EOF
# Phase 1 Foundation Services Environment Configuration
# Generated on: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Network Configuration
LUCID_NETWORK=$NETWORK_NAME
LUCID_SUBNET=$NETWORK_SUBNET
LUCID_GATEWAY=$NETWORK_GATEWAY

# MongoDB Configuration
MONGODB_ROOT_USERNAME=lucid
MONGODB_ROOT_PASSWORD=$mongo_password
MONGODB_DATABASE=lucid
MONGODB_REPLICA_SET_NAME=lucid-rs
MONGODB_PORT=27017

# Redis Configuration
REDIS_PASSWORD=$redis_password
REDIS_PORT=6379
REDIS_MAXMEMORY=1gb

# Elasticsearch Configuration
ELASTICSEARCH_PASSWORD=$redis_password
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_HEAP_SIZE=1g

# Auth Service Configuration
JWT_SECRET=$jwt_secret
JWT_EXPIRATION_HOURS=24
JWT_REFRESH_EXPIRATION_DAYS=7
ENCRYPTION_KEY=$encryption_key

# TRON Configuration (for auth service)
TRON_NETWORK=mainnet
TRON_API_URL=https://api.trongrid.io

# Security Configuration
TOR_PASSWORD=$tor_password
ENABLE_AUDIT_LOGGING=true
ENABLE_RATE_LIMITING=true

# Service Ports
AUTH_SERVICE_PORT=8089
STORAGE_DATABASE_PORT=8088

# Health Check Configuration
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10
HEALTH_CHECK_RETRIES=3

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE_PATH=/var/log/lucid

# Data Persistence
DATA_VOLUME_PATH=/opt/lucid/data
LOG_VOLUME_PATH=/opt/lucid/logs
EOF
    
    log_success "Environment configuration generated: $env_file"
}

# Create Docker Compose configuration
create_docker_compose() {
    log_info "Creating Docker Compose configuration..."
    
    local compose_file="$PROJECT_ROOT/configs/docker/docker-compose.foundation.yml"
    
    # Create configs directory if it doesn't exist
    mkdir -p "$(dirname "$compose_file")"
    
    cat > "$compose_file" << 'EOF'
version: '3.8'

services:
  # MongoDB Database
  lucid-mongodb:
    image: pickme/lucid-mongodb:latest-arm64
    container_name: lucid-mongodb
    restart: unless-stopped
    ports:
      - "27017:27017"
    environment:
      - MONGO_INITDB_ROOT_USERNAME=${MONGODB_ROOT_USERNAME}
      - MONGO_INITDB_ROOT_PASSWORD=${MONGODB_ROOT_PASSWORD}
      - MONGO_INITDB_DATABASE=${MONGODB_DATABASE}
    volumes:
      - mongodb_data:/data/db
      - mongodb_config:/data/configdb
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Redis Cache
  lucid-redis:
    image: pickme/lucid-redis:latest-arm64
    container_name: lucid-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "redis-cli", "--no-auth-warning", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  # Elasticsearch Search Engine
  lucid-elasticsearch:
    image: pickme/lucid-elasticsearch:latest-arm64
    container_name: lucid-elasticsearch
    restart: unless-stopped
    ports:
      - "9200:9200"
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms${ELASTICSEARCH_HEAP_SIZE} -Xmx${ELASTICSEARCH_HEAP_SIZE}"
      - xpack.security.enabled=true
      - ELASTIC_PASSWORD=${ELASTICSEARCH_PASSWORD}
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9200/_cluster/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # Auth Service
  lucid-auth-service:
    image: pickme/lucid-auth-service:latest-arm64
    container_name: lucid-auth-service
    restart: unless-stopped
    ports:
      - "8089:8089"
    environment:
      - JWT_SECRET=${JWT_SECRET}
      - JWT_EXPIRATION_HOURS=${JWT_EXPIRATION_HOURS}
      - JWT_REFRESH_EXPIRATION_DAYS=${JWT_REFRESH_EXPIRATION_DAYS}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - MONGODB_URL=mongodb://${MONGODB_ROOT_USERNAME}:${MONGODB_ROOT_PASSWORD}@lucid-mongodb:27017/${MONGODB_DATABASE}?authSource=admin
      - REDIS_URL=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0
      - TRON_NETWORK=${TRON_NETWORK}
      - TRON_API_URL=${TRON_API_URL}
      - ENABLE_AUDIT_LOGGING=${ENABLE_AUDIT_LOGGING}
      - ENABLE_RATE_LIMITING=${ENABLE_RATE_LIMITING}
      - LOG_LEVEL=${LOG_LEVEL}
    volumes:
      - auth_logs:/var/log/lucid/auth
    networks:
      - lucid-pi-network
    depends_on:
      lucid-mongodb:
        condition: service_healthy
      lucid-redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8089/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # Storage Database Service
  lucid-storage-database:
    image: pickme/lucid-storage-database:latest-arm64
    container_name: lucid-storage-database
    restart: unless-stopped
    ports:
      - "8088:8088"
    environment:
      - MONGODB_URL=mongodb://${MONGODB_ROOT_USERNAME}:${MONGODB_ROOT_PASSWORD}@lucid-mongodb:27017/${MONGODB_DATABASE}?authSource=admin
      - REDIS_URL=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0
      - ELASTICSEARCH_URL=http://lucid-elasticsearch:9200
      - ELASTICSEARCH_PASSWORD=${ELASTICSEARCH_PASSWORD}
      - LOG_LEVEL=${LOG_LEVEL}
    volumes:
      - storage_logs:/var/log/lucid/storage
    networks:
      - lucid-pi-network
    depends_on:
      lucid-mongodb:
        condition: service_healthy
      lucid-redis:
        condition: service_healthy
      lucid-elasticsearch:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8088/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

volumes:
  mongodb_data:
    driver: local
  mongodb_config:
    driver: local
  redis_data:
    driver: local
  elasticsearch_data:
    driver: local
  auth_logs:
    driver: local
  storage_logs:
    driver: local

networks:
  lucid-pi-network:
    external: true
EOF
    
    log_success "Docker Compose configuration created: $compose_file"
}

# Deploy configuration files to Pi
deploy_configurations() {
    log_info "Deploying configuration files to Pi..."
    
    local env_file="$PROJECT_ROOT/configs/environment/.env.foundation"
    local compose_file="$PROJECT_ROOT/configs/docker/docker-compose.foundation.yml"
    
    # Copy environment file
    ssh_copy "$env_file" "$PI_DEPLOY_PATH/.env.foundation"
    
    # Copy Docker Compose file
    ssh_copy "$compose_file" "$PI_DEPLOY_PATH/docker-compose.foundation.yml"
    
    log_success "Configuration files deployed to Pi"
}

# Pull images on Pi
pull_images() {
    log_info "Pulling images on Pi..."
    
    local images=(
        "$REGISTRY/lucid-mongodb:latest-arm64"
        "$REGISTRY/lucid-redis:latest-arm64"
        "$REGISTRY/lucid-elasticsearch:latest-arm64"
        "$REGISTRY/lucid-auth-service:latest-arm64"
        "$REGISTRY/lucid-storage-database:latest-arm64"
    )
    
    for image in "${images[@]}"; do
        log_info "Pulling image: $image"
        ssh_exec "docker pull $image"
    done
    
    log_success "All images pulled successfully"
}

# Deploy services
deploy_services() {
    log_info "Deploying Phase 1 services..."
    
    ssh_exec "cd $PI_DEPLOY_PATH && docker-compose -f docker-compose.foundation.yml up -d"
    
    log_success "Phase 1 services deployed"
}

# Wait for services to be healthy
wait_for_health() {
    log_info "Waiting for services to be healthy..."
    
    local max_wait=300  # 5 minutes
    local wait_time=0
    local interval=10
    
    while [[ $wait_time -lt $max_wait ]]; do
        local healthy_count=$(ssh_exec_capture "cd $PI_DEPLOY_PATH && docker-compose -f docker-compose.foundation.yml ps --filter 'health=healthy' --format 'table {{.Name}}' | tail -n +2 | wc -l")
        local total_services=5
        
        if [[ "$healthy_count" -eq "$total_services" ]]; then
            log_success "All services are healthy"
            return 0
        fi
        
        log_info "Waiting for services... ($healthy_count/$total_services healthy)"
        sleep $interval
        wait_time=$((wait_time + interval))
    done
    
    log_error "Timeout waiting for services to be healthy"
    ssh_exec "cd $PI_DEPLOY_PATH && docker-compose -f docker-compose.foundation.yml ps"
    exit 1
}

# Initialize MongoDB replica set
initialize_mongodb() {
    log_info "Initializing MongoDB replica set..."
    
    ssh_exec "docker exec lucid-mongodb mongosh --eval 'rs.initiate({_id: \"lucid-rs\", members: [{_id: 0, host: \"localhost:27017\"}]})'"
    
    # Wait for replica set to be ready
    sleep 10
    
    log_success "MongoDB replica set initialized"
}

# Create Elasticsearch index
create_elasticsearch_index() {
    log_info "Creating Elasticsearch index..."
    
    ssh_exec "curl -X PUT 'http://localhost:9200/lucid-sessions' -H 'Content-Type: application/json' -d '{\"mappings\":{\"properties\":{\"session_id\":{\"type\":\"keyword\"},\"timestamp\":{\"type\":\"date\"},\"content\":{\"type\":\"text\"}}}}'"
    
    log_success "Elasticsearch index created"
}

# Display deployment status
show_deployment_status() {
    log_info "Phase 1 deployment status:"
    
    ssh_exec "cd $PI_DEPLOY_PATH && docker-compose -f docker-compose.foundation.yml ps"
    
    log_info "Service endpoints:"
    log_info "  - MongoDB: mongodb://lucid:****@192.168.0.75:27017/lucid"
    log_info "  - Redis: redis://:****@192.168.0.75:6379"
    log_info "  - Elasticsearch: http://192.168.0.75:9200"
    log_info "  - Auth Service: http://192.168.0.75:8089"
    log_info "  - Storage Database: http://192.168.0.75:8088"
}

# Main execution
main() {
    log_info "Starting Phase 1 Foundation Services Deployment"
    log_info "Target Pi: $PI_HOST"
    log_info "Deploy Path: $PI_DEPLOY_PATH"
    log_info "Network: $NETWORK_NAME ($NETWORK_SUBNET)"
    
    # Setup SSH connection
    setup_ssh_connection
    
    # Validate environment
    validate_environment
    
    # Setup deployment
    setup_deployment_directory
    setup_docker_network
    
    # Generate and deploy configurations
    generate_environment_config
    create_docker_compose
    deploy_configurations
    
    # Deploy services
    pull_images
    deploy_services
    
    # Wait for health and initialize
    wait_for_health
    initialize_mongodb
    create_elasticsearch_index
    
    # Show status
    show_deployment_status
    
    # Cleanup SSH connections
    cleanup_ssh_connections
    
    log_success "Phase 1 Foundation Services deployment completed successfully!"
}

# Set up trap to cleanup SSH connections on exit
trap cleanup_ssh_connections EXIT INT TERM

# Run main function
main "$@"
