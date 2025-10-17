"""
Chunk Processor Service
Handles concurrent processing of session chunks with encryption and Merkle tree building.

This module implements the core chunk processing functionality for the Lucid session management system.
It processes chunks concurrently using 10 workers, applies AES-256-GCM encryption, and builds
Merkle trees for blockchain anchoring.

Features:
- Concurrent chunk processing (10 workers)
- AES-256-GCM encryption
- Merkle tree building
- Chunk validation and integrity checking
- Storage service integration
- Performance metrics and monitoring
"""

import asyncio
import hashlib
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import json

from .encryption import ChunkEncryptor
from .merkle_builder import MerkleTreeBuilder
from .config import ChunkProcessorConfig

logger = logging.getLogger(__name__)


@dataclass
class ChunkMetadata:
    """Metadata for a processed chunk."""
    chunk_id: str
    session_id: str
    original_size: int
    encrypted_size: int
    compression_ratio: float
    hash: str
    encrypted_hash: str
    timestamp: datetime
    processing_time_ms: float
    worker_id: int


@dataclass
class ProcessingResult:
    """Result of chunk processing operation."""
    success: bool
    chunk_metadata: Optional[ChunkMetadata]
    error_message: Optional[str]
    processing_time_ms: float


class ChunkProcessor:
    """
    Main chunk processor class that handles concurrent processing of session chunks.
    
    This class manages a pool of worker threads to process chunks concurrently,
    applies encryption, builds Merkle trees, and sends processed chunks to storage.
    """
    
    def __init__(self, config: ChunkProcessorConfig):
        """
        Initialize the chunk processor.
        
        Args:
            config: Configuration object containing processor settings
        """
        self.config = config
        self.encryptor = ChunkEncryptor(config.encryption_key)
        self.merkle_builder = MerkleTreeBuilder()
        
        # Worker pool for concurrent processing
        self.worker_pool = ThreadPoolExecutor(max_workers=config.max_workers)
        
        # Processing queues and state
        self.processing_queue = asyncio.Queue(maxsize=config.queue_size)
        self.results_queue = asyncio.Queue()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Metrics
        self.metrics = {
            "chunks_processed": 0,
            "chunks_failed": 0,
            "total_processing_time_ms": 0,
            "average_processing_time_ms": 0,
            "active_workers": 0,
            "queue_size": 0
        }
        
        # Storage service client (will be injected)
        self.storage_client = None
        
        logger.info(f"ChunkProcessor initialized with {config.max_workers} workers")
    
    async def start(self):
        """Start the chunk processor service."""
        logger.info("Starting chunk processor service")
        
        # Start worker tasks
        worker_tasks = []
        for worker_id in range(self.config.max_workers):
            task = asyncio.create_task(self._worker_loop(worker_id))
            worker_tasks.append(task)
        
        # Start metrics collection task
        metrics_task = asyncio.create_task(self._metrics_collector())
        
        logger.info(f"Started {self.config.max_workers} worker tasks and metrics collector")
    
    async def stop(self):
        """Stop the chunk processor service."""
        logger.info("Stopping chunk processor service")
        
        # Shutdown worker pool
        self.worker_pool.shutdown(wait=True)
        
        # Cancel all tasks
        for task in asyncio.all_tasks():
            if not task.done():
                task.cancel()
        
        logger.info("Chunk processor service stopped")
    
    async def process_chunk(
        self, 
        session_id: str, 
        chunk_id: str, 
        chunk_data: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessingResult:
        """
        Process a single chunk.
        
        Args:
            session_id: ID of the session this chunk belongs to
            chunk_id: Unique identifier for the chunk
            chunk_data: Raw chunk data to process
            metadata: Optional metadata for the chunk
            
        Returns:
            ProcessingResult containing processing outcome and metadata
        """
        start_time = time.time()
        
        try:
            logger.debug(f"Processing chunk {chunk_id} for session {session_id}")
            
            # Validate input
            if not chunk_data:
                raise ValueError("Chunk data cannot be empty")
            
            if len(chunk_data) > self.config.max_chunk_size:
                raise ValueError(f"Chunk size {len(chunk_data)} exceeds maximum {self.config.max_chunk_size}")
            
            # Calculate original hash
            original_hash = hashlib.sha256(chunk_data).hexdigest()
            
            # Encrypt chunk
            encrypted_data = await self._encrypt_chunk(chunk_data)
            encrypted_hash = hashlib.sha256(encrypted_data).hexdigest()
            
            # Calculate compression ratio
            compression_ratio = len(encrypted_data) / len(chunk_data) if chunk_data else 0
            
            # Create chunk metadata
            chunk_metadata = ChunkMetadata(
                chunk_id=chunk_id,
                session_id=session_id,
                original_size=len(chunk_data),
                encrypted_size=len(encrypted_data),
                compression_ratio=compression_ratio,
                hash=original_hash,
                encrypted_hash=encrypted_hash,
                timestamp=datetime.utcnow(),
                processing_time_ms=(time.time() - start_time) * 1000,
                worker_id=0  # Will be set by worker
            )
            
            # Update session Merkle tree
            await self._update_session_merkle_tree(session_id, original_hash)
            
            # Send to storage (if storage client is available)
            if self.storage_client:
                await self._send_to_storage(session_id, chunk_id, encrypted_data, chunk_metadata)
            
            # Update metrics
            self._update_metrics(True, chunk_metadata.processing_time_ms)
            
            logger.debug(f"Successfully processed chunk {chunk_id} in {chunk_metadata.processing_time_ms:.2f}ms")
            
            return ProcessingResult(
                success=True,
                chunk_metadata=chunk_metadata,
                error_message=None,
                processing_time_ms=chunk_metadata.processing_time_ms
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            error_msg = f"Failed to process chunk {chunk_id}: {str(e)}"
            logger.error(error_msg)
            
            self._update_metrics(False, processing_time)
            
            return ProcessingResult(
                success=False,
                chunk_metadata=None,
                error_message=error_msg,
                processing_time_ms=processing_time
            )
    
    async def process_chunks_batch(
        self, 
        session_id: str, 
        chunks: List[Tuple[str, bytes, Optional[Dict[str, Any]]]]
    ) -> List[ProcessingResult]:
        """
        Process multiple chunks concurrently.
        
        Args:
            session_id: ID of the session these chunks belong to
            chunks: List of (chunk_id, chunk_data, metadata) tuples
            
        Returns:
            List of ProcessingResult objects
        """
        logger.info(f"Processing batch of {len(chunks)} chunks for session {session_id}")
        
        # Submit all chunks to worker pool
        future_to_chunk = {}
        for chunk_id, chunk_data, metadata in chunks:
            future = self.worker_pool.submit(
                self._process_chunk_sync, 
                session_id, 
                chunk_id, 
                chunk_data, 
                metadata
            )
            future_to_chunk[future] = (chunk_id, chunk_data, metadata)
        
        # Collect results as they complete
        results = []
        for future in as_completed(future_to_chunk):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                chunk_id, _, _ = future_to_chunk[future]
                logger.error(f"Worker failed to process chunk {chunk_id}: {str(e)}")
                results.append(ProcessingResult(
                    success=False,
                    chunk_metadata=None,
                    error_message=str(e),
                    processing_time_ms=0
                ))
        
        logger.info(f"Completed batch processing: {len([r for r in results if r.success])} successful, {len([r for r in results if not r.success])} failed")
        return results
    
    async def get_session_merkle_root(self, session_id: str) -> Optional[str]:
        """
        Get the Merkle root for a session.
        
        Args:
            session_id: ID of the session
            
        Returns:
            Merkle root hash if available, None otherwise
        """
        if session_id in self.active_sessions:
            return self.active_sessions[session_id].get("merkle_root")
        return None
    
    async def finalize_session(self, session_id: str) -> Optional[str]:
        """
        Finalize a session and return the final Merkle root.
        
        Args:
            session_id: ID of the session to finalize
            
        Returns:
            Final Merkle root hash
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Session {session_id} not found for finalization")
            return None
        
        session_data = self.active_sessions[session_id]
        merkle_root = await self.merkle_builder.finalize_tree(session_data["chunk_hashes"])
        
        # Store final Merkle root
        session_data["merkle_root"] = merkle_root
        session_data["finalized"] = True
        
        logger.info(f"Finalized session {session_id} with Merkle root: {merkle_root}")
        return merkle_root
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current processing metrics."""
        return self.metrics.copy()
    
    async def _encrypt_chunk(self, chunk_data: bytes) -> bytes:
        """Encrypt chunk data using AES-256-GCM."""
        return await self.encryptor.encrypt(chunk_data)
    
    async def _update_session_merkle_tree(self, session_id: str, chunk_hash: str):
        """Update the Merkle tree for a session with a new chunk hash."""
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {
                "chunk_hashes": [],
                "merkle_root": None,
                "finalized": False,
                "created_at": datetime.utcnow()
            }
        
        self.active_sessions[session_id]["chunk_hashes"].append(chunk_hash)
    
    async def _send_to_storage(
        self, 
        session_id: str, 
        chunk_id: str, 
        encrypted_data: bytes, 
        metadata: ChunkMetadata
    ):
        """Send processed chunk to storage service."""
        if self.storage_client:
            try:
                await self.storage_client.store_chunk(
                    session_id=session_id,
                    chunk_id=chunk_id,
                    data=encrypted_data,
                    metadata=metadata
                )
            except Exception as e:
                logger.error(f"Failed to send chunk {chunk_id} to storage: {str(e)}")
                raise
    
    def _process_chunk_sync(
        self, 
        session_id: str, 
        chunk_id: str, 
        chunk_data: bytes, 
        metadata: Optional[Dict[str, Any]]
    ) -> ProcessingResult:
        """Synchronous wrapper for chunk processing (for thread pool)."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.process_chunk(session_id, chunk_id, chunk_data, metadata)
            )
        finally:
            loop.close()
    
    async def _worker_loop(self, worker_id: int):
        """Main worker loop for processing chunks from the queue."""
        logger.info(f"Worker {worker_id} started")
        
        while True:
            try:
                # Get chunk from queue
                chunk_task = await asyncio.wait_for(
                    self.processing_queue.get(), 
                    timeout=1.0
                )
                
                # Process chunk
                result = await self.process_chunk(
                    chunk_task["session_id"],
                    chunk_task["chunk_id"],
                    chunk_task["chunk_data"],
                    chunk_task.get("metadata")
                )
                
                # Put result in results queue
                await self.results_queue.put(result)
                
                # Mark task as done
                self.processing_queue.task_done()
                
            except asyncio.TimeoutError:
                # No work available, continue
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {str(e)}")
                await asyncio.sleep(1)  # Brief pause before retrying
    
    async def _metrics_collector(self):
        """Collect and update processing metrics."""
        while True:
            try:
                # Update queue size
                self.metrics["queue_size"] = self.processing_queue.qsize()
                
                # Update average processing time
                if self.metrics["chunks_processed"] > 0:
                    self.metrics["average_processing_time_ms"] = (
                        self.metrics["total_processing_time_ms"] / 
                        self.metrics["chunks_processed"]
                    )
                
                # Log metrics periodically
                if self.metrics["chunks_processed"] % 100 == 0 and self.metrics["chunks_processed"] > 0:
                    logger.info(f"Processing metrics: {self.metrics}")
                
                await asyncio.sleep(10)  # Update every 10 seconds
                
            except Exception as e:
                logger.error(f"Metrics collector error: {str(e)}")
                await asyncio.sleep(10)
    
    def _update_metrics(self, success: bool, processing_time_ms: float):
        """Update processing metrics."""
        if success:
            self.metrics["chunks_processed"] += 1
        else:
            self.metrics["chunks_failed"] += 1
        
        self.metrics["total_processing_time_ms"] += processing_time_ms


class ChunkProcessorService:
    """
    Service wrapper for the chunk processor.
    
    This class provides a service interface for the chunk processor,
    handling service lifecycle, health checks, and external integration.
    """
    
    def __init__(self, config: ChunkProcessorConfig):
        """Initialize the chunk processor service."""
        self.config = config
        self.processor = ChunkProcessor(config)
        self.is_running = False
    
    async def start(self):
        """Start the chunk processor service."""
        if self.is_running:
            logger.warning("Chunk processor service is already running")
            return
        
        await self.processor.start()
        self.is_running = True
        logger.info("Chunk processor service started")
    
    async def stop(self):
        """Stop the chunk processor service."""
        if not self.is_running:
            logger.warning("Chunk processor service is not running")
            return
        
        await self.processor.stop()
        self.is_running = False
        logger.info("Chunk processor service stopped")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the chunk processor service."""
        try:
            metrics = self.processor.get_metrics()
            
            health_status = {
                "status": "healthy" if self.is_running else "stopped",
                "is_running": self.is_running,
                "metrics": metrics,
                "config": {
                    "max_workers": self.config.max_workers,
                    "queue_size": self.config.queue_size,
                    "max_chunk_size": self.config.max_chunk_size
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def process_chunk(
        self, 
        session_id: str, 
        chunk_id: str, 
        chunk_data: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessingResult:
        """Process a single chunk."""
        return await self.processor.process_chunk(session_id, chunk_id, chunk_data, metadata)
    
    async def process_chunks_batch(
        self, 
        session_id: str, 
        chunks: List[Tuple[str, bytes, Optional[Dict[str, Any]]]]
    ) -> List[ProcessingResult]:
        """Process multiple chunks concurrently."""
        return await self.processor.process_chunks_batch(session_id, chunks)
    
    async def get_session_merkle_root(self, session_id: str) -> Optional[str]:
        """Get the Merkle root for a session."""
        return await self.processor.get_session_merkle_root(session_id)
    
    async def finalize_session(self, session_id: str) -> Optional[str]:
        """Finalize a session and return the final Merkle root."""
        return await self.processor.finalize_session(session_id)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current processing metrics."""
        return self.processor.get_metrics()
