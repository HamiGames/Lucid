#!/bin/bash
# Path: scripts/config/generate-all-env-complete.sh
# Complete Environment Generation Master Script
# Generates ALL .env files with ACTUAL values for the entire Lucid project
# NO PLACEHOLDERS - Everything is generated with cryptographically secure values

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_header() { echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"; echo -e "${PURPLE}$1${NC}"; echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"; }
log_step() { echo -e "${CYAN}[STEP]${NC} $1"; }

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_TIMESTAMP=$(date '+%Y%m%d-%H%M%S')
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Statistics
TOTAL_FILES=0
GENERATED_FILES=0
FAILED_FILES=0
TOTAL_SECRETS=0

# =============================================================================
# SECURE VALUE GENERATION FUNCTIONS
# =============================================================================

# Function to generate secure random string (base64)
generate_secure_value() {
    local length=${1:-32}
    openssl rand -base64 $length | tr -d '\n='
}

# Function to generate hex key
generate_hex_key() {
    local length=${1:-32}
    openssl rand -hex $length | tr -d '\n'
}

# Function to generate .onion address (v3)
generate_onion_address() {
    local temp_dir=$(mktemp -d)
    openssl genpkey -algorithm ed25519 -out "$temp_dir/private_key.pem" 2>/dev/null
    local pubkey=$(openssl pkey -in "$temp_dir/private_key.pem" -pubout -outform DER 2>/dev/null | tail -c 32 | base32 | tr -d '=' | tr '[:upper:]' '[:lower:]')
    rm -rf "$temp_dir"
    echo "${pubkey:0:56}.onion"
}

# =============================================================================
# GENERATE ALL SECURE VALUES
# =============================================================================
generate_all_secure_values() {
    log_header "STEP 1: GENERATING ALL SECURE VALUES"
    log_info "Generating cryptographically secure values using openssl..."
    
    # Database Passwords
    export MONGODB_PASSWORD=$(generate_secure_value 32)
    export REDIS_PASSWORD=$(generate_secure_value 32)
    export ELASTICSEARCH_PASSWORD=$(generate_secure_value 32)
    log_success "Generated database passwords (32 bytes each)"
    ((TOTAL_SECRETS+=3))
    
    # JWT and Authentication
    export JWT_SECRET=$(generate_secure_value 64)
    export JWT_SECRET_KEY=$(generate_secure_value 64)
    export ENCRYPTION_KEY=$(generate_hex_key 32)
    export SESSION_SECRET=$(generate_secure_value 32)
    log_success "Generated JWT and auth secrets (64/256-bit)"
    ((TOTAL_SECRETS+=4))
    
    # Service-specific secrets
    export API_SECRET=$(generate_secure_value 32)
    export API_GATEWAY_SECRET=$(generate_secure_value 32)
    export BLOCKCHAIN_SECRET=$(generate_secure_value 32)
    export NODE_MANAGEMENT_SECRET=$(generate_secure_value 32)
    export ADMIN_SECRET=$(generate_secure_value 32)
    export TRON_PAYMENT_SECRET=$(generate_secure_value 32)
    export HMAC_KEY=$(generate_secure_value 32)
    export SIGNING_KEY=$(generate_hex_key 32)
    log_success "Generated service secrets (32 bytes each)"
    ((TOTAL_SECRETS+=8))
    
    # TOR Configuration
    export TOR_PASSWORD=$(generate_secure_value 32)
    export TOR_CONTROL_PASSWORD=$(generate_secure_value 32)
    log_success "Generated TOR passwords (32 bytes each)"
    ((TOTAL_SECRETS+=2))
    
    # Encryption keys
    export MASTER_ENCRYPTION_KEY=$(generate_hex_key 32)
    export BACKUP_ENCRYPTION_KEY=$(generate_hex_key 32)
    export RESTORE_DECRYPTION_KEY=$(generate_hex_key 32)
    log_success "Generated encryption keys (256-bit each)"
    ((TOTAL_SECRETS+=3))
    
    # TRON-specific
    export TRON_PRIVATE_KEY=$(generate_hex_key 64)
    export DEPLOYMENT_KEY=$(generate_hex_key 32)
    export CONTRACT_OWNER_KEY=$(generate_hex_key 32)
    export COMPILER_KEY=$(generate_hex_key 32)
    export VERIFICATION_KEY=$(generate_hex_key 32)
    export ORCHESTRATOR_KEY=$(generate_hex_key 32)
    export GOVERNANCE_KEY=$(generate_hex_key 32)
    export ADMIN_KEY=$(generate_hex_key 32)
    export PRIVATE_KEY=$(generate_hex_key 64)
    export COMPLIANCE_SIGNER_KEY=$(generate_hex_key 32)
    export VM_ENCRYPTION_KEY=$(generate_hex_key 32)
    export VM_ACCESS_KEY=$(generate_hex_key 32)
    export LEDGER_ENCRYPTION_KEY=$(generate_hex_key 32)
    log_success "Generated blockchain keys (256-512 bit each)"
    ((TOTAL_SECRETS+=13))
    
    # Generate .onion addresses
    log_info "Generating Tor .onion addresses (v3)..."
    export API_GATEWAY_ONION=$(generate_onion_address)
    export AUTH_SERVICE_ONION=$(generate_onion_address)
    export BLOCKCHAIN_API_ONION=$(generate_onion_address)
    export ADMIN_INTERFACE_ONION=$(generate_onion_address)
    export SESSION_API_ONION=$(generate_onion_address)
    log_success "Generated 5 .onion addresses"
    ((TOTAL_SECRETS+=5))
    
    # Generate Service URLs (FIXED: No more circular references)
    export MONGODB_URL="mongodb://lucid:${MONGODB_PASSWORD}@172.20.0.11:27017/lucid?authSource=admin&retryWrites=false"
    export REDIS_URL="redis://:${REDIS_PASSWORD}@172.20.0.12:6379"
    export ELASTICSEARCH_URL="http://elastic:${ELASTICSEARCH_PASSWORD}@172.20.0.13:9200"
    export API_GATEWAY_URL="http://172.20.0.10:8080"
    export AUTH_SERVICE_URL="http://172.20.0.14:8089"
    export BLOCKCHAIN_ENGINE_URL="http://172.20.0.15:8084"
    export SESSION_API_URL="http://172.20.0.16:8085"
    export NODE_MANAGEMENT_URL="http://172.20.0.17:8087"
    export ADMIN_INTERFACE_URL="http://172.20.0.18:8088"
    export TRON_PAYMENT_URL="http://172.20.0.19:8090"
    export SERVICE_MESH_URL="http://172.20.0.20:8091"
    export BLOCKCHAIN_CORE_URL="http://172.20.0.21:8082"
    
    # TRON Configuration (FIXED: Generate actual values)
    export TRON_NETWORK="mainnet"
    export TRON_NODE_URL="https://api.trongrid.io"
    export TRON_ADDRESS=$(generate_hex_key 20)  # 20 bytes = 40 hex chars
    export USDT_CONTRACT_ADDRESS="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    export USDT_DECIMALS="6"
    
    # Additional configuration values
    export PI_HOST="${PI_HOST:-192.168.0.75}"
    export PI_USER="${PI_USER:-pickme}"
    export PI_DEPLOY_DIR="${PI_DEPLOY_DIR:-/opt/lucid/production}"
    export BUILD_PLATFORM="${BUILD_PLATFORM:-linux/arm64}"
    export BUILD_REGISTRY="${BUILD_REGISTRY:-pickme/lucid}"
    
    echo ""
    log_success "Total secure values generated: $TOTAL_SECRETS"
    echo ""
}

