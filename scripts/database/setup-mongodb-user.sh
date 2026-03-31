#!/bin/bash
# MongoDB User Setup Script for Lucid Project
# File: /app/scripts/database/setup-mongodb-user.sh
# x-lucid-file-path: /app/scripts/database/setup-mongodb-user.sh
# x-lucid-file-directory: /app/scripts/database
# x-lucid-file-type: shell
# Purpose: Create the 'lucid' user in MongoDB admin database
# Usage: Run this script ONCE to set up MongoDB authentication
# File: scripts/database/setup-mongodb-user.sh

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

echo -e "${GREEN}🔧 MongoDB User Setup for Lucid Project${NC}"
echo "=========================================="

# Get project root
PROJECT_ROOT="${PROJECT_ROOT:-$LUCID_REPO_ROOT}"
ENV_SECRETS="${PROJECT_ROOT}/configs/environment/.env.secrets"

# Check if env file exists
if [ ! -f "$ENV_SECRETS" ]; then
    echo -e "${RED}❌ Error: .env.secrets file not found at $ENV_SECRETS${NC}"
    exit 1
fi

# Get MongoDB password from env file
MONGODB_PASSWORD=$(grep "^MONGODB_PASSWORD=" "$ENV_SECRETS" | cut -d= -f2)

if [ -z "$MONGODB_PASSWORD" ]; then
    echo -e "${RED}❌ Error: MONGODB_PASSWORD not found in $ENV_SECRETS${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Configuration:${NC}"
echo "   Project Root: $PROJECT_ROOT"
echo "   MongoDB Container: lucid-mongodb"
echo "   User: lucid"
echo "   Password: ${MONGODB_PASSWORD:0:2}... (hidden)"

# Check if MongoDB container is running
if ! docker ps | grep -q "lucid-mongodb"; then
    echo -e "${RED}❌ Error: lucid-mongodb container is not running${NC}"
    echo -e "${YELLOW}💡 Start MongoDB first:${NC}"
    echo "   docker compose -f ${LUCID_HOST_COMPOSE_FOUNDATION} --env-file $PROJECT_ROOT/configs/environment/.env.foundation --env-file $PROJECT_ROOT/configs/environment/.env.support --env-file $PROJECT_ROOT/configs/environment/.env.distroless --env-file $PROJECT_ROOT/configs/environment/.env.secrets up -d lucid-mongodb"
    exit 1
fi

echo -e "${YELLOW}⏳ Waiting for MongoDB to be ready...${NC}"
for i in {1..30}; do
    if docker exec lucid-mongodb mongosh --quiet --eval "db.runCommand({ ping: 1 })" 2>/dev/null >/dev/null; then
        echo -e "${GREEN}✅ MongoDB is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ MongoDB did not become ready in time${NC}"
        exit 1
    fi
    sleep 2
done

# Check if user already exists
echo -e "${YELLOW}🔍 Checking if 'lucid' user exists...${NC}"
USER_EXISTS=$(docker exec lucid-mongodb mongosh --quiet admin --eval "try { db.getUser('lucid'); print('EXISTS'); } catch(e) { print('NOT_EXISTS'); }" 2>/dev/null | grep -q "EXISTS" && echo "yes" || echo "no")

if [ "$USER_EXISTS" = "yes" ]; then
    echo -e "${GREEN}ℹ️  User 'lucid' already exists${NC}"
    echo -e "${YELLOW}🔄 Testing authentication...${NC}"
    if docker exec lucid-mongodb mongosh --quiet -u lucid -p "$MONGODB_PASSWORD" --authenticationDatabase admin --eval "db.runCommand({ connectionStatus: 1 })" 2>/dev/null >/dev/null; then
        echo -e "${GREEN}✅ User 'lucid' exists and authentication works${NC}"
        exit 0
    else
        echo -e "${RED}❌ User exists but authentication failed. Password may be incorrect.${NC}"
        echo -e "${YELLOW}💡 You may need to update the user password or check MONGODB_PASSWORD in .env.secrets${NC}"
        exit 1
    fi
fi

# MongoDB is running with --auth, so we need to connect without auth first
# Check if we can connect without authentication (localhost connections might work)
echo -e "${YELLOW}🔐 Attempting to create 'lucid' user...${NC}"

# Try to create user (this will work if MongoDB allows localhost connections without auth)
CREATE_RESULT=$(docker exec lucid-mongodb mongosh --quiet admin --eval "
try {
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
    print('SUCCESS');
} catch(e) {
    if (e.message.includes('already exists')) {
        print('ALREADY_EXISTS');
    } else if (e.message.includes('requires authentication')) {
        print('AUTH_REQUIRED');
    } else {
        print('ERROR: ' + e.message);
    }
}
" 2>&1)

if echo "$CREATE_RESULT" | grep -q "SUCCESS"; then
    echo -e "${GREEN}✅ User 'lucid' created successfully${NC}"
elif echo "$CREATE_RESULT" | grep -q "ALREADY_EXISTS"; then
    echo -e "${GREEN}ℹ️  User 'lucid' already exists${NC}"
elif echo "$CREATE_RESULT" | grep -q "AUTH_REQUIRED"; then
    echo -e "${RED}❌ MongoDB requires authentication to create users${NC}"
    echo -e "${YELLOW}💡 Solution: MongoDB is running with --auth but no users exist yet.${NC}"
    echo -e "${YELLOW}   You need to temporarily disable --auth, create the user, then re-enable it.${NC}"
    echo ""
    echo -e "${YELLOW}📝 Manual steps:${NC}"
    echo "   1. Stop MongoDB: docker stop lucid-mongodb"
    echo "   2. Edit host file ${LUCID_HOST_REL_COMPOSE_FOUNDATION} (in-image ${LUCID_X_IMAGE_COMPOSE_FOUNDATION} per x-files-listing.txt)"
    echo "   3. Remove '--auth' from lucid-mongodb command (line ~166)"
    echo "   4. Start MongoDB: docker compose -f ... up -d lucid-mongodb"
    echo "   5. Run this script again"
    echo "   6. Re-add '--auth' to ${LUCID_HOST_REL_COMPOSE_FOUNDATION}"
    echo "   7. Restart MongoDB"
    exit 1
else
    echo -e "${RED}❌ Failed to create user: $CREATE_RESULT${NC}"
    exit 1
fi

# Verify the user works
echo -e "${YELLOW}✅ Verifying user authentication...${NC}"
if docker exec lucid-mongodb mongosh --quiet -u lucid -p "$MONGODB_PASSWORD" --authenticationDatabase admin --eval "db.runCommand({ connectionStatus: 1 })" 2>/dev/null >/dev/null; then
    echo -e "${GREEN}✅ User 'lucid' created and authentication verified${NC}"
    echo -e "${GREEN}🎉 MongoDB user setup completed successfully!${NC}"
else
    echo -e "${RED}❌ User created but authentication test failed${NC}"
    exit 1
fi

