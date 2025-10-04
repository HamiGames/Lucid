# ===== lucid_pi_bootstrap.sh =====
# One-time (or safe to re-run) bootstrap for Lucid on Raspberry Pi (Ubuntu Server 64-bit)
# - Installs Docker Engine + Compose v2 + git
# - Clones/updates the repo at /opt/lucid (from GitHub)
# - Builds Tor image (lucid/tor:dev)
# - Brings up dev stack with tor override
# - Shows health

set -euo pipefail

# --- configurable vars ---
PI_USER="${PI_USER:-$USER}"
REPO_URL="${REPO_URL:-https://github.com/HamiGames/Lucid.git}"
BRANCH="${BRANCH:-main}"
PI_PATH="${PI_PATH:-/opt/lucid}"
COMPOSE_DIR="$PI_PATH/06-orchestration-runtime/compose"
COMPOSE_FILE="$COMPOSE_DIR/lucid-dev.yaml"
TOR_PATH="$PI_PATH/02-network-security/tor"
TOR_IMAGE="lucid/tor:dev"
OVERRIDE_FILE="$COMPOSE_DIR/tor-image-override.yaml"

log(){ printf '[bootstrap] %s\n' "$*"; }
die(){ printf '[bootstrap] ERROR: %s\n' "$*" >&2; exit 1; }

# --- 0) sanity: Ubuntu + network ---
log "OS info:"; uname -a || true

# --- 1) packages: docker+compose+git (official repo) ---
log "Installing Docker Engine + Compose v2 + git…"
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl git gnupg

if ! command -v docker >/dev/null 2>&1; then
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

sudo systemctl enable docker
sudo systemctl start docker

# Add current user to docker group (new login needed to take effect)
if ! id -nG | grep -q '\bdocker\b'; then
  log "Adding $PI_USER to docker group (re-login required)…"
  sudo usermod -aG docker "$PI_USER" || true
fi

# --- 2) repo: clone/update at /opt/lucid (GitHub is canonical) ---
log "Ensuring repo at $PI_PATH…"
if [ ! -d "$PI_PATH/.git" ]; then
  sudo mkdir -p "$PI_PATH"
  sudo chown -R "$PI_USER":"$PI_USER" "$PI_PATH"
  git clone "$REPO_URL" "$PI_PATH"
fi
cd "$PI_PATH"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"

# --- 3) tor: build image from repo tree ---
log "Building Tor image $TOR_IMAGE from $TOR_PATH…"
[ -d "$TOR_PATH" ] || die "Missing $TOR_PATH"
docker build --no-cache -t "$TOR_IMAGE" "$TOR_PATH"

# --- 4) compose: create override to force our tor image, then build+up ---
log "Preparing compose override at $OVERRIDE_FILE…"
install -d -m 0755 "$COMPOSE_DIR"
cat > "$OVERRIDE_FILE" <<'YAML'
services:
  tor-proxy:
    image: lucid/tor:dev
    build: null
YAML

log "Bringing stack up (profile: dev)…"
[ -f "$COMPOSE_FILE" ] || die "Missing compose file: $COMPOSE_FILE"
docker compose -f "$COMPOSE_FILE" -f "$OVERRIDE_FILE" --profile dev build
docker compose -f "$COMPOSE_FILE" -f "$OVERRIDE_FILE" --profile dev up -d

log "Compose status:"
docker compose -f "$COMPOSE_FILE" ps

# --- 5) health: tor bootstrap + recent logs ---
log "Tail Tor logs (looking for 'Bootstrapped 100%: Done')…"
TOR_CTN="$(docker ps --format '{{.Names}}' | grep -E 'tor|tor-proxy' | head -n1 || true)"
if [ -n "$TOR_CTN" ]; then
  docker logs "$TOR_CTN" --since=10m | tail -n 200 || true
else
  log "WARN: Tor container not found yet."
fi

log "Recent stack logs (10m)…"
docker compose -f "$COMPOSE_FILE" logs --since=10m --no-log-prefix || true

log "Bootstrap complete."
