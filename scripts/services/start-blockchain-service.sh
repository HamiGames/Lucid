#!/bin/bash
# Blockchain Anchoring Service Startup Script
# LUCID-STRICT Layer 2 Service Management
# Purpose: Start blockchain anchoring service for blockchain integration
# Compatibility: Distroless, API compliant
# Generated: 2025-01-27

set -e

# Configuration
COMPOSE_FILE="${LUCID_COMPOSE_FILE:-/opt/lucid/docker-compose.yml}"
SERVICE_NAME="${BLOCKCHAIN_SERVICE_NAME:-lucid-blockchain}"
LOG_FILE="${LOG_FILE:-/var/log/lucid/blockchain-service.log}"
BLOCKCHAIN_NETWORK="${BLOCKCHAIN_NETWORK:-shasta}"
TRON_NODE_URL="${TRON_NODE_URL:-https://api.shasta.trongrid.io}"
CONTRACT_ADDRESS="${CONTRACT_ADDRESS:-}"
PRIVATE_KEY_FILE="${PRIVATE_KEY_FILE:-/data/keys/blockchain-private.key}"
ANCHOR_INTERVAL="${ANCHOR_INTERVAL:-300}" # 5 minutes
BATCH_SIZE="${BATCH_SIZE:-100}"
GAS_LIMIT="${GAS_LIMIT:-10000000}"
GAS_PRICE="${GAS_PRICE:-1000000}"
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB="${MONGO_DB:-lucid}"
MONGO_USER="${MONGO_USER:-lucid}"
MONGO_PASS="${MONGO_PASS:-lucid}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${1}" | tee -a "$LOG_FILE"
}

log_info() {
    log "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    log "${GREEN}✅ $1${NC}"
}

log_warning() {
    log "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    log "${RED}❌ $1${NC}"
}

# Create directories if they don't exist
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$(dirname "$PRIVATE_KEY_FILE")"

echo "========================================"
log_info "⛓️  LUCID Blockchain Anchoring Service"
echo "========================================"

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Start blockchain anchoring service for blockchain integration"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -f, --force             Force start without confirmation"
    echo "  -s, --stop              Stop blockchain service"
    echo "  -r, --restart           Restart blockchain service"
    echo "  -d, --daemon            Run in daemon mode"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -c, --check             Check service status"
    echo "  -l, --logs              Show service logs"
    echo "  -t, --test              Test blockchain connectivity"
    echo "  -n, --network NETWORK   Set blockchain network (shasta,mainnet)"
    echo "  -k, --key-file FILE     Set private key file path"
    echo "  -a, --anchor            Perform immediate anchor operation"
    echo "  --interval SECONDS      Set anchoring interval in seconds"
    echo "  --batch-size SIZE       Set batch size for anchoring"
    echo "  --gas-limit LIMIT       Set gas limit for transactions"
    echo "  --gas-price PRICE       Set gas price for transactions"
    echo ""
    echo "Environment Variables:"
    echo "  LUCID_COMPOSE_FILE      Docker compose file path"
    echo "  BLOCKCHAIN_SERVICE_NAME Service name (default: lucid-blockchain)"
    echo "  BLOCKCHAIN_NETWORK      Blockchain network (default: shasta)"
    echo "  TRON_NODE_URL           TRON node URL"
    echo "  CONTRACT_ADDRESS        Smart contract address"
    echo "  PRIVATE_KEY_FILE        Private key file path"
    echo "  ANCHOR_INTERVAL         Anchoring interval in seconds (default: 300)"
    echo "  BATCH_SIZE              Batch size for anchoring (default: 100)"
    echo "  GAS_LIMIT               Gas limit for transactions (default: 10000000)"
    echo "  GAS_PRICE               Gas price for transactions (default: 1000000)"
    echo ""
    echo "Examples:"
    echo "  $0 --network mainnet --key-file /secure/keys/blockchain.key"
    echo "  $0 --stop                       Stop blockchain service"
    echo "  $0 --restart                    Restart blockchain service"
    echo "  $0 --test                       Test blockchain connectivity"
    echo "  $0 --anchor                     Perform immediate anchor operation"
}

