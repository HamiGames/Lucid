#!/bin/bash
# LUCID RASPBERRY PI DEPLOYMENT SCRIPT
# Deploys Lucid system to Raspberry Pi with staging environment
# Path: scripts/deployment/deploy-pi.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LUCID_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PI_HOST="pickme@192.168.0.75"
PI_DEPLOY_DIR="/opt/lucid/staging"
DOCKER_REGISTRY="ghcr.io/hamigames/lucid"

# Pi-specific service configuration
declare -A PI_SERVICES=(
    ["api-gateway"]="8080"
    ["blockchain-core"]="8084"
    ["session-management"]="8085"
    ["rdp-services"]="8086"
    ["node-management"]="8087"
    ["admin-interface"]="8088"
    ["auth-service"]="8089"
    ["database"]="27017"
    ["redis"]="6379"
    ["elasticsearch"]="9200"
)

log() { echo -e "${BLUE}[PI-DEPLOY] $1${NC}"; }
success() { echo -e "${GREEN}[SUCCESS] $1${NC}"; }
warn() { echo -e "${YELLOW}[WARNING] $1${NC}"; }
error() { echo -e "${RED}[ERROR] $1${NC}"; }
section() { echo -e "${BOLD}${CYAN}=== $1 ===${NC}"; }

# Test SSH connectivity to Pi
test_pi_connection() {
    section "Testing Pi Connection"
    
    log "Testing SSH connection to $PI_HOST"
    if ssh -o ConnectTimeout=10 -o BatchMode=yes "$PI_HOST" "echo 'Pi connection successful'" 2>/dev/null; then
        success "✅ SSH connection to Pi verified"
    else
        error "❌ Cannot connect to Pi via SSH: $PI_HOST"
        error "Please ensure:"
        error "  - Pi is powered on and connected to network"
        error "  - SSH key is properly configured"
        error "  - Network connectivity to 192.168.0.75 exists"
        exit 1
    fi
    
    # Check Docker on Pi
    log "Verifying Docker on Pi"
    if ssh "$PI_HOST" "docker --version" >/dev/null 2>&1; then
        success "✅ Docker verified on Pi"
        
        # Show Pi system info
        PI_ARCH=$(ssh "$PI_HOST" "uname -m")
        PI_OS=$(ssh "$PI_HOST" "cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2" | tr -d '"')
        log "Pi Architecture: $PI_ARCH"
        log "Pi OS: $PI_OS"
        
        if [[ "$PI_ARCH" != "aarch64" ]] && [[ "$PI_ARCH" != "armv7l" ]]; then
            warn "⚠️ Unexpected Pi architecture: $PI_ARCH"
        fi
    else
        error "❌ Docker not found on Pi"
        exit 1
    fi
}

# Transfer staging files to Pi
transfer_staging_files() {
    section "Transferring Staging Files to Pi"
    
    # Create staging directory on Pi
    log "Creating staging directory on Pi: $PI_DEPLOY_DIR"
    ssh "$PI_HOST" "sudo mkdir -p $PI_DEPLOY_DIR && sudo chown -R pickme:pickme $PI_DEPLOY_DIR"
    
    # Transfer staging deployment script
    log "Transferring staging deployment script"
    scp "${LUCID_ROOT}/scripts/deployment/deploy-staging.sh" "$PI_HOST:$PI_DEPLOY_DIR/"
    ssh "$PI_HOST" "chmod +x $PI_DEPLOY_DIR/deploy-staging.sh"
    success "✅ Staging deployment script transferred"
    
    # Transfer Docker Compose files
    log "Transferring Docker Compose configurations"
    if [ -f "${LUCID_ROOT}/configs/docker/docker-compose.staging.yml" ]; then
        scp "${LUCID_ROOT}/configs/docker/docker-compose.staging.yml" "$PI_HOST:$PI_DEPLOY_DIR/"
    else
        # Create basic staging compose file
        create_pi_staging_compose
    fi
    
    # Transfer environment configuration
    log "Creating Pi-specific environment configuration"
    create_pi_environment_config
    
    success "✅ Staging files transferred to Pi"
}

