# Blockchain Core Cluster - Data Models

## Overview

This document defines the data models, validation rules, and MongoDB collections used by the Blockchain Core cluster (`lucid_blocks`). All models are specifically designed for blockchain operations and are **completely isolated** from TRON payment systems.

## Core Data Models

### Block Model

**Collection**: `blocks`

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid
import hashlib

class BlockStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    ORPHANED = "orphaned"
    INVALID = "invalid"

class BlockModel(BaseModel):
    """Block model for lucid_blocks blockchain"""
    block_id: str = Field(..., description="Unique block identifier")
    height: int = Field(..., ge=0, description="Block height in the chain")
    hash: str = Field(..., max_length=64, regex="^[a-fA-F0-9]{64}$", description="Block hash")
    previous_hash: str = Field(..., max_length=64, regex="^[a-fA-F0-9]{64}$", description="Previous block hash")
    merkle_root: str = Field(..., max_length=64, regex="^[a-fA-F0-9]{64}$", description="Merkle root of transactions")
    timestamp: datetime = Field(..., description="Block creation timestamp")
    nonce: int = Field(..., ge=0, description="Proof of work nonce")
    difficulty: float = Field(..., gt=0, description="Block difficulty")
    block_size_bytes: int = Field(..., ge=0, description="Block size in bytes")
    transaction_count: int = Field(..., ge=0, description="Number of transactions in block")
    validator: str = Field(..., max_length=100, description="Block validator node ID")
    signature: str = Field(..., max_length=256, description="Block signature")
    status: BlockStatus = Field(default=BlockStatus.PENDING, description="Block status")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Transaction references
    transaction_ids: List[str] = Field(default_factory=list, description="List of transaction IDs")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Block metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator('hash')
    def validate_block_hash(cls, v):
        """Validate block hash format"""
        if len(v) != 64:
            raise ValueError('Block hash must be 64 characters long')
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Block hash must contain only hexadecimal characters')
        return v.lower()
    
    @validator('previous_hash')
    def validate_previous_hash(cls, v):
        """Validate previous block hash format"""
        if len(v) != 64:
            raise ValueError('Previous hash must be 64 characters long')
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Previous hash must contain only hexadecimal characters')
        return v.lower()
    
    @validator('merkle_root')
    def validate_merkle_root(cls, v):
        """Validate Merkle root format"""
        if len(v) != 64:
            raise ValueError('Merkle root must be 64 characters long')
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Merkle root must contain only hexadecimal characters')
        return v.lower()
    
    @validator('block_size_bytes')
    def validate_block_size(cls, v):
        """Validate block size limits"""
        max_size = 1024 * 1024  # 1MB limit
        if v > max_size:
            raise ValueError(f'Block size {v} exceeds limit {max_size}')
        return v
    
    @validator('transaction_count')
    def validate_transaction_count(cls, v):
        """Validate transaction count limits"""
        max_transactions = 1000
        if v > max_transactions:
            raise ValueError(f'Transaction count {v} exceeds limit {max_transactions}')
        return v

# MongoDB Indexes for blocks
block_indexes = [
    {"block_id": 1},  # Unique index
    {"hash": 1},  # Unique index
    {"height": 1},  # Unique index
    {"previous_hash": 1},
    {"timestamp": 1},
    {"validator": 1},
    {"status": 1},
    {"created_at": 1},
    {"height": 1, "status": 1},  # Compound index
    {"timestamp": 1, "status": 1},  # Compound index
]
```

### Transaction Model

**Collection**: `transactions`

```python
class TransactionType(str, Enum):
    SESSION_ANCHOR = "session_anchor"
    DATA_STORAGE = "data_storage"
    CONSENSUS_VOTE = "consensus_vote"
    SYSTEM = "system"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    DROPPED = "dropped"

