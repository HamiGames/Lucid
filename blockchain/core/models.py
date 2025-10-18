# Path: blockchain/core/models.py
"""
Lucid Blockchain Core Data Models

Defines all data structures for the blockchain architecture:
- On-System Data Chain (primary blockchain)
- Payment service integration (handled separately)
- PoOT consensus engine
- Session anchoring and chunk metadata

Based on Spec-1a, Spec-1b, and Spec-1c requirements.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Union
import uuid


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class ChainType(Enum):
    """Blockchain types in architecture"""
    ON_SYSTEM_DATA = "on_system_data_chain"  # Primary blockchain


class ConsensusState(Enum):
    """PoOT consensus states"""
    CALCULATING = "calculating"
    LEADER_SELECTED = "leader_selected"
    BLOCK_PROPOSED = "block_proposed"
    BLOCK_CONFIRMED = "block_confirmed"
    SLOT_MISSED = "slot_missed"


# Payment router types are handled by payment service cluster


class TaskProofType(Enum):
    """PoOT task proof types (Spec-1b lines 129-134)"""
    RELAY_BANDWIDTH = "relay_bandwidth"
    STORAGE_AVAILABILITY = "storage_availability"
    VALIDATION_SIGNATURE = "validation_signature"
    UPTIME_BEACON = "uptime_beacon"


class SessionStatus(Enum):
    """Session anchoring status"""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PayoutStatus(Enum):
    """Payout status (handled by payment service)"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


# =============================================================================
# SESSION AND CHUNK MODELS
# =============================================================================

