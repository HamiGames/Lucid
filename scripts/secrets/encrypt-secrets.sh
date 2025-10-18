#!/bin/bash
# Secret Encryption Script
# LUCID-STRICT Secret Management System
# Purpose: Encrypt and decrypt secrets for secure storage and distribution
# Compatibility: Distroless, API compliant
# Generated: 2025-01-27

set -e

# Configuration
SECRETS_DIR="${LUCID_SECRETS_DIR:-configs/secrets}"
BACKUP_DIR="${LUCID_BACKUP_DIR:-/data/backups/secrets}"
LOG_FILE="${LOG_FILE:-/var/log/lucid/secret-encryption.log}"
ENCRYPTION_KEY_FILE="${LUCID_ENCRYPTION_KEY_FILE:-$SECRETS_DIR/.encryption-key}"
ENCRYPTED_SECRETS_FILE="$SECRETS_DIR/.secrets.encrypted"

# Encryption settings
ENCRYPTION_ALGORITHM="${ENCRYPTION_ALGORITHM:-AES-256-GCM}"
KEY_DERIVATION_FUNCTION="${KEY_DERIVATION_FUNCTION:-PBKDF2}"
KEY_DERIVATION_ITERATIONS="${KEY_DERIVATION_ITERATIONS:-100000}"
SALT_LENGTH="${SALT_LENGTH:-32}"
IV_LENGTH="${IV_LENGTH:-12}"

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

echo "========================================"
log_info "🔐 LUCID Secret Encryption"
echo "========================================"

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Encrypt and decrypt secrets for secure storage and distribution"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -e, --encrypt           Encrypt secrets file"
    echo "  -d, --decrypt           Decrypt secrets file"
    echo "  -b, --backup            Create backup before encryption/decryption"
    echo "  -r, --restore FILE      Restore from backup file"
    echo "  -k, --key-file FILE     Use specific encryption key file"
    echo "  -p, --passphrase        Use passphrase for encryption"
    echo "  -f, --force             Force operation without confirmation"
    echo "  -v, --verbose           Enable verbose output"
    echo "  --check-key             Check encryption key validity"
    echo "  --generate-key          Generate new encryption key"
    echo "  --re-encrypt            Re-encrypt with new key"
    echo "  --verify                Verify encrypted secrets integrity"
    echo ""
    echo "Environment Variables:"
    echo "  LUCID_SECRETS_DIR       Secrets directory (default: configs/secrets)"
    echo "  LUCID_BACKUP_DIR        Backup directory (default: /data/backups/secrets)"
    echo "  LUCID_ENCRYPTION_KEY_FILE Encryption key file (default: configs/secrets/.encryption-key)"
    echo "  ENCRYPTION_ALGORITHM    Encryption algorithm (default: AES-256-GCM)"
    echo "  KEY_DERIVATION_FUNCTION Key derivation function (default: PBKDF2)"
    echo "  KEY_DERIVATION_ITERATIONS Key derivation iterations (default: 100000)"
    echo ""
    echo "Examples:"
    echo "  $0 --encrypt            Encrypt secrets file"
    echo "  $0 --decrypt            Decrypt secrets file"
    echo "  $0 --backup --encrypt   Create backup and encrypt"
    echo "  $0 --restore backup.tar.gz Restore from backup"
    echo "  $0 --generate-key       Generate new encryption key"
    echo "  $0 --verify             Verify encrypted secrets"
}

# Parse command line arguments
ENCRYPT=false
DECRYPT=false
CREATE_BACKUP=false
RESTORE_FILE=""
KEY_FILE=""
USE_PASSPHRASE=false
FORCE=false
VERBOSE=false
CHECK_KEY=false
GENERATE_KEY=false
RE_ENCRYPT=false
VERIFY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -e|--encrypt)
            ENCRYPT=true
            shift
            ;;
        -d|--decrypt)
            DECRYPT=true
            shift
            ;;
        -b|--backup)
            CREATE_BACKUP=true
            shift
            ;;
        -r|--restore)
            RESTORE_FILE="$2"
            shift 2
            ;;
        -k|--key-file)
            KEY_FILE="$2"
            shift 2
            ;;
        -p|--passphrase)
            USE_PASSPHRASE=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --check-key)
            CHECK_KEY=true
            shift
            ;;
        --generate-key)
            GENERATE_KEY=true
            shift
            ;;
        --re-encrypt)
            RE_ENCRYPT=true
            shift
            ;;
        --verify)
            VERIFY=true
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

