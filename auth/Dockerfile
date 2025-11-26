# LUCID AUTH SERVICE - SPEC-1B Implementation
# Professional multi-platform Auth service for Pi deployment
# Compatible with devcontainer builds and ARM64 Pi architecture
# Security: LUCID-STRICT compliant with distroless base
# Authentication and authorization service (lucid-auth-service) - Port 8089
# Build context: project root (./)
# Deployment path: /mnt/myssd/Lucid/Lucid/

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64
ARG CRYPTOGRAPHY_VERSION=41.0.7
ARG PROTOBUF_VERSION=4.25.1

FROM --platform=$TARGETPLATFORM python:3.11-slim AS builder

ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG CRYPTOGRAPHY_VERSION
ARG PROTOBUF_VERSION

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    BUILD_ENV=production

WORKDIR /build

# Create placeholder files in system directories (ensures they're baked into image)
RUN echo "LUCID_AUTH_SERVICE_RUNTIME_DIRECTORY" > /var/run/.keep && \
    echo "LUCID_AUTH_SERVICE_LIB_DIRECTORY" > /var/lib/.keep && \
    chown -R 65532:65532 /var/run /var/lib

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc g++ make libffi-dev libssl-dev libpq-dev ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY auth/requirements.authentication-service.txt ./requirements.txt

RUN python - <<'PY'
from pathlib import Path
src = Path("requirements.txt").read_text().splitlines()
base, hw = [], []
current = base
for line in src:
    stripped = line.strip()
    if stripped.startswith("# Hardware wallet support"):
        current = hw
        continue
    if stripped.startswith("# TRON blockchain integration"):
        current = base
    if stripped and not stripped.startswith("#"):
        current.append(stripped)
Path("requirements.base.txt").write_text("\n".join(base) + "\n")
Path("requirements.hardware.txt").write_text("\n".join(hw) + "\n")
PY

RUN if grep -q "cryptography==41.0.7" requirements.base.txt || grep -q "cryptography==41.0.7" requirements.hardware.txt; then \
        sed -i "s/cryptography==41.0.8/cryptography==${CRYPTOGRAPHY_VERSION}/g" requirements.base.txt; \
        sed -i "s/cryptography==41.0.8/cryptography==${CRYPTOGRAPHY_VERSION}/g" requirements.hardware.txt; \
    fi

# Ensure directory structure exists before pip install
RUN mkdir -p /root/.local/lib/python3.11/site-packages && \
    mkdir -p /root/.local/bin

RUN pip install --user --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --user --no-cache-dir protobuf==${PROTOBUF_VERSION} && \
    pip install --user --no-cache-dir -r requirements.base.txt && \
    if [ -s requirements.hardware.txt ]; then \
        pip install --user --no-cache-dir --no-deps -r requirements.hardware.txt; \
    fi

# Create placeholder files with actual content (ensures directory structure is locked in)
RUN echo "LUCID_AUTH_PACKAGES_INSTALLED_$(date +%s)" > /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    echo "LUCID_AUTH_BINARIES_INSTALLED_$(date +%s)" > /root/.local/bin/.lucid-marker && \
    chown -R 65532:65532 /root/.local

# Verify packages are installed and verify directory structure
RUN python -c "import fastapi, uvicorn, motor, pymongo, cryptography, redis, jwt, bcrypt, eth_account, web3, base58, async_timeout; print('✅ critical packages installed')" && \
    python -c "import uvicorn; print('uvicorn location:', uvicorn.__file__)" && \
    test -d /root/.local/lib/python3.11/site-packages && \
    echo "Directory exists: /root/.local/lib/python3.11/site-packages" && \
    ls -la /root/.local/lib/python3.11/site-packages/ | head -20 && \
    echo "Package count: $(ls -1 /root/.local/lib/python3.11/site-packages/ | wc -l)"

# Copy auth source code to builder stage
COPY auth/api/ ./auth/api/
COPY auth/middleware/ ./auth/middleware/
COPY auth/models/ ./auth/models/
COPY auth/utils/ ./auth/utils/
COPY auth/__init__.py ./auth/__init__.py
COPY auth/main.py ./auth/main.py
COPY auth/config.py ./auth/config.py
COPY auth/authentication_service.py ./auth/authentication_service.py
COPY auth/user_manager.py ./auth/user_manager.py
COPY auth/hardware_wallet.py ./auth/hardware_wallet.py
COPY auth/session_manager.py ./auth/session_manager.py
COPY auth/permissions.py ./auth/permissions.py
COPY auth/healthcheck.py ./auth/healthcheck.py

