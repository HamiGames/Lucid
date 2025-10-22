#!/bin/bash
# Path: scripts/deployment/create-distroless-env.sh
# Create Distroless-Specific Environment File
# Merges foundation .env with distroless-specific overrides
# MUST RUN ON PI CONSOLE

set -euo pipefail

# Colors for output
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

# Project root
PROJECT_ROOT="${PROJECT_ROOT:-/mnt/myssd/Lucid/Lucid}"

echo ""
log_info "========================================"
log_info "Creating Distroless Environment File"
log_info "========================================"
echo ""

# Check if we're in the right directory
if [ ! -f "configs/docker/distroless/production.env" ]; then
    log_error "Not in project root directory!"
    log_error "Please run from: $PROJECT_ROOT"
    exit 1
fi

# Check if foundation .env exists
if [ ! -f "configs/environment/.env.foundation" ]; then
    log_error "Foundation .env file not found!"
    log_error "Please run first: bash scripts/config/generate-all-env-complete.sh"
    exit 1
fi

log_info "Found foundation .env file"
echo ""

# Step 1: Copy base distroless template
log_info "Copying distroless production template..."
cp configs/docker/distroless/production.env configs/environment/.env.distroless

if [ $? -eq 0 ]; then
    log_success "Template copied to configs/environment/.env.distroless"
else
    log_error "Failed to copy template"
    exit 1
fi
echo ""

# Step 2: Source foundation environment
log_info "Loading foundation environment variables..."
source configs/environment/.env.foundation

# Verify key variables are set
if [ -z "${MONGODB_PASSWORD:-}" ] || [ -z "${REDIS_PASSWORD:-}" ] || [ -z "${JWT_SECRET:-}" ] || [ -z "${ENCRYPTION_KEY:-}" ]; then
    log_error "Foundation environment variables not properly loaded!"
    log_error "Missing: MONGODB_PASSWORD, REDIS_PASSWORD, JWT_SECRET, or ENCRYPTION_KEY"
    exit 1
fi

log_success "Foundation environment loaded"
echo ""

# Step 3: Replace hardcoded passwords with secure values
log_info "Replacing hardcoded passwords with secure values..."

# Replace MongoDB passwords
sed -i "s|mongodb://lucid:lucid@|mongodb://lucid:${MONGODB_PASSWORD}@|g" configs/environment/.env.distroless
sed -i "s|MONGO_URI=mongodb://lucid:lucid@|MONGO_URI=mongodb://lucid:${MONGODB_PASSWORD}@|g" configs/environment/.env.distroless
sed -i "s|MONGO_URL=mongodb://lucid:lucid@|MONGO_URL=mongodb://lucid:${MONGODB_PASSWORD}@|g" configs/environment/.env.distroless

# Replace Redis passwords
sed -i "s|redis://lucid-redis:6379/0|redis://:${REDIS_PASSWORD}@lucid-redis:6379/0|g" configs/environment/.env.distroless

# Replace JWT secret
sed -i "s|JWT_SECRET=.*|JWT_SECRET=${JWT_SECRET}|g" configs/environment/.env.distroless

# Replace encryption key
sed -i "s|ENCRYPTION_KEY=.*|ENCRYPTION_KEY=${ENCRYPTION_KEY}|g" configs/environment/.env.distroless

# Replace TOR password if available
if [ -n "${TOR_PASSWORD:-}" ]; then
    sed -i "s|TOR_CONTROL_PASSWORD=.*|TOR_CONTROL_PASSWORD=${TOR_PASSWORD}|g" configs/environment/.env.distroless
fi

# Replace API secret if available
if [ -n "${API_SECRET:-}" ]; then
    sed -i "s|API_SECRET=.*|API_SECRET=${API_SECRET}|g" configs/environment/.env.distroless
fi

log_success "Passwords replaced with secure values"
echo ""

# Step 4: Add distroless-specific network configuration
log_info "Adding distroless-specific network configuration..."

