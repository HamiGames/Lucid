#!/bin/bash
# scripts/lib/lucid-x-file-paths.sh
# File: /app/scripts/lib/lucid-x-file-paths.sh
# x-lucid-file-path: /app/scripts/lib/lucid-x-file-paths.sh
# x-lucid-file-directory: /app/scripts/lib
# x-lucid-file-type: shell
#
# Sourced by scripts/lib/lucid-repo-paths.sh after LUCID_REPO_ROOT and LUCID_X_FILES_LISTING are set.
#
# Full index: lucid_x_listing_load_all reads x-files-listing.txt once and fills
#   LUCID_X_LISTING_PATHS[section]=x-lucid-file-path
# where section is the exact string between "# ---" and " ---" on each block header.
#
# Use in scripts:
#   source .../lucid-repo-paths.sh
#   # or minimal:
#   export LUCID_X_FILES_LISTING="$REPO/x-files-listing.txt"
#   source .../lucid-x-file-paths.sh && lucid_x_listing_load_all "$LUCID_X_FILES_LISTING"
#   p="${LUCID_X_LISTING_PATHS[configs/docker/docker-compose.foundation.yml]}"
#   lucid_x_listing_get "path/from/listing/header.ext"
#
# Curated LUCID_* exports: lucid_x_file_paths_load_from_listing (uses the index).
#
# One-off repair / verify (from repo root or any ancestor of scripts/lib):
#   bash scripts/lib/lucid-x-file-paths.sh
#   bash scripts/lib/lucid-x-file-paths.sh --verify
#   bash scripts/lib/lucid-x-file-paths.sh /path/to/x-files-listing.txt
#   bash scripts/lib/lucid-x-file-paths.sh --verify /path/to/x-files-listing.txt
#
# Regenerate listing: repo-root _normalise_lucid_headers.py --x-files-listing

# Requires Bash 4+ (associative arrays).
if ((BASH_VERSINFO[0] < 4)); then
    echo "lucid-x-file-paths: need Bash 4+ (associative arrays)." >&2
    return 2 2>/dev/null || exit 2
fi

declare -gA LUCID_X_LISTING_PATHS

# Parse entire x-files-listing.txt: first x-lucid-file-path per # --- section --- block.
lucid_x_listing_load_all() {
    local listing="$1"
    local line section=""

    if [[ -z "$listing" || ! -f "$listing" ]]; then
        echo "lucid-x-file-paths: listing missing or not a file: ${listing:-<empty>}" >&2
        return 1
    fi

    LUCID_X_LISTING_PATHS=()
    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line%$'\r'}"
        if [[ "$line" =~ ^#\ ---\ (.+)\ ---[[:space:]]*$ ]]; then
            section="${BASH_REMATCH[1]}"
            continue
        fi
        if [[ -n "$section" && "$line" =~ ^[[:space:]]*x-lucid-file-path:[[:space:]]*([^[:space:]]+) ]]; then
            if [[ -z "${LUCID_X_LISTING_PATHS[$section]+x}" ]]; then
                LUCID_X_LISTING_PATHS["$section"]="${BASH_REMATCH[1]}"
            fi
        fi
    done <"$listing"

    export LUCID_X_LISTING_PATHS
    return 0
}

# Echo x-lucid-file-path for section (requires lucid_x_listing_load_all first).
lucid_x_listing_get() {
    local section="$1"
    local v="${LUCID_X_LISTING_PATHS[$section]-}"
    [[ -n "$v" ]] || return 1
    printf '%s' "$v"
}

# Resolve path: use index if loaded, else scan file (slow).
lucid_x_listing_query_x_path() {
    local listing="$1"
    local section="$2"
    local line wanted=0

    if [[ -n "${LUCID_X_LISTING_PATHS[$section]+x}" ]]; then
        local v="${LUCID_X_LISTING_PATHS[$section]-}"
        [[ -n "$v" ]] && printf '%s' "$v" && return 0
        return 1
    fi

    [[ -f "$listing" ]] || return 1

    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line%$'\r'}"
        if [[ "$wanted" -eq 0 && "$line" == "# --- ${section} ---" ]]; then
            wanted=1
            continue
        fi
        if [[ "$wanted" -eq 1 ]]; then
            if [[ "$line" == "# --- "* ]]; then
                break
            fi
            if [[ "$line" =~ ^[[:space:]]*x-lucid-file-path:[[:space:]]*([^[:space:]]+)[[:space:]]*$ ]]; then
                printf '%s' "${BASH_REMATCH[1]}"
                return 0
            fi
        fi
    done <"$listing"
    return 1
}

