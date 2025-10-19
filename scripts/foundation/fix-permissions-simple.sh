#!/bin/bash
# scripts/foundation/fix-permissions-simple.sh
# Simple and fast permission fix for Lucid project

set -e

echo "Fixing permissions for Lucid project (simple approach)..."

# Configure git to ignore file mode changes
git config --local core.filemode false
echo "✓ Git filemode configured"

# Set umask for consistent permissions
umask 002
echo "✓ Umask set to 002"

# Fix directory permissions (batch operation)
echo "Fixing directory permissions..."
find . -type d -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -not -path "./.cursor/*" -not -path "./node_modules/*" -exec chmod 775 {} \;
echo "✓ Directory permissions fixed"

# Fix Python file permissions (batch operation)
echo "Fixing Python file permissions..."
find . -type f -name "*.py" -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -not -path "./.cursor/*" -not -path "./node_modules/*" -exec chmod 664 {} \;
echo "✓ Python file permissions fixed"

# Fix script permissions (batch operation)
echo "Fixing script permissions..."
find . -type f -name "*.sh" -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -not -path "./.cursor/*" -not -path "./node_modules/*" -exec chmod 775 {} \;
echo "✓ Script permissions fixed"

# Fix other file permissions (batch operation)
echo "Fixing other file permissions..."
find . -type f \( -name "*.yml" -o -name "*.yaml" -o -name "*.json" -o -name "*.md" -o -name "*.txt" -o -name "*.env*" \) -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -not -path "./.cursor/*" -not -path "./node_modules/*" -exec chmod 664 {} \;
echo "✓ Other file permissions fixed"

# Reset git index
git reset HEAD . >/dev/null 2>&1
echo "✓ Git index reset"

echo ""
echo "✅ Permission fix completed successfully!"
echo "All files now have proper permissions for Windows and Pi SSH access."
