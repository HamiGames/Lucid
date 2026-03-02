#!/usr/bin/env bash
# =============================================================================
# tor_entrypoint.sh — Lucid Tor Proxy Container Entrypoint v3.0.0
# =============================================================================
# Distroless-compatible entrypoint for the Tor daemon.
#
# Execution order:
#   1.  Preload consensus/cert/onion data  → fast bootstrap, onion consistency
#   2.  Generate torrc from env            → configuration
#   3.  Append bridge config               → ISP bypass
#   4.  Start Tor daemon                   → background process
#   5.  Wait for + locate auth cookie      → Tor must be UP first
#   6.  Distribute cookie to targets       → inter-service auth
#   7.  Wait for full bootstrap            → 100% via control port
#   8.  Verify onion service               → if configured
#   9.  Background health monitor          → keep container alive
#  10.  Wait on Tor PID                    → container lifecycle
#
# Distroless notes:
#   - Control port communication uses bash /dev/tcp — no netcat/socat
#   - hex_encode_file() has a pure bash fallback when od/xxd are absent
#   - File sizes checked with wc -c, not stat
#   - Subdirectory walk uses bash globs — find(1) is not required
#   - Cookie search scans multiple candidate paths — no find(1) needed
# =============================================================================
set -euo pipefail
IFS=$'\n\t'

# =============================================================================
# Constants
# =============================================================================
readonly SCRIPT_VERSION="3.0.0"
readonly COOKIE_SIZE=32        # Tor auth cookie is always exactly 32 bytes
readonly COOKIE_HEX_LENGTH=64  # 32 binary bytes → 64 hex nibbles

# =============================================================================
# Logging
# =============================================================================
_log() {
    local level="$1"; shift
    local ts
    ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || printf 'now')"
    printf '[%s] [%s] [tor-entrypoint] %s\n' "$ts" "$level" "$*" >&2
}
log()       { _log "INFO " "$@"; }
log_warn()  { _log "WARN " "$@"; }
log_error() { _log "ERROR" "$@"; }
log_debug() { [[ "${TOR_DEBUG:-0}" == "1" ]] && _log "DEBUG" "$@" || true; }

# =============================================================================
# Environment variables  (set via docker-compose .env.* files)
# =============================================================================

# ── Paths ─────────────────────────────────────────────────────────────────────
TOR_DATA_DIR="${TOR_DATA_DIR:-/var/lib/tor}"
TOR_CONFIG_DIR="${TOR_CONFIG_DIR:-/etc/tor}"
TOR_LOG_DIR="${TOR_LOG_DIR:-/var/log/tor}"
TOR_LOG_FILE="${TOR_LOG_DIR}/tor.log"
TORRC="${TOR_CONFIG_DIR}/torrc"

# ── Ports ──────────────────────────────────────────────────────────────────────
TOR_SOCKS_PORT="${TOR_SOCKS_PORT:-9050}"
TOR_CONTROL_PORT="${TOR_CONTROL_PORT:-9051}"
TOR_CONTROL_SOCKET="${TOR_CONTROL_SOCKET:-}"   # optional unix socket path
TOR_DNS_PORT="${TOR_DNS_PORT:-0}"              # 0 = disabled
TOR_TRANS_PORT="${TOR_TRANS_PORT:-0}"          # 0 = disabled

# ── Cookie / auth ──────────────────────────────────────────────────────────────
TOR_COOKIE_AUTH="${TOR_COOKIE_AUTH:-1}"
TOR_COOKIE_FILE="${TOR_COOKIE_FILE:-${TOR_DATA_DIR}/control_auth_cookie}"
# Colon-separated list of additional paths the cookie must be copied to.
# Example: TOR_COOKIE_TARGETS=/shared/control_auth_cookie:/mnt/tor/cookie
TOR_COOKIE_TARGETS="${TOR_COOKIE_TARGETS:-}"

# ── Seed data ──────────────────────────────────────────────────────────────────
TOR_SEED_DIR="${TOR_SEED_DIR:-/seed/tor-data}"
TOR_USE_SEED="${TOR_USE_SEED:-1}"

# ── Bridges / pluggable transports ─────────────────────────────────────────────
TOR_USE_BRIDGES="${TOR_USE_BRIDGES:-0}"
# Newline-separated bridge lines. "Bridge " prefix optional — added when absent.
TOR_BRIDGES="${TOR_BRIDGES:-}"
TOR_PLUGGABLE_TRANSPORT="${TOR_PLUGGABLE_TRANSPORT:-}"

# ── Onion service ──────────────────────────────────────────────────────────────
TOR_ONION_SERVICE_ENABLED="${TOR_ONION_SERVICE_ENABLED:-0}"
TOR_ONION_SERVICE_DIR="${TOR_ONION_SERVICE_DIR:-${TOR_DATA_DIR}/onion_service}"
TOR_ONION_SERVICE_PORT="${TOR_ONION_SERVICE_PORT:-80}"
TOR_ONION_SERVICE_TARGET="${TOR_ONION_SERVICE_TARGET:-127.0.0.1:80}"

# ── Timing ─────────────────────────────────────────────────────────────────────
TOR_BOOTSTRAP_TIMEOUT="${TOR_BOOTSTRAP_TIMEOUT:-300}"
TOR_BOOTSTRAP_POLL_INTERVAL="${TOR_BOOTSTRAP_POLL_INTERVAL:-5}"
TOR_COOKIE_WAIT_TIMEOUT="${TOR_COOKIE_WAIT_TIMEOUT:-60}"
TOR_HEALTH_CHECK_INTERVAL="${TOR_HEALTH_CHECK_INTERVAL:-30}"

# ── Runtime user ───────────────────────────────────────────────────────────────
TOR_USER="${TOR_USER:-debian-tor}"

# ── Internal state ─────────────────────────────────────────────────────────────
TOR_PID=""

# =============================================================================
# Utility helpers
# =============================================================================

# Ensure a directory exists; optionally chown it.
ensure_dir() {
    local dir="$1"
    local owner="${2:-}"
    [[ -d "$dir" ]] || mkdir -p "$dir"
    if [[ -n "$owner" ]]; then
        chown "$owner" "$dir" 2>/dev/null \
            || log_warn "chown ${owner} ${dir} failed — continuing"
    fi
}

