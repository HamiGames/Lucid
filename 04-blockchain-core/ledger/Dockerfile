# LUCID BLOCKCHAIN-LEDGER - SPEC-4 Stage 1 Chain Plane (Distroless)
# Professional ledger service for Pi deployment with distroless security
# Multi-platform build for ARM64 Pi and AMD64 development

# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS ledger-builder

# Metadata for professional container management
LABEL maintainer="Lucid Development Team" \
      version="1.0.0-distroless" \
      description="Blockchain Ledger service for Lucid chain plane (Distroless)" \
      org.lucid.plane="chain" \
      org.lucid.service="blockchain-ledger" \
      org.lucid.stage="1" \
      org.lucid.expose="8080"

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

# Set up application directory
WORKDIR /app
RUN chown -R lucid:lucid /app

# Install ledger-specific Python dependencies
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
COPY requirements.txt* /app/
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Copy application code
COPY --chown=lucid:lucid . /app/

# Create ledger-specific directories
RUN mkdir -p /var/lib/ledger /var/log/lucid/ledger \
    && chown -R lucid:lucid /var/lib/ledger /var/log/lucid/ledger

# Stage 2: Distroless runtime with Python and ledger dependencies
FROM gcr.io/distroless/python3-debian12:latest

# Metadata for runtime container
LABEL maintainer="Lucid Development Team" \
      version="1.0.0-distroless" \
      description="Blockchain Ledger service for Lucid chain plane (Distroless Runtime)" \
      org.lucid.plane="chain" \
      org.lucid.service="blockchain-ledger" \
      org.lucid.stage="1" \
      org.lucid.expose="8080"

# Copy Python installation and packages from builder
COPY --from=ledger-builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=ledger-builder /usr/local/bin/python3.12 /usr/local/bin/python3.12
COPY --from=ledger-builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

# Copy system dependencies for ledger operations
COPY --from=ledger-builder /usr/bin/curl /usr/bin/curl
COPY --from=ledger-builder /bin/nc /bin/nc
COPY --from=ledger-builder /usr/bin/jq /usr/bin/jq
COPY --from=ledger-builder /usr/sbin/gosu /usr/sbin/gosu

# Copy required dynamic libraries (architecture-specific)
COPY --from=ledger-builder /lib/*-linux-*/libc.so.6 /lib/
COPY --from=ledger-builder /lib/*-linux-*/libssl.so.3 /lib/
COPY --from=ledger-builder /lib/*-linux-*/libcrypto.so.3 /lib/
COPY --from=ledger-builder /lib/*-linux-*/libz.so.1 /lib/
COPY --from=ledger-builder /lib/*-linux-*/liblzma.so.5 /lib/
COPY --from=ledger-builder /lib/*-linux-*/libzstd.so.1 /lib/
COPY --from=ledger-builder /lib*/ld-linux-*.so.2 /lib64/

# Copy user and group information
COPY --from=ledger-builder /etc/passwd /etc/passwd
COPY --from=ledger-builder /etc/group /etc/group

# Copy CA certificates for ledger network communication
COPY --from=ledger-builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Copy application with proper ownership
COPY --from=ledger-builder --chown=lucid:lucid /app /app
COPY --from=ledger-builder --chown=lucid:lucid /var/lib/ledger /var/lib/ledger
COPY --from=ledger-builder --chown=lucid:lucid /var/log/lucid/ledger /var/log/lucid/ledger

# Runtime environment for ledger service
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    API_HOST=0.0.0.0 \
    API_PORT=8080 \
    UVICORN_WORKERS=1 \
    LEDGER_DATA_DIR=/var/lib/ledger

# Security and runtime configuration
EXPOSE 8080
USER lucid
WORKDIR /app

# Default command for ledger service
ENTRYPOINT ["/usr/local/bin/python3.12", "main.py"]
