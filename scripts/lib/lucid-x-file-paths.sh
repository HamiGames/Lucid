#!/bin/bash
# scripts/lib/lucid-x-file-paths.sh
# File: /app/scripts/lib/lucid-x-file-paths.sh
# x-lucid-file-path: /app/scripts/lib/lucid-x-file-paths.sh
# x-lucid-file-directory: /app/scripts/lib
# x-lucid-file-type: shell
#
# Sourced by scripts/lib/lucid-repo-paths.sh after LUCID_REPO_ROOT is set.
#
# Canonical structural map: x-files.json → key "section_to_canonical"
#   LUCID_X_LISTING_PATHS[repo-relative-section]=canonical-in-image-path
# (same key space as legacy x-files-listing.txt section headers.)
#
# Legacy: lucid_x_listing_load_all reads x-files-listing.txt (fallback only).
#
# Use in scripts:
#   source .../lucid-repo-paths.sh
#   # or minimal:
#   export LUCID_X_FILES_JSON="$REPO/configs/x-files.json"
#   source .../lucid-x-file-paths.sh && lucid_x_file_paths_load
#
# Curated LUCID_* exports: lucid_x_file_paths_load (alias: lucid_x_file_paths_load_from_listing).
#
# One-off repair / verify (from repo root or any ancestor of scripts/lib):
#   bash scripts/lib/lucid-x-file-paths.sh
#   bash scripts/lib/lucid-x-file-paths.sh --verify
#   bash scripts/lib/lucid-x-file-paths.sh /path/to/x-files.json
#   bash scripts/lib/lucid-x-file-paths.sh --verify /path/to/x-files-listing.txt
#
# Regenerate x-files.json / listing: repo tooling (see x-files.json "source_listing" note).

# Requires Bash 4+ (associative arrays).
if ((BASH_VERSINFO[0] < 4)); then
    echo "lucid-x-file-paths: need Bash 4+ (associative arrays)." >&2
    return 2 2>/dev/null || exit 2
fi

declare -gA LUCID_X_LISTING_PATHS

# Load section_to_canonical from x-files.json (requires python3 or jq).
lucid_x_json_load_all() {
    local jf="$1"
    local _tmp

    if [[ -z "$jf" || ! -f "$jf" ]]; then
        echo "lucid-x-file-paths: x-files.json missing or not a file: ${jf:-<empty>}" >&2
        return 1
    fi

    _tmp="$(mktemp "${TMPDIR:-/tmp}/lucid_x_paths.XXXXXX")" || return 1
    LUCID_X_LISTING_PATHS=()

    if command -v python3 >/dev/null 2>&1; then
        if ! python3 -c '
import json, sys
path = sys.argv[1]
out = open(sys.argv[2], "wb")
with open(path, encoding="utf-8") as f:
    d = json.load(f)
stc = d.get("section_to_canonical")
if not isinstance(stc, dict):
    sys.exit(2)
for k, v in stc.items():
    if not isinstance(k, str):
        k = str(k)
    if not isinstance(v, str):
        v = str(v)
    out.write((k + "\0" + v + "\0").encode("utf-8"))
out.close()
' "$jf" "$_tmp"; then
            rm -f "$_tmp"
            echo "lucid-x-file-paths: failed to parse section_to_canonical in: $jf" >&2
            return 1
        fi
    elif command -v jq >/dev/null 2>&1; then
        if ! jq -r '.section_to_canonical | to_entries[] | "\(.key)\u0000\(.value)\u0000"' "$jf" > "$_tmp"; then
            rm -f "$_tmp"
            echo "lucid-x-file-paths: jq failed on: $jf" >&2
            return 1
        fi
    else
        rm -f "$_tmp"
        echo "lucid-x-file-paths: need python3 or jq to read x-files.json" >&2
        return 1
    fi

    while IFS= read -r -d '' key && IFS= read -r -d '' val; do
        [[ -z "$key" ]] && continue
        LUCID_X_LISTING_PATHS["$key"]="$val"
    done < "$_tmp"
    rm -f "$_tmp"

    export LUCID_X_LISTING_PATHS
    return 0
}

