#!/bin/bash

# Lucid RDP Monitoring Configuration Script - Step 48
# Comprehensive monitoring configuration for all Lucid services

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MONITORING_DIR="$PROJECT_ROOT/ops/monitoring"
CONFIGS_DIR="$PROJECT_ROOT/configs"

# Colors for output
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

# Create monitoring directories
create_directories() {
    log_info "Creating monitoring directories..."
    
    local dirs=(
        "$MONITORING_DIR/prometheus/data"
        "$MONITORING_DIR/grafana/data"
        "$MONITORING_DIR/grafana/plugins"
        "$MONITORING_DIR/alertmanager/data"
        "$MONITORING_DIR/blackbox"
        "$MONITORING_DIR/grafana/dashboards"
    )
    
    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        chmod 755 "$dir"
    done
    
    log_success "Monitoring directories created"
}

# Configure Prometheus
configure_prometheus() {
    log_info "Configuring Prometheus..."
    
    # Validate Prometheus configuration
    if command -v promtool &> /dev/null; then
        if ! promtool check config "$MONITORING_DIR/prometheus/prometheus.yml"; then
            log_error "Prometheus configuration validation failed"
            exit 1
        fi
    fi
    
    # Validate alert rules
    if command -v promtool &> /dev/null; then
        if ! promtool check rules "$MONITORING_DIR/prometheus/alerts.yml"; then
            log_error "Alert rules validation failed"
            exit 1
        fi
    fi
    
    log_success "Prometheus configuration validated"
}

# Configure Grafana
configure_grafana() {
    log_info "Configuring Grafana..."
    
    # Create Grafana provisioning directories
    mkdir -p "$MONITORING_DIR/grafana/provisioning/datasources"
    mkdir -p "$MONITORING_DIR/grafana/provisioning/dashboards"
    
    # Copy datasources configuration
    cp "$MONITORING_DIR/grafana/datasources.yml" "$MONITORING_DIR/grafana/provisioning/datasources/"
    
    # Create dashboard provisioning configuration
    cat > "$MONITORING_DIR/grafana/provisioning/dashboards/dashboard.yml" << 'EOF'
apiVersion: 1

providers:
  - name: 'lucid-dashboards'
    orgId: 1
    folder: 'Lucid RDP'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
EOF

    log_success "Grafana configuration completed"
}

# Configure Alertmanager
configure_alertmanager() {
    log_info "Configuring Alertmanager..."
    
    # Create Alertmanager data directory
    mkdir -p "$MONITORING_DIR/alertmanager/data"
    chmod 755 "$MONITORING_DIR/alertmanager/data"
    
    # Validate Alertmanager configuration
    if command -v amtool &> /dev/null; then
        if ! amtool check-config "$MONITORING_DIR/alertmanager/alertmanager.yml"; then
            log_error "Alertmanager configuration validation failed"
            exit 1
        fi
    fi
    
    log_success "Alertmanager configuration completed"
}

# Configure Blackbox Exporter
configure_blackbox() {
    log_info "Configuring Blackbox Exporter..."
    
    # Validate Blackbox configuration
    if [[ -f "$MONITORING_DIR/blackbox/blackbox.yml" ]]; then
        log_success "Blackbox Exporter configuration found"
    else
        log_warning "Blackbox Exporter configuration not found"
    fi
}

# Create monitoring Docker Compose
create_monitoring_compose() {
    log_info "Creating monitoring Docker Compose configuration..."
    
    cat > "$MONITORING_DIR/docker-compose.monitoring.yml" << 'EOF'
version: '3.8'

services:
  # Prometheus for metrics collection
  prometheus:
    image: prom/prometheus:latest
    container_name: lucid-prometheus
    hostname: prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro
      - ./prometheus/data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
    networks:
      - lucid-monitoring

  # Grafana for visualization
  grafana:
    image: grafana/grafana:latest
    container_name: lucid-grafana
    hostname: grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - ./grafana/data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
      - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_INSTALL_PLUGINS=grafana-piechart-panel,grafana-worldmap-panel
    networks:
      - lucid-monitoring

  # Node Exporter for system metrics
  node-exporter:
    image: prom/node-exporter:latest
    container_name: lucid-node-exporter
    hostname: node-exporter
    restart: unless-stopped
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    networks:
      - lucid-monitoring

  # cAdvisor for container metrics
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    container_name: lucid-cadvisor
    hostname: cadvisor
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    privileged: true
    devices:
      - /dev/kmsg
    networks:
      - lucid-monitoring

  # Blackbox Exporter for external checks
  blackbox-exporter:
    image: prom/blackbox-exporter:latest
    container_name: lucid-blackbox-exporter
    hostname: blackbox-exporter
    restart: unless-stopped
    ports:
      - "9115:9115"
    volumes:
      - ./blackbox/blackbox.yml:/config/blackbox.yml:ro
    command:
      - '--config.file=/config/blackbox.yml'
    networks:
      - lucid-monitoring

  # Alertmanager for alert handling
  alertmanager:
    image: prom/alertmanager:latest
    container_name: lucid-alertmanager
    hostname: alertmanager
    restart: unless-stopped
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - ./alertmanager/data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
      - '--web.external-url=http://localhost:9093'
    networks:
      - lucid-monitoring

networks:
  lucid-monitoring:
    driver: bridge
    ipam:
      config:
        - subnet: 172.21.0.0/16
          gateway: 172.21.0.1

volumes:
  prometheus-data:
  grafana-data:
  alertmanager-data:
EOF

    log_success "Monitoring Docker Compose configuration created"
}

