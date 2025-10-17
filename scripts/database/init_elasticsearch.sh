#!/bin/bash
# Elasticsearch Initialization Script
# Database Cluster 08: Storage Database
# Step 3: Redis & Elasticsearch Setup

set -e

echo "========================================="
echo "Elasticsearch 8.11.0 Initialization Script"
echo "Lucid Blockchain System"
echo "========================================="

# Configuration
ES_VERSION="8.11.0"
ES_CONFIG="${ES_CONFIG:-/etc/elasticsearch/elasticsearch.yml}"
ES_DATA_DIR="${ES_DATA_DIR:-/usr/share/elasticsearch/data}"
ES_LOG_DIR="${ES_LOG_DIR:-/usr/share/elasticsearch/logs}"
ES_HOST="${ES_HOST:-localhost}"
ES_PORT="${ES_PORT:-9200}"
ES_CLUSTER_NAME="${ES_CLUSTER_NAME:-lucid-elasticsearch}"

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

# Check if Elasticsearch is installed
check_elasticsearch_installed() {
    print_info "Checking Elasticsearch installation..."
    if command -v elasticsearch &> /dev/null; then
        # Try to get version
        ES_INSTALLED_VERSION=$(elasticsearch --version 2>/dev/null | grep -oP 'Version: \K[0-9.]+' || echo "unknown")
        print_success "Elasticsearch found: version ${ES_INSTALLED_VERSION}"
        return 0
    else
        print_error "Elasticsearch not found"
        return 1
    fi
}

# Install Elasticsearch if not present
install_elasticsearch() {
    print_info "Installing Elasticsearch ${ES_VERSION}..."
    
    if [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | apt-key add -
        echo "deb https://artifacts.elastic.co/packages/8.x/apt stable main" > /etc/apt/sources.list.d/elastic-8.x.list
        apt-get update
        apt-get install -y elasticsearch
    elif [ -f /etc/redhat-release ]; then
        # RHEL/CentOS
        rpm --import https://artifacts.elastic.co/GPG-KEY-elasticsearch
        cat > /etc/yum.repos.d/elasticsearch.repo << EOF
[elasticsearch]
name=Elasticsearch repository for 8.x packages
baseurl=https://artifacts.elastic.co/packages/8.x/yum
gpgcheck=1
gpgkey=https://artifacts.elastic.co/GPG-KEY-elasticsearch
enabled=1
autorefresh=1
type=rpm-md
EOF
        yum install -y elasticsearch
    else
        print_error "Unsupported OS"
        exit 1
    fi
    
    print_success "Elasticsearch installed"
}

# Create Elasticsearch directories
create_data_directories() {
    print_info "Creating Elasticsearch directories..."
    
    mkdir -p "${ES_DATA_DIR}"
    mkdir -p "${ES_LOG_DIR}"
    mkdir -p "$(dirname ${ES_CONFIG})"
    
    chmod 755 "${ES_DATA_DIR}"
    chmod 755 "${ES_LOG_DIR}"
    
    # Set ownership to elasticsearch user if it exists
    if id elasticsearch &>/dev/null; then
        chown -R elasticsearch:elasticsearch "${ES_DATA_DIR}"
        chown -R elasticsearch:elasticsearch "${ES_LOG_DIR}"
    fi
    
    print_success "Directories created"
}

# Setup Elasticsearch configuration
setup_configuration() {
    print_info "Setting up Elasticsearch configuration..."
    
    # Check if custom config exists
    CUSTOM_CONF="configs/database/elasticsearch/elasticsearch.yml"
    if [ -f "${CUSTOM_CONF}" ]; then
        print_info "Using custom configuration from ${CUSTOM_CONF}"
        cp "${CUSTOM_CONF}" "${ES_CONFIG}"
    else
        print_warning "Custom config not found, creating minimal config"
        create_minimal_config
    fi
    
    # Update paths in configuration
    sed -i "s|path.data: .*|path.data: ${ES_DATA_DIR}|" "${ES_CONFIG}"
    sed -i "s|path.logs: .*|path.logs: ${ES_LOG_DIR}|" "${ES_CONFIG}"
    
    print_success "Configuration updated"
}

# Create minimal configuration if custom config not found
create_minimal_config() {
    cat > "${ES_CONFIG}" << EOF
cluster.name: ${ES_CLUSTER_NAME}
node.name: lucid-es-node-1
path.data: ${ES_DATA_DIR}
path.logs: ${ES_LOG_DIR}
network.host: 0.0.0.0
http.port: ${ES_PORT}
discovery.type: single-node
xpack.security.enabled: false
EOF
}

# System tuning for Elasticsearch
system_tuning() {
    print_info "Applying system tuning for Elasticsearch..."
    
    # Increase max file descriptors
    if [ -f /etc/security/limits.conf ]; then
        echo "elasticsearch soft nofile 65536" >> /etc/security/limits.conf
        echo "elasticsearch hard nofile 65536" >> /etc/security/limits.conf
        print_success "File descriptor limit increased"
    fi
    
    # Set vm.max_map_count
    sysctl -w vm.max_map_count=262144 || print_warning "Could not set vm.max_map_count"
    echo "vm.max_map_count=262144" >> /etc/sysctl.conf
    
    # Disable swap
    swapoff -a || print_warning "Could not disable swap"
    
    print_success "System tuning applied"
}

# Start Elasticsearch service
start_elasticsearch() {
    print_info "Starting Elasticsearch service..."
    
    # Check if running in Docker
    if [ -f /.dockerenv ]; then
        su elasticsearch -c "elasticsearch &"
        ES_PID=$!
        sleep 5
    else
        systemctl daemon-reload
        systemctl start elasticsearch
        systemctl enable elasticsearch
    fi
    
    print_success "Elasticsearch service started"
}

# Wait for Elasticsearch to be ready
wait_for_elasticsearch() {
    print_info "Waiting for Elasticsearch to be ready..."
    
    MAX_ATTEMPTS=60
    ATTEMPT=0
    
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        if curl -s "http://${ES_HOST}:${ES_PORT}/_cluster/health" &>/dev/null; then
            print_success "Elasticsearch is ready"
            return 0
        fi
        
        ATTEMPT=$((ATTEMPT+1))
        echo -n "."
        sleep 2
    done
    
    print_error "Elasticsearch failed to start"
    return 1
}

# Create Lucid indices
create_lucid_indices() {
    print_info "Creating Lucid indices..."
    
    # Index 1: Sessions
    print_info "Creating lucid_sessions index..."
    curl -X PUT "http://${ES_HOST}:${ES_PORT}/lucid_sessions" \
        -H 'Content-Type: application/json' \
        -d '{
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "refresh_interval": "5s"
            },
            "mappings": {
                "properties": {
                    "session_id": {"type": "keyword"},
                    "user_id": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "merkle_root": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "completed_at": {"type": "date"},
                    "metadata": {"type": "object"}
                }
            }
        }' \
        -s -o /dev/null -w "%{http_code}\n" | grep -q "200\|201" && print_success "lucid_sessions index created"
    
    # Index 2: Blocks
    print_info "Creating lucid_blocks index..."
    curl -X PUT "http://${ES_HOST}:${ES_PORT}/lucid_blocks" \
        -H 'Content-Type: application/json' \
        -d '{
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "refresh_interval": "10s"
            },
            "mappings": {
                "properties": {
                    "block_id": {"type": "keyword"},
                    "block_height": {"type": "long"},
                    "block_hash": {"type": "keyword"},
                    "previous_hash": {"type": "keyword"},
                    "merkle_root": {"type": "keyword"},
                    "timestamp": {"type": "date"},
                    "transactions": {"type": "nested"}
                }
            }
        }' \
        -s -o /dev/null -w "%{http_code}\n" | grep -q "200\|201" && print_success "lucid_blocks index created"
    
    # Index 3: Users
    print_info "Creating lucid_users index..."
    curl -X PUT "http://${ES_HOST}:${ES_PORT}/lucid_users" \
        -H 'Content-Type: application/json' \
        -d '{
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "refresh_interval": "30s"
            },
            "mappings": {
                "properties": {
                    "user_id": {"type": "keyword"},
                    "email": {
                        "type": "text",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "tron_address": {"type": "keyword"},
                    "roles": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "last_activity": {"type": "date"}
                }
            }
        }' \
        -s -o /dev/null -w "%{http_code}\n" | grep -q "200\|201" && print_success "lucid_users index created"
    
    print_success "All Lucid indices created"
}