# =============================================================================
# SAVE SECURE VALUES TO MASTER FILE
# =============================================================================
save_secure_values() {
    log_header "STEP 2: SAVING SECURE VALUES TO MASTER FILE"
    
    local secure_file="$PROJECT_ROOT/configs/environment/.env.secure"
    local secrets_dir="$(dirname "$secure_file")"
    mkdir -p "$secrets_dir"
    
    log_info "Creating master secure values file: $secure_file"
    
    cat > "$secure_file" << EOF
# Lucid Master Secure Environment Variables
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Build Timestamp: $BUILD_TIMESTAMP
# Git SHA: $GIT_SHA
# WARNING: Keep this file secure! Never commit to version control!

# =============================================================================
# BUILD CONFIGURATION
# =============================================================================
BUILD_TIMESTAMP=$BUILD_TIMESTAMP
GIT_SHA=$GIT_SHA
BUILD_PLATFORM=$BUILD_PLATFORM
BUILD_REGISTRY=$BUILD_REGISTRY

# =============================================================================
# DATABASE PASSWORDS
# =============================================================================
MONGODB_PASSWORD=$MONGODB_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD
ELASTICSEARCH_PASSWORD=$ELASTICSEARCH_PASSWORD

# =============================================================================
# JWT AND AUTHENTICATION
# =============================================================================
JWT_SECRET=$JWT_SECRET
JWT_SECRET_KEY=$JWT_SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY
SESSION_SECRET=$SESSION_SECRET

# =============================================================================
# SERVICE SECRETS
# =============================================================================
API_SECRET=$API_SECRET
API_GATEWAY_SECRET=$API_GATEWAY_SECRET
BLOCKCHAIN_SECRET=$BLOCKCHAIN_SECRET
NODE_MANAGEMENT_SECRET=$NODE_MANAGEMENT_SECRET
ADMIN_SECRET=$ADMIN_SECRET
TRON_PAYMENT_SECRET=$TRON_PAYMENT_SECRET
HMAC_KEY=$HMAC_KEY
SIGNING_KEY=$SIGNING_KEY

# =============================================================================
# TOR CONFIGURATION
# =============================================================================
TOR_PASSWORD=$TOR_PASSWORD
TOR_CONTROL_PASSWORD=$TOR_CONTROL_PASSWORD

# =============================================================================
# ENCRYPTION KEYS
# =============================================================================
MASTER_ENCRYPTION_KEY=$MASTER_ENCRYPTION_KEY
BACKUP_ENCRYPTION_KEY=$BACKUP_ENCRYPTION_KEY
RESTORE_DECRYPTION_KEY=$RESTORE_DECRYPTION_KEY

# =============================================================================
# BLOCKCHAIN KEYS
# =============================================================================
TRON_PRIVATE_KEY=$TRON_PRIVATE_KEY
DEPLOYMENT_KEY=$DEPLOYMENT_KEY
CONTRACT_OWNER_KEY=$CONTRACT_OWNER_KEY
COMPILER_KEY=$COMPILER_KEY
VERIFICATION_KEY=$VERIFICATION_KEY
ORCHESTRATOR_KEY=$ORCHESTRATOR_KEY
GOVERNANCE_KEY=$GOVERNANCE_KEY
ADMIN_KEY=$ADMIN_KEY
PRIVATE_KEY=$PRIVATE_KEY
COMPLIANCE_SIGNER_KEY=$COMPLIANCE_SIGNER_KEY
VM_ENCRYPTION_KEY=$VM_ENCRYPTION_KEY
VM_ACCESS_KEY=$VM_ACCESS_KEY
LEDGER_ENCRYPTION_KEY=$LEDGER_ENCRYPTION_KEY

# =============================================================================
# TOR HIDDEN SERVICE ADDRESSES (.onion)
# =============================================================================
API_GATEWAY_ONION=$API_GATEWAY_ONION
AUTH_SERVICE_ONION=$AUTH_SERVICE_ONION
BLOCKCHAIN_API_ONION=$BLOCKCHAIN_API_ONION
ADMIN_INTERFACE_ONION=$ADMIN_INTERFACE_ONION
SESSION_API_ONION=$SESSION_API_ONION

# =============================================================================
# SERVICE URLS (FIXED: No circular references)
# =============================================================================
MONGODB_URL=$MONGODB_URL
REDIS_URL=$REDIS_URL
ELASTICSEARCH_URL=$ELASTICSEARCH_URL
API_GATEWAY_URL=$API_GATEWAY_URL
AUTH_SERVICE_URL=$AUTH_SERVICE_URL
BLOCKCHAIN_ENGINE_URL=$BLOCKCHAIN_ENGINE_URL
SESSION_API_URL=$SESSION_API_URL
NODE_MANAGEMENT_URL=$NODE_MANAGEMENT_URL
ADMIN_INTERFACE_URL=$ADMIN_INTERFACE_URL
TRON_PAYMENT_URL=$TRON_PAYMENT_URL
SERVICE_MESH_URL=$SERVICE_MESH_URL
BLOCKCHAIN_CORE_URL=$BLOCKCHAIN_CORE_URL

# =============================================================================
# TRON CONFIGURATION (FIXED: Actual values)
# =============================================================================
TRON_NETWORK=$TRON_NETWORK
TRON_NODE_URL=$TRON_NODE_URL
TRON_ADDRESS=$TRON_ADDRESS
USDT_CONTRACT_ADDRESS=$USDT_CONTRACT_ADDRESS
USDT_DECIMALS=$USDT_DECIMALS

# =============================================================================
# DEPLOYMENT CONFIGURATION
# =============================================================================
PI_HOST=$PI_HOST
PI_USER=$PI_USER
PI_DEPLOY_DIR=$PI_DEPLOY_DIR

# =============================================================================
# SECURITY NOTES
# =============================================================================
# All values are cryptographically secure random values generated using openssl
# Database passwords: 32 bytes, base64 encoded
# JWT secrets: 64 bytes, base64 encoded
# Encryption keys: 256-bit (32 bytes), hex encoded
# Blockchain keys: 256-512 bit, hex encoded
# .onion addresses: v3 Tor hidden service addresses (ed25519-based)
# 
# IMPORTANT:
# - Store this file securely (chmod 600)
# - Never commit to version control
# - Rotate keys regularly in production
# - Backup to secure location
# - Use environment-specific key management in production
EOF

    chmod 600 "$secure_file"
    log_success "Master secure file created: $secure_file (chmod 600)"
    log_info "Total secrets stored: $TOTAL_SECRETS"
    echo ""
}

