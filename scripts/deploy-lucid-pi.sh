#!/bin/bash
# Path: scripts/deploy-lucid-pi.sh
# Lucid RDP deployment script for Raspberry Pi 5 (Ubuntu Server ARM64)

set -euo pipefail

# Configuration
LUCID_HOME="/opt/lucid"
LUCID_USER="lucid"
LUCID_SERVICE="lucid-rdp"
DOCKER_COMPOSE_FILE="$LUCID_HOME/docker-compose.yml"
ENV_FILE="$LUCID_HOME/.env"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$1] $2"
}

# Error handler
error_exit() {
    log "ERROR" "$1"
    exit 1
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error_exit "This script must be run as root (use sudo)"
    fi
}

# Install dependencies
install_dependencies() {
    log "INFO" "Installing system dependencies..."
    
    apt-get update || error_exit "Failed to update package list"
    
    # Install Docker and Docker Compose
    if ! command -v docker &> /dev/null; then
        log "INFO" "Installing Docker..."
        curl -fsSL https://get.docker.com | sh || error_exit "Failed to install Docker"
        systemctl enable docker || error_exit "Failed to enable Docker service"
        systemctl start docker || error_exit "Failed to start Docker service"
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log "INFO" "Installing Docker Compose..."
        pip3 install docker-compose || error_exit "Failed to install Docker Compose"
    fi
    
    # Install other dependencies
    apt-get install -y \
        tor \
        mongodb \
        python3 \
        python3-pip \
        curl \
        jq \
        htop \
        || error_exit "Failed to install dependencies"
        
    log "INFO" "Dependencies installed successfully"
}

# Create Lucid user
create_user() {
    if ! id "$LUCID_USER" &>/dev/null; then
        log "INFO" "Creating Lucid user..."
        useradd -r -s /bin/bash -d "$LUCID_HOME" -m "$LUCID_USER" || error_exit "Failed to create user"
        usermod -aG docker "$LUCID_USER" || error_exit "Failed to add user to docker group"
    fi
}

# Setup directory structure
setup_directories() {
    log "INFO" "Setting up directory structure..."
    
    mkdir -p "$LUCID_HOME"/{data,logs,config,scripts} || error_exit "Failed to create directories"
    chown -R "$LUCID_USER:$LUCID_USER" "$LUCID_HOME" || error_exit "Failed to set permissions"
}

# Configure Tor
configure_tor() {
    log "INFO" "Configuring Tor..."
    
    # Backup original config
    cp /etc/tor/torrc /etc/tor/torrc.backup || true
    
    cat > /etc/tor/torrc << 'EOF'
# Tor configuration for Lucid RDP
SocksPort 9050
ControlPort 9051
HashedControlPassword 16:872860B76453A77D60CA2BB8C1A7042072093276A3D701AD684053EC4C
HiddenServiceDir /var/lib/tor/lucid_service/
HiddenServicePort 80 127.0.0.1:8080
HiddenServicePort 5050 127.0.0.1:5050
RunAsDaemon 1
Log notice file /var/log/tor/notices.log
EOF

    systemctl enable tor || error_exit "Failed to enable Tor service"
    systemctl restart tor || error_exit "Failed to restart Tor service"
    
    log "INFO" "Tor configured successfully"
}

