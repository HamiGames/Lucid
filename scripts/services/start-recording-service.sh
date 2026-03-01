#!/bin/bash
# RDP Recording Service Startup Script
# LUCID-STRICT Layer 2 Service Management
# Purpose: Start session recording service for RDP recording
# Compatibility: Distroless, API compliant
# Generated: 2025-01-27

set -e

# Configuration
COMPOSE_FILE="${LUCID_COMPOSE_FILE:-/opt/lucid/docker-compose.yml}"
SERVICE_NAME="${RECORDING_SERVICE_NAME:-lucid-recording}"
LOG_FILE="${LOG_FILE:-/var/log/lucid/recording-service.log}"
RECORDING_DIR="${RECORDING_DIR:-/data/recordings}"
FFMPEG_PATH="${FFMPEG_PATH:-/usr/local/bin/ffmpeg}"
XRDP_PORT="${XRDP_PORT:-3389}"
RECORDING_QUALITY="${RECORDING_QUALITY:-medium}"
RECORDING_FORMAT="${RECORDING_FORMAT:-mp4}"
MAX_RECORDING_SIZE="${MAX_RECORDING_SIZE:-1GB}"
RECORDING_RETENTION_DAYS="${RECORDING_RETENTION_DAYS:-30}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${1}" | tee -a "$LOG_FILE"
}

log_info() {
    log "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    log "${GREEN}✅ $1${NC}"
}

log_warning() {
    log "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    log "${RED}❌ $1${NC}"
}

# Create directories if they don't exist
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$RECORDING_DIR"

echo "========================================"
log_info "🎥 LUCID RDP Recording Service"
echo "========================================"

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Start session recording service for RDP recording"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -f, --force             Force start without confirmation"
    echo "  -s, --stop              Stop recording service"
    echo "  -r, --restart           Restart recording service"
    echo "  -d, --daemon            Run in daemon mode"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -c, --check             Check service status"
    echo "  -l, --logs              Show service logs"
    echo "  -t, --test              Test recording functionality"
    echo "  --quality QUALITY       Set recording quality (low,medium,high)"
    echo "  --format FORMAT         Set recording format (mp4,avi,mkv)"
    echo "  --max-size SIZE         Set max recording size (e.g., 1GB, 500MB)"
    echo "  --retention DAYS        Set recording retention in days"
    echo ""
    echo "Environment Variables:"
    echo "  LUCID_COMPOSE_FILE      Docker compose file path"
    echo "  RECORDING_SERVICE_NAME  Service name (default: lucid-recording)"
    echo "  RECORDING_DIR           Recording directory (default: /data/recordings)"
    echo "  FFMPEG_PATH             FFmpeg binary path"
    echo "  XRDP_PORT               XRDP port (default: 3389)"
    echo "  RECORDING_QUALITY       Recording quality (default: medium)"
    echo "  RECORDING_FORMAT        Recording format (default: mp4)"
    echo "  MAX_RECORDING_SIZE      Max recording size (default: 1GB)"
    echo "  RECORDING_RETENTION_DAYS Recording retention (default: 30)"
    echo ""
    echo "Examples:"
    echo "  $0 --quality high --format mp4  Start with high quality MP4 recording"
    echo "  $0 --stop                       Stop recording service"
    echo "  $0 --restart                    Restart recording service"
    echo "  $0 --test                       Test recording functionality"
}

# Parse command line arguments
FORCE=false
ACTION="start"
DAEMON_MODE=false
VERBOSE=false
CHECK_STATUS=false
SHOW_LOGS=false
TEST_RECORDING=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -s|--stop)
            ACTION="stop"
            shift
            ;;
        -r|--restart)
            ACTION="restart"
            shift
            ;;
        -d|--daemon)
            DAEMON_MODE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--check)
            CHECK_STATUS=true
            shift
            ;;
        -l|--logs)
            SHOW_LOGS=true
            shift
            ;;
        -t|--test)
            TEST_RECORDING=true
            shift
            ;;
        --quality)
            RECORDING_QUALITY="$2"
            shift 2
            ;;
        --format)
            RECORDING_FORMAT="$2"
            shift 2
            ;;
        --max-size)
            MAX_RECORDING_SIZE="$2"
            shift 2
            ;;
        --retention)
            RECORDING_RETENTION_DAYS="$2"
            shift 2
            ;;
        -*)
            log_error "Unknown option $1"
            show_usage
            exit 1
            ;;
        *)
            log_error "Unexpected argument: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Function to check Docker availability
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not available"
        return 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        return 1
    fi
    
    log_success "Docker is available and running"
    return 0
}

