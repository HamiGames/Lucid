# Step 3: Clean blockchain/blockchain_anchor.py

## Overview
**Priority**: CRITICAL  
**Violations**: 67 TRON references (HIGHEST)  
**File**: `blockchain/blockchain_anchor.py`  
**Purpose**: Remove all TRON payment service code and ensure anchoring operations are TRON-free.

## Pre-Cleanup Actions

### 1. Backup Current File
```bash
# Create backup before modifications
cp blockchain/blockchain_anchor.py blockchain/blockchain_anchor.py.backup
```

### 2. Identify All TRON References
```bash
# Search for all TRON references in the file
grep -n "tron\|TRON" blockchain/blockchain_anchor.py
```

### 3. Document Current TRON Functionality
Before removal, document any valid payment logic that needs to be moved to `payment-systems/tron/`.

## Cleanup Actions

### 1. Remove TRON Payment Service Code (67 violations)
**Target**: All TRON payment service implementations

**Examples of what to remove**:
```python
# Remove TRON payment service imports
from tron_payment_service import TronPaymentService
from tron_client import TronClient
from tron_utils import TronUtils

# Remove TRON service initialization
self.tron_service = TronPaymentService()
self.tron_client = TronClient()

# Remove TRON payment methods
def process_tron_payment(self, amount, address):
    return self.tron_service.process_payment(amount, address)

def get_tron_balance(self, address):
    return self.tron_client.get_balance(address)

def send_tron_transaction(self, to_address, amount):
    return self.tron_client.send_transaction(to_address, amount)
```

### 2. Clean Up TRON Configuration Comments
**Target**: All TRON-related configuration comments

**Examples of what to remove**:
```python
# Remove TRON configuration comments
# TRON network configuration
# TRON mainnet URL: https://api.trongrid.io
# TRON testnet URL: https://api.shasta.trongrid.io
# TRON private key configuration
```

### 3. Remove TRON Payout Methods
**Target**: All TRON payout functionality

**Examples of what to remove**:
```python
# Remove TRON payout methods
def calculate_tron_payout(self, user_id):
    # TRON payout calculation logic
    pass

def execute_tron_payout(self, payout_data):
    # TRON payout execution logic
    pass

def validate_tron_address(self, address):
    # TRON address validation logic
    pass
```

### 4. Ensure Anchoring Operations Are TRON-Free
**Target**: Core anchoring functionality should only use lucid_blocks

**Required**: Anchoring operations should only reference:
- Lucid blockchain operations
- Core anchoring logic
- No payment processing integration

## Specific Code Changes

### Remove TRON Imports
```python
# REMOVE THESE IMPORTS:
from tron_payment_service import TronPaymentService
from tron_client import TronClient
from tron_utils import TronUtils
from tron_models import TronTransaction, TronAddress
```

### Remove TRON Service Initialization
```python
# REMOVE FROM __init__ METHOD:
self.tron_service = TronPaymentService()
self.tron_client = TronClient()
self.tron_config = TronConfig()
```

### Remove TRON Payment Methods
```python
# REMOVE ALL TRON PAYMENT METHODS:
def process_tron_payment(self, ...):
    # Remove entire method

def get_tron_balance(self, ...):
    # Remove entire method

def send_tron_transaction(self, ...):
    # Remove entire method

def calculate_tron_payout(self, ...):
    # Remove entire method

def execute_tron_payout(self, ...):
    # Remove entire method
```

### Clean Up Configuration
```python
# REMOVE TRON CONFIGURATION:
TRON_MAINNET_URL = "https://api.trongrid.io"
TRON_TESTNET_URL = "https://api.shasta.trongrid.io"
TRON_PRIVATE_KEY = os.getenv('TRON_PRIVATE_KEY')
```

## Move Valid Payment Logic to payment-systems/tron/

### Before Removal, Check for Valid Logic
If any TRON payment logic is still needed, move it to:
- `payment-systems/tron/tron_payment_service.py`
- `payment-systems/tron/tron_client.py`
- `payment-systems/tron/payout_router.py`

### Example of Logic to Move
```python
# If this logic exists and is needed, move to payment-systems/tron/:
class TronPaymentService:
    def process_payment(self, amount, address):
        # Move to payment-systems/tron/tron_payment_service.py
        pass

class TronClient:
    def get_balance(self, address):
        # Move to payment-systems/tron/tron_client.py
        pass
```

## Validation Steps

