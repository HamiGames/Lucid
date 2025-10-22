#!/bin/bash
# Path: scripts/deployment/create-distroless-networks.sh
# Create Enhanced Docker Networks for Distroless Deployment
# MUST RUN DIRECTLY ON PI CONSOLE
# Based on: distroless deployment plan network specifications

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

# Network specifications from distroless deployment plan
MAIN_NETWORK="lucid-pi-network"
MAIN_SUBNET="172.20.0.0/16"
MAIN_GATEWAY="172.20.0.1"

TRON_NETWORK="lucid-tron-isolated"
TRON_SUBNET="172.21.0.0/16"
TRON_GATEWAY="172.21.0.1"

GUI_NETWORK="lucid-gui-network"
GUI_SUBNET="172.22.0.0/16"
GUI_GATEWAY="172.22.0.1"

# Additional distroless networks
DISTROLESS_PROD_NETWORK="lucid-distroless-production"
DISTROLESS_PROD_SUBNET="172.23.0.0/16"
DISTROLESS_PROD_GATEWAY="172.23.0.1"

DISTROLESS_DEV_NETWORK="lucid-distroless-dev"
DISTROLESS_DEV_SUBNET="172.24.0.0/16"
DISTROLESS_DEV_GATEWAY="172.24.0.1"

MULTI_STAGE_NETWORK="lucid-multi-stage-network"
MULTI_STAGE_SUBNET="172.25.0.0/16"
MULTI_STAGE_GATEWAY="172.25.0.1"

echo ""
log_info "========================================"
log_info "Creating Enhanced Lucid Docker Networks"
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

# Function to remove old lucid networks
cleanup_old_networks() {
    log_info "Checking for old Lucid networks to remove..."
    
    # Find all lucid-related networks (including old ones)
    old_networks=$(docker network ls --format '{{.Name}}' | grep -E '^lucid-' || true)
    
    if [ -z "$old_networks" ]; then
        log_info "No old networks found"
        return 0
    fi
    
    echo ""
    log_warning "Found existing Lucid networks:"
    echo "$old_networks" | while read network; do
        echo "  • $network"
    done
    echo ""
    
    log_info "Removing old networks (containers must be stopped first)..."
    echo "$old_networks" | while read network; do
        if docker network rm "$network" 2>/dev/null; then
            log_success "Removed: $network"
        else
            log_warning "Could not remove: $network (may be in use)"
            log_info "Run 'docker-compose down' to stop containers first"
        fi
    done
    
    echo ""
}

# Function to create network
create_network() {
    local network_name=$1
    local subnet=$2
    local gateway=$3
    local network_type=$4
    
    log_info "Creating $network_type network: $network_name ($subnet)"
    
    # Check if network already exists with correct config
    if docker network ls --format '{{.Name}}' | grep -q "^${network_name}$"; then
        # Check if it has the correct subnet
        existing_subnet=$(docker network inspect "$network_name" --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null || echo "")
        
        if [ "$existing_subnet" = "$subnet" ]; then
            log_success "Network $network_name already exists with correct configuration"
            return 0
        else
            log_warning "Network $network_name exists with wrong subnet ($existing_subnet vs $subnet)"
            log_info "Removing and recreating..."
            docker network rm "$network_name" || {
                log_error "Failed to remove network (containers may be using it)"
                log_info "Stop containers first: docker-compose down"
                return 1
            }
        fi
    fi
    
    # Create network
    docker network create "$network_name" \
        --driver bridge \
        --subnet "$subnet" \
        --gateway "$gateway" \
        --attachable \
        --opt com.docker.network.bridge.enable_icc=true \
        --opt com.docker.network.bridge.enable_ip_masquerade=true \
        --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 \
        --opt com.docker.network.driver.mtu=1500 \
        --label "lucid.network=$network_type" \
        --label "lucid.subnet=$subnet"
    
    if [ $? -eq 0 ]; then
        log_success "Network $network_name created successfully"
        docker network inspect "$network_name" --format '  Subnet: {{range .IPAM.Config}}{{.Subnet}}{{end}}, Gateway: {{range .IPAM.Config}}{{.Gateway}}{{end}}'
    else
        log_error "Failed to create network $network_name"
        log_error "Possible causes:"
        log_error "  - Subnet overlap with existing network"
        log_error "  - Run 'docker network ls' to see existing networks"
        log_error "  - Run 'docker network inspect <name>' to see subnet ranges"
        return 1
    fi
}

# Main execution

# Step 1: Clean up old networks
cleanup_old_networks

# Step 2: Create main networks
log_info "Creating main Lucid networks per distroless deployment plan"
echo ""

# Create main network
if ! create_network "$MAIN_NETWORK" "$MAIN_SUBNET" "$MAIN_GATEWAY" "main"; then
    log_error "Failed to create main network - aborting"
    exit 1
fi
echo ""

# Create TRON isolated network
if ! create_network "$TRON_NETWORK" "$TRON_SUBNET" "$TRON_GATEWAY" "tron-isolated"; then
    log_error "Failed to create TRON network - aborting"
    exit 1
fi
echo ""

# Create GUI network
if ! create_network "$GUI_NETWORK" "$GUI_SUBNET" "$GUI_GATEWAY" "gui"; then
    log_error "Failed to create GUI network - aborting"
    exit 1
fi
echo ""

# Step 3: Create additional distroless networks
log_info "Creating additional distroless and multi-stage networks"
echo ""

# Create distroless production network
if ! create_network "$DISTROLESS_PROD_NETWORK" "$DISTROLESS_PROD_SUBNET" "$DISTROLESS_PROD_GATEWAY" "distroless-production"; then
    log_error "Failed to create distroless production network - aborting"
    exit 1
fi
echo ""

# Create distroless development network
if ! create_network "$DISTROLESS_DEV_NETWORK" "$DISTROLESS_DEV_SUBNET" "$DISTROLESS_DEV_GATEWAY" "distroless-dev"; then
    log_error "Failed to create distroless dev network - aborting"
    exit 1
fi
echo ""

# Create multi-stage network
if ! create_network "$MULTI_STAGE_NETWORK" "$MULTI_STAGE_SUBNET" "$MULTI_STAGE_GATEWAY" "multi-stage"; then
    log_error "Failed to create multi-stage network - aborting"
    exit 1
fi
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
log_info "  • $DISTROLESS_PROD_NETWORK ($DISTROLESS_PROD_SUBNET) - Distroless production infrastructure"
log_info "  • $DISTROLESS_DEV_NETWORK ($DISTROLESS_DEV_SUBNET) - Distroless development/testing"
log_info "  • $MULTI_STAGE_NETWORK ($MULTI_STAGE_SUBNET) - Multi-stage build infrastructure"
echo ""
log_info "Next steps (run on Pi console):"
log_info "  1. Set project root:"
log_info "     export PROJECT_ROOT=\"/mnt/myssd/Lucid/Lucid\""
log_info ""
log_info "  2. Generate .env files:"
log_info "     bash scripts/config/generate-all-env-complete.sh"
log_info ""
log_info "  3. Create distroless .env file:"
log_info "     bash scripts/deployment/create-distroless-env.sh"
log_info ""
log_info "  4. Deploy distroless base infrastructure:"
log_info "     bash scripts/deployment/deploy-distroless-base.sh"
log_info ""
log_info "  5. Deploy Lucid services:"
log_info "     bash scripts/deployment/deploy-lucid-services.sh"
echo ""
log_success "Enhanced networks ready for distroless deployment!"
echo ""
