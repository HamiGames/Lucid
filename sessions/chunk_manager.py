# Path: session/chunk_manager.py

from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Optional, BinaryIO, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import zstandard as zstd
from pathlib import Path
import os
import uuid
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


@dataclass
class SessionChunk:
    """A chunk of session data."""
    chunk_id: str
    session_id: str
    index: int
    original_size: int
    compressed_size: int
    compression_ratio: float
    hash_original: str
    hash_compressed: str
    created_at: datetime
    local_path: Optional[str] = None
    encrypted_path: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "session_id": self.session_id,
            "index": self.index,
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "compression_ratio": self.compression_ratio,
            "hash_original": self.hash_original,
            "hash_compressed": self.hash_compressed,
            "created_at": self.created_at.isoformat(),
            "local_path": self.local_path,
            "encrypted_path": self.encrypted_path
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> SessionChunk:
        return cls(
            chunk_id=data["chunk_id"],
            session_id=data["session_id"],
            index=data["index"],
            original_size=data["original_size"],
            compressed_size=data["compressed_size"],
            compression_ratio=data["compression_ratio"],
            hash_original=data["hash_original"],
            hash_compressed=data["hash_compressed"],
            created_at=datetime.fromisoformat(data["created_at"]),
            local_path=data.get("local_path"),
            encrypted_path=data.get("encrypted_path")
        )


