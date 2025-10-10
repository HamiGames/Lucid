#!/bin/bash
# On-System Chain Startup Script
# Starts EVM-compatible blockchain for Lucid session anchoring

set -euo pipefail

# Configuration
ON_SYSTEM_CHAIN_NETWORK=${ON_SYSTEM_CHAIN_NETWORK:-mainnet}
ON_SYSTEM_CHAIN_RPC_PORT=${ON_SYSTEM_CHAIN_RPC_PORT:-8545}
ON_SYSTEM_CHAIN_WS_PORT=${ON_SYSTEM_CHAIN_WS_PORT:-8546}
ON_SYSTEM_CHAIN_P2P_PORT=${ON_SYSTEM_CHAIN_P2P_PORT:-30303}
ON_SYSTEM_CHAIN_DATA_DIR=${ON_SYSTEM_CHAIN_DATA_DIR:-/app/data/chaindata}
ON_SYSTEM_CHAIN_KEYSTORE_DIR=${ON_SYSTEM_CHAIN_KEYSTORE_DIR:-/app/data/keystore}

# Smart Contract Configuration
LUCID_ANCHORS_ADDRESS=${LUCID_ANCHORS_ADDRESS:-0x1234567890abcdef1234567890abcdef12345678}
LUCID_CHUNK_STORE_ADDRESS=${LUCID_CHUNK_STORE_ADDRESS:-0xabcdef1234567890abcdef1234567890abcdef12}

# Consensus Configuration
CONSENSUS_ENGINE=${CONSENSUS_ENGINE:-proof-of-stake}
BLOCK_TIME_SECONDS=${BLOCK_TIME_SECONDS:-12}
GAS_LIMIT=${GAS_LIMIT:-30000000}

# Logging Configuration
LOG_LEVEL=${LOG_LEVEL:-info}
LOG_FORMAT=${LOG_FORMAT:-json}

# Security Configuration
PRIVATE_KEY_FILE=${PRIVATE_KEY_FILE:-/app/configs/private-key.pem}
TLS_CERT_FILE=${TLS_CERT_FILE:-/app/configs/tls.crt}
TLS_KEY_FILE=${TLS_KEY_FILE:-/app/configs/tls.key}

# Create directories if they don't exist
mkdir -p "$ON_SYSTEM_CHAIN_DATA_DIR"
mkdir -p "$ON_SYSTEM_CHAIN_KEYSTORE_DIR"
mkdir -p /app/logs

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a /app/logs/on-system-chain.log
}

# Function to check if geth is installed
check_geth() {
    if ! command -v geth &> /dev/null; then
        log "ERROR: geth not found. Please install geth."
        exit 1
    fi
    log "INFO: geth version: $(geth version | head -1)"
}

# Function to initialize genesis block if needed
init_genesis() {
    if [ ! -f "$ON_SYSTEM_CHAIN_DATA_DIR/geth/genesis.json" ]; then
        log "INFO: Initializing genesis block..."
        
        # Create genesis configuration
        cat > /tmp/genesis.json << EOF
{
    "config": {
        "chainId": 1337,
        "homesteadBlock": 0,
        "eip150Block": 0,
        "eip155Block": 0,
        "eip158Block": 0,
        "byzantiumBlock": 0,
        "constantinopleBlock": 0,
        "petersburgBlock": 0,
        "istanbulBlock": 0,
        "berlinBlock": 0,
        "londonBlock": 0,
        "arrowGlacierBlock": 0,
        "grayGlacierBlock": 0,
        "mergeNetsplitBlock": 0,
        "shanghaiTime": 0,
        "cancunTime": 0
    },
    "alloc": {
        "$LUCID_ANCHORS_ADDRESS": {
            "balance": "0x1000000000000000000000000"
        },
        "$LUCID_CHUNK_STORE_ADDRESS": {
            "balance": "0x1000000000000000000000000"
        }
    },
    "coinbase": "0x0000000000000000000000000000000000000000",
    "difficulty": "0x400000000",
    "extraData": "0x",
    "gasLimit": "0x1C9C380",
    "nonce": "0x0000000000000042",
    "mixhash": "0x0000000000000000000000000000000000000000000000000000000000000000",
    "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
    "timestamp": "0x00"
}
EOF
        
        # Initialize genesis block
        geth --datadir "$ON_SYSTEM_CHAIN_DATA_DIR" init /tmp/genesis.json
        log "INFO: Genesis block initialized"
    else
        log "INFO: Genesis block already exists"
    fi
}