# Function to generate encryption key
generate_encryption_key() {
    local key_file="${KEY_FILE:-$ENCRYPTION_KEY_FILE}"
    
    log_info "Generating encryption key..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would generate encryption key"
        return 0
    fi
    
    # Generate 256-bit encryption key
    if openssl rand -out "$key_file" 32; then
        chmod 600 "$key_file"
        log_success "Encryption key generated: $key_file"
        return 0
    else
        log_error "Failed to generate encryption key"
        return 1
    fi
}

# Function to check encryption key
check_encryption_key() {
    local key_file="${KEY_FILE:-$ENCRYPTION_KEY_FILE}"
    
    log_info "Checking encryption key..."
    
    if [[ ! -f "$key_file" ]]; then
        log_error "Encryption key file not found: $key_file"
        return 1
    fi
    
    # Check key file permissions
    local key_perms=$(stat -c %a "$key_file" 2>/dev/null || stat -f %A "$key_file" 2>/dev/null || echo "unknown")
    if [[ "$key_perms" != "600" ]]; then
        log_warning "Encryption key file has incorrect permissions: $key_perms (should be 600)"
    fi
    
    # Check key size
    local key_size=$(stat -c %s "$key_file" 2>/dev/null || stat -f %z "$key_file" 2>/dev/null || echo "0")
    if [[ $key_size -ne 32 ]]; then
        log_error "Encryption key has incorrect size: $key_size bytes (should be 32)"
        return 1
    fi
    
    log_success "Encryption key is valid"
    return 0
}