# Return file size in bytes via wc -c (stat absent on many minimal images).
file_size_bytes() {
    local f="$1"
    if [[ ! -f "$f" ]]; then
        printf '0'
    else
        wc -c < "$f" | tr -d '[:space:]'
    fi
}

# Hex-encode a binary file.
# Tries: od (coreutils) → xxd → pure bash fallback.
# Output: lowercase hex string on stdout, no trailing newline.
hex_encode_file() {
    local file="$1"

    if command -v od &>/dev/null; then
        od -An -tx1 "$file" | tr -d ' \n'
    elif command -v xxd &>/dev/null; then
        xxd -p "$file" | tr -d '\n'
    else
        # Pure bash — byte-by-byte; slow but works in fully distroless images
        local hex="" char
        while IFS= read -r -d '' -n 1 char; do
            printf -v hex '%s%02x' "$hex" "'$char"
        done < "$file"
        printf '%s' "$hex"
    fi
}

# =============================================================================
# Cookie validation
# =============================================================================
# Validates that a cookie file is a genuine Tor auth cookie:
#   1. File exists and is a regular file
#   2. Binary size is exactly COOKIE_SIZE (32) bytes  — checked via wc -c
#   3. Hex encoding is exactly COOKIE_HEX_LENGTH (64) chars — proves the
#      content is pure binary and has not been double-encoded or truncated
#
# Usage:  validate_cookie_file "/path/to/control_auth_cookie"
# Exits the container on any failure — a bad cookie means zero connectivity.
validate_cookie_file() {
    local cookie_path="$1"

    # ── 1. Existence ────────────────────────────────────────────────────────
    if [[ ! -f "${cookie_path}" ]]; then
        log_error "Cookie validation FAILED: file does not exist: ${cookie_path}"
        exit 1
    fi

    # ── 2. Binary size check (wc -c — distroless-safe, no stat needed) ─────
    local byte_count
    byte_count="$(wc -c < "${cookie_path}" | tr -d '[:space:]')"

    if [[ -z "${byte_count}" ]]; then
        log_error "Cookie validation FAILED: could not determine file size: ${cookie_path}"
        exit 1
    fi

    if (( byte_count != COOKIE_SIZE )); then
        log_error "Cookie validation FAILED: size=${byte_count} bytes (expected exactly ${COOKIE_SIZE}): ${cookie_path}"
        log_error "  A wrong size means Tor has not finished writing the cookie, or the"
        log_error "  file was corrupted / double-encoded. Aborting — no valid cookie, no connections."
        exit 1
    fi

    log_debug "Cookie size OK: ${byte_count} bytes — ${cookie_path}"

    # ── 3. Hex-length check ─────────────────────────────────────────────────
    # hex_encode_file() tries od → xxd → pure-bash fallback (distroless-safe).
    local hex_str
    hex_str="$(hex_encode_file "${cookie_path}")"
    local hex_len="${#hex_str}"

    if (( hex_len != COOKIE_HEX_LENGTH )); then
        log_error "Cookie validation FAILED: hex-encoded length=${hex_len} chars (expected exactly ${COOKIE_HEX_LENGTH}): ${cookie_path}"
        log_error "  Expected 32 binary bytes → 64 hex nibbles."
        log_error "  Got ${hex_len} chars — the cookie has been corrupted or double-encoded."
        log_error "  Raw hex dump (first 80 chars): ${hex_str:0:80}"
        exit 1
    fi

    log_debug "Cookie hex-length OK: ${hex_len} chars — ${cookie_path}"
    log "Cookie validated: ${cookie_path} — ${byte_count} bytes / ${hex_len}-char hex — GOOD"
}

