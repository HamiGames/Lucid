#!/bin/bash
# build/scripts/setup-hardware-accel.sh
# Setup Pi 5 hardware acceleration for distroless containers
# LUCID-STRICT: Pi 5 V4L2 hardware acceleration configuration

set -Eeuo pipefail

# Script metadata
SCRIPT_NAME="$(basename "$0")"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_PATH/../.." && pwd)"

# Configuration
PI_HOST="${PI_HOST:-192.168.0.75}"
PI_USER="${PI_USER:-pickme}"
GPU_MEMORY="${GPU_MEMORY:-128}"
V4L2M2M_ENABLED="${V4L2M2M_ENABLED:-true}"

# Logging
log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*"; }
die() { printf '[%s][ERROR] %s\n' "$SCRIPT_NAME" "$*" >&2; exit 1; }
warn() { printf '[%s][WARN] %s\n' "$SCRIPT_NAME" "$*" >&2; }

# SSH connection helper
ssh_pi() {
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$PI_USER@$PI_HOST" "$@"
}

# Check Pi 5 hardware
check_pi_hardware() {
    log "Checking Pi 5 hardware capabilities..."
    
    ssh_pi "uname -m" | grep -q "aarch64" || die "Not running on ARM64 architecture"
    ssh_pi "cat /proc/cpuinfo | grep -q 'BCM2712'" || warn "May not be Pi 5 hardware"
    ssh_pi "lsmod | grep -q v4l2" || warn "V4L2 modules not loaded"
    
    log "Pi 5 hardware check completed"
}

# Configure GPU memory allocation
configure_gpu_memory() {
    log "Configuring GPU memory allocation..."
    
    local config_cmd="cat > /boot/firmware/config.txt << 'EOF'
# Lucid RDP Pi 5 Hardware Acceleration Configuration
# GPU memory allocation for hardware video encoding
gpu_mem=${GPU_MEMORY}

# Enable V4L2 M2M driver for hardware codecs
dtoverlay=vc4-kms-v3d

# Enable hardware codec support
dtoverlay=imx477
dtoverlay=imx519

# Disable overscan for full resolution
disable_overscan=1

# Enable hardware acceleration
gpu_mem_1024=1
EOF"
    
    ssh_pi "sudo bash -c '$config_cmd'" || die "Failed to configure GPU memory"
    
    log "GPU memory configured to ${GPU_MEMORY}MB"
}

# Install V4L2 utilities
install_v4l2_utils() {
    log "Installing V4L2 utilities..."
    
    ssh_pi "sudo apt-get update && sudo apt-get install -y \
        v4l-utils \
        libv4l-dev \
        libv4l2-0 \
        media-ctl \
        yavta" || die "Failed to install V4L2 utilities"
    
    log "V4L2 utilities installed"
}

# Configure V4L2 M2M devices
configure_v4l2_devices() {
    log "Configuring V4L2 M2M devices..."
    
    # Create udev rules for V4L2 devices
    local udev_rules="cat > /etc/udev/rules.d/99-lucid-v4l2.rules << 'EOF'
# Lucid RDP V4L2 M2M Device Rules
# Allow distroless containers access to video devices

# V4L2 M2M encoder devices
SUBSYSTEM==\"video4linux\", KERNEL==\"video[0-9]*\", GROUP=\"video\", MODE=\"0664\"
SUBSYSTEM==\"video4linux\", KERNEL==\"video[0-9]*\", ATTRS{name}==\"bcm2835-codec-enc\", GROUP=\"video\", MODE=\"0664\"
SUBSYSTEM==\"video4linux\", KERNEL==\"video[0-9]*\", ATTRS{name}==\"bcm2835-codec-dec\", GROUP=\"video\", MODE=\"0664\"

# V4L2 M2M devices
SUBSYSTEM==\"misc\", KERNEL==\"v4l2m2m\", GROUP=\"video\", MODE=\"0664\"

# Device permissions for distroless containers
KERNEL==\"video[0-9]*\", GROUP=\"video\", MODE=\"0664\"
KERNEL==\"v4l2m2m\", GROUP=\"video\", MODE=\"0664\"
EOF"
    
    ssh_pi "sudo bash -c '$udev_rules'" || die "Failed to create udev rules"
    ssh_pi "sudo udevadm control --reload-rules" || die "Failed to reload udev rules"
    
    log "V4L2 device configuration completed"
}

