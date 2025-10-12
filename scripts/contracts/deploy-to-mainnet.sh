#!/bin/bash
# scripts/contracts/deploy-to-mainnet.sh
# Deploy contracts to TRON Mainnet for production deployment
# LUCID-STRICT: TRON payment system isolation, distroless architecture

set -Eeuo pipefail

# Script metadata
SCRIPT_NAME="$(basename "$0")"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_PATH/../../.." && pwd)"

# Configuration
TRON_NETWORK="${TRON_NETWORK:-mainnet}"
TRON_RPC_URL="${TRON_RPC_URL:-https://api.trongrid.io}"
CONTRACTS_DIR="${CONTRACTS_DIR:-$PROJECT_ROOT/contracts}"
DEPLOYMENT_DIR="${DEPLOYMENT_DIR:-$PROJECT_ROOT/deployments/mainnet}"
DEPLOYMENT_LOG="${DEPLOYMENT_LOG:-$DEPLOYMENT_DIR/deployment.log}"

# TRON payment system contracts (ISOLATED)
PAYMENT_CONTRACTS=(
    "PayoutRouterV0.sol"
    "PayoutRouterKYC.sol"
)

# Contract addresses (will be populated during deployment)
declare -A CONTRACT_ADDRESSES

# Logging
log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*"; }
die() { printf '[%s][ERROR] %s\n' "$SCRIPT_NAME" "$*" >&2; exit 1; }
warn() { printf '[%s][WARN] %s\n' "$SCRIPT_NAME" "$*" >&2; }

# Validate environment
validate_environment() {
    log "Validating deployment environment..."
    
    # Check required environment variables
    local required_vars=(
        "TRON_PRIVATE_KEY"
        "TRON_ADDRESS"
        "TRON_ENERGY_LIMIT"
        "TRON_BANDWIDTH_LIMIT"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            die "Required environment variable not set: $var"
        fi
    done
    
    # Validate TRON address format
    if [[ ! "$TRON_ADDRESS" =~ ^T[A-Za-z0-9]{33}$ ]]; then
        die "Invalid TRON address format: $TRON_ADDRESS"
    fi
    
    # Check if deployment directory exists
    if [[ ! -d "$DEPLOYMENT_DIR" ]]; then
        mkdir -p "$DEPLOYMENT_DIR"
        log "Created deployment directory: $DEPLOYMENT_DIR"
    fi
    
    # Check if contracts directory exists
    if [[ ! -d "$CONTRACTS_DIR" ]]; then
        die "Contracts directory not found: $CONTRACTS_DIR"
    fi
    
    log "Environment validation completed"
}

# Setup deployment environment
setup_deployment() {
    log "Setting up TRON mainnet deployment environment..."
    
    # Create deployment configuration
    cat > "$DEPLOYMENT_DIR/deployment-config.json" << EOF
{
    "network": "$TRON_NETWORK",
    "rpcUrl": "$TRON_RPC_URL",
    "deployerAddress": "$TRON_ADDRESS",
    "deploymentTimestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "contracts": {
        "payoutRouterV0": {
            "name": "PayoutRouterV0",
            "file": "PayoutRouterV0.sol",
            "purpose": "Non-KYC payout routing"
        },
        "payoutRouterKYC": {
            "name": "PayoutRouterKYC", 
            "file": "PayoutRouterKYC.sol",
            "purpose": "KYC-gated payout routing"
        }
    },
    "deployment": {
        "energyLimit": "$TRON_ENERGY_LIMIT",
        "bandwidthLimit": "$TRON_BANDWIDTH_LIMIT",
        "gasPrice": "1000000"
    }
}
EOF
    
    # Create deployment log
    cat > "$DEPLOYMENT_LOG" << EOF
Lucid RDP TRON Mainnet Deployment Log
====================================
Deployment Date: $(date)
Network: $TRON_NETWORK
Deployer: $TRON_ADDRESS
RPC URL: $TRON_RPC_URL

TRON PAYMENT SYSTEM ISOLATION:
- Only payment contracts deployed to TRON
- No session anchoring contracts
- No consensus participation
- No governance operations

EOF
    
    log "Deployment environment setup completed"
}

# Check TRON network connectivity
check_tron_connectivity() {
    log "Checking TRON mainnet connectivity..."
    
    # Test RPC connectivity
    local response
    response=$(curl -s -X POST "$TRON_RPC_URL/wallet/getnowblock" \
        -H "Content-Type: application/json" \
        -d '{}' || echo "ERROR")
    
    if [[ "$response" == "ERROR" ]]; then
        die "Failed to connect to TRON RPC: $TRON_RPC_URL"
    fi
    
    # Check if we can get account info
    local account_response
    account_response=$(curl -s -X POST "$TRON_RPC_URL/wallet/getaccount" \
        -H "Content-Type: application/json" \
        -d "{\"address\": \"$TRON_ADDRESS\"}" || echo "ERROR")
    
    if [[ "$account_response" == "ERROR" ]]; then
        die "Failed to get account info for: $TRON_ADDRESS"
    fi
    
    log "TRON mainnet connectivity verified"
}

