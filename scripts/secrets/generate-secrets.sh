#!/bin/bash
# Secret Generation Script
# LUCID-STRICT Secret Management System
# Purpose: Generate secure secrets for all Lucid clusters
# Compatibility: Distroless, API compliant
# Generated: 2025-01-27

set -e

# Configuration - Aligned with config directory structure
SECRETS_DIR="${LUCID_SECRETS_DIR:-configs/environment}"
BACKUP_DIR="${LUCID_BACKUP_DIR:-/data/backups/secrets}"
LOG_FILE="${LOG_FILE:-/var/log/lucid/secret-generation.log}"
SECRET_TYPES=("jwt" "database" "tron" "hardware" "mesh" "admin" "blockchain" "session" "rdp" "node" "monitoring" "external" "backup")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${1}" | tee -a "$LOG_FILE"
}

log_info() {
    log "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    log "${GREEN}✅ $1${NC}"
}

log_warning() {
    log "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    log "${RED}❌ $1${NC}"
}

# Create directories if they don't exist
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$SECRETS_DIR"
mkdir -p "$BACKUP_DIR"
mkdir -p "$SECRETS_DIR/rotation-log"

echo "========================================"
log_info "🔐 LUCID Secret Generation"
echo "========================================"

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Generate secure secrets for Lucid clusters"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -t, --type TYPE         Generate specific secret type"
    echo "  -a, --all               Generate all secret types"
    echo "  -f, --force             Force generation without confirmation"
    echo "  -d, --dry-run           Show what would be generated without executing"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -b, --backup            Create backup before generation"
    echo "  -c, --check             Check existing secrets"
    echo "  --validate             Validate secret format"
    echo "  --vault                Load secrets from secure vault"
    echo ""
    echo "Secret Types:"
    echo "  jwt                     JWT signing secrets"
    echo "  database                Database authentication secrets"
    echo "  tron                    TRON payment secrets (isolated)"
    echo "  hardware                Hardware wallet secrets"
    echo "  mesh                    Service mesh secrets"
    echo "  admin                   Admin interface secrets"
    echo "  blockchain              Blockchain consensus secrets"
    echo "  session                 Session management secrets"
    echo "  rdp                     RDP service secrets"
    echo "  node                    Node management secrets"
    echo "  monitoring              Monitoring and alerting secrets"
    echo "  external                External service secrets"
    echo "  backup                  Backup encryption secrets"
    echo ""
    echo "Environment Variables:"
    echo "  LUCID_SECRETS_DIR       Secrets directory (default: configs/environment)"
    echo "  LUCID_BACKUP_DIR        Backup directory (default: /data/backups/secrets)"
    echo ""
    echo "Examples:"
    echo "  $0 --type jwt           Generate JWT secrets only"
    echo "  $0 --all --backup       Generate all secrets with backup"
    echo "  $0 --check              Check existing secrets"
    echo "  $0 --validate           Validate secret formats"
}

# Parse command line arguments
SECRET_TYPE=""
GENERATE_ALL=false
FORCE=false
DRY_RUN=false
VERBOSE=false
CREATE_BACKUP=false
CHECK_SECRETS=false
VALIDATE_SECRETS=false
USE_VAULT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -t|--type)
            SECRET_TYPE="$2"
            shift 2
            ;;
        -a|--all)
            GENERATE_ALL=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -b|--backup)
            CREATE_BACKUP=true
            shift
            ;;
        -c|--check)
            CHECK_SECRETS=true
            shift
            ;;
        --validate)
            VALIDATE_SECRETS=true
            shift
            ;;
        --vault)
            USE_VAULT=true
            shift
            ;;
        -*)
            log_error "Unknown option $1"
            show_usage
            exit 1
            ;;
        *)
            log_error "Unexpected argument: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate secret type
if [[ -n "$SECRET_TYPE" ]]; then
    if [[ ! " ${SECRET_TYPES[@]} " =~ " ${SECRET_TYPE} " ]]; then
        log_error "Invalid secret type: $SECRET_TYPE"
        log_info "Valid types: ${SECRET_TYPES[*]}"
        exit 1
    fi
fi

