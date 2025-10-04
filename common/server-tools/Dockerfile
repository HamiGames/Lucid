# LUCID SERVER TOOLS - SPEC-4 Stage 0 Utilities
# Professional utility container for Pi deployment
# Compatible with devcontainer builds and ARM64 Pi architecture

FROM alpine:3.22.1

# Metadata for professional container management
LABEL maintainer="Lucid Development Team" \
      version="1.0.0" \
      description="Server utilities for Lucid core support" \
      com.lucid.plane="ops" \
      com.lucid.service="server-tools" \
      com.lucid.expose="none"

# Install comprehensive server utilities optimized for Pi
RUN apk update && apk upgrade --no-cache \
    && apk add --no-cache \
       # Core utilities
       bash \
       curl \
       wget \
       jq \
       yq \
       # Network tools
       bind-tools \
       netcat-openbsd \
       socat \
       nmap-ncat \
       tcpdump \
       iperf3 \
       # Security tools
       openssl \
       ca-certificates \
       gnupg \
       # System tools
       htop \
       ps \
       lsof \
       strace \
       # File tools
       rsync \
       unzip \
       tar \
       gzip \
       # Database tools
       mongodb-tools \
       # Development tools
       git \
       vim \
       nano \
       tree \
       # Monitoring tools
       procps \
       util-linux \
    && rm -rf /var/cache/apk/* \
    && adduser -D -s /bin/bash lucid

# Create utility directories
RUN mkdir -p /opt/lucid/tools /opt/lucid/scripts /var/log/lucid \
    && chown -R lucid:lucid /opt/lucid /var/log/lucid

# Install MongoDB shell (mongosh) for database operations
RUN curl -fsSL https://downloads.mongodb.com/compass/mongosh-1.10.6-linux-x64.tgz \
    | tar -xzC /tmp \
    && mv /tmp/mongosh-*/bin/* /usr/local/bin/ \
    && rm -rf /tmp/mongosh-*

# Create utility scripts for core support operations
RUN cat > /opt/lucid/scripts/health-check.sh <<'EOF' && chmod +x /opt/lucid/scripts/health-check.sh
#!/bin/bash
# Comprehensive health check for core support services
set -euo pipefail

echo "[health-check] Lucid Core Support Health Check"
echo "============================================"

# Check Tor proxy
if curl -fsS --max-time 5 --socks5 tor-proxy:9050 http://check.torproject.org >/dev/null 2>&1; then
    echo "✅ Tor proxy: HEALTHY"
else
    echo "❌ Tor proxy: UNHEALTHY"
fi

# Check MongoDB
if mongosh --quiet --eval "db.runCommand({ ping: 1 })" "$MONGO_URL" >/dev/null 2>&1; then
    echo "✅ MongoDB: HEALTHY"
else
    echo "❌ MongoDB: UNHEALTHY"
fi

# Check API Gateway
if curl -fsS --max-time 5 http://lucid_api_gateway:8080/health >/dev/null 2>&1; then
    echo "✅ API Gateway: HEALTHY"
else
    echo "❌ API Gateway: UNHEALTHY"
fi

# Check API Server
if curl -fsS --max-time 5 http://lucid_api:8081/health >/dev/null 2>&1; then
    echo "✅ API Server: HEALTHY"
else
    echo "❌ API Server: UNHEALTHY"
fi

echo "============================================"
EOF

RUN cat > /opt/lucid/scripts/network-test.sh <<'EOF' && chmod +x /opt/lucid/scripts/network-test.sh
#!/bin/bash
# Network connectivity test for core support services
set -euo pipefail

echo "[network-test] Core Support Network Test"
echo "========================================"

services=("tor-proxy:9050" "lucid_mongo:27017" "lucid_api_gateway:8080" "lucid_api:8081" "lucid_tunnel_tools:7000")

for service in "${services[@]}"; do
    host=$(echo "$service" | cut -d: -f1)
    port=$(echo "$service" | cut -d: -f2)
    
    if nc -z "$host" "$port" 2>/dev/null; then
        echo "✅ $service: REACHABLE"
    else
        echo "❌ $service: UNREACHABLE"
    fi
done

echo "========================================"
EOF

RUN cat > /opt/lucid/scripts/db-backup.sh <<'EOF' && chmod +x /opt/lucid/scripts/db-backup.sh
#!/bin/bash
# MongoDB backup utility for core support
set -euo pipefail

BACKUP_DIR="/var/log/lucid/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="lucid_backup_${TIMESTAMP}.gz"

echo "[db-backup] Starting MongoDB backup..."
mkdir -p "$BACKUP_DIR"

if mongodump --uri="$MONGO_URL" --archive="$BACKUP_DIR/$BACKUP_FILE" --gzip; then
    echo "✅ Backup completed: $BACKUP_DIR/$BACKUP_FILE"
    # Keep only last 5 backups
    ls -t "$BACKUP_DIR"/lucid_backup_*.gz | tail -n +6 | xargs -r rm
else
    echo "❌ Backup failed"
    exit 1
fi
EOF

# Environment variables for configuration
ENV LUCID_ENV=dev \
    TOOLS_DIR="/opt/lucid/tools" \
    SCRIPTS_DIR="/opt/lucid/scripts" \
    LOG_DIR="/var/log/lucid" \
    PATH="/opt/lucid/scripts:/opt/lucid/tools:$PATH"

# Health check for server tools
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD /opt/lucid/scripts/health-check.sh || exit 1

# Create startup script
RUN cat > /usr/local/bin/server-tools-start.sh <<'EOF' && chmod +x /usr/local/bin/server-tools-start.sh
#!/bin/bash
set -euo pipefail

echo "[server-tools] Lucid Server Tools starting..."
echo "[server-tools] Environment: $LUCID_ENV"
echo "[server-tools] Tools directory: $TOOLS_DIR"
echo "[server-tools] Scripts directory: $SCRIPTS_DIR"

# Wait for core services to be ready
echo "[server-tools] Waiting for core services..."
sleep 10

# Run initial health check
echo "[server-tools] Running initial health check..."
if /opt/lucid/scripts/health-check.sh; then
    echo "[server-tools] Core services are healthy"
else
    echo "[server-tools] Some core services are not healthy (this is normal during startup)"
fi

echo "[server-tools] Server tools ready. Available utilities:"
echo "  - health-check.sh: Check core support service health"
echo "  - network-test.sh: Test network connectivity"
echo "  - db-backup.sh: Backup MongoDB database"
echo "  - mongosh: MongoDB shell"
echo "  - curl, wget, jq: HTTP/API testing"
echo "  - nc, socat: Network debugging"
echo "  - openssl: Certificate/crypto operations"

# Keep container running
exec tail -f /dev/null
EOF

# Security and runtime configuration
USER lucid
WORKDIR /opt/lucid
ENTRYPOINT ["/usr/local/bin/server-tools-start.sh"]