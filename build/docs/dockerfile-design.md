## Lucid Dockerfile Design Pattern (Python Distroless Services)

This document defines the **canonical Dockerfile pattern** for Lucid Python services that use **distroless** runtime images. It is derived from the working `Dockerfile.engine` and aligned with `Dockerfile.data`.

The goals:
- **Distroless runtime** (minimal attack surface)
- **Multi-stage builds** (builder + distroless runtime)
- **Deterministic COPY behaviour** (no silent failures, aligned with `Dockerfile-copy-pattern.md`)
- **ARM64‑first** (Raspberry Pi compatible)

---

## 1. High‑Level Structure

Every Python service Dockerfile should follow this structure:

1. **Arguments & metadata**
2. **Stage 1 – Builder** (standard Python base, full toolchain)
3. **Stage 2 – Runtime** (distroless `gcr.io/distroless/python3-debian12`)

```dockerfile
# syntax=docker/dockerfile:1.5

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
...

############################
# Stage 2 – Runtime
############################
FROM --platform=$TARGETPLATFORM gcr.io/distroless/python3-debian12:latest
...
```

---

## 2. Builder Stage Pattern

### 2.1 Base Image & ENV

```dockerfile
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
```

### 2.2 System Packages

Use a single `apt-get` block with Docker cache mounts; clean afterwards:

```dockerfile
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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
```

### 2.3 Working Directory & System Markers

```dockerfile
WORKDIR /build

# Ensures /var/run and /var/lib exist with real content (COPY won’t be silent)
RUN echo "LUCID_<SERVICE>_RUNTIME_DIRECTORY" > /var/run/.keep && \
    echo "LUCID_<SERVICE>_LIB_DIRECTORY" > /var/lib/.keep && \
    chown -R 65532:65532 /var/run /var/lib
```

### 2.4 Python Dependencies

```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel

COPY <service>/requirements.txt ./requirements.txt

RUN mkdir -p /root/.local/lib/python3.11/site-packages && \
    mkdir -p /root/.local/bin

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --no-cache-dir --prefer-binary -r requirements.txt
```

#### Marker Files (per `Dockerfile-copy-pattern.md`)

```dockerfile
RUN echo "LUCID_<SERVICE>_PACKAGES_INSTALLED_$(date +%s)" > /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    echo "LUCID_<SERVICE>_BINARIES_INSTALLED_$(date +%s)" > /root/.local/bin/.lucid-marker && \
    chown -R 65532:65532 /root/.local
```

These **contentful** marker files ensure the directory structure is “locked in” so later `COPY` into distroless does not fail silently.

### 2.5 Builder‑Stage Verification

Import the **critical packages** used by the service and sanity‑check the directory:

```dockerfile
RUN python3 -c "import fastapi, uvicorn, pydantic; print('✅ critical packages installed')" && \
    python3 -c "import uvicorn; print('uvicorn location:', uvicorn.__file__)" && \
    test -d /root/.local/lib/python3.11/site-packages
```

Adjust the import list per service (`sqlalchemy`, `motor`, `pymongo`, `blake3`, etc.).

### 2.6 Application Source COPY

Always copy the **monorepo root** into a temporary `blockchain-src` (or equivalent), then selectively copy **only the directories needed** by this container:

```dockerfile
COPY blockchain/ ./blockchain-src/

# Example: engine service copies many dirs
RUN cp -r ./blockchain-src/api ./api && \
    cp -r ./blockchain-src/core ./core && \
    cp -r ./blockchain-src/utils ./utils && \
    cp -r ./blockchain-src/config ./config && \
    cp -r ./blockchain-src/contracts ./contracts && \
    cp -r ./blockchain-src/deployment ./deployment && \
    cp -r ./blockchain-src/chain-client ./chain-client && \
    cp -r ./blockchain-src/evm ./evm && \
    cp -r ./blockchain-src/on_system_chain ./on_system_chain && \
    cp ./blockchain-src/*.py ./ && \
    rm -rf ./blockchain-src
```

For smaller services (like data‑chain), copy **only** the required sub‑trees (e.g. `data`, `core`, `config`).

---

## 3. Runtime Stage Pattern (Distroless)

### 3.1 Base Image, Labels, and ENV

