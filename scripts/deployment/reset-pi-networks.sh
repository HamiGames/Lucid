#!/bin/bash
# Path: scripts/deployment/reset-pi-networks.sh
# Complete Docker Network Reset for Raspberry Pi with Buildx Rebuild
# Based on: docker-build-process-plan.md network specifications
# MUST RUN DIRECTLY ON PI CONSOLE
#
# Usage:
#   bash reset-pi-networks.sh          # Reset networks AND rebuild buildx
#   bash reset-pi-networks.sh no       # Reset networks ONLY (skip buildx)

set -euo pipefail

# Configuration per plan/build_instruction_docs/pre-build/04-distroless-base-images.md
REBUILD_BUILDX="${1:-yes}"  # Default: rebuild buildx
BUILDER_NAME="lucid-builder"  # Per plan specs (hyphen, not underscore)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
log_info "========================================"
log_info "Pi Docker Network Complete Reset"
log_info "Based on: docker-build-process-plan.md"
log_info "========================================"
log_info "Buildx Rebuild: $REBUILD_BUILDX"
echo ""

# STEP 1: Remove buildx builders and containers
log_info "STEP 1: Removing buildx builders..."
echo ""

# List all buildx builders
docker buildx ls
echo ""

# Stop and remove both lucid_builder (old) and lucid-builder (plan spec)
log_info "Removing lucid_builder and lucid-builder..."
docker buildx stop lucid_builder 2>/dev/null || true
docker buildx rm lucid_builder --force 2>/dev/null || true
docker buildx stop lucid-builder 2>/dev/null || true
docker buildx rm lucid-builder --force 2>/dev/null || true

# Remove any other non-default builders
builders=$(docker buildx ls | grep -v "^NAME" | awk '{print $1}' | grep -v "default" || true)
if [ -n "$builders" ]; then
    while read -r builder; do
        log_info "Removing builder: $builder"
        docker buildx stop "$builder" 2>/dev/null || true
        docker buildx rm "$builder" --force 2>/dev/null || true
    done <<< "$builders"
fi

# Force remove all buildkit containers
log_info "Removing buildkit containers..."
docker ps -a | grep buildkit | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true
log_success "All buildx builders removed"
echo ""

# STEP 2: Stop and remove all Lucid containers
log_info "STEP 2: Stopping all Lucid containers..."
echo ""

lucid_containers=$(docker ps -aq --filter "name=lucid" || true)
if [ -n "$lucid_containers" ]; then
    log_warning "Found Lucid containers - stopping and removing..."
    echo "$lucid_containers" | xargs -r docker stop 2>/dev/null || true
    echo "$lucid_containers" | xargs -r docker rm -f 2>/dev/null || true
    log_success "Removed Lucid containers"
else
    log_info "No Lucid containers found"
fi
echo ""

# STEP 3: Force remove ALL Lucid networks
log_info "STEP 3: Removing ALL Lucid networks (including dev networks)..."
echo ""

# Show current networks
log_info "Current networks:"
docker network ls
echo ""

# Get all networks with subnet information
log_info "Current subnet allocations:"
docker network inspect $(docker network ls -q) --format '{{.Name}}: {{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null | grep -v "^host:" | grep -v "^none:"
echo ""

# Find and remove all lucid-related networks
all_lucid_networks=$(docker network ls --format '{{.Name}}' | grep -iE 'lucid' || true)

if [ -n "$all_lucid_networks" ]; then
    log_warning "Removing these networks:"
    echo "$all_lucid_networks" | while read network; do
        subnet=$(docker network inspect "$network" --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null || echo "unknown")
        echo "  • $network ($subnet)"
    done
    echo ""
    
    # Force disconnect and remove each network
    echo "$all_lucid_networks" | while read network; do
        # Get all containers on this network
        containers=$(docker network inspect "$network" --format '{{range .Containers}}{{.Name}} {{end}}' 2>/dev/null || true)
        
        # Disconnect all containers
        if [ -n "$containers" ]; then
            log_info "Disconnecting containers from $network..."
            for container in $containers; do
                docker network disconnect -f "$network" "$container" 2>/dev/null || true
            done
        fi
        
        # Remove the network
        if docker network rm "$network" 2>/dev/null; then
            log_success "Removed: $network"
        else
            log_error "Failed to remove: $network (will retry)"
        fi
    done
else
    log_info "No Lucid networks found"
fi
echo ""

# STEP 4: Prune all unused networks
log_info "STEP 4: Pruning unused Docker networks..."
docker network prune -f
log_success "Network pruning complete"
echo ""

# STEP 5: Verify subnet availability
log_info "STEP 5: Verifying target subnets are available..."
echo ""

