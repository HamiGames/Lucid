#!/bin/bash
# Path: scripts/build_ffmpeg_pi.sh
# Cross-compile FFmpeg with V4L2 hardware acceleration for Raspberry Pi 5
# Based on LUCID-STRICT requirements per Spec-1d

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="${PROJECT_ROOT}/build/ffmpeg"
INSTALL_PREFIX="${PROJECT_ROOT}/dist/ffmpeg-pi5"
CROSS_COMPILE_PREFIX="aarch64-linux-gnu-"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        INFO) echo -e "${BLUE}[INFO]${NC} [$timestamp] $message" ;;
        WARN) echo -e "${YELLOW}[WARN]${NC} [$timestamp] $message" ;;
        ERROR) echo -e "${RED}[ERROR]${NC} [$timestamp] $message" >&2 ;;
        SUCCESS) echo -e "${GREEN}[SUCCESS]${NC} [$timestamp] $message" ;;
    esac
}

check_dependencies() {
    log INFO "Checking build dependencies..."
    
    local missing_deps=()
    
    # Check for cross-compilation toolchain
    if ! command -v "${CROSS_COMPILE_PREFIX}gcc" &> /dev/null; then
        missing_deps+=("gcc-aarch64-linux-gnu")
    fi
    
    if ! command -v "${CROSS_COMPILE_PREFIX}g++" &> /dev/null; then
        missing_deps+=("g++-aarch64-linux-gnu")
    fi
    
    # Check for build tools
    local required_tools=("make" "pkg-config" "nasm" "yasm" "git" "wget")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_deps+=("$tool")
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log ERROR "Missing dependencies: ${missing_deps[*]}"
        log INFO "Install with: sudo apt-get install ${missing_deps[*]}"
        return 1
    fi
    
    log SUCCESS "All dependencies available"
    return 0
}

setup_build_environment() {
    log INFO "Setting up build environment..."
    
    # Create build directories
    mkdir -p "$BUILD_DIR"
    mkdir -p "$INSTALL_PREFIX"
    
    # Export cross-compilation environment
    export CC="${CROSS_COMPILE_PREFIX}gcc"
    export CXX="${CROSS_COMPILE_PREFIX}g++"
    export AR="${CROSS_COMPILE_PREFIX}ar"
    export STRIP="${CROSS_COMPILE_PREFIX}strip"
    export PKG_CONFIG_LIBDIR="/usr/lib/aarch64-linux-gnu/pkgconfig"
    
    # Set target architecture flags
    export CFLAGS="-march=armv8-a+crc -mtune=cortex-a76 -O3 -fPIC"
    export CXXFLAGS="$CFLAGS"
    export LDFLAGS="-L/usr/lib/aarch64-linux-gnu"
    
    log SUCCESS "Build environment configured for ARM64/Pi5"
}

download_ffmpeg_source() {
    log INFO "Downloading FFmpeg source..."
    
    local ffmpeg_version="6.0"
    local ffmpeg_url="https://ffmpeg.org/releases/ffmpeg-${ffmpeg_version}.tar.xz"
    local source_dir="${BUILD_DIR}/ffmpeg-${ffmpeg_version}"
    
    if [[ -d "$source_dir" ]]; then
        log INFO "FFmpeg source already exists, skipping download"
        echo "$source_dir"
        return 0
    fi
    
    cd "$BUILD_DIR"
    
    # Download and extract
    wget -O "ffmpeg-${ffmpeg_version}.tar.xz" "$ffmpeg_url"
    tar -xf "ffmpeg-${ffmpeg_version}.tar.xz"
    
    log SUCCESS "FFmpeg source downloaded and extracted"
    echo "$source_dir"
}

