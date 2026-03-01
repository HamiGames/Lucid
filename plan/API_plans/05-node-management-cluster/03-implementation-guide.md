# Node Management Cluster Implementation Guide

## Code Structure

### Directory Structure
```
node/
├── worker/
│   ├── __init__.py
│   ├── node_routes.py          # FastAPI route handlers
│   ├── node_worker.py          # Core node management logic
│   ├── node_service.py         # Business logic layer
│   ├── node_repository.py      # Data access layer
│   └── node_models.py          # Pydantic models
├── pools/
│   ├── __init__.py
│   ├── pool_routes.py          # Pool management routes
│   ├── pool_service.py         # Pool business logic
│   ├── pool_repository.py      # Pool data access
│   └── pool_models.py          # Pool models
├── resources/
│   ├── __init__.py
│   ├── resource_monitor.py     # Resource monitoring service
│   ├── resource_collector.py   # System metrics collection
│   └── resource_models.py      # Resource models
├── poot/
│   ├── __init__.py
│   ├── poot_validator.py       # PoOT validation logic
│   ├── poot_calculator.py      # PoOT score calculation
│   ├── poot_routes.py          # PoOT API routes
│   └── poot_models.py          # PoOT models
├── payouts/
│   ├── __init__.py
│   ├── payout_processor.py     # Payout processing logic
│   ├── payout_scheduler.py     # Payout scheduling
│   ├── payout_routes.py        # Payout API routes
│   └── payout_models.py        # Payout models
├── auth/
│   ├── __init__.py
│   ├── node_auth.py            # Node authentication
│   └── permissions.py          # Permission management
├── utils/
│   ├── __init__.py
│   ├── validators.py           # Custom validators
│   ├── exceptions.py           # Custom exceptions
│   └── helpers.py              # Utility functions
├── config/
│   ├── __init__.py
│   ├── settings.py             # Configuration management
│   └── database.py             # Database configuration
├── tests/
│   ├── __init__.py
│   ├── test_node_service.py
│   ├── test_pool_service.py
│   ├── test_poot_validator.py
│   ├── test_payout_processor.py
│   └── fixtures/
└── main.py                     # FastAPI application entry point
```

## Naming Conventions

### File Naming
- **Python Files**: `snake_case.py`
- **Test Files**: `test_*.py`
- **Configuration Files**: `*.conf`, `*.yaml`, `*.toml`
- **Docker Files**: `Dockerfile.*`, `docker-compose*.yml`

### Class Naming
- **Services**: `{Domain}Service` (e.g., `NodeService`, `PoolService`)
- **Repositories**: `{Domain}Repository` (e.g., `NodeRepository`, `PoolRepository`)
- **Models**: `{Domain}Model` (e.g., `NodeModel`, `PoolModel`)
- **Validators**: `{Domain}Validator` (e.g., `NodeValidator`, `PoOTValidator`)
- **Exceptions**: `{Domain}Error` (e.g., `NodeNotFoundError`, `InvalidPoOTError`)

### Function Naming
- **Public Methods**: `snake_case`
- **Private Methods**: `_snake_case`
- **Async Methods**: `async def snake_case`
- **Property Methods**: `@property def snake_case`

### Variable Naming
- **Constants**: `UPPER_SNAKE_CASE`
- **Variables**: `snake_case`
- **Database Fields**: `snake_case`
- **API Fields**: `snake_case`

### Database Naming
- **Collections**: `snake_case` (e.g., `nodes`, `node_pools`)
- **Fields**: `snake_case` (e.g., `node_id`, `created_at`)
- **Indexes**: `idx_{field_name}` (e.g., `idx_node_id`, `idx_status`)

## Core Implementation

### Node Service Implementation

