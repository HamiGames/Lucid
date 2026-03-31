#!/bin/bash
# scripts/validation/validate-phase1-compose.sh
# File: /app/scripts/validation/validate-phase1-compose.sh
# x-lucid-file-path: /app/scripts/validation/validate-phase1-compose.sh
# x-lucid-file-directory: /app/scripts/validation
# x-lucid-file-type: shell
# Validate Phase 1 Docker Compose configuration (x-files-listing → LUCID_HOST_COMPOSE_*)

set -e

_LUCID_W="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
while [[ "$_LUCID_W" != "/" && "$(basename "$_LUCID_W")" != "scripts" ]]; do _LUCID_W="$(dirname "$_LUCID_W")"; done
# shellcheck source=lib/lucid-repo-paths.sh
source "${_LUCID_W}/lib/lucid-repo-paths.sh"

echo "Validating Phase 1 Docker Compose configuration..."

# Check if compose file exists
if [ ! -f "$LUCID_HOST_COMPOSE_FOUNDATION" ]; then
    echo "ERROR: Docker Compose file not found"
    exit 1
fi

# Validate compose file syntax
echo "Validating compose file syntax..."
if ! docker-compose -f "${LUCID_HOST_COMPOSE_FOUNDATION}" config > /dev/null 2>&1; then
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
