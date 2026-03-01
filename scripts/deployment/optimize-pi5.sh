#!/bin/bash
# Raspberry Pi 5 Optimization Script for Lucid RDP
# Configures Pi 5 for optimal ARM64 performance and Docker deployment
# Based on LUCID-STRICT requirements

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Runtime variables for Pi 5 optimization
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/lucid-pi5-optimize.log"
CONFIG_BACKUP_DIR="/opt/lucid/config-backup"

# Pi 5 specific optimizations
PI5_OPTIMIZATIONS=(
    "gpu_mem=128"                    # Allocate 128MB to GPU for better performance
    "arm_64bit=1"                    # Ensure 64-bit mode
    "max_framebuffers=2"            # For RDP video optimization  
    "dtparam=pcie=on"               # Enable PCIe for NVMe drives
    "dtoverlay=pcie-32bit-dma"      # 32-bit DMA for compatibility
    "arm_boost=1"                   # Enable ARM boost
    "over_voltage=2"                # Slight overclock (safe level)
    "arm_freq=2600"                 # Set ARM frequency to 2.6GHz (Pi 5 max)
)

# System optimizations
SYSTEM_OPTIMIZATIONS=(
    "vm.swappiness=10"              # Reduce swap usage
    "net.core.rmem_max=16777216"    # Network buffer optimization
    "net.core.wmem_max=16777216"    # Network buffer optimization
    "net.ipv4.tcp_rmem=4096 87380 16777216"  # TCP receive buffer
    "net.ipv4.tcp_wmem=4096 65536 16777216"  # TCP send buffer
    "kernel.shmmax=268435456"       # Shared memory for MongoDB
    "fs.file-max=65536"             # Max open files
)

# Docker optimizations for Pi 5
DOCKER_OPTIMIZATIONS=(
    "storage-driver=overlay2"
    "log-driver=json-file"
    "log-opts=max-size=10m"
    "log-opts=max-file=3"
)

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_header() {
    echo -e "${CYAN}===== $1 =====${NC}" | tee -a "$LOG_FILE"
}

check_pi5_hardware() {
    log_info "Verifying Raspberry Pi 5 hardware..."
    
    if [[ ! -f /sys/firmware/devicetree/base/model ]]; then
        log_error "Cannot detect hardware model"
        return 1
    fi
    
    PI_MODEL=$(cat /sys/firmware/devicetree/base/model | tr -d '\0')
    
    if [[ "$PI_MODEL" != *"Raspberry Pi 5"* ]]; then
        log_error "This script is designed for Raspberry Pi 5, detected: $PI_MODEL"
        return 1
    fi
    
    log_success "Running on $PI_MODEL"
    
    # Check architecture
    ARCH=$(uname -m)
    if [[ "$ARCH" != "aarch64" ]]; then
        log_error "ARM64 architecture required, found: $ARCH"
        return 1
    fi
    
    log_success "ARM64 architecture confirmed"
    return 0
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        return 1
    fi
    return 0
}

create_backup() {
    log_info "Creating configuration backups..."
    
    mkdir -p "$CONFIG_BACKUP_DIR"
    
    # Backup critical files
    local files_to_backup=(
        "/boot/firmware/config.txt"
        "/etc/sysctl.conf"
        "/etc/docker/daemon.json"
        "/etc/fstab"
    )
    
    for file in "${files_to_backup[@]}"; do
        if [[ -f "$file" ]]; then
            cp "$file" "$CONFIG_BACKUP_DIR/$(basename "$file").backup.$(date +%Y%m%d-%H%M%S)"
            log_success "Backed up $file"
        fi
    done
}