#### NodeService Class
```python
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio
import logging

from node.models.node_models import Node, NodeCreateRequest, NodeUpdateRequest
from node.repository.node_repository import NodeRepository
from node.utils.exceptions import NodeNotFoundError, InvalidNodeStatusError
from node.utils.validators import NodeValidator
from node.resources.resource_monitor import ResourceMonitor

logger = logging.getLogger(__name__)

class NodeService:
    def __init__(
        self,
        node_repository: NodeRepository,
        resource_monitor: ResourceMonitor,
        validator: NodeValidator
    ):
        self.node_repository = node_repository
        self.resource_monitor = resource_monitor
        self.validator = validator
        
    async def create_node(self, request: NodeCreateRequest) -> Node:
        """Create a new node with validation and initialization."""
        # Validate request
        await self.validator.validate_create_request(request)
        
        # Generate unique node ID
        node_id = f"node_{request.name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create node object
        node = Node(
            node_id=node_id,
            name=request.name,
            node_type=request.node_type,
            hardware_info=request.hardware_info,
            location=request.location,
            pool_id=request.initial_pool_id,
            configuration=request.configuration,
            status="inactive",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Save to database
        await self.node_repository.create(node)
        
        # Initialize resource monitoring
        await self.resource_monitor.initialize_node(node_id)
        
        logger.info(f"Created node {node_id}")
        return node
    
    async def get_node(self, node_id: str) -> Node:
        """Get node by ID with validation."""
        await self.validator.validate_node_id(node_id)
        
        node = await self.node_repository.get_by_id(node_id)
        if not node:
            raise NodeNotFoundError(f"Node {node_id} not found")
            
        return node
    
    async def update_node(self, node_id: str, request: NodeUpdateRequest) -> Node:
        """Update node configuration with validation."""
        node = await self.get_node(node_id)
        
        # Validate update request
        await self.validator.validate_update_request(node, request)
        
        # Update fields
        if request.name:
            node.name = request.name
        if request.node_type:
            node.node_type = request.node_type
        if request.pool_id:
            node.pool_id = request.pool_id
        if request.configuration:
            node.configuration = request.configuration
        if request.status:
            node.status = request.status
            
        node.updated_at = datetime.utcnow()
        
        # Save changes
        await self.node_repository.update(node)
        
        logger.info(f"Updated node {node_id}")
        return node
    
    async def start_node(self, node_id: str) -> Dict[str, Any]:
        """Start a node and return status."""
        node = await self.get_node(node_id)
        
        if node.status == "active":
            return {
                "node_id": node_id,
                "status": "active",
                "message": "Node is already active"
            }
        
        if node.status not in ["inactive", "stopped"]:
            raise InvalidNodeStatusError(f"Cannot start node in status: {node.status}")
        
        # Update status to starting
        node.status = "starting"
        node.updated_at = datetime.utcnow()
        await self.node_repository.update(node)
        
        try:
            # Initialize node resources
            await self.resource_monitor.start_monitoring(node_id)
            
            # Update status to active
            node.status = "active"
            node.last_heartbeat = datetime.utcnow()
            node.updated_at = datetime.utcnow()
            await self.node_repository.update(node)
            
            logger.info(f"Started node {node_id}")
            return {
                "node_id": node_id,
                "status": "active",
                "started_at": node.last_heartbeat.isoformat()
            }
            
        except Exception as e:
            # Rollback status on error
            node.status = "error"
            node.updated_at = datetime.utcnow()
            await self.node_repository.update(node)
            
            logger.error(f"Failed to start node {node_id}: {e}")
            raise
    
    async def stop_node(self, node_id: str) -> Dict[str, Any]:
        """Stop a node and return status."""
        node = await self.get_node(node_id)
        
        if node.status == "inactive":
            return {
                "node_id": node_id,
                "status": "inactive",
                "message": "Node is already inactive"
            }
        
        if node.status not in ["active", "running"]:
            raise InvalidNodeStatusError(f"Cannot stop node in status: {node.status}")
        
        # Update status to stopping
        node.status = "stopping"
        node.updated_at = datetime.utcnow()
        await self.node_repository.update(node)
        
        try:
            # Stop resource monitoring
            await self.resource_monitor.stop_monitoring(node_id)
            
            # Update status to inactive
            node.status = "inactive"
            node.updated_at = datetime.utcnow()
            await self.node_repository.update(node)
            
            logger.info(f"Stopped node {node_id}")
            return {
                "node_id": node_id,
                "status": "inactive",
                "stopped_at": node.updated_at.isoformat()
            }
            
        except Exception as e:
            # Rollback status on error
            node.status = "error"
            node.updated_at = datetime.utcnow()
            await self.node_repository.update(node)
            
            logger.error(f"Failed to stop node {node_id}: {e}")
            raise
    
    async def list_nodes(
        self,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
        pool_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """List nodes with pagination and filtering."""
        offset = (page - 1) * limit
        
        nodes = await self.node_repository.list(
            offset=offset,
            limit=limit,
            status=status,
            pool_id=pool_id
        )
        
        total = await self.node_repository.count(
            status=status,
            pool_id=pool_id
        )
        
        return {
            "nodes": nodes,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    
    async def get_node_resources(self, node_id: str, time_range: str = "1h") -> Dict[str, Any]:
        """Get current resource utilization for a node."""
        node = await self.get_node(node_id)
        
        # Get resource metrics
        metrics = await self.resource_monitor.get_metrics(
            node_id=node_id,
            time_range=time_range
        )
        
        return {
            "node_id": node_id,
            "time_range": time_range,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
```

