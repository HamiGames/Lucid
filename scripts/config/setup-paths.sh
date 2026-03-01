#!/bin/bash
# Path: scripts/config/setup-paths.sh
# Setup global path configuration for Lucid project
# Ensures all required directories exist and sets up path variables

set -euo pipefail

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

# =============================================================================
# GLOBAL PATH CONFIGURATION
# =============================================================================
# Set global path variables for consistent file management
PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"
ENV_CONFIG_DIR="$PROJECT_ROOT/configs/environment"
SCRIPTS_CONFIG_DIR="$PROJECT_ROOT/scripts/config"
SCRIPTS_DIR="$PROJECT_ROOT/scripts"
SESSION_CORE_DIR="$PROJECT_ROOT/sessions/core"

log_info "Lucid Project Path Setup"
log_info "Project Root: $PROJECT_ROOT"
log_info "Environment Config Dir: $ENV_CONFIG_DIR"
log_info "Scripts Config Dir: $SCRIPTS_CONFIG_DIR"

# =============================================================================
# DIRECTORY VALIDATION AND CREATION
# =============================================================================
log_info "Validating and creating required directories..."

# Create project root if it doesn't exist
if [ ! -d "$PROJECT_ROOT" ]; then
    log_info "Creating project root directory: $PROJECT_ROOT"
    mkdir -p "$PROJECT_ROOT"
fi

# Create environment config directory if it doesn't exist
if [ ! -d "$ENV_CONFIG_DIR" ]; then
    log_info "Creating environment config directory: $ENV_CONFIG_DIR"
    mkdir -p "$ENV_CONFIG_DIR"
fi

# Create scripts config directory if it doesn't exist
if [ ! -d "$SCRIPTS_CONFIG_DIR" ]; then
    log_info "Creating scripts config directory: $SCRIPTS_CONFIG_DIR"
    mkdir -p "$SCRIPTS_CONFIG_DIR"
fi

# Create scripts directory if it doesn't exist
if [ ! -d "$SCRIPTS_DIR" ]; then
    log_info "Creating scripts directory: $SCRIPTS_DIR"
    mkdir -p "$SCRIPTS_DIR"
fi

# Create session core directory if it doesn't exist
if [ ! -d "$SESSION_CORE_DIR" ]; then
    log_info "Creating session core directory: $SESSION_CORE_DIR"
    mkdir -p "$SESSION_CORE_DIR"
fi

# =============================================================================
# CREATE GLOBAL PATH CONFIGURATION FILE
# =============================================================================
PATH_CONFIG_FILE="$SCRIPTS_CONFIG_DIR/lucid-paths.conf"
log_info "Creating global path configuration file: $PATH_CONFIG_FILE"

cat > "$PATH_CONFIG_FILE" << EOF
# Lucid Project Global Path Configuration
# Generated: $(date)
# This file contains global path variables for the Lucid project

# =============================================================================
# PROJECT STRUCTURE
# =============================================================================
PROJECT_ROOT="$PROJECT_ROOT"
ENV_CONFIG_DIR="$ENV_CONFIG_DIR"
SCRIPTS_CONFIG_DIR="$SCRIPTS_CONFIG_DIR"
SCRIPTS_DIR="$SCRIPTS_DIR"
SESSION_CORE_DIR="$SESSION_CORE_DIR"

# =============================================================================
# ENVIRONMENT FILES
# =============================================================================
# Session Core Environment Files
ENV_ORCHESTRATOR="$ENV_CONFIG_DIR/.env.orchestrator"
ENV_CHUNKER="$ENV_CONFIG_DIR/.env.chunker"
ENV_MERKLE_BUILDER="$ENV_CONFIG_DIR/.env.merkle_builder"
ENV_SESSIONS_SECRETS="$ENV_CONFIG_DIR/.env.sessions.secrets"

# =============================================================================
# SCRIPT PATHS
# =============================================================================
# Core Scripts
SCRIPT_GENERATE_ENV="$SESSION_CORE_DIR/generate-env.sh"
SCRIPT_SETUP_PATHS="$SCRIPTS_CONFIG_DIR/setup-paths.sh"