optimize_boot_config() {
    log_header "Optimizing Boot Configuration"
    
    local config_file="/boot/firmware/config.txt"
    
    if [[ ! -f "$config_file" ]]; then
        log_error "Boot config file not found: $config_file"
        return 1
    fi
    
    # Add Lucid optimization section
    if ! grep -q "# Lucid RDP Optimizations" "$config_file"; then
        echo "" >> "$config_file"
        echo "# Lucid RDP Optimizations for Pi 5" >> "$config_file"
        echo "# Generated $(date)" >> "$config_file"
        
        for opt in "${PI5_OPTIMIZATIONS[@]}"; do
            echo "$opt" >> "$config_file"
            log_success "Added boot optimization: $opt"
        done
    else
        log_info "Boot optimizations already present"
    fi
    
    log_success "Boot configuration optimized"
}

optimize_system_kernel() {
    log_header "Optimizing System Kernel Parameters"
    
    local sysctl_file="/etc/sysctl.d/99-lucid-pi5.conf"
    
    # Create Lucid-specific sysctl config
    cat > "$sysctl_file" << EOF
# Lucid RDP Pi 5 System Optimizations
# Generated $(date)

EOF
    
    for opt in "${SYSTEM_OPTIMIZATIONS[@]}"; do
        echo "$opt" >> "$sysctl_file"
        log_success "Added system optimization: $opt"
    done
    
    # Apply immediately
    sysctl -p "$sysctl_file"
    
    log_success "System kernel parameters optimized"
}

optimize_docker() {
    log_header "Optimizing Docker for Pi 5"
    
    # Ensure Docker is installed
    if ! command -v docker >/dev/null 2>&1; then
        log_info "Installing Docker..."
        curl -fsSL https://get.docker.com | sh
        usermod -aG docker pi
        log_success "Docker installed"
    fi
    
    # Create Docker daemon configuration
    local docker_config="/etc/docker/daemon.json"
    
    cat > "$docker_config" << EOF
{
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "data-root": "/var/lib/docker",
  "exec-opts": ["native.cgroupdriver=systemd"],
  "live-restore": true,
  "userland-proxy": false,
  "experimental": true,
  "features": {
    "buildkit": true
  },
  "default-address-pools": [
    {
      "base": "172.30.0.0/16",
      "size": 24
    }
  ]
}
EOF
    
    # Restart Docker to apply changes
    systemctl restart docker
    systemctl enable docker
    
    log_success "Docker optimized for Pi 5"
}

setup_storage() {
    log_header "Optimizing Storage for Pi 5"
    
    # Check for NVMe drive
    if lsblk | grep -q nvme; then
        log_info "NVMe drive detected, optimizing for SSD performance"
        
        # Add fstab optimization for NVMe
        if ! grep -q "lucid-nvme-opt" /etc/fstab; then
            echo "# Lucid NVMe optimizations" >> /etc/fstab
            echo "tmpfs /tmp tmpfs defaults,noatime,nosuid,size=1G 0 0  # lucid-nvme-opt" >> /etc/fstab
            echo "tmpfs /var/log tmpfs defaults,noatime,nosuid,size=512M 0 0  # lucid-nvme-opt" >> /etc/fstab
        fi
        
        log_success "NVMe storage optimizations applied"
    else
        log_info "No NVMe drive detected, using SD card optimizations"
        
        # SD card specific optimizations
        if ! grep -q "lucid-sd-opt" /etc/fstab; then
            # Reduce SD card writes
            echo "tmpfs /tmp tmpfs defaults,noatime,nosuid,size=256M 0 0  # lucid-sd-opt" >> /etc/fstab
        fi
    fi
}

setup_memory() {
    log_header "Optimizing Memory Management"
    
    # Create memory management script
    cat > /usr/local/bin/lucid-memory-monitor << 'EOF'
#!/bin/bash
# Lucid Memory Monitor for Pi 5

while true; do
    # Clear caches if memory usage > 80%
    MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.0f"), $3/$2 * 100}')
    
    if [[ $MEMORY_USAGE -gt 80 ]]; then
        echo "High memory usage detected: ${MEMORY_USAGE}%"
        echo 3 > /proc/sys/vm/drop_caches
        echo "Memory caches cleared"
    fi
    
    sleep 300  # Check every 5 minutes
done
EOF
    
    chmod +x /usr/local/bin/lucid-memory-monitor
    
    # Create systemd service
    cat > /etc/systemd/system/lucid-memory-monitor.service << EOF
[Unit]
Description=Lucid Memory Monitor
After=multi-user.target

[Service]
Type=simple
ExecStart=/usr/local/bin/lucid-memory-monitor
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl enable lucid-memory-monitor.service
    log_success "Memory management optimized"
}