# Function to generate JWT secrets
generate_jwt_secrets() {
    local secrets_file="$SECRETS_DIR/.env.secure"
    local timestamp=$(date +%Y%m%d-%H%M%S)
    
    log_info "Generating JWT secrets..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would generate JWT secrets"
        return 0
    fi
    
    # Generate JWT secret key (256-bit)
    local jwt_secret=$(openssl rand -base64 64)
    local jwt_refresh_secret=$(openssl rand -base64 64)
    
    # Update secrets file
    if [[ -f "$secrets_file" ]]; then
        # Update existing file
        sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$jwt_secret/" "$secrets_file"
        sed -i "s/JWT_REFRESH_SECRET_KEY=.*/JWT_REFRESH_SECRET_KEY=$jwt_refresh_secret/" "$secrets_file"
    else
        # Create new file
        echo "JWT_SECRET_KEY=$jwt_secret" >> "$secrets_file"
        echo "JWT_REFRESH_SECRET_KEY=$jwt_refresh_secret" >> "$secrets_file"
    fi
    
    # Set secure permissions
    chmod 600 "$secrets_file"
    
    log_success "Generated JWT secrets"
    return 0
}

# Function to generate database secrets
generate_database_secrets() {
    local secrets_file="$SECRETS_DIR/.env.secure"
    
    log_info "Generating database secrets..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would generate database secrets"
        return 0
    fi
    
    # Generate MongoDB passwords
    local mongodb_password=$(openssl rand -base64 48)
    local mongodb_root_password=$(openssl rand -base64 48)
    local redis_password=$(openssl rand -base64 48)
    local elasticsearch_password=$(openssl rand -base64 48)
    
    # Update secrets file
    if [[ -f "$secrets_file" ]]; then
        sed -i "s/MONGODB_PASSWORD=.*/MONGODB_PASSWORD=$mongodb_password/" "$secrets_file"
        sed -i "s/MONGODB_ROOT_PASSWORD=.*/MONGODB_ROOT_PASSWORD=$mongodb_root_password/" "$secrets_file"
        sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=$redis_password/" "$secrets_file"
        sed -i "s/ELASTICSEARCH_PASSWORD=.*/ELASTICSEARCH_PASSWORD=$elasticsearch_password/" "$secrets_file"
    else
        echo "MONGODB_PASSWORD=$mongodb_password" >> "$secrets_file"
        echo "MONGODB_ROOT_PASSWORD=$mongodb_root_password" >> "$secrets_file"
        echo "REDIS_PASSWORD=$redis_password" >> "$secrets_file"
        echo "ELASTICSEARCH_PASSWORD=$elasticsearch_password" >> "$secrets_file"
    fi
    
    chmod 600 "$secrets_file"
    
    log_success "Generated database secrets"
    return 0
}

# Function to generate TRON payment secrets
generate_tron_secrets() {
    local secrets_file="$SECRETS_DIR/.env.secure"
    
    log_info "Generating TRON payment secrets..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would generate TRON payment secrets"
        return 0
    fi
    
    # Generate TRON private key (64 hex characters)
    local tron_private_key=$(openssl rand -hex 32)
    local tron_passphrase=$(openssl rand -base64 32)
    local tron_api_key=$(openssl rand -hex 32)
    
    # Update secrets file
    if [[ -f "$secrets_file" ]]; then
        sed -i "s/TRON_PRIVATE_KEY_ENCRYPTED=.*/TRON_PRIVATE_KEY_ENCRYPTED=$tron_private_key/" "$secrets_file"
        sed -i "s/TRON_PRIVATE_KEY_PASSPHRASE=.*/TRON_PRIVATE_KEY_PASSPHRASE=$tron_passphrase/" "$secrets_file"
        sed -i "s/TRON_API_KEY=.*/TRON_API_KEY=$tron_api_key/" "$secrets_file"
    else
        echo "TRON_PRIVATE_KEY_ENCRYPTED=$tron_private_key" >> "$secrets_file"
        echo "TRON_PRIVATE_KEY_PASSPHRASE=$tron_passphrase" >> "$secrets_file"
        echo "TRON_API_KEY=$tron_api_key" >> "$secrets_file"
    fi
    
    chmod 600 "$secrets_file"
    
    log_success "Generated TRON payment secrets"
    return 0
}