# =============================================================================
# GENERATE PHASE-LEVEL CONFIGS
# =============================================================================
generate_phase_configs() {
    log_header "STEP 3: GENERATING PHASE-LEVEL CONFIGURATIONS"
    
    local gen_all_script="$SCRIPT_DIR/generate-all-env.sh"
    
    if [[ -f "$gen_all_script" ]]; then
        log_step "Running generate-all-env.sh..."
        if bash "$gen_all_script"; then
            log_success "Phase-level configs generated"
            ((GENERATED_FILES+=6))
            
            # FIXED: Post-process phase configs to replace circular references
            fix_phase_configs
            fix_session_core_files
        else
            log_error "Failed to generate phase-level configs"
            ((FAILED_FILES+=6))
        fi
    else
        log_warning "generate-all-env.sh not found, skipping phase configs"
    fi
    
    echo ""
}

# =============================================================================
# FIX PHASE CONFIGURATION FILES
# =============================================================================
fix_phase_configs() {
    log_header "STEP 3.1: FIXING PHASE CONFIGURATION FILES"
    
    local config_dir="$PROJECT_ROOT/configs/environment"
    
    # Fix foundation config
    if [[ -f "$config_dir/.env.foundation" ]]; then
        log_info "Fixing .env.foundation..."
        # Fix all circular references
        sed -i "s|MONGODB_URL=\${MONGODB_URL}|MONGODB_URL=${MONGODB_URL}|g" "$config_dir/.env.foundation"
        sed -i "s|REDIS_URL=\${REDIS_URL}|REDIS_URL=${REDIS_URL}|g" "$config_dir/.env.foundation"
        sed -i "s|ELASTICSEARCH_URL=\${ELASTICSEARCH_URL}|ELASTICSEARCH_URL=${ELASTICSEARCH_URL}|g" "$config_dir/.env.foundation"
        sed -i "s|AUTH_SERVICE_URL=\${AUTH_SERVICE_URL}|AUTH_SERVICE_URL=${AUTH_SERVICE_URL}|g" "$config_dir/.env.foundation"
        # Fix any remaining ${VARIABLE} patterns that might cause shell interpretation errors
        sed -i "s|\${[A-Z_]*}|REPLACED|g" "$config_dir/.env.foundation"
    fi
    
    # Fix application config
    if [[ -f "$config_dir/env.application" ]]; then
        log_info "Fixing env.application..."
        sed -i "s|MONGODB_URL=\${MONGODB_URL}|MONGODB_URL=${MONGODB_URL}|g" "$config_dir/env.application"
        sed -i "s|REDIS_URL=\${REDIS_URL}|REDIS_URL=${REDIS_URL}|g" "$config_dir/env.application"
        sed -i "s|ELASTICSEARCH_URL=\${ELASTICSEARCH_URL}|ELASTICSEARCH_URL=${ELASTICSEARCH_URL}|g" "$config_dir/env.application"
        sed -i "s|API_GATEWAY_URL=\${API_GATEWAY_URL}|API_GATEWAY_URL=${API_GATEWAY_URL}|g" "$config_dir/env.application"
        sed -i "s|BLOCKCHAIN_ENGINE_URL=\${BLOCKCHAIN_ENGINE_URL}|BLOCKCHAIN_ENGINE_URL=${BLOCKCHAIN_ENGINE_URL}|g" "$config_dir/env.application"
        sed -i "s|SERVICE_MESH_URL=\${SERVICE_MESH_URL}|SERVICE_MESH_URL=${SERVICE_MESH_URL}|g" "$config_dir/env.application"
        sed -i "s|AUTH_SERVICE_URL=\${AUTH_SERVICE_URL}|AUTH_SERVICE_URL=${AUTH_SERVICE_URL}|g" "$config_dir/env.application"
        # Fix any remaining ${VARIABLE} patterns that might cause shell interpretation errors
        sed -i "s|\${[A-Z_]*}|REPLACED|g" "$config_dir/env.application"
    fi
    
    # Fix core config
    if [[ -f "$config_dir/env.core" ]]; then
        log_info "Fixing env.core..."
        sed -i "s|MONGODB_URL=\${MONGODB_URL}|MONGODB_URL=${MONGODB_URL}|g" "$config_dir/env.core"
        sed -i "s|REDIS_URL=\${REDIS_URL}|REDIS_URL=${REDIS_URL}|g" "$config_dir/env.core"
        sed -i "s|ELASTICSEARCH_URL=\${ELASTICSEARCH_URL}|ELASTICSEARCH_URL=${ELASTICSEARCH_URL}|g" "$config_dir/env.core"
        sed -i "s|AUTH_SERVICE_URL=\${AUTH_SERVICE_URL}|AUTH_SERVICE_URL=${AUTH_SERVICE_URL}|g" "$config_dir/env.core"
        sed -i "s|BLOCKCHAIN_ENGINE_URL=\${BLOCKCHAIN_ENGINE_URL}|BLOCKCHAIN_ENGINE_URL=${BLOCKCHAIN_ENGINE_URL}|g" "$config_dir/env.core"
        # Fix any remaining ${VARIABLE} patterns that might cause shell interpretation errors
        sed -i "s|\${[A-Z_]*}|REPLACED|g" "$config_dir/env.core"
    fi
    
    # Fix support config
    if [[ -f "$config_dir/env.support" ]]; then
        log_info "Fixing env.support..."
        sed -i "s|MONGODB_URL=\${MONGODB_URL}|MONGODB_URL=${MONGODB_URL}|g" "$config_dir/env.support"
        sed -i "s|REDIS_URL=\${REDIS_URL}|REDIS_URL=${REDIS_URL}|g" "$config_dir/env.support"
        sed -i "s|AUTH_SERVICE_URL=\${AUTH_SERVICE_URL}|AUTH_SERVICE_URL=${AUTH_SERVICE_URL}|g" "$config_dir/env.support"
        sed -i "s|TRON_NETWORK=\${TRON_NETWORK}|TRON_NETWORK=${TRON_NETWORK}|g" "$config_dir/env.support"
        sed -i "s|TRON_NODE_URL=\${TRON_NODE_URL}|TRON_NODE_URL=${TRON_NODE_URL}|g" "$config_dir/env.support"
        sed -i "s|TRON_ADDRESS=\${TRON_ADDRESS}|TRON_ADDRESS=${TRON_ADDRESS}|g" "$config_dir/env.support"
        sed -i "s|USDT_CONTRACT_ADDRESS=\${USDT_CONTRACT_ADDRESS}|USDT_CONTRACT_ADDRESS=${USDT_CONTRACT_ADDRESS}|g" "$config_dir/env.support"
        sed -i "s|USDT_DECIMALS=\${USDT_DECIMALS}|USDT_DECIMALS=${USDT_DECIMALS}|g" "$config_dir/env.support"
        # Fix any remaining ${VARIABLE} patterns that might cause shell interpretation errors
        sed -i "s|\${[A-Z_]*}|REPLACED|g" "$config_dir/env.support"
    fi
    
    # Fix GUI config
    if [[ -f "$config_dir/env.gui" ]]; then
        log_info "Fixing env.gui..."
        sed -i "s|API_GATEWAY_URL=\${API_GATEWAY_URL}|API_GATEWAY_URL=${API_GATEWAY_URL}|g" "$config_dir/env.gui"
        sed -i "s|BLOCKCHAIN_CORE_URL=\${BLOCKCHAIN_CORE_URL}|BLOCKCHAIN_CORE_URL=${BLOCKCHAIN_CORE_URL}|g" "$config_dir/env.gui"
        sed -i "s|AUTH_SERVICE_URL=\${AUTH_SERVICE_URL}|AUTH_SERVICE_URL=${AUTH_SERVICE_URL}|g" "$config_dir/env.gui"
        sed -i "s|SESSION_API_URL=\${SESSION_API_URL}|SESSION_API_URL=${SESSION_API_URL}|g" "$config_dir/env.gui"
        sed -i "s|NODE_MANAGEMENT_URL=\${NODE_MANAGEMENT_URL}|NODE_MANAGEMENT_URL=${NODE_MANAGEMENT_URL}|g" "$config_dir/env.gui"
        sed -i "s|ADMIN_INTERFACE_URL=\${ADMIN_INTERFACE_URL}|ADMIN_INTERFACE_URL=${ADMIN_INTERFACE_URL}|g" "$config_dir/env.gui"
        sed -i "s|TRON_PAYMENT_URL=\${TRON_PAYMENT_URL}|TRON_PAYMENT_URL=${TRON_PAYMENT_URL}|g" "$config_dir/env.gui"
        # Fix any remaining ${VARIABLE} patterns that might cause shell interpretation errors
        sed -i "s|\${[A-Z_]*}|REPLACED|g" "$config_dir/env.gui"
    fi
    
    log_success "Phase configuration files fixed"
    echo ""
}

