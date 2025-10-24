#!/bin/bash
# Path: infrastructure/docker/databases/build-env.sh
# Build Environment Script for Lucid Database Services
# Generates .env files for all database-related containers

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

log_info "Building environment files for Lucid Database Services"
log_info "Build timestamp: $BUILD_TIMESTAMP"
log_info "Git SHA: $GIT_SHA"

# Common environment variables for all database services
COMMON_ENV_VARS=(
    "BUILD_TIMESTAMP=$BUILD_TIMESTAMP"
    "GIT_SHA=$GIT_SHA"
    "LUCID_ENV=dev"
    "LUCID_PLANE=ops"
    "LUCID_CLUSTER_ID=dev-core"
    "LOG_LEVEL=INFO"
    "LOG_FORMAT=json"
)

# MongoDB 7 Environment
log_info "Creating .env.mongodb..."
cat > "$ENV_DIR/.env.mongodb" << EOF
# Lucid MongoDB 7 Environment
# Generated: $(date)

# Common settings
${COMMON_ENV_VARS[*]}

# MongoDB Configuration
MONGO_VERSION=7.0
MONGO_PORT=27017
MONGO_BIND_IP=0.0.0.0
MONGO_REPLICA_SET=rs0
MONGO_OPLOG_SIZE=128
MONGO_WIRED_TIGER_CACHE_SIZE=0.5

# Authentication Configuration
MONGO_INITDB_ROOT_USERNAME=lucid
MONGO_INITDB_ROOT_PASSWORD=lucid
MONGO_INITDB_DATABASE=lucid
MONGO_AUTH_ENABLED=true

# Database Configuration
MONGO_DB_NAME=lucid
MONGO_COLLECTIONS=sessions,authentication,work_proofs,blockchain_data,contracts,deployments

# Performance Configuration
MONGO_MAX_CONNECTIONS=100
MONGO_CONNECTION_TIMEOUT=30000
MONGO_SOCKET_TIMEOUT=30000
MONGO_SERVER_SELECTION_TIMEOUT=5000

# Security Configuration
MONGO_SSL_ENABLED=false
MONGO_SSL_REQUIRE_VALID_CERT=false
MONGO_SSL_CA_FILE=""
MONGO_SSL_CERT_FILE=""
MONGO_SSL_KEY_FILE=""

# Data Directories
MONGO_DATA_DIR=/data/db
MONGO_CONFIG_DIR=/data/configdb
MONGO_LOG_DIR=/var/log/mongodb

# Health Check Configuration
HEALTH_CHECK_INTERVAL=10
HEALTH_CHECK_TIMEOUT=5
HEALTH_CHECK_RETRIES=10
HEALTH_CHECK_START_PERIOD=15

# Backup Configuration
BACKUP_ENABLED=true
BACKUP_INTERVAL=3600
BACKUP_RETENTION_DAYS=7
BACKUP_DIR=/data/backups

# Monitoring Configuration
MONITORING_ENABLED=true
METRICS_PORT=9216
METRICS_PATH=/metrics
EOF

# MongoDB Initialization Environment
log_info "Creating .env.mongodb-init..."
cat > "$ENV_DIR/.env.mongodb-init" << EOF
# Lucid MongoDB Initialization Environment
# Generated: $(date)

# Common settings
${COMMON_ENV_VARS[*]}

# Initialization Configuration
INIT_SCRIPT_PATH=/docker-entrypoint-initdb.d
SCHEMA_SCRIPT=init_collections.js
AUTH_SCRIPT=init_auth.js
INDEX_SCRIPT=init_indexes.js

# Database Schema Configuration
SCHEMA_VERSION=1.0.0
COLLECTIONS_TO_CREATE=sessions,authentication,work_proofs,blockchain_data,contracts,deployments,users,payments

# Index Configuration
INDEXES_ENABLED=true
TEXT_INDEXES_ENABLED=true
COMPOUND_INDEXES_ENABLED=true

# Validation Configuration
VALIDATION_ENABLED=true
STRICT_VALIDATION=true
SCHEMA_VALIDATION_LEVEL=strict

# Data Directories
INIT_DATA_DIR=/data/init
SCHEMA_DIR=/data/schema
BACKUP_DIR=/data/backups

# Security Configuration
INIT_USER_ROLES=readWrite,dbAdmin,userAdmin
INIT_USER_DATABASES=lucid,admin

# Performance Configuration
BATCH_SIZE=1000
BULK_OPERATIONS=true
PARALLEL_INIT=true
EOF

# Database Backup Environment
log_info "Creating .env.database-backup..."
cat > "$ENV_DIR/.env.database-backup" << EOF
# Lucid Database Backup Environment
# Generated: $(date)

# Common settings
${COMMON_ENV_VARS[*]}

# Backup Configuration
BACKUP_SERVICE_NAME=database-backup
BACKUP_SERVICE_PORT=8089
BACKUP_SCHEDULE=0 2 * * *
BACKUP_RETENTION_DAYS=30
BACKUP_COMPRESSION=true
BACKUP_ENCRYPTION=true

# MongoDB Connection
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid
MONGODB_COLLECTIONS=*

# Storage Configuration
BACKUP_STORAGE_TYPE=local
BACKUP_STORAGE_PATH=/data/backups
BACKUP_STORAGE_S3_BUCKET=""
BACKUP_STORAGE_S3_REGION=""
BACKUP_STORAGE_S3_ACCESS_KEY=""
BACKUP_STORAGE_S3_SECRET_KEY=""

