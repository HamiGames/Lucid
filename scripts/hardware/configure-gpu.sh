#!/bin/bash
# scripts/hardware/configure-gpu.sh
# Configure Pi 5 GPU for video encoding with distroless containers
# LUCID-STRICT: Pi 5 GPU configuration for hardware acceleration

set -Eeuo pipefail

# Script metadata
SCRIPT_NAME="$(basename "$0")"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_PATH/../.." && pwd)"

# Configuration
GPU_MEMORY="${GPU_MEMORY:-128}"
GPU_FREQ="${GPU_FREQ:-500}"
OVERCLOCK="${OVERCLOCK:-false}"
THERMAL_PROTECTION="${THERMAL_PROTECTION:-true}"

# Pi 5 specific settings
PI5_GPU_MEMORY="${PI5_GPU_MEMORY:-128}"
PI5_GPU_FREQ="${PI5_GPU_FREQ:-500}"
PI5_OVERCLOCK="${PI5_OVERCLOCK:-false}"

# Logging
log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*"; }
die() { printf '[%s][ERROR] %s\n' "$SCRIPT_NAME" "$*" >&2; exit 1; }
warn() { printf '[%s][WARN] %s\n' "$SCRIPT_NAME" "$*" >&2; }

# Check if running on Pi 5
check_pi_model() {
    log "Checking Pi model..."
    
    local model
    model=$(cat /proc/device-tree/model 2>/dev/null || echo "Unknown")
    log "Pi Model: $model"
    
    if [[ "$model" == *"Pi 5"* ]]; then
        log "Pi 5 detected - using Pi 5 specific configuration"
        GPU_MEMORY="$PI5_GPU_MEMORY"
        GPU_FREQ="$PI5_GPU_FREQ"
        OVERCLOCK="$PI5_OVERCLOCK"
    elif [[ "$model" == *"Pi 4"* ]]; then
        log "Pi 4 detected - using Pi 4 configuration"
        GPU_MEMORY="128"
        GPU_FREQ="500"
    else
        warn "Unknown Pi model - using default configuration"
    fi
}

# Check current GPU configuration
check_current_gpu_config() {
    log "Checking current GPU configuration..."
    
    # Check GPU memory
    local current_gpu_mem
    current_gpu_mem=$(vcgencmd get_mem gpu 2>/dev/null || echo "gpu=Unknown")
    log "Current GPU memory: $current_gpu_mem"
    
    # Check GPU frequency
    local current_gpu_freq
    current_gpu_freq=$(vcgencmd measure_clock gpu 2>/dev/null || echo "frequency(45)=Unknown")
    log "Current GPU frequency: $current_gpu_freq"
    
    # Check GPU temperature
    local current_temp
    current_temp=$(vcgencmd measure_temp 2>/dev/null || echo "temp=Unknown")
    log "Current GPU temperature: $current_temp"
    
    # Check GPU voltage
    local current_voltage
    current_voltage=$(vcgencmd measure_volts core 2>/dev/null || echo "volt=Unknown")
    log "Current GPU voltage: $current_voltage"
}

# Backup current configuration
backup_config() {
    log "Backing up current configuration..."
    
    local backup_dir="/opt/lucid/backups/gpu-config"
    local backup_file="$backup_dir/gpu-config-$(date +%Y%m%d-%H%M%S).txt"
    
    mkdir -p "$backup_dir"
    
    cat > "$backup_file" << EOF
# Lucid RDP GPU Configuration Backup
# Date: $(date)
# Pi Model: $(cat /proc/device-tree/model 2>/dev/null || echo "Unknown")

# Current GPU Memory
$(vcgencmd get_mem gpu 2>/dev/null || echo "gpu=Unknown")

# Current GPU Frequency
$(vcgencmd measure_clock gpu 2>/dev/null || echo "frequency(45)=Unknown")

# Current GPU Temperature
$(vcgencmd measure_temp 2>/dev/null || echo "temp=Unknown")

# Current GPU Voltage
$(vcgencmd measure_volts core 2>/dev/null || echo "volt=Unknown")

# Current Configuration Files
$(cat /boot/firmware/config.txt 2>/dev/null || echo "config.txt not found")
EOF
    
    log "Configuration backed up to: $backup_file"
}

