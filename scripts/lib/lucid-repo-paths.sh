#!/bin/bash
# scripts/lib/lucid-repo-paths.sh
# File: /app/scripts/lib/lucid-repo-paths.sh
# x-lucid-file-path: /app/scripts/lib/lucid-repo-paths.sh
# x-lucid-file-directory: /app/scripts/lib
# x-lucid-file-type: shell
#
# PURPOSE (host / CI / optional container shell)
#   Resolve LUCID_REPO_ROOT and paths used by scripts under scripts/.
#
# NOT for Dockerfile RUN (unless you really source it — see below)
#   Image layout comes only from each Dockerfile's WORKDIR + COPY. Stages differ:
#   e.g. tor-builder uses WORKDIR /build, final distroless uses WORKDIR /app,
#   Dockerfile.tunnels uses /app/tunnel, gui images use /work/electron_gui — there is
#   no single "cd /build" that is correct for all of them.
#
#   Never: RUN ./scripts/lib/lucid-repo-paths.sh
#   That executes the file; then BASH_SOURCE[0] equals $0 and auto-init does NOT run.
#   To load vars in a build stage you would need: RUN bash -lc '. scripts/lib/lucid-repo-paths.sh'
#   from that stage's WORKDIR after COPY — usually unnecessary; prefer explicit RUN test -f ...
#
# If auto-detect fails (common on Windows): export before running any script:
#   export LUCID_REPO_ROOT="/c/path/to/Lucid"
#   bash scripts/config/generate-env.sh
#
# Repo root = first directory upward that matches EITHER:
#   - master-env-config.txt  (canonical for Docker COPY -> /app/configs/.env.master)
#   - infrastructure/containers/host-config.yml AND scripts/  (full checkout marker)
#
# In-container paths for host-config + stack compose: parsed from x-files.json (section_to_canonical) when present, else legacy x-files-listing.txt (see scripts/lib/lucid-x-file-paths.sh).

_LUCID_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

lucid_find_scripts_root_from_path() {
    local d="$1"
    while [[ -n "$d" && "$d" != "/" ]]; do
        if [[ "$(basename "$d")" == "scripts" && -f "$d/lib/lucid-repo-paths.sh" ]]; then
            printf '%s' "$d"
            return 0
        fi
        d="$(dirname "$d")"
    done
    return 1
}

# True if $1 looks like the Lucid repository root (directory must exist).
lucid_dir_is_repo_root() {
    local d="$1"
    [[ -n "$d" && -d "$d" ]] || return 1
    if [[ -f "$d/master-env-config.txt" ]]; then
        return 0
    fi
    if [[ -f "$d/infrastructure/containers/host-config.yml" && -d "$d/scripts" ]]; then
        return 0
    fi
    return 1
}

lucid_find_repo_root_from_path() {
    local d="$1"
    while [[ -n "$d" && "$d" != "/" ]]; do
        if lucid_dir_is_repo_root "$d"; then
            printf '%s' "$d"
            return 0
        fi
        d="$(dirname "$d")"
    done
    return 1
}

# Optional: path to calling script (from BASH_SOURCE[1] when this file is sourced).
lucid_resolve_repo_root() {
    local caller_script="${1-}"
    local candidate root s git_root

    for candidate in "${LUCID_REPO_ROOT:-}" "${PROJECT_ROOT:-}"; do
        if lucid_dir_is_repo_root "$candidate"; then
            printf '%s' "$(cd "$candidate" && pwd)"
            return 0
        fi
    done

    local -a starts=()
    if [[ -n "$caller_script" ]]; then
        if [[ -f "$caller_script" ]]; then
            s="$(cd "$(dirname "$caller_script")" && pwd)" && starts+=("$s")
        elif [[ -f "${BASH_SOURCE[0]}" ]]; then
            s="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" && starts+=("$s")
        fi
    fi
    starts+=("$(pwd)")

    for s in "${starts[@]}"; do
        [[ -z "$s" || ! -d "$s" ]] && continue
        if root="$(lucid_find_repo_root_from_path "$s")"; then
            printf '%s' "$(cd "$root" && pwd)"
            return 0
        fi
    done

    if git_root="$(git -C "$(pwd)" rev-parse --show-toplevel 2>/dev/null)"; then
        if lucid_dir_is_repo_root "$git_root"; then
            printf '%s' "$(cd "$git_root" && pwd)"
            return 0
        fi
    fi

    if [[ -f /app/configs/.env.master ]] || [[ -f /app/configs/host-config.yml ]] || [[ -f /app/configs/x-files.json ]] || [[ -f /app/infrastructure/containers/services/host-config.yml ]]; then
        printf '%s' "/app"
        return 0
    fi

    return 1
}

