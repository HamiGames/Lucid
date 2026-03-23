# syntax=docker/dockerfile:1.5
# LUCID SERVER CORE — Distroless Python (shared server-tier foundation)
# Aligned with 03_api_gateway/Dockerfile (builder wheels, /app runtime layout, tini)
# Image: pickme/lucid-server-core:latest-arm64
# Build context: repository root (.)
#
# This container hosts the server core structure: RDP server modules, protocol, shared
# common code, and RDP config — the HTTP surface is server.xrdp_integration (FastAPI).
#
# Control plane (separate images; they orchestrate or specialize this tier):
#   • infrastructure/containers/server/Dockerfile.server-manager
#       → Lucid Server Operations (full handler bundles + server_manager/entrypoint.py)
#   • infrastructure/containers/rdp/Dockerfile.rdp-server-manager
#       → RDP-focused manager slice (flat app layout, uvicorn xrdp_integration:app, port 8090)
#
# Admin UI backend (infrastructure/containers/admin/Dockerfile.admin-ui-backend) should
# reach this tier via compose DNS, e.g. LUCID_SERVER_CORE_URL=http://lucid-server-core:8088
# alongside API_GATEWAY_URL and other Lucid services.

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64
ARG PYTHON_VERSION=3.11

############################
# Stage 1 – Builder
############################
FROM --platform=$TARGETPLATFORM python:3.11-slim-bookworm AS builder

ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG PYTHON_VERSION

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PREFER_BINARY=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /build

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    rm -rf /var/lib/apt/lists/* && \
    apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        libffi-dev \
        libssl-dev \
        pkg-config \
        curl \
        ca-certificates \
        tini \
        python3-wheel \
        python3-dev \
        python3-pip \
        python3-setuptools \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN mkdir -p /usr/local/lib/python3.11/site-packages /usr/local/bin && \
    printf "LUCID_SERVER_CORE_RUNTIME" > /var/run/.keep && \
    printf "LUCID_SERVER_CORE_LIB" > /var/lib/.keep && \
    chown -R 65532:65532 /var/run /var/lib && \
    chmod 644 /var/run/.keep /var/lib/.keep

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel

COPY RDP/requirements.txt ./requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    mkdir -p /build/wheels && \
    printf "LUCID_SERVER_CORE_WHEELS_$(date +%s)" > /build/wheels/.keep && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r ./requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --no-index --find-links /build/wheels -r ./requirements.txt

RUN printf "LUCID_SERVER_CORE_PACKAGES_$(date +%s)" > /usr/local/lib/python3.11/site-packages/.lucid-marker && \
    chown 65532:65532 /usr/local/lib/python3.11/site-packages/.lucid-marker

RUN python3.11 -c "import fastapi, uvicorn, pydantic, motor, pymongo, redis, cryptography, aiofiles, httpx, aiohttp, structlog, prometheus_client, psutil; print('server core packages OK')"

COPY RDP/server/ ./server/
COPY RDP/protocol/ ./protocol/
COPY RDP/common/ ./common/
COPY RDP/config/ ./config/
COPY RDP/__init__.py ./__init__.py

RUN printf "LUCID_SERVER_CORE_SRC_$(date +%s)" > ./server/.lucid-source-marker && \
    printf "LUCID_SERVER_CORE_PROTOCOL_$(date +%s)" > ./protocol/.lucid-source-marker && \
    chown -R 65532:65532 ./server ./protocol ./common ./config ./__init__.py

RUN test -f ./server/xrdp_integration.py && \
    test -f ./server/.lucid-source-marker && \
    test -s ./server/.lucid-source-marker && \
    echo "server core source verified"

############################
# Stage 2 – Runtime (Distroless)
############################
FROM --platform=$TARGETPLATFORM gcr.io/distroless/python3-debian12:latest

WORKDIR /app

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL maintainer="Lucid Development Team" \
      org.opencontainers.image.title="Lucid Server Core" \
      org.opencontainers.image.description="Distroless server-tier foundation (RDP server, protocol, common, config); orchestrated by server-operations and RDP manager images" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      com.lucid.service="lucid-server-core" \
      com.lucid.role="server-core-foundation" \
      com.lucid.platform="arm64" \
      com.lucid.cluster="core" \
      com.lucid.security="distroless"

ENV PATH=/app/usr/local/bin:/app/usr/bin:/app/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/app/usr/local/lib/python3.11/site-packages \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    LUCID_SERVER_CORE_PORT=8100 \
    LUCID_SERVER_CORE_DNS=lucid-server-core

COPY --from=builder /var/run/ /app/var/run/
COPY --from=builder /var/lib/ /app/var/lib/
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /app/etc/ssl/certs/ca-certificates.crt
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /app/usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /app/usr/local/bin/
COPY --from=builder /usr/bin/ /app/usr/bin/
COPY --from=builder /usr/sbin/ /app/usr/sbin/

COPY --from=builder --chown=65532:65532 /build/wheels/ /app/wheels/
COPY --from=builder --chown=65532:65532 /build/server/ /app/server/
COPY --from=builder --chown=65532:65532 /build/protocol/ /app/protocol/
COPY --from=builder --chown=65532:65532 /build/common/ /app/common/
COPY --from=builder --chown=65532:65532 /build/config/ /app/config/
COPY --from=builder --chown=65532:65532 /build/__init__.py /app/__init__.py

RUN ["/app/usr/bin/python3.11", "-c", "import os,sys; sp='/app/usr/local/lib/python3.11/site-packages'; sys.path.insert(0,sp); assert os.path.isdir(sp); m=os.path.join(sp,'.lucid-marker'); assert os.path.isfile(m) and os.path.getsize(m)>0; import uvicorn,fastapi,cryptography,aiofiles,psutil; print('runtime site-packages OK')"]

RUN ["/app/usr/bin/python3.11", "-c", "import os; assert os.path.isfile('/app/server/xrdp_integration.py'); assert os.path.isfile('/app/server/.lucid-source-marker'); print('server core app tree OK')"]

EXPOSE 8100

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 CMD ["/app/usr/bin/python3.11", "-c", "import os,urllib.request,sys; p=os.environ.get('LUCID_SERVER_CORE_PORT',os.environ.get('LUCID_CORE_SERVER_PORT','8088')); urllib.request.urlopen('http://127.0.0.1:'+str(p)+'/health', timeout=10).read(); sys.exit(0)"]

USER 65532:65532

ENTRYPOINT ["/app/usr/bin/tini", "--"]

CMD ["/app/usr/bin/python3.11", "-m", "uvicorn", "server.xrdp_integration:app", "--host", "0.0.0.0", "--port", "8100"]