class ChunkManager:
    """
    Manages session data chunking, compression, and storage.
    Integrates with the session recorder and encryption manager.
    """
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        chunk_dir: Optional[str] = None,
        max_chunk_size: Optional[int] = None,
        compression_level: Optional[int] = None
    ):
        self.db = db
        self.chunk_dir = Path(chunk_dir or os.getenv("LUCID_CHUNK_MANAGER_DIR", "./data/chunks"))
        self.max_chunk_size = max_chunk_size or int(os.getenv("LUCID_MAX_CHUNK_SIZE", "16777216"))  # 16MB
        self.compression_level = compression_level or int(os.getenv("LUCID_CHUNK_COMPRESSION_LEVEL", "3"))  # Zstandard level 3
        
        # Create chunk directory
        self.chunk_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize compressor
        self.compressor = zstd.ZstdCompressor(level=compression_level)
        self.decompressor = zstd.ZstdDecompressor()
        
        # Chunk tracking
        self.active_chunks: Dict[str, List[SessionChunk]] = {}
        
    async def create_chunks_from_file(
        self,
        session_id: str,
        file_path: str,
        chunk_prefix: str = "chunk"
    ) -> List[SessionChunk]:
        """Create chunks from a session file."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"Session file not found: {file_path}")
                
            chunks = []
            file_size = file_path.stat().st_size
            
            with open(file_path, 'rb') as f:
                chunk_index = 0
                bytes_read = 0
                
                while bytes_read < file_size:
                    # Read chunk data
                    chunk_data = f.read(min(self.max_chunk_size, file_size - bytes_read))
                    if not chunk_data:
                        break
                        
                    # Create chunk
                    chunk = await self._create_chunk(
                        session_id=session_id,
                        index=chunk_index,
                        data=chunk_data,
                        prefix=chunk_prefix
                    )
                    
                    chunks.append(chunk)
                    bytes_read += len(chunk_data)
                    chunk_index += 1
                    
            # Store chunks in database
            for chunk in chunks:
                await self.db["chunks"].insert_one(chunk.to_dict())
                
            # Track active chunks
            if session_id not in self.active_chunks:
                self.active_chunks[session_id] = []
            self.active_chunks[session_id].extend(chunks)
            
            logger.info(f"Created {len(chunks)} chunks for session {session_id}")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to create chunks from file: {e}")
            raise
            
    async def create_chunk_from_stream(
        self,
        session_id: str,
        data_stream: BinaryIO,
        index: int,
        chunk_prefix: str = "chunk"
    ) -> SessionChunk:
        """Create a chunk from streaming data."""
        try:
            # Read data from stream
            data = data_stream.read(self.max_chunk_size)
            if not data:
                raise ValueError("No data in stream")
                
            # Create chunk
            chunk = await self._create_chunk(
                session_id=session_id,
                index=index,
                data=data,
                prefix=chunk_prefix
            )
            
            # Store in database
            await self.db["chunks"].insert_one(chunk.to_dict())
            
            # Track active chunk
            if session_id not in self.active_chunks:
                self.active_chunks[session_id] = []
            self.active_chunks[session_id].append(chunk)
            
            return chunk
            
        except Exception as e:
            logger.error(f"Failed to create chunk from stream: {e}")
            raise
            
    async def get_session_chunks(self, session_id: str) -> List[SessionChunk]:
        """Get all chunks for a session."""
        try:
            # Check active chunks first
            if session_id in self.active_chunks:
                return self.active_chunks[session_id]
                
            # Query database
            cursor = self.db["chunks"].find(
                {"session_id": session_id}
            ).sort("index", 1)
            
            chunks = []
            async for doc in cursor:
                chunk = SessionChunk.from_dict(doc)
                chunks.append(chunk)
                
            # Cache active chunks
            self.active_chunks[session_id] = chunks
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to get session chunks: {e}")
            return []
            
    async def reconstruct_file_from_chunks(
        self,
        session_id: str,
        output_path: str,
        verify_hashes: bool = True
    ) -> bool:
        """Reconstruct original file from chunks."""
        try:
            chunks = await self.get_session_chunks(session_id)
            if not chunks:
                logger.warning(f"No chunks found for session {session_id}")
                return False
                
            # Sort chunks by index
            chunks.sort(key=lambda x: x.index)
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'wb') as output_file:
                for chunk in chunks:
                    # Read compressed chunk
                    chunk_path = Path(chunk.local_path) if chunk.local_path else None
                    if not chunk_path or not chunk_path.exists():
                        logger.error(f"Chunk file not found: {chunk_path}")
                        return False
                        
                    with open(chunk_path, 'rb') as chunk_file:
                        compressed_data = chunk_file.read()
                        
                    # Verify compressed hash
                    if verify_hashes:
                        actual_hash = hashlib.blake2b(compressed_data).hexdigest()
                        if actual_hash != chunk.hash_compressed:
                            logger.error(f"Compressed hash mismatch for chunk {chunk.chunk_id}")
                            return False
                            
                    # Decompress
                    try:
                        original_data = self.decompressor.decompress(compressed_data)
                    except Exception as e:
                        logger.error(f"Failed to decompress chunk {chunk.chunk_id}: {e}")
                        return False
                        
                    # Verify original hash
                    if verify_hashes:
                        actual_hash = hashlib.blake2b(original_data).hexdigest()
                        if actual_hash != chunk.hash_original:
                            logger.error(f"Original hash mismatch for chunk {chunk.chunk_id}")
                            return False
                            
                    # Write to output file
                    output_file.write(original_data)
                    
            logger.info(f"Successfully reconstructed file for session {session_id}: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reconstruct file from chunks: {e}")
            return False
            
    async def delete_session_chunks(self, session_id: str) -> bool:
        """Delete all chunks for a session."""
        try:
            chunks = await self.get_session_chunks(session_id)
            
            # Delete chunk files
            for chunk in chunks:
                if chunk.local_path:
                    chunk_path = Path(chunk.local_path)
                    if chunk_path.exists():
                        chunk_path.unlink()
                        
                if chunk.encrypted_path:
                    encrypted_path = Path(chunk.encrypted_path)
                    if encrypted_path.exists():
                        encrypted_path.unlink()
                        
            # Delete from database
            result = await self.db["chunks"].delete_many({"session_id": session_id})
            
            # Remove from active chunks
            if session_id in self.active_chunks:
                del self.active_chunks[session_id]
                
            logger.info(f"Deleted {result.deleted_count} chunks for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session chunks: {e}")
            return False
            
    async def get_chunk_statistics(self) -> Dict:
        """Get statistics about stored chunks."""
        try:
            # Aggregate statistics
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "total_chunks": {"$sum": 1},
                        "total_original_size": {"$sum": "$original_size"},
                        "total_compressed_size": {"$sum": "$compressed_size"},
                        "avg_compression_ratio": {"$avg": "$compression_ratio"},
                        "sessions_count": {"$addToSet": "$session_id"}
                    }
                },
                {
                    "$project": {
                        "total_chunks": 1,
                        "total_original_size": 1,
                        "total_compressed_size": 1,
                        "avg_compression_ratio": 1,
                        "unique_sessions": {"$size": "$sessions_count"},
                        "space_saved_bytes": {
                            "$subtract": ["$total_original_size", "$total_compressed_size"]
                        }
                    }
                }
            ]
            
            cursor = self.db["chunks"].aggregate(pipeline)
            stats = await cursor.to_list(1)
            
            if stats:
                return stats[0]
            else:
                return {
                    "total_chunks": 0,
                    "total_original_size": 0,
                    "total_compressed_size": 0,
                    "avg_compression_ratio": 0,
                    "unique_sessions": 0,
                    "space_saved_bytes": 0
                }
                
        except Exception as e:
            logger.error(f"Failed to get chunk statistics: {e}")
            return {}
            
    async def _create_chunk(
        self,
        session_id: str,
        index: int,
        data: bytes,
        prefix: str
    ) -> SessionChunk:
        """Create a single chunk with compression."""
        try:
            chunk_id = str(uuid.uuid4())
            original_size = len(data)
            
            # Calculate original hash
            hash_original = hashlib.blake2b(data).hexdigest()
            
            # Compress data
            compressed_data = self.compressor.compress(data)
            compressed_size = len(compressed_data)
            compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
            
            # Calculate compressed hash
            hash_compressed = hashlib.blake2b(compressed_data).hexdigest()
            
            # Save compressed chunk to file
            chunk_filename = f"{prefix}_{session_id}_{index:04d}.zst"
            chunk_path = self.chunk_dir / chunk_filename
            
            with open(chunk_path, 'wb') as f:
                f.write(compressed_data)
                
            # Create chunk object
            chunk = SessionChunk(
                chunk_id=chunk_id,
                session_id=session_id,
                index=index,
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=compression_ratio,
                hash_original=hash_original,
                hash_compressed=hash_compressed,
                created_at=datetime.now(timezone.utc),
                local_path=str(chunk_path)
            )
            
            return chunk
            
        except Exception as e:
            logger.error(f"Failed to create chunk: {e}")
            raise
            
    async def cleanup_orphaned_chunks(self, older_than_hours: int = 168) -> int:
        """Clean up chunks with no corresponding session (older than 7 days by default)."""
        try:
            cutoff = datetime.now(timezone.utc).timestamp() - (older_than_hours * 3600)
            
            # Find chunks older than cutoff with no corresponding session
            orphaned_chunks = []
            cursor = self.db["chunks"].find({
                "created_at": {"$lt": datetime.fromtimestamp(cutoff, timezone.utc).isoformat()}
            })
            
            async for chunk_doc in cursor:
                session_id = chunk_doc["session_id"]
                session_exists = await self.db["sessions"].find_one({"session_id": session_id})
                
                if not session_exists:
                    orphaned_chunks.append(chunk_doc)
                    
            # Delete orphaned chunks
            deleted_count = 0
            for chunk_doc in orphaned_chunks:
                chunk = SessionChunk.from_dict(chunk_doc)
                
                # Delete chunk file
                if chunk.local_path:
                    chunk_path = Path(chunk.local_path)
                    if chunk_path.exists():
                        chunk_path.unlink()
                        
                # Delete from database
                await self.db["chunks"].delete_one({"chunk_id": chunk.chunk_id})
                deleted_count += 1
                
            logger.info(f"Cleaned up {deleted_count} orphaned chunks")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup orphaned chunks: {e}")
            return 0
            
    async def ensure_indexes(self) -> None:
        """Ensure database indexes for chunks collection."""
        try:
            await self.db["chunks"].create_index("chunk_id", unique=True)
            await self.db["chunks"].create_index([
                ("session_id", 1), ("index", 1)
            ], unique=True)
            await self.db["chunks"].create_index("created_at")
            await self.db["chunks"].create_index("session_id")
            
        except Exception as e:
            logger.warning(f"Failed to create chunk indexes: {e}")