# Data Chain Container

## Overview
Build data chain container for blockchain data management, indexing, and querying.

## Location
`blockchain/Dockerfile.data`

## Container Details
**Container**: `pickme/lucid-data-chain:latest-arm64`

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
EXPOSE 8090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["python", "-c", "import requests; requests.get('http://localhost:8090/health')"]

# Default command
CMD ["python", "data/main.py"]
```

## Requirements File
**File**: `blockchain/requirements.txt`

```txt
# Data Chain Dependencies
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

# Data Processing
pandas==2.1.4
numpy==1.24.3
elasticsearch==8.11.0

# Data Management
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
**File**: `blockchain/data/main.py`

```python
"""
Lucid Data Chain Service
Provides blockchain data management, indexing, and querying
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from blockchain.data.data_indexer import DataIndexer
from blockchain.data.data_storage import DataStorage
from blockchain.data.data_query import DataQuery
from blockchain.data.data_sync import DataSync
from blockchain.api.data_chain_api import DataChainAPI
from blockchain.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global services
data_indexer = None
data_storage = None
data_query = None
data_sync = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global data_indexer, data_storage, data_query, data_sync
    
    # Startup
    logger.info("Starting Lucid Data Chain Service...")
    
    settings = get_settings()
    
    # Initialize data indexer
    data_indexer = DataIndexer(settings)
    await data_indexer.initialize()
    
    # Initialize data storage
    data_storage = DataStorage(settings)
    await data_storage.initialize()
    
    # Initialize data query
    data_query = DataQuery(settings)
    await data_query.initialize()
    
    # Initialize data sync
    data_sync = DataSync(settings)
    await data_sync.initialize()
    
    logger.info("Data Chain Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Data Chain Service...")
    if data_indexer:
        await data_indexer.cleanup()
    if data_storage:
        await data_storage.cleanup()
    if data_query:
        await data_query.cleanup()
    if data_sync:
        await data_sync.cleanup()
    logger.info("Data Chain Service shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="Lucid Data Chain Service",
    description="Blockchain data management, indexing, and querying",
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
app.include_router(DataChainAPI.get_router(), prefix="/api/v1", tags=["data-chain"])

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "lucid-data-chain",
        "version": "1.0.0",
        "data_indexer": await data_indexer.check_health(),
        "data_storage": await data_storage.check_health(),
        "data_query": await data_query.check_health(),
        "data_sync": await data_sync.check_health()
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Lucid Data Chain Service",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": [
            "/api/v1/data",
            "/api/v1/index",
            "/api/v1/query"
        ]
    }

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8090,
        reload=False,
        log_level="info"
    )
```

### Data Indexer
**File**: `blockchain/data/data_indexer.py`

