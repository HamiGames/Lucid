# Blockchain Core Cluster - Implementation Guide

## Overview

This document provides comprehensive implementation guidance for the Blockchain Core cluster (`lucid_blocks`), including code structure, naming conventions, distroless container configuration, and deployment patterns. **CRITICAL**: This cluster is completely isolated from TRON operations.

## Code Structure

### Project Layout

```
blockchain/
├── Dockerfile.engine           # Blockchain engine distroless container
├── Dockerfile.anchoring        # Session anchoring distroless container
├── Dockerfile.manager          # Block manager distroless container
├── Dockerfile.data             # Data chain distroless container
├── docker-compose.yml          # Local development setup
├── requirements.txt            # Python dependencies
├── core/
│   ├── __init__.py
│   ├── blockchain_engine.py    # Core blockchain engine (NO TRON CODE)
│   ├── consensus_engine.py     # PoOT consensus implementation
│   ├── block_manager.py        # Block creation and validation
│   ├── transaction_processor.py # Transaction processing
│   └── merkle_tree_builder.py  # Merkle tree construction
├── api/
│   ├── app/
│   │   ├── main.py             # FastAPI application entry point
│   │   ├── config.py           # Configuration management
│   │   ├── middleware/         # Custom middleware
│   │   │   ├── __init__.py
│   │   │   ├── auth.py         # Authentication middleware
│   │   │   ├── rate_limit.py   # Rate limiting middleware
│   │   │   └── logging.py      # Request/response logging
│   │   ├── routers/            # API route handlers
│   │   │   ├── __init__.py
│   │   │   ├── blockchain.py   # Blockchain information endpoints
│   │   │   ├── blocks.py       # Block management endpoints
│   │   │   ├── transactions.py # Transaction endpoints
│   │   │   ├── anchoring.py    # Session anchoring endpoints
│   │   │   ├── consensus.py    # Consensus endpoints
│   │   │   └── merkle.py       # Merkle tree endpoints
│   │   ├── services/           # Business logic services
│   │   │   ├── __init__.py
│   │   │   ├── blockchain_service.py # Blockchain operations
│   │   │   ├── block_service.py # Block operations
│   │   │   ├── transaction_service.py # Transaction operations
│   │   │   ├── anchoring_service.py # Session anchoring
│   │   │   ├── consensus_service.py # Consensus operations
│   │   │   └── merkle_service.py # Merkle tree operations
│   │   ├── models/             # Data models
│   │   │   ├── __init__.py
│   │   │   ├── block.py        # Block models
│   │   │   ├── transaction.py  # Transaction models
│   │   │   ├── anchoring.py    # Anchoring models
│   │   │   ├── consensus.py    # Consensus models
│   │   │   └── merkle.py       # Merkle tree models
│   │   ├── database/           # Database layer
│   │   │   ├── __init__.py
│   │   │   ├── connection.py   # MongoDB connection
│   │   │   ├── repositories/   # Data repositories
│   │   │   │   ├── __init__.py
│   │   │   │   ├── block_repository.py
│   │   │   │   ├── transaction_repository.py
│   │   │   │   ├── anchoring_repository.py
│   │   │   │   ├── consensus_repository.py
│   │   │   │   └── merkle_repository.py
│   │   │   └── migrations/     # Database migrations
│   │   │       ├── __init__.py
│   │   │       └── v1_initial.py
│   │   └── utils/              # Utility functions
│   │       ├── __init__.py
│   │       ├── crypto.py       # Cryptographic utilities
│   │       ├── validation.py   # Validation utilities
│   │       ├── merkle.py       # Merkle tree utilities
│   │       └── consensus.py    # Consensus utilities
│   └── tests/                  # Test suite
│       ├── __init__.py
│       ├── conftest.py         # Test configuration
│       ├── test_blockchain.py  # Blockchain tests
│       ├── test_blocks.py      # Block tests
│       ├── test_transactions.py # Transaction tests
│       ├── test_anchoring.py   # Anchoring tests
│       ├── test_consensus.py   # Consensus tests
│       └── test_merkle.py      # Merkle tree tests
├── anchoring/
│   ├── Dockerfile              # Session anchoring service
│   ├── main.py                 # Anchoring service entry point
│   ├── anchoring_service.py    # Anchoring business logic
│   └── merkle_validator.py     # Merkle tree validation
├── manager/
│   ├── Dockerfile              # Block manager service
│   ├── main.py                 # Manager service entry point
│   ├── block_manager.py        # Block management logic
│   └── storage_manager.py      # Block storage management
├── data/
│   ├── Dockerfile              # Data chain service
│   ├── main.py                 # Data service entry point
│   ├── data_chain.py           # Data chain operations
│   └── chunk_manager.py        # Chunk management
└── scripts/                    # Deployment scripts
    ├── build.sh               # Build script
    ├── deploy.sh              # Deployment script
    └── health_check.sh        # Health check script
```

