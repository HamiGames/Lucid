# ==============================================================================
# Lucid Admin Interface - Phase 4 Distroless Container
# Step 33: Phase 4 Container Builds
# ==============================================================================
# 
# Build Command:
#   docker buildx build --platform linux/amd64,linux/arm64 \
#     --target distroless \
#     --tag pickme/lucid:admin-interface:latest \
#     --file Dockerfile \
#     --push .
#
# Security Features:
#   - Distroless base image (no shell, no package managers)
#   - Non-root user (UID 65532)
#   - Read-only root filesystem
#   - Minimal attack surface
#   - Multi-platform support (AMD64/ARM64)
#
# Phase 4 Compliance:
#   - Admin interface container
#   - Deploy to main network (lucid-dev)
#   - Support service cluster
# ==============================================================================

# ==============================================================================
# Stage 1: Builder - Install dependencies and build application
# ==============================================================================
FROM python:3.12-slim-bookworm AS builder

# Build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG PYTHON_VERSION=3.12

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt ./

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . ./

# Create necessary directories for runtime
RUN mkdir -p /app/logs /app/tmp /app/data /app/config && \
    chmod 755 /app/logs /app/tmp /app/data && \
    chmod 700 /app/config

# ==============================================================================
# Stage 2: Runtime - Distroless container with application
# ==============================================================================
FROM gcr.io/distroless/python3-debian12:nonroot AS distroless

# Metadata labels
LABEL maintainer="Lucid RDP Development Team <dev@lucid-rdp.onion>"
LABEL org.opencontainers.image.title="Lucid Admin Interface"
LABEL org.opencontainers.image.description="Lucid admin interface for system management"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.vendor="Lucid RDP"
LABEL org.opencontainers.image.licenses="Proprietary"
LABEL org.opencontainers.image.url="https://lucid-rdp.onion"
LABEL org.opencontainers.image.source="https://github.com/HamiGames/Lucid"

# Security labels
LABEL security.distroless="true"
LABEL security.nonroot="true"
LABEL security.readonly="true"
LABEL security.plane="ops"
LABEL security.cluster="admin-interface"

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV SERVICE_NAME=admin-interface
ENV SERVICE_PORT=8083
ENV LUCID_ENV=production

# Create application directory with proper permissions
USER nonroot:nonroot
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder --chown=nonroot:nonroot /opt/venv /opt/venv

# Copy application source with proper ownership
COPY --from=builder --chown=nonroot:nonroot /app /app

# Set Python path to use virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Health check (HTTP-based, no shell required)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/usr/bin/python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8083/admin/health').read()"]

# Expose service port
EXPOSE 8083

# Switch to non-root user (redundant but explicit)
USER 65532:65532

# Default command
CMD ["/usr/bin/python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8083", "--workers", "1"]
