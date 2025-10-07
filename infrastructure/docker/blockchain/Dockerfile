# LUCID BLOCKCHAIN API - Distroless
# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS blockchain-builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps (certs, build tools minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl build-essential gosu netcat-traditional jq \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 lucid \
    && useradd --uid 1000 --gid lucid --shell /bin/bash --create-home lucid

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY --chown=lucid:lucid blockchain/ /app/blockchain/

# Stage 2: Distroless runtime
FROM gcr.io/distroless/python3-debian12:latest

# Copy Python installation and packages from builder
COPY --from=blockchain-builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=blockchain-builder /usr/local/bin/python3.12 /usr/local/bin/python3.12
COPY --from=blockchain-builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

# Copy system dependencies
COPY --from=blockchain-builder /usr/bin/curl /usr/bin/curl
COPY --from=blockchain-builder /bin/nc /bin/nc
COPY --from=blockchain-builder /usr/bin/jq /usr/bin/jq
COPY --from=blockchain-builder /usr/sbin/gosu /usr/sbin/gosu

# Copy required dynamic libraries
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

# Copy CA certificates
COPY --from=blockchain-builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Copy application
COPY --from=blockchain-builder --chown=lucid:lucid /app /app

# Default envs (override at runtime)
ENV API_HOST=0.0.0.0 \
    API_PORT=8084 \
    PYTHONPATH=/app

EXPOSE 8084
USER lucid
WORKDIR /app
ENTRYPOINT ["/usr/local/bin/python3.12", "-m", "uvicorn", "app.main:app"]
CMD ["--host", "0.0.0.0", "--port", "8084"]
