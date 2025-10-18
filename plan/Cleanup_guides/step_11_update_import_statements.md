# Step 11: Update Import Statements Project-Wide

## Overview
**Priority**: HIGH  
**Estimated Time**: 30 minutes  
**Purpose**: Search for any remaining TRON imports in non-payment directories and update documentation to reflect correct architecture.

## Pre-Update Actions

### 1. Search for Remaining TRON Imports
```bash
# Search for TRON imports in non-payment directories
grep -r "from.*tron\|import.*tron" . --include="*.py" --exclude-dir=payment-systems
```

### 2. Document Current Import Structure
Before updates, document any remaining TRON imports that need to be addressed.

## Update Actions

### 1. Search for TRON Imports in Non-Payment Directories
**Target**: Find any remaining TRON imports outside payment-systems/

**Search Commands**:
```bash
# Search for TRON imports in blockchain/
grep -r "from.*tron\|import.*tron" blockchain/ --include="*.py"

# Search for TRON imports in api/
grep -r "from.*tron\|import.*tron" api/ --include="*.py"

# Search for TRON imports in other directories
grep -r "from.*tron\|import.*tron" . --include="*.py" --exclude-dir=payment-systems --exclude-dir=blockchain
```

### 2. Update Documentation to Reflect Correct Architecture
**Target**: Update documentation to show clean TRON isolation

**Files to Update**:
- `plan/api_build_prog/step28_tron_isolation_verification_completion.md`
- `BUILD_REQUIREMENTS_GUIDE.md`
- `README.md`
- Any other documentation files

**Update Actions**:
```bash
# Update step28 completion document
# Add post-cleanup verification results
# Update compliance scores
# Document cleanup actions taken

# Update BUILD_REQUIREMENTS_GUIDE.md
# Remove TRON references from blockchain requirements
# Update architecture diagrams
# Clarify TRON isolation requirements

# Update README.md
# Update architecture overview
# Update installation instructions
# Update service descriptions
```

### 3. Ensure API Gateway Routes Correctly to Isolated TRON Services
**Target**: Verify API Gateway configuration points to correct services

**Files to Check**:
- `api/gateway/routes.py`
- `api/gateway/middleware.py`
- `api/gateway/config.py`

**Verification Commands**:
```bash
# Check API Gateway routes
grep -r "TRON_PAYMENT_URL\|tron_payment" api/gateway/
grep -r "BLOCKCHAIN_CORE_URL\|blockchain_core" api/gateway/

# Verify route configurations
python -c "
from api.gateway.routes import *
print('API Gateway routes accessible')
"
```

## Specific Update Actions

### 1. Remove TRON Imports from Non-Payment Directories
**Target**: Clean up any remaining TRON imports

**Examples of what to remove**:
```python
# Remove TRON imports from blockchain/
from tron_client import TronClient
from tron_payment_service import TronPaymentService

# Remove TRON imports from api/
from tron_network import TronNetwork
from tron_utils import TronUtils
```

### 2. Update Import Statements to Use Correct Services
**Target**: Update imports to use isolated TRON services

**Examples of what to update**:
```python
# Update API Gateway imports
from payment_systems.tron.tron_client import TronClient
from payment_systems.tron.tron_payment_service import TronPaymentService

# Update blockchain imports
from blockchain.core.blockchain_engine import BlockchainEngine
from blockchain.core.models import LucidBlock
```

### 3. Update Documentation References
**Target**: Update all documentation to reflect clean architecture

**Examples of what to update**:
```markdown
# Update architecture diagrams
# Remove TRON references from blockchain core
# Add TRON isolation diagrams
# Update service descriptions
```

## Validation Steps

### 1. Verify No TRON Imports in Non-Payment Directories
```bash
# Check for remaining TRON imports
grep -r "from.*tron\|import.*tron" . --include="*.py" --exclude-dir=payment-systems
# Should return no results
```

### 2. Test Updated Import Statements
```bash
# Test API Gateway imports
python -c "
from api.gateway.routes import *
print('API Gateway routes updated successfully')
"

# Test blockchain imports
python -c "
from blockchain.core.blockchain_engine import BlockchainEngine
print('Blockchain imports updated successfully')
"
```

### 3. Verify Documentation Updates
```bash
# Check updated documentation
grep -r "TRON.*blockchain\|blockchain.*TRON" plan/ docs/ README.md
# Should return no results
```

## Expected Results

### After Updates
- [ ] No TRON imports in non-payment directories
- [ ] All imports use correct service paths
- [ ] Documentation updated to reflect clean architecture
- [ ] API Gateway routes correctly to isolated services
- [ ] No cross-contamination between systems

### Import Structure After Updates
```python
# API Gateway should import from:
from payment_systems.tron.tron_client import TronClient
from payment_systems.tron.tron_payment_service import TronPaymentService

# Blockchain should import from:
from blockchain.core.blockchain_engine import BlockchainEngine
from blockchain.core.models import LucidBlock, LucidTransaction
```

## Testing

### 1. Import Test
```bash
# Test all updated imports
python -c "
from api.gateway.routes import *
from blockchain.core.blockchain_engine import BlockchainEngine
from payment_systems.tron.tron_client import TronClient
print('All imports updated successfully')
"
```

### 2. Functionality Test
```bash
# Test API Gateway functionality
python -c "
from api.gateway.routes import *
# Test route registration
print('API Gateway routes functional')
"
```

### 3. Integration Test
```bash
# Test system integration
python -c "
from api.gateway.routes import *
from blockchain.core.blockchain_engine import BlockchainEngine
from payment_systems.tron.tron_client import TronClient
print('System integration successful')
"
```

## Troubleshooting

### If TRON Imports Still Exist
1. Check for case variations: `Tron`, `TRON`, `tron`
2. Verify all files were updated
3. Check for partial matches in comments

### If Import Errors Occur
1. Check for missing dependencies
2. Verify service paths are correct
3. Ensure no circular imports

### If Documentation Is Outdated
1. Update all documentation files
2. Verify architecture diagrams
3. Check service descriptions

## Success Criteria

### Must Complete
- [ ] No TRON imports in non-payment directories
- [ ] All imports use correct service paths
- [ ] Documentation updated to reflect clean architecture
- [ ] API Gateway routes correctly to isolated services
- [ ] No cross-contamination between systems

### Verification Commands
```bash
# Final verification
grep -r "from.*tron\|import.*tron" . --include="*.py" --exclude-dir=payment-systems
# Should return: (no matches)

# Test imports
python -c "from api.gateway.routes import *; from blockchain.core.blockchain_engine import BlockchainEngine; from payment_systems.tron.tron_client import TronClient"
# Should return: (no errors)
```

## Next Steps
After completing this update, proceed to Step 12: Verify Network Isolation

## Rollback Plan
If issues are encountered:
```bash
# Return to pre-cleanup state
git checkout pre-tron-cleanup
```

## References
- Critical Cleanup Plan: `critical-cleanup-plan.plan.md`
- BUILD_REQUIREMENTS_GUIDE.md - TRON isolation requirements
- TRON Payment Cluster Guide - Payment system architecture
- Lucid Blocks Architecture - Core blockchain functionality