# Function to deploy smart contracts
deploy_contracts() {
    log "INFO: Deploying smart contracts..."
    
    # Deploy LucidAnchors contract
    if [ ! -f "/app/contracts/build/LucidAnchors.json" ]; then
        log "ERROR: LucidAnchors contract not found. Please build contracts first."
        exit 1
    fi
    
    # Deploy LucidChunkStore contract
    if [ ! -f "/app/contracts/build/LucidChunkStore.json" ]; then
        log "ERROR: LucidChunkStore contract not found. Please build contracts first."
        exit 1
    fi
    
    log "INFO: Smart contracts ready for deployment"
}

# Function to start geth
start_geth() {
    log "INFO: Starting On-System Chain node..."
    
    # Build geth command
    GETH_CMD="geth"
    GETH_CMD="$GETH_CMD --datadir $ON_SYSTEM_CHAIN_DATA_DIR"
    GETH_CMD="$GETH_CMD --networkid 1337"
    GETH_CMD="$GETH_CMD --http"
    GETH_CMD="$GETH_CMD --http.addr 0.0.0.0"
    GETH_CMD="$GETH_CMD --http.port $ON_SYSTEM_CHAIN_RPC_PORT"
    GETH_CMD="$GETH_CMD --http.api eth,net,web3,personal,admin,miner,txpool,debug"
    GETH_CMD="$GETH_CMD --http.corsdomain '*'"
    GETH_CMD="$GETH_CMD --http.vhosts '*'"
    GETH_CMD="$GETH_CMD --ws"
    GETH_CMD="$GETH_CMD --ws.addr 0.0.0.0"
    GETH_CMD="$GETH_CMD --ws.port $ON_SYSTEM_CHAIN_WS_PORT"
    GETH_CMD="$GETH_CMD --ws.api eth,net,web3,personal,admin,miner,txpool,debug"
    GETH_CMD="$GETH_CMD --ws.origins '*'"
    GETH_CMD="$GETH_CMD --port $ON_SYSTEM_CHAIN_P2P_PORT"
    GETH_CMD="$GETH_CMD --maxpeers 50"
    GETH_CMD="$GETH_CMD --nodiscover"
    GETH_CMD="$GETH_CMD --allow-insecure-unlock"
    GETH_CMD="$GETH_CMD --unlock $LUCID_ANCHORS_ADDRESS,$LUCID_CHUNK_STORE_ADDRESS"
    GETH_CMD="$GETH_CMD --password /dev/null"
    GETH_CMD="$GETH_CMD --mine"
    GETH_CMD="$GETH_CMD --miner.etherbase $LUCID_ANCHORS_ADDRESS"
    GETH_CMD="$GETH_CMD --miner.gaslimit $GAS_LIMIT"
    GETH_CMD="$GETH_CMD --miner.threads 1"
    GETH_CMD="$GETH_CMD --verbosity $LOG_LEVEL"
    GETH_CMD="$GETH_CMD --log.json"
    
    # Add TLS configuration if certificates exist
    if [ -f "$TLS_CERT_FILE" ] && [ -f "$TLS_KEY_FILE" ]; then
        GETH_CMD="$GETH_CMD --tls.cert $TLS_CERT_FILE"
        GETH_CMD="$GETH_CMD --tls.key $TLS_KEY_FILE"
        log "INFO: TLS enabled"
    fi
    
    # Start geth
    log "INFO: Executing: $GETH_CMD"
    exec $GETH_CMD
}

# Function to handle shutdown
shutdown() {
    log "INFO: Shutting down On-System Chain node..."
    # geth will handle graceful shutdown
    exit 0
}

# Set up signal handlers
trap shutdown SIGTERM SIGINT

# Main execution
main() {
    log "INFO: Starting On-System Chain initialization..."
    
    # Check prerequisites
    check_geth
    
    # Initialize genesis block
    init_genesis
    
    # Deploy smart contracts
    deploy_contracts
    
    # Start geth
    start_geth
}

# Run main function
main "$@"
