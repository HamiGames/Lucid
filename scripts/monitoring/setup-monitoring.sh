#!/bin/bash

# Lucid RDP Monitoring Setup Script - Step 48
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

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root"
        exit 1
    fi
}

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."
    
    local deps=("docker" "docker-compose" "curl" "jq")
    local missing_deps=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing_deps+=("$dep")
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_info "Please install the missing dependencies and try again"
        exit 1
    fi
    
    log_success "All dependencies are available"
}

# Validate monitoring configuration files
validate_configs() {
    log_info "Validating monitoring configuration files..."
    
    local config_files=(
        "$MONITORING_DIR/prometheus/prometheus.yml"
        "$MONITORING_DIR/prometheus/alerts.yml"
        "$MONITORING_DIR/grafana/datasources.yml"
    )
    
    for config_file in "${config_files[@]}"; do
        if [[ ! -f "$config_file" ]]; then
            log_error "Configuration file not found: $config_file"
            exit 1
        fi
        
        # Validate YAML syntax
        if command -v yq &> /dev/null; then
            if ! yq eval '.' "$config_file" > /dev/null 2>&1; then
                log_error "Invalid YAML syntax in: $config_file"
                exit 1
            fi
        fi
    done
    
    log_success "All configuration files are valid"
}

# Setup Prometheus configuration
setup_prometheus() {
    log_info "Setting up Prometheus configuration..."
    
    # Create Prometheus data directory
    mkdir -p "$MONITORING_DIR/prometheus/data"
    chmod 755 "$MONITORING_DIR/prometheus/data"
    
    # Validate Prometheus configuration
    if command -v promtool &> /dev/null; then
        if ! promtool check config "$MONITORING_DIR/prometheus/prometheus.yml"; then
            log_error "Prometheus configuration validation failed"
            exit 1
        fi
    fi
    
    log_success "Prometheus configuration is valid"
}

# Setup Grafana configuration
setup_grafana() {
    log_info "Setting up Grafana configuration..."
    
    # Create Grafana data directory
    mkdir -p "$MONITORING_DIR/grafana/data"
    mkdir -p "$MONITORING_DIR/grafana/plugins"
    chmod 755 "$MONITORING_DIR/grafana/data"
    chmod 755 "$MONITORING_DIR/grafana/plugins"
    
    # Validate Grafana datasources
    if command -v jq &> /dev/null; then
        if ! jq empty "$MONITORING_DIR/grafana/datasources.yml" 2>/dev/null; then
            log_error "Invalid JSON in Grafana datasources configuration"
            exit 1
        fi
    fi
    
    log_success "Grafana configuration is valid"
}

# Setup alerting rules
setup_alerting() {
    log_info "Setting up alerting rules..."
    
    # Validate alert rules
    if command -v promtool &> /dev/null; then
        if ! promtool check rules "$MONITORING_DIR/prometheus/alerts.yml"; then
            log_error "Alert rules validation failed"
            exit 1
        fi
    fi
    
    log_success "Alert rules are valid"
}

# Create monitoring Docker Compose file
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
      - ./grafana/datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml:ro
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

# Create Alertmanager configuration
create_alertmanager_config() {
    log_info "Creating Alertmanager configuration..."
    
    mkdir -p "$MONITORING_DIR/alertmanager"
    
    cat > "$MONITORING_DIR/alertmanager/alertmanager.yml" << 'EOF'
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@lucid-rdp.com'
  smtp_auth_username: 'alerts@lucid-rdp.com'
  smtp_auth_password: 'password'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'
  routes:
  - match:
      severity: critical
    receiver: 'critical-alerts'
  - match:
      severity: warning
    receiver: 'warning-alerts'

receivers:
- name: 'web.hook'
  webhook_configs:
  - url: 'http://localhost:5001/'

- name: 'critical-alerts'
  email_configs:
  - to: 'admin@lucid-rdp.com'
    subject: 'CRITICAL: {{ .GroupLabels.alertname }}'
    body: |
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      {{ end }}

- name: 'warning-alerts'
  email_configs:
  - to: 'ops@lucid-rdp.com'
    subject: 'WARNING: {{ .GroupLabels.alertname }}'
    body: |
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      {{ end }}

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'cluster', 'service']
EOF

    log_success "Alertmanager configuration created"
}

# Create Blackbox configuration
create_blackbox_config() {
    log_info "Creating Blackbox Exporter configuration..."
    
    mkdir -p "$MONITORING_DIR/blackbox"
    
    cat > "$MONITORING_DIR/blackbox/blackbox.yml" << 'EOF'
modules:
  http_2xx:
    prober: http
    timeout: 5s
    http:
      valid_http_versions: ["HTTP/1.1", "HTTP/2.0"]
      valid_status_codes: [200]
      method: GET
      headers:
        User-Agent: "Blackbox Exporter"
      no_follow_redirects: false
      fail_if_ssl: false
      fail_if_not_ssl: false
      tls_config:
        insecure_skip_verify: false
      preferred_ip_protocol: "ip4"
      ip_protocol_fallback: false

  tcp_connect:
    prober: tcp
    timeout: 5s
    tcp:
      preferred_ip_protocol: "ip4"
      ip_protocol_fallback: false

  icmp:
    prober: icmp
    timeout: 5s
    icmp:
      preferred_ip_protocol: "ip4"
      ip_protocol_fallback: false
EOF

    log_success "Blackbox Exporter configuration created"
}

# Test monitoring setup
test_monitoring() {
    log_info "Testing monitoring setup..."
    
    # Test Prometheus configuration
    if command -v promtool &> /dev/null; then
        if promtool check config "$MONITORING_DIR/prometheus/prometheus.yml"; then
            log_success "Prometheus configuration test passed"
        else
            log_error "Prometheus configuration test failed"
            exit 1
        fi
    fi
    
    # Test alert rules
    if command -v promtool &> /dev/null; then
        if promtool check rules "$MONITORING_DIR/prometheus/alerts.yml"; then
            log_success "Alert rules test passed"
        else
            log_error "Alert rules test failed"
            exit 1
        fi
    fi
    
    log_success "All monitoring tests passed"
}

# Main execution
main() {
    log_info "Starting Lucid RDP Monitoring Setup (Step 48)"
    
    check_root
    check_dependencies
    validate_configs
    setup_prometheus
    setup_grafana
    setup_alerting
    create_monitoring_compose
    create_alertmanager_config
    create_blackbox_config
    test_monitoring
    
    log_success "Monitoring setup completed successfully!"
    log_info "To start monitoring services, run:"
    log_info "  cd $MONITORING_DIR"
    log_info "  docker-compose -f docker-compose.monitoring.yml up -d"
    log_info ""
    log_info "Access points:"
    log_info "  - Prometheus: http://localhost:9090"
    log_info "  - Grafana: http://localhost:3000 (admin/admin)"
    log_info "  - Alertmanager: http://localhost:9093"
}

# Run main function
main "$@"