# Encryption Configuration
BACKUP_ENCRYPTION_KEY=""
BACKUP_ENCRYPTION_ALGORITHM=AES-256-GCM

# Notification Configuration
NOTIFICATION_ENABLED=false
NOTIFICATION_WEBHOOK_URL=""
NOTIFICATION_EMAIL=""
NOTIFICATION_SLACK_WEBHOOK=""

# Data Directories
BACKUP_DIR=/data/backups
TEMP_DIR=/tmp/backup
LOG_DIR=/var/log/backup

# Performance Configuration
BACKUP_THREADS=4
BACKUP_BUFFER_SIZE=64MB
BACKUP_TIMEOUT=3600
EOF

# Database Restore Environment
log_info "Creating .env.database-restore..."
cat > "$ENV_DIR/.env.database-restore" << EOF
# Lucid Database Restore Environment
# Generated: $(date)

# Common settings
${COMMON_ENV_VARS[*]}

# Restore Configuration
RESTORE_SERVICE_NAME=database-restore
RESTORE_SERVICE_PORT=8090
RESTORE_DRY_RUN=false
RESTORE_DROP_COLLECTIONS=false
RESTORE_PRESERVE_INDEXES=true

# MongoDB Connection
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid

# Backup Source Configuration
BACKUP_SOURCE_TYPE=local
BACKUP_SOURCE_PATH=/data/backups
BACKUP_SOURCE_S3_BUCKET=""
BACKUP_SOURCE_S3_REGION=""
BACKUP_SOURCE_S3_ACCESS_KEY=""
BACKUP_SOURCE_S3_SECRET_KEY=""

# Decryption Configuration
RESTORE_DECRYPTION_KEY=""
RESTORE_DECRYPTION_ALGORITHM=AES-256-GCM

# Data Directories
RESTORE_DIR=/data/restore
TEMP_DIR=/tmp/restore
LOG_DIR=/var/log/restore

# Performance Configuration
RESTORE_THREADS=4
RESTORE_BUFFER_SIZE=64MB
RESTORE_TIMEOUT=3600
RESTORE_BATCH_SIZE=1000
EOF

# Database Monitoring Environment
log_info "Creating .env.database-monitoring..."
cat > "$ENV_DIR/.env.database-monitoring" << EOF
# Lucid Database Monitoring Environment
# Generated: $(date)

# Common settings
${COMMON_ENV_VARS[*]}

# Monitoring Configuration
MONITORING_SERVICE_NAME=database-monitoring
MONITORING_SERVICE_PORT=8091
MONITORING_INTERVAL=30
MONITORING_TIMEOUT=10
MONITORING_RETRIES=3

# MongoDB Connection
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid

# Metrics Configuration
METRICS_ENABLED=true
METRICS_PORT=9216
METRICS_PATH=/metrics
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=false

# Health Check Configuration
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10
HEALTH_CHECK_RETRIES=3

# Alerting Configuration
ALERTING_ENABLED=true
ALERTING_WEBHOOK_URL=""
ALERTING_EMAIL=""
ALERTING_SLACK_WEBHOOK=""

# Thresholds
CPU_THRESHOLD=80
MEMORY_THRESHOLD=80
DISK_THRESHOLD=85
CONNECTION_THRESHOLD=90
QUERY_TIME_THRESHOLD=1000

# Data Directories
MONITORING_DIR=/data/monitoring
LOG_DIR=/var/log/monitoring
METRICS_DIR=/data/metrics

# Performance Configuration
MONITORING_THREADS=2
MONITORING_BUFFER_SIZE=1MB
MONITORING_TIMEOUT=30
EOF

# Database Migration Environment
log_info "Creating .env.database-migration..."
cat > "$ENV_DIR/.env.database-migration" << EOF
# Lucid Database Migration Environment
# Generated: $(date)

# Common settings
${COMMON_ENV_VARS[*]}

# Migration Configuration
MIGRATION_SERVICE_NAME=database-migration
MIGRATION_SERVICE_PORT=8092
MIGRATION_VERSION=1.0.0
MIGRATION_DRY_RUN=false
MIGRATION_BACKUP_BEFORE=true

# MongoDB Connection
MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
MONGODB_DATABASE=lucid

# Migration Scripts
MIGRATION_SCRIPTS_DIR=/data/migrations
MIGRATION_SCRIPTS_PATTERN=*.js
MIGRATION_SCRIPTS_ORDER=sequential

# Schema Configuration
SCHEMA_VERSION_TABLE=migration_history
SCHEMA_VALIDATION=true
SCHEMA_BACKUP=true

# Data Directories
MIGRATION_DIR=/data/migration
BACKUP_DIR=/data/backups
LOG_DIR=/var/log/migration

# Performance Configuration
MIGRATION_BATCH_SIZE=1000
MIGRATION_THREADS=2
MIGRATION_TIMEOUT=3600
MIGRATION_RETRY_ATTEMPTS=3
EOF

log_success "Environment files created successfully in $ENV_DIR"
log_info "Created environment files for:"
log_info "  - .env.mongodb"
log_info "  - .env.mongodb-init"
log_info "  - .env.database-backup"
log_info "  - .env.database-restore"
log_info "  - .env.database-monitoring"
log_info "  - .env.database-migration"

echo
log_info "To use these environment files in Docker builds:"
log_info "  docker build --env-file $ENV_DIR/.env.mongodb -t pickme/lucid:mongodb ."
log_info "  docker build --env-file $ENV_DIR/.env.mongodb-init -t pickme/lucid:mongodb-init ."
log_info "  docker build --env-file $ENV_DIR/.env.database-backup -t pickme/lucid:database-backup ."
