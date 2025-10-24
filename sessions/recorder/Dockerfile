# Multi-stage build for Lucid Session Recorder Service
# Uses distroless base image for security and minimal size (Step 15 requirement)

# Stage 1: Builder
FROM python:3.11-slim AS builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG PYTHON_VERSION=3.11

# Install minimal build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements first for better layer caching
COPY requirements.txt .
COPY sessions/recorder/requirements.txt ./recorder/

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt
RUN pip install --no-cache-dir --user -r recorder/requirements.txt

# Install optional compression libraries
RUN pip install --no-cache-dir --user lz4 zstandard || true

# Copy source code
COPY sessions/ ./sessions/
COPY . .

# Create non-root user for security
RUN groupadd -r lucid && useradd -r -g lucid lucid

# Set proper permissions
RUN chown -R lucid:lucid /build

# Stage 2: Runtime (Distroless)
FROM gcr.io/distroless/python3-debian12

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY --from=builder /build/sessions /app/sessions
COPY --from=builder /build /app

# Set working directory
WORKDIR /app

# Create necessary directories
USER root
RUN mkdir -p /data/recordings /data/chunks /tmp/sessions && \
    chown -R 65532:65532 /data /tmp/sessions
USER 65532:65532

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV SERVICE_NAME=lucid-session-recorder
ENV PORT=8084
ENV HOST=0.0.0.0
ENV LOG_LEVEL=INFO
ENV DEBUG=false

# Recording configuration
ENV LUCID_RECORDING_PATH=/data/recordings
ENV LUCID_CHUNK_OUTPUT_PATH=/data/chunks
ENV LUCID_CHUNK_SIZE_MB=10
ENV LUCID_COMPRESSION_LEVEL=6
ENV LUCID_FFMPEG_PATH=/usr/bin/ffmpeg
ENV LUCID_XRDP_DISPLAY=:10
ENV LUCID_HARDWARE_ACCELERATION=true
ENV LUCID_VIDEO_CODEC=h264_v4l2m2m
ENV LUCID_AUDIO_CODEC=opus
ENV LUCID_BITRATE=2000k
ENV LUCID_FPS=30

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8084/health')"]

# Expose port
EXPOSE 8084

# Set entrypoint
ENTRYPOINT ["python", "-m", "sessions.recorder.main"]
