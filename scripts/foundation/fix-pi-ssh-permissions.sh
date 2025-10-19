#!/bin/bash
# scripts/foundation/fix-pi-ssh-permissions.sh
# Comprehensive Pi SSH permission fix for Lucid project

set -e

echo "Fixing Pi SSH permissions for Lucid project..."
echo "This script ensures all files are accessible and writable via SSH to the Pi."

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

# Pi connection details
PI_USER="pickme"
PI_HOST="192.168.0.75"
PI_PATH="/mnt/myssd/Lucid"

echo ""
echo "=== Pi SSH Permission Fix for Lucid Project ==="

# Check SSH connection first
echo "Testing SSH connection to Pi..."
if ssh -o ConnectTimeout=10 -o BatchMode=yes $PI_USER@$PI_HOST "echo 'SSH connection successful'" &> /dev/null; then
    print_status 0 "SSH connection to Pi successful"
else
    print_status 1 "SSH connection to Pi failed"
    echo "Please ensure:"
    echo "1. Pi is powered on and accessible at $PI_HOST"
    echo "2. SSH is enabled on Pi"
    echo "3. SSH key authentication is configured"
    echo "4. Pi has the project mounted at $PI_PATH"
    exit 1
fi

# Check if the project directory exists on Pi
echo "Checking if project directory exists on Pi..."
if ssh $PI_USER@$PI_HOST "[ -d $PI_PATH ]"; then
    print_status 0 "Project directory exists on Pi"
else
    print_status 1 "Project directory does not exist on Pi"
    echo "Please ensure the project is mounted or copied to $PI_PATH on the Pi"
    exit 1
fi

# Set umask on Pi for consistent permissions
echo "Setting umask on Pi..."
if ssh $PI_USER@$PI_HOST "umask 002"; then
    print_status 0 "Umask set on Pi"
else
    print_status 1 "Failed to set umask on Pi"
fi

echo ""
echo "=== Fixing Directory Permissions on Pi ==="

# Fix all directory permissions on Pi
print_info "Setting directory permissions to 775 on Pi..."
if ssh $PI_USER@$PI_HOST "find $PI_PATH -type d -not -path '$PI_PATH/.git/*' -not -path '$PI_PATH/.venv/*' -not -path '$PI_PATH/.mypy_cache/*' -not -path '$PI_PATH/.ruff_cache/*' -not -path '$PI_PATH/.cursor/*' -not -path '$PI_PATH/node_modules/*' -exec chmod 775 {} \;" &> /dev/null; then
    print_status 0 "Directory permissions set to 775 on Pi"
else
    print_status 1 "Failed to set directory permissions on Pi"
    exit 1
fi

echo ""
echo "=== Fixing Python File Permissions on Pi ==="

# Fix Python file permissions on Pi
print_info "Setting Python file permissions to 664 on Pi..."
if ssh $PI_USER@$PI_HOST "find $PI_PATH -type f -name '*.py' -not -path '$PI_PATH/.git/*' -not -path '$PI_PATH/.venv/*' -not -path '$PI_PATH/.mypy_cache/*' -not -path '$PI_PATH/.ruff_cache/*' -not -path '$PI_PATH/.cursor/*' -not -path '$PI_PATH/node_modules/*' -exec chmod 664 {} \;" &> /dev/null; then
    print_status 0 "Python file permissions set to 664 on Pi"
else
    print_status 1 "Failed to set Python file permissions on Pi"
    exit 1
fi

# Fix __init__.py files specifically on Pi
print_info "Setting __init__.py file permissions to 664 on Pi..."
if ssh $PI_USER@$PI_HOST "find $PI_PATH -name '__init__.py' -type f -not -path '$PI_PATH/.git/*' -not -path '$PI_PATH/.venv/*' -not -path '$PI_PATH/.mypy_cache/*' -not -path '$PI_PATH/.ruff_cache/*' -not -path '$PI_PATH/.cursor/*' -not -path '$PI_PATH/node_modules/*' -exec chmod 664 {} \;" &> /dev/null; then
    print_status 0 "__init__.py file permissions set to 664 on Pi"
else
    print_status 1 "Failed to set __init__.py file permissions on Pi"
    exit 1
fi

echo ""
echo "=== Fixing Script File Permissions on Pi ==="

# Fix shell script permissions on Pi
print_info "Setting shell script permissions to 775 on Pi..."
if ssh $PI_USER@$PI_HOST "find $PI_PATH -type f -name '*.sh' -not -path '$PI_PATH/.git/*' -not -path '$PI_PATH/.venv/*' -not -path '$PI_PATH/.mypy_cache/*' -not -path '$PI_PATH/.ruff_cache/*' -not -path '$PI_PATH/.cursor/*' -not -path '$PI_PATH/node_modules/*' -exec chmod 775 {} \;" &> /dev/null; then
    print_status 0 "Shell script permissions set to 775 on Pi"