# Check account balance and resources
check_account_resources() {
    log "Checking account resources..."
    
    # Get account balance
    local balance_response
    balance_response=$(curl -s -X POST "$TRON_RPC_URL/wallet/getaccount" \
        -H "Content-Type: application/json" \
        -d "{\"address\": \"$TRON_ADDRESS\"}")
    
    local trx_balance
    trx_balance=$(echo "$balance_response" | jq -r '.balance // 0')
    
    log "TRX Balance: $trx_balance SUN"
    
    # Check energy and bandwidth
    local resource_response
    resource_response=$(curl -s -X POST "$TRON_RPC_URL/wallet/getaccountresource" \
        -H "Content-Type: application/json" \
        -d "{\"address\": \"$TRON_ADDRESS\"}")
    
    local energy_limit
    energy_limit=$(echo "$resource_response" | jq -r '.EnergyLimit // 0')
    local bandwidth_limit
    bandwidth_limit=$(echo "$resource_response" | jq -r '.NetLimit // 0')
    
    log "Energy Limit: $energy_limit"
    log "Bandwidth Limit: $bandwidth_limit"
    
    # Check if we have enough resources
    if [[ "$energy_limit" -lt 1000000 ]]; then
        warn "Low energy limit: $energy_limit (recommended: 1000000+)"
    fi
    
    if [[ "$bandwidth_limit" -lt 1000000 ]]; then
        warn "Low bandwidth limit: $bandwidth_limit (recommended: 1000000+)"
    fi
    
    log "Account resources check completed"
}

# Compile contracts
compile_contracts() {
    log "Compiling TRON payment contracts..."
    
    # Check if Solidity compiler is available
    if ! command -v solc >/dev/null 2>&1; then
        die "Solidity compiler (solc) not found"
    fi
    
    # Compile each payment contract
    for contract in "${PAYMENT_CONTRACTS[@]}"; do
        local contract_path="$CONTRACTS_DIR/$contract"
        
        if [[ ! -f "$contract_path" ]]; then
            die "Contract file not found: $contract_path"
        fi
        
        log "Compiling $contract..."
        
        # Compile contract
        solc --bin --abi --optimize --optimize-runs 200 \
            --output-dir "$DEPLOYMENT_DIR/compiled" \
            "$contract_path" || die "Failed to compile $contract"
        
        log "Compiled $contract successfully"
    done
    
    log "All contracts compiled successfully"
}

# Deploy PayoutRouterV0 contract
deploy_payout_router_v0() {
    log "Deploying PayoutRouterV0 contract..."
    
    local contract_name="PayoutRouterV0"
    local contract_bin="$DEPLOYMENT_DIR/compiled/$contract_name.bin"
    local contract_abi="$DEPLOYMENT_DIR/compiled/$contract_name.abi"
    
    if [[ ! -f "$contract_bin" ]] || [[ ! -f "$contract_abi" ]]; then
        die "Compiled contract files not found for $contract_name"
    fi
    
    # Create deployment transaction
    local deploy_data
    deploy_data=$(cat "$contract_bin")
    
    # Create deployment transaction
    local deploy_tx
    deploy_tx=$(curl -s -X POST "$TRON_RPC_URL/wallet/createtransaction" \
        -H "Content-Type: application/json" \
        -d "{
            \"owner_address\": \"$TRON_ADDRESS\",
            \"contract_address\": \"\",
            \"fee_limit\": 1000000000,
            \"call_value\": 0,
            \"data\": \"$deploy_data\"
        }")
    
    # Sign transaction
    local signed_tx
    signed_tx=$(echo "$deploy_tx" | jq -r '.txID' | tron-sign "$TRON_PRIVATE_KEY" || die "Failed to sign transaction")
    
    # Broadcast transaction
    local broadcast_response
    broadcast_response=$(curl -s -X POST "$TRON_RPC_URL/wallet/broadcasttransaction" \
        -H "Content-Type: application/json" \
        -d "$signed_tx")
    
    local tx_id
    tx_id=$(echo "$broadcast_response" | jq -r '.txid // .txID')
    
    if [[ "$tx_id" == "null" ]] || [[ -z "$tx_id" ]]; then
        die "Failed to broadcast PayoutRouterV0 deployment transaction"
    fi
    
    log "PayoutRouterV0 deployment transaction broadcasted: $tx_id"
    
    # Wait for transaction confirmation
    wait_for_transaction "$tx_id"
    
    # Get contract address
    local contract_address
    contract_address=$(get_contract_address "$tx_id")
    
    if [[ -z "$contract_address" ]]; then
        die "Failed to get PayoutRouterV0 contract address"
    fi
    
    CONTRACT_ADDRESSES["PayoutRouterV0"]="$contract_address"
    
    log "PayoutRouterV0 deployed successfully at: $contract_address"
    
    # Save deployment info
    cat >> "$DEPLOYMENT_LOG" << EOF

PayoutRouterV0 Deployment:
- Transaction ID: $tx_id
- Contract Address: $contract_address
- Purpose: Non-KYC payout routing
- Network: $TRON_NETWORK
EOF
}