# Resolve and load manifest: prefer x-files.json, else x-files-listing.txt.
lucid_x_file_paths_load() {
    local load_path="" load_kind=""

    if [[ -n "${LUCID_X_FILES_JSON:-}" && -f "${LUCID_X_FILES_JSON}" ]]; then
        load_path="$LUCID_X_FILES_JSON"
        load_kind="json"
    elif [[ -n "${LUCID_X_FILES_LISTING:-}" && -f "${LUCID_X_FILES_LISTING}" ]]; then
        load_path="$LUCID_X_FILES_LISTING"
        load_kind="txt"
    elif [[ -n "${LUCID_REPO_ROOT:-}" ]]; then
        if [[ -f "${LUCID_REPO_ROOT}/configs/x-files.json" ]]; then
            export LUCID_X_FILES_JSON="${LUCID_REPO_ROOT}/configs/x-files.json"
            load_path="$LUCID_X_FILES_JSON"
            load_kind="json"
        elif [[ -f "${LUCID_REPO_ROOT}/x-files.json" ]]; then
            export LUCID_X_FILES_JSON="${LUCID_REPO_ROOT}/x-files.json"
            load_path="$LUCID_X_FILES_JSON"
            load_kind="json"
        elif [[ -f "${LUCID_REPO_ROOT}/x-files-listing.txt" ]]; then
            export LUCID_X_FILES_LISTING="${LUCID_REPO_ROOT}/x-files-listing.txt"
            load_path="$LUCID_X_FILES_LISTING"
            load_kind="txt"
        fi
    fi

    if [[ -z "$load_path" ]]; then
        echo "lucid-x-file-paths: need configs/x-files.json (preferred), or repo-root x-files.json, or set LUCID_X_FILES_JSON; legacy: x-files-listing.txt / LUCID_X_FILES_LISTING" >&2
        return 1
    fi

    if [[ "$load_kind" == "json" ]]; then
        lucid_x_json_load_all "$load_path" || return 1
    else
        lucid_x_listing_load_all "$load_path" || return 1
    fi

    _lucid_x_apply_curated_exports "$load_path"
}

