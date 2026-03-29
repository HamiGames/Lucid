#!/usr/bin/env bash
# Shared helpers for tunnel scripts
# Canonical layout: infrastructure/containers/services/tor/tor-operational-layout.yml
# (with container-runtime-layout.yml lucid_services_config_root + x-files-listing host-config paths)
# Aligns with:
#   - 02_network_security/tunnels/Dockerfile.tunnels → /app/tunnel/scripts (create_ephemeral = tor/scripts overlay)
#   - infrastructure/containers/tor/Dockerfile.tor-proxy-02 → /app/run/lucid/tor/bin and /app/run/lucid/tunnels/scripts mirror
#
# Terminal DIR: repo 02_network_security/tunnels/scripts; in-image /app/tunnel/scripts;
#   tor-proxy volume tree /app/run/lucid/tunnels/scripts (same create_ephemeral + bootstrap as tor/scripts).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Defaults from tunnels/Dockerfile ENV unless already set by compose:
#   CONTROL_HOST=tor-proxy CONTROL_PORT=9051
#   COOKIE_FILE=/app/var/lib/tor/control_auth_cookie
#   WRITE_ENV=/app/run/lucid/onion/.onion.env
_lucid_tunnel_env_defaults() {
  if [[ -d /app ]]; then
    # tor-proxy distroless: torrc present, no tunnel-tools Python entrypoint
    if [[ -f /app/run/lucid/tor/torrc ]] && [[ ! -f /app/tunnels/entrypoint.py ]]; then
      CONTROL_HOST="${CONTROL_HOST:-127.0.0.1}"
      if [[ -z "${COOKIE_FILE:-}" ]]; then
        COOKIE_FILE=""
        local c
        for c in /app/run/lucid/onion/control_auth_cookie /app/var/lib/tor/control_auth_cookie; do
          [[ -r "$c" ]] && { COOKIE_FILE="$c"; break; }
        done
        COOKIE_FILE="${COOKIE_FILE:-/app/var/lib/tor/control_auth_cookie}"
      fi
    else
      # lucid-tunnel-tools (or dev with /app layout)
      CONTROL_HOST="${CONTROL_HOST:-tor-proxy}"
      if [[ -z "${COOKIE_FILE:-}" ]]; then
        COOKIE_FILE=""
        local c
        for c in /app/run/lucid/onion/control_auth_cookie /app/var/lib/tor/control_auth_cookie; do
          [[ -r "$c" ]] && { COOKIE_FILE="$c"; break; }
        done
        COOKIE_FILE="${COOKIE_FILE:-/app/var/lib/tor/control_auth_cookie}"
      fi
    fi
    WRITE_ENV="${WRITE_ENV:-/app/run/lucid/onion/.onion.env}"
  else
    # No /app tree (rare): match tor-proxy-02 layout if bind-mounts provide it, else set COOKIE_FILE in env
    CONTROL_HOST="${CONTROL_HOST:-tor-proxy}"
    COOKIE_FILE="${COOKIE_FILE:-/app/run/lucid/onion/control_auth_cookie}"
    WRITE_ENV="${WRITE_ENV:-/app/run/lucid/onion/.onion.env}"
  fi
  CONTROL_PORT="${CONTROL_PORT:-9051}"
  TOR_CONTAINER_NAME="${TOR_CONTAINER_NAME:-${CONTROL_HOST:-tor-proxy}}"
  ENV_FILE="${ENV_FILE:-${WRITE_ENV}}"
}

_lucid_tunnel_env_defaults

_have() { command -v "$1" >/dev/null 2>&1; }

load_env() {
  if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC2046
    export $(grep -E '^(ONION|COOKIE|HEX)=' "$ENV_FILE" | xargs -d '\n' 2>/dev/null || true)
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
  # Read cookie from path visible to tunnel-tools or tor sidecar (see Dockerfiles).
  local cookie_file="${COOKIE_FILE:-/app/var/lib/tor/control_auth_cookie}"
  xxd -p "${cookie_file}" 2>/dev/null | tr -d '\n' || true
}

tor_ctl() {
  local container="${1:-${TOR_CONTAINER_NAME}}" cmds="${2:-}"
  local control_host="${CONTROL_HOST:-${container}}"
  local control_port="${CONTROL_PORT:-9051}"
  nc -w 5 "${control_host}" "${control_port}" <<<"${cmds}"
}

wait_bootstrap() {
  local tries="${1:-60}" i
  for ((i = 0; i < tries; i++)); do
    if _have docker; then
      if docker logs "${TOR_CONTAINER_NAME:-${CONTROL_HOST:-tor-proxy}}" 2>&1 | grep -q "Bootstrapped 100%"; then
        return 0
      fi
    else
      local hex=""
      [[ -r "${COOKIE_FILE:-}" ]] && hex="$(xxd -p "${COOKIE_FILE}" 2>/dev/null | tr -d '\n' || true)"
      if [[ -n "$hex" ]]; then
        local out
        out="$(printf 'AUTHENTICATE %s\r\nGETINFO status/bootstrap-phase\r\nQUIT\r\n' "$hex" \
          | nc -w 3 "${CONTROL_HOST}" "${CONTROL_PORT}" 2>/dev/null || true)"
        if echo "$out" | grep -q "PROGRESS=100"; then
          return 0
        fi
      fi
    fi
    sleep 1
  done
  echo "[tor] bootstrap not complete" >&2
  return 1
}
