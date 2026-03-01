# Multi-stage build for distroless recorder
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    libopencv-dev \
    python3-opencv \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libgtk-3-dev \
    libcanberra-gtk3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy source code
COPY . .

# Production stage - distroless
FROM gcr.io/distroless/python3-debian12

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY --chown=nonroot:nonroot . /app

# Set environment variables
ENV PYTHONPATH=/root/.local/lib/python3.11/site-packages:/app
ENV PATH=/root/.local/bin:$PATH

# Set user and working directory
USER nonroot
WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import sys; sys.exit(0)"]

# Start the application
CMD ["python", "recorder.py"]
