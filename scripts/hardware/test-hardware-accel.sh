#!/bin/bash
# scripts/hardware/test-hardware-accel.sh
# Test hardware acceleration on Pi 5 for distroless containers
# LUCID-STRICT: Comprehensive hardware acceleration validation

set -Eeuo pipefail

# Script metadata
SCRIPT_NAME="$(basename "$0")"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_PATH/../.." && pwd)"

# Configuration
TEST_DURATION="${TEST_DURATION:-60}"
TEST_RESOLUTIONS=("1280x720" "1920x1080" "2560x1440")
TEST_BITRATES=("1M" "2M" "4M" "8M")
OUTPUT_DIR="${OUTPUT_DIR:-/tmp/lucid-hw-accel-test}"
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

# Check system requirements
check_system_requirements() {
    log "Checking system requirements..."
    
    # Check if running on Pi
    local model
    model=$(cat /proc/device-tree/model 2>/dev/null || echo "Unknown")
    log "Pi Model: $model"
    
    if [[ "$model" != *"Pi"* ]]; then
        warn "Not running on Raspberry Pi - some tests may fail"
    fi
    
    # Check architecture
    local arch
    arch=$(uname -m)
    if [[ "$arch" != "aarch64" ]]; then
        warn "Not running on ARM64 architecture - some tests may fail"
    fi
    
    # Check available memory
    local total_mem
    total_mem=$(free -m | awk '/^Mem:/{print $2}')
    log "Total memory: ${total_mem}MB"
    
    if [[ "$total_mem" -lt 4096 ]]; then
        warn "Low memory detected - performance may be affected"
    fi
    
    # Check GPU memory
    local gpu_mem
    gpu_mem=$(vcgencmd get_mem gpu 2>/dev/null | cut -d= -f2 | cut -dM -f1)
    log "GPU memory: ${gpu_mem}MB"
    
    if [[ "$gpu_mem" -lt 128 ]]; then
        warn "Low GPU memory - hardware acceleration may not work properly"
    fi
}

# Check V4L2 hardware
check_v4l2_hardware() {
    log "Checking V4L2 hardware..."
    
    # Check V4L2 devices
    local video_devices
    video_devices=$(ls /dev/video* 2>/dev/null | wc -l)
    log "V4L2 video devices: $video_devices"
    
    if [[ "$video_devices" -eq 0 ]]; then
        die "No V4L2 video devices found"
    fi
    
    # Check V4L2 M2M devices
    local m2m_devices
    m2m_devices=$(ls /dev/v4l2m2m* 2>/dev/null | wc -l)
    log "V4L2 M2M devices: $m2m_devices"
    
    if [[ "$m2m_devices" -eq 0 ]]; then
        warn "No V4L2 M2M devices found - hardware acceleration may not work"
    fi
    
    # Check loaded modules
    local v4l2_modules
    v4l2_modules=$(lsmod | grep -E "(v4l2|bcm2835|vc4)" | wc -l)
    log "V4L2 modules loaded: $v4l2_modules"
    
    if [[ "$v4l2_modules" -eq 0 ]]; then
        warn "No V4L2 modules loaded - hardware acceleration may not work"
    fi
}

# Test FFmpeg hardware acceleration
test_ffmpeg_hardware() {
    log "Testing FFmpeg hardware acceleration..."
    
    local test_results=()
    
    for resolution in "${TEST_RESOLUTIONS[@]}"; do
        for bitrate in "${TEST_BITRATES[@]}"; do
            log "Testing H.264 encoding: $resolution @ $bitrate"
            
            local output_file="$OUTPUT_DIR/test_${resolution}_${bitrate}.mp4"
            local start_time end_time duration
            
            start_time=$(date +%s)
            
            if ffmpeg -f lavfi -i "testsrc=duration=$TEST_DURATION:size=$resolution:rate=30" \
                -c:v h264_v4l2m2m -b:v "$bitrate" \
                -f mp4 "$output_file" -y 2>&1 | tee "$OUTPUT_DIR/test_${resolution}_${bitrate}.log"; then
                
                end_time=$(date +%s)
                duration=$((end_time - start_time))
                
                if [[ -f "$output_file" ]]; then
                    local file_size
                    file_size=$(stat -c%s "$output_file" 2>/dev/null || echo "0")
                    log "Test passed: $resolution @ $bitrate (${duration}s, ${file_size} bytes)"
                    test_results+=("PASS:$resolution:$bitrate:$duration:$file_size")
                else
                    warn "Test failed: $resolution @ $bitrate (no output file)"
                    test_results+=("FAIL:$resolution:$bitrate:0:0")
                fi
            else
                warn "Test failed: $resolution @ $bitrate (encoding failed)"
                test_results+=("FAIL:$resolution:$bitrate:0:0")
            fi
        done
    done
    
    # Save test results
    printf "%s\n" "${test_results[@]}" > "$OUTPUT_DIR/ffmpeg_test_results.txt"
    log "FFmpeg hardware acceleration test completed"
}

