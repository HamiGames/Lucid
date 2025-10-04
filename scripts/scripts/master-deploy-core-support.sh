#!/bin/bash
# LUCID CORE SUPPORT - Master Deployment Script
# Orchestrates build in DevContainer and deployment to Pi
# GENIUS-LEVEL implementation with LUCID-STRICT compliance

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
LUCID_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${LUCID_ROOT}/infrastructure/compose/lucid-dev.yaml"
DOCKER_REGISTRY="pickme/lucid"
PI_HOST="pickme@192.168.0.75"

log() { echo -e "${BLUE}[MASTER-DEPLOY] $1${NC}"; }
success() { echo -e "${GREEN}[SUCCESS] $1${NC}"; }
warn() { echo -e "${YELLOW}[WARNING] $1${NC}"; }
error() { echo -e "${RED}[ERROR] $1${NC}"; }
section() { echo -e "${BOLD}${CYAN}=== $1 ===${NC}"; }

# Test Pi connectivity
test_pi_connection() {
    section "Pi Connectivity Test"
    
    log "Testing SSH connection to $PI_HOST"
    if ssh -o ConnectTimeout=10 -o BatchMode=yes "$PI_HOST" "echo 'Pi connection successful'" 2>/dev/null; then
        success "✅ SSH connection to Pi verified"
    else
        error "❌ Cannot connect to Pi via SSH: $PI_HOST"
        exit 1
    fi
}

# Quick build and deploy without full scripts
quick_deploy() {
    section "🚀 QUICK CORE SUPPORT DEPLOYMENT"
    
    # Test connectivity first
    test_pi_connection
    
    # Check compose file exists
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        error "Compose file not found: $COMPOSE_FILE"
        exit 1
    fi
    success "Found compose file: $COMPOSE_FILE"
    
    # Simple deployment using existing compose file
    log "Transferring compose file to Pi"
    scp "$COMPOSE_FILE" "$PI_HOST:/tmp/lucid-dev.yaml"
    
    # Create basic environment on Pi
    log "Setting up Pi environment"
    ssh "$PI_HOST" "mkdir -p /home/pickme/lucid-core"
    ssh "$PI_HOST" "mv /tmp/lucid-dev.yaml /home/pickme/lucid-core/"
    
    # Create basic .env file
    ssh "$PI_HOST" "cat > /home/pickme/lucid-core/.env << 'PIEOF'
LUCID_ENV=pi
LUCID_PLANE=ops
CLUSTER_ID=pi-core
MONGO_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin&retryWrites=false
TOR_CONTROL_PASSWORD=
ONION_API_GATEWAY=
ONION_API_SERVER=
ONION_TUNNEL=
ONION_MONGO=
ONION_TOR_CONTROL=
AGE_PRIVATE_KEY=
PIEOF"
    
    # Setup networking on Pi
    log "Setting up Pi networking"
    ssh "$PI_HOST" "docker network create lucid_core_net --driver bridge --subnet 172.21.0.0/16 --attachable 2>/dev/null || echo 'Network exists'"
    ssh "$PI_HOST" "docker network create lucid-dev_lucid_net --driver bridge --attachable 2>/dev/null || echo 'External network created'"
    
    # Start services
    log "Starting services on Pi"
    ssh "$PI_HOST" "cd /home/pickme/lucid-core && docker compose -f lucid-dev.yaml up -d"
    
    # Wait and check
    log "Waiting for services to start..."
    sleep 30
    
    log "Checking service status"
    ssh "$PI_HOST" "cd /home/pickme/lucid-core && docker compose -f lucid-dev.yaml ps"
    
    section "🎉 DEPLOYMENT COMPLETE!"
    success "Core support services deployed to Pi"
    log "Access: ssh $PI_HOST"
    log "Services: cd /home/pickme/lucid-core && docker compose -f lucid-dev.yaml ps"
}

# Main execution
case "${1:-quick}" in
    "test")
        test_pi_connection
        ;;
    "quick"|"")
        quick_deploy
        ;;
    *)
        echo "Usage: $0 [quick|test]"
        echo "  quick - Quick deployment using existing compose"
        echo "  test  - Test Pi connectivity"
        ;;
esac