# Create monitoring startup script
create_startup_script() {
    log_info "Creating monitoring startup script..."
    
    cat > "$MONITORING_DIR/start-monitoring.sh" << 'EOF'
#!/bin/bash

# Lucid RDP Monitoring Startup Script
# Start all monitoring services

set -euo pipefail

# Colors for output
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

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Start monitoring services
start_monitoring() {
    log_info "Starting Lucid RDP monitoring services..."
    
    # Start monitoring services
    docker-compose -f docker-compose.monitoring.yml up -d
    
    # Wait for services to start
    log_info "Waiting for services to start..."
    sleep 30
    
    # Check service status
    local services=("prometheus" "grafana" "alertmanager" "node-exporter" "cadvisor" "blackbox-exporter")
    
    for service in "${services[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "lucid-$service"; then
            log_success "$service is running"
        else
            log_error "$service is not running"
        fi
    done
    
    log_success "Monitoring services started successfully!"
    log_info "Access points:"
    log_info "  - Prometheus: http://localhost:9090"
    log_info "  - Grafana: http://localhost:3000 (admin/admin)"
    log_info "  - Alertmanager: http://localhost:9093"
}

# Main execution
main() {
    check_docker
    start_monitoring
}

# Run main function
main "$@"
EOF

    chmod +x "$MONITORING_DIR/start-monitoring.sh"
    log_success "Monitoring startup script created"
}

# Create monitoring stop script
create_stop_script() {
    log_info "Creating monitoring stop script..."
    
    cat > "$MONITORING_DIR/stop-monitoring.sh" << 'EOF'
#!/bin/bash

# Lucid RDP Monitoring Stop Script
# Stop all monitoring services

set -euo pipefail

# Colors for output
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

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Stop monitoring services
stop_monitoring() {
    log_info "Stopping Lucid RDP monitoring services..."
    
    # Stop monitoring services
    docker-compose -f docker-compose.monitoring.yml down
    
    log_success "Monitoring services stopped successfully!"
}

# Main execution
main() {
    stop_monitoring
}

# Run main function
main "$@"
EOF

    chmod +x "$MONITORING_DIR/stop-monitoring.sh"
    log_success "Monitoring stop script created"
}

# Create monitoring status script
create_status_script() {
    log_info "Creating monitoring status script..."
    
    cat > "$MONITORING_DIR/status-monitoring.sh" << 'EOF'
#!/bin/bash

# Lucid RDP Monitoring Status Script
# Check status of all monitoring services

set -euo pipefail

# Colors for output
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

# Check service status
check_service_status() {
    local service_name="$1"
    local container_name="lucid-$service_name"
    
    if docker ps --format "table {{.Names}}" | grep -q "$container_name"; then
        log_success "$service_name is running"
        return 0
    else
        log_error "$service_name is not running"
        return 1
    fi
}

# Check monitoring services
check_monitoring_services() {
    log_info "Checking monitoring services status..."
    
    local services=("prometheus" "grafana" "alertmanager" "node-exporter" "cadvisor" "blackbox-exporter")
    local healthy_services=0
    local total_services=${#services[@]}
    
    for service in "${services[@]}"; do
        if check_service_status "$service"; then
            ((healthy_services++))
        fi
    done
    
    log_info "Healthy services: $healthy_services/$total_services"
    
    if [[ $healthy_services -eq $total_services ]]; then
        log_success "All monitoring services are healthy"
    elif [[ $healthy_services -gt 0 ]]; then
        log_warning "Some monitoring services are healthy ($healthy_services/$total_services)"
    else
        log_error "No monitoring services are healthy"
        return 1
    fi
}

# Check service endpoints
check_service_endpoints() {
    log_info "Checking service endpoints..."
    
    local endpoints=(
        "http://localhost:9090"
        "http://localhost:3000"
        "http://localhost:9093"
        "http://localhost:9100"
        "http://localhost:8080"
        "http://localhost:9115"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if curl -s --max-time 5 "$endpoint" > /dev/null; then
            log_success "$endpoint is responding"
        else
            log_error "$endpoint is not responding"
        fi
    done
}

# Main execution
main() {
    check_monitoring_services
    check_service_endpoints
}

# Run main function
main "$@"
EOF

    chmod +x "$MONITORING_DIR/status-monitoring.sh"
    log_success "Monitoring status script created"
}

# Main execution
main() {
    log_info "Starting Lucid RDP Monitoring Configuration (Step 48)"
    
    create_directories
    configure_prometheus
    configure_grafana
    configure_alertmanager
    configure_blackbox
    create_monitoring_compose
    create_startup_script
    create_stop_script
    create_status_script
    
    log_success "Monitoring configuration completed successfully!"
    log_info "To start monitoring services, run:"
    log_info "  cd $MONITORING_DIR"
    log_info "  ./start-monitoring.sh"
    log_info ""
    log_info "To check status, run:"
    log_info "  ./status-monitoring.sh"
    log_info ""
    log_info "To stop monitoring services, run:"
    log_info "  ./stop-monitoring.sh"
}

# Run main function
main "$@"
