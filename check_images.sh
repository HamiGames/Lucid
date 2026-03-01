#!/bin/bash

echo "Ì¥ç LUCID PROJECT - 35 IMAGES AVAILABILITY CHECK"
echo "================================================"
echo ""

# Function to check image availability
check_image() {
    local image_name="$1"
    local phase="$2"
    local description="$3"
    
    echo -n "Checking $image_name... "
    
    if docker pull "$image_name" >/dev/null 2>&1; then
        echo "‚úÖ AVAILABLE"
        return 0
    else
        echo "‚ùå MISSING"
        return 1
    fi
}

echo "Ì≥ã PHASE 1: BASE INFRASTRUCTURE (3 images)"
echo "-------------------------------------------"
check_image "pickme/lucid-base:python-distroless-arm64" "Phase 1" "Python Distroless Base"
check_image "pickme/lucid-base:java-distroless-arm64" "Phase 1" "Java Distroless Base"
check_image "pickme/lucid-base:latest-arm64" "Phase 1" "Base Latest"

echo ""
echo "Ì≥ã PHASE 2: FOUNDATION SERVICES (4 images)"
echo "-------------------------------------------"
check_image "pickme/lucid-mongodb:latest-arm64" "Phase 2" "MongoDB Container"
check_image "pickme/lucid-redis:latest-arm64" "Phase 2" "Redis Container"
check_image "pickme/lucid-elasticsearch:latest-arm64" "Phase 2" "Elasticsearch Container"
check_image "pickme/lucid-auth-service:latest-arm64" "Phase 2" "Auth Service"

echo ""
echo "Ì≥ã PHASE 3: CORE SERVICES (6 images)"
echo "-------------------------------------------"
check_image "pickme/lucid-api-gateway:latest-arm64" "Phase 3" "API Gateway"
check_image "pickme/lucid-service-mesh-controller:latest-arm64" "Phase 3" "Service Mesh Controller"
check_image "pickme/lucid-blockchain-engine:latest-arm64" "Phase 3" "Blockchain Engine"
check_image "pickme/lucid-session-anchoring:latest-arm64" "Phase 3" "Session Anchoring"
check_image "pickme/lucid-block-manager:latest-arm64" "Phase 3" "Block Manager"
check_image "pickme/lucid-data-chain:latest-arm64" "Phase 3" "Data Chain"

echo ""
echo "Ì≥ã PHASE 4: APPLICATION SERVICES (10 images)"
echo "-------------------------------------------"
check_image "pickme/lucid-session-pipeline:latest-arm64" "Phase 4" "Session Pipeline"
check_image "pickme/lucid-session-recorder:latest-arm64" "Phase 4" "Session Recorder"
check_image "pickme/lucid-chunk-processor:latest-arm64" "Phase 4" "Chunk Processor"
check_image "pickme/lucid-session-storage:latest-arm64" "Phase 4" "Session Storage"
check_image "pickme/lucid-session-api:latest-arm64" "Phase 4" "Session API"
check_image "pickme/lucid-rdp-server-manager:latest-arm64" "Phase 4" "RDP Server Manager"
check_image "pickme/lucid-rdp-xrdp:latest-arm64" "Phase 4" "RDP XRDP"
check_image "pickme/lucid-rdp-controller:latest-arm64" "Phase 4" "RDP Controller"
check_image "pickme/lucid-rdp-monitor:latest-arm64" "Phase 4" "RDP Monitor"
check_image "pickme/lucid-node-management:latest-arm64" "Phase 4" "Node Management"

echo ""
echo "Ì≥ã PHASE 5: SUPPORT SERVICES (7 images)"
echo "-------------------------------------------"
check_image "pickme/lucid-admin-interface:latest-arm64" "Phase 5" "Admin Interface"
check_image "pickme/lucid-tron-client:latest-arm64" "Phase 5" "TRON Client"
check_image "pickme/lucid-payout-router:latest-arm64" "Phase 5" "Payout Router"
check_image "pickme/lucid-wallet-manager:latest-arm64" "Phase 5" "Wallet Manager"
check_image "pickme/lucid-usdt-manager:latest-arm64" "Phase 5" "USDT Manager"
check_image "pickme/lucid-trx-staking:latest-arm64" "Phase 5" "TRX Staking"
check_image "pickme/lucid-payment-gateway:latest-arm64" "Phase 5" "Payment Gateway"

echo ""
echo "Ì≥ã PHASE 6: SPECIALIZED SERVICES (5 images)"
echo "-------------------------------------------"
check_image "pickme/lucid-gui:latest-arm64" "Phase 6" "GUI Services"
check_image "pickme/lucid-rdp:latest-arm64" "Phase 6" "RDP Services"
check_image "pickme/lucid-vm:latest-arm64" "Phase 6" "VM Services"
check_image "pickme/lucid-database:latest-arm64" "Phase 6" "Database Services"
check_image "pickme/lucid-storage:latest-arm64" "Phase 6" "Storage Services"

echo ""
echo "ÌæØ CHECK COMPLETE"
