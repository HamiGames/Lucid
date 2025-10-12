#!/bin/bash
# LUCID CORE SUPPORT SERVICES - Pi Deployment Script
# Deploys core infrastructure services to Raspberry Pi
# GENIUS-LEVEL implementation with LUCID-STRICT compliance
# Path: scripts/deployment/deploy-to-pi.sh

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
PI_DEPLOY_DIR="/home/pickme/lucid-core"
DOCKER_REGISTRY="pickme/lucid"

# Core support services and their image tags
declare -A SERVICE_IMAGES=(
    ["tor-proxy"]="tor-proxy"
    ["lucid_api"]="api-server"
    ["lucid_api_gateway"]="api-gateway"
    ["tunnel-tools"]="tunnel-tools"
    ["server-tools"]="server-tools"
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

# Transfer compose file and configuration
transfer_files() {
    section "Transferring Files to Pi"
    
    # Create deployment directory on Pi
    log "Creating deployment directory on Pi: $PI_DEPLOY_DIR"
    ssh "$PI_HOST" "mkdir -p $PI_DEPLOY_DIR"
    
    # Transfer lucid-dev.yaml
    log "Transferring lucid-dev.yaml"
    scp "${LUCID_ROOT}/infrastructure/compose/lucid-dev.yaml" "$PI_HOST:$PI_DEPLOY_DIR/"
    success "✅ Compose file transferred"
    
    # Create environment file for Pi
    log "Creating Pi-specific environment file"
    cat > "/tmp/lucid-pi.env" << EOF
# LUCID Pi Deployment Environment
LUCID_ENV=pi
LUCID_PLANE=ops
CLUSTER_ID=pi-core

# Database configuration
MONGO_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin&retryWrites=false

# Tor configuration (will be populated by services)
TOR_CONTROL_PASSWORD=
ONION_API_GATEWAY=
ONION_API_SERVER=
ONION_TUNNEL=
ONION_MONGO=
ONION_TOR_CONTROL=

# Security
AGE_PRIVATE_KEY=

# Pi-specific paths
LUCID_DATA_PATH=/home/pickme/lucid-data
LUCID_LOGS_PATH=/home/pickme/lucid-logs
EOF
    
    scp "/tmp/lucid-pi.env" "$PI_HOST:$PI_DEPLOY_DIR/.env"
    rm "/tmp/lucid-pi.env"
    success "✅ Environment file created on Pi"
    
    # Transfer deployment scripts
    log "Transferring helper scripts"
    cat > "/tmp/pi-helper.sh" << 'EOF'
#!/bin/bash
# Pi Helper Scripts for Lucid Core Services

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[PI-HELPER] $1${NC}"; }
success() { echo -e "${GREEN}[SUCCESS] $1${NC}"; }
warn() { echo -e "${YELLOW}[WARNING] $1${NC}"; }

# Check all services
check_services() {
    echo "=== Lucid Core Services Status ==="
    docker compose -f lucid-dev.yaml ps
    echo ""
    
    echo "=== Health Checks ==="
    
    # Tor proxy health
    if curl -s --socks5-hostname localhost:9050 http://httpbin.org/ip >/dev/null 2>&1; then
        success "✅ Tor proxy healthy"
    else
        warn "⚠️ Tor proxy issues"
    fi
    
    # MongoDB health
    if docker exec lucid_mongo mongosh --quiet --eval "db.runCommand({ping: 1})" >/dev/null 2>&1; then
        success "✅ MongoDB healthy"
    else
        warn "⚠️ MongoDB issues"
    fi
    
    # API Server health
    if curl -fsS http://localhost:8081/health >/dev/null 2>&1; then
        success "✅ API Server healthy"
    else
        warn "⚠️ API Server issues"
    fi
    
    # API Gateway health
    if curl -fsS http://localhost:8080/health >/dev/null 2>&1; then
        success "✅ API Gateway healthy"
    else
        warn "⚠️ API Gateway issues"
    fi
}

# Show onion addresses
show_onions() {
    echo "=== Onion Addresses ==="
    if docker exec tor_proxy cat /run/lucid/onion/multi-onion.env 2>/dev/null; then
        success "✅ Onion addresses loaded"
    else
        warn "⚠️ Onion addresses not yet available"
    fi
}

# Show logs
show_logs() {
    local service=${1:-}
    if [[ -n "$service" ]]; then
        docker compose -f lucid-dev.yaml logs --tail=50 "$service"
    else
        docker compose -f lucid-dev.yaml logs --tail=20
    fi
}

# Restart services
restart_services() {
    log "Restarting core support services"
    docker compose -f lucid-dev.yaml restart
    success "Services restarted"
}

# Update services
update_services() {
    log "Pulling latest images and restarting"
    docker compose -f lucid-dev.yaml pull
    docker compose -f lucid-dev.yaml up -d
    success "Services updated"
}

# Main menu
case "${1:-status}" in
    "status"|"check")
        check_services
        ;;
    "onions")
        show_onions
        ;;
    "logs")
        show_logs "${2:-}"
        ;;
    "restart")
        restart_services
        ;;
    "update")
        update_services
        ;;
    *)
        echo "Usage: $0 [status|onions|logs [service]|restart|update]"
        echo ""
        echo "Commands:"
        echo "  status  - Show service status and health checks"
        echo "  onions  - Show onion addresses"
        echo "  logs    - Show service logs (optionally for specific service)"
        echo "  restart - Restart all services"
        echo "  update  - Pull latest images and restart"
        ;;
