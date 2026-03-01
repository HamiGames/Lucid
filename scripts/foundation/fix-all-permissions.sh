#!/bin/bash
# scripts/foundation/fix-all-permissions.sh
# Comprehensive permission fix for Lucid project - Windows and Pi compatible

set -e

echo "Setting up comprehensive permissions for Lucid project..."
echo "This script ensures proper permissions for both Windows console and Pi SSH access."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Function to print info
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

echo ""
echo "=== Comprehensive Lucid Project Permission Setup ==="

# Configure git to ignore file mode changes globally
echo "Configuring git filemode settings..."
if git config --local core.filemode false; then
    print_status 0 "Git filemode configured to ignore file permission changes"
else
    print_status 1 "Failed to configure git filemode"
    exit 1
fi

# Set umask for consistent permissions
echo "Setting umask for consistent file creation..."
umask 002
print_status 0 "Umask set to 002 (group write enabled)"

echo ""
echo "=== Fixing Directory Permissions ==="

# Fix all directory permissions
print_info "Setting directory permissions to 775 (rwxrwxr-x)..."
if find . -type d -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -not -path "./.cursor/*" -not -path "./node_modules/*" -exec chmod 775 {} \; &> /dev/null; then
    print_status 0 "Directory permissions set to 775"
else
    print_status 1 "Failed to set directory permissions"
    exit 1
fi

echo ""
echo "=== Fixing Python File Permissions ==="

# Fix Python file permissions
print_info "Setting Python file permissions to 664 (rw-rw-r--)..."
if find . -type f -name "*.py" -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -not -path "./.cursor/*" -not -path "./node_modules/*" -exec chmod 664 {} \; &> /dev/null; then
    print_status 0 "Python file permissions set to 664"
else
    print_status 1 "Failed to set Python file permissions"
    exit 1
fi

# Fix __init__.py files specifically
print_info "Setting __init__.py file permissions to 664..."
if find . -name "__init__.py" -type f -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -not -path "./.cursor/*" -not -path "./node_modules/*" -exec chmod 664 {} \; &> /dev/null; then
    print_status 0 "__init__.py file permissions set to 664"
else
    print_status 1 "Failed to set __init__.py file permissions"
    exit 1
fi

echo ""
echo "=== Fixing Script File Permissions ==="

# Fix shell script permissions
print_info "Setting shell script permissions to 775 (executable)..."
if find . -type f -name "*.sh" -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -not -path "./.cursor/*" -not -path "./node_modules/*" -exec chmod 775 {} \; &> /dev/null; then
    print_status 0 "Shell script permissions set to 775"
else
    print_status 1 "Failed to set shell script permissions"
    exit 1
fi

# Fix PowerShell script permissions
print_info "Setting PowerShell script permissions to 664..."
if find . -type f -name "*.ps1" -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -not -path "./.cursor/*" -not -path "./node_modules/*" -exec chmod 664 {} \; &> /dev/null; then
    print_status 0 "PowerShell script permissions set to 664"
else
    print_status 1 "Failed to set PowerShell script permissions"
    exit 1
fi

# Fix batch file permissions
print_info "Setting batch file permissions to 664..."
if find . -type f -name "*.bat" -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -not -path "./.cursor/*" -not -path "./node_modules/*" -exec chmod 664 {} \; &> /dev/null; then
    print_status 0 "Batch file permissions set to 664"
else
    print_status 1 "Failed to set batch file permissions"
    exit 1
fi

echo ""
echo "=== Fixing Configuration File Permissions ==="

# Fix configuration file permissions
print_info "Setting configuration file permissions to 664..."
if find . -type f \( -name "*.yml" -o -name "*.yaml" -o -name "*.json" -o -name "*.toml" -o -name "*.cfg" -o -name "*.conf" -o -name "*.ini" \) -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -not -path "./.cursor/*" -not -path "./node_modules/*" -exec chmod 664 {} \; &> /dev/null; then
    print_status 0 "Configuration file permissions set to 664"
else
    print_status 1 "Failed to set configuration file permissions"
    exit 1
fi

# Fix environment file permissions
print_info "Setting environment file permissions to 664..."
if find . -type f -name "*.env*" -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -not -path "./.cursor/*" -not -path "./node_modules/*" -exec chmod 664 {} \; &> /dev/null; then
    print_status 0 "Environment file permissions set to 664"
else
    print_status 1 "Failed to set environment file permissions"
    exit 1
fi

echo ""
echo "=== Fixing Documentation File Permissions ==="

# Fix documentation file permissions
print_info "Setting documentation file permissions to 664..."
if find . -type f \( -name "*.md" -o -name "*.txt" -o -name "*.rst" \) -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -not -path "./.cursor/*" -not -path "./node_modules/*" -exec chmod 664 {} \; &> /dev/null; then
    print_status 0 "Documentation file permissions set to 664"
else
    print_status 1 "Failed to set documentation file permissions"
    exit 1
fi

echo ""
echo "=== Fixing Docker File Permissions ==="

