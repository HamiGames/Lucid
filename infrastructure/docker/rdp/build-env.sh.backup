#!/bin/bash
# Path: infrastructure/docker/rdp/build-env.sh
# Build Environment Script for Lucid RDP Services
# Generates .env files for Remote Desktop Protocol containers

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

log_info "Building environment files for Lucid RDP Services"
log_info "Build timestamp: $BUILD_TIMESTAMP"
log_info "Git SHA: $GIT_SHA"

# RDP Server Environment
log_info "Creating rdp-server.env..."
cat > "$ENV_DIR/rdp-server.env" << EOF
# Lucid RDP Server Environment
# Generated: $(date)

# Build Configuration
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
LUCID_ENV=dev

# Service Configuration
SERVICE_NAME=rdp-server
SERVICE_PORT=3389
SERVICE_HOST=0.0.0.0

# RDP Configuration
RDP_PROTOCOL_VERSION=10.11
RDP_COLOR_DEPTH=32
RDP_COMPRESSION=true
RDP_ENCRYPTION=true

# Display Configuration
DISPLAY_WIDTH=1920
DISPLAY_HEIGHT=1080
DISPLAY_DEPTH=24
DISPLAY_REFRESH_RATE=60

# Security Configuration
RDP_CERTIFICATE_PATH=/etc/ssl/certs/rdp.crt
RDP_PRIVATE_KEY_PATH=/etc/ssl/private/rdp.key
RDP_ENCRYPTION_LEVEL=high

# Authentication Configuration
RDP_AUTHENTICATION_METHOD=ntlm
RDP_SINGLE_SIGN_ON=true
RDP_PASSWORD_POLICY=strict

# Performance Configuration
RDP_BANDWIDTH_LIMIT=10000000
RDP_LATENCY_OPTIMIZATION=true
RDP_CACHE_SIZE=100

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
RDP_LOG_FILE=/var/log/rdp/rdp.log

# Data Directories
RDP_DATA_DIR=/data/rdp
RDP_SESSIONS_DIR=/data/sessions
RDP_LOGS_DIR=/var/log/rdp
EOF

# RDP Server Manager Environment
log_info "Creating rdp-server-manager.env..."
cat > "$ENV_DIR/rdp-server-manager.env" << EOF
# Lucid RDP Server Manager Environment
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
SERVICE_NAME=rdp-server-manager
SERVICE_PORT=8100

# Management Configuration
MANAGER_POLL_INTERVAL=30
MANAGER_HEALTH_CHECK_INTERVAL=60
MAX_RDP_INSTANCES=10

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
RDP_DATABASE=lucid_rdp

# RDP Instance Configuration
RDP_INSTANCE_TIMEOUT=3600
RDP_INSTANCE_CLEANUP_INTERVAL=300
RDP_INSTANCE_MEMORY_LIMIT=2048

# Security Configuration
MANAGER_API_KEY=""
RDP_INSTANCE_ENCRYPTION=true
INSTANCE_ISOLATION=true

# Performance Configuration
MANAGER_THREAD_POOL_SIZE=20
MANAGER_QUEUE_SIZE=100
INSTANCE_STARTUP_TIMEOUT=120

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
MANAGER_DATA_DIR=/data/manager
INSTANCE_DIR=/data/instances
LOGS_DIR=/data/logs
EOF

# Session Host Manager Environment
log_info "Creating session-host-manager.env..."
cat > "$ENV_DIR/session-host-manager.env" << EOF
# Lucid Session Host Manager Environment
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
SERVICE_NAME=session-host-manager
SERVICE_PORT=8101

# Session Management Configuration
SESSION_TIMEOUT=7200
SESSION_CLEANUP_INTERVAL=300
MAX_CONCURRENT_SESSIONS=50
SESSION_POOL_SIZE=20

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
SESSION_DATABASE=lucid_sessions

# Host Configuration
HOST_RESOURCE_LIMIT_CPU=80
HOST_RESOURCE_LIMIT_MEMORY=80
HOST_RESOURCE_LIMIT_DISK=90

