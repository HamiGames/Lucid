#!/bin/bash
# Generate all environment configuration files
# Implements Step 2 from docker-build-process-plan.md

set -e

# Project root configuration - Dynamic detection
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root if not already there
if [ "$(pwd)" != "$PROJECT_ROOT" ]; then
    echo "Changing to project root: $PROJECT_ROOT"
    cd "$PROJECT_ROOT"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CONFIGS_DIR="$PROJECT_ROOT/configs"
ENV_DIR="$CONFIGS_DIR/environment"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to generate secure random string (aligned with generate-secure-keys.sh)
generate_secure_string() {
    local length=${1:-32}
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
}

# Function to generate JWT secret (64 characters) - aligned with generate-secure-keys.sh
generate_jwt_secret() {
    openssl rand -base64 48 | tr -d "=+/"
}

# Function to generate encryption key (32 bytes = 256 bits) - aligned with generate-secure-keys.sh
generate_encryption_key() {
    openssl rand -hex 32
}

# Function to generate database passwords - aligned with generate-secure-keys.sh
generate_db_password() {
    openssl rand -base64 24 | tr -d "=+/"
}

# Function to generate secure random values
generate_secure_value() {
    local length=$1
    openssl rand -base64 $length | tr -d '\n'
}

# Function to create directory structure
create_directory_structure() {
    log_info "Creating directory structure..."
    
    mkdir -p "$CONFIGS_DIR"
    mkdir -p "$ENV_DIR"
    mkdir -p "$CONFIGS_DIR/docker"
    
    log_success "Directory structure created"
}

# Function to generate secure values
generate_secure_values() {
    log_info "Generating secure configuration values..."
    
    # Generate secure values using aligned functions
    MONGODB_PASSWORD=$(generate_db_password)
    REDIS_PASSWORD=$(generate_db_password)
    JWT_SECRET_KEY=$(generate_jwt_secret)
    ENCRYPTION_KEY=$(generate_encryption_key)
    TOR_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/")
    SESSION_SECRET=$(generate_secure_string 32)
    API_SECRET=$(generate_secure_string 32)
    
    # Network configuration
    PI_HOST="192.168.0.75"
    PI_USER="pickme"
    PI_DEPLOY_DIR="/opt/lucid/production"
    
    # Build configuration
    BUILD_PLATFORM="linux/arm64"
    BUILD_REGISTRY="pickme/lucid"
    BUILD_TAG="latest"
    
    # Database configuration
    MONGODB_URI="mongodb://lucid:${MONGODB_PASSWORD}@mongodb:27017/lucid?authSource=admin"
    REDIS_URI="redis://redis:6379/0"
    ELASTICSEARCH_URI="http://elasticsearch:9200"
    
    log_success "Secure values generated"
}

# Function to generate .env.distroless (Main distroless environment)
generate_distroless_env() {
    log_info "Generating .env.distroless..."
    
    # Call the existing generate-distroless-env.sh script
    if [ -f "scripts/config/generate-distroless-env.sh" ]; then
        bash scripts/config/generate-distroless-env.sh
        log_success ".env.distroless generated"
    else
        log_error "generate-distroless-env.sh not found"
        exit 1
    fi
}

# Function to generate .env.foundation
generate_foundation_env() {
    log_info "Generating .env.foundation..."
    
    # Call the dedicated generate-foundation-env.sh script
    if [ -f "scripts/config/generate-foundation-env.sh" ]; then
        bash scripts/config/generate-foundation-env.sh
        log_success ".env.foundation generated"
    else
        log_error "generate-foundation-env.sh not found"
        exit 1
    fi
}

# Function to generate .env.core
generate_core_env() {
    log_info "Generating .env.core..."
    
    # Call the dedicated generate-core-env.sh script
    if [ -f "scripts/config/generate-core-env.sh" ]; then
        bash scripts/config/generate-core-env.sh
        log_success ".env.core generated"
    else
        log_error "generate-core-env.sh not found"
        exit 1
    fi
}

# Function to generate .env.application
generate_application_env() {
    log_info "Generating .env.application..."
    
    # Call the dedicated generate-application-env.sh script
    if [ -f "scripts/config/generate-application-env.sh" ]; then
        bash scripts/config/generate-application-env.sh
        log_success ".env.application generated"
    else
        log_error "generate-application-env.sh not found"
        exit 1
    fi
}

# Function to generate .env.support
generate_support_env() {
    log_info "Generating .env.support..."
    
    # Call the dedicated generate-support-env.sh script
    if [ -f "scripts/config/generate-support-env.sh" ]; then
        bash scripts/config/generate-support-env.sh
        log_success ".env.support generated"
    else
        log_error "generate-support-env.sh not found"
        exit 1
    fi
}

