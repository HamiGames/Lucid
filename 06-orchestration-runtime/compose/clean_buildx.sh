#!/usr/bin/env bash
# /workspaces/Lucid/06-orchestration-runtime/compose/cleanup_buildx.sh
set -euo pipefail

echo "==[1/8] Verify current state (read-only)=="
# Reason: Establish baseline before any changes.
docker context ls
docker buildx ls || true

echo "==[2/8] Ensure correct active builder & context=="
# Reason: Make sure builds use the wanted builder; prevents accidental removals of in-use builders.
docker buildx use lucidbx || true
# Keep current active context 'lucid-pi' as per requirement (do not change).

echo "==[3/8] Stop/disable all non-required builders (make them inert)=="
# Reason: Prune caches to free resources; ensure they are not default/active.
# 'lucid-pi' (docker driver) is context-bound; can't be removed while keeping its context.
for B in default desktop lucid_pi lucid-pi; do
  echo "---- pruning caches for builder: $B (ignore errors if missing)"
  docker buildx prune --builder "$B" -a -f || true
done

echo "==[4/8] Remove removable non-required builders=="
# Reason: Remove stray builders that are not context-bound or not needed.
# - Remove 'lucid_pi' (docker driver)
# - Remove 'default' and 'desktop' builders
# - Attempt 'lucid-pi' last; expect failure due to context binding (we keep its context).
docker buildx rm lucid_pi   || true
docker buildx rm default    || true
docker buildx rm desktop    || true
docker buildx rm lucid-pi   || true   # Expected: will NOT remove while 'lucid-pi' context is kept.

echo "==[5/8] Remove the unused SSH context with underscore=="
# Reason: You asked to remove everything except 'lucid-pi' context; delete 'lucid_pi' context safely.
docker context rm lucid_pi || true

echo "==[6/8] Re-bootstrap the kept builder to ensure healthy state=="
# Reason: Confirm BuildKit is running and platforms are detected on the kept builder.
docker buildx inspect --bootstrap lucidbx

echo "==[7/8] Final global prune (safe for caches only)=="
# Reason: Ensure no dangling Buildx caches remain (images/volumes untouched).
docker buildx prune -a -f || true

echo "==[8/8] Show final state=="
docker context ls
docker buildx ls

echo "Cleanup complete. Kept: context 'lucid-pi', builder 'lucidbx'. Others removed or made inert."
