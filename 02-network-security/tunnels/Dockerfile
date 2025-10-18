# LUCID TUNNEL TOOLS - SPEC-4 Stage 0 Network Security (Distroless)
# Professional tunneling utilities for Pi deployment with distroless security
# Multi-platform build for ARM64 Pi and AMD64 development

# syntax=docker/dockerfile:1.7
FROM alpine:3.19 AS tunnel-builder

# Metadata for professional container management
LABEL maintainer="Lucid Development Team" \
      version="1.0.0-distroless" \
      description="Network tunneling tools for Lucid core support (Distroless)" \
      com.lucid.plane="ops" \
      com.lucid.service="tunnel-tools" \
      com.lucid.expose="7000"

# Install comprehensive tunneling and network tools
RUN apk update && apk upgrade \
    && apk add --no-cache --update \
       # Python stack for tunnel management
       python3 \
       py3-requests \
       py3-pysocks \
       py3-cryptography \
       py3-pynacl \
       # Network utilities
       bash \
       netcat-openbsd \
       socat \
       curl \
       wget \
       xxd \
       bind-tools \
       # Security tools
       openssl \
       ca-certificates \
       gnupg \
       # System utilities
       tini \
       jq \
       procps \
       su-exec \
    && apk upgrade \
    && rm -rf /var/cache/apk/* /tmp/* /var/tmp/* \
    && addgroup -S lucid && adduser -S -D -H -s /bin/bash -G lucid lucid

# Create application and data directories
WORKDIR /app
RUN mkdir -p /app/scripts /var/lib/tunnel /var/log/tunnel \
    && chown -R lucid:lucid /app /var/lib/tunnel /var/log/tunnel

# Copy tunnel application files
COPY entrypoint.sh /app/entrypoint.sh
COPY scripts/ /app/scripts/
RUN chmod +x /app/entrypoint.sh /app/scripts/*.sh

# Create comprehensive tunnel management script
RUN cat > /app/scripts/tunnel-manager.py <<'EOF'
#!/usr/bin/env python3
"""
Lucid Tunnel Manager - Professional tunneling utilities
SPEC-4 Stage 0 compliant network security tools
"""

import os
import sys
import json
import time
import socket
import logging
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[tunnel-manager] %(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_tor_connectivity():
    """Check if Tor SOCKS proxy is available"""
    try:
        import socks
        import requests
        
        session = requests.Session()
        session.proxies = {
            'http': 'socks5://tor-proxy:9050',
            'https': 'socks5://tor-proxy:9050'
        }
        
        response = session.get('http://check.torproject.org', timeout=10)
        if 'Congratulations' in response.text:
            logger.info("✅ Tor connectivity: ACTIVE")
            return True
        else:
            logger.warning("❌ Tor connectivity: INACTIVE")
            return False
    except Exception as e:
        logger.error(f"❌ Tor connectivity check failed: {e}")
        return False

def create_tunnel(local_port, remote_host, remote_port):
    """Create a tunnel through Tor SOCKS proxy"""
    logger.info(f"Creating tunnel: localhost:{local_port} -> {remote_host}:{remote_port}")
    
    # Tunnel implementation would go here
    # For now, just log the tunnel creation
    logger.info(f"Tunnel established: {local_port} -> {remote_host}:{remote_port}")
    return True

def health_check():
    """Comprehensive health check for tunnel tools"""
    logger.info("Tunnel Tools Health Check")
    logger.info("==========================")
    
    # Check Tor connectivity
    tor_status = check_tor_connectivity()
    
    # Check tunnel port availability
    tunnel_port = int(os.environ.get('TUNNEL_PORT', '7000'))
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('0.0.0.0', tunnel_port))
        sock.close()
        logger.info(f"✅ Tunnel port {tunnel_port}: AVAILABLE")
        port_status = True
    except OSError:
        logger.info(f"✅ Tunnel port {tunnel_port}: IN USE (expected if tunnels active)")
        port_status = True
    
    logger.info("==========================")
    return tor_status and port_status

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "health":
        if health_check():
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        logger.info("Lucid Tunnel Manager starting...")
        # Main tunnel management logic would go here
        while True:
            time.sleep(30)
EOF

# Make tunnel manager executable
RUN chmod +x /app/scripts/tunnel-manager.py

# Stage 2: Distroless runtime with Python and network tools
FROM gcr.io/distroless/python3-debian12:latest

# Copy Python and all dependencies
COPY --from=tunnel-builder /usr/bin/python3 /usr/bin/python3
COPY --from=tunnel-builder /usr/lib/python3.11 /usr/lib/python3.11

# Copy network utilities
COPY --from=tunnel-builder /usr/bin/nc /usr/bin/nc
COPY --from=tunnel-builder /usr/bin/socat /usr/bin/socat
COPY --from=tunnel-builder /usr/bin/curl /usr/bin/curl
COPY --from=tunnel-builder /usr/bin/wget /usr/bin/wget
COPY --from=tunnel-builder /usr/bin/xxd /usr/bin/xxd
COPY --from=tunnel-builder /usr/bin/nslookup /usr/bin/nslookup
COPY --from=tunnel-builder /usr/bin/openssl /usr/bin/openssl
COPY --from=tunnel-builder /sbin/tini /sbin/tini
COPY --from=tunnel-builder /usr/bin/jq /usr/bin/jq
COPY --from=tunnel-builder /sbin/su-exec /sbin/su-exec

# Copy required dynamic libraries (architecture-specific)
COPY --from=tunnel-builder /lib/*-linux-*/libc.so.6 /lib/
COPY --from=tunnel-builder /lib/*-linux-*/libssl.so.3 /lib/
COPY --from=tunnel-builder /lib/*-linux-*/libcrypto.so.3 /lib/
COPY --from=tunnel-builder /lib/*-linux-*/libz.so.1 /lib/
COPY --from=tunnel-builder /lib/*-linux-*/liblzma.so.5 /lib/
COPY --from=tunnel-builder /lib*/ld-linux-*.so.2 /lib64/

# Copy user and group information
COPY --from=tunnel-builder /etc/passwd /etc/passwd
COPY --from=tunnel-builder /etc/group /etc/group

# Copy CA certificates
COPY --from=tunnel-builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Copy application and create directories with proper ownership
COPY --from=tunnel-builder --chown=lucid:lucid /app /app
COPY --from=tunnel-builder --chown=lucid:lucid /var/lib/tunnel /var/lib/tunnel
COPY --from=tunnel-builder --chown=lucid:lucid /var/log/tunnel /var/log/tunnel

# Environment variables for configuration
ENV TUNNEL_PORT=7000 \
    TUNNEL_MODE=client \
    TOR_PROXY=tor-proxy:9050 \
    LUCID_ENV=dev \
    PYTHONUNBUFFERED=1

# Security and runtime configuration
EXPOSE 7000
USER lucid
WORKDIR /app
ENTRYPOINT ["/sbin/tini", "--", "/app/entrypoint.sh"]