setup_networking() {
    log_header "Optimizing Network Configuration"
    
    # Network performance tuning
    cat > /etc/systemd/network/99-lucid.network << EOF
[Match]
Name=eth0

[Network]
DHCP=yes

[DHCP]
ClientIdentifier=mac
EOF
    
    # Enable systemd-networkd
    systemctl enable systemd-networkd
    
    log_success "Network configuration optimized"
}

install_dependencies() {
    log_header "Installing Required Dependencies"
    
    # Update package lists
    apt-get update
    
    # Essential packages for Lucid RDP
    local packages=(
        "curl"
        "wget"
        "git" 
        "python3"
        "python3-pip"
        "python3-venv"
        "build-essential"
        "cmake"
        "pkg-config"
        "libssl-dev"
        "libsodium-dev"
        "zstd"
        "htop"
        "iotop"
        "nethogs"
        "ncdu"
        "tree"
        "jq"
        "vim"
        "tmux"
    )
    
    apt-get install -y "${packages[@]}"
    
    log_success "Dependencies installed"
}

setup_firewall() {
    log_header "Configuring Firewall"
    
    # Install and configure UFW
    apt-get install -y ufw
    
    # Reset to defaults
    ufw --force reset
    
    # Default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # SSH access (be careful!)
    ufw allow ssh
    
    # Lucid RDP ports
    ufw allow 8081/tcp comment 'Lucid API Gateway'
    ufw allow 8082/tcp comment 'Lucid Blockchain Core'  
    ufw allow 27017/tcp comment 'MongoDB'
    
    # Tor proxy (internal only)
    ufw allow from 172.20.0.0/16 to any port 9050 comment 'Tor SOCKS proxy'
    ufw allow from 172.20.0.0/16 to any port 9051 comment 'Tor control port'
    
    # Enable firewall
    ufw --force enable
    
    log_success "Firewall configured"
}

create_lucid_user() {
    log_header "Setting up Lucid Service User"
    
    # Create lucid user for running services
    if ! id -u lucid >/dev/null 2>&1; then
        useradd -r -s /bin/bash -d /opt/lucid -m lucid
        usermod -aG docker lucid
        log_success "Created lucid service user"
    else
        log_info "Lucid user already exists"
    fi
    
    # Create service directories
    local dirs=(
        "/opt/lucid/data"
        "/opt/lucid/logs" 
        "/opt/lucid/config"
        "/opt/lucid/backups"
    )
    
    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        chown lucid:lucid "$dir"
        chmod 755 "$dir"
    done
    
    log_success "Lucid service directories created"
}

