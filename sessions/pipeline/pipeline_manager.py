# Path: apps/session_pipeline/pipeline_manager.py
# Lucid RDP Session Pipeline - End-to-end encrypted data processing
# Based on LUCID-STRICT requirements from Build_guide_docs

from __future__ import annotations

import asyncio
import os
import logging
import hashlib
import struct
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import json
import tempfile
import shutil

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
import blake3

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import msgpack

# Import blockchain engine
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from blockchain.core.blockchain_engine import get_blockchain_engine, BlockchainEngine, PayoutRouter

logger = logging.getLogger(__name__)

# Pipeline Constants per Spec-1a, Spec-1b
CHUNK_SIZE_MB = int(os.getenv("CHUNK_SIZE_MB", "16"))  # 16MB chunks for efficient storage
MAX_SESSION_SIZE_GB = int(os.getenv("MAX_SESSION_SIZE_GB", "100"))  # 100GB session limit
ENCRYPTION_CHUNK_SIZE = int(os.getenv("ENCRYPTION_CHUNK_SIZE", "65536"))  # 64KB encryption chunks
MERKLE_BATCH_SIZE = int(os.getenv("MERKLE_BATCH_SIZE", "1000"))  # Batch size for merkle tree
COMPRESSION_LEVEL = int(os.getenv("COMPRESSION_LEVEL", "6"))  # zstd compression level

# Storage Configuration (per Spec-1d)
STORAGE_ROOT = Path(os.getenv("STORAGE_ROOT", "./data/session_storage"))
TEMP_STORAGE = Path(os.getenv("TEMP_STORAGE", "./data/temp"))
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/lucid")


class SessionState(Enum):
    """Session pipeline states"""
    INITIALIZING = "initializing"
    RECORDING = "recording"
    FINALIZING = "finalizing"
    ANCHORING = "anchoring"
    COMPLETED = "completed"
    FAILED = "failed"


class ChunkState(Enum):
    """Chunk processing states"""
    PENDING = "pending"
    ENCRYPTED = "encrypted"
    STORED = "stored"
    MERKLED = "merkled"
    ANCHORED = "anchored"


@dataclass
class SessionMetadata:
    """Session metadata and configuration"""
    session_id: str
    owner_address: str
    node_id: str
    started_at: datetime
    total_chunks: int = 0
    total_bytes: int = 0
    encryption_key: Optional[bytes] = None
    merkle_root: Optional[str] = None
    manifest_hash: Optional[str] = None
    anchor_txid: Optional[str] = None
    state: SessionState = SessionState.INITIALIZING
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.session_id,
            "owner_addr": self.owner_address,
            "node_id": self.node_id,
            "started_at": self.started_at,
            "total_chunks": self.total_chunks,
            "total_bytes": self.total_bytes,
            "merkle_root": self.merkle_root,
            "manifest_hash": self.manifest_hash,
            "anchor_txid": self.anchor_txid,
            "state": self.state.value
        }


@dataclass
class ChunkMetadata:
    """Encrypted chunk metadata"""
    session_id: str
    chunk_id: str
    sequence: int
    original_size: int
    encrypted_size: int
    chunk_hash: str
    encryption_iv: bytes
    storage_path: Optional[str] = None
    merkle_position: Optional[int] = None
    state: ChunkState = ChunkState.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.chunk_id,
            "session_id": self.session_id,
            "sequence": self.sequence,
            "original_size": self.original_size,
            "encrypted_size": self.encrypted_size,
            "chunk_hash": self.chunk_hash,
            "encryption_iv": self.encryption_iv.hex(),
            "storage_path": self.storage_path,
            "merkle_position": self.merkle_position,
            "state": self.state.value,
            "created_at": self.created_at
        }


