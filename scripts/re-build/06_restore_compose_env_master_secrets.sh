#!/usr/bin/env bash
set -euo pipefail

# Restore env_file + volume bind-mounts for configs/environment/.env.master and
# .env.secrets on every non-GUI service (GUI = compose_service + compose_files in
# configs/alignment-mats/gui-services.json). Paths are computed relative to each
# compose file (same idea as ../../configs/... under infrastructure/compose/).
#
# Usage:
#   MODE=check bash scripts/re-build/06_restore_compose_env_master_secrets.sh
#   MODE=patch bash scripts/re-build/06_restore_compose_env_master_secrets.sh
#
# Requires: python3 + PyYAML (pip install pyyaml)
# Override mat: GUI_SERVICES_JSON=/path/to/gui-services.json
#
# Compose paths are passed on stdin to Python (--stdin) so Windows does not hit argv length limits.
# Timestamped .bak.* copies are created only for files that are actually modified (see gui_alignment.py),
# unless REBUILD_SKIP_BACKUP=1.

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00_rebuild_lib.sh
source "$here/00_rebuild_lib.sh"

require_cmd python

MODE="${MODE:-patch}" # patch | check

json="$(gui_services_json_path)"
[[ -f "$json" ]] || die "Missing alignment mat: $json"

python -c "import yaml" 2>/dev/null || die "PyYAML required (pip install pyyaml)"

main() {
  log_info "Alignment mat: $(print_relpath "$json")"
  log_info "Mode: $MODE"

  local -a files=()
  while IFS= read -r f; do
    files+=("$f")
  done < <(list_compose_files)

  if [[ "${#files[@]}" -eq 0 ]]; then
    log_warn "No compose files from list_compose_files"
    return 0
  fi

  local py=(python "$_rebuild_lib_dir/gui_alignment.py" restore --stdin)
  if [[ "$MODE" == "check" ]]; then
    py+=(--check)
  fi
  py+=("$project_root" "$json")

  local st=0
  printf '%s\n' "${files[@]}" | "${py[@]}" || st=$?
  if [[ "$st" -eq 0 ]]; then
    if [[ "$MODE" == "check" ]]; then
      log_ok "All non-GUI services have .env.master / .env.secrets env_file + volume wiring"
    else
      log_ok "Restore pass complete (non-GUI services)"
    fi
    return 0
  fi
  if [[ "$MODE" == "check" && "$st" -eq 1 ]]; then
    die "Check failed (non-GUI services missing env_file/volumes; see stderr above)"
  fi
  if [[ "$st" -eq 3 ]]; then
    die "Restore had per-file errors (YAML/IO); see stderr above"
  fi
  die "restore failed (python exit $st)"
}

main "$@"
