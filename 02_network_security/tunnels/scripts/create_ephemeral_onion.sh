#!/usr/bin/env bash
# Create a Tor v3 *ephemeral* onion via the ControlPort.
# Path: 02_network_security/tunnels/scripts/create_ephemeral_onion.sh
# Aligns with tunnels/Dockerfile (tunnel-tools) and tor/Dockerfile.tor-proxy-02 (Tor sidecar).

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_lib.sh"

# Fallback if --ports not provided. ONION_PORTS from Dockerfile may be "80 api-gateway:8080"
UPSTREAM_SERVICE="${UPSTREAM_SERVICE:-api-gateway}"
UPSTREAM_PORT="${UPSTREAM_PORT:-8080}"
DEFAULT_PORT_MAP="${ONION_PORTS:-80 ${UPSTREAM_SERVICE}:${UPSTREAM_PORT}}"

# ---- helpers ----
log() { printf '[create_ephemeral_onion] %s\n' "$*"; }
die() { printf '[create_ephemeral_onion][ERROR] %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "missing dependency: $1"; }

# Resolve a hostname to a single IPv4 address; passthrough if already an IP.
resolve_ip() {
  local host="$1"

  if printf '%s' "$host" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'; then
    printf '%s' "$host"
    return 0
  fi

  if command -v getent >/dev/null 2>&1; then
    local ip
    ip=$(getent hosts "$host" 2>/dev/null | awk '{print $1; exit}')
    if [[ -n "$ip" ]]; then
      printf '%s' "$ip"
      return 0
    fi
  fi

  if command -v nslookup >/dev/null 2>&1; then
    local ip
    ip=$(nslookup -timeout=2 "$host" 2>/dev/null | awk '/^Address: /{print $2; exit}')
    if [[ -n "$ip" ]]; then
      printf '%s' "$ip"
      return 0
    fi
  fi

  log "WARNING: DNS resolution tools not available, using hostname directly: $host"
  printf '%s' "$host"
  return 0
}

ctl_send() {
  local cmd="$1"
  local cookie_hex
  [[ -r "$COOKIE_FILE" ]] || die "cookie not readable: $COOKIE_FILE"
  cookie_hex="$(xxd -p "$COOKIE_FILE" | tr -d '\n')"
  printf 'AUTHENTICATE %s\r\n%s\r\nQUIT\r\n' "$cookie_hex" "$cmd" \
    | nc -w 5 "$CONTROL_HOST" "$CONTROL_PORT"
}

build_port_args() {
  local spec="$1"
  spec="$(printf '%s' "$spec" | tr ',;' ' ')"
  spec="$(printf '%s' "$spec" | tr -s ' ')"

  local -a toks=()
  read -r -a toks <<<"$spec"

  local n="${#toks[@]}"
  (( n % 2 == 0 )) || die "--ports must contain pairs: VPORT TARGET (got: $spec)"

  local i=0 out=() vport target host tport ip
  while (( i < n )); do
    vport="${toks[i]}"; target="${toks[i+1]}"; i=$((i+2))
    host="${target%:*}"
    tport="${target##*:}"
    [[ -n "$host" ]] || die "invalid target (no host): $target"
    [[ -n "$tport" ]] || die "invalid target (no port): $target"

    ip="$(resolve_ip "$host")"
    [[ -n "$ip" ]] || die "cannot resolve host: $host"
    out+=("Port=${vport},${ip}:${tport}")
  done

  printf '%s ' "${out[@]}"
}

# ---- arg parsing ----
PORT_SPECS=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --control-host) CONTROL_HOST="$2"; shift 2;;
    --control-port) CONTROL_PORT="$2"; shift 2;;
    --cookie-file)  COOKIE_FILE="$2";  shift 2;;
    --ports)        PORT_SPECS="${2}"; shift 2;;
    --write-env)    WRITE_ENV="$2";    shift 2;;
    --help|-h)
      cat <<'USAGE'
Usage: create_ephemeral_onion.sh [--control-host tor-proxy|127.0.0.1] [--control-port 9051]
                                 [--cookie-file /app/var/lib/tor/control_auth_cookie]
                                 [--ports "80 api-gateway:8080[, 443 api-gateway:8443]"]
                                 [--write-env /app/run/lucid/onion/.onion.env]
Notes:
 - Default paths match 02_network_security/tunnels/Dockerfile and tor/Dockerfile.tor-proxy-02.
 - --ports: pairs VPORT TARGET (HOST:PORT). Tor ADD_ONION requires IP:PORT for targets.
USAGE
      exit 0;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

need nc
need xxd

[[ -n "${PORT_SPECS}" ]] || PORT_SPECS="${DEFAULT_PORT_MAP}"
PORT_ARGS="$(build_port_args "${PORT_SPECS}")"
[[ -n "$PORT_ARGS" ]] || die "no valid Port= mappings built from: ${PORT_SPECS}"

log "Using ControlPort ${CONTROL_HOST}:${CONTROL_PORT}"
log "Cookie file: ${COOKIE_FILE}"
log "ADD_ONION maps: ${PORT_ARGS}"

RAW="$(ctl_send "ADD_ONION NEW:ED25519-V3 ${PORT_ARGS}")" || true
printf '%s\n' "$RAW" | sed -n '1,120p'

if ! printf '%s\n' "$RAW" | grep -q '^250-ServiceID='; then
  die "ADD_ONION failed (see control reply above)"
fi

ONION_ID="$(printf '%s\n' "$RAW" | awk -F= '/^250-ServiceID=/{print $2; exit}')"
ONION_ADDR="${ONION_ID}.onion"
log "Created onion: ${ONION_ADDR}"

if [[ -n "$WRITE_ENV" ]] && { [[ -w "$(dirname "$WRITE_ENV")" ]] || mkdir -p "$(dirname "$WRITE_ENV")" 2>/dev/null; }; then
  {
    printf 'ONION=%s\n' "$ONION_ADDR"
    PRIV="$(printf '%s\n' "$RAW" | awk -F= '/^250-PrivateKey=/{print $2; exit}')"
    if [[ -n "$PRIV" ]]; then
      printf '#HS_PRIVATE_KEY=%s\n' "$PRIV"
    fi
  } >"$WRITE_ENV" 2>/dev/null || true
  log "Wrote ${WRITE_ENV}"
fi

printf 'ONION=%s\n' "$ONION_ADDR"