class TransactionModel(BaseModel):
    """Transaction model for lucid_blocks blockchain"""
    tx_id: str = Field(..., description="Unique transaction identifier")
    type: TransactionType = Field(..., description="Transaction type")
    status: TransactionStatus = Field(default=TransactionStatus.PENDING, description="Transaction status")
    
    # Transaction data
    data: Dict[str, Any] = Field(..., description="Transaction payload data")
    signature: str = Field(..., max_length=256, description="Transaction signature")
    
    # Block reference
    block_id: Optional[str] = Field(None, description="Block containing this transaction")
    block_height: Optional[int] = Field(None, ge=0, description="Block height")
    transaction_index: Optional[int] = Field(None, ge=0, description="Transaction index in block")
    
    # Timing
    submitted_at: datetime = Field(default_factory=datetime.utcnow, description="Transaction submission time")
    confirmed_at: Optional[datetime] = Field(None, description="Transaction confirmation time")
    failed_at: Optional[datetime] = Field(None, description="Transaction failure time")
    
    # Fees and validation
    fee: float = Field(default=0.0, ge=0.0, description="Transaction fee")
    gas_limit: Optional[int] = Field(None, ge=0, description="Gas limit for transaction")
    gas_used: Optional[int] = Field(None, ge=0, description="Gas used by transaction")
    
    # Size and validation
    size_bytes: int = Field(..., ge=0, description="Transaction size in bytes")
    validation_errors: List[str] = Field(default_factory=list, description="Validation error messages")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Transaction metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator('size_bytes')
    def validate_transaction_size(cls, v):
        """Validate transaction size limits"""
        max_size = 1024 * 1024  # 1MB limit
        if v > max_size:
            raise ValueError(f'Transaction size {v} exceeds limit {max_size}')
        return v
    
    @validator('data')
    def validate_transaction_data(cls, v):
        """Validate transaction data structure"""
        if not isinstance(v, dict):
            raise ValueError('Transaction data must be a dictionary')
        
        # Check for required fields based on transaction type
        if 'type' in v:
            tx_type = v['type']
            if tx_type == TransactionType.SESSION_ANCHOR:
                required_fields = ['session_id', 'manifest_data', 'merkle_root']
                for field in required_fields:
                    if field not in v:
                        raise ValueError(f'Session anchor transaction requires {field}')
        
        return v

# MongoDB Indexes for transactions
transaction_indexes = [
    {"tx_id": 1},  # Unique index
    {"type": 1},
    {"status": 1},
    {"block_id": 1},
    {"block_height": 1},
    {"submitted_at": 1},
    {"confirmed_at": 1},
    {"validator": 1},
    {"type": 1, "status": 1},  # Compound index
    {"block_height": 1, "transaction_index": 1},  # Compound index
    {"submitted_at": 1, "status": 1},  # Compound index
]
```

### Session Anchoring Model

**Collection**: `session_anchorings`

```python
class AnchoringStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    EXPIRED = "expired"

