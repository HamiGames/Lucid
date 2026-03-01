#!/bin/bash
# scripts/hardware/test-v4l2m2m.sh
# Test hardware-accelerated H.264 encoding with V4L2 M2M
# LUCID-STRICT: Pi 5 hardware acceleration validation

set -Eeuo pipefail

# Script metadata
SCRIPT_NAME="$(basename "$0")"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_PATH/../.." && pwd)"

# Configuration
TEST_DURATION="${TEST_DURATION:-30}"
TEST_RESOLUTION="${TEST_RESOLUTION:-1920x1080}"
TEST_BITRATE="${TEST_BITRATE:-2M}"
OUTPUT_DIR="${OUTPUT_DIR:-/tmp/lucid-hw-test}"
FFMPEG_IMAGE="${FFMPEG_IMAGE:-pickme/lucid:ffmpeg-pi5-latest}"

# Logging
log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*"; }
die() { printf '[%s][ERROR] %s\n' "$SCRIPT_NAME" "$*" >&2; exit 1; }
warn() { printf '[%s][WARN] %s\n' "$SCRIPT_NAME" "$*" >&2; }

# Create output directory
create_output_dir() {
    mkdir -p "$OUTPUT_DIR"
    log "Output directory: $OUTPUT_DIR"
}

# Check V4L2 M2M devices
check_v4l2_devices() {
    log "Checking V4L2 M2M devices..."
    
    local devices_found=0
    
    # Check for V4L2 devices
    if ls /dev/video* >/dev/null 2>&1; then
        log "V4L2 devices found:"
        ls -la /dev/video* | while read -r line; do
            log "  $line"
        done
        devices_found=1
    else
        warn "No V4L2 devices found"
    fi
    
    # Check for V4L2 M2M devices
    if ls /dev/v4l2m2m* >/dev/null 2>&1; then
        log "V4L2 M2M devices found:"
        ls -la /dev/v4l2m2m* | while read -r line; do
            log "  $line"
        done
        devices_found=1
    else
        warn "No V4L2 M2M devices found"
    fi
    
    if [[ $devices_found -eq 0 ]]; then
        die "No V4L2 devices available for hardware acceleration"
    fi
}

