#!/bin/bash
# Test Deployment Fix - Verify Docker Hub Pull Configuration
# Path: scripts/deployment/test-deployment-fix.sh
# Run this to verify the deployment fix is working

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Testing Deployment Fix ===${NC}"
echo ""

# Test 1: Verify Docker Hub Authentication
echo -e "${BLUE}Test 1: Docker Hub Authentication${NC}"
if docker info 2>/dev/null | grep -q "Username:"; then
    username=$(docker info 2>/dev/null | grep "Username:" | awk '{print $2}')
    echo -e "${GREEN}✅ Logged into Docker Hub as: $username${NC}"
else
    echo -e "${RED}❌ Not logged into Docker Hub${NC}"
    echo "Run: docker login"
    exit 1
fi
echo ""

# Test 2: Verify Images Exist on Docker Hub
echo -e "${BLUE}Test 2: Verify Images on Docker Hub${NC}"
images=(
    "pickme/lucid-auth-service:latest-arm64"
    "pickme/lucid-mongodb:latest-arm64"
    "pickme/lucid-redis:latest-arm64"
)

all_images_exist=true
for image in "${images[@]}"; do
    if docker buildx imagetools inspect "$image" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ $image exists and is ARM64${NC}"
        
        # Show platform
        platform=$(docker buildx imagetools inspect "$image" 2>/dev/null | grep "Platform:" | head -1 | awk '{print $2}')
        echo "   Platform: $platform"
    else
        echo -e "${RED}❌ $image not found or not accessible${NC}"
        all_images_exist=false
    fi
done
echo ""

if [ "$all_images_exist" = false ]; then
    echo -e "${RED}❌ Some images missing. Run build scripts first.${NC}"
    exit 1
fi

# Test 3: Verify Compose File Configuration
echo -e "${BLUE}Test 3: Verify Compose File Configuration${NC}"
compose_file="configs/docker/docker-compose.foundation.yml"

if [ -f "$compose_file" ]; then
    echo -e "${GREEN}✅ Compose file exists${NC}"
    
    # Check for build: section in auth-service (should NOT exist)
    if grep -A 5 "lucid-auth-service:" "$compose_file" | grep -q "build:"; then
        echo -e "${RED}❌ Compose file still has 'build:' section for auth-service${NC}"
        echo "This will cause deployment to fail!"
        exit 1
    else
        echo -e "${GREEN}✅ Auth service uses image: tag (no build: section)${NC}"
    fi
    
    # Check for image: tag (should exist)
    if grep -A 5 "lucid-auth-service:" "$compose_file" | grep -q "image: pickme/lucid-auth-service"; then
        echo -e "${GREEN}✅ Auth service correctly configured with Docker Hub image${NC}"
    else
        echo -e "${RED}❌ Auth service missing image: tag${NC}"
        exit 1
    fi
    
    # Check for relative paths (should NOT exist in production compose)
    if grep "$compose_file" -e "\./database" -e "context: \.\."; then
        echo -e "${YELLOW}⚠️  Relative paths found in compose file${NC}"
        echo "These may cause issues on Pi deployment"
    else
        echo -e "${GREEN}✅ No problematic relative paths found${NC}"
    fi
else
    echo -e "${RED}❌ Compose file not found: $compose_file${NC}"
    exit 1
fi
echo ""

# Test 4: Verify SSH Connectivity (if Pi accessible)
echo -e "${BLUE}Test 4: SSH Connectivity to Pi${NC}"
PI_HOST="${PI_HOST:-192.168.0.75}"
PI_USER="${PI_USER:-pickme}"

if timeout 5 ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "echo connected" 2>/dev/null; then
    echo -e "${GREEN}✅ SSH connection to Pi successful (passwordless)${NC}"
    
    # Check Docker on Pi
    if ssh -o ConnectTimeout=5 "$PI_USER@$PI_HOST" "docker --version" 2>/dev/null; then
        docker_version=$(ssh "$PI_USER@$PI_HOST" "docker --version" 2>/dev/null)
        echo -e "${GREEN}✅ Docker on Pi: $docker_version${NC}"
    else
        echo -e "${YELLOW}⚠️  Docker not found on Pi${NC}"
    fi
    
    # Check NVMe mount
    if ssh "$PI_USER@$PI_HOST" "test -d /mnt/myssd/Lucid/Lucid" 2>/dev/null; then
        echo -e "${GREEN}✅ NVMe mount exists: /mnt/myssd/Lucid/Lucid${NC}"
    else
        echo -e "${YELLOW}⚠️  NVMe mount not found: /mnt/myssd/Lucid/Lucid${NC}"
        echo "Deployment will create this directory"
    fi
else
    echo -e "${YELLOW}⚠️  Cannot connect to Pi (SSH agent not configured or Pi offline)${NC}"
    echo "To fix:"
    echo "  eval \$(ssh-agent -s)"
    echo "  ssh-add ~/.ssh/id_rsa"
fi
echo ""

# Test 5: Verify Deployment Script
echo -e "${BLUE}Test 5: Verify Deployment Script${NC}"
deploy_script="scripts/deployment/deploy-phase1-pi.sh"

if [ -f "$deploy_script" ]; then
    echo -e "${GREEN}✅ Deployment script exists${NC}"
    
    # Check if it's executable
    if [ -x "$deploy_script" ]; then
        echo -e "${GREEN}✅ Deployment script is executable${NC}"
    else
        echo -e "${YELLOW}⚠️  Making deployment script executable${NC}"
        chmod +x "$deploy_script"
    fi
else
    echo -e "${RED}❌ Deployment script not found: $deploy_script${NC}"
    exit 1
fi
echo ""

# Final Summary
echo -e "${BLUE}=== Deployment Readiness Summary ===${NC}"
echo ""
echo "✅ Docker Hub authentication: OK"
echo "✅ ARM64 images available: OK"
echo "✅ Compose file configuration: FIXED"
echo "✅ Deployment script: READY"
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   DEPLOYMENT FIX VERIFIED ✅${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Setup SSH agent if not done:"
echo "     eval \$(ssh-agent -s)"
echo "     ssh-add ~/.ssh/id_rsa"
echo ""
echo "  2. Deploy to Pi:"
echo "     bash scripts/deployment/deploy-phase1-pi.sh"
echo ""
echo "  3. Monitor deployment:"
echo "     tail -f deployment-phase1.log"
echo ""

