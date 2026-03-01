# Blockchain Engine Container

## Overview
Build blockchain engine container with consensus mechanism, block creation, and transaction processing for Phase 2 core services.

## Location
`blockchain/Dockerfile.engine`

## Container Details
**Container**: `pickme/lucid-blockchain-engine:latest-arm64`

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
    libsecp256k1-dev \
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
EXPOSE 8084

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["python", "-c", "import requests; requests.get('http://localhost:8084/health')"]

# Default command
CMD ["python", "engine/main.py"]
```

## Requirements File
**File**: `blockchain/requirements.txt`

```txt
# Blockchain Engine Dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
httpx==0.25.2
aiofiles==23.2.1
python-multipart==0.0.6

# Blockchain & Cryptography
cryptography==41.0.8
secp256k1==0.14.0
hashlib2==1.3.1
merkle-tree==1.0.0

# Database Integration
motor==3.3.2
redis==5.0.1
pymongo==4.6.0

# Consensus & Networking
asyncio-mqtt==0.16.1
websockets==12.0

# Monitoring & Logging
prometheus-client==0.19.0
structlog==23.2.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-mock==3.12.0
```

## Application Code Structure

### Main Application
**File**: `blockchain/engine/main.py`

```python
"""
Lucid Blockchain Engine
Provides consensus mechanism, block creation, and transaction processing
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from blockchain.engine.consensus import ConsensusEngine
from blockchain.engine.block_creator import BlockCreator
from blockchain.engine.transaction_processor import TransactionProcessor
from blockchain.engine.network_manager import NetworkManager
from blockchain.api.blockchain_api import BlockchainAPI
from blockchain.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global services
consensus_engine = None
block_creator = None
transaction_processor = None
network_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global consensus_engine, block_creator, transaction_processor, network_manager
    
    # Startup
    logger.info("Starting Lucid Blockchain Engine...")
    
    settings = get_settings()
    
    # Initialize consensus engine
    consensus_engine = ConsensusEngine(settings)
    await consensus_engine.initialize()
    
    # Initialize block creator
    block_creator = BlockCreator(settings)
    await block_creator.initialize()
    
    # Initialize transaction processor
    transaction_processor = TransactionProcessor(settings)
    await transaction_processor.initialize()
    
    # Initialize network manager
    network_manager = NetworkManager(settings)
    await network_manager.initialize()
    
    logger.info("Blockchain Engine started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Blockchain Engine...")
    if consensus_engine:
        await consensus_engine.cleanup()
    if block_creator:
        await block_creator.cleanup()
    if transaction_processor:
        await transaction_processor.cleanup()
    if network_manager:
        await network_manager.cleanup()
    logger.info("Blockchain Engine shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="Lucid Blockchain Engine",
    description="Blockchain consensus, block creation, and transaction processing",
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
app.include_router(BlockchainAPI.get_router(), prefix="/api/v1", tags=["blockchain"])

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "lucid-blockchain-engine",
        "version": "1.0.0",
        "consensus": await consensus_engine.check_health(),
        "block_creator": await block_creator.check_health(),
        "transaction_processor": await transaction_processor.check_health(),
        "network": await network_manager.check_health()
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Lucid Blockchain Engine",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": [
            "/api/v1/blocks",
            "/api/v1/transactions",
            "/api/v1/consensus"
        ]
    }

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8084,
        reload=False,
        log_level="info"
    )
```

### Consensus Engine
**File**: `blockchain/engine/consensus.py`

```python
"""
Consensus engine for blockchain
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import hashlib
import json

logger = logging.getLogger(__name__)

