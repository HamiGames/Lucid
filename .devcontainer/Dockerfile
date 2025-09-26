# Use a lightweight Debian-based Python image with full bash support
FROM python:3.12-slim-bookworm

# Setup environment
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Create workspace directory
WORKDIR /workspaces/Lucid

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash curl git ca-certificates gnupg \
    build-essential pkg-config \
    python3-dev python3-pip python3-venv \
    openjdk-17-jdk \
    netcat-openbsd socat jq \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Node.js 20.x install
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get update && apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# MongoDB CLI install (mongosh)
RUN curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb.gpg && \
    echo "deb [arch=arm64,amd64 signed-by=/usr/share/keyrings/mongodb.gpg] https://repo.mongodb.org/apt/debian bookworm/mongodb-org/7.0 main" \
    > /etc/apt/sources.list.d/mongodb-org-7.0.list && \
    apt-get update && apt-get install -y mongodb-mongosh && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install global Node.js tools
RUN npm install -g \
    @redocly/cli \
    @openapitools/openapi-generator-cli \
    truffle \
    tronweb

# Copy and install Python requirements (optional: use `COPY` or mount)
COPY .devcontainer/requirements-dev.txt /tmp/requirements-dev.txt
RUN pip install --upgrade pip && \
    pip install -r /tmp/requirements-dev.txt && \
    rm /tmp/requirements-dev.txt
