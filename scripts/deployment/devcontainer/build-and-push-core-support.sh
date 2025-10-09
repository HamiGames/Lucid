#!/bin/bash
# LUCID CORE SUPPORT SERVICES - Build & Push Script
# Builds and pushes all core infrastructure services from lucid-dev.yaml
# GENIUS-LEVEL implementation with LUCID-STRICT compliance
# Path: scripts/devcontainer/build-and-push-core-support.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LUCID_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${LUCID_ROOT}/infrastructure/compose/lucid-dev.yaml"
DOCKER_REGISTRY="pickme/lucid"
BUILD_TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
BUILD_TAG="core-support-${BUILD_TIMESTAMP}"

# Multi-platform support for Pi deployment
PLATFORMS="linux/amd64,linux/arm64"

# Core support services to build and push
CORE_SERVICES=(
    "tor-proxy"
    "lucid_api"
    "lucid_api_gateway"
    "tunnel-tools"
    "server-tools"
)

# Service image mapping (service -> final image tag)
declare -A SERVICE_IMAGES=(
    ["tor-proxy"]="tor-proxy"
    ["lucid_api"]="api-server"
    ["lucid_api_gateway"]="api-gateway"
    ["tunnel-tools"]="tunnel-tools"
    ["server-tools"]="server-tools"
)

log() { echo -e "${BLUE}[CORE-SUPPORT-BUILD] $1${NC}"; }
success() { echo -e "${GREEN}[SUCCESS] $1${NC}"; }
warn() { echo -e "${YELLOW}[WARNING] $1${NC}"; }
error() { echo -e "${RED}[ERROR] $1${NC}"; }
section() { echo -e "${BOLD}${CYAN}=== $1 ===${NC}"; }

# Pre-flight checks
preflight_checks() {
    section "Pre-flight Checks"
    
    # Verify we're in DevContainer or have proper Docker setup
    if ! docker buildx version >/dev/null 2>&1; then
        error "Docker Buildx not available. Are you running in DevContainer?"
        exit 1
    fi
    
    # Verify lucid-dev.yaml exists
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        error "Core support compose file not found: $COMPOSE_FILE"
        exit 1
    fi
    success "Found core support compose file"
    
    # Verify all service contexts exist
    for service in "${CORE_SERVICES[@]}"; do
        case $service in
            "tor-proxy")
                context_path="${LUCID_ROOT}/02-network-security/tor"
                dockerfile="Dockerfile"
                ;;
            "lucid_api")
                context_path="${LUCID_ROOT}/03-api-gateway/api"
                dockerfile="Dockerfile.api"
                ;;
            "lucid_api_gateway")
                context_path="${LUCID_ROOT}/03-api-gateway/gateway"
                dockerfile="Dockerfile.gateway"
                ;;
            "tunnel-tools")
                context_path="${LUCID_ROOT}/02-network-security/tunnels"
                dockerfile="Dockerfile"
                ;;
            "server-tools")
                context_path="${LUCID_ROOT}/common/server-tools"
                dockerfile="Dockerfile"
                ;;
        esac
        
        if [[ ! -f "${context_path}/${dockerfile}" ]]; then
            error "Service ${service} Dockerfile not found: ${context_path}/${dockerfile}"
            exit 1
        fi
        success "Verified ${service} context: ${context_path}"
    done
    
    # Check Docker Hub login
    if ! docker info | grep -q "Username:"; then
        warn "Not logged into Docker Hub. You may need to run: docker login"
    else
        success "Docker Hub authentication verified"
    fi
    
    # Clear buildx volumes as per rules
    log "Clearing all Docker buildx volumes for fresh state"
    docker buildx prune -f --all || true
    success "Buildx volumes cleared"
}

# Setup buildx builder
setup_buildx() {
    section "Setting Up Multi-Platform Builder"
    
    BUILDER_NAME="lucid-core-builder"
    
    # Remove existing builder if it exists
    docker buildx rm "$BUILDER_NAME" 2>/dev/null || true
    
    # Create new builder with Pi support
    docker buildx create --name "$BUILDER_NAME" \
        --driver docker-container \
        --platform "$PLATFORMS" \
        --bootstrap
    
    docker buildx use "$BUILDER_NAME"
    docker buildx inspect --bootstrap
    
    success "Multi-platform builder ready: $BUILDER_NAME"
}

# Build and push individual service
build_and_push_service() {
    local service="$1"
    local image_name="${SERVICE_IMAGES[$service]}"
    local full_image="${DOCKER_REGISTRY}:${image_name}"
    local build_image="${DOCKER_REGISTRY}:${image_name}-${BUILD_TAG}"
    
    section "Building & Pushing: $service"
    log "Service: $service -> Image: $image_name"
    log "Registry: $full_image"
    
    # Determine build context and dockerfile
    case $service in
        "tor-proxy")
            context_path="${LUCID_ROOT}/02-network-security/tor"
            dockerfile="Dockerfile"
            ;;
        "lucid_api")
            context_path="${LUCID_ROOT}/03-api-gateway/api"
            dockerfile="Dockerfile.api"
            ;;
        "lucid_api_gateway")
            context_path="${LUCID_ROOT}/03-api-gateway/gateway"
            dockerfile="Dockerfile.gateway"
            ;;
        "tunnel-tools")
            context_path="${LUCID_ROOT}/02-network-security/tunnels"
            dockerfile="Dockerfile"
            ;;
        "server-tools")
            context_path="${LUCID_ROOT}/common/server-tools"
            dockerfile="Dockerfile"
            ;;
    esac
    
    log "Building from context: $context_path"
    log "Using Dockerfile: $dockerfile"
    log "Platforms: $PLATFORMS"
    
    # Build and push with proper tag management
    cd "$context_path"
    
    docker buildx build \
        --platform "$PLATFORMS" \
        --file "$dockerfile" \
        --tag "$full_image" \
        --tag "$build_image" \
        --tag "${DOCKER_REGISTRY}:${image_name}-latest" \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        --build-arg BUILD_TIMESTAMP="$BUILD_TIMESTAMP" \
        --build-arg BUILD_VERSION="core-support-1.0.0" \
        --cache-from type=registry,ref="${DOCKER_REGISTRY}:${image_name}-buildcache" \
        --cache-to type=registry,ref="${DOCKER_REGISTRY}:${image_name}-buildcache",mode=max \
        --push \
        .
    
    success "✅ Built and pushed: $service -> $full_image"
    
    cd "$LUCID_ROOT"
}

