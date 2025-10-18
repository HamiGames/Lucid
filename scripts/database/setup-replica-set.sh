#!/bin/bash
# scripts/database/setup-replica-set.sh
# Setup MongoDB replica set for high availability
# LUCID-STRICT: Distroless build method, API compliant

set -Eeuo pipefail

# Script metadata
SCRIPT_NAME="$(basename "$0")"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_PATH/../../.." && pwd)"

# Configuration
REPLICA_SET_NAME="${REPLICA_SET_NAME:-rs0}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_ADMIN_USER="${MONGO_ADMIN_USER:-admin}"
MONGO_ADMIN_PASSWORD="${MONGO_ADMIN_PASSWORD:-admin123}"
MONGO_DB_NAME="${MONGO_DB_NAME:-lucid}"

# Replica set members
REPLICA_MEMBERS=(
    "mongo-1:27017"
    "mongo-2:27017"
    "mongo-3:27017"
)

# Logging
log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*"; }
die() { printf '[%s][ERROR] %s\n' "$SCRIPT_NAME" "$*" >&2; exit 1; }
warn() { printf '[%s][WARN] %s\n' "$SCRIPT_NAME" "$*" >&2; }

# Check MongoDB connectivity
check_mongodb_connectivity() {
    log "Checking MongoDB connectivity..."
    
    for member in "${REPLICA_MEMBERS[@]}"; do
        local host port
        IFS=':' read -r host port <<< "$member"
        
        log "Checking connectivity to $host:$port..."
        
        if ! mongosh --host "$host" --port "$port" --eval "db.runCommand('ping')" --quiet >/dev/null 2>&1; then
            warn "Cannot connect to MongoDB at $host:$port"
            return 1
        fi
        
        log "✅ Connected to $host:$port"
    done
    
    log "All MongoDB instances are accessible"
    return 0
}

