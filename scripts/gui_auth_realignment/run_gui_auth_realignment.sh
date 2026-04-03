#!/usr/bin/env sh
# Wrapper → runtime_align_once.py (POSIX; no .ps1 per plan)
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec python3 "$REPO_ROOT/scripts/gui_auth_realignment/runtime_align_once.py" --repo-root "$REPO_ROOT" "$@"
