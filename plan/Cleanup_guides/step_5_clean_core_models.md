# Step 5: Clean blockchain/core/models.py

## Overview
**Priority**: CRITICAL  
**Violations**: 8 TRON references  
**File**: `blockchain/core/models.py`  
**Purpose**: Remove TRON payout models and ensure models only contain blockchain core data structures.

## Pre-Cleanup Actions

### 1. Backup Current File
```bash
# Create backup before modifications
cp blockchain/core/models.py blockchain/core/models.py.backup
```

### 2. Identify TRON References
```bash
# Search for TRON references in the file
grep -n "tron\|TRON" blockchain/core/models.py
```

### 3. Document Current TRON Models
Before removal, document any TRON model structures that need to be moved to `payment-systems/tron/`.

## Cleanup Actions

### 1. Remove TRON Payout Models
**Target**: All TRON-specific model definitions

**Examples of what to remove**:
```python
# Remove TRON payout models
class TronPayout(BaseModel):
    id: str
    user_id: str
    amount: float
    tron_address: str
    status: str
    created_at: datetime
    updated_at: datetime

class TronTransaction(BaseModel):
    id: str
    tron_address: str
    amount: float
    transaction_hash: str
    block_number: int
    status: str

class TronAddress(BaseModel):
    id: str
    address: str
    private_key: str
    public_key: str
    is_active: bool
```

### 2. Clean Up TRON-Specific Fields
**Target**: All TRON-related field definitions

**Examples of what to remove**:
```python
# Remove TRON-specific fields from existing models
class User(BaseModel):
    id: str
    username: str
    email: str
    # REMOVE THESE TRON FIELDS:
    tron_address: Optional[str] = None
    tron_balance: Optional[float] = None
    tron_payout_enabled: bool = False
```

### 3. Remove TRON Validation Functions
**Target**: All TRON-specific validation logic

**Examples of what to remove**:
```python
# Remove TRON validation functions
def validate_tron_address(address: str) -> bool:
    # TRON address validation logic
    pass

def validate_tron_transaction(transaction_data: dict) -> bool:
    # TRON transaction validation logic
    pass

def format_tron_amount(amount: float) -> str:
    # TRON amount formatting logic
    pass
```

### 4. Ensure Models Only Contain Blockchain Core Data Structures
**Target**: Models should only contain lucid_blocks related structures

**Required**: Models should only contain:
- Lucid blockchain data structures
- Core blockchain models
- No payment processing models

## Specific Code Changes

### Remove TRON Model Classes
```python
# REMOVE THESE MODEL CLASSES:
class TronPayout(BaseModel):
    # Remove entire class

class TronTransaction(BaseModel):
    # Remove entire class

class TronAddress(BaseModel):
    # Remove entire class

class TronWallet(BaseModel):
    # Remove entire class
```

### Remove TRON Fields from Existing Models
```python
# REMOVE TRON FIELDS FROM EXISTING MODELS:
class User(BaseModel):
    id: str
    username: str
    email: str
    # REMOVE THESE FIELDS:
    # tron_address: Optional[str] = None
    # tron_balance: Optional[float] = None
    # tron_payout_enabled: bool = False
```

### Remove TRON Validation Functions
```python
# REMOVE THESE FUNCTIONS:
def validate_tron_address(address: str) -> bool:
    # Remove entire function

def validate_tron_transaction(transaction_data: dict) -> bool:
    # Remove entire function

def format_tron_amount(amount: float) -> str:
    # Remove entire function

def get_tron_balance(address: str) -> float:
    # Remove entire function
```

## Move Valid TRON Models to payment-systems/tron/

### Before Removal, Check for Valid Models
If any TRON models are still needed, move them to:
- `payment-systems/tron/tron_models.py`
- `payment-systems/tron/tron_schemas.py`

### Example of Models to Move
```python
# If these models exist and are needed, move to payment-systems/tron/:
class TronPayout(BaseModel):
    # Move to payment-systems/tron/tron_models.py
    pass

class TronTransaction(BaseModel):
    # Move to payment-systems/tron/tron_models.py
    pass
```

## Ensure Core Blockchain Models Remain

