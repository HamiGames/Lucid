#!/usr/bin/env bash
set -euo pipefail

_rebuild_color() {
  local code="$1"; shift
  if [[ -t 1 ]]; then
    printf "\033[%sm%s\033[0m\n" "$code" "$*"
  else
    printf "%s\n" "$*"
  fi
}

log_info() { _rebuild_color "34" "[INFO] $*"; }
log_ok() { _rebuild_color "32" "[ OK ] $*"; }
log_warn() { _rebuild_color "33" "[WARN] $*"; }
log_err() { _rebuild_color "31" "[ERR ] $*"; }

die() { log_err "$*"; exit 1; }

require_cmd() {
  local c
  for c in "$@"; do
    command -v "$c" >/dev/null 2>&1 || die "Missing required command: $c"
  done
}

repo_root() {
  # Prefer git root; fallback to script's grandparent.
  if command -v git >/dev/null 2>&1; then
    local r
    r="$(git rev-parse --show-toplevel 2>/dev/null || true)"
    if [[ -n "$r" ]]; then
      printf "%s\n" "$r"
      return 0
    fi
  fi
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  printf "%s\n" "$(cd "$here/../.." && pwd)"
}

project_root="$(repo_root)"

# Directory of this file (scripts/re-build/) when sourced from sibling *.sh.
_rebuild_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Normalize backslashes to / so path heuristics match Git Bash / MSYS output.
rebuild_norm_path() {
  printf '%s\n' "${1//\\//}"
}

# Alignment mat for GUI compose + service names (optional override).
# Used first by is_gui_compose_file() before path heuristics.
GUI_SERVICES_JSON="${GUI_SERVICES_JSON:-}"

