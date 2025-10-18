#!/bin/bash
# LUCID SSH-BASED PI DEPLOYMENT SCRIPT
# Automated SSH deployment to Raspberry Pi with comprehensive error handling
# Path: scripts/deployment/ssh-deploy-pi.sh

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
PI_HOST="${PI_HOST:-pickme@192.168.0.75}"
PI_DEPLOY_DIR="${PI_DEPLOY_DIR:-/opt/lucid/staging}"
SSH_KEY="${SSH_KEY:-~/.ssh/id_rsa}"
SSH_TIMEOUT="${SSH_TIMEOUT:-30}"
DEPLOYMENT_ID="deploy-$(date +%Y%m%d-%H%M%S)"

# SSH Configuration
SSH_OPTS="-o ConnectTimeout=$SSH_TIMEOUT -o BatchMode=yes -o StrictHostKeyChecking=no"
SSH_CMD="ssh $SSH_OPTS -i $SSH_KEY $PI_HOST"
SCP_CMD="scp $SSH_OPTS -i $SSH_KEY"

log() { echo -e "${BLUE}[SSH-DEPLOY] $1${NC}"; }
success() { echo -e "${GREEN}[SUCCESS] $1${NC}"; }
warn() { echo -e "${YELLOW}[WARNING] $1${NC}"; }
error() { echo -e "${RED}[ERROR] $1${NC}"; }
section() { echo -e "${BOLD}${CYAN}=== $1 ===${NC}"; }

# Validate SSH connection and Pi environment
validate_ssh_connection() {
    section "Validating SSH Connection"
    
    log "Testing SSH connection to $PI_HOST"
    if $SSH_CMD "echo 'SSH connection successful'" 2>/dev/null; then
        success "✅ SSH connection to Pi verified"
    else
        error "❌ Cannot connect to Pi via SSH: $PI_HOST"
        error "Please ensure:"
        error "  - Pi is powered on and connected to network"
        error "  - SSH key ($SSH_KEY) is properly configured"
        error "  - Network connectivity to Pi exists"
        error "  - SSH service is running on Pi"
        exit 1
    fi
    
    # Check Pi system requirements
    log "Checking Pi system requirements"
    $SSH_CMD "docker --version && docker-compose --version" >/dev/null 2>&1 || {
        error "❌ Docker or Docker Compose not found on Pi"
        error "Please install Docker and Docker Compose on the Pi"
        exit 1
    }
    
    # Get Pi system information
    PI_ARCH=$($SSH_CMD "uname -m")
    PI_OS=$($SSH_CMD "cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2" | tr -d '"')
    PI_MEM=$($SSH_CMD "free -h | grep '^Mem:' | awk '{print \$2}'")
    PI_DISK=$($SSH_CMD "df -h / | tail -1 | awk '{print \$4}'")
    
    log "Pi System Information:"
    log "  Architecture: $PI_ARCH"
    log "  OS: $PI_OS"
    log "  Memory: $PI_MEM"
    log "  Available Disk: $PI_DISK"
    
    # Check if architecture is supported
    if [[ "$PI_ARCH" != "aarch64" ]] && [[ "$PI_ARCH" != "armv7l" ]]; then
        warn "⚠️ Unexpected Pi architecture: $PI_ARCH"
        warn "This may cause compatibility issues"
    fi
    
    success "✅ Pi system requirements validated"
}

# Create deployment directory structure on Pi
setup_pi_directories() {
    section "Setting Up Pi Directories"
    
    log "Creating deployment directory structure on Pi"
    $SSH_CMD "sudo mkdir -p $PI_DEPLOY_DIR/{configs,data,logs,backups,scripts}"
    $SSH_CMD "sudo mkdir -p $PI_DEPLOY_DIR/data/{mongodb,redis,elasticsearch,prometheus,grafana}"
    $SSH_CMD "sudo mkdir -p $PI_DEPLOY_DIR/logs/{api-gateway,blockchain,session,rdp,node,admin,auth,database}"
    $SSH_CMD "sudo mkdir -p $PI_DEPLOY_DIR/configs/{database,monitoring,services}"
    
    # Set proper permissions
    $SSH_CMD "sudo chown -R pickme:pickme $PI_DEPLOY_DIR"
    $SSH_CMD "sudo chmod -R 755 $PI_DEPLOY_DIR"
    
    success "✅ Pi directory structure created"
}