## Core Implementation Files

### Blockchain Engine (core/blockchain_engine.py)

```python
"""
Blockchain Engine for lucid_blocks

CRITICAL: This module contains NO TRON code. All TRON operations
are handled by the separate tron-payment-service.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import hashlib
import json

from .consensus_engine import ConsensusEngine
from .block_manager import BlockManager
from .transaction_processor import TransactionProcessor
from ..api.database.repositories.block_repository import BlockRepository
from ..api.database.repositories.transaction_repository import TransactionRepository
from ..api.models.block import BlockModel, BlockStatus
from ..api.models.transaction import TransactionModel, TransactionStatus

logger = logging.getLogger(__name__)

class BlockchainEngine:
    """Core blockchain engine for lucid_blocks system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.consensus_engine = ConsensusEngine(config)
        self.block_manager = BlockManager(config)
        self.transaction_processor = TransactionProcessor(config)
        
        # Repositories
        self.block_repo = BlockRepository()
        self.transaction_repo = TransactionRepository()
        
        # Blockchain state
        self.current_height = 0
        self.latest_block_id = None
        self.latest_block_hash = None
        self.network_difficulty = 1.0
        
        # Block production settings
        self.block_time_seconds = config.get('block_time_seconds', 10)
        self.max_transactions_per_block = config.get('max_transactions_per_block', 1000)
        
        # Consensus settings
        self.consensus_timeout = config.get('consensus_timeout', 30)
        self.min_participants = config.get('consensus_participants_min', 3)
        
        # State tracking
        self.is_running = False
        self.block_production_task = None
        
    async def initialize(self):
        """Initialize the blockchain engine"""
        logger.info("Initializing lucid_blocks blockchain engine")
        
        # Load blockchain state
        await self._load_blockchain_state()
        
        # Initialize consensus engine
        await self.consensus_engine.initialize()
        
        # Initialize block manager
        await self.block_manager.initialize()
        
        # Initialize transaction processor
        await self.transaction_processor.initialize()
        
        logger.info("Blockchain engine initialized successfully")
    
    async def start(self):
        """Start the blockchain engine"""
        if self.is_running:
            logger.warning("Blockchain engine is already running")
            return
        
        logger.info("Starting lucid_blocks blockchain engine")
        self.is_running = True
        
        # Start block production
        self.block_production_task = asyncio.create_task(self._block_production_loop())
        
        # Start consensus monitoring
        asyncio.create_task(self._consensus_monitoring_loop())
        
        logger.info("Blockchain engine started successfully")
    
    async def stop(self):
        """Stop the blockchain engine"""
        if not self.is_running:
            logger.warning("Blockchain engine is not running")
            return
        
        logger.info("Stopping lucid_blocks blockchain engine")
        self.is_running = False
        
        # Cancel block production task
        if self.block_production_task:
            self.block_production_task.cancel()
            try:
                await self.block_production_task
            except asyncio.CancelledError:
                pass
        
        # Stop consensus engine
        await self.consensus_engine.stop()
        
        logger.info("Blockchain engine stopped successfully")
    
    async def _block_production_loop(self):
        """Main block production loop"""
        while self.is_running:
            try:
                # Wait for block time
                await asyncio.sleep(self.block_time_seconds)
                
                # Check if we should produce a block
                if await self._should_produce_block():
                    await self._produce_block()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in block production loop: {e}")
                await asyncio.sleep(1)  # Brief pause before retry
    
    async def _should_produce_block(self) -> bool:
        """Check if we should produce a new block"""
        # Check if we have pending transactions
        pending_count = await self.transaction_repo.count_pending_transactions()
        if pending_count == 0:
            return False
        
        # Check if enough time has passed since last block
        latest_block = await self.block_repo.get_latest_block()
        if latest_block:
            time_since_last = datetime.utcnow() - latest_block.timestamp
            if time_since_last.total_seconds() < self.block_time_seconds:
                return False
        
        # Check consensus readiness
        if not await self.consensus_engine.is_ready_for_block():
            return False
        
        return True
    
    async def _produce_block(self):
        """Produce a new block"""
        try:
            logger.info("Producing new block")
            
            # Get pending transactions
            pending_transactions = await self.transaction_repo.get_pending_transactions(
                limit=self.max_transactions_per_block
            )
            
            if not pending_transactions:
                logger.info("No pending transactions to include in block")
                return
            
            # Create new block
            new_block = await self._create_block(pending_transactions)
            
            # Validate block
            if not await self._validate_block(new_block):
                logger.error("Block validation failed")
                return
            
            # Submit to consensus
            consensus_result = await self.consensus_engine.submit_block(new_block)
            
            if consensus_result.approved:
                # Confirm block
                await self._confirm_block(new_block, pending_transactions)
                logger.info(f"Block {new_block.height} confirmed successfully")
            else:
                logger.warning(f"Block {new_block.height} rejected by consensus")
                
        except Exception as e:
            logger.exception(f"Error producing block: {e}")
    
    async def _create_block(self, transactions: List[TransactionModel]) -> BlockModel:
        """Create a new block with given transactions"""
        # Get latest block for chain reference
        latest_block = await self.block_repo.get_latest_block()
        
        # Calculate new block height
        new_height = (latest_block.height + 1) if latest_block else 0
        
        # Build Merkle tree from transactions
        merkle_root = await self._build_merkle_root(transactions)
        
        # Create block
        block = BlockModel(
            block_id=f"block_{new_height}_{int(datetime.utcnow().timestamp())}",
            height=new_height,
            hash="",  # Will be calculated after
            previous_hash=latest_block.hash if latest_block else "0" * 64,
            merkle_root=merkle_root,
            timestamp=datetime.utcnow(),
            nonce=0,  # Will be calculated during mining
            difficulty=self.network_difficulty,
            block_size_bytes=0,  # Will be calculated
            transaction_count=len(transactions),
            validator=self.config.get('node_id', 'unknown'),
            signature="",  # Will be calculated after
            status=BlockStatus.PENDING,
            transaction_ids=[tx.tx_id for tx in transactions]
        )
        
        # Calculate block hash and signature
        block.hash = await self._calculate_block_hash(block)
        block.signature = await self._sign_block(block)
        block.block_size_bytes = len(json.dumps(block.dict()).encode())
        
        return block
    
    async def _build_merkle_root(self, transactions: List[TransactionModel]) -> str:
        """Build Merkle root from transaction list"""
        if not transactions:
            return "0" * 64
        
        # Get transaction hashes
        tx_hashes = [tx.tx_id for tx in transactions]
        
        # Build Merkle tree
        from ..api.utils.merkle import MerkleTree
        merkle_tree = MerkleTree(tx_hashes)
        return merkle_tree.get_root()
    
    async def _calculate_block_hash(self, block: BlockModel) -> str:
        """Calculate block hash"""
        # Create hash input (excluding hash and signature fields)
        hash_input = {
            "block_id": block.block_id,
            "height": block.height,
            "previous_hash": block.previous_hash,
            "merkle_root": block.merkle_root,
            "timestamp": block.timestamp.isoformat(),
            "nonce": block.nonce,
            "difficulty": block.difficulty,
            "transaction_count": block.transaction_count,
            "validator": block.validator
        }
        
        # Calculate SHA256 hash
        hash_string = json.dumps(hash_input, sort_keys=True)
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    async def _sign_block(self, block: BlockModel) -> str:
        """Sign block with validator key"""
        # In a real implementation, this would use the validator's private key
        # For now, we'll create a placeholder signature
        signature_data = f"{block.hash}{block.validator}{block.timestamp.isoformat()}"
        return hashlib.sha256(signature_data.encode()).hexdigest()
    
    async def _validate_block(self, block: BlockModel) -> bool:
        """Validate block structure and content"""
        try:
            # Validate block structure
            if not await self.block_manager.validate_block_structure(block):
                return False
            
            # Validate transactions
            for tx_id in block.transaction_ids:
                transaction = await self.transaction_repo.get_transaction_by_id(tx_id)
                if not transaction:
                    logger.error(f"Transaction {tx_id} not found")
                    return False
                
                if not await self.transaction_processor.validate_transaction(transaction):
                    logger.error(f"Transaction {tx_id} validation failed")
                    return False
            
            # Validate Merkle root
            transactions = await self.transaction_repo.get_transactions_by_ids(block.transaction_ids)
            expected_merkle_root = await self._build_merkle_root(transactions)
            if block.merkle_root != expected_merkle_root:
                logger.error("Merkle root mismatch")
                return False
            
            # Validate block hash
            expected_hash = await self._calculate_block_hash(block)
            if block.hash != expected_hash:
                logger.error("Block hash mismatch")
                return False
            
            return True
            
        except Exception as e:
            logger.exception(f"Block validation error: {e}")
            return False
    
    async def _confirm_block(self, block: BlockModel, transactions: List[TransactionModel]):
        """Confirm block and update blockchain state"""
        try:
            # Update block status
            block.status = BlockStatus.CONFIRMED
            block.updated_at = datetime.utcnow()
            await self.block_repo.save_block(block)
            
            # Update transaction statuses
            for transaction in transactions:
                transaction.status = TransactionStatus.CONFIRMED
                transaction.block_id = block.block_id
                transaction.block_height = block.height
                transaction.confirmed_at = datetime.utcnow()
                await self.transaction_repo.save_transaction(transaction)
            
            # Update blockchain state
            self.current_height = block.height
            self.latest_block_id = block.block_id
            self.latest_block_hash = block.hash
            
            # Save blockchain state
            await self._save_blockchain_state()
            
            logger.info(f"Block {block.height} confirmed and blockchain state updated")
            
        except Exception as e:
            logger.exception(f"Error confirming block: {e}")
            raise
    
    async def _load_blockchain_state(self):
        """Load blockchain state from database"""
        try:
            # In a real implementation, this would load from a state collection
            # For now, we'll get the latest block to determine state
            latest_block = await self.block_repo.get_latest_block()
            
            if latest_block:
                self.current_height = latest_block.height
                self.latest_block_id = latest_block.block_id
                self.latest_block_hash = latest_block.hash
            else:
                # Genesis block
                self.current_height = 0
                self.latest_block_id = None
                self.latest_block_hash = None
            
            logger.info(f"Loaded blockchain state: height={self.current_height}")
            
        except Exception as e:
            logger.exception(f"Error loading blockchain state: {e}")
            raise
    
    async def _save_blockchain_state(self):
        """Save blockchain state to database"""
        try:
            # In a real implementation, this would save to a state collection
            # For now, we'll just log the state
            logger.info(f"Saving blockchain state: height={self.current_height}")
            
        except Exception as e:
            logger.exception(f"Error saving blockchain state: {e}")
    
    async def _consensus_monitoring_loop(self):
        """Monitor consensus status"""
        while self.is_running:
            try:
                # Check consensus health
                consensus_status = await self.consensus_engine.get_status()
                
                if not consensus_status.healthy:
                    logger.warning("Consensus engine is not healthy")
                
                # Wait before next check
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in consensus monitoring: {e}")
                await asyncio.sleep(5)
    
    # Public API methods
    async def get_blockchain_info(self) -> Dict[str, Any]:
        """Get blockchain information"""
        return {
            "network_name": "lucid_blocks",
            "version": "1.0.0",
            "consensus_algorithm": "PoOT",
            "block_time_seconds": self.block_time_seconds,
            "current_height": self.current_height,
            "genesis_block": "0" * 64,
            "total_transactions": await self.transaction_repo.count_confirmed_transactions(),
            "network_difficulty": self.network_difficulty
        }
    
    async def get_blockchain_status(self) -> Dict[str, Any]:
        """Get blockchain status"""
        return {
            "status": "healthy" if self.is_running else "stopped",
            "current_height": self.current_height,
            "latest_block_id": self.latest_block_id,
            "latest_block_hash": self.latest_block_hash,
            "is_running": self.is_running,
            "consensus_status": await self.consensus_engine.get_status(),
            "pending_transactions": await self.transaction_repo.count_pending_transactions()
        }
    
    async def submit_transaction(self, transaction: TransactionModel) -> bool:
        """Submit a transaction to the blockchain"""
        try:
            # Validate transaction
            if not await self.transaction_processor.validate_transaction(transaction):
                return False
            
            # Save transaction
            await self.transaction_repo.save_transaction(transaction)
            
            logger.info(f"Transaction {transaction.tx_id} submitted successfully")
            return True
            
        except Exception as e:
            logger.exception(f"Error submitting transaction: {e}")
            return False
    
    async def get_block_by_height(self, height: int) -> Optional[BlockModel]:
        """Get block by height"""
        return await self.block_repo.get_block_by_height(height)
    
    async def get_block_by_hash(self, block_hash: str) -> Optional[BlockModel]:
        """Get block by hash"""
        return await self.block_repo.get_block_by_hash(block_hash)
    
    async def get_transaction_by_id(self, tx_id: str) -> Optional[TransactionModel]:
        """Get transaction by ID"""
        return await self.transaction_repo.get_transaction_by_id(tx_id)
```

