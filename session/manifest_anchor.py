# Path: session/manifest_anchor.py

from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import hashlib
import uuid
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


@dataclass
class SessionManifest:
    """Session manifest for blockchain anchoring."""
    session_id: str
    merkle_root: str
    chunk_count: int
    total_size: int
    participant_pubkeys: List[str] = field(default_factory=list)
    codec_info: Dict[str, Any] = field(default_factory=dict)
    recorder_version: str = "1.0.0"
    device_fingerprint: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    anchored_at: Optional[datetime] = None
    anchor_txid: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "merkle_root": self.merkle_root,
            "chunk_count": self.chunk_count,
            "total_size": self.total_size,
            "participant_pubkeys": self.participant_pubkeys,
            "codec_info": self.codec_info,
            "recorder_version": self.recorder_version,
            "device_fingerprint": self.device_fingerprint,
            "created_at": self.created_at.isoformat(),
            "anchored_at": self.anchored_at.isoformat() if self.anchored_at else None,
            "anchor_txid": self.anchor_txid
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SessionManifest:
        return cls(
            session_id=data["session_id"],
            merkle_root=data["merkle_root"],
            chunk_count=data["chunk_count"],
            total_size=data["total_size"],
            participant_pubkeys=data.get("participant_pubkeys", []),
            codec_info=data.get("codec_info", {}),
            recorder_version=data.get("recorder_version", "1.0.0"),
            device_fingerprint=data.get("device_fingerprint", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            anchored_at=datetime.fromisoformat(data["anchored_at"]) if data.get("anchored_at") else None,
            anchor_txid=data.get("anchor_txid")
        )
        
    def get_manifest_hash(self) -> str:
        """Calculate hash of manifest for anchoring."""
        manifest_data = {
            "session_id": self.session_id,
            "merkle_root": self.merkle_root,
            "chunk_count": self.chunk_count,
            "total_size": self.total_size,
            "participant_pubkeys": sorted(self.participant_pubkeys),
            "created_at": self.created_at.isoformat()
        }
        data_str = json.dumps(manifest_data, sort_keys=True)
        return hashlib.blake3(data_str.encode()).hexdigest()


class ManifestAnchor:
    """
    Manages session manifest anchoring to on-system data chain.
    Handles merkle tree calculation and blockchain anchoring.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        
    def calculate_merkle_root(self, chunk_hashes: List[str]) -> str:
        """Calculate Merkle root from chunk hashes using BLAKE3."""
        if not chunk_hashes:
            return hashlib.blake3(b"").hexdigest()
            
        # Build Merkle tree bottom-up
        current_level = [h.encode() if isinstance(h, str) else h for h in chunk_hashes]
        
        while len(current_level) > 1:
            next_level = []
            
            # Process pairs
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                
                # Combine and hash
                combined = left + right
                next_hash = hashlib.blake3(combined).digest()
                next_level.append(next_hash)
                
            current_level = next_level
            
        return current_level[0].hex() if current_level else hashlib.blake3(b"").hexdigest()
        
    async def create_manifest(
        self,
        session_id: str,
        chunk_hashes: List[str],
        total_size: int,
        participant_pubkeys: Optional[List[str]] = None,
        additional_metadata: Optional[Dict] = None
    ) -> SessionManifest:
        """Create session manifest with merkle root."""
        try:
            merkle_root = self.calculate_merkle_root(chunk_hashes)
            
            manifest = SessionManifest(
                session_id=session_id,
                merkle_root=merkle_root,
                chunk_count=len(chunk_hashes),
                total_size=total_size,
                participant_pubkeys=participant_pubkeys or [],
                codec_info=additional_metadata or {}
            )
            
            # Store manifest in database
            await self.db["manifests"].insert_one(manifest.to_dict())
            
            logger.info(f"Created manifest for session {session_id}")
            return manifest
            
        except Exception as e:
            logger.error(f"Failed to create manifest: {e}")
            raise
            
    async def anchor_manifest(
        self,
        manifest: SessionManifest,
        blockchain_service: Any  # Would be actual blockchain service
    ) -> str:
        """Anchor manifest to on-system data chain."""
        try:
            # In production, this would interact with the actual blockchain
            # For now, simulate anchoring with a transaction ID
            manifest_hash = manifest.get_manifest_hash()
            
            # Simulate blockchain transaction
            txid = f"anchor_{manifest.session_id}_{manifest_hash[:16]}"
            
            # Update manifest with anchor info
            manifest.anchored_at = datetime.now(timezone.utc)
            manifest.anchor_txid = txid
            
            # Update in database
            await self.db["manifests"].replace_one(
                {"session_id": manifest.session_id},
                manifest.to_dict()
            )
            
            logger.info(f"Anchored manifest for session {manifest.session_id}: {txid}")
            return txid
            
        except Exception as e:
            logger.error(f"Failed to anchor manifest: {e}")
            raise
            
    async def get_manifest(self, session_id: str) -> Optional[SessionManifest]:
        """Get manifest for session."""
        try:
            doc = await self.db["manifests"].find_one({"session_id": session_id})
            if doc:
                return SessionManifest.from_dict(doc)
        except Exception as e:
            logger.error(f"Failed to get manifest: {e}")
        return None
        
    async def verify_manifest_integrity(
        self,
        manifest: SessionManifest,
        chunk_hashes: List[str]
    ) -> bool:
        """Verify manifest integrity against chunk hashes."""
        try:
            expected_root = self.calculate_merkle_root(chunk_hashes)
            return expected_root == manifest.merkle_root
        except Exception as e:
            logger.error(f"Failed to verify manifest integrity: {e}")
            return False
