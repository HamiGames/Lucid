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
  # NOTE: tor-proxy is distroless (gcr.io/distroless/base-debian12) — no shell,
  # no xxd, no nc inside the container. Cookie is read directly from the
  # volume-mounted path accessible to lucid-tunnel-tools.
  # The 'container' arg is retained for API compatibility but is not used.
  local cookie_file="${COOKIE_FILE:-/run/lucid/tor/control_auth_cookie}"
  xxd -p "${cookie_file}" 2>/dev/null | tr -d '\n' || true
}

tor_ctl() {
  # Sends raw Tor control protocol commands directly over the Docker network.
  # tor-proxy is distroless — nc must run here in lucid-tunnel-tools, not via
  # docker exec into the container.
  local container="${1:-${TOR_CONTAINER_NAME}}" cmds="${2:-}"
  local control_host="${CONTROL_HOST:-${container}}"
  local control_port="${CONTROL_PORT:-9051}"
  nc -w 5 "${control_host}" "${control_port}" <<<"${cmds}"
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
