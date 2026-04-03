#!/usr/bin/env bash
set -euo pipefail

# Goal:
# - Enforce the "payment backend boundary":
#     - User-point containers (GUIs) must NEVER reference TRON_* or wallet/payment private keys.
#     - Only payment backend services may reference TRON secrets.
# - Provide quick scan + fail for secret leakage in compose + k8s manifests.
#
# This script does NOT modify code; it is an enforcement guardrail.

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00_rebuild_lib.sh
source "$here/00_rebuild_lib.sh"

require_cmd grep find

ALLOWLIST_SERVICE_HINTS_REGEX="${ALLOWLIST_SERVICE_HINTS_REGEX:-tron|payment|walletd|wallet|payout|gateway}"

declare -a SECRET_PATTERNS=(
  "TRON_PRIVATE_KEY"
  "TRON_API_KEY"
  "TRON_ADDRESS"
  "WALLET_ENCRYPTION_KEY"
)

is_user_point_path() {
  is_gui_compose_file "$1"
}

scan_path() {
  local base="$1"
  local found=0
  local f p

  while IFS= read -r f; do
    for p in "${SECRET_PATTERNS[@]}"; do
      if grep -nE "$p" "$f" >/dev/null 2>&1; then
        found=1
        if is_user_point_path "$f"; then
          log_err "Secret reference '$p' found in USER-POINT path: $(print_relpath "$f")"
          grep -nE "$p" "$f" | head -n 5 | sed 's/^/  /'
        else
          # If file is not user-point, ensure it looks like allowed backend service.
          if ! echo "$f" | grep -qiE "$ALLOWLIST_SERVICE_HINTS_REGEX"; then
            log_warn "Secret reference '$p' found outside allowlist-hinted backend path: $(print_relpath "$f")"
            grep -nE "$p" "$f" | head -n 5 | sed 's/^/  /'
          fi
        fi
      fi
    done
  done < <(find "$base" -type f \( -name "*.yml" -o -name "*.yaml" -o -name "*.env" -o -name "*.sh" -o -name "*.py" -o -name "*.md" \) 2>/dev/null | sort)

  return "$found"
}

main() {
  local root="$project_root"
  log_info "Scanning repo for payment secret leakage: $root"

  local leaked=0
  if scan_path "$root"; then
    leaked=1
  fi

  if [[ "$leaked" -eq 1 ]]; then
    die "Payment backend boundary violated: TRON/WALLET secret references found in forbidden locations"
  fi
  log_ok "No payment secret leakage detected in user-point paths"
}

main "$@"