configure_ffmpeg() {
    local source_dir=$1
    log INFO "Configuring FFmpeg for Raspberry Pi 5 with V4L2..."
    
    cd "$source_dir"
    
    # FFmpeg configuration for Pi5 with hardware acceleration
    ./configure \
        --prefix="$INSTALL_PREFIX" \
        --enable-cross-compile \
        --cross-prefix="${CROSS_COMPILE_PREFIX}" \
        --arch=arm64 \
        --target-os=linux \
        --cc="${CC}" \
        --cxx="${CXX}" \
        --ar="${AR}" \
        --strip="${STRIP}" \
        --pkg-config=pkg-config \
        --enable-gpl \
        --enable-version3 \
        --enable-nonfree \
        --enable-static \
        --disable-shared \
        --disable-debug \
        --enable-optimizations \
        --enable-runtime-cpudetect \
        --enable-v4l2_m2m \
        --enable-libv4l2 \
        --enable-encoder=h264_v4l2m2m \
        --enable-decoder=h264_v4l2m2m \
        --enable-encoder=hevc_v4l2m2m \
        --enable-decoder=hevc_v4l2m2m \
        --enable-hwaccel=h264_v4l2m2m \
        --enable-hwaccel=hevc_v4l2m2m \
        --enable-mmal \
        --enable-omx \
        --enable-omx-rpi \
        --enable-libx264 \
        --enable-libx265 \
        --enable-libvpx \
        --enable-libopus \
        --enable-libmp3lame \
        --enable-libfdk-aac \
        --enable-libfreetype \
        --enable-libass \
        --enable-libfontconfig \
        --enable-filter=scale \
        --enable-filter=fps \
        --enable-filter=overlay \
        --disable-doc \
        --disable-htmlpages \
        --disable-manpages \
        --disable-podpages \
        --disable-txtpages \
        --extra-cflags="$CFLAGS -I/usr/include/libdrm" \
        --extra-ldflags="$LDFLAGS" \
        --extra-libs="-lpthread -lm -latomic"
    
    if [[ $? -eq 0 ]]; then
        log SUCCESS "FFmpeg configured successfully"
    else
        log ERROR "FFmpeg configuration failed"
        return 1
    fi
}

build_ffmpeg() {
    local source_dir=$1
    log INFO "Building FFmpeg (this may take 20-30 minutes)..."
    
    cd "$source_dir"
    
    # Build with parallel jobs
    local cpu_count=$(nproc)
    local make_jobs=$((cpu_count > 4 ? 4 : cpu_count))
    
    if make -j"$make_jobs"; then
        log SUCCESS "FFmpeg build completed"
    else
        log ERROR "FFmpeg build failed"
        return 1
    fi
    
    # Install to prefix directory
    if make install; then
        log SUCCESS "FFmpeg installed to $INSTALL_PREFIX"
    else
        log ERROR "FFmpeg installation failed"
        return 1
    fi
}

create_docker_assets() {
    log INFO "Creating Docker assets for Pi deployment..."
    
    local docker_dir="${PROJECT_ROOT}/docker/ffmpeg-pi5"
    mkdir -p "$docker_dir"
    
    # Create Dockerfile for Pi5 with FFmpeg
    cat > "${docker_dir}/Dockerfile" << 'EOF'
FROM arm64v8/ubuntu:22.04

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libv4l-0 \
    libx264-164 \
    libx265-199 \
    libvpx7 \
    libopus0 \
    libmp3lame0 \
    libfdk-aac2 \
    libfreetype6 \
    libass9 \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

# Copy built FFmpeg
COPY --from=build /dist/ffmpeg-pi5 /usr/local

# Create lucid user
RUN useradd -r -s /bin/false -d /nonexistent lucid

# Test hardware acceleration
RUN /usr/local/bin/ffmpeg -encoders 2>&1 | grep v4l2m2m || \
    (echo "V4L2 M2M encoders not available" && exit 1)

ENTRYPOINT ["/usr/local/bin/ffmpeg"]
EOF
    
    # Create build script for Docker
    cat > "${docker_dir}/build.sh" << 'EOF'
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo "Building FFmpeg Docker image for Pi5..."

# Build FFmpeg first if not exists
if [[ ! -d "${PROJECT_ROOT}/dist/ffmpeg-pi5" ]]; then
    echo "FFmpeg not built yet, building..."
    "${PROJECT_ROOT}/scripts/build_ffmpeg_pi.sh"
fi

# Build Docker image
docker buildx build \
    --platform linux/arm64 \
    --build-context build="${PROJECT_ROOT}/dist" \
    --tag pickme/lucid-ffmpeg-pi5:latest \
    --tag pickme/lucid-ffmpeg-pi5:$(date +%Y%m%d) \
    --push \
    "$SCRIPT_DIR"

echo "FFmpeg Docker image built and pushed"
EOF
    
    chmod +x "${docker_dir}/build.sh"
    
    log SUCCESS "Docker assets created in $docker_dir"
}