# Security Configuration
SESSION_ENCRYPTION=true
SESSION_AUTHENTICATION=required
SESSION_ACCESS_CONTROL=true

# Performance Configuration
SESSION_STARTUP_TIMEOUT=60
SESSION_SHUTDOWN_TIMEOUT=30
SESSION_MONITORING_INTERVAL=10

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
SESSION_DATA_DIR=/data/sessions
HOST_DATA_DIR=/data/hosts
LOGS_DIR=/data/logs
EOF

# xRDP Integration Environment
log_info "Creating xrdp-integration.env..."
cat > "$ENV_DIR/xrdp-integration.env" << EOF
# Lucid xRDP Integration Environment
# Generated: $(date)

# Build Configuration
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
LUCID_ENV=dev

# Service Configuration
SERVICE_NAME=xrdp-integration
XRDP_PORT=3389
XRDP_SESMAN_PORT=3350

# xRDP Configuration
XRDP_CONFIG_PATH=/etc/xrdp
XRDP_LOG_PATH=/var/log/xrdp
XRDP_PID_PATH=/var/run/xrdp

# Session Configuration
XRDP_SESSION_TYPE=gnome
XRDP_SESSION_SCRIPT=/etc/xrdp/startwm.sh
XRDP_SESSION_TIMEOUT=3600

# Security Configuration
XRDP_CERT_PATH=/etc/xrdp/cert.pem
XRDP_KEY_PATH=/etc/xrdp/key.pem
XRDP_SSL_PROTOCOLS=TLSv1.2

# Authentication Configuration
XRDP_AUTH_METHOD=pam
XRDP_PASSWORD_AUTH=true
XRDP_KEYBOARD_AUTH=false

# Performance Configuration
XRDP_MAX_CONNECTIONS=100
XRDP_CONNECTION_TIMEOUT=60
XRDP_IDLE_TIMEOUT=1800

# Logging Configuration
LOG_LEVEL=INFO
XRDP_LOG_LEVEL=INFO
XRDP_SESMAN_LOG_LEVEL=INFO

# Data Directories
XRDP_DATA_DIR=/data/xrdp
XRDP_SESSIONS_DIR=/data/sessions
XRDP_LOGS_DIR=/var/log/xrdp
EOF

# Clipboard Handler Distroless Environment
log_info "Creating clipboard-handler.distroless.env..."
cat > "$ENV_DIR/clipboard-handler.distroless.env" << EOF
# Lucid Clipboard Handler Distroless Environment
# Generated: $(date)

# Python Configuration
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
PYTHONPATH=/app

# Build Configuration
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
LUCID_ENV=production

# Service Configuration
SERVICE_NAME=clipboard-handler
SERVICE_PORT=8095

# Clipboard Configuration
CLIPBOARD_MAX_SIZE=524288
CLIPBOARD_FORMATS=text,html
CLIPBOARD_COMPRESSION=true

# Security Configuration
CLIPBOARD_ENCRYPTION=true
ENCRYPTION_KEY=""
CLIPBOARD_VALIDATION=true
CONTENT_SCAN_DEPTH_LIMIT=1000

# Performance Configuration
CLIPBOARD_BUFFER_SIZE=32768
CLIPBOARD_SYNC_INTERVAL=200
MAX_CLIPBOARD_HISTORY=50

# Logging Configuration
LOG_LEVEL=WARNING
LOG_FORMAT=json

# Data Directories
CLIPBOARD_DIR=/data/clipboard
TEMP_DIR=/tmp/clipboard
LOGS_DIR=/data/logs
EOF

# File Transfer Handler Environment
log_info "Creating file-transfer-handler.env..."
cat > "$ENV_DIR/file-transfer-handler.env" << EOF
# Lucid File Transfer Handler Environment
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
SERVICE_NAME=file-transfer-handler
SERVICE_PORT=8096

# File Transfer Configuration
FILE_TRANSFER_MAX_SIZE=1073741824
FILE_TRANSFER_CHUNK_SIZE=1048576
FILE_TRANSFER_TIMEOUT=300

