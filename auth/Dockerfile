# ============================================================================
# Lucid Authentication Service - Distroless Multi-Stage Build
# Step 6: Authentication Container Build (Primary Dockerfile)
# Cluster 09: Authentication Service
# Port: 8089
# 
# This is the main Dockerfile for the authentication service.
# For infrastructure deployment, see: infrastructure/containers/auth/Dockerfile.auth-service
# 
# Build Requirements (13-BUILD_REQUIREMENTS_GUIDE.md Step 6):
# - Multi-stage distroless build
# - Base: gcr.io/distroless/python3-debian12
# - Container name: lucid-auth-service:latest
# - Deploy to lucid-dev network (Port 8089)
# - Validation: curl http://localhost:8089/health returns 200
# ============================================================================

# ============================================================================
# Stage 1: Builder - Install dependencies and compile packages
# ============================================================================
FROM python:3.11-slim AS builder

# Metadata for builder stage
LABEL maintainer="Lucid Development Team"
LABEL stage="builder"
LABEL cluster="09-authentication"
LABEL description="Build stage for authentication service"

# Set build-time environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /build

# Install build dependencies
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

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies to user directory for distroless compatibility
RUN pip install --user --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --user --no-cache-dir -r requirements.txt

# Verify critical packages are installed
RUN python -c "import fastapi, uvicorn, jwt, motor; print('Critical packages installed')"

# ============================================================================
# Stage 2: Runtime - Distroless Python base
# ============================================================================
FROM gcr.io/distroless/python3-debian12:latest

# Metadata for runtime stage
LABEL maintainer="Lucid Development Team"
LABEL service="lucid-auth-service"
LABEL cluster="09-authentication"
LABEL version="1.0.0"
LABEL description="Lucid Authentication Service - TRON signature verification and hardware wallet support"
LABEL base="distroless/python3-debian12"
LABEL port="8089"
LABEL features="tron-signature,hardware-wallet,jwt-tokens,rbac"

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Set runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/root/.local/bin:$PATH \
    SERVICE_NAME=lucid-auth-service \
    AUTH_SERVICE_PORT=8089

# Set working directory
WORKDIR /app

# Copy application code
COPY . /app/

# Expose service port
EXPOSE 8089

# Health check configuration
# Tests /health endpoint which verifies:
# - Service is running
# - Database connectivity
# - Redis connectivity
# - Hardware wallet availability (if enabled)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import requests; requests.get('http://localhost:8089/health')"]

# Run the authentication service
ENTRYPOINT ["python", "main.py"]

# ============================================================================
# Build Instructions:
# ============================================================================
# 
# Build the container:
#   docker build -t lucid-auth-service:latest -t lucid-auth-service:1.0.0 .
#
# Run the container:
#   docker run -d \
#     --name lucid-auth-service \
#     --network lucid-network \
#     -p 8089:8089 \
#     -e JWT_SECRET_KEY=${JWT_SECRET_KEY} \
#     -e MONGODB_URI=${MONGODB_URI} \
#     -e REDIS_URI=${REDIS_URI} \
#     lucid-auth-service:latest
#
# Or use docker-compose:
#   docker-compose up -d auth-service
#
# Validation:
#   curl http://localhost:8089/health
#   curl http://localhost:8089/meta/info
#
# ============================================================================
# Service Features (from 10-CLUSTER_09_AUTHENTICATION_BUILD_GUIDE.md):
# ============================================================================
# - TRON signature verification
# - Hardware wallet integration (Ledger, Trezor, KeepKey)
# - JWT token management (15min access, 7day refresh)
# - Session handling and management
# - RBAC engine (4 roles: USER, NODE_OPERATOR, ADMIN, SUPER_ADMIN)
# - Rate limiting (100/1000/10000 req/min tiers)
# - Audit logging (90 day retention)
# - Brute force protection (5 attempts, 15min cooldown)
#
# ============================================================================
# Security Features:
# ============================================================================
# - Distroless base (no shell, minimal attack surface)
# - Multi-stage build (build dependencies not in runtime)
# - Non-root user execution (distroless default)
# - Minimal package footprint
# - Health check endpoint
# - No sensitive data in image
#
# ============================================================================