# Function to generate hardware wallet secrets
generate_hardware_secrets() {
    local secrets_file="$SECRETS_DIR/.env.secure"
    
    log_info "Generating hardware wallet secrets..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would generate hardware wallet secrets"
        return 0
    fi
    
    # Generate hardware wallet app IDs
    local ledger_app_id=$(openssl rand -hex 16)
    local trezor_app_id=$(openssl rand -hex 16)
    local keepkey_app_id=$(openssl rand -hex 16)
    
    # Update secrets file
    if [[ -f "$secrets_file" ]]; then
        sed -i "s/LEDGER_APP_ID=.*/LEDGER_APP_ID=$ledger_app_id/" "$secrets_file"
        sed -i "s/TREZOR_APP_ID=.*/TREZOR_APP_ID=$trezor_app_id/" "$secrets_file"
        sed -i "s/KEEPKEY_APP_ID=.*/KEEPKEY_APP_ID=$keepkey_app_id/" "$secrets_file"
    else
        echo "LEDGER_APP_ID=$ledger_app_id" >> "$secrets_file"
        echo "TREZOR_APP_ID=$trezor_app_id" >> "$secrets_file"
        echo "KEEPKEY_APP_ID=$keepkey_app_id" >> "$secrets_file"
    fi
    
    chmod 600 "$secrets_file"
    
    log_success "Generated hardware wallet secrets"
    return 0
}

# Function to generate service mesh secrets
generate_mesh_secrets() {
    local secrets_file="$SECRETS_DIR/.env.secure"
    
    log_info "Generating service mesh secrets..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would generate service mesh secrets"
        return 0
    fi
    
    # Generate service mesh certificates and secrets
    local mesh_ca_cert=$(openssl rand -base64 64)
    local mesh_ca_key=$(openssl rand -base64 64)
    local mesh_jwt_secret=$(openssl rand -base64 64)
    
    # Update secrets file
    if [[ -f "$secrets_file" ]]; then
        sed -i "s/SERVICE_MESH_CA_CERT=.*/SERVICE_MESH_CA_CERT=$mesh_ca_cert/" "$secrets_file"
        sed -i "s/SERVICE_MESH_CA_KEY=.*/SERVICE_MESH_CA_KEY=$mesh_ca_key/" "$secrets_file"
        sed -i "s/SERVICE_MESH_JWT_SECRET=.*/SERVICE_MESH_JWT_SECRET=$mesh_jwt_secret/" "$secrets_file"
    else
        echo "SERVICE_MESH_CA_CERT=$mesh_ca_cert" >> "$secrets_file"
        echo "SERVICE_MESH_CA_KEY=$mesh_ca_key" >> "$secrets_file"
        echo "SERVICE_MESH_JWT_SECRET=$mesh_jwt_secret" >> "$secrets_file"
    fi
    
    chmod 600 "$secrets_file"
    
    log_success "Generated service mesh secrets"
    return 0
}

# Function to generate admin secrets
generate_admin_secrets() {
    local secrets_file="$SECRETS_DIR/.env.secure"
    
    log_info "Generating admin interface secrets..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would generate admin interface secrets"
        return 0
    fi
    
    # Generate admin secrets
    local admin_jwt_secret=$(openssl rand -base64 64)
    local admin_api_key=$(openssl rand -hex 32)
    local admin_session_secret=$(openssl rand -base64 64)
    
    # Update secrets file
    if [[ -f "$secrets_file" ]]; then
        sed -i "s/ADMIN_JWT_SECRET=.*/ADMIN_JWT_SECRET=$admin_jwt_secret/" "$secrets_file"
        sed -i "s/ADMIN_API_KEY=.*/ADMIN_API_KEY=$admin_api_key/" "$secrets_file"
        sed -i "s/ADMIN_SESSION_SECRET=.*/ADMIN_SESSION_SECRET=$admin_session_secret/" "$secrets_file"
    else
        echo "ADMIN_JWT_SECRET=$admin_jwt_secret" >> "$secrets_file"
        echo "ADMIN_API_KEY=$admin_api_key" >> "$secrets_file"
        echo "ADMIN_SESSION_SECRET=$admin_session_secret" >> "$secrets_file"
    fi
    
    chmod 600 "$secrets_file"
    
    log_success "Generated admin interface secrets"
    return 0
}

