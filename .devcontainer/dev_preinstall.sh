#!/usr/bin/env bash
# Dev bootstrap for OS-level tooling used across the project.
# - OpenJDK 17, Node.js 20.x + Redocly CLI (OpenAPI)
# - MongoDB 7 client tools (mongosh + database-tools)
# - Build deps for cryptography/native wheels
# - Utilities: nc, jq, openssl, shellcheck, tzdata
set -euo pipefail
umask 022

log(){ printf '[dev_preinstall] %s\n' "$*"; }

# ---- root escalation helpers -------------------------------------------------
_have(){ command -v "$1" >/dev/null 2>&1; }
_run_as_root(){
  # Prefer passwordless sudo (devcontainer default); fall back to su.
  if [ "$(id -u)" -eq 0 ]; then
    bash -lc "$*"
  elif _have sudo; then
    sudo -E bash -lc "$*"
  elif _have su; then
    su -c "$*"
  else
    echo "ERROR: need root to run: $*" >&2
    exit 1
  fi
}

# ---- apt hardening (fixes your permission error) -----------------------------
export DEBIAN_FRONTEND=noninteractive
export TZ=${TZ:-Etc/UTC}
export APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=1

log "Ensuring apt lists directory exists..."
_run_as_root 'mkdir -p -m 0755 /var/lib/apt/lists/partial || true'

log "Unlocking any stale apt locks (safe no-op if none)..."
_run_as_root 'rm -f /var/lib/apt/lists/lock /var/cache/apt/archives/lock /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock || true'

log "Updating package metadata..."
_run_as_root 'apt-get update -y'

log "Installing base packages..."
_run_as_root 'apt-get install -y --no-install-recommends \
  ca-certificates curl gnupg lsb-release git \
  build-essential pkg-config python3-dev \
  libssl-dev libffi-dev \
  netcat-openbsd jq openssl shellcheck tzdata'

# ---- Java (Tron JVM prereq) --------------------------------------------------
if !_have javac; then
  log "Installing OpenJDK 17..."
  _run_as_root 'apt-get install -y --no-install-recommends openjdk-17-jdk'
else
  log "Java present: $(javac -version 2>&1 || true)"
fi

# ---- Node.js 20.x + Redocly (OpenAPI) ---------------------------------------
if !_have node; then
  log "Installing Node.js 20.x (NodeSource repo)..."
  _run_as_root 'mkdir -p /etc/apt/keyrings'
  _run_as_root 'curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key -o /etc/apt/keyrings/nodesource.gpg'
  _run_as_root 'echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list'
  _run_as_root 'apt-get update -y && apt-get install -y --no-install-recommends nodejs'
fi
if _have corepack; then corepack enable || true; fi

if _have npm && !_have redocly; then
  log "Installing Redocly CLI (@redocly/cli)..."
  _run_as_root 'npm install -g @redocly/cli'
fi

# ---- MongoDB client tools (for MongoDB 7 service) ----------------------------
if !_have mongosh; then
  log "Installing MongoDB 7 client (mongosh + database-tools)..."
  _run_as_root 'curl -fsSL https://pgp.mongodb.com/server-7.0.asc -o /usr/share/keyrings/mongodb-server-7.0.gpg'
  _run_as_root 'echo "deb [signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg arch=$(dpkg --print-architecture)] https://repo.mongodb.org/apt/debian bookworm/mongodb-org/7.0 main" > /etc/apt/sources.list.d/mongodb-org-7.0.list'
  _run_as_root 'apt-get update -y && apt-get install -y --no-install-recommends mongodb-mongosh mongodb-database-tools'
fi

# ---- versions ---------------------------------------------------------------
log "Versions:"
{
  echo -n "  Java:     "; (javac -version 2>&1 || true)
  echo -n "  Node:     "; (node -v 2>&1 || true)
  echo -n "  npm:      "; (npm -v 2>&1 || true)
  echo -n "  Redocly:  "; (redocly --version 2>&1 || true)
  echo -n "  mongosh:  "; (mongosh --version 2>&1 | head -n1 || true)
  echo -n "  openssl:  "; (openssl version 2>&1 || true)
  echo -n "  shellcheck: "; (shellcheck --version 2>&1 | head -n1 || true)
} || true

log "Done."
