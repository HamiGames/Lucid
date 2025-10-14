# Multi-stage build for distroless container
# File: 03-api-gateway/Dockerfile
# Purpose: Distroless container build for Lucid API Gateway
# Build Host: Windows 11 console
# Target Host: Raspberry Pi (via SSH)

FROM python:3.11-slim as builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG BUILD_DATE
ARG VERSION=1.0.0

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy source code
COPY api/ ./api/
COPY gateway/ ./gateway/
COPY scripts/ ./scripts/

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Production stage - Distroless
FROM gcr.io/distroless/python3-debian12

# Set labels
LABEL maintainer="Lucid Development Team"
LABEL description="Lucid API Gateway - Distroless Container"
LABEL version="1.0.0"
LABEL build_date="${BUILD_DATE}"

# Copy Python packages from builder
COPY --from=builder /root/.local /home/app/.local

# Copy application code
COPY --from=builder /app/api /app/api
COPY --from=builder /app/gateway /app/gateway
COPY --from=builder /app/scripts /app/scripts

# Set working directory
WORKDIR /app

# Set Python path
ENV PYTHONPATH=/app
ENV PATH=/home/app/.local/bin:$PATH

# Create app user (distroless has no useradd, using nonroot user)
USER 65532:65532

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/v1/meta/health')"]

# Expose ports
EXPOSE 8080 8081

# Start application
CMD ["python", "-m", "api.app.main"]

