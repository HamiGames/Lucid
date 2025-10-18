# 03. Implementation Guide

## Overview

This document provides comprehensive implementation guidance for the Session Management Cluster, including code structure, naming conventions, service architecture, and integration patterns.

## Code Structure

### Project Layout
```
sessions/
├── api/
│   ├── __init__.py
│   ├── session_api.py          # FastAPI application
│   ├── middleware.py           # Custom middleware
│   └── dependencies.py         # Dependency injection
├── core/
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   ├── database.py            # Database connections
│   ├── security.py            # Security utilities
│   └── logging.py             # Logging configuration
├── models/
│   ├── __init__.py
│   ├── session.py             # Session models
│   ├── chunk.py               # Chunk models
│   └── pipeline.py            # Pipeline models
├── services/
│   ├── __init__.py
│   ├── session_service.py     # Session business logic
│   ├── chunk_service.py       # Chunk processing
│   ├── pipeline_service.py    # Pipeline orchestration
│   └── storage_service.py     # Storage management
├── pipeline/
│   ├── __init__.py
│   ├── pipeline_manager.py    # Pipeline orchestration
│   ├── stages/
│   │   ├── __init__.py
│   │   ├── recording_stage.py # Recording stage
│   │   ├── compression_stage.py # Compression stage
│   │   ├── encryption_stage.py # Encryption stage
│   │   └── storage_stage.py   # Storage stage
│   └── processors/
│       ├── __init__.py
│       ├── frame_processor.py # Frame processing
│       ├── chunk_processor.py # Chunk processing
│       └── quality_processor.py # Quality processing
├── recorder/
│   ├── __init__.py
│   ├── session_recorder.py    # Session recording
│   ├── rdp_client.py          # RDP client
│   └── frame_capture.py       # Frame capture
├── storage/
│   ├── __init__.py
│   ├── session_storage.py     # Session storage
│   ├── chunk_storage.py       # Chunk storage
│   └── metadata_storage.py    # Metadata storage
├── utils/
│   ├── __init__.py
│   ├── validators.py          # Validation utilities
│   ├── encoders.py            # Encoding utilities
│   └── metrics.py             # Metrics utilities
├── tests/
│   ├── __init__.py
│   ├── test_api.py            # API tests
│   ├── test_services.py       # Service tests
│   ├── test_pipeline.py       # Pipeline tests
│   └── test_recorder.py       # Recorder tests
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container definition
└── docker-compose.yml         # Local development
```

## Service Implementation

### 1. Session API Service

#### FastAPI Application Setup
```python
# sessions/api/session_api.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import uvicorn
from app.core.config import settings
from app.core.database import init_db
from app.api.v1 import session_router, chunk_router, pipeline_router
from app.core.middleware import RateLimitMiddleware, SecurityMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Lucid Session Management API",
    description="RDP session recording and processing system",
    version="1.0.0",
    lifespan=lifespan
)

# Security middleware
app.add_middleware(SecurityMiddleware)
app.add_middleware(RateLimitMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Include routers
app.include_router(session_router, prefix="/api/v1/sessions")
app.include_router(chunk_router, prefix="/api/v1/sessions")
app.include_router(pipeline_router, prefix="/api/v1/sessions")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "session-management-api"}

if __name__ == "__main__":
    uvicorn.run(
        "session_api:app",
        host="0.0.0.0",
        port=8087,
        reload=settings.DEBUG
    )
```

