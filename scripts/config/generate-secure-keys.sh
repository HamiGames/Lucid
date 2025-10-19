#!/bin/bash
# Generate Secure Keys and Passwords for Lucid Project
# Based on: lucid-container-build-plan.plan.md Step 2
# Generated: 2025-01-14

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔐 Generating Secure Keys and Passwords for Lucid Project${NC}"
echo "=================================================="

# Function to generate secure random string
generate_secure_string() {
    local length=${1:-32}
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
}

# Function to generate JWT secret (64 characters)
generate_jwt_secret() {
    openssl rand -base64 48 | tr -d "=+/"
}

# Function to generate encryption key (32 bytes = 256 bits)
generate_encryption_key() {
    openssl rand -hex 32
}

# Function to generate Tor control password
generate_tor_password() {
    openssl rand -base64 32 | tr -d "=+/"
}

# Function to generate database passwords
generate_db_password() {
    openssl rand -base64 24 | tr -d "=+/"
}

echo -e "${YELLOW}📝 Generating secure keys and passwords...${NC}"

# Generate JWT Secret Key (64 characters)
JWT_SECRET_KEY=$(generate_jwt_secret)
echo "JWT_SECRET_KEY generated: ${JWT_SECRET_KEY:0:8}..."

# Generate Encryption Key (256-bit)
ENCRYPTION_KEY=$(generate_encryption_key)
echo "ENCRYPTION_KEY generated: ${ENCRYPTION_KEY:0:8}..."

# Generate Tor Control Password
TOR_CONTROL_PASSWORD=$(generate_tor_password)
echo "TOR_CONTROL_PASSWORD generated: ${TOR_CONTROL_PASSWORD:0:8}..."

# Generate MongoDB Password
MONGODB_PASSWORD=$(generate_db_password)
echo "MONGODB_PASSWORD generated: ${MONGODB_PASSWORD:0:8}..."

# Generate Redis Password
REDIS_PASSWORD=$(generate_db_password)
echo "REDIS_PASSWORD generated: ${REDIS_PASSWORD:0:8}..."

# Generate Elasticsearch Password
ELASTICSEARCH_PASSWORD=$(generate_db_password)
echo "ELASTICSEARCH_PASSWORD generated: ${ELASTICSEARCH_PASSWORD:0:8}..."

# Generate API Gateway Secret
API_GATEWAY_SECRET=$(generate_secure_string 32)
echo "API_GATEWAY_SECRET generated: ${API_GATEWAY_SECRET:0:8}..."

# Generate Blockchain Secret
BLOCKCHAIN_SECRET=$(generate_secure_string 32)
echo "BLOCKCHAIN_SECRET generated: ${BLOCKCHAIN_SECRET:0:8}..."

# Generate Session Secret
SESSION_SECRET=$(generate_secure_string 32)
echo "SESSION_SECRET generated: ${SESSION_SECRET:0:8}..."

# Generate Node Management Secret
NODE_MANAGEMENT_SECRET=$(generate_secure_string 32)
echo "NODE_MANAGEMENT_SECRET generated: ${NODE_MANAGEMENT_SECRET:0:8}..."

# Generate Admin Secret
ADMIN_SECRET=$(generate_secure_string 32)
echo "ADMIN_SECRET generated: ${ADMIN_SECRET:0:8}..."

# Generate TRON Payment Secret
TRON_PAYMENT_SECRET=$(generate_secure_string 32)
echo "TRON_PAYMENT_SECRET generated: ${TRON_PAYMENT_SECRET:0:8}..."

echo -e "${GREEN}✅ All secure keys and passwords generated successfully!${NC}"

# Create secure environment file
SECURE_ENV_FILE="configs/environment/.env.secure"
echo -e "${YELLOW}📄 Creating secure environment file: ${SECURE_ENV_FILE}${NC}"

cat > "$SECURE_ENV_FILE" << EOF
# Lucid Secure Environment Variables
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# WARNING: Keep this file secure and never commit to version control

# ============================================================================
# SECURITY KEYS AND PASSWORDS
# ============================================================================

# JWT Configuration
JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Encryption Configuration
ENCRYPTION_KEY=${ENCRYPTION_KEY}
ENCRYPTION_ALGORITHM=AES-256-GCM

# Tor Configuration
TOR_CONTROL_PASSWORD=${TOR_CONTROL_PASSWORD}
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051

# Database Passwords
MONGODB_PASSWORD=${MONGODB_PASSWORD}
REDIS_PASSWORD=${REDIS_PASSWORD}
ELASTICSEARCH_PASSWORD=${ELASTICSEARCH_PASSWORD}

# Service Secrets
API_GATEWAY_SECRET=${API_GATEWAY_SECRET}
BLOCKCHAIN_SECRET=${BLOCKCHAIN_SECRET}
SESSION_SECRET=${SESSION_SECRET}
NODE_MANAGEMENT_SECRET=${NODE_MANAGEMENT_SECRET}
ADMIN_SECRET=${ADMIN_SECRET}
TRON_PAYMENT_SECRET=${TRON_PAYMENT_SECRET}

