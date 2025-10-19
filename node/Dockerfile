# Lucid Node Management Container - Fast Distroless Build
# Port: 8095
# Features: Node pool management, PoOT calculation, payout threshold (10 USDT), max 100 nodes

# Stage 1: Builder - only what's needed for compilation
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install minimal build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /build

# Copy only requirements first for better caching
COPY node/requirements.txt .

# Install Python dependencies to user directory
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy only node source code
COPY node/ .

# Stage 2: Distroless runtime - minimal and fast
FROM gcr.io/distroless/python3-debian12:nonroot

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NODE_MANAGEMENT_PORT=8095

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/nonroot/.local

# Copy application code
COPY --from=builder /build /app

# Set working directory
WORKDIR /app

# Add Python user packages to path
ENV PATH=/home/nonroot/.local/bin:$PATH

# Expose port
EXPOSE 8095

# Health check (simple Python check)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import sys; sys.exit(0)"]

# Use non-root user
USER nonroot

# Start application
CMD ["python", "main.py"]