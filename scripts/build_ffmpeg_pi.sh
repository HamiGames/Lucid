#!/bin/bash
# LUCID FFmpeg Pi 5 Cross-Compilation Script - SPEC-1D Implementation
# Cross-compile FFmpeg with V4L2 hardware acceleration for ARM64

set -euo pipefail

# Configuration
TARGET_ARCH="arm64"
PI_VERSION="5"
FFMPEG_VERSION="6.1.1"
BUILD_DIR="/tmp/ffmpeg-build"
INSTALL_DIR="/opt/ffmpeg-pi5"

echo "=== LUCID FFmpeg Pi 5 Cross-Compilation ==="

# Create build directory
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Download FFmpeg source
echo "Downloading FFmpeg source..."
wget -q "https://ffmpeg.org/releases/ffmpeg-${FFMPEG_VERSION}.tar.xz"
tar -xf "ffmpeg-${FFMPEG_VERSION}.tar.xz"
cd "ffmpeg-${FFMPEG_VERSION}"

# Configure for Pi 5 with V4L2 hardware acceleration
echo "Configuring FFmpeg for Pi 5..."
./configure \
    --arch=aarch64 \
    --target-os=linux \
    --cross-prefix=aarch64-linux-gnu- \
    --enable-cross-compile \
    --enable-v4l2-m2m \
    --enable-omx \
    --enable-omx-rpi \
    --enable-mmal \
    --enable-gpl \
    --enable-nonfree \
    --enable-libx264 \
    --enable-libx265 \
    --enable-libvpx \
    --enable-libfdk-aac \
    --enable-libmp3lame \
    --enable-libopus \
    --enable-libvorbis \
    --enable-libtheora \
    --enable-libfreetype \
    --enable-libfontconfig \
    --enable-libfribidi \
    --enable-libass \
    --enable-libbluray \
    --enable-libbs2b \
    --enable-libcaca \
    --enable-libcdio \
    --enable-libcodec2 \
    --enable-libflite \
    --enable-libgme \
    --enable-libgsm \
    --enable-libmodplug \
    --enable-libopenjpeg \
    --enable-libpulse \
    --enable-librsvg \
    --enable-librubberband \
    --enable-libsnappy \
    --enable-libsoxr \
    --enable-libspeex \
    --enable-libssh \
    --enable-libtwolame \
    --enable-libwavpack \
    --enable-libwebp \
    --enable-libxml2 \
    --enable-libzimg \
    --enable-libzmq \
    --enable-libzvbi \
    --enable-lv2 \
    --enable-libavresample \
    --enable-libavutil \
    --enable-libavcodec \
    --enable-libavformat \
    --enable-libavfilter \
    --enable-libavdevice \
    --enable-libswscale \
    --enable-libswresample \
    --enable-libpostproc \
    --enable-avresample \
    --enable-shared \
    --enable-static \
    --disable-debug \
    --disable-doc \
    --disable-htmlpages \
    --disable-manpages \
    --disable-podpages \
    --disable-txtpages \
    --disable-static \
    --enable-shared \
    --enable-pic \
    --extra-cflags="-O3 -fPIC" \
    --extra-ldflags="-Wl,-rpath-link=/usr/aarch64-linux-gnu/lib" \
    --prefix="$INSTALL_DIR"

# Build FFmpeg
echo "Building FFmpeg (this may take 30-60 minutes)..."
make -j$(nproc)

# Install FFmpeg
echo "Installing FFmpeg..."
sudo make install

# Create Pi 5 optimized configuration
echo "Creating Pi 5 optimized configuration..."
sudo tee "$INSTALL_DIR/etc/ffmpeg-pi5.conf" > /dev/null << 'EOF'
# LUCID FFmpeg Pi 5 Configuration
# Optimized for Raspberry Pi 5 with V4L2 hardware acceleration

# Hardware acceleration
-hwaccel v4l2m2m
-hwaccel_device /dev/video0

# Video encoding (H.264)
-vcodec h264_v4l2m2m
-preset fast
-crf 23
-maxrate 2M
-bufsize 4M

# Audio encoding
-acodec aac
-ar 44100
-ac 2
-ab 128k

# Pi 5 specific optimizations
-threads 4
-tune zerolatency
EOF

echo "=== FFmpeg Pi 5 Build Complete ==="
echo "Installation directory: $INSTALL_DIR"
echo "Configuration file: $INSTALL_DIR/etc/ffmpeg-pi5.conf"
echo "Usage: $INSTALL_DIR/bin/ffmpeg -f ffmpeg-pi5.conf [input] [output]"