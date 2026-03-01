# Path: sessions/processor/session_manifest.py
# LUCID Session Manifest Generator - Session metadata and integrity
# Professional session manifest generation with blockchain anchoring
# Multi-platform support for ARM64 Pi and AMD64 development

from __future__ import annotations

import asyncio
import logging
import os
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
import blake3

logger = logging.getLogger(__name__)

# Configuration from environment
MANIFEST_PATH = Path(os.getenv("LUCID_MANIFEST_PATH", "/app/data/manifests"))
DEFAULT_CHUNK_SIZE = int(os.getenv("LUCID_MANIFEST_CHUNK_SIZE", "1048576"))  # 1MB
MANIFEST_SIGNATURE_ALGORITHM = os.getenv("LUCID_MANIFEST_SIGNATURE_ALGORITHM", "Ed25519")
MANIFEST_HASH_ALGORITHM = os.getenv("LUCID_MANIFEST_HASH_ALGORITHM", "BLAKE3")


class ManifestStatus(Enum):
    """Manifest generation status"""
    PENDING = "pending"
    GENERATING = "generating"
    GENERATED = "generated"
    ANCHORED = "anchored"
    ERROR = "error"


class ManifestType(Enum):
    """Types of session manifests"""
    SESSION_RECORDING = "session_recording"
    SESSION_DATA = "session_data"
    SESSION_COMPRESSION = "session_compression"
    SESSION_ENCRYPTION = "session_encryption"
    SESSION_BLOCKCHAIN = "session_blockchain"


