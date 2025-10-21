#!/bin/bash
# Path: scripts/deployment/create-pi-networks.sh
# Create Docker Networks on Raspberry Pi
# MUST RUN DIRECTLY ON PI CONSOLE
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

echo ""
log_info "========================================"
log_info "Creating Lucid Docker Networks"
log_info "========================================"
echo ""

# Verify Docker is running
if ! docker info > /dev/null 2>&1; then
    log_error "Docker is not running!"
    log_error "Please start Docker: sudo systemctl start docker"
    exit 1
fi

log_success "Docker is running"
echo ""

# Function to create network
create_network() {
    local network_name=$1
    local subnet=$2
    local gateway=$3
    
    log_info "Creating network: $network_name ($subnet)"
    
    # Check if network already exists
    if docker network ls --format '{{.Name}}' | grep -q "^${network_name}$"; then
        log_warning "Network $network_name already exists"
        read -p "Remove and recreate? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Removing existing network..."
            docker network rm $network_name || {
                log_error "Failed to remove network (containers may be using it)"
                log_info "Stop all containers first: docker-compose down"
                return 1
            }
        else
            log_info "Keeping existing network"
            return 0
        fi
    fi
    
    # Create network
    log_info "Creating network with configuration:"
    log_info "  Name: $network_name"
    log_info "  Subnet: $subnet"
    log_info "  Gateway: $gateway"
    
    docker network create "$network_name" \
        --driver bridge \
        --subnet "$subnet" \
        --gateway "$gateway" \
        --attachable \
        --opt com.docker.network.bridge.enable_icc=true \
        --opt com.docker.network.bridge.enable_ip_masquerade=true \
        --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 \
        --opt com.docker.network.driver.mtu=1500
    
    if [ $? -eq 0 ]; then
        log_success "Network $network_name created successfully"
        
        # Show network details
        docker network inspect "$network_name" --format '{{range .IPAM.Config}}  Subnet: {{.Subnet}}, Gateway: {{.Gateway}}{{end}}'
    else
        log_error "Failed to create network $network_name"
        return 1
    fi
}

# Main execution
log_info "Network Configuration per docker-build-process-plan.md"
echo ""

# Create main network
create_network "$MAIN_NETWORK" "$MAIN_SUBNET" "$MAIN_GATEWAY"
echo ""

# Create TRON isolated network
create_network "$TRON_NETWORK" "$TRON_SUBNET" "$TRON_GATEWAY"
echo ""

# Create GUI network
create_network "$GUI_NETWORK" "$GUI_SUBNET" "$GUI_GATEWAY"
echo ""

# List all Lucid networks
log_info "All Lucid Docker Networks:"
docker network ls | grep lucid | awk '{print "  • " $2 " (ID: " $1 ")"}'
echo ""

log_success "========================================" 
log_success "All networks created successfully!"
log_success "========================================"
echo ""
log_info "Networks created:"
log_info "  • $MAIN_NETWORK ($MAIN_SUBNET) - Foundation, Core, Application services"
log_info "  • $TRON_NETWORK ($TRON_SUBNET) - TRON payment services (isolated)"
log_info "  • $GUI_NETWORK ($GUI_SUBNET) - GUI integration services"
echo ""
log_info "Next steps (run on Pi console):"
log_info "  1. Set project root:"
log_info "     export PROJECT_ROOT=\"/mnt/myssd/Lucid/Lucid\""
log_info ""
log_info "  2. Generate .env files:"
log_info "     bash scripts/config/generate-all-env-complete.sh"
log_info ""
log_info "  3. Deploy Phase 1 (Foundation):"
log_info "     docker-compose --env-file configs/environment/.env.foundation \\"
log_info "                    -f configs/docker/docker-compose.foundation.yml up -d"
log_info ""
log_info "  4. Deploy Phase 2 (Core):"
log_info "     docker-compose --env-file configs/environment/.env.foundation \\"
log_info "                    --env-file configs/environment/.env.core \\"
log_info "                    -f configs/docker/docker-compose.core.yml up -d"
log_info ""
echo ""
log_success "Networks ready for deployment!"
echo ""
