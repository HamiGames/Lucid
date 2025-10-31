# ============================================================================
# Lucid Authentication Service - Distroless Multi-Stage Build
# Aligned with essentials.md: pickme/lucid-auth-service:latest-arm64, port 8089
# Build Context: Project ROOT (build from root: docker buildx build -f auth/Dockerfile .)
# ============================================================================

# ============================================================================
# STAGE 1: Builder - Install dependencies and compile packages
# ============================================================================
FROM python:3.11-slim AS builder

# Set build-time environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    BUILD_ENV=production

# Set working directory
WORKDIR /build

# Install system build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        make \
        libffi-dev \
        libssl-dev \
        libpq-dev \
        ca-certificates \
        && rm -rf /var/lib/apt/lists/*

# Copy only requirements file first (for layer caching)
COPY requirements.txt ./requirements.txt

# Install Python dependencies to user directory for distroless compatibility
RUN pip install --user --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --user --no-cache-dir -r requirements.txt

# Verify critical packages are installed
RUN python -c "import fastapi, uvicorn, jwt, motor, redis; print('✅ Critical packages installed')"

# ============================================================================
# STAGE 2: Runtime - Distroless Python base
# ============================================================================
FROM gcr.io/distroless/python3-debian12:latest

# ============================================================================
# Runtime Environment Variables
# ============================================================================
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/root/.local/lib/python3.11/site-packages \
    PATH=/root/.local/bin:/usr/local/bin:/usr/bin:/bin \
    SERVICE_NAME=lucid-auth-service

# ============================================================================
# Working Directory Setup
# ============================================================================
WORKDIR /app

# ============================================================================
# Copy Files from Builder Stage
# ============================================================================
# Copy Python packages from builder (distroless compatible location)
COPY --from=builder /root/.local /root/.local

# Copy application code (using full paths from project root)
COPY --chown=65532:65532 api/ ./api/
COPY --chown=65532:65532 middleware/ ./middleware/
COPY --chown=65532:65532 models/ ./models/
COPY --chown=65532:65532 utils/ ./utils/
COPY --chown=65532:65532 __init__.py ./__init__.py
COPY --chown=65532:65532 main.py ./main.py
COPY --chown=65532:65532 config.py ./config.py
COPY --chown=65532:65532 authentication_service.py ./authentication_service.py
COPY --chown=65532:65532 user_manager.py ./user_manager.py
COPY --chown=65532:65532 hardware_wallet.py ./hardware_wallet.py
COPY --chown=65532:65532 session_manager.py ./session_manager.py
COPY --chown=65532:65532 permissions.py ./permissions.py
COPY --chown=65532:65532 healthcheck.py ./healthcheck.py

# ============================================================================
# Expose Service Port
# ============================================================================
EXPOSE 8089

# ============================================================================
# Health Check Configuration
# ============================================================================
# essentials.md: healthcheck_port=8089, healthcheck_path=/health
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8089/health').read()"]

# ============================================================================
# Container Entry Point
# ============================================================================
# Run as non-root user (distroless default)
USER 65532:65532

# Start the authentication service
ENTRYPOINT ["python", "main.py"]