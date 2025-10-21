#!/bin/bash
################################################################################
# Lucid Pi - Pull Missing Docker Images Script
# Location: /mnt/myssd/Lucid/Lucid/scripts/verification/pull-missing-images.sh
# Purpose: Pull all required Docker images that are missing from local registry
################################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="/mnt/myssd/Lucid/Lucid"
cd "${PROJECT_DIR}" || exit 1

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Pulling Missing Lucid Docker Images${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Complete list of all images
ALL_IMAGES=(
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
    
    # Phase 3: Application Services
    "pickme/lucid-session-pipeline:latest-arm64"
    "pickme/lucid-session-recorder:latest-arm64"
    "pickme/lucid-chunk-processor:latest-arm64"
    "pickme/lucid-session-storage:latest-arm64"
    "pickme/lucid-session-api:latest-arm64"
    "pickme/lucid-rdp-server-manager:latest-arm64"
    "pickme/lucid-xrdp-integration:latest-arm64"
    "pickme/lucid-session-controller:latest-arm64"
    "pickme/lucid-resource-monitor:latest-arm64"
    "pickme/lucid-node-management:latest-arm64"
    
    # Phase 4: Support Services
    "pickme/lucid-admin-interface:latest-arm64"
    "pickme/lucid-tron-client:latest-arm64"
    "pickme/lucid-payout-router:latest-arm64"
    "pickme/lucid-wallet-manager:latest-arm64"
    "pickme/lucid-usdt-manager:latest-arm64"
    "pickme/lucid-trx-staking:latest-arm64"
    "pickme/lucid-payment-gateway:latest-arm64"
)

PULLED=0
SKIPPED=0
FAILED=0

for IMAGE in "${ALL_IMAGES[@]}"; do
    # Check if image already exists locally
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${IMAGE}$"; then
        echo -e "${GREEN}✓ Already present:${NC} ${IMAGE}"
        SKIPPED=$((SKIPPED + 1))
    else
        echo -e "${YELLOW}⬇ Pulling:${NC} ${IMAGE}"
        
        if docker pull --platform linux/arm64 "$IMAGE" 2>&1; then
            echo -e "${GREEN}✓ Successfully pulled:${NC} ${IMAGE}"
            PULLED=$((PULLED + 1))
        else
            echo -e "${RED}✗ Failed to pull:${NC} ${IMAGE}"
            echo -e "${YELLOW}  (Image may not exist on Docker Hub yet)${NC}"
            FAILED=$((FAILED + 1))
        fi
    fi
    echo ""
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Pull Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Pulled:${NC}  $PULLED"
echo -e "${YELLOW}Skipped:${NC} $SKIPPED (already present)"
echo -e "${RED}Failed:${NC}  $FAILED"
echo ""

if [ $FAILED -gt 0 ]; then
    echo -e "${YELLOW}Note: Failed images likely haven't been built yet.${NC}"
    echo -e "${YELLOW}They will be available after running the build phases.${NC}"
fi

echo -e "${GREEN}✓ Pull process complete!${NC}"

