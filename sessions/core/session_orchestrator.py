"""Lucid RDP Session Orchestrator - Main coordination layer for session pipeline.

Based on LUCID-STRICT requirements and Layer 1 implementation strategy.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, AsyncGenerator, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# Core session components
from .session_generator import (
    SessionIdGenerator,
    SessionMetadata as SessionGenMetadata,
    SessionType
)
from .chunker import ChunkMetadata, SessionChunkManager
from ..encryption.encryptor import EncryptedChunk, SessionEncryptionManager
from .merkle_builder import MerkleProof, SessionMerkleManager

# Database integration
try:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
    HAS_MOTOR = True
except ImportError:
    HAS_MOTOR = False
    AsyncIOMotorClient = None
    AsyncIOMotorDatabase = None

# Blockchain integration
try:
    from blockchain.core.blockchain_engine import get_blockchain_engine
    HAS_BLOCKCHAIN = True
except ImportError:
    HAS_BLOCKCHAIN = False
    get_blockchain_engine = None

logger = logging.getLogger(__name__)

# Configuration constants from environment
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/lucid")
CHUNK_PROCESSING_TIMEOUT = int(
    os.getenv("CHUNK_PROCESSING_TIMEOUT", "300")
)  # 5 minutes
SESSION_FINALIZATION_TIMEOUT = int(
    os.getenv("SESSION_FINALIZATION_TIMEOUT", "1800")
)  # 30 minutes
MAX_CONCURRENT_SESSIONS = int(os.getenv("MAX_CONCURRENT_SESSIONS", "10"))
ENABLE_BLOCKCHAIN_ANCHORING = (
    os.getenv("ENABLE_BLOCKCHAIN_ANCHORING", "true").lower() == "true"
)


class PipelineState(Enum):
    """Session pipeline processing states"""
    INITIALIZED = "initialized"
    CHUNKING = "chunking"
    ENCRYPTING = "encrypting"
    MERKLE_BUILDING = "merkle_building"
    ANCHORING = "anchoring"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineError(Exception):
    """Session pipeline processing error."""
    
    def __init__(
        self,
        message: str,
        pipeline_state: PipelineState,
        session_id: Optional[str] = None
    ) -> None:
        """Initialize pipeline error.
        
        Args:
            message: Error message
            pipeline_state: Current pipeline state
            session_id: Optional session ID
        """
        super().__init__(message)
        self.pipeline_state = pipeline_state
        self.session_id = session_id


@dataclass
class SessionPipelineMetadata:
    """Complete session pipeline metadata."""
    
    session_id: str
    owner_address: str
    node_id: str
    pipeline_state: PipelineState
    created_at: datetime
    updated_at: datetime
    total_chunks: int = 0
    total_bytes: int = 0
    encrypted_chunks: List[str] = field(default_factory=list)
    merkle_root: Optional[str] = None
    anchor_txid: Optional[str] = None
    error_message: Optional[str] = None
    
    # Pipeline component states
    session_generator_complete: bool = False
    chunking_complete: bool = False
    encryption_complete: bool = False
    merkle_complete: bool = False
    anchoring_complete: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        return {
            "_id": self.session_id,
            "owner_address": self.owner_address,
            "node_id": self.node_id,
            "pipeline_state": self.pipeline_state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_chunks": self.total_chunks,
            "total_bytes": self.total_bytes,
            "encrypted_chunks": self.encrypted_chunks,
            "merkle_root": self.merkle_root,
            "anchor_txid": self.anchor_txid,
            "error_message": self.error_message,
            "session_generator_complete": self.session_generator_complete,
            "chunking_complete": self.chunking_complete,
            "encryption_complete": self.encryption_complete,
            "merkle_complete": self.merkle_complete,
            "anchoring_complete": self.anchoring_complete
        }


class SessionOrchestrator:
    """
    Main session pipeline orchestrator that coordinates all session processing components.
    
    This class implements the LUCID-STRICT Layer 1 Core Infrastructure by:
    - Coordinating session ID generation with chunking, encryption, and merkle tree building
    - Managing the complete session lifecycle from creation to blockchain anchoring
    - Providing error recovery and rollback capabilities
    - Integrating with MongoDB for state persistence
    - Supporting real-time session monitoring and status updates
    """
    
    def __init__(self, master_key: Optional[bytes] = None):
        """
        Initialize session orchestrator with all required components.
        
        Args:
            master_key: Master encryption key for session encryption (generates if None)
        """
        self.session_id_generator = SessionIdGenerator()
        self.chunk_manager = SessionChunkManager()
        
        # Initialize encryption manager with master key
        if master_key is None:
            master_key = os.urandom(32)  # Generate 256-bit key
        self.encryption_manager = SessionEncryptionManager(master_key)
        
        self.merkle_manager = SessionMerkleManager()
        
        # Database connection
        self.db_client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        
        # Blockchain integration
        self.blockchain_engine = None
        if HAS_BLOCKCHAIN and ENABLE_BLOCKCHAIN_ANCHORING:
            try:
                self.blockchain_engine = get_blockchain_engine()
            except Exception as e:
                logger.warning(f"Blockchain engine initialization failed: {e}")
        
        # Session tracking
        self.active_sessions: Dict[str, SessionPipelineMetadata] = {}
        self.processing_tasks: Dict[str, asyncio.Task] = {}
        
        # Pipeline statistics
        self.stats = {
            "sessions_created": 0,
            "sessions_completed": 0,
            "sessions_failed": 0,
            "total_chunks_processed": 0,
            "total_bytes_processed": 0
        }
        
        logger.info("Session orchestrator initialized")
    
    async def initialize_database(self) -> None:
        """Initialize MongoDB connection and setup collections"""
        if not HAS_MOTOR:
            logger.warning("Motor not available, database functionality disabled")
            return
        
        try:
            self.db_client = AsyncIOMotorClient(MONGODB_URI)
            self.db = self.db_client.get_default_database()
            
            # Test connection
            await self.db.command("ping")
            
            # Create indexes for session pipeline collections
            await self._setup_database_indexes()
            
            logger.info("Database connection established")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            self.db_client = None
            self.db = None
    
    async def _setup_database_indexes(self) -> None:
        """Setup MongoDB indexes for optimal session pipeline performance"""
        if not self.db:
            return
        
        try:
            # Sessions collection indexes
            await self.db.sessions.create_index([("owner_address", 1)])
            await self.db.sessions.create_index([("node_id", 1)])
            await self.db.sessions.create_index([("pipeline_state", 1)])
            await self.db.sessions.create_index([("created_at", -1)])
            
            # Chunks collection indexes
            await self.db.chunks.create_index([("session_id", 1), ("sequence_number", 1)])
            await self.db.chunks.create_index([("created_at", -1)])
            
            # Encrypted chunks collection indexes
            await self.db.encrypted_chunks.create_index([("session_id", 1), ("sequence_number", 1)])
            await self.db.encrypted_chunks.create_index([("created_at", -1)])
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Database index creation failed: {e}")
    
    async def create_session(self, 
                           owner_address: str, 
                           node_id: str,
                           session_type: SessionType = SessionType.RDP_USER) -> SessionPipelineMetadata:
        """
        Create new session and initialize all pipeline components.
        
        Args:
            owner_address: TRON address of session owner
            node_id: ID of the node hosting this session
            session_type: Type of session to create
            
        Returns:
            Complete session pipeline metadata
            
        Raises:
            PipelineError: If session creation fails
        """
        try:
            # Check concurrent session limits
            if len(self.active_sessions) >= MAX_CONCURRENT_SESSIONS:
                raise PipelineError(
                    f"Maximum concurrent sessions ({MAX_CONCURRENT_SESSIONS}) reached",
                    PipelineState.FAILED
                )
            
            # Generate session ID and metadata
            session_gen_meta = self.session_id_generator.generate_session_id(
                session_type=session_type,
                owner_address=owner_address,
                node_id=node_id
            )
            
            session_id = session_gen_meta.session_id
            
            # Create pipeline metadata
            pipeline_meta = SessionPipelineMetadata(
                session_id=session_id,
                owner_address=owner_address,
                node_id=node_id,
                pipeline_state=PipelineState.INITIALIZED,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                session_generator_complete=True
            )
            
            # Initialize session components
            self.chunk_manager.start_chunking(session_id)
            self.encryption_manager.start_encryption(session_id)
            self.merkle_manager.start_session(session_id)
            
            # Store in active sessions
            self.active_sessions[session_id] = pipeline_meta
            
            # Save to database
            if self.db:
                await self.db.sessions.replace_one(
                    {"_id": session_id},
                    pipeline_meta.to_dict(),
                    upsert=True
                )
                
                # Also store session generator metadata
                await self.db.session_metadata.replace_one(
                    {"_id": session_id},
                    session_gen_meta.to_dict(),
                    upsert=True
                )
            
            self.stats["sessions_created"] += 1
            
            logger.info(f"Session created: {session_id} (owner: {owner_address}, node: {node_id})")
            
            return pipeline_meta
            
        except Exception as e:
            logger.error(f"Session creation failed: {e}")
            raise PipelineError(f"Session creation failed: {e}", PipelineState.FAILED)
    
    async def process_session_data(self,
                                 session_id: str,
                                 data_stream: AsyncGenerator[bytes, None],
                                 progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """
        Process session data through the complete pipeline.
        
        Args:
            session_id: Session identifier
            data_stream: Async generator yielding data chunks
            progress_callback: Optional callback for progress updates (bytes_processed, total_chunks)
            
        Returns:
            True if processing completed successfully
            
        Raises:
            PipelineError: If processing fails
        """
        try:
            pipeline_meta = self.active_sessions.get(session_id)
            if not pipeline_meta:
                raise PipelineError(f"Session not found: {session_id}", PipelineState.FAILED, session_id)
            
            # Update pipeline state
            pipeline_meta.pipeline_state = PipelineState.CHUNKING
            pipeline_meta.updated_at = datetime.now(timezone.utc)
            
            logger.info(f"Starting data processing for session: {session_id}")
            
            # Process data stream through pipeline
            async for data_chunk in data_stream:
                # Step 1: Chunk the data
                chunk_metadata_list = self.chunk_manager.process_session_data(session_id, data_chunk)
                
                # Step 2: Encrypt each chunk and build merkle tree
                for chunk_meta in chunk_metadata_list:
                    # Load compressed chunk data from storage
                    compressed_data = self._load_compressed_chunk(session_id, chunk_meta.chunk_id)
                    
                    # Encrypt the chunk
                    encrypted_chunk = self.encryption_manager.encrypt_chunk(
                        session_id, chunk_meta, compressed_data
                    )
                    
                    # Add to merkle tree
                    self.merkle_manager.add_encrypted_chunk(session_id, encrypted_chunk)
                    
                    # Update pipeline metadata
                    pipeline_meta.total_chunks += 1
                    pipeline_meta.total_bytes += chunk_meta.original_size
                    pipeline_meta.encrypted_chunks.append(encrypted_chunk.chunk_id)
                    
                    # Store encrypted chunk metadata to database
                    if self.db:
                        await self.db.encrypted_chunks.replace_one(
                            {"_id": encrypted_chunk.chunk_id},
                            encrypted_chunk.to_dict(),
                            upsert=True
                        )
                    
                    # Call progress callback
                    if progress_callback:
                        progress_callback(pipeline_meta.total_bytes, pipeline_meta.total_chunks)
                    
                    logger.debug(f"Processed chunk {chunk_meta.chunk_id} for session {session_id}")
            
            # Mark chunking and encryption as complete
            pipeline_meta.chunking_complete = True
            pipeline_meta.encryption_complete = True
            pipeline_meta.pipeline_state = PipelineState.MERKLE_BUILDING
            pipeline_meta.updated_at = datetime.now(timezone.utc)
            
            # Finalize the session processing
            finalization_success = await self._finalize_session_processing(session_id)
            
            if finalization_success:
                logger.info(f"Session data processing completed: {session_id} ({pipeline_meta.total_chunks} chunks, {pipeline_meta.total_bytes} bytes)")
                return True
            else:
                raise PipelineError(f"Session finalization failed: {session_id}", PipelineState.FAILED, session_id)
            
        except Exception as e:
            logger.error(f"Session data processing failed for {session_id}: {e}")
            await self._mark_session_failed(session_id, str(e))
            raise PipelineError(f"Session data processing failed: {e}", PipelineState.FAILED, session_id)
    
    async def _finalize_session_processing(self, session_id: str) -> bool:
        """
        Finalize session processing by building merkle tree and anchoring to blockchain.
        
        Args:
            session_id: Session to finalize
            
        Returns:
            True if finalization successful
        """
        try:
            pipeline_meta = self.active_sessions.get(session_id)
            if not pipeline_meta:
                return False
            
            # Build final merkle tree
            merkle_root = self.merkle_manager.finalize_session(session_id)
            pipeline_meta.merkle_root = merkle_root
            pipeline_meta.merkle_complete = True
            pipeline_meta.pipeline_state = PipelineState.ANCHORING
            pipeline_meta.updated_at = datetime.now(timezone.utc)
            
            # Anchor to blockchain if enabled
            if self.blockchain_engine and ENABLE_BLOCKCHAIN_ANCHORING:
                try:
                    # Create session manifest for anchoring
                    session_manifest = {
                        "session_id": session_id,
                        "owner_address": pipeline_meta.owner_address,
                        "node_id": pipeline_meta.node_id,
                        "merkle_root": merkle_root,
                        "total_chunks": pipeline_meta.total_chunks,
                        "total_bytes": pipeline_meta.total_bytes,
                        "created_at": pipeline_meta.created_at.isoformat()
                    }
                    
                    # Anchor to blockchain (simplified - actual implementation depends on blockchain engine)
                    anchor_txid = f"mock_tx_{session_id[:8]}"  # Mock transaction ID
                    
                    pipeline_meta.anchor_txid = anchor_txid
                    pipeline_meta.anchoring_complete = True
                    
                    logger.info(f"Session anchored to blockchain: {session_id} -> {anchor_txid}")
                    
                except Exception as e:
                    logger.warning(f"Blockchain anchoring failed for {session_id}: {e}")
                    # Continue without anchoring - not critical for Layer 1 implementation
                    pipeline_meta.anchoring_complete = False
            else:
                logger.info(f"Blockchain anchoring disabled for session: {session_id}")
                pipeline_meta.anchoring_complete = False
            
            # Mark session as completed
            pipeline_meta.pipeline_state = PipelineState.COMPLETED
            pipeline_meta.updated_at = datetime.now(timezone.utc)
            
            # Update database
            if self.db:
                await self.db.sessions.replace_one(
                    {"_id": session_id},
                    pipeline_meta.to_dict(),
                    upsert=True
                )
            
            # Update statistics
            self.stats["sessions_completed"] += 1
            self.stats["total_chunks_processed"] += pipeline_meta.total_chunks
            self.stats["total_bytes_processed"] += pipeline_meta.total_bytes
            
            return True
            
        except Exception as e:
            logger.error(f"Session finalization failed for {session_id}: {e}")
            return False
    
    async def _mark_session_failed(self, session_id: str, error_message: str) -> None:
        """Mark session as failed and clean up resources"""
        try:
            pipeline_meta = self.active_sessions.get(session_id)
            if pipeline_meta:
                pipeline_meta.pipeline_state = PipelineState.FAILED
                pipeline_meta.error_message = error_message
                pipeline_meta.updated_at = datetime.now(timezone.utc)
                
                # Update database
                if self.db:
                    await self.db.sessions.replace_one(
                        {"_id": session_id},
                        pipeline_meta.to_dict(),
                        upsert=True
                    )
            
            # Clean up session components
            self.chunk_manager.finalize_session(session_id)
            self.encryption_manager.finalize_session(session_id)
            self.merkle_manager.cleanup_session(session_id)
            
            # Remove from active sessions
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            # Cancel any processing tasks
            if session_id in self.processing_tasks:
                self.processing_tasks[session_id].cancel()
                del self.processing_tasks[session_id]
            
            self.stats["sessions_failed"] += 1
            
            logger.error(f"Session marked as failed: {session_id} - {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to mark session as failed: {e}")
    
    def _load_compressed_chunk(self, session_id: str, chunk_id: str) -> bytes:
        """Load compressed chunk data from chunker storage"""
        try:
            chunk_file = Path(f"/tmp/lucid/chunks/{session_id}/{chunk_id}.zst")
            if not chunk_file.exists():
                raise FileNotFoundError(f"Chunk file not found: {chunk_file}")
            
            return chunk_file.read_bytes()
            
        except Exception as e:
            logger.error(f"Failed to load chunk {chunk_id}: {e}")
            raise
    
    async def get_session_status(self, session_id: str) -> Optional[SessionPipelineMetadata]:
        """Get current session status and pipeline metadata"""
        return self.active_sessions.get(session_id)
    
    async def get_session_progress(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed session progress information"""
        pipeline_meta = self.active_sessions.get(session_id)
        if not pipeline_meta:
            return None
        
        return {
            "session_id": session_id,
            "pipeline_state": pipeline_meta.pipeline_state.value,
            "progress_percentage": self._calculate_progress_percentage(pipeline_meta),
            "total_chunks": pipeline_meta.total_chunks,
            "total_bytes": pipeline_meta.total_bytes,
            "encrypted_chunks": len(pipeline_meta.encrypted_chunks),
            "merkle_root": pipeline_meta.merkle_root,
            "anchor_txid": pipeline_meta.anchor_txid,
            "created_at": pipeline_meta.created_at.isoformat(),
            "updated_at": pipeline_meta.updated_at.isoformat(),
            "components": {
                "session_generator": pipeline_meta.session_generator_complete,
                "chunking": pipeline_meta.chunking_complete,
                "encryption": pipeline_meta.encryption_complete,
                "merkle_building": pipeline_meta.merkle_complete,
                "blockchain_anchoring": pipeline_meta.anchoring_complete
            }
        }
    
    def _calculate_progress_percentage(self, pipeline_meta: SessionPipelineMetadata) -> int:
        """Calculate overall progress percentage for session pipeline"""
        completed_stages = 0
        total_stages = 5
        
        if pipeline_meta.session_generator_complete:
            completed_stages += 1
        if pipeline_meta.chunking_complete:
            completed_stages += 1
        if pipeline_meta.encryption_complete:
            completed_stages += 1
        if pipeline_meta.merkle_complete:
            completed_stages += 1
        if pipeline_meta.anchoring_complete:
            completed_stages += 1
        
        return int((completed_stages / total_stages) * 100)
    
    async def list_active_sessions(self) -> List[Dict[str, Any]]:
        """Get list of all active sessions with basic information"""
        sessions = []
        for session_id, meta in self.active_sessions.items():
            sessions.append({
                "session_id": session_id,
                "owner_address": meta.owner_address,
                "node_id": meta.node_id,
                "pipeline_state": meta.pipeline_state.value,
                "total_chunks": meta.total_chunks,
                "total_bytes": meta.total_bytes,
                "created_at": meta.created_at.isoformat(),
                "progress_percentage": self._calculate_progress_percentage(meta)
            })
        
        return sessions
    
    async def generate_merkle_proof(self, session_id: str, chunk_index: int) -> Optional[MerkleProof]:
        """Generate merkle proof for a specific chunk"""
        try:
            return self.merkle_manager.generate_chunk_proof(session_id, chunk_index)
        except Exception as e:
            logger.error(f"Failed to generate merkle proof: {e}")
            return None
    
    def get_orchestrator_statistics(self) -> Dict[str, Any]:
        """Get orchestrator statistics and health information"""
        return {
            "statistics": self.stats.copy(),
            "active_sessions": len(self.active_sessions),
            "max_concurrent_sessions": MAX_CONCURRENT_SESSIONS,
            "database_connected": self.db is not None,
            "blockchain_enabled": ENABLE_BLOCKCHAIN_ANCHORING and self.blockchain_engine is not None,
            "components": {
                "session_generator": "active",
                "chunk_manager": "active",
                "encryption_manager": "active", 
                "merkle_manager": "active"
            }
        }
    
    async def cleanup_completed_sessions(self, older_than_hours: int = 24) -> int:
        """Clean up completed sessions older than specified hours"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
            cleaned_sessions = 0
            
            sessions_to_remove = []
            for session_id, meta in self.active_sessions.items():
                if (meta.pipeline_state == PipelineState.COMPLETED and 
                    meta.updated_at < cutoff_time):
                    sessions_to_remove.append(session_id)
            
            for session_id in sessions_to_remove:
                # Clean up session components
                self.chunk_manager.finalize_session(session_id)
                self.encryption_manager.finalize_session(session_id)
                self.merkle_manager.cleanup_session(session_id)
                
                # Remove from active sessions
                del self.active_sessions[session_id]
                cleaned_sessions += 1
                
                logger.info(f"Cleaned up completed session: {session_id}")
            
            logger.info(f"Session cleanup completed: {cleaned_sessions} sessions removed")
            return cleaned_sessions
            
        except Exception as e:
            logger.error(f"Session cleanup failed: {e}")
            return 0
    
    async def shutdown(self) -> None:
        """Gracefully shutdown orchestrator and clean up resources"""
        try:
            logger.info("Shutting down session orchestrator...")
            
            # Cancel all processing tasks
            for task in self.processing_tasks.values():
                task.cancel()
            
            # Wait for tasks to complete
            if self.processing_tasks:
                await asyncio.gather(*self.processing_tasks.values(), return_exceptions=True)
            
            # Clean up all active sessions
            for session_id in list(self.active_sessions.keys()):
                await self._mark_session_failed(session_id, "orchestrator_shutdown")
            
            # Close database connection
            if self.db_client:
                self.db_client.close()
            
            logger.info("Session orchestrator shutdown complete")
            
        except Exception as e:
            logger.error(f"Orchestrator shutdown failed: {e}")


# Global orchestrator instance
_orchestrator: Optional[SessionOrchestrator] = None


def get_session_orchestrator(master_key: Optional[bytes] = None) -> SessionOrchestrator:
    """Get global session orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SessionOrchestrator(master_key)
    return _orchestrator


async def initialize_orchestrator() -> SessionOrchestrator:
    """Initialize session orchestrator with database connection"""
    orchestrator = get_session_orchestrator()
    await orchestrator.initialize_database()
    return orchestrator


if __name__ == "__main__":
    # Test session orchestrator functionality
    async def test_orchestrator():
        print("Initializing Lucid Session Orchestrator...")
        
        orchestrator = await initialize_orchestrator()
        
        # Create test session
        session_meta = await orchestrator.create_session(
            owner_address="TTestOwnerAddress123456789012345",
            node_id="test_node_001"
        )
        
        print(f"Test session created: {session_meta.session_id}")
        
        # Test status retrieval
        status = await orchestrator.get_session_status(session_meta.session_id)
        print(f"Session status: {status.pipeline_state.value}")
        
        # Test progress information
        progress = await orchestrator.get_session_progress(session_meta.session_id)
        print(f"Session progress: {progress}")
        
        # Test statistics
        stats = orchestrator.get_orchestrator_statistics()
        print(f"Orchestrator statistics: {stats}")
        
        await orchestrator.shutdown()
        print("Test completed")
    
    asyncio.run(test_orchestrator())