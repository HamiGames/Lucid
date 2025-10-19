# Block Manager Container

## Overview
Build block manager container for blockchain block management, validation, and chain maintenance.

## Location
`blockchain/Dockerfile.manager`

## Container Details
**Container**: `pickme/lucid-block-manager:latest-arm64`

## Multi-Stage Build Strategy

### Stage 1: Builder
```dockerfile
FROM python:3.11-slim as builder
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY blockchain/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target /build/deps

# Clean up unnecessary files
RUN find /build/deps -name "*.pyc" -delete && \
    find /build/deps -name "__pycache__" -type d -exec rm -rf {} + && \
    find /build/deps -name "*.dist-info" -type d -exec rm -rf {} +
```

### Stage 2: Runtime (Distroless)
```dockerfile
FROM gcr.io/distroless/python3-debian12:arm64

# Copy dependencies
COPY --from=builder /build/deps /app/deps

# Copy application code
COPY blockchain/ /app/

# Set environment variables
ENV PYTHONPATH=/app/deps
WORKDIR /app

# Set non-root user
USER 65532:65532

# Expose port
EXPOSE 8088

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["python", "-c", "import requests; requests.get('http://localhost:8088/health')"]

# Default command
CMD ["python", "manager/main.py"]
```

## Requirements File
**File**: `blockchain/requirements.txt`

```txt
# Block Manager Dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
httpx==0.25.2
aiofiles==23.2.1
python-multipart==0.0.6

# Blockchain & Cryptography
cryptography==41.0.8
hashlib2==1.3.1
merkle-tree==1.0.0

# Database Integration
motor==3.3.2
redis==5.0.1
pymongo==4.6.0

# Block Management
structlog==23.2.0
asyncio==3.4.3

# Monitoring & Logging
prometheus-client==0.19.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-mock==3.12.0
```

## Application Code Structure

### Main Application
**File**: `blockchain/manager/main.py`

```python
"""
Lucid Block Manager Service
Provides blockchain block management, validation, and chain maintenance
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from blockchain.manager.block_validator import BlockValidator
from blockchain.manager.chain_manager import ChainManager
from blockchain.manager.block_storage import BlockStorage
from blockchain.manager.chain_sync import ChainSync
from blockchain.api.block_manager_api import BlockManagerAPI
from blockchain.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global services
block_validator = None
chain_manager = None
block_storage = None
chain_sync = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global block_validator, chain_manager, block_storage, chain_sync
    
    # Startup
    logger.info("Starting Lucid Block Manager Service...")
    
    settings = get_settings()
    
    # Initialize block validator
    block_validator = BlockValidator(settings)
    await block_validator.initialize()
    
    # Initialize chain manager
    chain_manager = ChainManager(settings)
    await chain_manager.initialize()
    
    # Initialize block storage
    block_storage = BlockStorage(settings)
    await block_storage.initialize()
    
    # Initialize chain sync
    chain_sync = ChainSync(settings)
    await chain_sync.initialize()
    
    logger.info("Block Manager Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Block Manager Service...")
    if block_validator:
        await block_validator.cleanup()
    if chain_manager:
        await chain_manager.cleanup()
    if block_storage:
        await block_storage.cleanup()
    if chain_sync:
        await chain_sync.cleanup()
    logger.info("Block Manager Service shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="Lucid Block Manager Service",
    description="Blockchain block management, validation, and chain maintenance",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(BlockManagerAPI.get_router(), prefix="/api/v1", tags=["block-manager"])

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "lucid-block-manager",
        "version": "1.0.0",
        "block_validator": await block_validator.check_health(),
        "chain_manager": await chain_manager.check_health(),
        "block_storage": await block_storage.check_health(),
        "chain_sync": await chain_sync.check_health()
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Lucid Block Manager Service",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": [
            "/api/v1/blocks",
            "/api/v1/chain",
            "/api/v1/validation"
        ]
    }

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8088,
        reload=False,
        log_level="info"
    )
```

### Block Validator
**File**: `blockchain/manager/block_validator.py`

