#!/bin/bash
# TPM Key Generation Script
# LUCID-STRICT Layer 2 Security Management
# Purpose: Generate TPM-based keys for hardware security
# Compatibility: Distroless, API compliant
# Generated: 2025-01-27

set -e

# Configuration
KEYS_DIR="${LUCID_KEYS_DIR:-/data/keys}"
TPM_KEYS_DIR="${KEYS_DIR}/tpm"
BACKUP_DIR="${LUCID_BACKUP_DIR:-/data/backups/keys}"
LOG_FILE="${LOG_FILE:-/var/log/lucid/tpm-key-generation.log}"
TPM_DEVICE="${TPM_DEVICE:-/dev/tpm0}"
TPM_VERSION="${TPM_VERSION:-2.0}"

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
mkdir -p "$KEYS_DIR"
mkdir -p "$TPM_KEYS_DIR"
mkdir -p "$BACKUP_DIR"

echo "========================================"
log_info "🔐 LUCID TPM Key Generation"
echo "========================================"

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Generate TPM-based keys for hardware security"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -f, --force             Force key generation without confirmation"
    echo "  -d, --dry-run           Show what would be generated without executing"
    echo "  -t, --key-types TYPES   Generate specific key types (comma-separated)"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -b, --backup            Create backup of existing keys before generation"
    echo "  -c, --check-tpm         Check TPM availability and status"
    echo "  -l, --list              List existing TPM keys"
    echo "  -r, --remove-all        Remove all TPM keys (use with caution)"
    echo "  -s, --status            Show TPM status and capabilities"
    echo ""
    echo "Key Types:"
    echo "  session                 Session encryption keys"
    echo "  admin                   Admin authentication keys"
    echo "  storage                 Storage encryption keys"
    echo "  network                 Network communication keys"
    echo "  blockchain              Blockchain signing keys"
    echo "  all                     All key types (default)"
    echo ""
    echo "Environment Variables:"
    echo "  LUCID_KEYS_DIR          Keys directory (default: /data/keys)"
    echo "  TPM_KEYS_DIR            TPM keys directory (default: /data/keys/tpm)"
    echo "  LUCID_BACKUP_DIR        Backup directory (default: /data/backups/keys)"
    echo "  TPM_DEVICE              TPM device path (default: /dev/tpm0)"
    echo "  TPM_VERSION             TPM version (default: 2.0)"
    echo ""
    echo "Examples:"
    echo "  $0 --check-tpm          Check TPM availability"
    echo "  $0 --key-types session,admin  Generate specific key types"
    echo "  $0 --backup --force     Create backup and generate keys"
    echo "  $0 --dry-run            Show what would be generated"
}

# Parse command line arguments
FORCE=false
DRY_RUN=false
KEY_TYPES="all"
VERBOSE=false
BACKUP=false
CHECK_TPM=false
LIST_KEYS=false
REMOVE_ALL=false
SHOW_STATUS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -t|--key-types)
            KEY_TYPES="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -b|--backup)
            BACKUP=true
            shift
            ;;
        -c|--check-tpm)
            CHECK_TPM=true
            shift
            ;;
        -l|--list)
            LIST_KEYS=true
            shift
            ;;
        -r|--remove-all)
            REMOVE_ALL=true
            shift
            ;;
        -s|--status)
            SHOW_STATUS=true
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

# Function to check TPM availability
check_tpm_availability() {
    log_info "Checking TPM availability..."
    
    # Check if TPM device exists
    if [[ ! -e "$TPM_DEVICE" ]]; then
        log_error "TPM device not found: $TPM_DEVICE"
        log_info "Make sure TPM is enabled in BIOS/UEFI and driver is loaded"
        return 1
    fi
    
    # Check TPM version
    if command -v tpm2_getcap &> /dev/null; then
        local tpm_version=$(tpm2_getcap -T properties-fixed 2>/dev/null | grep -i "TPM_PT_FAMILY_INDICATOR" | awk '{print $3}' || echo "unknown")
        log_info "TPM version detected: $tpm_version"
        
        if [[ "$tpm_version" != "2.0" ]]; then
            log_warning "TPM version $tpm_version detected, expected 2.0"
        fi
    else
        log_warning "tpm2-tools not available, cannot verify TPM version"
    fi
    
    # Check TPM status
    if command -v tpm2_getcap &> /dev/null; then
        if tpm2_getcap -T properties-fixed &>/dev/null; then
            log_success "TPM is accessible and responding"
            return 0
        else
            log_error "TPM is not responding to commands"
            return 1
        fi
    else
        log_warning "tpm2-tools not available, cannot verify TPM status"
        return 1
    fi
}