class SessionEncryption:
    """
    Session-level encryption handler using ChaCha20-Poly1305.
    
    Per Spec-1a: All session data must be encrypted at rest and in transit.
    Uses per-session keys derived from node hardware-backed keys.
    """
    
    def __init__(self, node_private_key: ed25519.Ed25519PrivateKey, session_id: str):
        self.node_private_key = node_private_key
        self.session_id = session_id
        self.session_key = self._derive_session_key()
        self.cipher = ChaCha20Poly1305(self.session_key)
        
    def _derive_session_key(self) -> bytes:
        """Derive session-specific encryption key from node key + session ID"""
        # Use HKDF to derive session key from node key
        node_key_bytes = self.node_private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,  # 256-bit key for ChaCha20
            salt=None,
            info=self.session_id.encode()
        )
        
        return hkdf.derive(node_key_bytes)
    
    def encrypt_chunk(self, data: bytes, chunk_id: str) -> Tuple[bytes, bytes]:
        """
        Encrypt chunk data with unique nonce per chunk.
        
        Returns: (encrypted_data, nonce)
        """
        # Generate unique nonce for this chunk
        nonce = os.urandom(12)  # 96-bit nonce for ChaCha20
        
        # Add chunk ID to additional authenticated data
        aad = chunk_id.encode()
        
        # Encrypt with authentication
        encrypted_data = self.cipher.encrypt(nonce, data, aad)
        
        return encrypted_data, nonce
    
    def decrypt_chunk(self, encrypted_data: bytes, nonce: bytes, chunk_id: str) -> bytes:
        """Decrypt chunk data"""
        aad = chunk_id.encode()
        return self.cipher.decrypt(nonce, encrypted_data, aad)


class MerkleTreeBuilder:
    """
    Incremental Merkle tree builder for session chunks.
    
    Per Spec-1b: Session manifests must include Merkle root for integrity verification.
    Uses BLAKE3 for fast cryptographic hashing.
    """
    
    def __init__(self):
        self.leaves: List[bytes] = []
        self.tree_levels: List[List[bytes]] = []
        
    def add_chunk_hash(self, chunk_hash: str):
        """Add chunk hash as leaf node"""
        self.leaves.append(bytes.fromhex(chunk_hash))
    
    def build_tree(self) -> str:
        """Build complete Merkle tree and return root hash"""
        if not self.leaves:
            return "0" * 64  # Empty tree root
        
        # Start with leaf hashes
        current_level = self.leaves.copy()
        self.tree_levels = [current_level.copy()]
        
        # Build tree bottom-up
        while len(current_level) > 1:
            next_level = []
            
            # Process pairs
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                
                # Hash pair using BLAKE3
                parent_hash = blake3.blake3(left + right).digest()
                next_level.append(parent_hash)
            
            self.tree_levels.append(next_level.copy())
            current_level = next_level
        
        # Root hash is the final single element
        root_bytes = current_level[0]
        return root_bytes.hex()
    
    def get_proof(self, leaf_index: int) -> List[str]:
        """Get Merkle proof for specific leaf"""
        if leaf_index >= len(self.leaves):
            raise ValueError("Leaf index out of range")
        
        proof = []
        index = leaf_index
        
        # Traverse up the tree
        for level in self.tree_levels[:-1]:  # Exclude root level
            sibling_index = index ^ 1  # XOR with 1 to get sibling
            
            if sibling_index < len(level):
                proof.append(level[sibling_index].hex())
            
            index //= 2
        
        return proof