# ============================================================================
# GENERATED VALUES FOR BUILD PLAN
# ============================================================================
GENERATED_JWT_SECRET=${JWT_SECRET_KEY}
GENERATED_ENCRYPTION_KEY=${ENCRYPTION_KEY}
GENERATED_TOR_PASSWORD=${TOR_CONTROL_PASSWORD}
GENERATED_MONGODB_PASSWORD=${MONGODB_PASSWORD}
GENERATED_REDIS_PASSWORD=${REDIS_PASSWORD}

# ============================================================================
# SECURITY NOTES
# ============================================================================
# - All keys are cryptographically secure random values
# - JWT_SECRET_KEY: 64 characters, base64 encoded
# - ENCRYPTION_KEY: 256-bit (32 bytes) hex encoded
# - Database passwords: 24 characters, base64 encoded
# - Service secrets: 32 characters, base64 encoded
# - Store this file securely and never commit to version control
# - Rotate keys regularly in production environments
EOF

echo -e "${GREEN}✅ Secure environment file created: ${SECURE_ENV_FILE}${NC}"

# Create .env files for each phase with the generated values
echo -e "${YELLOW}📄 Updating phase environment files with generated values...${NC}"

# Update foundation.env
if [ -f "configs/environment/foundation.env" ]; then
    sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=${JWT_SECRET_KEY}/" configs/environment/foundation.env
    sed -i "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=${ENCRYPTION_KEY}/" configs/environment/foundation.env
    sed -i "s/TOR_CONTROL_PASSWORD=.*/TOR_CONTROL_PASSWORD=${TOR_CONTROL_PASSWORD}/" configs/environment/foundation.env
    sed -i "s/MONGODB_PASSWORD=.*/MONGODB_PASSWORD=${MONGODB_PASSWORD}/" configs/environment/foundation.env
    sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=${REDIS_PASSWORD}/" configs/environment/foundation.env
    echo "✅ Updated foundation.env"
fi

# Update core.env
if [ -f "configs/environment/env.core" ]; then
    sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=${JWT_SECRET_KEY}/" configs/environment/env.core
    sed -i "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=${ENCRYPTION_KEY}/" configs/environment/env.core
    sed -i "s/MONGODB_PASSWORD=.*/MONGODB_PASSWORD=${MONGODB_PASSWORD}/" configs/environment/env.core
    sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=${REDIS_PASSWORD}/" configs/environment/env.core
    echo "✅ Updated env.core"
fi

# Update application.env
if [ -f "configs/environment/env.application" ]; then
    sed -i "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=${ENCRYPTION_KEY}/" configs/environment/env.application
    sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=${JWT_SECRET_KEY}/" configs/environment/env.application
    sed -i "s/MONGODB_PASSWORD=.*/MONGODB_PASSWORD=${MONGODB_PASSWORD}/" configs/environment/env.application
    sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=${REDIS_PASSWORD}/" configs/environment/env.application
    echo "✅ Updated env.application"
fi

# Update support.env
if [ -f "configs/environment/env.support" ]; then
    sed -i "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=${ENCRYPTION_KEY}/" configs/environment/env.support
    sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=${JWT_SECRET_KEY}/" configs/environment/env.support
    sed -i "s/MONGODB_PASSWORD=.*/MONGODB_PASSWORD=${MONGODB_PASSWORD}/" configs/environment/env.support
    sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=${REDIS_PASSWORD}/" configs/environment/env.support
    sed -i "s/TOR_CONTROL_PASSWORD=.*/TOR_CONTROL_PASSWORD=${TOR_CONTROL_PASSWORD}/" configs/environment/env.support
    echo "✅ Updated env.support"
fi

# Update gui.env
if [ -f "configs/environment/env.gui" ]; then
    sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=${JWT_SECRET_KEY}/" configs/environment/env.gui
    sed -i "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=${ENCRYPTION_KEY}/" configs/environment/env.gui
    sed -i "s/TOR_CONTROL_PASSWORD=.*/TOR_CONTROL_PASSWORD=${TOR_CONTROL_PASSWORD}/" configs/environment/env.gui
    echo "✅ Updated env.gui"
fi

echo -e "${GREEN}🎉 All environment files updated with secure values!${NC}"
echo ""
echo -e "${RED}⚠️  IMPORTANT SECURITY NOTES:${NC}"
echo "1. The .env.secure file contains sensitive data - never commit to version control"
echo "2. Store these keys securely in production environments"
echo "3. Rotate keys regularly in production"
echo "4. Use environment-specific key management in production"
echo ""
echo -e "${BLUE}📋 Next Steps:${NC}"
echo "1. Review the generated .env.secure file"
echo "2. Update your .gitignore to exclude .env.secure"
echo "3. Use these values in your deployment scripts"
echo "4. Consider using a secrets management system for production"

echo -e "${GREEN}✅ Secure key generation completed successfully!${NC}"