# Function to generate blockchain secrets
generate_blockchain_secrets() {
    local secrets_file="$SECRETS_DIR/.env.secure"
    
    log_info "Generating blockchain secrets..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would generate blockchain secrets"
        return 0
    fi
    
    # Generate blockchain consensus secrets
    local consensus_secret=$(openssl rand -base64 64)
    local validator_key=$(openssl rand -hex 32)
    local node_id=$(openssl rand -hex 16)
    
    # Update secrets file
    if [[ -f "$secrets_file" ]]; then
        sed -i "s/BLOCKCHAIN_CONSENSUS_SECRET=.*/BLOCKCHAIN_CONSENSUS_SECRET=$consensus_secret/" "$secrets_file"
        sed -i "s/BLOCKCHAIN_VALIDATOR_KEY=.*/BLOCKCHAIN_VALIDATOR_KEY=$validator_key/" "$secrets_file"
        sed -i "s/BLOCKCHAIN_NODE_ID=.*/BLOCKCHAIN_NODE_ID=$node_id/" "$secrets_file"
    else
        echo "BLOCKCHAIN_CONSENSUS_SECRET=$consensus_secret" >> "$secrets_file"
        echo "BLOCKCHAIN_VALIDATOR_KEY=$validator_key" >> "$secrets_file"
        echo "BLOCKCHAIN_NODE_ID=$node_id" >> "$secrets_file"
    fi
    
    chmod 600 "$secrets_file"
    
    log_success "Generated blockchain secrets"
    return 0
}

# Function to generate session management secrets
generate_session_secrets() {
    local secrets_file="$SECRETS_DIR/.env.secure"
    
    log_info "Generating session management secrets..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would generate session management secrets"
        return 0
    fi
    
    # Generate session encryption secrets
    local session_encryption_key=$(openssl rand -base64 64)
    local session_signing_key=$(openssl rand -base64 64)
    local chunk_encryption_key=$(openssl rand -base64 64)
    
    # Update secrets file
    if [[ -f "$secrets_file" ]]; then
        sed -i "s/SESSION_ENCRYPTION_KEY=.*/SESSION_ENCRYPTION_KEY=$session_encryption_key/" "$secrets_file"
        sed -i "s/SESSION_SIGNING_KEY=.*/SESSION_SIGNING_KEY=$session_signing_key/" "$secrets_file"
        sed -i "s/CHUNK_ENCRYPTION_KEY=.*/CHUNK_ENCRYPTION_KEY=$chunk_encryption_key/" "$secrets_file"
    else
        echo "SESSION_ENCRYPTION_KEY=$session_encryption_key" >> "$secrets_file"
        echo "SESSION_SIGNING_KEY=$session_signing_key" >> "$secrets_file"
        echo "CHUNK_ENCRYPTION_KEY=$chunk_encryption_key" >> "$secrets_file"
    fi
    
    chmod 600 "$secrets_file"
    
    log_success "Generated session management secrets"
    return 0
}

# Function to generate RDP service secrets
generate_rdp_secrets() {
    local secrets_file="$SECRETS_DIR/.env.secure"
    
    log_info "Generating RDP service secrets..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would generate RDP service secrets"
        return 0
    fi
    
    # Generate RDP secrets
    local rdp_admin_password=$(openssl rand -base64 32)
    local xrdp_password=$(openssl rand -base64 32)
    local rdp_session_key=$(openssl rand -hex 32)
    
    # Update secrets file
    if [[ -f "$secrets_file" ]]; then
        sed -i "s/RDP_ADMIN_PASSWORD=.*/RDP_ADMIN_PASSWORD=$rdp_admin_password/" "$secrets_file"
        sed -i "s/XRDP_PASSWORD=.*/XRDP_PASSWORD=$xrdp_password/" "$secrets_file"
        sed -i "s/RDP_SESSION_KEY=.*/RDP_SESSION_KEY=$rdp_session_key/" "$secrets_file"
    else
        echo "RDP_ADMIN_PASSWORD=$rdp_admin_password" >> "$secrets_file"
        echo "XRDP_PASSWORD=$xrdp_password" >> "$secrets_file"
        echo "RDP_SESSION_KEY=$rdp_session_key" >> "$secrets_file"
    fi
    
    chmod 600 "$secrets_file"
    
    log_success "Generated RDP service secrets"
    return 0
}

