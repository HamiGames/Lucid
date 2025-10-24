# LUCID Session Storage Service - Distroless Container
# Step 17 Implementation: Session Storage & API

# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILDKIT_INLINE_CACHE=1
ARG BUILDKIT_PROGRESS=plain

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libzstd-dev \
    liblz4-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy source code
COPY . .

# Install the package
RUN pip install --no-cache-dir --user .

# Runtime stage - Distroless Python
FROM gcr.io/distroless/python3-debian12

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY --from=builder /build/sessions/storage /app/sessions/storage
COPY --from=builder /build/sessions/__init__.py /app/sessions/__init__.py
COPY --from=builder /build/sessions/core /app/sessions/core
COPY --from=builder /build/sessions/recorder /app/sessions/recorder

# Set environment variables
ENV PYTHONPATH=/app
ENV LUCID_STORAGE_HOST=0.0.0.0
ENV LUCID_STORAGE_PORT=8081
ENV LUCID_STORAGE_PATH=/data/sessions
ENV LUCID_CHUNK_STORE_PATH=/data/chunks
ENV LUCID_COMPRESSION_ALGORITHM=zstd
ENV LUCID_COMPRESSION_LEVEL=6
ENV LUCID_CHUNK_SIZE_MB=10
ENV LUCID_RETENTION_DAYS=30
ENV LUCID_MAX_SESSIONS=1000
ENV LUCID_CLEANUP_INTERVAL_HOURS=24
ENV LUCID_BACKUP_ENABLED=true
ENV LUCID_BACKUP_RETENTION_DAYS=7
ENV MONGO_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid
ENV REDIS_URL=redis://lucid_redis:6379/0

# Create data directories
USER root
RUN mkdir -p /data/sessions /data/chunks /data/temp /data/backup
RUN chown -R 65532:65532 /data
USER 65532

# Set working directory
WORKDIR /app

# Expose port
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD ["/usr/bin/python3", "-c", "import requests; requests.get('http://localhost:8081/health')"]

# Run the application
CMD ["/usr/bin/python3", "-m", "sessions.storage.main"]
