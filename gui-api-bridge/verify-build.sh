#!/bin/bash
# File: gui-api-bridge/verify-build.sh
# Purpose: Verify GUI API Bridge service build completeness
# Usage: bash gui-api-bridge/verify-build.sh

set -e

echo "======================================================================"
echo "GUI API Bridge Service - Build Verification"
echo "======================================================================"
echo

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check file exists
check_file() {
    local file=$1
    local name=$2
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $name"
        return 0
    else
        echo -e "${RED}✗${NC} $name (missing: $file)"
        return 1
    fi
}

# Function to check directory exists
check_dir() {
    local dir=$1
    local name=$2
    
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓${NC} $name"
        return 0
    else
        echo -e "${RED}✗${NC} $name (missing: $dir)"
        return 1
    fi
}

passed=0
failed=0

# Phase 1: Foundation
echo "Phase 1: Foundation"
echo "---"
check_file "gui-api-bridge/Dockerfile.gui-api-bridge" "Dockerfile" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/requirements.txt" "requirements.txt" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/__init__.py" "__init__.py" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/entrypoint.py" "entrypoint.py" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/config.py" "config.py" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/config/env.gui-api-bridge.template" "env template" && ((passed++)) || ((failed++))
echo

# Phase 2: Core Service
echo "Phase 2: Core Service"
echo "---"
check_file "gui-api-bridge/gui-api-bridge/main.py" "main.py (FastAPI)" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/healthcheck.py" "healthcheck.py" && ((passed++)) || ((failed++))
echo

# Phase 3: Integration
echo "Phase 3: Integration"
echo "---"
check_file "gui-api-bridge/gui-api-bridge/integration/service_base.py" "service_base.py" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/integration/integration_manager.py" "integration_manager.py" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/integration/blockchain_client.py" "blockchain_client.py" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/integration/api_gateway_client.py" "api_gateway_client.py" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/integration/auth_service_client.py" "auth_service_client.py" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/integration/session_api_client.py" "session_api_client.py" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/integration/node_management_client.py" "node_management_client.py" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/integration/admin_interface_client.py" "admin_interface_client.py" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/integration/tron_client.py" "tron_client.py" && ((passed++)) || ((failed++))
echo

# Phase 4: Middleware
echo "Phase 4: Middleware"
echo "---"
check_file "gui-api-bridge/gui-api-bridge/middleware/auth.py" "auth.py (JWT)" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/middleware/rate_limit.py" "rate_limit.py" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/middleware/logging.py" "logging.py" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/middleware/cors.py" "cors.py" && ((passed++)) || ((failed++))
echo

# Phase 5: Routers
echo "Phase 5: Routers"
echo "---"
check_file "gui-api-bridge/gui-api-bridge/routers/user.py" "user.py (/api/v1/user)" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/routers/developer.py" "developer.py (/api/v1/developer)" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/routers/node.py" "node.py (/api/v1/node)" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/routers/admin.py" "admin.py (/api/v1/admin)" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/routers/websocket.py" "websocket.py (/ws)" && ((passed++)) || ((failed++))
echo

# Phase 6: Services
echo "Phase 6: Services"
echo "---"
check_file "gui-api-bridge/gui-api-bridge/services/routing_service.py" "routing_service.py" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/services/discovery_service.py" "discovery_service.py" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/services/websocket_service.py" "websocket_service.py" && ((passed++)) || ((failed++))
echo

# Phase 7: Models
echo "Phase 7: Models"
echo "---"
check_file "gui-api-bridge/gui-api-bridge/models/common.py" "common.py" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/models/auth.py" "auth.py" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/models/routing.py" "routing.py" && ((passed++)) || ((failed++))
echo

# Phase 8: Utilities
echo "Phase 8: Utilities"
echo "---"
check_file "gui-api-bridge/gui-api-bridge/utils/logging.py" "logging.py" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/utils/errors.py" "errors.py" && ((passed++)) || ((failed++))
check_file "gui-api-bridge/gui-api-bridge/utils/validation.py" "validation.py" && ((passed++)) || ((failed++))
echo

# Documentation
echo "Phase 9: Documentation"
echo "---"
check_file "gui-api-bridge/README.md" "README.md" && ((passed++)) || ((failed++))
echo

# Directories
echo "Directory Structure"
echo "---"
check_dir "gui-api-bridge/gui-api-bridge" "gui-api-bridge/" && ((passed++)) || ((failed++))
check_dir "gui-api-bridge/gui-api-bridge/integration" "integration/" && ((passed++)) || ((failed++))
check_dir "gui-api-bridge/gui-api-bridge/middleware" "middleware/" && ((passed++)) || ((failed++))
check_dir "gui-api-bridge/gui-api-bridge/routers" "routers/" && ((passed++)) || ((failed++))
check_dir "gui-api-bridge/gui-api-bridge/services" "services/" && ((passed++)) || ((failed++))
check_dir "gui-api-bridge/gui-api-bridge/models" "models/" && ((passed++)) || ((failed++))
check_dir "gui-api-bridge/gui-api-bridge/utils" "utils/" && ((passed++)) || ((failed++))
check_dir "gui-api-bridge/gui-api-bridge/config" "config/" && ((passed++)) || ((failed++))
echo

# Summary
echo "======================================================================"
echo "Summary"
echo "======================================================================"
echo -e "${GREEN}Passed:${NC} $passed"
if [ $failed -gt 0 ]; then
    echo -e "${RED}Failed:${NC} $failed"
else
    echo -e "${GREEN}Failed:${NC} 0"
fi

total=$((passed + failed))
echo "Total: $total"
echo

# Build readiness
if [ $failed -eq 0 ]; then
    echo -e "${GREEN}✓ BUILD COMPLETE - READY FOR TESTING${NC}"
    echo
    echo "Next steps:"
    echo "1. Build Docker image:"
    echo "   docker build -f gui-api-bridge/Dockerfile.gui-api-bridge -t pickme/lucid-gui-api-bridge:latest-arm64 ."
    echo
    echo "2. Test locally:"
    echo "   pip install -r gui-api-bridge/requirements.txt"
    echo "   python -m uvicorn gui_api_bridge.main:app --reload --port 8102"
    echo
    echo "3. Deploy via docker-compose:"
    echo "   docker-compose -f configs/docker/docker-compose.gui-integration.yml up"
    echo
    exit 0
else
    echo -e "${RED}✗ BUILD INCOMPLETE - MISSING FILES${NC}"
    exit 1
fi
