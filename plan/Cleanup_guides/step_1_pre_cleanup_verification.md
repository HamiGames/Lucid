# Step 1: Pre-Cleanup Verification Guide

## Overview
**Priority**: CRITICAL  
**Estimated Time**: 15 minutes  
**Purpose**: Establish baseline before cleanup to measure progress and document current TRON isolation violations.

## Files to Execute

### 1. Run TRON Isolation Verification Script
```bash
# Navigate to project root
cd /path/to/Lucid

# Execute shell verification script
./scripts/verification/verify-tron-isolation.sh
```

### 2. Run Python Verification Script
```bash
# Execute Python verification script
python scripts/verification/verify-tron-isolation.py
```

### 3. Document Current Baseline
- Record current violation count (expected: 149 violations)
- Document which files contain TRON references
- Create baseline compliance report

## Expected Results

### Baseline Metrics
- **Total Violations**: 149 TRON references
- **Files Affected**: 7 files requiring cleanup
- **Compliance Score**: 0% (before cleanup)
- **Risk Level**: HIGH

### Files with TRON Violations
1. `blockchain/api/app/routes/chain.py` - 2 violations
2. `blockchain/blockchain_anchor.py` - 67 violations (HIGHEST)
3. `blockchain/deployment/contract_deployment.py` - 25 violations
4. `blockchain/core/models.py` - 8 violations
5. `blockchain/core/blockchain_engine.py` - 34 violations
6. `blockchain/core/__init__.py` - 1 violation
7. `blockchain/__init__.py` - 12 violations

## Validation Steps

### 1. Generate Initial Compliance Report
```bash
# Run verification and capture output
./scripts/verification/verify-tron-isolation.sh > baseline_report.txt 2>&1
python scripts/verification/verify-tron-isolation.py >> baseline_report.txt 2>&1
```

### 2. Document Current State
- Save current git state: `git tag pre-tron-cleanup`
- Create backup of critical files
- Document current architecture state

### 3. Verify Script Availability
Ensure the following scripts exist and are executable:
- `scripts/verification/verify-tron-isolation.sh`
- `scripts/verification/verify-tron-isolation.py`
- `tests/isolation/test_tron_isolation.py`

## Success Criteria

### Must Complete
- [ ] Both verification scripts execute successfully
- [ ] Baseline report generated showing 149 violations
- [ ] Current git state tagged as `pre-tron-cleanup`
- [ ] All 7 affected files identified and documented
- [ ] Compliance score recorded as 0%

### Documentation Required
- [ ] Baseline violation report saved
- [ ] Git tag created for rollback capability
- [ ] Current architecture state documented
- [ ] Verification script outputs captured

## Troubleshooting

### If Scripts Don't Exist
```bash
# Create verification scripts if missing
mkdir -p scripts/verification
# Create basic verification script
cat > scripts/verification/verify-tron-isolation.sh << 'EOF'
#!/bin/bash
echo "TRON Isolation Verification"
echo "=========================="
echo "Searching for TRON references in blockchain/ directory..."
grep -r "tron\|TRON" blockchain/ --include="*.py" | wc -l
EOF
chmod +x scripts/verification/verify-tron-isolation.sh
```

### If Python Script Missing
```bash
# Create Python verification script
cat > scripts/verification/verify-tron-isolation.py << 'EOF'
#!/usr/bin/env python3
import os
import re
import glob

def find_tron_references():
    violations = 0
    files_with_violations = []
    
    for root, dirs, files in os.walk('blockchain'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        tron_matches = re.findall(r'tron|TRON', content, re.IGNORECASE)
                        if tron_matches:
                            violations += len(tron_matches)
                            files_with_violations.append((filepath, len(tron_matches)))
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    print(f"Total TRON violations found: {violations}")
    print(f"Files with violations: {len(files_with_violations)}")
    for filepath, count in files_with_violations:
        print(f"  {filepath}: {count} violations")
    
    return violations, files_with_violations

if __name__ == "__main__":
    violations, files = find_tron_references()
    exit(0 if violations == 0 else 1)
EOF
chmod +x scripts/verification/verify-tron-isolation.py
```

## Next Steps
After completing this verification step, proceed to Step 2: Clean blockchain/api/app/routes/chain.py

## Rollback Plan
If issues are encountered:
```bash
# Return to pre-cleanup state
git checkout pre-tron-cleanup
```

## References
- Critical Cleanup Plan: `critical-cleanup-plan.plan.md`
- BUILD_REQUIREMENTS_GUIDE.md - Step 28 specifications
- TRON Payment Cluster Guide - Architecture requirements