### PoOT Validator Implementation

#### PoOTValidator Class
```python
import hashlib
import hmac
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio

from node.poot.poot_models import PoOTValidation, PoOTScore
from node.utils.exceptions import InvalidPoOTError, PoOTValidationError
from node.repository.poot_repository import PoOTRepository

class PoOTValidator:
    def __init__(self, poot_repository: PoOTRepository):
        self.poot_repository = poot_repository
        self.validation_timeout = 30  # seconds
        
    async def validate_poot(
        self,
        node_id: str,
        output_data: str,
        timestamp: datetime,
        nonce: str
    ) -> PoOTValidation:
        """Validate PoOT for a specific node."""
        validation_id = f"poot_val_{node_id}_{int(time.time())}"
        
        try:
            # Validate input parameters
            await self._validate_inputs(node_id, output_data, timestamp, nonce)
            
            # Calculate output hash
            output_hash = hashlib.sha256(output_data.encode()).hexdigest()
            
            # Perform PoOT validation
            validation_result = await self._perform_validation(
                node_id, output_data, timestamp, nonce
            )
            
            # Calculate confidence score
            confidence = await self._calculate_confidence(validation_result)
            
            # Create validation record
            validation = PoOTValidation(
                validation_id=validation_id,
                node_id=node_id,
                output_data=output_data,
                output_hash=output_hash,
                timestamp=timestamp,
                score=validation_result["score"],
                confidence=confidence,
                is_valid=validation_result["is_valid"],
                validation_time_ms=validation_result["validation_time_ms"],
                errors=validation_result.get("errors", [])
            )
            
            # Save validation record
            await self.poot_repository.save_validation(validation)
            
            return validation
            
        except Exception as e:
            logger.error(f"PoOT validation failed for node {node_id}: {e}")
            
            # Create failed validation record
            validation = PoOTValidation(
                validation_id=validation_id,
                node_id=node_id,
                output_data=output_data,
                output_hash="",
                timestamp=timestamp,
                score=0.0,
                confidence=0.0,
                is_valid=False,
                validation_time_ms=0,
                errors=[str(e)]
            )
            
            await self.poot_repository.save_validation(validation)
            raise PoOTValidationError(f"Validation failed: {e}")
    
    async def batch_validate_poot(
        self,
        validations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate PoOT for multiple nodes in batch."""
        batch_id = f"batch_{int(time.time())}"
        results = []
        
        # Process validations concurrently
        tasks = []
        for validation_request in validations:
            task = self.validate_poot(
                node_id=validation_request["node_id"],
                output_data=validation_request["output_data"],
                timestamp=validation_request["timestamp"],
                nonce=validation_request["nonce"]
            )
            tasks.append(task)
        
        try:
            # Wait for all validations to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            valid_count = 0
            invalid_count = 0
            error_count = 0
            
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_count += 1
                    processed_results.append({
                        "node_id": validations[i]["node_id"],
                        "is_valid": False,
                        "error": str(result)
                    })
                else:
                    processed_results.append(result)
                    if result.is_valid:
                        valid_count += 1
                    else:
                        invalid_count += 1
            
            return {
                "batch_id": batch_id,
                "results": processed_results,
                "summary": {
                    "total": len(validations),
                    "valid": valid_count,
                    "invalid": invalid_count,
                    "errors": error_count
                }
            }
            
        except Exception as e:
            logger.error(f"Batch PoOT validation failed: {e}")
            raise PoOTValidationError(f"Batch validation failed: {e}")
    
    async def _validate_inputs(
        self,
        node_id: str,
        output_data: str,
        timestamp: datetime,
        nonce: str
    ) -> None:
        """Validate input parameters."""
        # Check timestamp (must be within last 24 hours)
        now = datetime.utcnow()
        if timestamp > now or timestamp < now - timedelta(hours=24):
            raise InvalidPoOTError("Timestamp out of valid range")
        
        # Check output data size (max 1MB)
        if len(output_data) > 1024 * 1024:
            raise InvalidPoOTError("Output data too large")
        
        # Check nonce format
        if not nonce or len(nonce) < 8:
            raise InvalidPoOTError("Invalid nonce")
        
        # Check node exists and is active
        node = await self.node_repository.get_by_id(node_id)
        if not node or node.status != "active":
            raise InvalidPoOTError("Node not found or inactive")
    
    async def _perform_validation(
        self,
        node_id: str,
        output_data: str,
        timestamp: datetime,
        nonce: str
    ) -> Dict[str, Any]:
        """Perform the actual PoOT validation."""
        start_time = time.time()
        
        try:
            # Calculate output hash
            output_hash = hashlib.sha256(output_data.encode()).hexdigest()
            
            # Verify nonce uniqueness
            is_nonce_unique = await self._verify_nonce_uniqueness(node_id, nonce)
            
            # Calculate PoOT score based on multiple factors
            score = await self._calculate_poot_score(
                node_id, output_data, timestamp, nonce
            )
            
            # Determine if validation is valid (score >= 70)
            is_valid = score >= 70.0 and is_nonce_unique
            
            validation_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                "score": score,
                "is_valid": is_valid,
                "validation_time_ms": validation_time_ms,
                "errors": [] if is_valid else ["Score below threshold"]
            }
            
        except Exception as e:
            validation_time_ms = int((time.time() - start_time) * 1000)
            return {
                "score": 0.0,
                "is_valid": False,
                "validation_time_ms": validation_time_ms,
                "errors": [str(e)]
            }
    
    async def _calculate_poot_score(
        self,
        node_id: str,
        output_data: str,
        timestamp: datetime,
        nonce: str
    ) -> float:
        """Calculate PoOT score based on multiple factors."""
        score = 0.0
        
        # Factor 1: Output data complexity (0-30 points)
        complexity_score = min(30.0, len(output_data) / 1000)
        score += complexity_score
        
        # Factor 2: Timestamp freshness (0-25 points)
        now = datetime.utcnow()
        age_minutes = (now - timestamp).total_seconds() / 60
        freshness_score = max(0, 25.0 - (age_minutes / 10))
        score += freshness_score
        
        # Factor 3: Node reliability (0-25 points)
        node_reliability = await self._get_node_reliability(node_id)
        score += node_reliability * 25.0
        
        # Factor 4: Nonce randomness (0-20 points)
        randomness_score = self._calculate_nonce_randomness(nonce)
        score += randomness_score
        
        return min(100.0, score)
    
    async def _get_node_reliability(self, node_id: str) -> float:
        """Get node reliability score based on historical performance."""
        # Get recent validation history
        recent_validations = await self.poot_repository.get_recent_validations(
            node_id=node_id,
            limit=100
        )
        
        if not recent_validations:
            return 0.5  # Default reliability for new nodes
        
        # Calculate success rate
        valid_count = sum(1 for v in recent_validations if v.is_valid)
        total_count = len(recent_validations)
        success_rate = valid_count / total_count if total_count > 0 else 0.0
        
        # Calculate average score
        avg_score = sum(v.score for v in recent_validations) / total_count if total_count > 0 else 0.0
        
        # Combine success rate and average score
        reliability = (success_rate * 0.7) + ((avg_score / 100.0) * 0.3)
        
        return min(1.0, reliability)
    
    def _calculate_nonce_randomness(self, nonce: str) -> float:
        """Calculate nonce randomness score."""
        if len(nonce) < 16:
            return 0.0
        
        # Simple entropy calculation
        char_counts = {}
        for char in nonce:
            char_counts[char] = char_counts.get(char, 0) + 1
        
        # Calculate entropy
        entropy = 0.0
        for count in char_counts.values():
            probability = count / len(nonce)
            entropy -= probability * (probability.bit_length() - 1)
        
        # Normalize to 0-20 range
        return min(20.0, entropy * 5.0)
    
    async def _verify_nonce_uniqueness(self, node_id: str, nonce: str) -> bool:
        """Verify that nonce hasn't been used recently."""
        # Check if nonce was used in last 24 hours
        recent_validation = await self.poot_repository.get_by_nonce(
            node_id=node_id,
            nonce=nonce,
            since=datetime.utcnow() - timedelta(hours=24)
        )
        
        return recent_validation is None
```