#### Session Router Implementation
```python
# sessions/api/v1/session_router.py
from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional
from datetime import datetime
import uuid

from app.core.auth import get_current_user
from app.core.rate_limit import rate_limit
from app.models.session import (
    CreateSessionRequest, UpdateSessionRequest, SessionResponse, 
    SessionListResponse, SessionStatisticsResponse
)
from app.services.session_service import SessionService
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

@router.post("/", response_model=SessionResponse)
@rate_limit(calls=10, period=60)  # 10 sessions per minute
async def create_session(
    session_request: CreateSessionRequest,
    current_user: dict = Depends(get_current_user),
    session_service: SessionService = Depends()
):
    """Create a new session."""
    
    # Validate user permissions
    if not current_user.get("can_create_sessions"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create sessions"
        )
    
    try:
        # Generate unique session ID
        session_id = f"sess-{uuid.uuid4().hex[:8]}"
        
        # Create session
        session = await session_service.create_session(
            session_id=session_id,
            name=session_request.name,
            description=session_request.description,
            rdp_config=session_request.rdp_config,
            recording_config=session_request.recording_config,
            storage_config=session_request.storage_config,
            metadata=session_request.metadata,
            user_id=current_user["user_id"]
        )
        
        logger.info(f"Created session {session_id} for user {current_user['user_id']}")
        
        return SessionResponse(
            session_id=session.session_id,
            status=session.status,
            created_at=session.created_at,
            started_at=session.started_at,
            stopped_at=session.stopped_at,
            rdp_config=session.rdp_config,
            recording_config=session.recording_config,
            storage_config=session.storage_config,
            metadata=session.metadata,
            statistics=session.statistics
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid session configuration: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to create session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/{session_id}", response_model=SessionResponse)
@rate_limit(calls=100, period=60)
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    session_service: SessionService = Depends()
):
    """Get session by ID."""
    
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check user access
    if session.metadata.owner != current_user["user_id"] and not current_user.get("admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this session"
        )
    
    return SessionResponse(
        session_id=session.session_id,
        status=session.status,
        created_at=session.created_at,
        started_at=session.started_at,
        stopped_at=session.stopped_at,
        rdp_config=session.rdp_config,
        recording_config=session.recording_config,
        storage_config=session.storage_config,
        metadata=session.metadata,
        statistics=session.statistics
    )

@router.get("/", response_model=SessionListResponse)
@rate_limit(calls=100, period=60)
async def list_sessions(
    status: Optional[str] = Query(None, description="Filter by status"),
    project: Optional[str] = Query(None, description="Filter by project"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    limit: int = Query(50, ge=1, le=100, description="Number of results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: dict = Depends(get_current_user),
    session_service: SessionService = Depends()
):
    """List sessions with filtering and pagination."""
    
    sessions, total = await session_service.list_sessions(
        user_id=current_user["user_id"],
        status=status,
        project=project,
        environment=environment,
        limit=limit,
        offset=offset,
        admin=current_user.get("admin", False)
    )
    
    session_responses = [
        SessionResponse(
            session_id=session.session_id,
            status=session.status,
            created_at=session.created_at,
            started_at=session.started_at,
            stopped_at=session.stopped_at,
            rdp_config=session.rdp_config,
            recording_config=session.recording_config,
            storage_config=session.storage_config,
            metadata=session.metadata,
            statistics=session.statistics
        )
        for session in sessions
    ]
    
    return SessionListResponse(
        sessions=session_responses,
        pagination={
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_next": offset + limit < total,
            "has_previous": offset > 0
        }
    )
```

### 2. Session Service Implementation

