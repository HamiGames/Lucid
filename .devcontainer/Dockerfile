# Base Python + Bash + SSL support on Debian Bookworm
RUN docker pull debian:bookworm-slim 
FROM debian:bookworm-slim


# Environment setup

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8


# Set workspace

WORKDIR /workspaces/Lucid


# System dependencies

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash curl git ca-certificates gnupg \
    build-essential pkg-config \
    python3-dev python3-pip python3-venv \
    openjdk-17-jdk \
    netcat-openbsd socat jq \
    && rm -rf /var/lib/apt/lists/*


# Node.js 20.x install

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get update && apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*


# MongoDB CLI: `mongosh` (v7 compatible)

RUN curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb.gpg && \
    echo "deb [arch=arm64,amd64 signed-by=/usr/share/keyrings/mongodb.gpg] https://repo.mongodb.org/apt/debian bookworm/mongodb-org/7.0 main" \
    > /etc/apt/sources.list.d/mongodb-org-7.0.list && \
    apt-get update && apt-get install -y mongodb-mongosh && \
    rm -rf /var/lib/apt/lists/*


# Global JS/CLI tools

RUN npm install -g \
    @redocly/cli \
    @openapitools/openapi-generator-cli \
    truffle \
    tronweb


# Python requirements

COPY .devcontainer/requirements-dev.txt /tmp/requirements-dev.txt
RUN pip install --upgrade pip && \
    pip install -r /tmp/requirements-dev.txt && \
    rm /tmp/requirements-dev.txt


# Create necessary directories for project structure

RUN mkdir -p /workspaces/Lucid/02-network-security/tor \
    /workspaces/Lucid/02-network-security/tunnels \
    /workspaces/Lucid/03-api-gateway/api \
    /workspaces/Lucid/04-blockchain-core/api \
    /workspaces/Lucid/06-orchestration-runtime/compose \
    /workspaces/Lucid/08-quality/scripts


# Set up pre-commit hooks directory

RUN mkdir -p /workspaces/Lucid/.git/hooks


# Local package in editable mode (commented out until we have the actual package)

COPY . /workspaces/Lucid

RUN pip install -e /workspaces/Lucid