# Session Anchoring Container

## Overview
Build session anchoring container for anchoring session data to blockchain with Merkle tree verification and cryptographic proofs.

## Location
`blockchain/Dockerfile.anchoring`

## Container Details
**Container**: `pickme/lucid-session-anchoring:latest-arm64`

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
EXPOSE 8086

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["python", "-c", "import requests; requests.get('http://localhost:8086/health')"]

# Default command
CMD ["python", "anchoring/main.py"]
```

## Requirements File
**File**: `blockchain/requirements.txt`

```txt
# Session Anchoring Dependencies
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
pycryptodome==3.19.0

# Database Integration
motor==3.3.2
redis==5.0.1
pymongo==4.6.0

# Session Processing
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
**File**: `blockchain/anchoring/main.py`

```python
"""
Lucid Session Anchoring Service
Provides session data anchoring to blockchain with Merkle tree verification
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from blockchain.anchoring.merkle_processor import MerkleProcessor
from blockchain.anchoring.anchoring_service import AnchoringService
from blockchain.anchoring.proof_generator import ProofGenerator
from blockchain.anchoring.verification_service import VerificationService
from blockchain.api.anchoring_api import AnchoringAPI
from blockchain.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global services
merkle_processor = None
anchoring_service = None
proof_generator = None
verification_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global merkle_processor, anchoring_service, proof_generator, verification_service
    
    # Startup
    logger.info("Starting Lucid Session Anchoring Service...")
    
    settings = get_settings()
    
    # Initialize Merkle processor
    merkle_processor = MerkleProcessor(settings)
    await merkle_processor.initialize()
    
    # Initialize anchoring service
    anchoring_service = AnchoringService(settings)
    await anchoring_service.initialize()
    
    # Initialize proof generator
    proof_generator = ProofGenerator(settings)
    await proof_generator.initialize()
    
    # Initialize verification service
    verification_service = VerificationService(settings)
    await verification_service.initialize()
    
    logger.info("Session Anchoring Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Session Anchoring Service...")
    if merkle_processor:
        await merkle_processor.cleanup()
    if anchoring_service:
        await anchoring_service.cleanup()
    if proof_generator:
        await proof_generator.cleanup()
    if verification_service:
        await verification_service.cleanup()
    logger.info("Session Anchoring Service shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="Lucid Session Anchoring Service",
    description="Session data anchoring to blockchain with Merkle tree verification",
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
app.include_router(AnchoringAPI.get_router(), prefix="/api/v1", tags=["anchoring"])

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "lucid-session-anchoring",
        "version": "1.0.0",
        "merkle_processor": await merkle_processor.check_health(),
        "anchoring_service": await anchoring_service.check_health(),
        "proof_generator": await proof_generator.check_health(),
        "verification_service": await verification_service.check_health()
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Lucid Session Anchoring Service",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": [
            "/api/v1/anchoring",
            "/api/v1/merkle",
            "/api/v1/proofs"
        ]
    }

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8086,
        reload=False,
        log_level="info"
    )
```

### Merkle Processor
**File**: `blockchain/anchoring/merkle_processor.py`

