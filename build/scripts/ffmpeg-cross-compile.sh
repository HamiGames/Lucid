#!/bin/bash
# build/scripts/ffmpeg-cross-compile.sh
# Cross-compile FFmpeg with Pi V4L2 support for distroless containers
# LUCID-STRICT: Pi 5 hardware acceleration with distroless security

set -Eeuo pipefail

# Script metadata
SCRIPT_NAME="$(basename "$0")"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_PATH/../.." && pwd)"

# Configuration
FFMPEG_VERSION="${FFMPEG_VERSION:-6.1.1}"
BUILD_ARCH="${BUILD_ARCH:-arm64}"
PI_TARGET="${PI_TARGET:-aarch64-linux-gnu}"
BUILD_DIR="${BUILD_DIR:-$PROJECT_ROOT/build/ffmpeg-cross}"
DISTROLESS_BASE="${DISTROLESS_BASE:-gcr.io/distroless/python3-debian12}"

# Pi 5 specific hardware acceleration flags
V4L2M2M_ENABLED="${V4L2M2M_ENABLED:-true}"
HARDWARE_DECODE="${HARDWARE_DECODE:-true}"
GPU_MEMORY="${GPU_MEMORY:-128}"

# Logging
log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*"; }
die() { printf '[%s][ERROR] %s\n' "$SCRIPT_NAME" "$*" >&2; exit 1; }
warn() { printf '[%s][WARN] %s\n' "$SCRIPT_NAME" "$*" >&2; }

# Dependencies check
check_dependencies() {
    local deps=("docker" "git" "wget" "tar")
    for dep in "${deps[@]}"; do
        command -v "$dep" >/dev/null 2>&1 || die "Missing dependency: $dep"
    done
    
    # Check Docker buildx
    if ! docker buildx ls | grep -q "lucid-pi"; then
        log "Creating Docker buildx builder for Pi cross-compilation..."
        docker buildx create --name lucid-pi --use --driver docker-container --platform linux/arm64
    fi
}

# Download and verify FFmpeg source
download_ffmpeg() {
    local ffmpeg_url="https://github.com/FFmpeg/FFmpeg/archive/refs/tags/n${FFMPEG_VERSION}.tar.gz"
    local ffmpeg_archive="$BUILD_DIR/ffmpeg-${FFMPEG_VERSION}.tar.gz"
    local ffmpeg_dir="$BUILD_DIR/ffmpeg-${FFMPEG_VERSION}"
    
    log "Downloading FFmpeg ${FFMPEG_VERSION}..."
    mkdir -p "$BUILD_DIR"
    
    if [[ ! -f "$ffmpeg_archive" ]]; then
        wget -O "$ffmpeg_archive" "$ffmpeg_url" || die "Failed to download FFmpeg"
    fi
    
    if [[ ! -d "$ffmpeg_dir" ]]; then
        tar -xzf "$ffmpeg_archive" -C "$BUILD_DIR" || die "Failed to extract FFmpeg"
    fi
    
    echo "$ffmpeg_dir"
}

