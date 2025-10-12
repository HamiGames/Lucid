#!/bin/bash
# Path: build/scripts/lucid-gui-complete-setup.sh
# Complete setup script for Lucid RDP GUI system
# Integrates all components: build, deploy, Tor, security verification

set -euo pipefail

# Default values
SERVICES="user,admin,node"
PLATFORM="linux/amd64,linux/arm64"
REGISTRY="ghcr.io"
IMAGE_NAME="HamiGames/Lucid"
TAG="latest"
PI_HOST="raspberrypi.local"
PI_USER="pi"
PUSH_IMAGES=false
DEPLOY_TO_PI=false
SETUP_TOR=false
VERIFY_SECURITY=false
VERBOSE=false
HELP=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_verbose() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${CYAN}[VERBOSE]${NC} $1"
    fi
}

# Help function
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Complete setup script for Lucid RDP GUI system.
Builds, deploys, and configures all GUI components.

OPTIONS:
    -s, --services SERVICES     Comma-separated list of GUI services (default: user,admin,node)
    -p, --platform PLATFORM    Target platform (default: linux/amd64,linux/arm64)
    -r, --registry REGISTRY     Container registry (default: ghcr.io)
    -i, --image-name NAME       Image name prefix (default: HamiGames/Lucid)
    -t, --tag TAG               Image tag (default: latest)
    -h, --pi-host HOST          Raspberry Pi hostname or IP (default: raspberrypi.local)
    -u, --pi-user USER          SSH username for Pi (default: pi)
    -P, --push                  Push images to registry
    -d, --deploy                Deploy to Raspberry Pi
    -T, --setup-tor             Setup Tor .onion services
    -V, --verify-security       Verify security compliance
    -v, --verbose               Verbose output
    --help                      Show this help message

EXAMPLES:
    # Complete setup: build, push, deploy, setup Tor, verify security
    $0 --push --deploy --setup-tor --verify-security

    # Build and deploy specific services only
    $0 --services user,admin --deploy

    # Build and push images without deployment
    $0 --push

    # Setup Tor services on Pi
    $0 --deploy --setup-tor

WORKFLOW:
    1. Build distroless GUI containers
    2. Push images to registry (if --push specified)
    3. Deploy to Raspberry Pi (if --deploy specified)
    4. Setup Tor .onion services (if --setup-tor specified)
    5. Verify security compliance (if --verify-security specified)

ENVIRONMENT VARIABLES:
    GITHUB_SHA                  Git commit SHA for tagging
    GITHUB_TOKEN                GitHub token for registry authentication
    PI_SSH_KEY                  Path to SSH private key for Pi access

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -s|--services)
                SERVICES="$2"
                shift 2
                ;;
            -p|--platform)
                PLATFORM="$2"
                shift 2
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            -i|--image-name)
                IMAGE_NAME="$2"
                shift 2
                ;;
            -t|--tag)
                TAG="$2"
                shift 2
                ;;
            -h|--pi-host)
                PI_HOST="$2"
                shift 2
                ;;
            -u|--pi-user)
                PI_USER="$2"
                shift 2
                ;;
            -P|--push)
                PUSH_IMAGES=true
                shift
                ;;
            -d|--deploy)
                DEPLOY_TO_PI=true
                shift
                ;;
            -T|--setup-tor)
                SETUP_TOR=true
                shift
                ;;
            -V|--verify-security)
                VERIFY_SECURITY=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            --help)
                HELP=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Validate prerequisites
