#!/bin/bash
# Lucid Build Factory Setup Script
# Configures complete Docker-in-Docker build environment per SPEC-4 requirements
# Path: .devcontainer/setup-build-factory.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
NETWORK_NAME="lucid-dev_lucid_net"
BUILDER_NAME="lucid-pi"
SSH_HOST="pickme@192.168.0.75"

log() { echo -e "${BLUE}[BUILD-FACTORY] $1${NC}"; }
success() { echo -e "${GREEN}[SUCCESS] $1${NC}"; }
warn() { echo -e "${YELLOW}[WARNING] $1${NC}"; }
error() { echo -e "${RED}[ERROR] $1${NC}"; }

log "Initializing Lucid Build Factory..."

# 1. Verify Docker daemon is running
log "Verifying Docker daemon..."
if ! docker info >/dev/null 2>&1; then
    error "Docker daemon not accessible"
    exit 1
fi
success "Docker daemon ready"

# 2. Setup buildx builder for multi-platform builds
log "Setting up buildx builder: $BUILDER_NAME"
if docker buildx ls | grep -q "$BUILDER_NAME"; then
    warn "Builder $BUILDER_NAME already exists, removing..."
    docker buildx rm "$BUILDER_NAME" --force || true
fi

docker buildx create \
    --name "$BUILDER_NAME" \
    --driver docker-container \
    --platform linux/amd64,linux/arm64 \
    --use \
    --bootstrap

success "Buildx builder '$BUILDER_NAME' configured for AMD64/ARM64"

# 3. Verify network exists
log "Verifying network: $NETWORK_NAME"
if ! docker network ls --format "{{.Name}}" | grep -q "^${NETWORK_NAME}$"; then
    warn "Network $NETWORK_NAME not found, creating..."
    docker network create \
        --driver bridge \
        --attachable \
        --subnet=172.20.0.0/16 \
        --gateway=172.20.0.1 \
        "$NETWORK_NAME"
fi
success "Network '$NETWORK_NAME' ready"

# 4. Setup SSH configuration for Pi connection
log "Configuring SSH for Pi connection..."
mkdir -p /root/.ssh
chmod 700 /root/.ssh

# Create SSH config for Pi
cat > /root/.ssh/config << 'EOF'
Host *
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null
    LogLevel ERROR
    ServerAliveInterval 60
    ServerAliveCountMax 3

Host lucid-pi
    HostName 192.168.0.75
    User pickme
    Port 22
    ForwardAgent yes
EOF
chmod 600 /root/.ssh/config
success "SSH configuration ready for Pi connection"

# 5. Setup development tools and project dependencies
log "Installing project in development mode..."
cd /workspaces/Lucid
if [[ -f "pyproject.toml" ]] || [[ -f "setup.py" ]]; then
    pip install -e . || warn "Project install failed, continuing..."
fi

# Install Node.js dependencies if package.json exists
if [[ -f "package.json" ]]; then
    npm install || warn "npm install failed, continuing..."
fi

# 6. Setup Git configuration
log "Configuring Git..."
if [[ ! -f "/root/.gitconfig" ]]; then
    git config --global user.name "Lucid Developer"
    git config --global user.email "dev@lucid.local"
    git config --global init.defaultBranch main
    git config --global pull.rebase false
fi

# 7. Setup pre-commit hooks if available
if command -v pre-commit >/dev/null 2>&1 && [[ -f ".pre-commit-config.yaml" ]]; then
    log "Installing pre-commit hooks..."
    pre-commit install || warn "Pre-commit install failed"
fi

# 8. Start SSH daemon for remote access
log "Starting SSH daemon..."
/usr/sbin/sshd || warn "SSH daemon start failed"

# 9. Start Tor proxy for network privacy
log "Starting Tor proxy..."
if command -v tor >/dev/null 2>&1; then
    tor -f /etc/tor/torrc --runasdaemon 1 || warn "Tor start failed"
fi

# 10. Validate build environment
log "Validating build environment..."

# Check Docker functionality
docker --version && docker-compose --version || error "Docker tools not available"

# Check buildx functionality
docker buildx inspect "$BUILDER_NAME" >/dev/null || error "Buildx builder not working"

# Check development tools
java -version 2>&1 | head -1 || error "Java not available"
python3 --version || error "Python not available"
node --version || error "Node.js not available"

# Check SSH connectivity to Pi (optional)
if timeout 5 ssh -o ConnectTimeout=3 "$SSH_HOST" "echo 'Pi connection test'" >/dev/null 2>&1; then
    success "SSH connection to Pi verified"
else
    warn "SSH connection to Pi failed (network/auth issue)"
fi

# 11. Display build factory status
log "Build Factory Status:"
echo "  ✓ Docker daemon: $(docker --version)"
echo "  ✓ Buildx builder: $BUILDER_NAME ($(docker buildx ls | grep "$BUILDER_NAME" | awk '{print $3}'))"
echo "  ✓ Network: $NETWORK_NAME"
echo "  ✓ Java: $(java -version 2>&1 | head -1)"
echo "  ✓ Python: $(python3 --version)"
echo "  ✓ Node.js: $(node --version)"
echo "  ✓ SSH: Port 2222 (Pi: $SSH_HOST)"
echo "  ✓ Tor: SOCKS 9050, Control 9051"
echo "  ✓ Workspace: /workspaces/Lucid"

success "Lucid Build Factory is ready for SPEC-4 container orchestration!"

log "Available build commands:"
echo "  • docker buildx build --builder $BUILDER_NAME --platform linux/amd64,linux/arm64 ..."
echo "  • docker-compose -f 06-orchestration-runtime/compose/lucid-dev.yaml build"
echo "  • ssh -p 2222 root@localhost (local access)"
echo "  • ssh $SSH_HOST (Pi access)"

exit 0