# Function to check FFmpeg availability
check_ffmpeg() {
    if [[ ! -f "$FFMPEG_PATH" ]]; then
        log_error "FFmpeg not found at: $FFMPEG_PATH"
        log_info "Please ensure FFmpeg is installed and path is correct"
        return 1
    fi
    
    # Test FFmpeg functionality
    if "$FFMPEG_PATH" -version &> /dev/null; then
        local ffmpeg_version=$("$FFMPEG_PATH" -version 2>&1 | head -1)
        log_success "FFmpeg is available: $ffmpeg_version"
        return 0
    else
        log_error "FFmpeg is not functional"
        return 1
    fi
}

# Function to check hardware acceleration
check_hardware_acceleration() {
    log_info "Checking hardware acceleration support..."
    
    # Check for V4L2 M2M (Pi 5 hardware acceleration)
    if [[ -d "/dev/video10" ]]; then
        log_success "V4L2 M2M device found: /dev/video10"
        
        # Test hardware encoder availability
        if "$FFMPEG_PATH" -f lavfi -i testsrc=duration=1:size=320x240:rate=1 -c:v h264_v4l2m2m -f null - 2>/dev/null; then
            log_success "Hardware H.264 encoder (V4L2 M2M) is functional"
            return 0
        else
            log_warning "Hardware H.264 encoder (V4L2 M2M) test failed"
        fi
    else
        log_warning "V4L2 M2M device not found, using software encoding"
    fi
    
    # Check for other hardware encoders
    if "$FFMPEG_PATH" -encoders 2>/dev/null | grep -q "h264_nvenc"; then
        log_info "NVIDIA hardware encoder available"
    fi
    
    if "$FFMPEG_PATH" -encoders 2>/dev/null | grep -q "h264_qsv"; then
        log_info "Intel Quick Sync hardware encoder available"
    fi
    
    return 0
}

# Function to check service status
check_service_status() {
    log_info "Checking recording service status..."
    
    if [[ -f "$COMPOSE_FILE" ]]; then
        if docker-compose -f "$COMPOSE_FILE" ps "$SERVICE_NAME" &>/dev/null; then
            local status=$(docker-compose -f "$COMPOSE_FILE" ps "$SERVICE_NAME" --format "table {{.State}}" | tail -1)
            log_info "Service status: $status"
            
            if [[ "$status" == "Up" ]]; then
                log_success "Recording service is running"
                return 0
            else
                log_warning "Recording service is not running"
                return 1
            fi
        else
            log_warning "Service not found in compose file"
            return 1
        fi
    else
        log_error "Compose file not found: $COMPOSE_FILE"
        return 1
    fi
}

# Function to show service logs
show_service_logs() {
    log_info "Showing recording service logs..."
    
    if [[ -f "$COMPOSE_FILE" ]]; then
        docker-compose -f "$COMPOSE_FILE" logs --tail=50 "$SERVICE_NAME"
    else
        log_error "Compose file not found: $COMPOSE_FILE"
        return 1
    fi
}

# Function to test recording functionality
test_recording() {
    log_info "Testing recording functionality..."
    
    # Create test recording directory
    local test_dir="$RECORDING_DIR/test-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$test_dir"
    
    # Test FFmpeg recording
    log_info "Testing FFmpeg recording..."
    
    local test_file="$test_dir/test-recording.mp4"
    local test_duration=5
    
    # Test with different encoders
    local encoders=("libx264")
    
    # Add hardware encoders if available
    if [[ -d "/dev/video10" ]]; then
        encoders+=("h264_v4l2m2m")
    fi
    
    local success=false
    for encoder in "${encoders[@]}"; do
        log_info "Testing encoder: $encoder"
        
        if "$FFMPEG_PATH" -f lavfi -i testsrc=duration=$test_duration:size=640x480:rate=30 \
            -c:v "$encoder" -preset fast -crf 23 \
            -c:a aac -b:a 128k \
            -y "$test_file" 2>/dev/null; then
            
            if [[ -f "$test_file" && -s "$test_file" ]]; then
                local file_size=$(stat -c %s "$test_file" 2>/dev/null || stat -f %z "$test_file" 2>/dev/null || echo "unknown")
                log_success "Test recording successful with $encoder (size: $file_size bytes)"
                success=true
                break
            else
                log_warning "Test recording failed with $encoder (no output file)"
            fi
        else
            log_warning "Test recording failed with $encoder"
        fi
    done
    
    # Test XRDP connection
    log_info "Testing XRDP connection..."
    if nc -z localhost "$XRDP_PORT" 2>/dev/null; then
        log_success "XRDP port $XRDP_PORT is accessible"
    else
        log_warning "XRDP port $XRDP_PORT is not accessible"
    fi
    
    # Cleanup test files
    rm -rf "$test_dir"
    
    if [[ "$success" == "true" ]]; then
        log_success "Recording functionality test passed"
        return 0
    else
        log_error "Recording functionality test failed"
        return 1
    fi
}