# =============================================================================
# Step 1 — Preload seed / consensus / cert / onion data
# =============================================================================
# This function is the bootstrap accelerator.  Without it every cold start
# must fetch the full consensus + authority certs from the network BEFORE it
# can validate a single relay descriptor — which is exactly why the container
# fails to reach consensus on a clean start.
#
# What it loads and why:
#
#   cached-certs               — Authority signing + identity certificates.
#                                Tor CANNOT validate any consensus document
#                                without these.  This is the single most
#                                important file for bootstrap speed.
#
#   cached-consensus           — The full signed network consensus.  Preloading
#                                this means Tor already knows the state of the
#                                network and skips the initial consensus fetch.
#
#   cached-microdesc-consensus — Microdescriptor variant of the consensus.
#                                Required for building circuits when
#                                UseMicrodescriptors 1 (the Tor default).
#
#   cached-microdescs          — Microdescriptors for individual relays.
#                                Tor builds circuits from these.
#
#   cached-microdescs.new      — Freshly downloaded microdescs not yet merged.
#
#   cached-descriptors         — Full relay descriptors (older clients / exits).
#
#   cached-extrainfo           — Extra-info documents.
#
#   state                      — Guard state, transport state, bandwidth stats.
#                                Preserving guard selection prevents Tor from
#                                rotating guards on every restart.
#
# Subdirectory walk:
#   Every subdirectory of TOR_SEED_DIR that contains a "hostname" file is an
#   onion service directory.  The hostname file holds the .onion address for
#   that service.  Copying these ensures the .onion addresses are stable
#   across container restarts — without them Tor generates fresh keypairs and
#   the old .onion address becomes unreachable.
#
# Sentinel file:
#   ${TOR_DATA_DIR}/.seed_loaded — written after a successful bulk copy.
#   On subsequent starts the bulk copy is skipped (files are already in place)
#   but _verify_consensus_files() still runs to confirm the critical files
#   are present and non-empty.
# =============================================================================
preload_tor_data() {
    if [[ "${TOR_USE_SEED}" != "1" ]]; then
        log "Seed preload disabled (TOR_USE_SEED=${TOR_USE_SEED})"
        return
    fi

    if [[ ! -d "${TOR_SEED_DIR}" ]]; then
        log_warn "Seed directory not found: ${TOR_SEED_DIR} — will bootstrap from scratch (slow)"
        return
    fi

    ensure_dir "${TOR_DATA_DIR}" "${TOR_USER}"
    chmod 700 "${TOR_DATA_DIR}"

    # ── Sentinel: skip bulk copy on subsequent container starts ──────────────
    local sentinel="${TOR_DATA_DIR}/.seed_loaded"
    if [[ -f "${sentinel}" ]]; then
        log "Seed previously loaded — verifying critical consensus files"
        _verify_consensus_files
        return
    fi

    # ── Named consensus / cert files Tor reads at startup ────────────────────
    # Listed in order of importance: missing cached-certs alone prevents
    # the daemon from validating the consensus at all.
    local -a consensus_files=(
        cached-certs
        cached-consensus
        cached-microdesc-consensus
        cached-microdescs
        cached-microdescs.new
        cached-descriptors
        cached-extrainfo
        state
    )

    local found_count=0
    local -a missing_files=()
    for f in "${consensus_files[@]}"; do
        if [[ -f "${TOR_SEED_DIR}/${f}" ]]; then
            (( found_count++ ))
        else
            missing_files+=("${f}")
        fi
    done

    if (( found_count == 0 )); then
        log_warn "Seed dir exists but contains no recognisable Tor cache files — skipping"
        return
    fi

    log "Preloading Tor consensus/cert data: ${TOR_SEED_DIR} → ${TOR_DATA_DIR}"
    log "  Found ${found_count} file(s); not in seed: ${missing_files[*]:-none}"

    # ── Copy each named file with size verification ───────────────────────────
    local loaded_count=0
    local -a failed_files=()

    for f in "${consensus_files[@]}"; do
        local src="${TOR_SEED_DIR}/${f}"
        local dst="${TOR_DATA_DIR}/${f}"

        if [[ -f "${src}" ]]; then
            local src_sz
            src_sz="$(file_size_bytes "${src}")"

            if (( src_sz == 0 )); then
                log_warn "  SKIP  ${f} — seed file is empty"
                continue
            fi

            # cp -p: preserve permissions + timestamps
            if cp -p "${src}" "${dst}"; then
                local dst_sz
                dst_sz="$(file_size_bytes "${dst}")"

                if (( dst_sz == src_sz )); then
                    log_debug "  OK    ${f} (${dst_sz} bytes)"
                    (( loaded_count++ ))
                else
                    log_warn "  FAIL  ${f} — size mismatch: src=${src_sz} dst=${dst_sz}"
                    failed_files+=("${f}")
                fi
            else
                log_warn "  FAIL  ${f} — cp returned non-zero"
                failed_files+=("${f}")
            fi
        fi
    done

    # ── Subdirectory walk: onion service dirs and any extra Tor data ──────────
    # Each subdirectory that contains a "hostname" file is an onion service.
    # The hostname file contains the stable .onion address for that service.
    # Copying these prevents Tor from regenerating keypairs (and therefore
    # changing the .onion address) on every restart.
    #
    # Uses bash globs only — find(1) is not available in distroless images.
    local onion_count=0

    for subdir in "${TOR_SEED_DIR}"/*/; do
        # Strip trailing slash; skip if not a real directory
        subdir="${subdir%/}"
        [[ -d "${subdir}" ]] || continue

        local hostname_file="${subdir}/hostname"
        if [[ -f "${hostname_file}" ]]; then
            local onion_addr
            onion_addr="$(tr -d '[:space:]' < "${hostname_file}" 2>/dev/null || true)"

            if [[ -n "${onion_addr}" ]]; then
                # Compute relative path and create matching dir under TOR_DATA_DIR
                local rel_path="${subdir#"${TOR_SEED_DIR}"/}"
                local dst_subdir="${TOR_DATA_DIR}/${rel_path}"

                ensure_dir "${dst_subdir}"

                # cp -a: archive mode — preserves permissions, timestamps,
                # symlinks, and recursively copies all files (keys included)
                if cp -a "${subdir}/." "${dst_subdir}/"; then
                    chown -R "${TOR_USER}:${TOR_USER}" "${dst_subdir}" 2>/dev/null || true
                    chmod 700 "${dst_subdir}"
                    log "  Onion service loaded: ${onion_addr}  →  ${dst_subdir}"
                    (( onion_count++ ))
                else
                    log_warn "  Failed to copy onion service dir: ${subdir}"
                fi
            else
                log_warn "  Found hostname file but it is empty: ${hostname_file}"
            fi
        fi
    done

    # ── Final ownership pass on the whole data directory ─────────────────────
    chown -R "${TOR_USER}:${TOR_USER}" "${TOR_DATA_DIR}" 2>/dev/null \
        || log_warn "chown -R on ${TOR_DATA_DIR} failed — Tor may be unable to write state"
    chmod 700 "${TOR_DATA_DIR}"

    # ── Write sentinel so we skip the bulk copy on next start ────────────────
    touch "${sentinel}"

    log "Seed preload complete: ${loaded_count} consensus/cert file(s), ${onion_count} onion service(s)"
    if (( ${#failed_files[@]} > 0 )); then
        log_warn "Files that failed to load: ${failed_files[*]}"
    fi

    # ── Verify the most critical files are present and non-empty ─────────────
    _verify_consensus_files
}

# Internal helper — confirms that the three files Tor absolutely must have to
# validate and use a consensus are present in TOR_DATA_DIR and non-empty.
# Logs warnings (not fatal) so the daemon can still attempt a network bootstrap.
_verify_consensus_files() {
    # cached-certs is the most critical: without it Tor cannot verify the
    # signatures on ANY consensus document and must re-fetch certs from DAs.
    local -a critical=(
        cached-certs
        cached-consensus
        cached-microdesc-consensus
    )

    local all_ok=1

    for f in "${critical[@]}"; do
        local path="${TOR_DATA_DIR}/${f}"
        if [[ ! -f "${path}" ]]; then
            log_warn "  MISSING: ${path} — bootstrap will fetch this from network"
            all_ok=0
        else
            local sz
            sz="$(file_size_bytes "${path}")"
            if (( sz == 0 )); then
                log_warn "  EMPTY:   ${path} — bootstrap will fetch this from network"
                all_ok=0
            else
                log_debug "  OK: ${f} (${sz} bytes)"
            fi
        fi
    done

    if (( all_ok == 1 )); then
        log "All critical consensus/cert files present — bootstrap should be fast"
    else
        log_warn "Some critical files are missing — bootstrap will fetch from network (slower)"
    fi
}

# =============================================================================
# Step 2 — Generate torrc
# =============================================================================
# Writes the torrc from environment variables on every container start.
# All settings match the documented Lucid Tor Proxy configuration.
# Dynamic sections (DNS, bridges, onion service) are appended conditionally.
# =============================================================================
write_torrc() {
    log "Writing torrc → ${TORRC}"
    ensure_dir "${TOR_CONFIG_DIR}"
    ensure_dir "${TOR_DATA_DIR}" "${TOR_USER}"
    ensure_dir "${TOR_LOG_DIR}"

    # Write atomically: build in a temp file then mv into place so a crash
    # mid-write never leaves a half-written torrc.
    local tmp_torrc="${TORRC}.tmp.$$"

    # ── Core configuration ────────────────────────────────────────────────────
    cat > "${tmp_torrc}" << EOF
# ── Generated by tor_entrypoint.sh v${SCRIPT_VERSION} ────────────────────────
# Regenerated on every container start.
# Edit your .env.* file and docker-compose.*.yml, not this file directly.

Log notice stdout
DataDirectory ${TOR_DATA_DIR}

SocksPort 0.0.0.0:${TOR_SOCKS_PORT}
SocksListenAddress 127.0.0.1:${TOR_SOCKS_PORT}

ControlPort 0.0.0.0:${TOR_CONTROL_PORT}
EOF

    # ── Optional: unix control socket (additive to TCP port) ─────────────────
    if [[ -n "${TOR_CONTROL_SOCKET}" ]]; then
        printf 'ControlSocket %s\n' "${TOR_CONTROL_SOCKET}" >> "${tmp_torrc}"
    fi

    # ── Cookie authentication ─────────────────────────────────────────────────
    if [[ "${TOR_COOKIE_AUTH}" == "1" ]]; then
        cat >> "${tmp_torrc}" << EOF

CookieAuthentication 1
CookieAuthFile ${TOR_COOKIE_FILE}
CookieAuthFileGroupReadable 1
EOF
    fi

    # ── Dynamic DNS configuration ─────────────────────────────────────────────
    # Enabled when TOR_DNS_PORT is set to a non-zero port number.
    # AutomapHostsOnResolve + AutomapHostsSuffixes enable .onion DNS resolution
    # through the Tor DNS port (needed for services that resolve .onion via DNS).
    if [[ "${TOR_DNS_PORT}" != "0" ]]; then
        cat >> "${tmp_torrc}" << EOF

# ── Dynamic DNS configuration ───────────────────────────────────────────────
DNSPort 0.0.0.0:${TOR_DNS_PORT}
AutomapHostsOnResolve 1
AutomapHostsSuffixes .onion,.exit
EOF
    fi

    # ── Transparent proxy port ────────────────────────────────────────────────
    if [[ "${TOR_TRANS_PORT}" != "0" ]]; then
        printf '\nTransPort %s\n' "${TOR_TRANS_PORT}" >> "${tmp_torrc}"
    fi

    # ── Hidden / onion service ────────────────────────────────────────────────
    # When TOR_ONION_SERVICE_ENABLED=1 the live directives are written.
    # Otherwise they are commented out to prevent parse errors from an
    # HiddenServiceDir that has no keys yet (foundation phase).
    if [[ "${TOR_ONION_SERVICE_ENABLED}" == "1" ]]; then
        ensure_dir "${TOR_ONION_SERVICE_DIR}" "${TOR_USER}"
        chmod 700 "${TOR_ONION_SERVICE_DIR}"

        cat >> "${tmp_torrc}" << EOF

# ── Onion / Hidden Service ───────────────────────────────────────────────────
HiddenServiceDir ${TOR_ONION_SERVICE_DIR}
HiddenServiceVersion 3
HiddenServicePort ${TOR_ONION_SERVICE_PORT} ${TOR_ONION_SERVICE_TARGET}
EOF
    else
        cat >> "${tmp_torrc}" << 'EOF'

# Hidden service is disabled during foundation phase to avoid parse errors and
# to rely on ephemeral onions created by the controller.
# Uncomment and adjust only when the upstream is ready and reachable.
#HiddenServiceDir /var/lib/tor/hidden_service
#HiddenServiceVersion 3
#HiddenServicePort 80 127.0.0.1:8081
EOF
    fi

    # ── Daemon / disk settings ────────────────────────────────────────────────
    cat >> "${tmp_torrc}" << 'EOF'

RunAsDaemon 0
AvoidDiskWrites 0

# Disable IPv6 if not needed (reduces connection complexity)
# Uncomment if you need IPv6 support
#SocksListenAddress [::1]:9050
EOF

    mv "${tmp_torrc}" "${TORRC}"
    chmod 644 "${TORRC}"

    # Dump the generated torrc to the log at debug level so it is inspectable
    # via `docker logs` without needing to exec into the container.
    if [[ "${TOR_DEBUG:-0}" == "1" ]]; then
        log_debug "Generated torrc:"
        while IFS= read -r line; do
            log_debug "  ${line}"
        done < "${TORRC}"
    fi

    log "torrc written (SocksPort=0.0.0.0:${TOR_SOCKS_PORT}, ControlPort=0.0.0.0:${TOR_CONTROL_PORT})"
}

# =============================================================================
# Step 3 — Bridge configuration  (appended to torrc)
# =============================================================================
configure_bridges() {
    if [[ "${TOR_USE_BRIDGES}" != "1" ]]; then
        return
    fi

    if [[ -z "${TOR_BRIDGES}" ]]; then
        log_warn "TOR_USE_BRIDGES=1 but TOR_BRIDGES is empty — skipping bridge config"
        return
    fi

    log "Configuring bridges"

    {
        printf '\n# ── Bridge configuration ────────────────────────────────────────────\n'
        printf 'UseBridges 1\n'
        if [[ -n "${TOR_PLUGGABLE_TRANSPORT}" ]]; then
            printf 'ClientTransportPlugin %s\n' "${TOR_PLUGGABLE_TRANSPORT}"
        fi
    } >> "${TORRC}"

    local bridge_count=0
    while IFS= read -r line; do
        # Skip blank lines and comments
        [[ -z "$line" || "$line" == \#* ]] && continue

        # Trim leading/trailing whitespace (pure bash — no sed/awk)
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"
        [[ -z "$line" ]] && continue

        # Ensure the mandatory "Bridge" keyword prefix is present
        if [[ "${line,,}" != bridge\ * ]]; then
            line="Bridge ${line}"
        fi

        printf '%s\n' "$line" >> "${TORRC}"
        (( bridge_count++ ))
    done <<< "${TOR_BRIDGES}"

    log "Added ${bridge_count} bridge line(s) to torrc"
}

# =============================================================================
# Step 4 — Start Tor daemon
# =============================================================================
start_tor() {
    log "Starting Tor daemon"

    # Pre-flight: validate torrc syntax before forking
    if ! tor --verify-config -f "${TORRC}" >/dev/null 2>&1; then
        log_error "torrc failed validation — Tor will not start:"
        tor --verify-config -f "${TORRC}" >&2 || true
        exit 1
    fi
    log_debug "torrc syntax OK"

    # Ensure parent directory of the cookie file exists before Tor starts.
    # In a distroless container Tor cannot create missing directories.
    local cookie_dir
    cookie_dir="$(dirname "${TOR_COOKIE_FILE}")"
    if [[ ! -d "${cookie_dir}" ]]; then
        log "Creating cookie parent directory: ${cookie_dir}"
        if mkdir -p "${cookie_dir}"; then
            chown "${TOR_USER}:${TOR_USER}" "${cookie_dir}" 2>/dev/null || true
            chmod 750 "${cookie_dir}" 2>/dev/null || true
        else
            log_warn "Could not create ${cookie_dir} — Tor may fail to write cookie"
        fi
    fi

    # Ensure the log file is writable before Tor opens it
    touch "${TOR_LOG_FILE}" 2>/dev/null || true

    # Fork Tor and record its PID
    tor -f "${TORRC}" &
    TOR_PID=$!
    log "Tor started — PID ${TOR_PID}"

    # Brief pause then confirm Tor didn't immediately crash
    sleep 2
    if ! kill -0 "${TOR_PID}" 2>/dev/null; then
        log_error "Tor exited immediately after start — last 30 lines of log:"
        tail -n 30 "${TOR_LOG_FILE}" >&2 2>/dev/null || true
        exit 1
    fi

    log_debug "Tor process confirmed alive"
}

# =============================================================================
# Step 5 — Wait for auth cookie
# =============================================================================
# The auth cookie is written by Tor AFTER it has bound its listeners.
# This function MUST be called after start_tor().
#
# Behaviour:
#   1. On the first poll, pre-creates TOR_COOKIE_FILE (touch + perms) so Tor
#      has a writable target in distroless environments where it cannot mkdir.
#   2. Every poll cycle scans all known candidate paths for a valid 32-byte
#      cookie — handles mismatches between TOR_COOKIE_FILE and where Tor
#      actually decided to write the file.
#   3. When the cookie is found at a non-canonical path it is copied to
#      TOR_COOKIE_FILE so every downstream step works from one known location.
#   4. Calls validate_cookie_file() (size + hex-length) before returning.
#   5. On timeout, dumps the size of every candidate path and the Tor log
#      so the failure is immediately diagnosable from `docker logs`.
# =============================================================================
wait_for_cookie() {
    if [[ "${TOR_COOKIE_AUTH}" != "1" ]]; then
        log_debug "Cookie auth disabled — skipping wait_for_cookie"
        return
    fi

    # All paths Tor might have used for the cookie, in priority order.
    local -a candidates=(
        "${TOR_COOKIE_FILE}"
        "${TOR_DATA_DIR}/control_auth_cookie"
        "${TOR_DATA_DIR}/tor_control_auth_cookie"
        "/var/lib/tor/control_auth_cookie"
        "/run/tor/control_auth_cookie"
        "/tmp/tor_control_auth_cookie"
    )

    # Deduplicate while preserving order (pure bash — no sort/uniq)
    local -a unique_candidates=()
    local seen=""
    for c in "${candidates[@]}"; do
        if [[ "${seen}" != *"|${c}|"* ]]; then
            unique_candidates+=("$c")
            seen+="|${c}|"
        fi
    done

    log "Waiting for Tor auth cookie (timeout: ${TOR_COOKIE_WAIT_TIMEOUT}s)"
    log_debug "Canonical cookie path : ${TOR_COOKIE_FILE}"
    log_debug "All candidate paths   : ${unique_candidates[*]}"

    local elapsed=0
    local interval=2
    local first_poll=1

    while (( elapsed < TOR_COOKIE_WAIT_TIMEOUT )); do

        # Always check first: bail immediately if Tor has died
        if ! kill -0 "${TOR_PID}" 2>/dev/null; then
            log_error "Tor process (PID ${TOR_PID}) died while waiting for auth cookie"
            log_error "Last 30 lines of ${TOR_LOG_FILE}:"
            tail -n 30 "${TOR_LOG_FILE}" >&2 2>/dev/null || true
            exit 1
        fi

        # On the first poll pre-create the cookie file so Tor can overwrite it.
        # In a distroless container Tor may fail to create a new file if the
        # parent directory has restrictive permissions.
        if (( first_poll == 1 )); then
            first_poll=0
            if [[ ! -f "${TOR_COOKIE_FILE}" ]]; then
                log_debug "Pre-creating cookie placeholder: ${TOR_COOKIE_FILE}"
                if touch "${TOR_COOKIE_FILE}" 2>/dev/null; then
                    chown "${TOR_USER}:${TOR_USER}" "${TOR_COOKIE_FILE}" 2>/dev/null || true
                    chmod 640 "${TOR_COOKIE_FILE}" 2>/dev/null || true
                else
                    log_warn "Could not pre-create cookie file — Tor must create it itself"
                fi
            fi
        fi

        # Scan every candidate path for a valid 32-byte cookie
        for candidate in "${unique_candidates[@]}"; do
            if [[ ! -f "${candidate}" ]]; then
                continue
            fi

            local sz
            sz="$(file_size_bytes "${candidate}")"

            if (( sz != COOKIE_SIZE )); then
                log_debug "Candidate ${candidate}: size=${sz} bytes (need ${COOKIE_SIZE}) — still writing"
                continue
            fi

            # Valid-size cookie found.  If it is not at the canonical path,
            # copy it there now so every subsequent step has one known location.
            if [[ "${candidate}" != "${TOR_COOKIE_FILE}" ]]; then
                log_warn "Cookie found at ${candidate} (expected ${TOR_COOKIE_FILE}) — copying to canonical path"
                local cookie_parent
                cookie_parent="$(dirname "${TOR_COOKIE_FILE}")"
                mkdir -p "${cookie_parent}" 2>/dev/null || true

                if cp "${candidate}" "${TOR_COOKIE_FILE}"; then
                    chmod 640 "${TOR_COOKIE_FILE}"
                    log "Cookie copied to canonical path: ${TOR_COOKIE_FILE}"
                else
                    log_error "Failed to copy cookie from ${candidate} to ${TOR_COOKIE_FILE}"
                    exit 1
                fi
            fi

            # Full binary-size + hex-length validation before returning.
            # validate_cookie_file() exits the container if either check fails.
            validate_cookie_file "${TOR_COOKIE_FILE}"
            log "Auth cookie ready — ${TOR_COOKIE_FILE} (${sz} bytes)"
            return
        done

        sleep "${interval}"
        (( elapsed += interval ))
    done

    # Timeout — print diagnostic for every candidate so the user can see
    # exactly what Tor did (or did not) write and where.
    log_error "Timed out after ${TOR_COOKIE_WAIT_TIMEOUT}s waiting for auth cookie"
    log_error "Diagnostic scan of all candidate paths:"
    for candidate in "${unique_candidates[@]}"; do
        if [[ -f "${candidate}" ]]; then
            local sz
            sz="$(file_size_bytes "${candidate}")"
            log_error "  EXISTS  ${candidate}  (${sz} bytes — need exactly ${COOKIE_SIZE})"
        else
            log_error "  MISSING ${candidate}"
        fi
    done
    log_error "Last 30 lines of Tor log:"
    tail -n 30 "${TOR_LOG_FILE}" >&2 2>/dev/null || true
    exit 1
}

# =============================================================================
# Step 6 — Distribute cookie to shared volume targets
# =============================================================================
# Gets the validated 32-byte binary auth cookie and distributes it to every
# path listed in TOR_COOKIE_TARGETS.
#
# Three-stage operation:
#   Stage 1 — Locate:     If TOR_COOKIE_FILE is missing or wrong size, search
#                         all known candidate paths and copy the found cookie to
#                         the canonical path before proceeding.
#   Stage 2 — Validate:   Full byte-count + hex-length check on the source.
#                         A corrupt source exits immediately — pushing garbage
#                         to shared volumes silently breaks every consumer.
#   Stage 3 — Distribute: Binary cp to each target; validate each written copy.
# =============================================================================
copy_cookie_to_shared() {
    if [[ "${TOR_COOKIE_AUTH}" != "1" ]]; then
        log_debug "Cookie auth disabled — skipping cookie distribution"
    else
        if [[ -z "${TOR_COOKIE_TARGETS}" ]]; then
            log_debug "TOR_COOKIE_TARGETS not set — no cookie distribution needed"
        else
            log "Distributing auth cookie to shared target(s)"

            # ── Stage 1: Locate the cookie ────────────────────────────────────
            # Check whether the canonical cookie file is valid.  If not, search
            # all known candidate paths.  This handles the case where Tor wrote
            # the cookie in a non-default location (e.g. distroless permission
            # mismatch causing Tor to fall back to /tmp).
            local cookie_sz
            cookie_sz="$(file_size_bytes "${TOR_COOKIE_FILE}")"

            if (( cookie_sz != COOKIE_SIZE )); then
                log_warn "Cookie not valid at ${TOR_COOKIE_FILE} (size=${cookie_sz}) — searching candidate paths"

                local -a search_paths=(
                    "${TOR_DATA_DIR}/control_auth_cookie"
                    "${TOR_DATA_DIR}/tor_control_auth_cookie"
                    "/var/lib/tor/control_auth_cookie"
                    "/run/tor/control_auth_cookie"
                    "/tmp/tor_control_auth_cookie"
                )

                local found_at=""
                for candidate in "${search_paths[@]}"; do
                    if [[ -f "${candidate}" ]]; then
                        local cand_sz
                        cand_sz="$(file_size_bytes "${candidate}")"
                        if (( cand_sz == COOKIE_SIZE )); then
                            found_at="${candidate}"
                            break
                        fi
                    fi
                done

                if [[ -z "${found_at}" ]]; then
                    log_error "copy_cookie_to_shared: no valid ${COOKIE_SIZE}-byte cookie found on any candidate path"
                    log_error "Searched: ${TOR_COOKIE_FILE} ${search_paths[*]}"
                    log_error "Distribution aborted — downstream services will have no auth cookie"
                    exit 1
                else
                    log "Found valid cookie at ${found_at} — installing to canonical path ${TOR_COOKIE_FILE}"
                    local cookie_parent
                    cookie_parent="$(dirname "${TOR_COOKIE_FILE}")"

                    if ! mkdir -p "${cookie_parent}" 2>/dev/null; then
                        log_error "Cannot create cookie parent directory: ${cookie_parent}"
                        exit 1
                    fi

                    if cp "${found_at}" "${TOR_COOKIE_FILE}"; then
                        chmod 640 "${TOR_COOKIE_FILE}"
                        chown "${TOR_USER}:${TOR_USER}" "${TOR_COOKIE_FILE}" 2>/dev/null || true
                        log "Cookie installed at canonical path: ${TOR_COOKIE_FILE}"
                    else
                        log_error "cp failed: ${found_at} → ${TOR_COOKIE_FILE}"
                        exit 1
                    fi
                fi
            fi

            # ── Stage 2: Validate the source cookie ───────────────────────────
            # validate_cookie_file() runs both the byte-count check (wc -c)
            # and the hex-length check (hex_encode_file).  It exits the
            # container on any failure — distributing a corrupt cookie to all
            # shared volumes would silently break every downstream consumer.
            validate_cookie_file "${TOR_COOKIE_FILE}"

            # ── Stage 3: Distribute to all targets ────────────────────────────
            local ok=0
            local fail=0

            # TOR_COOKIE_TARGETS is a colon-separated list of destination paths.
            local saved_ifs="$IFS"
            IFS=':'
            local -a targets_arr
            read -r -a targets_arr <<< "${TOR_COOKIE_TARGETS}"
            IFS="${saved_ifs}"

            for target in "${targets_arr[@]}"; do
                if [[ -z "${target}" ]]; then
                    continue
                fi

                local target_dir
                target_dir="$(dirname "${target}")"

                if ! mkdir -p "${target_dir}" 2>/dev/null; then
                    log_error "Cannot create parent directory for cookie target: ${target_dir}"
                    (( fail++ ))
                else
                    # Binary copy — preserves the exact 32 bytes Tor wrote.
                    # Never re-encode: the cookie is a binary file that must
                    # reach consumers byte-for-byte identical to the source.
                    if cp "${TOR_COOKIE_FILE}" "${target}"; then
                        chmod 640 "${target}"
                        chown "${TOR_USER}:${TOR_USER}" "${target}" 2>/dev/null || true

                        # Validate the written copy — a filesystem full condition
                        # or FUSE glitch can produce a silently truncated file
                        # that passes a simple existence check.
                        local target_sz
                        target_sz="$(file_size_bytes "${target}")"
                        local target_hex
                        target_hex="$(hex_encode_file "${target}")"
                        local target_hex_len="${#target_hex}"

                        if (( target_sz != COOKIE_SIZE || target_hex_len != COOKIE_HEX_LENGTH )); then
                            log_error "Cookie target validation FAILED: ${target}"
                            log_error "  size=${target_sz} bytes (need ${COOKIE_SIZE}), hex-length=${target_hex_len} (need ${COOKIE_HEX_LENGTH})"
                            (( fail++ ))
                        else
                            log "Cookie distributed and validated → ${target} (${target_sz}B / ${target_hex_len}-char hex)"
                            (( ok++ ))
                        fi
                    else
                        log_error "cp failed: ${TOR_COOKIE_FILE} → ${target}"
                        (( fail++ ))
                    fi
                fi
            done

            if (( ok > 0 )); then
                log "Cookie successfully distributed to ${ok} target(s)"
            fi

            if (( fail > 0 )); then
                log_error "${fail} cookie distribution(s) failed — affected downstream services will lack auth"
                exit 1
            fi
        fi
    fi
}

# =============================================================================
# Control port helper — pure bash /dev/tcp, no netcat/socat (distroless-safe)
# =============================================================================
# Opens a TCP connection to the control port, authenticates with the cookie,
# sends one command, reads the response, closes the socket.
# Prints the response on stdout; exits the container on any error.
_tor_ctl() {
    local cmd="$1"
    local cookie_hex=""

    if [[ "${TOR_COOKIE_AUTH}" == "1" ]]; then
        cookie_hex="$(hex_encode_file "${TOR_COOKIE_FILE}")"
        # validate_cookie_file() has already confirmed 32 bytes / 64 hex chars
        # before we reach here, but we guard again defensively — if something
        # replaced the cookie file between validation and this call we must not
        # send garbage to the control port.
        if (( ${#cookie_hex} != COOKIE_HEX_LENGTH )); then
            log_error "Control port auth ABORTED: cookie hex length=${#cookie_hex} (expected ${COOKIE_HEX_LENGTH}) — cookie replaced or corrupted since validation"
            exit 1
        fi
    fi

    {
        exec 3<>"/dev/tcp/127.0.0.1/${TOR_CONTROL_PORT}" || exit 1

        if [[ "${TOR_COOKIE_AUTH}" == "1" ]]; then
            printf 'AUTHENTICATE %s\r\n' "${cookie_hex}" >&3
        else
            printf 'AUTHENTICATE ""\r\n' >&3
        fi

        local auth_resp=""
        IFS= read -r -t 5 auth_resp <&3
        auth_resp="${auth_resp%$'\r'}"
        if [[ "${auth_resp}" != 250* ]]; then
            log_error "Control port auth failed: ${auth_resp}"
            exec 3>&-
            exit 1
        fi

        printf '%s\r\n' "${cmd}" >&3

        local line response=""
        while IFS= read -r -t 5 line <&3; do
            line="${line%$'\r'}"
            response+="${line}"$'\n'
            # Terminal response line: exactly 3 digits followed by a space
            [[ "$line" =~ ^[0-9]{3}[[:space:]] ]] && break
        done

        printf 'QUIT\r\n' >&3
        exec 3>&-

        printf '%s' "${response}"
    }
}

# =============================================================================
# Step 7 — Bootstrap monitoring
# =============================================================================
wait_for_bootstrap() {
    log "Waiting for Tor to reach 100%% bootstrap (timeout: ${TOR_BOOTSTRAP_TIMEOUT}s)"

    local elapsed=0
    local last_pct=-1

    while (( elapsed < TOR_BOOTSTRAP_TIMEOUT )); do

        if ! kill -0 "${TOR_PID}" 2>/dev/null; then
            log_error "Tor process died during bootstrap"
            tail -n 50 "${TOR_LOG_FILE}" >&2 2>/dev/null || true
            exit 1
        fi

        # ── Primary path: control port ─────────────────────────────────────
        local resp=""
        if resp="$(_tor_ctl "GETINFO status/bootstrap-phase" 2>/dev/null)"; then
            local pct=""
            [[ "$resp" =~ PROGRESS=([0-9]+) ]] && pct="${BASH_REMATCH[1]}"

            if [[ -n "$pct" ]] && (( pct != last_pct )); then
                local summary=""
                [[ "$resp" =~ SUMMARY=\"([^\"]+)\" ]] && summary="${BASH_REMATCH[1]}"
                log "Bootstrap: ${pct}%${summary:+ — ${summary}}"
                last_pct=$pct
            fi

            if [[ -n "$pct" ]] && (( pct >= 100 )); then
                log "Bootstrap complete!"
                return
            fi

        # ── Fallback: grep the log file ────────────────────────────────────
        elif [[ -f "${TOR_LOG_FILE}" ]] && command -v grep &>/dev/null; then
            local last_boot_line=""
            last_boot_line="$(grep -oE 'Bootstrapped [0-9]+%[^:]*:.*' \
                                  "${TOR_LOG_FILE}" 2>/dev/null \
                              | tail -1)" || true

            if [[ -n "$last_boot_line" ]]; then
                log_debug "Log: ${last_boot_line}"
                if [[ "$last_boot_line" =~ Bootstrapped\ 100% ]]; then
                    log "Bootstrap complete (detected from log)!"
                    return
                fi
            fi
        fi

        sleep "${TOR_BOOTSTRAP_POLL_INTERVAL}"
        (( elapsed += TOR_BOOTSTRAP_POLL_INTERVAL ))
    done

    log_error "Bootstrap timed out after ${TOR_BOOTSTRAP_TIMEOUT}s (last progress: ${last_pct}%)"
    if [[ -f "${TOR_LOG_FILE}" ]]; then
        log_error "Last 40 lines of Tor log:"
        tail -n 40 "${TOR_LOG_FILE}" >&2 2>/dev/null || true
    fi
    exit 1
}

# =============================================================================
# Step 8 — Onion service verification
# =============================================================================
verify_onion_service() {
    if [[ "${TOR_ONION_SERVICE_ENABLED}" != "1" ]]; then
        return
    fi

    local hostname_file="${TOR_ONION_SERVICE_DIR}/hostname"
    log "Waiting for onion service hostname file…"

    local elapsed=0
    local timeout=60

    while (( elapsed < timeout )); do
        if [[ -f "${hostname_file}" && -s "${hostname_file}" ]]; then
            local onion_addr
            onion_addr="$(tr -d '[:space:]' < "${hostname_file}" 2>/dev/null)"
            log "Onion service active: ${onion_addr}"
            return
        fi
        sleep 2
        (( elapsed += 2 ))
    done

    log_warn "Onion hostname not generated within ${timeout}s — service may still be starting"
}

# =============================================================================
# Step 9 — Background health monitor
# =============================================================================
_health_monitor() {
    log_debug "Health monitor started (interval: ${TOR_HEALTH_CHECK_INTERVAL}s)"
    while true; do
        sleep "${TOR_HEALTH_CHECK_INTERVAL}"
        if ! kill -0 "${TOR_PID}" 2>/dev/null; then
            log_error "Tor process (PID ${TOR_PID}) has died — exiting container"
            exit 1
        fi
        log_debug "Health check OK — Tor PID ${TOR_PID} alive"
    done
}

# =============================================================================
# Signal / cleanup handler
# =============================================================================
_cleanup() {
    local rc=$?
    log "Shutdown signal received (exit code: ${rc})"

    if [[ -n "${TOR_PID}" ]] && kill -0 "${TOR_PID}" 2>/dev/null; then
        log "Sending SIGTERM to Tor (PID ${TOR_PID})"
        kill -TERM "${TOR_PID}" 2>/dev/null || true

        local i=0
        while (( i < 10 )) && kill -0 "${TOR_PID}" 2>/dev/null; do
            sleep 1
            (( i++ ))
        done

        if kill -0 "${TOR_PID}" 2>/dev/null; then
            log_warn "Graceful shutdown timed out — sending SIGKILL"
            kill -KILL "${TOR_PID}" 2>/dev/null || true
        fi
    fi

    log "Entrypoint exit"
    exit "${rc}"
}

trap _cleanup SIGTERM SIGINT SIGQUIT EXIT

# =============================================================================
# Main
# =============================================================================
main() {
    log "tor_entrypoint.sh v${SCRIPT_VERSION} — starting up"
    log_debug "TOR_DATA_DIR=${TOR_DATA_DIR}"
    log_debug "TOR_COOKIE_FILE=${TOR_COOKIE_FILE}"
    log_debug "TOR_SOCKS_PORT=${TOR_SOCKS_PORT}"
    log_debug "TOR_CONTROL_PORT=${TOR_CONTROL_PORT}"
    log_debug "TOR_DNS_PORT=${TOR_DNS_PORT}"
    log_debug "TOR_USE_BRIDGES=${TOR_USE_BRIDGES}"
    log_debug "TOR_USE_SEED=${TOR_USE_SEED}"
    log_debug "TOR_ONION_SERVICE_ENABLED=${TOR_ONION_SERVICE_ENABLED}"

    # 1. Load cached consensus, certs, and onion service keys from seed volume.
    #    Without cached-certs Tor must fetch authority certificates from the
    #    network before it can validate the consensus — the root cause of cold-
    #    start bootstrap failures.
    preload_tor_data

    # 2. Build torrc from environment variables
    write_torrc

    # 3. Append bridge config to torrc (when TOR_USE_BRIDGES=1)
    configure_bridges

    # 4. Fork Tor daemon — MUST happen before any cookie operations
    start_tor

    # 5. Wait until Tor has written the auth cookie; search all known paths;
    #    pre-create the file on first poll so Tor can always overwrite it;
    #    full byte-count + hex-length validation before returning.
    wait_for_cookie

    # 6. Locate, validate, and binary-copy the cookie to every path in
    #    TOR_COOKIE_TARGETS so downstream services can authenticate.
    copy_cookie_to_shared

    # 7. Poll the control port until bootstrap reaches 100%
    wait_for_bootstrap

    # 8. If onion service configured, confirm hostname file appeared
    verify_onion_service

    # 9. Start background health monitor
    _health_monitor &

    log "Tor fully operational — container handing off to Tor process (PID ${TOR_PID})"

    # Keep the container alive; propagate Tor's exit code
    wait "${TOR_PID}"
    local tor_exit=$?
    log_warn "Tor process exited with code ${tor_exit}"
    exit "${tor_exit}"
}

main "$@"