# Configure GPU memory
configure_gpu_memory() {
    log "Configuring GPU memory to ${GPU_MEMORY}MB..."
    
    local config_file="/boot/firmware/config.txt"
    local temp_config="/tmp/config.txt.tmp"
    
    # Create backup
    cp "$config_file" "$temp_config"
    
    # Remove existing gpu_mem settings
    grep -v "^gpu_mem=" "$temp_config" > "$temp_config.new"
    mv "$temp_config.new" "$temp_config"
    
    # Add new gpu_mem setting
    echo "gpu_mem=${GPU_MEMORY}" >> "$temp_config"
    
    # Validate configuration
    if grep -q "gpu_mem=${GPU_MEMORY}" "$temp_config"; then
        log "GPU memory configuration validated"
    else
        die "Failed to configure GPU memory"
    fi
    
    # Apply configuration
    sudo cp "$temp_config" "$config_file"
    rm -f "$temp_config"
    
    log "GPU memory configured to ${GPU_MEMORY}MB"
}

# Configure GPU frequency
configure_gpu_frequency() {
    log "Configuring GPU frequency to ${GPU_FREQ}MHz..."
    
    local config_file="/boot/firmware/config.txt"
    local temp_config="/tmp/config.txt.tmp"
    
    # Create backup
    cp "$config_file" "$temp_config"
    
    # Remove existing gpu_freq settings
    grep -v "^gpu_freq=" "$temp_config" > "$temp_config.new"
    mv "$temp_config.new" "$temp_config"
    
    # Add new gpu_freq setting
    echo "gpu_freq=${GPU_FREQ}" >> "$temp_config"
    
    # Validate configuration
    if grep -q "gpu_freq=${GPU_FREQ}" "$temp_config"; then
        log "GPU frequency configuration validated"
    else
        die "Failed to configure GPU frequency"
    fi
    
    # Apply configuration
    sudo cp "$temp_config" "$config_file"
    rm -f "$temp_config"
    
    log "GPU frequency configured to ${GPU_FREQ}MHz"
}

# Configure overclocking
configure_overclocking() {
    if [[ "$OVERCLOCK" == "true" ]]; then
        log "Configuring GPU overclocking..."
        
        local config_file="/boot/firmware/config.txt"
        local temp_config="/tmp/config.txt.tmp"
        
        # Create backup
        cp "$config_file" "$temp_config"
        
        # Add overclocking settings
        cat >> "$temp_config" << 'EOF'

# Lucid RDP GPU Overclocking Configuration
# WARNING: Overclocking may void warranty and cause instability

# GPU overclocking
gpu_freq=600
arm_freq=2200
over_voltage=2

# Memory overclocking
sdram_freq=2400
sdram_schmoo=0x02000020

# Temperature monitoring
temp_limit=80
EOF
        
        # Apply configuration
        sudo cp "$temp_config" "$config_file"
        rm -f "$temp_config"
        
        log "GPU overclocking configured"
        warn "Overclocking enabled - monitor temperature and stability"
    else
        log "GPU overclocking disabled"
    fi
}

# Configure thermal protection
configure_thermal_protection() {
    if [[ "$THERMAL_PROTECTION" == "true" ]]; then
        log "Configuring thermal protection..."
        
        local config_file="/boot/firmware/config.txt"
        local temp_config="/tmp/config.txt.tmp"
        
        # Create backup
        cp "$config_file" "$temp_config"
        
        # Add thermal protection settings
        cat >> "$temp_config" << 'EOF'

# Lucid RDP Thermal Protection Configuration
# Thermal throttling and protection settings

# Temperature limit (degrees Celsius)
temp_limit=80

# Thermal throttling
dtparam=temp_limit=80
EOF
        
        # Apply configuration
        sudo cp "$temp_config" "$config_file"
        rm -f "$temp_config"
        
        log "Thermal protection configured"
    else
        log "Thermal protection disabled"
    fi
}

