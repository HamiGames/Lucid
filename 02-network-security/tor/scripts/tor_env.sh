#!/usr/bin/env bash
# Lucid Tor environment (single source of truth)

# Host & ports (piggy-back on tor-proxy container)
TOR_HOST="${TOR_HOST:-127.0.0.1}"
TOR_SOCKS_PORT="${TOR_SOCKS_PORT:-9050}"
TOR_CONTROL_PORT="${TOR_CONTROL_PORT:-9051}"
TOR_CONTAINER_NAME="${TOR_CONTAINER_NAME:-tor-proxy}"
UPSTREAM_SERVICE="${UPSTREAM_SERVICE:-api-gateway}"
UPSTREAM_PORT="${UPSTREAM_PORT:-8080}"
# Paths inside container
TOR_DATA_DIR="${TOR_DATA_DIR:-/run/lucid/tor}"
TOR_COOKIE_FILE="${TOR_COOKIE_FILE:-${TOR_DATA_DIR}/control_auth_cookie}"
TOR_COOKIE_HOST_FILE="${TOR_COOKIE_HOST_FILE:-${TOR_DATA_DIR}/control_auth_cookie}"
TOR_ONION_DIR="${TOR_ONION_DIR:-/run/lucid/onion}"
TOR_SCRIPT_DIR="${TOR_SCRIPT_DIR:-/run/lucid/bin/tor}"
TOR_COOKIE_PORT="${TOR_COOKIE_PORT:-9051}"


# Helper: wait until Tor is fully bootstrapped
wait_for_tor() {
  echo "[tor_env] Waiting for Tor bootstrap on ${TOR_HOST}:${TOR_CONTROL_PORT}..."
  for i in $(seq 1 60); do
    if docker logs "${TOR_CONTAINER_NAME:-tor-proxy}" 2>/dev/null | grep -q "Bootstrapped 100%"; then
      echo "[tor_env] Tor is ready."
      return 0
    fi
    sleep 2
  done
  echo "[tor_env] ERROR: Tor failed to bootstrap within timeout." >&2
  exit 1
}

# Helper: create a dynamic onion
create_dynamic_onion() {
  echo "[tor_env] Creating dynamic onion for ${UPSTREAM_SERVICE}:${UPSTREAM_PORT}..."
  "${TOR_SCRIPT_DIR}/create_dynamic_onion.sh" --target-host "${UPSTREAM_SERVICE}" --target-port "${UPSTREAM_PORT}" --onion-port "${ONION_PORT}" --env-var "${ENV_VAR}" --persistent --wallet --list --remove --rotate --help
}

# Helper: create an ephemeral onion
create_ephemeral_onion() {
  echo "[tor_env] Creating ephemeral onion for ${UPSTREAM_SERVICE}:${UPSTREAM_PORT}..."
  "${TOR_SCRIPT_DIR}/create_ephemeral_onion.sh" --target-host "${UPSTREAM_SERVICE}" --target-port "${UPSTREAM_PORT}" --onion-port "${ONION_PORT}" --env-var "${ENV_VAR}" --persistent --wallet --list --remove --rotate --help
}

# Helper: check if Tor is fully bootstrapped
check_tor_bootstrap() {
  echo "[tor_env] Checking Tor bootstrap on ${TOR_HOST}:${TOR_CONTROL_PORT}..."
  "${TOR_SCRIPT_DIR}/check_tor_bootstrap.sh"
}

# Helper: start Tor
start_tor() {
  echo "[tor_env] Starting Tor on ${TOR_HOST}:${TOR_CONTROL_PORT}..."
  "${TOR_SCRIPT_DIR}/start_tor.sh"
}

main() {
  if ["$1" == "create_dynamic_onion"]; then
    create_dynamic_onion
  elif ["$1" == "create_ephemeral_onion"]; then
    create_ephemeral_onion
  elif ["$1" == "check_tor_bootstrap"]; then
    check_tor_bootstrap
  elif ["$1" == "start_tor"]; then
    start_tor
  fi
  else
    log "Unknown command: $1"
    exit 1
  fi
}

main "$@"