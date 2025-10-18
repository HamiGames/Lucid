#!/bin/bash

# Environment Configuration Generator for Lucid RDP System
# This script generates environment configuration files for different deployment scenarios

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIGS_DIR="$PROJECT_ROOT/configs/environment"
TEMPLATES_DIR="$PROJECT_ROOT/configs/templates"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date +'%Y-%m-%d %H:%M:%S')] ${message}${NC}"
}

print_info() {
    print_status "$BLUE" "INFO: $1"
}

print_success() {
    print_status "$GREEN" "SUCCESS: $1"
}

print_warning() {
    print_status "$YELLOW" "WARNING: $1"
}

print_error() {
    print_status "$RED" "ERROR: $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Environment Configuration Generator for Lucid RDP System

OPTIONS:
    -e, --environment ENV    Target environment (development, staging, production, test)
    -t, --template TEMPLATE  Template to use (default, pi, cloud, local)
    -o, --output FILE        Output file path
    -f, --force              Overwrite existing files
    -v, --verbose            Verbose output
    --help                   Show this help message

ENVIRONMENTS:
    development              Development environment configuration
    staging                  Staging environment configuration
    production               Production environment configuration
    test                     Test environment configuration

TEMPLATES:
    default                  Default configuration template
    pi                       Raspberry Pi optimized configuration
    cloud                    Cloud deployment configuration
    local                    Local development configuration

EXAMPLES:
    $0 --environment development --template local
    $0 --environment production --template cloud --output .env.production
    $0 --environment pi --template pi --force

EOF
}

# Function to generate random secrets
generate_secret() {
    local length=${1:-32}
    openssl rand -hex $((length / 2)) 2>/dev/null || \
    python3 -c "import secrets; print(secrets.token_hex($((length / 2))))" 2>/dev/null || \
    head -c $length /dev/urandom | base64 | tr -d '\n' | cut -c1-$length
}

# Function to generate JWT secret
generate_jwt_secret() {
    generate_secret 64
}

# Function to generate database password
generate_db_password() {
    generate_secret 32
}

# Function to generate encryption key
generate_encryption_key() {
    generate_secret 32
}

# Function to get environment-specific values
get_env_values() {
    local environment=$1
    local template=$2
    
    case "$environment" in
        "development")
            echo "DEBUG=true"
            echo "LOG_LEVEL=DEBUG"
            echo "API_RATE_LIMIT=1000"
            echo "SESSION_TIMEOUT=3600"
            echo "DATABASE_POOL_SIZE=10"
            echo "REDIS_POOL_SIZE=20"
            ;;
        "staging")
            echo "DEBUG=false"
            echo "LOG_LEVEL=INFO"
            echo "API_RATE_LIMIT=500"
            echo "SESSION_TIMEOUT=7200"
            echo "DATABASE_POOL_SIZE=20"
            echo "REDIS_POOL_SIZE=50"
            ;;
        "production")
            echo "DEBUG=false"
            echo "LOG_LEVEL=WARNING"
            echo "API_RATE_LIMIT=100"
            echo "SESSION_TIMEOUT=14400"
            echo "DATABASE_POOL_SIZE=50"
            echo "REDIS_POOL_SIZE=100"
            ;;
        "test")
            echo "DEBUG=true"
            echo "LOG_LEVEL=DEBUG"
            echo "API_RATE_LIMIT=10000"
            echo "SESSION_TIMEOUT=300"
            echo "DATABASE_POOL_SIZE=5"
            echo "REDIS_POOL_SIZE=10"
            ;;
    esac
    
    case "$template" in
        "pi")
            echo "HARDWARE_ACCELERATION=true"
            echo "V4L2_ENABLED=true"
            echo "GPU_MEMORY=128"
            echo "CPU_CORES=4"
            echo "MEMORY_LIMIT=2G"
            ;;
        "cloud")
            echo "HARDWARE_ACCELERATION=false"
            echo "V4L2_ENABLED=false"
            echo "SCALING_ENABLED=true"
            echo "AUTO_SCALING=true"
            echo "LOAD_BALANCER=true"
            ;;
        "local")
            echo "HARDWARE_ACCELERATION=false"
            echo "V4L2_ENABLED=false"
            echo "LOCAL_DEVELOPMENT=true"
            echo "HOT_RELOAD=true"
            ;;
    esac
}