# Configure V4L2 M2M driver
configure_v4l2_driver() {
    log "Configuring V4L2 M2M driver..."
    
    local config_file="/boot/firmware/config.txt"
    local temp_config="/tmp/config.txt.tmp"
    
    # Create backup
    cp "$config_file" "$temp_config"
    
    # Remove existing V4L2 settings
    grep -v "^dtoverlay=vc4" "$temp_config" > "$temp_config.new"
    mv "$temp_config.new" "$temp_config"
    
    # Add V4L2 M2M driver
    echo "dtoverlay=vc4-kms-v3d" >> "$temp_config"
    
    # Apply configuration
    sudo cp "$temp_config" "$config_file"
    rm -f "$temp_config"
    
    log "V4L2 M2M driver configured"
}

# Create GPU monitoring script
create_gpu_monitor() {
    log "Creating GPU monitoring script..."
    
    local monitor_script="/opt/lucid/scripts/gpu-monitor.sh"
    
    sudo mkdir -p "$(dirname "$monitor_script")"
    
    sudo tee "$monitor_script" > /dev/null << 'EOF'
#!/bin/bash
# GPU monitoring script for Lucid RDP

LOG_FILE="/var/log/lucid-gpu-monitor.log"
MAX_LOG_SIZE=10485760  # 10MB

# Rotate log if too large
if [[ -f "$LOG_FILE" ]] && [[ $(stat -c%s "$LOG_FILE") -gt $MAX_LOG_SIZE ]]; then
    mv "$LOG_FILE" "${LOG_FILE}.old"
fi

# Log GPU status
{
    echo "=== GPU Status $(date) ==="
    echo "GPU Memory: $(vcgencmd get_mem gpu 2>/dev/null || echo 'Unknown')"
    echo "GPU Frequency: $(vcgencmd measure_clock gpu 2>/dev/null || echo 'Unknown')"
    echo "GPU Temperature: $(vcgencmd measure_temp 2>/dev/null || echo 'Unknown')"
    echo "GPU Voltage: $(vcgencmd measure_volts core 2>/dev/null || echo 'Unknown')"
    echo "GPU Throttling: $(vcgencmd get_throttled 2>/dev/null || echo 'Unknown')"
    echo ""
} >> "$LOG_FILE"

# Check for throttling
throttled=$(vcgencmd get_throttled 2>/dev/null | cut -d= -f2)
if [[ "$throttled" != "0x0" ]]; then
    echo "WARNING: GPU throttling detected: $throttled" >> "$LOG_FILE"
fi

# Check temperature
temp=$(vcgencmd measure_temp 2>/dev/null | cut -d= -f2 | cut -d\' -f1)
if [[ "$temp" -gt 70 ]]; then
    echo "WARNING: High GPU temperature: ${temp}°C" >> "$LOG_FILE"
fi
EOF
    
    sudo chmod +x "$monitor_script"
    
    log "GPU monitoring script created: $monitor_script"
}

# Create systemd service for GPU monitoring
create_gpu_monitor_service() {
    log "Creating GPU monitoring service..."
    
    local service_file="/etc/systemd/system/lucid-gpu-monitor.service"
    
    sudo tee "$service_file" > /dev/null << 'EOF'
[Unit]
Description=Lucid RDP GPU Monitor
After=network.target

[Service]
Type=simple
User=root
ExecStart=/opt/lucid/scripts/gpu-monitor.sh
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
EOF
    
    # Create timer for periodic monitoring
    local timer_file="/etc/systemd/system/lucid-gpu-monitor.timer"
    
    sudo tee "$timer_file" > /dev/null << 'EOF'
[Unit]
Description=Lucid RDP GPU Monitor Timer
Requires=lucid-gpu-monitor.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF
    
    # Enable and start the service
    sudo systemctl daemon-reload
    sudo systemctl enable lucid-gpu-monitor.timer
    sudo systemctl start lucid-gpu-monitor.timer
    
    log "GPU monitoring service created and started"
}

# Test GPU configuration
test_gpu_configuration() {
    log "Testing GPU configuration..."
    
    # Test GPU memory
    local gpu_mem
    gpu_mem=$(vcgencmd get_mem gpu 2>/dev/null | cut -d= -f2 | cut -dM -f1)
    if [[ "$gpu_mem" == "$GPU_MEMORY" ]]; then
        log "GPU memory test passed: ${gpu_mem}MB"
    else
        warn "GPU memory test failed: expected ${GPU_MEMORY}MB, got ${gpu_mem}MB"
    fi
    
    # Test GPU frequency
    local gpu_freq
    gpu_freq=$(vcgencmd measure_clock gpu 2>/dev/null | cut -d= -f2)
    if [[ "$gpu_freq" -gt 0 ]]; then
        log "GPU frequency test passed: ${gpu_freq}Hz"
    else
        warn "GPU frequency test failed: $gpu_freq"
    fi
    
    # Test GPU temperature
    local gpu_temp
    gpu_temp=$(vcgencmd measure_temp 2>/dev/null | cut -d= -f2 | cut -d\' -f1)
    if [[ "$gpu_temp" -lt 80 ]]; then
        log "GPU temperature test passed: ${gpu_temp}°C"
    else
        warn "GPU temperature test failed: ${gpu_temp}°C (too hot)"
    fi
    
    # Test V4L2 devices
    if ls /dev/video* >/dev/null 2>&1; then
        log "V4L2 devices test passed"
    else
        warn "V4L2 devices test failed - no devices found"
    fi
}

# Create GPU configuration report
create_gpu_report() {
    log "Creating GPU configuration report..."
    
    local report_file="/opt/lucid/reports/gpu-config-report.txt"
    
    sudo mkdir -p "$(dirname "$report_file")"
    
    sudo tee "$report_file" > /dev/null << EOF
Lucid RDP GPU Configuration Report
==================================
Date: $(date)
Pi Model: $(cat /proc/device-tree/model 2>/dev/null || echo "Unknown")
Script: $SCRIPT_NAME

Configuration Applied:
- GPU Memory: ${GPU_MEMORY}MB
- GPU Frequency: ${GPU_FREQ}MHz
- Overclocking: $OVERCLOCK
- Thermal Protection: $THERMAL_PROTECTION

Current GPU Status:
$(vcgencmd get_mem gpu 2>/dev/null || echo "GPU Memory: Unknown")
$(vcgencmd measure_clock gpu 2>/dev/null || echo "GPU Frequency: Unknown")
$(vcgencmd measure_temp 2>/dev/null || echo "GPU Temperature: Unknown")
$(vcgencmd measure_volts core 2>/dev/null || echo "GPU Voltage: Unknown")
$(vcgencmd get_throttled 2>/dev/null || echo "GPU Throttling: Unknown")

V4L2 Devices:
$(ls -la /dev/video* 2>/dev/null || echo "No V4L2 devices found")

Loaded Modules:
$(lsmod | grep -E "(v4l2|bcm2835|vc4)" || echo "No relevant modules loaded")

Configuration Files:
$(cat /boot/firmware/config.txt 2>/dev/null || echo "config.txt not found")

End of Report
EOF
    
    log "GPU configuration report created: $report_file"
}

# Main execution
main() {
    log "Starting Pi GPU configuration..."
    log "GPU Memory: ${GPU_MEMORY}MB"
    log "GPU Frequency: ${GPU_FREQ}MHz"
    log "Overclocking: $OVERCLOCK"
    log "Thermal Protection: $THERMAL_PROTECTION"
    
    # Check Pi model
    check_pi_model
    
    # Check current configuration
    check_current_gpu_config
    
    # Backup current configuration
    backup_config
    
    # Configure GPU
    configure_gpu_memory
    configure_gpu_frequency
    configure_overclocking
    configure_thermal_protection
    configure_v4l2_driver
    
    # Create monitoring
    create_gpu_monitor
    create_gpu_monitor_service
    
    # Test configuration
    test_gpu_configuration
    
    # Create report
    create_gpu_report
    
    log "Pi GPU configuration completed successfully"
    log "Reboot required for changes to take effect"
    log "GPU monitoring service started"
    log "Report available at: /opt/lucid/reports/gpu-config-report.txt"
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