verify_build() {
    log INFO "Verifying FFmpeg build..."
    
    local ffmpeg_bin="${INSTALL_PREFIX}/bin/ffmpeg"
    
    if [[ ! -f "$ffmpeg_bin" ]]; then
        log ERROR "FFmpeg binary not found at $ffmpeg_bin"
        return 1
    fi
    
    # Check if it's ARM64
    local arch=$(file "$ffmpeg_bin" | grep -o 'aarch64')
    if [[ -z "$arch" ]]; then
        log ERROR "FFmpeg binary is not ARM64"
        return 1
    fi
    
    log SUCCESS "FFmpeg binary verified (ARM64)"
    
    # Create a simple test script for Pi deployment
    cat > "${INSTALL_PREFIX}/test_hw_accel.sh" << 'EOF'
#!/bin/bash
# Test V4L2 hardware acceleration on Raspberry Pi
set -euo pipefail

echo "Testing V4L2 M2M hardware acceleration..."

# Check available encoders
echo "Available V4L2 encoders:"
./bin/ffmpeg -encoders 2>&1 | grep v4l2m2m || echo "No V4L2 encoders found"

# Check available decoders  
echo "Available V4L2 decoders:"
./bin/ffmpeg -decoders 2>&1 | grep v4l2m2m || echo "No V4L2 decoders found"

# Test basic encoding (requires /dev/video* devices)
if [[ -e /dev/video11 ]]; then
    echo "Testing H.264 hardware encoding..."
    ./bin/ffmpeg \
        -f lavfi -i testsrc=duration=5:size=1280x720:rate=30 \
        -c:v h264_v4l2m2m \
        -b:v 2M \
        -f null - \
        2>&1 | grep -q "video:" && echo "H.264 encoding: PASS" || echo "H.264 encoding: FAIL"
else
    echo "No V4L2 devices found (/dev/video11), skipping encode test"
fi

echo "Hardware acceleration test completed"
EOF
    
    chmod +x "${INSTALL_PREFIX}/test_hw_accel.sh"
    
    log SUCCESS "Build verification completed"
}

cleanup_build() {
    log INFO "Cleaning up build artifacts..."
    
    # Remove source and intermediate files, keep dist
    rm -rf "${BUILD_DIR}/ffmpeg-"*.tar.xz
    
    log SUCCESS "Cleanup completed"
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Build FFmpeg with V4L2 hardware acceleration for Raspberry Pi 5"
    echo
    echo "Options:"
    echo "  --clean     Clean build (remove existing build directory)"
    echo "  --no-docker Skip Docker asset creation"
    echo "  --help      Show this help message"
    echo
    echo "Environment Variables:"
    echo "  INSTALL_PREFIX  Installation directory (default: ./dist/ffmpeg-pi5)"
    echo "  CROSS_COMPILE   Cross-compiler prefix (default: aarch64-linux-gnu-)"
}

main() {
    local clean_build=false
    local create_docker=true
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --clean)
                clean_build=true
                shift
                ;;
            --no-docker)
                create_docker=false
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    log INFO "Starting FFmpeg Pi5 build process..."
    
    # Clean build if requested
    if [[ "$clean_build" == "true" ]]; then
        log INFO "Performing clean build..."
        rm -rf "$BUILD_DIR" "$INSTALL_PREFIX"
    fi
    
    # Check if already built
    if [[ -f "${INSTALL_PREFIX}/bin/ffmpeg" ]] && [[ "$clean_build" == "false" ]]; then
        log INFO "FFmpeg already built, skipping compilation"
        verify_build
        return 0
    fi
    
    # Execute build pipeline
    check_dependencies || exit 1
    setup_build_environment || exit 1
    
    local source_dir
    source_dir=$(download_ffmpeg_source) || exit 1
    
    configure_ffmpeg "$source_dir" || exit 1
    build_ffmpeg "$source_dir" || exit 1
    
    verify_build || exit 1
    
    if [[ "$create_docker" == "true" ]]; then
        create_docker_assets || exit 1
    fi
    
    cleanup_build || exit 1
    
    log SUCCESS "FFmpeg Pi5 build completed successfully!"
    log INFO "Binary location: ${INSTALL_PREFIX}/bin/ffmpeg"
    log INFO "Test script: ${INSTALL_PREFIX}/test_hw_accel.sh"
    
    if [[ "$create_docker" == "true" ]]; then
        log INFO "Docker build script: ${PROJECT_ROOT}/docker/ffmpeg-pi5/build.sh"
    fi
}

# Execute main function with all arguments
main "$@"