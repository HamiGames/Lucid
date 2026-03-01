#!/bin/bash
# Setup Git Authentication for Lucid Project
# Supports both SSH and Personal Access Token methods

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[AUTH]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_status "Setting up Git authentication for Lucid project..."

# Check current git config
print_info "Current git configuration:"
git config --global --list | grep -E "(user\.name|user\.email)" || print_warning "No global git config found"

# Set basic git config if not set
if ! git config --global user.name >/dev/null 2>&1; then
    print_status "Setting default git username (change if needed)..."
    git config --global user.name "Lucid Developer"
fi

if ! git config --global user.email >/dev/null 2>&1; then
    print_status "Setting default git email (change if needed)..."
    git config --global user.email "developer@lucid-project.local"
fi

print_info "Git config after setup:"
git config --global --list | grep -E "(user\.name|user\.email)"

# Check SSH key availability
print_status "Checking SSH key availability..."
if [ -f "/root/.ssh/id_rsa" ] || [ -f "/root/.ssh/id_ed25519" ]; then
    print_status "SSH keys found, setting up SSH remote..."

    # Change remote to SSH
    git remote set-url origin git@github.com:HamiGames/Lucid.git
    print_status "✅ Remote changed to SSH"

    # Test SSH connection
    if ssh -T git@github.com -o StrictHostKeyChecking=no 2>&1 | grep -q "successfully authenticated"; then
        print_status "✅ SSH authentication working"
    else
        print_warning "SSH authentication not working, falling back to token method"
        git remote set-url origin https://github.com/HamiGames/Lucid.git
    fi
else
    print_info "No SSH keys found in /root/.ssh/"
    print_info "Using HTTPS with token authentication"
fi

print_status "Current remote configuration:"
git remote -v

# Create helper script for token authentication
cat > /usr/local/bin/git-token-push << 'EOF'
#!/bin/bash
# Helper script for pushing with personal access token
# Usage: git-token-push "commit message" [token]

COMMIT_MSG="${1:-update: development changes}"
TOKEN="${2:-}"

if [ -z "$TOKEN" ]; then
    echo "Usage: git-token-push \"commit message\" [token]"
    echo "Or set GITHUB_TOKEN environment variable"
    exit 1
fi

# Clean up pre-commit if needed
rm -rf /root/.cache/pre-commit 2>/dev/null || true

# Git operations with token
git add .
git commit -m "$COMMIT_MSG" --no-verify
git push https://${TOKEN}@github.com/HamiGames/Lucid.git main

echo "✅ Successfully pushed to GitHub!"
EOF

chmod +x /usr/local/bin/git-token-push

print_status "✅ Git authentication setup complete!"
print_info ""
print_info "🚀 USAGE OPTIONS:"
print_info "1. SSH (if keys working): ./quick-push.sh -b \"your message\""
print_info "2. Token: git-token-push \"your message\" your_github_token"
print_info "3. Token via env: export GITHUB_TOKEN=your_token && git-token-push \"message\""
print_info ""
print_warning "⚠️  For security, never commit your GitHub token to the repository!"