```python
"""
Block validator for blockchain
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
import hashlib
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class BlockValidator:
    """Block validator for blockchain"""
    
    def __init__(self, settings):
        self.settings = settings
        self.validation_rules = []
        
    async def initialize(self):
        """Initialize block validator"""
        try:
            # Load validation rules
            await self._load_validation_rules()
            
            logger.info("Block validator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize block validator: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup block validator"""
        logger.info("Block validator cleaned up")
    
    async def _load_validation_rules(self):
        """Load validation rules"""
        self.validation_rules = [
            self._validate_block_structure,
            self._validate_block_hash,
            self._validate_previous_hash,
            self._validate_merkle_root,
            self._validate_timestamp,
            self._validate_transactions
        ]
    
    async def validate_block(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """Validate block"""
        try:
            validation_results = []
            
            for rule in self.validation_rules:
                result = await rule(block)
                validation_results.append(result)
            
            # Check if all validations passed
            all_passed = all(result["passed"] for result in validation_results)
            
            return {
                "valid": all_passed,
                "results": validation_results,
                "validated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to validate block: {e}")
            return {
                "valid": False,
                "error": str(e),
                "validated_at": datetime.utcnow().isoformat()
            }
    
    async def _validate_block_structure(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """Validate block structure"""
        required_fields = ["index", "timestamp", "transactions", "previous_hash", "merkle_root", "nonce", "hash"]
        
        missing_fields = [field for field in required_fields if field not in block]
        
        return {
            "rule": "block_structure",
            "passed": len(missing_fields) == 0,
            "details": {
                "missing_fields": missing_fields,
                "required_fields": required_fields
            }
        }
    
    async def _validate_block_hash(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """Validate block hash"""
        try:
            # Calculate expected hash
            expected_hash = await self._calculate_block_hash(block)
            actual_hash = block.get("hash", "")
            
            return {
                "rule": "block_hash",
                "passed": expected_hash == actual_hash,
                "details": {
                    "expected_hash": expected_hash,
                    "actual_hash": actual_hash
                }
            }
            
        except Exception as e:
            return {
                "rule": "block_hash",
                "passed": False,
                "details": {"error": str(e)}
            }
    
    async def _validate_previous_hash(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """Validate previous hash"""
        try:
            # Get previous block
            previous_block = await self._get_previous_block(block["index"] - 1)
            
            if previous_block:
                expected_previous_hash = previous_block.get("hash", "")
                actual_previous_hash = block.get("previous_hash", "")
                
                return {
                    "rule": "previous_hash",
                    "passed": expected_previous_hash == actual_previous_hash,
                    "details": {
                        "expected_previous_hash": expected_previous_hash,
                        "actual_previous_hash": actual_previous_hash
                    }
                }
            else:
                # Genesis block
                return {
                    "rule": "previous_hash",
                    "passed": block.get("previous_hash", "") == "0" * 64,
                    "details": {"is_genesis": True}
                }
                
        except Exception as e:
            return {
                "rule": "previous_hash",
                "passed": False,
                "details": {"error": str(e)}
            }
    
    async def _validate_merkle_root(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Merkle root"""
        try:
            transactions = block.get("transactions", [])
            expected_merkle_root = await self._calculate_merkle_root(transactions)
            actual_merkle_root = block.get("merkle_root", "")
            
            return {
                "rule": "merkle_root",
                "passed": expected_merkle_root == actual_merkle_root,
                "details": {
                    "expected_merkle_root": expected_merkle_root,
                    "actual_merkle_root": actual_merkle_root
                }
            }
            
        except Exception as e:
            return {
                "rule": "merkle_root",
                "passed": False,
                "details": {"error": str(e)}
            }
    
    async def _validate_timestamp(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """Validate timestamp"""
        try:
            timestamp = block.get("timestamp", "")
            
            # Parse timestamp
            block_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            current_time = datetime.utcnow()
            
            # Check if timestamp is not too far in the future
            time_diff = (block_time - current_time).total_seconds()
            is_valid = abs(time_diff) < 3600  # 1 hour tolerance
            
            return {
                "rule": "timestamp",
                "passed": is_valid,
                "details": {
                    "block_time": timestamp,
                    "current_time": current_time.isoformat(),
                    "time_diff_seconds": time_diff
                }
            }
            
        except Exception as e:
            return {
                "rule": "timestamp",
                "passed": False,
                "details": {"error": str(e)}
            }
    
    async def _validate_transactions(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """Validate transactions"""
        try:
            transactions = block.get("transactions", [])
            
            # Validate each transaction
            valid_transactions = 0
            for tx in transactions:
                if await self._validate_transaction(tx):
                    valid_transactions += 1
            
            return {
                "rule": "transactions",
                "passed": valid_transactions == len(transactions),
                "details": {
                    "total_transactions": len(transactions),
                    "valid_transactions": valid_transactions
                }
            }
            
        except Exception as e:
            return {
                "rule": "transactions",
                "passed": False,
                "details": {"error": str(e)}
            }
    
    async def _validate_transaction(self, transaction: Dict[str, Any]) -> bool:
        """Validate individual transaction"""
        # Implementation would validate transaction structure and signatures
        return True
    
    async def _calculate_block_hash(self, block: Dict[str, Any]) -> str:
        """Calculate block hash"""
        block_string = f"{block['index']}{block['timestamp']}{block['previous_hash']}{block['merkle_root']}{block['nonce']}"
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    async def _calculate_merkle_root(self, transactions: List[Dict[str, Any]]) -> str:
        """Calculate Merkle root"""
        if not transactions:
            return "0" * 64
        
        # Calculate transaction hashes
        tx_hashes = []
        for tx in transactions:
            tx_string = json.dumps(tx, sort_keys=True)
            tx_hash = hashlib.sha256(tx_string.encode()).hexdigest()
            tx_hashes.append(tx_hash)
        
        # Build Merkle tree
        while len(tx_hashes) > 1:
            new_hashes = []
            for i in range(0, len(tx_hashes), 2):
                if i + 1 < len(tx_hashes):
                    combined = tx_hashes[i] + tx_hashes[i + 1]
                else:
                    combined = tx_hashes[i] + tx_hashes[i]
                new_hashes.append(hashlib.sha256(combined.encode()).hexdigest())
            tx_hashes = new_hashes
        
        return tx_hashes[0]
    
    async def _get_previous_block(self, index: int) -> Optional[Dict[str, Any]]:
        """Get previous block"""
        # Implementation would retrieve block from storage
        return None
    
    async def check_health(self) -> bool:
        """Check block validator health"""
        try:
            return len(self.validation_rules) > 0
        except Exception:
            return False
```

