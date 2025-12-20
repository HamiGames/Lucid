#!/usr/bin/env python3
"""
Lucid Session Management Pipeline Manager
Handles the complete session processing pipeline with state machine
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
import json
import uuid

from .state_machine import PipelineStateMachine, PipelineState, StateTransition
from .config import PipelineConfig
from ..core.logging import get_logger

logger = get_logger(__name__)

@dataclass
class PipelineMetrics:
    """Pipeline performance metrics"""
    total_chunks_processed: int = 0
    total_processing_time_ms: float = 0.0
    average_processing_time_ms: float = 0.0
    error_count: int = 0
    last_processed_at: Optional[datetime] = None
    throughput_chunks_per_second: float = 0.0

@dataclass
class PipelineStage:
    """Pipeline stage configuration"""
    stage_name: str
    stage_type: str
    status: str = "inactive"
    worker_count: int = 1
    buffer_size: int = 1000
    timeout_seconds: int = 30
    retry_count: int = 3
    metrics: PipelineMetrics = field(default_factory=PipelineMetrics)
    last_error: Optional[str] = None

@dataclass
class SessionPipeline:
    """Session pipeline instance"""
    session_id: str
    pipeline_id: str
    current_state: PipelineState
    stages: List[PipelineStage]
    config: PipelineConfig
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class PipelineManager:
    """
    Main pipeline manager for session processing
    Manages the complete lifecycle of session processing pipelines
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.state_machine = PipelineStateMachine()
        self.active_pipelines: Dict[str, SessionPipeline] = {}
        self.pipeline_workers: Dict[str, List[asyncio.Task]] = {}
        self._shutdown_event = asyncio.Event()
        
        # Initialize default pipeline stages
        self._initialize_default_stages()
        
        logger.info("Pipeline Manager initialized")
    
    def _initialize_default_stages(self):
        """Initialize default pipeline stages with 6 states as required by Step 15"""
        self.default_stages = [
            PipelineStage(
                stage_name="recording",
                stage_type="recorder",
                worker_count=self.config.recorder_workers,
                buffer_size=self.config.recorder_buffer_size,
                timeout_seconds=self.config.recorder_timeout
            ),
            PipelineStage(
                stage_name="chunk_generation",
                stage_type="chunk_generator",
                worker_count=self.config.chunk_workers,
                buffer_size=self.config.chunk_buffer_size,
                timeout_seconds=self.config.chunk_timeout
            ),
            PipelineStage(
                stage_name="compression",
                stage_type="compressor",
                worker_count=self.config.compressor_workers,
                buffer_size=self.config.compressor_buffer_size,
                timeout_seconds=self.config.compressor_timeout
            ),
            PipelineStage(
                stage_name="encryption",
                stage_type="encryptor",
                worker_count=self.config.encryptor_workers,
                buffer_size=self.config.encryptor_buffer_size,
                timeout_seconds=self.config.encryptor_timeout
            ),
            PipelineStage(
                stage_name="merkle_building",
                stage_type="merkle_builder",
                worker_count=self.config.merkle_workers,
                buffer_size=self.config.merkle_buffer_size,
                timeout_seconds=self.config.merkle_timeout
            ),
            PipelineStage(
                stage_name="storage",
                stage_type="storage",
                worker_count=self.config.storage_workers,
                buffer_size=self.config.storage_buffer_size,
                timeout_seconds=self.config.storage_timeout
            )
        ]
    
    async def create_pipeline(self, session_id: str, config: Optional[PipelineConfig] = None) -> str:
        """
        Create a new pipeline for a session
        
        Args:
            session_id: Unique session identifier
            config: Optional pipeline configuration
            
        Returns:
            pipeline_id: Unique pipeline identifier
            
        Raises:
            ValueError: If session already has active pipeline
        """
        if session_id in self.active_pipelines:
            raise ValueError(f"Session {session_id} already has an active pipeline")
        
        pipeline_id = f"pipeline-{uuid.uuid4().hex[:8]}"
        pipeline_config = config or self.config
        
        # Create pipeline stages
        stages = []
        for stage_config in self.default_stages:
            stage = PipelineStage(
                stage_name=stage_config.stage_name,
                stage_type=stage_config.stage_type,
                worker_count=pipeline_config.get_worker_count(stage_config.stage_type),
                buffer_size=pipeline_config.get_buffer_size(stage_config.stage_type),
                timeout_seconds=pipeline_config.get_timeout(stage_config.stage_type),
                retry_count=pipeline_config.get_retry_count(stage_config.stage_type)
            )
            stages.append(stage)
        
        # Create pipeline instance
        pipeline = SessionPipeline(
            session_id=session_id,
            pipeline_id=pipeline_id,
            current_state=PipelineState.CREATED,
            stages=stages,
            config=pipeline_config
        )
        
        # Register pipeline
        self.active_pipelines[session_id] = pipeline
        self.pipeline_workers[session_id] = []
        
        logger.info(f"Created pipeline {pipeline_id} for session {session_id}")
        return pipeline_id
    
    async def start_pipeline(self, session_id: str) -> bool:
        """
        Start the pipeline for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if pipeline started successfully
            
        Raises:
            ValueError: If session or pipeline not found
        """
        if session_id not in self.active_pipelines:
            raise ValueError(f"No pipeline found for session {session_id}")
        
        pipeline = self.active_pipelines[session_id]
        
        # Validate pipeline state
        if not self.state_machine.can_transition(pipeline.current_state, PipelineState.STARTING):
            raise ValueError(f"Cannot start pipeline in state {pipeline.current_state}")
        
        try:
            # Transition to starting state
            pipeline.current_state = self.state_machine.transition(
                pipeline.current_state, 
                StateTransition.START
            )
            
            # Start all pipeline stages
            await self._start_pipeline_stages(pipeline)
            
            # Transition to active state
            pipeline.current_state = self.state_machine.transition(
                pipeline.current_state,
                StateTransition.START_COMPLETE
            )
            
            pipeline.started_at = datetime.utcnow()
            
            logger.info(f"Started pipeline {pipeline.pipeline_id} for session {session_id}")
            return True
            
        except Exception as e:
            pipeline.current_state = PipelineState.ERROR
            pipeline.error_message = str(e)
            logger.error(f"Failed to start pipeline {session_id}: {str(e)}")
            return False
    
    async def stop_pipeline(self, session_id: str) -> bool:
        """
        Stop the pipeline for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if pipeline stopped successfully
        """
        if session_id not in self.active_pipelines:
            logger.warning(f"No pipeline found for session {session_id}")
            return False
        
        pipeline = self.active_pipelines[session_id]
        
        try:
            # Transition to stopping state
            pipeline.current_state = self.state_machine.transition(
                pipeline.current_state,
                StateTransition.STOP
            )
            
            # Stop all pipeline stages
            await self._stop_pipeline_stages(pipeline)
            
            # Cancel all worker tasks
            await self._cancel_pipeline_workers(session_id)
            
            # Transition to stopped state
            pipeline.current_state = self.state_machine.transition(
                pipeline.current_state,
                StateTransition.STOP_COMPLETE
            )
            
            pipeline.stopped_at = datetime.utcnow()
            
            logger.info(f"Stopped pipeline {pipeline.pipeline_id} for session {session_id}")
            return True
            
        except Exception as e:
            pipeline.current_state = PipelineState.ERROR
            pipeline.error_message = str(e)
            logger.error(f"Failed to stop pipeline {session_id}: {str(e)}")
            return False
    
    async def process_chunk(self, session_id: str, chunk_data: bytes, chunk_metadata: Dict[str, Any]) -> bool:
        """
        Process a chunk through the pipeline
        
        Args:
            session_id: Session identifier
            chunk_data: Raw chunk data
            chunk_metadata: Chunk metadata
            
        Returns:
            bool: True if chunk processed successfully
        """
        if session_id not in self.active_pipelines:
            logger.error(f"No active pipeline for session {session_id}")
            return False
        
        pipeline = self.active_pipelines[session_id]
        
        if pipeline.current_state != PipelineState.ACTIVE:
            logger.warning(f"Pipeline {session_id} is not active (state: {pipeline.current_state})")
            return False
        
        try:
            # Process chunk through all stages
            processed_data = chunk_data
            processing_start = datetime.utcnow()
            
            for stage in pipeline.stages:
                if stage.status != "active":
                    continue
                
                # Process chunk through stage
                processed_data = await self._process_stage_chunk(
                    stage, 
                    session_id, 
                    processed_data, 
                    chunk_metadata
                )
                
                # Update stage metrics
                self._update_stage_metrics(stage, processing_start)
            
            # Update pipeline metrics
            self._update_pipeline_metrics(pipeline, processing_start)
            
            logger.debug(f"Processed chunk for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process chunk for session {session_id}: {str(e)}")
            pipeline.error_message = str(e)
            return False
    
    async def get_pipeline_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get pipeline status for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Pipeline status dictionary or None if not found
        """
        if session_id not in self.active_pipelines:
            return None
        
        pipeline = self.active_pipelines[session_id]
        
        return {
            "session_id": session_id,
            "pipeline_id": pipeline.pipeline_id,
            "state": pipeline.current_state.value,
            "created_at": pipeline.created_at.isoformat(),
            "started_at": pipeline.started_at.isoformat() if pipeline.started_at else None,
            "stopped_at": pipeline.stopped_at.isoformat() if pipeline.stopped_at else None,
            "error_message": pipeline.error_message,
            "stages": [
                {
                    "name": stage.stage_name,
                    "type": stage.stage_type,
                    "status": stage.status,
                    "worker_count": stage.worker_count,
                    "metrics": {
                        "total_chunks_processed": stage.metrics.total_chunks_processed,
                        "average_processing_time_ms": stage.metrics.average_processing_time_ms,
                        "error_count": stage.metrics.error_count,
                        "throughput_chunks_per_second": stage.metrics.throughput_chunks_per_second
                    },
                    "last_error": stage.last_error
                }
                for stage in pipeline.stages
            ],
            "config": {
                "max_concurrent_sessions": self.config.max_concurrent_sessions,
                "chunk_size_mb": self.config.chunk_size_mb,
                "compression_level": self.config.compression_level
            }
        }
    
    async def cleanup_pipeline(self, session_id: str) -> bool:
        """
        Clean up pipeline resources for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if cleanup successful
        """
        try:
            # Stop pipeline if still running
            if session_id in self.active_pipelines:
                pipeline = self.active_pipelines[session_id]
                if pipeline.current_state in [PipelineState.ACTIVE, PipelineState.STARTING]:
                    await self.stop_pipeline(session_id)
            
            # Remove from active pipelines
            if session_id in self.active_pipelines:
                del self.active_pipelines[session_id]
            
            # Cancel and remove workers
            if session_id in self.pipeline_workers:
                await self._cancel_pipeline_workers(session_id)
                del self.pipeline_workers[session_id]
            
            logger.info(f"Cleaned up pipeline for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup pipeline for session {session_id}: {str(e)}")
            return False
    
    async def shutdown(self):
        """Shutdown the pipeline manager"""
        logger.info("Shutting down Pipeline Manager")
        
        # Set shutdown event
        self._shutdown_event.set()
        
        # Stop all active pipelines
        for session_id in list(self.active_pipelines.keys()):
            await self.cleanup_pipeline(session_id)
        
        logger.info("Pipeline Manager shutdown complete")
    
    async def _start_pipeline_stages(self, pipeline: SessionPipeline):
        """Start all pipeline stages"""
        for stage in pipeline.stages:
            try:
                # Start stage workers
                await self._start_stage_workers(pipeline.session_id, stage)
                stage.status = "active"
                
            except Exception as e:
                stage.status = "error"
                stage.last_error = str(e)
                logger.error(f"Failed to start stage {stage.stage_name}: {str(e)}")
                raise
    
    async def _stop_pipeline_stages(self, pipeline: SessionPipeline):
        """Stop all pipeline stages"""
        for stage in pipeline.stages:
            try:
                # Stop stage workers
                await self._stop_stage_workers(pipeline.session_id, stage)
                stage.status = "inactive"
                
            except Exception as e:
                stage.status = "error"
                stage.last_error = str(e)
                logger.error(f"Failed to stop stage {stage.stage_name}: {str(e)}")
    
    async def _start_stage_workers(self, session_id: str, stage: PipelineStage):
        """Start workers for a pipeline stage"""
        for worker_id in range(stage.worker_count):
            worker_task = asyncio.create_task(
                self._stage_worker(session_id, stage, worker_id)
            )
            self.pipeline_workers[session_id].append(worker_task)
    
    async def _stop_stage_workers(self, session_id: str, stage: PipelineStage):
        """Stop workers for a pipeline stage"""
        # Workers will stop when shutdown event is set
        pass
    
    async def _cancel_pipeline_workers(self, session_id: str):
        """Cancel all worker tasks for a session"""
        if session_id in self.pipeline_workers:
            for task in self.pipeline_workers[session_id]:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(
                *self.pipeline_workers[session_id],
                return_exceptions=True
            )
    
    async def _stage_worker(self, session_id: str, stage: PipelineStage, worker_id: int):
        """Worker task for a pipeline stage"""
        logger.info(f"Started {stage.stage_name} worker {worker_id} for session {session_id}")
        
        try:
            while not self._shutdown_event.is_set():
                # Worker implementation depends on stage type
                # Actual processing happens in _process_stage_chunk
                await asyncio.sleep(0.1)  # Small delay to prevent busy loop
                
        except asyncio.CancelledError:
            logger.info(f"Cancelled {stage.stage_name} worker {worker_id} for session {session_id}")
        except Exception as e:
            logger.error(f"Error in {stage.stage_name} worker {worker_id}: {str(e)}")
    
    async def _process_stage_chunk(
        self, 
        stage: PipelineStage, 
        session_id: str, 
        chunk_data: bytes, 
        chunk_metadata: Dict[str, Any]
    ) -> bytes:
        """Process chunk through a specific stage"""
        
        # Stage-specific processing logic for 6 states
        if stage.stage_type == "recorder":
            # Recording stage processing
            return chunk_data
        
        elif stage.stage_type == "chunk_generator":
            # Chunk generation stage processing (10MB chunks)
            return await self._generate_chunks(chunk_data, stage)
        
        elif stage.stage_type == "compressor":
            # Compression stage processing (gzip level 6)
            return await self._compress_chunk(chunk_data, stage)
        
        elif stage.stage_type == "encryptor":
            # Encryption stage processing
            return await self._encrypt_chunk(chunk_data, stage)
        
        elif stage.stage_type == "merkle_builder":
            # Merkle tree building stage processing
            return await self._build_merkle_tree(chunk_data, stage)
        
        elif stage.stage_type == "storage":
            # Storage stage processing
            await self._store_chunk(session_id, chunk_data, chunk_metadata, stage)
            return chunk_data
        
        else:
            return chunk_data
    
    async def _generate_chunks(self, chunk_data: bytes, stage: PipelineStage) -> bytes:
        """Generate 10MB chunks from session data"""
        try:
            # Import chunk generator
            from ..recorder.chunk_generator import ChunkGenerator, ChunkConfig
            
            # Configure for 10MB chunks (use config from settings)
            chunk_size_mb = self.config.settings.CHUNK_SIZE_MB
            compression_level = self.config.settings.COMPRESSION_LEVEL
            output_path = Path(self.config.settings.CHUNK_STORAGE_PATH)
            
            chunk_config = ChunkConfig(
                chunk_size_mb=chunk_size_mb,
                compression_level=compression_level,
                output_path=output_path
            )
            
            # Generate chunks
            generator = ChunkGenerator(chunk_config)
            await generator.initialize_session(stage.stage_name)
            completed_chunks = await generator.add_data(chunk_data)
            
            # Return processed data
            return chunk_data
        except Exception as e:
            stage.last_error = str(e)
            raise
    
    async def _build_merkle_tree(self, chunk_data: bytes, stage: PipelineStage) -> bytes:
        """Build Merkle tree from chunk data"""
        try:
            # Import Merkle tree builder
            from ..core.merkle_builder import MerkleTreeBuilder
            
            # Build Merkle tree
            builder = MerkleTreeBuilder()
            merkle_tree = await builder.build_tree([chunk_data])
            
            # Return processed data
            return chunk_data
        except Exception as e:
            stage.last_error = str(e)
            raise
    
    async def _compress_chunk(self, chunk_data: bytes, stage: PipelineStage) -> bytes:
        """Compress chunk data with gzip level 6"""
        try:
            import gzip
            compressed_data = gzip.compress(chunk_data, compresslevel=6)
            return compressed_data
        except Exception as e:
            stage.last_error = str(e)
            raise
    
    async def _encrypt_chunk(self, chunk_data: bytes, stage: PipelineStage) -> bytes:
        """Encrypt chunk data"""
        try:
            # TODO: Implement encryption using ENCRYPTION_KEY from config
            # For now, return unencrypted data if encryption is disabled
            if not self.config.settings.ENABLE_ENCRYPTION:
                return chunk_data
            # Encryption implementation needed using self.config.settings.ENCRYPTION_KEY
            logger.warning("Encryption is enabled but not yet implemented")
            return chunk_data
        except Exception as e:
            stage.last_error = str(e)
            raise
    
    async def _store_chunk(
        self, 
        session_id: str, 
        chunk_data: bytes, 
        chunk_metadata: Dict[str, Any], 
        stage: PipelineStage
    ):
        """Store chunk data"""
        try:
            # TODO: Implement storage to filesystem or database
            # Storage path should use self.config.settings.CHUNK_STORAGE_PATH
            storage_path = Path(self.config.settings.CHUNK_STORAGE_PATH)
            storage_path.mkdir(parents=True, exist_ok=True)
            # Storage implementation needed
            logger.debug(f"Chunk storage for session {session_id} - implementation needed")
            pass
        except Exception as e:
            stage.last_error = str(e)
            raise
    
    def _update_stage_metrics(self, stage: PipelineStage, start_time: datetime):
        """Update stage processing metrics"""
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        stage.metrics.total_chunks_processed += 1
        stage.metrics.total_processing_time_ms += processing_time
        stage.metrics.average_processing_time_ms = (
            stage.metrics.total_processing_time_ms / stage.metrics.total_chunks_processed
        )
        stage.metrics.last_processed_at = datetime.utcnow()
        
        # Calculate throughput (chunks per second)
        if stage.metrics.last_processed_at and stage.metrics.total_chunks_processed > 1:
            time_diff = (stage.metrics.last_processed_at - start_time).total_seconds()
            if time_diff > 0:
                stage.metrics.throughput_chunks_per_second = stage.metrics.total_chunks_processed / time_diff
    
    def _update_pipeline_metrics(self, pipeline: SessionPipeline, start_time: datetime):
        """Update pipeline processing metrics"""
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Aggregate metrics from all stages
        total_chunks = sum(stage.metrics.total_chunks_processed for stage in pipeline.stages)
        total_errors = sum(stage.metrics.error_count for stage in pipeline.stages)
        
        # Update pipeline metadata
        pipeline.metadata.update({
            "total_chunks_processed": total_chunks,
            "total_errors": total_errors,
            "last_processing_time_ms": processing_time,
            "last_processed_at": datetime.utcnow().isoformat()
        })