# Create Pi-specific staging compose file
create_pi_staging_compose() {
    log "Creating Pi-specific staging Docker Compose file"
    
    cat > "/tmp/pi-staging-compose.yml" << 'EOF'
version: '3.8'

services:
  # Database Services
  lucid-mongodb:
    image: mongo:7.0
    container_name: lucid-mongodb
    environment:
      MONGO_INITDB_ROOT_USERNAME: lucid
      MONGO_INITDB_ROOT_PASSWORD: lucid
      MONGO_INITDB_DATABASE: lucid
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
    networks:
      - lucid-staging
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.runCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-redis:
    image: redis:7.0-alpine
    container_name: lucid-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - lucid-staging
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-elasticsearch:
    image: elasticsearch:8.11.0
    container_name: lucid-elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms256m -Xmx256m"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    networks:
      - lucid-staging
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9200/_cluster/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Core Services
  lucid-api-gateway:
    image: ghcr.io/hamigames/lucid/api-gateway:latest
    container_name: lucid-api-gateway
    ports:
      - "8080:8080"
    environment:
      - LUCID_ENV=staging
      - MONGODB_URI=mongodb://lucid:lucid@lucid-mongodb:27017/lucid?authSource=admin
      - REDIS_URL=redis://lucid-redis:6379/0
    depends_on:
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-staging
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-blockchain-core:
    image: ghcr.io/hamigames/lucid/blockchain-core:latest
    container_name: lucid-blockchain-core
    ports:
      - "8084:8084"
    environment:
      - LUCID_ENV=staging
      - MONGODB_URI=mongodb://lucid:lucid@lucid-mongodb:27017/lucid?authSource=admin
      - REDIS_URL=redis://lucid-redis:6379/0
    depends_on:
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-staging
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8084/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-session-management:
    image: ghcr.io/hamigames/lucid/session-management:latest
    container_name: lucid-session-management
    ports:
      - "8085:8085"
    environment:
      - LUCID_ENV=staging
      - MONGODB_URI=mongodb://lucid:lucid@lucid-mongodb:27017/lucid?authSource=admin
      - REDIS_URL=redis://lucid-redis:6379/0
    depends_on:
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-staging
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8085/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-rdp-services:
    image: ghcr.io/hamigames/lucid/rdp-services:latest
    container_name: lucid-rdp-services
    ports:
      - "8086:8086"
    environment:
      - LUCID_ENV=staging
      - MONGODB_URI=mongodb://lucid:lucid@lucid-mongodb:27017/lucid?authSource=admin
      - REDIS_URL=redis://lucid-redis:6379/0
    depends_on:
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-staging
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8086/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-node-management:
    image: ghcr.io/hamigames/lucid/node-management:latest
    container_name: lucid-node-management
    ports:
      - "8087:8087"
    environment:
      - LUCID_ENV=staging
      - MONGODB_URI=mongodb://lucid:lucid@lucid-mongodb:27017/lucid?authSource=admin
      - REDIS_URL=redis://lucid-redis:6379/0
    depends_on:
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-staging
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8087/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-admin-interface:
    image: ghcr.io/hamigames/lucid/admin-interface:latest
    container_name: lucid-admin-interface
    ports:
      - "8088:8088"
    environment:
      - LUCID_ENV=staging
      - MONGODB_URI=mongodb://lucid:lucid@lucid-mongodb:27017/lucid?authSource=admin
      - REDIS_URL=redis://lucid-redis:6379/0
    depends_on:
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-staging
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8088/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  lucid-auth-service:
    image: ghcr.io/hamigames/lucid/auth-service:latest
    container_name: lucid-auth-service
    ports:
      - "8089:8089"
    environment:
      - LUCID_ENV=staging
      - MONGODB_URI=mongodb://lucid:lucid@lucid-mongodb:27017/lucid?authSource=admin
      - REDIS_URL=redis://lucid-redis:6379/0
      - JWT_SECRET_KEY=pi-staging-jwt-secret-key
    depends_on:
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-staging
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8089/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  lucid-staging:
    driver: bridge
    ipam:
      config:
        - subnet: 172.22.0.0/16

volumes:
  mongodb_data:
  redis_data:
  elasticsearch_data:
EOF
    
    scp "/tmp/pi-staging-compose.yml" "$PI_HOST:$PI_DEPLOY_DIR/docker-compose.staging.yml"
    rm "/tmp/pi-staging-compose.yml"
    success "✅ Pi staging Docker Compose file created"
}