class SessionAnchoringModel(BaseModel):
    """Session anchoring model for lucid_blocks blockchain"""
    anchoring_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique anchoring identifier")
    session_id: str = Field(..., description="Session ID being anchored")
    status: AnchoringStatus = Field(default=AnchoringStatus.PENDING, description="Anchoring status")
    
    # Manifest data
    manifest_data: Dict[str, Any] = Field(..., description="Session manifest data")
    merkle_root: str = Field(..., max_length=64, regex="^[a-fA-F0-9]{64}$", description="Merkle root hash")
    chunk_count: int = Field(..., ge=0, description="Number of chunks in session")
    total_size: int = Field(..., ge=0, description="Total session size in bytes")
    
    # Blockchain reference
    transaction_id: Optional[str] = Field(None, description="Blockchain transaction ID")
    block_id: Optional[str] = Field(None, description="Block containing anchoring transaction")
    block_height: Optional[int] = Field(None, ge=0, description="Block height")
    
    # User and validation
    user_id: str = Field(..., description="User who initiated anchoring")
    user_signature: str = Field(..., max_length=256, description="User signature")
    
    # Timing
    submitted_at: datetime = Field(default_factory=datetime.utcnow, description="Anchoring submission time")
    confirmed_at: Optional[datetime] = Field(None, description="Anchoring confirmation time")
    failed_at: Optional[datetime] = Field(None, description="Anchoring failure time")
    expires_at: Optional[datetime] = Field(None, description="Anchoring expiration time")
    
    # Validation results
    validation_results: Dict[str, Any] = Field(default_factory=dict, description="Validation results")
    error_messages: List[str] = Field(default_factory=list, description="Error messages")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Anchoring metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator('merkle_root')
    def validate_merkle_root(cls, v):
        """Validate Merkle root format"""
        if len(v) != 64:
            raise ValueError('Merkle root must be 64 characters long')
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Merkle root must contain only hexadecimal characters')
        return v.lower()
    
    @validator('total_size')
    def validate_session_size(cls, v):
        """Validate session size limits"""
        max_size = 100 * 1024 * 1024 * 1024  # 100GB limit
        if v > max_size:
            raise ValueError(f'Session size {v} exceeds limit {max_size}')
        return v
    
    @validator('chunk_count')
    def validate_chunk_count(cls, v):
        """Validate chunk count limits"""
        max_chunks = 1000000  # 1M chunks limit
        if v > max_chunks:
            raise ValueError(f'Chunk count {v} exceeds limit {max_chunks}')
        return v

# MongoDB Indexes for session anchorings
session_anchoring_indexes = [
    {"anchoring_id": 1},  # Unique index
    {"session_id": 1},  # Unique index
    {"status": 1},
    {"user_id": 1},
    {"submitted_at": 1},
    {"confirmed_at": 1},
    {"transaction_id": 1},  # Sparse index
    {"block_height": 1},  # Sparse index
    {"user_id": 1, "status": 1},  # Compound index
    {"submitted_at": 1, "status": 1},  # Compound index
]
```

### Consensus Model

**Collection**: `consensus_events`

```python
class ConsensusEventType(str, Enum):
    BLOCK_VALIDATION = "block_validation"
    PROPOSAL_VOTE = "proposal_vote"
    PARTICIPANT_SELECTION = "participant_selection"
    NETWORK_UPDATE = "network_update"

