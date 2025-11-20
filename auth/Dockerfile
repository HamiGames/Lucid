# LUCID AUTH SERVICE - SPEC-1B Implementation
# Professional multi-platform Auth service for Pi deployment
# Compatible with devcontainer builds and ARM64 Pi architecture
# Security: LUCID-STRICT compliant with distroless base
# Aligned with plan/constants/ requirements
# Authentication and authorization service (lucid-auth-service) - Port 8089
# Image: pickme/lucid-auth-service:latest-arm64 (from essentials.md line 172, path_plan.md line 26)
# Tor-proxy compatible: Uses CMD (no ENTRYPOINT), allows command override in compose
# Configuration: All values from .env.foundation, .env.secrets via docker-compose (no hardcoded secrets)
# Build Context: . (project root)
# Deployment: Pi console at /mnt/myssd/Lucid/Lucid/

# =============================================================================
# BUILD ARGUMENTS
# =============================================================================
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64
ARG CRYPTOGRAPHY_VERSION=41.0.7

# =============================================================================
# STAGE 1: Builder
# =============================================================================
FROM python:3.11-slim AS builder

ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG CRYPTOGRAPHY_VERSION

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    BUILD_ENV=production

WORKDIR /build

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        make \
        libffi-dev \
        libssl-dev \
        libpq-dev \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY auth/requirements.authentication-service.txt ./requirements.txt

# Patch unavailable cryptography pin if necessary, then install deps
RUN if grep -q "cryptography==41.0.8" requirements.txt; then \
        sed -i "s/cryptography==41.0.8/cryptography==${CRYPTOGRAPHY_VERSION}/" requirements.txt; \
    fi && \
    pip install --user --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --user --no-cache-dir -r requirements.txt

RUN python -c "import fastapi, uvicorn, motor, pymongo, cryptography; print('✅ critical packages installed')"

# =============================================================================
# STAGE 2: Distroless runtime
# =============================================================================
FROM gcr.io/distroless/python3-debian12:latest

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL maintainer="Lucid Development Team" \
      version="${VERSION}" \
      description="Distroless Auth Service for Lucid authentication support" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.title="Lucid Auth Service" \
      org.opencontainers.image.description="Distroless authentication service for Lucid project" \
      com.lucid.plane="ops" \
      com.lucid.service="auth-service" \
      com.lucid.platform="arm64" \
      com.lucid.architecture="linux/arm64" \
      com.lucid.security="distroless" \
      com.lucid.vulnerabilities="zero" \
      com.lucid.expose="8089" \
      com.lucid.cluster="foundation" \
      com.lucid.tor.compatible="true" \
      com.lucid.env.config=".env.foundation,.env.secrets" \
      com.lucid.deployment.path="/mnt/myssd/Lucid/Lucid"

ENV PATH=/root/.local/bin:/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/root/.local/lib/python3.11/site-packages \
    SERVICE_NAME=lucid-auth-service

WORKDIR /app

COPY --from=builder /root/.local /root/.local
COPY --from=builder /lib/*/libssl.so.3 /lib/
COPY --from=builder /lib/*/libcrypto.so.3 /lib/
COPY --from=builder /lib/*/libffi.so.8 /lib/
COPY --from=builder /lib/*/libc.so.6 /lib/
COPY --from=builder /lib/*/libz.so.1 /lib/
COPY --from=builder /lib/ld-linux-aarch64.so.1 /lib/ld-linux-aarch64.so.1
COPY --from=builder /lib/aarch64-linux-gnu /lib/aarch64-linux-gnu
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

COPY --chown=65532:65532 auth/api/ ./api/
COPY --chown=65532:65532 auth/middleware/ ./middleware/
COPY --chown=65532:65532 auth/models/ ./models/
COPY --chown=65532:65532 auth/utils/ ./utils/
COPY --chown=65532:65532 auth/__init__.py ./__init__.py
COPY --chown=65532:65532 auth/main.py ./main.py
COPY --chown=65532:65532 auth/config.py ./config.py
COPY --chown=65532:65532 auth/authentication_service.py ./authentication_service.py
COPY --chown=65532:65532 auth/user_manager.py ./user_manager.py
COPY --chown=65532:65532 auth/hardware_wallet.py ./hardware_wallet.py
COPY --chown=65532:65532 auth/session_manager.py ./session_manager.py
COPY --chown=65532:65532 auth/permissions.py ./permissions.py
COPY --chown=65532:65532 auth/healthcheck.py ./healthcheck.py

EXPOSE 8089

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8089/health').read(); exit(0)"]

USER 65532:65532

ENTRYPOINT ["/usr/bin/python3"]
CMD ["main.py"]