#### Session Service
```python
# sessions/services/session_service.py
from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.session import Session, CreateSessionRequest, UpdateSessionRequest
from app.models.chunk import Chunk
from app.services.pipeline_service import PipelineService
from app.services.storage_service import StorageService
from app.core.logging import get_logger

logger = get_logger(__name__)

class SessionService:
    def __init__(self, db: Session, pipeline_service: PipelineService, storage_service: StorageService):
        self.db = db
        self.pipeline_service = pipeline_service
        self.storage_service = storage_service
    
    async def create_session(
        self,
        session_id: str,
        name: str,
        description: Optional[str],
        rdp_config,
        recording_config,
        storage_config,
        metadata,
        user_id: str
    ) -> Session:
        """Create a new session."""
        
        # Validate RDP configuration
        await self._validate_rdp_config(rdp_config)
        
        # Create session record
        session = Session(
            session_id=session_id,
            name=name,
            status="created",
            rdp_config=rdp_config,
            recording_config=recording_config,
            storage_config=storage_config,
            metadata=metadata,
            created_at=datetime.utcnow()
        )
        
        # Set owner
        session.metadata.owner = user_id
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        # Initialize pipeline
        await self.pipeline_service.create_pipeline(session_id)
        
        # Initialize storage
        await self.storage_service.initialize_session_storage(session_id)
        
        logger.info(f"Created session {session_id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        return self.db.query(Session).filter(Session.session_id == session_id).first()
    
    async def list_sessions(
        self,
        user_id: str,
        status: Optional[str] = None,
        project: Optional[str] = None,
        environment: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        admin: bool = False
    ) -> Tuple[List[Session], int]:
        """List sessions with filtering."""
        
        query = self.db.query(Session)
        
        # Apply user filter (unless admin)
        if not admin:
            query = query.filter(Session.metadata.owner == user_id)
        
        # Apply filters
        if status:
            query = query.filter(Session.status == status)
        if project:
            query = query.filter(Session.metadata.project == project)
        if environment:
            query = query.filter(Session.metadata.environment == environment)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        sessions = query.offset(offset).limit(limit).all()
        
        return sessions, total
    
    async def start_recording(self, session_id: str) -> Session:
        """Start session recording."""
        
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.status != "created":
            raise ValueError(f"Session {session_id} is not in created state")
        
        # Start pipeline
        await self.pipeline_service.start_pipeline(session_id)
        
        # Update session status
        session.status = "recording"
        session.started_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Started recording for session {session_id}")
        return session
    
    async def stop_recording(self, session_id: str) -> Session:
        """Stop session recording."""
        
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.status != "recording":
            raise ValueError(f"Session {session_id} is not recording")
        
        # Stop pipeline
        await self.pipeline_service.stop_pipeline(session_id)
        
        # Update session status
        session.status = "stopped"
        session.stopped_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Stopped recording for session {session_id}")
        return session
    
    async def _validate_rdp_config(self, rdp_config):
        """Validate RDP configuration."""
        
        # Validate host connectivity
        import socket
        try:
            socket.create_connection((rdp_config.host, rdp_config.port), timeout=5)
        except (socket.error, socket.timeout):
            raise ValueError(f"Unable to connect to RDP host {rdp_config.host}:{rdp_config.port}")
        
        # Validate credentials (if provided)
        if rdp_config.password:
            # Additional credential validation can be added here
            pass
```

### 3. Pipeline Service Implementation