```dockerfile
FROM --platform=$TARGETPLATFORM gcr.io/distroless/python3-debian12:latest

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL maintainer="Lucid Development Team" \
      org.opencontainers.image.title="Lucid <Service>" \
      org.opencontainers.image.description="Distroless <service> for Lucid project" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      com.lucid.service="<service-id>" \
      com.lucid.platform="arm64" \
      com.lucid.cluster="core" \
      com.lucid.security="distroless"

ENV PATH=/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/usr/local/lib/python3.11/site-packages \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    <SERVICE_PORT_ENV>=<PORT> \
    <SERVICE_HOST_ENV>=0.0.0.0

WORKDIR /app
```

### 3.2 System Directories & Certificates

```dockerfile
COPY --from=builder --chown=65532:65532 /var/run /var/run
COPY --from=builder --chown=65532:65532 /var/lib /var/lib

# Distroless base already has correct linker/runtime; only copy CA certs
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
```

### 3.3 Python Packages (Per COPY Pattern Guide)

```dockerfile
COPY --from=builder --chown=65532:65532 /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder --chown=65532:65532 /root/.local/bin /usr/local/bin
```

#### Runtime Verification of Packages

Mirror the `Dockerfile.engine` pattern: verify that site‑packages exists, required packages are present, and the `.lucid-marker` is non‑empty.

```dockerfile
RUN ["python3", "-c", "import sys; import os; \
site_packages = '/usr/local/lib/python3.11/site-packages'; \
assert os.path.exists(site_packages), site_packages + ' does not exist'; \
assert os.path.exists(os.path.join(site_packages, 'uvicorn')), 'uvicorn not found'; \
assert os.path.exists(os.path.join(site_packages, 'fastapi')), 'fastapi not found'; \
assert os.path.exists(os.path.join(site_packages, '.lucid-marker')), 'marker file not found'; \
marker_path = os.path.join(site_packages, '.lucid-marker'); \
assert os.path.getsize(marker_path) > 0, 'marker file is empty: ' + marker_path; \
print('Packages verified in runtime stage')"]
```

Extend the assertions per service (`motor`, `pymongo`, `blake3`, `web3`, etc.).

### 3.4 Application Layout COPY

Follow the same **selective directory COPY** pattern as builder, but from `/build` to `/app`:

```dockerfile
COPY --chown=65532:65532 --from=builder /build/api           /app/api
COPY --chown=65532:65532 --from=builder /build/core          /app/core
COPY --chown=65532:65532 --from=builder /build/utils         /app/utils
COPY --chown=65532:65532 --from=builder /build/config        /app/config
COPY --chown=65532:65532 --from=builder /build/contracts     /app/contracts
...
COPY --chown=65532:65532 --from=builder /build/*.py          /app/
```

For data‑chain and similar containers, limit to just the necessary sub‑trees (for example, `/app/blockchain/data`, `/app/blockchain/core`, `/app/blockchain/config`).

### 3.5 Ports, Healthcheck, and Entrypoint

```dockerfile
EXPOSE <PORT>

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD ["python3", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', <PORT>)); s.close(); exit(0 if result == 0 else 1)"]

USER 65532:65532

# Clear base ENTRYPOINT so CMD works as expected
ENTRYPOINT []

CMD ["python3", "/app/<service-root>/api/entrypoint.py"]
```

The entrypoint path should always be **service‑specific** (e.g. blockchain engine vs data‑chain) and must not point to another service’s API.

---

## 4. Design Rules for Future Dockerfiles

When creating a new `Dockerfile.*` for a Python service:

- **Always** use:
  - `python:3.11-slim-bookworm` for the builder
  - `gcr.io/distroless/python3-debian12:latest` for the runtime
- **Always**:
  - Install Python packages under `/root/.local` in the builder
  - Create **contentful marker files** after `pip install`
  - Copy `/root/.local/lib/python3.11/site-packages` → `/usr/local/lib/python3.11/site-packages`
  - Verify packages in **both** builder and runtime stages
  - Use `COPY --chown=65532:65532` for all application and package directories
  - Run as `USER 65532:65532`
  - Clear `ENTRYPOINT` and use a JSON‑form `CMD ["python3", "..."]`
- **Never**:
  - Use shells (`/bin/sh`, `bash`) in the runtime stage
  - Copy system linkers/runtimes from builder into distroless base
  - Rely on empty `touch`/`> file` placeholders for directory creation

This pattern is the **reference design** for all future Python distroless containers (e.g. blockchain‑engine, data‑chain, manager services). Start from this document, then specialize the **requirements list**, **subdirectories**, and **entrypoint** for each container.