```python
"""
Data indexer for blockchain data
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class DataIndexer:
    """Data indexer for blockchain data"""
    
    def __init__(self, settings):
        self.settings = settings
        self.indexes = {}
        self.indexing_queue = []
        
    async def initialize(self):
        """Initialize data indexer"""
        try:
            # Start indexing loop
            asyncio.create_task(self._indexing_loop())
            
            logger.info("Data indexer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize data indexer: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup data indexer"""
        logger.info("Data indexer cleaned up")
    
    async def _indexing_loop(self):
        """Main indexing loop"""
        while True:
            try:
                # Process indexing queue
                await self._process_indexing_queue()
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Indexing loop error: {e}")
                await asyncio.sleep(5)
    
    async def _process_indexing_queue(self):
        """Process indexing queue"""
        if not self.indexing_queue:
            return
        
        # Process items in queue
        items_to_process = self.indexing_queue.copy()
        self.indexing_queue.clear()
        
        for item in items_to_process:
            try:
                await self._index_item(item)
            except Exception as e:
                logger.error(f"Failed to index item: {e}")
    
    async def _index_item(self, item: Dict[str, Any]):
        """Index individual item"""
        try:
            item_type = item.get("type")
            
            if item_type == "block":
                await self._index_block(item)
            elif item_type == "transaction":
                await self._index_transaction(item)
            elif item_type == "session":
                await self._index_session(item)
            else:
                logger.warning(f"Unknown item type: {item_type}")
                
        except Exception as e:
            logger.error(f"Failed to index item: {e}")
    
    async def _index_block(self, block: Dict[str, Any]):
        """Index block data"""
        try:
            block_id = block.get("id")
            block_index = block.get("index")
            timestamp = block.get("timestamp")
            
            # Create block index entry
            index_entry = {
                "id": block_id,
                "type": "block",
                "index": block_index,
                "timestamp": timestamp,
                "hash": block.get("hash"),
                "previous_hash": block.get("previous_hash"),
                "merkle_root": block.get("merkle_root"),
                "transaction_count": len(block.get("transactions", [])),
                "indexed_at": datetime.utcnow().isoformat()
            }
            
            # Store index entry
            await self._store_index_entry(index_entry)
            
            logger.info(f"Indexed block {block_index}")
            
        except Exception as e:
            logger.error(f"Failed to index block: {e}")
    
    async def _index_transaction(self, transaction: Dict[str, Any]):
        """Index transaction data"""
        try:
            tx_id = transaction.get("id")
            tx_type = transaction.get("type")
            timestamp = transaction.get("timestamp")
            
            # Create transaction index entry
            index_entry = {
                "id": tx_id,
                "type": "transaction",
                "tx_type": tx_type,
                "timestamp": timestamp,
                "block_index": transaction.get("block_index"),
                "session_id": transaction.get("session_id"),
                "indexed_at": datetime.utcnow().isoformat()
            }
            
            # Store index entry
            await self._store_index_entry(index_entry)
            
            logger.info(f"Indexed transaction {tx_id}")
            
        except Exception as e:
            logger.error(f"Failed to index transaction: {e}")
    
    async def _index_session(self, session: Dict[str, Any]):
        """Index session data"""
        try:
            session_id = session.get("id")
            timestamp = session.get("timestamp")
            
            # Create session index entry
            index_entry = {
                "id": session_id,
                "type": "session",
                "timestamp": timestamp,
                "status": session.get("status"),
                "user_id": session.get("user_id"),
                "indexed_at": datetime.utcnow().isoformat()
            }
            
            # Store index entry
            await self._store_index_entry(index_entry)
            
            logger.info(f"Indexed session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to index session: {e}")
    
    async def _store_index_entry(self, entry: Dict[str, Any]):
        """Store index entry"""
        # Implementation would store entry in database
        pass
    
    async def add_to_indexing_queue(self, item: Dict[str, Any]):
        """Add item to indexing queue"""
        self.indexing_queue.append(item)
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get indexing statistics"""
        return {
            "total_indexed": len(self.indexes),
            "queue_size": len(self.indexing_queue),
            "indexes": list(self.indexes.keys())
        }
    
    async def check_health(self) -> bool:
        """Check data indexer health"""
        try:
            return True
        except Exception:
            return False
```

### Data Storage
**File**: `blockchain/data/data_storage.py`

