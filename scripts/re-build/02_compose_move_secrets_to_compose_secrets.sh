#!/usr/bin/env bash
set -euo pipefail

# Goal:
# - Stop distributing secrets via configs/environment/.env.secrets to every container
# - Convert to per-secret files usable with Docker Compose `secrets:` (file-based)
# - Patch compose files to:
#     - remove `.env.secrets` from env_file and volume mounts
#     - add `secrets:` mounts ONLY on backend services (never GUIs)
#
# IMPORTANT:
# - This script does best-effort patching of YAML text (not a YAML parser).
# - It is designed to be run iteratively; it creates backups before edits.
#
# Outputs:
# - Secret files under: configs/secrets/runtime/compose/*.secret
# - Patched compose files in-place (with timestamped .bak backups)
#
# Safety:
# - Does NOT print secret values.
#
# MODE=check vs 01_gui_stop_loading_env_secrets.sh:
# - Check fails if *any* scanned compose file still references .env.secrets (backends, integration, GUI, etc.).
# - 01_* only strips user-point/GUI compose. Seeing this check fail does not, by itself, mean 01 failed —
#   most repos still reference .env.secrets on backend stacks until you run MODE=patch here.
# Suggested order: MODE=patch scripts/re-build/01_gui_stop_loading_env_secrets.sh, then MODE=patch this script.
# GUI vs backend classification: configs/alignment-mats/gui-services.json (see 00_rebuild_lib.sh is_gui_compose_file).

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00_rebuild_lib.sh
source "$here/00_rebuild_lib.sh"

require_cmd grep sed find mkdir

ENV_SECRETS_FILE="${ENV_SECRETS_FILE:-$(env_secrets_path_default)}"
OUT_DIR="${OUT_DIR:-$project_root/configs/secrets/runtime/compose}"
MODE="${MODE:-patch}" # patch | check

# Secrets we expect in `.env.secrets` that should never reach user-point containers.
declare -a SECRET_KEYS=(
  "MONGODB_PASSWORD"
  "REDIS_PASSWORD"
  "JWT_SECRET_KEY"
  "ENCRYPTION_KEY"
  "SESSION_SECRET"
  "TRON_PRIVATE_KEY"
  "TRON_API_KEY"
  "API_GATEWAY_SECRET"
  "ELASTICSEARCH_PASSWORD"
  "TOR_PASSWORD"
  "TOR_CONTROL_PASSWORD"
  "WALLET_ENCRYPTION_KEY"
)

write_compose_secret_files() {
  log_info "Writing compose secret files to: $(print_relpath "$OUT_DIR")"
  mkdir -p "$OUT_DIR"

  local k v out
  for k in "${SECRET_KEYS[@]}"; do
    if v="$(read_env_kv "$ENV_SECRETS_FILE" "$k" 2>/dev/null)"; then
      out="$OUT_DIR/${k}.secret"
      write_secret_file "$out" "$v"
      log_ok "Prepared secret file: $(print_relpath "$out")"
    else
      log_warn "Key not found in .env.secrets (skipping secret file): $k"
    fi
  done
}

remove_env_secrets_refs_from_compose() {
  local f="$1"
  if ! has_env_secrets_ref "$f"; then
    return 0
  fi

backup_file "$f"

safe_sed_inplace "/^[[:space:]]*-[[:space:]]+.*configs\/environment\/\.env\.secrets[[:space:]]*$/d" "$f"
safe_sed_inplace "/^[[:space:]]*-[[:space:]]+.*\/\.env\.secrets[[:space:]]*$/d" "$f"
safe_sed_inplace "/^[[:space:]]*-[[:space:]]+.*configs\/environment\/\.env\.secrets:.*$/d" "$f"
safe_sed_inplace "/^[[:space:]]*-[[:space:]]+.*\/\.env\.secrets:.*$/d" "$f"

  # Mapping keys (e.g. config_files.secrets: path/to/.env.secrets) — not Compose list items.
  safe_sed_inplace "/^[[:space:]]*secrets:[[:space:]].*\.env\.secrets/d" "$f"
  safe_sed_inplace "/^[[:space:]]*secrets:[[:space:]].*configs\\/environment\\/\\.env\\.secrets/d" "$f"
  safe_sed_inplace "/^[[:space:]]*-[[:space:]]+LUCID_ENV_SECRETS_FILE=.*\\.env\\.secrets/d" "$f"

  # Long-form bind mounts (source:/target: under - type: bind).
  remove_longform_compose_env_secrets_binds "$f"
}

