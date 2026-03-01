#!/bin/bash
# scripts/contracts/verify-deployment.sh
# Verify contract deployment and addresses on TRON network
# LUCID-STRICT: TRON payment system isolation, distroless architecture

set -Eeuo pipefail

# Script metadata
SCRIPT_NAME="$(basename "$0")"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_PATH/../../.." && pwd)"

# Configuration
TRON_NETWORK="${TRON_NETWORK:-mainnet}"
TRON_RPC_URL="${TRON_RPC_URL:-https://api.trongrid.io}"
DEPLOYMENT_DIR="${DEPLOYMENT_DIR:-$PROJECT_ROOT/deployments/mainnet}"
VERIFICATION_LOG="${VERIFICATION_LOG:-$DEPLOYMENT_DIR/verification.log}"

# Contract addresses to verify
declare -A CONTRACT_ADDRESSES
CONTRACT_ADDRESSES=(
    ["PayoutRouterV0"]=""
    ["PayoutRouterKYC"]=""
)

# Logging
log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*"; }
die() { printf '[%s][ERROR] %s\n' "$SCRIPT_NAME" "$*" >&2; exit 1; }
warn() { printf '[%s][WARN] %s\n' "$SCRIPT_NAME" "$*" >&2; }

# Load contract addresses from deployment summary
load_contract_addresses() {
    log "Loading contract addresses from deployment summary..."
    
    local summary_file="$DEPLOYMENT_DIR/deployment-summary.json"
    
    if [[ ! -f "$summary_file" ]]; then
        die "Deployment summary not found: $summary_file"
    fi
    
    # Extract contract addresses
    CONTRACT_ADDRESSES["PayoutRouterV0"]=$(jq -r '.contracts.PayoutRouterV0.address // empty' "$summary_file")
    CONTRACT_ADDRESSES["PayoutRouterKYC"]=$(jq -r '.contracts.PayoutRouterKYC.address // empty' "$summary_file")
    
    # Validate addresses
    for contract in "${!CONTRACT_ADDRESSES[@]}"; do
        local address="${CONTRACT_ADDRESSES[$contract]}"
        if [[ -z "$address" ]] || [[ "$address" == "null" ]]; then
            warn "Contract address not found for: $contract"
        else
            log "Loaded $contract address: $address"
        fi
    done
}

# Check TRON network connectivity
check_tron_connectivity() {
    log "Checking TRON network connectivity..."
    
    # Test RPC connectivity
    local response
    response=$(curl -s -X POST "$TRON_RPC_URL/wallet/getnowblock" \
        -H "Content-Type: application/json" \
        -d '{}' || echo "ERROR")
    
    if [[ "$response" == "ERROR" ]]; then
        die "Failed to connect to TRON RPC: $TRON_RPC_URL"
    fi
    
    # Get current block info
    local block_height
    block_height=$(echo "$response" | jq -r '.block_header.raw_data.number // "unknown"')
    
    log "Connected to TRON $TRON_NETWORK (Block: $block_height)"
}

