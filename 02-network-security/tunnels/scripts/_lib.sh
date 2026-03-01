#!/usr/bin/env bash
# Shared helpers for tunnel scripts (works against tor-proxy container)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load environment variables from .env file (set by docker-compose or environment)
# Default to WRITE_ENV if set, otherwise use standard location
ENV_FILE="${ENV_FILE:-${WRITE_ENV:-/run/lucid/onion/.onion.env}}"

# Tor container name (from environment or default)
TOR_CONTAINER_NAME="${TOR_CONTAINER_NAME:-${CONTROL_HOST:-tor-proxy}}"

_have(){ command -v "$1" >/dev/null 2>&1; }

load_env() {
  if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC2046
    export $(grep -E '^(ONION|COOKIE|HEX)=' "$ENV_FILE" | xargs -d '\n' || true)
  fi
}

save_env_var() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    if ! sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE" 2>/dev/null; then
      if _have sudo; then sudo sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
      else echo "[_lib] ERROR: cannot write $key to $ENV_FILE"; exit 1; fi
    fi
  else
    printf "%s=%s\n" "$key" "$val" >> "$ENV_FILE" 2>/dev/null || {
      if _have sudo; then printf "%s=%s\n" "$key" "$val" | sudo tee -a "$ENV_FILE" >/dev/null
      else echo "[_lib] ERROR: cannot append $key to $ENV_FILE"; exit 1; fi
    }
  fi
}

hex_from_cookie_in_container() {
  local container="${1:-${TOR_CONTAINER_NAME}}"
  docker exec "$container" sh -lc 'hexdump -v -e "/1 \"%02x\"" /var/lib/tor/control.authcookie' 2>/dev/null || true
}

tor_ctl() {
  local container="${1:-${TOR_CONTAINER_NAME}}" cmds="${2:-}"
  docker exec -i "$container" sh -lc 'nc 127.0.0.1 9051' <<<"$cmds"
}

wait_bootstrap() {
  local container="${1:-${TOR_CONTAINER_NAME}}" tries=60
  for _ in $(seq 1 "$tries"); do
    if docker logs "$container" 2>&1 | grep -q "Bootstrapped 100%"; then
      return 0
    fi
    sleep 1
  done
  echo "[tor] bootstrap not complete" >&2
  return 1
}
