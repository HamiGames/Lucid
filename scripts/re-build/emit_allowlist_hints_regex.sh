#!/usr/bin/env bash
set -euo pipefail

# Print a ready-to-paste ALLOWLIST_SERVICE_HINTS_REGEX= line for
# scripts/re-build/04_payment_backend_boundary_guards.sh.
#
# Builds alternation tokens from:
#   - fixed payment/backend hints
#   - configs/container/* and infrastructure/containers/* (excluding gui + electron_gui)
#   - parent directory names of each non-GUI compose file (list_compose_files + is_gui_compose_file)
#
# Tokens are regex-escaped for grep -E (see 04_* script).
#
# Usage (repo root):
#   bash scripts/re-build/emit_allowlist_hints_regex.sh
#   eval "$(bash scripts/re-build/emit_allowlist_hints_regex.sh)"

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00_rebuild_lib.sh
source "$here/00_rebuild_lib.sh"

declare -a tok=()

add_tok() {
  local t="$1"
  [[ -z "$t" ]] && return 0
  # bash 4+ lower-case
  t="${t,,}"
  tok+=("$t")
}

for s in \
  tron payment walletd wallet payout gateway \
  auth mongodb redis elasticsearch blockchain \
  server kubernetes k8s session sessions \
  storage database tor rdp admin base \
  manager worker engine registry chain \
  mesh "service-mesh" "service_mesh" distroless \
  devcontainer compose docker proxy intern external internal \
  anchoring merkle pipeline chunk api bridge; do
  add_tok "$s"
done

if [[ -d "$project_root/configs/container" ]]; then
  for d in "$project_root/configs/container"/*/; do
    [[ -d "$d" ]] || continue
    b="$(basename "$d")"
    [[ "$b" == gui || "$b" == electron_gui ]] && continue
    add_tok "$b"
  done
fi

if [[ -d "$project_root/infrastructure/containers" ]]; then
  for d in "$project_root/infrastructure/containers"/*/; do
    [[ -d "$d" ]] || continue
    b="$(basename "$d")"
    [[ "$b" == gui || "$b" == electron_gui ]] && continue
    add_tok "$b"
  done
fi

while IFS= read -r f; do
  is_gui_compose_file "$f" && continue
  add_tok "$(basename "$(dirname "$f")")"
done < <(list_compose_files)

if [[ -d "$project_root/infrastructure/service_mesh" ]]; then
  add_tok "service_mesh"
fi

printf '%s\n' "${tok[@]}" | sort -u | python -c "
import re, sys
lines = [
    ln.strip()
    for ln in sys.stdin
    if ln.strip() and not ln.strip().startswith('__')
]
pat = '|'.join(re.escape(t) for t in lines)
print('ALLOWLIST_SERVICE_HINTS_REGEX=\"' + pat + '\"')
"