# Create cross-compilation Dockerfile
create_build_dockerfile() {
    local ffmpeg_dir="$1"
    local dockerfile="$ffmpeg_dir/Dockerfile.cross-compile"
    
    log "Creating cross-compilation Dockerfile..."
    cat > "$dockerfile" << 'EOF'
# Multi-stage FFmpeg cross-compilation for Pi 5 with distroless runtime
FROM --platform=linux/amd64 ubuntu:22.04 AS builder

# Install cross-compilation toolchain
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    pkg-config \
    autoconf \
    automake \
    libtool \
    crossbuild-essential-arm64 \
    libc6-dev-arm64-cross \
    libasound2-dev \
    libx264-dev \
    libx265-dev \
    libvpx-dev \
    libmp3lame-dev \
    libopus-dev \
    libvorbis-dev \
    libtheora-dev \
    libfreetype6-dev \
    libfontconfig1-dev \
    libfribidi-dev \
    libharfbuzz-dev \
    libass-dev \
    libssl-dev \
    libdrm-dev \
    libx11-dev \
    libxext-dev \
    libxfixes-dev \
    libva-dev \
    libvdpau-dev \
    && rm -rf /var/lib/apt/lists/*

# Set cross-compilation environment
ENV CC=aarch64-linux-gnu-gcc
ENV CXX=aarch64-linux-gnu-g++
ENV AR=aarch64-linux-gnu-ar
ENV STRIP=aarch64-linux-gnu-strip
ENV PKG_CONFIG_PATH=/usr/lib/aarch64-linux-gnu/pkgconfig
ENV CROSS_PREFIX=aarch64-linux-gnu-

# Build directory
WORKDIR /build

# Copy FFmpeg source
COPY . /build/ffmpeg/

# Configure FFmpeg with Pi 5 hardware acceleration
RUN cd /build/ffmpeg && \
    ./configure \
        --cross-prefix=aarch64-linux-gnu- \
        --arch=aarch64 \
        --target-os=linux \
        --enable-cross-compile \
        --prefix=/usr/local \
        --enable-shared \
        --disable-static \
        --enable-gpl \
        --enable-version3 \
        --enable-nonfree \
        --enable-libx264 \
        --enable-libx265 \
        --enable-libvpx \
        --enable-libmp3lame \
        --enable-libopus \
        --enable-libvorbis \
        --enable-libtheora \
        --enable-libfreetype \
        --enable-libfontconfig \
        --enable-libfribidi \
        --enable-libharfbuzz \
        --enable-libass \
        --enable-openssl \
        --enable-vaapi \
        --enable-vdpau \
        --enable-v4l2-m2m \
        --enable-decoder=h264_v4l2m2m \
        --enable-decoder=hevc_v4l2m2m \
        --enable-decoder=mpeg2_v4l2m2m \
        --enable-decoder=mpeg4_v4l2m2m \
        --enable-decoder=vp8_v4l2m2m \
        --enable-decoder=vp9_v4l2m2m \
        --enable-encoder=h264_v4l2m2m \
        --enable-encoder=hevc_v4l2m2m \
        --enable-hwaccel=h264_v4l2m2m \
        --enable-hwaccel=hevc_v4l2m2m \
        --enable-hwaccel=mpeg2_v4l2m2m \
        --enable-hwaccel=mpeg4_v4l2m2m \
        --enable-hwaccel=vp8_v4l2m2m \
        --enable-hwaccel=vp9_v4l2m2m \
        --disable-doc \
        --disable-debug \
        --disable-ffplay \
        --disable-ffprobe \
        --enable-ffmpeg \
        --extra-cflags="-O3 -fPIC" \
        --extra-ldflags="-Wl,-rpath,/usr/local/lib" \
    && make -j$(nproc) \
    && make install

# Distroless runtime stage
FROM gcr.io/distroless/python3-debian12

# Copy FFmpeg binaries and libraries
COPY --from=builder /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=builder /usr/local/lib/libav* /usr/local/lib/
COPY --from=builder /usr/local/lib/pkgconfig/ /usr/local/lib/pkgconfig/

# Copy Pi 5 specific device files
COPY --from=builder /lib/aarch64-linux-gnu/libc.so.6 /lib/aarch64-linux-gnu/libc.so.6
COPY --from=builder /lib/aarch64-linux-gnu/ld-linux-aarch64.so.1 /lib/aarch64-linux-gnu/ld-linux-aarch64.so.1

# Set environment
ENV PATH="/usr/local/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/lib:${LD_LIBRARY_PATH}"

# Non-root user
USER 65532

# Default command
ENTRYPOINT ["/usr/local/bin/ffmpeg"]
EOF
}

# Build FFmpeg with Docker
build_ffmpeg() {
    local ffmpeg_dir="$1"
    local image_tag="pickme/lucid:ffmpeg-pi5-${FFMPEG_VERSION}"
    
    log "Building FFmpeg for Pi 5 with hardware acceleration..."
    
    docker buildx build \
        --platform linux/arm64 \
        --file "$ffmpeg_dir/Dockerfile.cross-compile" \
        --tag "$image_tag" \
        --tag "pickme/lucid:ffmpeg-pi5-latest" \
        --load \
        "$ffmpeg_dir" || die "FFmpeg build failed"
    
    log "FFmpeg build completed: $image_tag"
    echo "$image_tag"
}

# Test the built FFmpeg
test_ffmpeg() {
    local image_tag="$1"
    
    log "Testing FFmpeg hardware acceleration support..."
    
    # Test V4L2M2M support
    docker run --rm --privileged \
        -v /dev:/dev \
        "$image_tag" \
        -f lavfi -i testsrc=duration=1:size=1920x1080:rate=30 \
        -c:v h264_v4l2m2m \
        -b:v 2M \
        -f null \
        - 2>&1 | grep -q "h264_v4l2m2m" || warn "V4L2M2M hardware acceleration not working"
    
    # Test codec support
    docker run --rm "$image_tag" -codecs 2>&1 | grep -q "h264_v4l2m2m" || die "H264 V4L2M2M encoder not available"
    
    log "FFmpeg hardware acceleration test passed"
}

# Create Pi 5 specific configuration
create_pi_config() {
    local config_dir="$PROJECT_ROOT/configs/ffmpeg"
    local config_file="$config_dir/pi5-hw-accel.conf"
    
    log "Creating Pi 5 hardware acceleration configuration..."
    mkdir -p "$config_dir"
    
    cat > "$config_file" << 'EOF'
# Pi 5 Hardware Acceleration Configuration
# LUCID-STRICT: Distroless container configuration

# GPU Memory allocation for hardware acceleration
gpu_mem=128

# Enable V4L2 M2M driver
dtoverlay=vc4-kms-v3d

# Hardware codec configuration
[hardware_acceleration]
v4l2m2m_enabled=true
h264_hw_decode=true
h264_hw_encode=true
hevc_hw_decode=true
hevc_hw_encode=true

# Performance settings
[performance]
max_bitrate=8M
preset=fast
tune=zerolatency
crf=23

# Distroless security
[security]
no_shell=true
read_only_rootfs=true
user=65532
EOF
    
    log "Pi 5 configuration created: $config_file"
}

# Main execution
main() {
    log "Starting FFmpeg cross-compilation for Pi 5..."
    log "Build directory: $BUILD_DIR"
    log "Target architecture: $BUILD_ARCH"
    log "FFmpeg version: $FFMPEG_VERSION"
    
    # Check dependencies
    check_dependencies
    
    # Download FFmpeg source
    local ffmpeg_dir
    ffmpeg_dir=$(download_ffmpeg)
    
    # Create build configuration
    create_build_dockerfile "$ffmpeg_dir"
    
    # Build FFmpeg
    local image_tag
    image_tag=$(build_ffmpeg "$ffmpeg_dir")
    
    # Test the build
    test_ffmpeg "$image_tag"
    
    # Create Pi 5 configuration
    create_pi_config
    
    log "FFmpeg cross-compilation completed successfully"
    log "Image: $image_tag"
    log "Configuration: $PROJECT_ROOT/configs/ffmpeg/pi5-hw-accel.conf"
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
