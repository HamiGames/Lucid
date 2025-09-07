#!/usr/bin/env bash
# Path: 06-orchestration-runtime/compose/tor_healthcheck.sh
# Verify Tor has bootstrapped to 100% by scanning container logs.
# Uses the standard "Bootstrapped 100%" notice emitted by Tor. :contentReference[oaicite:1]{index=1}

set -euo pipefail

CONTAINER="${1:-lucid_tor}"   # alt: tor-proxy
TIMEOUT="${2:-60}"            # seconds
INTERVAL="${3:-2}"

echo "[tor_healthcheck] Watching logs from '${CONTAINER}' for up to ${TIMEOUT}s..."

deadline=$((SECONDS + TIMEOUT))
found=0

while (( SECONDS < deadline )); do
  if docker logs "${CONTAINER}" 2>&1 | grep -qE 'Bootstrapped 100%.*Done'; then
    found=1
    break
  fi
  sleep "${INTERVAL}"
done

if (( found == 1 )); then
  echo "[tor_healthcheck] OK: Tor is bootstrapped (100%)."
  exit 0
else
  echo "[tor_healthcheck] FAIL: Did not observe 'Bootstrapped 100%' in logs within ${TIMEOUT}s."
  exit 1
fi
