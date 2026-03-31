#!/usr/bin/env bash
#
# File: /app/configs/lucid_docker_build_codegen.sh
# x-lucid-file-path: /app/configs/lucid_docker_build_codegen.sh
# x-lucid-file-directory: /app/configs
# x-lucid-file-type: shell
# Run Lucid header normalisers and listing / host-config / cluster calibration generators.
# Host (repo root):  bash infrastructure/containers/lucid_docker_build_codegen.sh
# Docker builder:    WORKDIR must be repo root (e.g. /build) with full tree for rglob scanners.
#
# Order: shell headers -> YAML headers -> Python docstrings -> x-files-listing -> host-config -> cluster YAMLs.

set -euo pipefail

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

resolve_repo_root() {
  if [[ -n "${LUCID_REPO_ROOT:-}" ]]; then
    echo "${LUCID_REPO_ROOT}"
    return
  fi
  local here
  here="$(pwd)"
  if [[ -f "${here}/_normalise_lucid_headers.py" ]]; then
    echo "${here}"
    return
  fi
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  echo "$(cd "${script_dir}/../.." && pwd)"
}

REPO_ROOT="$(resolve_repo_root)"
export REPO_ROOT
cd "${REPO_ROOT}"

if [[ ! -f "${REPO_ROOT}/_normalise_lucid_headers.py" ]]; then
  echo "lucid_docker_build_codegen.sh: missing ${REPO_ROOT}/_normalise_lucid_headers.py (wrong LUCID_REPO_ROOT or incomplete COPY?)" >&2
  exit 1
fi

PY="$(pick_python)"
if [[ -z "${PY}" ]]; then
  echo "lucid_docker_build_codegen.sh: need python3 or python on PATH" >&2
  exit 1
fi

if ! "${PY}" -c "import yaml" 2>/dev/null; then
  "${PY}" -m pip install --no-cache-dir pyyaml
fi

bash "${REPO_ROOT}/_normalise_lucid_shell_headers.sh"
"${PY}" "${REPO_ROOT}/_normalise_lucid_yaml_headers.py"
"${PY}" "${REPO_ROOT}/_normalise_lucid_headers.py"
"${PY}" "${REPO_ROOT}/_normalise_lucid_headers.py" --x-files-listing
"${PY}" "${REPO_ROOT}/_gen_host_config.py"
"${PY}" "${REPO_ROOT}/infrastructure/containers/_gen_x_lucid_cluster_calibration.py"

echo "lucid_docker_build_codegen.sh: done (repo root: ${REPO_ROOT})"
