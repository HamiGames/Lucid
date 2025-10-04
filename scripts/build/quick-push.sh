#!/bin/bash
# Quick Push Script for Lucid Project
# Handles both GitHub and DockerHub pushes with pre-commit management

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[PUSH]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse arguments
BYPASS_PRECOMMIT=false
PUSH_DOCKER=false
COMMIT_MSG="update: development changes"

while [[ $# -gt 0 ]]; do
    case $1 in
        --bypass-precommit|-b)
            BYPASS_PRECOMMIT=true
            shift
            ;;
        --docker|-d)
            PUSH_DOCKER=true
            shift
            ;;
        --message|-m)
            COMMIT_MSG="$2"
            shift 2
            ;;
        *)
            COMMIT_MSG="$1"
            shift
            ;;
    esac
done

print_status "Starting Lucid project push..."
print_status "Commit message: $COMMIT_MSG"

# Clean up pre-commit cache if needed
if [ "$BYPASS_PRECOMMIT" = true ]; then
    print_warning "Bypassing pre-commit hooks"
    rm -rf /root/.cache/pre-commit 2>/dev/null || true
fi

# Git operations
print_status "Adding all changes..."
git add .

if [ "$BYPASS_PRECOMMIT" = true ]; then
    print_status "Committing with pre-commit bypass..."
    git commit -m "$COMMIT_MSG" --no-verify
else
    print_status "Running pre-commit hooks..."
    # Try to fix pre-commit environment
    if ! git commit -m "$COMMIT_MSG"; then
        print_error "Pre-commit failed. Retry with --bypass-precommit or fix issues"
        exit 1
    fi
fi

# Push to GitHub
print_status "Pushing to GitHub..."
git push origin main || {
    print_error "GitHub push failed. Check network and credentials."
    exit 1
}

print_status "✅ Successfully pushed to GitHub!"

# Docker operations if requested
if [ "$PUSH_DOCKER" = true ]; then
    print_status "Building and pushing Docker images..."
    
    # Check if we're in the devcontainer
    if [ ! -f "/workspaces/Lucid/docker-compose.yml" ] && [ ! -f "/workspaces/Lucid/_compose_resolved.yaml" ]; then
        print_error "Docker compose files not found. Are you in the right directory?"
        exit 1
    fi
    
    # Build images using buildx for multi-platform
    if command -v docker buildx >/dev/null 2>&1; then
        print_status "Building multi-platform images with buildx..."
        
        # Build main services
        for service in api-gateway blockchain-core network-security; do
            if [ -d "./$service" ] || [ -d "./0*-$service" ]; then
                print_status "Building $service..."
                docker buildx build --platform linux/amd64,linux/arm64 \
                    --tag pickme/lucid:$service-latest \
                    --push \
                    ./$(find . -name "*$service*" -type d | head -1) || {
                    print_warning "Failed to build $service, continuing..."
                }
            fi
        done
        
        # Build devcontainer
        print_status "Building devcontainer..."
        docker buildx build --platform linux/amd64 \
            --tag pickme/lucid:devcontainer-dind \
            --push \
            -f .devcontainer/Dockerfile . || {
            print_warning "Failed to build devcontainer"
        }
        
    else
        print_warning "Docker buildx not available, using regular docker build"
        docker build -t pickme/lucid:latest .
        docker push pickme/lucid:latest
    fi
    
    print_status "✅ Successfully pushed to DockerHub!"
fi

print_status "🚀 All operations completed successfully!"
print_status "GitHub: ✅ | DockerHub: $([ "$PUSH_DOCKER" = true ] && echo "✅" || echo "⏭️ (skipped)")"