## Distroless Container Implementation

### Dockerfile Structure
```dockerfile
# Multi-stage build for Node Management Service
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILDKIT_INLINE_CACHE=1
ARG BUILDKIT_PROGRESS=plain

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy source code
COPY . .

# Build the application
RUN python -m compileall .

# Production stage with distroless base
FROM gcr.io/distroless/python3-debian11

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY --from=builder /app /app

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8083

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import requests; requests.get('http://localhost:8083/health')"]

# Run the application
ENTRYPOINT ["python", "main.py"]
```

### Docker Compose Configuration
```yaml
version: '3.8'

services:
  node-management:
    build:
      context: .
      dockerfile: Dockerfile
      target: final
    image: ghcr.io/hamigames/lucid/node-management:latest
    container_name: lucid-node-management
    hostname: node-management
    
    environment:
      # Service configuration
      - SERVICE_NAME=node-management-service
      - VERSION=1.0.0
      - PORT=8083
      - ENVIRONMENT=production
      
      # Database configuration
      - MONGODB_URL=mongodb://lucid:lucid@lucid-mongo:27017/lucid?authSource=admin
      - MONGODB_DATABASE=lucid
      
      # Redis configuration
      - REDIS_URL=redis://lucid-redis:6379/0
      
      # Logging configuration
      - LOG_LEVEL=INFO
      - LOG_FORMAT=json
      
      # Security configuration
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      
      # Node management configuration
      - NODE_HEARTBEAT_INTERVAL=30
      - RESOURCE_COLLECTION_INTERVAL=60
      - POOT_VALIDATION_TIMEOUT=30
      - PAYOUT_BATCH_SIZE=100
      
    ports:
      - "8083:8083"
    
    volumes:
      # Configuration files
      - ./config/node-management.conf:/app/config/node-management.conf:ro
      
      # Logs (if needed for debugging)
      - node-management-logs:/app/logs
    
    networks:
      - lucid-network
    
    depends_on:
      - lucid-mongo
      - lucid-redis
    
    restart: unless-stopped
    
    # Resource limits
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    
    # Security configuration
    security_opt:
      - no-new-privileges:true
    
    read_only: true
    tmpfs:
      - /tmp
      - /app/logs
    
    # User configuration (non-root)
    user: "1000:1000"

volumes:
  node-management-logs:
    driver: local

networks:
  lucid-network:
    external: true
```

