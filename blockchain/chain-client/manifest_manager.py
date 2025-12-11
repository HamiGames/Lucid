#!/usr/bin/env python3
"""
Manifest Manager for Lucid Blockchain System
Manages session manifests, merkle trees, and blockchain anchoring
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

import aiofiles
from motor.motor_asyncio import AsyncIOMotorDatabase


class ManifestStatus(Enum):
    """Manifest status states"""
    CREATING = "creating"
    READY = "ready"
    ANCHORING = "anchoring"
    ANCHORED = "anchored"
    FAILED = "failed"


class ChunkStatus(Enum):
    """Chunk status states"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ChunkInfo:
    """Chunk information for manifest"""
    chunk_id: str
    session_id: str
    chunk_index: int
    file_path: str
    size_bytes: int
    hash_sha256: str
    merkle_path: List[str] = field(default_factory=list)
    status: ChunkStatus = ChunkStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.chunk_id,
            "session_id": self.session_id,
            "chunk_index": self.chunk_index,
            "file_path": self.file_path,
            "size_bytes": self.size_bytes,
            "hash_sha256": self.hash_sha256,
            "merkle_path": self.merkle_path,
            "status": self.status.value,
            "created_at": self.created_at,
            "processed_at": self.processed_at
        }


@dataclass
class SessionManifest:
    """Session manifest for blockchain anchoring"""
    manifest_id: str
    session_id: str
    owner_address: str
    merkle_root: str
    chunk_count: int
    total_size_bytes: int
    start_time: float
    end_time: float
    status: ManifestStatus = ManifestStatus.CREATING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    anchored_at: Optional[datetime] = None
    anchor_tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.manifest_id,
            "session_id": self.session_id,
            "owner_address": self.owner_address,
            "merkle_root": self.merkle_root,
            "chunk_count": self.chunk_count,
            "total_size_bytes": self.total_size_bytes,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status.value,
            "created_at": self.created_at,
            "anchored_at": self.anchored_at,
            "anchor_tx_hash": self.anchor_tx_hash,
            "block_number": self.block_number,
            "metadata": self.metadata
        }