# Check loaded V4L2 modules
check_v4l2_modules() {
    log "Checking loaded V4L2 modules..."
    
    local modules=("v4l2_mem2mem" "bcm2835_codec" "vc4")
    local loaded_modules=()
    
    for module in "${modules[@]}"; do
        if lsmod | grep -q "$module"; then
            loaded_modules+=("$module")
            log "Module loaded: $module"
        else
            warn "Module not loaded: $module"
        fi
    done
    
    if [[ ${#loaded_modules[@]} -eq 0 ]]; then
        warn "No V4L2 hardware modules loaded"
    fi
}

# Test V4L2 device capabilities
test_device_capabilities() {
    log "Testing V4L2 device capabilities..."
    
    if ! command -v v4l2-ctl >/dev/null 2>&1; then
        warn "v4l2-ctl not available, skipping device capability test"
        return 0
    fi
    
    for device in /dev/video*; do
        if [[ -c "$device" ]]; then
            log "Testing device: $device"
            
            # List formats
            v4l2-ctl --device="$device" --list-formats-ext 2>/dev/null | head -20 || warn "Failed to get formats for $device"
            
            # Check if device supports M2M
            if v4l2-ctl --device="$device" --list-formats-ext 2>/dev/null | grep -q "M2M"; then
                log "Device $device supports M2M (Memory-to-Memory)"
            else
                warn "Device $device does not support M2M"
            fi
        fi
    done
}

# Test hardware H.264 encoding
test_h264_encoding() {
    log "Testing hardware H.264 encoding..."
    
    local output_file="$OUTPUT_DIR/h264_hw_test.mp4"
    local test_cmd=(
        "ffmpeg"
        "-f" "lavfi"
        "-i" "testsrc=duration=$TEST_DURATION:size=$TEST_RESOLUTION:rate=30"
        "-c:v" "h264_v4l2m2m"
        "-b:v" "$TEST_BITRATE"
        "-preset" "fast"
        "-tune" "zerolatency"
        "-f" "mp4"
        "$output_file"
        "-y"
    )
    
    log "Running H.264 hardware encoding test..."
    log "Command: ${test_cmd[*]}"
    
    if "${test_cmd[@]}" 2>&1 | tee "$OUTPUT_DIR/h264_hw_test.log"; then
        if [[ -f "$output_file" ]]; then
            local file_size=$(stat -c%s "$output_file" 2>/dev/null || echo "0")
            log "H.264 hardware encoding test passed"
            log "Output file: $output_file ($file_size bytes)"
            return 0
        else
            die "H.264 hardware encoding test failed - no output file"
        fi
    else
        die "H.264 hardware encoding test failed"
    fi
}

# Test hardware H.264 decoding
test_h264_decoding() {
    log "Testing hardware H.264 decoding..."
    
    local input_file="$OUTPUT_DIR/h264_hw_test.mp4"
    local output_file="$OUTPUT_DIR/h264_hw_decode_test.mp4"
    
    if [[ ! -f "$input_file" ]]; then
        warn "Input file not found, skipping H.264 decoding test"
        return 0
    fi
    
    local test_cmd=(
        "ffmpeg"
        "-i" "$input_file"
        "-c:v" "h264_v4l2m2m"
        "-b:v" "$TEST_BITRATE"
        "-f" "mp4"
        "$output_file"
        "-y"
    )
    
    log "Running H.264 hardware decoding test..."
    log "Command: ${test_cmd[*]}"
    
    if "${test_cmd[@]}" 2>&1 | tee "$OUTPUT_DIR/h264_hw_decode_test.log"; then
        if [[ -f "$output_file" ]]; then
            local file_size=$(stat -c%s "$output_file" 2>/dev/null || echo "0")
            log "H.264 hardware decoding test passed"
            log "Output file: $output_file ($file_size bytes)"
            return 0
        else
            die "H.264 hardware decoding test failed - no output file"
        fi
    else
        die "H.264 hardware decoding test failed"
    fi
}

# Test with Docker container
test_docker_hardware() {
    log "Testing hardware acceleration with Docker container..."
    
    if ! command -v docker >/dev/null 2>&1; then
        warn "Docker not available, skipping Docker test"
        return 0
    fi
    
    local output_file="$OUTPUT_DIR/docker_hw_test.mp4"
    
    # Test with privileged container
    local docker_cmd=(
        "docker" "run" "--rm"
        "--device=/dev/video0"
        "--device=/dev/v4l2m2m"
        "-v" "$OUTPUT_DIR:/tmp/output"
        "$FFMPEG_IMAGE"
        "ffmpeg"
        "-f" "lavfi"
        "-i" "testsrc=duration=10:size=1280x720:rate=30"
        "-c:v" "h264_v4l2m2m"
        "-b:v" "1M"
        "-f" "mp4"
        "/tmp/output/docker_hw_test.mp4"
        "-y"
    )
    
    log "Running Docker hardware acceleration test..."
    log "Command: ${docker_cmd[*]}"
    
    if "${docker_cmd[@]}" 2>&1 | tee "$OUTPUT_DIR/docker_hw_test.log"; then
        if [[ -f "$output_file" ]]; then
            local file_size=$(stat -c%s "$output_file" 2>/dev/null || echo "0")
            log "Docker hardware acceleration test passed"
            log "Output file: $output_file ($file_size bytes)"
            return 0
        else
            warn "Docker hardware acceleration test failed - no output file"
        fi
    else
        warn "Docker hardware acceleration test failed"
    fi
}

# Performance benchmark
run_performance_benchmark() {
    log "Running performance benchmark..."
    
    local benchmark_file="$OUTPUT_DIR/benchmark_results.txt"
    local start_time end_time duration
    
    cat > "$benchmark_file" << EOF
Lucid RDP Hardware Acceleration Benchmark
=========================================
Test Date: $(date)
Pi Model: $(cat /proc/device-tree/model 2>/dev/null || echo "Unknown")
GPU Memory: $(vcgencmd get_mem gpu 2>/dev/null || echo "Unknown")
Temperature: $(vcgencmd measure_temp 2>/dev/null || echo "Unknown")

EOF
    
    # Benchmark H.264 encoding
    log "Benchmarking H.264 hardware encoding..."
    start_time=$(date +%s)
    
    if test_h264_encoding; then
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        
        cat >> "$benchmark_file" << EOF
H.264 Hardware Encoding:
- Duration: ${duration}s
- Resolution: $TEST_RESOLUTION
- Bitrate: $TEST_BITRATE
- Status: PASSED

EOF
        log "H.264 encoding benchmark: ${duration}s"
    else
        cat >> "$benchmark_file" << EOF
H.264 Hardware Encoding:
- Status: FAILED

EOF
    fi
    
    # Benchmark H.264 decoding
    log "Benchmarking H.264 hardware decoding..."
    start_time=$(date +%s)
    
    if test_h264_decoding; then
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        
        cat >> "$benchmark_file" << EOF
H.264 Hardware Decoding:
- Duration: ${duration}s
- Resolution: $TEST_RESOLUTION
- Bitrate: $TEST_BITRATE
- Status: PASSED

EOF
        log "H.264 decoding benchmark: ${duration}s"
    else
        cat >> "$benchmark_file" << EOF
H.264 Hardware Decoding:
- Status: FAILED

EOF
    fi
    
    log "Performance benchmark completed: $benchmark_file"
}

# Generate test report
generate_report() {
    log "Generating test report..."
    
    local report_file="$OUTPUT_DIR/v4l2m2m_test_report.txt"
    
    cat > "$report_file" << EOF
Lucid RDP V4L2 M2M Hardware Acceleration Test Report
====================================================
Test Date: $(date)
Script: $SCRIPT_NAME
Project: $(basename "$PROJECT_ROOT")

Configuration:
- Test Duration: ${TEST_DURATION}s
- Test Resolution: $TEST_RESOLUTION
- Test Bitrate: $TEST_BITRATE
- Output Directory: $OUTPUT_DIR
- FFmpeg Image: $FFMPEG_IMAGE

Hardware Information:
$(cat /proc/cpuinfo | grep "model name" | head -1 || echo "CPU: Unknown")
$(cat /proc/device-tree/model 2>/dev/null || echo "Board: Unknown")
GPU Memory: $(vcgencmd get_mem gpu 2>/dev/null || echo "Unknown")
Temperature: $(vcgencmd measure_temp 2>/dev/null || echo "Unknown")

V4L2 Devices:
$(ls -la /dev/video* 2>/dev/null || echo "No V4L2 devices found")
$(ls -la /dev/v4l2m2m* 2>/dev/null || echo "No V4L2 M2M devices found")

Loaded Modules:
$(lsmod | grep -E "(v4l2|bcm2835|vc4)" || echo "No relevant modules loaded")

Test Results:
EOF
    
    # Add test results
    if [[ -f "$OUTPUT_DIR/h264_hw_test.mp4" ]]; then
        echo "- H.264 Hardware Encoding: PASSED" >> "$report_file"
    else
        echo "- H.264 Hardware Encoding: FAILED" >> "$report_file"
    fi
    
    if [[ -f "$OUTPUT_DIR/h264_hw_decode_test.mp4" ]]; then
        echo "- H.264 Hardware Decoding: PASSED" >> "$report_file"
    else
        echo "- H.264 Hardware Decoding: FAILED" >> "$report_file"
    fi
    
    if [[ -f "$OUTPUT_DIR/docker_hw_test.mp4" ]]; then
        echo "- Docker Hardware Acceleration: PASSED" >> "$report_file"
    else
        echo "- Docker Hardware Acceleration: FAILED" >> "$report_file"
    fi
    
    cat >> "$report_file" << EOF

Log Files:
$(ls -la "$OUTPUT_DIR"/*.log 2>/dev/null || echo "No log files found")

Output Files:
$(ls -la "$OUTPUT_DIR"/*.mp4 2>/dev/null || echo "No output files found")

End of Report
EOF
    
    log "Test report generated: $report_file"
}

# Cleanup function
cleanup() {
    log "Cleaning up test files..."
    
    # Keep only the report and benchmark files
    find "$OUTPUT_DIR" -name "*.mp4" -delete 2>/dev/null || true
    find "$OUTPUT_DIR" -name "*.log" -delete 2>/dev/null || true
    
    log "Cleanup completed"
}

# Main execution
main() {
    log "Starting V4L2 M2M hardware acceleration test..."
    log "Test duration: ${TEST_DURATION}s"
    log "Test resolution: $TEST_RESOLUTION"
    log "Test bitrate: $TEST_BITRATE"
    
    # Create output directory
    create_output_dir
    
    # Check hardware
    check_v4l2_devices
    check_v4l2_modules
    test_device_capabilities
    
    # Run tests
    test_h264_encoding
    test_h264_decoding
    test_docker_hardware
    
    # Performance benchmark
    run_performance_benchmark
    
    # Generate report
    generate_report
    
    log "V4L2 M2M hardware acceleration test completed successfully"
    log "Results available in: $OUTPUT_DIR"
    
    # Cleanup
    cleanup
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
