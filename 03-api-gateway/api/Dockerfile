# LUCID API SERVER - SPEC-4 Stage 0 Core Support (Distroless)
# Professional FastAPI server for Pi deployment with distroless security
# Aligned with dockerfile-design.md and Dockerfile-copy-pattern.md
# syntax=docker/dockerfile:1.5

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64
ARG PYTHON_VERSION=3.11

############################
# Stage 1 – Builder
############################
FROM --platform=$TARGETPLATFORM python:3.11-slim-bookworm AS builder

ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG PYTHON_VERSION

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PREFER_BINARY=1 \
    DEBIAN_FRONTEND=noninteractive

# Install build dependencies with apt cache mount
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    rm -rf /var/lib/apt/lists/* && \
    apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
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

# Create system directory markers (ensures COPY won't fail silently)
RUN echo "LUCID_API_SERVER_RUNTIME_DIRECTORY" > /var/run/.keep && \
    echo "LUCID_API_SERVER_LIB_DIRECTORY" > /var/lib/.keep && \
    mkdir -p /run/lucid/onion /var/log/lucid && \
    echo "LUCID_API_SERVER_RUN_LUCID" > /run/lucid/.keep && \
    echo "LUCID_API_SERVER_LOG_LUCID" > /var/log/lucid/.keep && \
    chown -R 65532:65532 /var/run /var/lib /run/lucid /var/log/lucid

# Upgrade pip
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel

# Copy requirements
COPY requirements.txt ./requirements.txt

# Ensure directory structure exists before pip install
RUN mkdir -p /root/.local/lib/python3.11/site-packages && \
    mkdir -p /root/.local/bin

# Install Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --no-cache-dir --prefer-binary -r requirements.txt

# Create marker files with actual content (ensures directory structure is locked in)
RUN echo "LUCID_API_SERVER_PACKAGES_INSTALLED_$(date +%s)" > /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    echo "LUCID_API_SERVER_BINARIES_INSTALLED_$(date +%s)" > /root/.local/bin/.lucid-marker && \
    chown -R 65532:65532 /root/.local

# Verify packages are installed (builder stage)
RUN python3 -c "import fastapi, uvicorn, pydantic, motor, pymongo, httpx, aiofiles; print('✅ critical packages installed')" && \
    python3 -c "import uvicorn; print('uvicorn location:', uvicorn.__file__)" && \
    test -d /root/.local/lib/python3.11/site-packages && \
    echo "Directory exists: /root/.local/lib/python3.11/site-packages" && \
    ls -la /root/.local/lib/python3.11/site-packages/ | head -20 && \
    echo "Package count: $(ls -1 /root/.local/lib/python3.11/site-packages/ | wc -l)"

# Copy application code
COPY app/ ./app/

############################
# Stage 2 – Runtime (Distroless)
############################
FROM --platform=$TARGETPLATFORM gcr.io/distroless/python3-debian12:latest

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL maintainer="Lucid Development Team" \
      org.opencontainers.image.title="Lucid API Server" \
      org.opencontainers.image.description="Distroless FastAPI server for Lucid sessions gateway" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      com.lucid.service="api-server" \
      com.lucid.platform="arm64" \
      com.lucid.cluster="core" \
      com.lucid.security="distroless"

ENV PATH=/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/usr/local/lib/python3.11/site-packages \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8081

WORKDIR /app

# Copy system directories from builder
COPY --from=builder --chown=65532:65532 /var/run /var/run
COPY --from=builder --chown=65532:65532 /var/lib /var/lib
COPY --from=builder --chown=65532:65532 /run/lucid /run/lucid
COPY --from=builder --chown=65532:65532 /var/log/lucid /var/log/lucid

# Copy CA certificates (distroless base already has correct linker/runtime)
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Copy Python packages (per COPY pattern guide)
COPY --from=builder --chown=65532:65532 /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder --chown=65532:65532 /root/.local/bin /usr/local/bin

# Verify packages were copied (runtime stage - fails build if missing)
RUN ["python3", "-c", "import sys; import os; \
site_packages = '/usr/local/lib/python3.11/site-packages'; \
assert os.path.exists(site_packages), site_packages + ' does not exist'; \
assert os.path.exists(os.path.join(site_packages, 'uvicorn')), 'uvicorn not found'; \
assert os.path.exists(os.path.join(site_packages, 'fastapi')), 'fastapi not found'; \
assert os.path.exists(os.path.join(site_packages, 'pydantic')), 'pydantic not found'; \
assert os.path.exists(os.path.join(site_packages, 'motor')), 'motor not found'; \
assert os.path.exists(os.path.join(site_packages, '.lucid-marker')), 'marker file not found'; \
marker_path = os.path.join(site_packages, '.lucid-marker'); \
assert os.path.getsize(marker_path) > 0, 'marker file is empty: ' + marker_path; \
print('Packages verified in runtime stage')"]

# Copy application code
COPY --chown=65532:65532 --from=builder /build/app /app/app

EXPOSE 8081

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD ["python3", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', 8081)); s.close(); exit(0 if result == 0 else 1)"]

USER 65532:65532

# Clear base ENTRYPOINT so CMD works as expected
ENTRYPOINT []

CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081"]
