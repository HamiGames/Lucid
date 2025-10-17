# Multi-stage build for Lucid Pipeline Manager Service
# Uses distroless base image for security and minimal size (Step 15 requirement)

# Stage 1: Builder
FROM python:3.11-slim AS builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG PYTHON_VERSION=3.11

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements first for better layer caching
COPY requirements.txt .
COPY sessions/pipeline/requirements.txt ./pipeline/

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt
RUN pip install --no-cache-dir --user -r pipeline/requirements.txt

# Copy source code
COPY sessions/ ./sessions/
COPY . .

# Create non-root user for security
RUN groupadd -r lucid && useradd -r -g lucid lucid

# Set proper permissions
RUN chown -R lucid:lucid /build

# Stage 2: Runtime (Distroless)
FROM gcr.io/distroless/python3-debian12

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY --from=builder /build/sessions /app/sessions
COPY --from=builder /build /app

# Set working directory
WORKDIR /app

# Create necessary directories
USER root
RUN mkdir -p /storage/chunks /storage/sessions /tmp/sessions && \
    chown -R 1000:1000 /storage /tmp/sessions
USER 1000

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV SERVICE_NAME=lucid-pipeline-manager
ENV PORT=8083
ENV HOST=0.0.0.0
ENV LOG_LEVEL=INFO
ENV DEBUG=false

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8083/health')"]

# Expose port
EXPOSE 8083

# Set entrypoint
ENTRYPOINT ["python", "-m", "sessions.pipeline.main"]