#### Pipeline Manager
```python
# sessions/pipeline/pipeline_manager.py
import asyncio
from typing import Dict, List
from datetime import datetime
from app.models.pipeline import Pipeline, PipelineStage, StageStatus
from app.pipeline.stages.recording_stage import RecordingStage
from app.pipeline.stages.compression_stage import CompressionStage
from app.pipeline.stages.encryption_stage import EncryptionStage
from app.pipeline.stages.storage_stage import StorageStage
from app.core.logging import get_logger

logger = get_logger(__name__)

class PipelineManager:
    def __init__(self):
        self.stages = {
            "recording": RecordingStage(),
            "compression": CompressionStage(),
            "encryption": EncryptionStage(),
            "storage": StorageStage()
        }
        self.active_pipelines: Dict[str, Pipeline] = {}
    
    async def create_pipeline(self, session_id: str) -> Pipeline:
        """Create a new pipeline for a session."""
        
        pipeline = Pipeline(
            session_id=session_id,
            pipeline_status="inactive",
            stages=[
                PipelineStage(stage_name="recording", status=StageStatus.INACTIVE),
                PipelineStage(stage_name="compression", status=StageStatus.INACTIVE),
                PipelineStage(stage_name="encryption", status=StageStatus.INACTIVE),
                PipelineStage(stage_name="storage", status=StageStatus.INACTIVE)
            ]
        )
        
        self.active_pipelines[session_id] = pipeline
        logger.info(f"Created pipeline for session {session_id}")
        return pipeline
    
    async def start_pipeline(self, session_id: str):
        """Start the pipeline for a session."""
        
        if session_id not in self.active_pipelines:
            await self.create_pipeline(session_id)
        
        pipeline = self.active_pipelines[session_id]
        pipeline.pipeline_status = "active"
        
        # Start all stages
        for stage in pipeline.stages:
            stage.status = StageStatus.ACTIVE
            await self.stages[stage.stage_name].start(session_id)
        
        logger.info(f"Started pipeline for session {session_id}")
    
    async def stop_pipeline(self, session_id: str):
        """Stop the pipeline for a session."""
        
        if session_id not in self.active_pipelines:
            return
        
        pipeline = self.active_pipelines[session_id]
        pipeline.pipeline_status = "stopped"
        
        # Stop all stages
        for stage in pipeline.stages:
            stage.status = StageStatus.INACTIVE
            await self.stages[stage.stage_name].stop(session_id)
        
        logger.info(f"Stopped pipeline for session {session_id}")
    
    async def process_chunk(self, session_id: str, chunk_data: bytes) -> bool:
        """Process a chunk through the pipeline."""
        
        if session_id not in self.active_pipelines:
            return False
        
        pipeline = self.active_pipelines[session_id]
        if pipeline.pipeline_status != "active":
            return False
        
        try:
            # Process through each stage
            processed_data = chunk_data
            
            for stage in pipeline.stages:
                if stage.status != StageStatus.ACTIVE:
                    continue
                
                start_time = datetime.utcnow()
                
                # Process chunk
                processed_data = await self.stages[stage.stage_name].process(
                    session_id, processed_data
                )
                
                # Update metrics
                processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                stage.metrics.items_processed += 1
                stage.metrics.processing_time_ms = processing_time
                stage.last_processed = datetime.utcnow()
            
            return True
            
        except Exception as e:
            logger.error(f"Pipeline processing error for session {session_id}: {str(e)}")
            pipeline.pipeline_status = "error"
            return False
    
    async def get_pipeline_status(self, session_id: str) -> Optional[Pipeline]:
        """Get pipeline status for a session."""
        return self.active_pipelines.get(session_id)
```

### 4. Recording Stage Implementation

#### Recording Stage
```python
# sessions/pipeline/stages/recording_stage.py
import asyncio
from typing import Dict, Optional
from datetime import datetime
from app.recorder.session_recorder import SessionRecorder
from app.core.logging import get_logger

logger = get_logger(__name__)

class RecordingStage:
    def __init__(self):
        self.active_recorders: Dict[str, SessionRecorder] = {}
    
    async def start(self, session_id: str):
        """Start recording for a session."""
        
        # Get session configuration
        from app.services.session_service import SessionService
        session_service = SessionService()
        session = await session_service.get_session(session_id)
        
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Create recorder
        recorder = SessionRecorder(
            session_id=session_id,
            rdp_config=session.rdp_config,
            recording_config=session.recording_config
        )
        
        # Start recording
        await recorder.start()
        self.active_recorders[session_id] = recorder
        
        logger.info(f"Started recording for session {session_id}")
    
    async def stop(self, session_id: str):
        """Stop recording for a session."""
        
        if session_id in self.active_recorders:
            recorder = self.active_recorders[session_id]
            await recorder.stop()
            del self.active_recorders[session_id]
            
            logger.info(f"Stopped recording for session {session_id}")
    
    async def process(self, session_id: str, data: bytes) -> bytes:
        """Process recording data."""
        
        if session_id not in self.active_recorders:
            return data
        
        recorder = self.active_recorders[session_id]
        
        # Capture frame
        frame_data = await recorder.capture_frame()
        
        # Process frame
        processed_data = await recorder.process_frame(frame_data)
        
        return processed_data
```

### 5. Session Recorder Implementation

