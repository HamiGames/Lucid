# LUCID AUTH SERVICE - SPEC-1B Implementation
# Professional multi-platform Auth service for Pi deployment
# Compatible with devcontainer builds and ARM64 Pi architecture
# Security: LUCID-STRICT compliant with distroless base
# Authentication and authorization service (lucid-auth-service) - Port 8089
# Build context: project root (./)

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64
ARG CRYPTOGRAPHY_VERSION=41.0.7
ARG PROTOBUF_VERSION=4.25.1

FROM python:3.11-slim AS builder

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

# CRITICAL: Explicitly create build directory before WORKDIR (per Dockerfile-copy-pattern.md)
RUN mkdir -p /build
WORKDIR /build

# Create placeholder files in system directories (ensures they're baked into image)
RUN echo "LUCID_AUTH_SERVICE_RUNTIME_DIRECTORY" > /var/run/.keep && \
    echo "LUCID_AUTH_SERVICE_LIB_DIRECTORY" > /var/lib/.keep && \
    chown -R 65532:65532 /var/run /var/lib

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc g++ make libffi-dev libssl-dev libpq-dev ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy pre-split requirements files (simpler and more maintainable)
COPY auth/requirements.base.txt /build/requirements.base.txt
COPY auth/requirements.hardware.txt /build/requirements.hardware.txt

# Verify requirements files exist and normalize cryptography version
RUN test -f /build/requirements.base.txt || (echo "ERROR: requirements.base.txt not found" && exit 1) && \
    test -f /build/requirements.hardware.txt || (echo "ERROR: requirements.hardware.txt not found" && exit 1) && \
    # Normalize cryptography version to match build arg (replace any version with CRYPTOGRAPHY_VERSION)
    sed -i "s/cryptography==[0-9.]*/cryptography==${CRYPTOGRAPHY_VERSION}/g" /build/requirements.base.txt || (echo "ERROR: sed failed on requirements.base.txt" && exit 1) && \
    sed -i "s/cryptography==[0-9.]*/cryptography==${CRYPTOGRAPHY_VERSION}/g" /build/requirements.hardware.txt || (echo "ERROR: sed failed on requirements.hardware.txt" && exit 1) && \
    # Verify the replacement worked
    (grep -q "cryptography==${CRYPTOGRAPHY_VERSION}" /build/requirements.base.txt || echo "WARNING: cryptography version not found in requirements.base.txt")

# Ensure directory structure exists before pip install
RUN mkdir -p /root/.local/lib/python3.11/site-packages && \
    mkdir -p /root/.local/bin

RUN pip install --user --no-cache-dir --upgrade pip setuptools wheel || (echo "ERROR: pip upgrade failed" && exit 1) && \
    pip install --user --no-cache-dir protobuf==${PROTOBUF_VERSION} || (echo "ERROR: protobuf installation failed" && exit 1) && \
    pip install --user --no-cache-dir -r /build/requirements.base.txt || (echo "ERROR: requirements.base.txt installation failed" && exit 1) && \
    (python -m pip check || (echo "ERROR: pip dependency check failed after base requirements" && exit 1)) && \
    (python -c "import sys; sys.path.insert(0, '/root/.local/lib/python3.11/site-packages'); import fastapi; print('✅ fastapi')" || (echo "ERROR: fastapi import failed" && exit 1)) && \
    (python -c "import sys; sys.path.insert(0, '/root/.local/lib/python3.11/site-packages'); import uvicorn; print('✅ uvicorn')" || (echo "ERROR: uvicorn import failed" && exit 1)) && \
    (python -c "import sys; sys.path.insert(0, '/root/.local/lib/python3.11/site-packages'); import motor, pymongo; print('✅ database packages')" || (echo "ERROR: database packages import failed" && exit 1)) && \
    (python -c "import sys; sys.path.insert(0, '/root/.local/lib/python3.11/site-packages'); import cryptography, redis; print('✅ crypto/redis packages')" || (echo "ERROR: crypto/redis packages import failed" && exit 1)) && \
    (python -c "import sys; sys.path.insert(0, '/root/.local/lib/python3.11/site-packages'); import jwt; print('✅ jwt')" || (echo "ERROR: jwt import failed" && exit 1)) && \
    (python -c "import sys; sys.path.insert(0, '/root/.local/lib/python3.11/site-packages'); import bcrypt; print('✅ bcrypt')" || (echo "ERROR: bcrypt import failed" && exit 1)) && \
    (python -c "import sys; sys.path.insert(0, '/root/.local/lib/python3.11/site-packages'); import eth_account, web3, base58; print('✅ blockchain packages')" || (echo "ERROR: blockchain packages import failed" && exit 1)) && \
    (python -c "import sys; sys.path.insert(0, '/root/.local/lib/python3.11/site-packages'); import async_timeout, starlette; print('✅ async packages')" || (echo "ERROR: async packages import failed" && exit 1)) && \
    (python -c "import sys; sys.path.insert(0, '/root/.local/lib/python3.11/site-packages'); import pydantic, pydantic_settings; print('✅ pydantic packages')" || (echo "ERROR: pydantic packages import failed" && exit 1)) && \
    (python -c "import sys; sys.path.insert(0, '/root/.local/lib/python3.11/site-packages'); import tronpy, requests; print('✅ All critical packages verified after base installation')" || (echo "ERROR: tronpy/requests import failed" && exit 1)) && \
    if [ -s /build/requirements.hardware.txt ]; then \
        pip install --user --no-cache-dir --no-deps -r /build/requirements.hardware.txt || (echo "ERROR: hardware wallet requirements installation failed" && exit 1); \
    fi