# Test Docker hardware acceleration
test_docker_hardware() {
    log "Testing Docker hardware acceleration..."
    
    if ! command -v docker >/dev/null 2>&1; then
        warn "Docker not available, skipping Docker test"
        return 0
    fi
    
    local test_results=()
    
    for resolution in "${TEST_RESOLUTIONS[@]}"; do
        for bitrate in "${TEST_BITRATES[@]}"; do
            log "Testing Docker H.264 encoding: $resolution @ $bitrate"
            
            local output_file="$OUTPUT_DIR/docker_${resolution}_${bitrate}.mp4"
            local start_time end_time duration
            
            start_time=$(date +%s)
            
            if docker run --rm --device=/dev/video0 --device=/dev/v4l2m2m \
                -v "$OUTPUT_DIR:/tmp/output" \
                "$FFMPEG_IMAGE" \
                ffmpeg -f lavfi -i "testsrc=duration=$TEST_DURATION:size=$resolution:rate=30" \
                -c:v h264_v4l2m2m -b:v "$bitrate" \
                -f mp4 "/tmp/output/docker_${resolution}_${bitrate}.mp4" -y \
                2>&1 | tee "$OUTPUT_DIR/docker_${resolution}_${bitrate}.log"; then
                
                end_time=$(date +%s)
                duration=$((end_time - start_time))
                
                if [[ -f "$output_file" ]]; then
                    local file_size
                    file_size=$(stat -c%s "$output_file" 2>/dev/null || echo "0")
                    log "Docker test passed: $resolution @ $bitrate (${duration}s, ${file_size} bytes)"
                    test_results+=("PASS:$resolution:$bitrate:$duration:$file_size")
                else
                    warn "Docker test failed: $resolution @ $bitrate (no output file)"
                    test_results+=("FAIL:$resolution:$bitrate:0:0")
                fi
            else
                warn "Docker test failed: $resolution @ $bitrate (encoding failed)"
                test_results+=("FAIL:$resolution:$bitrate:0:0")
            fi
        done
    done
    
    # Save test results
    printf "%s\n" "${test_results[@]}" > "$OUTPUT_DIR/docker_test_results.txt"
    log "Docker hardware acceleration test completed"
}

# Test performance benchmarks
test_performance_benchmarks() {
    log "Running performance benchmarks..."
    
    local benchmark_file="$OUTPUT_DIR/performance_benchmarks.txt"
    
    cat > "$benchmark_file" << EOF
Lucid RDP Hardware Acceleration Performance Benchmarks
=====================================================
Test Date: $(date)
Pi Model: $(cat /proc/device-tree/model 2>/dev/null || echo "Unknown")
GPU Memory: $(vcgencmd get_mem gpu 2>/dev/null || echo "Unknown")
GPU Frequency: $(vcgencmd measure_clock gpu 2>/dev/null || echo "Unknown")
GPU Temperature: $(vcgencmd measure_temp 2>/dev/null || echo "Unknown")

EOF
    
    # Benchmark different resolutions
    for resolution in "${TEST_RESOLUTIONS[@]}"; do
        log "Benchmarking $resolution..."
        
        local start_time end_time duration
        start_time=$(date +%s)
        
        if ffmpeg -f lavfi -i "testsrc=duration=30:size=$resolution:rate=30" \
            -c:v h264_v4l2m2m -b:v 2M \
            -f mp4 "$OUTPUT_DIR/benchmark_${resolution}.mp4" -y 2>/dev/null; then
            
            end_time=$(date +%s)
            duration=$((end_time - start_time))
            
            local file_size
            file_size=$(stat -c%s "$OUTPUT_DIR/benchmark_${resolution}.mp4" 2>/dev/null || echo "0")
            
            cat >> "$benchmark_file" << EOF
Resolution: $resolution
- Duration: ${duration}s
- File Size: ${file_size} bytes
- Bitrate: 2M
- Status: PASSED

EOF
        else
            cat >> "$benchmark_file" << EOF
Resolution: $resolution
- Status: FAILED

EOF
        fi
    done
    
    log "Performance benchmarks completed: $benchmark_file"
}

# Test system stability
test_system_stability() {
    log "Testing system stability..."
    
    local stability_file="$OUTPUT_DIR/stability_test.txt"
    
    cat > "$stability_file" << EOF
Lucid RDP System Stability Test
===============================
Test Date: $(date)

EOF
    
    # Monitor system during encoding
    local start_time end_time duration
    start_time=$(date +%s)
    
    log "Running stability test for 5 minutes..."
    
    if timeout 300 ffmpeg -f lavfi -i "testsrc=duration=300:size=1920x1080:rate=30" \
        -c:v h264_v4l2m2m -b:v 4M \
        -f mp4 "$OUTPUT_DIR/stability_test.mp4" -y 2>&1 | tee "$OUTPUT_DIR/stability_test.log"; then
        
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        
        cat >> "$stability_file" << EOF
Stability Test Results:
- Duration: ${duration}s
- Status: PASSED
- No crashes or hangs detected

EOF
        log "System stability test passed"
    else
        cat >> "$stability_file" << EOF
Stability Test Results:
- Status: FAILED
- System may be unstable under load

EOF
        warn "System stability test failed"
    fi
}

