#!/bin/bash
# Build Missing Components Script
# LUCID-STRICT Layer 1 Core Infrastructure
# Generated: 2025-10-04

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔧 LUCID Layer 1 Build System${NC}"
echo "================================"
echo ""

# Configuration
PLATFORM="${PLATFORM:-linux/arm64,linux/amd64}"
REGISTRY="${REGISTRY:-pickme}"
VERSION="${VERSION:-latest}"

# Build functions
build_service() {
    local service_name=$1
    local dockerfile=$2
    local context=$3
    
    echo -e "${BLUE}📦 Building ${service_name}...${NC}"
    
    docker buildx build \
        --platform ${PLATFORM} \
        --tag ${REGISTRY}/lucid:${service_name}-${VERSION} \
        --tag ${REGISTRY}/lucid:${service_name} \
        --file ${dockerfile} \
        ${context}
    
    echo -e "${GREEN}✅ ${service_name} built successfully${NC}"
}

# Build all Layer 1 services
echo -e "${YELLOW}🚀 Building Layer 1 services...${NC}"
echo ""

# Session Chunker
build_service "session-chunker" "sessions/core/Dockerfile.chunker" "."

# Session Encryptor
build_service "session-encryptor" "sessions/encryption/Dockerfile.encryptor" "."

# Merkle Builder
build_service "merkle-builder" "sessions/core/Dockerfile.merkle_builder" "."

# Session Orchestrator
build_service "session-orchestrator" "sessions/core/Dockerfile.orchestrator" "."

# Authentication Service
build_service "auth-service" "auth/Dockerfile.authentication" "."

# Push images (optional)
if [[ "$1" == "--push" ]]; then
    echo -e "${YELLOW}📤 Pushing images to registry...${NC}"
    
    docker push ${REGISTRY}/lucid:session-chunker-${VERSION}
    docker push ${REGISTRY}/lucid:session-encryptor-${VERSION}
    docker push ${REGISTRY}/lucid:merkle-builder-${VERSION}
    docker push ${REGISTRY}/lucid:session-orchestrator-${VERSION}
    docker push ${REGISTRY}/lucid:auth-service-${VERSION}
    
    echo -e "${GREEN}✅ All images pushed successfully${NC}"
fi

# Create deployment manifest
echo -e "${BLUE}📋 Creating deployment manifest...${NC}"
cat > deployment/layer1-manifest.json <<EOF
{
  "layer": 1,
  "phase": "foundation",
  "services": [
    {
      "name": "session-chunker",
      "image": "${REGISTRY}/lucid:session-chunker-${VERSION}",
      "port": 8081,
      "description": "Session data chunking with Zstd compression"
    },
    {
      "name": "session-encryptor",
      "image": "${REGISTRY}/lucid:session-encryptor-${VERSION}",
      "port": 8082,
      "description": "XChaCha20-Poly1305 encryption service"
    },
    {
      "name": "merkle-builder",
      "image": "${REGISTRY}/lucid:merkle-builder-${VERSION}",
      "port": 8083,
      "description": "BLAKE3 Merkle tree construction"
    },
    {
      "name": "session-orchestrator",
      "image": "${REGISTRY}/lucid:session-orchestrator-${VERSION}",
      "port": 8084,
      "description": "Session pipeline orchestration"
    },
    {
      "name": "auth-service",
      "image": "${REGISTRY}/lucid:auth-service-${VERSION}",
      "port": 8085,
      "description": "TRON address authentication service"
    }
  ],
  "built_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "platform": "${PLATFORM}",
  "registry": "${REGISTRY}"
}
EOF

# Create Pi deployment script
echo -e "${BLUE}🍓 Creating Pi deployment script...${NC}"
cat > scripts/deploy-layer1-pi.sh <<EOF
#!/bin/bash
# Pi 5 Layer 1 Deployment Script

set -e

echo "🚀 Deploying LUCID Layer 1 to Pi 5..."

# Pull images
echo "📥 Pulling Layer 1 images..."
docker pull ${REGISTRY}/lucid:session-chunker-${VERSION}
docker pull ${REGISTRY}/lucid:session-encryptor-${VERSION}
docker pull ${REGISTRY}/lucid:merkle-builder-${VERSION}
docker pull ${REGISTRY}/lucid:session-orchestrator-${VERSION}
docker pull ${REGISTRY}/lucid:auth-service-${VERSION}

# Initialize MongoDB
echo "🗄️ Initializing MongoDB schema..."
./scripts/init_mongodb_schema.sh

# Deploy services
echo "🐳 Starting Layer 1 services..."
docker-compose -f infrastructure/compose/lucid-dev-layer1.yaml --profile layer1 up -d

# Wait for services
echo "⏳ Waiting for services to be ready..."
sleep 30

# Health check
echo "🔍 Performing health checks..."
services=("8081" "8082" "8083" "8084" "8085")
for port in "\${services[@]}"; do
    if curl -fsS http://localhost:\$port/health &>/dev/null; then
        echo "✅ Service on port \$port: HEALTHY"
    else
        echo "❌ Service on port \$port: UNHEALTHY"
    fi
done

echo "🎉 Layer 1 deployment completed!"
echo ""
echo "Services available:"
echo "  Session Chunker: http://localhost:8081"
echo "  Session Encryptor: http://localhost:8082"
echo "  Merkle Builder: http://localhost:8083"
echo "  Session Orchestrator: http://localhost:8084"
echo "  Auth Service: http://localhost:8085"
EOF

chmod +x scripts/deploy-layer1-pi.sh

echo -e "${GREEN}🎉 Layer 1 build system complete!${NC}"
echo ""
echo -e "${BLUE}Usage:${NC}"
echo "  Build all services: ./scripts/build_missing_components.sh"
echo "  Build and push: ./scripts/build_missing_components.sh --push"
echo "  Deploy to Pi: ./scripts/deploy-layer1-pi.sh"
echo ""
echo -e "${GREEN}Ready for Layer 2 implementation!${NC}"