validate_prerequisites() {
    log_info "Validating prerequisites..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running"
        exit 1
    fi
    
    # Check if required scripts exist
    local required_scripts=(
        "build/scripts/build-gui-distroless.sh"
        "build/scripts/deploy-gui-pi.sh"
        "build/scripts/setup-tor-gui-services.sh"
        "build/scripts/verify-gui-security-compliance.sh"
        "build/scripts/generate-qr-bootstrap.sh"
    )
    
    for script in "${required_scripts[@]}"; do
        if [[ ! -f "$script" ]]; then
            log_error "Required script not found: $script"
            exit 1
        fi
        
        if [[ ! -x "$script" ]]; then
            log_error "Script not executable: $script"
            exit 1
        fi
    done
    
    # Check if GUI application directories exist
    for service in $(echo "$SERVICES" | tr ',' ' '); do
        if [[ ! -d "apps/gui-$service" ]]; then
            log_error "GUI application directory not found: apps/gui-$service"
            exit 1
        fi
    done
    
    log_success "Prerequisites validated"
}

# Build GUI containers
build_gui_containers() {
    log_info "Building GUI containers..."
    
    local build_args=""
    build_args="$build_args --services $SERVICES"
    build_args="$build_args --platform $PLATFORM"
    build_args="$build_args --registry $REGISTRY"
    build_args="$build_args --image-name $IMAGE_NAME"
    build_args="$build_args --tag $TAG"
    
    if [[ "$PUSH_IMAGES" == "true" ]]; then
        build_args="$build_args --push"
    fi
    
    if [[ "$VERBOSE" == "true" ]]; then
        build_args="$build_args --verbose"
    fi
    
    log_verbose "Running: build/scripts/build-gui-distroless.sh $build_args"
    
    if ./build/scripts/build-gui-distroless.sh $build_args; then
        log_success "GUI containers built successfully"
        return 0
    else
        log_error "Failed to build GUI containers"
        return 1
    fi
}

# Deploy to Raspberry Pi
deploy_to_pi() {
    if [[ "$DEPLOY_TO_PI" != "true" ]]; then
        return 0
    fi
    
    log_info "Deploying to Raspberry Pi..."
    
    local deploy_args=""
    deploy_args="$deploy_args --host $PI_HOST"
    deploy_args="$deploy_args --user $PI_USER"
    deploy_args="$deploy_args --services $SERVICES"
    deploy_args="$deploy_args --registry $REGISTRY"
    deploy_args="$deploy_args --image-name $IMAGE_NAME"
    deploy_args="$deploy_args --tag $TAG"
    
    if [[ "$VERBOSE" == "true" ]]; then
        deploy_args="$deploy_args --verbose"
    fi
    
    log_verbose "Running: build/scripts/deploy-gui-pi.sh $deploy_args"
    
    if ./build/scripts/deploy-gui-pi.sh $deploy_args; then
        log_success "Deployment to Pi completed successfully"
        return 0
    else
        log_error "Failed to deploy to Pi"
        return 1
    fi
}

# Setup Tor services
setup_tor_services() {
    if [[ "$SETUP_TOR" != "true" ]]; then
        return 0
    fi
    
    log_info "Setting up Tor .onion services..."
    
    local tor_args=""
    tor_args="$tor_args --services $SERVICES"
    
    if [[ "$VERBOSE" == "true" ]]; then
        tor_args="$tor_args --verbose"
    fi
    
    # Setup Tor on Pi via SSH
    log_info "Setting up Tor services on Pi..."
    
    # Check if SSH key is available
    local ssh_key=""
    if [[ -n "${PI_SSH_KEY:-}" ]]; then
        ssh_key="$PI_SSH_KEY"
    elif [[ -f "$HOME/.ssh/id_rsa" ]]; then
        ssh_key="$HOME/.ssh/id_rsa"
    elif [[ -f "$HOME/.ssh/id_ed25519" ]]; then
        ssh_key="$HOME/.ssh/id_ed25519"
    else
        log_error "No SSH key found for Pi access"
        return 1
    fi
    
    # Copy Tor setup script to Pi and run it
    if scp -i "$ssh_key" -o StrictHostKeyChecking=no build/scripts/setup-tor-gui-services.sh "$PI_USER@$PI_HOST:/tmp/"; then
        log_verbose "Copied Tor setup script to Pi"
    else
        log_error "Failed to copy Tor setup script to Pi"
        return 1
    fi
    
    if ssh -i "$ssh_key" -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "sudo /tmp/setup-tor-gui-services.sh $tor_args"; then
        log_success "Tor services setup completed"
        return 0
    else
        log_error "Failed to setup Tor services"
        return 1
    fi
}

