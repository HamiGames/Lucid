# Multi-stage Dockerfile for Lucid RDP Development Environment
# Target: Raspberry Pi 5 (ARM64) with full development stack
# Based on Spec-1d requirements for Pi 5 + Ubuntu Server simulation

# Stage 1: Base development environment
# Use more reliable base image tag and add retry logic
FROM python:3.12-slim AS base

# Environment setup per LUCID-STRICT requirements
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    DOCKER_DEFAULT_PLATFORM=linux/amd64 \
    LUCID_ENV=dev

# Set workspace per devcontainer spec
WORKDIR /workspaces/Lucid

# Stage 2: System dependencies and tools
FROM base AS system-deps

# Core system packages - split into smaller chunks to prevent hanging
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash curl wget git ca-certificates gnupg lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config cmake \
    && rm -rf /var/lib/apt/lists/*

# Python and network tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-dev python3-pip python3-venv \
    netcat-openbsd socat jq dnsutils \
    && rm -rf /var/lib/apt/lists/*

# Crypto and compression libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsodium-dev libssl-dev zstd libzstd-dev \
    && rm -rf /var/lib/apt/lists/*

# Optional tools (remove heavy packages that might cause issues)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tor torsocks supervisor \
    && rm -rf /var/lib/apt/lists/*

# Stage 3: Node.js 20 LTS (per Spec-1b requirements)
FROM system-deps AS nodejs

# Node.js 20.x install for Admin UI and chain clients
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get update && apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Global Node.js tools for blockchain and API development
RUN npm install -g \
    # API documentation
    @redocly/cli \
    @openapitools/openapi-generator-cli \
    # Blockchain tools
    truffle \
    # TRON integration (per Spec-1b)
    tronweb@6 \
    # Development utilities
    nodemon \
    # Package management
    yarn

# Stage 4: MongoDB tools (per R-MUST-019 - MongoDB 7 only)
FROM nodejs AS mongodb-tools

# MongoDB 7 CLI tools (mongosh) for database interaction
RUN curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb.gpg && \
    echo "deb [arch=arm64,amd64 signed-by=/usr/share/keyrings/mongodb.gpg] https://repo.mongodb.org/apt/debian bookworm/mongodb-org/7.0 main" \
    > /etc/apt/sources.list.d/mongodb-org-7.0.list && \
    apt-get update && apt-get install -y mongodb-mongosh && \
    rm -rf /var/lib/apt/lists/*

# Stage 5: Python development environment
FROM mongodb-tools AS python-dev

# Copy and install Python requirements
COPY .devcontainer/requirements-dev.txt /tmp/requirements-dev.txt
COPY pyproject.toml /tmp/pyproject.toml

# Install Python dependencies with development extras
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements-dev.txt && \
    # Install core cryptography libraries for XChaCha20-Poly1305 and BLAKE3
    pip install pynacl blake3 && \
    # Install TRON development tools
    pip install tronpy && \
    # Cleanup
    rm /tmp/requirements-dev.txt /tmp/pyproject.toml

# Stage 6: Development workspace setup
FROM python-dev AS workspace

# Create project directory structure per Spec-1d monorepo layout
RUN mkdir -p \
    # Core service directories
    /workspaces/Lucid/03-api-gateway/api/app \
    /workspaces/Lucid/04-blockchain-core/api/app \
    /workspaces/Lucid/02-network-security/tor \
    /workspaces/Lucid/02-network-security/tunnels \
    /workspaces/Lucid/06-orchestration-runtime/compose \
    # Development directories
    /workspaces/Lucid/tests \
    /workspaces/Lucid/src \
    /workspaces/Lucid/wallet \
    /workspaces/Lucid/blockchain \
    /workspaces/Lucid/tools \
    # Build and deployment
    /workspaces/Lucid/.devcontainer \
    /workspaces/Lucid/.vscode \
    /workspaces/Lucid/Build_guide_docs \
    # Git hooks
    /workspaces/Lucid/.git/hooks \
    # Runtime directories
    /run/lucid/onion \
    /var/lib/tor \
    /tmp/lucid

# Set proper permissions for Tor and runtime directories
RUN chown -R root:root /run/lucid /var/lib/tor /tmp/lucid && \
    chmod 700 /run/lucid/onion /var/lib/tor

# Stage 7: Tor configuration (per R-MUST-014, R-MUST-020)
FROM workspace AS tor-config

# Create basic Tor configuration for development
RUN echo "# Lucid Development Tor Configuration" > /etc/tor/torrc && \
    echo "SocksPort 9050" >> /etc/tor/torrc && \
    echo "ControlPort 9051" >> /etc/tor/torrc && \
    echo "CookieAuthentication 1" >> /etc/tor/torrc && \
    echo "CookieAuthFileGroupReadable 1" >> /etc/tor/torrc && \
    echo "DataDirectory /var/lib/tor" >> /etc/tor/torrc && \
    echo "Log notice file /var/log/tor/notices.log" >> /etc/tor/torrc && \
    # Create log directory
    mkdir -p /var/log/tor && \
    chown debian-tor:debian-tor /var/log/tor

# Stage 8: Final development environment
FROM tor-config AS final

# Copy project files (will be mounted in devcontainer)
# This ensures the container works standalone if needed
COPY . /workspaces/Lucid/

# Install project in editable mode
RUN cd /workspaces/Lucid && pip install -e .

# Create startup script for services
RUN echo '#!/bin/bash' > /usr/local/bin/start-lucid-dev && \
    echo 'set -e' >> /usr/local/bin/start-lucid-dev && \
    echo 'echo "Starting Lucid Development Environment..."' >> /usr/local/bin/start-lucid-dev && \
    echo 'service tor start' >> /usr/local/bin/start-lucid-dev && \
    echo 'echo "Tor started on ports 9050 (SOCKS) and 9051 (Control)"' >> /usr/local/bin/start-lucid-dev && \
    echo 'cd /workspaces/Lucid' >> /usr/local/bin/start-lucid-dev && \
    echo 'exec "$@"' >> /usr/local/bin/start-lucid-dev && \
    chmod +x /usr/local/bin/start-lucid-dev

# Set working directory and default user
WORKDIR /workspaces/Lucid
USER root

# Health check to ensure container is ready
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f --socks5 127.0.0.1:9050 http://check.torproject.org/ || exit 1

# Default command
CMD ["/usr/local/bin/start-lucid-dev", "bash"]
