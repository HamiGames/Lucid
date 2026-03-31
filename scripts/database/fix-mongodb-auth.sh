#!/bin/bash
# Fix MongoDB Authentication - Creates/Updates MongoDB user with password from .env.secrets
# File: /app/scripts/database/fix-mongodb-auth.sh
# x-lucid-file-path: /app/scripts/database/fix-mongodb-auth.sh
# x-lucid-file-directory: /app/scripts/database
# x-lucid-file-type: shell
# This script fixes authentication issues where MongoDB user doesn't exist or has wrong password

set -e

_lucid_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_lucid_scripts="$_lucid_here"
while [[ "$_lucid_scripts" != "/" && "$(basename "$_lucid_scripts")" != "scripts" ]]; do
    _lucid_scripts="$(dirname "$_lucid_scripts")"
done
# shellcheck source=../lib/lucid-repo-paths.sh
source "$_lucid_scripts/lib/lucid-repo-paths.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔧 Fixing MongoDB Authentication${NC}"
echo "========================================"

# Get password from .env.secrets
ENV_SECRETS_FILE="$LUCID_ENV_CONFIG_DIR/.env.secrets"
if [ ! -f "$ENV_SECRETS_FILE" ]; then
    echo -e "${RED}❌ Error: .env.secrets file not found at $ENV_SECRETS_FILE${NC}"
    exit 1
fi

# Extract MONGODB_PASSWORD from .env.secrets
MONGODB_PASSWORD=$(grep "^MONGODB_PASSWORD=" "$ENV_SECRETS_FILE" | cut -d'=' -f2 | tr -d '"' | tr -d "'")
if [ -z "$MONGODB_PASSWORD" ]; then
    echo -e "${RED}❌ Error: MONGODB_PASSWORD not found in $ENV_SECRETS_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Found MONGODB_PASSWORD in .env.secrets${NC}"

# Check if MongoDB container is running
if ! docker ps | grep -q lucid-mongodb; then
    echo -e "${RED}❌ Error: lucid-mongodb container is not running${NC}"
    exit 1
fi

echo -e "${YELLOW}⏳ Checking MongoDB connection...${NC}"

# Try to connect without auth first (MongoDB might be running without auth if not initialized)
# Check if we can connect without authentication
if docker exec lucid-mongodb mongosh --quiet --eval "db.runCommand({ ping: 1 })" 2>/dev/null; then
    echo -e "${GREEN}✅ MongoDB is accessible without authentication${NC}"
    AUTH_DISABLED=true
else
    echo -e "${YELLOW}⚠️ MongoDB requires authentication${NC}"
    AUTH_DISABLED=false
    
    # Try to connect with password from .env.secrets
    if docker exec lucid-mongodb mongosh --quiet -u lucid -p "$MONGODB_PASSWORD" --authenticationDatabase admin --eval "db.runCommand({ ping: 1 })" 2>/dev/null; then
        echo -e "${GREEN}✅ MongoDB authentication is working correctly${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠️ Authentication failed, will attempt to fix...${NC}"
    fi
fi

echo -e "${YELLOW}⏳ Fixing MongoDB user authentication...${NC}"

if [ "$AUTH_DISABLED" = true ]; then
    # MongoDB is running without auth, create/update user
    echo -e "${YELLOW}Creating/updating MongoDB user 'lucid'...${NC}"
    
    docker exec lucid-mongodb mongosh admin --quiet --eval "
        try {
            var user = db.getUser('lucid');
            if (user) {
                print('User exists, updating password...');
                db.changeUserPassword('lucid', '$MONGODB_PASSWORD');
                print('✅ Password updated successfully');
            } else {
                print('User does not exist, creating...');
                db.createUser({
                    user: 'lucid',
                    pwd: '$MONGODB_PASSWORD',
                    roles: [
                        { role: 'userAdminAnyDatabase', db: 'admin' },
                        { role: 'readWriteAnyDatabase', db: 'admin' },
                        { role: 'dbAdminAnyDatabase', db: 'admin' },
                        { role: 'clusterAdmin', db: 'admin' }
                    ]
                });
                print('✅ User created successfully');
            }
        } catch(e) {
            print('❌ Error: ' + e.message);
            quit(1);
        }
    "
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ MongoDB user 'lucid' created/updated successfully${NC}"
        
        # Verify authentication works
        echo -e "${YELLOW}⏳ Verifying authentication...${NC}"
        if docker exec lucid-mongodb mongosh --quiet -u lucid -p "$MONGODB_PASSWORD" --authenticationDatabase admin --eval "db.runCommand({ ping: 1 })" 2>/dev/null; then
            echo -e "${GREEN}✅ Authentication verified successfully${NC}"
            exit 0
        else
            echo -e "${RED}❌ Authentication verification failed${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ Failed to create/update MongoDB user${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ MongoDB authentication is enabled but user cannot be created/updated${NC}"
    echo -e "${YELLOW}💡 You may need to temporarily disable --auth or clear MongoDB data${NC}"
    exit 1
fi