# Create placeholder files with actual content (ensures directory structure is locked in)
# CRITICAL: Must be AFTER pip install, with actual content (not empty)
RUN echo "LUCID_AUTH_PACKAGES_INSTALLED_$(date +%s)" > /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    echo "LUCID_AUTH_BINARIES_INSTALLED_$(date +%s)" > /root/.local/bin/.lucid-marker && \
    chown -R 65532:65532 /root/.local

# Verify packages are installed and verify directory structure
# CRITICAL: Import all packages used in the codebase to catch missing dependencies during build
# CRITICAL: Add sys.path before importing to ensure packages are found
RUN python -c "import sys; sys.path.insert(0, '/root/.local/lib/python3.11/site-packages'); import fastapi, uvicorn, motor, pymongo, cryptography, redis, jwt, bcrypt, eth_account, web3, base58, async_timeout, starlette, pydantic, pydantic_settings, tronpy, requests; print('✅ critical packages installed')" && \
    python -c "import sys; sys.path.insert(0, '/root/.local/lib/python3.11/site-packages'); import uvicorn; print('uvicorn location:', uvicorn.__file__)" && \
    test -d /root/.local/lib/python3.11/site-packages || (echo "ERROR: site-packages directory missing" && exit 1) && \
    test -d /root/.local/bin || (echo "ERROR: bin directory missing" && exit 1) && \
    echo "Directory exists: /root/.local/lib/python3.11/site-packages" && \
    ls -la /root/.local/lib/python3.11/site-packages/ | head -20 && \
    package_count=$(ls -1 /root/.local/lib/python3.11/site-packages/ | wc -l) && \
    test "$package_count" -gt 0 || (echo "ERROR: No packages found in site-packages" && exit 1) && \
    echo "Package count: $package_count"

# Copy auth source code to builder stage - CRITICAL: Copy to /build/auth/ to maintain package structure
# Note: COPY will include all files; we clean up platform-specific and cache files immediately after
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

# CRITICAL: Remove platform-specific files and Python cache files immediately after COPY
# This prevents silently passing non-Linux files and cache artifacts into the image
RUN find ./auth -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find ./auth -type f -name "*.pyc" -delete 2>/dev/null || true && \
    find ./auth -type f -name "*.pyo" -delete 2>/dev/null || true && \
    find ./auth -type f -name ".DS_Store" -delete 2>/dev/null || true && \
    find ./auth -type f -name "Thumbs.db" -delete 2>/dev/null || true && \
    find ./auth -type f -name "desktop.ini" -delete 2>/dev/null || true && \
    find ./auth -type f -name "*.swp" -delete 2>/dev/null || true && \
    find ./auth -type f -name "*.swo" -delete 2>/dev/null || true && \
    find ./auth -type f -name "*~" -delete 2>/dev/null || true