# Initialize replica set configuration
init_replica_set_config() {
    log "Initializing replica set configuration..."
    
    local config_file="$PROJECT_ROOT/configs/mongodb/replica-set-config.js"
    local config_dir="$(dirname "$config_file")"
    
    # Create config directory
    mkdir -p "$config_dir"
    
    # Generate replica set configuration
    cat > "$config_file" << EOF
// MongoDB Replica Set Configuration for Lucid RDP
// LUCID-STRICT: High availability configuration

var config = {
    _id: "$REPLICA_SET_NAME",
    members: [
EOF
    
    local member_id=0
    for member in "${REPLICA_MEMBERS[@]}"; do
        local host port
        IFS=':' read -r host port <<< "$member"
        
        cat >> "$config_file" << EOF
        {
            _id: $member_id,
            host: "$host:$port",
            priority: $([ $member_id -eq 0 ] && echo "2" || echo "1")
        }$([ $member_id -lt $((${#REPLICA_MEMBERS[@]} - 1)) ] && echo "," || echo "")
EOF
        ((member_id++))
    done
    
    cat >> "$config_file" << EOF
    ],
    settings: {
        heartbeatTimeoutSecs: 10,
        electionTimeoutMillis: 10000,
        catchUpTimeoutMillis: 2000,
        catchUpTakeoverDelayMillis: 30000
    }
};

// Initialize replica set
rs.initiate(config);

// Wait for replica set to be ready
rs.status();
EOF
    
    log "Replica set configuration created: $config_file"
}

# Setup replica set authentication
setup_replica_set_auth() {
    log "Setting up replica set authentication..."
    
    local auth_file="$PROJECT_ROOT/configs/mongodb/replica-set-auth.js"
    
    cat > "$auth_file" << EOF
// MongoDB Replica Set Authentication Setup
// LUCID-STRICT: Secure authentication configuration

// Switch to admin database
db = db.getSiblingDB('admin');

// Create admin user
db.createUser({
    user: "$MONGO_ADMIN_USER",
    pwd: "$MONGO_ADMIN_PASSWORD",
    roles: [
        { role: "userAdminAnyDatabase", db: "admin" },
        { role: "readWriteAnyDatabase", db: "admin" },
        { role: "dbAdminAnyDatabase", db: "admin" },
        { role: "clusterAdmin", db: "admin" }
    ]
});

// Create application user for Lucid database
db = db.getSiblingDB('$MONGO_DB_NAME');

db.createUser({
    user: "lucid",
    pwd: "lucid123",
    roles: [
        { role: "readWrite", db: "$MONGO_DB_NAME" },
        { role: "dbAdmin", db: "$MONGO_DB_NAME" }
    ]
});

// Enable authentication
db.adminCommand({setParameter: 1, authenticationMechanisms: ["SCRAM-SHA-1", "SCRAM-SHA-256"]});

print("Authentication setup completed");
EOF
    
    log "Authentication configuration created: $auth_file"
}

# Initialize replica set
init_replica_set() {
    log "Initializing MongoDB replica set..."
    
    local primary_member="${REPLICA_MEMBERS[0]}"
    local host port
    IFS=':' read -r host port <<< "$primary_member"
    
    log "Connecting to primary member: $primary_member"
    
    # Initialize replica set
    if mongosh --host "$host" --port "$port" --file "$PROJECT_ROOT/configs/mongodb/replica-set-config.js"; then
        log "✅ Replica set initialized successfully"
    else
        die "Failed to initialize replica set"
    fi
    
    # Wait for replica set to be ready
    log "Waiting for replica set to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if mongosh --host "$host" --port "$port" --eval "rs.status().ok" --quiet 2>/dev/null | grep -q "1"; then
            log "✅ Replica set is ready"
            break
        fi
        
        log "Waiting for replica set... (attempt $attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        die "Replica set initialization timeout"
    fi
}

# Setup authentication
setup_authentication() {
    log "Setting up replica set authentication..."
    
    local primary_member="${REPLICA_MEMBERS[0]}"
    local host port
    IFS=':' read -r host port <<< "$primary_member"
    
    # Setup authentication
    if mongosh --host "$host" --port "$port" --file "$PROJECT_ROOT/configs/mongodb/replica-set-auth.js"; then
        log "✅ Authentication setup completed"
    else
        warn "Authentication setup failed - continuing without auth"
    fi
}

# Configure replica set settings
configure_replica_set() {
    log "Configuring replica set settings..."
    
    local primary_member="${REPLICA_MEMBERS[0]}"
    local host port
    IFS=':' read -r host port <<< "$primary_member"
    
    # Configure replica set settings
    cat > "$PROJECT_ROOT/configs/mongodb/replica-set-settings.js" << EOF
// MongoDB Replica Set Configuration Settings
// LUCID-STRICT: Optimized settings for Lucid RDP

// Switch to admin database
db = db.getSiblingDB('admin');

// Configure replica set settings
var config = rs.conf();
config.settings = {
    heartbeatTimeoutSecs: 10,
    electionTimeoutMillis: 10000,
    catchUpTimeoutMillis: 2000,
    catchUpTakeoverDelayMillis: 30000
};

// Update replica set configuration
rs.reconfig(config);

// Configure oplog size (1GB)
db.adminCommand({replSetResizeOplog: 1, size: 1024});

// Configure write concern
db.adminCommand({
    setDefaultRWConcern: {
        defaultReadConcern: { level: "majority" },
        defaultWriteConcern: { w: "majority", j: true }
    }
});

print("Replica set configuration updated");
EOF
    
    if mongosh --host "$host" --port "$port" --file "$PROJECT_ROOT/configs/mongodb/replica-set-settings.js"; then
        log "✅ Replica set configuration updated"
    else
        warn "Failed to update replica set configuration"
    fi
}

# Verify replica set status
verify_replica_set() {
    log "Verifying replica set status..."
    
    local primary_member="${REPLICA_MEMBERS[0]}"
    local host port
    IFS=':' read -r host port <<< "$primary_member"
    
    # Get replica set status
    local status
    status=$(mongosh --host "$host" --port "$port" --eval "rs.status()" --quiet)
    
    if [[ $? -eq 0 ]]; then
        log "✅ Replica set status verified"
        
        # Display replica set information
        echo "$status" | jq -r '.members[] | "\(.name): \(.stateStr) (Priority: \(.priority))"' 2>/dev/null || echo "$status"
    else
        warn "Failed to verify replica set status"
    fi
}

# Create replica set monitoring script
create_monitoring_script() {
    log "Creating replica set monitoring script..."
    
    local monitor_script="$PROJECT_ROOT/scripts/database/monitor-replica-set.sh"
    
    cat > "$monitor_script" << 'EOF'
#!/bin/bash
# MongoDB Replica Set Monitoring Script
# LUCID-STRICT: Continuous monitoring for high availability

set -Eeuo pipefail

SCRIPT_NAME="$(basename "$0")"
REPLICA_SET_NAME="${REPLICA_SET_NAME:-rs0}"
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"

log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*"; }
warn() { printf '[%s][WARN] %s\n' "$SCRIPT_NAME" "$*" >&2; }

# Check replica set health
check_replica_set_health() {
    local status
    status=$(mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" --eval "rs.status()" --quiet 2>/dev/null)
    
    if [[ $? -eq 0 ]]; then
        # Check if replica set is healthy
        local healthy_members
        healthy_members=$(echo "$status" | jq -r '.members[] | select(.health == 1) | .name' 2>/dev/null | wc -l)
        
        if [[ "$healthy_members" -ge 2 ]]; then
            log "✅ Replica set healthy ($healthy_members members)"
            return 0
        else
            warn "⚠️ Replica set unhealthy ($healthy_members healthy members)"
            return 1
        fi
    else
        warn "Failed to get replica set status"
        return 1
    fi
}

# Check primary member
check_primary_member() {
    local primary
    primary=$(mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" --eval "rs.isMaster().primary" --quiet 2>/dev/null)
    
    if [[ -n "$primary" ]] && [[ "$primary" != "null" ]]; then
        log "✅ Primary member: $primary"
        return 0
    else
        warn "⚠️ No primary member found"
        return 1
    fi
}

# Main monitoring function
main() {
    log "Monitoring replica set: $REPLICA_SET_NAME"
    
    if check_replica_set_health && check_primary_member; then
        log "Replica set monitoring: HEALTHY"
        exit 0
    else
        log "Replica set monitoring: UNHEALTHY"
        exit 1
    fi
}

main "$@"
EOF
    
    chmod +x "$monitor_script"
    log "Monitoring script created: $monitor_script"
}

# Create Docker Compose configuration for replica set
create_docker_compose_config() {
    log "Creating Docker Compose configuration for replica set..."
    
    local compose_file="$PROJECT_ROOT/infrastructure/compose/docker-compose.replica-set.yml"
    local compose_dir="$(dirname "$compose_file")"
    
    mkdir -p "$compose_dir"
    
    cat > "$compose_file" << EOF
# MongoDB Replica Set Docker Compose Configuration
# LUCID-STRICT: Distroless MongoDB configuration

version: '3.8'

networks:
  mongo-replica-net:
    driver: bridge

volumes:
  mongo-1-data:
    driver: local
  mongo-2-data:
    driver: local
  mongo-3-data:
    driver: local

services:
  mongo-1:
    image: mongo:7.0
    container_name: lucid-mongo-1
    hostname: mongo-1
    
    command: ["mongod", "--replSet", "$REPLICA_SET_NAME", "--bind_ip_all", "--port", "$MONGO_PORT"]
    
    environment:
      - MONGO_INITDB_ROOT_USERNAME=$MONGO_ADMIN_USER
      - MONGO_INITDB_ROOT_PASSWORD=$MONGO_ADMIN_PASSWORD
      - MONGO_INITDB_DATABASE=$MONGO_DB_NAME
    
    volumes:
      - mongo-1-data:/data/db
      - ./configs/mongodb:/etc/mongodb:ro
    
    ports:
      - "27017:$MONGO_PORT"
    
    networks:
      - mongo-replica-net
    
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.runCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  mongo-2:
    image: mongo:7.0
    container_name: lucid-mongo-2
    hostname: mongo-2
    
    command: ["mongod", "--replSet", "$REPLICA_SET_NAME", "--bind_ip_all", "--port", "$MONGO_PORT"]
    
    environment:
      - MONGO_INITDB_ROOT_USERNAME=$MONGO_ADMIN_USER
      - MONGO_INITDB_ROOT_PASSWORD=$MONGO_ADMIN_PASSWORD
      - MONGO_INITDB_DATABASE=$MONGO_DB_NAME
    
    volumes:
      - mongo-2-data:/data/db
      - ./configs/mongodb:/etc/mongodb:ro
    
    ports:
      - "27018:$MONGO_PORT"
    
    networks:
      - mongo-replica-net
    
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.runCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  mongo-3:
    image: mongo:7.0
    container_name: lucid-mongo-3
    hostname: mongo-3
    
    command: ["mongod", "--replSet", "$REPLICA_SET_NAME", "--bind_ip_all", "--port", "$MONGO_PORT"]
    
    environment:
      - MONGO_INITDB_ROOT_USERNAME=$MONGO_ADMIN_USER
      - MONGO_INITDB_ROOT_PASSWORD=$MONGO_ADMIN_PASSWORD
      - MONGO_INITDB_DATABASE=$MONGO_DB_NAME
    
    volumes:
      - mongo-3-data:/data/db
      - ./configs/mongodb:/etc/mongodb:ro
    
    ports:
      - "27019:$MONGO_PORT"
    
    networks:
      - mongo-replica-net
    
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.runCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
EOF
    
    log "Docker Compose configuration created: $compose_file"
}

# Create startup script
create_startup_script() {
    log "Creating replica set startup script..."
    
    local startup_script="$PROJECT_ROOT/scripts/database/start-replica-set.sh"
    
    cat > "$startup_script" << 'EOF'
#!/bin/bash
# MongoDB Replica Set Startup Script
# LUCID-STRICT: Automated replica set startup

set -Eeuo pipefail

SCRIPT_NAME="$(basename "$0")"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*"; }
die() { printf '[%s][ERROR] %s\n' "$SCRIPT_NAME" "$*" >&2; exit 1; }

# Start replica set
start_replica_set() {
    log "Starting MongoDB replica set..."
    
    cd "$PROJECT_ROOT"
    
    # Start Docker Compose services
    docker-compose -f infrastructure/compose/docker-compose.replica-set.yml up -d
    
    # Wait for services to be ready
    log "Waiting for MongoDB instances to be ready..."
    sleep 30
    
    # Initialize replica set
    if [[ -f "configs/mongodb/replica-set-config.js" ]]; then
        log "Initializing replica set..."
        mongosh --host mongo-1 --port 27017 --file configs/mongodb/replica-set-config.js
    fi
    
    log "✅ Replica set started successfully"
}

# Stop replica set
stop_replica_set() {
    log "Stopping MongoDB replica set..."
    
    cd "$PROJECT_ROOT"
    docker-compose -f infrastructure/compose/docker-compose.replica-set.yml down
    
    log "✅ Replica set stopped"
}

# Main function
main() {
    case "${1:-start}" in
        start)
            start_replica_set
            ;;
        stop)
            stop_replica_set
            ;;
        *)
            echo "Usage: $0 {start|stop}"
            exit 1
            ;;
    esac
}

main "$@"
EOF
    
    chmod +x "$startup_script"
    log "Startup script created: $startup_script"
}

# Main execution
main() {
    log "Setting up MongoDB replica set..."
    log "Replica set name: $REPLICA_SET_NAME"
    log "Members: ${REPLICA_MEMBERS[*]}"
    
    # Check connectivity
    if ! check_mongodb_connectivity; then
        die "Cannot connect to all MongoDB instances"
    fi
    
    # Initialize configuration
    init_replica_set_config
    setup_replica_set_auth
    
    # Initialize replica set
    init_replica_set
    setup_authentication
    configure_replica_set
    
    # Verify setup
    verify_replica_set
    
    # Create additional scripts
    create_monitoring_script
    create_docker_compose_config
    create_startup_script
    
    log "✅ MongoDB replica set setup completed successfully"
    log "Configuration files created in: $PROJECT_ROOT/configs/mongodb/"
    log "Start replica set with: $PROJECT_ROOT/scripts/database/start-replica-set.sh"
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