# Repo-relative path mirroring /app/... (strip leading /app/).
lucid_x_listing_host_rel_from_image_path() {
    local x="$1"
    if [[ "$x" == /app/* ]]; then
        printf '%s' "${x#/app/}"
    else
        printf '%s' "$x"
    fi
}

lucid_x_file_paths_load_from_listing() {
    local listing="${LUCID_X_FILES_LISTING:-}"
    local x

    if [[ -z "$listing" || ! -f "$listing" ]]; then
        echo "lucid-x-file-paths: LUCID_X_FILES_LISTING missing or not a file: ${listing:-<empty>}" >&2
        return 1
    fi

    lucid_x_listing_load_all "$listing" || return 1

    local hc="infrastructure/containers/host-config.yml"
    if ! x="$(lucid_x_listing_get "$hc")"; then
        echo "lucid-x-file-paths: no x-lucid-file-path for section # --- ${hc} --- in ${listing}" >&2
        return 1
    fi
    LUCID_X_IMAGE_HOST_CONFIG_CANONICAL="$x"
    LUCID_X_IMAGE_HOST_CONFIG_CONFIGS="$x"
    LUCID_HOST_REL_HOST_CONFIG_SOURCE="$hc"

    local crl="infrastructure/containers/services/container-runtime-layout.yml"
    if ! x="$(lucid_x_listing_get "$crl")"; then
        echo "lucid-x-file-paths: no x-lucid-file-path for section # --- ${crl} --- in ${listing}" >&2
        return 1
    fi
    LUCID_X_IMAGE_CONTAINER_RUNTIME_LAYOUT="$x"
    LUCID_HOST_REL_CONTAINER_RUNTIME_LAYOUT="$crl"

    local dev="infrastructure/compose/lucid-dev.yaml"
    if ! x="$(lucid_x_listing_get "$dev")"; then
        echo "lucid-x-file-paths: no x-lucid-file-path for section # --- ${dev} --- in ${listing}" >&2
        return 1
    fi
    LUCID_X_IMAGE_LUCID_DEV="$x"
    LUCID_HOST_REL_LUCID_DEV="$dev"

    local app="configs/docker/docker-compose.application.yml"
    if ! x="$(lucid_x_listing_get "$app")"; then
        echo "lucid-x-file-paths: no x-lucid-file-path for section # --- ${app} --- in ${listing}" >&2
        return 1
    fi
    LUCID_X_IMAGE_COMPOSE_APPLICATION="$x"
    LUCID_HOST_REL_COMPOSE_APPLICATION="$app"

    local sup="configs/docker/docker-compose.support.yml"
    if ! x="$(lucid_x_listing_get "$sup")"; then
        echo "lucid-x-file-paths: no x-lucid-file-path for section # --- ${sup} --- in ${listing}" >&2
        return 1
    fi
    LUCID_X_IMAGE_COMPOSE_SUPPORT="$x"
    LUCID_HOST_REL_COMPOSE_SUPPORT="$sup"

    local all="configs/docker/docker-compose.all.yml"
    if ! x="$(lucid_x_listing_get "$all")"; then
        echo "lucid-x-file-paths: no x-lucid-file-path for section # --- ${all} --- in ${listing}" >&2
        return 1
    fi
    LUCID_X_IMAGE_COMPOSE_ALL="$x"
    LUCID_HOST_REL_COMPOSE_ALL="$all"

    local cor="configs/docker/docker-compose.core.yml"
    if ! x="$(lucid_x_listing_get "$cor")"; then
        echo "lucid-x-file-paths: no x-lucid-file-path for section # --- ${cor} --- in ${listing}" >&2
        return 1
    fi
    LUCID_X_IMAGE_COMPOSE_CORE="$x"
    LUCID_HOST_REL_COMPOSE_CORE="$cor"

    local fnd="configs/docker/docker-compose.foundation.yml"
    if ! x="$(lucid_x_listing_get "$fnd")"; then
        echo "lucid-x-file-paths: no x-lucid-file-path for section # --- ${fnd} --- in ${listing}" >&2
        return 1
    fi
    LUCID_X_IMAGE_COMPOSE_FOUNDATION="$x"
    LUCID_HOST_REL_COMPOSE_FOUNDATION="$fnd"

    local gui="configs/docker/docker-compose.gui-integration.yml"
    if ! x="$(lucid_x_listing_get "$gui")"; then
        echo "lucid-x-file-paths: no x-lucid-file-path for section # --- ${gui} --- in ${listing}" >&2
        return 1
    fi
    LUCID_X_IMAGE_COMPOSE_GUI_INTEGRATION="$x"
    LUCID_HOST_REL_COMPOSE_GUI_INTEGRATION="$gui"

    local int="infrastructure/compose/docker-compose.integration.yaml"
    if ! x="$(lucid_x_listing_get "$int")"; then
        echo "lucid-x-file-paths: no x-lucid-file-path for section # --- ${int} --- in ${listing}" >&2
        return 1
    fi
    LUCID_X_IMAGE_COMPOSE_INTEGRATION="$x"
    # Dockerfile route: tor/Dockerfile.tor-proxy-02 — COPY infrastructure/compose/ ./configs/compose/
    if [[ "$x" == /app/* ]]; then
        LUCID_HOST_REL_COMPOSE_INTEGRATION="${x#/app/}"
    else
        LUCID_HOST_REL_COMPOSE_INTEGRATION="$int"
    fi

    export LUCID_X_IMAGE_HOST_CONFIG_CANONICAL LUCID_X_IMAGE_HOST_CONFIG_CONFIGS
    export LUCID_HOST_REL_HOST_CONFIG_SOURCE
    export LUCID_X_IMAGE_CONTAINER_RUNTIME_LAYOUT LUCID_HOST_REL_CONTAINER_RUNTIME_LAYOUT
    export LUCID_X_IMAGE_LUCID_DEV LUCID_HOST_REL_LUCID_DEV
    export LUCID_X_IMAGE_COMPOSE_APPLICATION LUCID_HOST_REL_COMPOSE_APPLICATION
    export LUCID_X_IMAGE_COMPOSE_SUPPORT LUCID_HOST_REL_COMPOSE_SUPPORT
    export LUCID_X_IMAGE_COMPOSE_ALL LUCID_HOST_REL_COMPOSE_ALL
    export LUCID_X_IMAGE_COMPOSE_CORE LUCID_HOST_REL_COMPOSE_CORE
    export LUCID_X_IMAGE_COMPOSE_FOUNDATION LUCID_HOST_REL_COMPOSE_FOUNDATION
    export LUCID_X_IMAGE_COMPOSE_GUI_INTEGRATION LUCID_HOST_REL_COMPOSE_GUI_INTEGRATION
    export LUCID_X_IMAGE_COMPOSE_INTEGRATION LUCID_HOST_REL_COMPOSE_INTEGRATION
}

# --- executed (not sourced): one-off load / repair check ---
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    _lucid_listing_arg=""
    _lucid_verify=0
    for _lucid_a in "$@"; do
        if [[ "$_lucid_a" == "--verify" ]]; then
            _lucid_verify=1
        elif [[ -f "$_lucid_a" ]]; then
            _lucid_listing_arg="$_lucid_a"
        else
            echo "lucid-x-file-paths: unknown argument: $_lucid_a" >&2
            echo "Usage: $0 [--verify] [path/to/x-files-listing.txt]" >&2
            exit 2
        fi
    done

    if [[ -z "$_lucid_listing_arg" ]]; then
        _lucid_d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        while [[ "$_lucid_d" != "/" ]]; do
            if [[ -f "$_lucid_d/x-files-listing.txt" ]]; then
                _lucid_listing_arg="$_lucid_d/x-files-listing.txt"
                break
            fi
            _lucid_d="$(dirname "$_lucid_d")"
        done
    fi

    if [[ -z "$_lucid_listing_arg" || ! -f "$_lucid_listing_arg" ]]; then
        echo "lucid-x-file-paths: x-files-listing.txt not found; pass full path as argument." >&2
        exit 1
    fi

    lucid_x_listing_load_all "$_lucid_listing_arg" || exit 1
    echo "lucid-x-file-paths: loaded ${#LUCID_X_LISTING_PATHS[@]} entries from"
    echo "  $_lucid_listing_arg"

    if [[ "$_lucid_verify" -eq 1 ]]; then
        export LUCID_X_FILES_LISTING="$_lucid_listing_arg"
        lucid_x_file_paths_load_from_listing || exit 1
        echo "lucid-x-file-paths: curated LUCID_* paths (compose + host-config + layout + dev) OK."
    fi
    exit 0
fi
