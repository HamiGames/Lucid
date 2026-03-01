#!/bin/bash
# Complete Secret Generation Script for Lucid Project
# Generates ALL missing secrets that generate-secrets.sh expects
# Aligned with config directory structure
# Generated: 2025-01-27

set -e

# Configuration - Aligned with config directory structure
SECRETS_DIR="${LUCID_SECRETS_DIR:-configs/environment}"
SECRETS_FILE="$SECRETS_DIR/.env.secure"

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

echo "========================================"
log_info "🔐 LUCID Complete Secret Generation"
echo "========================================"

# Create directories if they don't exist
mkdir -p "$SECRETS_DIR"

# Function to generate secure random string
generate_secure_string() {
    local length=${1:-32}
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
}

# Function to generate hex key
generate_hex_key() {
    local length=${1:-32}
    openssl rand -hex $length
}

log_info "Generating all missing secrets..."

# Generate JWT secrets
JWT_SECRET_KEY=$(openssl rand -base64 64)
JWT_REFRESH_SECRET_KEY=$(openssl rand -base64 64)
log_success "Generated JWT secrets"

# Generate database passwords
MONGODB_PASSWORD=$(openssl rand -base64 48)
MONGODB_ROOT_PASSWORD=$(openssl rand -base64 48)
REDIS_PASSWORD=$(openssl rand -base64 48)
ELASTICSEARCH_PASSWORD=$(openssl rand -base64 48)
log_success "Generated database passwords"

# Generate TRON secrets
TRON_PRIVATE_KEY_ENCRYPTED=$(openssl rand -hex 32)
TRON_PRIVATE_KEY_PASSPHRASE=$(openssl rand -base64 32)
TRON_API_KEY=$(openssl rand -hex 32)
log_success "Generated TRON secrets"

# Generate admin secrets
ADMIN_JWT_SECRET=$(openssl rand -base64 64)
ADMIN_API_KEY=$(openssl rand -hex 32)
ADMIN_SESSION_SECRET=$(openssl rand -base64 64)
log_success "Generated admin secrets"

# Generate blockchain secrets
BLOCKCHAIN_CONSENSUS_SECRET=$(openssl rand -base64 64)
BLOCKCHAIN_VALIDATOR_KEY=$(openssl rand -hex 32)
BLOCKCHAIN_NODE_ID=$(openssl rand -hex 16)
log_success "Generated blockchain secrets"

# Generate session secrets
SESSION_ENCRYPTION_KEY=$(openssl rand -base64 64)
SESSION_SIGNING_KEY=$(openssl rand -base64 64)
CHUNK_ENCRYPTION_KEY=$(openssl rand -base64 64)
log_success "Generated session secrets"

# Generate RDP secrets
RDP_ADMIN_PASSWORD=$(openssl rand -base64 32)
XRDP_PASSWORD=$(openssl rand -base64 32)
RDP_SESSION_KEY=$(openssl rand -hex 32)
log_success "Generated RDP secrets"

# Generate node management secrets
NODE_OPERATOR_KEY=$(openssl rand -hex 32)
POOT_VALIDATION_SECRET=$(openssl rand -base64 64)
NODE_REGISTRATION_TOKEN=$(openssl rand -hex 32)
log_success "Generated node management secrets"

# Generate monitoring secrets
PROMETHEUS_SECRET=$(openssl rand -base64 64)
GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 32)
ALERTMANAGER_WEBHOOK_SECRET=$(openssl rand -hex 32)
log_success "Generated monitoring secrets"

# Generate hardware wallet secrets
LEDGER_APP_ID=$(openssl rand -hex 16)
TREZOR_APP_ID=$(openssl rand -hex 16)
KEEPKEY_APP_ID=$(openssl rand -hex 16)
log_success "Generated hardware wallet secrets"

# Generate service mesh secrets
SERVICE_MESH_CA_CERT=$(openssl rand -base64 64)
SERVICE_MESH_CA_KEY=$(openssl rand -base64 64)
SERVICE_MESH_JWT_SECRET=$(openssl rand -base64 64)
log_success "Generated service mesh secrets"

# Generate external service secrets
TOR_CONTROL_PASSWORD=$(openssl rand -base64 32)
DOCKER_REGISTRY_PASSWORD=$(openssl rand -base64 32)
GITHUB_TOKEN=$(openssl rand -hex 32)
log_success "Generated external service secrets"

# Generate backup secrets
BACKUP_ENCRYPTION_KEY=$(openssl rand -base64 64)
BACKUP_SIGNING_KEY=$(openssl rand -base64 64)
log_success "Generated backup secrets"

# Create the secrets file
log_info "Creating secrets file: $SECRETS_FILE"

cat > "$SECRETS_FILE" << EOF
# Lucid Master Secure Environment Variables
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# WARNING: Keep this file secure! Never commit to version control!

# =============================================================================
# JWT AND AUTHENTICATION SECRETS
# =============================================================================
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_REFRESH_SECRET_KEY=$JWT_REFRESH_SECRET_KEY

# =============================================================================
# DATABASE PASSWORDS
# =============================================================================
MONGODB_PASSWORD=$MONGODB_PASSWORD
MONGODB_ROOT_PASSWORD=$MONGODB_ROOT_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD
ELASTICSEARCH_PASSWORD=$ELASTICSEARCH_PASSWORD

# =============================================================================
# TRON PAYMENT SECRETS (ISOLATED)
# =============================================================================
TRON_PRIVATE_KEY_ENCRYPTED=$TRON_PRIVATE_KEY_ENCRYPTED
TRON_PRIVATE_KEY_PASSPHRASE=$TRON_PRIVATE_KEY_PASSPHRASE
TRON_API_KEY=$TRON_API_KEY