gui_services_json_path() {
  if [[ -n "$GUI_SERVICES_JSON" ]]; then
    if [[ "$GUI_SERVICES_JSON" == /* || "$GUI_SERVICES_JSON" == [A-Za-z]:/* ]]; then
      printf '%s\n' "$GUI_SERVICES_JSON"
    else
      printf '%s\n' "$project_root/${GUI_SERVICES_JSON#./}"
    fi
    return 0
  fi
  printf '%s\n' "$project_root/configs/alignment-mats/gui-services.json"
}

# Set REBUILD_SKIP_BACKUP=1 to skip timestamped .bak.* copies (less disk clutter; no rollback snapshot).
REBUILD_SKIP_BACKUP="${REBUILD_SKIP_BACKUP:-0}"

# Optional: extra directories (colon-separated) that hold GUI / user-point compose/workloads.
# Relative entries resolve under project_root; absolute paths are used as-is.
# Example: EXTRA_GUI_SCAN_DIRS="apps/gui-admin:apps/gui-user"
EXTRA_GUI_SCAN_DIRS="${EXTRA_GUI_SCAN_DIRS:-}"

gui_userpoint_compose_scan_roots() {
  local root="$project_root"
  printf '%s\n' "$root/electron_gui"
  printf '%s\n' "$root/gui_api_bridge"
  if [[ -n "$EXTRA_GUI_SCAN_DIRS" ]]; then
    local IFS=':'
    local d
    for d in $EXTRA_GUI_SCAN_DIRS; do
      [[ -z "$d" ]] && continue
      if [[ "$d" == /* || "$d" == [A-Za-z]:/* ]]; then
        printf '%s\n' "$d"
      else
        printf '%s\n' "$root/${d#./}"
      fi
    done
  fi
}

# Path-level + alignment-mat (configs/alignment-mats/gui-services.json compose_files).
# Files listed there are treated as GUI stacks before legacy path rules.
is_gui_compose_file() {
  local f_raw="$1"
  local f
  f="$(rebuild_norm_path "$f_raw")"
  local json
  json="$(gui_services_json_path)"
  if [[ -f "$json" ]] && command -v python >/dev/null 2>&1; then
    if python "$_rebuild_lib_dir/gui_alignment.py" is-gui-compose-file "$f_raw" "$project_root" "$json" >/dev/null; then
      return 0
    fi
  fi

  if [[ "$f" == *"/infrastructure/containers/gui/"* ]]; then
    return 0
  fi
  if [[ "$f" == *"/configs/container/gui/"* ]]; then
    return 0
  fi
  if [[ "$f" == *"/infrastructure/containers/electron_gui/"* ]]; then
    return 0
  fi
  if [[ "$f" == *"/configs/container/electron_gui/"* ]]; then
    return 0
  fi
  if [[ "$f" == *"/electron_gui/"* ]]; then
    return 0
  fi
  if [[ "$f" == *"/gui_api_bridge/"* ]]; then
    return 0
  fi
  if [[ "$f" == *"/apps/gui-"* ]]; then
    return 0
  fi
  if [[ "$f" == *"/infrastructure/containers/node/"* && "$f" == *"gui"* ]]; then
    return 0
  fi
  if [[ "$f" == *"/configs/container/node/"* && "$f" == *"gui"* ]]; then
    return 0
  fi
  # Service-definition YAMLs under configs/services/ and containers/services/ (not always named docker-compose*.yml).
  if [[ "$f" == *"/configs/services/gui-"* ]]; then
    return 0
  fi
  if [[ "$f" == *"/infrastructure/containers/services/gui-"* ]]; then
    return 0
  fi
  if [[ "$f" == *"/configs/services/admin-interface"* ]]; then
    return 0
  fi
  if [[ "$f" == *"/configs/services/user-interface"* ]]; then
    return 0
  fi
  if [[ "$f" == *"/infrastructure/containers/services/admin-interface"* ]]; then
    return 0
  fi
  if [[ "$f" == *"/infrastructure/containers/services/user-interface"* ]]; then
    return 0
  fi

  if [[ -n "$EXTRA_GUI_SCAN_DIRS" ]]; then
    local IFS=':'
    local d abs
    for d in $EXTRA_GUI_SCAN_DIRS; do
      [[ -z "$d" ]] && continue
      if [[ "$d" == /* || "$d" == [A-Za-z]:/* ]]; then
        abs="$d"
      else
        abs="$project_root/${d#./}"
      fi
      abs="$(rebuild_norm_path "$abs")"
      if [[ "$f" == "$abs" || "$f" == "$abs/"* ]]; then
        return 0
      fi
    done
  fi

  return 1
}

env_secrets_path_default() {
  printf "%s\n" "$project_root/configs/environment/.env.secrets"
}

read_env_kv() {
  # Usage: read_env_kv <file> <KEY>
  # Prints value without KEY= prefix, preserving everything after first '='.
  local file="$1"
  local key="$2"
  [[ -f "$file" ]] || die "Missing env file: $file"
  local line
  line="$(grep -E "^[[:space:]]*${key}=" "$file" | head -n 1 || true)"
  [[ -n "$line" ]] || return 1
  printf "%s\n" "${line#*=}"
}

write_secret_file() {
  # Usage: write_secret_file <out_file> <value>
  # Writes exactly the value + newline; chmod 600 best-effort.
  local out="$1"
  local val="$2"
  mkdir -p "$(dirname "$out")"
  umask 077
  printf "%s\n" "$val" >"$out"
  chmod 600 "$out" 2>/dev/null || true
}

is_yaml_file() {
  case "$1" in
    *.yml|*.yaml) return 0 ;;
    *) return 1 ;;
  esac
}

# True if YAML looks like Docker Compose (named docker-compose* / *.compose.yml or top-level "services:" key).
is_docker_compose_like() {
  local f="$1"
  [[ -f "$f" ]] || return 1
  case "$(basename "$f")" in
    docker-compose*.yml|docker-compose*.yaml|*.compose.yml|*.compose.yaml) return 0 ;;
  esac
  grep -qE '^[[:space:]]*services:[[:space:]]*($|#)' "$f" 2>/dev/null
}

# Every *.yml / *.yaml under infrastructure/containers/services (full recursive tree;
# distroless/, multi-stage/, payment_services/, x_lucid_cluster_calibration/, etc.).
list_infrastructure_containers_services_yaml_files() {
  local base="$project_root/infrastructure/containers/services"
  [[ -d "$base" ]] || return 0
  find "$base" -type f ! -name "*.bak.*" \( -name "*.yml" -o -name "*.yaml" \) 2>/dev/null
}

list_compose_files() {
  # Compose-named files under known roots + all service-definition YAML in explicit trees.
  local base="$project_root"
  local -a roots=(
    "$base/infrastructure/compose"
    "$base/infrastructure/docker"
    "$base/infrastructure/containers"
    "$base/configs"
  )
  local r
  while IFS= read -r r; do
    [[ -d "$r" ]] && roots+=("$r")
  done < <(gui_userpoint_compose_scan_roots)

  local sd
  {
    find "${roots[@]}" \
      -type f ! -name "*.bak.*" \
      \( -name "docker-compose*.yml" -o -name "docker-compose*.yaml" -o -name "*.compose.yml" -o -name "*.compose.yaml" \) \
      2>/dev/null
    list_infrastructure_containers_services_yaml_files
    for sd in "$base/configs/services" "$base/configs/integration"; do
      [[ -d "$sd" ]] || continue
      find "$sd" -type f ! -name "*.bak.*" \( -name "*.yml" -o -name "*.yaml" \) 2>/dev/null
    done
  } | sort -u
}

backup_file() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  if [[ "$REBUILD_SKIP_BACKUP" == "1" ]]; then
    return 0
  fi
  local ts
  ts="$(date -u +"%Y%m%dT%H%M%SZ")"
  cp -p "$f" "$f.bak.$ts"
}

safe_sed_inplace() {
  # GNU/BSD compatible sed -i wrapper.
  local script="$1"
  local file="$2"
  if sed --version >/dev/null 2>&1; then
    sed -i -E "$script" "$file"
  else
    sed -i '' -E "$script" "$file"
  fi
}

has_env_secrets_ref() {
  local file="$1"
  # Ignore comments; we only care about effective config usage.
  grep -E "\.env\.secrets" "$file" 2>/dev/null | grep -vE "^[[:space:]]*#" >/dev/null 2>&1
}

remove_longform_compose_env_secrets_binds() {
  # Compose long-form volume entries (source:/target:) are not matched by list-item sed rules.
  # Example:
  #   - type: bind
  #     source: ../../../configs/environment/.env.secrets
  #     target: ../../configs/environment/.env.secrets
  local f="$1"
  [[ -f "$f" ]] || return 0
  command -v python >/dev/null 2>&1 || return 0
  python -c "
import re, sys
path = sys.argv[1]
with open(path, newline='') as fp:
    lines = fp.readlines()
out = []
i, n = 0, len(lines)
while i < n:
    line = lines[i]
    m = re.match(r'^([ \\t]*)-\\s+type:\\s+bind\\s*\$', line)
    if not m:
        out.append(line)
        i += 1
        continue
    base = m.group(1)
    chunk = [line]
    i += 1
    while i < n:
        ln = lines[i]
        if ln.strip() == '':
            chunk.append(ln)
            i += 1
            continue
        if ln.startswith(base):
            tail = ln[len(base):]
            if re.match(r'-\\s', tail):
                break
        chunk.append(ln)
        i += 1
    if '.env.secrets' not in ''.join(chunk):
        out.extend(chunk)
with open(path, 'w', newline='') as fp:
    fp.writelines(out)
" "$f"
}

print_relpath() {
  local p="$1"
  if command -v python >/dev/null 2>&1; then
    # Use argv to avoid bash-incompatible `${var!r}` quoting.
    python -c "import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))" "$p" "$project_root"
  else
    printf "%s\n" "$p"
  fi
}

