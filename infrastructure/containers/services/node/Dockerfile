# syntax=docker/dockerfile:1.5
# LUCID NODE SERVICES — baked config tree (builder pattern aligned with infrastructure/containers/tor/Dockerfile.tor-proxy-02)
# Purpose: ship container-runtime-layout.yml, host-config.yml, this compose fragment, and node-management-config.yaml
#   under /app/configs/services/ for parity with tor-proxy Stage-1 → /app/configs/services in runtime images.
# Image (optional): pickme/lucid-node-services-config:latest-arm64
# Build context: repository root (.)
#
# From repository root (Lucid):
#   docker build -f infrastructure/containers/services/node/Dockerfile --platform linux/arm64 -t pickme/lucid-node-services-config:latest-arm64 .

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64

# =============================================================================
# Stage 1 — Debian scaffold (matches tor-proxy-02 tor-builder config COPY block)
# =============================================================================
FROM debian:12-slim AS node-services-builder

ARG BUILDPLATFORM
ARG TARGETPLATFORM

ENV DEBIAN_FRONTEND=noninteractive

RUN mkdir -p /build/configs

COPY configs/environment/.env.secrets /build/configs/.env.secrets
COPY master-env-config.txt /build/configs/.env.master

RUN mkdir -p /build/configs/services/node

COPY infrastructure/containers/services/container-runtime-layout.yml /build/configs/services/container-runtime-layout.yml
COPY infrastructure/containers/host-config.yml /build/configs/services/host-config.yml
COPY infrastructure/containers/services/node/docker-compose.node-management.yml /build/configs/services/node/docker-compose.node-management.yml
COPY infrastructure/containers/services/node/node-management-config.yaml /build/configs/services/node/node-management-config.yaml

# =============================================================================
# Stage 2 — Distroless static payload (data-only; no shell — same role as baking /app/configs/services on tor runtime)
# =============================================================================
FROM gcr.io/distroless/static-debian12:latest

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL maintainer="Lucid Development Team" \
      version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.title="Lucid Node Services Config Bundle" \
      org.opencontainers.image.description="Baked layouts for infrastructure/containers/services/node (host-config + node-management)" \
      com.lucid.service="node-services-config" \
      com.lucid.platform="arm64" \
      com.lucid.cluster="application" \
      com.lucid.security="distroless" \
      com.lucid.host_config.service.primary="node-management" \
      com.lucid.host_config.service.staging="node-management-staging"

# Discovery alignment: infrastructure/containers/host-config.yml (node_management), service-ip.txt.
ENV LUCID_HOST_CONFIG_PATH=/app/configs/services/host-config.yml \
    LUCID_HOST_CONFIG_SERVICE_KEY=node_management \
    LUCID_SERVICE_HOST_IP=172.20.10.25 \
    LUCID_SERVICE_HTTP_PATH=http://node-management:8095/app

COPY --from=node-services-builder --chown=65532:65532 /build/configs/.env.secrets /app/configs/.env.secrets
COPY --from=node-services-builder --chown=65532:65532 /build/configs/.env.master /app/configs/.env.master
COPY --from=node-services-builder --chown=65532:65532 /build/configs/services /app/configs/services

USER 65532:65532