# =============================================================================
# DATA DIRECTORIES
# =============================================================================
DATA_DIR="/data"
SESSIONS_DATA_DIR="/data/sessions"
CHUNKS_DATA_DIR="/data/chunks"
MERKLE_DATA_DIR="/data/merkle"
LOGS_DATA_DIR="/data/logs"
TEMP_DATA_DIR="/tmp"

# =============================================================================
# USAGE INSTRUCTIONS
# =============================================================================
# To use these paths in other scripts:
# source "$PATH_CONFIG_FILE"
# echo "Project root: \$PROJECT_ROOT"
# echo "Environment config: \$ENV_CONFIG_DIR"
EOF

chmod 644 "$PATH_CONFIG_FILE"
log_success "Global path configuration saved to: $PATH_CONFIG_FILE"

# =============================================================================
# CREATE ENVIRONMENT FILE TEMPLATES
# =============================================================================
log_info "Creating environment file templates..."

# Create .env.secure template
SECURE_ENV_TEMPLATE="$ENV_CONFIG_DIR/.env.secure.template"
cat > "$SECURE_ENV_TEMPLATE" << 'EOF'
# Lucid Secure Environment Configuration Template
# Copy this file to .env.secure and fill in your secure values
# WARNING: Never commit .env.secure to version control!

# MongoDB Configuration
# MONGODB_PASSWORD=your_secure_mongodb_password_here

# Redis Configuration  
# REDIS_PASSWORD=your_secure_redis_password_here

# JWT Configuration
# JWT_SECRET_KEY=your_secure_jwt_secret_here

# Encryption Configuration
# ENCRYPTION_KEY=your_secure_encryption_key_here
EOF

# Create .env.application template
APPLICATION_ENV_TEMPLATE="$ENV_CONFIG_DIR/.env.application.template"
cat > "$APPLICATION_ENV_TEMPLATE" << 'EOF'
# Lucid Application Environment Configuration Template
# Copy this file to .env.application and configure your application settings

# Application Configuration
# LUCID_APP_NAME=Lucid
# LUCID_APP_VERSION=1.0.0
# LUCID_APP_ENVIRONMENT=production

# Network Configuration
# LUCID_NETWORK_HOST=0.0.0.0
# LUCID_NETWORK_PORT=8080

# Database Configuration
# LUCID_DB_HOST=localhost
# LUCID_DB_PORT=27017
# LUCID_DB_NAME=lucid
EOF

log_success "Environment templates created:"
log_success "  • $SECURE_ENV_TEMPLATE"
log_success "  • $APPLICATION_ENV_TEMPLATE"

# =============================================================================
# VALIDATION
# =============================================================================
log_info "Validating setup..."

# Check if all directories exist
for dir in "$PROJECT_ROOT" "$ENV_CONFIG_DIR" "$SCRIPTS_CONFIG_DIR" "$SCRIPTS_DIR" "$SESSION_CORE_DIR"; do
    if [ -d "$dir" ]; then
        log_success "Directory exists: $dir"
    else
        log_error "Directory missing: $dir"
        exit 1
    fi
done

# Check if path config file exists
if [ -f "$PATH_CONFIG_FILE" ]; then
    log_success "Path configuration file created: $PATH_CONFIG_FILE"
else
    log_error "Path configuration file not created: $PATH_CONFIG_FILE"
    exit 1
fi

echo ""
log_info "==================================================================="
log_info "Lucid Project Path Setup Complete!"
log_info "==================================================================="
echo ""
log_info "Project structure:"
log_info "  • Project Root        : $PROJECT_ROOT"
log_info "  • Environment Config  : $ENV_CONFIG_DIR"
log_info "  • Scripts Config      : $SCRIPTS_CONFIG_DIR"
log_info "  • Scripts Directory   : $SCRIPTS_DIR"
log_info "  • Session Core        : $SESSION_CORE_DIR"
echo ""
log_info "Configuration files:"
log_info "  • Path Configuration  : $PATH_CONFIG_FILE"
log_info "  • Secure Env Template : $SECURE_ENV_TEMPLATE"
log_info "  • Application Template: $APPLICATION_ENV_TEMPLATE"
echo ""
log_info "Next steps:"
log_info "  1. Copy .env.secure.template to .env.secure and configure"
log_info "  2. Copy .env.application.template to .env.application and configure"
log_info "  3. Run generate-env.sh to create session core environment files"
echo ""
log_success "Path setup complete!"