# Build and push all services
build_all_services() {
    section "Building All Core Support Services"
    
    for service in "${CORE_SERVICES[@]}"; do
        build_and_push_service "$service"
    done
    
    success "All core support services built and pushed!"
}

# Create manifest for multi-arch images
create_manifests() {
    section "Creating Multi-Architecture Manifests"
    
    for service in "${CORE_SERVICES[@]}"; do
        local image_name="${SERVICE_IMAGES[$service]}"
        local full_image="${DOCKER_REGISTRY}:${image_name}"
        
        log "Creating manifest for: $full_image"
        
        # Enable experimental features for manifest
        export DOCKER_CLI_EXPERIMENTAL=enabled
        
        # Create manifest (already done by buildx, but verify)
        docker manifest inspect "$full_image" >/dev/null 2>&1 && {
            success "✅ Multi-arch manifest verified: $full_image"
        } || {
            warn "⚠️ Manifest verification failed for: $full_image"
        }
    done
}

# Generate deployment information
generate_deployment_info() {
    section "Generating Pi Deployment Information"
    
    DEPLOY_INFO="${LUCID_ROOT}/infrastructure/pi-deployment-info.md"
    
    cat > "$DEPLOY_INFO" << EOF
# Pi Deployment Information - Core Support Services
Generated: $(date -u)
Build Tag: $BUILD_TAG

## Docker Images (Multi-arch: AMD64 + ARM64)

$(for service in "${CORE_SERVICES[@]}"; do
    echo "- **${service}**: \`${DOCKER_REGISTRY}:${SERVICE_IMAGES[$service]}\`"
done)

## Deployment Commands for Pi

\`\`\`bash
# 1. Transfer lucid-dev.yaml to Pi
scp infrastructure/compose/lucid-dev.yaml pickme@192.168.0.75:~/

# 2. SSH to Pi and pull images
ssh pickme@192.168.0.75

# 3. Pull all core support images
$(for service in "${CORE_SERVICES[@]}"; do
    echo "docker pull ${DOCKER_REGISTRY}:${SERVICE_IMAGES[$service]}"
done)

# 4. Create core network
docker network create lucid_core_net --driver bridge --subnet 172.21.0.0/16 || echo "Network exists"

# 5. Start core support services
docker compose -f lucid-dev.yaml up -d

# 6. Verify services
docker compose -f lucid-dev.yaml ps
docker compose -f lucid-dev.yaml logs
\`\`\`

## Service Health Checks

\`\`\`bash
# Tor proxy
curl -s --socks5-hostname localhost:9050 http://httpbin.org/ip

# MongoDB
docker exec lucid_mongo mongosh --eval "db.runCommand({ping: 1})"

# API Server
curl -fsS http://localhost:8081/health

# API Gateway
curl -fsS http://localhost:8080/health
\`\`\`

## Multi-Onion Support

The core infrastructure supports:
- **Static onions**: 5 pre-configured services
- **Dynamic onions**: Unlimited wallet and runtime onions
- **Cookie authentication**: ED25519-V3 format
- **Onion rotation**: Supported for security

Access onion addresses:
\`\`\`bash
docker exec tor_proxy cat /run/lucid/onion/multi-onion.env
\`\`\`
EOF

    success "Pi deployment info generated: $DEPLOY_INFO"
}

# Cleanup builder
cleanup_builder() {
    section "Cleanup"
    
    if [[ "${1:-}" == "keep-builder" ]]; then
        log "Keeping builder: $BUILDER_NAME"
    else
        log "Removing builder: $BUILDER_NAME"
        docker buildx rm "$BUILDER_NAME" 2>/dev/null || true
    fi
}

# Main execution
main() {
    section "LUCID CORE SUPPORT SERVICES - Build & Push"
    log "Building multi-arch images for Pi deployment"
    log "Registry: $DOCKER_REGISTRY"
    log "Build tag: $BUILD_TAG"
    log "Platforms: $PLATFORMS"
    
    preflight_checks
    setup_buildx
    
    # Build and push all services
    build_all_services
    
    # Verify manifests
    create_manifests
    
    # Generate deployment info
    generate_deployment_info
    
    # Cleanup (keep builder for future builds)
    cleanup_builder "keep-builder"
    
    section "🎉 CORE SUPPORT BUILD COMPLETE!"
    success "All services built and pushed to Docker Hub"
    success "Images are ready for Pi deployment"
    
    log "Next steps:"
    echo "  1. Transfer compose file to Pi"
    echo "  2. SSH to Pi and pull images"
    echo "  3. Start services with: docker compose -f lucid-dev.yaml up -d"
    echo "  4. Verify with health checks"
    
    log "Deployment info: infrastructure/pi-deployment-info.md"
}

# Handle script arguments
case "${1:-build}" in
    "build"|"")
        main
        ;;
    "preflight")
        preflight_checks
        ;;
    "cleanup")
        cleanup_builder
        ;;
    *)
        echo "Usage: $0 [build|preflight|cleanup]"
        exit 1
        ;;
esac