# Function to show TPM status
show_tpm_status() {
    log_info "TPM Status and Capabilities:"
    echo ""
    
    # Device information
    if [[ -e "$TPM_DEVICE" ]]; then
        log_success "TPM Device: $TPM_DEVICE (exists)"
        if [[ -r "$TPM_DEVICE" && -w "$TPM_DEVICE" ]]; then
            log_success "TPM Device: Read/Write access available"
        else
            log_warning "TPM Device: Limited access permissions"
        fi
    else
        log_error "TPM Device: $TPM_DEVICE (not found)"
    fi
    
    # TPM capabilities
    if command -v tpm2_getcap &> /dev/null; then
        echo ""
        log_info "TPM Capabilities:"
        
        # Get TPM properties
        if tpm2_getcap -T properties-fixed &>/dev/null; then
            local manufacturer=$(tpm2_getcap -T properties-fixed 2>/dev/null | grep -i "TPM_PT_MANUFACTURER" | awk '{print $3}' || echo "unknown")
            local family=$(tpm2_getcap -T properties-fixed 2>/dev/null | grep -i "TPM_PT_FAMILY_INDICATOR" | awk '{print $3}' || echo "unknown")
            local spec_level=$(tpm2_getcap -T properties-fixed 2>/dev/null | grep -i "TPM_PT_SPEC_LEVEL" | awk '{print $3}' || echo "unknown")
            
            echo "  Manufacturer: $manufacturer"
            echo "  Family: $family"
            echo "  Spec Level: $spec_level"
        fi
        
        # Get algorithm support
        echo ""
        log_info "Supported Algorithms:"
        if tpm2_getcap -T algorithms &>/dev/null; then
            tpm2_getcap -T algorithms 2>/dev/null | grep -E "(TPM_ALG_|name)" | head -10 || echo "  Unable to retrieve algorithms"
        fi
        
        # Get key types support
        echo ""
        log_info "Supported Key Types:"
        if tpm2_getcap -T ecc-curves &>/dev/null; then
            echo "  ECC Curves: Available"
        fi
        if tpm2_getcap -T rsa &>/dev/null; then
            echo "  RSA: Available"
        fi
    else
        log_warning "tpm2-tools not available, limited status information"
    fi
    
    echo ""
}