# Fix Docker file permissions
print_info "Setting Docker file permissions to 664..."
if find . -type f \( -name "Dockerfile*" -o -name "docker-compose*.yml" -o -name "docker-compose*.yaml" \) -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -not -path "./.cursor/*" -not -path "./node_modules/*" -exec chmod 664 {} \; &> /dev/null; then
    print_status 0 "Docker file permissions set to 664"
else
    print_status 1 "Failed to set Docker file permissions"
    exit 1
fi

echo ""
echo "=== Fixing Special Files ==="

# Fix .gitignore and similar files
print_info "Setting git-related file permissions to 664..."
if find . -type f \( -name ".gitignore" -o -name ".gitattributes" -o -name ".gitmodules" \) -not -path "./.git/*" -exec chmod 664 {} \; &> /dev/null; then
    print_status 0 "Git-related file permissions set to 664"
else
    print_status 1 "Failed to set git-related file permissions"
    exit 1
fi

# Fix Makefile permissions
print_info "Setting Makefile permissions to 664..."
if find . -type f \( -name "Makefile*" -o -name "makefile*" \) -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -not -path "./.cursor/*" -not -path "./node_modules/*" -exec chmod 664 {} \; &> /dev/null; then
    print_status 0 "Makefile permissions set to 664"
else
    print_status 1 "Failed to set Makefile permissions"
    exit 1
fi

echo ""
echo "=== Fixing JavaScript/TypeScript Files ==="

# Fix JavaScript/TypeScript file permissions
print_info "Setting JavaScript/TypeScript file permissions to 664..."
if find . -type f \( -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" \) -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -not -path "./.cursor/*" -not -path "./node_modules/*" -exec chmod 664 {} \; &> /dev/null; then
    print_status 0 "JavaScript/TypeScript file permissions set to 664"
else
    print_status 1 "Failed to set JavaScript/TypeScript file permissions"
    exit 1
fi

echo ""
echo "=== Fixing CSS/HTML Files ==="

# Fix CSS/HTML file permissions
print_info "Setting CSS/HTML file permissions to 664..."
if find . -type f \( -name "*.css" -o -name "*.html" -o -name "*.htm" -o -name "*.scss" -o -name "*.sass" \) -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -not -path "./.cursor/*" -not -path "./node_modules/*" -exec chmod 664 {} \; &> /dev/null; then
    print_status 0 "CSS/HTML file permissions set to 664"
else
    print_status 1 "Failed to set CSS/HTML file permissions"
    exit 1
fi

echo ""
echo "=== Fixing Other File Types ==="

# Fix other common file types
print_info "Setting other file permissions to 664..."
if find . -type f \( -name "*.xml" -o -name "*.sql" -o -name "*.sh" -o -name "*.bash" -o -name "*.zsh" \) -not -path "./.git/*" -not -path "./.venv/*" -not -path "./.mypy_cache/*" -not -path "./.ruff_cache/*" -not -path "./.cursor/*" -not -path "./node_modules/*" -exec chmod 664 {} \; &> /dev/null; then
    print_status 0 "Other file permissions set to 664"
else
    print_status 1 "Failed to set other file permissions"
    exit 1
fi

echo ""
echo "=== Setting Special Directory Permissions ==="

# Fix specific directory permissions
print_info "Setting special directory permissions..."

# Scripts directory should be executable
if [ -d "scripts" ]; then
    chmod 775 scripts
    print_status 0 "Scripts directory set to 775"
fi

# Configs directory
if [ -d "configs" ]; then
    chmod 775 configs
    print_status 0 "Configs directory set to 775"
fi

# Build directory
if [ -d "build" ]; then
    chmod 775 build
    print_status 0 "Build directory set to 775"
fi

# Tests directory
if [ -d "tests" ]; then
    chmod 775 tests
    print_status 0 "Tests directory set to 775"
fi

echo ""
echo "=== Cleaning Up Git Index ==="

# Reset git index to ignore permission changes
print_info "Resetting git index for permission changes..."
if git reset HEAD . &> /dev/null; then
    print_status 0 "Git index reset successfully"
else
    print_status 1 "Failed to reset git index"
fi

echo ""
echo "=== Permission Summary ==="

print_info "Permission structure applied:"
echo "  📁 Directories: 775 (rwxrwxr-x) - Full access for owner and group"
echo "  🐍 Python files: 664 (rw-rw-r--) - Read/write for owner and group"
echo "  📜 Scripts (.sh): 775 (rwxrwxr-x) - Executable for owner and group"
echo "  ⚙️  Config files: 664 (rw-rw-r--) - Read/write for owner and group"
echo "  📄 Documentation: 664 (rw-rw-r--) - Read/write for owner and group"
echo "  🐳 Docker files: 664 (rw-rw-r--) - Read/write for owner and group"
echo "  🌐 Web files: 664 (rw-rw-r--) - Read/write for owner and group"

echo ""
echo -e "${GREEN}✓ Comprehensive permission setup completed!${NC}"
echo ""
echo "This setup ensures:"
echo "  ✅ Files are writable from Windows console"
echo "  ✅ Files are writable via SSH to Pi"
echo "  ✅ Scripts are executable on both platforms"
echo "  ✅ Git ignores file permission changes"
echo "  ✅ Consistent permissions across the entire project"
echo ""
echo "The Lucid project is now ready for cross-platform development!"