cat >> configs/environment/.env.distroless << 'EOF'

# =============================================================================
# DISTROLESS-SPECIFIC CONFIGURATION
# =============================================================================

# Distroless Network Configuration
DISTROLESS_NETWORK=lucid-distroless-production
DISTROLESS_DEV_NETWORK=lucid-distroless-dev
MULTI_STAGE_NETWORK=lucid-multi-stage-network

# Distroless Security Configuration
DISTROLESS_SECURITY_MODE=hardened
DISTROLESS_READ_ONLY=true
DISTROLESS_NO_NEW_PRIVILEGES=true
DISTROLESS_USER_ID=1000
DISTROLESS_GROUP_ID=1000

# Distroless Runtime Configuration
DISTROLESS_PYTHON_PATH=/app
DISTROLESS_WORKING_DIR=/app
DISTROLESS_TMPFS_SIZE=100m
DISTROLESS_VAR_TMPFS_SIZE=50m

# Distroless Health Check Configuration
DISTROLESS_HEALTH_INTERVAL=30s
DISTROLESS_HEALTH_TIMEOUT=10s
DISTROLESS_HEALTH_RETRIES=3
DISTROLESS_HEALTH_START_PERIOD=10s

# Distroless Resource Limits
DISTROLESS_MEMORY_LIMIT=512M
DISTROLESS_CPU_LIMIT=0.5
DISTROLESS_MEMORY_RESERVATION=256M
DISTROLESS_CPU_RESERVATION=0.25
EOF

log_success "Distroless-specific configuration added"
echo ""

# Step 5: Verify the file
log_info "Verifying distroless environment file..."

# Check file exists
if [ ! -f "configs/environment/.env.distroless" ]; then
    log_error "Distroless .env file not created!"
    exit 1
fi

# Check no hardcoded "lucid" passwords remain
if grep -q "mongodb://lucid:lucid@" configs/environment/.env.distroless; then
    log_error "Hardcoded MongoDB password still present!"
    exit 1
fi

# Check secure passwords are present
if ! grep -q "mongodb://lucid:${MONGODB_PASSWORD}@" configs/environment/.env.distroless; then
    log_error "Secure MongoDB password not found!"
    exit 1
fi

# Check no placeholders
if grep -q "_PLACEHOLDER" configs/environment/.env.distroless; then
    log_error "Placeholders found in distroless .env file!"
    exit 1
fi

log_success "Distroless environment file verified"
echo ""

# Step 6: Set secure permissions
log_info "Setting secure file permissions..."
chmod 600 configs/environment/.env.distroless

if [ $? -eq 0 ]; then
    log_success "File permissions set to 600 (owner read/write only)"
else
    log_warning "Could not set file permissions"
fi
echo ""

# Step 7: Show summary
log_info "Distroless Environment File Summary:"
echo ""
log_info "File: configs/environment/.env.distroless"
log_info "Size: $(wc -l < configs/environment/.env.distroless) lines"
log_info "Permissions: $(ls -la configs/environment/.env.distroless | awk '{print $1}')"
echo ""

log_info "Key variables configured:"
log_info "  • MongoDB URI: mongodb://lucid:***@mongo-distroless:27019/lucid"
log_info "  • Redis URI: redis://:***@lucid-redis:6379/0"
log_info "  • JWT Secret: ${JWT_SECRET:0:8}... (64+ bytes)"
log_info "  • Encryption Key: ${ENCRYPTION_KEY:0:8}... (32+ bytes)"
log_info "  • Network: lucid-distroless-production (172.23.0.0/16)"
echo ""

log_success "========================================"
log_success "Distroless environment file created!"
log_success "========================================"
echo ""
log_info "Next steps:"
log_info "  1. Deploy distroless base infrastructure:"
log_info "     bash scripts/deployment/deploy-distroless-base.sh"
log_info ""
log_info "  2. Deploy Lucid services:"
log_info "     bash scripts/deployment/deploy-lucid-services.sh"
echo ""
