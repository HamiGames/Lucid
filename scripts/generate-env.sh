#!/bin/bash
# Simple wrapper script for environment generation
# Usage: ./scripts/generate-env.sh

set -e

# Project root configuration
PROJECT_ROOT="/mnt/myssd/Lucid/Lucid"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to project root if not already there
if [ "$(pwd)" != "$PROJECT_ROOT" ]; then
    echo "Changing to project root: $PROJECT_ROOT"
    cd "$PROJECT_ROOT"
fi

echo "🔧 Lucid Environment Generation"
echo "================================"
echo "Project Root: $PROJECT_ROOT"
echo ""

# Run the master environment generation script
bash "$SCRIPT_DIR/config/generate-master-env.sh"