# Parse command line arguments
FORCE=false
ACTION="start"
DAEMON_MODE=false
VERBOSE=false
CHECK_STATUS=false
SHOW_LOGS=false
TEST_CONNECTIVITY=false
IMMEDIATE_ANCHOR=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -s|--stop)
            ACTION="stop"
            shift
            ;;
        -r|--restart)
            ACTION="restart"
            shift
            ;;
        -d|--daemon)
            DAEMON_MODE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--check)
            CHECK_STATUS=true
            shift
            ;;
        -l|--logs)
            SHOW_LOGS=true
            shift
            ;;
        -t|--test)
            TEST_CONNECTIVITY=true
            shift
            ;;
        -n|--network)
            BLOCKCHAIN_NETWORK="$2"
            shift 2
            ;;
        -k|--key-file)
            PRIVATE_KEY_FILE="$2"
            shift 2
            ;;
        -a|--anchor)
            IMMEDIATE_ANCHOR=true
            shift
            ;;
        --interval)
            ANCHOR_INTERVAL="$2"
            shift 2
            ;;
        --batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --gas-limit)
            GAS_LIMIT="$2"
            shift 2
            ;;
        --gas-price)
            GAS_PRICE="$2"
            shift 2
            ;;
        -*)
            log_error "Unknown option $1"
            show_usage
            exit 1
            ;;
        *)
            log_error "Unexpected argument: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Function to set network configuration
set_network_config() {
    case "$BLOCKCHAIN_NETWORK" in
        "shasta")
            TRON_NODE_URL="${TRON_NODE_URL:-https://api.shasta.trongrid.io}"
            log_info "Using Shasta testnet: $TRON_NODE_URL"
            ;;
        "mainnet")
            TRON_NODE_URL="${TRON_NODE_URL:-https://api.trongrid.io}"
            log_info "Using TRON mainnet: $TRON_NODE_URL"
            ;;
        *)
            log_error "Unsupported blockchain network: $BLOCKCHAIN_NETWORK"
            log_info "Supported networks: shasta, mainnet"
            return 1
            ;;
    esac
}

# Function to check Docker availability
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not available"
        return 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        return 1
    fi
    
    log_success "Docker is available and running"
    return 0
}

# Function to check MongoDB connection
check_mongodb() {
    log_info "Testing MongoDB connection..."
    
    local auth_string=""
    if [[ -n "$MONGO_USER" && -n "$MONGO_PASS" ]]; then
        auth_string="-u $MONGO_USER -p $MONGO_PASS --authenticationDatabase admin"
    fi
    
    if mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" $auth_string --eval "db.runCommand({ping: 1})" &>/dev/null; then
        log_success "MongoDB connection successful"
        return 0
    else
        log_error "MongoDB connection failed"
        return 1
    fi
}

# Function to check private key file
check_private_key() {
    if [[ ! -f "$PRIVATE_KEY_FILE" ]]; then
        log_error "Private key file not found: $PRIVATE_KEY_FILE"
        log_info "Please ensure the private key file exists and is accessible"
        return 1
    fi
    
    # Check file permissions
    local file_perms=$(stat -c %a "$PRIVATE_KEY_FILE" 2>/dev/null || stat -f %A "$PRIVATE_KEY_FILE" 2>/dev/null || echo "unknown")
    if [[ "$file_perms" != "600" ]]; then
        log_warning "Private key file permissions are $file_perms (recommended: 600)"
        if [[ "$FORCE" == "false" ]]; then
            read -p "Continue with insecure permissions? (yes/no): " confirm
            if [[ "$confirm" != "yes" ]]; then
                log_info "Please secure the private key file: chmod 600 $PRIVATE_KEY_FILE"
                return 1
            fi
        fi
    fi
    
    log_success "Private key file found and accessible"
    return 0
}

