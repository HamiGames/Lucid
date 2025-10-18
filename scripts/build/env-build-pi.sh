#!/bin/bash

# Lucid Raspberry Pi Environment Build Script
# Generates SSH keys and configuration for Pi deployment
# Usage: ./env-build-pi.sh [generate-keys|setup-config|validate]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LUCID_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
PI_CONFIG_DIR="$LUCID_ROOT/configs/pi"
SSH_KEY_DIR="$PI_CONFIG_DIR/ssh"
ENV_FILE="$PI_CONFIG_DIR/.env"

# Pi deployment configuration
PI_HOST="${PI_HOST:-192.168.0.75}"
PI_USER="${PI_USER:-pickme}"
PI_SSH_KEY_NAME="${PI_SSH_KEY_NAME:-lucid_pi_key}"
PI_SSH_KEY_PATH="$SSH_KEY_DIR/$PI_SSH_KEY_NAME"

# Logging functions
log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create necessary directories
setup_directories() {
    log "Setting up Pi configuration directories..."
    
    mkdir -p "$PI_CONFIG_DIR"
    mkdir -p "$SSH_KEY_DIR"
    
    success "Directories created: $PI_CONFIG_DIR"
}

# Generate SSH key pair for Pi deployment
generate_ssh_keys() {
    log "Generating SSH key pair for Pi deployment..."
    
    if [[ -f "$PI_SSH_KEY_PATH" ]]; then
        warn "SSH key already exists: $PI_SSH_KEY_PATH"
        read -p "Do you want to regenerate it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Using existing SSH key"
            return 0
        fi
        rm -f "$PI_SSH_KEY_PATH" "$PI_SSH_KEY_PATH.pub"
    fi
    
    # Generate SSH key pair
    ssh-keygen -t ed25519 \
        -f "$PI_SSH_KEY_PATH" \
        -C "lucid-pi-deployment-$(date +%Y%m%d)" \
        -N "" \
        -q
    
    # Set proper permissions
    chmod 600 "$PI_SSH_KEY_PATH"
    chmod 644 "$PI_SSH_KEY_PATH.pub"
    
    success "SSH key pair generated:"
    success "  Private key: $PI_SSH_KEY_PATH"
    success "  Public key:  $PI_SSH_KEY_PATH.pub"
    
    # Display public key for manual copying to Pi
    echo
    log "Public key content (copy this to your Pi's ~/.ssh/authorized_keys):"
    echo "----------------------------------------"
    cat "$PI_SSH_KEY_PATH.pub"
    echo "----------------------------------------"
    echo
    warn "IMPORTANT: Copy the public key above to your Pi's ~/.ssh/authorized_keys file"
    warn "Run this command on your Pi:"
    warn "  echo '$(cat "$PI_SSH_KEY_PATH.pub")' >> ~/.ssh/authorized_keys"
    warn "  chmod 600 ~/.ssh/authorized_keys"
}

