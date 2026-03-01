# Step 6: Clean blockchain/core/blockchain_engine.py

## Overview
**Priority**: CRITICAL  
**Violations**: 34 TRON references  
**File**: `blockchain/core/blockchain_engine.py`  
**Purpose**: Remove TRON client initialization and ensure engine only manages lucid_blocks operations.

## Pre-Cleanup Actions

### 1. Backup Current File
```bash
# Create backup before modifications
cp blockchain/core/blockchain_engine.py blockchain/core/blockchain_engine.py.backup
```

### 2. Identify TRON References
```bash
# Search for TRON references in the file
grep -n "tron\|TRON" blockchain/core/blockchain_engine.py
```

### 3. Document Current TRON Functionality
Before removal, document any TRON engine logic that needs to be moved to `payment-systems/tron/`.

## Cleanup Actions

### 1. Remove TRON Client Initialization
**Target**: All TRON client setup and configuration

**Examples of what to remove**:
```python
# Remove TRON client imports
from tron_client import TronClient
from tron_network import TronNetwork
from tron_utils import TronUtils

# Remove TRON client initialization
self.tron_client = TronClient()
self.tron_network = TronNetwork()
self.tron_config = TronConfig()

# Remove TRON client configuration
TRON_MAINNET_URL = "https://api.trongrid.io"
TRON_TESTNET_URL = "https://api.shasta.trongrid.io"
TRON_PRIVATE_KEY = os.getenv('TRON_PRIVATE_KEY')
```

### 2. Clean Up TRON Payout Monitoring
**Target**: All TRON payout monitoring and tracking logic

**Examples of what to remove**:
```python
# Remove TRON payout monitoring methods
def monitor_tron_payouts(self):
    # TRON payout monitoring logic
    pass

def track_tron_transactions(self):
    # TRON transaction tracking logic
    pass

def update_tron_balances(self):
    # TRON balance update logic
    pass

def process_tron_payout_queue(self):
    # TRON payout queue processing logic
    pass
```

### 3. Remove TRON Transaction Handling
**Target**: All TRON-specific transaction processing

**Examples of what to remove**:
```python
# Remove TRON transaction handling methods
def process_tron_transaction(self, transaction_data):
    # TRON transaction processing logic
    pass

def validate_tron_transaction(self, transaction):
    # TRON transaction validation logic
    pass

def broadcast_tron_transaction(self, transaction):
    # TRON transaction broadcasting logic
    pass

def get_tron_transaction_status(self, tx_hash):
    # TRON transaction status checking logic
    pass
```

### 4. Ensure Engine Only Manages Lucid Blocks Operations
**Target**: Engine should only handle lucid_blocks operations

**Required**: Engine should only contain:
- Lucid blockchain operations
- Core blockchain engine logic
- No payment processing integration

## Specific Code Changes

### Remove TRON Imports
```python
# REMOVE THESE IMPORTS:
from tron_client import TronClient
from tron_network import TronNetwork
from tron_utils import TronUtils
from tron_models import TronTransaction, TronAddress
```

### Remove TRON Client Initialization
```python
# REMOVE FROM __init__ METHOD:
self.tron_client = TronClient()
self.tron_network = TronNetwork()
self.tron_config = TronConfig()
self.tron_payout_monitor = TronPayoutMonitor()
```

### Remove TRON Methods
```python
# REMOVE ALL TRON METHODS:
def monitor_tron_payouts(self, ...):
    # Remove entire method

def track_tron_transactions(self, ...):
    # Remove entire method

def process_tron_transaction(self, ...):
    # Remove entire method

def validate_tron_transaction(self, ...):
    # Remove entire method

def broadcast_tron_transaction(self, ...):
    # Remove entire method

def get_tron_transaction_status(self, ...):
    # Remove entire method

def update_tron_balances(self, ...):
    # Remove entire method

def process_tron_payout_queue(self, ...):
    # Remove entire method
```

### Clean Up Configuration
```python
# REMOVE TRON CONFIGURATION:
TRON_MAINNET_URL = "https://api.trongrid.io"
TRON_TESTNET_URL = "https://api.shasta.trongrid.io"
TRON_PRIVATE_KEY = os.getenv('TRON_PRIVATE_KEY')
TRON_PAYOUT_ENABLED = os.getenv('TRON_PAYOUT_ENABLED', 'false').lower() == 'true'
```

## Move Valid TRON Logic to payment-systems/tron/

### Before Removal, Check for Valid Logic
If any TRON engine logic is still needed, move it to:
- `payment-systems/tron/tron_engine.py`
- `payment-systems/tron/tron_client.py`
- `payment-systems/tron/payout_monitor.py`