setup_monitoring() {
    log_header "Setting up System Monitoring"
    
    # Create monitoring script
    cat > /usr/local/bin/lucid-system-monitor << 'EOF'
#!/bin/bash
# Lucid System Monitor for Pi 5

LOG_FILE="/opt/lucid/logs/system-monitor.log"

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    # System metrics
    CPU_TEMP=$(vcgencmd measure_temp | cut -d= -f2 | cut -d\' -f1)
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d% -f1)
    MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.1f"), $3/$2 * 100}')
    DISK_USAGE=$(df / | awk 'NR==2{printf("%.1f"), $5}' | sed 's/%//')
    
    # Network stats
    RX_BYTES=$(cat /sys/class/net/eth0/statistics/rx_bytes 2>/dev/null || echo 0)
    TX_BYTES=$(cat /sys/class/net/eth0/statistics/tx_bytes 2>/dev/null || echo 0)
    
    # Docker stats
    DOCKER_CONTAINERS=$(docker ps -q | wc -l)
    
    # Log metrics
    echo "$TIMESTAMP,CPU:${CPU_USAGE}%,TEMP:${CPU_TEMP}°C,MEM:${MEMORY_USAGE}%,DISK:${DISK_USAGE}%,CONTAINERS:${DOCKER_CONTAINERS},RX:${RX_BYTES},TX:${TX_BYTES}" >> "$LOG_FILE"
    
    # Alert on high temperature (Pi 5 throttles at 80°C)
    if [[ $(echo "$CPU_TEMP > 75" | bc -l) -eq 1 ]]; then
        echo "$TIMESTAMP WARNING: High CPU temperature: ${CPU_TEMP}°C" >> "$LOG_FILE"
    fi
    
    sleep 60  # Log every minute
done
EOF
    
    chmod +x /usr/local/bin/lucid-system-monitor
    
    # Create systemd service
    cat > /etc/systemd/system/lucid-system-monitor.service << EOF
[Unit]
Description=Lucid System Monitor
After=multi-user.target

[Service]
Type=simple
ExecStart=/usr/local/bin/lucid-system-monitor
User=lucid
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl enable lucid-system-monitor.service
    log_success "System monitoring configured"
}

generate_optimization_report() {
    log_header "Generating Optimization Report"
    
    local report_file="/opt/lucid/pi5-optimization-report.txt"
    
    cat > "$report_file" << EOF
Lucid RDP Raspberry Pi 5 Optimization Report
Generated: $(date)
Hostname: $(hostname)
Kernel: $(uname -r)
Hardware: $(cat /sys/firmware/devicetree/base/model | tr -d '\0')

System Configuration:
- Boot optimizations: Applied
- Kernel parameters: Optimized
- Docker: Optimized for Pi 5
- Storage: $(lsblk | grep -q nvme && echo "NVMe optimized" || echo "SD card optimized")
- Memory management: Enabled
- Firewall: Configured
- Monitoring: Enabled

Services Status:
$(systemctl status lucid-memory-monitor.service --no-pager -l)
$(systemctl status lucid-system-monitor.service --no-pager -l)
$(systemctl status docker.service --no-pager -l)

System Resources:
CPU Temperature: $(vcgencmd measure_temp)
Memory Usage: $(free -h | grep Mem)
Disk Usage: $(df -h /)

Network Configuration:
$(ip addr show eth0 | grep inet)

Docker Status:
$(docker info | head -10)

Next Steps:
1. Reboot to apply all boot configuration changes
2. Run deploy-lucid-pi.sh to deploy Lucid RDP services
3. Monitor system performance with: tail -f /opt/lucid/logs/system-monitor.log

EOF

    chown lucid:lucid "$report_file"
    log_success "Optimization report generated: $report_file"
}

main() {
    log_header "Raspberry Pi 5 Optimization for Lucid RDP"
    
    # Prerequisite checks
    if ! check_root; then
        exit 1
    fi
    
    if ! check_pi5_hardware; then
        exit 1
    fi
    
    # Create log file
    touch "$LOG_FILE"
    chmod 644 "$LOG_FILE"
    
    log_info "Starting Pi 5 optimization process..."
    
    # Run optimizations
    create_backup
    install_dependencies
    optimize_boot_config
    optimize_system_kernel  
    optimize_docker
    setup_storage
    setup_memory
    setup_networking
    setup_firewall
    create_lucid_user
    setup_monitoring
    generate_optimization_report
    
    log_header "Optimization Complete"
    log_success "Pi 5 has been optimized for Lucid RDP"
    log_info "Configuration backups saved to: $CONFIG_BACKUP_DIR"
    log_info "System report saved to: /opt/lucid/pi5-optimization-report.txt"
    log_warning "REBOOT REQUIRED to apply all changes"
    
    read -p "Would you like to reboot now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Rebooting in 5 seconds..."
        sleep 5
        reboot
    else
        log_info "Please reboot manually when convenient"
    fi
}

# Run main function
main "$@"