### Health Check Implementation
```python
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
import asyncio
import logging
from datetime import datetime

from node.config.database import get_database
from node.resources.resource_monitor import ResourceMonitor

logger = logging.getLogger(__name__)

class HealthChecker:
    def __init__(self, app: FastAPI):
        self.app = app
        self.db = get_database()
        self.resource_monitor = ResourceMonitor()
        
    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "checks": {}
        }
        
        # Check database connectivity
        db_status = await self._check_database()
        health_status["checks"]["database"] = db_status
        
        # Check resource monitoring
        resource_status = await self._check_resource_monitoring()
        health_status["checks"]["resource_monitoring"] = resource_status
        
        # Check Redis connectivity
        redis_status = await self._check_redis()
        health_status["checks"]["redis"] = redis_status
        
        # Check node connectivity
        node_status = await self._check_node_connectivity()
        health_status["checks"]["nodes"] = node_status
        
        # Determine overall status
        all_healthy = all(
            check["status"] == "healthy" 
            for check in health_status["checks"].values()
        )
        
        if not all_healthy:
            health_status["status"] = "unhealthy"
        
        return health_status
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            # Test database connection
            await self.db.command("ping")
            
            # Test collection access
            nodes_collection = self.db.nodes
            await nodes_collection.find_one()
            
            return {
                "status": "healthy",
                "message": "Database connection successful",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Database connection failed: {e}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_resource_monitoring(self) -> Dict[str, Any]:
        """Check resource monitoring system."""
        try:
            # Test resource monitor
            is_running = await self.resource_monitor.is_running()
            
            if is_running:
                return {
                    "status": "healthy",
                    "message": "Resource monitoring active",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Resource monitoring inactive",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Resource monitoring health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Resource monitoring failed: {e}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity."""
        try:
            import redis.asyncio as redis
            
            redis_client = redis.from_url("redis://lucid-redis:6379/0")
            await redis_client.ping()
            await redis_client.close()
            
            return {
                "status": "healthy",
                "message": "Redis connection successful",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Redis connection failed: {e}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_node_connectivity(self) -> Dict[str, Any]:
        """Check connectivity to managed nodes."""
        try:
            # Get active nodes
            nodes_collection = self.db.nodes
            active_nodes = await nodes_collection.find(
                {"status": "active"}
            ).to_list(100)
            
            # Check heartbeat status
            now = datetime.utcnow()
            healthy_nodes = 0
            total_nodes = len(active_nodes)
            
            for node in active_nodes:
                if node.get("last_heartbeat"):
                    heartbeat_age = (now - node["last_heartbeat"]).total_seconds()
                    if heartbeat_age < 300:  # 5 minutes
                        healthy_nodes += 1
            
            health_ratio = healthy_nodes / total_nodes if total_nodes > 0 else 1.0
            
            if health_ratio >= 0.8:  # 80% of nodes healthy
                status = "healthy"
                message = f"{healthy_nodes}/{total_nodes} nodes healthy"
            else:
                status = "unhealthy"
                message = f"Only {healthy_nodes}/{total_nodes} nodes healthy"
            
            return {
                "status": status,
                "message": message,
                "healthy_nodes": healthy_nodes,
                "total_nodes": total_nodes,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Node connectivity health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Node connectivity check failed: {e}",
                "timestamp": datetime.utcnow().isoformat()
            }
```

