#!/bin/bash
# Path: infrastructure/docker/vm/build-env.sh
# Build Environment Script for Lucid VM Services
# Generates .env files for virtual machine management containers

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

log_info "Building environment files for Lucid VM Services"
log_info "Build timestamp: $BUILD_TIMESTAMP"
log_info "Git SHA: $GIT_SHA"

# VM Manager Environment
log_info "Creating vm-manager.env..."
cat > "$ENV_DIR/vm-manager.env" << EOF
# Lucid VM Manager Environment
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
SERVICE_NAME=vm-manager
SERVICE_PORT=8113

# VM Configuration
VM_TYPE=qemu
VM_HYPERVISOR=kvm
VM_ARCHITECTURE=x86_64
VM_DEFAULT_MEMORY=2048
VM_DEFAULT_CPUS=2

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
VM_DATABASE=lucid_vms

# Security Configuration
VM_ENCRYPTION_KEY=""
VM_ACCESS_KEY=""
VM_ISOLATION=true
VM_NETWORK_ISOLATION=true

# Performance Configuration
MAX_VM_INSTANCES=10
VM_STARTUP_TIMEOUT=120
VM_SHUTDOWN_TIMEOUT=30
VM_RESOURCE_LIMIT_CPU=80
VM_RESOURCE_LIMIT_MEMORY=80

# Storage Configuration
VM_STORAGE_PATH=/data/vms
VM_DISK_SIZE=20G
VM_DISK_FORMAT=qcow2
VM_SNAPSHOT_ENABLED=true

# Network Configuration
VM_NETWORK_TYPE=bridge
VM_NETWORK_INTERFACE=virbr0
VM_NETWORK_ISOLATION=true

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
VM_DATA_DIR=/data/vms
VM_INSTANCES_DIR=/data/instances
VM_LOGS_DIR=/data/logs
EOF

# VM Orchestrator Environment
log_info "Creating vm-orchestrator.env..."
cat > "$ENV_DIR/vm-orchestrator.env" << EOF
# Lucid VM Orchestrator Environment
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
SERVICE_NAME=vm-orchestrator
SERVICE_PORT=8114

# Orchestration Configuration
ORCHESTRATOR_MODE=distributed
ORCHESTRATION_ALGORITHM=round_robin
LOAD_BALANCING=true
AUTO_SCALING=true

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
ORCHESTRATOR_DATABASE=lucid_orchestrator

# VM Management Configuration
VM_POOL_SIZE=20
VM_POOL_MIN_SIZE=5
VM_POOL_MAX_SIZE=50
VM_POOL_SCALE_THRESHOLD=0.8

# Security Configuration
ORCHESTRATOR_ENCRYPTION_KEY=""
VM_COMMUNICATION_ENCRYPTION=true
ORCHESTRATOR_ACCESS_CONTROL=true

# Performance Configuration
ORCHESTRATOR_THREAD_POOL_SIZE=20
ORCHESTRATOR_QUEUE_SIZE=100
VM_PROVISIONING_TIMEOUT=300
VM_DEPROVISIONING_TIMEOUT=60

# Monitoring Configuration
VM_MONITORING_ENABLED=true
VM_METRICS_COLLECTION=true
VM_ALERTING_ENABLED=true

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
ORCHESTRATOR_DATA_DIR=/data/orchestrator
VM_POOL_DATA_DIR=/data/vm-pool
LOGS_DIR=/data/logs
EOF

# VM Resource Monitor Environment
log_info "Creating vm-resource-monitor.env..."
cat > "$ENV_DIR/vm-resource-monitor.env" << EOF
# Lucid VM Resource Monitor Environment
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
SERVICE_NAME=vm-resource-monitor
SERVICE_PORT=8115

# Monitoring Configuration
MONITORING_INTERVAL=10
METRICS_COLLECTION_INTERVAL=5
ALERT_CHECK_INTERVAL=30
RESOURCE_THRESHOLD_CPU=80
RESOURCE_THRESHOLD_MEMORY=80
RESOURCE_THRESHOLD_DISK=90

# Database Configuration
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
MONITORING_DATABASE=lucid_monitoring

# Alerting Configuration
ALERT_ENABLED=true
ALERT_THRESHOLD_BREACHES=3
ALERT_COOLDOWN_PERIOD=300
ALERT_ESCALATION_ENABLED=true

# Performance Configuration
MONITORING_DATA_RETENTION=86400
METRICS_COMPRESSION=true
MAX_MONITORING_HISTORY=1000
MONITORING_BATCH_SIZE=100

# Security Configuration
MONITORING_ENCRYPTION_KEY=""
METRICS_ENCRYPTION=true
MONITORING_ACCESS_CONTROL=true

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Data Directories
MONITORING_DATA_DIR=/data/monitoring
METRICS_DATA_DIR=/data/metrics
ALERT_DATA_DIR=/data/alerts
LOGS_DIR=/data/logs
EOF

log_success "Environment files created successfully in $ENV_DIR"
log_info "Created environment files for:"
log_info "  - vm-manager.env"
log_info "  - vm-orchestrator.env"
log_info "  - vm-resource-monitor.env"

echo
log_info "To use these environment files in Docker builds:"
log_info "  docker build --env-file $ENV_DIR/vm-manager.env -t pickme/lucid:vm-manager ."
log_info "  docker build --env-file $ENV_DIR/vm-orchestrator.env -t pickme/lucid:vm-orchestrator ."
log_info "  docker build --env-file $ENV_DIR/vm-resource-monitor.env -t pickme/lucid:vm-resource-monitor ."