# Create environment configuration file
create_env_config() {
    log "Creating Pi environment configuration..."
    
    # Get the private key content (base64 encoded for GitHub secrets)
    if [[ ! -f "$PI_SSH_KEY_PATH" ]]; then
        error "SSH private key not found: $PI_SSH_KEY_PATH"
        error "Run with 'generate-keys' first"
        exit 1
    fi
    
    # Generate base64 encoded private key for GitHub secrets
    PI_SSH_KEY_B64=$(base64 -w 0 "$PI_SSH_KEY_PATH")
    
    cat > "$ENV_FILE" << EOF
# Lucid Pi Deployment Environment Configuration
# Generated on: $(date)
# 
# This file contains environment variables for Pi deployment
# Copy the values to your GitHub repository secrets

# Pi Connection Configuration
PI_HOST=$PI_HOST
PI_USER=$PI_USER

# SSH Key Configuration (Base64 encoded for GitHub secrets)
PI_SSH_KEY_B64=$PI_SSH_KEY_B64

# Deployment Configuration
LUCID_ENV=pi
LUCID_PLANE=ops
CLUSTER_ID=pi-core

# Database Configuration
MONGO_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin&retryWrites=false

# Registry Configuration
REGISTRY=ghcr.io
IMAGE_NAME=HamiGames/Lucid

# Service Configuration
SERVICES=gui,blockchain,rdp,node,storage,database,vm
EOF

    success "Environment configuration created: $ENV_FILE"
    
    # Create GitHub secrets instructions
    cat > "$PI_CONFIG_DIR/github-secrets-instructions.md" << EOF
# GitHub Secrets Configuration

To configure the GitHub Actions workflow for Pi deployment, add these secrets to your repository:

## Required Secrets

1. **PI_SSH_KEY**: The private SSH key for Pi access
   - Value: \`$PI_SSH_KEY_B64\`
   - Description: Base64 encoded private SSH key for Pi deployment

2. **PI_USER**: The SSH username for Pi access
   - Value: \`$PI_USER\`
   - Description: SSH username for Raspberry Pi

## How to Add Secrets

1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add each secret with the values above

## Verification

After adding the secrets, the deploy-pi.yml workflow should be able to:
- Connect to your Pi via SSH
- Deploy Docker containers
- Run health checks
- Perform rollbacks if needed

## Security Notes

- Keep the private key secure
- Never commit private keys to the repository
- Rotate keys periodically
- Use key-based authentication only (disable password auth on Pi)
EOF

    success "GitHub secrets instructions created: $PI_CONFIG_DIR/github-secrets-instructions.md"
}

# Validate SSH connection to Pi
validate_pi_connection() {
    log "Validating SSH connection to Pi..."
    
    if [[ ! -f "$PI_SSH_KEY_PATH" ]]; then
        error "SSH private key not found: $PI_SSH_KEY_PATH"
        error "Run with 'generate-keys' first"
        exit 1
    fi
    
    # Test SSH connection
    log "Testing SSH connection to $PI_USER@$PI_HOST..."
    if ssh -i "$PI_SSH_KEY_PATH" \
           -o ConnectTimeout=10 \
           -o StrictHostKeyChecking=no \
           -o BatchMode=yes \
           "$PI_USER@$PI_HOST" "echo 'SSH connection successful'" 2>/dev/null; then
        success "✅ SSH connection to Pi verified"
        
        # Check Pi system info
        log "Checking Pi system information..."
        PI_ARCH=$(ssh -i "$PI_SSH_KEY_PATH" -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "uname -m")
        PI_OS=$(ssh -i "$PI_SSH_KEY_PATH" -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2" | tr -d '"')
        
        log "Pi Architecture: $PI_ARCH"
        log "Pi OS: $PI_OS"
        
        # Check Docker
        if ssh -i "$PI_SSH_KEY_PATH" -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "docker --version" >/dev/null 2>&1; then
            success "✅ Docker is installed on Pi"
        else
            warn "⚠️ Docker not found on Pi - deployment may fail"
        fi
        
        # Check available disk space
        DISK_USAGE=$(ssh -i "$PI_SSH_KEY_PATH" -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "df -h / | tail -1 | awk '{print \$5}' | sed 's/%//'")
        log "Pi disk usage: ${DISK_USAGE}%"
        
        if [[ $DISK_USAGE -gt 80 ]]; then
            warn "⚠️ Pi disk usage is high (${DISK_USAGE}%)"
        else
            success "✅ Pi has sufficient disk space"
        fi
        
    else
        error "❌ Cannot connect to Pi via SSH"
        error "Please ensure:"
        error "  - Pi is powered on and connected to network"
        error "  - SSH key is properly configured on Pi"
        error "  - Network connectivity to $PI_HOST exists"
        error "  - Public key is in Pi's ~/.ssh/authorized_keys"
        exit 1
    fi
}

# Display usage information
usage() {
    echo "Lucid Pi Environment Build Script"
    echo
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  generate-keys    Generate SSH key pair for Pi deployment"
    echo "  setup-config     Create environment configuration files"
    echo "  validate         Test SSH connection to Pi"
    echo "  all              Run all steps (generate keys, setup config, validate)"
    echo "  help             Show this help message"
    echo
    echo "Environment variables:"
    echo "  PI_HOST          Pi hostname or IP (default: 192.168.0.75)"
    echo "  PI_USER          SSH username (default: pickme)"
    echo "  PI_SSH_KEY_NAME  SSH key filename (default: lucid_pi_key)"
    echo
    echo "Examples:"
    echo "  $0 generate-keys"
    echo "  PI_HOST=raspberrypi.local $0 validate"
    echo "  $0 all"
}

# Main execution
main() {
    case "${1:-help}" in
        generate-keys)
            setup_directories
            generate_ssh_keys
            ;;
        setup-config)
            setup_directories
            create_env_config
            ;;
        validate)
            validate_pi_connection
            ;;
        all)
            setup_directories
            generate_ssh_keys
            create_env_config
            validate_pi_connection
            success "🎉 Pi environment setup completed successfully!"
            echo
            log "Next steps:"
            log "1. Copy the public key to your Pi's ~/.ssh/authorized_keys"
            log "2. Add the secrets to your GitHub repository"
            log "3. Test the deployment workflow"
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            error "Unknown command: $1"
            echo
            usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
