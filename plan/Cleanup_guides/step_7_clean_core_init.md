# Step 7: Clean blockchain/core/__init__.py

## Overview
**Priority**: CRITICAL  
**Violations**: 1 TRON reference  
**File**: `blockchain/core/__init__.py`  
**Purpose**: Remove TRON-related imports and ensure clean module initialization.

## Pre-Cleanup Actions

### 1. Backup Current File
```bash
# Create backup before modifications
cp blockchain/core/__init__.py blockchain/core/__init__.py.backup
```

### 2. Identify TRON References
```bash
# Search for TRON references in the file
grep -n "tron\|TRON" blockchain/core/__init__.py
```

### 3. Document Current TRON Exports
Before removal, document any TRON-related exports that need to be moved to `payment-systems/tron/`.

## Cleanup Actions

### 1. Remove TRON-Related Imports
**Target**: All TRON import statements

**Examples of what to remove**:
```python
# Remove TRON imports
from .tron_client import TronClient
from .tron_models import TronTransaction, TronAddress
from .tron_utils import TronUtils
from .tron_engine import TronEngine
```

### 2. Clean Up TRON Exports
**Target**: All TRON-related exports in __all__ list

**Examples of what to remove**:
```python
# Remove TRON exports from __all__
__all__ = [
    'BlockchainEngine',
    'LucidBlock',
    'LucidTransaction',
    # REMOVE THESE TRON EXPORTS:
    # 'TronClient',
    # 'TronTransaction',
    # 'TronAddress',
    # 'TronUtils',
    # 'TronEngine'
]
```

### 3. Ensure Clean Module Initialization
**Target**: Module should only export core blockchain functionality

**Required**: Module should only contain:
- Core blockchain engine exports
- Core blockchain model exports
- No payment processing exports

## Specific Code Changes

### Remove TRON Imports
```python
# REMOVE THESE IMPORTS:
from .tron_client import TronClient
from .tron_models import TronTransaction, TronAddress
from .tron_utils import TronUtils
from .tron_engine import TronEngine
from .tron_network import TronNetwork
```

### Remove TRON Exports
```python
# REMOVE TRON EXPORTS FROM __all__:
__all__ = [
    'BlockchainEngine',
    'LucidBlock',
    'LucidTransaction',
    'LucidWallet',
    # REMOVE THESE:
    # 'TronClient',
    # 'TronTransaction',
    # 'TronAddress',
    # 'TronUtils',
    # 'TronEngine',
    # 'TronNetwork'
]
```

### Remove TRON Initialization
```python
# REMOVE TRON INITIALIZATION CODE:
# tron_client = TronClient()
# tron_engine = TronEngine()
# tron_network = TronNetwork()
```

## Ensure Core Blockchain Exports Remain

### Required Core Exports
```python
# ENSURE THESE CORE EXPORTS REMAIN:
from .blockchain_engine import BlockchainEngine
from .models import LucidBlock, LucidTransaction, LucidWallet
from .blockchain import LucidBlockchain

__all__ = [
    'BlockchainEngine',
    'LucidBlock',
    'LucidTransaction',
    'LucidWallet',
    'LucidBlockchain'
]
```

## Validation Steps

### 1. Verify TRON References Removed
```bash
# Check for any remaining TRON references
grep -i "tron" blockchain/core/__init__.py
# Should return no results
```

### 2. Test Module Import
```bash
# Ensure module imports successfully
python -c "
from blockchain.core import BlockchainEngine, LucidBlock, LucidTransaction
print('Core module imports successfully')
"
```

### 3. Verify No TRON Dependencies
```bash
# Check that no TRON modules are imported
python -c "
import ast
import sys
with open('blockchain/core/__init__.py', 'r') as f:
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
- [ ] Zero TRON references in __init__.py
- [ ] All TRON-related imports removed
- [ ] All TRON exports removed
- [ ] Module imports successfully without TRON dependencies
- [ ] Core blockchain functionality preserved
- [ ] Clean module initialization

### File Structure After Cleanup
```python
# blockchain/core/__init__.py should contain:
from .blockchain_engine import BlockchainEngine
from .models import LucidBlock, LucidTransaction, LucidWallet
from .blockchain import LucidBlockchain

__all__ = [
    'BlockchainEngine',
    'LucidBlock',
    'LucidTransaction',
    'LucidWallet',
    'LucidBlockchain'
]

# No TRON imports
# No TRON exports
# No TRON initialization
```

## Testing

### 1. Import Test
```bash
cd blockchain/core
python -c "from __init__ import *; print('Core module imports successfully')"
```

### 2. Export Test
```bash
# Test that core exports are available
python -c "
from blockchain.core import BlockchainEngine, LucidBlock, LucidTransaction
engine = BlockchainEngine()
block = LucidBlock(id='test', block_number=1, previous_hash='0', merkle_root='0', timestamp='2023-01-01T00:00:00', nonce=0, hash='0')
print('Core exports work correctly')
"
```

### 3. Integration Test
```bash
# Ensure core module integrates with blockchain
python -c "
from blockchain.core import BlockchainEngine, LucidBlock
from blockchain.core.blockchain_engine import BlockchainEngine as Engine
print('Core module integration successful')
"
```

## Troubleshooting

### If Import Errors Occur
1. Check for missing core module dependencies
2. Verify blockchain core modules are accessible
3. Ensure no circular imports

### If TRON References Persist
1. Search for case variations: `Tron`, `TRON`, `tron`
2. Check for partial matches in comments
3. Verify all string literals are clean
4. Check for TRON in export names

### If Module Doesn't Work
1. Verify blockchain core functionality is intact
2. Check that TRON exports have been moved to payment-systems/
3. Ensure no critical module functionality was accidentally removed

## Success Criteria

### Must Complete
- [ ] Zero TRON references found in file
- [ ] All TRON-related imports removed
- [ ] All TRON exports removed
- [ ] File imports without errors
- [ ] Core blockchain functionality preserved
- [ ] Clean module initialization

### Verification Commands
```bash
# Final verification
grep -i "tron" blockchain/core/__init__.py
# Should return: (no matches)

# Test import
python -c "from blockchain.core import BlockchainEngine, LucidBlock, LucidTransaction"
# Should return: (no errors)

# Test exports
python -c "from blockchain.core import *; print('All exports available')"
# Should return: (no errors)
```

## Next Steps
After completing this cleanup, proceed to Step 8: Clean blockchain/__init__.py

## Rollback Plan
If issues are encountered:
```bash
# Restore from backup
cp blockchain/core/__init__.py.backup blockchain/core/__init__.py
```

## References
- Critical Cleanup Plan: `critical-cleanup-plan.plan.md`
- BUILD_REQUIREMENTS_GUIDE.md - TRON isolation requirements
- Lucid Blocks Architecture - Core blockchain functionality
- TRON Payment Cluster Guide - Payment system architecture
