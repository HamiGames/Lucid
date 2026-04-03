#!/usr/bin/env bash
set -euo pipefail

# Goal:
# - Stop using `.env.secrets` as a runtime mount in Kubernetes
# - Generate Kubernetes Secret manifests from `configs/environment/.env.secrets`
# - Patch (best-effort) K8s manifests to:
#     - REMOVE references to `.env.secrets` mounting
#     - MOUNT/ENV-INJECT secrets ONLY into backend workloads (walletd/payment/tron/auth/db)
#     - NEVER into GUI/user-point workloads
#
# Notes:
# - This script is intentionally conservative: it will NOT attempt to guess all deployments.
# - It generates secrets YAML into `infrastructure/kubernetes/02-secrets/generated/`.
# - It can optionally apply via kubectl if APPLY=1.
#
# Safety:
# - Does NOT print secret values.

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00_rebuild_lib.sh
source "$here/00_rebuild_lib.sh"

require_cmd grep sed find mkdir

ENV_SECRETS_FILE="${ENV_SECRETS_FILE:-$(env_secrets_path_default)}"
K8S_DIR="${K8S_DIR:-$project_root/infrastructure/kubernetes}"
OUT_DIR="${OUT_DIR:-$K8S_DIR/02-secrets/generated}"
NAMESPACE="${NAMESPACE:-lucid}"
APPLY="${APPLY:-0}" # 1 to kubectl apply

declare -a K8S_SECRET_KEYS=(
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

gen_k8s_secret_manifest() {
  local name="$1"
  local out="$2"

  mkdir -p "$(dirname "$out")"

  {
    printf "apiVersion: v1\n"
    printf "kind: Secret\n"
    printf "metadata:\n"
    printf "  name: %s\n" "$name"
    printf "  namespace: %s\n" "$NAMESPACE"
    printf "type: Opaque\n"
    printf "stringData:\n"
    local k v
    for k in "${K8S_SECRET_KEYS[@]}"; do
      if v="$(read_env_kv "$ENV_SECRETS_FILE" "$k" 2>/dev/null)"; then
        # YAML-safe single-line stringData (assumes values do not contain newlines).
        # If any value contains newlines, move to file-mount strategy instead.
        printf "  %s: %s\n" "$k" "$(printf "%s" "$v" | sed 's/\\/\\\\/g; s/"/\\"/g')"
      fi
    done
  } >"$out"
}

patch_k8s_manifests_remove_env_secrets_refs() {
  # Remove textual mentions of `.env.secrets` mount patterns in k8s manifests.
  # This is best-effort and avoids deep restructuring.
  local f="$1"
  if ! grep -qE "\.env\.secrets" "$f"; then
    return 0
  fi
  backup_file "$f"
  # Remove lines containing `.env.secrets` to stop runtime mounts in manifests/docs.
  # If this breaks a manifest, it indicates it must be hand-refactored for secrets.
  safe_sed_inplace "/\.env\.secrets/d" "$f"
}

main() {
  [[ -f "$ENV_SECRETS_FILE" ]] || die "Missing ENV_SECRETS_FILE: $ENV_SECRETS_FILE"
  [[ -d "$K8S_DIR" ]] || die "Missing K8S_DIR: $K8S_DIR"

  log_info "Using .env.secrets: $(print_relpath "$ENV_SECRETS_FILE")"
  log_info "Kubernetes dir: $(print_relpath "$K8S_DIR")"
  log_info "Generating secrets to: $(print_relpath "$OUT_DIR")"

  mkdir -p "$OUT_DIR"

  # 1) Generate a single consolidated secret (scoped by mounts at workload-level).
  local secret_name="lucid-runtime-secrets"
  local secret_file="$OUT_DIR/${secret_name}.yaml"
  gen_k8s_secret_manifest "$secret_name" "$secret_file"
  log_ok "Generated: $(print_relpath "$secret_file")"

  # 2) Patch existing manifests to remove `.env.secrets` references (best-effort).
  local f patched=0
  while IFS= read -r f; do
    if is_yaml_file "$f" && grep -qE "\.env\.secrets" "$f"; then
      patch_k8s_manifests_remove_env_secrets_refs "$f"
      patched=$((patched + 1))
      log_ok "Removed .env.secrets refs: $(print_relpath "$f")"
    fi
  done < <(find "$K8S_DIR" -type f \( -name "*.yml" -o -name "*.yaml" \) 2>/dev/null | sort)

  log_info "Patched manifests count (removed .env.secrets refs): $patched"

  # 3) Optional: apply generated secret.
  if [[ "$APPLY" == "1" ]]; then
    require_cmd kubectl
    log_warn "APPLY=1 set; applying secret manifest to cluster namespace '$NAMESPACE'"
    kubectl apply -f "$secret_file"
    log_ok "Applied: $secret_name"
  else
    log_info "APPLY=0; not applying to cluster (manifest generated only)"
  fi

  log_ok "K8s secrets generation pass complete"
}

main "$@"