```python
"""
Data storage for blockchain data
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class DataStorage:
    """Data storage for blockchain data"""
    
    def __init__(self, settings):
        self.settings = settings
        self.storage_backend = None
        
    async def initialize(self):
        """Initialize data storage"""
        try:
            # Initialize storage backend
            await self._initialize_storage_backend()
            
            logger.info("Data storage initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize data storage: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup data storage"""
        if self.storage_backend:
            await self.storage_backend.close()
        logger.info("Data storage cleaned up")
    
    async def _initialize_storage_backend(self):
        """Initialize storage backend"""
        # Implementation would initialize storage backend (MongoDB, etc.)
        pass
    
    async def store_block(self, block: Dict[str, Any]) -> bool:
        """Store block data"""
        try:
            # Store block in storage backend
            await self._store_block_data(block)
            
            logger.info(f"Stored block {block.get('index')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store block: {e}")
            return False
    
    async def store_transaction(self, transaction: Dict[str, Any]) -> bool:
        """Store transaction data"""
        try:
            # Store transaction in storage backend
            await self._store_transaction_data(transaction)
            
            logger.info(f"Stored transaction {transaction.get('id')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store transaction: {e}")
            return False
    
    async def store_session(self, session: Dict[str, Any]) -> bool:
        """Store session data"""
        try:
            # Store session in storage backend
            await self._store_session_data(session)
            
            logger.info(f"Stored session {session.get('id')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store session: {e}")
            return False
    
    async def _store_block_data(self, block: Dict[str, Any]):
        """Store block data in backend"""
        # Implementation would store block data
        pass
    
    async def _store_transaction_data(self, transaction: Dict[str, Any]):
        """Store transaction data in backend"""
        # Implementation would store transaction data
        pass
    
    async def _store_session_data(self, session: Dict[str, Any]):
        """Store session data in backend"""
        # Implementation would store session data
        pass
    
    async def get_block(self, block_id: str) -> Optional[Dict[str, Any]]:
        """Get block data"""
        try:
            # Retrieve block from storage backend
            return await self._get_block_data(block_id)
            
        except Exception as e:
            logger.error(f"Failed to get block {block_id}: {e}")
            return None
    
    async def get_transaction(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction data"""
        try:
            # Retrieve transaction from storage backend
            return await self._get_transaction_data(tx_id)
            
        except Exception as e:
            logger.error(f"Failed to get transaction {tx_id}: {e}")
            return None
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        try:
            # Retrieve session from storage backend
            return await self._get_session_data(session_id)
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def _get_block_data(self, block_id: str) -> Optional[Dict[str, Any]]:
        """Get block data from backend"""
        # Implementation would retrieve block data
        return None
    
    async def _get_transaction_data(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction data from backend"""
        # Implementation would retrieve transaction data
        return None
    
    async def _get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from backend"""
        # Implementation would retrieve session data
        return None
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        return {
            "total_blocks": 0,
            "total_transactions": 0,
            "total_sessions": 0,
            "storage_size": 0
        }
    
    async def check_health(self) -> bool:
        """Check data storage health"""
        try:
            return self.storage_backend is not None
        except Exception:
            return False
```

### Data Query
**File**: `blockchain/data/data_query.py`

```python
"""
Data query for blockchain data
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class DataQuery:
    """Data query for blockchain data"""
    
    def __init__(self, settings):
        self.settings = settings
        self.query_cache = {}
        
    async def initialize(self):
        """Initialize data query"""
        try:
            # Initialize query cache
            await self._initialize_query_cache()
            
            logger.info("Data query initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize data query: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup data query"""
        self.query_cache.clear()
        logger.info("Data query cleaned up")
    
    async def _initialize_query_cache(self):
        """Initialize query cache"""
        # Implementation would initialize query cache
        pass
    
    async def query_blocks(self, filters: Dict[str, Any] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Query blocks with filters"""
        try:
            # Build query
            query = self._build_block_query(filters)
            
            # Execute query
            results = await self._execute_block_query(query, limit)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to query blocks: {e}")
            return []
    
    async def query_transactions(self, filters: Dict[str, Any] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Query transactions with filters"""
        try:
            # Build query
            query = self._build_transaction_query(filters)
            
            # Execute query
            results = await self._execute_transaction_query(query, limit)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to query transactions: {e}")
            return []
    
    async def query_sessions(self, filters: Dict[str, Any] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Query sessions with filters"""
        try:
            # Build query
            query = self._build_session_query(filters)
            
            # Execute query
            results = await self._execute_session_query(query, limit)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to query sessions: {e}")
            return []
    
    def _build_block_query(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Build block query"""
        query = {}
        
        if filters:
            if "index_range" in filters:
                start, end = filters["index_range"]
                query["index"] = {"$gte": start, "$lte": end}
            
            if "timestamp_range" in filters:
                start, end = filters["timestamp_range"]
                query["timestamp"] = {"$gte": start, "$lte": end}
            
            if "hash" in filters:
                query["hash"] = filters["hash"]
        
        return query
    
    def _build_transaction_query(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Build transaction query"""
        query = {}
        
        if filters:
            if "type" in filters:
                query["type"] = filters["type"]
            
            if "session_id" in filters:
                query["session_id"] = filters["session_id"]
            
            if "timestamp_range" in filters:
                start, end = filters["timestamp_range"]
                query["timestamp"] = {"$gte": start, "$lte": end}
        
        return query
    
    def _build_session_query(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Build session query"""
        query = {}
        
        if filters:
            if "status" in filters:
                query["status"] = filters["status"]
            
            if "user_id" in filters:
                query["user_id"] = filters["user_id"]
            
            if "timestamp_range" in filters:
                start, end = filters["timestamp_range"]
                query["timestamp"] = {"$gte": start, "$lte": end}
        
        return query
    
    async def _execute_block_query(self, query: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Execute block query"""
        # Implementation would execute block query
        return []
    
    async def _execute_transaction_query(self, query: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Execute transaction query"""
        # Implementation would execute transaction query
        return []
    
    async def _execute_session_query(self, query: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Execute session query"""
        # Implementation would execute session query
        return []
    
    async def get_query_stats(self) -> Dict[str, Any]:
        """Get query statistics"""
        return {
            "cache_size": len(self.query_cache),
            "total_queries": 0,
            "average_query_time": 0
        }
    
    async def check_health(self) -> bool:
        """Check data query health"""
        try:
            return True
        except Exception:
            return False
```

