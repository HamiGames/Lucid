#!/bin/bash
# scripts/database/configure-sharding.sh
# Configure MongoDB sharding for scalability
# LUCID-STRICT: Distroless build method, API compliant

set -Eeuo pipefail

# Script metadata
SCRIPT_NAME="$(basename "$0")"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_PATH/../../.." && pwd)"

# Configuration
SHARD_CLUSTER_NAME="${SHARD_CLUSTER_NAME:-lucid-shard-cluster}"
CONFIG_SERVER_PORT="${CONFIG_SERVER_PORT:-27019}"
MONGOS_PORT="${MONGOS_PORT:-27017}"
SHARD_PORT="${SHARD_PORT:-27018}"

# Shard configuration
SHARDS=(
    "shard-1:27018"
    "shard-2:27018"
    "shard-3:27018"
)

# Config servers
CONFIG_SERVERS=(
    "config-1:27019"
    "config-2:27019"
    "config-3:27019"
)

# Collections to shard
SHARDED_COLLECTIONS=(
    "sessions"
    "chunks"
    "task_proofs"
    "work_tally"
    "payouts"
)

# Logging
log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*"; }
die() { printf '[%s][ERROR] %s\n' "$SCRIPT_NAME" "$*" >&2; exit 1; }
warn() { printf '[%s][WARN] %s\n' "$SCRIPT_NAME" "$*" >&2; }

# Check MongoDB connectivity
check_mongodb_connectivity() {
    log "Checking MongoDB connectivity..."
    
    # Check config servers
    for config in "${CONFIG_SERVERS[@]}"; do
        local host port
        IFS=':' read -r host port <<< "$config"
        
        log "Checking config server: $host:$port..."
        if ! mongosh --host "$host" --port "$port" --eval "db.runCommand('ping')" --quiet >/dev/null 2>&1; then
            warn "Cannot connect to config server: $host:$port"
            return 1
        fi
    done
    
    # Check shards
    for shard in "${SHARDS[@]}"; do
        local host port
        IFS=':' read -r host port <<< "$shard"
        
        log "Checking shard: $host:$port..."
        if ! mongosh --host "$host" --port "$port" --eval "db.runCommand('ping')" --quiet >/dev/null 2>&1; then
            warn "Cannot connect to shard: $host:$port"
            return 1
        fi
    done
    
    # Check mongos
    if ! mongosh --host "localhost" --port "$MONGOS_PORT" --eval "db.runCommand('ping')" --quiet >/dev/null 2>&1; then
        warn "Cannot connect to mongos: localhost:$MONGOS_PORT"
        return 1
    fi
    
    log "All MongoDB instances are accessible"
    return 0
}

