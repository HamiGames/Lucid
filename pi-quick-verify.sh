#!/bin/bash
################################################################################
# Quick Pi Verification - One Command Execution
# Copy this entire script to Pi and run: bash pi-quick-verify.sh
################################################################################

echo "============================================"
echo "Lucid Pi Quick Verification"
echo "============================================"
echo ""

# Ensure we're in the correct directory
cd /mnt/myssd/Lucid/Lucid || { echo "ERROR: Cannot access project directory"; exit 1; }
echo "Working directory: $(pwd)"
echo ""

# Make scripts executable
echo "[1/5] Setting script permissions..."
chmod +x scripts/verification/verify-pi-docker-setup.sh 2>/dev/null || true
chmod +x scripts/verification/pull-missing-images.sh 2>/dev/null || true
chmod +x scripts/config/generate-all-env.sh 2>/dev/null || true
echo "✓ Permissions set"
echo ""

# Check if verification script exists
if [ -f "scripts/verification/verify-pi-docker-setup.sh" ]; then
    echo "[2/5] Running Docker setup verification..."
    bash scripts/verification/verify-pi-docker-setup.sh
else
    echo "⚠ Verification script not found. Please pull latest code from GitHub."
    echo ""
    echo "[2/5] Running manual checks..."
    
    # Manual Docker check
    echo "Docker Status:"
    docker info | grep -E "Version|Architecture|CPUs|Total Memory|Server Version"
    echo ""
    
    # Manual Network check
    echo "Docker Networks:"
    docker network ls | grep -E "lucid-pi-network|lucid-tron-isolated|NAME"
    echo ""
    
    # Manual Buildx check
    echo "Docker Buildx:"
    docker buildx version
    echo ""
    
    # Manual Images check
    echo "Lucid Docker Images:"
    docker images | grep pickme/lucid
    echo ""
fi

echo "[3/5] Checking .env files..."
if [ -d "configs/environment" ]; then
    echo "Existing .env files:"
    ls -lah configs/environment/ | grep "\.env"
    
    # Check for placeholders
    echo ""
    echo "Checking for placeholders..."
    if grep -r '\${' configs/environment/ 2>/dev/null; then
        echo "⚠ Placeholders found - regeneration needed"
    else
        echo "✓ No placeholders detected"
    fi
else
    echo "⚠ Environment configs directory not found"
fi
echo ""

echo "[4/5] Disk Space Check..."
df -h /mnt/myssd | grep -E "Filesystem|myssd"
echo ""

echo "[5/5] Summary..."
echo "Architecture: $(uname -m)"
echo "Docker: $(docker --version)"
echo "Compose: $(docker compose version)"
echo "Buildx: $(docker buildx version)"
echo ""

echo "============================================"
echo "Verification Complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. If images are missing, run: bash scripts/verification/pull-missing-images.sh"
echo "2. If .env files missing, run: bash scripts/config/generate-all-env.sh"
echo "3. Check PI_VERIFICATION_INSTRUCTIONS.md for detailed guidance"

