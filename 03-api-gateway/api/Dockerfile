# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Minimal OS deps + tini for proper signal handling
RUN apt-get update && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -u 10001 -m appuser
WORKDIR /app

# Install Python deps first to leverage layer cache
# If a requirements.txt is present in this folder, it will be used.
# Otherwise we install the minimal runtime set to avoid FastAPI import errors.
COPY requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    else \
        pip install "fastapi==0.111.*" "uvicorn[standard]==0.30.*" "motor==3.*" "pydantic==2.*" "python-dotenv==1.*"; \
    fi

# Copy app source
COPY . /app

# Ensure package imports resolve (e.g., routes/health.py)
ENV PYTHONPATH=/app

# Expose API port
EXPOSE 8081

# Drop privileges
USER appuser

# Use tini as PID 1
ENTRYPOINT ["/usr/bin/tini","--"]

# Run FastAPI
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8081"]
