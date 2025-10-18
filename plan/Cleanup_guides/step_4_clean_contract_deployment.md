# Step 4: Clean blockchain/deployment/contract_deployment.py

## Overview
**Priority**: CRITICAL  
**Violations**: 25 TRON references  
**File**: `blockchain/deployment/contract_deployment.py`  
**Purpose**: Remove TRON client setup code and ensure only lucid_blocks contracts are deployed.

## Pre-Cleanup Actions

### 1. Backup Current File
```bash
# Create backup before modifications
cp blockchain/deployment/contract_deployment.py blockchain/deployment/contract_deployment.py.backup
```

### 2. Identify TRON References
```bash
# Search for TRON references in the file
grep -n "tron\|TRON" blockchain/deployment/contract_deployment.py
```

### 3. Document Current TRON Functionality
Before removal, document any TRON contract deployment logic that needs to be moved to `payment-systems/tron/`.

## Cleanup Actions

### 1. Remove TRON Client Setup Code
**Target**: All TRON client initialization and configuration

**Examples of what to remove**:
```python
# Remove TRON client imports
from tron_client import TronClient
from tron_contract import TronContract
from tron_network import TronNetwork

# Remove TRON client initialization
self.tron_client = TronClient()
self.tron_network = TronNetwork()

# Remove TRON client configuration
TRON_MAINNET_URL = "https://api.trongrid.io"
TRON_TESTNET_URL = "https://api.shasta.trongrid.io"
TRON_PRIVATE_KEY = os.getenv('TRON_PRIVATE_KEY')
```

### 2. Clean Up TRON Network Configuration
**Target**: All TRON network setup and configuration

**Examples of what to remove**:
```python
# Remove TRON network configuration
def setup_tron_network(self):
    # TRON network setup logic
    pass

def configure_tron_client(self):
    # TRON client configuration logic
    pass

def initialize_tron_connection(self):
    # TRON connection initialization
    pass
```

### 3. Remove TRON Contract Deployment Logic
**Target**: All TRON-specific contract deployment code

**Examples of what to remove**:
```python
# Remove TRON contract deployment methods
def deploy_tron_contract(self, contract_data):
    # TRON contract deployment logic
    pass

def verify_tron_contract(self, contract_address):
    # TRON contract verification logic
    pass

def update_tron_contract(self, contract_address, new_data):
    # TRON contract update logic
    pass
```

### 4. Ensure Only Lucid Blocks Contracts Are Deployed
**Target**: Contract deployment should only handle lucid_blocks contracts

**Required**: Contract deployment should only reference:
- Lucid blockchain contracts
- Core contract deployment logic
- No TRON-specific contract handling

## Specific Code Changes

### Remove TRON Imports
```python
# REMOVE THESE IMPORTS:
from tron_client import TronClient
from tron_contract import TronContract
from tron_network import TronNetwork
from tron_utils import TronUtils
```

### Remove TRON Client Initialization
```python
# REMOVE FROM __init__ METHOD:
self.tron_client = TronClient()
self.tron_network = TronNetwork()
self.tron_config = TronConfig()
```

### Remove TRON Contract Methods
```python
# REMOVE ALL TRON CONTRACT METHODS:
def deploy_tron_contract(self, ...):
    # Remove entire method

def verify_tron_contract(self, ...):
    # Remove entire method

def update_tron_contract(self, ...):
    # Remove entire method

def get_tron_contract_address(self, ...):
    # Remove entire method
```

### Clean Up Configuration
```python
# REMOVE TRON CONFIGURATION:
TRON_MAINNET_URL = "https://api.trongrid.io"
TRON_TESTNET_URL = "https://api.shasta.trongrid.io"
TRON_CONTRACT_ADDRESS = os.getenv('TRON_CONTRACT_ADDRESS')
TRON_PRIVATE_KEY = os.getenv('TRON_PRIVATE_KEY')
```

## Move Valid TRON Logic to payment-systems/tron/

### Before Removal, Check for Valid Logic
If any TRON contract deployment logic is still needed, move it to:
- `payment-systems/tron/tron_contract_deployment.py`
- `payment-systems/tron/tron_client.py`
- `payment-systems/tron/contract_router.py`

### Example of Logic to Move
```python
# If this logic exists and is needed, move to payment-systems/tron/:
class TronContractDeployment:
    def deploy_contract(self, contract_data):
        # Move to payment-systems/tron/tron_contract_deployment.py
        pass

class TronClient:
    def deploy_contract(self, contract_bytecode):
        # Move to payment-systems/tron/tron_client.py
        pass
```