# Verify indices
verify_indices() {
    print_info "Verifying indices..."
    
    # List all indices
    INDICES=$(curl -s "http://${ES_HOST}:${ES_PORT}/_cat/indices?v")
    echo "${INDICES}"
    
    # Check for Lucid indices
    for INDEX in lucid_sessions lucid_blocks lucid_users; do
        if echo "${INDICES}" | grep -q "${INDEX}"; then
            print_success "Index ${INDEX} verified"
        else
            print_error "Index ${INDEX} not found"
            return 1
        fi
    done
    
    return 0
}

# Setup index lifecycle management (optional)
setup_ilm_policies() {
    print_info "Setting up Index Lifecycle Management policies..."
    
    # Session index retention policy (90 days)
    curl -X PUT "http://${ES_HOST}:${ES_PORT}/_ilm/policy/lucid_sessions_policy" \
        -H 'Content-Type: application/json' \
        -d '{
            "policy": {
                "phases": {
                    "hot": {
                        "actions": {}
                    },
                    "delete": {
                        "min_age": "90d",
                        "actions": {
                            "delete": {}
                        }
                    }
                }
            }
        }' \
        -s -o /dev/null && print_success "Sessions ILM policy created"
    
    print_info "ILM policies configured"
}

# Run health check
health_check() {
    print_info "Running health check..."
    
    # Cluster health check
    CLUSTER_HEALTH=$(curl -s "http://${ES_HOST}:${ES_PORT}/_cluster/health")
    CLUSTER_STATUS=$(echo "${CLUSTER_HEALTH}" | grep -oP '"status":"\K[^"]+')
    
    if [ "${CLUSTER_STATUS}" = "green" ] || [ "${CLUSTER_STATUS}" = "yellow" ]; then
        print_success "Cluster health: ${CLUSTER_STATUS}"
    else
        print_error "Cluster health: ${CLUSTER_STATUS}"
        echo "${CLUSTER_HEALTH}"
        return 1
    fi
    
    # Test index operations
    TEST_DOC_ID="health_check_$(date +%s)"
    
    # Index a test document
    curl -X POST "http://${ES_HOST}:${ES_PORT}/lucid_sessions/_doc/${TEST_DOC_ID}" \
        -H 'Content-Type: application/json' \
        -d '{
            "session_id": "test_session",
            "user_id": "test_user",
            "status": "health_check",
            "created_at": "'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'"
        }' \
        -s -o /dev/null && print_success "Index test: PASSED"
    
    # Search test
    sleep 1  # Wait for refresh
    SEARCH_RESULT=$(curl -s "http://${ES_HOST}:${ES_PORT}/lucid_sessions/_search?q=session_id:test_session")
    if echo "${SEARCH_RESULT}" | grep -q "test_session"; then
        print_success "Search test: PASSED"
    else
        print_error "Search test: FAILED"
        return 1
    fi
    
    # Clean up test document
    curl -X DELETE "http://${ES_HOST}:${ES_PORT}/lucid_sessions/_doc/${TEST_DOC_ID}" \
        -s -o /dev/null
    
    # Get cluster stats
    curl -s "http://${ES_HOST}:${ES_PORT}/_cluster/stats" > /tmp/elasticsearch_stats.json
    print_success "Cluster stats saved to /tmp/elasticsearch_stats.json"
    
    print_success "All health checks passed"
    return 0
}

