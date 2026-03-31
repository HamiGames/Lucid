#!/bin/bash
# RDP/scripts/prepare-distroless-image.sh
# File: /app/RDP/scripts/prepare-distroless-image.sh
# x-lucid-file-path: /app/RDP/scripts/prepare-distroless-image.sh
# x-lucid-file-directory: /app/RDP/scripts
# x-lucid-file-type: shell
# Script to pre-pull and prepare distroless image for transfer to Pi
# Run this on a machine with internet access

set -e

IMAGE="gcr.io/distroless/python3-debian12:latest"
PLATFORM="linux/arm64"
OUTPUT_FILE="distroless-python3-debian12-arm64.tar.gz"

echo "🔍 Pulling distroless Python image for ARM64..."
docker pull --platform "$PLATFORM" "$IMAGE"

echo "💾 Saving image to archive..."
docker save "$IMAGE" | gzip > "$OUTPUT_FILE"

echo "✅ Image saved to: $OUTPUT_FILE"
echo ""
echo "📦 To transfer to Pi:"
echo "   1. Copy $OUTPUT_FILE to Pi"
echo "   2. On Pi, run: docker load < $OUTPUT_FILE"
echo "   3. Update Dockerfile.xrdp line 99 to use: FROM --platform=\$TARGETPLATFORM gcr.io/distroless/python3-debian12:latest"
echo "   4. Update HEALTHCHECK and CMD to use /usr/bin/python3.11 instead of python3"

