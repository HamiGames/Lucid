# LUCID RDP Server Manager - Distroless Container
# LUCID-STRICT Layer 2 Service Integration
# Multi-platform support for Pi 5 ARM64
# Distroless container implementation

# Stage 1: Builder
FROM python:3.11-slim AS builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG TARGETOS
ARG TARGETARCH

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    make \
    pkg-config \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy source code
COPY . .

# Stage 2: Runtime (Distroless)
FROM gcr.io/distroless/python3-debian12

# Set labels
LABEL maintainer="Lucid Development Team"
LABEL version="1.0.0"
LABEL description="Lucid RDP Server Manager - Distroless Container"
LABEL org.opencontainers.image.title="lucid-rdp-server-manager"
LABEL org.opencontainers.image.description="RDP server lifecycle management for Lucid system"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.source="https://github.com/HamiGames/Lucid"

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY --from=builder /build /app

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV SERVICE_NAME=rdp-server-manager
ENV SERVICE_PORT=8081

# Expose port
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8081/health')"]

# Run application
CMD ["python", "main.py"]
