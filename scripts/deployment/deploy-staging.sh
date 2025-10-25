#!/bin/bash
# LUCID STAGING DEPLOYMENT SCRIPT
# Deploys Lucid system to staging environment
# Path: /mnt/myssd/Lucid/Lucid/scripts/deployment/deploy-staging.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Global Configuration - Pi Native Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LUCID_ROOT="/mnt/myssd/Lucid/Lucid"
PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"
CONFIGS_DIR="/mnt/myssd/Lucid/Lucid/configs"
ENV_DIR="/mnt/myssd/Lucid/Lucid/configs/environment"
SCRIPTS_DIR="/mnt/myssd/Lucid/Lucid/scripts"
STAGING_DIR="/opt/lucid/staging"
STAGING_ENV="staging"
DOCKER_REGISTRY="ghcr.io/hamigames/lucid"

# Service configuration
declare -A STAGING_SERVICES=(
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

log() { echo -e "${BLUE}[STAGING] $1${NC}"; }
success() { echo -e "${GREEN}[SUCCESS] $1${NC}"; }
warn() { echo -e "${YELLOW}[WARNING] $1${NC}"; }
error() { echo -e "${RED}[ERROR] $1${NC}"; }
section() { echo -e "${BOLD}${CYAN}=== $1 ===${NC}"; }

# Validate staging environment
validate_staging_environment() {
    section "Validating Staging Environment"
    
    log "Checking staging directory: $STAGING_DIR"
    if [ ! -d "$STAGING_DIR" ]; then
        log "Creating staging directory: $STAGING_DIR"
        sudo mkdir -p "$STAGING_DIR"
        sudo chown -R $(whoami):$(whoami) "$STAGING_DIR"
    fi
    
    # Check Docker availability
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    success "✅ Staging environment validated"
}

# Create staging configuration
create_staging_config() {
    section "Creating Staging Configuration"
    
    # Create staging environment file
    log "Creating staging environment configuration"
    cat > "${STAGING_DIR}/.env.staging" << EOF
# LUCID Staging Environment Configuration
LUCID_ENV=staging
LUCID_PLANE=staging
CLUSTER_ID=staging-cluster

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
JWT_SECRET_KEY=staging-jwt-secret-key-change-in-production
ENCRYPTION_KEY=staging-encryption-key-change-in-production
TOR_CONTROL_PASSWORD=staging-tor-password

# Monitoring Configuration
PROMETHEUS_URL=http://lucid-prometheus:9090
GRAFANA_URL=http://lucid-grafana:3000

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_OUTPUT=file

# Performance Configuration
WORKER_PROCESSES=4
MAX_CONNECTIONS=1000
REQUEST_TIMEOUT=30
KEEPALIVE_TIMEOUT=65

# Staging Specific
STAGING_MODE=true
DEBUG_MODE=true
MOCK_EXTERNAL_SERVICES=true
EOF
    
    success "✅ Staging configuration created"
}

# Create staging Docker Compose file
create_staging_compose() {
    section "Creating Staging Docker Compose Configuration"
    
    log "Creating staging docker-compose.yml"
    cat > "${STAGING_DIR}/docker-compose.staging.yml" << 'EOF'
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
      - ./configs/database/mongod.conf:/etc/mongod.conf:ro
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
      - ./configs/database/redis/redis.conf:/usr/local/etc/redis/redis.conf:ro
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
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
      - ./configs/database/elasticsearch/elasticsearch.yml:/usr/share/elasticsearch/config/elasticsearch.yml:ro
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
    image: pickme/lucid-api-gateway:latest-arm64
    container_name: lucid-api-gateway
    ports:
      - "8080:8080"
    environment:
      - LUCID_ENV=staging
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URL=${REDIS_URL}
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
    image: pickme/lucid-blockchain-engine:latest-arm64
    container_name: lucid-blockchain-core
    ports:
      - "8084:8084"
    environment:
      - LUCID_ENV=staging
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URL=${REDIS_URL}
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
    image: pickme/lucid-session-api:latest-arm64
    container_name: lucid-session-management
    ports:
      - "8085:8085"
    environment:
      - LUCID_ENV=staging
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URL=${REDIS_URL}
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
    image: pickme/lucid-rdp:latest-arm64
    container_name: lucid-rdp-services
    ports:
      - "8086:8086"
    environment:
      - LUCID_ENV=staging
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URL=${REDIS_URL}
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
    image: pickme/lucid-node-management:latest-arm64
    container_name: lucid-node-management
    ports:
      - "8087:8087"
    environment:
      - LUCID_ENV=staging
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URL=${REDIS_URL}
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
    image: pickme/lucid-admin-interface:latest-arm64
    container_name: lucid-admin-interface
    ports:
      - "8088:8088"
    environment:
      - LUCID_ENV=staging
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URL=${REDIS_URL}
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
    image: pickme/lucid-auth-service:latest-arm64
    container_name: lucid-auth-service
    ports:
      - "8089:8089"
    environment:
      - LUCID_ENV=staging
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URL=${REDIS_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
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

  # Monitoring Services
  lucid-prometheus:
    image: prom/prometheus:latest
    container_name: lucid-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./configs/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    networks:
      - lucid-staging
    restart: unless-stopped

  lucid-grafana:
    image: grafana/grafana:latest
    container_name: lucid-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./configs/monitoring/grafana:/etc/grafana/provisioning:ro
    networks:
      - lucid-staging
    restart: unless-stopped

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
  prometheus_data:
  grafana_data:
EOF
    
    success "✅ Staging Docker Compose configuration created"
}

# Setup staging directories
setup_staging_directories() {
    section "Setting Up Staging Directories"
    
    log "Creating staging directory structure"
    mkdir -p "${STAGING_DIR}/configs/database"
    mkdir -p "${STAGING_DIR}/configs/monitoring"
    mkdir -p "${STAGING_DIR}/data/mongodb"
    mkdir -p "${STAGING_DIR}/data/redis"
    mkdir -p "${STAGING_DIR}/data/elasticsearch"
    mkdir -p "${STAGING_DIR}/logs"
    mkdir -p "${STAGING_DIR}/backups"
    
    success "✅ Staging directories created"
}

# Deploy staging services
deploy_staging_services() {
    section "Deploying Staging Services"
    
    log "Starting staging services"
    cd "${STAGING_DIR}"
    
    # Load environment variables
    set -a
    source .env.staging
    set +a
    
    # Start services
    docker-compose -f docker-compose.staging.yml up -d
    
    # Wait for services to initialize
    log "Waiting for services to initialize..."
    sleep 30
    
    success "✅ Staging services deployed"
}

# Verify staging deployment
verify_staging_deployment() {
    section "Verifying Staging Deployment"
    
    log "Checking service health"
    cd "${STAGING_DIR}"
    
    # Check all services are running
    local failed_services=""
    
    for service in "${!STAGING_SERVICES[@]}"; do
        local port="${STAGING_SERVICES[$service]}"
        local container_name="lucid-${service}"
        
        if docker ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
            if curl -f "http://localhost:${port}/health" >/dev/null 2>&1; then
                success "✅ ${service}: Healthy"
            else
                warn "⚠️ ${service}: Running but health check failed"
            fi
        else
            error "❌ ${service}: Not running"
            failed_services="${failed_services} ${service}"
        fi
    done
    
    if [ -n "${failed_services}" ]; then
        error "Failed services: ${failed_services}"
        return 1
    fi
    
    success "✅ All staging services are healthy"
}

# Show staging summary
show_staging_summary() {
    section "🎉 Staging Deployment Complete!"
    
    success "Lucid staging environment is running"
    
    echo ""
    log "Staging Access Information:"
    echo "  • Staging Directory: ${STAGING_DIR}"
    echo "  • Environment File: ${STAGING_DIR}/.env.staging"
    echo "  • Compose File: ${STAGING_DIR}/docker-compose.staging.yml"
    
    echo ""
    log "Service Access (Local):"
    for service in "${!STAGING_SERVICES[@]}"; do
        local port="${STAGING_SERVICES[$service]}"
        echo "  • ${service}: http://localhost:${port}"
    done
    
    echo ""
    log "Management Commands:"
    echo "  • Status: cd ${STAGING_DIR} && docker-compose -f docker-compose.staging.yml ps"
    echo "  • Logs: cd ${STAGING_DIR} && docker-compose -f docker-compose.staging.yml logs"
    echo "  • Restart: cd ${STAGING_DIR} && docker-compose -f docker-compose.staging.yml restart"
    echo "  • Stop: cd ${STAGING_DIR} && docker-compose -f docker-compose.staging.yml down"
    echo "  • Update: cd ${STAGING_DIR} && docker-compose -f docker-compose.staging.yml pull && docker-compose -f docker-compose.staging.yml up -d"
}

# Main deployment function
main() {
    section "LUCID STAGING DEPLOYMENT"
    log "Deploying to staging environment"
    log "Staging directory: ${STAGING_DIR}"
    
    validate_staging_environment
    create_staging_config
    create_staging_compose
    setup_staging_directories
    deploy_staging_services
    verify_staging_deployment
    show_staging_summary
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy"|"")
        main
        ;;
    "validate")
        validate_staging_environment
        ;;
    "config")
        create_staging_config
        create_staging_compose
        setup_staging_directories
        ;;
    "start")
        deploy_staging_services
        ;;
    "verify")
        verify_staging_deployment
        ;;
    "status")
        cd "${STAGING_DIR}"
        docker-compose -f docker-compose.staging.yml ps
        ;;
    "logs")
        cd "${STAGING_DIR}"
        docker-compose -f docker-compose.staging.yml logs "${2:-}"
        ;;
    "stop")
        cd "${STAGING_DIR}"
        docker-compose -f docker-compose.staging.yml down
        ;;
    "cleanup")
        cd "${STAGING_DIR}"
        docker-compose -f docker-compose.staging.yml down -v
        sudo rm -rf "${STAGING_DIR}"
        ;;
    *)
        echo "Usage: $0 [deploy|validate|config|start|verify|status|logs [service]|stop|cleanup]"
        echo ""
        echo "Commands:"
        echo "  deploy   - Full staging deployment process"
        echo "  validate - Validate staging environment"
        echo "  config   - Create configuration files only"
        echo "  start    - Start staging services"
        echo "  verify   - Verify staging deployment"
        echo "  status   - Show service status"
        echo "  logs     - Show service logs (optionally for specific service)"
        echo "  stop     - Stop staging services"
        echo "  cleanup  - Remove staging environment"
        exit 1
        ;;
esac