# Initialize config servers
init_config_servers() {
    log "Initializing config servers..."
    
    local config_file="$PROJECT_ROOT/configs/mongodb/config-server-init.js"
    local config_dir="$(dirname "$config_file")"
    
    mkdir -p "$config_dir"
    
    # Generate config server initialization script
    cat > "$config_file" << EOF
// MongoDB Config Server Initialization
// LUCID-STRICT: Config server setup for sharding

// Initialize config servers as replica set
rs.initiate({
    _id: "configReplSet",
    configsvr: true,
    members: [
EOF
    
    local member_id=0
    for config in "${CONFIG_SERVERS[@]}"; do
        local host port
        IFS=':' read -r host port <<< "$config"
        
        cat >> "$config_file" << EOF
        {
            _id: $member_id,
            host: "$host:$port"
        }$([ $member_id -lt $((${#CONFIG_SERVERS[@]} - 1)) ] && echo "," || echo "")
EOF
        ((member_id++))
    done
    
    cat >> "$config_file" << EOF
    ]
});

print("Config servers initialized");
EOF
    
    # Execute config server initialization
    local primary_config="${CONFIG_SERVERS[0]}"
    local host port
    IFS=':' read -r host port <<< "$primary_config"
    
    if mongosh --host "$host" --port "$port" --file "$config_file"; then
        log "✅ Config servers initialized successfully"
    else
        die "Failed to initialize config servers"
    fi
}

# Configure sharding
configure_sharding() {
    log "Configuring MongoDB sharding..."
    
    local sharding_config="$PROJECT_ROOT/configs/mongodb/sharding-config.js"
    
    cat > "$sharding_config" << EOF
// MongoDB Sharding Configuration
// LUCID-STRICT: Sharding setup for Lucid RDP scalability

// Connect to mongos
db = db.getSiblingDB('admin');

// Add shards to cluster
EOF
    
    # Add each shard
    for shard in "${SHARDS[@]}"; do
        local host port
        IFS=':' read -r host port <<< "$shard"
        
        cat >> "$sharding_config" << EOF
sh.addShard("$host:$port");
EOF
    done
    
    cat >> "$sharding_config" << EOF

// Enable sharding for lucid database
sh.enableSharding("lucid");

print("Sharding configuration completed");
EOF
    
    # Execute sharding configuration
    if mongosh --host "localhost" --port "$MONGOS_PORT" --file "$sharding_config"; then
        log "✅ Sharding configured successfully"
    else
        die "Failed to configure sharding"
    fi
}

# Configure collection sharding
configure_collection_sharding() {
    log "Configuring collection sharding..."
    
    local collection_config="$PROJECT_ROOT/configs/mongodb/collection-sharding.js"
    
    cat > "$collection_config" << EOF
// MongoDB Collection Sharding Configuration
// LUCID-STRICT: Optimized sharding for Lucid RDP collections

// Switch to lucid database
db = db.getSiblingDB('lucid');

EOF
    
    # Configure sharding for each collection
    for collection in "${SHARDED_COLLECTIONS[@]}"; do
        case "$collection" in
            "sessions")
                cat >> "$collection_config" << EOF
// Shard sessions collection by owner_addr
sh.shardCollection("lucid.sessions", {"owner_addr": 1});
print("Sessions collection sharded by owner_addr");

EOF
                ;;
            "chunks")
                cat >> "$collection_config" << EOF
// Shard chunks collection by session_id
sh.shardCollection("lucid.chunks", {"session_id": 1});
print("Chunks collection sharded by session_id");

EOF
                ;;
            "task_proofs")
                cat >> "$collection_config" << EOF
// Shard task_proofs collection by slot and node_id
sh.shardCollection("lucid.task_proofs", {"slot": 1, "node_id": 1});
print("Task_proofs collection sharded by slot and node_id");

EOF
                ;;
            "work_tally")
                cat >> "$collection_config" << EOF
// Shard work_tally collection by epoch and entity_id
sh.shardCollection("lucid.work_tally", {"epoch": 1, "entity_id": 1});
print("Work_tally collection sharded by epoch and entity_id");

EOF
                ;;
            "payouts")
                cat >> "$collection_config" << EOF
// Shard payouts collection by recipient and timestamp
sh.shardCollection("lucid.payouts", {"recipient": 1, "timestamp": 1});
print("Payouts collection sharded by recipient and timestamp");

EOF
                ;;
        esac
    done
    
    # Execute collection sharding configuration
    if mongosh --host "localhost" --port "$MONGOS_PORT" --file "$collection_config"; then
        log "✅ Collection sharding configured successfully"
    else
        die "Failed to configure collection sharding"
    fi
}

