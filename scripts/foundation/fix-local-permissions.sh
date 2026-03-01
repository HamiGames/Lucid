#!/bin/bash
# scripts/foundation/fix-local-permissions.sh
# Fix file permissions for local git repository

set -e

echo "Fixing local repository permissions..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

echo "=== Fixing Local Repository Permissions ==="

# Configure git to ignore file mode changes
echo "Configuring git filemode..."
if git config --local core.filemode false; then
    print_status 0 "Git filemode configured to ignore file permission changes"
else
    print_status 1 "Failed to configure git filemode"
    exit 1
fi

# Fix directory permissions
echo "Fixing directory permissions..."
if find . -type d -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -exec chmod 775 {} \; &> /dev/null; then
    print_status 0 "Directory permissions fixed"
else
    print_status 1 "Failed to fix directory permissions"
    exit 1
fi

# Fix Python file permissions
echo "Fixing Python file permissions..."
if find . -type f -name "*.py" -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -exec chmod 664 {} \; &> /dev/null; then
    print_status 0 "Python file permissions fixed"
else
    print_status 1 "Failed to fix Python file permissions"
    exit 1
fi

# Fix __init__.py files specifically
echo "Fixing __init__.py file permissions..."
if find . -name "__init__.py" -type f -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -exec chmod 664 {} \; &> /dev/null; then
    print_status 0 "__init__.py file permissions fixed"
else
    print_status 1 "Failed to fix __init__.py file permissions"
    exit 1
fi

# Fix script file permissions
echo "Fixing script file permissions..."
if find . -type f -name "*.sh" -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -exec chmod 775 {} \; &> /dev/null; then
    print_status 0 "Script file permissions fixed"
else
    print_status 1 "Failed to fix script file permissions"
    exit 1
fi

# Fix other common file types
echo "Fixing other file permissions..."
if find . -type f \( -name "*.yml" -o -name "*.yaml" -o -name "*.json" -o -name "*.md" -o -name "*.txt" -o -name "*.env" \) -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -exec chmod 664 {} \; &> /dev/null; then
    print_status 0 "Other file permissions fixed"
else
    print_status 1 "Failed to fix other file permissions"
    exit 1
fi

# Reset git index to ignore permission changes
echo "Resetting git index for permission changes..."
if git reset HEAD . &> /dev/null; then
    print_status 0 "Git index reset"
else
    print_status 1 "Failed to reset git index"
fi

echo ""
echo -e "${GREEN}✓ Local repository permissions fix completed!${NC}"
echo ""
echo "Permissions fixed:"
echo "- Directories: 775 (rwxrwxr-x)"
echo "- Python files: 664 (rw-rw-r--)"
echo "- Script files: 775 (rwxrwxr-x)"
echo "- Other files: 664 (rw-rw-r--)"
echo ""
echo "Git is now configured to ignore file permission changes."
echo "This should resolve permission issues when working with the repository."
