#!/bin/bash
# Path: build/scripts/deploy-gui-pi.sh
# Deploy GUI services to Raspberry Pi
# Follows SPEC-1A and SPEC-5 Web-Based GUI Architecture

set -euo pipefail

# Default values
PI_HOST="${PI_HOST:-raspberrypi.local}"
PI_USER="${PI_USER:-pi}"
SERVICES="user,admin,node"
REGISTRY="ghcr.io"
IMAGE_NAME="HamiGames/Lucid"
TAG="latest"
DEPLOYMENT_TYPE="update"
FORCE_DEPLOY=false
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

Deploy GUI services to Raspberry Pi for Lucid RDP project.

OPTIONS:
    -h, --host HOST           Raspberry Pi hostname or IP (default: raspberrypi.local)
    -u, --user USER           SSH username (default: pi)
    -s, --services SERVICES   Comma-separated list of GUI services (default: user,admin,node)
    -r, --registry REGISTRY   Container registry (default: ghcr.io)
    -i, --image-name NAME     Image name prefix (default: HamiGames/Lucid)
    -t, --tag TAG             Image tag (default: latest)
    -d, --deployment TYPE     Deployment type: full, update, rollback (default: update)
    -f, --force               Force deployment even if no changes
    -v, --verbose             Verbose output
    --help                    Show this help message

EXAMPLES:
    # Deploy all GUI services
    $0

    # Deploy specific services
    $0 --services user,admin

    # Full deployment with custom host
    $0 --host 192.168.1.100 --deployment full

    # Rollback deployment
    $0 --deployment rollback

ENVIRONMENT VARIABLES:
    PI_HOST                   Raspberry Pi hostname or IP
    PI_USER                   SSH username
    GITHUB_TOKEN              GitHub token for registry authentication
    PI_SSH_KEY                Path to SSH private key

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--host)
                PI_HOST="$2"
                shift 2
                ;;
            -u|--user)
                PI_USER="$2"
                shift 2
                ;;
            -s|--services)
                SERVICES="$2"
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
            -d|--deployment)
                DEPLOYMENT_TYPE="$2"
                shift 2
                ;;
            -f|--force)
                FORCE_DEPLOY=true
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

# Setup SSH connection
setup_ssh() {
    log_info "Setting up SSH connection to $PI_USER@$PI_HOST..."
    
    # Check if SSH key is available
    local ssh_key=""
    if [[ -n "${PI_SSH_KEY:-}" ]]; then
        ssh_key="$PI_SSH_KEY"
    elif [[ -f "$HOME/.ssh/id_rsa" ]]; then
        ssh_key="$HOME/.ssh/id_rsa"
    elif [[ -f "$HOME/.ssh/id_ed25519" ]]; then
        ssh_key="$HOME/.ssh/id_ed25519"
    else
        log_error "No SSH key found. Please set PI_SSH_KEY or ensure ~/.ssh/id_rsa exists"
        exit 1
    fi
    
    # Test SSH connection
    log_info "Testing SSH connection..."
    if ssh -i "$ssh_key" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" "echo 'SSH connection successful'" >/dev/null 2>&1; then
        log_success "SSH connection established"
    else
        log_error "Failed to connect to $PI_USER@$PI_HOST"
        exit 1
    fi
    
    # Export SSH command for use in functions
    export SSH_CMD="ssh -i $ssh_key -o StrictHostKeyChecking=no $PI_USER@$PI_HOST"
}

# Check Pi prerequisites
check_pi_prerequisites() {
    log_info "Checking Pi prerequisites..."
    
    # Check if Docker is installed and running
    if ! $SSH_CMD "docker info >/dev/null 2>&1"; then
        log_error "Docker is not running on Pi"
        exit 1
    fi
    
    # Check if Docker Compose is available
    if ! $SSH_CMD "docker compose version >/dev/null 2>&1"; then
        log_error "Docker Compose is not available on Pi"
        exit 1
    fi
    
    # Check if Tor is running
    if ! $SSH_CMD "systemctl is-active --quiet tor"; then
        log_warn "Tor service is not running on Pi"
    fi
    
    # Check if required directories exist
    if ! $SSH_CMD "test -d /opt/lucid"; then
        log_info "Creating /opt/lucid directory..."
        $SSH_CMD "sudo mkdir -p /opt/lucid"
        $SSH_CMD "sudo chown $PI_USER:$PI_USER /opt/lucid"
    fi
    
    log_success "Pi prerequisites checked"
}

