#!/usr/bin/env bash
set -euo pipefail

# File: scripts/re-build/07_gui_scrub_python_env_secrets.sh
# Directory: scripts/re-build
#
# Goal:
# - Remove every ``.env.secrets`` reference from Python under GUI integration services
#   named in configs/alignment-mats/gui-services.json (see gui_scrub_python_env_secrets.py).
# - Rewrite remaining mentions to API-gateway SSH / API-key style env vars (no legacy filename).
#
# Safety:
# - Timestamped ``*.bak.<UTC>`` per changed file (unless REBUILD_SKIP_BACKUP=1)
# - Does not read or print secret values
#
# Optional:
#   GUI_SCRUB_EXTRA_ROOTS — extra repo-relative dirs to scan (; or : separated).
#   GUI_SCRUB_LIST_ROOTS=1 — print resolved scan roots to stderr.
#
# Usage (repo root or any cwd):
#   bash scripts/re-build/07_gui_scrub_python_env_secrets.sh
#   MODE=check bash scripts/re-build/07_gui_scrub_python_env_secrets.sh

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00_rebuild_lib.sh
source "$here/00_rebuild_lib.sh"

require_cmd python

MODE="${MODE:-patch}"

json="$(gui_services_json_path)"
log_info "Repo root: $project_root"
log_info "Mode: $MODE"
log_info "GUI services mat: $(print_relpath "$json")"

if [[ ! -f "$json" ]]; then
  die "Missing gui-services.json: $json"
fi

if python "$here/gui_scrub_python_env_secrets.py" \
  --mode "$MODE" \
  --project-root "$project_root" \
  --gui-services-json "$json"; then
  if [[ "$MODE" == "check" ]]; then
    log_ok "GUI-service Python sources contain no .env.secrets references"
  else
    log_ok "GUI-service Python env_secrets scrub pass complete"
  fi
else
  ec=$?
  if [[ "$MODE" == "check" && "$ec" -eq 1 ]]; then
    die "GUI-service Python still references .env.secrets (check failed)"
  fi
  exit "$ec"
fi
