#!/usr/bin/env sh
# Entrypoint for lucid_tor container
# Path: 02-network-security/tor/entrypoint.sh

set -eu

log() { printf '[tor-entrypoint] %s\n' "$*"; }

# Default tor config
TOR_CONFIG="/etc/tor/torrc"

# Check if torrc exists
if [ ! -f "$TOR_CONFIG" ]; then
    log "Missing torrc at $TOR_CONFIG"
    exit 1
fi

# Ensure data directory exists
if [ ! -d /var/lib/tor ]; then
    log "Creating /var/lib/tor..."
    mkdir -p /var/lib/tor
    chown tor:tor /var/lib/tor
    chmod 700 /var/lib/tor
fi

# Print tor version
tor --version || true

log "Starting Tor with config: $TOR_CONFIG"
exec tor -f "$TOR_CONFIG"
