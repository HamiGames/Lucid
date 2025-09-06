#!/usr/bin/env bash
# Force push ALL files in repo to GitHub, ignoring junk

set -euo pipefail

echo "[git] Cleaning index"
git reset

echo "[git] Removing cached junk"
git rm -r --cached .venv .pre-commit-cache .tmp 2>/dev/null || true

echo "[git] Forcing add of all files (ignoring errors)"
git add --ignore-errors -A

echo "[git] Commit"
git commit -m "Force add/update all project files" --no-verify || echo "[git] Nothing new to commit"

echo "[git] Push"
git push origin main --force
