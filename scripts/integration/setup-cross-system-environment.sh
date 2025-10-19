#!/bin/bash
# Cross-System Environment Setup Script
# Sets up environment coordination across GUI, API, and Docker systems

set -euo pipefail

# Script configuration
SCRIPT_NAME="setup-cross-system-environment.sh"
SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Configuration variables
ENVIRONMENT="${LUCID_ENVIRONMENT:-production}"
PI_HOST="${PI_HOST:-192.168.0.75}"
PI_USER="${PI_USER:-pickme}"
PI_DEPLOY_DIR="${PI_DEPLOY_DIR:-/opt/lucid/production}"

# Directories
CONFIGS_DIR="$PROJECT_ROOT/configs"
ENVIRONMENT_DIR="$CONFIGS_DIR/environment"
DOCKER_DIR="$CONFIGS_DIR/docker"
SERVICES_DIR="$CONFIGS_DIR/services"
SCRIPTS_DIR="$PROJECT_ROOT/scripts"

# Environment files
ENV_COORDINATION_FILE="$ENVIRONMENT_DIR/env.coordination.yml"
ENV_GUI_FILE="$ENVIRONMENT_DIR/env.gui"
DOCKER_COMPOSE_ALL="$DOCKER_DIR/docker-compose.all.yml"
DOCKER_COMPOSE_GUI="$DOCKER_DIR/docker-compose.gui-integration.yml"

# Function to validate prerequisites
validate_prerequisites() {
    log_info "Validating prerequisites..."
    
    # Check if running as root (not recommended)
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root is not recommended for security reasons"
    fi
    
    # Check required tools
    local required_tools=("docker" "docker-compose" "yq" "jq" "ssh")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Required tool '$tool' is not installed"
            exit 1
        fi
    done
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running or not accessible"
        exit 1
    fi
    
    # Check SSH connection to Pi
    if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$PI_USER@$PI_HOST" exit &> /dev/null; then
        log_warning "SSH connection to Pi ($PI_USER@$PI_HOST) failed"
        log_warning "Please ensure SSH keys are configured"
    fi
    
    log_success "Prerequisites validation completed"
}

# Function to generate secure secrets
generate_secrets() {
    log_info "Generating secure secrets..."
    
    local secrets_file="$ENVIRONMENT_DIR/.secrets"
    
    # Generate JWT secret
    local jwt_secret=$(openssl rand -base64 64 | tr -d '\n')
    
    # Generate encryption key
    local encryption_key=$(openssl rand -base64 32 | tr -d '\n')
    
    # Generate Tor control password
    local tor_password=$(openssl rand -base64 16 | tr -d '\n')
    
    # Generate MongoDB password
    local mongodb_password=$(openssl rand -base64 16 | tr -d '\n')
    
    # Generate Redis password
    local redis_password=$(openssl rand -base64 16 | tr -d '\n')
    
    # Create secrets file
    cat > "$secrets_file" << EOF
# Generated secrets for Lucid system
# DO NOT COMMIT THIS FILE TO VERSION CONTROL
# Generated on: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Authentication
JWT_SECRET_KEY="$jwt_secret"
ENCRYPTION_KEY="$encryption_key"
TOR_CONTROL_PASSWORD="$tor_password"

# Database passwords
MONGODB_PASSWORD="$mongodb_password"
REDIS_PASSWORD="$redis_password"

# TRON configuration
TRON_PRIVATE_KEY="CHANGE_ME_IN_PRODUCTION"
TRON_NETWORK="shasta"
EOF
    
    # Set secure permissions
    chmod 600 "$secrets_file"
    
    log_success "Secrets generated and saved to $secrets_file"
}

# Function to validate environment configuration
validate_environment_config() {
    log_info "Validating environment configuration..."
    
    # Check if coordination file exists
    if [[ ! -f "$ENV_COORDINATION_FILE" ]]; then
        log_error "Environment coordination file not found: $ENV_COORDINATION_FILE"
        exit 1
    fi
    
    # Check if GUI environment file exists
    if [[ ! -f "$ENV_GUI_FILE" ]]; then
        log_error "GUI environment file not found: $ENV_GUI_FILE"
        exit 1
    fi
    
    # Validate YAML syntax
    if ! yq eval '.' "$ENV_COORDINATION_FILE" &> /dev/null; then
        log_error "Invalid YAML syntax in coordination file"
        exit 1
    fi
    
    if ! yq eval '.' "$ENV_GUI_FILE" &> /dev/null; then
        log_error "Invalid YAML syntax in GUI environment file"
        exit 1
    fi
    
    log_success "Environment configuration validation completed"
}

