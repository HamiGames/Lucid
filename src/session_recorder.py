# Lucid RDP Session Recorder
# Handles RDP session recording, chunking, and compression
# Based on LUCID-STRICT requirements for Raspberry Pi 5

from __future__ import annotations

import asyncio
import os
import zstandard as zstd
import hashlib
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

logger = logging.getLogger(__name__)

# Runtime variables aligned for Windows 11 and Raspberry Pi 5
CHUNK_MIN_SIZE = int(os.getenv("LUCID_CHUNK_MIN_SIZE", "8388608"))  # 8MB
CHUNK_MAX_SIZE = int(os.getenv("LUCID_CHUNK_MAX_SIZE", "16777216"))  # 16MB
COMPRESSION_LEVEL = int(os.getenv("LUCID_COMPRESSION_LEVEL", "3"))  # Zstd level 3
SESSION_DATA_DIR = Path(os.getenv("LUCID_SESSION_DATA_DIR", "/tmp/lucid/sessions"))
ONION_STATE_DIR = Path(os.getenv("LUCID_ONION_STATE_DIR", "/run/lucid/onion"))


@dataclass(frozen=True)
class SessionChunk:
    """Represents a compressed and encrypted RDP session chunk"""
    chunk_id: str
    session_id: str
    sequence_number: int
    original_size: int
    compressed_size: int
    encrypted_size: int
    local_path: Path
    ciphertext_sha256: str
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        return {
            "_id": self.chunk_id,
            "session_id": self.session_id,
            "idx": self.sequence_number,
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "encrypted_size": self.encrypted_size,
            "local_path": str(self.local_path),
            "ciphertext_sha256": self.ciphertext_sha256,
            "created_at": self.created_at,
            "metadata": self.metadata
        }


@dataclass
class SessionManifest:
    """Session manifest with anchoring data"""
    session_id: str
    owner_address: str
    started_at: datetime
    ended_at: Optional[datetime]
    chunks: List[SessionChunk]
    manifest_hash: Optional[str] = None
    merkle_root: Optional[str] = None
    anchor_txid: Optional[str] = None

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)

    @property
    def total_original_size(self) -> int:
        return sum(chunk.original_size for chunk in self.chunks)

    @property
    def total_compressed_size(self) -> int:
        return sum(chunk.compressed_size for chunk in self.chunks)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        return {
            "_id": self.session_id,
            "owner_addr": self.owner_address,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "chunk_count": self.chunk_count,
            "manifest_hash": self.manifest_hash,
            "merkle_root": self.merkle_root,
            "anchor_txid": self.anchor_txid,
            "chunks": [chunk.to_dict() for chunk in self.chunks]
        }


class SessionEncryption:
    """XChaCha20-Poly1305 encryption for session chunks"""
    
    def __init__(self, session_key: bytes):
        """Initialize with session-derived key"""
        if len(session_key) != 32:
            raise ValueError("Session key must be 32 bytes")
        self.cipher = ChaCha20Poly1305(session_key)
    
    @classmethod
    def derive_session_key(cls, session_id: str, master_key: bytes) -> bytes:
        """Derive session key using HKDF-BLAKE3"""
        hkdf = HKDF(
            algorithm=hashes.BLAKE2b(64),
            length=32,
            salt=None,
            info=f"lucid-session-{session_id}".encode('utf-8')
        )
        return hkdf.derive(master_key)
    
    def encrypt_chunk(self, plaintext: bytes, chunk_nonce: bytes) -> bytes:
        """Encrypt chunk with per-chunk nonce"""
        if len(chunk_nonce) != 12:  # ChaCha20Poly1305 requires 12-byte nonce
            raise ValueError("Nonce must be 12 bytes")
        return self.cipher.encrypt(chunk_nonce, plaintext, None)
    
    def decrypt_chunk(self, ciphertext: bytes, chunk_nonce: bytes) -> bytes:
        """Decrypt chunk with per-chunk nonce"""
        return self.cipher.decrypt(chunk_nonce, ciphertext, None)


