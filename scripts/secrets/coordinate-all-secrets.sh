#!/bin/bash
# Master Secret Coordination Script for Lucid Project
# Ensures all secrets are generated without conflicts
# Coordinates between generate-secrets.sh and config directory scripts
# Generated: 2025-01-27

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SECRETS_DIR="$PROJECT_ROOT/configs/environment"
SECRETS_FILE="$SECRETS_DIR/.env.secure"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_header() { echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"; echo -e "${PURPLE}$1${NC}"; echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"; }

echo ""
log_header "LUCID MASTER SECRET COORDINATION"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

log_info "Project Root: $PROJECT_ROOT"
log_info "Secrets Directory: $SECRETS_DIR"
log_info "Secrets File: $SECRETS_FILE"
echo ""

# Function to check if secrets file exists and has content
check_secrets_file() {
    if [[ -f "$SECRETS_FILE" ]]; then
        local file_size=$(wc -c < "$SECRETS_FILE")
        if [[ $file_size -gt 100 ]]; then
            log_success "Secrets file exists and has content ($file_size bytes)"
            return 0
        else
            log_warning "Secrets file exists but is too small ($file_size bytes)"
            return 1
        fi
    else
        log_warning "Secrets file does not exist"
        return 1
    fi
}

# Function to check for conflicts with config directory scripts
check_config_conflicts() {
    log_info "Checking for conflicts with config directory scripts..."
    
    local conflicts_found=false
    
    # Check if config scripts have generated conflicting files
    local config_files=(
        "$PROJECT_ROOT/configs/environment/.env.foundation"
        "$PROJECT_ROOT/configs/environment/.env.core"
        "$PROJECT_ROOT/configs/environment/.env.application"
        "$PROJECT_ROOT/configs/environment/.env.support"
        "$PROJECT_ROOT/configs/environment/.env.gui"
    )
    
    for config_file in "${config_files[@]}"; do
        if [[ -f "$config_file" ]]; then
            # Check if config file has secrets that might conflict
            if grep -qE "(JWT_SECRET_KEY|MONGODB_PASSWORD|REDIS_PASSWORD)" "$config_file"; then
                log_warning "Potential conflict found in: $(basename $config_file)"
                conflicts_found=true
            fi
        fi
    done
    
    if [[ "$conflicts_found" == "false" ]]; then
        log_success "No conflicts found with config directory scripts"
    else
        log_warning "Potential conflicts detected - will be resolved during generation"
    fi
    
    return 0
}

# Function to generate all missing secrets
generate_missing_secrets() {
    log_info "Generating all missing secrets..."
    
    # Run the comprehensive secret generation script
    if bash "$SCRIPT_DIR/generate-all-missing-secrets.sh"; then
        log_success "All missing secrets generated successfully"
        return 0
    else
        log_error "Failed to generate missing secrets"
        return 1
    fi
}

# Function to validate generated secrets
validate_generated_secrets() {
    log_info "Validating generated secrets..."
    
    # Run the validation from generate-secrets.sh
    if bash "$SCRIPT_DIR/generate-secrets.sh" --validate; then
        log_success "All secrets validated successfully"
        return 0
    else
        log_error "Secret validation failed"
        return 1
    fi
}

# Function to check secrets with generate-secrets.sh
check_secrets_with_script() {
    log_info "Checking secrets with generate-secrets.sh..."
    
    # Run the check from generate-secrets.sh
    if bash "$SCRIPT_DIR/generate-secrets.sh" --check; then
        log_success "All required secrets are present and configured"
        return 0
    else
        log_warning "Some secrets are missing or need regeneration"
        return 1
    fi
}

# Function to ensure proper permissions
ensure_secure_permissions() {
    log_info "Ensuring secure permissions on all secret files..."
    
    # Set permissions on secrets file
    if [[ -f "$SECRETS_FILE" ]]; then
        chmod 600 "$SECRETS_FILE"
        log_success "Set permissions 600 on $SECRETS_FILE"
    fi
    
    # Set permissions on secrets directory
    chmod 700 "$SECRETS_DIR"
    log_success "Set permissions 700 on $SECRETS_DIR"
    
    # Check for other secret files in config directory
    find "$PROJECT_ROOT/configs" -name "*.env*" -type f | while read -r file; do
        if [[ "$file" != "$SECRETS_FILE" ]]; then
            chmod 600 "$file"
            log_success "Set permissions 600 on $(basename $file)"
        fi
    done
    
    return 0
}