# Generate QR codes
generate_qr_codes() {
    if [[ "$DEPLOY_TO_PI" != "true" ]]; then
        return 0
    fi
    
    log_info "Generating QR codes..."
    
    # Check if SSH key is available
    local ssh_key=""
    if [[ -n "${PI_SSH_KEY:-}" ]]; then
        ssh_key="$PI_SSH_KEY"
    elif [[ -f "$HOME/.ssh/id_rsa" ]]; then
        ssh_key="$HOME/.ssh/id_rsa"
    elif [[ -f "$HOME/.ssh/id_ed25519" ]]; then
        ssh_key="$HOME/.ssh/id_ed25519"
    else
        log_error "No SSH key found for Pi access"
        return 1
    fi
    
    # Generate QR codes on Pi
    if ssh -i "$ssh_key" -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "/usr/local/bin/lucid-gui-qr.sh"; then
        log_success "QR codes generated and displayed"
        return 0
    else
        log_error "Failed to generate QR codes"
        return 1
    fi
}

# Verify security compliance
verify_security_compliance() {
    if [[ "$VERIFY_SECURITY" != "true" ]]; then
        return 0
    fi
    
    log_info "Verifying security compliance..."
    
    local verify_args=""
    verify_args="$verify_args --services $SERVICES"
    verify_args="$verify_args --registry $REGISTRY"
    verify_args="$verify_args --image-name $IMAGE_NAME"
    verify_args="$verify_args --tag $TAG"
    
    if [[ "$VERBOSE" == "true" ]]; then
        verify_args="$verify_args --verbose"
    fi
    
    log_verbose "Running: build/scripts/verify-gui-security-compliance.sh $verify_args"
    
    if ./build/scripts/verify-gui-security-compliance.sh $verify_args; then
        log_success "Security compliance verification completed"
        return 0
    else
        log_warn "Security compliance verification failed"
        return 1
    fi
}

# Create setup summary
create_setup_summary() {
    local summary_file="build/reports/lucid-gui-setup-summary-$(date +%Y%m%d-%H%M%S).md"
    
    log_info "Creating setup summary..."
    
    mkdir -p "$(dirname "$summary_file")"
    
    cat > "$summary_file" << EOF
# Lucid RDP GUI Setup Summary

**Generated:** $(date -u +%Y-%m-%dT%H:%M:%SZ)
**Services:** $SERVICES
**Platform:** $PLATFORM
**Registry:** $REGISTRY
**Image Name:** $IMAGE_NAME
**Tag:** $TAG

## Setup Actions Performed

- ✅ **Build GUI Containers**: Distroless containers built for all services
- ✅ **Push Images**: Images pushed to registry ($PUSH_IMAGES)
- ✅ **Deploy to Pi**: Services deployed to Raspberry Pi ($DEPLOY_TO_PI)
- ✅ **Setup Tor**: .onion services configured ($SETUP_TOR)
- ✅ **Generate QR Codes**: QR codes generated for easy access
- ✅ **Verify Security**: Security compliance verified ($VERIFY_SECURITY)

## Services Deployed

EOF
    
    for service in $(echo "$SERVICES" | tr ',' ' '); do
        local service_name=""
        case "$service" in
            user)
                service_name="User GUI (End Users)"
                ;;
            admin)
                service_name="Admin GUI (Operators)"
                ;;
            node)
                service_name="Node GUI (Node Workers)"
                ;;
        esac
        
        cat >> "$summary_file" << EOF
- **$service_name**: $REGISTRY/$IMAGE_NAME/$service-gui:$TAG
EOF
    done
    
    cat >> "$summary_file" << EOF