else
    print_status 1 "Failed to set shell script permissions on Pi"
    exit 1
fi

echo ""
echo "=== Fixing Configuration File Permissions on Pi ==="

# Fix configuration file permissions on Pi
print_info "Setting configuration file permissions to 664 on Pi..."
if ssh $PI_USER@$PI_HOST "find $PI_PATH -type f \( -name '*.yml' -o -name '*.yaml' -o -name '*.json' -o -name '*.toml' -o -name '*.cfg' -o -name '*.conf' -o -name '*.ini' \) -not -path '$PI_PATH/.git/*' -not -path '$PI_PATH/.venv/*' -not -path '$PI_PATH/.mypy_cache/*' -not -path '$PI_PATH/.ruff_cache/*' -not -path '$PI_PATH/.cursor/*' -not -path '$PI_PATH/node_modules/*' -exec chmod 664 {} \;" &> /dev/null; then
    print_status 0 "Configuration file permissions set to 664 on Pi"
else
    print_status 1 "Failed to set configuration file permissions on Pi"
    exit 1
fi

# Fix environment file permissions on Pi
print_info "Setting environment file permissions to 664 on Pi..."
if ssh $PI_USER@$PI_HOST "find $PI_PATH -type f -name '*.env*' -not -path '$PI_PATH/.git/*' -not -path '$PI_PATH/.venv/*' -not -path '$PI_PATH/.mypy_cache/*' -not -path '$PI_PATH/.ruff_cache/*' -not -path '$PI_PATH/.cursor/*' -not -path '$PI_PATH/node_modules/*' -exec chmod 664 {} \;" &> /dev/null; then
    print_status 0 "Environment file permissions set to 664 on Pi"
else
    print_status 1 "Failed to set environment file permissions on Pi"
    exit 1
fi

echo ""
echo "=== Fixing Documentation File Permissions on Pi ==="

# Fix documentation file permissions on Pi
print_info "Setting documentation file permissions to 664 on Pi..."
if ssh $PI_USER@$PI_HOST "find $PI_PATH -type f \( -name '*.md' -o -name '*.txt' -o -name '*.rst' \) -not -path '$PI_PATH/.git/*' -not -path '$PI_PATH/.venv/*' -not -path '$PI_PATH/.mypy_cache/*' -not -path '$PI_PATH/.ruff_cache/*' -not -path '$PI_PATH/.cursor/*' -not -path '$PI_PATH/node_modules/*' -exec chmod 664 {} \;" &> /dev/null; then
    print_status 0 "Documentation file permissions set to 664 on Pi"
else
    print_status 1 "Failed to set documentation file permissions on Pi"
    exit 1
fi

echo ""
echo "=== Fixing Docker File Permissions on Pi ==="

# Fix Docker file permissions on Pi
print_info "Setting Docker file permissions to 664 on Pi..."
if ssh $PI_USER@$PI_HOST "find $PI_PATH -type f \( -name 'Dockerfile*' -o -name 'docker-compose*.yml' -o -name 'docker-compose*.yaml' \) -not -path '$PI_PATH/.git/*' -not -path '$PI_PATH/.venv/*' -not -path '$PI_PATH/.mypy_cache/*' -not -path '$PI_PATH/.ruff_cache/*' -not -path '$PI_PATH/.cursor/*' -not -path '$PI_PATH/node_modules/*' -exec chmod 664 {} \;" &> /dev/null; then
    print_status 0 "Docker file permissions set to 664 on Pi"
else
    print_status 1 "Failed to set Docker file permissions on Pi"
    exit 1
fi

echo ""
echo "=== Fixing Web File Permissions on Pi ==="

# Fix JavaScript/TypeScript file permissions on Pi
print_info "Setting JavaScript/TypeScript file permissions to 664 on Pi..."
if ssh $PI_USER@$PI_HOST "find $PI_PATH -type f \( -name '*.js' -o -name '*.ts' -o -name '*.jsx' -o -name '*.tsx' \) -not -path '$PI_PATH/.git/*' -not -path '$PI_PATH/.venv/*' -not -path '$PI_PATH/.mypy_cache/*' -not -path '$PI_PATH/.ruff_cache/*' -not -path '$PI_PATH/.cursor/*' -not -path '$PI_PATH/node_modules/*' -exec chmod 664 {} \;" &> /dev/null; then
    print_status 0 "JavaScript/TypeScript file permissions set to 664 on Pi"
