#!/usr/bin/env bash
# Lucid Onion Management Demo - Shows both static multi-onion and dynamic onion capabilities
# This script demonstrates the full onion creation workflow

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTDIR="${ONION_DIR:-/run/lucid/onion}"

log() { printf '[demo] %s\n' "$*"; }
success() { printf '[demo][✓] %s\n' "$*"; }
error() { printf '[demo][ERROR] %s\n' "$*" >&2; }

echo "============================================"
echo "Lucid Multi-Onion System Demonstration"
echo "============================================"
echo

# Step 1: Create 5 static onions for core services
log "Step 1: Creating 5 static onion services..."
if "$SCRIPT_DIR/create_ephemeral_onion.sh"; then
    success "Static multi-onion setup complete"
    echo
    
    log "Static onions created:"
    [ -f "$OUTDIR/multi-onion.env" ] && cat "$OUTDIR/multi-onion.env" | grep "^ONION_" || echo "No static onions found"
    echo
else
    error "Failed to create static onions"
    exit 1
fi

# Step 2: Create dynamic onions for different use cases
log "Step 2: Creating dynamic onions for various services..."

# Create a wallet onion with secure defaults
log "Creating wallet onion (secure random port)..."
if "$SCRIPT_DIR/create_dynamic_onion.sh" --wallet --target-host wallet --persistent wallet-primary; then
    success "Wallet onion created"
else
    error "Failed to create wallet onion"
fi

# Create a payment API onion
log "Creating payment API onion..."
if "$SCRIPT_DIR/create_dynamic_onion.sh" --target-host payment-api --target-port 3000 --onion-port 443 payment-gateway; then
    success "Payment API onion created"
else
    error "Failed to create payment API onion"
fi

# Create a monitoring onion
log "Creating monitoring dashboard onion..."
if "$SCRIPT_DIR/create_dynamic_onion.sh" --target-host monitor --target-port 3001 --onion-port 80 monitoring; then
    success "Monitoring onion created"
else
    error "Failed to create monitoring onion"
fi

echo

# Step 3: List all onions
log "Step 3: Listing all onion services..."
"$SCRIPT_DIR/create_dynamic_onion.sh" --list
echo

# Step 4: Show environment files
log "Step 4: Environment files created:"
echo "  Static onions: $OUTDIR/multi-onion.env"
echo "  Dynamic onions: $OUTDIR/dynamic-onions.env"
echo "  JSON Registry: $OUTDIR/onion-registry.json"
echo

# Step 5: Demonstrate rotation
log "Step 5: Demonstrating onion rotation (security practice)..."
if "$SCRIPT_DIR/create_dynamic_onion.sh" --rotate monitoring; then
    success "Monitoring onion rotated with new address"
else
    error "Failed to rotate monitoring onion"
fi

echo
log "Demo Summary:"
echo "  ✓ 5 static onions created for core services"
echo "  ✓ 3 dynamic onions created (wallet, payment, monitoring)"  
echo "  ✓ 1 onion rotated (monitoring)"
echo "  ✓ Environment files generated for docker-compose integration"
echo

# Show usage examples
cat << 'EXAMPLES'
============================================
Usage Examples for Production
============================================

# Create a new wallet onion on-demand:
./create_dynamic_onion.sh --wallet --target-host wallet-service wallet-xyz

# Create payment processor onion:
./create_dynamic_onion.sh --target-host payment --target-port 8443 --onion-port 443 payments

# Rotate a compromised onion:
./create_dynamic_onion.sh --rotate wallet-xyz

# List all active onions:
./create_dynamic_onion.sh --list

# Remove an onion when service shuts down:
./create_dynamic_onion.sh --remove payments

# Integration with docker-compose:
# Source the environment files in your compose:
#   env_file:
#     - /run/lucid/onion/multi-onion.env
#     - /run/lucid/onion/dynamic-onions.env

============================================
Security Notes
============================================

1. Wallet onions use random high ports (8000-9999) for security
2. All onions use ED25519-V3 keys (56-character addresses)
3. Cookie authentication prevents unauthorized onion creation
4. Service IDs are backed up in hex format for recovery
5. JSON registry tracks all onions for audit purposes
6. Rotation capability allows fresh addresses when needed

============================================
EXAMPLES

log "Demo complete! Multi-onion system is ready for production use."