### Example of Logic to Move
```python
# If this logic exists and is needed, move to payment-systems/tron/:
class TronEngine:
    def monitor_payouts(self):
        # Move to payment-systems/tron/tron_engine.py
        pass

class TronPayoutMonitor:
    def track_transactions(self):
        # Move to payment-systems/tron/payout_monitor.py
        pass
```

## Ensure Core Blockchain Engine Functionality

### Required Core Engine Logic
```python
# ENSURE THESE CORE METHODS REMAIN:
class BlockchainEngine:
    def __init__(self):
        self.blockchain = LucidBlockchain()
        # No TRON services
    
    def create_block(self, transactions):
        # Core block creation logic
        pass
    
    def validate_block(self, block):
        # Core block validation logic
        pass
    
    def add_transaction(self, transaction):
        # Core transaction addition logic
        pass
    
    def get_blockchain_state(self):
        # Core blockchain state logic
        pass
```

## Validation Steps

### 1. Verify TRON References Removed
```bash
# Check for any remaining TRON references
grep -i "tron" blockchain/core/blockchain_engine.py
# Should return no results
```

### 2. Test Engine Functionality
```bash
# Ensure engine still works
python -c "
from blockchain.core.blockchain_engine import BlockchainEngine
engine = BlockchainEngine()
print('Blockchain engine created successfully')
"
```

### 3. Verify No TRON Dependencies
```bash
# Check that no TRON modules are imported
python -c "
import ast
import sys
with open('blockchain/core/blockchain_engine.py', 'r') as f:
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
- [ ] Zero TRON references in blockchain_engine.py
- [ ] All TRON client initialization removed
- [ ] All TRON payout monitoring removed
- [ ] All TRON transaction handling removed
- [ ] Engine only manages lucid_blocks operations
- [ ] File imports successfully without TRON dependencies
- [ ] Core blockchain engine functionality preserved

### File Structure After Cleanup
```python
# blockchain/core/blockchain_engine.py should contain:
from blockchain.core.models import LucidBlock, LucidTransaction
from blockchain.core.blockchain import LucidBlockchain

class BlockchainEngine:
    def __init__(self):
        self.blockchain = LucidBlockchain()
        # No TRON services
    
    def create_block(self, transactions):
        # Core block creation logic only
        # No TRON dependencies
        pass
    
    def validate_block(self, block):
        # Core block validation logic only
        # No TRON dependencies
        pass
    
    def add_transaction(self, transaction):
        # Core transaction addition logic only
        # No TRON dependencies
        pass
```

## Testing

### 1. Import Test
```bash
cd blockchain/core
python -c "from blockchain_engine import BlockchainEngine; print('BlockchainEngine imports successfully')"
```

### 2. Functionality Test
```bash
# Test core engine operations
python -c "
from blockchain_engine import BlockchainEngine
engine = BlockchainEngine()
# Test basic functionality without TRON dependencies
print('Core blockchain engine functionality accessible')
"
```

### 3. Integration Test
```bash
# Ensure engine integrates with blockchain core
python -c "
from blockchain_engine import BlockchainEngine
from blockchain.core.models import LucidBlock, LucidTransaction
engine = BlockchainEngine()
print('Engine integration successful')
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
4. Check for TRON in method names

### If Engine Doesn't Work
1. Verify blockchain core functionality is intact
2. Check that TRON engine logic has been moved to payment-systems/
3. Ensure no critical engine functionality was accidentally removed

## Success Criteria

### Must Complete
- [ ] Zero TRON references found in file
- [ ] All TRON client initialization removed
- [ ] All TRON payout monitoring removed
- [ ] All TRON transaction handling removed
- [ ] File imports without errors
- [ ] Core blockchain engine functionality preserved
- [ ] Engine only manages lucid_blocks operations

### Verification Commands
```bash
# Final verification
grep -i "tron" blockchain/core/blockchain_engine.py
# Should return: (no matches)

# Test import
python -c "from blockchain.core.blockchain_engine import BlockchainEngine"
# Should return: (no errors)

# Test functionality
python -c "from blockchain.core.blockchain_engine import BlockchainEngine; engine = BlockchainEngine()"
# Should return: (no errors)
```

## Next Steps
After completing this cleanup, proceed to Step 7: Clean blockchain/core/__init__.py

## Rollback Plan
If issues are encountered:
```bash
# Restore from backup
cp blockchain/core/blockchain_engine.py.backup blockchain/core/blockchain_engine.py
```

## References
- Critical Cleanup Plan: `critical-cleanup-plan.plan.md`
- BUILD_REQUIREMENTS_GUIDE.md - TRON isolation requirements
- Lucid Blocks Architecture - Core blockchain functionality
- TRON Payment Cluster Guide - Payment system architecture