lucid_init_repo_paths() {
    local caller_script="${1-}"

    export LUCID_REPO_ROOT
    if ! LUCID_REPO_ROOT="$(lucid_resolve_repo_root "$caller_script")"; then
        echo "lucid-repo-paths: could not find Lucid repo root." >&2
        echo "  Expected: master-env-config.txt OR infrastructure/containers/host-config.yml + scripts/ at repo root." >&2
        echo "  Fix: export LUCID_REPO_ROOT=/absolute/path/to/Lucid  (then re-run)." >&2
        echo "  Docker build: do not rely on this script — use WORKDIR and COPY in the Dockerfile." >&2
        return 1
    fi

    local start
    start="$(pwd)"
    if [[ -n "$caller_script" && -f "$caller_script" ]]; then
        start="$(cd "$(dirname "$caller_script")" && pwd)"
    fi

    export LUCID_SCRIPTS_DIR
    if [[ -d "$LUCID_REPO_ROOT/scripts" ]]; then
        LUCID_SCRIPTS_DIR="$LUCID_REPO_ROOT/scripts"
    elif LUCID_SCRIPTS_DIR="$(lucid_find_scripts_root_from_path "$start")"; then
        :
    else
        LUCID_SCRIPTS_DIR="$LUCID_REPO_ROOT/scripts"
    fi

    if [[ -z "${PROJECT_ROOT:-}" ]] || ! lucid_dir_is_repo_root "$PROJECT_ROOT"; then
        export PROJECT_ROOT="$LUCID_REPO_ROOT"
    fi

    export LUCID_MASTER_ENV_SOURCE="$LUCID_REPO_ROOT/master-env-config.txt"
    export LUCID_ENV_CONFIG_DIR="$LUCID_REPO_ROOT/configs/environment"
    if [[ -f "$LUCID_REPO_ROOT/configs/x-files.json" ]]; then
        export LUCID_X_FILES_JSON="$LUCID_REPO_ROOT/configs/x-files.json"
    elif [[ -f "$LUCID_REPO_ROOT/x-files.json" ]]; then
        export LUCID_X_FILES_JSON="$LUCID_REPO_ROOT/x-files.json"
    else
        export LUCID_X_FILES_JSON="$LUCID_REPO_ROOT/configs/x-files.json"
    fi
    export LUCID_X_FILES_LISTING="$LUCID_REPO_ROOT/x-files-listing.txt"

    # shellcheck source=lucid-x-file-paths.sh
    # shellcheck disable=SC1091
    source "${_LUCID_LIB_DIR}/lucid-x-file-paths.sh"
    lucid_x_file_paths_load || return 1

    export LUCID_HOST_CONFIG_SOURCE="$LUCID_REPO_ROOT/$LUCID_HOST_REL_HOST_CONFIG_SOURCE"
    export LUCID_CONTAINER_RUNTIME_LAYOUT_SOURCE="$LUCID_REPO_ROOT/$LUCID_HOST_REL_CONTAINER_RUNTIME_LAYOUT"

    export LUCID_IMAGE_APP_ROOT="/app"
    export LUCID_IMAGE_CONFIG_DIR="/app/configs"
    export LUCID_IMAGE_MASTER_ENV="/app/configs/.env.master"
    export LUCID_IMAGE_HOST_CONFIG="$LUCID_X_IMAGE_HOST_CONFIG_CANONICAL"
    export LUCID_IMAGE_HOST_CONFIG_ALT="$LUCID_X_IMAGE_HOST_CONFIG_CONFIGS"
    export LUCID_IMAGE_SERVICE_CONFIGS="/app/service_configs"

    export LUCID_FOUNDATION_STORAGE_DOCKER_DIR="$LUCID_REPO_ROOT/infrastructure/containers/storage"

    export LUCID_CONFIGS_DOCKER_DIR="$LUCID_REPO_ROOT/configs/docker"
    export LUCID_INFRA_COMPOSE_DIR="$LUCID_REPO_ROOT/infrastructure/compose"
    export LUCID_INFRA_DOCKER_COMPOSE_DIR="$LUCID_REPO_ROOT/infrastructure/docker/compose"
    export LUCID_INFRA_CONTAINERS_SERVICES_DIR="$LUCID_REPO_ROOT/infrastructure/containers/services"

    export LUCID_HOST_COMPOSE_APPLICATION="$LUCID_REPO_ROOT/$LUCID_HOST_REL_COMPOSE_APPLICATION"
    export LUCID_HOST_COMPOSE_SUPPORT="$LUCID_REPO_ROOT/$LUCID_HOST_REL_COMPOSE_SUPPORT"
    export LUCID_HOST_COMPOSE_ALL="$LUCID_REPO_ROOT/$LUCID_HOST_REL_COMPOSE_ALL"
    export LUCID_HOST_COMPOSE_CORE="$LUCID_REPO_ROOT/$LUCID_HOST_REL_COMPOSE_CORE"
    export LUCID_HOST_COMPOSE_FOUNDATION="$LUCID_REPO_ROOT/$LUCID_HOST_REL_COMPOSE_FOUNDATION"
    export LUCID_HOST_COMPOSE_GUI_INTEGRATION="$LUCID_REPO_ROOT/$LUCID_HOST_REL_COMPOSE_GUI_INTEGRATION"
    export LUCID_HOST_COMPOSE_INTEGRATION="$LUCID_REPO_ROOT/$LUCID_HOST_REL_COMPOSE_INTEGRATION"

    export LUCID_DEFAULT_STACK_COMPOSE="$LUCID_HOST_COMPOSE_FOUNDATION"
    export LUCID_DEV_COMPOSE_FILE="$LUCID_REPO_ROOT/$LUCID_HOST_REL_LUCID_DEV"

    export LUCID_X_IMAGE_HOST_CONFIG_CANONICAL LUCID_X_IMAGE_HOST_CONFIG_CONFIGS
    export LUCID_X_IMAGE_CONTAINER_RUNTIME_LAYOUT LUCID_X_IMAGE_LUCID_DEV
    export LUCID_X_IMAGE_COMPOSE_APPLICATION LUCID_X_IMAGE_COMPOSE_SUPPORT LUCID_X_IMAGE_COMPOSE_ALL
    export LUCID_X_IMAGE_COMPOSE_CORE LUCID_X_IMAGE_COMPOSE_FOUNDATION LUCID_X_IMAGE_COMPOSE_GUI_INTEGRATION
    export LUCID_X_IMAGE_COMPOSE_INTEGRATION
    export LUCID_HOST_REL_HOST_CONFIG_SOURCE LUCID_HOST_REL_CONTAINER_RUNTIME_LAYOUT LUCID_HOST_REL_LUCID_DEV
    export LUCID_HOST_REL_COMPOSE_APPLICATION LUCID_HOST_REL_COMPOSE_SUPPORT LUCID_HOST_REL_COMPOSE_ALL
    export LUCID_HOST_REL_COMPOSE_CORE LUCID_HOST_REL_COMPOSE_FOUNDATION LUCID_HOST_REL_COMPOSE_GUI_INTEGRATION
    export LUCID_HOST_REL_COMPOSE_INTEGRATION
}

if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    _lucid_caller="${BASH_SOURCE[1]-}"
    if [[ -z "$_lucid_caller" || "$_lucid_caller" == bash || "$_lucid_caller" == */bash || "$_lucid_caller" == -bash ]]; then
        _lucid_caller=""
    fi
    lucid_init_repo_paths "$_lucid_caller" || return 1
    unset _lucid_caller
fi