## Configuration Management

### Settings Configuration
```python
from pydantic import BaseSettings, Field
from typing import Optional, List
import os

class NodeManagementSettings(BaseSettings):
    # Service configuration
    service_name: str = Field(default="node-management-service", env="SERVICE_NAME")
    version: str = Field(default="1.0.0", env="VERSION")
    port: int = Field(default=8083, env="PORT")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Database configuration
    mongodb_url: str = Field(env="MONGODB_URL")
    mongodb_database: str = Field(default="lucid", env="MONGODB_DATABASE")
    
    # Redis configuration
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Security configuration
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    encryption_key: str = Field(env="ENCRYPTION_KEY")
    
    # Node management configuration
    node_heartbeat_interval: int = Field(default=30, env="NODE_HEARTBEAT_INTERVAL")
    resource_collection_interval: int = Field(default=60, env="RESOURCE_COLLECTION_INTERVAL")
    poot_validation_timeout: int = Field(default=30, env="POOT_VALIDATION_TIMEOUT")
    payout_batch_size: int = Field(default=100, env="PAYOUT_BATCH_SIZE")
    
    # Logging configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Rate limiting configuration
    rate_limit_per_minute: int = Field(default=1000, env="RATE_LIMIT_PER_MINUTE")
    
    # Resource monitoring configuration
    resource_retention_days: int = Field(default=90, env="RESOURCE_RETENTION_DAYS")
    resource_cleanup_interval: int = Field(default=3600, env="RESOURCE_CLEANUP_INTERVAL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = NodeManagementSettings()
```