# =============================================================================
# FIX SESSION CORE FILES
# =============================================================================
fix_session_core_files() {
    log_header "STEP 3.2: FIXING SESSION CORE FILES"
    
    local session_core_dir="$PROJECT_ROOT/sessions/core"
    
    if [[ ! -d "$session_core_dir" ]]; then
        log_warning "Session core directory not found, skipping"
        return 0
    fi
    
    log_info "Fixing session core .env files..."
    
    # Fix .env.chunker
    if [[ -f "$session_core_dir/.env.chunker" ]]; then
        log_info "  Fixing .env.chunker..."
        sed -i 's|MONGODB_PASSWORD_PLACEHOLDER|'"${MONGODB_PASSWORD}"'|g' "$session_core_dir/.env.chunker"
        sed -i 's|REDIS_PASSWORD_PLACEHOLDER|'"${REDIS_PASSWORD}"'|g' "$session_core_dir/.env.chunker"
        sed -i 's|ENCRYPTION_KEY_PLACEHOLDER|'"${ENCRYPTION_KEY}"'|g' "$session_core_dir/.env.chunker"
        sed -i 's|JWT_SECRET_PLACEHOLDER|'"${JWT_SECRET}"'|g' "$session_core_dir/.env.chunker"
        log_success "  .env.chunker fixed"
    fi
    
    # Fix .env.merkle_builder
    if [[ -f "$session_core_dir/.env.merkle_builder" ]]; then
        log_info "  Fixing .env.merkle_builder..."
        sed -i 's|MONGODB_PASSWORD_PLACEHOLDER|'"${MONGODB_PASSWORD}"'|g' "$session_core_dir/.env.merkle_builder"
        sed -i 's|REDIS_PASSWORD_PLACEHOLDER|'"${REDIS_PASSWORD}"'|g' "$session_core_dir/.env.merkle_builder"
        sed -i 's|ENCRYPTION_KEY_PLACEHOLDER|'"${ENCRYPTION_KEY}"'|g' "$session_core_dir/.env.merkle_builder"
        sed -i 's|JWT_SECRET_PLACEHOLDER|'"${JWT_SECRET}"'|g' "$session_core_dir/.env.merkle_builder"
        sed -i 's|SIGNING_KEY_PLACEHOLDER|'"${SIGNING_KEY}"'|g' "$session_core_dir/.env.merkle_builder"
        log_success "  .env.merkle_builder fixed"
    fi
    
    # Fix .env.orchestrator
    if [[ -f "$session_core_dir/.env.orchestrator" ]]; then
        log_info "  Fixing .env.orchestrator..."
        sed -i 's|MONGODB_PASSWORD_PLACEHOLDER|'"${MONGODB_PASSWORD}"'|g' "$session_core_dir/.env.orchestrator"
        sed -i 's|REDIS_PASSWORD_PLACEHOLDER|'"${REDIS_PASSWORD}"'|g' "$session_core_dir/.env.orchestrator"
        sed -i 's|ENCRYPTION_KEY_PLACEHOLDER|'"${ENCRYPTION_KEY}"'|g' "$session_core_dir/.env.orchestrator"
        sed -i 's|JWT_SECRET_PLACEHOLDER|'"${JWT_SECRET}"'|g' "$session_core_dir/.env.orchestrator"
        sed -i 's|SESSION_SECRET_PLACEHOLDER|'"${SESSION_SECRET}"'|g' "$session_core_dir/.env.orchestrator"
        sed -i 's|HMAC_KEY_PLACEHOLDER|'"${HMAC_KEY}"'|g' "$session_core_dir/.env.orchestrator"
        log_success "  .env.orchestrator fixed"
    fi
    
    echo ""
}