# Function to start recording service
start_recording_service() {
    log_info "Starting recording service..."
    
    # Check prerequisites
    if ! check_docker; then
        return 1
    fi
    
    if ! check_ffmpeg; then
        return 1
    fi
    
    check_hardware_acceleration
    
    # Check if service is already running
    if check_service_status &>/dev/null; then
        log_warning "Recording service is already running"
        if [[ "$FORCE" == "false" ]]; then
            read -p "Restart the service? (yes/no): " confirm
            if [[ "$confirm" == "yes" ]]; then
                stop_recording_service
            else
                log_info "Service start cancelled"
                return 0
            fi
        else
            stop_recording_service
        fi
    fi
    
    # Start service using docker-compose
    if [[ -f "$COMPOSE_FILE" ]]; then
        log_info "Starting service from compose file: $COMPOSE_FILE"
        
        # Set environment variables for the service
        export RECORDING_QUALITY="$RECORDING_QUALITY"
        export RECORDING_FORMAT="$RECORDING_FORMAT"
        export MAX_RECORDING_SIZE="$MAX_RECORDING_SIZE"
        export RECORDING_RETENTION_DAYS="$RECORDING_RETENTION_DAYS"
        export FFMPEG_PATH="$FFMPEG_PATH"
        export RECORDING_DIR="$RECORDING_DIR"
        
        if docker-compose -f "$COMPOSE_FILE" up -d "$SERVICE_NAME"; then
            log_success "Recording service started successfully"
            
            # Wait for service to be ready
            log_info "Waiting for service to be ready..."
            sleep 5
            
            if check_service_status; then
                log_success "Recording service is running and healthy"
                return 0
            else
                log_error "Recording service started but is not healthy"
                return 1
            fi
        else
            log_error "Failed to start recording service"
            return 1
        fi
    else
        log_error "Compose file not found: $COMPOSE_FILE"
        log_info "Please ensure the compose file exists and contains the recording service"
        return 1
    fi
}

# Function to stop recording service
stop_recording_service() {
    log_info "Stopping recording service..."
    
    if [[ -f "$COMPOSE_FILE" ]]; then
        if docker-compose -f "$COMPOSE_FILE" stop "$SERVICE_NAME"; then
            log_success "Recording service stopped successfully"
            return 0
        else
            log_error "Failed to stop recording service"
            return 1
        fi
    else
        log_error "Compose file not found: $COMPOSE_FILE"
        return 1
    fi
}

# Function to restart recording service
restart_recording_service() {
    log_info "Restarting recording service..."
    
    if stop_recording_service; then
        sleep 2
        if start_recording_service; then
            log_success "Recording service restarted successfully"
            return 0
        else
            log_error "Failed to restart recording service"
            return 1
        fi
    else
        log_error "Failed to stop recording service for restart"
        return 1
    fi
}

# Function to cleanup old recordings
cleanup_old_recordings() {
    log_info "Cleaning up old recordings (older than $RECORDING_RETENTION_DAYS days)..."
    
    local old_recordings=($(find "$RECORDING_DIR" -name "*.mp4" -o -name "*.avi" -o -name "*.mkv" -type f -mtime +$RECORDING_RETENTION_DAYS))
    
    if [[ ${#old_recordings[@]} -eq 0 ]]; then
        log_info "No old recordings to cleanup"
        return 0
    fi
    
    local removed=0
    for old_recording in "${old_recordings[@]}"; do
        if rm "$old_recording"; then
            log_info "Removed old recording: $(basename "$old_recording")"
            ((removed++))
        else
            log_warning "Failed to remove old recording: $(basename "$old_recording")"
        fi
    done
    
    log_success "Cleaned up $removed old recordings"
}

# Main function
main() {
    # Handle special operations
    if [[ "$CHECK_STATUS" == "true" ]]; then
        check_service_status
        return $?
    fi
    
    if [[ "$SHOW_LOGS" == "true" ]]; then
        show_service_logs
        return 0
    fi
    
    if [[ "$TEST_RECORDING" == "true" ]]; then
        test_recording
        return $?
    fi
    
    # Handle main actions
    case "$ACTION" in
        "start")
            start_recording_service
            ;;
        "stop")
            stop_recording_service
            ;;
        "restart")
            restart_recording_service
            ;;
        *)
            log_error "Unknown action: $ACTION"
            show_usage
            exit 1
            ;;
    esac
    
    # Cleanup old recordings after successful start
    if [[ "$ACTION" == "start" && $? -eq 0 ]]; then
        cleanup_old_recordings
    fi
}

# Set up signal handlers
cleanup() {
    log_info "Cleaning up..."
    # Cleanup will be handled by individual functions
}

trap cleanup EXIT INT TERM

# Run main function
main "$@"