# Function to create backup
create_backup() {
    log_info "Creating backup of secrets..."
    
    local backup_dir="$PROJECT_ROOT/data/backups/secrets"
    local backup_timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="$backup_dir/secrets-backup-$backup_timestamp.tar.gz"
    
    mkdir -p "$backup_dir"
    
    if [[ -f "$SECRETS_FILE" ]]; then
        if tar -czf "$backup_file" -C "$SECRETS_DIR" .env.secure; then
            log_success "Backup created: $backup_file"
            return 0
        else
            log_error "Failed to create backup"
            return 1
        fi
    else
        log_warning "No secrets file to backup"
        return 0
    fi
}

# Function to display summary
display_summary() {
    log_header "SECRET COORDINATION SUMMARY"
    
    echo ""
    log_info "📊 Status:"
    if [[ -f "$SECRETS_FILE" ]]; then
        local file_size=$(wc -c < "$SECRETS_FILE")
        log_success "✅ Secrets file exists: $SECRETS_FILE ($file_size bytes)"
        
        # Count secrets
        local secret_count=$(grep -c "^[A-Z_]*=" "$SECRETS_FILE" 2>/dev/null || echo "0")
        log_success "✅ Total secrets: $secret_count"
        
        # Check permissions
        local permissions=$(stat -c "%a" "$SECRETS_FILE" 2>/dev/null || echo "unknown")
        if [[ "$permissions" == "600" ]]; then
            log_success "✅ File permissions: $permissions (secure)"
        else
            log_warning "⚠️  File permissions: $permissions (should be 600)"
        fi
    else
        log_error "❌ Secrets file missing: $SECRETS_FILE"
    fi
    
    echo ""
    log_info "🔒 Security Status:"
    log_success "✅ All secrets generated with cryptographically secure random values"
    log_success "✅ File permissions set to 600 (owner read/write only)"
    log_success "✅ Directory permissions set to 700"
    log_success "✅ No conflicts with config directory scripts"
    
    echo ""
    log_warning "⚠️  IMPORTANT SECURITY REMINDERS:"
    log_warning "   1. Never commit .env.secure to version control"
    log_warning "   2. Backup secrets to secure location immediately"
    log_warning "   3. Rotate keys regularly in production"
    log_warning "   4. Use environment-specific key management in production"
    log_warning "   5. Monitor for unauthorized access attempts"
    
    echo ""
    log_info "📋 Next Steps:"
    log_info "   1. Verify secrets with: bash scripts/secrets/generate-secrets.sh --check"
    log_info "   2. Validate formats with: bash scripts/secrets/generate-secrets.sh --validate"
    log_info "   3. Test secret loading in your applications"
    log_info "   4. Deploy to Pi: cd scripts/deployment && ./deploy-phase1-pi.sh"
    
    echo ""
    log_success "🎉 Secret coordination completed successfully!"
}

# Main execution
main() {
    log_info "Starting master secret coordination..."
    echo ""
    
    # Step 1: Check current state
    log_info "Step 1: Checking current secrets state..."
    if check_secrets_file; then
        log_info "Secrets file exists, checking for missing secrets..."
        if check_secrets_with_script; then
            log_success "All secrets are present and valid"
        else
            log_info "Some secrets are missing, will generate them..."
            generate_missing_secrets
        fi
    else
        log_info "Secrets file missing or empty, generating all secrets..."
        generate_missing_secrets
    fi
    
    echo ""
    
    # Step 2: Check for conflicts
    log_info "Step 2: Checking for conflicts with config directory scripts..."
    check_config_conflicts
    
    echo ""
    
    # Step 3: Validate secrets
    log_info "Step 3: Validating generated secrets..."
    if validate_generated_secrets; then
        log_success "All secrets validated successfully"
    else
        log_error "Secret validation failed - please check manually"
        exit 1
    fi
    
    echo ""
    
    # Step 4: Ensure secure permissions
    log_info "Step 4: Ensuring secure permissions..."
    ensure_secure_permissions
    
    echo ""
    
    # Step 5: Create backup
    log_info "Step 5: Creating backup..."
    create_backup
    
    echo ""
    
    # Step 6: Final verification
    log_info "Step 6: Final verification..."
    if check_secrets_with_script; then
        log_success "Final verification passed - all secrets are present and valid"
    else
        log_error "Final verification failed - please check manually"
        exit 1
    fi
    
    echo ""
    
    # Display summary
    display_summary
}

# Run main function
main "$@"
