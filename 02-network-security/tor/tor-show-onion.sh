#!/bin/sh
set -e
DIR="${ONION_DIR:-/run/lucid/onion}"
FILE="$DIR/tor_bootstrap.env"

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