# Login to registry on Pi
login_to_registry() {
    log_info "Logging in to registry on Pi..."
    
    if [[ -n "${GITHUB_TOKEN:-}" ]]; then
        $SSH_CMD "echo '$GITHUB_TOKEN' | docker login $REGISTRY -u $GITHUB_ACTOR --password-stdin"
    else
        log_warn "No GITHUB_TOKEN provided, skipping registry login"
    fi
}

# Pull GUI images on Pi
pull_gui_images() {
    log_info "Pulling GUI images on Pi..."
    
    for service in $(echo "$SERVICES" | tr ',' ' '); do
        log_info "Pulling $service GUI image..."
        
        if $SSH_CMD "docker pull $REGISTRY/$IMAGE_NAME/$service-gui:$TAG"; then
            log_success "Pulled $service GUI image"
        else
            log_error "Failed to pull $service GUI image"
            exit 1
        fi
    done
}

# Backup current deployment
backup_current_deployment() {
    if [[ "$DEPLOYMENT_TYPE" == "rollback" ]]; then
        return 0
    fi
    
    log_info "Backing up current deployment..."
    
    local backup_dir="/opt/lucid/backups/backup-$(date +%Y%m%d-%H%M%S)"
    
    $SSH_CMD "mkdir -p $backup_dir"
    
    # Backup docker-compose files
    if $SSH_CMD "test -f /opt/lucid/docker-compose.yml"; then
        $SSH_CMD "cp /opt/lucid/docker-compose.yml $backup_dir/"
    fi
    
    # Backup configuration files
    if $SSH_CMD "test -d /opt/lucid/configs"; then
        $SSH_CMD "cp -r /opt/lucid/configs $backup_dir/"
    fi
    
    log_success "Backup created at $backup_dir"
}