# Function to update environment variables
update_environment_variables() {
    log_info "Updating environment variables..."
    
    # Load secrets if available
    local secrets_file="$ENVIRONMENT_DIR/.secrets"
    if [[ -f "$secrets_file" ]]; then
        source "$secrets_file"
        log_info "Loaded secrets from $secrets_file"
    fi
    
    # Update coordination file with actual values
    yq eval "
        .shared.PI_HOST = \"$PI_HOST\" |
        .shared.PI_USER = \"$PI_USER\" |
        .shared.PI_DEPLOY_DIR = \"$PI_DEPLOY_DIR\" |
        .shared.MONGODB_URI = \"mongodb://lucid:${MONGODB_PASSWORD:-lucid}@$PI_HOST:27017/lucid?authSource=admin\" |
        .shared.REDIS_URL = \"redis://:${REDIS_PASSWORD:-lucid}@$PI_HOST:6379/0\" |
        .shared.ELASTICSEARCH_URL = \"http://$PI_HOST:9200\" |
        .shared.JWT_SECRET_KEY = \"${JWT_SECRET_KEY:-lucid_jwt_secret_key_change_in_production}\" |
        .shared.ENCRYPTION_KEY = \"${ENCRYPTION_KEY:-lucid_encryption_key_change_in_production}\" |
        .shared.TOR_CONTROL_PASSWORD = \"${TOR_CONTROL_PASSWORD:-lucid_tor_password_change_in_production}\"
    " -i "$ENV_COORDINATION_FILE"
    
    # Update GUI environment file
    yq eval "
        .PI_HOST = \"$PI_HOST\" |
        .PI_USER = \"$PI_USER\" |
        .PI_DEPLOY_DIR = \"$PI_DEPLOY_DIR\" |
        .API_GATEWAY_URL = \"http://$PI_HOST:8080\" |
        .BLOCKCHAIN_CORE_URL = \"http://$PI_HOST:8084\" |
        .AUTH_SERVICE_URL = \"http://$PI_HOST:8089\" |
        .SESSION_API_URL = \"http://$PI_HOST:8087\" |
        .NODE_MANAGEMENT_URL = \"http://$PI_HOST:8095\" |
        .ADMIN_INTERFACE_URL = \"http://$PI_HOST:8083\" |
        .TRON_PAYMENT_URL = \"http://$PI_HOST:8085\" |
        .GUI_API_BRIDGE_URL = \"http://$PI_HOST:8097\" |
        .GUI_DOCKER_MANAGER_URL = \"http://$PI_HOST:8098\" |
        .GUI_HARDWARE_WALLET_URL = \"http://$PI_HOST:8099\"
    " -i "$ENV_GUI_FILE"
    
    log_success "Environment variables updated"
}

# Function to validate Docker Compose files
validate_docker_compose_files() {
    log_info "Validating Docker Compose files..."
    
    local compose_files=(
        "$DOCKER_COMPOSE_ALL"
        "$DOCKER_COMPOSE_GUI"
    )
    
    for compose_file in "${compose_files[@]}"; do
        if [[ ! -f "$compose_file" ]]; then
            log_error "Docker Compose file not found: $compose_file"
            exit 1
        fi
        
        # Validate compose file syntax
        if ! docker-compose -f "$compose_file" config &> /dev/null; then
            log_error "Invalid Docker Compose syntax in: $compose_file"
            exit 1
        fi
    done
    
    log_success "Docker Compose files validation completed"
}

# Function to setup SSH configuration
setup_ssh_configuration() {
    log_info "Setting up SSH configuration for Pi deployment..."
    
    local ssh_config_dir="$HOME/.ssh"
    local ssh_config_file="$ssh_config_dir/config"
    
    # Create SSH config entry for Pi
    if [[ ! -f "$ssh_config_file" ]]; then
        mkdir -p "$ssh_config_dir"
        touch "$ssh_config_file"
        chmod 600 "$ssh_config_file"
    fi
    
    # Add Pi configuration if not exists
    if ! grep -q "Host lucid-pi" "$ssh_config_file"; then
        cat >> "$ssh_config_file" << EOF

# Lucid Pi Configuration
Host lucid-pi
    HostName $PI_HOST
    User $PI_USER
    Port 22
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    ServerAliveInterval 60
    ServerAliveCountMax 3
EOF
        log_success "SSH configuration added for Pi"
    else
        log_info "SSH configuration for Pi already exists"
    fi
}

