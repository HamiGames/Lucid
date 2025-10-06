# LUCID BLOCKCHAIN API - SPEC-4 Stage 1 Chain Plane (Distroless)
# Professional FastAPI blockchain service for Pi deployment with distroless security
# Multi-platform build for ARM64 Pi and AMD64 development
# LUCID-STRICT Mode: Enhanced security with minimal attack surface

# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS blockchain-builder

# Metadata for professional container management
LABEL maintainer="Lucid Development Team" \
      version="1.0.0-distroless" \
      description="Blockchain API service for Lucid chain plane (Distroless)" \
      org.lucid.plane="chain" \
      org.lucid.service="blockchain-api" \
      org.lucid.stage="1" \
      org.lucid.expose="8084"

# Build-time environment for dependency installation
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies and create user
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
        netcat-traditional \
        jq \
        gosu \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && groupadd --gid 1000 lucid \
    && useradd --uid 1000 --gid lucid --shell /bin/bash --create-home lucid

# Set up application directory with Pi mount path reference
WORKDIR /mnt/myssd/Lucid/04-blockchain-core/api
RUN chown -R lucid:lucid /mnt/myssd/Lucid/04-blockchain-core/api

# Install blockchain-specific Python dependencies
RUN pip install --no-cache-dir \
        "uvicorn[standard]>=0.24.0" \
        "fastapi>=0.104.0" \
        "pydantic>=2.0.0" \
        "sqlalchemy>=2.0.0" \
        "alembic>=1.12.0" \
        "asyncpg>=0.28.0" \
        "redis>=5.0.0" \
        "celery>=5.3.0" \
        "web3>=6.11.0" \
        "eth-account>=0.9.0" \
        "cryptography>=41.0.0" \
        "httpx>=0.25.0" \
        "python-multipart>=0.0.6"

# Copy requirements if it exists and install additional dependencies
COPY requirements.txt* /mnt/myssd/Lucid/04-blockchain-core/api/
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Copy application code with Pi mount structure
COPY --chown=lucid:lucid app/ /mnt/myssd/Lucid/04-blockchain-core/api/app/

# Create blockchain-specific directories
RUN mkdir -p /var/lib/blockchain /var/log/lucid/blockchain \
    && chown -R lucid:lucid /var/lib/blockchain /var/log/lucid/blockchain

# Stage 2: Distroless runtime with Python and blockchain dependencies
FROM gcr.io/distroless/python3-debian12:latest

# Metadata for runtime container
LABEL maintainer="Lucid Development Team" \
      version="1.0.0-distroless" \
      description="Blockchain API service for Lucid chain plane (Distroless Runtime)" \
      org.lucid.plane="chain" \
      org.lucid.service="blockchain-api" \
      org.lucid.stage="1" \
      org.lucid.expose="8084"

# Copy Python installation and packages from builder
COPY --from=blockchain-builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=blockchain-builder /usr/local/bin/python3.12 /usr/local/bin/python3.12
COPY --from=blockchain-builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

# Copy system dependencies for blockchain operations
COPY --from=blockchain-builder /usr/bin/curl /usr/bin/curl
COPY --from=blockchain-builder /bin/nc /bin/nc
COPY --from=blockchain-builder /usr/bin/jq /usr/bin/jq
COPY --from=blockchain-builder /usr/sbin/gosu /usr/sbin/gosu

# Copy required dynamic libraries (architecture-specific)
COPY --from=blockchain-builder /lib/*-linux-*/libc.so.6 /lib/
COPY --from=blockchain-builder /lib/*-linux-*/libssl.so.3 /lib/
COPY --from=blockchain-builder /lib/*-linux-*/libcrypto.so.3 /lib/
COPY --from=blockchain-builder /lib/*-linux-*/libz.so.1 /lib/
COPY --from=blockchain-builder /lib/*-linux-*/liblzma.so.5 /lib/
COPY --from=blockchain-builder /lib/*-linux-*/libzstd.so.1 /lib/
COPY --from=blockchain-builder /lib*/ld-linux-*.so.2 /lib64/

# Copy user and group information
COPY --from=blockchain-builder /etc/passwd /etc/passwd
COPY --from=blockchain-builder /etc/group /etc/group

# Copy CA certificates for blockchain network communication
COPY --from=blockchain-builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Copy application with Pi mount structure and proper ownership
COPY --from=blockchain-builder --chown=lucid:lucid /mnt/myssd/Lucid/04-blockchain-core/api /mnt/myssd/Lucid/04-blockchain-core/api
COPY --from=blockchain-builder --chown=lucid:lucid /var/lib/blockchain /var/lib/blockchain
COPY --from=blockchain-builder --chown=lucid:lucid /var/log/lucid/blockchain /var/log/lucid/blockchain

# Runtime environment for blockchain API
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/mnt/myssd/Lucid/04-blockchain-core/api \
    API_HOST=0.0.0.0 \
    API_PORT=8084 \
    UVICORN_WORKERS=1 \
    BLOCKCHAIN_NETWORK=mainnet \
    BLOCKCHAIN_DATA_DIR=/var/lib/blockchain

# Security and runtime configuration
EXPOSE 8084
USER lucid
WORKDIR /mnt/myssd/Lucid/04-blockchain-core/api

# Default command for blockchain API service
ENTRYPOINT ["/usr/local/bin/python3.12", "-m", "uvicorn", "app.main:app"]
CMD ["--host", "0.0.0.0", "--port", "8084", "--workers", "1"]