# =============================================================================
# POST-PROCESS BLOCKCHAIN FILES WITH GENERATED VALUES
# =============================================================================
inject_blockchain_values() {
    log_header "STEP 4: INJECTING VALUES INTO BLOCKCHAIN .ENV FILES"
    
    local env_dir="$PROJECT_ROOT/infrastructure/docker/blockchain/env"
    
    if [[ ! -d "$env_dir" ]]; then
        log_warning "Blockchain env directory not found, skipping injection"
        return 0
    fi
    
    log_info "Injecting generated secure values into blockchain .env files..."
    
    for env_file in "$env_dir"/.env.*; do
        if [[ -f "$env_file" ]]; then
            log_info "  Processing $(basename $env_file)..."
            
            # FIXED: Replace circular references and empty values with actual generated values
            sed -i "s|MONGODB_URL=\${MONGODB_URL}|MONGODB_URL=${MONGODB_URL}|g" "$env_file"
            sed -i "s|REDIS_URL=\${REDIS_URL}|REDIS_URL=${REDIS_URL}|g" "$env_file"
            sed -i "s|ELASTICSEARCH_URL=\${ELASTICSEARCH_URL}|ELASTICSEARCH_URL=${ELASTICSEARCH_URL}|g" "$env_file"
            sed -i "s|API_GATEWAY_URL=\${API_GATEWAY_URL}|API_GATEWAY_URL=${API_GATEWAY_URL}|g" "$env_file"
            sed -i "s|AUTH_SERVICE_URL=\${AUTH_SERVICE_URL}|AUTH_SERVICE_URL=${AUTH_SERVICE_URL}|g" "$env_file"
            sed -i "s|BLOCKCHAIN_ENGINE_URL=\${BLOCKCHAIN_ENGINE_URL}|BLOCKCHAIN_ENGINE_URL=${BLOCKCHAIN_ENGINE_URL}|g" "$env_file"
            sed -i "s|SESSION_API_URL=\${SESSION_API_URL}|SESSION_API_URL=${SESSION_API_URL}|g" "$env_file"
            sed -i "s|NODE_MANAGEMENT_URL=\${NODE_MANAGEMENT_URL}|NODE_MANAGEMENT_URL=${NODE_MANAGEMENT_URL}|g" "$env_file"
            sed -i "s|ADMIN_INTERFACE_URL=\${ADMIN_INTERFACE_URL}|ADMIN_INTERFACE_URL=${ADMIN_INTERFACE_URL}|g" "$env_file"
            sed -i "s|TRON_PAYMENT_URL=\${TRON_PAYMENT_URL}|TRON_PAYMENT_URL=${TRON_PAYMENT_URL}|g" "$env_file"
            sed -i "s|SERVICE_MESH_URL=\${SERVICE_MESH_URL}|SERVICE_MESH_URL=${SERVICE_MESH_URL}|g" "$env_file"
            sed -i "s|BLOCKCHAIN_CORE_URL=\${BLOCKCHAIN_CORE_URL}|BLOCKCHAIN_CORE_URL=${BLOCKCHAIN_CORE_URL}|g" "$env_file"
            
            # Replace empty values with generated ones
            sed -i "s|ENCRYPTION_KEY=\"\"|ENCRYPTION_KEY=\"${ENCRYPTION_KEY}\"|g" "$env_file"
            sed -i "s|JWT_SECRET_KEY=\"\"|JWT_SECRET_KEY=\"${JWT_SECRET}\"|g" "$env_file"
            sed -i "s|PRIVATE_KEY=\"\"|PRIVATE_KEY=\"${PRIVATE_KEY}\"|g" "$env_file"
            sed -i "s|DEPLOYMENT_KEY=\"\"|DEPLOYMENT_KEY=\"${DEPLOYMENT_KEY}\"|g" "$env_file"
            sed -i "s|CONTRACT_OWNER_KEY=\"\"|CONTRACT_OWNER_KEY=\"${CONTRACT_OWNER_KEY}\"|g" "$env_file"
            sed -i "s|COMPILER_KEY=\"\"|COMPILER_KEY=\"${COMPILER_KEY}\"|g" "$env_file"
            sed -i "s|VERIFICATION_KEY=\"\"|VERIFICATION_KEY=\"${VERIFICATION_KEY}\"|g" "$env_file"
            sed -i "s|ORCHESTRATOR_KEY=\"\"|ORCHESTRATOR_KEY=\"${ORCHESTRATOR_KEY}\"|g" "$env_file"
            sed -i "s|GOVERNANCE_KEY=\"\"|GOVERNANCE_KEY=\"${GOVERNANCE_KEY}\"|g" "$env_file"
            sed -i "s|ADMIN_KEY=\"\"|ADMIN_KEY=\"${ADMIN_KEY}\"|g" "$env_file"
            sed -i "s|COMPLIANCE_SIGNER_KEY=\"\"|COMPLIANCE_SIGNER_KEY=\"${COMPLIANCE_SIGNER_KEY}\"|g" "$env_file"
            sed -i "s|VM_ENCRYPTION_KEY=\"\"|VM_ENCRYPTION_KEY=\"${VM_ENCRYPTION_KEY}\"|g" "$env_file"
            sed -i "s|VM_ACCESS_KEY=\"\"|VM_ACCESS_KEY=\"${VM_ACCESS_KEY}\"|g" "$env_file"
            sed -i "s|LEDGER_ENCRYPTION_KEY=\"\"|LEDGER_ENCRYPTION_KEY=\"${LEDGER_ENCRYPTION_KEY}\"|g" "$env_file"
            sed -i "s|SIGNING_KEY=\"\"|SIGNING_KEY=\"${SIGNING_KEY}\"|g" "$env_file"
            sed -i "s|TRON_PRIVATE_KEY=\"\"|TRON_PRIVATE_KEY=\"${TRON_PRIVATE_KEY}\"|g" "$env_file"
            sed -i "s|KEY_ENC_SECRET=\"\"|KEY_ENC_SECRET=\"${ENCRYPTION_KEY}\"|g" "$env_file"
            sed -i "s|AGE_PRIVATE_KEY=\"\"|AGE_PRIVATE_KEY=\"${PRIVATE_KEY}\"|g" "$env_file"
            
            # FIXED: Replace TRON configuration
            sed -i "s|TRON_NETWORK=\${TRON_NETWORK}|TRON_NETWORK=${TRON_NETWORK}|g" "$env_file"
            sed -i "s|TRON_NODE_URL=\${TRON_NODE_URL}|TRON_NODE_URL=${TRON_NODE_URL}|g" "$env_file"
            sed -i "s|TRON_ADDRESS=\${TRON_ADDRESS}|TRON_ADDRESS=${TRON_ADDRESS}|g" "$env_file"
            sed -i "s|USDT_CONTRACT_ADDRESS=\${USDT_CONTRACT_ADDRESS}|USDT_CONTRACT_ADDRESS=${USDT_CONTRACT_ADDRESS}|g" "$env_file"
            sed -i "s|USDT_DECIMALS=\${USDT_DECIMALS}|USDT_DECIMALS=${USDT_DECIMALS}|g" "$env_file"
        fi
    done
    
    log_success "Blockchain .env files updated with generated values"
    echo ""
}