class ManifestManager:
    """Manages session manifests and merkle tree construction"""
    
    def __init__(self, db: AsyncIOMotorDatabase, output_dir: str = "/data/manifests"):
        self.db = db
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # Collections
        self.manifests_collection = self.db["session_manifests"]
        self.chunks_collection = self.db["session_chunks"]
        
        # Active manifests
        self.active_manifests: Dict[str, SessionManifest] = {}
        self.manifest_chunks: Dict[str, List[ChunkInfo]] = {}
        
    async def start(self):
        """Initialize manifest manager"""
        await self._setup_indexes()
        await self._load_active_manifests()
        self.logger.info("ManifestManager started")
        
    async def stop(self):
        """Stop manifest manager"""
        await self._save_all_manifests()
        self.logger.info("ManifestManager stopped")
        
    async def create_manifest(self, session_id: str, owner_address: str, 
                            start_time: float, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new session manifest"""
        manifest_id = f"manifest_{session_id}_{int(time.time())}"
        
        manifest = SessionManifest(
            manifest_id=manifest_id,
            session_id=session_id,
            owner_address=owner_address,
            merkle_root="",  # Will be calculated when chunks are added
            chunk_count=0,
            total_size_bytes=0,
            start_time=start_time,
            end_time=0.0,
            metadata=metadata or {}
        )
        
        # Store in database
        await self.manifests_collection.insert_one(manifest.to_dict())
        
        # Add to active manifests
        self.active_manifests[session_id] = manifest
        self.manifest_chunks[session_id] = []
        
        self.logger.info(f"Created manifest {manifest_id} for session {session_id}")
        return manifest_id
        
    async def add_chunk(self, session_id: str, chunk_index: int, file_path: str) -> str:
        """Add a chunk to the manifest"""
        if session_id not in self.active_manifests:
            raise ValueError(f"No active manifest for session {session_id}")
            
        # Calculate chunk hash
        chunk_hash = await self._calculate_file_hash(file_path)
        file_size = Path(file_path).stat().st_size
        
        chunk_id = f"chunk_{session_id}_{chunk_index}"
        chunk_info = ChunkInfo(
            chunk_id=chunk_id,
            session_id=session_id,
            chunk_index=chunk_index,
            file_path=file_path,
            size_bytes=file_size,
            hash_sha256=chunk_hash
        )
        
        # Store chunk in database
        await self.chunks_collection.insert_one(chunk_info.to_dict())
        
        # Add to active manifest
        self.manifest_chunks[session_id].append(chunk_info)
        
        # Update manifest
        manifest = self.active_manifests[session_id]
        manifest.chunk_count += 1
        manifest.total_size_bytes += file_size
        
        self.logger.info(f"Added chunk {chunk_id} to manifest for session {session_id}")
        return chunk_id
        
    async def finalize_manifest(self, session_id: str, end_time: float) -> str:
        """Finalize manifest and calculate merkle root"""
        if session_id not in self.active_manifests:
            raise ValueError(f"No active manifest for session {session_id}")
            
        manifest = self.active_manifests[session_id]
        chunks = self.manifest_chunks[session_id]
        
        # Sort chunks by index
        chunks.sort(key=lambda x: x.chunk_index)
        
        # Calculate merkle root
        merkle_root = await self._calculate_merkle_root(chunks)
        manifest.merkle_root = merkle_root
        manifest.end_time = end_time
        manifest.status = ManifestStatus.READY
        
        # Update database
        await self.manifests_collection.update_one(
            {"_id": manifest.manifest_id},
            {"$set": {
                "merkle_root": merkle_root,
                "end_time": end_time,
                "status": manifest.status.value
            }}
        )
        
        # Save manifest to file
        await self._save_manifest_to_file(manifest, chunks)
        
        self.logger.info(f"Finalized manifest {manifest.manifest_id} with merkle root {merkle_root}")
        return merkle_root
        
    async def get_manifest(self, session_id: str) -> Optional[SessionManifest]:
        """Get manifest for session"""
        if session_id in self.active_manifests:
            return self.active_manifests[session_id]
            
        # Load from database
        manifest_doc = await self.manifests_collection.find_one({"session_id": session_id})
        if manifest_doc:
            return self._manifest_from_dict(manifest_doc)
        return None
        
    async def get_manifest_chunks(self, session_id: str) -> List[ChunkInfo]:
        """Get chunks for session manifest"""
        if session_id in self.manifest_chunks:
            return self.manifest_chunks[session_id]
            
        # Load from database
        chunks_docs = await self.chunks_collection.find(
            {"session_id": session_id}
        ).sort("chunk_index", 1).to_list(length=None)
        
        return [self._chunk_from_dict(chunk_doc) for chunk_doc in chunks_docs]
        
    async def anchor_manifest(self, session_id: str, anchor_tx_hash: str, block_number: int):
        """Mark manifest as anchored on blockchain"""
        manifest = await self.get_manifest(session_id)
        if not manifest:
            raise ValueError(f"No manifest found for session {session_id}")
            
        manifest.status = ManifestStatus.ANCHORED
        manifest.anchored_at = datetime.now(timezone.utc)
        manifest.anchor_tx_hash = anchor_tx_hash
        manifest.block_number = block_number
        
        # Update database
        await self.manifests_collection.update_one(
            {"_id": manifest.manifest_id},
            {"$set": {
                "status": manifest.status.value,
                "anchored_at": manifest.anchored_at,
                "anchor_tx_hash": anchor_tx_hash,
                "block_number": block_number
            }}
        )
        
        self.logger.info(f"Anchored manifest {manifest.manifest_id} at block {block_number}")
        
    async def verify_manifest_integrity(self, session_id: str) -> bool:
        """Verify manifest integrity by recalculating merkle root"""
        manifest = await self.get_manifest(session_id)
        if not manifest:
            return False
            
        chunks = await self.get_manifest_chunks(session_id)
        if len(chunks) != manifest.chunk_count:
            return False
            
        # Recalculate merkle root
        calculated_root = await self._calculate_merkle_root(chunks)
        return calculated_root == manifest.merkle_root
        
    async def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        hash_sha256 = hashlib.sha256()
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
        
    async def _calculate_merkle_root(self, chunks: List[ChunkInfo]) -> str:
        """Calculate merkle root from chunk hashes"""
        if not chunks:
            return ""
            
        # Sort chunks by index
        chunks.sort(key=lambda x: x.chunk_index)
        
        # Get chunk hashes
        hashes = [chunk.hash_sha256 for chunk in chunks]
        
        # Build merkle tree
        while len(hashes) > 1:
            next_level = []
            for i in range(0, len(hashes), 2):
                if i + 1 < len(hashes):
                    # Combine two hashes
                    combined = hashes[i] + hashes[i + 1]
                    next_hash = hashlib.sha256(combined.encode()).hexdigest()
                    next_level.append(next_hash)
                else:
                    # Odd number of hashes, use the last one
                    next_level.append(hashes[i])
            hashes = next_level
            
        return hashes[0] if hashes else ""
        
    async def _save_manifest_to_file(self, manifest: SessionManifest, chunks: List[ChunkInfo]):
        """Save manifest to file"""
        manifest_file = self.output_dir / f"{manifest.manifest_id}.json"
        
        manifest_data = {
            "manifest": manifest.to_dict(),
            "chunks": [chunk.to_dict() for chunk in chunks]
        }
        
        async with aiofiles.open(manifest_file, 'w') as f:
            await f.write(json.dumps(manifest_data, indent=2, default=str))
            
    async def _load_manifest_from_file(self, manifest_id: str) -> Optional[Dict[str, Any]]:
        """Load manifest from file"""
        manifest_file = self.output_dir / f"{manifest_id}.json"
        if not manifest_file.exists():
            return None
            
        async with aiofiles.open(manifest_file, 'r') as f:
            content = await f.read()
            return json.loads(content)
            
    async def _setup_indexes(self):
        """Setup database indexes"""
        await self.manifests_collection.create_index("session_id", unique=True)
        await self.manifests_collection.create_index("owner_address")
        await self.manifests_collection.create_index("status")
        await self.manifests_collection.create_index("created_at")
        
        await self.chunks_collection.create_index("session_id")
        await self.chunks_collection.create_index("chunk_index")
        await self.chunks_collection.create_index([("session_id", 1), ("chunk_index", 1)], unique=True)
        
    async def _load_active_manifests(self):
        """Load active manifests from database"""
        active_docs = await self.manifests_collection.find(
            {"status": {"$in": [ManifestStatus.CREATING.value, ManifestStatus.READY.value]}}
        ).to_list(length=None)
        
        for manifest_doc in active_docs:
            manifest = self._manifest_from_dict(manifest_doc)
            self.active_manifests[manifest.session_id] = manifest
            
            # Load chunks
            chunks_docs = await self.chunks_collection.find(
                {"session_id": manifest.session_id}
            ).sort("chunk_index", 1).to_list(length=None)
            
            self.manifest_chunks[manifest.session_id] = [
                self._chunk_from_dict(chunk_doc) for chunk_doc in chunks_docs
            ]
            
    async def _save_all_manifests(self):
        """Save all active manifests to database"""
        for manifest in self.active_manifests.values():
            await self.manifests_collection.replace_one(
                {"_id": manifest.manifest_id},
                manifest.to_dict(),
                upsert=True
            )
            
    def _manifest_from_dict(self, data: Dict[str, Any]) -> SessionManifest:
        """Create SessionManifest from dictionary"""
        return SessionManifest(
            manifest_id=data["_id"],
            session_id=data["session_id"],
            owner_address=data["owner_address"],
            merkle_root=data["merkle_root"],
            chunk_count=data["chunk_count"],
            total_size_bytes=data["total_size_bytes"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            status=ManifestStatus(data["status"]),
            created_at=data["created_at"],
            anchored_at=data.get("anchored_at"),
            anchor_tx_hash=data.get("anchor_tx_hash"),
            block_number=data.get("block_number"),
            metadata=data.get("metadata", {})
        )
        
    def _chunk_from_dict(self, data: Dict[str, Any]) -> ChunkInfo:
        """Create ChunkInfo from dictionary"""
        return ChunkInfo(
            chunk_id=data["_id"],
            session_id=data["session_id"],
            chunk_index=data["chunk_index"],
            file_path=data["file_path"],
            size_bytes=data["size_bytes"],
            hash_sha256=data["hash_sha256"],
            merkle_path=data.get("merkle_path", []),
            status=ChunkStatus(data["status"]),
            created_at=data["created_at"],
            processed_at=data.get("processed_at")
        )


# Global instance
_manifest_manager: Optional[ManifestManager] = None


def get_manifest_manager() -> Optional[ManifestManager]:
    """Get global manifest manager instance"""
    return _manifest_manager


def create_manifest_manager(db: AsyncIOMotorDatabase, output_dir: str = "/data/manifests") -> ManifestManager:
    """Create manifest manager instance"""
    global _manifest_manager
    _manifest_manager = ManifestManager(db, output_dir)
    return _manifest_manager


async def cleanup_manifest_manager():
    """Cleanup manifest manager"""
    global _manifest_manager
    if _manifest_manager:
        await _manifest_manager.stop()
        _manifest_manager = None


if __name__ == "__main__":
    async def test_manifest_manager():
        """Test manifest manager functionality"""
        from motor.motor_asyncio import AsyncIOMotorClient
        
        # Connect to MongoDB
        import os
        mongo_uri = os.getenv("MONGO_URL") or os.getenv("MONGODB_URL")
        if not mongo_uri:
            raise RuntimeError("MONGO_URL or MONGODB_URL environment variable must be set")
        client = AsyncIOMotorClient(mongo_uri)
        db = client["lucid_test"]
        
        # Create manifest manager
        manager = create_manifest_manager(db)
        await manager.start()
        
        try:
            # Test manifest creation
            session_id = "test_session_001"
            owner_address = "TTestAddress123456789"
            start_time = time.time()
            
            manifest_id = await manager.create_manifest(session_id, owner_address, start_time)
            print(f"Created manifest: {manifest_id}")
            
            # Test chunk addition
            chunk_path = "/tmp/test_chunk.bin"
            with open(chunk_path, 'wb') as f:
                f.write(b"test chunk data")
                
            chunk_id = await manager.add_chunk(session_id, 0, chunk_path)
            print(f"Added chunk: {chunk_id}")
            
            # Test manifest finalization
            end_time = time.time()
            merkle_root = await manager.finalize_manifest(session_id, end_time)
            print(f"Finalized manifest with merkle root: {merkle_root}")
            
            # Test manifest retrieval
            manifest = await manager.get_manifest(session_id)
            print(f"Retrieved manifest: {manifest.manifest_id}")
            
            # Test integrity verification
            is_valid = await manager.verify_manifest_integrity(session_id)
            print(f"Manifest integrity: {is_valid}")
            
        finally:
            await manager.stop()
            client.close()
            
    # Run test
    asyncio.run(test_manifest_manager())