# Create hardware acceleration test script
create_test_script() {
    log "Creating hardware acceleration test script..."
    
    local test_script="cat > /opt/lucid/scripts/test-hw-accel.sh << 'EOF'
#!/bin/bash
# Hardware acceleration test script for Pi 5

echo \"Testing Pi 5 hardware acceleration...\"

# Check V4L2 devices
echo \"V4L2 Devices:\"
ls -la /dev/video* 2>/dev/null || echo \"No V4L2 devices found\"

# Check V4L2 M2M devices
echo \"V4L2 M2M Devices:\"
ls -la /dev/v4l2m2m* 2>/dev/null || echo \"No V4L2 M2M devices found\"

# Check loaded modules
echo \"Loaded V4L2 modules:\"
lsmod | grep -E \"(v4l2|bcm2835|vc4)\"

# Test hardware codec capabilities
echo \"Testing hardware codec capabilities...\"
if command -v v4l2-ctl >/dev/null 2>&1; then
    for device in /dev/video*; do
        if [[ -c \"\$device\" ]]; then
            echo \"Device: \$device\"
            v4l2-ctl --device=\"\$device\" --list-formats-ext 2>/dev/null || true
        fi
    done
fi

# Test FFmpeg hardware acceleration
echo \"Testing FFmpeg hardware acceleration...\"
if command -v ffmpeg >/dev/null 2>&1; then
    ffmpeg -f lavfi -i testsrc=duration=1:size=1920x1080:rate=30 \
        -c:v h264_v4l2m2m -b:v 2M \
        -f null - 2>&1 | grep -E \"(h264_v4l2m2m|fps|bitrate)\" || echo \"Hardware acceleration test failed\"
else
    echo \"FFmpeg not found\"
fi

echo \"Hardware acceleration test completed\"
EOF"
    
    ssh_pi "sudo bash -c '$test_script'" || die "Failed to create test script"
    ssh_pi "sudo chmod +x /opt/lucid/scripts/test-hw-accel.sh" || die "Failed to make test script executable"
    
    log "Hardware acceleration test script created"
}

# Configure Docker for hardware access
configure_docker_hardware() {
    log "Configuring Docker for hardware access..."
    
    # Create Docker daemon configuration
    local docker_config="cat > /etc/docker/daemon.json << 'EOF'
{
    \"default-runtime\": \"runc\",
    \"runtimes\": {
        \"runc\": {
            \"path\": \"runc\"
        }
    },
    \"exec-opts\": [\"native.cgroupdriver=systemd\"],
    \"log-driver\": \"json-file\",
    \"log-opts\": {
        \"max-size\": \"100m\",
        \"max-file\": \"3\"
    },
    \"storage-driver\": \"overlay2\",
    \"storage-opts\": [
        \"overlay2.override_kernel_check=true\"
    ],
    \"device-cgroup-rules\": [
        \"c 81:* rmw\",
        \"c 10:* rmw\"
    ]
}
EOF"
    
    ssh_pi "sudo bash -c '$docker_config'" || die "Failed to configure Docker daemon"
    ssh_pi "sudo systemctl restart docker" || die "Failed to restart Docker"
    
    log "Docker configured for hardware access"
}

