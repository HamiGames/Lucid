#!/usr/bin/env bash
# tor_entrypoint.sh — Tor Proxy Container Entrypoint v5.1.0
# Distroless busybox compatible.
# No return statements — all flow control is if/else/exit.
# All arithmetic increments use pre-increment (( ++var )) || true to survive set -e.
#
# v5.1.0 — applied over v5.0.0 base:
#   [fix-1] write_torrc: removed SocksListenAddress — deprecated/fatal on Tor ≥ 0.4.x
#   [fix-2] write_torrc: added Log notice file so busybox tail/grep fallbacks get content
#   [fix-3] _cleanup: trap - EXIT SIGTERM SIGINT SIGQUIT prevents exit-trap infinite recursion
#   [fix-4] _tor_ctl: set +e/set -e guard around exec 3<> fd open (set -e race)
#   [fix-5] _tor_ctl: /dev/tcp pre-check — stripped bash builds omit net redirections
#   [fix-6] write_torrc: onion-disabled comment heredoc uses ${TOR_DATA_DIR} (was hardcoded)
#   [fix-7] write_torrc: IPv6 comment corrected to #SocksPort (was #SocksListenAddress)
#   [fix-8] hex_encode_file: NUL-byte caveat comment on pure-bash fallback
#   [fix-9] start_tor: chown TOR_LOG_FILE to TOR_USER:TOR_GROUP after touch
set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_VERSION="5.1.0"
readonly COOKIE_SIZE=32
readonly COOKIE_HEX_LENGTH=64

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
log_debug() {
    if [[ "${TOR_DEBUG:-0}" == "1" ]]; then
        _log "DEBUG" "$@"
    fi
}

# =============================================================================
# Environment  (override via .env.* / docker-compose.*.yml)
# =============================================================================
TOR_DATA_DIR="${TOR_DATA_DIR:-/app/run/lucid/tor}"
TOR_CONFIG_DIR="${TOR_CONFIG_DIR:-/app/opt/lucid/tor/}"
TOR_LOG_DIR="${TOR_LOG_DIR:-/app/var/log/tor}"
TOR_LOG_FILE="${TOR_LOG_DIR}/tor.log"
TORRC="${TOR_CONFIG_DIR}/torrc"

TOR_SOCKS_PORT="${TOR_SOCKS_PORT:-9050}"
TOR_CONTROL_PORT="${TOR_CONTROL_PORT:-9051}"
TOR_CONTROL_SOCKET="${TOR_CONTROL_SOCKET:-}"
TOR_DNS_PORT="${TOR_DNS_PORT:-0}"
TOR_TRANS_PORT="${TOR_TRANS_PORT:-0}"
BOOTSTRAP_HELPER="${BOOTSTRAP_HELPER:-/app/run/lucid/tor/bin/bootstrap-helper.sh}"
TOR_COOKIE_AUTH="${TOR_COOKIE_AUTH:-1}"
TOR_COOKIE_FILE="${TOR_COOKIE_FILE:-${TOR_DATA_DIR}/control_auth_cookie}"
TOR_COOKIE_TARGETS="${TOR_COOKIE_TARGETS:-}"
TOR_COOKIE_TMP="/tmp/tor/control_auth_cookie"

TOR_SEED_DIR="${TOR_SEED_DIR:-/app/seed/tor-data}"
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
TOR_GROUP="${TOR_GROUP:-debian-tor}"
TOR_PID=""

# =============================================================================
# Utility helpers
# =============================================================================
ensure_dir() {
    local dir="$1"
    local owner="${2:-}"
    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir"
    fi
    if [[ -n "$owner" ]]; then
        if ! chown "$owner" "$dir" 2>/dev/null; then
            log_warn "chown ${owner} ${dir} failed — continuing"
        fi
    fi
}

# File size via wc -c — stat(1) absent on minimal/distroless images.
file_size_bytes() {
    local f="$1"
    if [[ ! -f "$f" ]]; then
        printf '0'
    else
        wc -c < "$f" | busybox tr -d '[:space:]'
    fi
}