### Consensus Engine (core/consensus_engine.py)

```python
"""
Consensus Engine for lucid_blocks - PoOT (Proof of Observation Time)

CRITICAL: This module contains NO TRON code. All TRON operations
are handled by the separate tron-payment-service.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from ..api.models.block import BlockModel
from ..api.models.consensus import ConsensusEventModel, ConsensusResult
from ..api.database.repositories.consensus_repository import ConsensusRepository

logger = logging.getLogger(__name__)

class ConsensusStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"

@dataclass
class ConsensusParticipant:
    """Consensus participant information"""
    node_id: str
    address: str
    voting_power: float
    last_seen: datetime
    is_active: bool

@dataclass
class ConsensusResult:
    """Consensus result"""
    approved: bool
    participants_count: int
    approval_percentage: float
    consensus_time: datetime
    reasoning: str

class ConsensusEngine:
    """PoOT (Proof of Observation Time) consensus engine"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.consensus_repo = ConsensusRepository()
        
        # Consensus settings
        self.consensus_timeout = config.get('consensus_timeout', 30)
        self.min_participants = config.get('consensus_participants_min', 3)
        self.approval_threshold = config.get('consensus_approval_threshold', 0.67)
        
        # Participant management
        self.participants: Dict[str, ConsensusParticipant] = {}
        self.node_id = config.get('node_id', 'unknown')
        
        # Consensus state
        self.is_initialized = False
        self.current_round = 0
        self.active_consensus = None
        
        # Monitoring
        self.consensus_history: List[Dict[str, Any]] = []
        
    async def initialize(self):
        """Initialize consensus engine"""
        logger.info("Initializing PoOT consensus engine")
        
        # Load consensus participants
        await self._load_participants()
        
        # Initialize consensus state
        self.current_round = 0
        self.active_consensus = None
        
        self.is_initialized = True
        logger.info("Consensus engine initialized successfully")
    
    async def stop(self):
        """Stop consensus engine"""
        logger.info("Stopping consensus engine")
        
        # Cancel any active consensus
        if self.active_consensus:
            await self._cancel_active_consensus()
        
        self.is_initialized = False
        logger.info("Consensus engine stopped")
    
    async def _load_participants(self):
        """Load consensus participants from configuration or database"""
        # In a real implementation, this would load from a participants collection
        # For now, we'll use configuration
        participants_config = self.config.get('consensus_participants', [])
        
        for participant_config in participants_config:
            participant = ConsensusParticipant(
                node_id=participant_config['node_id'],
                address=participant_config['address'],
                voting_power=participant_config.get('voting_power', 1.0),
                last_seen=datetime.utcnow(),
                is_active=True
            )
            self.participants[participant.node_id] = participant
        
        logger.info(f"Loaded {len(self.participants)} consensus participants")
    
    async def is_ready_for_block(self) -> bool:
        """Check if consensus is ready for block production"""
        if not self.is_initialized:
            return False
        
        # Check if we have enough active participants
        active_participants = [p for p in self.participants.values() if p.is_active]
        if len(active_participants) < self.min_participants:
            logger.warning(f"Not enough consensus participants: {len(active_participants)} < {self.min_participants}")
            return False
        
        # Check if there's an active consensus
        if self.active_consensus:
            logger.warning("Consensus already active")
            return False
        
        return True
    
    async def submit_block(self, block: BlockModel) -> ConsensusResult:
        """Submit block for consensus"""
        if not await self.is_ready_for_block():
            return ConsensusResult(
                approved=False,
                participants_count=0,
                approval_percentage=0.0,
                consensus_time=datetime.utcnow(),
                reasoning="Consensus not ready"
            )
        
        logger.info(f"Submitting block {block.height} for consensus")
        
        # Create consensus event
        consensus_event = ConsensusEventModel(
            event_type="block_validation",
            target_id=block.block_id,
            round_number=self.current_round,
            participants=[p.node_id for p in self.participants.values() if p.is_active],
            votes={},
            approval_threshold=self.approval_threshold,
            started_at=datetime.utcnow(),
            timeout_at=datetime.utcnow() + timedelta(seconds=self.consensus_timeout)
        )
        
        # Start consensus process
        self.active_consensus = consensus_event
        consensus_result = await self._run_consensus(consensus_event)
        
        # Clean up
        self.active_consensus = None
        self.current_round += 1
        
        # Save consensus event
        await self.consensus_repo.save_consensus_event(consensus_event)
        
        return consensus_result
    
    async def _run_consensus(self, consensus_event: ConsensusEventModel) -> ConsensusResult:
        """Run consensus process"""
        try:
            logger.info(f"Starting consensus round {consensus_event.round_number}")
            
            # Collect votes from participants
            votes = await self._collect_votes(consensus_event)
            consensus_event.votes = votes
            
            # Calculate consensus result
            approval_count = sum(1 for vote in votes.values() if vote == 'approve')
            total_votes = len(votes)
            approval_percentage = approval_count / total_votes if total_votes > 0 else 0.0
            
            # Determine result
            approved = approval_percentage >= self.approval_threshold
            
            consensus_result = ConsensusResult(
                approved=approved,
                participants_count=total_votes,
                approval_percentage=approval_percentage,
                consensus_time=datetime.utcnow(),
                reasoning=f"Approval: {approval_count}/{total_votes} ({approval_percentage:.2%})"
            )
            
            # Update consensus event
            consensus_event.result = "approved" if approved else "rejected"
            consensus_event.approval_percentage = approval_percentage
            consensus_event.completed_at = datetime.utcnow()
            
            logger.info(f"Consensus completed: {consensus_result.reasoning}")
            
            return consensus_result
            
        except Exception as e:
            logger.exception(f"Error in consensus process: {e}")
            
            return ConsensusResult(
                approved=False,
                participants_count=0,
                approval_percentage=0.0,
                consensus_time=datetime.utcnow(),
                reasoning=f"Consensus error: {str(e)}"
            )
    
    async def _collect_votes(self, consensus_event: ConsensusEventModel) -> Dict[str, str]:
        """Collect votes from consensus participants"""
        votes = {}
        
        # In a real implementation, this would send requests to other nodes
        # For now, we'll simulate votes from local participants
        
        for participant_id in consensus_event.participants:
            try:
                # Simulate vote collection (in reality, this would be an RPC call)
                vote = await self._simulate_participant_vote(participant_id, consensus_event)
                votes[participant_id] = vote
                
            except Exception as e:
                logger.warning(f"Failed to collect vote from {participant_id}: {e}")
                votes[participant_id] = 'abstain'
        
        return votes
    
    async def _simulate_participant_vote(self, participant_id: str, consensus_event: ConsensusEventModel) -> str:
        """Simulate participant vote (for testing purposes)"""
        # In a real implementation, this would make an RPC call to the participant
        # For now, we'll simulate different voting patterns
        
        await asyncio.sleep(0.1)  # Simulate network delay
        
        # Simple simulation: 80% approval rate
        import random
        if random.random() < 0.8:
            return 'approve'
        elif random.random() < 0.9:
            return 'reject'
        else:
            return 'abstain'
    
    async def _cancel_active_consensus(self):
        """Cancel active consensus process"""
        if self.active_consensus:
            self.active_consensus.result = "failed"
            self.active_consensus.completed_at = datetime.utcnow()
            self.active_consensus = None
    
    async def get_status(self) -> Dict[str, Any]:
        """Get consensus engine status"""
        active_participants = [p for p in self.participants.values() if p.is_active]
        
        return {
            "status": "healthy" if self.is_initialized else "stopped",
            "current_round": self.current_round,
            "participants_count": len(active_participants),
            "min_participants": self.min_participants,
            "approval_threshold": self.approval_threshold,
            "active_consensus": self.active_consensus is not None,
            "consensus_timeout": self.consensus_timeout,
            "participants": [
                {
                    "node_id": p.node_id,
                    "address": p.address,
                    "voting_power": p.voting_power,
                    "is_active": p.is_active,
                    "last_seen": p.last_seen.isoformat()
                }
                for p in self.participants.values()
            ]
        }
    
    async def submit_vote(self, vote_request: Dict[str, Any]) -> bool:
        """Submit a consensus vote"""
        try:
            if not self.active_consensus:
                logger.warning("No active consensus to vote on")
                return False
            
            participant_id = vote_request.get('participant_id')
            vote_decision = vote_request.get('vote_decision')
            
            if participant_id not in self.active_consensus.participants:
                logger.warning(f"Participant {participant_id} not in consensus")
                return False
            
            if vote_decision not in ['approve', 'reject', 'abstain']:
                logger.warning(f"Invalid vote decision: {vote_decision}")
                return False
            
            # Record vote
            self.active_consensus.votes[participant_id] = vote_decision
            
            logger.info(f"Vote recorded: {participant_id} -> {vote_decision}")
            return True
            
        except Exception as e:
            logger.exception(f"Error submitting vote: {e}")
            return False
    
    async def get_consensus_history(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get consensus history"""
        try:
            events = await self.consensus_repo.get_consensus_events(limit=limit, offset=offset)
            
            return [
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "target_id": event.target_id,
                    "round_number": event.round_number,
                    "result": event.result,
                    "participants_count": len(event.participants),
                    "approval_percentage": event.approval_percentage,
                    "started_at": event.started_at.isoformat(),
                    "completed_at": event.completed_at.isoformat() if event.completed_at else None
                }
                for event in events
            ]
            
        except Exception as e:
            logger.exception(f"Error getting consensus history: {e}")
            return []
```