# Function to generate environment file
generate_env_file() {
    local environment=$1
    local template=$2
    local output_file=$3
    local force=$4
    
    print_info "Generating environment file for $environment with $template template..."
    
    # Check if file exists and force is not set
    if [ -f "$output_file" ] && [ "$force" = false ]; then
        print_warning "File $output_file already exists. Use --force to overwrite."
        return 1
    fi
    
    # Create output directory if it doesn't exist
    mkdir -p "$(dirname "$output_file")"
    
    # Generate secrets
    local jwt_secret=$(generate_jwt_secret)
    local db_password=$(generate_db_password)
    local encryption_key=$(generate_encryption_key)
    local tron_private_key=$(generate_secret 64)
    
    # Get environment-specific values
    local env_values=$(get_env_values "$environment" "$template")
    
    # Generate the environment file
    cat > "$output_file" << EOF
# Lucid RDP System Environment Configuration
# Generated: $(date)
# Environment: $environment
# Template: $template

# =============================================================================
# SYSTEM CONFIGURATION
# =============================================================================

# Project Information
PROJECT_NAME="Lucid RDP System"
PROJECT_VERSION="1.0.0"
ENVIRONMENT="$environment"
TEMPLATE="$template"

# Debug and Logging
DEBUG=$(echo "$env_values" | grep "^DEBUG=" | cut -d'=' -f2)
LOG_LEVEL=$(echo "$env_values" | grep "^LOG_LEVEL=" | cut -d'=' -f2)
LOG_FORMAT="json"
LOG_FILE="/var/log/lucid/lucid.log"

# =============================================================================
# API GATEWAY CONFIGURATION
# =============================================================================

# API Gateway Settings
API_GATEWAY_HOST="0.0.0.0"
API_GATEWAY_PORT=8080
API_GATEWAY_WORKERS=4
API_RATE_LIMIT=$(echo "$env_values" | grep "^API_RATE_LIMIT=" | cut -d'=' -f2)
API_TIMEOUT=30

# CORS Configuration
CORS_ORIGINS="*"
CORS_METHODS="GET,POST,PUT,DELETE,OPTIONS"
CORS_HEADERS="*"

# =============================================================================
# AUTHENTICATION CONFIGURATION
# =============================================================================

# JWT Configuration
JWT_SECRET="$jwt_secret"
JWT_ALGORITHM="HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Session Configuration
SESSION_TIMEOUT=$(echo "$env_values" | grep "^SESSION_TIMEOUT=" | cut -d'=' -f2)
SESSION_SECRET=$(generate_secret 32)
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true

# Hardware Wallet Configuration
HARDWARE_WALLET_ENABLED=true
HARDWARE_WALLET_TIMEOUT=30
HARDWARE_WALLET_RETRY_ATTEMPTS=3

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# MongoDB Configuration
MONGODB_HOST="localhost"
MONGODB_PORT=27017
MONGODB_DATABASE="lucid"
MONGODB_USERNAME="lucid"
MONGODB_PASSWORD="$db_password"
MONGODB_AUTH_SOURCE="admin"
MONGODB_POOL_SIZE=$(echo "$env_values" | grep "^DATABASE_POOL_SIZE=" | cut -d'=' -f2)
MONGODB_MAX_IDLE_TIME=30000
MONGODB_SERVER_SELECTION_TIMEOUT=5000

# MongoDB Replica Set
MONGODB_REPLICA_SET="lucid-rs"
MONGODB_REPLICA_SET_HOSTS="localhost:27017,localhost:27018,localhost:27019"

# Redis Configuration
REDIS_HOST="localhost"
REDIS_PORT=6379
REDIS_PASSWORD=""
REDIS_DATABASE=0
REDIS_POOL_SIZE=$(echo "$env_values" | grep "^REDIS_POOL_SIZE=" | cut -d'=' -f2)
REDIS_MAX_CONNECTIONS=1000
REDIS_TIMEOUT=5

# Elasticsearch Configuration
ELASTICSEARCH_HOST="localhost"
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_USERNAME=""
ELASTICSEARCH_PASSWORD=""
ELASTICSEARCH_INDEX_PREFIX="lucid"

# =============================================================================
# BLOCKCHAIN CONFIGURATION
# =============================================================================

# Blockchain Core Settings
BLOCKCHAIN_NETWORK="lucid"
BLOCKCHAIN_CONSENSUS="poot"
BLOCKCHAIN_BLOCK_TIME=10
BLOCKCHAIN_DIFFICULTY=1
BLOCKCHAIN_REWARD=1.0

# Session Anchoring
ANCHORING_ENABLED=true
ANCHORING_BATCH_SIZE=10
ANCHORING_INTERVAL=60
ANCHORING_TIMEOUT=30

# Merkle Tree Configuration
MERKLE_TREE_ALGORITHM="blake3"
MERKLE_TREE_LEAF_SIZE=1024
MERKLE_TREE_DEPTH_LIMIT=20

# =============================================================================
# SESSION MANAGEMENT CONFIGURATION
# =============================================================================

# Session Recording
RECORDING_ENABLED=true
RECORDING_QUALITY="medium"
RECORDING_FPS=30
RECORDING_BITRATE=2000
RECORDING_RESOLUTION="1920x1080"

# Chunk Processing
CHUNK_SIZE=10485760
CHUNK_COMPRESSION_LEVEL=6
CHUNK_ENCRYPTION_ENABLED=true
CHUNK_ENCRYPTION_ALGORITHM="AES-256-GCM"

# Session Storage
SESSION_STORAGE_PATH="/data/sessions"
SESSION_STORAGE_RETENTION_DAYS=30
SESSION_BACKUP_ENABLED=true
SESSION_BACKUP_INTERVAL=3600

# =============================================================================
# RDP SERVICES CONFIGURATION
# =============================================================================

# RDP Server Configuration
RDP_SERVER_ENABLED=true
RDP_SERVER_PORT_RANGE="13389-14389"
RDP_SERVER_MAX_SESSIONS=100
RDP_SERVER_TIMEOUT=300

# XRDP Configuration
XRDP_ENABLED=true
XRDP_CONFIG_PATH="/etc/xrdp"
XRDP_LOG_PATH="/var/log/xrdp"

# Session Controller
SESSION_CONTROLLER_PORT=8092
SESSION_CONTROLLER_WORKERS=2
SESSION_CONTROLLER_TIMEOUT=30

# Resource Monitor
RESOURCE_MONITOR_PORT=8093
RESOURCE_MONITOR_INTERVAL=30
RESOURCE_MONITOR_THRESHOLDS_CPU=80
RESOURCE_MONITOR_THRESHOLDS_MEMORY=80
RESOURCE_MONITOR_THRESHOLDS_DISK=90

# =============================================================================
# NODE MANAGEMENT CONFIGURATION
# =============================================================================

# Node Registration
NODE_REGISTRATION_ENABLED=true
NODE_REGISTRATION_PORT=8095
NODE_REGISTRATION_TIMEOUT=30

# PoOT Configuration
POOT_ENABLED=true
POOT_CALCULATION_INTERVAL=300
POOT_REWARD_FACTOR=1.0
POOT_PENALTY_FACTOR=0.5

# Node Pools
NODE_POOL_ENABLED=true
NODE_POOL_MIN_SIZE=5
NODE_POOL_MAX_SIZE=100
NODE_POOL_SCALE_UP_THRESHOLD=80
NODE_POOL_SCALE_DOWN_THRESHOLD=20

# =============================================================================
# ADMIN INTERFACE CONFIGURATION
# =============================================================================

# Admin Interface
ADMIN_INTERFACE_ENABLED=true
ADMIN_INTERFACE_PORT=8083
ADMIN_INTERFACE_HOST="0.0.0.0"

# RBAC Configuration
RBAC_ENABLED=true
RBAC_DEFAULT_ROLE="read_only"
RBAC_ADMIN_ROLE="super_admin"

# Audit Logging
AUDIT_LOGGING_ENABLED=true
AUDIT_LOG_RETENTION_DAYS=90
AUDIT_LOG_LEVEL="INFO"

# Emergency Controls
EMERGENCY_CONTROLS_ENABLED=true
EMERGENCY_LOCKDOWN_ENABLED=true
EMERGENCY_SHUTDOWN_ENABLED=true

# =============================================================================
# TRON PAYMENT CONFIGURATION
# =============================================================================

# TRON Network Configuration
TRON_NETWORK="mainnet"
TRON_API_URL="https://api.trongrid.io"
TRON_API_KEY=""
TRON_PRIVATE_KEY="$tron_private_key"

# USDT Configuration
USDT_CONTRACT_ADDRESS="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
USDT_DECIMALS=6
USDT_MIN_TRANSFER=1

# Payout Configuration
PAYOUT_ENABLED=true
PAYOUT_V0_ENABLED=true
PAYOUT_KYC_ENABLED=true
PAYOUT_DIRECT_ENABLED=true
PAYOUT_MIN_AMOUNT=1
PAYOUT_MAX_AMOUNT=10000

# Staking Configuration
STAKING_ENABLED=true
STAKING_MIN_AMOUNT=1000
STAKING_REWARD_RATE=0.05
STAKING_LOCK_PERIOD=86400

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

# Encryption
ENCRYPTION_KEY="$encryption_key"
ENCRYPTION_ALGORITHM="AES-256-GCM"
ENCRYPTION_IV_LENGTH=12

# SSL/TLS Configuration
SSL_ENABLED=true
SSL_CERT_PATH="/etc/ssl/certs/lucid.crt"
SSL_KEY_PATH="/etc/ssl/private/lucid.key"
SSL_CA_PATH="/etc/ssl/certs/ca.crt"

# Security Headers
SECURITY_HEADERS_ENABLED=true
SECURITY_HEADERS_HSTS=true
SECURITY_HEADERS_CSP=true
SECURITY_HEADERS_XFRAME=true

# =============================================================================
# MONITORING CONFIGURATION
# =============================================================================

# Prometheus Configuration
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
PROMETHEUS_PATH="/metrics"
PROMETHEUS_INTERVAL=15

# Grafana Configuration
GRAFANA_ENABLED=true
GRAFANA_PORT=3000
GRAFANA_ADMIN_USER="admin"
GRAFANA_ADMIN_PASSWORD="$(generate_secret 16)"

# Health Checks
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10
HEALTH_CHECK_RETRIES=3

# =============================================================================
# HARDWARE CONFIGURATION
# =============================================================================

# Hardware Acceleration
HARDWARE_ACCELERATION=$(echo "$env_values" | grep "^HARDWARE_ACCELERATION=" | cut -d'=' -f2)
V4L2_ENABLED=$(echo "$env_values" | grep "^V4L2_ENABLED=" | cut -d'=' -f2)

# GPU Configuration
GPU_ENABLED=false
GPU_MEMORY=$(echo "$env_values" | grep "^GPU_MEMORY=" | cut -d'=' -f2)
GPU_DEVICE_ID=0

# CPU Configuration
CPU_CORES=$(echo "$env_values" | grep "^CPU_CORES=" | cut -d'=' -f2)
CPU_AFFINITY=""

# Memory Configuration
MEMORY_LIMIT=$(echo "$env_values" | grep "^MEMORY_LIMIT=" | cut -d'=' -f2)
MEMORY_SWAP=false

# =============================================================================
# NETWORK CONFIGURATION
# =============================================================================

# Network Settings
NETWORK_INTERFACE="eth0"
NETWORK_MTU=1500
NETWORK_BUFFER_SIZE=65536

# Tor Configuration
TOR_ENABLED=false
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051
TOR_DATA_DIR="/var/lib/tor"

# Firewall Configuration
FIREWALL_ENABLED=true
FIREWALL_DEFAULT_POLICY="DROP"
FIREWALL_ALLOWED_PORTS="22,80,443,8080,8083,8089,8091,8092,8093,8094,8095,8096"

# =============================================================================
# DEPLOYMENT CONFIGURATION
# =============================================================================

# Container Configuration
CONTAINER_RUNTIME="docker"
CONTAINER_NETWORK="lucid-network"
CONTAINER_SUBNET="172.20.0.0/16"

# Scaling Configuration
SCALING_ENABLED=$(echo "$env_values" | grep "^SCALING_ENABLED=" | cut -d'=' -f2)
AUTO_SCALING=$(echo "$env_values" | grep "^AUTO_SCALING=" | cut -d'=' -f2)
LOAD_BALANCER=$(echo "$env_values" | grep "^LOAD_BALANCER=" | cut -d'=' -f2)

# Development Configuration
LOCAL_DEVELOPMENT=$(echo "$env_values" | grep "^LOCAL_DEVELOPMENT=" | cut -d'=' -f2)
HOT_RELOAD=$(echo "$env_values" | grep "^HOT_RELOAD=" | cut -d'=' -f2)

# =============================================================================
# BACKUP CONFIGURATION
# =============================================================================

# Backup Settings
BACKUP_ENABLED=true
BACKUP_SCHEDULE="0 2 * * *"
BACKUP_RETENTION_DAYS=30
BACKUP_COMPRESSION=true
BACKUP_ENCRYPTION=true

# Backup Storage
BACKUP_STORAGE_TYPE="local"
BACKUP_STORAGE_PATH="/var/backups/lucid"
BACKUP_S3_BUCKET=""
BACKUP_S3_REGION=""
BACKUP_S3_ACCESS_KEY=""
BACKUP_S3_SECRET_KEY=""

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Log Configuration
LOG_ENABLED=true
LOG_LEVEL=$(echo "$env_values" | grep "^LOG_LEVEL=" | cut -d'=' -f2)
LOG_FORMAT="json"
LOG_OUTPUT="file"
LOG_FILE="/var/log/lucid/lucid.log"
LOG_MAX_SIZE="100MB"
LOG_MAX_FILES=10
LOG_COMPRESS=true

# Log Aggregation
LOG_AGGREGATION_ENABLED=false
LOG_AGGREGATION_HOST=""
LOG_AGGREGATION_PORT=514
LOG_AGGREGATION_PROTOCOL="udp"

# =============================================================================
# ALERTING CONFIGURATION
# =============================================================================

# Alert Configuration
ALERTING_ENABLED=true
ALERTING_PROVIDER="email"
ALERTING_EMAIL_SMTP_HOST=""
ALERTING_EMAIL_SMTP_PORT=587
ALERTING_EMAIL_SMTP_USER=""
ALERTING_EMAIL_SMTP_PASSWORD=""
ALERTING_EMAIL_FROM=""
ALERTING_EMAIL_TO=""

# Alert Thresholds
ALERT_CPU_THRESHOLD=80
ALERT_MEMORY_THRESHOLD=80
ALERT_DISK_THRESHOLD=90
ALERT_NETWORK_THRESHOLD=1000
ALERT_ERROR_RATE_THRESHOLD=5

EOF
    
    print_success "Environment file generated: $output_file"
}

