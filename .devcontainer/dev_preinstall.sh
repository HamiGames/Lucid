#!/usr/bin/env bash
# Lucid RDP — Devcontainer Preinstall Script
# Purpose: provision full groundwork for Python, Node.js, OpenAPI, Tron-node, and MongoDB tooling.
# Runs as root during devcontainer build (via initializeCommand).

set -euo pipefail
log() { echo "[dev_preinstall] $*"; }

log "Ensuring apt lists directory exists..."
mkdir -p /var/lib/apt/lists/partial
chmod 755 /var/lib/apt/lists /var/lib/apt/lists/partial

log "Updating apt package index..."
apt-get update -y

log "Installing essential system dependencies..."
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    build-essential \
    pkg-config \
    python3-dev \
    python3-venv \
    python3-pip \
    openjdk-17-jdk \
    netcat-openbsd \
    socat \
    jq \
    gnupg

log "Installing Node.js (Node 20.x)..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends nodejs

log "Installing MongoDB client (mongosh)..."
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb.gpg
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb.gpg ] https://repo.mongodb.org/apt/debian bookworm/mongodb-org/7.0 main" \
  > /etc/apt/sources.list.d/mongodb-org-7.0.list
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends mongodb-mongosh

log "Installing global Node.js tooling for OpenAPI, Tron, etc..."
npm install -g \
    @redocly/cli \
    @openapitools/openapi-generator-cli \
    truffle \
    tronweb

log "Cleaning up apt cache..."
rm -rf /var/lib/apt/lists/*

log "Devcontainer base preinstall complete."