# Create Pi environment configuration
create_pi_environment_config() {
    log "Creating Pi-specific environment configuration"
    
    cat > "/tmp/pi-staging.env" << EOF
# LUCID Pi Staging Environment Configuration
LUCID_ENV=staging
LUCID_PLANE=staging
CLUSTER_ID=pi-staging-cluster

# Network Configuration
LUCID_NETWORK=lucid-staging
LUCID_SUBNET=172.22.0.0/16

# Database Configuration
MONGODB_URI=mongodb://lucid:lucid@lucid-mongodb:27017/lucid?authSource=admin&retryWrites=false
REDIS_URL=redis://lucid-redis:6379/0
ELASTICSEARCH_URL=http://lucid-elasticsearch:9200

# Service URLs
API_GATEWAY_URL=http://lucid-api-gateway:8080
BLOCKCHAIN_CORE_URL=http://lucid-blockchain-core:8084
SESSION_MANAGEMENT_URL=http://lucid-session-management:8085
RDP_SERVICES_URL=http://lucid-rdp-services:8086
NODE_MANAGEMENT_URL=http://lucid-node-management:8087
ADMIN_INTERFACE_URL=http://lucid-admin-interface:8088
AUTH_SERVICE_URL=http://lucid-auth-service:8089

# Security Configuration
JWT_SECRET_KEY=pi-staging-jwt-secret-key
ENCRYPTION_KEY=pi-staging-encryption-key
TOR_CONTROL_PASSWORD=pi-staging-tor-password

# Pi-specific Configuration
PI_DEPLOYMENT=true
PI_ARCHITECTURE=aarch64
PI_OPTIMIZATION=true
RESOURCE_LIMITS=true

# Performance Configuration (Pi-optimized)
WORKER_PROCESSES=2
MAX_CONNECTIONS=500
REQUEST_TIMEOUT=60
KEEPALIVE_TIMEOUT=120

# Staging Specific
STAGING_MODE=true
DEBUG_MODE=true
MOCK_EXTERNAL_SERVICES=true
EOF
    
    scp "/tmp/pi-staging.env" "$PI_HOST:$PI_DEPLOY_DIR/.env.staging"
    rm "/tmp/pi-staging.env"
    success "✅ Pi environment configuration created"
}

# Setup Pi networking
setup_pi_networking() {
    section "Setting Up Pi Networking"
    
    log "Creating lucid-staging network on Pi"
    ssh "$PI_HOST" "docker network create lucid-staging --driver bridge --subnet 172.22.0.0/16 --attachable 2>/dev/null || echo 'Network already exists'"
    
    success "✅ Pi networking configured"
}

# Create Pi data directories
setup_pi_directories() {
    section "Setting Up Pi Directories"
    
    log "Creating data directories on Pi"
    ssh "$PI_HOST" "mkdir -p $PI_DEPLOY_DIR/{data,logs,backups,configs}"
    ssh "$PI_HOST" "mkdir -p $PI_DEPLOY_DIR/data/{mongodb,redis,elasticsearch}"
    
    # Set proper permissions
    ssh "$PI_HOST" "sudo chown -R pickme:pickme $PI_DEPLOY_DIR"
    
    success "✅ Pi directories created"
}

# Pull Docker images on Pi
pull_pi_images() {
    section "Pulling Docker Images on Pi"
    
    log "Logging into GitHub Container Registry on Pi"
    ssh "$PI_HOST" "echo '$GITHUB_TOKEN' | docker login ghcr.io -u $GITHUB_ACTOR --password-stdin" || {
        warn "⚠️ GitHub token not available, using public images"
    }
    
    # Pull database images
    log "Pulling database images"
    ssh "$PI_HOST" "docker pull mongo:7.0"
    ssh "$PI_HOST" "docker pull redis:7.0-alpine"
    ssh "$PI_HOST" "docker pull elasticsearch:8.11.0"
    
    # Pull Lucid service images
    for service in "${!PI_SERVICES[@]}"; do
        if [[ "$service" != "database" && "$service" != "redis" && "$service" != "elasticsearch" ]]; then
            log "Pulling $service image"
            ssh "$PI_HOST" "docker pull $DOCKER_REGISTRY/$service:latest" || {
                warn "⚠️ Failed to pull $service image, will use local build"
            }
        fi
    done
    
    success "✅ Docker images pulled on Pi"
}

