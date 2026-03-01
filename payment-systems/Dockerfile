# TRON Client - Distroless (ARM64)
# Image: pickme/lucid-tron-client:latest-arm64
# Ports per essentials.md: 8091, 8101

FROM --platform=linux/arm64 python:3.12-slim-bookworm AS builder
RUN apt-get update && apt-get install -y build-essential gcc g++ libffi-dev libssl-dev libxml2-dev libxslt1-dev zlib1g-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN python -m venv /opt/venv
COPY payment-systems/tron/requirements.txt ./requirements.txt
COPY payment-systems/tron/requirements-prod.txt ./requirements-prod.txt
RUN /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt -r requirements-prod.txt
COPY payment-systems/tron/services/tron_client.py ./services/tron_client.py
COPY payment-systems/tron/services/__init__.py ./services/__init__.py
COPY payment-systems/tron/config.py ./config.py
COPY payment-systems/tron/main.py ./main.py

FROM --platform=linux/arm64 gcr.io/distroless/python3-debian12:nonroot
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app \
    SERVICE_NAME=tron-client SERVICE_PORT=8091 \
    LUCID_ENV=production LUCID_PLATFORM=arm64 PROJECT_ROOT=/mnt/myssd/Lucid/Lucid
WORKDIR /app
COPY --from=builder --chown=nonroot:nonroot /opt/venv /opt/venv
COPY --from=builder --chown=nonroot:nonroot /app /app
ENV PATH="/opt/venv/bin:$PATH"

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["/opt/venv/bin/python3","-c","import urllib.request; urllib.request.urlopen('http://localhost:8091/health').read()"]

EXPOSE 8091 8101
CMD ["/opt/venv/bin/python3","-m","uvicorn","main:app","--host","0.0.0.0","--port","8091","--workers","1"]
