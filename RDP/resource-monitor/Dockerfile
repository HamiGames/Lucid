# Multi-stage build for RDP Resource Monitor
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime (Distroless)
FROM gcr.io/distroless/python3-debian12:nonroot

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/nonroot/.local

# Copy application code
COPY --chown=nonroot:nonroot . .

# Set environment variables
ENV PYTHONPATH=/app:/home/nonroot/.local/lib/python3.11/site-packages
ENV PATH=/home/nonroot/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Expose service port
EXPOSE 8090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8090/health')"]

# Run the application
ENTRYPOINT ["python", "-m", "resource_monitor.main"]