# Deploy PayoutRouterKYC contract
deploy_payout_router_kyc() {
    log "Deploying PayoutRouterKYC contract..."
    
    local contract_name="PayoutRouterKYC"
    local contract_bin="$DEPLOYMENT_DIR/compiled/$contract_name.bin"
    local contract_abi="$DEPLOYMENT_DIR/compiled/$contract_name.abi"
    
    if [[ ! -f "$contract_bin" ]] || [[ ! -f "$contract_abi" ]]; then
        die "Compiled contract files not found for $contract_name"
    fi
    
    # Create deployment transaction
    local deploy_data
    deploy_data=$(cat "$contract_bin")
    
    # Create deployment transaction
    local deploy_tx
    deploy_tx=$(curl -s -X POST "$TRON_RPC_URL/wallet/createtransaction" \
        -H "Content-Type: application/json" \
        -d "{
            \"owner_address\": \"$TRON_ADDRESS\",
            \"contract_address\": \"\",
            \"fee_limit\": 1000000000,
            \"call_value\": 0,
            \"data\": \"$deploy_data\"
        }")
    
    # Sign transaction
    local signed_tx
    signed_tx=$(echo "$deploy_tx" | jq -r '.txID' | tron-sign "$TRON_PRIVATE_KEY" || die "Failed to sign transaction")
    
    # Broadcast transaction
    local broadcast_response
    broadcast_response=$(curl -s -X POST "$TRON_RPC_URL/wallet/broadcasttransaction" \
        -H "Content-Type: application/json" \
        -d "$signed_tx")
    
    local tx_id
    tx_id=$(echo "$broadcast_response" | jq -r '.txid // .txID')
    
    if [[ "$tx_id" == "null" ]] || [[ -z "$tx_id" ]]; then
        die "Failed to broadcast PayoutRouterKYC deployment transaction"
    fi
    
    log "PayoutRouterKYC deployment transaction broadcasted: $tx_id"
    
    # Wait for transaction confirmation
    wait_for_transaction "$tx_id"
    
    # Get contract address
    local contract_address
    contract_address=$(get_contract_address "$tx_id")
    
    if [[ -z "$contract_address" ]]; then
        die "Failed to get PayoutRouterKYC contract address"
    fi
    
    CONTRACT_ADDRESSES["PayoutRouterKYC"]="$contract_address"
    
    log "PayoutRouterKYC deployed successfully at: $contract_address"
    
    # Save deployment info
    cat >> "$DEPLOYMENT_LOG" << EOF

PayoutRouterKYC Deployment:
- Transaction ID: $tx_id
- Contract Address: $contract_address
- Purpose: KYC-gated payout routing
- Network: $TRON_NETWORK
EOF
}

# Wait for transaction confirmation
wait_for_transaction() {
    local tx_id="$1"
    local max_attempts=30
    local attempt=1
    
    log "Waiting for transaction confirmation: $tx_id"
    
    while [[ $attempt -le $max_attempts ]]; do
        local tx_info
        tx_info=$(curl -s -X POST "$TRON_RPC_URL/wallet/gettransactioninfobyid" \
            -H "Content-Type: application/json" \
            -d "{\"value\": \"$tx_id\"}")
        
        local result
        result=$(echo "$tx_info" | jq -r '.result // "PENDING"')
        
        if [[ "$result" == "SUCCESS" ]]; then
            log "Transaction confirmed: $tx_id"
            return 0
        elif [[ "$result" == "FAILED" ]]; then
            die "Transaction failed: $tx_id"
        fi
        
        log "Transaction pending... (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    die "Transaction confirmation timeout: $tx_id"
}

