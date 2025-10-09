# LUCID API SERVER - SPEC-4 Stage 0 Core Support (Distroless)
# Professional FastAPI server for Pi deployment with distroless security
# Multi-platform build for ARM64 Pi and AMD64 development

# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS python-builder

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

# Install Python dependencies
WORKDIR /app
COPY requirements.txt* /app/
RUN pip install --no-cache-dir \
        "uvicorn[standard]>=0.24.0" \
        "fastapi>=0.104.0" \
        "pydantic>=2.0.0" \
        "motor>=3.3.0" \
        "pymongo>=4.5.0" \
        "python-multipart>=0.0.6" \
        "python-jose[cryptography]>=3.3.0" \
        "passlib[bcrypt]>=1.7.4" \
        "aiofiles>=23.0.0" \
        "httpx>=0.25.0" \
    && if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Create application directories
RUN mkdir -p /run/lucid/onion /var/log/lucid \
    && chown -R lucid:lucid /app /run/lucid /var/log/lucid

# Copy application code
COPY --chown=lucid:lucid app/ /app/app/

# Stage 2: Distroless runtime with Python and dependencies
FROM gcr.io/distroless/python3-debian12:latest

# Metadata for professional container management
LABEL maintainer="Lucid Development Team" \
      version="1.0.0-distroless" \
      description="FastAPI server for Lucid sessions gateway (Distroless)" \
      com.lucid.plane="ops" \
      com.lucid.service="api-server" \
      com.lucid.expose="8081"

# Copy Python installation and packages from builder
COPY --from=python-builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=python-builder /usr/local/bin/python3.12 /usr/local/bin/python3.12
COPY --from=python-builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

# Copy system dependencies
COPY --from=python-builder /usr/bin/curl /usr/bin/curl
COPY --from=python-builder /bin/nc /bin/nc
COPY --from=python-builder /usr/bin/jq /usr/bin/jq
COPY --from=python-builder /usr/sbin/gosu /usr/sbin/gosu

# Copy required dynamic libraries (architecture-specific)
COPY --from=python-builder /lib/*-linux-*/libc.so.6 /lib/
COPY --from=python-builder /lib/*-linux-*/libssl.so.3 /lib/
COPY --from=python-builder /lib/*-linux-*/libcrypto.so.3 /lib/
COPY --from=python-builder /lib/*-linux-*/libz.so.1 /lib/
COPY --from=python-builder /lib/*-linux-*/liblzma.so.5 /lib/
COPY --from=python-builder /lib/*-linux-*/libzstd.so.1 /lib/
COPY --from=python-builder /lib*/ld-linux-*.so.2 /lib64/

# Copy user and group information
COPY --from=python-builder /etc/passwd /etc/passwd
COPY --from=python-builder /etc/group /etc/group

# Copy CA certificates
COPY --from=python-builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Copy application and create directories with proper ownership
COPY --from=python-builder --chown=lucid:lucid /app /app
COPY --from=python-builder --chown=lucid:lucid /run/lucid /run/lucid
COPY --from=python-builder --chown=lucid:lucid /var/log/lucid /var/log/lucid

# Runtime environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UVICORN_WORKERS=1 \
    UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8081

# Security and runtime configuration
EXPOSE 8081
USER lucid
WORKDIR /app

# Default command
ENTRYPOINT ["/usr/local/bin/python3.12", "-m", "uvicorn", "app.main:app"]
CMD ["--host", "0.0.0.0", "--port", "8081", "--workers", "1"]