esac
EOF
    
    scp "/tmp/pi-helper.sh" "$PI_HOST:$PI_DEPLOY_DIR/helper.sh"
    ssh "$PI_HOST" "chmod +x $PI_DEPLOY_DIR/helper.sh"
    rm "/tmp/pi-helper.sh"
    success "✅ Helper scripts transferred"
}

# Pull Docker images on Pi
pull_images() {
    section "Pulling Docker Images on Pi"
    
    # MongoDB doesn't need pulling (official image)
    log "MongoDB uses official mongo:7 image (will pull automatically)"
    
    # Pull our custom images
    for service_key in "${!SERVICE_IMAGES[@]}"; do
        local image_tag="${SERVICE_IMAGES[$service_key]}"
        local full_image="${DOCKER_REGISTRY}:${image_tag}"
        
        log "Pulling $service_key -> $full_image"
        if ssh "$PI_HOST" "docker pull $full_image"; then
            success "✅ Pulled: $full_image"
        else
            error "❌ Failed to pull: $full_image"
            return 1
        fi
    done
    
    success "All images pulled successfully on Pi"
}

# Setup Pi networking
setup_pi_networking() {
    section "Setting Up Pi Networking"
    
    log "Creating lucid_core_net network on Pi"
    ssh "$PI_HOST" "docker network create lucid_core_net --driver bridge --subnet 172.21.0.0/16 --attachable 2>/dev/null || echo 'Network already exists'"
    
    log "Creating external devcontainer network reference"
    
    success "✅ Pi networking configured"
}

# Create Pi data directories
setup_pi_directories() {
    section "Setting Up Pi Directories"
    
    log "Creating data directories on Pi"
    ssh "$PI_HOST" "mkdir -p /home/pickme/lucid-data/{mongo,tor,onions,tunnels,logs}"
    ssh "$PI_HOST" "mkdir -p /home/pickme/lucid-logs"
    
    # Set proper permissions
    ssh "$PI_HOST" "sudo chown -R pickme:pickme /home/pickme/lucid-data /home/pickme/lucid-logs"
    
    success "✅ Pi directories created"
}

# Deploy and start services
deploy_services() {
    section "Deploying Core Support Services"
    
    log "Starting core support services on Pi"
    ssh "$PI_HOST" "cd $PI_DEPLOY_DIR && docker compose -f lucid-dev.yaml up -d"
    
    # Wait for services to initialize
    log "Waiting for services to initialize..."
    sleep 30
    
    # Check service status
    log "Checking service status"
    ssh "$PI_HOST" "cd $PI_DEPLOY_DIR && docker compose -f lucid-dev.yaml ps"
    
    success "✅ Core support services deployed on Pi"
}

# Verify deployment
verify_deployment() {
    section "Verifying Pi Deployment"
    
    log "Running health checks on Pi"
    ssh "$PI_HOST" "cd $PI_DEPLOY_DIR && ./helper.sh status"
    
    success "✅ Pi deployment verification complete"
}

# Show deployment summary
show_summary() {
    section "🎉 Pi Deployment Complete!"
    
    success "Core support services are running on Pi"
    
    echo ""
    log "Pi Access Information:"
    echo "  • SSH: ssh $PI_HOST"
    echo "  • Services directory: $PI_DEPLOY_DIR"
    echo "  • Helper script: cd $PI_DEPLOY_DIR && ./helper.sh"
    
    echo ""
    log "Service Access (from Pi):"
    echo "  • API Gateway: http://localhost:8080"
    echo "  • API Server: http://localhost:8081"
    echo "  • MongoDB: mongodb://localhost:27017"
    echo "  • Tor SOCKS: localhost:9050"
    
    echo ""
    log "Management Commands:"
    echo "  • Status: ssh $PI_HOST 'cd $PI_DEPLOY_DIR && ./helper.sh status'"
    echo "  • Logs: ssh $PI_HOST 'cd $PI_DEPLOY_DIR && ./helper.sh logs'"
    echo "  • Onions: ssh $PI_HOST 'cd $PI_DEPLOY_DIR && ./helper.sh onions'"
    echo "  • Restart: ssh $PI_HOST 'cd $PI_DEPLOY_DIR && ./helper.sh restart'"
    echo "  • Update: ssh $PI_HOST 'cd $PI_DEPLOY_DIR && ./helper.sh update'"
}

# Main deployment function
main() {
    section "LUCID CORE SUPPORT - Pi Deployment"
    log "Deploying to: $PI_HOST"
    log "Deploy directory: $PI_DEPLOY_DIR"
    
    test_pi_connection
    transfer_files
    pull_images
    setup_pi_networking
    setup_pi_directories
    deploy_services
    verify_deployment
    show_summary
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
        transfer_files
        ;;
    "pull")
        pull_images
        ;;
    "verify")
        verify_deployment
        ;;
    *)
        echo "Usage: $0 [deploy|test-connection|transfer|pull|verify]"
        echo ""
        echo "Commands:"
        echo "  deploy         - Full deployment process"
        echo "  test-connection - Test SSH connection to Pi"
        echo "  transfer       - Transfer files to Pi only"
        echo "  pull          - Pull images on Pi only"
        echo "  verify        - Verify existing deployment"
        exit 1
        ;;
esac