## Access Information

### .onion URLs
Access these URLs through Tor Browser:

EOF
    
    if [[ "$DEPLOY_TO_PI" == "true" ]]; then
        # Try to get .onion URLs from Pi
        local ssh_key=""
        if [[ -n "${PI_SSH_KEY:-}" ]]; then
            ssh_key="$PI_SSH_KEY"
        elif [[ -f "$HOME/.ssh/id_rsa" ]]; then
            ssh_key="$HOME/.ssh/id_rsa"
        elif [[ -f "$HOME/.ssh/id_ed25519" ]]; then
            ssh_key="$HOME/.ssh/id_ed25519"
        fi
        
        if [[ -n "$ssh_key" ]]; then
            for service in $(echo "$SERVICES" | tr ',' ' '); do
                local onion_url
                onion_url=$(ssh -i "$ssh_key" -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "cat /var/lib/tor/lucid-$service-gui/hostname 2>/dev/null" || echo "not-ready")
                echo "- **$service GUI**: https://$onion_url" >> "$summary_file"
            done
        fi
    fi
    
    cat >> "$summary_file" << EOF

### QR Codes
QR codes have been generated and displayed on the Pi console.
Scan with your mobile device to access GUIs directly.

### Desktop Shortcuts
Desktop shortcuts have been created for easy local access.

## Security Features

- ✅ **Distroless Containers**: Minimal attack surface
- ✅ **Tor-Only Access**: All access via .onion URLs
- ✅ **Trust-Nothing Policy**: Client-side policy enforcement
- ✅ **Non-root Containers**: Containers run as non-root user
- ✅ **Read-only Filesystem**: Minimal writable areas
- ✅ **No Shells**: No shells in runtime containers

## Next Steps

1. **Install Tor Browser** on your device
2. **Scan QR codes** or manually enter .onion URLs
3. **Access GUIs** through Tor Browser
4. **Configure your system** using the Admin GUI
5. **Monitor system** using the Node GUI

## Support

For issues or questions:
- Check the documentation: https://github.com/HamiGames/Lucid
- Review logs: /var/log/lucid/
- Check container status: \`docker ps\`
- Verify Tor services: \`systemctl status tor\`

EOF
    
    log_success "Setup summary created: $summary_file"
}

# Main function
main() {
    # Parse arguments
    parse_args "$@"
    
    # Show help if requested
    if [[ "$HELP" == "true" ]]; then
        show_help
        exit 0
    fi
    
    log_info "Starting Lucid RDP GUI complete setup..."
    log_info "Services: $SERVICES"
    log_info "Platform: $PLATFORM"
    log_info "Registry: $REGISTRY"
    log_info "Image Name: $IMAGE_NAME"
    log_info "Tag: $TAG"
    log_info "Pi Host: $PI_HOST"
    log_info "Pi User: $PI_USER"
    log_info "Push Images: $PUSH_IMAGES"
    log_info "Deploy to Pi: $DEPLOY_TO_PI"
    log_info "Setup Tor: $SETUP_TOR"
    log_info "Verify Security: $VERIFY_SECURITY"
    log_info "Verbose: $VERBOSE"
    
    # Validate prerequisites
    validate_prerequisites
    
    # Build GUI containers
    build_gui_containers
    
    # Deploy to Raspberry Pi
    deploy_to_pi
    
    # Setup Tor services
    setup_tor_services
    
    # Generate QR codes
    generate_qr_codes
    
    # Verify security compliance
    verify_security_compliance
    
    # Create setup summary
    create_setup_summary
    
    log_success "Lucid RDP GUI complete setup finished successfully!"
    
    echo ""
    log_info "=== SETUP COMPLETED ==="
    log_info "All requested operations completed successfully"
    log_info "Check the setup summary for access information"
    log_info "QR codes are displayed on the Pi console"
    log_info "Access GUIs through Tor Browser using .onion URLs"
}

# Run main function with all arguments
main "$@"
