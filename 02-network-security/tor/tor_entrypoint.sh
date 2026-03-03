#!/usr/bin/env bash
# tor_entrypoint.sh — Tor Proxy Container Entrypoint v4.2.0
# Distroless busybox compatible.
# No return statements — all flow control is if/else/exit.
# All arithmetic increments use (( ++var )) || true to survive set -e.
set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_VERSION="4.2.0"
readonly COOKIE_SIZE=32
readonly COOKIE_HEX_LENGTH=64

# =============================================================================
# Logging
# =============================================================================
_log() {
    local level="$1"
    shift
    local ts
    ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || printf 'now')"
    printf '[%s] [%s] [tor-entrypoint] %s\n' "${ts}" "${level}" "$*" >&2
}

log()       { _log "INFO " "$@"; }
log_warn()  { _log "WARN " "$@"; }
log_error() { _log "ERROR" "$@"; }

log_debug() {
    if [[ "${TOR_DEBUG:-0}" == "1" ]]; then
        _log "DEBUG" "$@"
    fi
}

# =============================================================================
# Environment  (override via .env.* / docker-compose.*.yml)
# =============================================================================
TOR_DATA_DIR="${TOR_DATA_DIR:-/var/lib/tor}"
TOR_CONFIG_DIR="${TOR_CONFIG_DIR:-/etc/tor}"
TOR_LOG_DIR="${TOR_LOG_DIR:-/var/log/tor}"
TOR_LOG_FILE="${TOR_LOG_DIR}/tor.log"
TORRC="${TOR_CONFIG_DIR}/torrc"

TOR_SOCKS_PORT="${TOR_SOCKS_PORT:-9050}"
TOR_CONTROL_PORT="${TOR_CONTROL_PORT:-9051}"
TOR_CONTROL_SOCKET="${TOR_CONTROL_SOCKET:-}"
TOR_DNS_PORT="${TOR_DNS_PORT:-0}"
TOR_TRANS_PORT="${TOR_TRANS_PORT:-0}"

TOR_COOKIE_AUTH="${TOR_COOKIE_AUTH:-1}"
TOR_COOKIE_FILE="${TOR_COOKIE_FILE:-${TOR_DATA_DIR}/control_auth_cookie}"
TOR_COOKIE_TARGETS="${TOR_COOKIE_TARGETS:-}"
TOR_COOKIE_TMP="/tmp/tor_control_auth_cookie"

TOR_SEED_DIR="${TOR_SEED_DIR:-/seed/tor-data}"
TOR_USE_SEED="${TOR_USE_SEED:-1}"

TOR_USE_BRIDGES="${TOR_USE_BRIDGES:-0}"
TOR_BRIDGES="${TOR_BRIDGES:-}"
TOR_PLUGGABLE_TRANSPORT="${TOR_PLUGGABLE_TRANSPORT:-}"

TOR_ONION_SERVICE_ENABLED="${TOR_ONION_SERVICE_ENABLED:-0}"
TOR_ONION_SERVICE_DIR="${TOR_ONION_SERVICE_DIR:-${TOR_DATA_DIR}/onion_service}"
TOR_ONION_SERVICE_PORT="${TOR_ONION_SERVICE_PORT:-80}"
TOR_ONION_SERVICE_TARGET="${TOR_ONION_SERVICE_TARGET:-127.0.0.1:80}"

TOR_BOOTSTRAP_TIMEOUT="${TOR_BOOTSTRAP_TIMEOUT:-300}"
TOR_BOOTSTRAP_POLL_INTERVAL="${TOR_BOOTSTRAP_POLL_INTERVAL:-5}"
TOR_COOKIE_WAIT_TIMEOUT="${TOR_COOKIE_WAIT_TIMEOUT:-60}"
TOR_HEALTH_CHECK_INTERVAL="${TOR_HEALTH_CHECK_INTERVAL:-30}"

TOR_USER="${TOR_USER:-debian-tor}"
TOR_PID=""

# =============================================================================
# Utility helpers
# =============================================================================
ensure_dir() {
    local dir="$1"
    local owner="${2:-}"
    if [[ ! -d "${dir}" ]]; then
        mkdir -p "${dir}"
    fi
    if [[ -n "${owner}" ]]; then
        if ! chown "${owner}" "${dir}" 2>/dev/null; then
            log_warn "chown ${owner} ${dir} failed — continuing"
        fi
    fi
}

# File size via wc -c — stat(1) absent on minimal/distroless images.
file_size_bytes() {
    local f="$1"
    if [[ ! -f "${f}" ]]; then
        printf '0'
    else
        wc -c < "${f}" | tr -d '[:space:]'
    fi
}