# Function to create deployment directories
create_deployment_directories() {
    log_info "Creating deployment directories..."
    
    local directories=(
        "$PROJECT_ROOT/logs"
        "$PROJECT_ROOT/data"
        "$PROJECT_ROOT/backups"
        "$PROJECT_ROOT/certs"
        "$PROJECT_ROOT/tor-data"
    )
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_info "Created directory: $dir"
        fi
    done
    
    log_success "Deployment directories created"
}

# Function to setup Tor configuration
setup_tor_configuration() {
    log_info "Setting up Tor configuration..."
    
    local tor_config_dir="$PROJECT_ROOT/configs/tor"
    local torrc_file="$tor_config_dir/torrc.gui"
    
    # Create Tor configuration file
    cat > "$torrc_file" << EOF
# Tor configuration for Lucid GUI
# Generated by $SCRIPT_NAME on $(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Basic Tor configuration
SocksPort 9050
ControlPort 9051
DataDirectory $PROJECT_ROOT/tor-data
Log notice file $PROJECT_ROOT/logs/tor.log

# Authentication for control port
HashedControlPassword $(tor --hash-password "${TOR_CONTROL_PASSWORD:-lucid_tor_password_change_in_production}" | grep -v "Warning")

# Security settings
SafeLogging 1
WarnPlaintextPorts 23,109,110,143,80
RejectPlaintextPorts 25,135,139,445,563,1214,4661,4662,6346,6665,6666,6667,6668,6669

# Performance settings
CircuitBuildTimeout 60
NewCircuitPeriod 30
MaxCircuitDirtiness 600
MaxClientCircuitsPending 32

# Exit policy (restrictive for GUI)
ExitPolicy reject *:*

# Bridge configuration (if needed)
# UseBridges 1
# Bridge obfs4 0.0.2.0:1 cert=... iat-mode=0

# Hidden service configuration (for future use)
# HiddenServiceDir $PROJECT_ROOT/tor-data/hidden-service
# HiddenServicePort 80 127.0.0.1:8080
EOF
    
    log_success "Tor configuration created: $torrc_file"
}

# Function to validate system integration
validate_system_integration() {
    log_info "Validating system integration..."
    
    # Check if all required services are defined
    local required_services=(
        "lucid-api-gateway"
        "lucid-blockchain-core"
        "lucid-auth-service"
        "lucid-session-api"
        "lucid-node-management"
        "lucid-admin-interface"
        "lucid-tron-client"
        "lucid-gui-api-bridge"
        "lucid-gui-docker-manager"
        "lucid-gui-tor-manager"
        "lucid-gui-hardware-wallet"
    )
    
    # Validate services in Docker Compose files
    for service in "${required_services[@]}"; do
        if ! grep -q "$service" "$DOCKER_COMPOSE_ALL" "$DOCKER_COMPOSE_GUI"; then
            log_warning "Service '$service' not found in Docker Compose files"
        fi
    done
    
    # Check network configuration
    if ! docker network ls | grep -q "lucid-pi-network"; then
        log_info "Creating Lucid network..."
        docker network create --driver bridge --subnet 172.20.0.0/16 lucid-pi-network
    fi
    
    if ! docker network ls | grep -q "lucid-network-isolated"; then
        log_info "Creating isolated TRON network..."
        docker network create --driver bridge --subnet 172.21.0.0/16 lucid-network-isolated
    fi
    
    if ! docker network ls | grep -q "lucid-gui-network"; then
        log_info "Creating GUI network..."
        docker network create --driver bridge --subnet 172.22.0.0/16 lucid-gui-network
    fi
    
    log_success "System integration validation completed"
}

# Function to generate deployment script
generate_deployment_script() {
    log_info "Generating deployment script..."
    
    local deploy_script="$SCRIPTS_DIR/deployment/deploy-all-systems.sh"
    local deploy_dir="$(dirname "$deploy_script")"
    
    mkdir -p "$deploy_dir"
    
    cat > "$deploy_script" << 'EOF'
#!/bin/bash
# Deploy All Systems Script
# Deploys the complete Lucid system including GUI integration

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Load environment variables
source "$PROJECT_ROOT/configs/environment/.secrets" 2>/dev/null || true

# Deploy phases in order
echo "Deploying Phase 1: Foundation Services..."
docker-compose -f "$PROJECT_ROOT/configs/docker/docker-compose.foundation.yml" up -d

echo "Deploying Phase 2: Core Services..."
docker-compose -f "$PROJECT_ROOT/configs/docker/docker-compose.core.yml" up -d

echo "Deploying Phase 3: Application Services..."
docker-compose -f "$PROJECT_ROOT/configs/docker/docker-compose.application.yml" up -d

echo "Deploying Phase 4: Support Services..."
docker-compose -f "$PROJECT_ROOT/configs/docker/docker-compose.support.yml" up -d

echo "Deploying GUI Integration Services..."
docker-compose -f "$PROJECT_ROOT/configs/docker/docker-compose.gui-integration.yml" up -d

echo "All systems deployed successfully!"
EOF
    
    chmod +x "$deploy_script"
    log_success "Deployment script generated: $deploy_script"
}