# Function to test blockchain connectivity
test_blockchain_connectivity() {
    log_info "Testing blockchain connectivity..."
    
    # Set network configuration
    set_network_config
    
    # Test TRON node connectivity
    log_info "Testing TRON node connectivity: $TRON_NODE_URL"
    
    if command -v curl &> /dev/null; then
        local response=$(curl -s -w "%{http_code}" -o /dev/null --connect-timeout 10 "$TRON_NODE_URL/wallet/getnowblock")
        if [[ "$response" == "200" ]]; then
            log_success "TRON node is accessible"
        else
            log_error "TRON node connectivity failed (HTTP $response)"
            return 1
        fi
    else
        log_warning "curl not available, cannot test node connectivity"
    fi
    
    # Test private key validity
    if check_private_key; then
        log_info "Testing private key validity..."
        
        # Try to derive address from private key (basic validation)
        local private_key=$(head -1 "$PRIVATE_KEY_FILE" | tr -d '\n\r')
        if [[ ${#private_key} -eq 64 ]]; then
            log_success "Private key format appears valid"
        else
            log_warning "Private key format may be invalid (length: ${#private_key})"
        fi
    fi
    
    # Test contract address if provided
    if [[ -n "$CONTRACT_ADDRESS" ]]; then
        log_info "Testing contract address: $CONTRACT_ADDRESS"
        
        if command -v curl &> /dev/null; then
            local contract_response=$(curl -s --connect-timeout 10 "$TRON_NODE_URL/wallet/getcontract?value=$CONTRACT_ADDRESS")
            if echo "$contract_response" | grep -q "contract_name"; then
                log_success "Contract address is valid and accessible"
            else
                log_warning "Contract address may be invalid or not accessible"
            fi
        else
            log_warning "curl not available, cannot test contract address"
        fi
    else
        log_warning "No contract address configured"
    fi
    
    log_success "Blockchain connectivity test completed"
    return 0
}

# Function to check service status
check_service_status() {
    log_info "Checking blockchain service status..."
    
    if [[ -f "$COMPOSE_FILE" ]]; then
        if docker-compose -f "$COMPOSE_FILE" ps "$SERVICE_NAME" &>/dev/null; then
            local status=$(docker-compose -f "$COMPOSE_FILE" ps "$SERVICE_NAME" --format "table {{.State}}" | tail -1)
            log_info "Service status: $status"
            
            if [[ "$status" == "Up" ]]; then
                log_success "Blockchain service is running"
                return 0
            else
                log_warning "Blockchain service is not running"
                return 1
            fi
        else
            log_warning "Service not found in compose file"
            return 1
        fi
    else
        log_error "Compose file not found: $COMPOSE_FILE"
        return 1
    fi
}

# Function to show service logs
show_service_logs() {
    log_info "Showing blockchain service logs..."
    
    if [[ -f "$COMPOSE_FILE" ]]; then
        docker-compose -f "$COMPOSE_FILE" logs --tail=50 "$SERVICE_NAME"
    else
        log_error "Compose file not found: $COMPOSE_FILE"
        return 1
    fi
}

# Function to perform immediate anchor operation
perform_anchor_operation() {
    log_info "Performing immediate anchor operation..."
    
    # Check if service is running
    if ! check_service_status &>/dev/null; then
        log_error "Blockchain service is not running"
        return 1
    fi
    
    # Trigger anchor operation via service API or direct command
    if [[ -f "$COMPOSE_FILE" ]]; then
        if docker-compose -f "$COMPOSE_FILE" exec "$SERVICE_NAME" python -c "
import sys
sys.path.append('/app')
from blockchain.anchor import trigger_immediate_anchor
trigger_immediate_anchor()
" 2>/dev/null; then
            log_success "Immediate anchor operation triggered successfully"
            return 0
        else
            log_error "Failed to trigger immediate anchor operation"
            return 1
        fi
    else
        log_error "Compose file not found: $COMPOSE_FILE"
        return 1
    fi
}

# Function to start blockchain service
start_blockchain_service() {
    log_info "Starting blockchain service..."
    
    # Check prerequisites
    if ! check_docker; then
        return 1
    fi
    
    if ! check_mongodb; then
        return 1
    fi
    
    if ! check_private_key; then
        return 1
    fi
    
    # Set network configuration
    if ! set_network_config; then
        return 1
    fi
    
    # Check if service is already running
    if check_service_status &>/dev/null; then
        log_warning "Blockchain service is already running"
        if [[ "$FORCE" == "false" ]]; then
            read -p "Restart the service? (yes/no): " confirm
            if [[ "$confirm" == "yes" ]]; then
                stop_blockchain_service
            else
                log_info "Service start cancelled"
                return 0
            fi
        else
            stop_blockchain_service
        fi
    fi
    
    # Start service using docker-compose
    if [[ -f "$COMPOSE_FILE" ]]; then
        log_info "Starting service from compose file: $COMPOSE_FILE"
        
        # Set environment variables for the service
        export BLOCKCHAIN_NETWORK="$BLOCKCHAIN_NETWORK"
        export TRON_NODE_URL="$TRON_NODE_URL"
        export CONTRACT_ADDRESS="$CONTRACT_ADDRESS"
        export PRIVATE_KEY_FILE="$PRIVATE_KEY_FILE"
        export ANCHOR_INTERVAL="$ANCHOR_INTERVAL"
        export BATCH_SIZE="$BATCH_SIZE"
        export GAS_LIMIT="$GAS_LIMIT"
        export GAS_PRICE="$GAS_PRICE"
        export MONGO_HOST="$MONGO_HOST"
        export MONGO_PORT="$MONGO_PORT"
        export MONGO_DB="$MONGO_DB"
        export MONGO_USER="$MONGO_USER"
        export MONGO_PASS="$MONGO_PASS"
        
        if docker-compose -f "$COMPOSE_FILE" up -d "$SERVICE_NAME"; then
            log_success "Blockchain service started successfully"
            
            # Wait for service to be ready
            log_info "Waiting for service to be ready..."
            sleep 10
            
            if check_service_status; then
                log_success "Blockchain service is running and healthy"
                return 0
            else
                log_error "Blockchain service started but is not healthy"
                return 1
            fi
        else
            log_error "Failed to start blockchain service"
            return 1
        fi
    else
        log_error "Compose file not found: $COMPOSE_FILE"
        log_info "Please ensure the compose file exists and contains the blockchain service"
        return 1
    fi
}

# Function to stop blockchain service
stop_blockchain_service() {
    log_info "Stopping blockchain service..."
    
    if [[ -f "$COMPOSE_FILE" ]]; then
        if docker-compose -f "$COMPOSE_FILE" stop "$SERVICE_NAME"; then
            log_success "Blockchain service stopped successfully"
            return 0
        else
            log_error "Failed to stop blockchain service"
            return 1
        fi
    else
        log_error "Compose file not found: $COMPOSE_FILE"
        return 1
    fi
}

# Function to restart blockchain service
restart_blockchain_service() {
    log_info "Restarting blockchain service..."
    
    if stop_blockchain_service; then
        sleep 5
        if start_blockchain_service; then
            log_success "Blockchain service restarted successfully"
            return 0
        else
            log_error "Failed to restart blockchain service"
            return 1
        fi
    else
        log_error "Failed to stop blockchain service for restart"
        return 1
    fi
}

# Function to validate configuration
validate_configuration() {
    log_info "Validating blockchain service configuration..."
    
    local errors=0
    
    # Check required environment variables
    if [[ -z "$BLOCKCHAIN_NETWORK" ]]; then
        log_error "BLOCKCHAIN_NETWORK is not set"
        ((errors++))
    fi
    
    if [[ -z "$TRON_NODE_URL" ]]; then
        log_error "TRON_NODE_URL is not set"
        ((errors++))
    fi
    
    if [[ -z "$CONTRACT_ADDRESS" ]]; then
        log_warning "CONTRACT_ADDRESS is not set - anchoring may not work"
    fi
    
    if [[ -z "$PRIVATE_KEY_FILE" ]]; then
        log_error "PRIVATE_KEY_FILE is not set"
        ((errors++))
    fi
    
    # Validate numeric parameters
    if ! [[ "$ANCHOR_INTERVAL" =~ ^[0-9]+$ ]]; then
        log_error "ANCHOR_INTERVAL must be a number"
        ((errors++))
    fi
    
    if ! [[ "$BATCH_SIZE" =~ ^[0-9]+$ ]]; then
        log_error "BATCH_SIZE must be a number"
        ((errors++))
    fi
    
    if ! [[ "$GAS_LIMIT" =~ ^[0-9]+$ ]]; then
        log_error "GAS_LIMIT must be a number"
        ((errors++))
    fi
    
    if ! [[ "$GAS_PRICE" =~ ^[0-9]+$ ]]; then
        log_error "GAS_PRICE must be a number"
        ((errors++))
    fi
    
    if [[ $errors -eq 0 ]]; then
        log_success "Configuration validation passed"
        return 0
    else
        log_error "Configuration validation failed with $errors errors"
        return 1
    fi
}

# Main function
main() {
    # Handle special operations
    if [[ "$CHECK_STATUS" == "true" ]]; then
        check_service_status
        return $?
    fi
    
    if [[ "$SHOW_LOGS" == "true" ]]; then
        show_service_logs
        return 0
    fi
    
    if [[ "$TEST_CONNECTIVITY" == "true" ]]; then
        test_blockchain_connectivity
        return $?
    fi
    
    if [[ "$IMMEDIATE_ANCHOR" == "true" ]]; then
        perform_anchor_operation
        return $?
    fi
    
    # Validate configuration
    if ! validate_configuration; then
        log_error "Configuration validation failed"
        return 1
    fi
    
    # Handle main actions
    case "$ACTION" in
        "start")
            start_blockchain_service
            ;;
        "stop")
            stop_blockchain_service
            ;;
        "restart")
            restart_blockchain_service
            ;;
        *)
            log_error "Unknown action: $ACTION"
            show_usage
            exit 1
            ;;
    esac
}

# Set up signal handlers
cleanup() {
    log_info "Cleaning up..."
    # Cleanup will be handled by individual functions
}

trap cleanup EXIT INT TERM

# Run main function
main "$@"
