#!/usr/bin/env bash
# Lucid Tor environment (single source of truth)

# Host & ports (piggy-back on lucid_tor container)
TOR_HOST="${TOR_HOST:-127.0.0.1}"
TOR_SOCKS_PORT="${TOR_SOCKS_PORT:-9050}"
TOR_CONTROL_PORT="${TOR_CONTROL_PORT:-9051}"

# Paths inside container
TOR_DATA_DIR="${TOR_DATA_DIR:-/var/lib/tor}"
TOR_COOKIE_FILE="${TOR_COOKIE_FILE:-${TOR_DATA_DIR}/control.authcookie}"

# Helper: wait until Tor is fully bootstrapped
wait_for_tor() {
  echo "[tor_env] Waiting for Tor bootstrap on ${TOR_HOST}:${TOR_CONTROL_PORT}..."
  for i in $(seq 1 60); do
    if docker logs lucid_tor 2>/dev/null | grep -q "Bootstrapped 100%"; then
      echo "[tor_env] Tor is ready."
      return 0
    fi
    sleep 2
  done
  echo "[tor_env] ERROR: Tor failed to bootstrap within timeout." >&2
  return 1
}