# Transfer deployment files to Pi
transfer_deployment_files() {
    section "Transferring Deployment Files"
    
    log "Transferring core deployment files"
    
    # Transfer staging deployment script
    if [ -f "${LUCID_ROOT}/scripts/deployment/deploy-staging.sh" ]; then
        $SCP_CMD "${LUCID_ROOT}/scripts/deployment/deploy-staging.sh" "$PI_HOST:$PI_DEPLOY_DIR/"
        $SSH_CMD "chmod +x $PI_DEPLOY_DIR/deploy-staging.sh"
        success "✅ Staging deployment script transferred"
    fi
    
    # Transfer Pi deployment script
    if [ -f "${LUCID_ROOT}/scripts/deployment/deploy-pi.sh" ]; then
        $SCP_CMD "${LUCID_ROOT}/scripts/deployment/deploy-pi.sh" "$PI_HOST:$PI_DEPLOY_DIR/"
        $SSH_CMD "chmod +x $PI_DEPLOY_DIR/deploy-pi.sh"
        success "✅ Pi deployment script transferred"
    fi
    
    # Transfer Docker Compose files
    if [ -f "${LUCID_ROOT}/configs/docker/docker-compose.staging.yml" ]; then
        $SCP_CMD "${LUCID_ROOT}/configs/docker/docker-compose.staging.yml" "$PI_HOST:$PI_DEPLOY_DIR/"
        success "✅ Docker Compose configuration transferred"
    else
        # Create basic staging compose file on Pi
        create_pi_compose_file
    fi
    
    # Transfer environment configuration
    create_pi_environment_file
    
    # Transfer monitoring configurations
    transfer_monitoring_configs
    
    success "✅ All deployment files transferred"
}

# Create Pi-specific Docker Compose file
create_pi_compose_file() {
    log "Creating Pi-specific Docker Compose file"
    
    cat > "/tmp/pi-compose.yml" << 'EOF'
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
      - ./logs/database:/var/log/mongodb
    networks:
      - lucid-staging
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.runCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  lucid-redis:
    image: redis:7.0-alpine
    container_name: lucid-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      - ./logs/redis:/var/log/redis
    networks:
      - lucid-staging
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

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
      - ./logs/elasticsearch:/usr/share/elasticsearch/logs
    networks:
      - lucid-staging
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9200/_cluster/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

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
    volumes:
      - ./logs/api-gateway:/app/logs
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
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  lucid-blockchain-core:
    image: ghcr.io/hamigames/lucid/blockchain-core:latest
    container_name: lucid-blockchain-core
    ports:
      - "8084:8084"
    environment:
      - LUCID_ENV=staging
      - MONGODB_URI=mongodb://lucid:lucid@lucid-mongodb:27017/lucid?authSource=admin
      - REDIS_URL=redis://lucid-redis:6379/0
    volumes:
      - ./logs/blockchain:/app/logs
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
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  lucid-session-management:
    image: ghcr.io/hamigames/lucid/session-management:latest
    container_name: lucid-session-management
    ports:
      - "8085:8085"
    environment:
      - LUCID_ENV=staging
      - MONGODB_URI=mongodb://lucid:lucid@lucid-mongodb:27017/lucid?authSource=admin
      - REDIS_URL=redis://lucid-redis:6379/0
    volumes:
      - ./logs/session:/app/logs
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
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  lucid-rdp-services:
    image: ghcr.io/hamigames/lucid/rdp-services:latest
    container_name: lucid-rdp-services
    ports:
      - "8086:8086"
    environment:
      - LUCID_ENV=staging
      - MONGODB_URI=mongodb://lucid:lucid@lucid-mongodb:27017/lucid?authSource=admin
      - REDIS_URL=redis://lucid-redis:6379/0
    volumes:
      - ./logs/rdp:/app/logs
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
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  lucid-node-management:
    image: ghcr.io/hamigames/lucid/node-management:latest
    container_name: lucid-node-management
    ports:
      - "8087:8087"
    environment:
      - LUCID_ENV=staging
      - MONGODB_URI=mongodb://lucid:lucid@lucid-mongodb:27017/lucid?authSource=admin
      - REDIS_URL=redis://lucid-redis:6379/0
    volumes:
      - ./logs/node:/app/logs
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
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  lucid-admin-interface:
    image: ghcr.io/hamigames/lucid/admin-interface:latest
    container_name: lucid-admin-interface
    ports:
      - "8088:8088"
    environment:
      - LUCID_ENV=staging
      - MONGODB_URI=mongodb://lucid:lucid@lucid-mongodb:27017/lucid?authSource=admin
      - REDIS_URL=redis://lucid-redis:6379/0
    volumes:
      - ./logs/admin:/app/logs
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
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

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
    volumes:
      - ./logs/auth:/app/logs
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
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  # Monitoring Services
  lucid-prometheus:
    image: prom/prometheus:latest
    container_name: lucid-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./configs/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
      - ./logs/prometheus:/var/log/prometheus
    networks:
      - lucid-staging
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 128M
        reservations:
          memory: 64M

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
      - ./logs/grafana:/var/log/grafana
    networks:
      - lucid-staging
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 128M
        reservations:
          memory: 64M

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
    
    $SCP_CMD "/tmp/pi-compose.yml" "$PI_HOST:$PI_DEPLOY_DIR/docker-compose.staging.yml"
    rm "/tmp/pi-compose.yml"
    success "✅ Pi Docker Compose file created"
}