class ConsensusEngine:
    """Consensus engine for blockchain"""
    
    def __init__(self, settings):
        self.settings = settings
        self.current_block = None
        self.consensus_state = "idle"
        self.participants = []
        
    async def initialize(self):
        """Initialize consensus engine"""
        try:
            # Initialize consensus state
            self.consensus_state = "idle"
            self.participants = []
            
            # Start consensus loop
            asyncio.create_task(self._consensus_loop())
            
            logger.info("Consensus engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize consensus engine: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup consensus engine"""
        self.consensus_state = "shutdown"
        logger.info("Consensus engine cleaned up")
    
    async def _consensus_loop(self):
        """Main consensus loop"""
        while self.consensus_state != "shutdown":
            try:
                if self.consensus_state == "idle":
                    await self._start_consensus()
                elif self.consensus_state == "voting":
                    await self._process_votes()
                elif self.consensus_state == "finalizing":
                    await self._finalize_block()
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Consensus loop error: {e}")
                await asyncio.sleep(5)
    
    async def _start_consensus(self):
        """Start consensus process"""
        try:
            # Check if we have enough participants
            if len(self.participants) < 2:
                return
            
            # Create new block proposal
            self.current_block = await self._create_block_proposal()
            
            # Start voting phase
            self.consensus_state = "voting"
            
            # Broadcast block proposal
            await self._broadcast_block_proposal(self.current_block)
            
            logger.info("Consensus started for new block")
            
        except Exception as e:
            logger.error(f"Failed to start consensus: {e}")
            self.consensus_state = "idle"
    
    async def _process_votes(self):
        """Process consensus votes"""
        try:
            # Check if we have enough votes
            votes = await self._collect_votes()
            
            if len(votes) >= (len(self.participants) // 2) + 1:
                # Majority reached, finalize block
                self.consensus_state = "finalizing"
                await self._finalize_block()
            else:
                # Wait for more votes
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Failed to process votes: {e}")
            self.consensus_state = "idle"
    
    async def _finalize_block(self):
        """Finalize consensus block"""
        try:
            if self.current_block:
                # Add block to blockchain
                await self._add_block_to_chain(self.current_block)
                
                # Reset consensus state
                self.consensus_state = "idle"
                self.current_block = None
                
                logger.info("Block finalized and added to chain")
                
        except Exception as e:
            logger.error(f"Failed to finalize block: {e}")
            self.consensus_state = "idle"
    
    async def _create_block_proposal(self) -> Dict[str, Any]:
        """Create new block proposal"""
        return {
            "index": await self._get_next_block_index(),
            "timestamp": datetime.utcnow().isoformat(),
            "transactions": await self._get_pending_transactions(),
            "previous_hash": await self._get_previous_block_hash(),
            "merkle_root": None,  # Will be calculated
            "nonce": 0,
            "hash": None  # Will be calculated
        }
    
    async def _broadcast_block_proposal(self, block: Dict[str, Any]):
        """Broadcast block proposal to participants"""
        # Implementation would send block to all participants
        pass
    
    async def _collect_votes(self) -> List[Dict[str, Any]]:
        """Collect votes from participants"""
        # Implementation would collect votes from participants
        return []
    
    async def _add_block_to_chain(self, block: Dict[str, Any]):
        """Add block to blockchain"""
        # Implementation would add block to persistent storage
        pass
    
    async def _get_next_block_index(self) -> int:
        """Get next block index"""
        # Implementation would get next block index from storage
        return 0
    
    async def _get_pending_transactions(self) -> List[Dict[str, Any]]:
        """Get pending transactions"""
        # Implementation would get pending transactions from storage
        return []
    
    async def _get_previous_block_hash(self) -> str:
        """Get previous block hash"""
        # Implementation would get previous block hash from storage
        return "0" * 64
    
    async def check_health(self) -> bool:
        """Check consensus engine health"""
        try:
            return self.consensus_state in ["idle", "voting", "finalizing"]
        except Exception:
            return False
```

### Block Creator
**File**: `blockchain/engine/block_creator.py`

```python
"""
Block creator for blockchain
"""

import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime
import hashlib
import json

logger = logging.getLogger(__name__)

class BlockCreator:
    """Block creator for blockchain"""
    
    def __init__(self, settings):
        self.settings = settings
        self.block_interval = 10  # 10 seconds
        self.last_block_time = None
        
    async def initialize(self):
        """Initialize block creator"""
        try:
            # Start block creation loop
            asyncio.create_task(self._block_creation_loop())
            
            logger.info("Block creator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize block creator: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup block creator"""
        logger.info("Block creator cleaned up")
    
    async def _block_creation_loop(self):
        """Main block creation loop"""
        while True:
            try:
                # Check if it's time to create a new block
                if await self._should_create_block():
                    await self._create_new_block()
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Block creation loop error: {e}")
                await asyncio.sleep(5)
    
    async def _should_create_block(self) -> bool:
        """Check if it's time to create a new block"""
        if self.last_block_time is None:
            return True
        
        time_since_last = (datetime.utcnow() - self.last_block_time).total_seconds()
        return time_since_last >= self.block_interval
    
    async def _create_new_block(self):
        """Create new block"""
        try:
            # Get pending transactions
            transactions = await self._get_pending_transactions()
            
            if not transactions:
                return
            
            # Create block
            block = await self._build_block(transactions)
            
            # Add block to chain
            await self._add_block_to_chain(block)
            
            # Update last block time
            self.last_block_time = datetime.utcnow()
            
            logger.info(f"Created new block with {len(transactions)} transactions")
            
        except Exception as e:
            logger.error(f"Failed to create new block: {e}")
    
    async def _build_block(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build block from transactions"""
        # Calculate merkle root
        merkle_root = await self._calculate_merkle_root(transactions)
        
        # Get previous block hash
        previous_hash = await self._get_previous_block_hash()
        
        # Create block
        block = {
            "index": await self._get_next_block_index(),
            "timestamp": datetime.utcnow().isoformat(),
            "transactions": transactions,
            "previous_hash": previous_hash,
            "merkle_root": merkle_root,
            "nonce": 0,
            "hash": None
        }
        
        # Calculate block hash
        block["hash"] = await self._calculate_block_hash(block)
        
        return block
    
    async def _calculate_merkle_root(self, transactions: List[Dict[str, Any]]) -> str:
        """Calculate merkle root for transactions"""
        if not transactions:
            return "0" * 64
        
        # Simple merkle root calculation
        hashes = [hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest() for tx in transactions]
        
        while len(hashes) > 1:
            new_hashes = []
            for i in range(0, len(hashes), 2):
                if i + 1 < len(hashes):
                    combined = hashes[i] + hashes[i + 1]
                else:
                    combined = hashes[i] + hashes[i]
                new_hashes.append(hashlib.sha256(combined.encode()).hexdigest())
            hashes = new_hashes
        
        return hashes[0]
    
    async def _calculate_block_hash(self, block: Dict[str, Any]) -> str:
        """Calculate block hash"""
        block_string = f"{block['index']}{block['timestamp']}{block['previous_hash']}{block['merkle_root']}{block['nonce']}"
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    async def _get_pending_transactions(self) -> List[Dict[str, Any]]:
        """Get pending transactions"""
        # Implementation would get pending transactions from storage
        return []
    
    async def _get_previous_block_hash(self) -> str:
        """Get previous block hash"""
        # Implementation would get previous block hash from storage
        return "0" * 64
    
    async def _get_next_block_index(self) -> int:
        """Get next block index"""
        # Implementation would get next block index from storage
        return 0
    
    async def _add_block_to_chain(self, block: Dict[str, Any]):
        """Add block to chain"""
        # Implementation would add block to persistent storage
        pass
    
    async def check_health(self) -> bool:
        """Check block creator health"""
        try:
            return True
        except Exception:
            return False
```

## Build Command

```bash
# Build blockchain engine container
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-blockchain-engine:latest-arm64 \
  -f blockchain/Dockerfile.engine \
  --push \
  .
```

## Build Script Implementation

**File**: `scripts/core/build-blockchain-engine.sh`

```bash
#!/bin/bash
# scripts/core/build-blockchain-engine.sh
# Build blockchain engine container

set -e

echo "Building blockchain engine container..."

# Create blockchain directory if it doesn't exist
mkdir -p blockchain

# Create requirements.txt
cat > blockchain/requirements.txt << 'EOF'
# Blockchain Engine Dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
httpx==0.25.2
aiofiles==23.2.1
python-multipart==0.0.6

# Blockchain & Cryptography
cryptography==41.0.8
secp256k1==0.14.0
hashlib2==1.3.1
merkle-tree==1.0.0

# Database Integration
motor==3.3.2
redis==5.0.1
pymongo==4.6.0

# Consensus & Networking
asyncio-mqtt==0.16.1
websockets==12.0

# Monitoring & Logging
prometheus-client==0.19.0
structlog==23.2.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-mock==3.12.0
EOF

# Create Dockerfile
cat > blockchain/Dockerfile.engine << 'EOF'
# Multi-stage build for blockchain engine
FROM python:3.11-slim as builder
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libsecp256k1-dev \
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
EXPOSE 8084

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["python", "-c", "import requests; requests.get('http://localhost:8084/health')"]

# Default command
CMD ["python", "engine/main.py"]
EOF

# Build blockchain engine container
echo "Building blockchain engine container..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-blockchain-engine:latest-arm64 \
  -f blockchain/Dockerfile.engine \
  --push \
  .

echo "Blockchain engine container built and pushed successfully!"
echo "Container: pickme/lucid-blockchain-engine:latest-arm64"
```

## Validation Criteria
- Container runs on Pi successfully
- Consensus mechanism operational
- Block creation working (1 block per 10 seconds)
- Transaction processing functional
- Health checks passing

## Environment Configuration
Uses `.env.core` for:
- Blockchain engine port
- Consensus configuration
- Block creation interval
- Network settings

## Security Features
- **Consensus Security**: Majority voting mechanism
- **Block Validation**: Cryptographic hash verification
- **Transaction Integrity**: Merkle tree validation
- **Non-root User**: Container runs as non-root user
- **Distroless Runtime**: Minimal attack surface

## API Endpoints

### Blockchain Operations
- `GET /api/v1/blocks` - List blocks
- `GET /api/v1/blocks/{index}` - Get specific block
- `POST /api/v1/blocks` - Create new block
- `GET /api/v1/chain` - Get blockchain

### Transaction Operations
- `GET /api/v1/transactions` - List transactions
- `POST /api/v1/transactions` - Submit transaction
- `GET /api/v1/transactions/{tx_id}` - Get transaction

### Consensus Operations
- `GET /api/v1/consensus/status` - Get consensus status
- `POST /api/v1/consensus/vote` - Submit consensus vote
- `GET /api/v1/consensus/participants` - List participants

## Troubleshooting

### Build Failures
```bash
# Check build logs
docker buildx build --progress=plain \
  --platform linux/arm64 \
  -t pickme/lucid-blockchain-engine:latest-arm64 \
  -f blockchain/Dockerfile.engine \
  .
```

### Runtime Issues
```bash
# Check container logs
docker logs lucid-blockchain-engine

# Test health endpoint
curl http://localhost:8084/health
```

### Consensus Issues
```bash
# Check consensus status
curl http://localhost:8084/api/v1/consensus/status

# Check block creation
curl http://localhost:8084/api/v1/blocks
```

## Next Steps
After successful blockchain engine build, proceed to session anchoring container build.