### 1. Verify TRON References Removed
```bash
# Check for any remaining TRON references
grep -i "tron" blockchain/blockchain_anchor.py
# Should return no results
```

### 2. Test Anchoring Functionality
```bash
# Ensure anchoring operations still work
python -c "
from blockchain.blockchain_anchor import BlockchainAnchor
anchor = BlockchainAnchor()
print('Blockchain anchor created successfully')
"
```

### 3. Verify No TRON Dependencies
```bash
# Check that no TRON modules are imported
python -c "
import ast
import sys
with open('blockchain/blockchain_anchor.py', 'r') as f:
    tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if 'tron' in alias.name.lower():
                    print(f'TRON import found: {alias.name}')
                    sys.exit(1)
        elif isinstance(node, ast.ImportFrom):
            if node.module and 'tron' in node.module.lower():
                print(f'TRON import found: {node.module}')
                sys.exit(1)
print('No TRON imports found')
"
```

## Expected Results

### After Cleanup
- [ ] Zero TRON references in blockchain_anchor.py
- [ ] All TRON payment service code removed
- [ ] All TRON configuration comments removed
- [ ] All TRON payout methods removed
- [ ] Anchoring operations use only lucid_blocks
- [ ] File imports successfully without TRON dependencies
- [ ] Core anchoring functionality preserved

### File Structure After Cleanup
```python
# blockchain/blockchain_anchor.py should contain:
from blockchain.core.blockchain_engine import BlockchainEngine
from blockchain.core.models import LucidBlock

class BlockchainAnchor:
    def __init__(self):
        self.blockchain_engine = BlockchainEngine()
        # No TRON services
    
    def anchor_block(self, block_data):
        # Core anchoring logic only
        # No payment processing
        pass
    
    def verify_anchor(self, anchor_data):
        # Core verification logic only
        # No TRON dependencies
        pass
```

## Testing

### 1. Import Test
```bash
cd blockchain
python -c "from blockchain_anchor import BlockchainAnchor; print('BlockchainAnchor imports successfully')"
```

### 2. Functionality Test
```bash
# Test core anchoring operations
python -c "
from blockchain_anchor import BlockchainAnchor
anchor = BlockchainAnchor()
# Test basic functionality without TRON dependencies
print('Core anchoring functionality accessible')
"
```

### 3. Integration Test
```bash
# Ensure anchoring integrates with blockchain core
python -c "
from blockchain_anchor import BlockchainAnchor
from blockchain.core.blockchain_engine import BlockchainEngine
anchor = BlockchainAnchor()
engine = BlockchainEngine()
print('Integration successful')
"
```

## Troubleshooting

### If Import Errors Occur
1. Check for missing blockchain core dependencies
2. Verify blockchain core modules are accessible
3. Ensure no circular imports

### If TRON References Persist
1. Search for case variations: `Tron`, `TRON`, `tron`
2. Check for partial matches in comments
3. Verify all string literals are clean
4. Check for TRON in variable names

### If Anchoring Doesn't Work
1. Verify blockchain core functionality is intact
2. Check that payment logic has been moved to payment-systems/
3. Ensure no critical anchoring functionality was accidentally removed

## Success Criteria

### Must Complete
- [ ] Zero TRON references found in file
- [ ] All TRON payment service code removed
- [ ] All TRON configuration comments removed
- [ ] All TRON payout methods removed
- [ ] File imports without errors
- [ ] Core anchoring functionality preserved
- [ ] No payment processing logic in anchoring

### Verification Commands
```bash
# Final verification
grep -i "tron" blockchain/blockchain_anchor.py
# Should return: (no matches)

# Test import
python -c "from blockchain.blockchain_anchor import BlockchainAnchor"
# Should return: (no errors)

# Test functionality
python -c "from blockchain.blockchain_anchor import BlockchainAnchor; anchor = BlockchainAnchor()"
# Should return: (no errors)
```

## Next Steps
After completing this cleanup, proceed to Step 4: Clean blockchain/deployment/contract_deployment.py

## Rollback Plan
If issues are encountered:
```bash
# Restore from backup
cp blockchain/blockchain_anchor.py.backup blockchain/blockchain_anchor.py
```

## References
- Critical Cleanup Plan: `critical-cleanup-plan.plan.md`
- BUILD_REQUIREMENTS_GUIDE.md - TRON isolation requirements
- Lucid Blocks Architecture - Core blockchain functionality
- TRON Payment Cluster Guide - Payment system architecture