class ConsensusResult(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"
    FAILED = "failed"

class ConsensusEventModel(BaseModel):
    """Consensus event model for lucid_blocks blockchain"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique event identifier")
    event_type: ConsensusEventType = Field(..., description="Type of consensus event")
    target_id: str = Field(..., description="ID of the target being voted on")
    
    # Consensus details
    round_number: int = Field(..., ge=0, description="Consensus round number")
    participants: List[str] = Field(..., min_items=1, description="List of participating node IDs")
    votes: Dict[str, str] = Field(default_factory=dict, description="Node votes (node_id -> vote)")
    
    # Results
    result: ConsensusResult = Field(default=ConsensusResult.PENDING, description="Consensus result")
    approval_threshold: float = Field(..., ge=0.0, le=1.0, description="Required approval threshold")
    approval_percentage: Optional[float] = Field(None, ge=0.0, le=1.0, description="Actual approval percentage")
    
    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Consensus start time")
    completed_at: Optional[datetime] = Field(None, description="Consensus completion time")
    timeout_at: Optional[datetime] = Field(None, description="Consensus timeout")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Consensus metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator('participants')
    def validate_participants(cls, v):
        """Validate consensus participants"""
        if len(v) < 3:
            raise ValueError('Consensus requires at least 3 participants')
        if len(set(v)) != len(v):
            raise ValueError('Consensus participants must be unique')
        return v
    
    @validator('votes')
    def validate_votes(cls, v, values):
        """Validate consensus votes"""
        participants = values.get('participants', [])
        valid_votes = ['approve', 'reject', 'abstain']
        
        for node_id, vote in v.items():
            if node_id not in participants:
                raise ValueError(f'Vote from non-participant node: {node_id}')
            if vote not in valid_votes:
                raise ValueError(f'Invalid vote: {vote}')
        
        return v

# MongoDB Indexes for consensus events
consensus_event_indexes = [
    {"event_id": 1},  # Unique index
    {"event_type": 1},
    {"target_id": 1},
    {"round_number": 1},
    {"result": 1},
    {"started_at": 1},
    {"completed_at": 1},
    {"round_number": 1, "event_type": 1},  # Compound index
    {"target_id": 1, "result": 1},  # Compound index
]
```

### Merkle Tree Model

**Collection**: `merkle_trees`

```python
class MerkleTreeStatus(str, Enum):
    BUILDING = "building"
    BUILT = "built"
    VALIDATED = "validated"
    FAILED = "failed"

class MerkleTreeModel(BaseModel):
    """Merkle tree model for lucid_blocks blockchain"""
    tree_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique tree identifier")
    session_id: str = Field(..., description="Associated session ID")
    root_hash: str = Field(..., max_length=64, regex="^[a-fA-F0-9]{64}$", description="Merkle root hash")
    
    # Tree structure
    tree_height: int = Field(..., ge=0, description="Height of the Merkle tree")
    leaf_count: int = Field(..., ge=1, description="Number of leaf nodes")
    total_nodes: int = Field(..., ge=1, description="Total number of nodes in tree")
    
    # Status and validation
    status: MerkleTreeStatus = Field(default=MerkleTreeStatus.BUILDING, description="Tree status")
    validation_results: Dict[str, Any] = Field(default_factory=dict, description="Validation results")
    error_messages: List[str] = Field(default_factory=list, description="Error messages")
    
    # Chunk data
    chunk_hashes: List[str] = Field(..., min_items=1, description="List of chunk hashes")
    chunk_metadata: List[Dict[str, Any]] = Field(default_factory=list, description="Chunk metadata")
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Tree creation time")
    completed_at: Optional[datetime] = Field(None, description="Tree completion time")
    validated_at: Optional[datetime] = Field(None, description="Tree validation time")
    
    # Storage
    storage_path: Optional[str] = Field(None, description="Path to tree data storage")
    compression_used: bool = Field(default=False, description="Whether tree data is compressed")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Tree metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator('root_hash')
    def validate_root_hash(cls, v):
        """Validate Merkle root hash format"""
        if len(v) != 64:
            raise ValueError('Root hash must be 64 characters long')
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Root hash must contain only hexadecimal characters')
        return v.lower()
    
    @validator('tree_height')
    def validate_tree_height(cls, v):
        """Validate tree height limits"""
        max_height = 20
        if v > max_height:
            raise ValueError(f'Tree height {v} exceeds limit {max_height}')
        return v
    
    @validator('leaf_count')
    def validate_leaf_count(cls, v):
        """Validate leaf count limits"""
        max_leaves = 1000000  # 1M leaves limit
        if v > max_leaves:
            raise ValueError(f'Leaf count {v} exceeds limit {max_leaves}')
        return v
    
    @validator('chunk_hashes')
    def validate_chunk_hashes(cls, v):
        """Validate chunk hash format"""
        for i, chunk_hash in enumerate(v):
            if len(chunk_hash) != 64:
                raise ValueError(f'Chunk hash {i} must be 64 characters long')
            if not all(c in '0123456789abcdefABCDEF' for c in chunk_hash):
                raise ValueError(f'Chunk hash {i} must contain only hexadecimal characters')
        return [hash.lower() for hash in v]

# MongoDB Indexes for merkle trees
merkle_tree_indexes = [
    {"tree_id": 1},  # Unique index
    {"session_id": 1},  # Unique index
    {"root_hash": 1},  # Unique index
    {"status": 1},
    {"created_at": 1},
    {"completed_at": 1},
    {"validated_at": 1},
    {"session_id": 1, "status": 1},  # Compound index
    {"created_at": 1, "status": 1},  # Compound index
]
```

### Blockchain State Model

**Collection**: `blockchain_state`

```python
class BlockchainStateModel(BaseModel):
    """Blockchain state model for lucid_blocks blockchain"""
    state_id: str = Field(default="current", description="State identifier")
    
    # Current blockchain state
    current_height: int = Field(..., ge=0, description="Current blockchain height")
    latest_block_id: str = Field(..., description="Latest block ID")
    latest_block_hash: str = Field(..., max_length=64, regex="^[a-fA-F0-9]{64}$", description="Latest block hash")
    
    # Network state
    active_validators: List[str] = Field(default_factory=list, description="Active validator nodes")
    consensus_participants: List[str] = Field(default_factory=list, description="Consensus participants")
    network_difficulty: float = Field(..., gt=0, description="Current network difficulty")
    
    # Statistics
    total_transactions: int = Field(default=0, ge=0, description="Total transactions processed")
    total_sessions_anchored: int = Field(default=0, ge=0, description="Total sessions anchored")
    average_block_time: float = Field(default=10.0, gt=0, description="Average block time in seconds")
    
    # Timing
    last_block_time: datetime = Field(..., description="Last block creation time")
    last_consensus_time: Optional[datetime] = Field(None, description="Last consensus event time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="State update time")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="State metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator('latest_block_hash')
    def validate_latest_block_hash(cls, v):
        """Validate latest block hash format"""
        if len(v) != 64:
            raise ValueError('Latest block hash must be 64 characters long')
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Latest block hash must contain only hexadecimal characters')
        return v.lower()
    
    @validator('active_validators')
    def validate_validators(cls, v):
        """Validate validator list"""
        if len(set(v)) != len(v):
            raise ValueError('Validator IDs must be unique')
        return v
    
    @validator('consensus_participants')
    def validate_participants(cls, v):
        """Validate consensus participants"""
        if len(set(v)) != len(v):
            raise ValueError('Consensus participant IDs must be unique')
        return v

# MongoDB Indexes for blockchain state
blockchain_state_indexes = [
    {"state_id": 1},  # Unique index
    {"current_height": 1},
    {"latest_block_id": 1},
    {"updated_at": 1},
    {"last_block_time": 1},
]
```

## Request/Response Models

### Block Request Models

```python
class BlockValidationRequest(BaseModel):
    """Request model for block validation"""
    block_data: BlockModel = Field(..., description="Block data to validate")
    validate_signature: bool = Field(default=True, description="Whether to validate signature")
    validate_merkle_root: bool = Field(default=True, description="Whether to validate Merkle root")
    validate_transactions: bool = Field(default=True, description="Whether to validate transactions")

class BlockValidationResponse(BaseModel):
    """Response model for block validation"""
    valid: bool = Field(..., description="Whether block is valid")
    validation_results: Dict[str, bool] = Field(..., description="Detailed validation results")
    errors: List[str] = Field(default_factory=list, description="Validation error messages")
    validation_time_ms: float = Field(..., description="Validation time in milliseconds")
```

### Transaction Request Models

```python
class TransactionSubmitRequest(BaseModel):
    """Request model for transaction submission"""
    type: TransactionType = Field(..., description="Transaction type")
    data: Dict[str, Any] = Field(..., description="Transaction data")
    signature: str = Field(..., max_length=256, description="Transaction signature")
    fee: float = Field(default=0.0, ge=0.0, description="Transaction fee")
    timestamp: Optional[datetime] = Field(None, description="Transaction timestamp")

class TransactionBatchRequest(BaseModel):
    """Request model for batch transaction submission"""
    transactions: List[TransactionSubmitRequest] = Field(..., min_items=1, max_items=100, description="List of transactions")
    batch_signature: Optional[str] = Field(None, description="Batch signature")

class TransactionResponse(BaseModel):
    """Response model for transaction submission"""
    tx_id: str = Field(..., description="Transaction ID")
    status: TransactionStatus = Field(..., description="Transaction status")
    submitted_at: datetime = Field(..., description="Submission time")
    confirmation_time: Optional[datetime] = Field(None, description="Confirmation time")
    block_height: Optional[int] = Field(None, description="Block height")
```

### Anchoring Request Models

```python
class SessionAnchoringRequest(BaseModel):
    """Request model for session anchoring"""
    session_id: str = Field(..., description="Session ID to anchor")
    manifest_data: Dict[str, Any] = Field(..., description="Session manifest data")
    merkle_root: str = Field(..., max_length=64, regex="^[a-fA-F0-9]{64}$", description="Merkle root hash")
    user_signature: str = Field(..., max_length=256, description="User signature")

class AnchoringVerificationRequest(BaseModel):
    """Request model for anchoring verification"""
    session_id: str = Field(..., description="Session ID to verify")
    merkle_root: str = Field(..., max_length=64, regex="^[a-fA-F0-9]{64}$", description="Merkle root hash")
    block_height: Optional[int] = Field(None, description="Expected block height")

class SessionAnchoringResponse(BaseModel):
    """Response model for session anchoring"""
    anchoring_id: str = Field(..., description="Anchoring ID")
    status: AnchoringStatus = Field(..., description="Anchoring status")
    submitted_at: datetime = Field(..., description="Submission time")
    estimated_confirmation_time: Optional[datetime] = Field(None, description="Estimated confirmation time")
```

### Consensus Request Models

```python
class ConsensusVoteRequest(BaseModel):
    """Request model for consensus voting"""
    vote_type: ConsensusEventType = Field(..., description="Type of vote")
    target_id: str = Field(..., description="Target being voted on")
    vote_decision: str = Field(..., regex="^(approve|reject|abstain)$", description="Vote decision")
    reasoning: Optional[str] = Field(None, max_length=1000, description="Vote reasoning")
    signature: str = Field(..., max_length=256, description="Vote signature")

class ConsensusVoteResponse(BaseModel):
    """Response model for consensus voting"""
    vote_id: str = Field(..., description="Vote ID")
    status: str = Field(..., description="Vote status")
    submitted_at: datetime = Field(..., description="Submission time")
    vote_weight: float = Field(..., description="Vote weight")
```

### Merkle Tree Request Models

```python
class MerkleTreeBuildRequest(BaseModel):
    """Request model for Merkle tree building"""
    session_id: str = Field(..., description="Session ID")
    chunk_hashes: List[str] = Field(..., min_items=1, description="List of chunk hashes")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Tree metadata")

class MerkleProofVerificationRequest(BaseModel):
    """Request model for Merkle proof verification"""
    root_hash: str = Field(..., max_length=64, regex="^[a-fA-F0-9]{64}$", description="Merkle root hash")
    leaf_hash: str = Field(..., max_length=64, regex="^[a-fA-F0-9]{64}$", description="Leaf hash")
    proof_path: List[str] = Field(..., description="Merkle proof path")

class MerkleTreeResponse(BaseModel):
    """Response model for Merkle tree operations"""
    tree_id: str = Field(..., description="Tree ID")
    root_hash: str = Field(..., description="Merkle root hash")
    tree_height: int = Field(..., description="Tree height")
    leaf_count: int = Field(..., description="Leaf count")
    created_at: datetime = Field(..., description="Creation time")
    session_id: str = Field(..., description="Session ID")
```

## Validation Rules

### Block Validation Rules

```python
# Block validation constants
MAX_BLOCK_SIZE_BYTES = 1024 * 1024  # 1MB
MAX_TRANSACTIONS_PER_BLOCK = 1000
MIN_BLOCK_TIME_SECONDS = 1
MAX_BLOCK_TIME_SECONDS = 60

# Block hash validation
def validate_block_hash(block_hash: str) -> bool:
    """Validate block hash format and length"""
    if len(block_hash) != 64:
        return False
    if not all(c in '0123456789abcdefABCDEF' for c in block_hash):
        return False
    return True

# Block size validation
def validate_block_size(size_bytes: int) -> bool:
    """Validate block size limits"""
    return 0 <= size_bytes <= MAX_BLOCK_SIZE_BYTES

# Transaction count validation
def validate_transaction_count(count: int) -> bool:
    """Validate transaction count limits"""
    return 0 <= count <= MAX_TRANSACTIONS_PER_BLOCK
```

### Transaction Validation Rules

```python
# Transaction validation constants
MAX_TRANSACTION_SIZE_BYTES = 1024 * 1024  # 1MB
MIN_TRANSACTION_FEE = 0.0
MAX_TRANSACTION_FEE = 1000.0

# Transaction size validation
def validate_transaction_size(size_bytes: int) -> bool:
    """Validate transaction size limits"""
    return 0 <= size_bytes <= MAX_TRANSACTION_SIZE_BYTES

# Transaction fee validation
def validate_transaction_fee(fee: float) -> bool:
    """Validate transaction fee limits"""
    return MIN_TRANSACTION_FEE <= fee <= MAX_TRANSACTION_FEE

# Transaction signature validation
def validate_transaction_signature(signature: str) -> bool:
    """Validate transaction signature format"""
    if len(signature) < 64 or len(signature) > 256:
        return False
    # Additional signature format validation would go here
    return True
```

### Merkle Tree Validation Rules

```python
# Merkle tree validation constants
MAX_MERKLE_TREE_HEIGHT = 20
MAX_LEAF_COUNT = 1000000  # 1M leaves
MIN_CHUNK_HASH_LENGTH = 64
MAX_CHUNK_HASH_LENGTH = 64

# Merkle tree height validation
def validate_merkle_tree_height(height: int) -> bool:
    """Validate Merkle tree height limits"""
    return 0 <= height <= MAX_MERKLE_TREE_HEIGHT

# Leaf count validation
def validate_leaf_count(count: int) -> bool:
    """Validate leaf count limits"""
    return 1 <= count <= MAX_LEAF_COUNT

# Chunk hash validation
def validate_chunk_hash(chunk_hash: str) -> bool:
    """Validate chunk hash format"""
    if len(chunk_hash) != 64:
        return False
    if not all(c in '0123456789abcdefABCDEF' for c in chunk_hash):
        return False
    return True
```

## MongoDB Collection Configuration

### Collection Settings

```javascript
// blocks collection
db.createCollection("blocks", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["block_id", "height", "hash", "previous_hash", "merkle_root", "timestamp"],
      properties: {
        block_id: { bsonType: "string" },
        height: { bsonType: "int", minimum: 0 },
        hash: { bsonType: "string", pattern: "^[a-f0-9]{64}$" },
        previous_hash: { bsonType: "string", pattern: "^[a-f0-9]{64}$" },
        merkle_root: { bsonType: "string", pattern: "^[a-f0-9]{64}$" },
        block_size_bytes: { bsonType: "int", minimum: 0, maximum: 1048576 },
        transaction_count: { bsonType: "int", minimum: 0, maximum: 1000 }
      }
    }
  },
  validationLevel: "strict",
  validationAction: "error"
});

// transactions collection
db.createCollection("transactions", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["tx_id", "type", "data", "signature", "size_bytes"],
      properties: {
        tx_id: { bsonType: "string" },
        type: { enum: ["session_anchor", "data_storage", "consensus_vote", "system"] },
        size_bytes: { bsonType: "int", minimum: 0, maximum: 1048576 },
        fee: { bsonType: "double", minimum: 0, maximum: 1000 }
      }
    }
  },
  validationLevel: "strict",
  validationAction: "error"
});
```

### Index Creation Script

```javascript
// Create all indexes for Blockchain Core collections
db.blocks.createIndex({ "block_id": 1 }, { unique: true });
db.blocks.createIndex({ "hash": 1 }, { unique: true });
db.blocks.createIndex({ "height": 1 }, { unique: true });
db.blocks.createIndex({ "previous_hash": 1 });
db.blocks.createIndex({ "timestamp": 1 });
db.blocks.createIndex({ "validator": 1 });
db.blocks.createIndex({ "status": 1 });
db.blocks.createIndex({ "height": 1, "status": 1 });

db.transactions.createIndex({ "tx_id": 1 }, { unique: true });
db.transactions.createIndex({ "type": 1 });
db.transactions.createIndex({ "status": 1 });
db.transactions.createIndex({ "block_id": 1 });
db.transactions.createIndex({ "block_height": 1 });
db.transactions.createIndex({ "submitted_at": 1 });
db.transactions.createIndex({ "type": 1, "status": 1 });
db.transactions.createIndex({ "block_height": 1, "transaction_index": 1 });

db.session_anchorings.createIndex({ "anchoring_id": 1 }, { unique: true });
db.session_anchorings.createIndex({ "session_id": 1 }, { unique: true });
db.session_anchorings.createIndex({ "status": 1 });
db.session_anchorings.createIndex({ "user_id": 1 });
db.session_anchorings.createIndex({ "transaction_id": 1 }, { sparse: true });
db.session_anchorings.createIndex({ "block_height": 1 }, { sparse: true });
db.session_anchorings.createIndex({ "user_id": 1, "status": 1 });

db.consensus_events.createIndex({ "event_id": 1 }, { unique: true });
db.consensus_events.createIndex({ "event_type": 1 });
db.consensus_events.createIndex({ "target_id": 1 });
db.consensus_events.createIndex({ "round_number": 1 });
db.consensus_events.createIndex({ "result": 1 });
db.consensus_events.createIndex({ "started_at": 1 });
db.consensus_events.createIndex({ "round_number": 1, "event_type": 1 });

db.merkle_trees.createIndex({ "tree_id": 1 }, { unique: true });
db.merkle_trees.createIndex({ "session_id": 1 }, { unique: true });
db.merkle_trees.createIndex({ "root_hash": 1 }, { unique: true });
db.merkle_trees.createIndex({ "status": 1 });
db.merkle_trees.createIndex({ "created_at": 1 });
db.merkle_trees.createIndex({ "session_id": 1, "status": 1 });

db.blockchain_state.createIndex({ "state_id": 1 }, { unique: true });
db.blockchain_state.createIndex({ "current_height": 1 });
db.blockchain_state.createIndex({ "latest_block_id": 1 });
db.blockchain_state.createIndex({ "updated_at": 1 });
```

## Data Migration Scripts

### Block Migration

```python
async def migrate_blocks():
    """Migrate blocks from old schema to new schema"""
    async for block in db.blocks.find({}):
        # Add new fields with defaults
        update_data = {
            "status": "confirmed",
            "transaction_ids": [],
            "metadata": {},
            "updated_at": datetime.utcnow()
        }
        
        # Update block document
        await db.blocks.update_one(
            {"_id": block["_id"]},
            {"$set": update_data}
        )
```

### Transaction Migration

```python
async def migrate_transactions():
    """Migrate transactions from old schema to new schema"""
    async for transaction in db.transactions.find({}):
        # Add new fields with defaults
        update_data = {
            "validation_errors": [],
            "metadata": {},
            "gas_limit": None,
            "gas_used": None
        }
        
        # Update transaction document
        await db.transactions.update_one(
            {"_id": transaction["_id"]},
            {"$set": update_data}
        )
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