# Verify no unwanted files remain (this will fail the build if verification fails)
RUN test ! -d ./auth/api/__pycache__ && \
    test ! -d ./auth/middleware/__pycache__ && \
    test ! -d ./auth/models/__pycache__ && \
    test ! -d ./auth/utils/__pycache__ && \
    echo "✅ Verified: No __pycache__ directories present" && \
    find ./auth -name "*.pyc" -o -name "*.pyo" -o -name ".DS_Store" -o -name "Thumbs.db" | wc -l | xargs test 0 -eq && \
    echo "✅ Verified: No platform-specific or cache files present" && \
    # CRITICAL: Verify imports are correct (catch old cached versions)
    (grep -q "from auth.models.user" ./auth/api/auth_routes.py || (echo "ERROR: auth_routes.py has incorrect import 'from models.user' - should be 'from auth.models.user'" && exit 1)) && \
    (grep -q "from auth.models.session" ./auth/api/auth_routes.py || (echo "ERROR: auth_routes.py missing correct session import" && exit 1)) && \
    (grep -q "from auth.models.user" ./auth/api/user_routes.py || (echo "ERROR: user_routes.py has incorrect import" && exit 1)) && \
    (grep -q "from auth.models.session" ./auth/api/session_routes.py || (echo "ERROR: session_routes.py has incorrect import" && exit 1)) && \
    (grep -q "from auth.models.hardware_wallet" ./auth/api/hardware_wallet_routes.py || (echo "ERROR: hardware_wallet_routes.py has incorrect import" && exit 1)) && \
    echo "✅ Verified: All API route files have correct imports (auth.models.*)"

# Lock in source directory structure with marker files (per Dockerfile-copy-pattern)
# CRITICAL: Create marker files with actual content AFTER copying source code
RUN echo "LUCID_AUTH_SOURCE_API_$(date +%s)" > ./auth/api/.lucid-api-marker && \
    echo "LUCID_AUTH_SOURCE_MIDDLEWARE_$(date +%s)" > ./auth/middleware/.lucid-middleware-marker && \
    echo "LUCID_AUTH_SOURCE_MODELS_$(date +%s)" > ./auth/models/.lucid-models-marker && \
    echo "LUCID_AUTH_SOURCE_UTILS_$(date +%s)" > ./auth/utils/.lucid-utils-marker && \
    echo "LUCID_AUTH_MAIN_$(date +%s)" > ./auth/main.py.lucid-marker && \
    chown -R 65532:65532 ./auth

# Copy verification script for runtime stage (maintainable alternative to long inline Python)
# Note: This script is only executed in the runtime stage, not in builder
COPY auth/verify_runtime.py ./verify_runtime.py
RUN chmod +x ./verify_runtime.py && \
    echo "✅ Verification script copied to builder stage (will be used in runtime stage)"

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
      com.lucid.service="auth-service" \
      com.lucid.cluster="foundation"

ENV PATH=/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/usr/local/lib/python3.11/site-packages \
    SERVICE_NAME=lucid-auth-service

WORKDIR /app

# Copy runtime directories from builder (directory already populated with .keep files)
# CRITICAL: Verify only .keep files exist before copying
COPY --from=builder --chown=65532:65532 /var/run /var/run
COPY --from=builder --chown=65532:65532 /var/lib /var/lib

# Copy dynamic linker for ARM64 (required for native extensions like cryptography, grpcio)
COPY --from=builder /lib/ld-linux-aarch64.so.1 /lib/ld-linux-aarch64.so.1

# Copy arch-specific libraries directory
# Required for ARM64 native extensions and shared libraries
# Note: This copies the entire directory; ensure builder stage only contains required libraries
COPY --from=builder /lib/aarch64-linux-gnu /lib/aarch64-linux-gnu

# Copy CA certificates (required for SSL/TLS operations)
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Copy Python packages to /usr/local (SAME PATTERN AS ELASTICSEARCH - exact directory structure)
# Directory already populated with packages + marker files from builder stage
COPY --from=builder --chown=65532:65532 /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder --chown=65532:65532 /root/.local/bin /usr/local/bin

