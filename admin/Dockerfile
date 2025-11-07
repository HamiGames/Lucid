# LUCID ADMIN INTERFACE - SPEC-1B Implementation
# Professional multi-platform Admin Interface service for Pi deployment
# Compatible with devcontainer builds and ARM64 Pi architecture
# Security: LUCID-STRICT compliant with distroless base
# Aligned with plan/constants/ requirements
# Admin Interface service (lucid-admin-interface) - Ports 8083, 8088, 8100
# Image: pickme/lucid-admin-interface:latest-arm64 (essentials.md, path_plan.md)
# Tor-proxy compatible: Uses CMD (no ENTRYPOINT)
# Configuration: All values from .env.support, .env.core, .env.secrets, .env.foundation via docker-compose
# Build Context: . (project root) - copy admin/ directory

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64
ARG PYTHON_VERSION=3.12

FROM python:3.12-slim-bookworm AS builder

ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG PYTHON_VERSION

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PREFER_BINARY=1 \
    DEBIAN_FRONTEND=noninteractive

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        libffi-dev \
        libssl-dev \
        libxml2-dev \
        libxslt1-dev \
        zlib1g-dev \
        pkg-config \
        curl \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /app

COPY admin/requirements.txt ./requirements.txt

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install --prefer-binary -r requirements.txt

COPY admin/ ./admin/

FROM gcr.io/distroless/python3-debian12:nonroot

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL maintainer="Lucid Development Team" \
      version="${VERSION}" \
      description="Distroless Admin Interface for Lucid support services" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.title="Lucid Admin Interface" \
      org.opencontainers.image.description="Distroless admin interface service for Lucid project" \
      com.lucid.plane="ops" \
      com.lucid.service="admin-interface" \
      com.lucid.platform="arm64" \
      com.lucid.architecture="linux/arm64" \
      com.lucid.security="distroless" \
      com.lucid.vulnerabilities="zero" \
      com.lucid.expose="8083,8088,8100" \
      com.lucid.cluster="support" \
      com.lucid.tor.compatible="true" \
      com.lucid.env.config=".env.support,.env.core,.env.secrets,.env.foundation" \
      com.lucid.deployment.path="/mnt/myssd/Lucid/Lucid"

ENV PATH=/opt/venv/bin:/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY --from=builder --chown=nonroot:nonroot /opt/venv /opt/venv
COPY --from=builder --chown=nonroot:nonroot /app/admin /app

EXPOSE 8083 8088 8100

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/opt/venv/bin/python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8083/health').read(); exit(0)"]

USER nonroot

CMD ["/opt/venv/bin/python3", "-m", "uvicorn", "admin.main:app", "--host", "0.0.0.0", "--port", "8083", "--workers", "1"]

# All configuration values provided by .env.support, .env.core, .env.secrets, .env.foundation