#!/bin/bash
# Path: infrastructure/docker/gui/build-env.sh
# Build Environment Script for Lucid GUI Services
# Generates .env files for graphical user interface containers

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

log_info "Building environment files for Lucid GUI Services"
log_info "Build timestamp: $BUILD_TIMESTAMP"
log_info "Git SHA: $GIT_SHA"

# Desktop Environment Environment
log_info "Creating desktop-environment.env..."
cat > "$ENV_DIR/desktop-environment.env" << EOF
# Lucid Desktop Environment Environment
# Generated: $(date)

# Build Configuration
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
LUCID_ENV=dev

# Service Configuration
SERVICE_NAME=desktop-environment
DISPLAY_NUMBER=:1
DISPLAY_WIDTH=1920
DISPLAY_HEIGHT=1080
DISPLAY_DEPTH=24

# Desktop Environment Configuration
DESKTOP_ENVIRONMENT=gnome
DESKTOP_SESSION=gnome
DESKTOP_AUTOLOGIN=true
DESKTOP_SCREENSAVER_TIMEOUT=0

# X11 Configuration
X11_DISPLAY=:1
X11_AUTH_PROTOCOL=MIT-MAGIC-COOKIE-1
X11_FORWARDING=true
X11_COMPOSITING=true

# Security Configuration
DESKTOP_ENCRYPTION_KEY=""
DESKTOP_ACCESS_CONTROL=true
DESKTOP_SESSION_ISOLATION=true

# Performance Configuration
DESKTOP_MEMORY_LIMIT=2048
DESKTOP_CPU_LIMIT=2
DESKTOP_GPU_ACCELERATION=true
DESKTOP_COMPOSITING=true

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
DESKTOP_DATA_DIR=/data/desktop
DESKTOP_SESSIONS_DIR=/data/sessions
DESKTOP_LOGS_DIR=/data/logs
EOF

# GUI Builder Environment
log_info "Creating gui-builder.env..."
cat > "$ENV_DIR/gui-builder.env" << EOF
# Lucid GUI Builder Environment
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
SERVICE_NAME=gui-builder
SERVICE_PORT=8119

# GUI Builder Configuration
BUILDER_TYPE=qt
BUILDER_THEME=lucid
BUILDER_RESOLUTION=1920x1080
BUILDER_COLOR_DEPTH=32

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
GUI_DATABASE=lucid_gui

# Security Configuration
BUILDER_ENCRYPTION_KEY=""
BUILDER_ACCESS_CONTROL=true
BUILDER_AUDIT_ENABLED=true

# Performance Configuration
BUILDER_CACHE_SIZE=1000
BUILDER_CACHE_TTL=3600
MAX_CONCURRENT_BUILDS=5
BUILD_TIMEOUT=300

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
BUILDER_DATA_DIR=/data/builder
BUILDER_CACHE_DIR=/data/cache
BUILDER_LOGS_DIR=/data/logs
EOF

# GUI Hooks Environment
log_info "Creating gui-hooks.env..."
cat > "$ENV_DIR/gui-hooks.env" << EOF
# Lucid GUI Hooks Environment
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
SERVICE_NAME=gui-hooks
SERVICE_PORT=8120

# Hooks Configuration
HOOKS_ENABLED=true
HOOKS_TIMEOUT=30
HOOKS_RETRY_ATTEMPTS=3
HOOKS_PRIORITY_QUEUE=true

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
HOOKS_DATABASE=lucid_hooks

# Security Configuration
HOOKS_ENCRYPTION_KEY=""
HOOKS_ACCESS_CONTROL=true
HOOKS_AUDIT_ENABLED=true

# Performance Configuration
HOOKS_CACHE_SIZE=500
HOOKS_CACHE_TTL=1800
MAX_CONCURRENT_HOOKS=20
HOOKS_BATCH_SIZE=10

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
HOOKS_DATA_DIR=/data/hooks
HOOKS_CACHE_DIR=/data/cache
HOOKS_LOGS_DIR=/data/logs
EOF

log_success "Environment files created successfully in $ENV_DIR"
log_info "Created environment files for:"
log_info "  - desktop-environment.env"
log_info "  - gui-builder.env"
log_info "  - gui-hooks.env"

echo
log_info "To use these environment files in Docker builds:"
log_info "  docker build --env-file $ENV_DIR/desktop-environment.env -t pickme/lucid:desktop-environment ."
log_info "  docker build --env-file $ENV_DIR/gui-builder.env -t pickme/lucid:gui-builder ."
log_info "  docker build --env-file $ENV_DIR/gui-hooks.env -t pickme/lucid:gui-hooks ."
