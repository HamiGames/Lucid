#!/bin/bash
################################################################################
# Lucid Pi Docker Setup Verification Script
# Location: /mnt/myssd/Lucid/Lucid/scripts/verification/verify-pi-docker-setup.sh
# Purpose: Verify all Docker images, networks, buildx, and .env scripts on Pi
################################################################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project base directory
PROJECT_DIR="/mnt/myssd/Lucid/Lucid"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Lucid Pi Docker Setup Verification${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Verify we're in the correct directory
cd "${PROJECT_DIR}" || { echo -e "${RED}ERROR: Cannot access ${PROJECT_DIR}${NC}"; exit 1; }
echo -e "${GREEN}✓ Working directory: $(pwd)${NC}"
echo ""

################################################################################
# 1. EXTRACT AND VERIFY DOCKER IMAGES
################################################################################

echo -e "${BLUE}[1/5] Checking Docker Images${NC}"
echo "----------------------------------------"

# Complete list of all images from docker-build-process-plan.md
REQUIRED_IMAGES=(
    # Base Images
    "pickme/lucid-base:python-distroless-arm64"
    "pickme/lucid-base:java-distroless-arm64"
    
    # Phase 1: Foundation Services
    "pickme/lucid-mongodb:latest-arm64"
    "pickme/lucid-redis:latest-arm64"
    "pickme/lucid-elasticsearch:latest-arm64"
    "pickme/lucid-auth-service:latest-arm64"
    
    # Phase 2: Core Services
    "pickme/lucid-api-gateway:latest-arm64"
    "pickme/lucid-service-mesh-controller:latest-arm64"
    "pickme/lucid-blockchain-engine:latest-arm64"
    "pickme/lucid-session-anchoring:latest-arm64"
    "pickme/lucid-block-manager:latest-arm64"
    "pickme/lucid-data-chain:latest-arm64"
    
    # Phase 3: Application Services - Session Management
    "pickme/lucid-session-pipeline:latest-arm64"
    "pickme/lucid-session-recorder:latest-arm64"
    "pickme/lucid-chunk-processor:latest-arm64"
    "pickme/lucid-session-storage:latest-arm64"
    "pickme/lucid-session-api:latest-arm64"
    
    # Phase 3: Application Services - RDP Services
    "pickme/lucid-rdp-server-manager:latest-arm64"
    "pickme/lucid-xrdp-integration:latest-arm64"
    "pickme/lucid-session-controller:latest-arm64"
    "pickme/lucid-resource-monitor:latest-arm64"
    
    # Phase 3: Application Services - Node Management
    "pickme/lucid-node-management:latest-arm64"
    
    # Phase 4: Support Services - Admin
    "pickme/lucid-admin-interface:latest-arm64"
    
    # Phase 4: Support Services - TRON Payment (Isolated)
    "pickme/lucid-tron-client:latest-arm64"
    "pickme/lucid-payout-router:latest-arm64"
    "pickme/lucid-wallet-manager:latest-arm64"
    "pickme/lucid-usdt-manager:latest-arm64"
    "pickme/lucid-trx-staking:latest-arm64"
    "pickme/lucid-payment-gateway:latest-arm64"
)

PRESENT_IMAGES=()
MISSING_IMAGES=()

for IMAGE in "${REQUIRED_IMAGES[@]}"; do
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${IMAGE}$"; then
        echo -e "${GREEN}✓ Present:${NC} ${IMAGE}"
        PRESENT_IMAGES+=("$IMAGE")
    else
        echo -e "${YELLOW}✗ Missing:${NC} ${IMAGE}"
        MISSING_IMAGES+=("$IMAGE")
    fi
done

echo ""
echo -e "${BLUE}Summary:${NC} ${GREEN}${#PRESENT_IMAGES[@]} present${NC}, ${YELLOW}${#MISSING_IMAGES[@]} missing${NC} (out of ${#REQUIRED_IMAGES[@]} total)"
echo ""

################################################################################
# 2. VERIFY DOCKER NETWORKS
################################################################################

echo -e "${BLUE}[2/5] Checking Docker Networks${NC}"
echo "----------------------------------------"

REQUIRED_NETWORKS=(
    "lucid-pi-network"
    "lucid-tron-isolated"
)

NETWORK_STATUS=0

for NETWORK in "${REQUIRED_NETWORKS[@]}"; do
    if docker network ls --format "{{.Name}}" | grep -q "^${NETWORK}$"; then
        echo -e "${GREEN}✓ Network exists:${NC} ${NETWORK}"
        
        # Get network details
        DRIVER=$(docker network inspect "$NETWORK" --format '{{.Driver}}')
        SUBNET=$(docker network inspect "$NETWORK" --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}')
        echo -e "  ${BLUE}Driver:${NC} ${DRIVER}, ${BLUE}Subnet:${NC} ${SUBNET}"
    else
        echo -e "${RED}✗ Network missing:${NC} ${NETWORK}"
        NETWORK_STATUS=1
    fi
done

echo ""

################################################################################
# 3. VERIFY DOCKER BUILDX
################################################################################

echo -e "${BLUE}[3/5] Checking Docker Buildx${NC}"
echo "----------------------------------------"

if command -v docker &> /dev/null; then
    if docker buildx version &> /dev/null; then
        BUILDX_VERSION=$(docker buildx version)
        echo -e "${GREEN}✓ Docker Buildx available:${NC} ${BUILDX_VERSION}"
        
        # List builders
        echo ""
        echo -e "${BLUE}Available builders:${NC}"
        docker buildx ls
    else
        echo -e "${RED}✗ Docker Buildx not available${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Docker command not found${NC}"
    exit 1
fi

echo ""

################################################################################
# 4. VERIFY .ENV GENERATION SCRIPTS
################################################################################

echo -e "${BLUE}[4/5] Checking .env Generation Scripts${NC}"
echo "----------------------------------------"

ENV_SCRIPTS=(
    "scripts/config/generate-all-env.sh"
)

ENV_FILES=(
    "configs/environment/.env.pi-build"
    "configs/environment/.env.foundation"
    "configs/environment/.env.core"
    "configs/environment/.env.application"
    "configs/environment/.env.support"
    "configs/environment/.env.gui"
)

# Check scripts exist
for SCRIPT in "${ENV_SCRIPTS[@]}"; do
    SCRIPT_PATH="${PROJECT_DIR}/${SCRIPT}"
    if [ -f "$SCRIPT_PATH" ]; then
        echo -e "${GREEN}✓ Script exists:${NC} ${SCRIPT}"
        
        # Check if executable
        if [ -x "$SCRIPT_PATH" ]; then
            echo -e "  ${GREEN}Executable: Yes${NC}"
        else
            echo -e "  ${YELLOW}Executable: No (can be fixed with chmod +x)${NC}"
        fi
    else
        echo -e "${RED}✗ Script missing:${NC} ${SCRIPT}"
    fi
done

echo ""

# Check .env files exist
echo -e "${BLUE}Required .env files:${NC}"
for ENV_FILE in "${ENV_FILES[@]}"; do
    ENV_PATH="${PROJECT_DIR}/${ENV_FILE}"
    if [ -f "$ENV_PATH" ]; then
        echo -e "${GREEN}✓ Present:${NC} ${ENV_FILE}"
        
        # Check for placeholders
        if grep -q '\${' "$ENV_PATH" 2>/dev/null; then
            echo -e "  ${YELLOW}⚠ Contains placeholders - needs generation${NC}"
        else
            echo -e "  ${GREEN}No placeholders detected${NC}"
        fi
    else
        echo -e "${YELLOW}✗ Missing:${NC} ${ENV_FILE} (will be generated)"
    fi
done

echo ""

################################################################################
# 5. VERIFY DEPLOYMENT SCRIPTS PATHS
################################################################################

echo -e "${BLUE}[5/5] Checking Deployment Scripts${NC}"
echo "----------------------------------------"

DEPLOYMENT_SCRIPTS=(
    "scripts/deployment/deploy-phase1-pi.sh"
    "scripts/deployment/deploy-phase2-pi.sh"
    "scripts/deployment/deploy-phase3-pi.sh"
    "scripts/deployment/deploy-phase4-pi.sh"
)

for SCRIPT in "${DEPLOYMENT_SCRIPTS[@]}"; do
    SCRIPT_PATH="${PROJECT_DIR}/${SCRIPT}"
    if [ -f "$SCRIPT_PATH" ]; then
        echo -e "${GREEN}✓ Script exists:${NC} ${SCRIPT}"
    else
        echo -e "${YELLOW}✗ Script missing:${NC} ${SCRIPT}"
    fi
done

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Verification Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${BLUE}Docker Images:${NC} ${GREEN}${#PRESENT_IMAGES[@]} present${NC}, ${YELLOW}${#MISSING_IMAGES[@]} missing${NC}"
echo -e "${BLUE}Networks:${NC} $([ $NETWORK_STATUS -eq 0 ] && echo -e "${GREEN}All present${NC}" || echo -e "${RED}Some missing${NC}")"
echo -e "${BLUE}Buildx:${NC} ${GREEN}Available${NC}"
echo ""

################################################################################
# PULL MISSING IMAGES (OPTIONAL)
################################################################################

if [ ${#MISSING_IMAGES[@]} -gt 0 ]; then
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}Missing Images Detected${NC}"
    echo -e "${YELLOW}========================================${NC}"
    echo ""
    echo -e "${YELLOW}The following ${#MISSING_IMAGES[@]} images need to be pulled:${NC}"
    for IMG in "${MISSING_IMAGES[@]}"; do
        echo "  - $IMG"
    done
    echo ""
    echo -e "${BLUE}To pull all missing images, run:${NC}"
    echo -e "${GREEN}  bash scripts/verification/pull-missing-images.sh${NC}"
    echo ""
fi

echo -e "${GREEN}✓ Verification complete!${NC}"

