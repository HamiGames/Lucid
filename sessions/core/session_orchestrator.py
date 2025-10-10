#!/usr/bin/env python3
"""
LUCID Session Orchestrator - SPEC-1B Implementation
Coordinates session pipeline: chunker → encryptor → merkle → blockchain anchor
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Tuple
import json

from .chunker import SessionChunker, ChunkMetadata
from ..encryption.encryptor import SessionEncryptor, EncryptedChunk
from .merkle_builder import MerkleTreeBuilder, MerkleRoot

logger = logging.getLogger(__name__)

class PipelineStage(Enum):
    """Session pipeline stages"""
    INITIALIZED = "initialized"
    CHUNKING = "chunking"
    ENCRYPTING = "encrypting"
    MERKLE_BUILDING = "merkle_building"
    ANCHORING = "anchoring"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class SessionPipeline:
    """Session pipeline state and metadata"""
    session_id: str
    stage: PipelineStage
    start_time: float
    end_time: Optional[float] = None
    chunks: List[ChunkMetadata] = None
    encrypted_chunks: List[EncryptedChunk] = None
    merkle_root: Optional[MerkleRoot] = None
    blockchain_anchor: Optional[str] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.chunks is None:
            self.chunks = []
        if self.encrypted_chunks is None:
            self.encrypted_chunks = []

class SessionOrchestrator:
    """
    Orchestrates the complete session pipeline per SPEC-1b
    """
    
    def __init__(
        self,
        chunker_dir: str = None,
        encryptor_dir: str = None, 
        merkle_dir: str = None,
        output_dir: str = None
    ):
        self.output_dir = Path(output_dir or os.getenv("LUCID_SESSION_OUTPUT_DIR", "/data/sessions"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize pipeline components
        self.chunker = SessionChunker(chunker_dir)
        self.encryptor = SessionEncryptor(encryptor_dir)
        self.merkle_builder = MerkleTreeBuilder(merkle_dir)
        
        # Active pipelines
        self._active_pipelines: Dict[str, SessionPipeline] = {}
        
        logger.info("SessionOrchestrator initialized with complete pipeline")
    
    async def orchestrate_session_pipeline(
        self, 
        session_id: str, 
        data_stream: AsyncGenerator[bytes, None],
        target_chunk_size: Optional[int] = None
    ) -> SessionPipeline:
        """
        Orchestrate complete session pipeline
        
        Args:
            session_id: Unique session identifier
            data_stream: Async generator yielding session data
            target_chunk_size: Optional target chunk size for chunking
            
        Returns:
            SessionPipeline object with complete pipeline state
        """
        # Initialize pipeline
        pipeline = SessionPipeline(
            session_id=session_id,
            stage=PipelineStage.INITIALIZED,
            start_time=time.time()
        )
        
        self._active_pipelines[session_id] = pipeline
        
        try:
            logger.info(f"Starting session pipeline for {session_id}")
            
            # Stage 1: Chunking
            await self._update_pipeline_stage(pipeline, PipelineStage.CHUNKING)
            chunks = await self._chunk_session_data(pipeline, data_stream, target_chunk_size)
            pipeline.chunks = chunks
            
            # Stage 2: Encryption
            await self._update_pipeline_stage(pipeline, PipelineStage.ENCRYPTING)
            encrypted_chunks = await self._encrypt_chunks(pipeline)
            pipeline.encrypted_chunks = encrypted_chunks
            
            # Stage 3: Merkle Tree Building
            await self._update_pipeline_stage(pipeline, PipelineStage.MERKLE_BUILDING)
            merkle_root = await self._build_merkle_tree(pipeline)
            pipeline.merkle_root = merkle_root
            
            # Stage 4: Blockchain Anchoring (placeholder)
            await self._update_pipeline_stage(pipeline, PipelineStage.ANCHORING)
            blockchain_anchor = await self._anchor_to_blockchain(pipeline)
            pipeline.blockchain_anchor = blockchain_anchor
            
            # Complete pipeline
            await self._update_pipeline_stage(pipeline, PipelineStage.COMPLETED)
            pipeline.end_time = time.time()
            
            # Save pipeline state
            await self._save_pipeline_state(pipeline)
            
            logger.info(f"Session pipeline completed for {session_id} in {pipeline.end_time - pipeline.start_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Session pipeline failed for {session_id}: {e}")
            await self._update_pipeline_stage(pipeline, PipelineStage.FAILED, str(e))
            pipeline.end_time = time.time()
            raise
        
        finally:
            # Remove from active pipelines
            if session_id in self._active_pipelines:
                del self._active_pipelines[session_id]
        
        return pipeline
    
    async def _update_pipeline_stage(
        self, 
        pipeline: SessionPipeline, 
        stage: PipelineStage, 
        error_message: Optional[str] = None
    ):
        """Update pipeline stage with logging"""
        pipeline.stage = stage
        if error_message:
            pipeline.error_message = error_message
        
        logger.info(f"Pipeline {pipeline.session_id}: {stage.value}")
    
    async def _chunk_session_data(
        self, 
        pipeline: SessionPipeline, 
        data_stream: AsyncGenerator[bytes, None],
        target_chunk_size: Optional[int]
    ) -> List[ChunkMetadata]:
        """Chunk session data using the chunker"""
        
        chunks = []
        async for chunk_metadata in self.chunker.stream_chunk_session_data(
            pipeline.session_id, data_stream
        ):
            chunks.append(chunk_metadata)
        
        logger.info(f"Chunking complete: {len(chunks)} chunks for session {pipeline.session_id}")
        return chunks
    
    async def _encrypt_chunks(self, pipeline: SessionPipeline) -> List[EncryptedChunk]:
        """Encrypt session chunks using the encryptor"""
        
        # Prepare chunk data for encryption
        chunk_data_pairs = []
        for chunk in pipeline.chunks:
            # Read chunk data
            chunk_data = await self.chunker.get_chunk_data(chunk)
            chunk_data_pairs.append((chunk.chunk_id, chunk_data))
        
        # Encrypt all chunks
        encrypted_chunks = await self.encryptor.encrypt_session_chunks(
            chunk_data_pairs, pipeline.session_id
        )
        
        logger.info(f"Encryption complete: {len(encrypted_chunks)} encrypted chunks for session {pipeline.session_id}")
        return encrypted_chunks
    
    async def _build_merkle_tree(self, pipeline: SessionPipeline) -> MerkleRoot:
        """Build Merkle tree for session integrity"""
        
        # Prepare encrypted chunk data for Merkle tree
        chunk_data_pairs = []
        for encrypted_chunk in pipeline.encrypted_chunks:
            # Read encrypted data
            with open(encrypted_chunk.file_path, 'rb') as f:
                encrypted_data = f.read()
            chunk_data_pairs.append((encrypted_chunk.chunk_id, encrypted_data))
        
        # Build Merkle tree
        merkle_root = await self.merkle_builder.build_session_merkle_tree(
            chunk_data_pairs, pipeline.session_id
        )
        
        logger.info(f"Merkle tree built for session {pipeline.session_id}: {merkle_root.root_hash.hex()[:16]}...")
        return merkle_root
    
    async def _anchor_to_blockchain(self, pipeline: SessionPipeline) -> str:
        """Anchor Merkle root to blockchain (placeholder implementation)"""
        
        # This would integrate with the blockchain anchoring system
        # For now, return a placeholder anchor hash
        anchor_hash = f"anchor_{pipeline.session_id}_{int(time.time())}"
        
        logger.info(f"Blockchain anchoring complete for session {pipeline.session_id}: {anchor_hash}")
        return anchor_hash
    
    async def _save_pipeline_state(self, pipeline: SessionPipeline):
        """Save pipeline state to disk"""
        
        state_filename = f"{pipeline.session_id}_pipeline_state.json"
        state_path = self.output_dir / state_filename
        
        state_data = {
            "session_id": pipeline.session_id,
            "stage": pipeline.stage.value,
            "start_time": pipeline.start_time,
            "end_time": pipeline.end_time,
            "chunk_count": len(pipeline.chunks),
            "encrypted_chunk_count": len(pipeline.encrypted_chunks),
            "merkle_root": pipeline.merkle_root.root_hash.hex() if pipeline.merkle_root else None,
            "blockchain_anchor": pipeline.blockchain_anchor,
            "error_message": pipeline.error_message
        }
        
        with open(state_path, 'w') as f:
            json.dump(state_data, f, indent=2)
        
        logger.debug(f"Saved pipeline state to {state_path}")
    
    async def load_pipeline_state(self, session_id: str) -> Optional[SessionPipeline]:
        """Load pipeline state from disk"""
        
        state_filename = f"{session_id}_pipeline_state.json"
        state_path = self.output_dir / state_filename
        
        if not state_path.exists():
            return None
        
        with open(state_path, 'r') as f:
            state_data = json.load(f)
        
        # Reconstruct pipeline (simplified - would need to load full objects)
        pipeline = SessionPipeline(
            session_id=state_data["session_id"],
            stage=PipelineStage(state_data["stage"]),
            start_time=state_data["start_time"],
            end_time=state_data.get("end_time")
        )
        
        pipeline.blockchain_anchor = state_data.get("blockchain_anchor")
        pipeline.error_message = state_data.get("error_message")
        
        logger.debug(f"Loaded pipeline state for session {session_id}")
        return pipeline
    
    async def get_pipeline_status(self, session_id: str) -> Optional[dict]:
        """Get current pipeline status"""
        
        if session_id in self._active_pipelines:
            pipeline = self._active_pipelines[session_id]
            return {
                "session_id": session_id,
                "stage": pipeline.stage.value,
                "active": True,
                "duration": time.time() - pipeline.start_time,
                "chunk_count": len(pipeline.chunks),
                "encrypted_chunk_count": len(pipeline.encrypted_chunks)
            }
        
        # Check for completed pipeline
        pipeline = await self.load_pipeline_state(session_id)
        if pipeline:
            return {
                "session_id": session_id,
                "stage": pipeline.stage.value,
                "active": False,
                "duration": (pipeline.end_time or time.time()) - pipeline.start_time,
                "chunk_count": len(pipeline.chunks),
                "encrypted_chunk_count": len(pipeline.encrypted_chunks),
                "merkle_root": pipeline.merkle_root.root_hash.hex() if pipeline.merkle_root else None,
                "blockchain_anchor": pipeline.blockchain_anchor
            }
        
        return None
    
    async def cleanup_session_pipeline(self, session_id: str) -> bool:
        """Clean up all data for a session"""
        
        try:
            # Clean up chunks
            await self.chunker.cleanup_session_chunks(session_id)
            
            # Clean up encrypted chunks
            await self.encryptor.cleanup_session_encrypted_chunks(session_id)
            
            # Clean up Merkle root
            await self.merkle_builder.cleanup_session_merkle_root(session_id)
            
            # Clean up pipeline state
            state_filename = f"{session_id}_pipeline_state.json"
            state_path = self.output_dir / state_filename
            if state_path.exists():
                state_path.unlink()
            
            logger.info(f"Cleaned up all data for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {e}")
            return False
    
    def get_orchestrator_stats(self) -> dict:
        """Get orchestrator statistics"""
        
        return {
            "active_pipelines": len(self._active_pipelines),
            "active_session_ids": list(self._active_pipelines.keys()),
            "output_directory": str(self.output_dir),
            "components": {
                "chunker": str(self.chunker.output_dir),
                "encryptor": str(self.encryptor.output_dir),
                "merkle_builder": str(self.merkle_builder.output_dir)
            }
        }

# CLI interface for testing
async def main():
    """Test the orchestrator with sample data"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LUCID Session Orchestrator")
    parser.add_argument("--session-id", required=True, help="Session ID")
    parser.add_argument("--input-file", required=True, help="Input file to process")
    parser.add_argument("--output-dir", default="/data/sessions", help="Output directory")
    parser.add_argument("--chunk-size", type=int, default=8*1024*1024, help="Target chunk size")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create orchestrator
    orchestrator = SessionOrchestrator(output_dir=args.output_dir)
    
    # Create async data stream
    async def data_stream():
        with open(args.input_file, 'rb') as f:
            while True:
                chunk = f.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                yield chunk
    
    # Run pipeline
    try:
        pipeline = await orchestrator.orchestrate_session_pipeline(
            args.session_id, data_stream(), args.chunk_size
        )
        
        print(f"Pipeline completed:")
        print(f"  Session ID: {pipeline.session_id}")
        print(f"  Stage: {pipeline.stage.value}")
        print(f"  Duration: {pipeline.end_time - pipeline.start_time:.2f}s")
        print(f"  Chunks: {len(pipeline.chunks)}")
        print(f"  Encrypted chunks: {len(pipeline.encrypted_chunks)}")
        if pipeline.merkle_root:
            print(f"  Merkle root: {pipeline.merkle_root.root_hash.hex()[:16]}...")
        if pipeline.blockchain_anchor:
            print(f"  Blockchain anchor: {pipeline.blockchain_anchor}")
            
    except Exception as e:
        print(f"Pipeline failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())