inject_top_level_secrets_block_if_missing() {
  local f="$1"
  # Never append a Compose "secrets:" block to non-Compose service YAML.
  if ! is_docker_compose_like "$f"; then
    return 0
  fi
  # Top-level Compose "secrets:" only (column 0); avoids false positives from nested keys like config_files.secrets.
  if grep -qE '^secrets:[[:space:]]*($|#)' "$f"; then
    return 0
  fi

backup_file "$f"

cat >>"$f" <<EOF

secrets:
  MONGODB_PASSWORD:
    file: ${OUT_DIR}/MONGODB_PASSWORD.secret
  REDIS_PASSWORD:
    file: ${OUT_DIR}/REDIS_PASSWORD.secret
  JWT_SECRET_KEY:
    file: ${OUT_DIR}/JWT_SECRET_KEY.secret
  ENCRYPTION_KEY:
    file: ${OUT_DIR}/ENCRYPTION_KEY.secret
  SESSION_SECRET:
    file: ${OUT_DIR}/SESSION_SECRET.secret
  TRON_PRIVATE_KEY:
    file: ${OUT_DIR}/TRON_PRIVATE_KEY.secret
  TRON_API_KEY:
    file: ${OUT_DIR}/TRON_API_KEY.secret
  API_GATEWAY_SECRET:
    file: ${OUT_DIR}/API_GATEWAY_SECRET.secret
  ELASTICSEARCH_PASSWORD:
    file: ${OUT_DIR}/ELASTICSEARCH_PASSWORD.secret
  TOR_PASSWORD:
    file: ${OUT_DIR}/TOR_PASSWORD.secret
  TOR_CONTROL_PASSWORD:
    file: ${OUT_DIR}/TOR_CONTROL_PASSWORD.secret
  WALLET_ENCRYPTION_KEY:
    file: ${OUT_DIR}/WALLET_ENCRYPTION_KEY.secret
EOF
}

warn_about_secret_env_vars() {
  local f="$1"
  local key
  for key in "${SECRET_KEYS[@]}"; do
    if grep -qE "${key}=" "$f"; then
      log_warn "Compose file still sets ${key}=... directly: $(print_relpath "$f")"
    fi
  done
}

main() {
  [[ -f "$ENV_SECRETS_FILE" ]] || die "Missing ENV_SECRETS_FILE: $ENV_SECRETS_FILE"
  log_info "Using .env.secrets: $(print_relpath "$ENV_SECRETS_FILE")"
  log_info "Mode: $MODE"

  if [[ "$MODE" == "patch" ]]; then
    write_compose_secret_files
  fi

  local -a files=()
  while IFS= read -r f; do
    files+=("$f")
  done < <(list_compose_files)

  local -a ref_files=()
  local f
  for f in "${files[@]}"; do
    if has_env_secrets_ref "$f"; then
      ref_files+=("$f")
    fi
  done

  if [[ "$MODE" == "check" ]]; then
    if [[ "${#ref_files[@]}" -gt 0 ]]; then
      log_err "Compose files still reference .env.secrets (${#ref_files[@]} file(s)):"
      for f in "${ref_files[@]}"; do
        if is_gui_compose_file "$f"; then
          log_err "  [user-point/GUI] $(print_relpath "$f")"
        else
          log_err "  [backend/other] $(print_relpath "$f")"
        fi
      done
      log_err "01_gui_stop_loading_env_secrets.sh only patches user-point/GUI paths — it does not migrate backend compose."
      log_err "To fix from repo root: MODE=patch bash scripts/re-build/02_compose_move_secrets_to_compose_secrets.sh"
      die "Compose .env.secrets check failed"
    fi
    log_ok "No compose files reference .env.secrets"
    return 0
  fi

  # MODE=patch
  for f in "${ref_files[@]}"; do
    # GUI files: strip .env.secrets only (no top-level secrets: block).
    if is_gui_compose_file "$f"; then
      remove_env_secrets_refs_from_compose "$f"
      if has_env_secrets_ref "$f"; then
        die "Failed removing .env.secrets from GUI compose: $(print_relpath "$f")"
      fi
      log_ok "Removed .env.secrets refs (GUI): $(print_relpath "$f")"
      continue
    fi

    remove_env_secrets_refs_from_compose "$f"
    inject_top_level_secrets_block_if_missing "$f"
    warn_about_secret_env_vars "$f"

    if has_env_secrets_ref "$f"; then
      die "Patch incomplete (still references .env.secrets): $(print_relpath "$f")"
    fi
    log_ok "Patched (removed .env.secrets + added secrets block): $(print_relpath "$f")"
  done

  log_ok "Compose secrets migration pass complete"
}

main "$@"