# =============================================================================
# ADMIN INTERFACE SECRETS
# =============================================================================
ADMIN_JWT_SECRET=$ADMIN_JWT_SECRET
ADMIN_API_KEY=$ADMIN_API_KEY
ADMIN_SESSION_SECRET=$ADMIN_SESSION_SECRET

# =============================================================================
# BLOCKCHAIN CONSENSUS SECRETS
# =============================================================================
BLOCKCHAIN_CONSENSUS_SECRET=$BLOCKCHAIN_CONSENSUS_SECRET
BLOCKCHAIN_VALIDATOR_KEY=$BLOCKCHAIN_VALIDATOR_KEY
BLOCKCHAIN_NODE_ID=$BLOCKCHAIN_NODE_ID

# =============================================================================
# SESSION MANAGEMENT SECRETS
# =============================================================================
SESSION_ENCRYPTION_KEY=$SESSION_ENCRYPTION_KEY
SESSION_SIGNING_KEY=$SESSION_SIGNING_KEY
CHUNK_ENCRYPTION_KEY=$CHUNK_ENCRYPTION_KEY

# =============================================================================
# RDP SERVICE SECRETS
# =============================================================================
RDP_ADMIN_PASSWORD=$RDP_ADMIN_PASSWORD
XRDP_PASSWORD=$XRDP_PASSWORD
RDP_SESSION_KEY=$RDP_SESSION_KEY

# =============================================================================
# NODE MANAGEMENT SECRETS
# =============================================================================
NODE_OPERATOR_KEY=$NODE_OPERATOR_KEY
POOT_VALIDATION_SECRET=$POOT_VALIDATION_SECRET
NODE_REGISTRATION_TOKEN=$NODE_REGISTRATION_TOKEN

# =============================================================================
# MONITORING AND ALERTING SECRETS
# =============================================================================
PROMETHEUS_SECRET=$PROMETHEUS_SECRET
GRAFANA_ADMIN_PASSWORD=$GRAFANA_ADMIN_PASSWORD
ALERTMANAGER_WEBHOOK_SECRET=$ALERTMANAGER_WEBHOOK_SECRET

# =============================================================================
# HARDWARE WALLET SECRETS
# =============================================================================
LEDGER_APP_ID=$LEDGER_APP_ID
TREZOR_APP_ID=$TREZOR_APP_ID
KEEPKEY_APP_ID=$KEEPKEY_APP_ID

# =============================================================================
# SERVICE MESH SECRETS
# =============================================================================
SERVICE_MESH_CA_CERT=$SERVICE_MESH_CA_CERT
SERVICE_MESH_CA_KEY=$SERVICE_MESH_CA_KEY
SERVICE_MESH_JWT_SECRET=$SERVICE_MESH_JWT_SECRET

# =============================================================================
# EXTERNAL SERVICE SECRETS
# =============================================================================
TOR_CONTROL_PASSWORD=$TOR_CONTROL_PASSWORD
DOCKER_REGISTRY_PASSWORD=$DOCKER_REGISTRY_PASSWORD
GITHUB_TOKEN=$GITHUB_TOKEN

# =============================================================================
# BACKUP ENCRYPTION SECRETS
# =============================================================================
BACKUP_ENCRYPTION_KEY=$BACKUP_ENCRYPTION_KEY
BACKUP_SIGNING_KEY=$BACKUP_SIGNING_KEY

# =============================================================================
# SECURITY NOTES
# =============================================================================
# All values are cryptographically secure random values generated using openssl
# Database passwords: 48 bytes, base64 encoded
# JWT secrets: 64 bytes, base64 encoded
# Encryption keys: 64 bytes, base64 encoded
# Blockchain keys: 32-64 bytes, hex encoded
# 
# IMPORTANT:
# - Store this file securely (chmod 600)
# - Never commit to version control
# - Rotate keys regularly in production
# - Backup to secure location
# - Use environment-specific key management in production
EOF

# Set secure permissions
chmod 600 "$SECRETS_FILE"

log_success "Secrets file created: $SECRETS_FILE (chmod 600)"

# Verify the secrets were created correctly
log_info "Verifying secrets..."

# Check for required secrets
required_secrets=(
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

missing_count=0
for secret in "${required_secrets[@]}"; do
    if grep -q "^${secret}=" "$SECRETS_FILE"; then
        local value=$(grep "^${secret}=" "$SECRETS_FILE" | cut -d'=' -f2)
        if [[ -n "$value" ]] && [[ "$value" != *"your-"* ]] && [[ "$value" != *"change-in-production"* ]]; then
            log_success "✅ $secret"
        else
            log_error "❌ $secret (empty or placeholder)"
            ((missing_count++))
        fi
    else
        log_error "❌ $secret (missing)"
        ((missing_count++))
    fi
done

if [[ $missing_count -eq 0 ]]; then
    log_success "All required secrets generated successfully!"
    echo ""
    log_info "📋 Summary:"
    log_info "   • Secrets file: $SECRETS_FILE"
    log_info "   • File permissions: 600 (owner read/write only)"
    log_info "   • Total secrets generated: ${#required_secrets[@]}"
    log_info "   • All secrets are cryptographically secure"
    echo ""
    log_warning "⚠️  SECURITY REMINDERS:"
    log_warning "   1. Never commit this file to version control"
    log_warning "   2. Backup to secure location immediately"
    log_warning "   3. Rotate keys regularly in production"
    log_warning "   4. Use environment-specific key management"
    echo ""
    log_success "🎉 Secret generation completed successfully!"
    exit 0
else
    log_error "Secret generation failed: $missing_count secrets missing or invalid"
    exit 1
fi
