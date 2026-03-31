#!/usr/bin/env bash
# _normalise_lucid_shell_headers.sh — add Lucid # headers after shebang + line 2
# File: /app/_normalise_lucid_shell_headers.sh
# x-lucid-file-path: /app/_normalise_lucid_shell_headers.sh
# x-lucid-file-directory: /app
# x-lucid-file-type: shell
# Same /app/... rules as _normalise_lucid_headers.py (map_repo_rel_to_app_paths + ROOTS).
#
# Repo root: directory containing this script (must also contain _normalise_lucid_headers.py).
# Run:  bash _normalise_lucid_shell_headers.sh
# Dry-run:  bash _normalise_lucid_shell_headers.sh --dry-run

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]] || [[ "${1:-}" == "-n" ]]; then
  DRY_RUN=1
fi

pick_python() {
  if [[ -n "${PYTHON:-}" ]] && command -v "${PYTHON}" >/dev/null 2>&1; then
    echo "${PYTHON}"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    echo python3
    return
  fi
  if command -v python >/dev/null 2>&1; then
    echo python
    return
  fi
  echo ""
}

# Prints TSV: absolute_filepath<TAB>app_path<TAB>x-lucid-file-directory
list_repo_sh_with_canonical() {
  local py="$1"
  REPO_ROOT="${REPO_ROOT}" "${py}" -c '
import os
import sys
from pathlib import Path

repo = Path(os.environ["REPO_ROOT"]).resolve()
sys.path.insert(0, str(repo))
from _normalise_lucid_headers import (  # noqa: E402
    _should_skip_py_path,
    resolve_lucid_app_path,
)

for p in sorted(repo.rglob("*.sh"), key=lambda x: str(x).lower()):
    if _should_skip_py_path(p, repo):
        continue
    app, parent = resolve_lucid_app_path(p, repo)
    print(f"{p}\t{app}\t{parent}")
'
}

process_one_sh() {
  local filepath="$1"
  local canonical="$2"
  local parent_dir="$3"
  local file_line path_line dir_line type_line
  local -a lines=()
  local i tmp

  file_line="# File: ${canonical}"
  path_line="# x-lucid-file-path: ${canonical}"
  dir_line="# x-lucid-file-directory: ${parent_dir}"
  type_line="# x-lucid-file-type: shell"

  mapfile -t lines < "$filepath" || return 0
  [[ ${#lines[@]} -eq 0 ]] && return 0

  if [[ "${lines[0]}" == $'\xef\xbb\xbf'* ]]; then
    lines[0]="${lines[0]#$'\xef\xbb\xbf'}"
  fi
  for i in "${!lines[@]}"; do
    lines[i]="${lines[$i]%$'\r'}"
  done

  if [[ ${#lines[@]} -ge 6 ]] \
    && [[ "${lines[2]}" == "$file_line" ]] \
    && [[ "${lines[3]}" == "$path_line" ]] \
    && [[ "${lines[4]}" == "$dir_line" ]] \
    && [[ "${lines[5]}" == "$type_line" ]]; then
    return 0
  fi

  local -a filtered=()
  for i in "${!lines[@]}"; do
    if [[ "${lines[$i]}" =~ ^[[:space:]]*#[[:space:]]*File:[[:space:]]*/app/ ]]; then
      continue
    fi
    if [[ "${lines[$i]}" =~ ^[[:space:]]*#[[:space:]]*x-lucid-file-path: ]]; then
      continue
    fi
    if [[ "${lines[$i]}" =~ ^[[:space:]]*#[[:space:]]*x-lucid-file-directory: ]]; then
      continue
    fi
    if [[ "${lines[$i]}" =~ ^[[:space:]]*#[[:space:]]*x-lucid-file-type: ]]; then
      continue
    fi
    filtered+=("${lines[$i]}")
  done
  lines=("${filtered[@]}")

  while [[ ${#lines[@]} -lt 2 ]]; do
    lines+=( "" )
  done

  local -a newl=()
  newl+=( "${lines[0]}" "${lines[1]}" )
  newl+=( "$file_line" "$path_line" "$dir_line" "$type_line" )
  for ((i = 2; i < ${#lines[@]}; i++)); do
    newl+=( "${lines[$i]}" )
  done

  tmp="$(mktemp "${TMPDIR:-/tmp}/lucid-sh-hdr.XXXXXX")"
  printf '%s\n' "${newl[@]}" > "$tmp"
  if cmp -s "$filepath" "$tmp" 2>/dev/null; then
    rm -f "$tmp"
    return 0
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf 'Would update: %s\n' "$filepath"
    rm -f "$tmp"
    return 0
  fi
  mv "$tmp" "$filepath"
  printf 'Updated: %s\n' "$filepath"
}

main() {
  local py count filepath canonical parent_dir

  if [[ ! -f "${REPO_ROOT}/_normalise_lucid_headers.py" ]]; then
    echo "Missing ${REPO_ROOT}/_normalise_lucid_headers.py (needed for ROOTS / paths)." >&2
    exit 1
  fi

  py="$(pick_python)"
  if [[ -z "$py" ]]; then
    echo "No python3 or python on PATH; set PYTHON=... or install Python." >&2
    exit 1
  fi

  count=0
  while IFS=$'\t' read -r filepath canonical parent_dir; do
    [[ -z "${filepath:-}" ]] && continue
    [[ ! -f "$filepath" ]] && continue
    process_one_sh "$filepath" "$canonical" "$parent_dir"
    count=$((count + 1))
  done < <(list_repo_sh_with_canonical "$py")

  echo "Scanned ${count} *.sh under ${REPO_ROOT}"
}

main "$@"