# Deploy GUI services
deploy_gui_services() {
    log_info "Deploying GUI services..."
    
    # Copy docker-compose file if it doesn't exist
    if ! $SSH_CMD "test -f /opt/lucid/docker-compose.yml"; then
        log_info "Creating docker-compose.yml on Pi..."
        
        # Create basic docker-compose file for GUI services
        $SSH_CMD "cat > /opt/lucid/docker-compose.yml << 'EOF'
version: '3.8'

services:
  # User GUI
  lucid-user-gui:
    image: $REGISTRY/$IMAGE_NAME/user-gui:$TAG
    container_name: lucid-user-gui
    restart: unless-stopped
    ports:
      - \"3001:3001\"
    environment:
      - NODE_ENV=production
      - PORT=3001
      - TOR_SOCKS=127.0.0.1:9050
    networks:
      - lucid-gui-net
    profiles: [\"gui\", \"user\"]

  # Admin GUI
  lucid-admin-gui:
    image: $REGISTRY/$IMAGE_NAME/admin-gui:$TAG
    container_name: lucid-admin-gui
    restart: unless-stopped
    ports:
      - \"3002:3002\"
    environment:
      - NODE_ENV=production
      - PORT=3002
      - TOR_SOCKS=127.0.0.1:9050
    networks:
      - lucid-gui-net
    profiles: [\"gui\", \"admin\"]

  # Node GUI
  lucid-node-gui:
    image: $REGISTRY/$IMAGE_NAME/node-gui:$TAG
    container_name: lucid-node-gui
    restart: unless-stopped
    ports:
      - \"3003:3003\"
    environment:
      - NODE_ENV=production
      - PORT=3003
      - TOR_SOCKS=127.0.0.1:9050
    networks:
      - lucid-gui-net
    profiles: [\"gui\", \"node\"]

networks:
  lucid-gui-net:
    name: lucid-gui-net
    driver: bridge
    attachable: true
    ipam:
      config:
        - subnet: 172.21.0.0/16
          gateway: 172.21.0.1
EOF"
    fi
    
    # Update image tags in docker-compose file
    for service in $(echo "$SERVICES" | tr ',' ' '); do
        log_info "Updating $service GUI image tag..."
        $SSH_CMD "sed -i 's|image: $REGISTRY/$IMAGE_NAME/$service-gui:.*|image: $REGISTRY/$IMAGE_NAME/$service-gui:$TAG|' /opt/lucid/docker-compose.yml"
    done
    
    # Start GUI services
    log_info "Starting GUI services..."
    $SSH_CMD "cd /opt/lucid && docker compose --profile gui up -d"
    
    log_success "GUI services deployed"
}

# Setup Tor .onion services
setup_tor_onion_services() {
    log_info "Setting up Tor .onion services..."
    
    # Create Tor configuration for GUI services
    $SSH_CMD "sudo tee /etc/tor/torrc.d/lucid-gui.conf << 'EOF'
# Lucid GUI .onion services
HiddenServiceDir /var/lib/tor/lucid-user-gui
HiddenServicePort 80 127.0.0.1:3001

HiddenServiceDir /var/lib/tor/lucid-admin-gui
HiddenServicePort 80 127.0.0.1:3002

HiddenServiceDir /var/lib/tor/lucid-node-gui
HiddenServicePort 80 127.0.0.1:3003
EOF"
    
    # Restart Tor service
    $SSH_CMD "sudo systemctl restart tor"
    
    # Wait for .onion services to be ready
    log_info "Waiting for .onion services to be ready..."
    sleep 10
    
    # Display .onion URLs
    echo ""
    log_info "=== GUI .ONION URLs ==="
    
    for service in $(echo "$SERVICES" | tr ',' ' '); do
        local onion_file="/var/lib/tor/lucid-$service-gui/hostname"
        if $SSH_CMD "test -f $onion_file"; then
            local onion_url
            onion_url=$($SSH_CMD "cat $onion_file")
            log_success "$service GUI: https://$onion_url"
        else
            log_warn "$service GUI .onion service not ready"
        fi
    done
}

# Generate QR codes
generate_qr_codes() {
    log_info "Generating QR codes for GUI access..."
    
    # Install qrencode if not available
    $SSH_CMD "sudo apt-get update && sudo apt-get install -y qrencode" || true
    
    # Create QR code generation script
    $SSH_CMD "cat > /usr/local/bin/lucid-gui-qr.sh << 'EOF'
#!/bin/bash
set -euo pipefail

echo \"=== Lucid RDP GUI Access ===\"
echo \"\"

for service in user admin node; do
    onion_file=\"/var/lib/tor/lucid-\$service-gui/hostname\"
    if [ -f \"\$onion_file\" ]; then
        onion_url=\$(cat \"\$onion_file\")
        case \"\$service\" in
            user)
                echo \"User GUI (End Users):\"
                ;;
            admin)
                echo \"Admin GUI (Operators):\"
                ;;
            node)
                echo \"Node GUI (Node Workers):\"
                ;;
        esac
        echo \"https://\$onion_url\"
        qrencode -t ANSI256 \"https://\$onion_url\" || echo \"QR code generation failed\"
        echo \"\"
    fi
done
EOF"
    
    $SSH_CMD "chmod +x /usr/local/bin/lucid-gui-qr.sh"
    
    # Display QR codes
    $SSH_CMD "/usr/local/bin/lucid-gui-qr.sh"
}

# Create systemd service for auto-start
create_systemd_service() {
    log_info "Creating systemd service for auto-start..."
    
    $SSH_CMD "sudo tee /etc/systemd/system/lucid-gui.service << 'EOF'
[Unit]
Description=Lucid GUI Services
After=docker.service tor.service
Requires=docker.service tor.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/lucid-gui-start.sh
RemainAfterExit=yes
User=pi
Group=pi

[Install]
WantedBy=multi-user.target
EOF"
    
    # Create startup script
    $SSH_CMD "cat > /usr/local/bin/lucid-gui-start.sh << 'EOF'
#!/bin/bash
set -euo pipefail

# Wait for Docker and Tor
until docker info >/dev/null 2>&1; do sleep 1; done
until nc -z localhost 9050; do sleep 1; done

# Start GUI services
cd /opt/lucid
docker compose --profile gui up -d

# Display QR codes
/usr/local/bin/lucid-gui-qr.sh
EOF"
    
    $SSH_CMD "chmod +x /usr/local/bin/lucid-gui-start.sh"
    $SSH_CMD "sudo systemctl enable lucid-gui.service"
    
    log_success "Systemd service created and enabled"
}

# Create desktop shortcuts
create_desktop_shortcuts() {
    log_info "Creating desktop shortcuts..."
    
    for service in $(echo "$SERVICES" | tr ',' ' '); do
        local service_name=""
        case "$service" in
            user)
                service_name="User"
                ;;
            admin)
                service_name="Admin"
                ;;
            node)
                service_name="Node"
                ;;
        esac
        
        $SSH_CMD "cat > /home/$PI_USER/Desktop/lucid-$service-gui.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Lucid $service_name GUI