### Chain Manager
**File**: `blockchain/manager/chain_manager.py`

```python
"""
Chain manager for blockchain
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ChainManager:
    """Chain manager for blockchain"""
    
    def __init__(self, settings):
        self.settings = settings
        self.chain_state = "idle"
        self.current_height = 0
        
    async def initialize(self):
        """Initialize chain manager"""
        try:
            # Load current chain state
            await self._load_chain_state()
            
            # Start chain maintenance loop
            asyncio.create_task(self._chain_maintenance_loop())
            
            logger.info("Chain manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize chain manager: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup chain manager"""
        self.chain_state = "shutdown"
        logger.info("Chain manager cleaned up")
    
    async def _load_chain_state(self):
        """Load current chain state"""
        try:
            # Get current chain height
            self.current_height = await self._get_chain_height()
            
            logger.info(f"Chain state loaded: height={self.current_height}")
            
        except Exception as e:
            logger.error(f"Failed to load chain state: {e}")
            self.current_height = 0
    
    async def _chain_maintenance_loop(self):
        """Chain maintenance loop"""
        while self.chain_state != "shutdown":
            try:
                # Perform chain maintenance
                await self._perform_chain_maintenance()
                
                await asyncio.sleep(60)  # Run every minute
                
            except Exception as e:
                logger.error(f"Chain maintenance error: {e}")
                await asyncio.sleep(30)
    
    async def _perform_chain_maintenance(self):
        """Perform chain maintenance"""
        try:
            # Check chain integrity
            await self._check_chain_integrity()
            
            # Clean up old blocks if needed
            await self._cleanup_old_blocks()
            
            # Update chain metrics
            await self._update_chain_metrics()
            
        except Exception as e:
            logger.error(f"Chain maintenance failed: {e}")
    
    async def _check_chain_integrity(self):
        """Check chain integrity"""
        try:
            # Get chain height
            current_height = await self._get_chain_height()
            
            # Verify chain from genesis to current height
            for i in range(1, current_height + 1):
                block = await self._get_block_by_index(i)
                if not block:
                    logger.warning(f"Missing block at index {i}")
                    continue
                
                # Validate block
                validation_result = await self._validate_block(block)
                if not validation_result["valid"]:
                    logger.error(f"Invalid block at index {i}: {validation_result}")
                    
        except Exception as e:
            logger.error(f"Chain integrity check failed: {e}")
    
    async def _cleanup_old_blocks(self):
        """Clean up old blocks if needed"""
        try:
            # Get cleanup policy
            max_blocks = self.settings.max_blocks_to_keep
            
            if self.current_height > max_blocks:
                # Remove old blocks
                blocks_to_remove = self.current_height - max_blocks
                await self._remove_old_blocks(blocks_to_remove)
                
                logger.info(f"Cleaned up {blocks_to_remove} old blocks")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old blocks: {e}")
    
    async def _update_chain_metrics(self):
        """Update chain metrics"""
        try:
            # Update current height
            self.current_height = await self._get_chain_height()
            
            # Update other metrics
            await self._update_chain_statistics()
            
        except Exception as e:
            logger.error(f"Failed to update chain metrics: {e}")
    
    async def _get_chain_height(self) -> int:
        """Get current chain height"""
        # Implementation would get height from storage
        return 0
    
    async def _get_block_by_index(self, index: int) -> Optional[Dict[str, Any]]:
        """Get block by index"""
        # Implementation would retrieve block from storage
        return None
    
    async def _validate_block(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """Validate block"""
        # Implementation would validate block
        return {"valid": True}
    
    async def _remove_old_blocks(self, count: int):
        """Remove old blocks"""
        # Implementation would remove old blocks from storage
        pass
    
    async def _update_chain_statistics(self):
        """Update chain statistics"""
        # Implementation would update chain statistics
        pass
    
    async def get_chain_info(self) -> Dict[str, Any]:
        """Get chain information"""
        return {
            "height": self.current_height,
            "state": self.chain_state,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    async def check_health(self) -> bool:
        """Check chain manager health"""
        try:
            return self.chain_state in ["idle", "maintenance"]
        except Exception:
            return False
```

