#!/usr/bin/env bash
# scripts/lib/lucid-host-config-path.sh
# File: /app/scripts/lib/lucid-host-config-path.sh
# x-lucid-file-path: /app/scripts/lib/lucid-host-config-path.sh
# x-lucid-file-directory: /app/scripts/lib
# x-lucid-file-type: shell
#
# Host registry paths aligned with:
#   - x-files.json section_to_canonical["infrastructure/containers/host-config.yml"]
#     → in-image canonical: /app/configs/host-config.yml
#   - Legacy fallback: x-files-listing.txt (same section keys)
#   - Source tree: infrastructure/containers/host-config.yml
#   - scripts/lib/lucid-x-file-paths.sh (LUCID_X_IMAGE_* exports)
#   - scripts/lib/lucid-repo-paths.sh (full repo + compose + host-config init)
#
# Use when you need host-config resolution without pulling in all compose paths:
#   source scripts/lib/lucid-host-config-path.sh
#   lucid_host_config_paths_load || exit 1
#
# Prefer for most scripts: source scripts/lib/lucid-repo-paths.sh (includes this data).
#
# One-off (repo root):
#   bash scripts/lib/lucid-host-config-path.sh
#   bash scripts/lib/lucid-host-config-path.sh --verify

_LHCP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=lucid-x-file-paths.sh
# shellcheck disable=SC1091
source "${_LHCP_DIR}/lucid-x-file-paths.sh"

# Static fallback if listing unavailable (must match x-files.json).
LUCID_HOST_CONFIG_REPO_REL_DEFAULT="infrastructure/containers/host-config.yml"
LUCID_HOST_CONFIG_IMAGE_DEFAULT="/app/configs/host-config.yml"

# Print repo root directory containing configs/x-files.json, x-files.json, or x-files-listing.txt.
lucid_host_config_find_manifest_root() {
    local d="${1:-$(pwd)}"
    while [[ -n "$d" && "$d" != "/" ]]; do
        if [[ -f "$d/configs/x-files.json" ]] || [[ -f "$d/x-files.json" ]] || [[ -f "$d/x-files-listing.txt" ]]; then
            printf '%s' "$d"
            return 0
        fi
        d="$(dirname "$d")"
    done
    return 1
}

lucid_host_config_set_manifest_env_for_root() {
    local root="$1"
    export LUCID_REPO_ROOT="$root"
    if [[ -f "$root/configs/x-files.json" ]]; then
        export LUCID_X_FILES_JSON="$root/configs/x-files.json"
    elif [[ -f "$root/x-files.json" ]]; then
        export LUCID_X_FILES_JSON="$root/x-files.json"
    else
        unset LUCID_X_FILES_JSON 2>/dev/null || true
    fi
    if [[ -f "$root/x-files-listing.txt" ]]; then
        export LUCID_X_FILES_LISTING="$root/x-files-listing.txt"
    else
        unset LUCID_X_FILES_LISTING 2>/dev/null || true
    fi
}

# Load LUCID_X_* host-config fields via lucid_x_file_paths_load (JSON preferred).
# Optional: pass repo root as $1.
lucid_host_config_paths_load() {
    local root="${1:-}"
    if [[ -n "$root" ]]; then
        root="$(cd "$root" && pwd)"
        lucid_host_config_set_manifest_env_for_root "$root"
    elif [[ -n "${LUCID_X_FILES_JSON:-}" && -f "${LUCID_X_FILES_JSON}" ]]; then
        :
    elif [[ -n "${LUCID_X_FILES_LISTING:-}" && -f "${LUCID_X_FILES_LISTING}" ]]; then
        :
    else
        local r
        if r="$(lucid_host_config_find_manifest_root "$(pwd)")"; then
            lucid_host_config_set_manifest_env_for_root "$r"
        else
            echo "lucid-host-config-path: configs/x-files.json (preferred), repo-root x-files.json, or x-files-listing.txt not found; set LUCID_X_FILES_JSON or pass repo root." >&2
            return 1
        fi
    fi

    lucid_x_file_paths_load || return 1

    if [[ -z "${LUCID_REPO_ROOT:-}" ]]; then
        if [[ -n "${LUCID_X_FILES_JSON:-}" ]]; then
            _lhc_jdir="$(dirname "$LUCID_X_FILES_JSON")"
            if [[ "$(basename "$_lhc_jdir")" == "configs" ]]; then
                export LUCID_REPO_ROOT="$(dirname "$_lhc_jdir")"
            else
                export LUCID_REPO_ROOT="$_lhc_jdir"
            fi
            unset _lhc_jdir
        elif [[ -n "${LUCID_X_FILES_LISTING:-}" ]]; then
            export LUCID_REPO_ROOT="$(dirname "$LUCID_X_FILES_LISTING")"
        fi
    fi

    export LUCID_HOST_CONFIG_REPO_REL="${LUCID_HOST_REL_HOST_CONFIG_SOURCE:-$LUCID_HOST_CONFIG_REPO_REL_DEFAULT}"
    export LUCID_HOST_CONFIG_IMAGE="${LUCID_X_IMAGE_HOST_CONFIG_CANONICAL:-$LUCID_HOST_CONFIG_IMAGE_DEFAULT}"

    if [[ -n "${LUCID_REPO_ROOT:-}" ]]; then
        export LUCID_HOST_CONFIG_SOURCE="${LUCID_REPO_ROOT}/${LUCID_HOST_CONFIG_REPO_REL}"
    fi
    return 0
}

# Path to use at runtime: in container vs host checkout.
lucid_host_config_effective_path() {
    if [[ -f "$LUCID_HOST_CONFIG_IMAGE_DEFAULT" ]]; then
        printf '%s' "$LUCID_HOST_CONFIG_IMAGE_DEFAULT"
        return 0
    fi
    if [[ -n "${LUCID_HOST_CONFIG_SOURCE:-}" && -f "$LUCID_HOST_CONFIG_SOURCE" ]]; then
        printf '%s' "$LUCID_HOST_CONFIG_SOURCE"
        return 0
    fi
    if [[ -n "${LUCID_REPO_ROOT:-}" && -f "${LUCID_REPO_ROOT}/${LUCID_HOST_CONFIG_REPO_REL_DEFAULT}" ]]; then
        printf '%s' "${LUCID_REPO_ROOT}/${LUCID_HOST_CONFIG_REPO_REL_DEFAULT}"
        return 0
    fi
    printf '%s' "${LUCID_HOST_CONFIG_SOURCE:-${LUCID_REPO_ROOT:-.}/${LUCID_HOST_CONFIG_REPO_REL_DEFAULT}}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    _verify=0
    _root=""
    for _a in "$@"; do
        if [[ "$_a" == "--verify" ]]; then
            _verify=1
        elif [[ -d "$_a" ]]; then
            _root="$_a"
        fi
    done
    if lucid_host_config_paths_load "${_root}"; then
        echo "lucid-host-config-path: manifest OK → image ${LUCID_HOST_CONFIG_IMAGE}"
        echo "  repo-relative: ${LUCID_HOST_CONFIG_REPO_REL}"
        if [[ "$_verify" -eq 1 ]]; then
            if [[ "${LUCID_HOST_CONFIG_IMAGE}" != "/app/configs/host-config.yml" ]]; then
                echo "lucid-host-config-path: VERIFY FAIL: expected /app/configs/host-config.yml (x-files.json canonical)" >&2
                exit 1
            fi
            echo "lucid-host-config-path: verify OK (canonical /app/configs/host-config.yml)."
        fi
        exit 0
    fi
    exit 1
fi