## Ensure Lucid Blocks Contract Deployment

### Required Contract Deployment Logic
```python
# ENSURE THESE PATTERNS REMAIN:
from blockchain.core.blockchain_engine import BlockchainEngine
from blockchain.core.models import LucidContract

class ContractDeployment:
    def __init__(self):
        self.blockchain_engine = BlockchainEngine()
        # No TRON services
    
    def deploy_lucid_contract(self, contract_data):
        # Deploy lucid_blocks contracts only
        pass
    
    def verify_lucid_contract(self, contract_address):
        # Verify lucid_blocks contracts only
        pass
```

## Validation Steps

### 1. Verify TRON References Removed
```bash
# Check for any remaining TRON references
grep -i "tron" blockchain/deployment/contract_deployment.py
# Should return no results
```

### 2. Test Contract Deployment Functionality
```bash
# Ensure contract deployment still works
python -c "
from blockchain.deployment.contract_deployment import ContractDeployment
deployment = ContractDeployment()
print('Contract deployment created successfully')
"
```

### 3. Verify No TRON Dependencies
```bash
# Check that no TRON modules are imported
python -c "
import ast
import sys
with open('blockchain/deployment/contract_deployment.py', 'r') as f:
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
- [ ] Zero TRON references in contract_deployment.py
- [ ] All TRON client setup code removed
- [ ] All TRON network configuration removed
- [ ] All TRON contract deployment logic removed
- [ ] Only lucid_blocks contracts are deployed
- [ ] File imports successfully without TRON dependencies
- [ ] Core contract deployment functionality preserved

### File Structure After Cleanup
```python
# blockchain/deployment/contract_deployment.py should contain:
from blockchain.core.blockchain_engine import BlockchainEngine
from blockchain.core.models import LucidContract

class ContractDeployment:
    def __init__(self):
        self.blockchain_engine = BlockchainEngine()
        # No TRON services
    
    def deploy_lucid_contract(self, contract_data):
        # Core contract deployment logic only
        # No TRON dependencies
        pass
    
    def verify_lucid_contract(self, contract_address):
        # Core verification logic only
        # No TRON dependencies
        pass
```

## Testing

### 1. Import Test
```bash
cd blockchain/deployment
python -c "from contract_deployment import ContractDeployment; print('ContractDeployment imports successfully')"
```

### 2. Functionality Test
```bash
# Test core contract deployment operations
python -c "
from contract_deployment import ContractDeployment
deployment = ContractDeployment()
# Test basic functionality without TRON dependencies
print('Core contract deployment functionality accessible')
"
```

### 3. Integration Test
```bash
# Ensure contract deployment integrates with blockchain core
python -c "
from contract_deployment import ContractDeployment
from blockchain.core.blockchain_engine import BlockchainEngine
deployment = ContractDeployment()
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

### If Contract Deployment Doesn't Work
1. Verify blockchain core functionality is intact
2. Check that TRON contract logic has been moved to payment-systems/
3. Ensure no critical contract deployment functionality was accidentally removed

## Success Criteria

### Must Complete
- [ ] Zero TRON references found in file
- [ ] All TRON client setup code removed
- [ ] All TRON network configuration removed
- [ ] All TRON contract deployment logic removed
- [ ] File imports without errors
- [ ] Core contract deployment functionality preserved
- [ ] Only lucid_blocks contracts are deployed

### Verification Commands
```bash
# Final verification
grep -i "tron" blockchain/deployment/contract_deployment.py
# Should return: (no matches)

# Test import
python -c "from blockchain.deployment.contract_deployment import ContractDeployment"
# Should return: (no errors)

# Test functionality
python -c "from blockchain.deployment.contract_deployment import ContractDeployment; deployment = ContractDeployment()"
# Should return: (no errors)
```

## Next Steps
After completing this cleanup, proceed to Step 5: Clean blockchain/core/models.py

## Rollback Plan
If issues are encountered:
```bash
# Restore from backup
cp blockchain/deployment/contract_deployment.py.backup blockchain/deployment/contract_deployment.py
```

## References
- Critical Cleanup Plan: `critical-cleanup-plan.plan.md`
- BUILD_REQUIREMENTS_GUIDE.md - TRON isolation requirements
- Lucid Blocks Architecture - Core blockchain functionality
- TRON Payment Cluster Guide - Payment system architecture