# Security Configuration
FILE_TRANSFER_ENCRYPTION=true
ENCRYPTION_KEY=""
FILE_VALIDATION=true
VIRUS_SCANNING=true

# Performance Configuration
MAX_CONCURRENT_TRANSFERS=10
TRANSFER_BUFFER_SIZE=65536
TRANSFER_RETRY_ATTEMPTS=3

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
TRANSFER_DIR=/data/transfers
TEMP_DIR=/tmp/transfers
LOGS_DIR=/data/logs
EOF

# Keystroke Monitor Environment
log_info "Creating keystroke-monitor.env..."
cat > "$ENV_DIR/keystroke-monitor.env" << EOF
# Lucid Keystroke Monitor Environment
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
SERVICE_NAME=keystroke-monitor
SERVICE_PORT=8097

# Monitoring Configuration
KEYSTROKE_SAMPLING_RATE=100
KEYSTROKE_BUFFER_SIZE=1000
KEYSTROKE_FLUSH_INTERVAL=1

# Security Configuration
KEYSTROKE_ENCRYPTION=true
ENCRYPTION_KEY=""
SENSITIVE_PATTERN_DETECTION=true

# Performance Configuration
MAX_KEYSTROKE_HISTORY=10000
KEYSTROKE_COMPRESSION=true
MONITORING_OVERHEAD_LIMIT=5

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
KEYSTROKE_DIR=/data/keystrokes
TEMP_DIR=/tmp/keystrokes
LOGS_DIR=/data/logs
EOF

# Resource Monitor Environment
log_info "Creating resource-monitor.env..."
cat > "$ENV_DIR/resource-monitor.env" << EOF
# Lucid Resource Monitor Environment
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
SERVICE_NAME=resource-monitor
SERVICE_PORT=8098

# Monitoring Configuration
MONITORING_INTERVAL=5
RESOURCE_THRESHOLD_CPU=80
RESOURCE_THRESHOLD_MEMORY=80
RESOURCE_THRESHOLD_DISK=90

# Alert Configuration
ALERT_ENABLED=true
ALERT_THRESHOLD_BREACHES=3
ALERT_COOLDOWN_PERIOD=300

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
MONITORING_DATABASE=lucid_monitoring

# Performance Configuration
MONITORING_DATA_RETENTION=86400
MONITORING_COMPRESSION=true
MAX_MONITORING_HISTORY=1000

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
MONITORING_DIR=/data/monitoring
TEMP_DIR=/tmp/monitoring
LOGS_DIR=/data/logs
EOF

log_success "Environment files created successfully in $ENV_DIR"
log_info "Created environment files for:"
log_info "  - rdp-server.env"
log_info "  - rdp-server-manager.env"
log_info "  - session-host-manager.env"
log_info "  - xrdp-integration.env"
log_info "  - clipboard-handler.distroless.env"
log_info "  - file-transfer-handler.env"
log_info "  - keystroke-monitor.env"
log_info "  - resource-monitor.env"

echo
log_info "To use these environment files in Docker builds:"
log_info "  docker build --env-file $ENV_DIR/rdp-server.env -t pickme/lucid:rdp-server ."
log_info "  docker build --env-file $ENV_DIR/rdp-server-manager.env -t pickme/lucid:rdp-server-manager ."
log_info "  docker build --env-file $ENV_DIR/session-host-manager.env -t pickme/lucid:session-host-manager ."
log_info "  docker build --env-file $ENV_DIR/xrdp-integration.env -t pickme/lucid:xrdp-integration ."
log_info "  docker build --env-file $ENV_DIR/clipboard-handler.distroless.env -t pickme/lucid:clipboard-handler ."
log_info "  docker build --env-file $ENV_DIR/file-transfer-handler.env -t pickme/lucid:file-transfer-handler ."
log_info "  docker build --env-file $ENV_DIR/keystroke-monitor.env -t pickme/lucid:keystroke-monitor ."
log_info "  docker build --env-file $ENV_DIR/resource-monitor.env -t pickme/lucid:resource-monitor ."