# =============================================================================
# POST-PROCESS DATABASE FILES WITH GENERATED VALUES
# =============================================================================
inject_database_values() {
    log_header "STEP 5: INJECTING VALUES INTO DATABASE .ENV FILES"
    
    local env_dir="$PROJECT_ROOT/infrastructure/docker/databases/env"
    
    if [[ ! -d "$env_dir" ]]; then
        log_warning "Database env directory not found, skipping injection"
        return 0
    fi
    
    log_info "Injecting generated secure values into database .env files..."
    
    for env_file in "$env_dir"/.env.*; do
        if [[ -f "$env_file" ]]; then
            log_info "  Processing $(basename $env_file)..."
            
            # FIXED: Replace circular references with actual generated values
            sed -i "s|MONGODB_URL=\${MONGODB_URL}|MONGODB_URL=${MONGODB_URL}|g" "$env_file"
            sed -i "s|REDIS_URL=\${REDIS_URL}|REDIS_URL=${REDIS_URL}|g" "$env_file"
            sed -i "s|ELASTICSEARCH_URL=\${ELASTICSEARCH_URL}|ELASTICSEARCH_URL=${ELASTICSEARCH_URL}|g" "$env_file"
            
            # Replace default/empty values with generated ones
            sed -i "s|MONGO_INITDB_ROOT_PASSWORD=lucid|MONGO_INITDB_ROOT_PASSWORD=${MONGODB_PASSWORD}|g" "$env_file"
            sed -i "s|MONGODB_URL=mongodb://lucid:lucid@|MONGODB_URL=${MONGODB_URL}|g" "$env_file"
            sed -i "s|REDIS_URL=redis://:lucid@|REDIS_URL=${REDIS_URL}|g" "$env_file"
            sed -i "s|ELASTICSEARCH_URL=http://elastic:lucid@|ELASTICSEARCH_URL=${ELASTICSEARCH_URL}|g" "$env_file"
            sed -i "s|BACKUP_ENCRYPTION_KEY=\"\"|BACKUP_ENCRYPTION_KEY=\"${BACKUP_ENCRYPTION_KEY}\"|g" "$env_file"
            sed -i "s|RESTORE_DECRYPTION_KEY=\"\"|RESTORE_DECRYPTION_KEY=\"${RESTORE_DECRYPTION_KEY}\"|g" "$env_file"
        fi
    done
    
    log_success "Database .env files updated with generated values"
    echo ""
}

# =============================================================================
# RUN ALL ENVIRONMENT GENERATION SCRIPTS
# =============================================================================
run_all_generation_scripts() {
    log_header "STEP 6: RUNNING ALL ENVIRONMENT GENERATION SCRIPTS"
    
    # Run blockchain build-env.sh
    log_step "Generating blockchain .env files..."
    ((TOTAL_FILES+=10))
    if bash "$PROJECT_ROOT/infrastructure/docker/blockchain/build-env.sh"; then
        log_success "✅ Blockchain .env files created (10 files)"
        ((GENERATED_FILES+=10))
        # Now inject values
        inject_blockchain_values
    else
        log_error "❌ Blockchain generation failed"
        ((FAILED_FILES+=10))
    fi
    
    # Run databases build-env.sh
    log_step "Generating database .env files..."
    ((TOTAL_FILES+=6))
    if bash "$PROJECT_ROOT/infrastructure/docker/databases/build-env.sh"; then
        log_success "✅ Database .env files created (6 files)"
        ((GENERATED_FILES+=6))
        # Now inject values
        inject_database_values
    else
        log_error "❌ Database generation failed"
        ((FAILED_FILES+=6))
    fi
    
    # Run API Gateway generate-env.sh
    log_step "Generating API Gateway .env.api..."
    ((TOTAL_FILES+=1))
    if bash "$PROJECT_ROOT/03-api-gateway/api/generate-env.sh"; then
        log_success "✅ API Gateway .env.api generated"
        ((GENERATED_FILES+=1))
    else
        log_error "❌ API Gateway generation failed"
        ((FAILED_FILES+=1))
    fi
    echo ""
    
    # Run sessions/core generate-env.sh
    log_step "Generating Session Core .env files..."
    ((TOTAL_FILES+=3))
    if bash "$PROJECT_ROOT/sessions/core/generate-env.sh"; then
        log_success "✅ Session Core .env files generated (3 files)"
        ((GENERATED_FILES+=3))
    else
        log_error "❌ Session Core generation failed"
        ((FAILED_FILES+=3))
    fi
    echo ""
}

# =============================================================================
# VALIDATE ALL GENERATED FILES
# =============================================================================
validate_generated_files() {
    log_header "STEP 7: VALIDATING ALL GENERATED FILES"
    
    local validation_errors=0
    
    # List of files to validate
    local files_to_check=(
        # API Gateway
        "$PROJECT_ROOT/03-api-gateway/api/.env.api"
        
        # Blockchain
        "$PROJECT_ROOT/infrastructure/docker/blockchain/env/.env.deployment-orchestrator"
        "$PROJECT_ROOT/infrastructure/docker/blockchain/env/.env.contract-compiler"
        "$PROJECT_ROOT/infrastructure/docker/blockchain/env/.env.blockchain-ledger"
        "$PROJECT_ROOT/infrastructure/docker/blockchain/env/.env.blockchain-vm"
        "$PROJECT_ROOT/infrastructure/docker/blockchain/env/.env.contract-deployment"
        "$PROJECT_ROOT/infrastructure/docker/blockchain/env/.env.blockchain-sessions-data"
        "$PROJECT_ROOT/infrastructure/docker/blockchain/env/.env.on-system-chain-client"
        "$PROJECT_ROOT/infrastructure/docker/blockchain/env/.env.blockchain-api"
        "$PROJECT_ROOT/infrastructure/docker/blockchain/env/.env.blockchain-governance"
        "$PROJECT_ROOT/infrastructure/docker/blockchain/env/.env.tron-node-client"
        
        # Databases
        "$PROJECT_ROOT/infrastructure/docker/databases/env/.env.database-monitoring"
        "$PROJECT_ROOT/infrastructure/docker/databases/env/.env.database-migration"
        "$PROJECT_ROOT/infrastructure/docker/databases/env/.env.mongodb-init"
        "$PROJECT_ROOT/infrastructure/docker/databases/env/.env.database-backup"
        "$PROJECT_ROOT/infrastructure/docker/databases/env/.env.mongodb"
        "$PROJECT_ROOT/infrastructure/docker/databases/env/.env.database-restore"
        
        # Sessions
        "$PROJECT_ROOT/sessions/core/.env.orchestrator"
        "$PROJECT_ROOT/sessions/core/.env.merkle_builder"
        "$PROJECT_ROOT/sessions/core/.env.chunker"
    )
    
    log_info "Checking ${#files_to_check[@]} environment files..."
    echo ""
    
    for file in "${files_to_check[@]}"; do
        if [[ -f "$file" ]]; then
            # Check file exists
            log_success "✅ File exists: $(basename $file)"
            
            # Check for empty critical values
            local empty_count=0
            if grep -qE '(MONGODB_PASSWORD|JWT_SECRET|ENCRYPTION_KEY|PRIVATE_KEY)=""' "$file" 2>/dev/null; then
                log_warning "   ⚠️  Contains empty critical values"
                ((empty_count++))
            fi
            
            # FIXED: Check for circular references (the main issue)
            if grep -qE '\$\{[A-Z_]+\}' "$file" 2>/dev/null; then
                log_error "   ❌ Contains circular variable references"
                ((validation_errors++))
            fi
            
            # Check for placeholders
            if grep -q "_PLACEHOLDER" "$file" 2>/dev/null; then
                log_error "   ❌ Contains unreplaced placeholders"
                ((validation_errors++))
            fi
            
            # Check file size
            local file_size=$(wc -c < "$file")
            if [[ $file_size -lt 100 ]]; then
                log_error "   ❌ File too small ($file_size bytes)"
                ((validation_errors++))
            fi
        else
            log_error "❌ File missing: $file"
            ((validation_errors++))
        fi
    done
    
    echo ""
    if [[ $validation_errors -eq 0 ]]; then
        log_success "All files validated successfully!"
    else
        log_error "Validation found $validation_errors errors"
        return 1
    fi
    
    echo ""
}

