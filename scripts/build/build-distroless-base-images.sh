#!/bin/bash
# Build Distroless Base Images for Lucid Project
# Creates all required distroless base images for deployment

set -euo pipefail

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REGISTRY="ghcr.io"
REPOSITORY="hamigames/lucid"
TAG="latest-arm64"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏗️  Building Lucid Distroless Base Images${NC}"
echo "=============================================="
echo "Registry: $REGISTRY"
echo "Repository: $REPOSITORY"
echo "Tag: $TAG"
echo ""

# Function to build image
build_image() {
    local service_name="$1"
    local dockerfile_path="$2"
    local context_path="$3"
    
    echo -e "${YELLOW}Building $service_name...${NC}"
    
    # Build the image
    docker buildx build \
        --platform linux/arm64 \
        --file "$dockerfile_path" \
        --tag "$REGISTRY/$REPOSITORY/$service_name:$TAG" \
        --tag "$REGISTRY/$REPOSITORY/$service_name:latest" \
        --push \
        "$context_path"
    
    echo -e "${GREEN}✅ $service_name built successfully${NC}"
}

# Function to create requirements.txt for a service
create_requirements() {
    local service_name="$1"
    local requirements_file="$2"
    
    echo -e "${YELLOW}Creating requirements.txt for $service_name...${NC}"
    
    cat > "$requirements_file" << EOF
# Requirements for $service_name
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Core dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Database dependencies
motor==3.3.2
redis==5.0.1
elasticsearch==8.11.0

# Authentication and security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# HTTP client
httpx==0.25.2
aiohttp==3.9.1

# Logging and monitoring
structlog==23.2.0
prometheus-client==0.19.0

# Utilities
python-dotenv==1.0.0
click==8.1.7
rich==13.7.0

# Development and testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
EOF
    
    echo -e "${GREEN}✅ Requirements.txt created for $service_name${NC}"
}

# Main build function
main() {
    echo -e "${BLUE}📋 Building Distroless Base Images${NC}"
    echo "====================================="
    
    # Create build directory
    mkdir -p "$PROJECT_ROOT/build/distroless"
    
    # Build API Gateway
    echo -e "${BLUE}🔧 Building API Gateway...${NC}"
    create_requirements "api-gateway" "$PROJECT_ROOT/build/distroless/requirements-api-gateway.txt"
    build_image "api-gateway" "infrastructure/docker/distroless/base/Dockerfile.api-gateway" "$PROJECT_ROOT"
    
    # Build Blockchain Core
    echo -e "${BLUE}🔧 Building Blockchain Core...${NC}"
    create_requirements "blockchain-core" "$PROJECT_ROOT/build/distroless/requirements-blockchain-core.txt"
    build_image "blockchain-core" "infrastructure/docker/distroless/base/Dockerfile.blockchain-core" "$PROJECT_ROOT"
    
    # Build Auth Service
    echo -e "${BLUE}🔧 Building Auth Service...${NC}"
    create_requirements "auth-service" "$PROJECT_ROOT/build/distroless/requirements-auth-service.txt"
    build_image "auth-service" "infrastructure/docker/distroless/base/Dockerfile.auth-service" "$PROJECT_ROOT"
    
    # Build Session Pipeline
    echo -e "${BLUE}🔧 Building Session Pipeline...${NC}"
    create_requirements "session-pipeline" "$PROJECT_ROOT/build/distroless/requirements-session-pipeline.txt"
    build_image "session-pipeline" "infrastructure/docker/multi-stage/Dockerfile.gui" "$PROJECT_ROOT"
    
    # Build RDP Services
    echo -e "${BLUE}🔧 Building RDP Services...${NC}"
    create_requirements "rdp-server-manager" "$PROJECT_ROOT/build/distroless/requirements-rdp-server-manager.txt"
    build_image "rdp-server-manager" "infrastructure/docker/multi-stage/Dockerfile.rdp" "$PROJECT_ROOT"
    
    # Build Node Management
    echo -e "${BLUE}🔧 Building Node Management...${NC}"
    create_requirements "node-management" "$PROJECT_ROOT/build/distroless/requirements-node-management.txt"
    build_image "node-management" "infrastructure/docker/multi-stage/Dockerfile.node" "$PROJECT_ROOT"
    
    # Build Storage Services
    echo -e "${BLUE}🔧 Building Storage Services...${NC}"
    create_requirements "storage-database" "$PROJECT_ROOT/build/distroless/requirements-storage-database.txt"
    build_image "storage-database" "infrastructure/docker/multi-stage/Dockerfile.storage" "$PROJECT_ROOT"
    
    # Build Database Services
    echo -e "${BLUE}🔧 Building Database Services...${NC}"
    create_requirements "mongodb" "$PROJECT_ROOT/build/distroless/requirements-mongodb.txt"
    build_image "mongodb" "infrastructure/docker/multi-stage/Dockerfile.database" "$PROJECT_ROOT"
    
    # Build VM Services
    echo -e "${BLUE}🔧 Building VM Services...${NC}"
    create_requirements "vm-management" "$PROJECT_ROOT/build/distroless/requirements-vm-management.txt"
    build_image "vm-management" "infrastructure/docker/multi-stage/Dockerfile.vm" "$PROJECT_ROOT"
    
    # Build Admin Interface
    echo -e "${BLUE}🔧 Building Admin Interface...${NC}"
    create_requirements "admin-interface" "$PROJECT_ROOT/build/distroless/requirements-admin-interface.txt"
    build_image "admin-interface" "infrastructure/docker/multi-stage/Dockerfile.gui" "$PROJECT_ROOT"
    
    echo -e "${GREEN}🎉 All distroless base images built successfully!${NC}"
    echo ""
    echo -e "${BLUE}📊 Built Images:${NC}"
    echo "==============="
    echo "• $REGISTRY/$REPOSITORY/api-gateway:$TAG"
    echo "• $REGISTRY/$REPOSITORY/blockchain-core:$TAG"
    echo "• $REGISTRY/$REPOSITORY/auth-service:$TAG"
    echo "• $REGISTRY/$REPOSITORY/session-pipeline:$TAG"
    echo "• $REGISTRY/$REPOSITORY/rdp-server-manager:$TAG"
    echo "• $REGISTRY/$REPOSITORY/node-management:$TAG"
    echo "• $REGISTRY/$REPOSITORY/storage-database:$TAG"
    echo "• $REGISTRY/$REPOSITORY/mongodb:$TAG"
    echo "• $REGISTRY/$REPOSITORY/vm-management:$TAG"
    echo "• $REGISTRY/$REPOSITORY/admin-interface:$TAG"
    echo ""
    echo -e "${GREEN}✅ All images are ready for deployment${NC}"
}

# Run main function
main "$@"
