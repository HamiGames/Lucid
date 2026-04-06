#!/usr/bin/env bash
# x-lucid-file-path: /app/02_network_security/tor/scripts/set_host_config.sh
# x-lucid-file-directory: /app/02_network_security/tor/scripts
# x-lucid-file-type: shell
#
# Reads the Lucid host registry (cross-container DNS, ports, static host IPs) from
#   /app/infrastructure/containers/services/host-config.yml
# and exports environment variables used by Tor scripts and onion helpers.
#
# Canonical in-container path (see infrastructure/containers/*/Dockerfile COPY):
#   infrastructure/containers/host-config.yml  ->  /app/infrastructure/containers/services/host-config.yml
# Optional legacy mirror: /app/configs/host-config.yml
#
# Usage:
#   . "/app/02_network_security/tor/scripts/set_host_config.sh"
#   lucid_load_host_config
# Or run directly (WORKDIR /app in tor images):
#   ./02_network_security/tor/scripts/set_host_config.sh
#
# Terminal DIR when exec'd in container: WORKDIR /app (or repo root on dev host).

set -euo pipefail

log_hc() { printf '[lucid-host-config] %s\n' "$*" >&2; }

# shellcheck disable=SC2034
LUCID_HOST_CONFIG_PATH="${LUCID_HOST_CONFIG_PATH:-}"

# Extract port, service_name, host_ip from a top-level services.* block (two-space indent keys).
_lucid_hc_parse_block() {
  local yml_file="$1"
  local block_key="$2"
  awk -v blk="$block_key" '
    BEGIN { p = 0 }
    $0 ~ "^  " blk ": *$" { p = 1; next }
    p && /^  [a-z_][a-z0-9_]*: *$/ && $0 !~ "^  " blk ":" { exit }
    p && /^    port:/ {
      line = $0
      sub(/^[^:]*:[[:space:]]*/, "", line)
      gsub(/[[:space:]]+$/, "", line)
      print "port=" line
    }
    p && /^    service_name:/ {
      line = $0
      sub(/^[^:]*:[[:space:]]*/, "", line)
      gsub(/[[:space:]]+$/, "", line)
      print "service_name=" line
    }
    p && /^    host_ip:/ {
      line = $0
      sub(/^[^:]*:[[:space:]]*/, "", line)
      gsub(/[[:space:]]+$/, "", line)
      print "host_ip=" line
    }
  ' "$yml_file"
}

_lucid_hc_resolve_path() {
  local p
  for p in \
    "${LUCID_HOST_CONFIG_PATH:-}" \
    "/app/infrastructure/containers/services/host-config.yml" \
    "/app/configs/host-config.yml"; do
    [[ -n "$p" && -f "$p" ]] && { printf '%s' "$p"; return 0; }
  done
  return 1
}