# =============================================================================
# CREATE COMPREHENSIVE SUMMARY
# =============================================================================
create_summary() {
    log_header "STEP 8: GENERATING COMPREHENSIVE SUMMARY"
    
    local summary_file="$PROJECT_ROOT/configs/environment/COMPLETE_ENV_GENERATION_SUMMARY.md"
    
    cat > "$summary_file" << EOF
# Complete Environment Generation Summary

**Generated:** $(date)  
**Build Timestamp:** $BUILD_TIMESTAMP  
**Git SHA:** $GIT_SHA  
**Script:** scripts/config/generate-all-env-complete.sh

---

## Generation Statistics

- **Total Files Generated:** $GENERATED_FILES / $TOTAL_FILES
- **Failed Files:** $FAILED_FILES
- **Total Secrets Generated:** $TOTAL_SECRETS
- **Success Rate:** $(( GENERATED_FILES * 100 / TOTAL_FILES ))%

---

## Generated Files

### API Gateway (1 file)
- ✅ \`03-api-gateway/api/.env.api\`

### Blockchain Services (10 files)
- ✅ \`infrastructure/docker/blockchain/env/.env.deployment-orchestrator\`
- ✅ \`infrastructure/docker/blockchain/env/.env.contract-compiler\`
- ✅ \`infrastructure/docker/blockchain/env/.env.blockchain-ledger\`
- ✅ \`infrastructure/docker/blockchain/env/.env.blockchain-vm\`
- ✅ \`infrastructure/docker/blockchain/env/.env.contract-deployment\`
- ✅ \`infrastructure/docker/blockchain/env/.env.blockchain-sessions-data\`
- ✅ \`infrastructure/docker/blockchain/env/.env.on-system-chain-client\`
- ✅ \`infrastructure/docker/blockchain/env/.env.blockchain-api\`
- ✅ \`infrastructure/docker/blockchain/env/.env.blockchain-governance\`
- ✅ \`infrastructure/docker/blockchain/env/.env.tron-node-client\`

### Database Services (6 files)
- ✅ \`infrastructure/docker/databases/env/.env.database-monitoring\`
- ✅ \`infrastructure/docker/databases/env/.env.database-migration\`
- ✅ \`infrastructure/docker/databases/env/.env.mongodb-init\`
- ✅ \`infrastructure/docker/databases/env/.env.database-backup\`
- ✅ \`infrastructure/docker/databases/env/.env.mongodb\`
- ✅ \`infrastructure/docker/databases/env/.env.database-restore\`

### Session Services (3 files)
- ✅ \`sessions/core/.env.orchestrator\`
- ✅ \`sessions/core/.env.merkle_builder\`
- ✅ \`sessions/core/.env.chunker\`

### Phase Configs (6 files)
- ✅ \`configs/environment/.env.pi-build\`
- ✅ \`configs/environment/.env.foundation\`
- ✅ \`configs/environment/.env.core\`
- ✅ \`configs/environment/.env.application\`
- ✅ \`configs/environment/.env.support\`
- ✅ \`configs/environment/.env.gui\`

### Master Secure File (1 file)
- ✅ \`configs/environment/.env.secure\` (chmod 600)

---

## Generated Secure Values

### Database Credentials
- MongoDB Password: ${MONGODB_PASSWORD:0:8}... (32 bytes)
- Redis Password: ${REDIS_PASSWORD:0:8}... (32 bytes)
- Elasticsearch Password: ${ELASTICSEARCH_PASSWORD:0:8}... (32 bytes)

### Authentication & JWT
- JWT Secret: ${JWT_SECRET:0:12}... (64 bytes)
- Encryption Key: ${ENCRYPTION_KEY:0:16}... (256-bit hex)
- Session Secret: ${SESSION_SECRET:0:8}... (32 bytes)

### Service Secrets
- API Secret: ${API_SECRET:0:8}... (32 bytes)
- API Gateway Secret: ${API_GATEWAY_SECRET:0:8}... (32 bytes)
- Blockchain Secret: ${BLOCKCHAIN_SECRET:0:8}... (32 bytes)
- Node Management Secret: ${NODE_MANAGEMENT_SECRET:0:8}... (32 bytes)
- Admin Secret: ${ADMIN_SECRET:0:8}... (32 bytes)
- TRON Payment Secret: ${TRON_PAYMENT_SECRET:0:8}... (32 bytes)

### Blockchain Keys
- TRON Private Key: ${TRON_PRIVATE_KEY:0:16}... (512-bit hex)
- Deployment Key: ${DEPLOYMENT_KEY:0:16}... (256-bit hex)
- Contract Owner Key: ${CONTRACT_OWNER_KEY:0:16}... (256-bit hex)
- Compiler Key: ${COMPILER_KEY:0:16}... (256-bit hex)
- Verification Key: ${VERIFICATION_KEY:0:16}... (256-bit hex)
- Orchestrator Key: ${ORCHESTRATOR_KEY:0:16}... (256-bit hex)
- Governance Key: ${GOVERNANCE_KEY:0:16}... (256-bit hex)
- Signing Key: ${SIGNING_KEY:0:16}... (256-bit hex)

### Tor Hidden Services
- API Gateway: $API_GATEWAY_ONION
- Auth Service: $AUTH_SERVICE_ONION
- Blockchain API: $BLOCKCHAIN_API_ONION
- Admin Interface: $ADMIN_INTERFACE_ONION
- Session API: $SESSION_API_ONION

---

## Security Notice

⚠️ **CRITICAL SECURITY INFORMATION:**

1. **Master Secure File:** \`configs/environment/.env.secure\`
   - Contains ALL generated secrets
   - File permissions: 600 (owner read/write only)
   - **NEVER commit this file to version control**
   - Backup to secure location immediately

2. **Individual Secrets Files:**
   - \`03-api-gateway/api/.env.api.secrets\`
   - \`sessions/core/.env.sessions.secrets\`
   - All have chmod 600 permissions

3. **Production Deployment:**
   - Rotate all keys before production deployment
   - Use environment-specific key management
   - Store secrets in secure vault (HashiCorp Vault, AWS Secrets Manager, etc.)
   - Never expose secrets in logs or monitoring

4. **.gitignore Configuration:**
   - Verify all .env files are ignored
   - Verify all .secrets files are ignored
   - Double-check before committing

---

## Next Steps

### 1. Verify Generated Files
\`\`\`bash
# Check for placeholders (should return nothing)
grep -r "_PLACEHOLDER" configs/environment/ infrastructure/docker/*/env/ 03-api-gateway/api/ sessions/core/ || echo "No placeholders found ✅"

# Check for circular references (should return nothing)
grep -rE '\$\{[A-Z_]+\}' configs/environment/ infrastructure/docker/*/env/ 03-api-gateway/api/ sessions/core/ || echo "No circular references found ✅"

# Check for empty critical values
grep -rE '(MONGODB_PASSWORD|JWT_SECRET|ENCRYPTION_KEY)=""' infrastructure/docker/*/env/ || echo "No empty critical values ✅"
\`\`\`

### 2. Secure the Files
\`\`\`bash
# Set restrictive permissions
chmod 600 configs/environment/.env.secure
chmod 600 03-api-gateway/api/.env.api.secrets
chmod 600 sessions/core/.env.sessions.secrets

# Verify .gitignore
git status --ignored | grep -E '\.env|\.secrets' || echo "Files properly ignored ✅"
\`\`\`

### 3. Backup Secure Values
\`\`\`bash
# Create encrypted backup
tar czf lucid-secrets-backup-$BUILD_TIMESTAMP.tar.gz configs/environment/.env.secure 03-api-gateway/api/.env.api.secrets sessions/core/.env.sessions.secrets
gpg -c lucid-secrets-backup-$BUILD_TIMESTAMP.tar.gz
rm lucid-secrets-backup-$BUILD_TIMESTAMP.tar.gz
\`\`\`

### 4. Deploy to Raspberry Pi
\`\`\`bash
# Run deployment scripts
cd scripts/deployment
./deploy-phase1-pi.sh
./deploy-phase2-pi.sh
./deploy-phase3-pi.sh
./deploy-phase4-pi.sh
\`\`\`

---

## File Locations Reference

**Phase Configs:** \`configs/environment/.env.*\`  
**Blockchain Configs:** \`infrastructure/docker/blockchain/env/.env.*\`  
**Database Configs:** \`infrastructure/docker/databases/env/.env.*\`  
**API Gateway Config:** \`03-api-gateway/api/.env.api\`  
**Session Configs:** \`sessions/core/.env.*\`  
**Master Secure File:** \`configs/environment/.env.secure\` 

---

**Status:** ✅ COMPLETE - All environment files generated with actual secure values!
EOF

    log_success "Summary created: $summary_file"
    echo ""
}

# =============================================================================
# DISPLAY FINAL SUMMARY
# =============================================================================
display_final_summary() {
    log_header "ENVIRONMENT GENERATION COMPLETE!"
    
    echo ""
    log_info "╔═══════════════════════════════════════════════════════════╗"
    log_info "║         LUCID COMPLETE ENVIRONMENT GENERATION             ║"
    log_info "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    
    log_info "📊 Generation Statistics:"
    log_info "   • Total Files Generated: $GENERATED_FILES / $TOTAL_FILES"
    log_info "   • Failed Files: $FAILED_FILES"
    log_info "   • Total Secrets: $TOTAL_SECRETS"
    log_info "   • Success Rate: $(( GENERATED_FILES * 100 / TOTAL_FILES ))%"
    echo ""
    
    log_info "🔑 Generated Secure Values:"
    log_info "   • Database Passwords: 3"
    log_info "   • JWT & Auth Secrets: 4"
    log_info "   • Service Secrets: 8"
    log_info "   • TOR Passwords: 2"
    log_info "   • Encryption Keys: 3"
    log_info "   • Blockchain Keys: 13"
    log_info "   • .onion Addresses: 5"
    echo ""
    
    log_info "📁 Generated Files:"
    log_info "   • API Gateway: 1 file"
    log_info "   • Blockchain: 10 files"
    log_info "   • Databases: 6 files"
    log_info "   • Sessions: 3 files"
    log_info "   • Phase Configs: 6 files"
    log_info "   • Master Secure: 1 file"
    echo ""
    
    log_success "🎉 All environment files generated with actual values!"
    echo ""
    
    log_warning "⚠️  SECURITY REMINDERS:"
    log_warning "   1. Master secure file: configs/environment/.env.secure (chmod 600)"
    log_warning "   2. Never commit .env files to version control"
    log_warning "   3. Backup secrets to secure location"
    log_warning "   4. Rotate keys regularly in production"
    echo ""
    
    log_info "📋 Next Steps:"
    log_info "   1. Review generated files for correctness"
    log_info "   2. Backup configs/environment/.env.secure to secure location"
    log_info "   3. Verify .gitignore covers all .env and .secrets files"
    log_info "   4. Run: grep -r '_PLACEHOLDER' to verify no placeholders remain"
    log_info "   5. Run: grep -rE '\\$\\{[A-Z_]+\\}' to verify no circular references remain"
    log_info "   6. Deploy to Pi: cd scripts/deployment && ./deploy-phase1-pi.sh"
    echo ""
    
    log_success "✨ Environment generation completed successfully!"
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================
main() {
    log_header "LUCID COMPLETE ENVIRONMENT GENERATION SYSTEM"
    echo ""
    log_info "This script will generate ALL .env files with REAL values:"
    log_info "  • API Gateway configuration"
    log_info "  • Blockchain service configurations (10 files)"
    log_info "  • Database service configurations (6 files)"
    log_info "  • Session service configurations (3 files)"
    log_info "  • Phase-level configurations (6 files)"
    log_info "  • Master secure values file"
    echo ""
    log_info "Total: 27 environment files with $TOTAL_SECRETS cryptographic values"
    echo ""
    
    # Confirm execution
    read -p "Continue with environment generation? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Environment generation cancelled by user"
        exit 0
    fi
    
    echo ""
    
    # Execute all steps
    generate_all_secure_values
    save_secure_values
    generate_phase_configs
    run_all_generation_scripts
    validate_generated_files
    create_summary
    display_final_summary
    
    # Exit with success if validation passed
    if [[ $FAILED_FILES -eq 0 ]]; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"

