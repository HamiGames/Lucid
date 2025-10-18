#!/bin/bash
# Redis Initialization Script
# Database Cluster 08: Storage Database
# Step 3: Redis & Elasticsearch Setup

set -e

echo "========================================="
echo "Redis 7.0 Initialization Script"
echo "Lucid Blockchain System"
echo "========================================="

# Configuration
REDIS_VERSION="7.0"
REDIS_CONF="${REDIS_CONF:-/etc/redis/redis.conf}"
REDIS_DATA_DIR="${REDIS_DATA_DIR:-/data/redis}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "ℹ $1"
}

# Check if Redis is installed
check_redis_installed() {
    print_info "Checking Redis installation..."
    if command -v redis-server &> /dev/null; then
        INSTALLED_VERSION=$(redis-server --version | grep -oP 'v=\K[0-9.]+' | cut -d. -f1-2)
        print_success "Redis found: version ${INSTALLED_VERSION}"
        return 0
    else
        print_error "Redis not found"
        return 1
    fi
}

# Install Redis if not present
install_redis() {
    print_info "Installing Redis ${REDIS_VERSION}..."
    
    if [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        apt-get update
        apt-get install -y redis-server redis-tools
    elif [ -f /etc/redhat-release ]; then
        # RHEL/CentOS
        yum install -y redis
    else
        print_error "Unsupported OS"
        exit 1
    fi
    
    print_success "Redis installed"
}

# Create Redis data directory
create_data_directory() {
    print_info "Creating Redis data directory: ${REDIS_DATA_DIR}"
    mkdir -p "${REDIS_DATA_DIR}"
    chmod 755 "${REDIS_DATA_DIR}"
    
    # Set ownership to redis user if it exists
    if id redis &>/dev/null; then
        chown -R redis:redis "${REDIS_DATA_DIR}"
    fi
    
    print_success "Data directory created"
}

# Copy Redis configuration
setup_configuration() {
    print_info "Setting up Redis configuration..."
    
    # Check if custom config exists
    CUSTOM_CONF="configs/database/redis/redis.conf"
    if [ -f "${CUSTOM_CONF}" ]; then
        print_info "Using custom configuration from ${CUSTOM_CONF}"
        cp "${CUSTOM_CONF}" "${REDIS_CONF}"
    else
        print_warning "Custom config not found, using default"
    fi
    
    # Update configuration with environment variables
    if [ -n "${REDIS_PASSWORD}" ]; then
        sed -i "s/# requirepass .*/requirepass ${REDIS_PASSWORD}/" "${REDIS_CONF}"
        print_success "Password authentication configured"
    fi
    
    # Set data directory
    sed -i "s|dir /data|dir ${REDIS_DATA_DIR}|" "${REDIS_CONF}"
    
    print_success "Configuration updated"
}

# Start Redis service
start_redis() {
    print_info "Starting Redis service..."
    
    # Check if running in Docker
    if [ -f /.dockerenv ]; then
        redis-server "${REDIS_CONF}" &
        REDIS_PID=$!
        sleep 2
    else
        systemctl start redis
        systemctl enable redis
    fi
    
    print_success "Redis service started"
}

# Wait for Redis to be ready
wait_for_redis() {
    print_info "Waiting for Redis to be ready..."
    
    MAX_ATTEMPTS=30
    ATTEMPT=0
    
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        if redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ping &>/dev/null; then
            print_success "Redis is ready"
            return 0
        fi
        
        ATTEMPT=$((ATTEMPT+1))
        echo -n "."
        sleep 1
    done
    
    print_error "Redis failed to start"
    return 1
}

# Configure Redis for Lucid
configure_lucid_settings() {
    print_info "Configuring Redis for Lucid blockchain..."
    
    # Set up database allocation
    # DB 0: Session tokens and rate limiting
    # DB 1: Authentication data
    # DB 2: Node metrics and monitoring
    # DB 3: Cache data
    
    print_info "Database allocation:"
    print_info "  DB 0: Session tokens and rate limiting"
    print_info "  DB 1: Authentication data"
    print_info "  DB 2: Node metrics and monitoring"
    print_info "  DB 3: Cache data"
    
    # Test database connectivity
    for db in 0 1 2 3; do
        if redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" -n ${db} PING &>/dev/null; then
            print_success "Database ${db} accessible"
        else
            print_error "Database ${db} not accessible"
        fi
    done
}

# Create Redis indices (keyspace patterns)
setup_keyspace_patterns() {
    print_info "Setting up keyspace patterns..."
    
    # Document keyspace patterns for Lucid
    cat > /tmp/redis_keyspace_patterns.txt << 'EOF'
# Lucid Redis Keyspace Patterns

# Session Tokens (DB 0)
session:token:{token_id}         -> User session data (TTL: 900s = 15min)
session:refresh:{token_id}       -> Refresh token data (TTL: 604800s = 7days)

# Rate Limiting (DB 0)
ratelimit:user:{user_id}         -> User request count (TTL: 60s)
ratelimit:ip:{ip_address}        -> IP request count (TTL: 60s)
ratelimit:endpoint:{endpoint}    -> Endpoint request count (TTL: 60s)

# Authentication (DB 1)
auth:user:{user_id}              -> User auth data
auth:jwt:{token_hash}            -> JWT token validation cache (TTL: 900s)

# Node Metrics (DB 2)
node:metrics:{node_id}           -> Node metrics (TTL: 30s)
node:status:{node_id}            -> Node status (TTL: 60s)
node:poot:{node_id}              -> PoOT score cache (TTL: 300s)

# Cache (DB 3)
cache:blockchain:info            -> Blockchain info (TTL: 300s)
cache:block:{block_height}       -> Block data cache (TTL: 3600s)
cache:session:{session_id}       -> Session metadata cache (TTL: 300s)
EOF
    
    print_success "Keyspace patterns documented at /tmp/redis_keyspace_patterns.txt"
}

# Verify Redis configuration
verify_configuration() {
    print_info "Verifying Redis configuration..."
    
    # Check memory configuration
    MAX_MEMORY=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" CONFIG GET maxmemory | tail -1)
    print_info "Max memory: ${MAX_MEMORY}"
    
    # Check persistence settings
    AOF_ENABLED=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" CONFIG GET appendonly | tail -1)
    print_info "AOF persistence: ${AOF_ENABLED}"
    
    # Check eviction policy
    EVICTION_POLICY=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" CONFIG GET maxmemory-policy | tail -1)
    print_info "Eviction policy: ${EVICTION_POLICY}"
    
    print_success "Configuration verified"
}

# Performance tuning
performance_tuning() {
    print_info "Applying performance tuning..."
    
    # Disable Transparent Huge Pages (THP)
    if [ -f /sys/kernel/mm/transparent_hugepage/enabled ]; then
        echo never > /sys/kernel/mm/transparent_hugepage/enabled
        print_success "THP disabled"
    fi
    
    # Set TCP backlog
    sysctl -w net.core.somaxconn=65535 || print_warning "Could not set somaxconn"
    
    # Set overcommit memory
    sysctl -w vm.overcommit_memory=1 || print_warning "Could not set overcommit_memory"
    
    print_success "Performance tuning applied"
}

# Run health check
health_check() {
    print_info "Running health check..."
    
    # Basic ping test
    if redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" PING | grep -q PONG; then
        print_success "PING test: PASSED"
    else
        print_error "PING test: FAILED"
        return 1
    fi
    
    # Test SET/GET operations
    TEST_KEY="lucid:healthcheck:$(date +%s)"
    TEST_VALUE="health_check_passed"
    
    if redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" SET "${TEST_KEY}" "${TEST_VALUE}" EX 10 | grep -q OK; then
        print_success "SET operation: PASSED"
    else
        print_error "SET operation: FAILED"
        return 1
    fi
    
    RETRIEVED_VALUE=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" GET "${TEST_KEY}")
    if [ "${RETRIEVED_VALUE}" = "${TEST_VALUE}" ]; then
        print_success "GET operation: PASSED"
    else
        print_error "GET operation: FAILED"
        return 1
    fi
    
    # Clean up test key
    redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" DEL "${TEST_KEY}" &>/dev/null
    
    # Check info stats
    redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" INFO stats > /tmp/redis_info.txt
    print_success "Redis INFO saved to /tmp/redis_info.txt"
    
    print_success "All health checks passed"
    return 0
}

# Main execution
main() {
    echo ""
    print_info "Starting Redis initialization..."
    echo ""
    
    # Step 1: Check/Install Redis
    if ! check_redis_installed; then
        install_redis
    fi
    
    # Step 2: Create data directory
    create_data_directory
    
    # Step 3: Setup configuration
    setup_configuration
    
    # Step 4: Apply performance tuning
    performance_tuning
    
    # Step 5: Start Redis
    start_redis
    
    # Step 6: Wait for Redis
    wait_for_redis || exit 1
    
    # Step 7: Configure Lucid settings
    configure_lucid_settings
    
    # Step 8: Setup keyspace patterns
    setup_keyspace_patterns
    
    # Step 9: Verify configuration
    verify_configuration
    
    # Step 10: Health check
    health_check || exit 1
    
    echo ""
    echo "========================================="
    print_success "Redis initialization complete!"
    echo "========================================="
    echo ""
    print_info "Redis is running on ${REDIS_HOST}:${REDIS_PORT}"
    print_info "Data directory: ${REDIS_DATA_DIR}"
    print_info "Configuration: ${REDIS_CONF}"
    echo ""
    print_info "Next steps:"
    print_info "  1. Verify connection: redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} ping"
    print_info "  2. Monitor logs: tail -f /var/log/redis/redis.log"
    print_info "  3. Check metrics: redis-cli info"
    echo ""
}

# Run main function
main "$@"