# Populates exports from host-config.yml. Safe to call multiple times.
lucid_load_host_config() {
  local yml
  if ! yml="$(_lucid_hc_resolve_path)"; then
    log_hc "WARN: host-config.yml not found under /app/service_configs or /app/configs — using built-in defaults"
    export LUCID_HOST_CONFIG_PATH=""
  else
    export LUCID_HOST_CONFIG_PATH="$yml"
  fi

  local tor_port tor_name tor_ip gw_port gw_name gw_ip tun_port tun_name tun_ip

  local gui_port gui_name gui_ip mongo_port mongo_name mongo_ip

  if [[ -n "${LUCID_HOST_CONFIG_PATH}" ]]; then
    while IFS= read -r line; do
      case "$line" in
        port=*) tor_port="${line#port=}" ;;
        service_name=*) tor_name="${line#service_name=}" ;;
        host_ip=*) tor_ip="${line#host_ip=}" ;;
      esac
    done < <(_lucid_hc_parse_block "${LUCID_HOST_CONFIG_PATH}" "tor_socks")

    while IFS= read -r line; do
      case "$line" in
        port=*) gw_port="${line#port=}" ;;
        service_name=*) gw_name="${line#service_name=}" ;;
        host_ip=*) gw_ip="${line#host_ip=}" ;;
      esac
    done < <(_lucid_hc_parse_block "${LUCID_HOST_CONFIG_PATH}" "main_lucid_gateway")

    while IFS= read -r line; do
      case "$line" in
        port=*) tun_port="${line#port=}" ;;
        service_name=*) tun_name="${line#service_name=}" ;;
        host_ip=*) tun_ip="${line#host_ip=}" ;;
      esac
    done < <(_lucid_hc_parse_block "${LUCID_HOST_CONFIG_PATH}" "tunnel_tools")

    while IFS= read -r line; do
      case "$line" in
        port=*) gui_port="${line#port=}" ;;
        service_name=*) gui_name="${line#service_name=}" ;;
        host_ip=*) gui_ip="${line#host_ip=}" ;;
      esac
    done < <(_lucid_hc_parse_block "${LUCID_HOST_CONFIG_PATH}" "gui_api_bridge")

    while IFS= read -r line; do
      case "$line" in
        port=*) mongo_port="${line#port=}" ;;
        service_name=*) mongo_name="${line#service_name=}" ;;
        host_ip=*) mongo_ip="${line#host_ip=}" ;;
      esac
    done < <(_lucid_hc_parse_block "${LUCID_HOST_CONFIG_PATH}" "lucid_mongodb")
  fi

  # Defaults align with infrastructure/containers/host-config.yml (tor_socks, main_lucid_gateway, tunnel_tools).
  export LUCID_TOR_SOCKS_SERVICE="${tor_name:-tor-socks}"
  export LUCID_TOR_SOCKS_PORT="${tor_port:-9050}"
  export LUCID_TOR_PUBLIC_HOST_IP="${tor_ip:-}"
  export LUCID_API_GATEWAY_SERVICE="${gw_name:-api-gateway}"
  export LUCID_API_GATEWAY_PORT="${gw_port:-8080}"
  export LUCID_API_GATEWAY_HOST_IP="${gw_ip:-}"
  export LUCID_TUNNEL_TOOLS_SERVICE="${tun_name:-tunnel-tools}"
  export LUCID_TUNNEL_TOOLS_PORT="${tun_port:-7000}"
  export LUCID_TUNNEL_TOOLS_HOST_IP="${tun_ip:-}"
  export LUCID_GUI_API_BRIDGE_SERVICE="${gui_name:-gui-api-bridge}"
  export LUCID_GUI_API_BRIDGE_PORT="${gui_port:-8203}"
  export LUCID_GUI_API_BRIDGE_HOST_IP="${gui_ip:-}"
  export LUCID_MONGODB_SERVICE="${mongo_name:-lucid-mongodb}"
  export LUCID_MONGODB_PORT="${mongo_port:-27019}"
  export LUCID_MONGODB_HOST_IP="${mongo_ip:-}"

  # Cross-container Docker DNS name for the Tor SOCKS/control stack (same as service_name for tor_socks).
  export LUCID_TOR_DOCKER_SERVICE="${LUCID_TOR_SOCKS_SERVICE}"

  # Compatibility: scripts historically used these names for upstream HTTP gateway.
  export UPSTREAM_SERVICE="${UPSTREAM_SERVICE:-$LUCID_API_GATEWAY_SERVICE}"
  export UPSTREAM_PORT="${UPSTREAM_PORT:-$LUCID_API_GATEWAY_PORT}"

  # SOCKS port for clients (registry — Tor still listens on TOR_SOCKS_PORT from torrc).
  export TOR_SOCKS_PORT="${TOR_SOCKS_PORT:-$LUCID_TOR_SOCKS_PORT}"

  # Control plane: not listed in host-config (Tor convention 9051). Peers use LUCID_TOR_DOCKER_SERVICE:TOR_CONTROL_PORT.
  export TOR_CONTROL_PORT="${TOR_CONTROL_PORT:-9051}"
  # Do not set TOR_CONTROL_HOST here — use 127.0.0.1 inside the tor-socks container; use LUCID_TOR_DOCKER_SERVICE from peers.

  # Alias for docs / compose that referred to tor_public_ip.
  export TOR_PUBLIC_HOST_IP="${TOR_PUBLIC_HOST_IP:-$LUCID_TOR_PUBLIC_HOST_IP}"

  # Optional: docker logs / compose container name (not in YAML) — keep override.
  export TOR_CONTAINER_NAME="${TOR_CONTAINER_NAME:-tor-proxy}"

  local out_dir="${TOR_CONFIG_DIR:-/app/run/lucid/tor}"
  if ! mkdir -p "$out_dir" 2>/dev/null; then
    out_dir="${TMPDIR:-/tmp}/lucid-tor-host-config"
    mkdir -p "$out_dir" 2>/dev/null || out_dir=""
  fi
  if [[ -z "$out_dir" || ! -d "$out_dir" ]]; then
    log_hc "WARN: cannot write lucid-host-network.env — no writable output directory"
  else
    local out_file="${out_dir}/lucid-host-network.env"
    umask 022
    cat > "${out_file}.tmp" << EOF