# Deploy application
deploy_application() {
    log "INFO" "Deploying Lucid RDP application..."
    
    # Copy application files
    if [[ -d "./06-orchestration-runtime/compose" ]]; then
        cp -r ./06-orchestration-runtime/compose/* "$LUCID_HOME/" || error_exit "Failed to copy compose files"
    fi
    
    # Copy environment configuration
    if [[ -f "./.env.pi" ]]; then
        cp ./.env.pi "$ENV_FILE" || error_exit "Failed to copy environment file"
    else
        cat > "$ENV_FILE" << 'EOF'
# Lucid RDP Environment Configuration - Raspberry Pi
LUCID_MODE=production
LUCID_NETWORK=mainnet
MONGO_URI=mongodb://localhost:27017/lucid
TOR_ENABLED=true
LOG_LEVEL=INFO
DATA_DIR=/opt/lucid/data
CHUNK_SIZE=16777216
COMPRESSION_LEVEL=3
EOF
    fi
    
    chown "$LUCID_USER:$LUCID_USER" "$ENV_FILE" || error_exit "Failed to set env file permissions"
    
    log "INFO" "Application deployed successfully"
}

# Create systemd service
create_service() {
    log "INFO" "Creating systemd service..."
    
    cat > "/etc/systemd/system/$LUCID_SERVICE.service" << EOF
[Unit]
Description=Lucid RDP Service
Requires=docker.service tor.service mongodb.service
After=docker.service tor.service mongodb.service
StartLimitBurst=3
StartLimitIntervalSec=60

[Service]
Type=oneshot
RemainAfterExit=yes
User=$LUCID_USER
Group=$LUCID_USER
WorkingDirectory=$LUCID_HOME
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
ExecReload=/usr/bin/docker-compose restart
TimeoutStartSec=300
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload || error_exit "Failed to reload systemd"
    systemctl enable "$LUCID_SERVICE" || error_exit "Failed to enable service"
    
    log "INFO" "Systemd service created successfully"
}

# Start services
start_services() {
    log "INFO" "Starting Lucid RDP services..."
    
    # Start MongoDB if not running
    systemctl start mongodb || true
    
    # Start the main service
    systemctl start "$LUCID_SERVICE" || error_exit "Failed to start Lucid service"
    
    # Wait for services to be ready
    sleep 10
    
    log "INFO" "Services started successfully"
}

# Health check
health_check() {
    log "INFO" "Running health checks..."
    
    # Check Docker containers
    if ! docker ps | grep -q "lucid"; then
        log "WARN" "No Lucid containers found running"
    else
        log "INFO" "Lucid containers are running"
    fi
    
    # Check Tor service
    if ! systemctl is-active --quiet tor; then
        log "WARN" "Tor service is not active"
    else
        log "INFO" "Tor service is active"
        # Get onion address
        if [[ -f "/var/lib/tor/lucid_service/hostname" ]]; then
            ONION_ADDR=$(cat /var/lib/tor/lucid_service/hostname)
            log "INFO" "Onion address: $ONION_ADDR"
        fi
    fi
    
    # Check MongoDB
    if ! systemctl is-active --quiet mongodb; then
        log "WARN" "MongoDB service is not active"
    else
        log "INFO" "MongoDB service is active"
    fi
    
    log "INFO" "Health check completed"
}

# Show status
show_status() {
    log "INFO" "Lucid RDP Status:"
    echo "=================="
    
    echo "System Information:"
    echo "  - Hostname: $(hostname)"
    echo "  - OS: $(lsb_release -d | cut -f2)"
    echo "  - Kernel: $(uname -r)"
    echo "  - Uptime: $(uptime -p)"
    
    echo ""
    echo "Service Status:"
    systemctl status "$LUCID_SERVICE" --no-pager -l || true
    
    echo ""
    echo "Container Status:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(lucid|mongo|tor)" || echo "No containers found"
    
    echo ""
    echo "Network Information:"
    if [[ -f "/var/lib/tor/lucid_service/hostname" ]]; then
        echo "  - Onion Address: $(cat /var/lib/tor/lucid_service/hostname)"
    fi
    echo "  - Docker Networks:"
    docker network ls | grep lucid || echo "    No Lucid networks found"
    
    echo ""
    echo "Resource Usage:"
    free -h
    df -h | grep -E "/(|opt)" || true
}

# Stop services
stop_services() {
    log "INFO" "Stopping Lucid RDP services..."
    
    systemctl stop "$LUCID_SERVICE" || true
    docker-compose -f "$DOCKER_COMPOSE_FILE" down || true
    
    log "INFO" "Services stopped"
}

# Cleanup installation
cleanup() {
    log "INFO" "Cleaning up Lucid RDP installation..."
    
    stop_services
    
    systemctl disable "$LUCID_SERVICE" || true
    rm -f "/etc/systemd/system/$LUCID_SERVICE.service"
    systemctl daemon-reload
    
    # Remove user and home directory
    if id "$LUCID_USER" &>/dev/null; then
        userdel -r "$LUCID_USER" || true
    fi
    
    # Remove application directory
    rm -rf "$LUCID_HOME" || true
    
    log "INFO" "Cleanup completed"
}

# Update application
update_application() {
    log "INFO" "Updating Lucid RDP application..."
    
    # Stop services
    systemctl stop "$LUCID_SERVICE" || true
    
    # Pull latest images
    docker-compose -f "$DOCKER_COMPOSE_FILE" pull || error_exit "Failed to pull latest images"
    
    # Start services
    systemctl start "$LUCID_SERVICE" || error_exit "Failed to start services after update"
    
    log "INFO" "Application updated successfully"
}

# Main function
main() {
    case "${1:-}" in
        "deploy")
            check_root
            log "INFO" "Starting Lucid RDP deployment..."
            install_dependencies
            create_user
            setup_directories
            configure_tor
            deploy_application
            create_service
            start_services
            health_check
            show_status
            log "INFO" "Deployment completed successfully!"
            ;;
        "start")
            check_root
            start_services
            ;;
        "stop")
            check_root
            stop_services
            ;;
        "restart")
            check_root
            stop_services
            sleep 5
            start_services
            ;;
        "status")
            show_status
            ;;
        "health")
            health_check
            ;;
        "update")
            check_root
            update_application
            ;;
        "cleanup")
            check_root
            echo "This will completely remove Lucid RDP installation."
            read -p "Are you sure? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                cleanup
            else
                echo "Operation cancelled."
            fi
            ;;
        *)
            echo "Usage: $0 {deploy|start|stop|restart|status|health|update|cleanup}"
            echo ""
            echo "Commands:"
            echo "  deploy  - Full deployment of Lucid RDP"
            echo "  start   - Start Lucid RDP services"
            echo "  stop    - Stop Lucid RDP services"
            echo "  restart - Restart Lucid RDP services"
            echo "  status  - Show service status"
            echo "  health  - Run health checks"
            echo "  update  - Update application"
            echo "  cleanup - Remove installation completely"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"