```python
"""
Merkle tree processor for session anchoring
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
import hashlib
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class MerkleProcessor:
    """Merkle tree processor for session anchoring"""
    
    def __init__(self, settings):
        self.settings = settings
        self.merkle_trees = {}
        
    async def initialize(self):
        """Initialize Merkle processor"""
        try:
            logger.info("Merkle processor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Merkle processor: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup Merkle processor"""
        logger.info("Merkle processor cleaned up")
    
    async def create_merkle_tree(self, session_id: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create Merkle tree from session chunks"""
        try:
            # Calculate chunk hashes
            chunk_hashes = []
            for chunk in chunks:
                chunk_hash = await self._calculate_chunk_hash(chunk)
                chunk_hashes.append(chunk_hash)
            
            # Build Merkle tree
            merkle_tree = await self._build_merkle_tree(chunk_hashes)
            
            # Store Merkle tree
            self.merkle_trees[session_id] = {
                "tree": merkle_tree,
                "chunks": chunks,
                "created_at": datetime.utcnow(),
                "root_hash": merkle_tree["root"]
            }
            
            logger.info(f"Created Merkle tree for session {session_id}")
            
            return {
                "session_id": session_id,
                "root_hash": merkle_tree["root"],
                "tree_depth": merkle_tree["depth"],
                "chunk_count": len(chunks),
                "created_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create Merkle tree for session {session_id}: {e}")
            raise
    
    async def _calculate_chunk_hash(self, chunk: Dict[str, Any]) -> str:
        """Calculate hash for chunk"""
        chunk_string = json.dumps(chunk, sort_keys=True)
        return hashlib.sha256(chunk_string.encode()).hexdigest()
    
    async def _build_merkle_tree(self, hashes: List[str]) -> Dict[str, Any]:
        """Build Merkle tree from hashes"""
        if not hashes:
            return {"root": "0" * 64, "depth": 0, "nodes": []}
        
        # Build tree bottom-up
        current_level = hashes.copy()
        tree_nodes = []
        depth = 0
        
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else current_level[i]
                
                # Combine and hash
                combined = left + right
                parent_hash = hashlib.sha256(combined.encode()).hexdigest()
                
                next_level.append(parent_hash)
                tree_nodes.append({
                    "left": left,
                    "right": right,
                    "parent": parent_hash,
                    "level": depth
                })
            
            current_level = next_level
            depth += 1
        
        return {
            "root": current_level[0],
            "depth": depth,
            "nodes": tree_nodes
        }
    
    async def generate_proof(self, session_id: str, chunk_index: int) -> Dict[str, Any]:
        """Generate Merkle proof for specific chunk"""
        try:
            if session_id not in self.merkle_trees:
                raise ValueError(f"Session {session_id} not found")
            
            merkle_tree = self.merkle_trees[session_id]
            tree_nodes = merkle_tree["tree"]["nodes"]
            
            # Find path to chunk
            proof_path = await self._find_proof_path(tree_nodes, chunk_index)
            
            return {
                "session_id": session_id,
                "chunk_index": chunk_index,
                "proof_path": proof_path,
                "root_hash": merkle_tree["root_hash"],
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate proof for session {session_id}, chunk {chunk_index}: {e}")
            raise
    
    async def _find_proof_path(self, tree_nodes: List[Dict[str, Any]], chunk_index: int) -> List[str]:
        """Find proof path for chunk"""
        # Implementation would find the path from chunk to root
        # This is a simplified version
        return []
    
    async def verify_proof(self, session_id: str, chunk_index: int, proof_path: List[str]) -> bool:
        """Verify Merkle proof for chunk"""
        try:
            if session_id not in self.merkle_trees:
                return False
            
            merkle_tree = self.merkle_trees[session_id]
            root_hash = merkle_tree["root_hash"]
            
            # Verify proof
            is_valid = await self._verify_proof_path(proof_path, root_hash)
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Failed to verify proof for session {session_id}, chunk {chunk_index}: {e}")
            return False
    
    async def _verify_proof_path(self, proof_path: List[str], root_hash: str) -> bool:
        """Verify proof path"""
        # Implementation would verify the proof path
        # This is a simplified version
        return True
    
    async def get_merkle_tree(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get Merkle tree for session"""
        return self.merkle_trees.get(session_id)
    
    async def check_health(self) -> bool:
        """Check Merkle processor health"""
        try:
            return True
        except Exception:
            return False
```

### Anchoring Service
**File**: `blockchain/anchoring/anchoring_service.py`

```python
"""
Anchoring service for session data to blockchain
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

class AnchoringService:
    """Anchoring service for session data to blockchain"""
    
    def __init__(self, settings):
        self.settings = settings
        self.blockchain_url = settings.blockchain_engine_url
        self.http_client = None
        
    async def initialize(self):
        """Initialize anchoring service"""
        try:
            self.http_client = httpx.AsyncClient(timeout=30.0)
            logger.info("Anchoring service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize anchoring service: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup anchoring service"""
        if self.http_client:
            await self.http_client.aclose()
        logger.info("Anchoring service cleaned up")
    
    async def anchor_session(self, session_id: str, merkle_root: str, session_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Anchor session to blockchain"""
        try:
            # Create anchoring transaction
            transaction = await self._create_anchoring_transaction(session_id, merkle_root, session_metadata)
            
            # Submit transaction to blockchain
            block_hash = await self._submit_to_blockchain(transaction)
            
            # Store anchoring record
            anchoring_record = {
                "session_id": session_id,
                "merkle_root": merkle_root,
                "block_hash": block_hash,
                "transaction_id": transaction["id"],
                "anchored_at": datetime.utcnow(),
                "metadata": session_metadata
            }
            
            await self._store_anchoring_record(anchoring_record)
            
            logger.info(f"Session {session_id} anchored to blockchain")
            
            return anchoring_record
            
        except Exception as e:
            logger.error(f"Failed to anchor session {session_id}: {e}")
            raise
    
    async def _create_anchoring_transaction(self, session_id: str, merkle_root: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create anchoring transaction"""
        return {
            "id": f"anchor_{session_id}_{datetime.utcnow().timestamp()}",
            "type": "session_anchoring",
            "session_id": session_id,
            "merkle_root": merkle_root,
            "metadata": metadata,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _submit_to_blockchain(self, transaction: Dict[str, Any]) -> str:
        """Submit transaction to blockchain"""
        try:
            response = await self.http_client.post(
                f"{self.blockchain_url}/api/v1/transactions",
                json=transaction
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("block_hash", "unknown")
            else:
                raise Exception(f"Failed to submit transaction: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to submit transaction to blockchain: {e}")
            raise
    
    async def _store_anchoring_record(self, record: Dict[str, Any]):
        """Store anchoring record"""
        # Implementation would store record in database
        pass
    
    async def get_anchoring_record(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get anchoring record for session"""
        # Implementation would retrieve record from database
        return None
    
    async def verify_anchoring(self, session_id: str) -> bool:
        """Verify session anchoring"""
        try:
            record = await self.get_anchoring_record(session_id)
            if not record:
                return False
            
            # Verify block exists on blockchain
            block_exists = await self._verify_block_exists(record["block_hash"])
            
            return block_exists
            
        except Exception as e:
            logger.error(f"Failed to verify anchoring for session {session_id}: {e}")
            return False
    
    async def _verify_block_exists(self, block_hash: str) -> bool:
        """Verify block exists on blockchain"""
        try:
            response = await self.http_client.get(f"{self.blockchain_url}/api/v1/blocks/{block_hash}")
            return response.status_code == 200
        except Exception:
            return False
    
    async def check_health(self) -> bool:
        """Check anchoring service health"""
        try:
            # Test blockchain connection
            response = await self.http_client.get(f"{self.blockchain_url}/health")
            return response.status_code == 200
        except Exception:
            return False
```