@dataclass
class ChunkInfo:
    """Information about a data chunk"""
    chunk_id: str
    chunk_index: int
    size: int
    checksum: str
    compression_ratio: Optional[float] = None
    encryption_key_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionMetadata:
    """Session metadata information"""
    session_id: str
    owner_address: str
    session_type: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    total_size: int = 0
    chunk_count: int = 0
    compression_algorithm: Optional[str] = None
    encryption_algorithm: Optional[str] = None
    blockchain_network: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionManifest:
    """Session manifest structure"""
    manifest_id: str
    manifest_version: str
    manifest_type: ManifestType
    session_metadata: SessionMetadata
    chunks: List[ChunkInfo]
    merkle_root: str
    total_checksum: str
    generated_at: datetime
    generated_by: str
    signature: Optional[str] = None
    blockchain_tx_hash: Optional[str] = None
    blockchain_block_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ManifestGenerationTask:
    """Manifest generation task"""
    task_id: str
    session_id: str
    owner_address: str
    manifest_type: ManifestType
    status: ManifestStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    manifest: Optional[SessionManifest] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SessionManifestGenerator:
    """
    Professional session manifest generator for Lucid RDP sessions.
    
    Creates comprehensive manifests with integrity verification,
    blockchain anchoring, and cryptographic signatures.
    """
    
    def __init__(self):
        """Initialize manifest generator"""
        # Task tracking
        self.active_tasks: Dict[str, ManifestGenerationTask] = {}
        self.generated_manifests: Dict[str, SessionManifest] = {}
        
        # Cryptographic keys
        self.signing_key: Optional[ed25519.Ed25519PrivateKey] = None
        self.verification_key: Optional[ed25519.Ed25519PublicKey] = None
        
        # Create directories
        self._create_directories()
        
        # Initialize cryptographic keys
        self._initialize_keys()
        
        logger.info("Session manifest generator initialized")
    
    def _create_directories(self) -> None:
        """Create required directories"""
        MANIFEST_PATH.mkdir(parents=True, exist_ok=True)
        (MANIFEST_PATH / "temp").mkdir(exist_ok=True)
        (MANIFEST_PATH / "signed").mkdir(exist_ok=True)
        logger.info(f"Created manifest directories: {MANIFEST_PATH}")
    
    def _initialize_keys(self) -> None:
        """Initialize cryptographic signing keys"""
        try:
            # Generate or load signing key
            key_path = MANIFEST_PATH / "manifest_signing_key.pem"
            
            if key_path.exists():
                # Load existing key
                with open(key_path, 'rb') as f:
                    key_data = f.read()
                self.signing_key = serialization.load_pem_private_key(
                    key_data, password=None
                )
                self.verification_key = self.signing_key.public_key()
                logger.info("Loaded existing manifest signing key")
            else:
                # Generate new key
                self.signing_key = ed25519.Ed25519PrivateKey.generate()
                self.verification_key = self.signing_key.public_key()
                
                # Save key
                key_data = self.signing_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
                with open(key_path, 'wb') as f:
                    f.write(key_data)
                logger.info("Generated new manifest signing key")
                
        except Exception as e:
            logger.error(f"Failed to initialize signing keys: {e}")
            raise
    
    async def generate_manifest(self,
                               session_id: str,
                               owner_address: str,
                               manifest_type: ManifestType,
                               session_data_path: Optional[Path] = None,
                               chunk_size: int = DEFAULT_CHUNK_SIZE) -> SessionManifest:
        """Generate session manifest"""
        try:
            # Generate task ID
            task_id = str(uuid.uuid4())
            
            # Create generation task
            task = ManifestGenerationTask(
                task_id=task_id,
                session_id=session_id,
                owner_address=owner_address,
                manifest_type=manifest_type,
                status=ManifestStatus.GENERATING,
                created_at=datetime.now(timezone.utc),
                metadata={}
            )
            
            # Store task
            self.active_tasks[task_id] = task
            
            # Generate manifest based on type
            if manifest_type == ManifestType.SESSION_RECORDING:
                manifest = await self._generate_recording_manifest(
                    session_id, owner_address, session_data_path, chunk_size
                )
            elif manifest_type == ManifestType.SESSION_DATA:
                manifest = await self._generate_data_manifest(
                    session_id, owner_address, session_data_path, chunk_size
                )
            elif manifest_type == ManifestType.SESSION_COMPRESSION:
                manifest = await self._generate_compression_manifest(
                    session_id, owner_address, session_data_path, chunk_size
                )
            elif manifest_type == ManifestType.SESSION_ENCRYPTION:
                manifest = await self._generate_encryption_manifest(
                    session_id, owner_address, session_data_path, chunk_size
                )
            elif manifest_type == ManifestType.SESSION_BLOCKCHAIN:
                manifest = await self._generate_blockchain_manifest(
                    session_id, owner_address, session_data_path, chunk_size
                )
            else:
                raise ValueError(f"Unsupported manifest type: {manifest_type}")
            
            # Sign manifest
            manifest.signature = await self._sign_manifest(manifest)
            
            # Save manifest
            await self._save_manifest(manifest)
            
            # Update task
            task.status = ManifestStatus.GENERATED
            task.completed_at = datetime.now(timezone.utc)
            task.manifest = manifest
            
            # Store manifest
            self.generated_manifests[manifest.manifest_id] = manifest
            
            logger.info(f"Generated manifest: {manifest.manifest_id}")
            
            return manifest
            
        except Exception as e:
            logger.error(f"Manifest generation failed: {e}")
            if task_id in self.active_tasks:
                self.active_tasks[task_id].status = ManifestStatus.ERROR
                self.active_tasks[task_id].error_message = str(e)
            
            raise Exception(f"Manifest generation failed: {str(e)}")
    
    async def _generate_recording_manifest(self,
                                          session_id: str,
                                          owner_address: str,
                                          session_data_path: Optional[Path],
                                          chunk_size: int) -> SessionManifest:
        """Generate recording session manifest"""
        try:
            # Generate manifest ID
            manifest_id = f"{session_id}_recording_manifest"
            
            # Create session metadata
            session_metadata = SessionMetadata(
                session_id=session_id,
                owner_address=owner_address,
                session_type="recording",
                started_at=datetime.now(timezone.utc),
                compression_algorithm="zstd",
                encryption_algorithm="XChaCha20-Poly1305",
                blockchain_network="tron",
                metadata={
                    "recording_format": "mp4",
                    "video_codec": "h264_v4l2m2m",
                    "audio_codec": "opus",
                    "resolution": "1920x1080",
                    "fps": 30
                }
            )
            
            # Process session data if provided
            chunks = []
            if session_data_path and session_data_path.exists():
                chunks = await self._chunk_file(session_data_path, chunk_size)
                session_metadata.total_size = sum(chunk.size for chunk in chunks)
                session_metadata.chunk_count = len(chunks)
                session_metadata.ended_at = datetime.now(timezone.utc)
                session_metadata.duration_seconds = int(
                    (session_metadata.ended_at - session_metadata.started_at).total_seconds()
                )
            
            # Generate Merkle root
            checksums = [chunk.checksum for chunk in chunks]
            merkle_root = await self._generate_merkle_root(checksums)
            
            # Generate total checksum
            total_checksum = await self._generate_total_checksum(checksums)
            
            # Create manifest
            manifest = SessionManifest(
                manifest_id=manifest_id,
                manifest_version="1.0",
                manifest_type=ManifestType.SESSION_RECORDING,
                session_metadata=session_metadata,
                chunks=chunks,
                merkle_root=merkle_root,
                total_checksum=total_checksum,
                generated_at=datetime.now(timezone.utc),
                generated_by="lucid_session_manifest_generator",
                metadata={
                    "generation_time": time.time(),
                    "chunk_size": chunk_size,
                    "hardware_acceleration": True
                }
            )
            
            return manifest
            
        except Exception as e:
            logger.error(f"Recording manifest generation failed: {e}")
            raise
    
    async def _generate_data_manifest(self,
                                     session_id: str,
                                     owner_address: str,
                                     session_data_path: Optional[Path],
                                     chunk_size: int) -> SessionManifest:
        """Generate data session manifest"""
        try:
            # Generate manifest ID
            manifest_id = f"{session_id}_data_manifest"
            
            # Create session metadata
            session_metadata = SessionMetadata(
                session_id=session_id,
                owner_address=owner_address,
                session_type="data",
                started_at=datetime.now(timezone.utc),
                compression_algorithm="zstd",
                encryption_algorithm="XChaCha20-Poly1305",
                blockchain_network="tron",
                metadata={
                    "data_type": "session_data",
                    "compression_level": 3,
                    "encryption_mode": "per_chunk"
                }
            )
            
            # Process session data if provided
            chunks = []
            if session_data_path and session_data_path.exists():
                chunks = await self._chunk_file(session_data_path, chunk_size)
                session_metadata.total_size = sum(chunk.size for chunk in chunks)
                session_metadata.chunk_count = len(chunks)
                session_metadata.ended_at = datetime.now(timezone.utc)
                session_metadata.duration_seconds = int(
                    (session_metadata.ended_at - session_metadata.started_at).total_seconds()
                )
            
            # Generate Merkle root
            checksums = [chunk.checksum for chunk in chunks]
            merkle_root = await self._generate_merkle_root(checksums)
            
            # Generate total checksum
            total_checksum = await self._generate_total_checksum(checksums)
            
            # Create manifest
            manifest = SessionManifest(
                manifest_id=manifest_id,
                manifest_version="1.0",
                manifest_type=ManifestType.SESSION_DATA,
                session_metadata=session_metadata,
                chunks=chunks,
                merkle_root=merkle_root,
                total_checksum=total_checksum,
                generated_at=datetime.now(timezone.utc),
                generated_by="lucid_session_manifest_generator",
                metadata={
                    "generation_time": time.time(),
                    "chunk_size": chunk_size,
                    "data_processing": "streaming"
                }
            )
            
            return manifest
            
        except Exception as e:
            logger.error(f"Data manifest generation failed: {e}")
            raise
    
    async def _generate_compression_manifest(self,
                                            session_id: str,
                                            owner_address: str,
                                            session_data_path: Optional[Path],
                                            chunk_size: int) -> SessionManifest:
        """Generate compression session manifest"""
        try:
            # Generate manifest ID
            manifest_id = f"{session_id}_compression_manifest"
            
            # Create session metadata
            session_metadata = SessionMetadata(
                session_id=session_id,
                owner_address=owner_address,
                session_type="compression",
                started_at=datetime.now(timezone.utc),
                compression_algorithm="zstd",
                encryption_algorithm="XChaCha20-Poly1305",
                blockchain_network="tron",
                metadata={
                    "compression_type": "session_compression",
                    "compression_level": 3,
                    "compression_ratio": 0.0
                }
            )
            
            # Process session data if provided
            chunks = []
            if session_data_path and session_data_path.exists():
                chunks = await self._chunk_file(session_data_path, chunk_size)
                session_metadata.total_size = sum(chunk.size for chunk in chunks)
                session_metadata.chunk_count = len(chunks)
                session_metadata.ended_at = datetime.now(timezone.utc)
                session_metadata.duration_seconds = int(
                    (session_metadata.ended_at - session_metadata.started_at).total_seconds()
                )
                
                # Calculate compression ratio
                if chunks:
                    total_original = sum(chunk.size for chunk in chunks)
                    total_compressed = sum(
                        chunk.size * (chunk.compression_ratio or 1.0) for chunk in chunks
                    )
                    if total_original > 0:
                        session_metadata.metadata["compression_ratio"] = total_compressed / total_original
            
            # Generate Merkle root
            checksums = [chunk.checksum for chunk in chunks]
            merkle_root = await self._generate_merkle_root(checksums)
            
            # Generate total checksum
            total_checksum = await self._generate_total_checksum(checksums)
            
            # Create manifest
            manifest = SessionManifest(
                manifest_id=manifest_id,
                manifest_version="1.0",
                manifest_type=ManifestType.SESSION_COMPRESSION,
                session_metadata=session_metadata,
                chunks=chunks,
                merkle_root=merkle_root,
                total_checksum=total_checksum,
                generated_at=datetime.now(timezone.utc),
                generated_by="lucid_session_manifest_generator",
                metadata={
                    "generation_time": time.time(),
                    "chunk_size": chunk_size,
                    "compression_engine": "zstd"
                }
            )
            
            return manifest
            
        except Exception as e:
            logger.error(f"Compression manifest generation failed: {e}")
            raise
    
    async def _generate_encryption_manifest(self,
                                           session_id: str,
                                           owner_address: str,
                                           session_data_path: Optional[Path],
                                           chunk_size: int) -> SessionManifest:
        """Generate encryption session manifest"""
        try:
            # Generate manifest ID
            manifest_id = f"{session_id}_encryption_manifest"
            
            # Create session metadata
            session_metadata = SessionMetadata(
                session_id=session_id,
                owner_address=owner_address,
                session_type="encryption",
                started_at=datetime.now(timezone.utc),
                compression_algorithm="zstd",
                encryption_algorithm="XChaCha20-Poly1305",
                blockchain_network="tron",
                metadata={
                    "encryption_type": "per_chunk_encryption",
                    "key_derivation": "HKDF-BLAKE2b",
                    "nonce_size": 24,
                    "tag_size": 16
                }
            )
            
            # Process session data if provided
            chunks = []
            if session_data_path and session_data_path.exists():
                chunks = await self._chunk_file(session_data_path, chunk_size)
                session_metadata.total_size = sum(chunk.size for chunk in chunks)
                session_metadata.chunk_count = len(chunks)
                session_metadata.ended_at = datetime.now(timezone.utc)
                session_metadata.duration_seconds = int(
                    (session_metadata.ended_at - session_metadata.started_at).total_seconds()
                )
            
            # Generate Merkle root
            checksums = [chunk.checksum for chunk in chunks]
            merkle_root = await self._generate_merkle_root(checksums)
            
            # Generate total checksum
            total_checksum = await self._generate_total_checksum(checksums)
            
            # Create manifest
            manifest = SessionManifest(
                manifest_id=manifest_id,
                manifest_version="1.0",
                manifest_type=ManifestType.SESSION_ENCRYPTION,
                session_metadata=session_metadata,
                chunks=chunks,
                merkle_root=merkle_root,
                total_checksum=total_checksum,
                generated_at=datetime.now(timezone.utc),
                generated_by="lucid_session_manifest_generator",
                metadata={
                    "generation_time": time.time(),
                    "chunk_size": chunk_size,
                    "encryption_engine": "XChaCha20-Poly1305"
                }
            )
            
            return manifest
            
        except Exception as e:
            logger.error(f"Encryption manifest generation failed: {e}")
            raise
    
    async def _generate_blockchain_manifest(self,
                                           session_id: str,
                                           owner_address: str,
                                           session_data_path: Optional[Path],
                                           chunk_size: int) -> SessionManifest:
        """Generate blockchain session manifest"""
        try:
            # Generate manifest ID
            manifest_id = f"{session_id}_blockchain_manifest"
            
            # Create session metadata
            session_metadata = SessionMetadata(
                session_id=session_id,
                owner_address=owner_address,
                session_type="blockchain",
                started_at=datetime.now(timezone.utc),
                compression_algorithm="zstd",
                encryption_algorithm="XChaCha20-Poly1305",
                blockchain_network="tron",
                metadata={
                    "blockchain_type": "session_anchoring",
                    "network": "tron",
                    "contract_address": "TContractAddress",
                    "gas_limit": 1000000
                }
            )
            
            # Process session data if provided
            chunks = []
            if session_data_path and session_data_path.exists():
                chunks = await self._chunk_file(session_data_path, chunk_size)
                session_metadata.total_size = sum(chunk.size for chunk in chunks)
                session_metadata.chunk_count = len(chunks)
                session_metadata.ended_at = datetime.now(timezone.utc)
                session_metadata.duration_seconds = int(
                    (session_metadata.ended_at - session_metadata.started_at).total_seconds()
                )
            
            # Generate Merkle root
            checksums = [chunk.checksum for chunk in chunks]
            merkle_root = await self._generate_merkle_root(checksums)
            
            # Generate total checksum
            total_checksum = await self._generate_total_checksum(checksums)
            
            # Create manifest
            manifest = SessionManifest(
                manifest_id=manifest_id,
                manifest_version="1.0",
                manifest_type=ManifestType.SESSION_BLOCKCHAIN,
                session_metadata=session_metadata,
                chunks=chunks,
                merkle_root=merkle_root,
                total_checksum=total_checksum,
                generated_at=datetime.now(timezone.utc),
                generated_by="lucid_session_manifest_generator",
                metadata={
                    "generation_time": time.time(),
                    "chunk_size": chunk_size,
                    "blockchain_engine": "tron"
                }
            )
            
            return manifest
            
        except Exception as e:
            logger.error(f"Blockchain manifest generation failed: {e}")
            raise
    
    async def _chunk_file(self, file_path: Path, chunk_size: int) -> List[ChunkInfo]:
        """Chunk file into pieces"""
        chunks = []
        
        try:
            with open(file_path, 'rb') as f:
                chunk_index = 0
                while True:
                    chunk_data = f.read(chunk_size)
                    if not chunk_data:
                        break
                    
                    # Generate chunk ID
                    chunk_id = f"{file_path.stem}_chunk_{chunk_index:06d}"
                    
                    # Calculate checksum
                    checksum = blake3.blake3(chunk_data).hexdigest()
                    
                    # Create chunk info
                    chunk_info = ChunkInfo(
                        chunk_id=chunk_id,
                        chunk_index=chunk_index,
                        size=len(chunk_data),
                        checksum=checksum,
                        metadata={
                            "file_path": str(file_path),
                            "chunk_offset": chunk_index * chunk_size
                        }
                    )
                    
                    chunks.append(chunk_info)
                    chunk_index += 1
            
            logger.debug(f"Chunked file {file_path} into {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"File chunking failed: {e}")
            raise
    
    async def _generate_merkle_root(self, checksums: List[str]) -> str:
        """Generate Merkle root from checksums"""
        try:
            if not checksums:
                return "0" * 64
            
            # Convert checksums to bytes
            hash_bytes = [bytes.fromhex(checksum) for checksum in checksums]
            
            # Build Merkle tree
            while len(hash_bytes) > 1:
                next_level = []
                for i in range(0, len(hash_bytes), 2):
                    left = hash_bytes[i]
                    right = hash_bytes[i + 1] if i + 1 < len(hash_bytes) else left
                    combined = left + right
                    parent_hash = blake3.blake3(combined).digest()
                    next_level.append(parent_hash)
                hash_bytes = next_level
            
            return hash_bytes[0].hex()
            
        except Exception as e:
            logger.error(f"Merkle root generation failed: {e}")
            raise
    
    async def _generate_total_checksum(self, checksums: List[str]) -> str:
        """Generate total checksum from all chunk checksums"""
        try:
            if not checksums:
                return "0" * 64
            
            # Combine all checksums
            combined = "".join(checksums)
            total_checksum = blake3.blake3(combined.encode()).hexdigest()
            
            return total_checksum
            
        except Exception as e:
            logger.error(f"Total checksum generation failed: {e}")
            raise
    
    async def _sign_manifest(self, manifest: SessionManifest) -> str:
        """Sign manifest with Ed25519"""
        try:
            if not self.signing_key:
                raise Exception("Signing key not available")
            
            # Create signature data
            signature_data = {
                "manifest_id": manifest.manifest_id,
                "manifest_version": manifest.manifest_version,
                "session_id": manifest.session_metadata.session_id,
                "owner_address": manifest.session_metadata.owner_address,
                "merkle_root": manifest.merkle_root,
                "total_checksum": manifest.total_checksum,
                "generated_at": manifest.generated_at.isoformat()
            }
            
            # Serialize signature data
            signature_json = json.dumps(signature_data, sort_keys=True)
            signature_bytes = signature_json.encode()
            
            # Sign data
            signature = self.signing_key.sign(signature_bytes)
            
            return signature.hex()
            
        except Exception as e:
            logger.error(f"Manifest signing failed: {e}")
            raise
    
    async def _save_manifest(self, manifest: SessionManifest) -> None:
        """Save manifest to disk"""
        try:
            # Create manifest data
            manifest_data = {
                "manifest_id": manifest.manifest_id,
                "manifest_version": manifest.manifest_version,
                "manifest_type": manifest.manifest_type.value,
                "session_metadata": {
                    "session_id": manifest.session_metadata.session_id,
                    "owner_address": manifest.session_metadata.owner_address,
                    "session_type": manifest.session_metadata.session_type,
                    "started_at": manifest.session_metadata.started_at.isoformat(),
                    "ended_at": manifest.session_metadata.ended_at.isoformat() if manifest.session_metadata.ended_at else None,
                    "duration_seconds": manifest.session_metadata.duration_seconds,
                    "total_size": manifest.session_metadata.total_size,
                    "chunk_count": manifest.session_metadata.chunk_count,
                    "compression_algorithm": manifest.session_metadata.compression_algorithm,
                    "encryption_algorithm": manifest.session_metadata.encryption_algorithm,
                    "blockchain_network": manifest.session_metadata.blockchain_network,
                    "metadata": manifest.session_metadata.metadata
                },
                "chunks": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "chunk_index": chunk.chunk_index,
                        "size": chunk.size,
                        "checksum": chunk.checksum,
                        "compression_ratio": chunk.compression_ratio,
                        "encryption_key_id": chunk.encryption_key_id,
                        "metadata": chunk.metadata
                    }
                    for chunk in manifest.chunks
                ],
                "merkle_root": manifest.merkle_root,
                "total_checksum": manifest.total_checksum,
                "generated_at": manifest.generated_at.isoformat(),
                "generated_by": manifest.generated_by,
                "signature": manifest.signature,
                "blockchain_tx_hash": manifest.blockchain_tx_hash,
                "blockchain_block_number": manifest.blockchain_block_number,
                "metadata": manifest.metadata
            }
            
            # Save manifest file
            manifest_file = MANIFEST_PATH / f"{manifest.manifest_id}.json"
            with open(manifest_file, 'w') as f:
                json.dump(manifest_data, f, indent=2)
            
            logger.debug(f"Saved manifest to {manifest_file}")
            
        except Exception as e:
            logger.error(f"Manifest saving failed: {e}")
            raise
    
    async def verify_manifest(self, manifest: SessionManifest) -> bool:
        """Verify manifest integrity and signature"""
        try:
            # Verify signature
            if not self._verify_signature(manifest):
                logger.error("Manifest signature verification failed")
                return False
            
            # Verify Merkle root
            if not await self._verify_merkle_root(manifest):
                logger.error("Manifest Merkle root verification failed")
                return False
            
            # Verify total checksum
            if not await self._verify_total_checksum(manifest):
                logger.error("Manifest total checksum verification failed")
                return False
            
            logger.info(f"Manifest verification successful: {manifest.manifest_id}")
            return True
            
        except Exception as e:
            logger.error(f"Manifest verification failed: {e}")
            return False
    
    def _verify_signature(self, manifest: SessionManifest) -> bool:
        """Verify manifest signature"""
        try:
            if not self.verification_key or not manifest.signature:
                return False
            
            # Create signature data
            signature_data = {
                "manifest_id": manifest.manifest_id,
                "manifest_version": manifest.manifest_version,
                "session_id": manifest.session_metadata.session_id,
                "owner_address": manifest.session_metadata.owner_address,
                "merkle_root": manifest.merkle_root,
                "total_checksum": manifest.total_checksum,
                "generated_at": manifest.generated_at.isoformat()
            }
            
            # Serialize signature data
            signature_json = json.dumps(signature_data, sort_keys=True)
            signature_bytes = signature_json.encode()
            
            # Verify signature
            signature = bytes.fromhex(manifest.signature)
            self.verification_key.verify(signature, signature_bytes)
            
            return True
            
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False
    
    async def _verify_merkle_root(self, manifest: SessionManifest) -> bool:
        """Verify Merkle root"""
        try:
            checksums = [chunk.checksum for chunk in manifest.chunks]
            calculated_root = await self._generate_merkle_root(checksums)
            return calculated_root == manifest.merkle_root
            
        except Exception as e:
            logger.error(f"Merkle root verification failed: {e}")
            return False
    
    async def _verify_total_checksum(self, manifest: SessionManifest) -> bool:
        """Verify total checksum"""
        try:
            checksums = [chunk.checksum for chunk in manifest.chunks]
            calculated_checksum = await self._generate_total_checksum(checksums)
            return calculated_checksum == manifest.total_checksum
            
        except Exception as e:
            logger.error(f"Total checksum verification failed: {e}")
            return False
    
    def get_manifest(self, manifest_id: str) -> Optional[SessionManifest]:
        """Get manifest by ID"""
        return self.generated_manifests.get(manifest_id)
    
    def list_manifests(self) -> Dict[str, Any]:
        """List all generated manifests"""
        return {
            "manifests": [
                {
                    "manifest_id": manifest.manifest_id,
                    "manifest_type": manifest.manifest_type.value,
                    "session_id": manifest.session_metadata.session_id,
                    "owner_address": manifest.session_metadata.owner_address,
                    "generated_at": manifest.generated_at.isoformat(),
                    "chunk_count": len(manifest.chunks),
                    "total_size": manifest.session_metadata.total_size
                }
                for manifest in self.generated_manifests.values()
            ]
        }


# Global manifest generator instance
session_manifest_generator = SessionManifestGenerator()