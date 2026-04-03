#!/usr/bin/env bash
set -euo pipefail

# Goal:
# - Stop JWT_SECRET_KEY from appearing in user-point / GUI configs (same notion of “GUI” as
#   configs/alignment-mats/gui-services.json + is_gui_compose_file in 00_rebuild_lib.sh).
# - Optional strict mode: require only auth-service paths to mention JWT_SECRET_KEY (HS256
#   introspection / asymmetric target architecture).
#
# Default (JWT_STRICT_AUTH_ONLY=0):
#   - CHECK: fail only if JWT_SECRET_KEY appears under GUI/user-point paths.
#   - PATCH: remove JWT_SECRET_KEY lines only from those user-point files (never bulk-strip backends).
#
# Strict (JWT_STRICT_AUTH_ONLY=1):
#   - Also fail/warn when non-auth paths reference JWT_SECRET_KEY (legacy behavior).
#
# IMPORTANT:
# - This script does NOT implement asymmetric signing inside services (code change required).

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00_rebuild_lib.sh
source "$here/00_rebuild_lib.sh"

require_cmd grep sed find

TARGET_MODE="${TARGET_MODE:-introspection}" # introspection | asymmetric
MODE="${MODE:-check}"                      # check | patch

# 0 = GUI boundary only (recommended with compose top-level secrets: + multi-service HS256).
# 1 = only paths matching auth may reference JWT_SECRET_KEY (strict sprawl / future introspection).
JWT_STRICT_AUTH_ONLY="${JWT_STRICT_AUTH_ONLY:-0}"

JWT_SECRET_KEY_NAME="JWT_SECRET_KEY"
declare -a PUBLIC_JWT_HINTS=(
  "JWT_PUBLIC_KEY"
  "JWKS_URL"
)

is_user_point_path() {
  is_gui_compose_file "$1"
}

is_auth_service_path() {
  local f="$1"
  echo "$f" | grep -qiE "auth|lucid-auth-service"
}

patch_remove_jwt_secret_key_refs() {
  local f="$1"
  backup_file "$f"

  # Remove env var assignment lines for JWT_SECRET_KEY in compose/k8s yaml.
  # Compose:
  #   - JWT_SECRET_KEY=${JWT_SECRET_KEY}
  safe_sed_inplace "/^[[:space:]]*-[[:space:]]*${JWT_SECRET_KEY_NAME}=.*$/d" "$f"

  # K8s env blocks:
  #   - name: JWT_SECRET_KEY
  #     valueFrom: ...
  safe_sed_inplace "/^[[:space:]]*-[[:space:]]*name:[[:space:]]*${JWT_SECRET_KEY_NAME}[[:space:]]*$/d" "$f"
  safe_sed_inplace "/^[[:space:]]*name:[[:space:]]*${JWT_SECRET_KEY_NAME}[[:space:]]*$/d" "$f"
  safe_sed_inplace "/^[[:space:]]*valueFrom:[[:space:]]*$/d" "$f"
  safe_sed_inplace "/^[[:space:]]*secretKeyRef:[[:space:]]*$/d" "$f"
  safe_sed_inplace "/^[[:space:]]*key:[[:space:]]*jwt-secret.*$/d" "$f"
}

check_file_for_jwt_secret_sprawl() {
  local f="$1"
  if ! grep -qE "${JWT_SECRET_KEY_NAME}" "$f"; then
    return 0
  fi

  # JWT_SECRET_KEY must NOT appear in user-point paths.
  if is_user_point_path "$f"; then
    log_err "JWT secret present in USER-POINT config: $(print_relpath "$f")"
    _jwt_sprawl_show_matches "$f"
    return 1
  fi

  # Optional: full sprawl — only auth-service paths may reference JWT_SECRET_KEY.
  if [[ "$JWT_STRICT_AUTH_ONLY" == "1" ]] && [[ "$TARGET_MODE" == "introspection" || "$TARGET_MODE" == "asymmetric" ]]; then
    if ! is_auth_service_path "$f"; then
      log_warn "JWT secret present outside auth-service (should be removed): $(print_relpath "$f")"
      _jwt_sprawl_show_matches "$f"
      return 2
    fi
  fi

  return 0
}

# Avoid dumping literal secret values from generated K8s Secret stringData.
_jwt_sprawl_show_matches() {
  local f="$1"
  if [[ "$f" == *"/02-secrets/generated/"* ]] || [[ "$f" == *"lucid-runtime-secrets"* ]]; then
    log_err "  (matches omitted: file may contain plaintext secret values under stringData)"
    return 0
  fi
  grep -nE "${JWT_SECRET_KEY_NAME}" "$f" | head -n 5 | sed 's/^/  /'
}

check_public_jwt_material_presence() {
  # If asymmetric mode, ensure we at least have configuration hints for public verification.
  # This doesn't enforce correctness; it just ensures configs mention a public mechanism.
  local f="$1"
  local ok=0
  local k
  for k in "${PUBLIC_JWT_HINTS[@]}"; do
    if grep -qE "$k" "$f"; then
      ok=1
      break
    fi
  done
  return "$ok"
}

main() {
  log_info "TARGET_MODE: $TARGET_MODE"
  log_info "MODE: $MODE"
  log_info "JWT_STRICT_AUTH_ONLY: $JWT_STRICT_AUTH_ONLY (0=GUI boundary only; 1=auth-only paths for JWT)"

  local root="$project_root"
  local -a files=()

  while IFS= read -r f; do
    # Limit to config-like files for speed/safety.
    case "$f" in
      *.yml|*.yaml|*.env) files+=("$f") ;;
    esac
  done < <(find "$root/infrastructure" "$root/configs"  -type f 2>/dev/null | sort)

  local violations=0
  local f
  for f in "${files[@]}"; do
    if grep -qE "${JWT_SECRET_KEY_NAME}" "$f"; then
      if [[ "$MODE" == "patch" ]]; then
        # Only scrub user-point/GUI files — never strip JWT from backend compose in bulk.
        if is_user_point_path "$f"; then
          patch_remove_jwt_secret_key_refs "$f"
        fi
      fi

      if ! check_file_for_jwt_secret_sprawl "$f"; then
        violations=$((violations + 1))
      fi
    fi
  done

  if [[ "$TARGET_MODE" == "asymmetric" ]]; then
    # Best-effort warning if no public-key/jwks configuration exists anywhere.
    local any_public=0
    for f in "${files[@]}"; do
      if check_public_jwt_material_presence "$f"; then
        any_public=1
        break
      fi
    done
    if [[ "$any_public" -eq 0 ]]; then
      log_warn "Asymmetric mode selected, but no JWT_PUBLIC_KEY/JWKS_URL found in configs yet."
      log_warn "Code/config changes required: auth must publish public key/JWKS and services must verify using it."
    fi
  fi

  if [[ "$violations" -gt 0 ]]; then
    die "JWT secret sprawl violations detected: $violations"
  fi

  log_ok "JWT sprawl guardrails satisfied"
}

main "$@"