# Function to validate environment file
validate_env_file() {
    local env_file=$1
    
    print_info "Validating environment file: $env_file"
    
    if [ ! -f "$env_file" ]; then
        print_error "Environment file not found: $env_file"
        return 1
    fi
    
    # Check for required variables
    local required_vars=(
        "PROJECT_NAME"
        "ENVIRONMENT"
        "JWT_SECRET"
        "MONGODB_PASSWORD"
        "ENCRYPTION_KEY"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "$env_file"; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_error "Missing required variables: ${missing_vars[*]}"
        return 1
    fi
    
    # Check for empty values
    local empty_vars=()
    
    while IFS= read -r line; do
        if [[ "$line" =~ ^[A-Z_]+=.*$ ]] && [[ "$line" =~ =$ ]]; then
            local var_name=$(echo "$line" | cut -d'=' -f1)
            empty_vars+=("$var_name")
        fi
    done < "$env_file"
    
    if [ ${#empty_vars[@]} -gt 0 ]; then
        print_warning "Variables with empty values: ${empty_vars[*]}"
    fi
    
    print_success "Environment file validation completed"
    return 0
}

# Main execution
main() {
    # Parse command line arguments
    local environment=""
    local template="default"
    local output_file=""
    local force=false
    local verbose=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                environment="$2"
                shift 2
                ;;
            -t|--template)
                template="$2"
                shift 2
                ;;
            -o|--output)
                output_file="$2"
                shift 2
                ;;
            -f|--force)
                force=true
                shift
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Validate required parameters
    if [ -z "$environment" ]; then
        print_error "Environment is required"
        show_usage
        exit 1
    fi
    
    # Set default output file if not provided
    if [ -z "$output_file" ]; then
        output_file="$CONFIGS_DIR/.env.$environment"
    fi
    
    # Validate environment
    case "$environment" in
        "development"|"staging"|"production"|"test")
            ;;
        *)
            print_error "Invalid environment: $environment"
            print_info "Valid environments: development, staging, production, test"
            exit 1
            ;;
    esac
    
    # Validate template
    case "$template" in
        "default"|"pi"|"cloud"|"local")
            ;;
        *)
            print_error "Invalid template: $template"
            print_info "Valid templates: default, pi, cloud, local"
            exit 1
            ;;
    esac
    
    print_info "Generating environment configuration..."
    print_info "Environment: $environment"
    print_info "Template: $template"
    print_info "Output file: $output_file"
    
    # Generate environment file
    if generate_env_file "$environment" "$template" "$output_file" "$force"; then
        print_success "Environment file generated successfully"
        
        # Validate the generated file
        if validate_env_file "$output_file"; then
            print_success "Environment file validation passed"
        else
            print_warning "Environment file validation failed"
        fi
        
        print_info "Next steps:"
        print_info "1. Review the generated environment file: $output_file"
        print_info "2. Update any environment-specific values"
        print_info "3. Secure the file with appropriate permissions"
        print_info "4. Use the file in your deployment configuration"
        
    else
        print_error "Failed to generate environment file"
        exit 1
    fi
}

# Run main function
main "$@"