# Generated by set_host_config.sh — do not hand-edit.
# Source: ${LUCID_HOST_CONFIG_PATH:-<defaults>}
LUCID_HOST_CONFIG_PATH=${LUCID_HOST_CONFIG_PATH:-}
LUCID_TOR_SOCKS_SERVICE=${LUCID_TOR_SOCKS_SERVICE}
LUCID_TOR_SOCKS_PORT=${LUCID_TOR_SOCKS_PORT}
LUCID_TOR_PUBLIC_HOST_IP=${LUCID_TOR_PUBLIC_HOST_IP}
LUCID_TOR_DOCKER_SERVICE=${LUCID_TOR_DOCKER_SERVICE}
LUCID_API_GATEWAY_SERVICE=${LUCID_API_GATEWAY_SERVICE}
LUCID_API_GATEWAY_PORT=${LUCID_API_GATEWAY_PORT}
LUCID_API_GATEWAY_HOST_IP=${LUCID_API_GATEWAY_HOST_IP}
LUCID_TUNNEL_TOOLS_SERVICE=${LUCID_TUNNEL_TOOLS_SERVICE}
LUCID_TUNNEL_TOOLS_PORT=${LUCID_TUNNEL_TOOLS_PORT}
LUCID_TUNNEL_TOOLS_HOST_IP=${LUCID_TUNNEL_TOOLS_HOST_IP}
LUCID_GUI_API_BRIDGE_SERVICE=${LUCID_GUI_API_BRIDGE_SERVICE}
LUCID_GUI_API_BRIDGE_PORT=${LUCID_GUI_API_BRIDGE_PORT}
LUCID_GUI_API_BRIDGE_HOST_IP=${LUCID_GUI_API_BRIDGE_HOST_IP}
LUCID_MONGODB_SERVICE=${LUCID_MONGODB_SERVICE}
LUCID_MONGODB_PORT=${LUCID_MONGODB_PORT}
LUCID_MONGODB_HOST_IP=${LUCID_MONGODB_HOST_IP}
UPSTREAM_SERVICE=${UPSTREAM_SERVICE}
UPSTREAM_PORT=${UPSTREAM_PORT}
TOR_SOCKS_PORT=${TOR_SOCKS_PORT}
TOR_CONTROL_PORT=${TOR_CONTROL_PORT}
LUCID_TOR_DOCKER_SERVICE=${LUCID_TOR_DOCKER_SERVICE}
TOR_PUBLIC_HOST_IP=${TOR_PUBLIC_HOST_IP}
EOF
    mv "${out_file}.tmp" "$out_file"
    log_hc "Wrote ${out_file}"
  fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  lucid_load_host_config "$@"
fi