### Main Application (api/app/main.py)

```python
"""
Blockchain Core API Main Application

This is the primary entry point for the lucid_blocks blockchain API.
CRITICAL: This module contains NO TRON code.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
import uvicorn

from app.config import get_settings
from app.middleware.auth import AuthMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.logging import LoggingMiddleware
from app.routers import (
    blockchain,
    blocks,
    transactions,
    anchoring,
    consensus,
    merkle
)
from app.database.connection import init_database
from app.utils.logging import setup_logging
from app.models.common import ErrorResponse, ErrorDetail
import uuid
from datetime import datetime

# Global settings
settings = get_settings()

# Setup logging
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting lucid_blocks blockchain API")
    await init_database()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down lucid_blocks blockchain API")

# Create FastAPI application
app = FastAPI(
    title="Lucid Blockchain Core (lucid_blocks)",
    description="Core blockchain operations for the Lucid blockchain system - COMPLETELY ISOLATED from TRON",
    version=settings.API_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan
)

# Add middleware (order matters!)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)

# Include routers
app.include_router(blockchain.router, prefix="/api/v1/chain", tags=["Blockchain"])
app.include_router(blocks.router, prefix="/api/v1/blocks", tags=["Blocks"])
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["Transactions"])
app.include_router(anchoring.router, prefix="/api/v1/anchoring", tags=["Anchoring"])
app.include_router(consensus.router, prefix="/api/v1/consensus", tags=["Consensus"])
app.include_router(merkle.router, prefix="/api/v1/merkle", tags=["Merkle"])

# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    
    error_detail = ErrorDetail(
        code="LUCID_ERR_1001",
        message="Invalid request data",
        details={"validation_errors": exc.errors()},
        request_id=request_id,
        timestamp=datetime.utcnow(),
        service="lucid-blocks",
        version="v1"
    )
    
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(error=error_detail).dict()
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    
    # Map HTTP status codes to Lucid error codes
    error_code_map = {
        400: "LUCID_ERR_4001",
        401: "LUCID_ERR_2001",
        403: "LUCID_ERR_2004",
        404: "LUCID_ERR_4001",
        409: "LUCID_ERR_4002",
        422: "LUCID_ERR_1001",
        429: "LUCID_ERR_3001",
        500: "LUCID_ERR_5001",
        503: "LUCID_ERR_5008"
    }
    
    error_code = error_code_map.get(exc.status_code, "LUCID_ERR_5001")
    
    error_detail = ErrorDetail(
        code=error_code,
        message=exc.detail,
        request_id=request_id,
        timestamp=datetime.utcnow(),
        service="lucid-blocks",
        version="v1"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=error_detail).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    logger.exception(f"Unhandled exception: {exc}")
    
    error_detail = ErrorDetail(
        code="LUCID_ERR_5001",
        message="Internal server error",
        request_id=request_id,
        timestamp=datetime.utcnow(),
        service="lucid-blocks",
        version="v1"
    )
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error=error_detail).dict()
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.BLOCKCHAIN_ENGINE_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
```

