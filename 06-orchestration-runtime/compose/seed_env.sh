#!/usr/bin/env bash
# Safely create/update the shared .env used by compose/tunnel scripts.
# Hardened to avoid permission errors (tries normal write, then sudo fallback).
set -euo pipefail
umask 022

log(){ printf '[seed_env] %s\n' "$*"; }
have(){ command -v "$1" >/dev/null 2>&1; }

OUT_FILE="${1:-"$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.env"}"
OUT_DIR="$(dirname "$OUT_FILE")"

# -- ensure directory exists (with sudo fallback) ------------------------------
if ! mkdir -p "$OUT_DIR" 2>/dev/null; then
  if have sudo; then sudo mkdir -p "$OUT_DIR"; else
    log "ERROR: cannot create $OUT_DIR (no permission and no sudo)"; exit 1
  fi
fi

# -- ensure file exists (with sudo fallback) -----------------------------------
if [[ ! -e "$OUT_FILE" ]]; then
  if ! : > "$OUT_FILE" 2>/dev/null; then
    if have sudo; then
      sudo sh -c ": > \"$OUT_FILE\""
      # try to hand ownership back to the current user (best effort)
      sudo chown "$(id -u)":"$(id -g)" "$OUT_FILE" || true
      sudo chmod 0644 "$OUT_FILE" || true
    else
      log "ERROR: cannot create $OUT_FILE (no permission and no sudo)"; exit 1
    fi
  fi
fi

# -- ensure writability (best-effort chown/chmod) ------------------------------
if [[ ! -w "$OUT_FILE" ]]; then
  if have sudo; then
    sudo chown "$(id -u)":"$(id -g)" "$OUT_FILE" || true
    sudo chmod 0644 "$OUT_FILE" || true
  fi
fi

# -- idempotent upsert of keys -------------------------------------------------
ensure_key(){
  local key="$1"
  if ! grep -qE "^${key}=" "$OUT_FILE" 2>/dev/null; then
    # normal append, or sudo tee fallback
    if ! printf "%s=\n" "$key" >> "$OUT_FILE" 2>/dev/null; then
      if have sudo; then
        printf "%s=\n" "$key" | sudo tee -a "$OUT_FILE" >/dev/null
      else
        log "ERROR: cannot write key $key to $OUT_FILE (no permission and no sudo)"; exit 1
      fi
    fi
  fi
}

ensure_key "ONION"
ensure_key "COOKIE"
ensure_key "HEX"

log "Wrote/verified placeholders in $OUT_FILE"