# Function to generate node management secrets
generate_node_secrets() {
    local secrets_file="$SECRETS_DIR/.env.secure"
    
    log_info "Generating node management secrets..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would generate node management secrets"
        return 0
    fi
    
    # Generate node management secrets
    local node_operator_key=$(openssl rand -hex 32)
    local poot_validation_secret=$(openssl rand -base64 64)
    local node_registration_token=$(openssl rand -hex 32)
    
    # Update secrets file
    if [[ -f "$secrets_file" ]]; then
        sed -i "s/NODE_OPERATOR_KEY=.*/NODE_OPERATOR_KEY=$node_operator_key/" "$secrets_file"
        sed -i "s/POOT_VALIDATION_SECRET=.*/POOT_VALIDATION_SECRET=$poot_validation_secret/" "$secrets_file"
        sed -i "s/NODE_REGISTRATION_TOKEN=.*/NODE_REGISTRATION_TOKEN=$node_registration_token/" "$secrets_file"
    else
        echo "NODE_OPERATOR_KEY=$node_operator_key" >> "$secrets_file"
        echo "POOT_VALIDATION_SECRET=$poot_validation_secret" >> "$secrets_file"
        echo "NODE_REGISTRATION_TOKEN=$node_registration_token" >> "$secrets_file"
    fi
    
    chmod 600 "$secrets_file"
    
    log_success "Generated node management secrets"
    return 0
}

# Function to generate monitoring secrets
generate_monitoring_secrets() {
    local secrets_file="$SECRETS_DIR/.env.secure"
    
    log_info "Generating monitoring secrets..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would generate monitoring secrets"
        return 0
    fi
    
    # Generate monitoring secrets
    local prometheus_secret=$(openssl rand -base64 64)
    local grafana_admin_password=$(openssl rand -base64 32)
    local alertmanager_webhook_secret=$(openssl rand -hex 32)
    
    # Update secrets file
    if [[ -f "$secrets_file" ]]; then
        sed -i "s/PROMETHEUS_SECRET=.*/PROMETHEUS_SECRET=$prometheus_secret/" "$secrets_file"
        sed -i "s/GRAFANA_ADMIN_PASSWORD=.*/GRAFANA_ADMIN_PASSWORD=$grafana_admin_password/" "$secrets_file"
        sed -i "s/ALERTMANAGER_WEBHOOK_SECRET=.*/ALERTMANAGER_WEBHOOK_SECRET=$alertmanager_webhook_secret/" "$secrets_file"
    else
        echo "PROMETHEUS_SECRET=$prometheus_secret" >> "$secrets_file"
        echo "GRAFANA_ADMIN_PASSWORD=$grafana_admin_password" >> "$secrets_file"
        echo "ALERTMANAGER_WEBHOOK_SECRET=$alertmanager_webhook_secret" >> "$secrets_file"
    fi
    
    chmod 600 "$secrets_file"
    
    log_success "Generated monitoring secrets"
    return 0
}

# Function to generate external service secrets
generate_external_secrets() {
    local secrets_file="$SECRETS_DIR/.env.secure"
    
    log_info "Generating external service secrets..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would generate external service secrets"
        return 0
    fi
    
    # Generate external service secrets
    local tor_control_password=$(openssl rand -base64 32)
    local docker_registry_password=$(openssl rand -base64 32)
    local github_token=$(openssl rand -hex 32)
    
    # Update secrets file
    if [[ -f "$secrets_file" ]]; then
        sed -i "s/TOR_CONTROL_PASSWORD=.*/TOR_CONTROL_PASSWORD=$tor_control_password/" "$secrets_file"
        sed -i "s/DOCKER_REGISTRY_PASSWORD=.*/DOCKER_REGISTRY_PASSWORD=$docker_registry_password/" "$secrets_file"
        sed -i "s/GITHUB_TOKEN=.*/GITHUB_TOKEN=$github_token/" "$secrets_file"
    else
        echo "TOR_CONTROL_PASSWORD=$tor_control_password" >> "$secrets_file"
        echo "DOCKER_REGISTRY_PASSWORD=$docker_registry_password" >> "$secrets_file"
        echo "GITHUB_TOKEN=$github_token" >> "$secrets_file"
    fi
    
    chmod 600 "$secrets_file"
    
    log_success "Generated external service secrets"
    return 0
}

