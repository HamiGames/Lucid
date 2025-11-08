# LUCID SERVICE MESH CONTROLLER - SPEC-1B Implementation
# Service discovery and mesh orchestration (Consul-based)
# Configuration: .env.core/.env.foundation via compose; no hardcoded values
# Build context: project root (paths prefixed with service-mesh/)

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64
ARG PYTHON_VERSION=3.11

# =============================================================================
# Stage 1: Builder
# =============================================================================
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

WORKDIR /build

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        libffi-dev \
        libssl-dev \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY service-mesh/requirements.txt ./requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --user --prefer-binary -r requirements.txt

COPY service-mesh/ ./service-mesh/

# =============================================================================
# Stage 2: Distroless runtime
# =============================================================================
FROM gcr.io/distroless/python3-debian12:latest

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

LABEL maintainer="Lucid Development Team" \
      version="${VERSION}" \
      description="Lucid Service Mesh Controller (Consul-based)" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.title="Lucid Service Mesh Controller" \
      org.opencontainers.image.description="Service discovery and mesh orchestration for Lucid" \
      com.lucid.plane="core" \
      com.lucid.service="service-mesh-controller" \
      com.lucid.platform="arm64" \
      com.lucid.architecture="linux/arm64" \
      com.lucid.security="distroless" \
      com.lucid.vulnerabilities="zero" \
      com.lucid.expose="8500,8501,8502,8600,8088" \
      com.lucid.cluster="core" \
      com.lucid.tor.compatible="true"

ENV PATH=/root/.local/bin:/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/root/.local/lib/python3.11/site-packages

WORKDIR /app

COPY --from=builder /root/.local /root/.local
COPY --from=builder --chown=65532:65532 /build/service-mesh/ ./service-mesh/

WORKDIR /app/service-mesh

EXPOSE 8500 8501 8502 8600 8088
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8500/v1/status/leader').read(); exit(0)"]

USER 65532:65532

CMD ["python3", "-c", "import asyncio; from controller.main import main; asyncio.run(main())"]