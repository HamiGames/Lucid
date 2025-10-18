# Multi-stage build for api
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt* ./
RUN pip install --no-cache-dir --user -r requirements.txt 2>/dev/null || echo "No requirements.txt found"

# Copy source code
COPY . .

# Install the package
RUN pip install --no-cache-dir --user -e . 2>/dev/null || echo "No setup.py found"

# Runtime stage - distroless
FROM gcr.io/distroless/python3-debian11

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY --from=builder /app /app

# Set working directory
WORKDIR /app

# Add user for security
USER 1000

# Expose port
EXPOSE 8080

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python3", "-c", "import requests; requests.get('http://localhost:8080/health', timeout=5)"]

# Run the application
CMD ["python3", "-m", "api"]
