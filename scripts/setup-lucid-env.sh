#!/bin/bash
# Path: scripts/setup-lucid-env.sh
# Master script to setup Lucid project environment
# Runs path setup and generates all environment files

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

log_info "Lucid Environment Setup Master Script"
log_info "Project Root: $PROJECT_ROOT"

# =============================================================================
# STEP 1: SETUP PATHS
# =============================================================================
log_info "Step 1: Setting up project paths..."

# Check if setup-paths.sh exists
SETUP_PATHS_SCRIPT="$SCRIPTS_CONFIG_DIR/setup-paths.sh"
if [ -f "$SETUP_PATHS_SCRIPT" ]; then
    log_info "Running path setup script: $SETUP_PATHS_SCRIPT"
    bash "$SETUP_PATHS_SCRIPT"
    if [ $? -eq 0 ]; then
        log_success "Path setup completed successfully"
    else
        log_error "Path setup failed"
        exit 1
    fi
else
    log_warning "Path setup script not found: $SETUP_PATHS_SCRIPT"
    log_info "Creating directories manually..."
    
    # Create directories manually
    mkdir -p "$PROJECT_ROOT"
    mkdir -p "$ENV_CONFIG_DIR"
    mkdir -p "$SCRIPTS_CONFIG_DIR"
    mkdir -p "$SCRIPTS_DIR"
    mkdir -p "$SESSION_CORE_DIR"
    
    log_success "Directories created manually"
fi

# =============================================================================
# STEP 2: LOAD PATH CONFIGURATION
# =============================================================================
log_info "Step 2: Loading path configuration..."

PATH_CONFIG_FILE="$SCRIPTS_CONFIG_DIR/lucid-paths.conf"
if [ -f "$PATH_CONFIG_FILE" ]; then
    log_info "Loading path configuration from: $PATH_CONFIG_FILE"
    source "$PATH_CONFIG_FILE"
    log_success "Path configuration loaded"
else
    log_warning "Path configuration file not found: $PATH_CONFIG_FILE"
    log_info "Using default paths..."
fi

# =============================================================================
# STEP 3: GENERATE ENVIRONMENT FILES
# =============================================================================
log_info "Step 3: Generating environment files..."

# Check if generate-env.sh exists
GENERATE_ENV_SCRIPT="$SESSION_CORE_DIR/generate-env.sh"
if [ -f "$GENERATE_ENV_SCRIPT" ]; then
    log_info "Running environment generation script: $GENERATE_ENV_SCRIPT"
    bash "$GENERATE_ENV_SCRIPT"
    if [ $? -eq 0 ]; then
        log_success "Environment files generated successfully"
    else
        log_error "Environment generation failed"
        exit 1
    fi
else
    log_error "Environment generation script not found: $GENERATE_ENV_SCRIPT"
    exit 1
fi

# =============================================================================
# STEP 4: VALIDATION
# =============================================================================
log_info "Step 4: Validating generated files..."

# Check if all environment files exist
ENV_FILES=(
    "$ENV_CONFIG_DIR/.env.orchestrator"
    "$ENV_CONFIG_DIR/.env.chunker"
    "$ENV_CONFIG_DIR/.env.merkle_builder"
    "$ENV_CONFIG_DIR/.env.sessions.secrets"
)

all_files_exist=true
for env_file in "${ENV_FILES[@]}"; do
    if [ -f "$env_file" ]; then
        log_success "Environment file exists: $env_file"
    else
        log_error "Environment file missing: $env_file"
        all_files_exist=false
    fi
done

if [ "$all_files_exist" = true ]; then
    log_success "All environment files generated successfully"
else
    log_error "Some environment files are missing"
    exit 1
fi

# =============================================================================
# STEP 5: SUMMARY
# =============================================================================
echo ""
log_info "==================================================================="
log_info "Lucid Environment Setup Complete!"
log_info "==================================================================="
echo ""
log_info "Project structure:"
log_info "  • Project Root        : $PROJECT_ROOT"
log_info "  • Environment Config  : $ENV_CONFIG_DIR"
log_info "  • Scripts Config      : $SCRIPTS_CONFIG_DIR"
echo ""
log_info "Generated environment files:"
for env_file in "${ENV_FILES[@]}"; do
    if [ -f "$env_file" ]; then
        log_info "  • $(basename "$env_file") : $env_file"
    fi
done
echo ""
log_info "Configuration files:"
log_info "  • Path Configuration  : $PATH_CONFIG_FILE"
log_info "  • Secure Env Template  : $ENV_CONFIG_DIR/.env.secure.template"
log_info "  • Application Template : $ENV_CONFIG_DIR/.env.application.template"
echo ""
log_warning "SECURITY NOTICE:"
log_warning "  • Review and configure .env.secure and .env.application templates"
log_warning "  • Keep .env.sessions.secrets file secure (chmod 600)"
log_warning "  • Never commit .env.sessions.secrets to version control"
log_warning "  • Backup secrets file to secure location"
echo ""
log_success "Lucid environment setup complete!"