# Create sharding indexes
create_sharding_indexes() {
    log "Creating sharding indexes..."
    
    local index_config="$PROJECT_ROOT/configs/mongodb/sharding-indexes.js"
    
    cat > "$index_config" << EOF
// MongoDB Sharding Indexes
// LUCID-STRICT: Optimized indexes for sharded collections

// Switch to lucid database
db = db.getSiblingDB('lucid');

// Create indexes for sessions collection
db.sessions.createIndex({"owner_addr": 1});
db.sessions.createIndex({"started_at": 1});
db.sessions.createIndex({"status": 1});
db.sessions.createIndex({"merkle_root": 1});

// Create indexes for chunks collection
db.chunks.createIndex({"session_id": 1});
db.chunks.createIndex({"chunk_index": 1});
db.chunks.createIndex({"created_at": 1});

// Create indexes for task_proofs collection
db.task_proofs.createIndex({"slot": 1, "node_id": 1});
db.task_proofs.createIndex({"proof_type": 1});
db.task_proofs.createIndex({"timestamp": 1});

// Create indexes for work_tally collection
db.work_tally.createIndex({"epoch": 1, "entity_id": 1});
db.work_tally.createIndex({"credits": -1});
db.work_tally.createIndex({"rank": 1});

// Create indexes for payouts collection
db.payouts.createIndex({"recipient": 1, "timestamp": 1});
db.payouts.createIndex({"status": 1});
db.payouts.createIndex({"amount": -1});

print("Sharding indexes created");
EOF
    
    # Execute index creation
    if mongosh --host "localhost" --port "$MONGOS_PORT" --file "$index_config"; then
        log "✅ Sharding indexes created successfully"
    else
        die "Failed to create sharding indexes"
    fi
}

# Verify sharding configuration
verify_sharding() {
    log "Verifying sharding configuration..."
    
    local verification_script="$PROJECT_ROOT/configs/mongodb/verify-sharding.js"
    
    cat > "$verification_script" << EOF
// MongoDB Sharding Verification
// LUCID-STRICT: Verify sharding configuration

// Switch to admin database
db = db.getSiblingDB('admin');

// Check shard status
print("=== Shard Status ===");
sh.status();

// Check database sharding
print("\n=== Database Sharding ===");
db.databases.find().forEach(function(db) {
    print("Database: " + db._id + ", Sharded: " + db.sharded);
});

// Check collection sharding
print("\n=== Collection Sharding ===");
db.collections.find().forEach(function(coll) {
    if (coll.dropped == false) {
        print("Collection: " + coll._id + ", Sharded: " + (coll.sharded || false));
    }
});

print("\nSharding verification completed");
EOF
    
    # Execute verification
    if mongosh --host "localhost" --port "$MONGOS_PORT" --file "$verification_script"; then
        log "✅ Sharding verification completed"
    else
        warn "Sharding verification failed"
    fi
}

# Create sharding monitoring script
create_sharding_monitor() {
    log "Creating sharding monitoring script..."
    
    local monitor_script="$PROJECT_ROOT/scripts/database/monitor-sharding.sh"
    
    cat > "$monitor_script" << 'EOF'
#!/bin/bash
# MongoDB Sharding Monitoring Script
# LUCID-STRICT: Monitor sharding health and performance

set -Eeuo pipefail

SCRIPT_NAME="$(basename "$0")"
MONGOS_HOST="${MONGOS_HOST:-localhost}"
MONGOS_PORT="${MONGOS_PORT:-27017}"

log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*"; }
warn() { printf '[%s][WARN] %s\n' "$SCRIPT_NAME" "$*" >&2; }

# Check sharding health
check_sharding_health() {
    local status
    status=$(mongosh --host "$MONGOS_HOST" --port "$MONGOS_PORT" --eval "sh.status()" --quiet 2>/dev/null)
    
    if [[ $? -eq 0 ]]; then
        log "✅ Sharding cluster healthy"
        return 0
    else
        warn "⚠️ Sharding cluster unhealthy"
        return 1
    fi
}

# Check shard balance
check_shard_balance() {
    local balance
    balance=$(mongosh --host "$MONGOS_HOST" --port "$MONGOS_PORT" --eval "sh.getBalancerState()" --quiet 2>/dev/null)
    
    if [[ "$balance" == "true" ]]; then
        log "✅ Shard balancer enabled"
    else
        warn "⚠️ Shard balancer disabled"
    fi
}

# Check chunk distribution
check_chunk_distribution() {
    local chunks
    chunks=$(mongosh --host "$MONGOS_HOST" --port "$MONGOS_PORT" --eval "db.chunks.count()" --quiet 2>/dev/null)
    
    if [[ -n "$chunks" ]] && [[ "$chunks" -gt 0 ]]; then
        log "✅ Chunks distributed: $chunks"
    else
        warn "⚠️ No chunks found"
    fi
}

# Main monitoring function
main() {
    log "Monitoring MongoDB sharding..."
    
    if check_sharding_health && check_shard_balance && check_chunk_distribution; then
        log "Sharding monitoring: HEALTHY"
        exit 0
    else
        log "Sharding monitoring: UNHEALTHY"
        exit 1
    fi
}

main "$@"
EOF
    
    chmod +x "$monitor_script"
    log "Sharding monitoring script created: $monitor_script"
}