# Get contract address from transaction
get_contract_address() {
    local tx_id="$1"
    
    local tx_info
    tx_info=$(curl -s -X POST "$TRON_RPC_URL/wallet/gettransactioninfobyid" \
        -H "Content-Type: application/json" \
        -d "{\"value\": \"$tx_id\"}")
    
    echo "$tx_info" | jq -r '.contract_address // empty'
}

# Verify deployment
verify_deployment() {
    log "Verifying contract deployments..."
    
    # Verify PayoutRouterV0
    if [[ -n "${CONTRACT_ADDRESSES[PayoutRouterV0]:-}" ]]; then
        local pr0_address="${CONTRACT_ADDRESSES[PayoutRouterV0]}"
        local pr0_code
        pr0_code=$(curl -s -X POST "$TRON_RPC_URL/wallet/getcontract" \
            -H "Content-Type: application/json" \
            -d "{\"value\": \"$pr0_address\"}" | jq -r '.bytecode // ""')
        
        if [[ -n "$pr0_code" ]] && [[ "$pr0_code" != "null" ]]; then
            log "✅ PayoutRouterV0 verified at: $pr0_address"
        else
            warn "⚠️ PayoutRouterV0 verification failed"
        fi
    fi
    
    # Verify PayoutRouterKYC
    if [[ -n "${CONTRACT_ADDRESSES[PayoutRouterKYC]:-}" ]]; then
        local prkyc_address="${CONTRACT_ADDRESSES[PayoutRouterKYC]}"
        local prkyc_code
        prkyc_code=$(curl -s -X POST "$TRON_RPC_URL/wallet/getcontract" \
            -H "Content-Type: application/json" \
            -d "{\"value\": \"$prkyc_address\"}" | jq -r '.bytecode // ""')
        
        if [[ -n "$prkyc_code" ]] && [[ "$prkyc_code" != "null" ]]; then
            log "✅ PayoutRouterKYC verified at: $prkyc_address"
        else
            warn "⚠️ PayoutRouterKYC verification failed"
        fi
    fi
}

# Create deployment summary
create_deployment_summary() {
    log "Creating deployment summary..."
    
    local summary_file="$DEPLOYMENT_DIR/deployment-summary.json"
    
    cat > "$summary_file" << EOF
{
    "deployment": {
        "network": "$TRON_NETWORK",
        "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "deployer": "$TRON_ADDRESS",
        "rpcUrl": "$TRON_RPC_URL"
    },
    "contracts": {
        "PayoutRouterV0": {
            "address": "${CONTRACT_ADDRESSES[PayoutRouterV0]:-}",
            "purpose": "Non-KYC payout routing",
            "network": "$TRON_NETWORK"
        },
        "PayoutRouterKYC": {
            "address": "${CONTRACT_ADDRESSES[PayoutRouterKYC]:-}",
            "purpose": "KYC-gated payout routing", 
            "network": "$TRON_NETWORK"
        }
    },
    "isolation": {
        "note": "TRON is used ONLY for payment operations",
        "excluded": [
            "Session anchoring (uses On-System Data Chain)",
            "Consensus participation (uses PoOT)",
            "Governance operations (uses On-System Data Chain)",
            "Chunk storage (uses On-System Data Chain)"
        ]
    }
}
EOF
    
    log "Deployment summary created: $summary_file"
    
    # Display summary
    cat >> "$DEPLOYMENT_LOG" << EOF

DEPLOYMENT SUMMARY:
==================
Network: $TRON_NETWORK
Deployer: $TRON_ADDRESS
Timestamp: $(date)

Deployed Contracts:
- PayoutRouterV0: ${CONTRACT_ADDRESSES[PayoutRouterV0]:-}
- PayoutRouterKYC: ${CONTRACT_ADDRESSES[PayoutRouterKYC]:-}

TRON ISOLATION CONFIRMED:
- Only payment contracts deployed
- No session anchoring
- No consensus participation  
- No governance operations

Deployment completed successfully!
EOF
    
    log "TRON mainnet deployment completed successfully"
    log "Contract addresses saved to: $summary_file"
    log "Full deployment log: $DEPLOYMENT_LOG"
}

# Main execution
main() {
    log "Starting TRON mainnet contract deployment..."
    log "Network: $TRON_NETWORK"
    log "Deployer: $TRON_ADDRESS"
    log "RPC URL: $TRON_RPC_URL"
    
    # Validate environment
    validate_environment
    
    # Setup deployment
    setup_deployment
    
    # Check connectivity and resources
    check_tron_connectivity
    check_account_resources
    
    # Compile contracts
    compile_contracts
    
    # Deploy contracts
    deploy_payout_router_v0
    deploy_payout_router_kyc
    
    # Verify deployment
    verify_deployment
    
    # Create summary
    create_deployment_summary
    
    log "TRON mainnet deployment completed successfully"
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
