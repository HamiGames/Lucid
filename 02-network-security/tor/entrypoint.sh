#!/usr/bin/env bash
# Path: 02-network-security/tor/entrypoint.sh
# Custom entrypoint for Lucid Tor Proxy

set -euo pipefail

log() { printf '[tor-entrypoint] %s\n' "$*"; }

# Start tor in background
log "Starting Tor..."
tor -f /etc/tor/torrc &
TOR_PID=$!

# Wait for tor to bootstrap
log "Waiting for Tor bootstrap..."
while true; do
  if grep -q "Bootstrapped 100%: Done" <(docker logs "$HOSTNAME" 2>&1 || true); then
    break
  fi
  sleep 2
done
log "Tor bootstrap complete."

# Run seed_env.sh if available
if [[ -x "/scripts/seed_env.sh" ]]; then
  log "Seeding environment variables..."
  /scripts/seed_env.sh
else
  log "WARN: seed_env.sh not found/executable"
fi

# Run create_ephemeral_onion.sh if available
if [[ -x "/scripts/create_ephemeral_onion.sh" ]]; then
  log "Creating ephemeral onion service..."
  /scripts/create_ephemeral_onion.sh --host 127.0.0.1 --ports "80 lucid_api:4000"
else
  log "WARN: create_ephemeral_onion.sh not found/executable"
fi

# Bring tor to foreground to keep container alive
wait $TOR_PID