# Function to generate .env.gui
generate_gui_env() {
    log_info "Generating .env.gui..."
    
    cat > "$ENV_DIR/.env.gui" << EOF
# GUI Integration Configuration
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Services: Electron GUI, API Bridge, Docker Manager, Tor Manager, Hardware Wallet

# Database Configuration (inherited from foundation)
MONGODB_PASSWORD=$MONGODB_PASSWORD
MONGODB_URI=$MONGODB_URI
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URI=$REDIS_URI

# Authentication Configuration (inherited from foundation)
JWT_SECRET_KEY=$JWT_SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY

# GUI API Bridge Configuration
GUI_API_BRIDGE_PORT=8099
GUI_API_BRIDGE_HOST=gui-api-bridge
GUI_API_BRIDGE_TIMEOUT=30

# GUI Docker Manager Configuration
GUI_DOCKER_MANAGER_PORT=8100
GUI_DOCKER_MANAGER_HOST=gui-docker-manager
GUI_DOCKER_MANAGER_TIMEOUT=30

# GUI Tor Manager Configuration
GUI_TOR_MANAGER_PORT=8101
GUI_TOR_MANAGER_HOST=gui-tor-manager
GUI_TOR_MANAGER_TIMEOUT=30

# GUI Hardware Wallet Configuration
GUI_HARDWARE_WALLET_PORT=8102
GUI_HARDWARE_WALLET_HOST=gui-hardware-wallet
GUI_HARDWARE_WALLET_TIMEOUT=30

# Electron GUI Configuration
ELECTRON_GUI_PORT=3000
ELECTRON_GUI_HOST=localhost
ELECTRON_GUI_DEVELOPMENT=false
ELECTRON_GUI_PRODUCTION=true

# GUI Variants
GUI_VARIANTS=user,developer,node,admin
GUI_DEFAULT_VARIANT=user

# Hardware Wallet Configuration
HARDWARE_WALLET_ENABLED=true
HARDWARE_WALLET_SUPPORTED=ledger,trezor,keepkey
HARDWARE_WALLET_TIMEOUT=30

# Tor Configuration
TOR_ENABLED=true
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051
TOR_DATA_DIR=/var/lib/tor
TOR_LOG_DIR=/var/log/tor

# GUI Security Configuration
GUI_HTTPS_ENABLED=true
GUI_CERT_PATH=/etc/ssl/certs/lucid-gui.crt
GUI_KEY_PATH=/etc/ssl/private/lucid-gui.key
GUI_CORS_ENABLED=true
GUI_CORS_ORIGINS=*
EOF

    log_success ".env.gui generated"
}

# Function to validate generated files
validate_generated_files() {
    log_info "Validating generated environment files..."
    
    local env_files=(
        ".env.distroless"
        ".env.foundation"
        ".env.core"
        ".env.application"
        ".env.support"
        ".env.gui"
    )
    
    for env_file in "${env_files[@]}"; do
        local file_path="$ENV_DIR/$env_file"
        
        if [[ -f "$file_path" ]]; then
            # Check for placeholder values
            if grep -q '\${' "$file_path"; then
                log_error "Placeholder values found in $env_file"
                exit 1
            fi
            
            # Check file size
            local file_size=$(wc -c < "$file_path")
            if [[ $file_size -lt 100 ]]; then
                log_error "File $env_file is too small ($file_size bytes)"
                exit 1
            fi
            
            log_success "$env_file validated"
        else
            log_error "File not found: $env_file"
            exit 1
        fi
    done
    
    log_success "All environment files validated"
}

# Function to display summary
display_summary() {
    log_info "Environment Configuration Generation Summary:"
    echo ""
    echo "Generated Files:"
    echo "  • $ENV_DIR/.env.distroless"
    echo "  • $ENV_DIR/.env.foundation"
    echo "  • $ENV_DIR/.env.core"
    echo "  • $ENV_DIR/.env.application"
    echo "  • $ENV_DIR/.env.support"
    echo "  • $ENV_DIR/.env.gui"
    echo ""
    echo "Configuration Details:"
    echo "  • MongoDB Password: Generated (32 bytes)"
    echo "  • Redis Password: Generated (32 bytes)"
    echo "  • JWT Secret Key: Generated (64 bytes)"
    echo "  • Encryption Key: Generated (32 bytes)"
    echo "  • Tor Password: Generated (32 bytes)"
    echo "  • Pi Host: $PI_HOST"
    echo "  • Pi User: $PI_USER"
    echo "  • Build Platform: $BUILD_PLATFORM"
    echo "  • Build Registry: $BUILD_REGISTRY"
    echo ""
    log_success "Environment configuration generation completed successfully!"
}

# Main execution
main() {
    log_info "=== Environment Configuration Generation ==="
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Configs Directory: $CONFIGS_DIR"
    log_info "Environment Directory: $ENV_DIR"
    echo ""
    
    # Execute generation steps
    create_directory_structure
    generate_secure_values
    generate_distroless_env
    generate_foundation_env
    generate_core_env
    generate_application_env
    generate_support_env
    generate_gui_env
    validate_generated_files
    
    # Display summary
    echo ""
    display_summary
}

# Run main function
main "$@"