class ChunkProcessor:
    """
    Chunk processing pipeline for encryption, storage and merkle tree inclusion.
    
    Handles:
    - Chunk-by-chunk encryption with ChaCha20-Poly1305
    - Secure storage with content-addressed paths
    - Merkle tree building for integrity verification
    - MongoDB metadata tracking
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, storage_root: Path):
        self.db = db
        self.storage_root = storage_root
        self.storage_root.mkdir(parents=True, exist_ok=True)
        
    async def process_chunk(self, session_meta: SessionMetadata, 
                          chunk_data: bytes, sequence: int) -> ChunkMetadata:
        """Process single chunk through encryption and storage pipeline"""
        try:
            # Generate chunk ID
            chunk_id = f"{session_meta.session_id}_{sequence:06d}"
            
            # Initialize encryption
            encryptor = SessionEncryption(
                self._load_node_key(session_meta.node_id),
                session_meta.session_id
            )
            
            # Encrypt chunk
            encrypted_data, nonce = encryptor.encrypt_chunk(chunk_data, chunk_id)
            
            # Calculate chunk hash
            chunk_hash = blake3.blake3(chunk_data).hexdigest()
            
            # Create chunk metadata
            chunk_meta = ChunkMetadata(
                session_id=session_meta.session_id,
                chunk_id=chunk_id,
                sequence=sequence,
                original_size=len(chunk_data),
                encrypted_size=len(encrypted_data),
                chunk_hash=chunk_hash,
                encryption_iv=nonce
            )
            
            # Store encrypted chunk to disk
            storage_path = await self._store_encrypted_chunk(
                encrypted_data, session_meta.session_id, chunk_id
            )
            chunk_meta.storage_path = storage_path
            chunk_meta.state = ChunkState.STORED
            
            # Store chunk metadata in MongoDB
            await self.db["chunks"].replace_one(
                {"_id": chunk_id},
                chunk_meta.to_dict(),
                upsert=True
            )
            
            logger.debug(f"Processed chunk {chunk_id}: {len(chunk_data)} -> {len(encrypted_data)} bytes")
            return chunk_meta
            
        except Exception as e:
            logger.error(f"Failed to process chunk {sequence}: {e}")
            raise
    
    async def _store_encrypted_chunk(self, encrypted_data: bytes, 
                                   session_id: str, chunk_id: str) -> str:
        """Store encrypted chunk to content-addressed storage"""
        # Create session directory
        session_dir = self.storage_root / session_id[:2] / session_id[2:4] / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Store chunk file
        chunk_path = session_dir / f"{chunk_id}.enc"
        
        with open(chunk_path, 'wb') as f:
            f.write(encrypted_data)
        
        return str(chunk_path.relative_to(self.storage_root))
    
    def _load_node_key(self, node_id: str) -> ed25519.Ed25519PrivateKey:
        """Load node private key (simplified - would use hardware security module)"""
        # This is simplified - in production would load from hardware-backed keystore
        key_bytes = hashlib.sha256(f"node_{node_id}".encode()).digest()
        return ed25519.Ed25519PrivateKey.from_private_bytes(key_bytes)


class SessionPipelineManager:
    """
    Main session pipeline orchestrator.
    
    Manages:
    - Session lifecycle from initialization to blockchain anchoring
    - Real-time chunk processing during RDP sessions
    - Merkle tree building and manifest creation
    - Integration with blockchain engine for anchoring
    - Payout calculations and distribution
    """
    
    def __init__(self):
        self.mongo_client = AsyncIOMotorClient(MONGODB_URI)
        self.db = self.mongo_client.get_default_database()
        
        # Initialize components
        self.chunk_processor = ChunkProcessor(self.db, STORAGE_ROOT)
        self.blockchain = get_blockchain_engine()
        
        # Session tracking
        self.active_sessions: Dict[str, SessionMetadata] = {}
        self.merkle_builders: Dict[str, MerkleTreeBuilder] = {}
        
        # Initialize MongoDB indexes
        asyncio.create_task(self._setup_mongodb_indexes())
        
        logger.info("Session pipeline manager initialized")
    
    async def _setup_mongodb_indexes(self):
        """Setup MongoDB indexes for session pipeline collections"""
        try:
            # sessions collection
            await self.db["sessions"].create_index([("owner_addr", 1)])
            await self.db["sessions"].create_index([("node_id", 1)])
            await self.db["sessions"].create_index([("state", 1)])
            await self.db["sessions"].create_index([("started_at", -1)])
            
            # chunks collection - sharded on session_id
            await self.db["chunks"].create_index([("session_id", 1), ("sequence", 1)])
            await self.db["chunks"].create_index([("state", 1)])
            
            logger.info("Session pipeline MongoDB indexes created")
            
        except Exception as e:
            logger.error(f"Failed to setup MongoDB indexes: {e}")
    
    async def initialize_session(self, session_id: str, owner_address: str, 
                               node_id: str) -> SessionMetadata:
        """Initialize new session pipeline"""
        try:
            session_meta = SessionMetadata(
                session_id=session_id,
                owner_address=owner_address,
                node_id=node_id,
                started_at=datetime.now(timezone.utc),
                state=SessionState.INITIALIZING
            )
            
            # Store session metadata
            await self.db["sessions"].replace_one(
                {"_id": session_id},
                session_meta.to_dict(),
                upsert=True
            )
            
            # Initialize Merkle tree builder
            self.merkle_builders[session_id] = MerkleTreeBuilder()
            
            # Track active session
            self.active_sessions[session_id] = session_meta
            session_meta.state = SessionState.RECORDING
            
            logger.info(f"Session initialized: {session_id} (owner: {owner_address})")
            return session_meta
            
        except Exception as e:
            logger.error(f"Failed to initialize session {session_id}: {e}")
            raise
    
    async def process_session_chunk(self, session_id: str, chunk_data: bytes) -> bool:
        """Process incoming session chunk in real-time"""
        try:
            session_meta = self.active_sessions.get(session_id)
            if not session_meta or session_meta.state != SessionState.RECORDING:
                logger.warning(f"Session not active for chunk processing: {session_id}")
                return False
            
            # Check session size limits
            new_total = session_meta.total_bytes + len(chunk_data)
            if new_total > MAX_SESSION_SIZE_GB * 1024 * 1024 * 1024:
                logger.error(f"Session size limit exceeded: {session_id}")
                await self._fail_session(session_id, "size_limit_exceeded")
                return False
            
            # Process chunk
            chunk_meta = await self.chunk_processor.process_chunk(
                session_meta, chunk_data, session_meta.total_chunks
            )
            
            # Update session metadata
            session_meta.total_chunks += 1
            session_meta.total_bytes = new_total
            
            # Add to Merkle tree
            merkle_builder = self.merkle_builders[session_id]
            merkle_builder.add_chunk_hash(chunk_meta.chunk_hash)
            chunk_meta.merkle_position = len(merkle_builder.leaves) - 1
            chunk_meta.state = ChunkState.MERKLED
            
            # Update chunk in database
            await self.db["chunks"].update_one(
                {"_id": chunk_meta.chunk_id},
                {"$set": {
                    "merkle_position": chunk_meta.merkle_position,
                    "state": chunk_meta.state.value
                }}
            )
            
            # Update session in database
            await self.db["sessions"].update_one(
                {"_id": session_id},
                {"$set": {
                    "total_chunks": session_meta.total_chunks,
                    "total_bytes": session_meta.total_bytes
                }}
            )
            
            logger.debug(f"Chunk processed: {session_id} chunk {session_meta.total_chunks}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process chunk for session {session_id}: {e}")
            await self._fail_session(session_id, f"chunk_processing_error: {e}")
            return False
    
    async def finalize_session(self, session_id: str) -> bool:
        """Finalize session and anchor to blockchain"""
        try:
            session_meta = self.active_sessions.get(session_id)
            if not session_meta:
                logger.error(f"Session not found for finalization: {session_id}")
                return False
            
            session_meta.state = SessionState.FINALIZING
            
            # Build final Merkle tree
            merkle_builder = self.merkle_builders[session_id]
            merkle_root = merkle_builder.build_tree()
            session_meta.merkle_root = merkle_root
            
            # Create session manifest
            manifest = await self._create_session_manifest(session_meta)
            manifest_hash = blake3.blake3(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
            session_meta.manifest_hash = manifest_hash
            
            # Update session state
            session_meta.state = SessionState.ANCHORING
            await self.db["sessions"].update_one(
                {"_id": session_id},
                {"$set": {
                    "merkle_root": merkle_root,
                    "manifest_hash": manifest_hash,
                    "state": session_meta.state.value
                }}
            )
            
            # Anchor to blockchain
            try:
                anchor_txid = await self.blockchain.anchor_session_manifest(
                    session_id=session_id,
                    manifest_hash=manifest_hash,
                    merkle_root=merkle_root,
                    owner_address=session_meta.owner_address,
                    chunk_count=session_meta.total_chunks
                )
                
                session_meta.anchor_txid = anchor_txid
                session_meta.state = SessionState.COMPLETED
                
                # Mark all chunks as anchored
                await self.db["chunks"].update_many(
                    {"session_id": session_id},
                    {"$set": {"state": ChunkState.ANCHORED.value}}
                )
                
                # Clean up active session tracking
                del self.active_sessions[session_id]
                del self.merkle_builders[session_id]
                
                logger.info(f"Session finalized and anchored: {session_id} -> {anchor_txid}")
                
                # Trigger payout processing
                asyncio.create_task(self._process_session_payouts(session_meta))
                
                return True
                
            except Exception as e:
                logger.error(f"Blockchain anchoring failed for session {session_id}: {e}")
                await self._fail_session(session_id, f"anchoring_failed: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Session finalization failed: {session_id}: {e}")
            await self._fail_session(session_id, f"finalization_error: {e}")
            return False
    
    async def _create_session_manifest(self, session_meta: SessionMetadata) -> Dict[str, Any]:
        """Create session manifest with chunk metadata"""
        # Get all chunks for session
        chunks_cursor = self.db["chunks"].find(
            {"session_id": session_meta.session_id}
        ).sort("sequence", 1)
        
        chunks = await chunks_cursor.to_list(length=None)
        
        manifest = {
            "version": "1.0",
            "sessionId": session_meta.session_id,
            "owner": session_meta.owner_address,
            "nodeId": session_meta.node_id,
            "startedAt": session_meta.started_at.isoformat(),
            "totalChunks": session_meta.total_chunks,
            "totalBytes": session_meta.total_bytes,
            "merkleRoot": session_meta.merkle_root,
            "chunks": [
                {
                    "id": chunk["_id"],
                    "sequence": chunk["sequence"],
                    "hash": chunk["chunk_hash"],
                    "originalSize": chunk["original_size"],
                    "encryptedSize": chunk["encrypted_size"],
                    "merklePosition": chunk.get("merkle_position")
                }
                for chunk in chunks
            ]
        }
        
        return manifest
    
    async def _fail_session(self, session_id: str, reason: str):
        """Mark session as failed and clean up"""
        try:
            await self.db["sessions"].update_one(
                {"_id": session_id},
                {"$set": {
                    "state": SessionState.FAILED.value,
                    "failure_reason": reason,
                    "failed_at": datetime.now(timezone.utc)
                }}
            )
            
            # Clean up tracking
            self.active_sessions.pop(session_id, None)
            self.merkle_builders.pop(session_id, None)
            
            logger.error(f"Session failed: {session_id} - {reason}")
            
        except Exception as e:
            logger.error(f"Failed to mark session as failed: {e}")
    
    async def _process_session_payouts(self, session_meta: SessionMetadata):
        """Process payouts for completed session"""
        try:
            # Calculate payout amounts based on session size and duration
            base_payout = self._calculate_base_payout(session_meta)
            node_payout = base_payout * 0.7  # 70% to node worker
            network_payout = base_payout * 0.3  # 30% to network
            
            # Create node worker payout (KYC required per R-MUST-018)
            if node_payout > 0:
                # Note: In production, need actual node worker address and KYC data
                await self.blockchain.create_payout(
                    session_id=session_meta.session_id,
                    recipient_address="TSomeNodeWorkerAddress",  # Would be actual node address
                    amount_usdt=node_payout,
                    router_type=PayoutRouter.PRKYC,
                    reason=f"Session processing: {session_meta.total_bytes} bytes",
                    private_key="node_payout_private_key",  # Would be actual key
                    kyc_hash="node_kyc_hash",  # Would be actual KYC hash
                    compliance_signature={  # Would be actual compliance sig
                        "expiry": int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp()),
                        "v": 27,
                        "r": "0x" + "0" * 64,
                        "s": "0x" + "0" * 64
                    }
                )
            
            logger.info(f"Session payouts processed: {session_meta.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to process session payouts: {e}")
    
    def _calculate_base_payout(self, session_meta: SessionMetadata) -> float:
        """Calculate base payout amount in USDT"""
        # Simple calculation: $0.01 per GB processed
        gb_processed = session_meta.total_bytes / (1024 * 1024 * 1024)
        return gb_processed * 0.01
    
    # Public API methods
    
    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session status and metadata"""
        try:
            session_doc = await self.db["sessions"].find_one({"_id": session_id})
            return session_doc
        except Exception as e:
            logger.error(f"Failed to get session status: {e}")
            return None
    
    async def get_session_chunks(self, session_id: str, limit: int = 100, 
                               offset: int = 0) -> List[Dict[str, Any]]:
        """Get session chunks with pagination"""
        try:
            chunks_cursor = self.db["chunks"].find(
                {"session_id": session_id}
            ).sort("sequence", 1).skip(offset).limit(limit)
            
            return await chunks_cursor.to_list(length=None)
            
        except Exception as e:
            logger.error(f"Failed to get session chunks: {e}")
            return []
    
    async def get_chunk_merkle_proof(self, chunk_id: str) -> Optional[List[str]]:
        """Get Merkle proof for specific chunk"""
        try:
            chunk = await self.db["chunks"].find_one({"_id": chunk_id})
            if not chunk or chunk.get("merkle_position") is None:
                return None
            
            session_id = chunk["session_id"]
            merkle_position = chunk["merkle_position"]
            
            # Rebuild Merkle tree for proof generation
            chunks_cursor = self.db["chunks"].find(
                {"session_id": session_id}
            ).sort("sequence", 1)
            
            merkle_builder = MerkleTreeBuilder()
            async for chunk_doc in chunks_cursor:
                merkle_builder.add_chunk_hash(chunk_doc["chunk_hash"])
            
            merkle_builder.build_tree()
            return merkle_builder.get_proof(merkle_position)
            
        except Exception as e:
            logger.error(f"Failed to get Merkle proof: {e}")
            return None
    
    async def decrypt_chunk(self, chunk_id: str, node_private_key: ed25519.Ed25519PrivateKey) -> Optional[bytes]:
        """Decrypt and return chunk data"""
        try:
            # Get chunk metadata
            chunk = await self.db["chunks"].find_one({"_id": chunk_id})
            if not chunk:
                logger.warning(f"Chunk not found: {chunk_id}")
                return None
            
            # Read encrypted chunk data
            storage_path = STORAGE_ROOT / chunk["storage_path"]
            if not storage_path.exists():
                logger.error(f"Chunk file not found: {storage_path}")
                return None
            
            with open(storage_path, 'rb') as f:
                encrypted_data = f.read()
            
            # Initialize decryption
            encryptor = SessionEncryption(node_private_key, chunk["session_id"])
            
            # Decrypt chunk
            nonce = bytes.fromhex(chunk["encryption_iv"])
            decrypted_data = encryptor.decrypt_chunk(encrypted_data, nonce, chunk_id)
            
            # Verify chunk hash
            actual_hash = blake3.blake3(decrypted_data).hexdigest()
            if actual_hash != chunk["chunk_hash"]:
                logger.error(f"Chunk hash mismatch: {chunk_id}")
                return None
            
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Failed to decrypt chunk: {e}")
            return None
    
    async def cleanup_failed_sessions(self, older_than_hours: int = 24):
        """Clean up failed or abandoned sessions"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
            
            # Find failed/stuck sessions
            failed_cursor = self.db["sessions"].find({
                "$or": [
                    {"state": SessionState.FAILED.value},
                    {
                        "state": {"$in": [SessionState.RECORDING.value, SessionState.FINALIZING.value]},
                        "started_at": {"$lt": cutoff_time}
                    }
                ]
            })
            
            cleanup_count = 0
            async for session in failed_cursor:
                session_id = session["_id"]
                
                # Remove chunks from storage
                chunks_cursor = self.db["chunks"].find({"session_id": session_id})
                async for chunk in chunks_cursor:
                    if chunk.get("storage_path"):
                        try:
                            storage_path = STORAGE_ROOT / chunk["storage_path"]
                            if storage_path.exists():
                                storage_path.unlink()
                        except Exception as e:
                            logger.warning(f"Failed to delete chunk file: {e}")
                
                # Remove database records
                await self.db["chunks"].delete_many({"session_id": session_id})
                await self.db["sessions"].delete_one({"_id": session_id})
                
                cleanup_count += 1
                logger.info(f"Cleaned up failed session: {session_id}")
            
            logger.info(f"Session cleanup completed: {cleanup_count} sessions removed")
            
        except Exception as e:
            logger.error(f"Session cleanup failed: {e}")
    
    async def close(self):
        """Close pipeline manager and connections"""
        self.mongo_client.close()
        logger.info("Session pipeline manager closed")


# Global pipeline manager instance  
pipeline_manager: Optional[SessionPipelineManager] = None


def get_pipeline_manager() -> SessionPipelineManager:
    """Get global pipeline manager instance"""
    global pipeline_manager
    if pipeline_manager is None:
        pipeline_manager = SessionPipelineManager()
    return pipeline_manager


async def start_pipeline_service():
    """Start session pipeline service"""
    manager = get_pipeline_manager()
    logger.info("Session pipeline service started")


async def stop_pipeline_service():
    """Stop session pipeline service"""
    global pipeline_manager
    if pipeline_manager:
        await pipeline_manager.close()
        pipeline_manager = None


if __name__ == "__main__":
    # Test session pipeline
    async def test_pipeline():
        print("Starting Lucid session pipeline...")
        await start_pipeline_service()
        
        # Test session processing
        manager = get_pipeline_manager()
        
        # Initialize test session
        session = await manager.initialize_session(
            session_id=str(uuid.uuid4()),
            owner_address="0x1234567890123456789012345678901234567890",
            node_id="test_node_001"
        )
        
        print(f"Test session created: {session.session_id}")
        
        # Process test chunks
        for i in range(5):
            test_data = f"Test chunk data {i} " * 1000
            await manager.process_session_chunk(session.session_id, test_data.encode())
            print(f"Processed chunk {i + 1}")
        
        # Finalize session
        await manager.finalize_session(session.session_id)
        print("Session finalized and anchored")
        
        # Keep running briefly
        await asyncio.sleep(5)
        
        print("Stopping session pipeline...")
        await stop_pipeline_service()
    
    asyncio.run(test_pipeline())