### Required Core Models
```python
# ENSURE THESE CORE MODELS REMAIN:
class LucidBlock(BaseModel):
    id: str
    block_number: int
    previous_hash: str
    merkle_root: str
    timestamp: datetime
    nonce: int
    hash: str

class LucidTransaction(BaseModel):
    id: str
    from_address: str
    to_address: str
    amount: float
    timestamp: datetime
    signature: str

class LucidWallet(BaseModel):
    id: str
    address: str
    public_key: str
    is_active: bool
```

## Validation Steps

### 1. Verify TRON References Removed
```bash
# Check for any remaining TRON references
grep -i "tron" blockchain/core/models.py
# Should return no results
```

### 2. Test Model Functionality
```bash
# Ensure models still work
python -c "
from blockchain.core.models import LucidBlock, LucidTransaction
print('Core models import successfully')
"
```

### 3. Verify No TRON Dependencies
```bash
# Check that no TRON modules are imported
python -c "
import ast
import sys
with open('blockchain/core/models.py', 'r') as f:
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
- [ ] Zero TRON references in models.py
- [ ] All TRON payout models removed
- [ ] All TRON-specific fields removed
- [ ] All TRON validation functions removed
- [ ] Models only contain blockchain core data structures
- [ ] File imports successfully without TRON dependencies
- [ ] Core blockchain models preserved

### File Structure After Cleanup
```python
# blockchain/core/models.py should contain:
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class LucidBlock(BaseModel):
    # Core blockchain block model
    pass

class LucidTransaction(BaseModel):
    # Core blockchain transaction model
    pass

class LucidWallet(BaseModel):
    # Core blockchain wallet model
    pass

# No TRON models
# No TRON fields
# No TRON validation functions
```

## Testing

### 1. Import Test
```bash
cd blockchain/core
python -c "from models import LucidBlock, LucidTransaction; print('Core models import successfully')"
```

### 2. Model Creation Test
```bash
# Test core model creation
python -c "
from models import LucidBlock, LucidTransaction
block = LucidBlock(id='test', block_number=1, previous_hash='0', merkle_root='0', timestamp='2023-01-01T00:00:00', nonce=0, hash='0')
print('Core models create successfully')
"
```

### 3. Integration Test
```bash
# Ensure models integrate with blockchain core
python -c "
from models import LucidBlock, LucidTransaction
from blockchain.core.blockchain_engine import BlockchainEngine
print('Model integration successful')
"
```

## Troubleshooting

### If Import Errors Occur
1. Check for missing pydantic dependencies
2. Verify core model dependencies are accessible
3. Ensure no circular imports

### If TRON References Persist
1. Search for case variations: `Tron`, `TRON`, `tron`
2. Check for partial matches in comments
3. Verify all string literals are clean
4. Check for TRON in field names

### If Models Don't Work
1. Verify core blockchain functionality is intact
2. Check that TRON models have been moved to payment-systems/
3. Ensure no critical model functionality was accidentally removed

## Success Criteria

### Must Complete
- [ ] Zero TRON references found in file
- [ ] All TRON payout models removed
- [ ] All TRON-specific fields removed
- [ ] All TRON validation functions removed
- [ ] File imports without errors
- [ ] Core blockchain models preserved
- [ ] No payment processing models in core

### Verification Commands
```bash
# Final verification
grep -i "tron" blockchain/core/models.py
# Should return: (no matches)

# Test import
python -c "from blockchain.core.models import LucidBlock, LucidTransaction"
# Should return: (no errors)

# Test model creation
python -c "from blockchain.core.models import LucidBlock; block = LucidBlock(id='test', block_number=1, previous_hash='0', merkle_root='0', timestamp='2023-01-01T00:00:00', nonce=0, hash='0')"
# Should return: (no errors)
```

## Next Steps
After completing this cleanup, proceed to Step 6: Clean blockchain/core/blockchain_engine.py

## Rollback Plan
If issues are encountered:
```bash
# Restore from backup
cp blockchain/core/models.py.backup blockchain/core/models.py
```

## References
- Critical Cleanup Plan: `critical-cleanup-plan.plan.md`
- BUILD_REQUIREMENTS_GUIDE.md - TRON isolation requirements
- Lucid Blocks Architecture - Core blockchain functionality
- TRON Payment Cluster Guide - Payment system architecture
