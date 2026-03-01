#!/bin/bash
# scripts/validation/validate-phase1-compose.sh
# Validate Phase 1 Docker Compose configuration

set -e

echo "Validating Phase 1 Docker Compose configuration..."

# Check if compose file exists
if [ ! -f "configs/docker/docker-compose.foundation.yml" ]; then
    echo "ERROR: Docker Compose file not found"
    exit 1
fi

# Validate compose file syntax
echo "Validating compose file syntax..."
if ! docker-compose -f configs/docker/docker-compose.foundation.yml config > /dev/null 2>&1; then
    echo "ERROR: Docker Compose file syntax invalid"
    exit 1
fi

# Check environment variables
echo "Checking environment variables..."
ENV_FILE="configs/environment/.env.foundation"
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: Environment file not found: $ENV_FILE"
    exit 1
fi

# Validate environment variables are set
REQUIRED_VARS=("MONGODB_URI" "REDIS_URL" "JWT_SECRET_KEY" "ENCRYPTION_KEY")
for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${var}=" "$ENV_FILE"; then
        echo "ERROR: Required environment variable $var not found"
        exit 1
    fi
done

echo "Phase 1 Docker Compose validation completed successfully"
