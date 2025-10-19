# LUCID XRDP Service - Distroless Container
# LUCID-STRICT Layer 2 Service Integration
# Multi-platform support for Pi 5 ARM64
# Distroless container implementation

# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG TARGETOS
ARG TARGETARCH

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage - Distroless Python
FROM gcr.io/distroless/python3-debian12

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV SERVICE_NAME=xrdp-service
ENV SERVICE_PORT=3389

# Set working directory
WORKDIR /app

# Copy Python application
COPY --from=builder /root/.local /root/.local
COPY . .

# Expose port
EXPOSE 3389

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:3389/health')"]

# Run application
CMD ["python", "main.py"]