# Create Pi environment configuration
create_pi_environment_file() {
    log "Creating Pi environment configuration"
    
    cat > "/tmp/pi-env" << EOF
# LUCID Pi Staging Environment Configuration
LUCID_ENV=staging
LUCID_PLANE=staging
CLUSTER_ID=pi-staging-cluster
DEPLOYMENT_ID=$DEPLOYMENT_ID

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
JWT_SECRET_KEY=pi-staging-jwt-secret-key-$(date +%s)
ENCRYPTION_KEY=pi-staging-encryption-key-$(date +%s)
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

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_OUTPUT=file
LOG_ROTATION=true
LOG_MAX_SIZE=100M
LOG_MAX_FILES=5

# Staging Specific
STAGING_MODE=true
DEBUG_MODE=true
MOCK_EXTERNAL_SERVICES=true
HEALTH_CHECK_INTERVAL=30
METRICS_ENABLED=true
EOF
    
    $SCP_CMD "/tmp/pi-env" "$PI_HOST:$PI_DEPLOY_DIR/.env.staging"
    rm "/tmp/pi-env"
    success "✅ Pi environment configuration created"
}

# Transfer monitoring configurations
transfer_monitoring_configs() {
    log "Transferring monitoring configurations"
    
    # Create Prometheus configuration
    cat > "/tmp/prometheus.yml" << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alerts.yml"

scrape_configs:
  - job_name: 'lucid-services'
    static_configs:
      - targets: 
        - 'lucid-api-gateway:8080'
        - 'lucid-blockchain-core:8084'
        - 'lucid-session-management:8085'
        - 'lucid-rdp-services:8086'
        - 'lucid-node-management:8087'
        - 'lucid-admin-interface:8088'
        - 'lucid-auth-service:8089'
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'lucid-databases'
    static_configs:
      - targets:
        - 'lucid-mongodb:27017'
        - 'lucid-redis:6379'
        - 'lucid-elasticsearch:9200'
    scrape_interval: 30s
EOF
    
    $SCP_CMD "/tmp/prometheus.yml" "$PI_HOST:$PI_DEPLOY_DIR/configs/monitoring/"
    rm "/tmp/prometheus.yml"
    
    # Create Grafana datasource configuration
    cat > "/tmp/grafana-datasource.yml" << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://lucid-prometheus:9090
    isDefault: true
    editable: true
EOF
    
    $SCP_CMD "/tmp/grafana-datasource.yml" "$PI_HOST:$PI_DEPLOY_DIR/configs/monitoring/grafana/"
    rm "/tmp/grafana-datasource.yml"
    
    success "✅ Monitoring configurations transferred"
}