# Create Docker Compose configuration for sharding
create_sharding_docker_compose() {
    log "Creating Docker Compose configuration for sharding..."
    
    local compose_file="$PROJECT_ROOT/infrastructure/compose/docker-compose.sharding.yml"
    local compose_dir="$(dirname "$compose_file")"
    
    mkdir -p "$compose_dir"
    
    cat > "$compose_file" << EOF
# MongoDB Sharding Docker Compose Configuration
# LUCID-STRICT: Distroless MongoDB sharding configuration

version: '3.8'

networks:
  mongo-shard-net:
    driver: bridge

volumes:
  config-1-data:
    driver: local
  config-2-data:
    driver: local
  config-3-data:
    driver: local
  shard-1-data:
    driver: local
  shard-2-data:
    driver: local
  shard-3-data:
    driver: local

services:
  # Config servers
  config-1:
    image: mongo:7.0
    container_name: lucid-config-1
    hostname: config-1
    
    command: ["mongod", "--configsvr", "--replSet", "configReplSet", "--bind_ip_all", "--port", "$CONFIG_SERVER_PORT"]
    
    volumes:
      - config-1-data:/data/db
    
    ports:
      - "27019:$CONFIG_SERVER_PORT"
    
    networks:
      - mongo-shard-net
    
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.runCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3

  config-2:
    image: mongo:7.0
    container_name: lucid-config-2
    hostname: config-2
    
    command: ["mongod", "--configsvr", "--replSet", "configReplSet", "--bind_ip_all", "--port", "$CONFIG_SERVER_PORT"]
    
    volumes:
      - config-2-data:/data/db
    
    ports:
      - "27020:$CONFIG_SERVER_PORT"
    
    networks:
      - mongo-shard-net
    
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.runCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3

  config-3:
    image: mongo:7.0
    container_name: lucid-config-3
    hostname: config-3
    
    command: ["mongod", "--configsvr", "--replSet", "configReplSet", "--bind_ip_all", "--port", "$CONFIG_SERVER_PORT"]
    
    volumes:
      - config-3-data:/data/db
    
    ports:
      - "27021:$CONFIG_SERVER_PORT"
    
    networks:
      - mongo-shard-net
    
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.runCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Shards
  shard-1:
    image: mongo:7.0
    container_name: lucid-shard-1
    hostname: shard-1
    
    command: ["mongod", "--shardsvr", "--bind_ip_all", "--port", "$SHARD_PORT"]
    
    volumes:
      - shard-1-data:/data/db
    
    ports:
      - "27022:$SHARD_PORT"
    
    networks:
      - mongo-shard-net
    
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.runCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3

  shard-2:
    image: mongo:7.0
    container_name: lucid-shard-2
    hostname: shard-2
    
    command: ["mongod", "--shardsvr", "--bind_ip_all", "--port", "$SHARD_PORT"]
    
    volumes:
      - shard-2-data:/data/db
    
    ports:
      - "27023:$SHARD_PORT"
    
    networks:
      - mongo-shard-net
    
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.runCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3

  shard-3:
    image: mongo:7.0
    container_name: lucid-shard-3
    hostname: shard-3
    
    command: ["mongod", "--shardsvr", "--bind_ip_all", "--port", "$SHARD_PORT"]
    
    volumes:
      - shard-3-data:/data/db
    
    ports:
      - "27024:$SHARD_PORT"
    
    networks:
      - mongo-shard-net
    
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.runCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Mongos router
  mongos:
    image: mongo:7.0
    container_name: lucid-mongos
    hostname: mongos
    
    command: ["mongos", "--configdb", "configReplSet/config-1:27019,config-2:27019,config-3:27019", "--bind_ip_all", "--port", "$MONGOS_PORT"]
    
    ports:
      - "27017:$MONGOS_PORT"
    
    networks:
      - mongo-shard-net
    
    depends_on:
      - config-1
      - config-2
      - config-3
      - shard-1
      - shard-2
      - shard-3
    
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.runCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3
EOF
    
    log "Sharding Docker Compose configuration created: $compose_file"
}