## Error Handling

### Custom Exceptions
```python
class NodeManagementError(Exception):
    """Base exception for node management errors."""
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class NodeNotFoundError(NodeManagementError):
    """Raised when a node is not found."""
    def __init__(self, node_id: str):
        super().__init__(f"Node {node_id} not found", "LUCID_ERR_5001")

class InvalidNodeStatusError(NodeManagementError):
    """Raised when node status is invalid for operation."""
    def __init__(self, message: str):
        super().__init__(message, "LUCID_ERR_5003")

class PoolNotFoundError(NodeManagementError):
    """Raised when a pool is not found."""
    def __init__(self, pool_id: str):
        super().__init__(f"Pool {pool_id} not found", "LUCID_ERR_5002")

class InvalidPoOTError(NodeManagementError):
    """Raised when PoOT validation fails."""
    def __init__(self, message: str):
        super().__init__(message, "LUCID_ERR_5005")

class PayoutProcessingError(NodeManagementError):
    """Raised when payout processing fails."""
    def __init__(self, message: str):
        super().__init__(message, "LUCID_ERR_5006")

class ResourceLimitExceededError(NodeManagementError):
    """Raised when resource limits are exceeded."""
    def __init__(self, resource: str, limit: str):
        super().__init__(f"{resource} limit exceeded: {limit}", "LUCID_ERR_5004")
```

### Error Handler Middleware
```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import logging
import uuid
from datetime import datetime

from node.utils.exceptions import NodeManagementError

logger = logging.getLogger(__name__)

class ErrorHandlerMiddleware:
    def __init__(self, app: FastAPI):
        self.app = app
        
    async def __call__(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
            
        except NodeManagementError as e:
            return await self._handle_node_management_error(e, request)
            
        except HTTPException as e:
            return await self._handle_http_exception(e, request)
            
        except Exception as e:
            return await self._handle_unexpected_error(e, request)
    
    async def _handle_node_management_error(
        self, 
        error: NodeManagementError, 
        request: Request
    ) -> JSONResponse:
        """Handle node management specific errors."""
        request_id = str(uuid.uuid4())
        
        error_response = {
            "error": {
                "code": error.error_code or "LUCID_ERR_5000",
                "message": error.message,
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
                "path": str(request.url)
            }
        }
        
        logger.error(f"Node management error: {error.message}", extra={
            "request_id": request_id,
            "error_code": error.error_code,
            "path": str(request.url)
        })
        
        return JSONResponse(
            status_code=400,
            content=error_response
        )
    
    async def _handle_http_exception(
        self, 
        error: HTTPException, 
        request: Request
    ) -> JSONResponse:
        """Handle HTTP exceptions."""
        request_id = str(uuid.uuid4())
        
        error_response = {
            "error": {
                "code": f"HTTP_{error.status_code}",
                "message": error.detail,
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
                "path": str(request.url)
            }
        }
        
        logger.warning(f"HTTP error: {error.detail}", extra={
            "request_id": request_id,
            "status_code": error.status_code,
            "path": str(request.url)
        })
        
        return JSONResponse(
            status_code=error.status_code,
            content=error_response
        )
    
    async def _handle_unexpected_error(
        self, 
        error: Exception, 
        request: Request
    ) -> JSONResponse:
        """Handle unexpected errors."""
        request_id = str(uuid.uuid4())
        
        error_response = {
            "error": {
                "code": "LUCID_ERR_5999",
                "message": "Internal server error",
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
                "path": str(request.url)
            }
        }
        
        logger.error(f"Unexpected error: {str(error)}", extra={
            "request_id": request_id,
            "path": str(request.url)
        }, exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content=error_response
        )
```

This implementation guide provides a comprehensive foundation for building the Node Management Cluster with proper code structure, naming conventions, and distroless container implementation following the Lucid project standards.
