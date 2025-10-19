#!/bin/bash
# scripts/foundation/fix-pi-permissions.sh
# Fix file permissions on Raspberry Pi for SSH access

set -e

echo "Fixing file permissions on Raspberry Pi..."

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

# Pi connection details
PI_USER="pickme"
PI_HOST="192.168.0.75"
PI_PATH="/mnt/myssd/Lucid"

echo "=== Fixing Permissions on Raspberry Pi ==="

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
    exit 1
fi

# Fix directory permissions on Pi
echo "Fixing directory permissions on Pi..."
if ssh $PI_USER@$PI_HOST "find $PI_PATH -type d -not -path '$PI_PATH/.git/*' -not -path '$PI_PATH/.venv/*' -exec chmod 775 {} \;" &> /dev/null; then
    print_status 0 "Directory permissions fixed on Pi"
else
    print_status 1 "Failed to fix directory permissions on Pi"
    exit 1
fi

# Fix Python file permissions on Pi
echo "Fixing Python file permissions on Pi..."
if ssh $PI_USER@$PI_HOST "find $PI_PATH -type f -name '*.py' -not -path '$PI_PATH/.git/*' -not -path '$PI_PATH/.venv/*' -exec chmod 664 {} \;" &> /dev/null; then
    print_status 0 "Python file permissions fixed on Pi"
else
    print_status 1 "Failed to fix Python file permissions on Pi"
    exit 1
fi

# Fix __init__.py files specifically on Pi
echo "Fixing __init__.py file permissions on Pi..."
if ssh $PI_USER@$PI_HOST "find $PI_PATH -name '__init__.py' -type f -not -path '$PI_PATH/.git/*' -not -path '$PI_PATH/.venv/*' -exec chmod 664 {} \;" &> /dev/null; then
    print_status 0 "__init__.py file permissions fixed on Pi"
else
    print_status 1 "Failed to fix __init__.py file permissions on Pi"
    exit 1
fi

# Fix other common file types
echo "Fixing other file permissions on Pi..."
if ssh $PI_USER@$PI_HOST "find $PI_PATH -type f \( -name '*.sh' -o -name '*.yml' -o -name '*.yaml' -o -name '*.json' -o -name '*.md' -o -name '*.txt' -o -name '*.env' \) -not -path '$PI_PATH/.git/*' -not -path '$PI_PATH/.venv/*' -exec chmod 664 {} \;" &> /dev/null; then
    print_status 0 "Other file permissions fixed on Pi"
else
    print_status 1 "Failed to fix other file permissions on Pi"
    exit 1
fi

# Set ownership to pi user
echo "Setting file ownership on Pi..."
if ssh $PI_USER@$PI_HOST "sudo chown -R $PI_USER:$PI_USER $PI_PATH" &> /dev/null; then
    print_status 0 "File ownership set on Pi"
else
    print_status 1 "Failed to set file ownership on Pi"
    echo "Note: This may require sudo privileges on the Pi"
fi

# Configure git filemode on Pi
echo "Configuring git filemode on Pi..."
if ssh $PI_USER@$PI_HOST "cd $PI_PATH && git config core.filemode false" &> /dev/null; then
    print_status 0 "Git filemode configured on Pi"
else
    print_status 1 "Failed to configure git filemode on Pi"
fi

echo ""
echo -e "${GREEN}✓ Pi permissions fix completed!${NC}"
echo "Files on the Pi should now be writable via SSH."
echo ""
echo "To test, try editing a file via SSH:"
echo "ssh $PI_USER@$PI_HOST 'echo \"# Test edit\" >> $PI_PATH/test_file.py'"
