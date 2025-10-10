#!/bin/bash
# Path: infrastructure/docker/common/build-env.sh
# Build Environment Script for Lucid Common Services
# Generates .env files for common infrastructure containers

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
ENV_DIR="${SCRIPT_DIR}/env"
BUILD_TIMESTAMP=$(date '+%Y%m%d-%H%M%S')
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Create environment directory
mkdir -p "$ENV_DIR"

log_info "Building environment files for Lucid Common Services"
log_info "Build timestamp: $BUILD_TIMESTAMP"
log_info "Git SHA: $GIT_SHA"

# Common Server Tools Environment
log_info "Creating server-tools.env..."
cat > "$ENV_DIR/server-tools.env" << EOF
# Lucid Server Tools Environment
# Generated: $(date)

# Build Configuration
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
LUCID_ENV=dev

# Service Configuration
SERVICE_NAME=server-tools
TOOLS_DIR=/opt/lucid/tools
SCRIPTS_DIR=/opt/lucid/scripts
LOG_DIR=/var/log/lucid

# Database Configuration
MONGO_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin

# Network Configuration
TOR_PROXY_HOST=tor-proxy
TOR_PROXY_PORT=9050
API_GATEWAY_HOST=lucid_api_gateway
API_GATEWAY_PORT=8080
API_SERVER_HOST=lucid_api
API_SERVER_PORT=8081

# Health Check Configuration
HEALTH_CHECK_TIMEOUT=5
HEALTH_CHECK_RETRIES=3

# Backup Configuration
BACKUP_RETENTION_DAYS=30
BACKUP_COMPRESSION=true
BACKUP_ENCRYPTION=true

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_ROTATION_SIZE=100MB
LOG_ROTATION_COUNT=10

# Security Configuration
SECURE_MODE=true
ENCRYPTION_KEY=""
EOF

# Lucid Governor Environment
log_info "Creating lucid-governor.env..."
cat > "$ENV_DIR/lucid-governor.env" << EOF
# Lucid Governor Environment
# Generated: $(date)

# Python Configuration
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
PYTHONPATH=/app

# Build Configuration
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
LUCID_ENV=dev

# Service Configuration
SERVICE_NAME=lucid-governor
SERVICE_PORT=8108

# Governance Configuration
GOVERNANCE_PATH=/opt/lucid/governance
VOTING_PATH=/opt/lucid/voting
PARAMETERS_PATH=/opt/lucid/parameters
XDG_RUNTIME_DIR=/tmp/governor

# Voting Configuration
VOTING_PERIOD_SECONDS=172800
PROPOSAL_THRESHOLD=1000
QUORUM_THRESHOLD=4000
VOTING_DELAY_SECONDS=86400
EXECUTION_DELAY_SECONDS=172800

# Database Configuration
GOVERNANCE_DB=lucid_governance
GOVERNANCE_CONTRACT_ADDRESS=0x0000000000000000000000000000000000000000

# Security Configuration
GOVERNANCE_KEY=""
ADMIN_KEY=""
ENCRYPTION_KEY=""

# Performance Configuration
MAX_PROPOSALS=1000
MAX_VOTES_PER_PROPOSAL=10000
PROPOSAL_TIMEOUT=604800

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF

# Timelock Environment
log_info "Creating timelock.env..."
cat > "$ENV_DIR/timelock.env" << EOF
# Lucid Timelock Environment
# Generated: $(date)

# Python Configuration
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
PYTHONPATH=/app

# Build Configuration
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
LUCID_ENV=dev

# Service Configuration
SERVICE_NAME=timelock
SERVICE_PORT=8109

# Timelock Configuration
TIMELOCK_PATH=/opt/lucid/governance/timelock
QUEUES_PATH=/opt/lucid/governance/queues
XDG_RUNTIME_DIR=/tmp/timelock