Comment=Access Lucid RDP $service_name Interface
Exec=xdg-open https://\$(cat /var/lib/tor/lucid-$service-gui/hostname)
Icon=lucid-$service
Terminal=false
Categories=Network;RemoteAccess;
EOF"
        
        $SSH_CMD "chmod +x /home/$PI_USER/Desktop/lucid-$service-gui.desktop"
    done
    
    log_success "Desktop shortcuts created"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check if services are running
    for service in $(echo "$SERVICES" | tr ',' ' '); do
        if $SSH_CMD "docker ps --format '{{.Names}}' | grep -q 'lucid-$service-gui'"; then
            log_success "$service GUI service is running"
        else
            log_error "$service GUI service is not running"
            return 1
        fi
    done
    
    # Check .onion services
    for service in $(echo "$SERVICES" | tr ',' ' '); do
        local onion_file="/var/lib/tor/lucid-$service-gui/hostname"
        if $SSH_CMD "test -f $onion_file"; then
            local onion_url
            onion_url=$($SSH_CMD "cat $onion_file")
            log_success "$service GUI .onion service: $onion_url"
        else
            log_warn "$service GUI .onion service not found"
        fi
    done
    
    log_success "Deployment verification completed"
}

# Rollback deployment
rollback_deployment() {
    log_info "Rolling back deployment..."
    
    # Find the most recent backup
    local latest_backup
    latest_backup=$($SSH_CMD "ls -t /opt/lucid/backups/ 2>/dev/null | head -1" || echo "")
    
    if [[ -z "$latest_backup" ]]; then
        log_error "No backup found for rollback"
        exit 1
    fi
    
    log_info "Rolling back to: $latest_backup"
    
    # Stop current services
    $SSH_CMD "cd /opt/lucid && docker compose --profile gui down" || true
    
    # Restore from backup
    $SSH_CMD "cp /opt/lucid/backups/$latest_backup/docker-compose.yml /opt/lucid/" || true
    
    # Start services with previous configuration
    $SSH_CMD "cd /opt/lucid && docker compose --profile gui up -d"
    
    log_success "Rollback completed"
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
    
    log_info "Starting GUI deployment to Pi..."
    log_info "Host: $PI_HOST"
    log_info "User: $PI_USER"
    log_info "Services: $SERVICES"
    log_info "Deployment Type: $DEPLOYMENT_TYPE"
    log_info "Force Deploy: $FORCE_DEPLOY"
    log_info "Verbose: $VERBOSE"
    
    # Setup SSH connection
    setup_ssh
    
    # Check Pi prerequisites
    check_pi_prerequisites
    
    # Handle rollback
    if [[ "$DEPLOYMENT_TYPE" == "rollback" ]]; then
        rollback_deployment
        verify_deployment
        exit 0
    fi
    
    # Login to registry
    login_to_registry
    
    # Backup current deployment
    backup_current_deployment
    
    # Pull images
    pull_gui_images
    
    # Deploy services
    deploy_gui_services
    
    # Setup Tor .onion services
    setup_tor_onion_services
    
    # Create systemd service
    create_systemd_service
    
    # Create desktop shortcuts
    create_desktop_shortcuts
    
    # Generate QR codes
    generate_qr_codes
    
    # Verify deployment
    verify_deployment
    
    log_success "GUI deployment completed successfully!"
    
    echo ""
    log_info "=== DEPLOYMENT SUMMARY ==="
    log_info "Services deployed: $SERVICES"
    log_info "Registry: $REGISTRY"
    log_info "Image tag: $TAG"
    log_info "Auto-start: Enabled"
    log_info "QR codes: Generated"
    log_info "Desktop shortcuts: Created"
}

# Run main function with all arguments
main "$@"
