# Distroless Base Image for Lucid Project
# Multi-stage build with distroless runtime

# =============================================================================
# BUILD STAGE
# =============================================================================
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    make \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# DISTROLESS RUNTIME STAGE
# =============================================================================
FROM gcr.io/distroless/python3-debian12

# Set metadata labels
LABEL maintainer="HamiGames <contact@hamigames.com>" \
      org.opencontainers.image.title="Lucid Base Distroless" \
      org.opencontainers.image.description="Distroless base image for Lucid project" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/HamiGames/Lucid" \
      org.opencontainers.image.vendor="HamiGames" \
      org.opencontainers.image.licenses="MIT" \
      lucid.service="base" \
      lucid.type="distroless" \
      lucid.platform="arm64" \
      lucid.security="hardened"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    LUCID_ENV=production \
    LUCID_PLATFORM=arm64 \
    LUCID_ARCHITECTURE=linux/arm64

# Create non-root user (distroless standard)
USER 65532:65532

# Set working directory
WORKDIR /app

# Copy application from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Set default command
CMD ["/usr/bin/python3", "-c", "import sys; print('Lucid Base Distroless Container Ready'); sys.exit(0)"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python3", "-c", "import sys; sys.exit(0)"]