# Lock in source directory structure with marker files (per Dockerfile-copy-pattern)
RUN echo "LUCID_AUTH_SOURCE_API_$(date +%s)" > ./auth/api/.lucid-api-marker && \
    echo "LUCID_AUTH_SOURCE_MIDDLEWARE_$(date +%s)" > ./auth/middleware/.lucid-middleware-marker && \
    echo "LUCID_AUTH_SOURCE_MODELS_$(date +%s)" > ./auth/models/.lucid-models-marker && \
    echo "LUCID_AUTH_SOURCE_UTILS_$(date +%s)" > ./auth/utils/.lucid-utils-marker && \
    echo "LUCID_AUTH_MAIN_$(date +%s)" > ./auth/main.py.lucid-marker && \
    chown -R 65532:65532 ./auth

FROM --platform=$TARGETPLATFORM gcr.io/distroless/python3-debian12:latest

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL maintainer="Lucid Development Team" \
      version="${VERSION}" \
      description="Distroless Auth Service for Lucid authentication support" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      com.lucid.service="auth-service" \
      com.lucid.cluster="foundation"

ENV PATH=/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/usr/local/lib/python3.11/site-packages \
    SERVICE_NAME=lucid-auth-service

WORKDIR /app

# Copy runtime directories from builder
COPY --from=builder --chown=65532:65532 /var/run /var/run
COPY --from=builder --chown=65532:65532 /var/lib /var/lib

# Copy Python packages to /usr/local (SAME PATTERN AS ELASTICSEARCH - exact directory structure)
# Directory already populated with packages + marker files from builder stage
COPY --from=builder --chown=65532:65532 /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder --chown=65532:65532 /root/.local/bin /usr/local/bin

# Verify packages were copied (this will fail the build if packages are missing)
RUN ["/usr/bin/python3.11", "-c", "import sys; import os; site_packages = '/usr/local/lib/python3.11/site-packages'; assert os.path.exists(site_packages), f'{site_packages} does not exist'; assert os.path.exists(os.path.join(site_packages, 'uvicorn')), 'uvicorn not found'; assert os.path.exists(os.path.join(site_packages, 'redis')), 'redis not found'; assert os.path.exists(os.path.join(site_packages, 'async_timeout')) or os.path.exists(os.path.join(site_packages, 'async_timeout.py')), 'async_timeout not found'; print('Packages verified in runtime stage')"]

# Copy dynamic linker for ARM64
COPY --from=builder /lib/ld-linux-aarch64.so.1 /lib/ld-linux-aarch64.so.1

# Copy arch-specific libraries directory (SAME PATTERN AS ELASTICSEARCH - entire directory, not individual files)
COPY --from=builder /lib/aarch64-linux-gnu /lib/aarch64-linux-gnu

# Copy CA certificates
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Copy auth source code from builder (directory already populated with source + marker files)
COPY --from=builder --chown=65532:65532 /build/auth/api ./api
COPY --from=builder --chown=65532:65532 /build/auth/middleware ./middleware
COPY --from=builder --chown=65532:65532 /build/auth/models ./models
COPY --from=builder --chown=65532:65532 /build/auth/utils ./utils
COPY --from=builder --chown=65532:65532 /build/auth/__init__.py ./__init__.py
COPY --from=builder --chown=65532:65532 /build/auth/main.py ./main.py
COPY --from=builder --chown=65532:65532 /build/auth/config.py ./config.py
COPY --from=builder --chown=65532:65532 /build/auth/authentication_service.py ./authentication_service.py
COPY --from=builder --chown=65532:65532 /build/auth/user_manager.py ./user_manager.py
COPY --from=builder --chown=65532:65532 /build/auth/hardware_wallet.py ./hardware_wallet.py
COPY --from=builder --chown=65532:65532 /build/auth/session_manager.py ./session_manager.py
COPY --from=builder --chown=65532:65532 /build/auth/permissions.py ./permissions.py
COPY --from=builder --chown=65532:65532 /build/auth/healthcheck.py ./healthcheck.py

# Verify source code was copied (this will fail the build if files are missing)
RUN ["/usr/bin/python3.11", "-c", "import os, importlib.util; assert os.path.exists('/app/main.py'), 'main.py missing'; assert os.path.exists('/app/api'), 'api directory missing'; assert os.path.exists('/app/middleware'), 'middleware directory missing'; assert os.path.exists('/app/models'), 'models directory missing'; assert os.path.exists('/app/utils'), 'utils directory missing'; assert importlib.util.find_spec('main', package=None), 'main module not importable'; print('Auth source code verified in runtime stage')"]

EXPOSE 8089

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8089/health').read(); exit(0)"]

USER 65532:65532

ENTRYPOINT ["/usr/bin/python3"]
CMD ["main.py"]