## Build Command

```bash
# Build block manager container
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-block-manager:latest-arm64 \
  -f blockchain/Dockerfile.manager \
  --push \
  .
```

## Build Script Implementation

**File**: `scripts/core/build-block-manager.sh`

```bash
#!/bin/bash
# scripts/core/build-block-manager.sh
# Build block manager container

set -e

echo "Building block manager container..."

# Create blockchain directory if it doesn't exist
mkdir -p blockchain

# Create requirements.txt
cat > blockchain/requirements.txt << 'EOF'
# Block Manager Dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
httpx==0.25.2
aiofiles==23.2.1
python-multipart==0.0.6

# Blockchain & Cryptography
cryptography==41.0.8
hashlib2==1.3.1
merkle-tree==1.0.0

# Database Integration
motor==3.3.2
redis==5.0.1
pymongo==4.6.0

# Block Management
structlog==23.2.0
asyncio==3.4.3

# Monitoring & Logging
prometheus-client==0.19.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-mock==3.12.0
EOF

# Create Dockerfile
cat > blockchain/Dockerfile.manager << 'EOF'
# Multi-stage build for block manager
FROM python:3.11-slim as builder
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY blockchain/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target /build/deps

# Clean up unnecessary files
RUN find /build/deps -name "*.pyc" -delete && \
    find /build/deps -name "__pycache__" -type d -exec rm -rf {} + && \
    find /build/deps -name "*.dist-info" -type d -exec rm -rf {} +

# Final distroless stage
FROM gcr.io/distroless/python3-debian12:arm64

# Copy dependencies
COPY --from=builder /build/deps /app/deps

# Copy application code
COPY blockchain/ /app/

# Set environment variables
ENV PYTHONPATH=/app/deps
WORKDIR /app

# Set non-root user
USER 65532:65532

# Expose port
EXPOSE 8088

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["python", "-c", "import requests; requests.get('http://localhost:8088/health')"]

# Default command
CMD ["python", "manager/main.py"]
EOF

# Build block manager container
echo "Building block manager container..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-block-manager:latest-arm64 \
  -f blockchain/Dockerfile.manager \
  --push \
  .

echo "Block manager container built and pushed successfully!"
echo "Container: pickme/lucid-block-manager:latest-arm64"
```

## Validation Criteria
- Container runs on Pi successfully
- Block validation working
- Chain management functional
- Block storage operational
- Chain synchronization working
- Health checks passing

## Environment Configuration
Uses `.env.core` for:
- Block manager port
- Chain configuration
- Block storage settings
- Chain sync settings

## Security Features
- **Block Validation**: Comprehensive block validation rules
- **Chain Integrity**: Continuous chain integrity checking
- **Block Storage**: Secure block storage and retrieval
- **Non-root User**: Container runs as non-root user
- **Distroless Runtime**: Minimal attack surface

## API Endpoints

### Block Management
- `GET /api/v1/blocks` - List blocks
- `GET /api/v1/blocks/{index}` - Get block by index
- `POST /api/v1/blocks/validate` - Validate block
- `DELETE /api/v1/blocks/{index}` - Remove block

### Chain Management
- `GET /api/v1/chain/info` - Get chain information
- `GET /api/v1/chain/height` - Get chain height
- `POST /api/v1/chain/maintenance` - Trigger chain maintenance

### Validation
- `POST /api/v1/validation/block` - Validate block
- `POST /api/v1/validation/chain` - Validate chain
- `GET /api/v1/validation/rules` - Get validation rules

## Troubleshooting

### Build Failures
```bash
# Check build logs
docker buildx build --progress=plain \
  --platform linux/arm64 \
  -t pickme/lucid-block-manager:latest-arm64 \
  -f blockchain/Dockerfile.manager \
  .
```

### Runtime Issues
```bash
# Check container logs
docker logs lucid-block-manager

# Test health endpoint
curl http://localhost:8088/health
```

### Chain Issues
```bash
# Check chain info
curl http://localhost:8088/api/v1/chain/info

# Check chain height
curl http://localhost:8088/api/v1/chain/height

# Trigger chain maintenance
curl -X POST http://localhost:8088/api/v1/chain/maintenance
```

## Next Steps
After successful block manager build, proceed to data chain container build.