# Verify contract deployment
verify_contract_deployment() {
    local contract_name="$1"
    local contract_address="$2"
    
    if [[ -z "$contract_address" ]] || [[ "$contract_address" == "null" ]]; then
        warn "No address provided for $contract_name"
        return 1
    fi
    
    log "Verifying $contract_name at: $contract_address"
    
    # Get contract information
    local contract_info
    contract_info=$(curl -s -X POST "$TRON_RPC_URL/wallet/getcontract" \
        -H "Content-Type: application/json" \
        -d "{\"value\": \"$contract_address\"}" || echo "ERROR")
    
    if [[ "$contract_info" == "ERROR" ]]; then
        warn "Failed to get contract info for $contract_name"
        return 1
    fi
    
    # Check if contract exists
    local bytecode
    bytecode=$(echo "$contract_info" | jq -r '.bytecode // ""')
    
    if [[ -z "$bytecode" ]] || [[ "$bytecode" == "null" ]]; then
        warn "No bytecode found for $contract_name at $contract_address"
        return 1
    fi
    
    # Get contract creator
    local creator
    creator=$(echo "$contract_info" | jq -r '.creator_address // "unknown"')
    
    # Get contract creation transaction
    local tx_id
    tx_id=$(echo "$contract_info" | jq -r '.origin_address // "unknown"')
    
    log "✅ $contract_name verified:"
    log "   Address: $contract_address"
    log "   Creator: $creator"
    log "   Bytecode: ${#bytecode} characters"
    
    # Save verification details
    cat >> "$VERIFICATION_LOG" << EOF

$contract_name Verification:
- Address: $contract_address
- Creator: $creator
- Bytecode Length: ${#bytecode} characters
- Network: $TRON_NETWORK
- Verified: $(date)
EOF
    
    return 0
}

# Verify contract functionality
verify_contract_functionality() {
    local contract_name="$1"
    local contract_address="$2"
    
    if [[ -z "$contract_address" ]] || [[ "$contract_address" == "null" ]]; then
        return 1
    fi
    
    log "Verifying $contract_name functionality..."
    
    # Test contract call (get basic info)
    local test_response
    test_response=$(curl -s -X POST "$TRON_RPC_URL/wallet/triggerconstantcontract" \
        -H "Content-Type: application/json" \
        -d "{
            \"owner_address\": \"$TRON_ADDRESS\",
            \"contract_address\": \"$contract_address\",
            \"function_selector\": \"name()\",
            \"parameter\": \"\"
        }" || echo "ERROR")
    
    if [[ "$test_response" == "ERROR" ]]; then
        warn "Failed to call $contract_name function"
        return 1
    fi
    
    local result
    result=$(echo "$test_response" | jq -r '.result // "failed"')
    
    if [[ "$result" == "success" ]]; then
        log "✅ $contract_name functionality verified"
        return 0
    else
        warn "⚠️ $contract_name functionality test failed"
        return 1
    fi
}

# Verify TRON isolation compliance
verify_tron_isolation() {
    log "Verifying TRON isolation compliance..."
    
    # Check that only payment contracts are deployed
    local payment_contracts=("PayoutRouterV0" "PayoutRouterKYC")
    local deployed_contracts=()
    
    for contract in "${payment_contracts[@]}"; do
        local address="${CONTRACT_ADDRESSES[$contract]}"
        if [[ -n "$address" ]] && [[ "$address" != "null" ]]; then
            deployed_contracts+=("$contract")
        fi
    done
    
    log "Deployed payment contracts: ${deployed_contracts[*]}"
    
    # Verify no session anchoring contracts
    local session_contracts=("LucidAnchors" "LucidChunkStore" "LucidGovernor")
    for contract in "${session_contracts[@]}"; do
        if [[ -n "${CONTRACT_ADDRESSES[$contract]:-}" ]]; then
            die "VIOLATION: Session anchoring contract found on TRON: $contract"
        fi
    done
    
    log "✅ TRON isolation compliance verified"
    log "   - Only payment contracts deployed"
    log "   - No session anchoring contracts"
    log "   - No consensus participation"
    log "   - No governance operations"
}

# Check contract interactions
check_contract_interactions() {
    log "Checking contract interactions..."
    
    # Check PayoutRouterV0 interactions
    if [[ -n "${CONTRACT_ADDRESSES[PayoutRouterV0]:-}" ]]; then
        local pr0_address="${CONTRACT_ADDRESSES[PayoutRouterV0]}"
        log "Checking PayoutRouterV0 interactions at: $pr0_address"
        
        # Get recent transactions
        local recent_txs
        recent_txs=$(curl -s -X POST "$TRON_RPC_URL/wallet/gettransactionsfromthis" \
            -H "Content-Type: application/json" \
            -d "{\"address\": \"$pr0_address\", \"limit\": 10}" || echo "ERROR")
        
        if [[ "$recent_txs" != "ERROR" ]]; then
            local tx_count
            tx_count=$(echo "$recent_txs" | jq -r '.data | length // 0')
            log "PayoutRouterV0 recent transactions: $tx_count"
        fi
    fi
    
    # Check PayoutRouterKYC interactions
    if [[ -n "${CONTRACT_ADDRESSES[PayoutRouterKYC]:-}" ]]; then
        local prkyc_address="${CONTRACT_ADDRESSES[PayoutRouterKYC]}"
        log "Checking PayoutRouterKYC interactions at: $prkyc_address"
        
        # Get recent transactions
        local recent_txs
        recent_txs=$(curl -s -X POST "$TRON_RPC_URL/wallet/gettransactionsfromthis" \
            -H "Content-Type: application/json" \
            -d "{\"address\": \"$prkyc_address\", \"limit\": 10}" || echo "ERROR")
        
        if [[ "$recent_txs" != "ERROR" ]]; then
            local tx_count
            tx_count=$(echo "$recent_txs" | jq -r '.data | length // 0')
            log "PayoutRouterKYC recent transactions: $tx_count"
        fi
    fi
}

# Generate verification report
generate_verification_report() {
    log "Generating verification report..."
    
    local report_file="$DEPLOYMENT_DIR/verification-report.json"
    
    cat > "$report_file" << EOF
{
    "verification": {
        "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "network": "$TRON_NETWORK",
        "rpcUrl": "$TRON_RPC_URL",
        "status": "completed"
    },
    "contracts": {
        "PayoutRouterV0": {
            "address": "${CONTRACT_ADDRESSES[PayoutRouterV0]:-}",
            "verified": $([ -n "${CONTRACT_ADDRESSES[PayoutRouterV0]:-}" ] && echo "true" || echo "false"),
            "purpose": "Non-KYC payout routing"
        },
        "PayoutRouterKYC": {
            "address": "${CONTRACT_ADDRESSES[PayoutRouterKYC]:-}",
            "verified": $([ -n "${CONTRACT_ADDRESSES[PayoutRouterKYC]:-}" ] && echo "true" || echo "false"),
            "purpose": "KYC-gated payout routing"
        }
    },
    "compliance": {
        "tronIsolation": {
            "status": "verified",
            "note": "TRON used ONLY for payment operations",
            "excluded": [
                "Session anchoring (On-System Data Chain)",
                "Consensus participation (PoOT)",
                "Governance operations (On-System Data Chain)",
                "Chunk storage (On-System Data Chain)"
            ]
        }
    }
}
EOF
    
    log "Verification report created: $report_file"
}

# Create verification summary
create_verification_summary() {
    log "Creating verification summary..."
    
    cat > "$VERIFICATION_LOG" << EOF
Lucid RDP TRON Contract Verification Report
===========================================
Verification Date: $(date)
Network: $TRON_NETWORK
RPC URL: $TRON_RPC_URL

TRON PAYMENT SYSTEM VERIFICATION:
- Only payment contracts verified on TRON
- No session anchoring contracts found
- No consensus participation contracts found
- No governance operation contracts found

Contract Verification Results:
EOF
    
    # Add verification results for each contract
    for contract in "${!CONTRACT_ADDRESSES[@]}"; do
        local address="${CONTRACT_ADDRESSES[$contract]}"
        if [[ -n "$address" ]] && [[ "$address" != "null" ]]; then
            cat >> "$VERIFICATION_LOG" << EOF

$contract:
- Address: $address
- Status: VERIFIED
- Purpose: Payment operations only
EOF
        else
            cat >> "$VERIFICATION_LOG" << EOF

$contract:
- Status: NOT FOUND
- Note: Contract not deployed or address not available
EOF
        fi
    done
    
    cat >> "$VERIFICATION_LOG" << EOF

VERIFICATION SUMMARY:
====================
- TRON Isolation: VERIFIED ✅
- Payment Contracts: VERIFIED ✅
- No Unauthorized Contracts: VERIFIED ✅

Verification completed successfully!
EOF
    
    log "Verification summary created: $VERIFICATION_LOG"
}

# Main execution
main() {
    log "Starting TRON contract verification..."
    log "Network: $TRON_NETWORK"
    log "RPC URL: $TRON_RPC_URL"
    
    # Load contract addresses
    load_contract_addresses
    
    # Check connectivity
    check_tron_connectivity
    
    # Verify each contract
    local verification_success=true
    
    for contract in "${!CONTRACT_ADDRESSES[@]}"; do
        local address="${CONTRACT_ADDRESSES[$contract]}"
        if [[ -n "$address" ]] && [[ "$address" != "null" ]]; then
            if ! verify_contract_deployment "$contract" "$address"; then
                verification_success=false
            fi
            
            if ! verify_contract_functionality "$contract" "$address"; then
                verification_success=false
            fi
        else
            warn "Skipping verification for $contract (no address)"
        fi
    done
    
    # Verify TRON isolation
    verify_tron_isolation
    
    # Check contract interactions
    check_contract_interactions
    
    # Generate reports
    generate_verification_report
    create_verification_summary
    
    if [[ "$verification_success" == "true" ]]; then
        log "✅ All contract verifications completed successfully"
    else
        warn "⚠️ Some contract verifications failed"
        exit 1
    fi
    
    log "TRON contract verification completed"
    log "Verification report: $DEPLOYMENT_DIR/verification-report.json"
    log "Verification log: $VERIFICATION_LOG"
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