## Distroless Container Configuration

### Blockchain Engine Dockerfile

```dockerfile
# Multi-stage build for distroless container
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy source code
COPY core/ ./core/
COPY api/ ./api/
COPY scripts/ ./scripts/

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Production stage - Distroless
FROM gcr.io/distroless/python3-debian12

# Set labels
LABEL maintainer="Lucid Development Team"
LABEL description="Lucid Blockchain Engine (lucid_blocks) - Distroless Container"
LABEL version="1.0.0"

# Copy Python packages from builder
COPY --from=builder /root/.local /home/app/.local

# Copy application code
COPY --from=builder /app/core /app/core
COPY --from=builder /app/api /app/api
COPY --from=builder /app/scripts /app/scripts

# Set working directory
WORKDIR /app

# Set Python path
ENV PYTHONPATH=/app
ENV PATH=/home/app/.local/bin:$PATH

# Create app user (distroless has no useradd)
USER 65532:65532

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8084/api/v1/chain/status')"]

# Expose ports
EXPOSE 8084

# Start application
CMD ["python", "-m", "api.app.main"]
```

## Naming Conventions

### Service Naming

```python
# Service names follow the pattern: lucid-{cluster}-{service}
SERVICE_NAMES = {
    "blockchain_engine": "lucid-blocks-engine",
    "session_anchoring": "lucid-session-anchoring", 
    "block_manager": "lucid-block-manager",
    "data_chain": "lucid-data-chain"
}

# Container names follow the pattern: lucid-{cluster}-{service}
CONTAINER_NAMES = {
    "blockchain_engine": "lucid-lucid-blocks-engine",
    "session_anchoring": "lucid-session-anchoring",
    "block_manager": "lucid-block-manager", 
    "data_chain": "lucid-data-chain"
}

# Database collections use snake_case
COLLECTION_NAMES = {
    "blocks": "blocks",
    "transactions": "transactions", 
    "session_anchorings": "session_anchorings",
    "consensus_events": "consensus_events",
    "merkle_trees": "merkle_trees",
    "blockchain_state": "blockchain_state"
}
```

