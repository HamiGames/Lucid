#!/bin/bash
# MongoDB Schema Initialization Script
# File: /app/scripts/init_mongodb_schema.sh
# x-lucid-file-path: /app/scripts/init_mongodb_schema.sh
# x-lucid-file-directory: /app/scripts
# x-lucid-file-type: shell
# LUCID-STRICT Layer 1 Core Infrastructure
# Generated: 2025-10-04

set -e

# Configuration
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB="${MONGO_DB:-lucid}"
MONGO_USER="${MONGO_USER:-lucid_admin}"
MONGO_PASS="${MONGO_PASS:-lucid_password}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔧 LUCID MongoDB Schema Initialization${NC}"
echo "========================================"

# Wait for MongoDB to be ready
echo -e "${YELLOW}⏳ Waiting for MongoDB to be ready...${NC}"
for i in {1..30}; do
    if mongosh --host $MONGO_HOST --port $MONGO_PORT --eval "db.runCommand({ping: 1})" &>/dev/null; then
        echo -e "${GREEN}✅ MongoDB is ready${NC}"
        break
    fi
    echo -e "${YELLOW}⏳ Waiting... ($i/30)${NC}"
    sleep 2
done

# Check if MongoDB is running
if ! mongosh --host $MONGO_HOST --port $MONGO_PORT --eval "db.runCommand({ping: 1})" &>/dev/null; then
    echo -e "${RED}❌ MongoDB is not running or not accessible${NC}"
    exit 1
fi

# Create admin user if authentication is enabled
if [ -n "$MONGO_USER" ] && [ -n "$MONGO_PASS" ]; then
    echo -e "${YELLOW}🔐 Creating admin user...${NC}"
    mongosh --host $MONGO_HOST --port $MONGO_PORT admin <<EOF
    db.createUser({
        user: "$MONGO_USER",
        pwd: "$MONGO_PASS",
        roles: [
            { role: "userAdminAnyDatabase", db: "admin" },
            { role: "readWriteAnyDatabase", db: "admin" },
            { role: "dbAdminAnyDatabase", db: "admin" }
        ]
    });
EOF
fi

# Initialize database schema
echo -e "${YELLOW}📊 Initializing database schema...${NC}"
if [ -n "$MONGO_USER" ] && [ -n "$MONGO_PASS" ]; then
    mongosh --host $MONGO_HOST --port $MONGO_PORT -u "$MONGO_USER" -p "$MONGO_PASS" --authenticationDatabase admin $MONGO_DB < database/init_collections.js
else
    mongosh --host $MONGO_HOST --port $MONGO_PORT $MONGO_DB < database/init_collections.js
fi

# Verify schema creation
echo -e "${YELLOW}🔍 Verifying schema...${NC}"
COLLECTIONS=$(mongosh --host $MONGO_HOST --port $MONGO_PORT -u "$MONGO_USER" -p "$MONGO_PASS" --authenticationDatabase admin $MONGO_DB --quiet --eval "db.getCollectionNames().join(',')")

if [[ $COLLECTIONS == *"sessions"* ]] && [[ $COLLECTIONS == *"authentication"* ]] && [[ $COLLECTIONS == *"work_proofs"* ]]; then
    echo -e "${GREEN}✅ Schema initialized successfully${NC}"
    echo "Collections created: $COLLECTIONS"
else
    echo -e "${RED}❌ Schema initialization failed${NC}"
    exit 1
fi

# Create indexes verification
echo -e "${YELLOW}🔍 Verifying indexes...${NC}"
INDEX_COUNT=$(mongosh --host $MONGO_HOST --port $MONGO_PORT -u "$MONGO_USER" -p "$MONGO_PASS" --authenticationDatabase admin $MONGO_DB --quiet --eval "
    let count = 0;
    db.getCollectionNames().forEach(function(name) {
        count += db[name].getIndexes().length;
    });
    print(count);
")

echo -e "${GREEN}✅ Total indexes created: $INDEX_COUNT${NC}"

# Test basic operations
echo -e "${YELLOW}🧪 Testing basic operations...${NC}"
TEST_RESULT=$(mongosh --host $MONGO_HOST --port $MONGO_PORT -u "$MONGO_USER" -p "$MONGO_PASS" --authenticationDatabase admin $MONGO_DB --quiet --eval "
    try {
        db.sessions.insertOne({
            _id: 'test_session_001',
            owner_address: 'TXYZ1234567890123456789012345678901234567',
            started_at: new Date(),
            status: 'pending',
            chunks: [],
            merkle_root: '0000000000000000000000000000000000000000000000000000000000000000'
        });
        db.sessions.deleteOne({_id: 'test_session_001'});
        print('SUCCESS');
    } catch (e) {
        print('FAILED: ' + e.message);
    }
")

if [[ $TEST_RESULT == "SUCCESS" ]]; then
    echo -e "${GREEN}✅ Basic operations test passed${NC}"
else
    echo -e "${RED}❌ Basic operations test failed: $TEST_RESULT${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 MongoDB schema initialization completed successfully!${NC}"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Start the LUCID services"
echo "2. Verify session pipeline functionality"
echo "3. Test authentication flow"
echo "4. Deploy to Pi 5 for final testing"