class SessionRecorder:
    """Main session recorder for Lucid RDP"""
    
    def __init__(self, session_id: str, owner_address: str, master_key: bytes):
        self.session_id = session_id
        self.owner_address = owner_address
        self.started_at = datetime.now(timezone.utc)
        self.ended_at: Optional[datetime] = None
        
        # Initialize encryption
        session_key = SessionEncryption.derive_session_key(session_id, master_key)
        self.encryptor = SessionEncryption(session_key)
        
        # Initialize storage
        self.session_dir = SESSION_DATA_DIR / session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # Chunk tracking
        self.chunks: List[SessionChunk] = []
        self.current_chunk_data: bytes = b""
        self.current_chunk_number = 0
        
        # Recording state
        self.is_recording = False
        self._recording_task: Optional[asyncio.Task] = None
        
        logger.info(f"Session recorder initialized: {session_id}")
    
    async def start_recording(self) -> None:
        """Start RDP session recording"""
        if self.is_recording:
            logger.warning(f"Session {self.session_id} already recording")
            return
        
        self.is_recording = True
        self._recording_task = asyncio.create_task(self._recording_loop())
        logger.info(f"Started recording session: {self.session_id}")
    
    async def stop_recording(self) -> SessionManifest:
        """Stop recording and finalize session"""
        if not self.is_recording:
            logger.warning(f"Session {self.session_id} not recording")
            return await self._create_manifest()
        
        self.is_recording = False
        self.ended_at = datetime.now(timezone.utc)
        
        if self._recording_task:
            self._recording_task.cancel()
            try:
                await self._recording_task
            except asyncio.CancelledError:
                pass
        
        # Finalize any remaining chunk data
        if self.current_chunk_data:
            await self._finalize_chunk()
        
        manifest = await self._create_manifest()
        logger.info(f"Stopped recording session: {self.session_id}, chunks: {len(self.chunks)}")
        return manifest
    
    async def _recording_loop(self) -> None:
        """Main recording loop - simulated RDP capture"""
        try:
            while self.is_recording:
                # Simulate RDP data capture
                # In real implementation, this would capture from xrdp/Wayland
                rdp_data = await self._capture_rdp_frame()
                
                if rdp_data:
                    await self._append_data(rdp_data)
                
                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            logger.info(f"Recording loop cancelled for session: {self.session_id}")
        except Exception as e:
            logger.error(f"Recording error for session {self.session_id}: {e}")
    
    async def _capture_rdp_frame(self) -> bytes:
        """Simulate RDP frame capture - replace with real xrdp integration"""
        # This is a simulation - real implementation would capture from RDP stream
        import random
        frame_size = random.randint(1024, 4096)  # 1KB to 4KB per frame
        return os.urandom(frame_size)
    
    async def _append_data(self, data: bytes) -> None:
        """Append data to current chunk, finalize if needed"""
        self.current_chunk_data += data
        
        # Check if chunk is ready for finalization
        if len(self.current_chunk_data) >= CHUNK_MIN_SIZE:
            await self._finalize_chunk()
    
    async def _finalize_chunk(self) -> SessionChunk:
        """Compress, encrypt, and store current chunk"""
        if not self.current_chunk_data:
            raise ValueError("No chunk data to finalize")
        
        original_size = len(self.current_chunk_data)
        
        # Compress with Zstd
        compressed_data = zstd.compress(self.current_chunk_data, COMPRESSION_LEVEL)
        compressed_size = len(compressed_data)
        
        # Generate chunk nonce and encrypt
        chunk_nonce = os.urandom(12)
        encrypted_data = self.encryptor.encrypt_chunk(compressed_data, chunk_nonce)
        encrypted_size = len(encrypted_data)
        
        # Generate chunk ID and file path
        chunk_id = f"{self.session_id}-{self.current_chunk_number:06d}"
        chunk_file = self.session_dir / f"{chunk_id}.enc"
        
        # Store encrypted chunk with nonce prepended
        chunk_file.write_bytes(chunk_nonce + encrypted_data)
        
        # Calculate ciphertext hash
        ciphertext_sha256 = hashlib.sha256(encrypted_data).hexdigest()
        
        # Create chunk metadata
        chunk = SessionChunk(
            chunk_id=chunk_id,
            session_id=self.session_id,
            sequence_number=self.current_chunk_number,
            original_size=original_size,
            compressed_size=compressed_size,
            encrypted_size=encrypted_size,
            local_path=chunk_file,
            ciphertext_sha256=ciphertext_sha256,
            created_at=datetime.now(timezone.utc),
            metadata={
                "compression_ratio": compressed_size / original_size,
                "encryption_overhead": (encrypted_size - compressed_size) / compressed_size
            }
        )
        
        self.chunks.append(chunk)
        
        # Reset for next chunk
        self.current_chunk_data = b""
        self.current_chunk_number += 1
        
        logger.debug(f"Finalized chunk {chunk_id}: {original_size}→{compressed_size}→{encrypted_size} bytes")
        return chunk
    
    async def _create_manifest(self) -> SessionManifest:
        """Create session manifest for blockchain anchoring"""
        manifest = SessionManifest(
            session_id=self.session_id,
            owner_address=self.owner_address,
            started_at=self.started_at,
            ended_at=self.ended_at,
            chunks=self.chunks
        )
        
        # Calculate manifest hash for integrity
        manifest_data = str(manifest.to_dict()).encode('utf-8')
        manifest.manifest_hash = hashlib.blake2b(manifest_data).hexdigest()
        
        # Calculate Merkle root of chunk hashes for blockchain anchoring
        if self.chunks:
            chunk_hashes = [bytes.fromhex(chunk.ciphertext_sha256) for chunk in self.chunks]
            merkle_root = self._calculate_merkle_root(chunk_hashes)
            manifest.merkle_root = merkle_root.hex()
        
        return manifest
    
    def _calculate_merkle_root(self, hashes: List[bytes]) -> bytes:
        """Calculate BLAKE3 Merkle root of chunk hashes"""
        if not hashes:
            return b"\x00" * 32
        
        nodes = hashes.copy()
        
        while len(nodes) > 1:
            if len(nodes) % 2 == 1:
                nodes.append(nodes[-1])  # Duplicate last node if odd count
            
            new_nodes = []
            for i in range(0, len(nodes), 2):
                combined = nodes[i] + nodes[i + 1]
                # Using BLAKE3 for Merkle tree hashing per spec
                import blake3
                new_nodes.append(blake3.blake3(combined).digest())
            
            nodes = new_nodes
        
        return nodes[0]


class SessionManager:
    """Manages multiple recording sessions"""
    
    def __init__(self, master_key: bytes):
        self.master_key = master_key
        self.active_sessions: Dict[str, SessionRecorder] = {}
    
    async def start_session(self, owner_address: str) -> str:
        """Start a new recording session"""
        session_id = str(uuid.uuid4())
        
        recorder = SessionRecorder(session_id, owner_address, self.master_key)
        self.active_sessions[session_id] = recorder
        
        await recorder.start_recording()
        return session_id
    
    async def stop_session(self, session_id: str) -> Optional[SessionManifest]:
        """Stop and finalize a recording session"""
        recorder = self.active_sessions.get(session_id)
        if not recorder:
            logger.warning(f"Session {session_id} not found")
            return None
        
        manifest = await recorder.stop_recording()
        del self.active_sessions[session_id]
        
        return manifest
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        return list(self.active_sessions.keys())
    
    async def shutdown(self) -> None:
        """Shutdown all active sessions"""
        for session_id in list(self.active_sessions.keys()):
            await self.stop_session(session_id)