# Verify packages were copied (this will fail the build if packages are missing)
# CRITICAL: Check all critical packages used in the codebase to catch COPY failures
# CRITICAL: Add site-packages to sys.path before importing (ensures packages can be found in distroless)
# CRITICAL: Verify marker file exists and has content (prevents silent COPY failures per Dockerfile-copy-pattern)
RUN ["/usr/bin/python3.11", "-c", "import sys; import os; import importlib.util; site_packages = '/usr/local/lib/python3.11/site-packages'; bin_dir = '/usr/local/bin'; sys.path.insert(0, site_packages); assert os.path.exists(site_packages), f'ERROR: {site_packages} does not exist'; assert os.path.isdir(site_packages), f'ERROR: {site_packages} is not a directory'; assert os.path.exists(bin_dir), f'ERROR: {bin_dir} does not exist'; assert os.path.isdir(bin_dir), f'ERROR: {bin_dir} is not a directory'; marker_path = os.path.join(site_packages, '.lucid-marker'); bin_marker_path = os.path.join(bin_dir, '.lucid-marker'); assert os.path.exists(marker_path), f'ERROR: marker file not found: {marker_path}'; assert os.path.exists(bin_marker_path), f'ERROR: bin marker file not found: {bin_marker_path}'; assert os.path.getsize(marker_path) > 0, f'ERROR: marker file is empty: {marker_path}'; assert os.path.getsize(bin_marker_path) > 0, f'ERROR: bin marker file is empty: {bin_marker_path}'; required = ('fastapi', 'uvicorn', 'motor', 'pymongo', 'cryptography', 'redis', 'jwt', 'bcrypt', 'eth_account', 'web3', 'base58', 'async_timeout', 'starlette', 'pydantic', 'pydantic_settings', 'tronpy', 'requests'); failed = [pkg for pkg in required if not importlib.util.find_spec(pkg)]; assert len(failed) == 0, f'ERROR: Packages cannot be imported: {failed}'; [importlib.import_module(pkg) for pkg in required]; assert os.path.exists(os.path.join(site_packages, 'uvicorn')), 'ERROR: uvicorn not found'; assert os.path.exists(os.path.join(site_packages, 'redis')) or os.path.exists(os.path.join(site_packages, 'redis/__init__.py')), 'ERROR: redis not found'; assert os.path.exists(os.path.join(site_packages, 'async_timeout')) or os.path.exists(os.path.join(site_packages, 'async_timeout.py')), 'ERROR: async_timeout not found'; print('✅ All critical packages verified in runtime stage: directories exist, imports work, and marker files have content')"]

# Copy auth source code from builder - CRITICAL: Copy files to /app/ root level for proper imports
COPY --from=builder --chown=65532:65532 /build/auth/api ./auth/api
COPY --from=builder --chown=65532:65532 /build/auth/middleware ./auth/middleware
COPY --from=builder --chown=65532:65532 /build/auth/models ./auth/models
COPY --from=builder --chown=65532:65532 /build/auth/utils ./auth/utils
COPY --from=builder --chown=65532:65532 /build/auth/__init__.py ./auth/__init__.py
COPY --from=builder --chown=65532:65532 /build/auth/main.py ./auth/main.py
COPY --from=builder --chown=65532:65532 /build/auth/config.py ./auth/config.py
COPY --from=builder --chown=65532:65532 /build/auth/authentication_service.py ./auth/authentication_service.py
COPY --from=builder --chown=65532:65532 /build/auth/user_manager.py ./auth/user_manager.py
COPY --from=builder --chown=65532:65532 /build/auth/hardware_wallet.py ./auth/hardware_wallet.py
COPY --from=builder --chown=65532:65532 /build/auth/session_manager.py ./auth/session_manager.py
COPY --from=builder --chown=65532:65532 /build/auth/permissions.py ./auth/permissions.py
COPY --from=builder --chown=65532:65532 /build/auth/healthcheck.py ./auth/healthcheck.py

# Copy verification script from builder stage
COPY --from=builder --chown=65532:65532 /build/verify_runtime.py ./verify_runtime.py

# Verify source code was copied and no unwanted files are present
# CRITICAL: Files are copied to /app/auth/ not /app/ root - verify correct paths
# CRITICAL: Also verify imports are correct to catch Docker cache issues
# CRITICAL: Check ALL route files for correct imports (auth.models.* not models.*)
# Using dedicated verification script for maintainability and easier debugging
RUN ["/usr/bin/python3.11", "./verify_runtime.py"]

EXPOSE 8089

# CRITICAL FIX: Use full path /usr/bin/python3 instead of python3 for consistency with ENTRYPOINT
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/usr/bin/python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8089/health').read(); exit(0)"]

USER 65532:65532

ENTRYPOINT ["/usr/bin/python3"]
CMD ["-m", "auth.main"]
