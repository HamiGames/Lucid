#!/bin/bash
set -e
# ONION_DIR: hidden-service dirs (lucid_admin, lucid_api, etc.) — /run/lucid/onion per Dockerfile scaffold
DIR="${ONION_DIR:-/run/lucid/onion}"
# Bootstrap env is written by tor-health to TOR_DATA_DIR, not inside onion dir
FILE="${TOR_DATA_DIR:-/run/lucid/tor}/tor_bootstrap.env"

if [ -d "$DIR" ]; then
  ls -l "$DIR"
else
  echo "[info] $DIR does not exist"
  exit 0
fi

if [ -f "$FILE" ]; then
  echo "--- tor_bootstrap.env (path: $FILE) ---"
  head -n 200 "$FILE"
else
  echo "[info] $FILE not found"
fi