# Function to create health check script
create_health_check_script() {
    log_info "Creating health check script..."
    
    local health_script="$SCRIPTS_DIR/monitoring/health-check-all.sh"
    local health_dir="$(dirname "$health_script")"
    
    mkdir -p "$health_dir"
    
    cat > "$health_script" << 'EOF'
#!/bin/bash
# Health Check All Systems Script
# Checks health of all Lucid services

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Service endpoints
declare -A SERVICES=(
    ["API Gateway"]="http://localhost:8080/health"
    ["Blockchain Core"]="http://localhost:8084/health"
    ["Auth Service"]="http://localhost:8089/health"
    ["Session API"]="http://localhost:8087/health"
    ["Node Management"]="http://localhost:8095/health"
    ["Admin Interface"]="http://localhost:8083/health"
    ["TRON Payment"]="http://localhost:8096/health"
    ["GUI API Bridge"]="http://localhost:8097/health"
    ["GUI Docker Manager"]="http://localhost:8098/health"
    ["GUI Hardware Wallet"]="http://localhost:8099/health"
)

# Check service health
for service in "${!SERVICES[@]}"; do
    endpoint="${SERVICES[$service]}"
    if curl -f -s "$endpoint" > /dev/null; then
        echo "✅ $service: Healthy"
    else
        echo "❌ $service: Unhealthy"
    fi
done
EOF
    
    chmod +x "$health_script"
    log_success "Health check script created: $health_script"
}

# Function to display summary
display_summary() {
    log_info "Setup Summary:"
    echo ""
    echo "Environment Configuration:"
    echo "  - Environment: $ENVIRONMENT"
    echo "  - Pi Host: $PI_HOST"
    echo "  - Pi User: $PI_USER"
    echo "  - Deployment Directory: $PI_DEPLOY_DIR"
    echo ""
    echo "Generated Files:"
    echo "  - Environment coordination: $ENV_COORDINATION_FILE"
    echo "  - GUI environment: $ENV_GUI_FILE"
    echo "  - Secrets file: $ENVIRONMENT_DIR/.secrets"
    echo "  - Tor configuration: $PROJECT_ROOT/configs/tor/torrc.gui"
    echo ""
    echo "Docker Networks:"
    echo "  - Main network: lucid-pi-network (172.20.0.0/16)"
    echo "  - TRON isolated: lucid-network-isolated (172.21.0.0/16)"
    echo "  - GUI network: lucid-gui-network (172.22.0.0/16)"
    echo ""
    echo "Generated Scripts:"
    echo "  - Deployment: $SCRIPTS_DIR/deployment/deploy-all-systems.sh"
    echo "  - Health check: $SCRIPTS_DIR/monitoring/health-check-all.sh"
    echo ""
    echo "Next Steps:"
    echo "  1. Review and update secrets in $ENVIRONMENT_DIR/.secrets"
    echo "  2. Configure SSH keys for Pi access"
    echo "  3. Run deployment script: $SCRIPTS_DIR/deployment/deploy-all-systems.sh"
    echo "  4. Monitor system health: $SCRIPTS_DIR/monitoring/health-check-all.sh"
    echo ""
    log_success "Cross-system environment setup completed!"
}

# Main execution
main() {
    log_info "Starting cross-system environment setup..."
    log_info "Script: $SCRIPT_NAME v$SCRIPT_VERSION"
    log_info "Project root: $PROJECT_ROOT"
    
    validate_prerequisites
    generate_secrets
    validate_environment_config
    update_environment_variables
    validate_docker_compose_files
    setup_ssh_configuration
    create_deployment_directories
    setup_tor_configuration
    validate_system_integration
    generate_deployment_script
    create_health_check_script
    display_summary
}

# Run main function
main "$@"