# Delay Configuration
MIN_DELAY_SECONDS=86400
MAX_DELAY_SECONDS=2592000
GRACE_PERIOD_SECONDS=1296000
EXECUTION_TIMEOUT_SECONDS=604800

# Database Configuration
TIMELOCK_DB=lucid_timelock
MINIMUM_DELAY_SECONDS=3600
MAXIMUM_DELAY_SECONDS=2592000

# Queue Configuration
MAX_QUEUE_SIZE=1000
QUEUE_PROCESSING_INTERVAL=60
QUEUE_CLEANUP_INTERVAL=3600

# Security Configuration
TIMELOCK_KEY=""
EXECUTOR_KEY=""
ENCRYPTION_KEY=""

# Performance Configuration
BATCH_SIZE=100
PROCESSING_TIMEOUT=300

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF

# Beta Sidecar Environment
log_info "Creating beta.env..."
cat > "$ENV_DIR/beta.env" << EOF
# Lucid Beta Sidecar Environment
# Generated: $(date)

# Build Configuration
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
LUCID_ENV=dev

# Service Configuration
SERVICE_NAME=beta
BETA_PLANES=ops,chain,wallet
BETA_CLUSTER_ID=dev

# Tor Configuration
TOR_CONTROL_PASSWORD=""
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051

# Onion Service Configuration
ONION_SERVICE_DIR=/run/lucid/onion
ONION_SERVICE_VERSION=3

# Network Configuration
TOR_PROXY_HOST=127.0.0.1
TOR_PROXY_PORT=9050

# Security Configuration
ACL_ENFORCEMENT=true
PLANE_SEPARATION=true
FAIL_CLOSED=true

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
TOR_LOG_LEVEL=notice
EOF

# Common Distroless Environment
log_info "Creating common.distroless.env..."
cat > "$ENV_DIR/common.distroless.env" << EOF
# Lucid Common Distroless Environment
# Generated: $(date)

# Build Configuration
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
LUCID_ENV=production

# Service Configuration
SERVICE_NAME=common
TOOLS_DIR=/opt/lucid/tools
SCRIPTS_DIR=/opt/lucid/scripts
LOG_DIR=/var/log/lucid

# Database Configuration
MONGO_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin

# Network Configuration
TOR_PROXY_HOST=tor-proxy
TOR_PROXY_PORT=9050
API_GATEWAY_HOST=lucid_api_gateway
API_GATEWAY_PORT=8080
API_SERVER_HOST=lucid_api
API_SERVER_PORT=8081

# Health Check Configuration
HEALTH_CHECK_TIMEOUT=5
HEALTH_CHECK_RETRIES=3

# Backup Configuration
BACKUP_RETENTION_DAYS=7
BACKUP_COMPRESSION=true
BACKUP_ENCRYPTION=true

# Logging Configuration
LOG_LEVEL=WARNING
LOG_FORMAT=json
LOG_ROTATION_SIZE=50MB
LOG_ROTATION_COUNT=5

# Security Configuration
SECURE_MODE=true
ENCRYPTION_KEY=""
DISTROLESS_MODE=true
EOF

log_success "Environment files created successfully in $ENV_DIR"
log_info "Created environment files for:"
log_info "  - server-tools.env"
log_info "  - lucid-governor.env"
log_info "  - timelock.env"
log_info "  - beta.env"
log_info "  - common.distroless.env"

echo
log_info "To use these environment files in Docker builds:"
log_info "  docker build --env-file $ENV_DIR/server-tools.env -t pickme/lucid:server-tools ."
log_info "  docker build --env-file $ENV_DIR/lucid-governor.env -t pickme/lucid:lucid-governor ."
log_info "  docker build --env-file $ENV_DIR/timelock.env -t pickme/lucid:timelock ."
log_info "  docker build --env-file $ENV_DIR/beta.env -t pickme/lucid:beta ."
log_info "  docker build --env-file $ENV_DIR/common.distroless.env -t pickme/lucid:common ."
