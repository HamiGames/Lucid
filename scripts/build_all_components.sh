#!/bin/bash
# LUCID Complete Build System - SPEC-1D Implementation
# Build all components with distroless Docker images

set -euo pipefail

# Configuration
REGISTRY="pickme"
TAG="latest"
PUSH="false"
NO_CACHE="false"
PLATFORMS="linux/arm64,linux/amd64"

echo "=== LUCID Complete Component Build System ==="

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --registry=*)
            REGISTRY="${1#*=}"
            shift
            ;;
        --tag=*)
            TAG="${1#*=}"
            shift
            ;;
        --push)
            PUSH="true"
            shift
            ;;
        --no-cache)
            NO_CACHE="true"
            shift
            ;;
        --platforms=*)
            PLATFORMS="${1#*=}"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Build arguments
BUILD_ARGS=""
if [ "$PUSH" = "true" ]; then
    BUILD_ARGS+=" --push"
fi
if [ "$NO_CACHE" = "true" ]; then
    BUILD_ARGS+=" --no-cache"
fi

echo "Build configuration:"
echo "  Registry: $REGISTRY"
echo "  Tag: $TAG"
echo "  Push: $PUSH"
echo "  No Cache: $NO_CACHE"
echo "  Platforms: $PLATFORMS"
echo ""

# Function to build component
build_component() {
    local component_name="$1"
    local dockerfile_path="$2"
    local context_path="$3"
    
    echo "Building $component_name..."
    
    if docker buildx build --platform "$PLATFORMS" \
        -t "$REGISTRY/lucid:$component_name" \
        -f "$dockerfile_path" \
        "$context_path" \
        $BUILD_ARGS; then
        echo "✅ $component_name built successfully"
    else
        echo "❌ $component_name build failed"
        return 1
    fi
}

# Build Session Pipeline Components
echo "=== Building Session Pipeline Components ==="
build_component "session-chunker" "sessions/core/Dockerfile.chunker" "sessions/core"
build_component "session-encryptor" "sessions/encryption/Dockerfile.encryptor" "sessions/encryption"
build_component "merkle-builder" "sessions/core/Dockerfile.merkle_builder" "sessions/core"
build_component "session-orchestrator" "sessions/core/Dockerfile.orchestrator" "sessions/core"

# Build Blockchain Components
echo "=== Building Blockchain Components ==="
build_component "on-system-chain-client" "blockchain/on_system_chain/Dockerfile.chain-client" "blockchain/on_system_chain"
build_component "tron-node-client" "blockchain/tron_node/Dockerfile.tron-client" "blockchain/tron_node"

# Build Node Components
echo "=== Building Node Components ==="
build_component "dht-crdt-node" "node/dht_crdt/Dockerfile.dht-node" "node/dht_crdt"

# Build Core Support Services (if they exist)
echo "=== Building Core Support Services ==="
if [ -f "02-network-security/tor/Dockerfile" ]; then
    build_component "tor-proxy" "02-network-security/tor/Dockerfile" "02-network-security/tor"
fi

if [ -f "02-network-security/tunnels/Dockerfile" ]; then
    build_component "tunnel-tools" "02-network-security/tunnels/Dockerfile" "02-network-security/tunnels"
fi

if [ -f "common/server-tools/Dockerfile" ]; then
    build_component "server-tools" "common/server-tools/Dockerfile" "common/server-tools"
fi

# Build API Gateway Services (if they exist)
echo "=== Building API Gateway Services ==="
if [ -f "03-api-gateway/api/Dockerfile.api" ]; then
    build_component "api-server" "03-api-gateway/api/Dockerfile.api" "03-api-gateway/api"
fi

if [ -f "03-api-gateway/gateway/Dockerfile.gateway" ]; then
    build_component "api-gateway" "03-api-gateway/gateway/Dockerfile.gateway" "03-api-gateway/gateway"
fi

# Build OpenAPI Services (if they exist)
echo "=== Building OpenAPI Services ==="
if [ -f "open-api/api/Dockerfile.api" ]; then
    build_component "openapi-server" "open-api/api/Dockerfile.api" "open-api/api"
fi

if [ -f "open-api/gateway/Dockerfile.gateway" ]; then
    build_component "openapi-gateway" "open-api/gateway/Dockerfile.gateway" "open-api/gateway"
fi

# Build Blockchain Core Services (if they exist)
echo "=== Building Blockchain Core Services ==="
if [ -f "04-blockchain-core/api/Dockerfile" ]; then
    build_component "blockchain-api" "04-blockchain-core/api/Dockerfile" "04-blockchain-core/api"
fi

if [ -f "04-blockchain-core/governance/Dockerfile" ]; then
    build_component "blockchain-governance" "04-blockchain-core/governance/Dockerfile" "04-blockchain-core/governance"
fi

if [ -f "04-blockchain-core/sessions-data/Dockerfile" ]; then
    build_component "blockchain-sessions-data" "04-blockchain-core/sessions-data/Dockerfile" "04-blockchain-core/sessions-data"
fi

if [ -f "04-blockchain-core/vm/Dockerfile" ]; then
    build_component "blockchain-vm" "04-blockchain-core/vm/Dockerfile" "04-blockchain-core/vm"
fi

if [ -f "04-blockchain-core/ledger/Dockerfile" ]; then
    build_component "blockchain-ledger" "04-blockchain-core/ledger/Dockerfile" "04-blockchain-core/ledger"
fi

# Build Legacy Blockchain API (if it exists)
if [ -f "blockchain/api/Dockerfile" ]; then
    build_component "blockchain-api-legacy" "blockchain/api/Dockerfile" "blockchain/api"
fi

echo ""
echo "=== Build Summary ==="
echo "All components built successfully!"
echo "Registry: $REGISTRY"
echo "Tag: $TAG"
echo "Platforms: $PLATFORMS"

if [ "$PUSH" = "true" ]; then
    echo "Images pushed to registry"
else
    echo "Images built locally (use --push to upload)"
fi

echo ""
echo "=== Available Images ==="
echo "Session Pipeline:"
echo "  - $REGISTRY/lucid:session-chunker"
echo "  - $REGISTRY/lucid:session-encryptor"
echo "  - $REGISTRY/lucid:merkle-builder"
echo "  - $REGISTRY/lucid:session-orchestrator"
echo ""
echo "Blockchain:"
echo "  - $REGISTRY/lucid:on-system-chain-client"
echo "  - $REGISTRY/lucid:tron-node-client"
echo ""
echo "Node Systems:"
echo "  - $REGISTRY/lucid:dht-crdt-node"
echo ""
echo "Core Support:"
echo "  - $REGISTRY/lucid:tor-proxy"
echo "  - $REGISTRY/lucid:tunnel-tools"
echo "  - $REGISTRY/lucid:server-tools"
echo ""
echo "API Services:"
echo "  - $REGISTRY/lucid:api-server"
echo "  - $REGISTRY/lucid:api-gateway"
echo "  - $REGISTRY/lucid:openapi-server"
echo "  - $REGISTRY/lucid:openapi-gateway"
echo ""
echo "Blockchain Core:"
echo "  - $REGISTRY/lucid:blockchain-api"
echo "  - $REGISTRY/lucid:blockchain-governance"
echo "  - $REGISTRY/lucid:blockchain-sessions-data"
echo "  - $REGISTRY/lucid:blockchain-vm"
echo "  - $REGISTRY/lucid:blockchain-ledger"
echo "  - $REGISTRY/lucid:blockchain-api-legacy"

echo ""
echo "=== Build Complete ==="