# Create sharding startup script
create_sharding_startup() {
    log "Creating sharding startup script..."
    
    local startup_script="$PROJECT_ROOT/scripts/database/start-sharding.sh"
    
    cat > "$startup_script" << 'EOF'
#!/bin/bash
# MongoDB Sharding Startup Script
# LUCID-STRICT: Automated sharding startup

set -Eeuo pipefail

SCRIPT_NAME="$(basename "$0")"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*"; }
die() { printf '[%s][ERROR] %s\n' "$SCRIPT_NAME" "$*" >&2; exit 1; }

# Start sharding cluster
start_sharding() {
    log "Starting MongoDB sharding cluster..."
    
    cd "$PROJECT_ROOT"
    
    # Start Docker Compose services
    docker-compose -f infrastructure/compose/docker-compose.sharding.yml up -d
    
    # Wait for services to be ready
    log "Waiting for MongoDB instances to be ready..."
    sleep 60
    
    # Initialize config servers
    if [[ -f "configs/mongodb/config-server-init.js" ]]; then
        log "Initializing config servers..."
        mongosh --host config-1 --port 27019 --file configs/mongodb/config-server-init.js
    fi
    
    # Configure sharding
    if [[ -f "configs/mongodb/sharding-config.js" ]]; then
        log "Configuring sharding..."
        mongosh --host localhost --port 27017 --file configs/mongodb/sharding-config.js
    fi
    
    log "✅ Sharding cluster started successfully"
}

# Stop sharding cluster
stop_sharding() {
    log "Stopping MongoDB sharding cluster..."
    
    cd "$PROJECT_ROOT"
    docker-compose -f infrastructure/compose/docker-compose.sharding.yml down
    
    log "✅ Sharding cluster stopped"
}

# Main function
main() {
    case "${1:-start}" in
        start)
            start_sharding
            ;;
        stop)
            stop_sharding
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
    log "Sharding startup script created: $startup_script"
}

# Main execution
main() {
    log "Configuring MongoDB sharding..."
    log "Shard cluster name: $SHARD_CLUSTER_NAME"
    log "Config servers: ${CONFIG_SERVERS[*]}"
    log "Shards: ${SHARDS[*]}"
    
    # Check connectivity
    if ! check_mongodb_connectivity; then
        die "Cannot connect to all MongoDB instances"
    fi
    
    # Initialize config servers
    init_config_servers
    
    # Configure sharding
    configure_sharding
    configure_collection_sharding
    create_sharding_indexes
    
    # Verify configuration
    verify_sharding
    
    # Create additional scripts
    create_sharding_monitor
    create_sharding_docker_compose
    create_sharding_startup
    
    log "✅ MongoDB sharding configuration completed successfully"
    log "Configuration files created in: $PROJECT_ROOT/configs/mongodb/"
    log "Start sharding cluster with: $PROJECT_ROOT/scripts/database/start-sharding.sh"
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