# Setup Pi networking
setup_pi_networking() {
    section "Setting Up Pi Networking"
    
    log "Creating Docker networks on Pi"
    $SSH_CMD "docker network create lucid-staging --driver bridge --subnet 172.22.0.0/16 --attachable 2>/dev/null || echo 'Network already exists'"
    
    success "✅ Pi networking configured"
}

# Pull Docker images on Pi
pull_pi_images() {
    section "Pulling Docker Images on Pi"
    
    log "Logging into GitHub Container Registry on Pi"
    if [ -n "${GITHUB_TOKEN:-}" ]; then
        $SSH_CMD "echo '$GITHUB_TOKEN' | docker login ghcr.io -u $GITHUB_ACTOR --password-stdin" || {
            warn "⚠️ GitHub token authentication failed, using public images"
        }
    else
        warn "⚠️ GitHub token not available, using public images"
    fi
    
    # Pull database images
    log "Pulling database images"
    $SSH_CMD "docker pull mongo:7.0"
    $SSH_CMD "docker pull redis:7.0-alpine"
    $SSH_CMD "docker pull elasticsearch:8.11.0"
    
    # Pull monitoring images
    log "Pulling monitoring images"
    $SSH_CMD "docker pull prom/prometheus:latest"
    $SSH_CMD "docker pull grafana/grafana:latest"
    
    # Pull Lucid service images
    local services=("api-gateway" "blockchain-core" "session-management" "rdp-services" "node-management" "admin-interface" "auth-service")
    for service in "${services[@]}"; do
        log "Pulling $service image"
        $SSH_CMD "docker pull ghcr.io/hamigames/lucid/$service:latest" || {
            warn "⚠️ Failed to pull $service image, will use local build if available"
        }
    done
    
    success "✅ Docker images pulled on Pi"
}

# Deploy services on Pi
deploy_pi_services() {
    section "Deploying Services on Pi"
    
    log "Starting services on Pi"
    $SSH_CMD "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml up -d"
    
    # Wait for services to initialize
    log "Waiting for services to initialize..."
    sleep 60
    
    # Check service status
    log "Checking service status on Pi"
    $SSH_CMD "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml ps"
    
    success "✅ Services deployed on Pi"
}

# Verify Pi deployment
verify_pi_deployment() {
    section "Verifying Pi Deployment"
    
    log "Running health checks on Pi"
    
    # Check all services are running
    local failed_services=""
    local services=("api-gateway" "blockchain-core" "session-management" "rdp-services" "node-management" "admin-interface" "auth-service" "mongodb" "redis" "elasticsearch")
    
    for service in "${services[@]}"; do
        local container_name="lucid-${service}"
        if $SSH_CMD "docker ps --format '{{.Names}}' | grep -q '^${container_name}$'"; then
            success "✅ ${service}: Running"
        else
            error "❌ ${service}: Not running"
            failed_services="${failed_services} ${service}"
        fi
    done
    
    if [ -n "${failed_services}" ]; then
        error "Failed services: ${failed_services}"
        return 1
    fi
    
    # Test service health endpoints
    log "Testing service health endpoints"
    $SSH_CMD "curl -f http://localhost:8080/health" >/dev/null 2>&1 && success "✅ API Gateway: Healthy" || warn "⚠️ API Gateway: Health check failed"
    $SSH_CMD "curl -f http://localhost:8084/health" >/dev/null 2>&1 && success "✅ Blockchain Core: Healthy" || warn "⚠️ Blockchain Core: Health check failed"
    $SSH_CMD "curl -f http://localhost:8085/health" >/dev/null 2>&1 && success "✅ Session Management: Healthy" || warn "⚠️ Session Management: Health check failed"
    
    success "✅ Pi deployment verification complete"
}