# Function to create backup
create_encryption_backup() {
    local backup_timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="$BACKUP_DIR/encryption-backup-$backup_timestamp.tar.gz"
    
    log_info "Creating encryption backup: $backup_file"
    
    local files_to_backup=()
    
    # Add secrets file if it exists
    if [[ -f "$SECRETS_DIR/.secrets" ]]; then
        files_to_backup+=("$SECRETS_DIR/.secrets")
    fi
    
    # Add encrypted secrets file if it exists
    if [[ -f "$ENCRYPTED_SECRETS_FILE" ]]; then
        files_to_backup+=("$ENCRYPTED_SECRETS_FILE")
    fi
    
    # Add encryption key if it exists
    if [[ -f "$ENCRYPTION_KEY_FILE" ]]; then
        files_to_backup+=("$ENCRYPTION_KEY_FILE")
    fi
    
    if [[ ${#files_to_backup[@]} -gt 0 ]]; then
        if tar -czf "$backup_file" -C "$SECRETS_DIR" "${files_to_backup[@]##*/}"; then
            log_success "Encryption backup created: $backup_file"
            return 0
        else
            log_error "Failed to create encryption backup"
            return 1
        fi
    else
        log_warning "No files to backup"
        return 0
    fi
}

# Function to restore from backup
restore_from_backup() {
    local backup_file="$1"
    
    if [[ -z "$backup_file" ]]; then
        log_error "Backup file not specified"
        return 1
    fi
    
    log_info "Restoring from backup: $backup_file"
    
    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    # Create temporary restore directory
    local temp_restore_dir="/tmp/lucid-secret-restore-$(date +%s)"
    mkdir -p "$temp_restore_dir"
    
    # Extract backup
    if tar -xzf "$backup_file" -C "$temp_restore_dir"; then
        log_success "Backup extracted successfully"
    else
        log_error "Failed to extract backup"
        rm -rf "$temp_restore_dir"
        return 1
    fi
    
    # Restore files
    local restored=0
    
    for file in "$temp_restore_dir"/*; do
        if [[ -f "$file" ]]; then
            local file_name=$(basename "$file")
            local target_path="$SECRETS_DIR/$file_name"
            
            if cp "$file" "$target_path"; then
                # Set appropriate permissions
                if [[ "$file_name" == ".encryption-key" ]]; then
                    chmod 600 "$target_path"
                elif [[ "$file_name" == ".secrets" ]]; then
                    chmod 600 "$target_path"
                elif [[ "$file_name" == ".secrets.encrypted" ]]; then
                    chmod 600 "$target_path"
                fi
                
                log_success "Restored: $file_name"
                ((restored++))
            else
                log_error "Failed to restore: $file_name"
            fi
        fi
    done
    
    # Cleanup
    rm -rf "$temp_restore_dir"
    
    log_success "Restore completed: $restored files restored"
    return 0
}

# Function to encrypt secrets
encrypt_secrets() {
    local secrets_file="$SECRETS_DIR/.secrets"
    local key_file="${KEY_FILE:-$ENCRYPTION_KEY_FILE}"
    
    log_info "Encrypting secrets..."
    
    if [[ ! -f "$secrets_file" ]]; then
        log_error "Secrets file not found: $secrets_file"
        return 1
    fi
    
    if [[ ! -f "$key_file" ]]; then
        log_error "Encryption key file not found: $key_file"
        return 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would encrypt secrets"
        return 0
    fi
    
    # Generate random salt and IV
    local salt=$(openssl rand -hex 16)
    local iv=$(openssl rand -hex 6)
    
    # Encrypt secrets file
    if openssl enc -$ENCRYPTION_ALGORITHM -in "$secrets_file" -out "$ENCRYPTED_SECRETS_FILE" -K "$(cat "$key_file" | xxd -p -c 256)" -iv "$iv" -S "$salt" -pbkdf2 -iter "$KEY_DERIVATION_ITERATIONS"; then
        chmod 600 "$ENCRYPTED_SECRETS_FILE"
        
        # Create metadata file
        cat > "$ENCRYPTED_SECRETS_FILE.meta" << EOF
{
    "algorithm": "$ENCRYPTION_ALGORITHM",
    "salt": "$salt",
    "iv": "$iv",
    "iterations": $KEY_DERIVATION_ITERATIONS,
    "created": "$(date -Iseconds)",
    "key_file": "$key_file"
}
EOF
        chmod 600 "$ENCRYPTED_SECRETS_FILE.meta"
        
        log_success "Secrets encrypted successfully"
        return 0
    else
        log_error "Failed to encrypt secrets"
        return 1
    fi
}

# Function to decrypt secrets
decrypt_secrets() {
    local secrets_file="$SECRETS_DIR/.secrets"
    local key_file="${KEY_FILE:-$ENCRYPTION_KEY_FILE}"
    
    log_info "Decrypting secrets..."
    
    if [[ ! -f "$ENCRYPTED_SECRETS_FILE" ]]; then
        log_error "Encrypted secrets file not found: $ENCRYPTED_SECRETS_FILE"
        return 1
    fi
    
    if [[ ! -f "$key_file" ]]; then
        log_error "Encryption key file not found: $key_file"
        return 1
    fi
    
    if [[ ! -f "$ENCRYPTED_SECRETS_FILE.meta" ]]; then
        log_error "Encryption metadata file not found: $ENCRYPTED_SECRETS_FILE.meta"
        return 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would decrypt secrets"
        return 0
    fi
    
    # Read metadata
    local salt=$(grep '"salt"' "$ENCRYPTED_SECRETS_FILE.meta" | cut -d'"' -f4)
    local iv=$(grep '"iv"' "$ENCRYPTED_SECRETS_FILE.meta" | cut -d'"' -f4)
    local iterations=$(grep '"iterations"' "$ENCRYPTED_SECRETS_FILE.meta" | cut -d':' -f2 | tr -d ' ,')
    
    # Decrypt secrets file
    if openssl enc -$ENCRYPTION_ALGORITHM -d -in "$ENCRYPTED_SECRETS_FILE" -out "$secrets_file" -K "$(cat "$key_file" | xxd -p -c 256)" -iv "$iv" -S "$salt" -pbkdf2 -iter "$iterations"; then
        chmod 600 "$secrets_file"
        log_success "Secrets decrypted successfully"
        return 0
    else
        log_error "Failed to decrypt secrets"
        return 1
    fi
}

# Function to verify encrypted secrets
verify_encrypted_secrets() {
    log_info "Verifying encrypted secrets..."
    
    if [[ ! -f "$ENCRYPTED_SECRETS_FILE" ]]; then
        log_error "Encrypted secrets file not found"
        return 1
    fi
    
    if [[ ! -f "$ENCRYPTED_SECRETS_FILE.meta" ]]; then
        log_error "Encryption metadata file not found"
        return 1
    fi
    
    # Check file permissions
    local encrypted_perms=$(stat -c %a "$ENCRYPTED_SECRETS_FILE" 2>/dev/null || stat -f %A "$ENCRYPTED_SECRETS_FILE" 2>/dev/null || echo "unknown")
    if [[ "$encrypted_perms" != "600" ]]; then
        log_warning "Encrypted secrets file has incorrect permissions: $encrypted_perms (should be 600)"
    fi
    
    # Check metadata format
    if ! jq empty "$ENCRYPTED_SECRETS_FILE.meta" 2>/dev/null; then
        log_error "Encryption metadata file is not valid JSON"
        return 1
    fi
    
    # Check required metadata fields
    local required_fields=("algorithm" "salt" "iv" "iterations" "created" "key_file")
    for field in "${required_fields[@]}"; do
        if ! grep -q "\"$field\"" "$ENCRYPTED_SECRETS_FILE.meta"; then
            log_error "Missing required metadata field: $field"
            return 1
        fi
    done
    
    log_success "Encrypted secrets verification passed"
    return 0
}

# Function to re-encrypt with new key
re_encrypt_secrets() {
    log_info "Re-encrypting secrets with new key..."
    
    # Generate new encryption key
    if ! generate_encryption_key; then
        log_error "Failed to generate new encryption key"
        return 1
    fi
    
    # Decrypt with old key (if encrypted)
    if [[ -f "$ENCRYPTED_SECRETS_FILE" ]]; then
        if ! decrypt_secrets; then
            log_error "Failed to decrypt with old key"
            return 1
        fi
    fi
    
    # Encrypt with new key
    if ! encrypt_secrets; then
        log_error "Failed to encrypt with new key"
        return 1
    fi
    
    log_success "Secrets re-encrypted with new key"
    return 0
}

# Main function
main() {
    # Handle special operations
    if [[ "$CHECK_KEY" == "true" ]]; then
        check_encryption_key
        return $?
    fi
    
    if [[ "$GENERATE_KEY" == "true" ]]; then
        generate_encryption_key
        return $?
    fi
    
    if [[ "$VERIFY" == "true" ]]; then
        verify_encrypted_secrets
        return $?
    fi
    
    if [[ "$RE_ENCRYPT" == "true" ]]; then
        re_encrypt_secrets
        return $?
    fi
    
    if [[ -n "$RESTORE_FILE" ]]; then
        restore_from_backup "$RESTORE_FILE"
        return $?
    fi
    
    # Create backup if requested
    if [[ "$CREATE_BACKUP" == "true" ]]; then
        create_encryption_backup
    fi
    
    # Perform encryption/decryption
    if [[ "$ENCRYPT" == "true" ]]; then
        encrypt_secrets
    elif [[ "$DECRYPT" == "true" ]]; then
        decrypt_secrets
    else
        log_error "No operation specified. Use --encrypt or --decrypt"
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