# Binary file → lowercase hex string on stdout (no newline).
# Cascade: busybox od (primary) → standalone od → pure bash byte loop.
# Excluded: hexdump (not in minimal busybox), xxd (not a busybox applet),
#           awk (not binary-safe — truncates at null bytes in cookie data).
hex_encode_file() {
    local file="$1"
    local result=""

    if result="$(busybox od -An -tx1 "$file" 2>/dev/null \
                 | busybox tr -d ' \n\t' 2>/dev/null)" \
       && [[ -n "$result" ]]; then
        printf '%s' "$result"

    elif result="$(od -An -tx1 "$file" 2>/dev/null \
                   | tr -d ' \n\t' 2>/dev/null)" \
         && [[ -n "$result" ]]; then
        printf '%s' "$result"

    else
        # [fix-8] Pure bash last-resort fallback.
        # NUL-BYTE CAVEAT: read -d '' treats the NUL character as the input
        # delimiter, so the first NUL byte in the cookie terminates the read
        # early.  The resulting char="" maps to ordval=0 (correct for that
        # byte), but no further bytes are read — the hex output is silently
        # truncated.  busybox od above handles NUL bytes correctly and must
        # always be present on any busybox image; this path should never be
        # reached in practice on the target environment.
        local hex_out="" char ordval
        local LC_ALL=C
        while IFS= read -r -d '' -n 1 char; do
            printf -v ordval '%d' "'${char}" 2>/dev/null || ordval=0
            printf -v hex_out '%s%02x' "${hex_out}" "${ordval}"
        done < "$file"
        printf '%s' "${hex_out}"
    fi
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
    byte_count="$(wc -c < "${cookie_path}" | busybox tr -d '[:space:]')"

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
# Step 0 — Pre-generate control auth cookie (failsafe preinit)
# =============================================================================
# Fires ONLY when no valid cookie exists on any candidate path.
# If a valid 32B / 64-hex cookie is found it is preserved and mirrored to
# /tmp/tor/control_auth_cookie (the persistent failsafe source).
# If nothing valid is found, generates one via dd+/dev/urandom and pre-applies
# it to all canonical paths so Tor can authenticate immediately on start.
# /tmp/tor/control_auth_cookie persists until container stop.
generate_control_auth_cookie_preinit() {
    if [[ "${TOR_COOKIE_AUTH}" != "1" ]]; then
        log_debug "Cookie auth disabled — skipping preinit"
    else
        log "Cookie preinit — checking all candidate paths for a valid cookie"

        # Ensure /tmp/tor/ directory structure exists.
        if [[ ! -d /tmp/tor ]]; then
            if mkdir -p /tmp/tor; then
                log_debug "Created /tmp/tor/"
            else
                log_error "Cannot create /tmp/tor/ — fatal"
                exit 1
            fi
        fi

        local tmp_cookie="/tmp/tor/control_auth_cookie"

        # All paths where a valid cookie may already exist.
        local -a candidates=(
            "${tmp_cookie}"
            "${TOR_COOKIE_FILE}"
            "${TOR_DATA_DIR}/control_auth_cookie"
            "/var/lib/tor/control_auth_cookie"
            "/run/tor/control_auth_cookie"
        )

        # Deduplicate while preserving order.
        local -a unique_candidates=()
        local seen=""
        local c
        for c in "${candidates[@]}"; do
            if [[ "${seen}" != *"|${c}|"* ]]; then
                unique_candidates+=("${c}")
                seen+="|${c}|"
            fi
        done

        # Search every candidate for a valid (32B + 64-hex) cookie.
        local valid_source=""
        local candidate
        for candidate in "${unique_candidates[@]}"; do
            if [[ -f "${candidate}" ]]; then
                local cand_sz
                cand_sz="$(file_size_bytes "${candidate}")"
                if (( cand_sz == COOKIE_SIZE )); then
                    local cand_hex
                    cand_hex="$(hex_encode_file "${candidate}")"
                    local cand_hex_len="${#cand_hex}"
                    if (( cand_hex_len == COOKIE_HEX_LENGTH )); then
                        valid_source="${candidate}"
                        log "Valid cookie found: ${candidate} (${cand_sz}B / ${cand_hex_len}-char hex) — preserving"
                        break
                    else
                        log_warn "Cookie at ${candidate}: invalid hex length ${cand_hex_len} — skipping"
                    fi
                else
                    log_warn "Cookie at ${candidate}: invalid size ${cand_sz}B — skipping"
                fi
            fi
        done

        if [[ -n "${valid_source}" ]]; then
            # Valid cookie exists — mirror to failsafe path if not already there.
            if [[ "${valid_source}" != "${tmp_cookie}" ]]; then
                if cp "${valid_source}" "${tmp_cookie}" 2>/dev/null; then
                    chmod 640 "${tmp_cookie}" 2>/dev/null || true
                    chown "${TOR_USER}:${TOR_GROUP}" "${tmp_cookie}" 2>/dev/null || true
                    log_debug "Failsafe mirror: ${valid_source} → ${tmp_cookie}"
                else
                    log_warn "Cannot mirror to ${tmp_cookie} — continuing with existing source"
                fi
            fi
            log "Preinit complete — valid cookie preserved, no generation needed"

        else
            # No valid cookie found anywhere — generate one now as the failsafe.
            log "No valid cookie found — generating 32-byte cookie via dd+/dev/urandom"

            if dd if=/dev/urandom of="${tmp_cookie}" bs=32 count=1 2>/dev/null; then
                chmod 640 "${tmp_cookie}" 2>/dev/null || true
                chown "${TOR_USER}:${TOR_GROUP}" "${tmp_cookie}" 2>/dev/null || true
            else
                log_error "dd failed to generate cookie at ${tmp_cookie} — fatal"
                exit 1
            fi

            # Validate the generated cookie before doing anything else.
            local gen_sz
            gen_sz="$(file_size_bytes "${tmp_cookie}")"
            if (( gen_sz != COOKIE_SIZE )); then
                log_error "Generated cookie size invalid: ${gen_sz}B (expected ${COOKIE_SIZE}B) — fatal"
                exit 1
            fi

            local gen_hex
            gen_hex="$(hex_encode_file "${tmp_cookie}")"
            local gen_hex_len="${#gen_hex}"
            if (( gen_hex_len != COOKIE_HEX_LENGTH )); then
                log_error "Generated cookie hex length invalid: ${gen_hex_len} (expected ${COOKIE_HEX_LENGTH}) — fatal"
                exit 1
            fi

            log "Cookie generated: ${tmp_cookie} — ${gen_sz}B / ${gen_hex_len}-char hex — OK"

            # Pre-apply generated cookie to canonical paths so Tor can use it on start.
            local -a preinit_targets=(
                "${TOR_COOKIE_FILE}"
                "${TOR_DATA_DIR}/control_auth_cookie"
            )

            # Deduplicate targets.
            local -a unique_targets=()
            local seen_t=""
            local pt
            for pt in "${preinit_targets[@]}"; do
                if [[ "${seen_t}" != *"|${pt}|"* ]]; then
                    unique_targets+=("${pt}")
                    seen_t+="|${pt}|"
                fi
            done

            for pt in "${unique_targets[@]}"; do
                local pt_dir
                pt_dir="$(dirname "${pt}")"
                if [[ ! -d "${pt_dir}" ]]; then
                    mkdir -p "${pt_dir}" 2>/dev/null || true
                    chown "${TOR_USER}:${TOR_GROUP}" "${pt_dir}" 2>/dev/null || true
                    chmod 750 "${pt_dir}" 2>/dev/null || true
                fi
                if cp "${tmp_cookie}" "${pt}" 2>/dev/null; then
                    chmod 640 "${pt}" 2>/dev/null || true
                    chown "${TOR_USER}:${TOR_GROUP}" "${pt}" 2>/dev/null || true
                    local pt_sz
                    pt_sz="$(file_size_bytes "${pt}")"
                    local pt_hex
                    pt_hex="$(hex_encode_file "${pt}")"
                    local pt_hex_len="${#pt_hex}"
                    if (( pt_sz == COOKIE_SIZE && pt_hex_len == COOKIE_HEX_LENGTH )); then
                        log_debug "Cookie pre-applied: ${pt} (${pt_sz}B / ${pt_hex_len}-char hex)"
                    else
                        log_warn "Cookie pre-apply to ${pt}: validation failed (${pt_sz}B / ${pt_hex_len}-char hex)"
                    fi
                else
                    log_warn "Cannot pre-apply cookie to ${pt} — Tor will write it on start"
                fi
            done

            log "Preinit complete — /tmp/tor/control_auth_cookie is persistent failsafe source"
        fi

        sleep 1
    fi
}

# =============================================================================
# Step 1 — Preload seed / consensus / cert / onion data
# =============================================================================
# Breaks the bootstrap catch-22: Tor cannot validate a consensus without
# cached-certs, and cannot fetch cached-certs without a valid consensus.
# Preloading both from a seed volume lets Tor validate immediately on start.
# Onion subdirs are copied to preserve the Ed25519 keypair (stable .onion addr).
preload_tor_data() {
    if [[ "${TOR_USE_SEED}" != "1" ]]; then
        log "Seed preload disabled (TOR_USE_SEED=${TOR_USE_SEED})"
    else
        if [[ ! -d "${TOR_SEED_DIR}" ]]; then
            log_warn "Seed dir not found: ${TOR_SEED_DIR} — cold bootstrap (will be slow)"
        else
            ensure_dir "${TOR_DATA_DIR}" "${TOR_USER}"
            chmod 700 "${TOR_DATA_DIR}"

            local sentinel="${TOR_DATA_DIR}/.seed_loaded"

            if [[ -f "${sentinel}" ]]; then
                log "Seed previously loaded — verifying critical consensus files"
                _verify_consensus_files
            else
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
                else
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
                            else
                                if cp -p "${src}" "${dst}"; then
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
                        fi
                    done

                    # Copy onion service subdirs — preserves Ed25519 keypair (stable .onion address).
                    local onion_count=0
                    local subdir

                    for subdir in "${TOR_SEED_DIR}"/*/; do
                        subdir="${subdir%/}"
                        if [[ -d "${subdir}" ]]; then
                            if [[ -f "${subdir}/hostname" ]]; then
                                local onion_addr
                                onion_addr="$(busybox tr -d '[:space:]' < "${subdir}/hostname" 2>/dev/null || true)"
                                if [[ -n "${onion_addr}" ]]; then
                                    local rel_path="${subdir#"${TOR_SEED_DIR}"/}"
                                    local dst_subdir="${TOR_DATA_DIR}/${rel_path}"
                                    ensure_dir "${dst_subdir}"
                                    if cp -a "${subdir}/." "${dst_subdir}/"; then
                                        chown -R "${TOR_USER}:${TOR_GROUP}" "${dst_subdir}" 2>/dev/null || true
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
                        fi
                    done

                    if ! chown -R "${TOR_USER}:${TOR_GROUP}" "${TOR_DATA_DIR}" 2>/dev/null; then
                        log_warn "chown -R ${TOR_DATA_DIR} failed — Tor may be unable to write state"
                    fi
                    chmod 700 "${TOR_DATA_DIR}"

                    touch "${sentinel}"
                    log "Seed preload complete: ${loaded_count} consensus/cert file(s), ${onion_count} onion service(s)"
                    _verify_consensus_files
                fi
            fi
        fi
    fi
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
# Built from environment variables and written atomically via tmp file + mv.
# Dynamic sections (DNS, bridges, onion service) appended conditionally.
write_torrc() {
    log "Writing torrc → ${TORRC}"
    ensure_dir "${TOR_CONFIG_DIR}"
    ensure_dir "${TOR_DATA_DIR}" "${TOR_USER}"
    ensure_dir "${TOR_LOG_DIR}"

    local tmp_torrc="${TORRC}.tmp.$$"

    # [fix-1] SocksListenAddress removed — directive was deprecated in Tor 0.4.x
    #         and causes immediate startup failure on any modern Tor image.
    # [fix-2] Log notice file added — without it TOR_LOG_FILE stays empty and
    #         the busybox tail/grep fallbacks in wait_for_bootstrap return nothing.
    cat > "${tmp_torrc}" << EOF
# Generated by tor_entrypoint.sh v${SCRIPT_VERSION} — do not edit directly.
# Regenerated on every container start from environment variables.
Log notice stdout
Log notice file ${TOR_LOG_FILE}
DataDirectory ${TOR_DATA_DIR}

SocksPort 0.0.0.0:${TOR_SOCKS_PORT}

ControlPort 0.0.0.0:${TOR_CONTROL_PORT}
EOF

    if [[ -n "${TOR_CONTROL_SOCKET}" ]]; then
        printf 'ControlSocket %s\n' "${TOR_CONTROL_SOCKET}" >> "${tmp_torrc}"
    fi

    if [[ "${TOR_COOKIE_AUTH}" == "1" ]]; then
        cat >> "${tmp_torrc}" << EOF

CookieAuthentication 1
CookieAuthFile ${TOR_COOKIE_FILE}
CookieAuthFileGroupReadable 1
EOF
    fi

    # Dynamic DNS — enables .onion resolution through the Tor DNS port.
    if [[ "${TOR_DNS_PORT}" != "0" ]]; then
        cat >> "${tmp_torrc}" << EOF

DNSPort 0.0.0.0:${TOR_DNS_PORT}
AutomapHostsOnResolve 1
AutomapHostsSuffixes .onion,.exit
EOF
    fi

    if [[ "${TOR_TRANS_PORT}" != "0" ]]; then
        printf '\nTransPort %s\n' "${TOR_TRANS_PORT}" >> "${tmp_torrc}"
    fi

    if [[ "${TOR_ONION_SERVICE_ENABLED}" == "1" ]]; then
        ensure_dir "${TOR_ONION_SERVICE_DIR}" "${TOR_USER}"
        chmod 700 "${TOR_ONION_SERVICE_DIR}"
        cat >> "${tmp_torrc}" << EOF

HiddenServiceDir ${TOR_ONION_SERVICE_DIR}
HiddenServiceVersion 3
HiddenServicePort ${TOR_ONION_SERVICE_PORT} ${TOR_ONION_SERVICE_TARGET}
EOF
    else
        # [fix-6] Heredoc changed from 'EOF' to EOF so ${TOR_DATA_DIR} expands
        #         in the comment — was hardcoded to /var/lib/tor/hidden_service.
        cat >> "${tmp_torrc}" << EOF

# Hidden service disabled (foundation phase).
# Set TOR_ONION_SERVICE_ENABLED=1 when the upstream is ready.
#HiddenServiceDir ${TOR_DATA_DIR}/hidden_service
#HiddenServiceVersion 3
#HiddenServicePort 80 127.0.0.1:8081
EOF
    fi

    # [fix-7] Heredoc changed from 'EOF' to EOF so ${TOR_SOCKS_PORT} expands.
    #         IPv6 comment corrected from #SocksListenAddress (deprecated) to
    #         #SocksPort — the correct modern directive for per-address binding.
    cat >> "${tmp_torrc}" << EOF

RunAsDaemon 0
AvoidDiskWrites 0

# Uncomment for IPv6 SOCKS support
#SocksPort [::1]:${TOR_SOCKS_PORT}
EOF

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
    else
        if [[ -z "${TOR_BRIDGES}" ]]; then
            log_warn "TOR_USE_BRIDGES=1 but TOR_BRIDGES is empty — skipping bridge config"
        else
            log "Configuring bridges"

            {
                printf '\nUseBridges 1\n'
                if [[ -n "${TOR_PLUGGABLE_TRANSPORT}" ]]; then
                    printf 'ClientTransportPlugin %s\n' "${TOR_PLUGGABLE_TRANSPORT}"
                fi
            } >> "${TORRC}"

            local bridge_count=0
            while IFS= read -r line; do
                if [[ -n "$line" && "$line" != \#* ]]; then
                    line="${line#"${line%%[![:space:]]*}"}"
                    line="${line%"${line##*[![:space:]]}"}"
                    if [[ -n "$line" ]]; then
                        if [[ "${line,,}" != bridge\ * ]]; then
                            line="Bridge ${line}"
                        fi
                        printf '%s\n' "$line" >> "${TORRC}"
                        (( ++bridge_count )) || true
                    fi
                fi
            done <<< "${TOR_BRIDGES}"

            log "Added ${bridge_count} bridge line(s) to torrc"
        fi
    fi
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

    # Ensure cookie dir exists before Tor starts.
    local cookie_dir
    cookie_dir="$(dirname "${TOR_COOKIE_FILE}")"
    if [[ ! -d "${cookie_dir}" ]]; then
        if mkdir -p "${cookie_dir}"; then
            chown "${TOR_USER}:${TOR_GROUP}" "${cookie_dir}" 2>/dev/null || true
            chmod 750 "${cookie_dir}" 2>/dev/null || true
        else
            log_warn "Cannot create cookie dir: ${cookie_dir} — Tor may fail to write cookie"
        fi
    fi

    if [[ ! -d /tmp ]]; then
        mkdir -p /tmp
        log_debug "Created /tmp"
    fi

    # [fix-9] chown after touch so Tor (running as TOR_USER) can append to the file.
    #         Without this, touch creates a root-owned file and Log notice file fails silently.
    touch "${TOR_LOG_FILE}" 2>/dev/null || true
    chown "${TOR_USER}:${TOR_GROUP}" "${TOR_LOG_FILE}" 2>/dev/null || true
    chmod 640 "${TOR_LOG_FILE}" 2>/dev/null || true

    tor -f "${TORRC}" &
    TOR_PID=$!
    log "Tor forked — PID ${TOR_PID}"

    # Poll up to 10s (5 × 2s) confirming Tor does not immediately crash.
    local i=0
    while (( i < 5 )); do
        sleep 2
        (( ++i )) || true
        if ! kill -0 "${TOR_PID}" 2>/dev/null; then
            log_error "Tor exited immediately after start — last 30 lines of log:"
            busybox tail -n 30 "${TOR_LOG_FILE}" >&2 2>/dev/null || true
            exit 1
        fi
        log_debug "Start check ${i}/5 — PID ${TOR_PID} alive"
    done

    log "Tor process confirmed running (PID ${TOR_PID})"
}

# =============================================================================
# Step 5 — Wait for auth cookie
# =============================================================================
# Cookie is written by Tor AFTER it binds its listeners — MUST run after start_tor.
# Searches all candidate paths, pre-creates placeholder on first poll,
# copies to canonical path if found elsewhere, then validates (size + hex).
# Writes /tmp/tor/control_auth_cookie backup as fail-safe source for copy_cookie_to_shared.
wait_for_cookie() {
    if [[ "${TOR_COOKIE_AUTH}" != "1" ]]; then
        log_debug "Cookie auth disabled — skipping wait_for_cookie"
    else
        local -a candidates=(
            "${TOR_COOKIE_FILE}"
            "${TOR_DATA_DIR}/control_auth_cookie"
            "${TOR_DATA_DIR}/tor_control_auth_cookie"
            "/var/lib/tor/control_auth_cookie"
            "/run/tor/control_auth_cookie"
            "${TOR_COOKIE_TMP}"
        )

        # Deduplicate while preserving order — pure bash, no sort/uniq.
        local -a unique_candidates=()
        local seen=""
        local c
        for c in "${candidates[@]}"; do
            if [[ "${seen}" != *"|${c}|"* ]]; then
                unique_candidates+=("$c")
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
                busybox tail -n 30 "${TOR_LOG_FILE}" >&2 2>/dev/null || true
                exit 1
            fi

            # First poll: pre-create placeholder so Tor can overwrite it.
            if (( first_poll == 1 )); then
                first_poll=0
                if [[ ! -f "${TOR_COOKIE_FILE}" ]]; then
                    if touch "${TOR_COOKIE_FILE}" 2>/dev/null; then
                        chown "${TOR_USER}:${TOR_GROUP}" "${TOR_COOKIE_FILE}" 2>/dev/null || true
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
                                chown "${TOR_USER}:${TOR_GROUP}" "${TOR_COOKIE_FILE}" 2>/dev/null || true
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
            busybox tail -n 30 "${TOR_LOG_FILE}" >&2 2>/dev/null || true
            exit 1
        fi

        # Full binary-size + hex-length validation before proceeding.
        validate_cookie_file "${TOR_COOKIE_FILE}"

        # Write /tmp/tor backup — fail-safe source for copy_cookie_to_shared.
        local tmp_dir
        tmp_dir="$(dirname "${TOR_COOKIE_TMP}")"
        if [[ ! -d "${tmp_dir}" ]]; then
            mkdir -p "${tmp_dir}" 2>/dev/null || true
        fi
        if cp "${TOR_COOKIE_FILE}" "${TOR_COOKIE_TMP}" 2>/dev/null; then
            chmod 640 "${TOR_COOKIE_TMP}" 2>/dev/null || true
            log_debug "Cookie backup written: ${TOR_COOKIE_TMP}"
        else
            log_warn "Could not write /tmp cookie backup — continuing without it"
        fi

        log "Auth cookie ready — ${TOR_COOKIE_FILE}"
    fi
}

# =============================================================================
# Step 6 — Distribute cookie to shared volume targets
# =============================================================================
# Stage 1: Locate — if canonical path is wrong-size, search candidates + /tmp backup.
# Stage 2: Validate source — byte-count + hex-length before any distribution.
# Stage 3: Distribute — binary cp to each target, validate each written copy.
copy_cookie_to_shared() {
    if [[ "${TOR_COOKIE_AUTH}" != "1" ]]; then
        log_debug "Cookie auth disabled — skipping distribution"
    else
        if [[ -z "${TOR_COOKIE_TARGETS}" ]]; then
            log_debug "TOR_COOKIE_TARGETS not set — no distribution required"
        else
            log "Distributing auth cookie to shared target(s)"

            # Stage 1: Locate valid cookie
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
                else
                    log "Valid cookie at ${found_at} — installing to canonical path ${TOR_COOKIE_FILE}"
                    local cookie_parent
                    cookie_parent="$(dirname "${TOR_COOKIE_FILE}")"
                    if mkdir -p "${cookie_parent}" 2>/dev/null; then
                        if cp "${found_at}" "${TOR_COOKIE_FILE}"; then
                            chmod 640 "${TOR_COOKIE_FILE}"
                            chown "${TOR_USER}:${TOR_GROUP}" "${TOR_COOKIE_FILE}" 2>/dev/null || true
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
            fi

            # Stage 2: Validate source
            validate_cookie_file "${TOR_COOKIE_FILE}"

            # Stage 3: Distribute to all targets
            local ok=0
            local fail=0

            local saved_ifs="$IFS"
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
                            chown "${TOR_USER}:${TOR_GROUP}" "${target}" 2>/dev/null || true

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
        fi
    fi
}

# =============================================================================
# Control port helper — pure bash /dev/tcp (no netcat/socat required)
# =============================================================================
# Called exclusively via command substitution: resp="$(_tor_ctl ...)"
# Any exit 1 inside just causes the outer `if` to fail; the calling function
# falls through to its busybox grep log-file fallback — the container does NOT die.
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

    # [fix-5] /dev/tcp is a bash compile-time option (--enable-net-redirections).
    #         Stripped busybox bash builds commonly omit it.  Bail early so the
    #         caller falls through to the busybox grep log-file fallback instead
    #         of hitting a cryptic "No such file or directory" on exec.
    if [[ ! -e /dev/tcp ]]; then
        log_debug "_tor_ctl: /dev/tcp not available in this bash build — skipping control port"
        exit 1
    fi

    # [fix-4] set -e can fire on a failed exec before the || handler is reached.
    #         Temporarily disable errexit for the fd-open line and capture the
    #         return code explicitly.
    set +e
    exec 3<>"/dev/tcp/127.0.0.1/${TOR_CONTROL_PORT}" 2>/dev/null
    local fd_rc=$?
    set -e

    if (( fd_rc != 0 )); then
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

    local line response=""
    while IFS= read -r -t 5 line <&3; do
        line="${line%$'\r'}"
        response+="${line}"$'\n'
        if [[ "$line" =~ ^[0-9]{3}[[:space:]] ]]; then
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
# Polls control port for GETINFO status/bootstrap-phase until 100%.
# Falls back to busybox grep on the log file if control port unreachable.
wait_for_bootstrap() {
    log "Waiting for 100%% bootstrap (timeout: ${TOR_BOOTSTRAP_TIMEOUT}s)"

    local elapsed=0
    local last_pct=-1
    local bootstrapped=0

    while (( elapsed < TOR_BOOTSTRAP_TIMEOUT )) && (( bootstrapped == 0 )); do

        if ! kill -0 "${TOR_PID}" 2>/dev/null; then
            log_error "Tor process died during bootstrap"
            busybox tail -n 50 "${TOR_LOG_FILE}" >&2 2>/dev/null || true
            exit 1
        fi

        local resp=""
        if resp="$(_tor_ctl "GETINFO status/bootstrap-phase" 2>/dev/null)"; then
            local pct=""
            if [[ "$resp" =~ PROGRESS=([0-9]+) ]]; then
                pct="${BASH_REMATCH[1]}"
            fi

            if [[ -n "$pct" ]] && (( pct != last_pct )); then
                local summary=""
                if [[ "$resp" =~ SUMMARY=\"([^\"]+)\" ]]; then
                    summary="${BASH_REMATCH[1]}"
                fi
                log "Bootstrap: ${pct}%${summary:+ — ${summary}}"
                last_pct=$pct
            fi

            if [[ -n "$pct" ]] && (( pct >= 100 )); then
                bootstrapped=1
            fi
        else
            # Fallback: busybox grep on log file (busybox applet, always present).
            # [fix-2] This branch now actually gets content because write_torrc
            #         emits "Log notice file ${TOR_LOG_FILE}" into torrc.
            if [[ -f "${TOR_LOG_FILE}" ]]; then
                local last_boot_line=""
                last_boot_line="$(busybox grep -oE 'Bootstrapped [0-9]+%[^:]*:.*' \
                    "${TOR_LOG_FILE}" 2>/dev/null \
                    | busybox tail -1)" || true

                if [[ -n "$last_boot_line" ]]; then
                    log_debug "Log fallback: ${last_boot_line}"
                    if [[ "$last_boot_line" =~ Bootstrapped\ 100% ]]; then
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
            busybox tail -n 40 "${TOR_LOG_FILE}" >&2 2>/dev/null || true
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
    else
        local hostname_file="${TOR_ONION_SERVICE_DIR}/hostname"
        log "Waiting for onion service hostname file"

        local elapsed=0
        local timeout=60
        local onion_found=0

        while (( elapsed < timeout )) && (( onion_found == 0 )); do
            if [[ -f "${hostname_file}" && -s "${hostname_file}" ]]; then
                local onion_addr
                onion_addr="$(busybox tr -d '[:space:]' < "${hostname_file}" 2>/dev/null || true)"
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
    # [fix-3] Deregister all traps immediately.
    #         Without this, the exit "${rc}" call at the bottom re-fires the EXIT
    #         trap, which calls _cleanup again, which calls exit again — infinite
    #         recursion until bash hits its call-stack limit.
    trap - EXIT SIGTERM SIGINT SIGQUIT

    local rc=$?
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

    log "--- Step 0: Cookie failsafe preinit"
    generate_control_auth_cookie_preinit
    sleep 1

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
