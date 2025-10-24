# Multi-stage Dockerfile for Chunk Processor Service
# Uses distroless base image for security and minimal attack surface

# Stage 1: Builder
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /build

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy source code
COPY . .

# Stage 2: Runtime (distroless)
FROM gcr.io/distroless/python3-debian12

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY --from=builder /build /app

# Set working directory
WORKDIR /app

# Set Python path
ENV PYTHONPATH=/app:/root/.local/lib/python3.11/site-packages
ENV PATH=/root/.local/bin:$PATH

# Create non-root user (distroless standard)
USER 65532:65532

# Expose port
EXPOSE 8085

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8085/health')"]

# Set environment variables
ENV SERVICE_NAME=chunk-processor
ENV PORT=8085
ENV PYTHONUNBUFFERED=1

# Run the application
ENTRYPOINT ["python", "-m", "sessions.processor.main"]