# Create README with usage examples
create_usage_guide() {
    cat > /tmp/elasticsearch_usage_guide.md << 'EOF'
# Elasticsearch Usage Guide for Lucid

## Available Indices

1. **lucid_sessions** - Session data
2. **lucid_blocks** - Blockchain blocks
3. **lucid_users** - User information

## Common Operations

### Search Sessions by User
```bash
curl -X GET "http://localhost:9200/lucid_sessions/_search" \
  -H 'Content-Type: application/json' \
  -d '{"query": {"match": {"user_id": "user123"}}}'
```

### Search Blocks by Height Range
```bash
curl -X GET "http://localhost:9200/lucid_blocks/_search" \
  -H 'Content-Type: application/json' \
  -d '{"query": {"range": {"block_height": {"gte": 100, "lte": 200}}}}'
```

### Search Users by Email
```bash
curl -X GET "http://localhost:9200/lucid_users/_search" \
  -H 'Content-Type: application/json' \
  -d '{"query": {"match": {"email": "user@example.com"}}}'
```

## Monitoring

### Check Cluster Health
```bash
curl http://localhost:9200/_cluster/health?pretty
```

### List All Indices
```bash
curl http://localhost:9200/_cat/indices?v
```

### Get Index Statistics
```bash
curl http://localhost:9200/lucid_sessions/_stats?pretty
```
EOF

    print_success "Usage guide created at /tmp/elasticsearch_usage_guide.md"
}

# Main execution
main() {
    echo ""
    print_info "Starting Elasticsearch initialization..."
    echo ""
    
    # Step 1: Check/Install Elasticsearch
    if ! check_elasticsearch_installed; then
        install_elasticsearch
    fi
    
    # Step 2: Create directories
    create_data_directories
    
    # Step 3: Setup configuration
    setup_configuration
    
    # Step 4: System tuning
    system_tuning
    
    # Step 5: Start Elasticsearch
    start_elasticsearch
    
    # Step 6: Wait for Elasticsearch
    wait_for_elasticsearch || exit 1
    
    # Step 7: Create Lucid indices
    create_lucid_indices
    
    # Step 8: Verify indices
    verify_indices || exit 1
    
    # Step 9: Setup ILM policies (optional)
    setup_ilm_policies
    
    # Step 10: Health check
    health_check || exit 1
    
    # Step 11: Create usage guide
    create_usage_guide
    
    echo ""
    echo "========================================="
    print_success "Elasticsearch initialization complete!"
    echo "========================================="
    echo ""
    print_info "Elasticsearch is running on ${ES_HOST}:${ES_PORT}"
    print_info "Cluster name: ${ES_CLUSTER_NAME}"
    print_info "Data directory: ${ES_DATA_DIR}"
    print_info "Log directory: ${ES_LOG_DIR}"
    print_info "Configuration: ${ES_CONFIG}"
    echo ""
    print_info "Indices created:"
    print_info "  - lucid_sessions"
    print_info "  - lucid_blocks"
    print_info "  - lucid_users"
    echo ""
    print_info "Next steps:"
    print_info "  1. Check cluster health: curl http://${ES_HOST}:${ES_PORT}/_cluster/health"
    print_info "  2. List indices: curl http://${ES_HOST}:${ES_PORT}/_cat/indices?v"
    print_info "  3. View usage guide: cat /tmp/elasticsearch_usage_guide.md"
    echo ""
}

# Run main function
main "$@"