# Function to list existing TPM keys
list_tpm_keys() {
    log_info "Existing TPM Keys:"
    echo ""
    
    local key_files=($(find "$TPM_KEYS_DIR" -name "*.key" -o -name "*.pub" -o -name "*.priv" -type f))
    
    if [[ ${#key_files[@]} -eq 0 ]]; then
        log_warning "No TPM keys found"
        return 0
    fi
    
    printf "%-40s %-20s %-15s %-10s %-15s\n" "KEY FILE" "CREATED" "AGE" "SIZE" "TYPE"
    echo "--------------------------------------------------------------------------------------------------------"
    
    for key_file in "${key_files[@]}"; do
        local file_name=$(basename "$key_file")
        local created=$(stat -c %y "$key_file" 2>/dev/null || stat -f %Sm "$key_file" 2>/dev/null || echo "unknown")
        local age=$(find "$key_file" -type f -printf '%T@\n' 2>/dev/null | awk '{print int((systime() - $1) / 86400)}' || echo "unknown")
        local size=$(stat -c %s "$key_file" 2>/dev/null || stat -f %z "$key_file" 2>/dev/null || echo "unknown")
        local file_type="unknown"
        
        if [[ "$file_name" == *.pub ]]; then
            file_type="public"
        elif [[ "$file_name" == *.priv ]]; then
            file_type="private"
        elif [[ "$file_name" == *.key ]]; then
            file_type="symmetric"
        fi
        
        printf "%-40s %-20s %-15s %-10s %-15s\n" "$file_name" "${created% *}" "${age}d" "${size}B" "$file_type"
    done
    
    echo ""
}

# Function to backup existing keys
backup_existing_keys() {
    log_info "Creating backup of existing TPM keys..."
    
    local backup_timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_path="$BACKUP_DIR/tpm-keys-backup-$backup_timestamp"
    
    mkdir -p "$backup_path"
    
    # Backup all TPM key files
    local key_files=($(find "$TPM_KEYS_DIR" -type f))
    
    if [[ ${#key_files[@]} -eq 0 ]]; then
        log_warning "No TPM keys found to backup"
        return 0
    fi
    
    local backed_up=0
    for key_file in "${key_files[@]}"; do
        local key_name=$(basename "$key_file")
        if cp "$key_file" "$backup_path/$key_name"; then
            log_info "Backed up key: $key_name"
            ((backed_up++))
        else
            log_error "Failed to backup key: $key_name"
        fi
    done
    
    # Create backup manifest
    cat > "$backup_path/manifest.json" << EOF
{
    "backup_timestamp": "$backup_timestamp",
    "backup_date": "$(date -Iseconds)",
    "keys_backed_up": $backed_up,
    "tpm_version": "$TPM_VERSION",
    "tpm_device": "$TPM_DEVICE",
    "lucid_version": "$(cat /opt/lucid/VERSION 2>/dev/null || echo 'unknown')"
}
EOF
    
    # Compress backup
    if tar -czf "$backup_path.tar.gz" -C "$(dirname "$backup_path")" "$(basename "$backup_path")"; then
        rm -rf "$backup_path"
        log_success "TPM keys backup created: $backup_path.tar.gz"
        return 0
    else
        log_error "Failed to compress backup"
        return 1
    fi
}

# Function to remove all TPM keys
remove_all_tpm_keys() {
    log_warning "Removing all TPM keys..."
    
    local key_files=($(find "$TPM_KEYS_DIR" -type f))
    
    if [[ ${#key_files[@]} -eq 0 ]]; then
        log_info "No TPM keys found to remove"
        return 0
    fi
    
    if [[ "$FORCE" == "false" ]]; then
        echo ""
        log_warning "This will remove ${#key_files[@]} TPM key files:"
        for key_file in "${key_files[@]}"; do
            echo "  - $(basename "$key_file")"
        done
        echo ""
        read -p "Are you sure you want to continue? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log_info "Key removal cancelled by user"
            return 0
        fi
    fi
    
    local removed=0
    for key_file in "${key_files[@]}"; do
        if rm "$key_file"; then
            log_info "Removed key: $(basename "$key_file")"
            ((removed++))
        else
            log_error "Failed to remove key: $(basename "$key_file")"
        fi
    done
    
    log_success "Removed $removed TPM keys"
}

# Function to generate TPM key
generate_tpm_key() {
    local key_type="$1"
    local key_name="$2"
    local key_path="$3"
    
    log_info "Generating TPM key: $key_type ($key_name)"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would generate TPM key $key_name"
        return 0
    fi
    
    # Check if tpm2-tools is available
    if ! command -v tpm2_create &> /dev/null; then
        log_error "tpm2-tools not available for TPM key generation"
        return 1
    fi
    
    # Generate key based on type
    case "$key_type" in
        "session")
            # Generate symmetric session key
            if openssl rand -out "$key_path" 32; then
                chmod 600 "$key_path"
                log_success "Generated session key: $key_name"
                return 0
            else
                log_error "Failed to generate session key: $key_name"
                return 1
            fi
            ;;
        "admin"|"storage"|"network"|"blockchain")
            # Generate ECC key pair
            local public_key="${key_path%.*}.pub"
            local private_key="${key_path%.*}.priv"
            
            if tpm2_create -C e -g sha256 -G ecc256 -u "$public_key" -r "$private_key" -c "$key_path.ctx" 2>/dev/null; then
                # Extract key material
                if tpm2_readpublic -c "$key_path.ctx" -o "$public_key" &>/dev/null; then
                    log_success "Generated $key_type key pair: $key_name"
                    chmod 600 "$private_key"
                    chmod 644 "$public_key"
                    rm -f "$key_path.ctx"  # Clean up context file
                    return 0
                else
                    log_error "Failed to extract public key: $key_name"
                    rm -f "$public_key" "$private_key" "$key_path.ctx"
                    return 1
                fi
            else
                log_error "Failed to generate $key_type key: $key_name"
                rm -f "$public_key" "$private_key" "$key_path.ctx"
                return 1
            fi
            ;;
        *)
            log_error "Unknown key type: $key_type"
            return 1
            ;;
    esac
}

# Function to generate all TPM keys
generate_all_tpm_keys() {
    log_info "Generating TPM keys..."
    
    # Check TPM availability
    if ! check_tpm_availability; then
        log_error "TPM not available, cannot generate TPM keys"
        return 1
    fi
    
    # Backup existing keys if requested
    if [[ "$BACKUP" == "true" ]]; then
        backup_existing_keys
    fi
    
    # Parse key types
    local key_types_to_generate=()
    if [[ "$KEY_TYPES" == "all" ]]; then
        key_types_to_generate=("session" "admin" "storage" "network" "blockchain")
    else
        IFS=',' read -ra TYPES_ARRAY <<< "$KEY_TYPES"
        key_types_to_generate=("${TYPES_ARRAY[@]}")
    fi
    
    # Generate keys
    local generated=0
    local failed=0
    
    for key_type in "${key_types_to_generate[@]}"; do
        local key_timestamp=$(date +"%Y%m%d-%H%M%S")
        local key_name="${key_type}-${key_timestamp}"
        
        case "$key_type" in
            "session")
                local key_path="$TPM_KEYS_DIR/${key_name}.key"
                ;;
            *)
                local key_path="$TPM_KEYS_DIR/${key_name}.key"
                ;;
        esac
        
        if generate_tpm_key "$key_type" "$key_name" "$key_path"; then
            ((generated++))
        else
            ((failed++))
        fi
    done
    
    if [[ "$DRY_RUN" == "false" ]]; then
        log_success "TPM key generation completed: $generated generated, $failed failed"
        
        # Create key manifest
        create_key_manifest
    else
        log_info "DRY RUN: Would generate $generated TPM keys"
    fi
    
    return 0
}

# Function to create key manifest
create_key_manifest() {
    local manifest_file="$TPM_KEYS_DIR/manifest.json"
    local manifest_timestamp=$(date +"%Y%m%d_%H%M%S")
    
    log_info "Creating TPM key manifest..."
    
    # Get all key files
    local key_files=($(find "$TPM_KEYS_DIR" -name "*.key" -o -name "*.pub" -o -name "*.priv" -type f))
    
    # Generate key information
    local key_info=()
    for key_file in "${key_files[@]}"; do
        local key_name=$(basename "$key_file")
        local key_type="unknown"
        local key_size=$(stat -c %s "$key_file" 2>/dev/null || stat -f %z "$key_file" 2>/dev/null || echo "unknown")
        
        # Determine key type from filename
        if [[ "$key_name" == session-*.key ]]; then
            key_type="session"
        elif [[ "$key_name" == admin-*.key ]]; then
            key_type="admin"
        elif [[ "$key_name" == storage-*.key ]]; then
            key_type="storage"
        elif [[ "$key_name" == network-*.key ]]; then
            key_type="network"
        elif [[ "$key_name" == blockchain-*.key ]]; then
            key_type="blockchain"
        fi
        
        key_info+=("{\"name\":\"$key_name\",\"type\":\"$key_type\",\"size\":$key_size}")
    done
    
    # Create manifest JSON
    cat > "$manifest_file" << EOF
{
    "manifest_timestamp": "$manifest_timestamp",
    "manifest_date": "$(date -Iseconds)",
    "tpm_version": "$TPM_VERSION",
    "tpm_device": "$TPM_DEVICE",
    "total_keys": ${#key_files[@]},
    "lucid_version": "$(cat /opt/lucid/VERSION 2>/dev/null || echo 'unknown')",
    "keys": [$(IFS=','; echo "${key_info[*]}")]
}
EOF
    
    log_success "TPM key manifest created: $manifest_file"
}

# Main function
main() {
    # Handle special operations
    if [[ "$CHECK_TPM" == "true" ]]; then
        check_tpm_availability
        return $?
    fi
    
    if [[ "$SHOW_STATUS" == "true" ]]; then
        show_tpm_status
        return 0
    fi
    
    if [[ "$LIST_KEYS" == "true" ]]; then
        list_tpm_keys
        return 0
    fi
    
    if [[ "$REMOVE_ALL" == "true" ]]; then
        remove_all_tpm_keys
        return $?
    fi
    
    # Confirmation prompt (unless forced or dry run)
    if [[ "$FORCE" == "false" && "$DRY_RUN" == "false" ]]; then
        echo ""
        log_info "This will generate TPM keys for: $KEY_TYPES"
        log_info "Keys will be stored in: $TPM_KEYS_DIR"
        
        if [[ "$BACKUP" == "true" ]]; then
            log_info "Existing keys will be backed up before generation"
        fi
        
        echo ""
        read -p "Continue with TPM key generation? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log_info "TPM key generation cancelled by user"
            return 0
        fi
    fi
    
    # Generate TPM keys
    generate_all_tpm_keys
}

# Set up signal handlers
cleanup() {
    log_info "Cleaning up..."
    # Cleanup will be handled by individual functions
}

trap cleanup EXIT INT TERM

# Run main function
main "$@"