# Show deployment summary
show_deployment_summary() {
    section "🎉 SSH Pi Deployment Complete!"
    
    success "Lucid staging environment is running on Raspberry Pi"
    
    echo ""
    log "Deployment Information:"
    echo "  • Pi Host: $PI_HOST"
    echo "  • Deployment ID: $DEPLOYMENT_ID"
    echo "  • Staging Directory: $PI_DEPLOY_DIR"
    echo "  • Environment File: $PI_DEPLOY_DIR/.env.staging"
    echo "  • Compose File: $PI_DEPLOY_DIR/docker-compose.staging.yml"
    
    echo ""
    log "Service Access (from Pi):"
    echo "  • API Gateway: http://localhost:8080"
    echo "  • Blockchain Core: http://localhost:8084"
    echo "  • Session Management: http://localhost:8085"
    echo "  • RDP Services: http://localhost:8086"
    echo "  • Node Management: http://localhost:8087"
    echo "  • Admin Interface: http://localhost:8088"
    echo "  • Auth Service: http://localhost:8089"
    echo "  • Prometheus: http://localhost:9090"
    echo "  • Grafana: http://localhost:3000"
    
    echo ""
    log "Management Commands:"
    echo "  • Status: $SSH_CMD 'cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml ps'"
    echo "  • Logs: $SSH_CMD 'cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml logs'"
    echo "  • Restart: $SSH_CMD 'cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml restart'"
    echo "  • Stop: $SSH_CMD 'cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml down'"
    echo "  • Update: $SSH_CMD 'cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml pull && docker-compose -f docker-compose.staging.yml up -d'"
}

# Main deployment function
main() {
    section "LUCID SSH PI DEPLOYMENT"
    log "Deploying to Pi via SSH: $PI_HOST"
    log "Staging directory: $PI_DEPLOY_DIR"
    log "Deployment ID: $DEPLOYMENT_ID"
    
    validate_ssh_connection
    setup_pi_directories
    transfer_deployment_files
    setup_pi_networking
    pull_pi_images
    deploy_pi_services
    verify_pi_deployment
    show_deployment_summary
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy"|"")
        main
        ;;
    "validate")
        validate_ssh_connection
        ;;
    "setup")
        setup_pi_directories
        setup_pi_networking
        ;;
    "transfer")
        transfer_deployment_files
        ;;
    "pull")
        pull_pi_images
        ;;
    "start")
        deploy_pi_services
        ;;
    "verify")
        verify_pi_deployment
        ;;
    "status")
        $SSH_CMD "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml ps"
        ;;
    "logs")
        $SSH_CMD "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml logs ${2:-}"
        ;;
    "stop")
        $SSH_CMD "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml down"
        ;;
    "cleanup")
        $SSH_CMD "cd $PI_DEPLOY_DIR && docker-compose -f docker-compose.staging.yml down -v"
        $SSH_CMD "sudo rm -rf $PI_DEPLOY_DIR"
        ;;
    *)
        echo "Usage: $0 [deploy|validate|setup|transfer|pull|start|verify|status|logs [service]|stop|cleanup]"
        echo ""
        echo "Commands:"
        echo "  deploy   - Full SSH Pi deployment process"
        echo "  validate - Validate SSH connection and Pi environment"
        echo "  setup    - Setup Pi directories and networking"
        echo "  transfer - Transfer deployment files to Pi"
        echo "  pull     - Pull Docker images on Pi"
        echo "  start    - Start services on Pi"
        echo "  verify   - Verify Pi deployment"
        echo "  status   - Show service status on Pi"
        echo "  logs     - Show service logs (optionally for specific service)"
        echo "  stop     - Stop services on Pi"
        echo "  cleanup  - Remove Pi deployment"
        echo ""
        echo "Environment Variables:"
        echo "  PI_HOST       - Pi hostname or IP (default: pickme@192.168.0.75)"
        echo "  PI_DEPLOY_DIR - Pi deployment directory (default: /opt/lucid/staging)"
        echo "  SSH_KEY       - SSH private key path (default: ~/.ssh/id_rsa)"
        echo "  SSH_TIMEOUT   - SSH connection timeout (default: 30)"
        echo "  GITHUB_TOKEN  - GitHub token for container registry access"
        echo "  GITHUB_ACTOR  - GitHub username for container registry access"
        exit 1
        ;;
esac
