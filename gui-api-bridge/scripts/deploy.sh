#!/bin/bash
# Deployment script for GUI API Bridge
# File: gui-api-bridge/scripts/deploy.sh
# Build Host: Windows 11 console
# Target Host: Raspberry Pi
# No hardcoded values - all from environment or .env file

set -e

echo "=========================================="
echo "Deploying Lucid GUI API Bridge"
echo "=========================================="

# Navigate to project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Script Dir: $SCRIPT_DIR"
echo "Project Dir: $PROJECT_DIR"
echo "Workspace Dir: $WORKSPACE_DIR"
echo ""

# Load environment variables from .env file
ENV_FILE="$WORKSPACE_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment variables from $ENV_FILE"
    set -a
    source "$ENV_FILE"
    set +a
else
    echo "Warning: .env file not found at $ENV_FILE"
    echo "Using environment variables from system"
fi

# Validate required environment variables
echo "Validating required environment variables..."
required_vars=("JWT_SECRET_KEY" "MONGODB_PASSWORD" "REDIS_PASSWORD")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: $var is not set in environment"
        exit 1
    fi
done

echo "✅ Environment variables validated"
echo ""

# Create necessary directories
echo "Creating required directories..."
mkdir -p "$PROJECT_DIR/logs" "$PROJECT_DIR/certs" "$PROJECT_DIR/database" "$PROJECT_DIR/config"

# Check if Docker Compose file exists
DOCKER_COMPOSE_FILE="$WORKSPACE_DIR/docker-compose.yml"
if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
    echo "Error: docker-compose.yml not found at $DOCKER_COMPOSE_FILE"
    exit 1
fi

echo "Using Docker Compose file: $DOCKER_COMPOSE_FILE"
echo ""

# Navigate to workspace directory for docker-compose
cd "$WORKSPACE_DIR"

# Build image if SKIP_BUILD is not set
if [ "${SKIP_BUILD:-false}" != "true" ]; then
    echo "Building GUI API Bridge image..."
    if [ -f "$SCRIPT_DIR/build.sh" ]; then
        bash "$SCRIPT_DIR/build.sh"
    else
        echo "Error: build.sh not found"
        exit 1
    fi
    echo ""
else
    echo "Skipping build (SKIP_BUILD=true)"
    echo ""
fi

# Start services with Docker Compose
echo "Starting GUI API Bridge service with Docker Compose..."
docker-compose -f "$DOCKER_COMPOSE_FILE" up -d lucid-gui-api-bridge

# Wait for service to be healthy
echo ""
echo "Waiting for service to be healthy..."
HEALTH_CHECK_ENDPOINT="${HEALTH_CHECK_ENDPOINT:-http://localhost:8102/health}"
timeout=60
while [ $timeout -gt 0 ]; do
    if curl -sf "$HEALTH_CHECK_ENDPOINT" > /dev/null 2>&1; then
        echo "✅ Service is healthy!"
        break
    fi
    echo "Waiting for service... ($timeout seconds remaining)"
    sleep 2
    timeout=$((timeout - 2))
done

if [ $timeout -le 0 ]; then
    echo ""
    echo "Error: Service failed to become healthy"
    echo "Showing logs:"
    docker-compose logs lucid-gui-api-bridge
    exit 1
fi

echo ""
echo "=========================================="
echo "Deployment completed successfully!"
echo "=========================================="
echo "GUI API Bridge is available at:"
echo "  HTTP: ${SERVICE_URL:-http://localhost:8102}"
echo ""
echo "Endpoints:"
echo "  Health check: curl http://localhost:8102/health"
echo "  API root: curl http://localhost:8102/api/v1"
echo ""
echo "View logs: docker-compose logs -f lucid-gui-api-bridge"
echo ""