# Deploy staging services on Pi
deploy_pi_staging_services() {
    section "Deploying Staging Services on Pi"
    
    log "Starting staging services on Pi"
    ssh "$PI_HOST" "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml up -d"
    
    # Wait for services to initialize
    log "Waiting for services to initialize..."
    sleep 45
    
    # Check service status
    log "Checking service status on Pi"
    ssh "$PI_HOST" "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml ps"
    
    success "✅ Staging services deployed on Pi"
}

# Verify Pi deployment
verify_pi_deployment() {
    section "Verifying Pi Deployment"
    
    log "Running health checks on Pi"
    ssh "$PI_HOST" "cd $PI_DEPLOY_DIR && ./deploy-staging.sh verify"
    
    success "✅ Pi deployment verification complete"
}

# Show Pi deployment summary
show_pi_summary() {
    section "🎉 Pi Staging Deployment Complete!"
    
    success "Lucid staging environment is running on Raspberry Pi"
    
    echo ""
    log "Pi Access Information:"
    echo "  • SSH: ssh $PI_HOST"
    echo "  • Staging Directory: $PI_DEPLOY_DIR"
    echo "  • Environment File: $PI_DEPLOY_DIR/.env.staging"
    echo "  • Compose File: $PI_DEPLOY_DIR/docker-compose.staging.yml"
    
    echo ""
    log "Service Access (from Pi):"
    for service in "${!PI_SERVICES[@]}"; do
        local port="${PI_SERVICES[$service]}"
        echo "  • ${service}: http://localhost:${port}"
    done
    
    echo ""
    log "Management Commands:"
    echo "  • Status: ssh $PI_HOST 'cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml ps'"
    echo "  • Logs: ssh $PI_HOST 'cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml logs'"
    echo "  • Restart: ssh $PI_HOST 'cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml restart'"
    echo "  • Stop: ssh $PI_HOST 'cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml down'"
    echo "  • Update: ssh $PI_HOST 'cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml pull && docker-compose -f docker-compose.staging.yml up -d'"
}

# Main deployment function
main() {
    section "LUCID PI STAGING DEPLOYMENT"
    log "Deploying to Pi: $PI_HOST"
    log "Staging directory: $PI_DEPLOY_DIR"
    
    test_pi_connection
    transfer_staging_files
    setup_pi_networking
    setup_pi_directories
    pull_pi_images
    deploy_pi_staging_services
    verify_pi_deployment
    show_pi_summary
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy"|"")
        main
        ;;
    "test-connection")
        test_pi_connection
        ;;
    "transfer")
        transfer_staging_files
        ;;
    "setup")
        setup_pi_networking
        setup_pi_directories
        ;;
    "pull")
        pull_pi_images
        ;;
    "start")
        deploy_pi_staging_services
        ;;
    "verify")
        verify_pi_deployment
        ;;
    "status")
        ssh "$PI_HOST" "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml ps"
        ;;
    "logs")
        ssh "$PI_HOST" "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml logs ${2:-}"
        ;;
    "stop")
        ssh "$PI_HOST" "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml down"
        ;;
    "cleanup")
        ssh "$PI_HOST" "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml down -v"
        ssh "$PI_HOST" "sudo rm -rf $PI_DEPLOY_DIR"
        ;;
    *)
        echo "Usage: $0 [deploy|test-connection|transfer|setup|pull|start|verify|status|logs [service]|stop|cleanup]"
        echo ""
        echo "Commands:"
        echo "  deploy         - Full Pi staging deployment process"
        echo "  test-connection - Test SSH connection to Pi"
        echo "  transfer       - Transfer staging files to Pi only"
        echo "  setup          - Setup Pi networking and directories"
        echo "  pull          - Pull Docker images on Pi only"
        echo "  start         - Start staging services on Pi"
        echo "  verify        - Verify Pi deployment"
        echo "  status        - Show service status on Pi"
        echo "  logs          - Show service logs (optionally for specific service)"
        echo "  stop          - Stop staging services on Pi"
        echo "  cleanup       - Remove Pi staging environment"
        exit 1
        ;;
esac