# Create distroless container configuration
create_distroless_config() {
    log "Creating distroless container configuration..."
    
    local container_config="cat > /opt/lucid/configs/hardware-accel.yml << 'EOF'
# Lucid RDP Hardware Acceleration Configuration
# Distroless container configuration for Pi 5

version: '3.8'

services:
  ffmpeg-hardware:
    image: pickme/lucid:ffmpeg-pi5-latest
    container_name: lucid-ffmpeg-hw
    privileged: false
    user: \"65532:video\"
    devices:
      - /dev/video0:/dev/video0
      - /dev/v4l2m2m:/dev/v4l2m2m
    volumes:
      - /tmp/lucid-ffmpeg:/tmp
    environment:
      - V4L2M2M_ENABLED=true
      - HARDWARE_DECODE=true
      - GPU_MEMORY=${GPU_MEMORY}
    command: [\"ffmpeg\", \"-f\", \"lavfi\", \"-i\", \"testsrc=duration=10:size=1920x1080:rate=30\", \"-c:v\", \"h264_v4l2m2m\", \"-b:v\", \"2M\", \"-f\", \"mp4\", \"/tmp/test.mp4\"]
    restart: unless-stopped
    networks:
      - lucid_net

networks:
  lucid_net:
    external: true
EOF"
    
    ssh_pi "sudo bash -c '$container_config'" || die "Failed to create container configuration"
    
    log "Distroless container configuration created"
}

# Test hardware acceleration
test_hardware_acceleration() {
    log "Testing hardware acceleration setup..."
    
    # Run the test script
    ssh_pi "sudo /opt/lucid/scripts/test-hw-accel.sh" || warn "Hardware acceleration test failed"
    
    # Test with Docker container
    log "Testing hardware acceleration with Docker container..."
    ssh_pi "sudo docker run --rm --device=/dev/video0 --device=/dev/v4l2m2m \
        -v /tmp/lucid-test:/tmp \
        pickme/lucid:ffmpeg-pi5-latest \
        ffmpeg -f lavfi -i testsrc=duration=5:size=1280x720:rate=30 \
        -c:v h264_v4l2m2m -b:v 1M \
        -f mp4 /tmp/hw-test.mp4" || warn "Docker hardware acceleration test failed"
    
    log "Hardware acceleration testing completed"
}

# Create systemd service for hardware monitoring
create_hardware_monitor() {
    log "Creating hardware monitoring service..."
    
    local monitor_service="cat > /etc/systemd/system/lucid-hardware-monitor.service << 'EOF'
[Unit]
Description=Lucid RDP Hardware Acceleration Monitor
After=network.target

[Service]
Type=simple
User=root
ExecStart=/opt/lucid/scripts/hardware-monitor.sh
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF"
    
    local monitor_script="cat > /opt/lucid/scripts/hardware-monitor.sh << 'EOF'
#!/bin/bash
# Hardware acceleration monitor for Pi 5

while true; do
    # Check V4L2 devices
    if ! ls /dev/video* >/dev/null 2>&1; then
        echo \"\$(date): V4L2 devices not available\" >> /var/log/lucid-hardware.log
    fi
    
    # Check GPU memory usage
    vcgencmd get_mem gpu >> /var/log/lucid-hardware.log
    
    # Check temperature
    vcgencmd measure_temp >> /var/log/lucid-hardware.log
    
    sleep 60
done
EOF"
    
    ssh_pi "sudo bash -c '$monitor_service'" || die "Failed to create monitor service"
    ssh_pi "sudo bash -c '$monitor_script'" || die "Failed to create monitor script"
    ssh_pi "sudo chmod +x /opt/lucid/scripts/hardware-monitor.sh" || die "Failed to make monitor script executable"
    ssh_pi "sudo systemctl enable lucid-hardware-monitor" || die "Failed to enable monitor service"
    
    log "Hardware monitoring service created"
}

# Main execution
main() {
    log "Starting Pi 5 hardware acceleration setup..."
    log "Target Pi: $PI_USER@$PI_HOST"
    log "GPU Memory: ${GPU_MEMORY}MB"
    
    # Check hardware
    check_pi_hardware
    
    # Configure GPU memory
    configure_gpu_memory
    
    # Install V4L2 utilities
    install_v4l2_utils
    
    # Configure V4L2 devices
    configure_v4l2_devices
    
    # Create test script
    create_test_script
    
    # Configure Docker
    configure_docker_hardware
    
    # Create distroless configuration
    create_distroless_config
    
    # Test hardware acceleration
    test_hardware_acceleration
    
    # Create monitoring service
    create_hardware_monitor
    
    log "Pi 5 hardware acceleration setup completed successfully"
    log "Reboot required for GPU memory changes to take effect"
    log "Test script available at: /opt/lucid/scripts/test-hw-accel.sh"
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