current_subnets=$(docker network inspect $(docker network ls -q) --format '{{.Name}}: {{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null | grep -v "^host:" | grep -v "^none:" || true)
echo "Remaining networks:"
echo "$current_subnets"
echo ""

# Check for conflicts with our target subnets
conflicts=0
if echo "$current_subnets" | grep -q "172.20.0.0/16"; then
    log_error "CONFLICT: 172.20.0.0/16 (lucid-pi-network) is still allocated!"
    echo "$current_subnets" | grep "172.20.0.0/16"
    conflicts=$((conflicts + 1))
fi
if echo "$current_subnets" | grep -q "172.21.0.0/16"; then
    log_error "CONFLICT: 172.21.0.0/16 (lucid-tron-isolated) is still allocated!"
    echo "$current_subnets" | grep "172.21.0.0/16"
    conflicts=$((conflicts + 1))
fi
if echo "$current_subnets" | grep -q "172.22.0.0/16"; then
    log_error "CONFLICT: 172.22.0.0/16 (lucid-gui-network) is still allocated!"
    echo "$current_subnets" | grep "172.22.0.0/16"
    conflicts=$((conflicts + 1))
fi

if [ $conflicts -gt 0 ]; then
    log_error "❌ $conflicts subnet conflicts found!"
    log_error "Manual cleanup required - exiting"
    exit 1
else
    log_success "✅ All target subnets are available"
fi
echo ""

# STEP 6: Create Lucid Pi networks per docker-build-process-plan.md
log_info "STEP 6: Creating Lucid Pi production networks..."
echo ""

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

# Create Network 1: Main Network (Foundation + Core + Application + Blockchain)
log_info "Creating: $MAIN_NETWORK ($MAIN_SUBNET)"
log_info "  Purpose: Foundation, Core, Application, and Blockchain services"
log_info "  Public Access: YES (NAT enabled for internet access)"
echo ""

if docker network create "$MAIN_NETWORK" \
    --driver bridge \
    --subnet "$MAIN_SUBNET" \
    --gateway "$MAIN_GATEWAY" \
    --attachable \
    --opt com.docker.network.bridge.enable_icc=true \
    --opt com.docker.network.bridge.enable_ip_masquerade=true \
    --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 \
    --opt com.docker.network.driver.mtu=1500 \
    --label "lucid.network=main" \
    --label "lucid.subnet=172.20.0.0/16" \
    --label "lucid.services=foundation,core,application,blockchain" \
    --label "lucid.internet=enabled"; then
    
    log_success "✅ Created: $MAIN_NETWORK"
    docker network inspect "$MAIN_NETWORK" --format 'Subnet: {{range .IPAM.Config}}{{.Subnet}}{{end}}, Gateway: {{range .IPAM.Config}}{{.Gateway}}{{end}}'
else
    log_error "❌ Failed to create: $MAIN_NETWORK"
    docker network inspect $(docker network ls -q) --format '{{.Name}}: {{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null
    exit 1
fi
echo ""

# Create Network 2: TRON Isolated Network (Payment Services Only)
log_info "Creating: $TRON_NETWORK ($TRON_SUBNET)"
log_info "  Purpose: TRON payment services (ISOLATED from blockchain)"
log_info "  Public Access: YES (needs TRON network access)"
echo ""

if docker network create "$TRON_NETWORK" \
    --driver bridge \
    --subnet "$TRON_SUBNET" \
    --gateway "$TRON_GATEWAY" \
    --attachable \
    --opt com.docker.network.bridge.enable_icc=true \
    --opt com.docker.network.bridge.enable_ip_masquerade=true \
    --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 \
    --opt com.docker.network.driver.mtu=1500 \
    --label "lucid.network=tron-isolated" \
    --label "lucid.subnet=172.21.0.0/16" \
    --label "lucid.services=tron-payment" \
    --label "lucid.isolation=payment-only" \
    --label "lucid.internet=enabled"; then
    
    log_success "✅ Created: $TRON_NETWORK"
    docker network inspect "$TRON_NETWORK" --format 'Subnet: {{range .IPAM.Config}}{{.Subnet}}{{end}}, Gateway: {{range .IPAM.Config}}{{.Gateway}}{{end}}'
else
    log_error "❌ Failed to create: $TRON_NETWORK"
    exit 1
fi
echo ""

# Create Network 3: GUI Network
log_info "Creating: $GUI_NETWORK ($GUI_SUBNET)"
log_info "  Purpose: Electron GUI integration services"
log_info "  Public Access: YES (NAT enabled)"
echo ""

if docker network create "$GUI_NETWORK" \
    --driver bridge \
    --subnet "$GUI_SUBNET" \
    --gateway "$GUI_GATEWAY" \
    --attachable \
    --opt com.docker.network.bridge.enable_icc=true \
    --opt com.docker.network.bridge.enable_ip_masquerade=true \
    --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 \
    --opt com.docker.network.driver.mtu=1500 \
    --label "lucid.network=gui" \
    --label "lucid.subnet=172.22.0.0/16" \
    --label "lucid.services=electron-gui" \
    --label "lucid.internet=enabled"; then
    
    log_success "✅ Created: $GUI_NETWORK"
    docker network inspect "$GUI_NETWORK" --format 'Subnet: {{range .IPAM.Config}}{{.Subnet}}{{end}}, Gateway: {{range .IPAM.Config}}{{.Gateway}}{{end}}'
else
    log_error "❌ Failed to create: $GUI_NETWORK"
    exit 1
fi
echo ""

# STEP 7: Rebuild Docker Buildx (per plan/build_instruction_docs/pre-build/04-distroless-base-images.md)
if [ "$REBUILD_BUILDX" = "yes" ]; then
    log_info "STEP 7: Rebuilding Docker Buildx builder..."
    echo ""
    
    # Verify buildx is available
    if ! docker buildx version >/dev/null 2>&1; then
        log_error "Docker Buildx not found!"
        log_error "Please install Docker Buildx to continue"
        exit 1
    fi
    
    log_success "Docker Buildx is available"
    
    # Create new buildx builder per plan specifications
    # Ref: plan/build_instruction_docs/pre-build/04-distroless-base-images.md line 373
    log_info "Creating buildx builder: $BUILDER_NAME"
    log_info "  Driver: docker-container"
    log_info "  Network: host (for maximum compatibility)"
    log_info "  Platforms: linux/amd64, linux/arm64"
    echo ""
    
    if docker buildx create \
        --name "$BUILDER_NAME" \
        --driver docker-container \
        --driver-opt network=host \
        --platform linux/amd64,linux/arm64 \
        --bootstrap \
        --use; then
        
        log_success "✅ Created buildx builder: $BUILDER_NAME"
        echo ""
        
        # Inspect the builder
        log_info "Builder details:"
        docker buildx inspect "$BUILDER_NAME"
        echo ""
        
        log_success "✅ Buildx builder ready for multi-platform builds"
    else
        log_error "❌ Failed to create buildx builder"
        log_warning "You can manually create it later with:"
        echo "  docker buildx create --name $BUILDER_NAME --driver docker-container --driver-opt network=host --platform linux/amd64,linux/arm64 --use"
    fi
    echo ""
else
    log_info "STEP 7: Skipping buildx rebuild (as requested)"
    log_info "To rebuild buildx later, run:"
    echo "  docker buildx create --name $BUILDER_NAME --driver docker-container --driver-opt network=host --platform linux/amd64,linux/arm64 --use"
    echo ""
fi

# STEP 8: Final Verification and Summary
log_info "STEP 8: Final Verification..."
echo ""

log_info "All Lucid Docker Networks:"
docker network ls | grep lucid || log_warning "No lucid networks found!"
echo ""

log_info "Network Details:"
docker network inspect lucid-pi-network lucid-tron-isolated lucid-gui-network --format '{{.Name}}: Subnet={{range .IPAM.Config}}{{.Subnet}}{{end}}, Gateway={{range .IPAM.Config}}{{.Gateway}}{{end}}' 2>/dev/null || log_error "Some networks missing!"
echo ""

if [ "$REBUILD_BUILDX" = "yes" ]; then
    log_info "Buildx Builders:"
    docker buildx ls
    echo ""
fi

log_success "========================================"
log_success "Pi Network Reset Complete!"
log_success "========================================"
echo ""

log_info "Networks created per docker-build-process-plan.md:"
echo ""
log_info "1. $MAIN_NETWORK ($MAIN_SUBNET)"
log_info "   Services: Foundation, Core, Application, BLOCKCHAIN"
log_info "   Internet: ✅ Enabled (NAT)"
log_info "   Services: MongoDB, Redis, Elasticsearch, Auth, API Gateway,"
log_info "            Service Mesh, Blockchain Core, Blockchain Engine,"
log_info "            Session Anchoring, Block Manager, Data Chain,"
log_info "            Session Pipeline, RDP Services, Node Management, Admin"
echo ""
log_info "2. $TRON_NETWORK ($TRON_SUBNET)"
log_info "   Services: TRON Payment Services (ISOLATED)"
log_info "   Internet: ✅ Enabled (TRON network access)"
log_info "   Services: TRON Client, Payout Router, Wallet Manager,"
log_info "            USDT Manager, TRX Staking, Payment Gateway"
echo ""
log_info "3. $GUI_NETWORK ($GUI_SUBNET)"
log_info "   Services: GUI Integration"
log_info "   Internet: ✅ Enabled (NAT)"
log_info "   Services: Electron GUI components"
echo ""

if [ "$REBUILD_BUILDX" = "yes" ]; then
    log_info "✅ Buildx Builder: $BUILDER_NAME"
    log_info "   Platforms: linux/amd64, linux/arm64"
    log_info "   Driver: docker-container"
    log_info "   Network: host"
    log_info "   Status: Ready for ARM64 Pi builds"
    echo ""
fi

log_success "System ready for deployment!"
echo ""
log_info "Next steps:"
log_info "  1. Generate environment files:"
log_info "     bash scripts/config/generate-all-env-complete.sh"
echo ""
log_info "  2. Deploy Phase 1 (Foundation):"
log_info "     docker-compose --env-file configs/environment/.env.foundation \\"
log_info "                    -f configs/docker/docker-compose.foundation.yml up -d"
echo ""