# Binary file → lowercase hex string on stdout (no newline).
# Cascade: xxd (primary) → od → pure bash byte loop.
# xxd -p produces clean lowercase hex without spaces.
# od -An -tx1 is a reliable POSIX fallback.
# Pure bash fallback uses /proc/self/fd trick to avoid null-byte read issue.
hex_encode_file() {
    local file="$1"
    local result=""

    # Primary: xxd — binary-safe, produces clean lowercase hex
    if command -v xxd >/dev/null 2>&1; then
        if result="$(xxd -p "${file}" 2>/dev/null | tr -d '\n')" \
           && [[ -n "${result}" ]]; then
            printf '%s' "${result}"
            return 0
        fi
    fi

    # Secondary: od — binary-safe POSIX fallback
    if result="$(od -An -tx1 "${file}" 2>/dev/null | tr -d ' \n\t')" \
       && [[ -n "${result}" ]]; then
        printf '%s' "${result}"
        return 0
    fi

    # Tertiary: pure bash — uses python if available to handle null bytes safely.
    # The read -n 1 -d '' loop stops at the first null byte (\x00), which is
    # common in random 32-byte Tor cookies. Python handles arbitrary binary.
    if command -v python3 >/dev/null 2>&1; then
        result="$(python3 -c "
import sys
data = sys.stdin.buffer.read()
sys.stdout.write(data.hex())
" < "${file}" 2>/dev/null)" && [[ -n "${result}" ]] && {
            printf '%s' "${result}"
            return 0
        }
    fi

    # Last resort: pure bash byte loop.
    # WARNING: stops at first null byte — only reaches here if xxd, od, and
    # python3 are all absent, which should never happen in this image.
    log_warn "hex_encode_file: falling back to bash byte loop — null bytes in cookie will be misread"
    local hex_out=""
    local char=""
    local ordval=0
    local LC_ALL=C
    while IFS= read -r -d $'\001' -n 1 char; do
        printf -v ordval '%d' "'${char}" 2>/dev/null || ordval=0
        printf -v hex_out '%s%02x' "${hex_out}" "${ordval}"
    done < "${file}"
    printf '%s' "${hex_out}"
}

# Validates a Tor auth cookie: existence, byte count (32), hex length (64).
# Exits the container on any failure — a bad cookie means zero connectivity.
validate_cookie_file() {
    local cookie_path="$1"

    if [[ ! -f "${cookie_path}" ]]; then
        log_error "Cookie INVALID — file missing: ${cookie_path}"
        exit 1
    fi

    local byte_count
    byte_count="$(wc -c < "${cookie_path}" | tr -d '[:space:]')"

    if [[ -z "${byte_count}" ]]; then
        log_error "Cookie INVALID — cannot read size: ${cookie_path}"
        exit 1
    fi

    if (( byte_count != COOKIE_SIZE )); then
        log_error "Cookie INVALID — size=${byte_count}B expected=${COOKIE_SIZE}B: ${cookie_path}"
        exit 1
    fi

    local hex_str
    hex_str="$(hex_encode_file "${cookie_path}")"
    local hex_len="${#hex_str}"

    if (( hex_len != COOKIE_HEX_LENGTH )); then
        log_error "Cookie INVALID — hex_len=${hex_len} expected=${COOKIE_HEX_LENGTH}: ${cookie_path}"
        exit 1
    fi

    log "Cookie validated: ${cookie_path} — ${byte_count}B / ${hex_len}-char hex — OK"
}