# Internal: after LUCID_X_LISTING_PATHS is filled, set LUCID_* compose/host-config exports.
_lucid_x_apply_curated_exports() {
    local _src="$1"
    local x
    local hc="infrastructure/containers/host-config.yml"
    if ! x="$(lucid_x_listing_get "$hc")"; then
        echo "lucid-x-file-paths: no path for section ${hc} in ${_src}" >&2
        return 1
    fi
    LUCID_X_IMAGE_HOST_CONFIG_CANONICAL="$x"
    LUCID_X_IMAGE_HOST_CONFIG_CONFIGS="$x"
    LUCID_HOST_REL_HOST_CONFIG_SOURCE="$hc"

    local crl="infrastructure/containers/services/container-runtime-layout.yml"
    if ! x="$(lucid_x_listing_get "$crl")"; then
        echo "lucid-x-file-paths: no path for section ${crl} in ${_src}" >&2
        return 1
    fi
    LUCID_X_IMAGE_CONTAINER_RUNTIME_LAYOUT="$x"
    LUCID_HOST_REL_CONTAINER_RUNTIME_LAYOUT="$crl"

    local dev="infrastructure/compose/lucid-dev.yaml"
    if ! x="$(lucid_x_listing_get "$dev")"; then
        echo "lucid-x-file-paths: no path for section ${dev} in ${_src}" >&2
        return 1
    fi
    LUCID_X_IMAGE_LUCID_DEV="$x"
    LUCID_HOST_REL_LUCID_DEV="$dev"

    local app="configs/docker/docker-compose.application.yml"
    if ! x="$(lucid_x_listing_get "$app")"; then
        echo "lucid-x-file-paths: no path for section ${app} in ${_src}" >&2
        return 1
    fi
    LUCID_X_IMAGE_COMPOSE_APPLICATION="$x"
    LUCID_HOST_REL_COMPOSE_APPLICATION="$app"

    local sup="configs/docker/docker-compose.support.yml"
    if ! x="$(lucid_x_listing_get "$sup")"; then
        echo "lucid-x-file-paths: no path for section ${sup} in ${_src}" >&2
        return 1
    fi
    LUCID_X_IMAGE_COMPOSE_SUPPORT="$x"
    LUCID_HOST_REL_COMPOSE_SUPPORT="$sup"

    local all="configs/docker/docker-compose.all.yml"
    if ! x="$(lucid_x_listing_get "$all")"; then
        echo "lucid-x-file-paths: no path for section ${all} in ${_src}" >&2
        return 1
    fi
    LUCID_X_IMAGE_COMPOSE_ALL="$x"
    LUCID_HOST_REL_COMPOSE_ALL="$all"

    local cor="configs/docker/docker-compose.core.yml"
    if ! x="$(lucid_x_listing_get "$cor")"; then
        echo "lucid-x-file-paths: no path for section ${cor} in ${_src}" >&2
        return 1
    fi
    LUCID_X_IMAGE_COMPOSE_CORE="$x"
    LUCID_HOST_REL_COMPOSE_CORE="$cor"

    local fnd="configs/docker/docker-compose.foundation.yml"
    if ! x="$(lucid_x_listing_get "$fnd")"; then
        echo "lucid-x-file-paths: no path for section ${fnd} in ${_src}" >&2
        return 1
    fi
    LUCID_X_IMAGE_COMPOSE_FOUNDATION="$x"
    LUCID_HOST_REL_COMPOSE_FOUNDATION="$fnd"

    local gui="configs/docker/docker-compose.gui-integration.yml"
    if ! x="$(lucid_x_listing_get "$gui")"; then
        echo "lucid-x-file-paths: no path for section ${gui} in ${_src}" >&2
        return 1
    fi
    LUCID_X_IMAGE_COMPOSE_GUI_INTEGRATION="$x"
    LUCID_HOST_REL_COMPOSE_GUI_INTEGRATION="$gui"

    local int="infrastructure/compose/docker-compose.integration.yaml"
    if ! x="$(lucid_x_listing_get "$int")"; then
        echo "lucid-x-file-paths: no path for section ${int} in ${_src}" >&2
        return 1
    fi
    LUCID_X_IMAGE_COMPOSE_INTEGRATION="$x"
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

# Backward-compatible name (now loads x-files.json first).
lucid_x_file_paths_load_from_listing() {
    lucid_x_file_paths_load
}

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

# --- executed (not sourced): one-off load / repair check ---
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    _lucid_manifest_arg=""
    _lucid_verify=0
    for _lucid_a in "$@"; do
        if [[ "$_lucid_a" == "--verify" ]]; then
            _lucid_verify=1
        elif [[ -f "$_lucid_a" ]]; then
            _lucid_manifest_arg="$_lucid_a"
        else
            echo "lucid-x-file-paths: unknown argument: $_lucid_a" >&2
            echo "Usage: $0 [--verify] [path/to/x-files.json|x-files-listing.txt]" >&2
            exit 2
        fi
    done

    if [[ -z "$_lucid_manifest_arg" ]]; then
        _lucid_d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        while [[ "$_lucid_d" != "/" ]]; do
            if [[ -f "$_lucid_d/configs/x-files.json" ]]; then
                _lucid_manifest_arg="$_lucid_d/configs/x-files.json"
                break
            fi
            if [[ -f "$_lucid_d/x-files.json" ]]; then
                _lucid_manifest_arg="$_lucid_d/x-files.json"
                break
            fi
            if [[ -f "$_lucid_d/x-files-listing.txt" ]]; then
                _lucid_manifest_arg="$_lucid_d/x-files-listing.txt"
                break
            fi
            _lucid_d="$(dirname "$_lucid_d")"
        done
    fi

    if [[ -z "$_lucid_manifest_arg" || ! -f "$_lucid_manifest_arg" ]]; then
        echo "lucid-x-file-paths: x-files.json (preferred) or x-files-listing.txt not found; pass full path." >&2
        exit 1
    fi

    case "$_lucid_manifest_arg" in
        *.json)
            lucid_x_json_load_all "$_lucid_manifest_arg" || exit 1
            ;;
        *)
            lucid_x_listing_load_all "$_lucid_manifest_arg" || exit 1
            ;;
    esac
    echo "lucid-x-file-paths: loaded ${#LUCID_X_LISTING_PATHS[@]} entries from"
    echo "  $_lucid_manifest_arg"

    if [[ "$_lucid_verify" -eq 1 ]]; then
        case "$_lucid_manifest_arg" in
            *.json) export LUCID_X_FILES_JSON="$_lucid_manifest_arg" ;;
            *)      export LUCID_X_FILES_LISTING="$_lucid_manifest_arg" ;;
        esac
        lucid_x_file_paths_load || exit 1
        echo "lucid-x-file-paths: curated LUCID_* paths (compose + host-config + layout + dev) OK."
    fi
    exit 0
fi