## Build Command

```bash
# Build data chain container
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-data-chain:latest-arm64 \
  -f blockchain/Dockerfile.data \
  --push \
  .
```

## Build Script Implementation

**File**: `scripts/core/build-data-chain.sh`

```bash
#!/bin/bash
# scripts/core/build-data-chain.sh
# Build data chain container

set -e

echo "Building data chain container..."

# Create blockchain directory if it doesn't exist
mkdir -p blockchain

# Create requirements.txt
cat > blockchain/requirements.txt << 'EOF'
# Data Chain Dependencies
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

# Data Processing
pandas==2.1.4
numpy==1.24.3
elasticsearch==8.11.0

# Data Management
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
cat > blockchain/Dockerfile.data << 'EOF'
# Multi-stage build for data chain
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
EXPOSE 8090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["python", "-c", "import requests; requests.get('http://localhost:8090/health')"]

# Default command
CMD ["python", "data/main.py"]
EOF

# Build data chain container
echo "Building data chain container..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-data-chain:latest-arm64 \
  -f blockchain/Dockerfile.data \
  --push \
  .

echo "Data chain container built and pushed successfully!"
echo "Container: pickme/lucid-data-chain:latest-arm64"
```

## Validation Criteria
- Container runs on Pi successfully
- Data indexing working
- Data storage functional
- Data querying operational
- Data synchronization working
- Health checks passing

## Environment Configuration
Uses `.env.core` for:
- Data chain port
- Storage backend configuration
- Indexing settings
- Query cache settings

## Security Features
- **Data Integrity**: Cryptographic data verification
- **Query Security**: Secure query execution
- **Data Privacy**: Encrypted data storage
- **Non-root User**: Container runs as non-root user
- **Distroless Runtime**: Minimal attack surface

## API Endpoints

### Data Management
- `GET /api/v1/data/blocks` - Query blocks
- `GET /api/v1/data/transactions` - Query transactions
- `GET /api/v1/data/sessions` - Query sessions
- `POST /api/v1/data/index` - Index data

### Data Storage
- `POST /api/v1/storage/blocks` - Store block
- `POST /api/v1/storage/transactions` - Store transaction
- `POST /api/v1/storage/sessions` - Store session
- `GET /api/v1/storage/stats` - Get storage stats

### Data Query
- `POST /api/v1/query/blocks` - Query blocks
- `POST /api/v1/query/transactions` - Query transactions
- `POST /api/v1/query/sessions` - Query sessions
- `GET /api/v1/query/stats` - Get query stats

## Troubleshooting

### Build Failures
```bash
# Check build logs
docker buildx build --progress=plain \
  --platform linux/arm64 \
  -t pickme/lucid-data-chain:latest-arm64 \
  -f blockchain/Dockerfile.data \
  .
```

### Runtime Issues
```bash
# Check container logs
docker logs lucid-data-chain

# Test health endpoint
curl http://localhost:8090/health
```

### Data Issues
```bash
# Check data stats
curl http://localhost:8090/api/v1/storage/stats

# Test data query
curl -X POST http://localhost:8090/api/v1/query/blocks \
  -H "Content-Type: application/json" \
  -d '{"filters": {}, "limit": 10}'
```

## Next Steps
After successful data chain build, proceed to Phase 2 Docker Compose generation.