#### Session Recorder
```python
# sessions/recorder/session_recorder.py
import asyncio
from typing import Optional
from datetime import datetime
from app.recorder.rdp_client import RDPClient
from app.recorder.frame_capture import FrameCapture
from app.core.logging import get_logger

logger = get_logger(__name__)

class SessionRecorder:
    def __init__(self, session_id: str, rdp_config, recording_config):
        self.session_id = session_id
        self.rdp_config = rdp_config
        self.recording_config = recording_config
        self.rdp_client: Optional[RDPClient] = None
        self.frame_capture: Optional[FrameCapture] = None
        self.is_recording = False
        self.frame_count = 0
        self.start_time: Optional[datetime] = None
    
    async def start(self):
        """Start recording session."""
        
        # Create RDP client
        self.rdp_client = RDPClient(
            host=self.rdp_config.host,
            port=self.rdp_config.port,
            username=self.rdp_config.username,
            password=self.rdp_config.password,
            domain=self.rdp_config.domain
        )
        
        # Connect to RDP server
        await self.rdp_client.connect()
        
        # Create frame capture
        self.frame_capture = FrameCapture(
            rdp_client=self.rdp_client,
            frame_rate=self.recording_config.frame_rate,
            resolution=self.recording_config.resolution,
            quality=self.recording_config.quality
        )
        
        # Start recording
        self.is_recording = True
        self.start_time = datetime.utcnow()
        
        # Start frame capture loop
        asyncio.create_task(self._capture_loop())
        
        logger.info(f"Started recording session {self.session_id}")
    
    async def stop(self):
        """Stop recording session."""
        
        self.is_recording = False
        
        if self.frame_capture:
            await self.frame_capture.stop()
        
        if self.rdp_client:
            await self.rdp_client.disconnect()
        
        logger.info(f"Stopped recording session {self.session_id}")
    
    async def capture_frame(self) -> bytes:
        """Capture a single frame."""
        
        if not self.frame_capture or not self.is_recording:
            return b""
        
        frame_data = await self.frame_capture.capture_frame()
        self.frame_count += 1
        
        return frame_data
    
    async def process_frame(self, frame_data: bytes) -> bytes:
        """Process captured frame."""
        
        if not frame_data:
            return b""
        
        # Apply quality settings
        processed_data = await self._apply_quality_settings(frame_data)
        
        # Apply compression if enabled
        if self.recording_config.compression != "none":
            processed_data = await self._compress_frame(processed_data)
        
        return processed_data
    
    async def _capture_loop(self):
        """Main capture loop."""
        
        frame_interval = 1.0 / self.recording_config.frame_rate
        
        while self.is_recording:
            start_time = datetime.utcnow()
            
            try:
                # Capture frame
                frame_data = await self.capture_frame()
                
                # Process frame
                processed_data = await self.process_frame(frame_data)
                
                # Send to pipeline
                from app.services.pipeline_service import PipelineService
                pipeline_service = PipelineService()
                await pipeline_service.process_chunk(self.session_id, processed_data)
                
            except Exception as e:
                logger.error(f"Frame capture error: {str(e)}")
            
            # Wait for next frame
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            sleep_time = max(0, frame_interval - elapsed)
            await asyncio.sleep(sleep_time)
    
    async def _apply_quality_settings(self, frame_data: bytes) -> bytes:
        """Apply quality settings to frame."""
        
        # Quality processing implementation
        # This would include resolution scaling, bitrate adjustment, etc.
        return frame_data
    
    async def _compress_frame(self, frame_data: bytes) -> bytes:
        """Compress frame data."""
        
        if self.recording_config.compression == "zstd":
            import zstandard as zstd
            compressor = zstd.ZstdCompressor()
            return compressor.compress(frame_data)
        elif self.recording_config.compression == "lz4":
            import lz4.frame
            return lz4.frame.compress(frame_data)
        else:
            return frame_data
```

## Configuration Management

