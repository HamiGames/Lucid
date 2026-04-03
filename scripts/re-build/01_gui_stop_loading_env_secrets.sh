#!/usr/bin/env bash
set -euo pipefail

# Goal:
# - Make it ILLEGAL for GUI stacks to load configs/environment/.env.secrets
# - Patch known GUI compose files to remove `.env.secrets` env_file entries
# - Ensure GUI services only carry non-secret connection endpoints
#
# Scope:
# - User-point/GUI compose only. Passing MODE=check here does not clear
#   scripts/re-build/02_compose_move_secrets_to_compose_secrets.sh MODE=check, which also
#   requires backend/integration stacks to stop referencing .env.secrets.
#
# Safety:
# - Creates timestamped .bak backups of modified files
# - Does NOT print secret values

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00_rebuild_lib.sh
source "$here/00_rebuild_lib.sh"

require_cmd grep sed find

MODE="${MODE:-patch}"          # patch | check

# Optional GUI scan roots: EXTRA_GUI_SCAN_DIRS (see 00_rebuild_lib.sh)
# compose_files from configs/alignment-mats/gui-services.json are always included when present.

gather_gui_candidate_files() {
  local root="$project_root"
  local -a scan_dirs=(
    "$root/infrastructure/containers/gui"
    "$root/configs/container/gui"
    "$root/electron_gui"
    "$root/infrastructure/containers/electron_gui"
    "$root/configs/container/electron_gui"
    "$root/infrastructure/containers/node"
    "$root/configs/container/node"
    "$root/configs/docker"
    "$root/gui_api_bridge"
  )

  # Append caller-specified scan dirs.
  if [[ -n "$EXTRA_GUI_SCAN_DIRS" ]]; then
    local IFS=":"
    local d
    for d in $EXTRA_GUI_SCAN_DIRS; do
      if [[ "$d" == /* || "$d" == [A-Za-z]:/* ]]; then
        scan_dirs+=("$d")
      else
        scan_dirs+=("$root/$d")
      fi
    done
  fi

  local j cf d
  j="$(gui_services_json_path)"
  {
    if [[ -f "$j" ]] && command -v python >/dev/null 2>&1; then
      while IFS= read -r cf; do
        [[ -z "$cf" ]] && continue
        # compose_files entries are file paths (not dirs); emit explicitly for candidates.
        [[ -f "$root/$cf" ]] && printf '%s\n' "$root/$cf"
      done < <(python "$_rebuild_lib_dir/gui_alignment.py" list-gui-compose-files "$root" "$j" 2>/dev/null || true)
    fi

    # Full recursive tree: infrastructure/containers/services/**/*.yml|yaml (see 00_rebuild_lib.sh).
    list_infrastructure_containers_services_yaml_files

    local svc_dir
    for svc_dir in "$root/configs/services" "$root/configs/integration"; do
      [[ -d "$svc_dir" ]] || continue
      find "$svc_dir" -type f ! -name "*.bak.*" \( -name "*.yml" -o -name "*.yaml" \) 2>/dev/null
    done

    for d in "${scan_dirs[@]}"; do
      [[ -d "$d" ]] || continue
      # Prefer compose-like names; also include the special-case gui_api_bridge/docker-compose.yml.
      find "$d" -maxdepth 2 -type f \( \
        -name "docker-compose*.yml" -o -name "docker-compose*.yaml" -o \
        -name "*gui*.yml" -o -name "*gui*.yaml" -o \
        -name "docker-compose.yml" -o -name "docker-compose.yaml" \
      \) 2>/dev/null
    done

    # Always include gui_api_bridge/docker-compose.yml if present (direct user-point bridge).
    if [[ -f "$root/gui_api_bridge/docker-compose.yml" ]]; then
      printf '%s\n' "$root/gui_api_bridge/docker-compose.yml"
    fi
  } | sort -u
}

patch_gui_compose_file() {
  local f="$1"

  local is_bridge=0
  if [[ "$f" == *"/gui_api_bridge/docker-compose.yml" ]]; then
    is_bridge=1
  fi
  if [[ "$is_bridge" -eq 0 ]] && ! has_env_secrets_ref "$f"; then
    return 0
  fi

  backup_file "$f"

  # Normalize CRLF → LF so sed regex `$` matches correctly in Git Bash on Windows.
  safe_sed_inplace "s/\r$//" "$f"

  # 1) Remove env_file entries that reference `.env.secrets` (common patterns).
  # Handles both:
  #   - ../../../configs/environment/.env.secrets
  #   - ../../configs/environment/.env.secrets
  safe_sed_inplace "/^[[:space:]]*-[[:space:]]+.*configs\/environment\/\.env\.secrets[[:space:]]*$/d" "$f"
  safe_sed_inplace "/^[[:space:]]*-[[:space:]]+.*configs\\\\environment\\\\\\.env\\.secrets[[:space:]]*$/d" "$f"
  safe_sed_inplace "/^[[:space:]]*-[[:space:]]+.*\\/\\.env\\.secrets[[:space:]]*$/d" "$f"

  # 2) Remove bind-mounts that mount `.env.secrets` into container.
  # Example:
  #   - ../../../configs/environment/.env.secrets:/app/configs/.env.secrets:ro
  safe_sed_inplace "/^[[:space:]]*-[[:space:]]+.*configs\/environment\/\.env\.secrets:.*$/d" "$f"
  safe_sed_inplace "/^[[:space:]]*-[[:space:]]+.*configs\\\\environment\\\\\\.env\\.secrets:.*$/d" "$f"
  safe_sed_inplace "/^[[:space:]]*-[[:space:]]+.*\/\.env\.secrets:.*$/d" "$f"

  safe_sed_inplace "/^[[:space:]]*secrets:[[:space:]].*\.env\.secrets/d" "$f"
  safe_sed_inplace "/^[[:space:]]*secrets:[[:space:]].*configs\\/environment\\/\\.env\\.secrets/d" "$f"
  safe_sed_inplace "/^[[:space:]]*-[[:space:]]+LUCID_ENV_SECRETS_FILE=.*\\.env\\.secrets/d" "$f"

  remove_longform_compose_env_secrets_binds "$f"

  # 2b) Electron GUI uses YAML anchor lists (x-env-electron) which include .env.secrets.
  # These appear as plain list items, so the deletions above cover them.

  # 2c) gui_api_bridge is direct-accessible and must not carry JWT/db secrets.
  # Strip sensitive env var lines if present (best-effort).
  if [[ "$is_bridge" -eq 1 ]]; then
    # Use broad literal matches (robust against indentation/list styles).
    safe_sed_inplace "/JWT_SECRET_KEY=/d" "$f"
    safe_sed_inplace "/MONGODB_URL=/d" "$f"
    safe_sed_inplace "/REDIS_URL=/d" "$f"
    safe_sed_inplace "/MONGODB_PASSWORD/d" "$f"
    safe_sed_inplace "/REDIS_PASSWORD/d" "$f"
  fi

  # 3) Intentional: do NOT auto-inject environment values.
  # This avoids brittle YAML edits and prevents sed escaping issues on URLs.
}

main() {
  local root="$project_root"
  log_info "Repo root: $root"
  log_info "Mode: $MODE"

  local -a candidates=()
  while IFS= read -r f; do
    # We still run through `is_gui_compose_file` to avoid accidental patching of unrelated YAML.
    if is_gui_compose_file "$f"; then
      candidates+=("$f")
    fi
  done < <(gather_gui_candidate_files)

  if [[ "${#candidates[@]}" -eq 0 ]]; then
    die "No GUI/user-point compose files found in scan roots"
  fi

  local found=0
  local f
  for f in "${candidates[@]}"; do
    if [[ "$f" == *"/gui_api_bridge/docker-compose.yml" ]]; then
      # Always patch the bridge: it must not carry JWT/DB secrets even if it doesn't reference .env.secrets.
      log_warn "User-point bridge will be scrubbed: $(print_relpath "$f")"
      if [[ "$MODE" == "patch" ]]; then
        patch_gui_compose_file "$f"
        log_ok "Patched: $(print_relpath "$f")"
      fi
      continue
    fi

    if has_env_secrets_ref "$f"; then
      found=1
      log_warn "GUI compose references .env.secrets: $(print_relpath "$f")"
      if [[ "$MODE" == "patch" ]]; then
        patch_gui_compose_file "$f"
        if has_env_secrets_ref "$f"; then
          die "Patch incomplete (still references .env.secrets): $(print_relpath "$f")"
        else
          log_ok "Patched: $(print_relpath "$f")"
        fi
      fi
    fi
  done

  if [[ "$MODE" == "check" ]]; then
    if [[ "$found" -eq 1 ]]; then
      die "GUI stacks must NOT load .env.secrets (check failed)"
    fi
    log_ok "No GUI stacks load .env.secrets"
  else
    log_ok "GUI patch pass complete"
  fi
}

main "$@"

