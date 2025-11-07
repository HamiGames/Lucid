# LUCID NODE MANAGEMENT - SPEC-1B Implementation
# Professional multi-platform Node Management service for Pi deployment
# Compatible with devcontainer builds and ARM64 Pi architecture
# Security: LUCID-STRICT compliant with distroless base
# Aligned with plan/constants/ requirements
# Node Management service (lucid-node-management) - Ports 8095, 8099
# Image: pickme/lucid-node-management:latest-arm64 (essentials.md, path_plan.md)
# Tor-proxy compatible: Uses CMD (no ENTRYPOINT)
# Configuration: All values from .env.application, .env.core, .env.secrets, .env.foundation via docker-compose
# Build Context: . (project root) - copy node/ directory

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64
ARG PYTHON_VERSION=3.11

FROM python:3.11-slim AS builder

ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG PYTHON_VERSION

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
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
        pkg-config \
        curl \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /build

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip wheel setuptools

COPY node/requirements.txt ./requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --prefer-binary -r requirements.txt

COPY node/ ./node/

FROM gcr.io/distroless/python3-debian12:latest

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL maintainer="Lucid Development Team" \
      version="${VERSION}" \
      description="Distroless Node Management for Lucid node management support" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.title="Lucid Node Management" \
      org.opencontainers.image.description="Distroless node management service for Lucid project" \
      com.lucid.plane="ops" \
      com.lucid.service="node-management" \
      com.lucid.platform="arm64" \
      com.lucid.architecture="linux/arm64" \
      com.lucid.security="distroless" \
      com.lucid.vulnerabilities="zero" \
      com.lucid.expose="8095,8099" \
      com.lucid.cluster="application" \
      com.lucid.tor.compatible="true" \
      com.lucid.env.config=".env.application,.env.core,.env.secrets,.env.foundation" \
      com.lucid.deployment.path="/mnt/myssd/Lucid/Lucid"

ENV PATH=/root/.local/bin:/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/root/.local/lib/python3.11/site-packages

WORKDIR /app

COPY --from=builder /root/.local /root/.local
COPY --chown=65532:65532 --from=builder /build/node /app

EXPOSE 8095 8099

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8095/health').read(); exit(0)"]

USER 65532:65532

CMD ["python3", "-m", "main"]

# All configuration comes from .env.application, .env.core, .env.secrets, .env.foundation