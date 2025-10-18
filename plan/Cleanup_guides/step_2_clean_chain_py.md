# Step 2: Clean blockchain/api/app/routes/chain.py

## Overview
**Priority**: CRITICAL  
**Violations**: 2 TRON references  
**File**: `blockchain/api/app/routes/chain.py`  
**Purpose**: Remove all TRON references from blockchain chain routes to ensure TRON isolation compliance.

## Pre-Cleanup Actions

### 1. Backup Current File
```bash
# Create backup before modifications
cp blockchain/api/app/routes/chain.py blockchain/api/app/routes/chain.py.backup
```

### 2. Identify TRON References
```bash
# Search for TRON references in the file
grep -n "tron\|TRON" blockchain/api/app/routes/chain.py
```

## Cleanup Actions

### 1. Remove Commented TRON Imports
**Target**: Any commented import statements containing TRON references

**Example of what to remove**:
```python
# from tron_payment_service import TronPaymentService
# import tron_client
```

**Action**: Delete all lines containing commented TRON imports.

### 2. Clean Up TRON Service References
**Target**: Any references to TRON services in route handlers

**Example of what to remove**:
```python
# tron_service = TronPaymentService()
# tron_client = TronClient()
```

**Action**: Remove all TRON service instantiations and references.

### 3. Ensure Blockchain Operations Reference Only Lucid Blocks
**Target**: Verify all blockchain operations use lucid_blocks

**Required**: All blockchain operations should reference:
- `lucid_blocks` instead of any TRON-specific implementations
- Core blockchain functionality only
- No payment processing logic (moved to payment-systems/)

## Specific Code Changes

### Remove TRON Import Comments
```python
# REMOVE THESE LINES:
# from tron_payment_service import TronPaymentService
# from tron_client import TronClient
# import tron_utils
```

### Remove TRON Service References
```python
# REMOVE THESE PATTERNS:
# tron_service = TronPaymentService()
# tron_client = TronClient()
# tron_payment = tron_service.process_payment()
```

### Ensure Clean Route Handlers
```python
# ENSURE ROUTES ONLY CONTAIN:
from blockchain.core.blockchain_engine import BlockchainEngine
from blockchain.core.models import LucidBlock

# Route handlers should only use:
# - BlockchainEngine for core operations
# - LucidBlock models
# - No payment processing logic
```

## Validation Steps

### 1. Verify TRON References Removed
```bash
# Check for any remaining TRON references
grep -i "tron" blockchain/api/app/routes/chain.py
# Should return no results
```

### 2. Test Route Functionality
```bash
# Ensure routes still work without TRON dependencies
python -c "from blockchain.api.app.routes.chain import *; print('Import successful')"
```

### 3. Verify Import Dependencies
```bash
# Check that no TRON modules are imported
python -c "
import ast
import sys
with open('blockchain/api/app/routes/chain.py', 'r') as f:
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
- [ ] Zero TRON references in chain.py
- [ ] All commented TRON imports removed
- [ ] All TRON service references removed
- [ ] Routes only reference lucid_blocks
- [ ] File imports successfully without TRON dependencies
- [ ] All blockchain operations use core blockchain functionality only

### File Structure After Cleanup
```python
# blockchain/api/app/routes/chain.py should contain:
from blockchain.core.blockchain_engine import BlockchainEngine
from blockchain.core.models import LucidBlock
from flask import Blueprint, request, jsonify

# Route handlers for blockchain operations only
# No payment processing logic
# No TRON service references
```

## Testing

### 1. Import Test
```bash
cd blockchain/api/app/routes
python -c "import chain; print('Chain module imports successfully')"
```

### 2. Route Test
```bash
# Test that routes can be registered without TRON dependencies
python -c "
from chain import chain_bp
print('Chain blueprint created successfully')
"
```

### 3. Functionality Test
```bash
# Ensure core blockchain operations still work
python -c "
from blockchain.core.blockchain_engine import BlockchainEngine
engine = BlockchainEngine()
print('Blockchain engine accessible')
"
```

## Troubleshooting

### If Import Errors Occur
1. Check for missing dependencies
2. Verify blockchain core modules are accessible
3. Ensure no circular imports

### If TRON References Persist
1. Search for case variations: `Tron`, `TRON`, `tron`
2. Check for partial matches in comments
3. Verify all string literals are clean

### If Routes Don't Work
1. Verify blockchain core functionality is intact
2. Check that payment logic has been moved to payment-systems/
3. Ensure no critical functionality was accidentally removed

## Success Criteria

### Must Complete
- [ ] Zero TRON references found in file
- [ ] All commented TRON imports removed
- [ ] All TRON service references removed
- [ ] File imports without errors
- [ ] Routes register successfully
- [ ] Core blockchain functionality preserved

### Verification Commands
```bash
# Final verification
grep -i "tron" blockchain/api/app/routes/chain.py
# Should return: (no matches)

# Test import
python -c "from blockchain.api.app.routes.chain import *"
# Should return: (no errors)
```

## Next Steps
After completing this cleanup, proceed to Step 3: Clean blockchain/blockchain_anchor.py

## Rollback Plan
If issues are encountered:
```bash
# Restore from backup
cp blockchain/api/app/routes/chain.py.backup blockchain/api/app/routes/chain.py
```

## References
- Critical Cleanup Plan: `critical-cleanup-plan.plan.md`
- BUILD_REQUIREMENTS_GUIDE.md - TRON isolation requirements
- Lucid Blocks Architecture - Core blockchain functionality