# Function to generate backup secrets
generate_backup_secrets() {
    local secrets_file="$SECRETS_DIR/.env.secure"
    
    log_info "Generating backup secrets..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would generate backup secrets"
        return 0
    fi
    
    # Generate backup encryption secrets
    local backup_encryption_key=$(openssl rand -base64 64)
    local backup_signing_key=$(openssl rand -base64 64)
    
    # Update secrets file
    if [[ -f "$secrets_file" ]]; then
        sed -i "s/BACKUP_ENCRYPTION_KEY=.*/BACKUP_ENCRYPTION_KEY=$backup_encryption_key/" "$secrets_file"
        sed -i "s/BACKUP_SIGNING_KEY=.*/BACKUP_SIGNING_KEY=$backup_signing_key/" "$secrets_file"
    else
        echo "BACKUP_ENCRYPTION_KEY=$backup_encryption_key" >> "$secrets_file"
        echo "BACKUP_SIGNING_KEY=$backup_signing_key" >> "$secrets_file"
    fi
    
    chmod 600 "$secrets_file"
    
    log_success "Generated backup secrets"
    return 0
}

# Function to check existing secrets
check_existing_secrets() {
    local secrets_file="$SECRETS_DIR/.env.secure"
    
    log_info "Checking existing secrets..."
    
    if [[ ! -f "$secrets_file" ]]; then
        log_warning "No secrets file found: $secrets_file"
        return 1
    fi
    
    local missing_secrets=()
    local present_secrets=()
    
    # Check for required secrets
    local required_secrets=(
        "JWT_SECRET_KEY"
        "MONGODB_PASSWORD"
        "REDIS_PASSWORD"
        "TRON_PRIVATE_KEY_ENCRYPTED"
        "ADMIN_JWT_SECRET"
        "BLOCKCHAIN_CONSENSUS_SECRET"
        "SESSION_ENCRYPTION_KEY"
        "RDP_ADMIN_PASSWORD"
        "NODE_OPERATOR_KEY"
        "PROMETHEUS_SECRET"
    )
    
    for secret in "${required_secrets[@]}"; do
        if grep -q "^${secret}=" "$secrets_file"; then
            local value=$(grep "^${secret}=" "$secrets_file" | cut -d'=' -f2)
            if [[ "$value" == *"your-"* ]] || [[ "$value" == *"change-in-production"* ]] || [[ -z "$value" ]]; then
                missing_secrets+=("$secret")
            else
                present_secrets+=("$secret")
            fi
        else
            missing_secrets+=("$secret")
        fi
    done
    
    if [[ ${#present_secrets[@]} -gt 0 ]]; then
        log_success "Present secrets (${#present_secrets[@]}):"
        for secret in "${present_secrets[@]}"; do
            echo "  ✅ $secret"
        done
    fi
    
    if [[ ${#missing_secrets[@]} -gt 0 ]]; then
        log_warning "Missing or default secrets (${#missing_secrets[@]}):"
        for secret in "${missing_secrets[@]}"; do
            echo "  ❌ $secret"
        done
        return 1
    fi
    
    log_success "All required secrets are present and configured"
    return 0
}

# Function to validate secret formats
validate_secret_formats() {
    local secrets_file="$SECRETS_DIR/.env.secure"
    
    log_info "Validating secret formats..."
    
    if [[ ! -f "$secrets_file" ]]; then
        log_error "No secrets file found: $secrets_file"
        return 1
    fi
    
    local validation_errors=()
    
    # Validate JWT secrets (base64, 64 characters)
    local jwt_secret=$(grep "^JWT_SECRET_KEY=" "$secrets_file" | cut -d'=' -f2)
    if [[ -n "$jwt_secret" ]]; then
        if [[ ${#jwt_secret} -lt 32 ]] || [[ "$jwt_secret" == *"your-"* ]] || [[ -z "$jwt_secret" ]]; then
            validation_errors+=("JWT_SECRET_KEY: Invalid format or default value")
        fi
    fi
    
    # Validate database passwords (32+ characters)
    local mongodb_password=$(grep "^MONGODB_PASSWORD=" "$secrets_file" | cut -d'=' -f2)
    if [[ -n "$mongodb_password" ]]; then
        if [[ ${#mongodb_password} -lt 32 ]] || [[ "$mongodb_password" == *"your-"* ]] || [[ -z "$mongodb_password" ]]; then
            validation_errors+=("MONGODB_PASSWORD: Invalid format or default value")
        fi
    fi
    
    # Validate TRON private key (hex, 64 characters)
    local tron_key=$(grep "^TRON_PRIVATE_KEY_ENCRYPTED=" "$secrets_file" | cut -d'=' -f2)
    if [[ -n "$tron_key" ]]; then
        if [[ ${#tron_key} -ne 64 ]] || [[ "$tron_key" == *"your-"* ]] || [[ -z "$tron_key" ]]; then
            validation_errors+=("TRON_PRIVATE_KEY_ENCRYPTED: Invalid format or default value")
        fi
    fi
    
    if [[ ${#validation_errors[@]} -gt 0 ]]; then
        log_error "Secret validation errors:"
        for error in "${validation_errors[@]}"; do
            echo "  ❌ $error"
        done
        return 1
    fi
    
    log_success "All secret formats are valid"
    return 0
}

# Function to create backup
create_backup() {
    local backup_timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="$BACKUP_DIR/secrets-backup-$backup_timestamp.tar.gz"
    
    log_info "Creating secrets backup: $backup_file"
    
    if [[ -f "$SECRETS_DIR/.env.secure" ]]; then
        if tar -czf "$backup_file" -C "$SECRETS_DIR" .env.secure; then
            log_success "Secrets backup created: $backup_file"
            return 0
        else
            log_error "Failed to create secrets backup"
            return 1
        fi
    else
        log_warning "No secrets file to backup"
        return 0
    fi
}

# Function to generate all secrets
generate_all_secrets() {
    log_info "Generating all secret types..."
    
    local generated=0
    
    # Generate each secret type
    for secret_type in "${SECRET_TYPES[@]}"; do
        case "$secret_type" in
            "jwt")
                generate_jwt_secrets
                ((generated++))
                ;;
            "database")
                generate_database_secrets
                ((generated++))
                ;;
            "tron")
                generate_tron_secrets
                ((generated++))
                ;;
            "hardware")
                generate_hardware_secrets
                ((generated++))
                ;;
            "mesh")
                generate_mesh_secrets
                ((generated++))
                ;;
            "admin")
                generate_admin_secrets
                ((generated++))
                ;;
            "blockchain")
                generate_blockchain_secrets
                ((generated++))
                ;;
            "session")
                generate_session_secrets
                ((generated++))
                ;;
            "rdp")
                generate_rdp_secrets
                ((generated++))
                ;;
            "node")
                generate_node_secrets
                ((generated++))
                ;;
            "monitoring")
                generate_monitoring_secrets
                ((generated++))
                ;;
            "external")
                generate_external_secrets
                ((generated++))
                ;;
            "backup")
                generate_backup_secrets
                ((generated++))
                ;;
        esac
    done
    
    log_success "Generated $generated secret types"
    return 0
}

# Main function
main() {
    # Handle special operations
    if [[ "$CHECK_SECRETS" == "true" ]]; then
        check_existing_secrets
        return $?
    fi
    
    if [[ "$VALIDATE_SECRETS" == "true" ]]; then
        validate_secret_formats
        return $?
    fi
    
    # Create backup if requested
    if [[ "$CREATE_BACKUP" == "true" ]]; then
        create_backup
    fi
    
    # Generate secrets
    if [[ "$GENERATE_ALL" == "true" ]]; then
        generate_all_secrets
    elif [[ -n "$SECRET_TYPE" ]]; then
        case "$SECRET_TYPE" in
            "jwt")
                generate_jwt_secrets
                ;;
            "database")
                generate_database_secrets
                ;;
            "tron")
                generate_tron_secrets
                ;;
            "hardware")
                generate_hardware_secrets
                ;;
            "mesh")
                generate_mesh_secrets
                ;;
            "admin")
                generate_admin_secrets
                ;;
            "blockchain")
                generate_blockchain_secrets
                ;;
            "session")
                generate_session_secrets
                ;;
            "rdp")
                generate_rdp_secrets
                ;;
            "node")
                generate_node_secrets
                ;;
            "monitoring")
                generate_monitoring_secrets
                ;;
            "external")
                generate_external_secrets
                ;;
            "backup")
                generate_backup_secrets
                ;;
        esac
    else
        log_error "No secret type specified. Use --type or --all"
        show_usage
        exit 1
    fi
}

# Set up signal handlers
cleanup() {
    log_info "Cleaning up..."
}

trap cleanup EXIT INT TERM

# Run main function
main "$@"