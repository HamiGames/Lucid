#!/bin/bash
# MongoDB Health Check Script for Lucid Database Services
# File: /app/configs/docker//databases/mongodb-health.sh
# x-lucid-file-path: /app/configs/docker//databases/mongodb-health.sh
# x-lucid-file-directory: /app/configs/docker//databases
# x-lucid-file-type: shell
# LUCID-STRICT Layer 0 Core Infrastructure

set -euo pipefail

# Configuration
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_USER="${MONGO_USER:-lucid}"
MONGO_PASS="${MONGO_PASS:-lucid}"
MONGO_DB="${MONGO_DB:-lucid}"
MONGO_AUTH_DB="${MONGO_AUTH_DB:-admin}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${GREEN}[HEALTH]${NC} $1" >&2; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1" >&2; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# Health check function
check_mongodb_health() {
    local exit_code=0
    
    # Test 1: Basic connectivity
    log_info "Testing MongoDB connectivity..."
    if mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" --quiet --eval "db.runCommand({ping: 1})" >/dev/null 2>&1; then
        log_info "✅ MongoDB connectivity test passed"
    else
        log_error "❌ MongoDB connectivity test failed"
        exit_code=1
    fi
    
    # Test 2: Authentication
    log_info "Testing MongoDB authentication..."
    if mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" -u "$MONGO_USER" -p "$MONGO_PASS" --authenticationDatabase "$MONGO_AUTH_DB" --quiet --eval "db.runCommand({ping: 1})" >/dev/null 2>&1; then
        log_info "✅ MongoDB authentication test passed"
    else
        log_error "❌ MongoDB authentication test failed"
        exit_code=1
    fi
    
    # Test 3: Database access
    log_info "Testing database access..."
    if mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" -u "$MONGO_USER" -p "$MONGO_PASS" --authenticationDatabase "$MONGO_AUTH_DB" "$MONGO_DB" --quiet --eval "db.runCommand({ping: 1})" >/dev/null 2>&1; then
        log_info "✅ Database access test passed"
    else
        log_error "❌ Database access test failed"
        exit_code=1
    fi
    
    # Test 4: Replica set status (if applicable)
    log_info "Testing replica set status..."
    if mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" -u "$MONGO_USER" -p "$MONGO_PASS" --authenticationDatabase "$MONGO_AUTH_DB" --quiet --eval "rs.status().ok" | grep -q "1" 2>/dev/null; then
        log_info "✅ Replica set status test passed"
    else
        log_warning "⚠️ Replica set status test failed or not applicable"
    fi
    
    # Test 5: Collection operations
    log_info "Testing collection operations..."
    if mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" -u "$MONGO_USER" -p "$MONGO_PASS" --authenticationDatabase "$MONGO_AUTH_DB" "$MONGO_DB" --quiet --eval "
        try {
            db.health_check.insertOne({test: 'health_check', timestamp: new Date()});
            db.health_check.deleteOne({test: 'health_check'});
            print('SUCCESS');
        } catch (e) {
            print('FAILED: ' + e.message);
        }
    " | grep -q "SUCCESS" 2>/dev/null; then
        log_info "✅ Collection operations test passed"
    else
        log_error "❌ Collection operations test failed"
        exit_code=1
    fi
    
    # Test 6: Index operations
    log_info "Testing index operations..."
    if mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" -u "$MONGO_USER" -p "$MONGO_PASS" --authenticationDatabase "$MONGO_AUTH_DB" "$MONGO_DB" --quiet --eval "
        try {
            db.health_check.createIndex({test: 1});
            db.health_check.dropIndex({test: 1});
            print('SUCCESS');
        } catch (e) {
            print('FAILED: ' + e.message);
        }
    " | grep -q "SUCCESS" 2>/dev/null; then
        log_info "✅ Index operations test passed"
    else
        log_error "❌ Index operations test failed"
        exit_code=1
    fi
    
    return $exit_code
}

# Main execution
main() {
    log_info "Starting MongoDB health check..."
    log_info "Host: $MONGO_HOST:$MONGO_PORT"
    log_info "Database: $MONGO_DB"
    log_info "User: $MONGO_USER"
    
    if check_mongodb_health; then
        log_info "🎉 All MongoDB health checks passed"
        exit 0
    else
        log_error "💥 MongoDB health checks failed"
        exit 1
    fi
}

# Run main function
main "$@"