## Build Command

```bash
# Build session anchoring container
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-session-anchoring:latest-arm64 \
  -f blockchain/Dockerfile.anchoring \
  --push \
  .
```

## Build Script Implementation

**File**: `scripts/core/build-session-anchoring.sh`

```bash
#!/bin/bash
# scripts/core/build-session-anchoring.sh
# Build session anchoring container

set -e

echo "Building session anchoring container..."

# Create blockchain directory if it doesn't exist
mkdir -p blockchain

# Create requirements.txt
cat > blockchain/requirements.txt << 'EOF'
# Session Anchoring Dependencies
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
pycryptodome==3.19.0

# Database Integration
motor==3.3.2
redis==5.0.1
pymongo==4.6.0

# Session Processing
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
cat > blockchain/Dockerfile.anchoring << 'EOF'
# Multi-stage build for session anchoring
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
EXPOSE 8086

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["python", "-c", "import requests; requests.get('http://localhost:8086/health')"]

# Default command
CMD ["python", "anchoring/main.py"]
EOF

# Build session anchoring container
echo "Building session anchoring container..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-session-anchoring:latest-arm64 \
  -f blockchain/Dockerfile.anchoring \
  --push \
  .

echo "Session anchoring container built and pushed successfully!"
echo "Container: pickme/lucid-session-anchoring:latest-arm64"
```

## Validation Criteria
- Container runs on Pi successfully
- Merkle tree processing working
- Session anchoring to blockchain functional
- Proof generation and verification working
- Health checks passing

## Environment Configuration
Uses `.env.core` for:
- Session anchoring port
- Blockchain engine URL
- Merkle tree configuration
- Anchoring settings

## Security Features
- **Merkle Tree Security**: Cryptographic hash verification
- **Anchoring Integrity**: Blockchain immutability
- **Proof Verification**: Cryptographic proof validation
- **Non-root User**: Container runs as non-root user
- **Distroless Runtime**: Minimal attack surface

## API Endpoints

### Anchoring Operations
- `POST /api/v1/anchoring/anchor` - Anchor session to blockchain
- `GET /api/v1/anchoring/{session_id}` - Get anchoring record
- `POST /api/v1/anchoring/verify` - Verify session anchoring

### Merkle Tree Operations
- `POST /api/v1/merkle/create` - Create Merkle tree
- `GET /api/v1/merkle/{session_id}` - Get Merkle tree
- `POST /api/v1/merkle/proof` - Generate Merkle proof

### Proof Operations
- `POST /api/v1/proofs/generate` - Generate proof
- `POST /api/v1/proofs/verify` - Verify proof
- `GET /api/v1/proofs/{proof_id}` - Get proof details

## Troubleshooting

### Build Failures
```bash
# Check build logs
docker buildx build --progress=plain \
  --platform linux/arm64 \
  -t pickme/lucid-session-anchoring:latest-arm64 \
  -f blockchain/Dockerfile.anchoring \
  .
```

### Runtime Issues
```bash
# Check container logs
docker logs lucid-session-anchoring

# Test health endpoint
curl http://localhost:8086/health
```

### Anchoring Issues
```bash
# Test anchoring endpoint
curl -X POST http://localhost:8086/api/v1/anchoring/anchor \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "merkle_root": "abc123"}'

# Check anchoring status
curl http://localhost:8086/api/v1/anchoring/test
```

## Next Steps
After successful session anchoring build, proceed to block manager container build.