# Generate comprehensive report
generate_comprehensive_report() {
    log "Generating comprehensive test report..."
    
    local report_file="$OUTPUT_DIR/hardware_acceleration_report.txt"
    
    cat > "$report_file" << EOF
Lucid RDP Hardware Acceleration Test Report
===========================================
Test Date: $(date)
Script: $SCRIPT_NAME
Project: $(basename "$PROJECT_ROOT")

System Information:
- Pi Model: $(cat /proc/device-tree/model 2>/dev/null || echo "Unknown")
- Architecture: $(uname -m)
- Kernel: $(uname -r)
- Total Memory: $(free -m | awk '/^Mem:/{print $2}')MB
- GPU Memory: $(vcgencmd get_mem gpu 2>/dev/null || echo "Unknown")
- GPU Frequency: $(vcgencmd measure_clock gpu 2>/dev/null || echo "Unknown")
- GPU Temperature: $(vcgencmd measure_temp 2>/dev/null || echo "Unknown")

V4L2 Hardware:
- Video Devices: $(ls /dev/video* 2>/dev/null | wc -l)
- M2M Devices: $(ls /dev/v4l2m2m* 2>/dev/null | wc -l)
- Loaded Modules: $(lsmod | grep -E "(v4l2|bcm2835|vc4)" | wc -l)

Test Configuration:
- Test Duration: ${TEST_DURATION}s
- Test Resolutions: ${TEST_RESOLUTIONS[*]}
- Test Bitrates: ${TEST_BITRATES[*]}
- FFmpeg Image: $FFMPEG_IMAGE

Test Results:

EOF
    
    # Add FFmpeg test results
    if [[ -f "$OUTPUT_DIR/ffmpeg_test_results.txt" ]]; then
        cat >> "$report_file" << EOF
FFmpeg Hardware Acceleration Tests:
$(cat "$OUTPUT_DIR/ffmpeg_test_results.txt")

EOF
    fi
    
    # Add Docker test results
    if [[ -f "$OUTPUT_DIR/docker_test_results.txt" ]]; then
        cat >> "$report_file" << EOF
Docker Hardware Acceleration Tests:
$(cat "$OUTPUT_DIR/docker_test_results.txt")

EOF
    fi
    
    # Add performance benchmarks
    if [[ -f "$OUTPUT_DIR/performance_benchmarks.txt" ]]; then
        cat >> "$report_file" << EOF
Performance Benchmarks:
$(cat "$OUTPUT_DIR/performance_benchmarks.txt")

EOF
    fi
    
    # Add stability test results
    if [[ -f "$OUTPUT_DIR/stability_test.txt" ]]; then
        cat >> "$report_file" << EOF
System Stability Test:
$(cat "$OUTPUT_DIR/stability_test.txt")

EOF
    fi
    
    cat >> "$report_file" << EOF

Summary:
- Total Tests: $((${#TEST_RESOLUTIONS[@]} * ${#TEST_BITRATES[@]} * 2))
- FFmpeg Tests: $((${#TEST_RESOLUTIONS[@]} * ${#TEST_BITRATES[@]}))
- Docker Tests: $((${#TEST_RESOLUTIONS[@]} * ${#TEST_BITRATES[@]}))
- Performance Benchmarks: ${#TEST_RESOLUTIONS[@]}
- Stability Test: 1

Log Files:
$(ls -la "$OUTPUT_DIR"/*.log 2>/dev/null || echo "No log files found")

Output Files:
$(ls -la "$OUTPUT_DIR"/*.mp4 2>/dev/null || echo "No output files found")

End of Report
EOF
    
    log "Comprehensive test report generated: $report_file"
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
    log "Starting comprehensive hardware acceleration test..."
    log "Test duration: ${TEST_DURATION}s"
    log "Test resolutions: ${TEST_RESOLUTIONS[*]}"
    log "Test bitrates: ${TEST_BITRATES[*]}"
    
    # Create output directory
    create_output_dir
    
    # Check system requirements
    check_system_requirements
    
    # Check V4L2 hardware
    check_v4l2_hardware
    
    # Run tests
    test_ffmpeg_hardware
    test_docker_hardware
    test_performance_benchmarks
    test_system_stability
    
    # Generate report
    generate_comprehensive_report
    
    log "Comprehensive hardware acceleration test completed successfully"
    log "Results available in: $OUTPUT_DIR"
    
    # Cleanup
    cleanup
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