### Variable Naming

```python
# Python variables use snake_case
block_height = 12345
merkle_root = "abc123..."
consensus_participants = ["node1", "node2", "node3"]

# Database fields use snake_case
block_data = {
    "block_id": "block_12345_1641234567",
    "height": 12345,
    "hash": "abc123...",
    "previous_hash": "def456...",
    "merkle_root": "ghi789...",
    "timestamp": "2025-01-10T19:08:00Z",
    "transaction_count": 150
}

# API endpoints use kebab-case
API_ENDPOINTS = {
    "/api/v1/chain/info": "blockchain_information",
    "/api/v1/blocks/latest": "latest_block",
    "/api/v1/session-anchoring": "session_anchoring",
    "/api/v1/consensus/status": "consensus_status"
}

# Error codes use UPPER_CASE with underscores
ERROR_CODES = {
    "LUCID_ERR_4001": "Block not found",
    "LUCID_ERR_5001": "Transaction not found", 
    "LUCID_ERR_6001": "Session anchoring not found",
    "LUCID_ERR_7001": "Consensus participant not authorized"
}
```

## TRON Isolation Enforcement

### Code Review Checklist

```python
# TRON Isolation Code Review Checklist
TRON_ISOLATION_CHECKLIST = [
    "No TRON network imports",
    "No TRON wallet operations", 
    "No USDT-TRC20 transaction handling",
    "No TRON payout processing",
    "No TRON contract interactions",
    "No TRON RPC calls",
    "No TRON address validation",
    "No TRON signature verification",
    "No TRON balance queries",
    "No TRON transaction broadcasting"
]

# Prohibited imports (should never appear in blockchain core)
PROHIBITED_IMPORTS = [
    "tronpy",
    "tronapi", 
    "tron_client",
    "tron_wallet",
    "tron_node",
    "tron_network",
    "tron_rpc",
    "tron_contract"
]

# Allowed blockchain operations (lucid_blocks only)
ALLOWED_OPERATIONS = [
    "block_creation",
    "block_validation", 
    "transaction_processing",
    "consensus_operations",
    "merkle_tree_building",
    "session_anchoring",
    "blockchain_state_management"
]
```

### Dependency Scanning

```python
# requirements.txt for blockchain core (NO TRON dependencies)
BLOCKCHAIN_CORE_DEPENDENCIES = [
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
    "motor>=3.3.0",  # MongoDB async driver
    "pydantic>=2.4.0",
    "python-multipart>=0.0.6",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "redis>=5.0.0",
    "cryptography>=41.0.0",
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0"
]

# Prohibited dependencies (should never appear)
PROHIBITED_DEPENDENCIES = [
    "tronpy",
    "tronapi",
    "tron-client",
    "tron-wallet", 
    "tron-node",
    "tron-network"
]
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