else
    print_status 1 "Failed to set JavaScript/TypeScript file permissions on Pi"
    exit 1
fi

# Fix CSS/HTML file permissions on Pi
print_info "Setting CSS/HTML file permissions to 664 on Pi..."
if ssh $PI_USER@$PI_HOST "find $PI_PATH -type f \( -name '*.css' -o -name '*.html' -o -name '*.htm' -o -name '*.scss' -o -name '*.sass' \) -not -path '$PI_PATH/.git/*' -not -path '$PI_PATH/.venv/*' -not -path '$PI_PATH/.mypy_cache/*' -not -path '$PI_PATH/.ruff_cache/*' -not -path '$PI_PATH/.cursor/*' -not -path '$PI_PATH/node_modules/*' -exec chmod 664 {} \;" &> /dev/null; then
    print_status 0 "CSS/HTML file permissions set to 664 on Pi"
else
    print_status 1 "Failed to set CSS/HTML file permissions on Pi"
    exit 1
fi

echo ""
echo "=== Setting Ownership on Pi ==="

# Set ownership to pi user
print_info "Setting file ownership to $PI_USER on Pi..."
if ssh $PI_USER@$PI_HOST "sudo chown -R $PI_USER:$PI_USER $PI_PATH" &> /dev/null; then
    print_status 0 "File ownership set to $PI_USER on Pi"
else
    print_status 1 "Failed to set file ownership on Pi"
    echo "Note: This may require sudo privileges on the Pi"
fi

echo ""
echo "=== Configuring Git on Pi ==="

# Configure git filemode on Pi
print_info "Configuring git filemode on Pi..."
if ssh $PI_USER@$PI_HOST "cd $PI_PATH && git config core.filemode false" &> /dev/null; then
    print_status 0 "Git filemode configured on Pi"
else
    print_status 1 "Failed to configure git filemode on Pi"
fi

# Configure git user on Pi if not set
print_info "Configuring git user on Pi..."
if ssh $PI_USER@$PI_HOST "cd $PI_PATH && git config user.name || git config user.name 'Pi User'" &> /dev/null; then
    print_status 0 "Git user configured on Pi"
else
    print_status 1 "Failed to configure git user on Pi"
fi

if ssh $PI_USER@$PI_HOST "cd $PI_PATH && git config user.email || git config user.email 'pi@lucid.local'" &> /dev/null; then
    print_status 0 "Git email configured on Pi"
else
    print_status 1 "Failed to configure git email on Pi"
fi

echo ""
echo "=== Testing SSH Write Access ==="

# Test SSH write access
print_info "Testing SSH write access..."
if ssh $PI_USER@$PI_HOST "echo '# SSH Write Test - $(date)' >> $PI_PATH/ssh_write_test.txt" &> /dev/null; then
    print_status 0 "SSH write access test successful"
    # Clean up test file
    ssh $PI_USER@$PI_HOST "rm -f $PI_PATH/ssh_write_test.txt" &> /dev/null
else
    print_status 1 "SSH write access test failed"
    exit 1
fi

echo ""
echo "=== Permission Summary for Pi ==="

print_info "Permission structure applied on Pi:"
echo "  📁 Directories: 775 (rwxrwxr-x) - Full access for owner and group"
echo "  🐍 Python files: 664 (rw-rw-r--) - Read/write for owner and group"
echo "  📜 Scripts (.sh): 775 (rwxrwxr-x) - Executable for owner and group"
echo "  ⚙️  Config files: 664 (rw-rw-r--) - Read/write for owner and group"
echo "  📄 Documentation: 664 (rw-rw-r--) - Read/write for owner and group"
echo "  🐳 Docker files: 664 (rw-rw-r--) - Read/write for owner and group"
echo "  🌐 Web files: 664 (rw-rw-r--) - Read/write for owner and group"

echo ""
echo -e "${GREEN}✓ Pi SSH permission setup completed!${NC}"
echo ""
echo "Pi SSH access is now configured with:"
echo "  ✅ All files writable via SSH"
echo "  ✅ Proper ownership set"
echo "  ✅ Git configured for Pi usage"
echo "  ✅ Scripts executable on Pi"
echo "  ✅ Consistent permissions across all file types"
echo ""
echo "You can now edit files on the Pi via SSH without permission errors!"
echo ""
echo "Test commands:"
echo "  ssh $PI_USER@$PI_HOST 'cd $PI_PATH && touch test_file.py'"
echo "  ssh $PI_USER@$PI_HOST 'cd $PI_PATH && echo \"# Test\" >> test_file.py'"
echo "  ssh $PI_USER@$PI_HOST 'cd $PI_PATH && rm test_file.py'"