@dataclass
class ChunkMetadata:
    """
    Encrypted chunk metadata for On-System Chain storage.
    
    Used by LucidChunkStore contract for chunk metadata storage.
    """
    idx: int
    local_path: str
    ciphertext_sha256: str
    size_bytes: int
    session_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        return {
            "_id": f"{self.session_id}_{self.idx:03d}",
            "session_id": self.session_id,
            "idx": self.idx,
            "local_path": self.local_path,
            "ciphertext_sha256": self.ciphertext_sha256,
            "size_bytes": self.size_bytes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ChunkMetadata:
        """Create from MongoDB document"""
        return cls(
            idx=data["idx"],
            local_path=data["local_path"],
            ciphertext_sha256=data["ciphertext_sha256"],
            size_bytes=data["size_bytes"],
            session_id=data.get("session_id", "")
        )


@dataclass
class SessionManifest:
    """
    Session manifest for On-System Chain anchoring.
    
    Contains session metadata and chunk information for anchoring
    to LucidAnchors contract.
    """
    session_id: str
    owner_address: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    manifest_hash: str = ""
    merkle_root: str = ""
    chunk_count: int = 0
    chunks: List[ChunkMetadata] = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate manifest hash and merkle root after initialization"""
        if not self.manifest_hash:
            self.manifest_hash = self._calculate_manifest_hash()
        if not self.merkle_root:
            self.merkle_root = self._calculate_merkle_root()
        if self.chunk_count == 0 and self.chunks:
            self.chunk_count = len(self.chunks)
    
    def _calculate_manifest_hash(self) -> str:
        """Calculate SHA256 hash of session manifest"""
        manifest_data = {
            "session_id": self.session_id,
            "owner_address": self.owner_address,
            "started_at": self.started_at.isoformat(),
            "chunk_count": self.chunk_count
        }
        
        manifest_str = str(sorted(manifest_data.items()))
        return "0x" + hashlib.sha256(manifest_str.encode()).hexdigest()
    
    def _calculate_merkle_root(self) -> str:
        """Calculate Merkle root of chunks"""
        if not self.chunks:
            return "0x" + "0" * 64
        
        # Sort chunks by index for consistent ordering
        sorted_chunks = sorted(self.chunks, key=lambda x: x.idx)
        
        # Create leaf hashes
        leaf_hashes = []
        for chunk in sorted_chunks:
            leaf_data = f"{chunk.idx}{chunk.ciphertext_sha256}{chunk.size_bytes}"
            leaf_hash = hashlib.sha256(leaf_data.encode()).hexdigest()
            leaf_hashes.append(leaf_hash)
        
        # Build Merkle tree
        while len(leaf_hashes) > 1:
            next_level = []
            for i in range(0, len(leaf_hashes), 2):
                left = leaf_hashes[i]
                right = leaf_hashes[i + 1] if i + 1 < len(leaf_hashes) else left
                combined = hashlib.sha256((left + right).encode()).hexdigest()
                next_level.append(combined)
            leaf_hashes = next_level
        
        return "0x" + leaf_hashes[0]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        return {
            "_id": self.session_id,
            "owner_addr": self.owner_address,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "manifest_hash": self.manifest_hash,
            "merkle_root": self.merkle_root,
            "chunk_count": self.chunk_count,
            "anchor_txid": None,  # Set when anchored
            "block_number": None,
            "gas_used": 0,
            "status": SessionStatus.PENDING.value
        }


# =============================================================================
# ON-SYSTEM CHAIN MODELS
# =============================================================================

@dataclass
class SessionAnchor:
    """
    On-System Chain session anchor (Spec-1b lines 56-59).
    
    REBUILT: Focused on On-System Chain anchoring.
    Uses LucidAnchors contract for session manifest anchoring.
    """
    session_id: str
    manifest_hash: str
    merkle_root: str
    started_at: int
    owner_address: str
    chunk_count: int
    block_number: Optional[int] = None
    txid: Optional[str] = None
    gas_used: int = 0
    status: str = "pending"  # pending, confirmed, failed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        return {
            "_id": self.session_id,
            "owner_addr": self.owner_address,
            "started_at": self.started_at,
            "ended_at": None,
            "manifest_hash": self.manifest_hash,
            "merkle_root": self.merkle_root,
            "chunk_count": self.chunk_count,
            "anchor_txid": self.txid,  # On-System Chain txid
            "block_number": self.block_number,
            "gas_used": self.gas_used,
            "status": self.status
        }


@dataclass
class AnchorTransaction:
    """On-System Chain anchor transaction details"""
    txid: str
    block_number: int
    gas_used: int
    gas_price: int
    timestamp: datetime
    status: str  # pending, confirmed, failed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        return {
            "txid": self.txid,
            "block_number": self.block_number,
            "gas_used": self.gas_used,
            "gas_price": self.gas_price,
            "timestamp": self.timestamp,
            "status": self.status
        }


@dataclass
class ChunkStoreEntry:
    """LucidChunkStore contract entry for chunk metadata"""
    session_id: str
    chunk_idx: int
    ciphertext_hash: str
    size_bytes: int
    txid: Optional[str] = None
    block_number: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        return {
            "_id": f"{self.session_id}_{self.chunk_idx:03d}",
            "session_id": self.session_id,
            "chunk_idx": self.chunk_idx,
            "ciphertext_hash": self.ciphertext_hash,
            "size_bytes": self.size_bytes,
            "txid": self.txid,
            "block_number": self.block_number
        }


# =============================================================================
# POOT CONSENSUS MODELS
# =============================================================================

@dataclass
class TaskProof:
    """
    PoOT work credits proof submission (Spec-1b lines 129-134).
    
    Used for relay bandwidth, storage availability, validation signatures,
    and uptime beacons in the PoOT consensus mechanism.
    """
    node_id: str
    pool_id: Optional[str]
    slot: int
    type: TaskProofType
    value: Dict[str, Any]
    sig: str
    ts: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        return {
            "_id": f"{self.node_id}_{self.slot}_{self.type.value}",
            "nodeId": self.node_id,
            "poolId": self.pool_id,
            "slot": self.slot,
            "type": self.type.value,
            "value": self.value,
            "sig": self.sig,
            "ts": self.ts
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskProof:
        """Create from MongoDB document"""
        return cls(
            node_id=data["nodeId"],
            pool_id=data.get("poolId"),
            slot=data["slot"],
            type=TaskProofType(data["type"]),
            value=data["value"],
            sig=data["sig"],
            ts=data["ts"]
        )


@dataclass
class WorkCredit:
    """PoOT work credits calculation result"""
    entity_id: str  # node_id or pool_id
    credits: int
    live_score: float
    rank: int
    epoch: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        return {
            "_id": f"{self.epoch}_{self.entity_id}",
            "epoch": self.epoch,
            "entityId": self.entity_id,
            "credits": self.credits,
            "liveScore": self.live_score,
            "rank": self.rank
        }


@dataclass
class WorkCreditsTally:
    """PoOT work credits tally per epoch"""
    epoch: int
    entity_id: str  # node_id or pool_id
    credits_total: int
    relay_bandwidth: int
    storage_proofs: int
    validation_signatures: int
    uptime_score: float
    live_score: float
    rank: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        return {
            "_id": f"{self.epoch}_{self.entity_id}",
            "epoch": self.epoch,
            "entityId": self.entity_id,
            "credits": self.credits_total,
            "liveScore": self.live_score,
            "rank": self.rank
        }


@dataclass
class LeaderSchedule:
    """Block leader schedule per slot (Spec-1b lines 135-157)"""
    slot: int
    primary: str  # entity_id
    fallbacks: List[str]  # fallback entity_ids
    winner: Optional[str] = None
    reason: str = ""
    deadline: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        return {
            "_id": self.slot,
            "slot": self.slot,
            "primary": self.primary,
            "fallbacks": self.fallbacks,
            "result": {"winner": self.winner, "reason": self.reason}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LeaderSchedule:
        """Create from MongoDB document"""
        result = data.get("result", {})
        return cls(
            slot=data["slot"],
            primary=data["primary"],
            fallbacks=data["fallbacks"],
            winner=result.get("winner"),
            reason=result.get("reason", "")
        )


# =============================================================================
# PAYOUT MODELS
# =============================================================================

# Payout models are handled by payment service cluster


# =============================================================================
# NETWORK MODELS
# =============================================================================

@dataclass
class TransactionStatus:
    """Generic transaction status"""
    txid: str
    status: str  # pending, confirmed, failed, unknown
    block_number: Optional[int] = None
    confirmations: int = 0
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        return {
            "txid": self.txid,
            "status": self.status,
            "block_number": self.block_number,
            "confirmations": self.confirmations,
            "timestamp": self.timestamp
        }


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def generate_session_id() -> str:
    """Generate a new session ID"""
    return str(uuid.uuid4())


def validate_ethereum_address(address: str) -> bool:
    """Validate Ethereum address format"""
    if not address.startswith("0x"):
        return False
    if len(address) != 42:
        return False
    try:
        int(address[2:], 16)
        return True
    except ValueError:
        return False


# Address validation is handled by payment service cluster


def calculate_work_credits_formula(storage_sessions: int, bandwidth_mb: int, base_mb_per_session: int = 5) -> int:
    """
    Calculate work credits using Spec-1b formula.
    
    W_t = max(S_t, ceil(B_t / BASE_MB_PER_SESSION))
    where:
    - S_t = storage sessions
    - B_t = bandwidth in MB
    - BASE_MB_PER_SESSION = 5MB (default)
    """
    import math
    bandwidth_credits = math.ceil(bandwidth_mb / base_mb_per_session)
    return max(storage_sessions, bandwidth_credits)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "ChainType", "ConsensusState", "TaskProofType",
    "SessionStatus", "PayoutStatus",
    
    # Session and Chunk Models
    "ChunkMetadata", "SessionManifest", "SessionAnchor",
    
    # On-System Chain Models
    "AnchorTransaction", "ChunkStoreEntry",
    
    # PoOT Consensus Models
    "TaskProof", "WorkCredit", "WorkCreditsTally", "LeaderSchedule",
    
    # Payment models are handled by payment service cluster
    
    # Network Models
    "TransactionStatus",
    
    # Utility Functions
    "generate_session_id", "validate_ethereum_address",
    "calculate_work_credits_formula"
]
