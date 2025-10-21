#!/bin/bash
# Path: scripts/deployment/create-pi-networks.sh
# Create Docker Networks on Raspberry Pi
# Must run BEFORE any docker-compose deployments
# Based on: docker-build-process-plan.md network specifications

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

# Configuration
PI_HOST="${PI_HOST:-192.168.0.75}"
PI_USER="${PI_USER:-pickme}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Network specifications from docker-build-process-plan.md
MAIN_NETWORK="lucid-pi-network"
MAIN_SUBNET="172.20.0.0/16"
MAIN_GATEWAY="172.20.0.1"

TRON_NETWORK="lucid-tron-isolated"
TRON_SUBNET="172.21.0.0/16"
TRON_GATEWAY="172.21.0.1"

GUI_NETWORK="lucid-gui-network"
GUI_SUBNET="172.22.0.0/16"
GUI_GATEWAY="172.22.0.1"

log_info "========================================"
log_info "Creating Lucid Docker Networks on Pi"
log_info "========================================"
echo ""

# Function to create network on Pi
create_network_on_pi() {
    local network_name=$1
    local subnet=$2
    local gateway=$3
    
    log_info "Creating network: $network_name ($subnet)"
    
    ssh "$PI_USER@$PI_HOST" << EOF
        # Check if network already exists
        if docker network ls | grep -q "$network_name"; then
            echo "Network $network_name already exists, removing..."
            docker network rm $network_name 2>/dev/null || true
        fi
        
        # Create network
        docker network create $network_name \
            --driver bridge \
            --subnet $subnet \
            --gateway $gateway \
            --attachable \
            --opt com.docker.network.bridge.enable_icc=true \
            --opt com.docker.network.bridge.enable_ip_masquerade=true \
            --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 \
            --opt com.docker.network.driver.mtu=1500
        
        # Verify network was created
        if docker network ls | grep -q "$network_name"; then
            echo "✅ Network $network_name created successfully"
            docker network inspect $network_name | grep -E "Subnet|Gateway"
        else
            echo "❌ Failed to create network $network_name"
            exit 1
        fi
EOF
    
    if [ $? -eq 0 ]; then
        log_success "Network $network_name created on Pi"
    else
        log_error "Failed to create network $network_name on Pi"
        return 1
    fi
}

# Main execution
main() {
    log_info "Target Pi: $PI_USER@$PI_HOST"
    echo ""
    
    # Test SSH connection
    log_info "Testing SSH connection to Pi..."
    if ! ssh -o ConnectTimeout=10 "$PI_USER@$PI_HOST" "echo 'SSH connection successful'"; then
        log_error "Cannot connect to Pi at $PI_HOST"
        log_error "Please verify:"
        log_error "  - Pi is powered on and connected to network"
        log_error "  - SSH is enabled on Pi"
        log_error "  - IP address is correct: $PI_HOST"
        log_error "  - SSH keys are properly configured"
        exit 1
    fi
    log_success "SSH connection established"
    echo ""
    
    # Create networks
    log_info "Creating Docker networks on Pi..."
    echo ""
    
    # Create main network
    create_network_on_pi "$MAIN_NETWORK" "$MAIN_SUBNET" "$MAIN_GATEWAY"
    echo ""
    
    # Create TRON isolated network
    create_network_on_pi "$TRON_NETWORK" "$TRON_SUBNET" "$TRON_GATEWAY"
    echo ""
    
    # Create GUI network
    create_network_on_pi "$GUI_NETWORK" "$GUI_SUBNET" "$GUI_GATEWAY"
    echo ""
    
    # List all Lucid networks
    log_info "Listing all Lucid networks on Pi:"
    ssh "$PI_USER@$PI_HOST" "docker network ls | grep lucid"
    echo ""
    
    log_success "========================================" 
    log_success "All networks created successfully!"
    log_success "========================================"
    echo ""
    log_info "Networks created:"
    log_info "  • $MAIN_NETWORK ($MAIN_SUBNET)"
    log_info "  • $TRON_NETWORK ($TRON_SUBNET)"
    log_info "  • $GUI_NETWORK ($GUI_SUBNET)"
    echo ""
    log_info "Next steps:"
    log_info "  1. Generate .env files: cd /mnt/myssd/Lucid/Lucid && bash scripts/config/generate-all-env-complete.sh"
    log_info "  2. Deploy Phase 1: bash scripts/deployment/deploy-phase1-pi.sh"
    log_info "  3. Deploy Phase 2: bash scripts/deployment/deploy-phase2-pi.sh"
    log_info "  4. Deploy Phase 3: bash scripts/deployment/deploy-phase3-pi.sh"
    log_info "  5. Deploy Phase 4: bash scripts/deployment/deploy-phase4-pi.sh"
    echo ""
}

# Run main function
main "$@"