# =============================================================================
# Step 1 — Preload seed / consensus / cert / onion data
# =============================================================================
preload_tor_data() {
    if [[ "${TOR_USE_SEED}" != "1" ]]; then
        log "Seed preload disabled (TOR_USE_SEED=${TOR_USE_SEED})"
        return 0
    fi

    if [[ ! -d "${TOR_SEED_DIR}" ]]; then
        log_warn "Seed dir not found: ${TOR_SEED_DIR} — cold bootstrap (will be slow)"
        return 0
    fi

    ensure_dir "${TOR_DATA_DIR}" "${TOR_USER}"
    chmod 700 "${TOR_DATA_DIR}"

    local sentinel="${TOR_DATA_DIR}/.seed_loaded"

    if [[ -f "${sentinel}" ]]; then
        log "Seed previously loaded — verifying critical consensus files"
        _verify_consensus_files
        return 0
    fi

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
    local f
    for f in "${consensus_files[@]}"; do
        if [[ -f "${TOR_SEED_DIR}/${f}" ]]; then
            (( ++found_count )) || true
        fi
    done

    if (( found_count == 0 )); then
        log_warn "Seed dir has no recognisable Tor cache files — skipping preload"
        return 0
    fi

    log "Preloading ${found_count} cache file(s): ${TOR_SEED_DIR} → ${TOR_DATA_DIR}"

    local loaded_count=0

    for f in "${consensus_files[@]}"; do
        local src="${TOR_SEED_DIR}/${f}"
        local dst="${TOR_DATA_DIR}/${f}"

        if [[ -f "${src}" ]]; then
            local src_sz
            src_sz="$(file_size_bytes "${src}")"

            if (( src_sz == 0 )); then
                log_warn "  SKIP ${f} — seed file is empty"
            elif cp -p "${src}" "${dst}"; then
                local dst_sz
                dst_sz="$(file_size_bytes "${dst}")"
                if (( dst_sz == src_sz )); then
                    log "  OK   ${f} (${dst_sz}B)"
                    (( ++loaded_count )) || true
                else
                    log_warn "  FAIL ${f} — size mismatch src=${src_sz}B dst=${dst_sz}B"
                fi
            else
                log_warn "  FAIL ${f} — cp returned non-zero"
            fi
        fi
    done

    local onion_count=0
    local subdir

    for subdir in "${TOR_SEED_DIR}"/*/; do
        subdir="${subdir%/}"
        if [[ -d "${subdir}" && -f "${subdir}/hostname" ]]; then
            local onion_addr
            onion_addr="$(tr -d '[:space:]' < "${subdir}/hostname" 2>/dev/null || printf '')"
            if [[ -n "${onion_addr}" ]]; then
                local rel_path="${subdir#"${TOR_SEED_DIR}"/}"
                local dst_subdir="${TOR_DATA_DIR}/${rel_path}"
                ensure_dir "${dst_subdir}"
                if cp -a "${subdir}/." "${dst_subdir}/"; then
                    chown -R "${TOR_USER}:${TOR_USER}" "${dst_subdir}" 2>/dev/null || true
                    chmod 700 "${dst_subdir}"
                    log "  Onion ${onion_addr} → ${dst_subdir}"
                    (( ++onion_count )) || true
                else
                    log_warn "  Failed to copy onion dir: ${subdir}"
                fi
            else
                log_warn "  Onion hostname file is empty: ${subdir}/hostname"
            fi
        fi
    done

    if ! chown -R "${TOR_USER}:${TOR_USER}" "${TOR_DATA_DIR}" 2>/dev/null; then
        log_warn "chown -R ${TOR_DATA_DIR} failed — Tor may be unable to write state"
    fi
    chmod 700 "${TOR_DATA_DIR}"

    touch "${sentinel}"
    log "Seed preload complete: ${loaded_count} consensus/cert file(s), ${onion_count} onion service(s)"
    _verify_consensus_files
}

_verify_consensus_files() {
    local -a critical=(
        cached-certs
        cached-consensus
        cached-microdesc-consensus
    )
    local all_ok=1
    local f

    for f in "${critical[@]}"; do
        local path="${TOR_DATA_DIR}/${f}"
        if [[ ! -f "${path}" ]]; then
            log_warn "  MISSING: ${f} — bootstrap will fetch from network"
            all_ok=0
        else
            local sz
            sz="$(file_size_bytes "${path}")"
            if (( sz == 0 )); then
                log_warn "  EMPTY:   ${f} — bootstrap will fetch from network"
                all_ok=0
            else
                log "  OK: ${f} (${sz}B)"
            fi
        fi
    done

    if (( all_ok == 1 )); then
        log "All critical consensus/cert files present — fast bootstrap expected"
    else
        log_warn "Some consensus/cert files missing — bootstrap will fetch from network (slower)"
    fi
}

# =============================================================================
# Step 2 — Write torrc
# =============================================================================
write_torrc() {
    log "Writing torrc → ${TORRC}"
    ensure_dir "${TOR_CONFIG_DIR}"
    ensure_dir "${TOR_DATA_DIR}" "${TOR_USER}"
    # FIX: pass TOR_USER so Tor can write its log file
    ensure_dir "${TOR_LOG_DIR}" "${TOR_USER}"
    chmod 755 "${TOR_LOG_DIR}" 2>/dev/null || true

    local tmp_torrc="${TORRC}.tmp.$$"

    # FIX: use ${TOR_DATA_DIR}, ${TOR_SOCKS_PORT}, ${TOR_CONTROL_PORT} variables.
    # FIX: removed SocksListenAddress — deprecated and removed in Tor >= 0.4.x,
    #      causes immediate startup failure.
    # FIX: Log to both stdout (for docker logs) and file (for tail -n diagnostics).
    cat > "${tmp_torrc}" << TORRC_END
# Generated by tor_entrypoint.sh v${SCRIPT_VERSION} — do not edit directly.
# Regenerated on every container start from environment variables.
Log notice stdout
Log notice file ${TOR_LOG_FILE}
DataDirectory ${TOR_DATA_DIR}

SocksPort 0.0.0.0:${TOR_SOCKS_PORT}
ControlPort 0.0.0.0:${TOR_CONTROL_PORT}
TORRC_END

    if [[ -n "${TOR_CONTROL_SOCKET}" ]]; then
        printf 'ControlSocket %s\n' "${TOR_CONTROL_SOCKET}" >> "${tmp_torrc}"
    fi

    if [[ "${TOR_COOKIE_AUTH}" == "1" ]]; then
        cat >> "${tmp_torrc}" << COOKIE_END

CookieAuthentication 1
CookieAuthFile ${TOR_DATA_DIR}/control_auth_cookie
CookieAuthFileGroupReadable 1
COOKIE_END
    fi

    # FIX: use ${TOR_DNS_PORT} — was hardcoded to 9053
    if [[ "${TOR_DNS_PORT}" != "0" ]]; then
        cat >> "${tmp_torrc}" << DNS_END

DNSPort 0.0.0.0:${TOR_DNS_PORT}
AutomapHostsOnResolve 1
AutomapHostsSuffixes .onion,.exit
DNS_END
    fi

    if [[ "${TOR_TRANS_PORT}" != "0" ]]; then
        printf '\nTransPort %s\n' "${TOR_TRANS_PORT}" >> "${tmp_torrc}"
    fi

    # FIX: removed single-quotes from << 'ONION_END' so variables expand correctly.
    # TOR_ONION_SERVICE_PORT and TOR_ONION_SERVICE_TARGET were silently substituted
    # as literal strings with the quoted heredoc delimiter.
    if [[ "${TOR_ONION_SERVICE_ENABLED}" == "1" ]]; then
        ensure_dir "${TOR_ONION_SERVICE_DIR}" "${TOR_USER}"
        chmod 700 "${TOR_ONION_SERVICE_DIR}"
        cat >> "${tmp_torrc}" << ONION_END

HiddenServiceDir ${TOR_ONION_SERVICE_DIR}
HiddenServiceVersion 3
HiddenServicePort ${TOR_ONION_SERVICE_PORT} ${TOR_ONION_SERVICE_TARGET}
ONION_END
    else
        cat >> "${tmp_torrc}" << ONION_DISABLED

# Hidden service disabled (foundation phase).
# Set TOR_ONION_SERVICE_ENABLED=1 when the upstream is ready.
#HiddenServiceDir ${TOR_DATA_DIR}/hidden_service
#HiddenServiceVersion 3
#HiddenServicePort 80 127.0.0.1:8081
ONION_DISABLED
    fi

    cat >> "${tmp_torrc}" << RUN_END

RunAsDaemon 0
AvoidDiskWrites 0

# Uncomment for IPv6 SOCKS support
#SocksPort [::1]:${TOR_SOCKS_PORT}
RUN_END

    mv "${tmp_torrc}" "${TORRC}"
    chmod 644 "${TORRC}"

    if [[ "${TOR_DEBUG:-0}" == "1" ]]; then
        log_debug "Generated torrc contents:"
        while IFS= read -r line; do
            log_debug "  ${line}"
        done < "${TORRC}"
    fi

    log "torrc written — SocksPort=0.0.0.0:${TOR_SOCKS_PORT} ControlPort=0.0.0.0:${TOR_CONTROL_PORT}"
}

# =============================================================================
# Step 3 — Bridge configuration  (appended to torrc)
# =============================================================================
configure_bridges() {
    if [[ "${TOR_USE_BRIDGES}" != "1" ]]; then
        log_debug "Bridges disabled (TOR_USE_BRIDGES=${TOR_USE_BRIDGES})"
        return 0
    fi

    if [[ -z "${TOR_BRIDGES}" ]]; then
        log_warn "TOR_USE_BRIDGES=1 but TOR_BRIDGES is empty — skipping bridge config"
        return 0
    fi

    log "Configuring bridges"

    {
        printf '\nUseBridges 1\n'
        if [[ -n "${TOR_PLUGGABLE_TRANSPORT}" ]]; then
            printf 'ClientTransportPlugin %s\n' "${TOR_PLUGGABLE_TRANSPORT}"
        fi
    } >> "${TORRC}"

    local bridge_count=0
    while IFS= read -r line; do
        if [[ -n "${line}" && "${line}" != \#* ]]; then
            line="${line#"${line%%[![:space:]]*}"}"
            line="${line%"${line##*[![:space:]]}"}"
            if [[ -n "${line}" ]]; then
                if [[ "${line,,}" != bridge\ * ]]; then
                    line="Bridge ${line}"
                fi
                printf '%s\n' "${line}" >> "${TORRC}"
                (( ++bridge_count )) || true
            fi
        fi
    done <<< "${TOR_BRIDGES}"

    log "Added ${bridge_count} bridge line(s) to torrc"
}

# =============================================================================
# Step 4 — Start Tor daemon
# =============================================================================
start_tor() {
    log "Starting Tor daemon"

    if ! tor --verify-config -f "${TORRC}" >/dev/null 2>&1; then
        log_error "torrc validation failed — Tor will not start:"
        tor --verify-config -f "${TORRC}" >&2 || true
        exit 1
    fi
    log_debug "torrc syntax OK"

    local cookie_dir
    cookie_dir="$(dirname "${TOR_COOKIE_FILE}")"
    if [[ ! -d "${cookie_dir}" ]]; then
        if mkdir -p "${cookie_dir}"; then
            chown "${TOR_USER}:${TOR_USER}" "${cookie_dir}" 2>/dev/null || true
            chmod 750 "${cookie_dir}" 2>/dev/null || true
        else
            log_warn "Cannot create cookie dir: ${cookie_dir} — Tor may fail to write cookie"
        fi
    fi

    if [[ ! -d /tmp ]]; then
        mkdir -p /tmp
        log_debug "Created /tmp"
    fi

    # Ensure log file exists and is writable before Tor starts
    touch "${TOR_LOG_FILE}" 2>/dev/null || true
    chown "${TOR_USER}:${TOR_USER}" "${TOR_LOG_FILE}" 2>/dev/null || true

    tor -f "${TORRC}" &
    TOR_PID=$!
    log "Tor forked — PID ${TOR_PID}"

    local i=0
    while (( i < 5 )); do
        sleep 2
        (( ++i )) || true
        if ! kill -0 "${TOR_PID}" 2>/dev/null; then
            log_error "Tor exited immediately after start — last 30 lines of log:"
            tail -n 30 "${TOR_LOG_FILE}" >&2 2>/dev/null || true
            exit 1
        fi
        log_debug "Start check ${i}/5 — PID ${TOR_PID} alive"
    done

    log "Tor process confirmed running (PID ${TOR_PID})"
}

# =============================================================================
# Step 5 — Wait for auth cookie
# =============================================================================
wait_for_cookie() {
    if [[ "${TOR_COOKIE_AUTH}" != "1" ]]; then
        log_debug "Cookie auth disabled — skipping wait_for_cookie"
        return 0
    fi

    local -a candidates=(
        "${TOR_COOKIE_FILE}"
        "${TOR_DATA_DIR}/control_auth_cookie"
        "${TOR_DATA_DIR}/tor_control_auth_cookie"
        "/var/lib/tor/control_auth_cookie"
        "/run/tor/control_auth_cookie"
        "${TOR_COOKIE_TMP}"
    )

    local -a unique_candidates=()
    local seen=""
    local c
    for c in "${candidates[@]}"; do
        if [[ "${seen}" != *"|${c}|"* ]]; then
            unique_candidates+=("${c}")
            seen+="|${c}|"
        fi
    done

    log "Waiting for auth cookie (timeout: ${TOR_COOKIE_WAIT_TIMEOUT}s)"
    log_debug "Canonical path : ${TOR_COOKIE_FILE}"
    log_debug "All candidates : ${unique_candidates[*]}"

    local elapsed=0
    local interval=2
    local first_poll=1
    local cookie_ready=0

    while (( elapsed < TOR_COOKIE_WAIT_TIMEOUT )) && (( cookie_ready == 0 )); do

        if ! kill -0 "${TOR_PID}" 2>/dev/null; then
            log_error "Tor (PID ${TOR_PID}) died while waiting for auth cookie"
            tail -n 30 "${TOR_LOG_FILE}" >&2 2>/dev/null || true
            exit 1
        fi

        if (( first_poll == 1 )); then
            first_poll=0
            if [[ ! -f "${TOR_COOKIE_FILE}" ]]; then
                if touch "${TOR_COOKIE_FILE}" 2>/dev/null; then
                    chown "${TOR_USER}:${TOR_USER}" "${TOR_COOKIE_FILE}" 2>/dev/null || true
                    chmod 640 "${TOR_COOKIE_FILE}" 2>/dev/null || true
                    log_debug "Pre-created cookie placeholder: ${TOR_COOKIE_FILE}"
                else
                    log_warn "Cannot pre-create cookie placeholder — Tor must create it itself"
                fi
            fi
        fi

        local candidate
        for candidate in "${unique_candidates[@]}"; do
            if [[ -f "${candidate}" ]]; then
                local sz
                sz="$(file_size_bytes "${candidate}")"
                if (( sz == COOKIE_SIZE )); then
                    if [[ "${candidate}" != "${TOR_COOKIE_FILE}" ]]; then
                        log_warn "Cookie found at ${candidate} — copying to canonical path ${TOR_COOKIE_FILE}"
                        local cookie_parent
                        cookie_parent="$(dirname "${TOR_COOKIE_FILE}")"
                        mkdir -p "${cookie_parent}" 2>/dev/null || true
                        if cp "${candidate}" "${TOR_COOKIE_FILE}"; then
                            chmod 640 "${TOR_COOKIE_FILE}"
                            chown "${TOR_USER}:${TOR_USER}" "${TOR_COOKIE_FILE}" 2>/dev/null || true
                            log "Cookie installed at canonical path"
                        else
                            log_error "cp failed: ${candidate} → ${TOR_COOKIE_FILE}"
                            exit 1
                        fi
                    fi
                    cookie_ready=1
                    break
                else
                    log_debug "Candidate ${candidate}: ${sz}B (need ${COOKIE_SIZE}) — still writing"
                fi
            fi
        done

        if (( cookie_ready == 0 )); then
            sleep "${interval}"
            (( elapsed += interval )) || true
        fi
    done

    if (( cookie_ready == 0 )); then
        log_error "Timed out after ${TOR_COOKIE_WAIT_TIMEOUT}s — no valid ${COOKIE_SIZE}B cookie found"
        local candidate
        for candidate in "${unique_candidates[@]}"; do
            if [[ -f "${candidate}" ]]; then
                local sz
                sz="$(file_size_bytes "${candidate}")"
                log_error "  EXISTS  ${candidate} (${sz}B — need ${COOKIE_SIZE})"
            else
                log_error "  MISSING ${candidate}"
            fi
        done
        log_error "Last 30 lines of Tor log:"
        tail -n 30 "${TOR_LOG_FILE}" >&2 2>/dev/null || true
        exit 1
    fi

    validate_cookie_file "${TOR_COOKIE_FILE}"

    if cp "${TOR_COOKIE_FILE}" "${TOR_COOKIE_TMP}" 2>/dev/null; then
        chmod 640 "${TOR_COOKIE_TMP}" 2>/dev/null || true
        log_debug "Cookie backup written: ${TOR_COOKIE_TMP}"
    else
        log_warn "Could not write /tmp cookie backup — continuing without it"
    fi

    log "Auth cookie ready — ${TOR_COOKIE_FILE}"
}

# =============================================================================
# Step 6 — Distribute cookie to shared volume targets
# =============================================================================
copy_cookie_to_shared() {
    if [[ "${TOR_COOKIE_AUTH}" != "1" ]]; then
        log_debug "Cookie auth disabled — skipping distribution"
        return 0
    fi

    if [[ -z "${TOR_COOKIE_TARGETS}" ]]; then
        log_debug "TOR_COOKIE_TARGETS not set — no distribution required"
        return 0
    fi

    log "Distributing auth cookie to shared target(s)"

    local cookie_sz
    cookie_sz="$(file_size_bytes "${TOR_COOKIE_FILE}")"

    if (( cookie_sz != COOKIE_SIZE )); then
        log_warn "Canonical cookie invalid (${cookie_sz}B) — searching candidate paths"

        local -a search_paths=(
            "${TOR_DATA_DIR}/control_auth_cookie"
            "${TOR_DATA_DIR}/tor_control_auth_cookie"
            "/var/lib/tor/control_auth_cookie"
            "/run/tor/control_auth_cookie"
            "${TOR_COOKIE_TMP}"
        )

        local found_at=""
        local candidate
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
            log_error "No valid ${COOKIE_SIZE}B cookie found on any candidate path — aborting distribution"
            exit 1
        fi

        log "Valid cookie at ${found_at} — installing to canonical path ${TOR_COOKIE_FILE}"
        local cookie_parent
        cookie_parent="$(dirname "${TOR_COOKIE_FILE}")"
        if mkdir -p "${cookie_parent}" 2>/dev/null; then
            if cp "${found_at}" "${TOR_COOKIE_FILE}"; then
                chmod 640 "${TOR_COOKIE_FILE}"
                chown "${TOR_USER}:${TOR_USER}" "${TOR_COOKIE_FILE}" 2>/dev/null || true
                log "Cookie installed at canonical path: ${TOR_COOKIE_FILE}"
            else
                log_error "cp failed: ${found_at} → ${TOR_COOKIE_FILE}"
                exit 1
            fi
        else
            log_error "Cannot create cookie parent dir: ${cookie_parent}"
            exit 1
        fi
    fi

    validate_cookie_file "${TOR_COOKIE_FILE}"

    local ok=0
    local fail=0

    local saved_ifs="${IFS}"
    IFS=':'
    local -a targets_arr
    read -r -a targets_arr <<< "${TOR_COOKIE_TARGETS}"
    IFS="${saved_ifs}"

    local target
    for target in "${targets_arr[@]}"; do
        if [[ -n "${target}" ]]; then
            local target_dir
            target_dir="$(dirname "${target}")"
            if mkdir -p "${target_dir}" 2>/dev/null; then
                if cp "${TOR_COOKIE_FILE}" "${target}"; then
                    chmod 640 "${target}"
                    chown "${TOR_USER}:${TOR_USER}" "${target}" 2>/dev/null || true

                    local target_sz
                    target_sz="$(file_size_bytes "${target}")"
                    local target_hex
                    target_hex="$(hex_encode_file "${target}")"
                    local target_hex_len="${#target_hex}"

                    if (( target_sz != COOKIE_SIZE || target_hex_len != COOKIE_HEX_LENGTH )); then
                        log_error "Target validation FAILED: ${target} (${target_sz}B / ${target_hex_len}-char hex)"
                        (( ++fail )) || true
                    else
                        log "Cookie distributed → ${target} (${target_sz}B / ${target_hex_len}-char hex)"
                        (( ++ok )) || true
                    fi
                else
                    log_error "cp failed: ${TOR_COOKIE_FILE} → ${target}"
                    (( ++fail )) || true
                fi
            else
                log_error "Cannot create target dir: ${target_dir}"
                (( ++fail )) || true
            fi
        fi
    done

    if (( ok > 0 )); then
        log "Cookie successfully distributed to ${ok} target(s)"
    fi

    if (( fail > 0 )); then
        log_error "${fail} cookie distribution(s) failed — exit"
        exit 1
    fi
}

# =============================================================================
# Control port helper — pure bash /dev/tcp (no netcat/socat required)
# =============================================================================
_tor_ctl() {
    local cmd="$1"
    local cookie_hex=""

    if [[ "${TOR_COOKIE_AUTH}" == "1" ]]; then
        cookie_hex="$(hex_encode_file "${TOR_COOKIE_FILE}")"
        if (( ${#cookie_hex} != COOKIE_HEX_LENGTH )); then
            log_error "_tor_ctl: cookie hex length=${#cookie_hex} (need ${COOKIE_HEX_LENGTH}) — aborting"
            exit 1
        fi
    fi

    # FIX: exec 3<> with set -e can fire before || is evaluated in some bash versions.
    # Use set +e / set -e guard around the exec to make failure handling reliable.
    local fd_ok=0
    set +e
    exec 3<>"/dev/tcp/127.0.0.1/${TOR_CONTROL_PORT}" 2>/dev/null
    fd_ok=$?
    set -e

    if (( fd_ok != 0 )); then
        log_error "_tor_ctl: cannot connect to control port ${TOR_CONTROL_PORT}"
        exit 1
    fi

    if [[ "${TOR_COOKIE_AUTH}" == "1" ]]; then
        printf 'AUTHENTICATE %s\r\n' "${cookie_hex}" >&3
    else
        printf 'AUTHENTICATE ""\r\n' >&3
    fi

    local auth_resp=""
    IFS= read -r -t 5 auth_resp <&3
    auth_resp="${auth_resp%$'\r'}"

    if [[ "${auth_resp}" != 250* ]]; then
        log_error "_tor_ctl: AUTHENTICATE rejected: ${auth_resp}"
        exec 3>&-
        exit 1
    fi

    printf '%s\r\n' "${cmd}" >&3

    local line=""
    local response=""
    while IFS= read -r -t 5 line <&3; do
        line="${line%$'\r'}"
        response+="${line}"$'\n'
        if [[ "${line}" =~ ^[0-9]{3}[[:space:]] ]]; then
            break
        fi
    done

    printf 'QUIT\r\n' >&3
    exec 3>&-

    printf '%s' "${response}"
}

# =============================================================================
# Step 7 — Bootstrap monitoring
# =============================================================================
wait_for_bootstrap() {
    log "Waiting for 100%% bootstrap (timeout: ${TOR_BOOTSTRAP_TIMEOUT}s)"

    local elapsed=0
    local last_pct=-1
    local bootstrapped=0

    while (( elapsed < TOR_BOOTSTRAP_TIMEOUT )) && (( bootstrapped == 0 )); do

        if ! kill -0 "${TOR_PID}" 2>/dev/null; then
            log_error "Tor process died during bootstrap"
            tail -n 50 "${TOR_LOG_FILE}" >&2 2>/dev/null || true
            exit 1
        fi

        local resp=""
        # _tor_ctl runs in a subshell here; if it exits non-zero (control port not
        # yet up) the if-condition absorbs it and we fall through to log fallback.
        if resp="$(_tor_ctl "GETINFO status/bootstrap-phase" 2>/dev/null)"; then
            local pct=""
            if [[ "${resp}" =~ PROGRESS=([0-9]+) ]]; then
                pct="${BASH_REMATCH[1]}"
            fi

            if [[ -n "${pct}" ]] && (( pct != last_pct )); then
                local summary=""
                if [[ "${resp}" =~ SUMMARY=\"([^\"]+)\" ]]; then
                    summary="${BASH_REMATCH[1]}"
                fi
                log "Bootstrap: ${pct}%${summary:+ — ${summary}}"
                last_pct="${pct}"
            fi

            if [[ -n "${pct}" ]] && (( pct >= 100 )); then
                bootstrapped=1
            fi
        else
            # Control port not yet ready — fall back to log file scanning
            if [[ -f "${TOR_LOG_FILE}" ]]; then
                local last_boot_line=""
                last_boot_line="$(grep -oE 'Bootstrapped [0-9]+%[^:]*:.*' \
                    "${TOR_LOG_FILE}" 2>/dev/null \
                    | tail -1)" || true

                if [[ -n "${last_boot_line}" ]]; then
                    log_debug "Log fallback: ${last_boot_line}"
                    if [[ "${last_boot_line}" =~ Bootstrapped\ 100% ]]; then
                        bootstrapped=1
                    fi
                fi
            fi
        fi

        if (( bootstrapped == 0 )); then
            sleep "${TOR_BOOTSTRAP_POLL_INTERVAL}"
            (( elapsed += TOR_BOOTSTRAP_POLL_INTERVAL )) || true
        fi
    done

    if (( bootstrapped == 0 )); then
        log_error "Bootstrap timed out after ${TOR_BOOTSTRAP_TIMEOUT}s (last progress: ${last_pct}%)"
        if [[ -f "${TOR_LOG_FILE}" ]]; then
            log_error "Last 40 lines of Tor log:"
            tail -n 40 "${TOR_LOG_FILE}" >&2 2>/dev/null || true
        fi
        exit 1
    fi

    log "Bootstrap complete!"
}

# =============================================================================
# Step 8 — Onion service verification
# =============================================================================
verify_onion_service() {
    if [[ "${TOR_ONION_SERVICE_ENABLED}" != "1" ]]; then
        log_debug "Onion service disabled — skipping verification"
        return 0
    fi

    local hostname_file="${TOR_ONION_SERVICE_DIR}/hostname"
    log "Waiting for onion service hostname file"

    local elapsed=0
    local timeout=60
    local onion_found=0

    while (( elapsed < timeout )) && (( onion_found == 0 )); do
        if [[ -f "${hostname_file}" && -s "${hostname_file}" ]]; then
            local onion_addr
            onion_addr="$(tr -d '[:space:]' < "${hostname_file}" 2>/dev/null || printf '')"
            log "Onion service active: ${onion_addr}"
            onion_found=1
        else
            sleep 2
            (( elapsed += 2 )) || true
        fi
    done

    if (( onion_found == 0 )); then
        log_warn "Onion hostname not generated within ${timeout}s — service may still be starting"
    fi
}

# =============================================================================
# Step 9 — Background health monitor
# =============================================================================
_health_monitor() {
    log_debug "Health monitor started (interval: ${TOR_HEALTH_CHECK_INTERVAL}s)"
    while true; do
        sleep "${TOR_HEALTH_CHECK_INTERVAL}"
        if ! kill -0 "${TOR_PID}" 2>/dev/null; then
            log_error "Tor (PID ${TOR_PID}) has died — exiting container"
            exit 1
        fi
        log_debug "Health OK — Tor PID ${TOR_PID} alive"
    done
}

# =============================================================================
# Signal / cleanup handler
# =============================================================================
_cleanup() {
    local rc=$?

    # FIX: de-register all traps immediately to prevent _cleanup re-entering
    # itself when it calls exit "${rc}" at the end, which would otherwise
    # re-fire the EXIT trap and loop indefinitely.
    trap - EXIT SIGTERM SIGINT SIGQUIT

    log "Shutdown signal received (exit code: ${rc})"

    if [[ -n "${TOR_PID}" ]] && kill -0 "${TOR_PID}" 2>/dev/null; then
        log "Sending SIGTERM to Tor (PID ${TOR_PID})"
        kill -TERM "${TOR_PID}" 2>/dev/null || true

        local i=0
        while (( i < 10 )) && kill -0 "${TOR_PID}" 2>/dev/null; do
            sleep 1
            (( ++i )) || true
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
    log "tor_entrypoint.sh v${SCRIPT_VERSION} starting"
    log_debug "TOR_DATA_DIR=${TOR_DATA_DIR}"
    log_debug "TOR_COOKIE_FILE=${TOR_COOKIE_FILE}"
    log_debug "TOR_SOCKS_PORT=${TOR_SOCKS_PORT}"
    log_debug "TOR_CONTROL_PORT=${TOR_CONTROL_PORT}"
    log_debug "TOR_DNS_PORT=${TOR_DNS_PORT}"
    log_debug "TOR_USE_BRIDGES=${TOR_USE_BRIDGES}"
    log_debug "TOR_USE_SEED=${TOR_USE_SEED}"
    log_debug "TOR_ONION_SERVICE_ENABLED=${TOR_ONION_SERVICE_ENABLED}"

    log "--- Step 1: Preloading consensus/cert/onion seed data"
    preload_tor_data
    sleep 1

    log "--- Step 2: Writing torrc"
    write_torrc
    sleep 1

    log "--- Step 3: Configuring bridges"
    configure_bridges

    log "--- Step 4: Starting Tor daemon"
    start_tor
    sleep 2

    log "--- Step 5: Waiting for auth cookie"
    wait_for_cookie
    sleep 1

    log "--- Step 6: Distributing cookie to shared targets"
    copy_cookie_to_shared
    sleep 1

    log "--- Step 7: Waiting for full bootstrap"
    wait_for_bootstrap

    log "--- Step 8: Verifying onion service"
    verify_onion_service

    log "--- Step 9: Starting background health monitor"
    _health_monitor &

    log "Tor fully operational — container handing off to Tor process (PID ${TOR_PID})"
    wait "${TOR_PID}"
    local tor_exit=$?
    log_warn "Tor process exited with code ${tor_exit}"
    exit "${tor_exit}"
}

main "$@"