### Environment Configuration
```python
# sessions/core/config.py
from pydantic import BaseSettings, validator
from typing import List, Optional

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Lucid Session Management"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8087
    
    # Database
    MONGODB_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Storage
    CHUNK_STORAGE_PATH: str = "/storage/chunks"
    SESSION_STORAGE_PATH: str = "/storage/sessions"
    MAX_STORAGE_SIZE_GB: int = 1000
    
    # Recording
    DEFAULT_FRAME_RATE: int = 30
    DEFAULT_RESOLUTION: str = "1920x1080"
    DEFAULT_QUALITY: str = "high"
    DEFAULT_COMPRESSION: str = "zstd"
    
    # Pipeline
    PIPELINE_BUFFER_SIZE: int = 1000
    PIPELINE_WORKER_COUNT: int = 4
    PIPELINE_TIMEOUT_SECONDS: int = 30
    
    # Security
    SECRET_KEY: str
    ALLOWED_HOSTS: List[str] = ["*"]
    ALLOWED_ORIGINS: List[str] = []
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE_URL: str = "redis://localhost:6379/1"
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 9090
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    @validator('ALLOWED_HOSTS', pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(',')]
        return v
    
    @validator('ALLOWED_ORIGINS', pre=True)
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

## Naming Conventions

### Service Names
- **Session Management API**: `session-management-api`
- **Pipeline Manager**: `pipeline-manager`
- **Session Recorder**: `session-recorder`
- **Chunk Processor**: `chunk-processor`
- **Session Storage**: `session-storage`

### Container Names
- **API Service**: `lucid-session-api`
- **Pipeline Service**: `lucid-pipeline-manager`
- **Recorder Service**: `lucid-session-recorder`
- **Processor Service**: `lucid-chunk-processor`
- **Storage Service**: `lucid-session-storage`

### Network Names
- **Internal Network**: `session-management-net`
- **Database Network**: `session-db-net`
- **Storage Network**: `session-storage-net`

## Integration Patterns

### Service Communication
```python
# Inter-service communication using gRPC
from grpclib.client import Channel
from app.proto.session_pb2 import SessionRequest, SessionResponse
from app.proto.session_grpc import SessionServiceStub

class SessionClient:
    def __init__(self, host: str, port: int):
        self.channel = Channel(host, port)
        self.stub = SessionServiceStub(self.channel)
    
    async def create_session(self, request: SessionRequest) -> SessionResponse:
        return await self.stub.create_session(request)
    
    async def close(self):
        self.channel.close()
```

### Event-Driven Architecture
```python
# Event publishing and subscription
from app.core.events import EventPublisher, EventSubscriber

class SessionEventPublisher:
    def __init__(self):
        self.publisher = EventPublisher()
    
    async def publish_session_created(self, session_id: str, user_id: str):
        await self.publisher.publish("session.created", {
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def publish_session_started(self, session_id: str):
        await self.publisher.publish("session.started", {
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        })

class SessionEventSubscriber:
    def __init__(self):
        self.subscriber = EventSubscriber()
    
    async def subscribe_to_session_events(self):
        await self.subscriber.subscribe("session.*", self.handle_session_event)
    
    async def handle_session_event(self, event_type: str, event_data: dict):
        if event_type == "session.created":
            await self.handle_session_created(event_data)
        elif event_type == "session.started":
            await self.handle_session_started(event_data)
    
    async def handle_session_created(self, event_data: dict):
        # Handle session created event
        pass
    
    async def handle_session_started(self, event_data: dict):
        # Handle session started event
        pass
```

## Error Handling

### Custom Exception Classes
```python
# sessions/core/exceptions.py
class SessionManagementError(Exception):
    """Base exception for session management errors."""
    pass

class SessionNotFoundError(SessionManagementError):
    """Raised when session is not found."""
    pass

class SessionConfigurationError(SessionManagementError):
    """Raised when session configuration is invalid."""
    pass

class PipelineError(SessionManagementError):
    """Raised when pipeline processing fails."""
    pass

class RecordingError(SessionManagementError):
    """Raised when recording fails."""
    pass

class StorageError(SessionManagementError):
    """Raised when storage operation fails."""
    pass
```

### Error Handling Middleware
```python
# sessions/api/middleware.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from app.core.exceptions import SessionManagementError
from app.core.logging import get_logger

logger = get_logger(__name__)

async def error_handler_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except SessionManagementError as e:
        logger.error(f"Session management error: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "LUCID_ERR_3000",
                    "message": str(e),
                    "request_id": request.headers.get("X-Request-ID", "unknown"),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "LUCID_ERR_3099",
                    "message": "Internal server error",
                    "request_id": request.headers.get("X-Request-ID", "unknown"),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
```

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-XX  
**Next Review**: 2024-04-XX
