# Path: blockchain/core/consensus_engine.py
# Lucid Blockchain Core - Consensus Engine
# Implements PoOT (Proof of Operational Tasks) consensus mechanism
# Based on BUILD_REQUIREMENTS_GUIDE.md Step 11 and blockchain cluster specifications

from __future__ import annotations

import asyncio
import logging
import hashlib
import struct
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase
import blake3

from .models import (
    ConsensusState, TaskProofType, TaskProof, WorkCreditsTally, 
    LeaderSchedule, Block, Transaction, generate_session_id
)

logger = logging.getLogger(__name__)

# Consensus parameters from BUILD_REQUIREMENTS_GUIDE.md
SLOT_DURATION_SEC = 120  # Fixed 2-minute slots
SLOT_TIMEOUT_MS = 5000   # 5-second leader timeout
COOLDOWN_SLOTS = 16      # 16-slot cooldown period
LEADER_WINDOW_DAYS = 7   # 7-day PoOT calculation window
D_MIN = 0.2             # Minimum density threshold
BASE_MB_PER_SESSION = 5  # 5MB base unit for work credits

class ConsensusPhase(Enum):
    """Consensus phases for PoOT algorithm"""
    LEADER_SELECTION = "leader_selection"
    BLOCK_PROPOSAL = "block_proposal"
    BLOCK_VALIDATION = "block_validation"
    BLOCK_COMMITMENT = "block_commitment"
    FINALIZATION = "finalization"

@dataclass
class ConsensusRound:
    """Represents a single consensus round"""
    slot: int
    phase: ConsensusPhase
    leader: str
    fallbacks: List[str]
    proposed_block: Optional[Block] = None
    votes: Dict[str, bool] = field(default_factory=dict)
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deadline: Optional[datetime] = None
    result: Optional[str] = None

class ConsensusEngine:
    """
    PoOT (Proof of Operational Tasks) Consensus Engine
    
    Implements the consensus mechanism for the lucid_blocks blockchain:
    - Work credits calculation from operational tasks
    - Leader selection based on work credits ranking
    - Block proposal and validation
    - Fallback mechanisms for failed leaders
    - Cooldown periods to prevent centralization
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, node_id: str):
        self.db = db
        self.node_id = node_id
        self.current_slot = 0
        self.current_round: Optional[ConsensusRound] = None
        self.consensus_state = ConsensusState.IDLE
        self.running = False
        
        # Consensus tracking
        self.leader_schedule: Dict[int, LeaderSchedule] = {}
        self.work_credits_cache: Dict[str, WorkCreditsTally] = {}
        self.cooldown_entities: Set[str] = set()
        
        # Performance metrics
        self.metrics = {
            "blocks_produced": 0,
            "consensus_rounds": 0,
            "failed_rounds": 0,
            "average_round_time": 0.0
        }
        
        logger.info(f"Consensus engine initialized for node: {node_id}")
    
    async def start(self) -> bool:
        """Start the consensus engine"""
        try:
            self.running = True
            
            # Setup MongoDB indexes
            await self._setup_mongodb_indexes()
            
            # Initialize current slot based on genesis time
            await self._initialize_slot_timing()
            
            # Start consensus loop
            asyncio.create_task(self._consensus_loop())
            
            logger.info("Consensus engine started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start consensus engine: {e}")
            return False
    
    async def stop(self):
        """Stop the consensus engine"""
        try:
            self.running = False
            self.consensus_state = ConsensusState.IDLE
            logger.info("Consensus engine stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop consensus engine: {e}")
    
    async def _setup_mongodb_indexes(self):
        """Setup MongoDB indexes for consensus collections"""
        try:
            # Task proofs collection - for work credits calculation
            await self.db["task_proofs"].create_index([("slot", 1), ("node_id", 1)])
            await self.db["task_proofs"].create_index([("type", 1)])
            await self.db["task_proofs"].create_index([("timestamp", -1)])
            
            # Work credits tally collection
            await self.db["work_credits"].create_index([("epoch", 1), ("entity_id", 1)])
            await self.db["work_credits"].create_index([("live_score", -1)])
            await self.db["work_credits"].create_index([("rank", 1)])
            
            # Leader schedule collection
            await self.db["leader_schedule"].create_index([("slot", 1)])
            await self.db["leader_schedule"].create_index([("primary", 1)])
            
            # Consensus rounds collection
            await self.db["consensus_rounds"].create_index([("slot", 1)])
            await self.db["consensus_rounds"].create_index([("phase", 1)])
            
            # Blocks collection
            await self.db["blocks"].create_index([("height", 1)])
            await self.db["blocks"].create_index([("hash", 1)])
            await self.db["blocks"].create_index([("timestamp", -1)])
            
            logger.info("Consensus MongoDB indexes created")
            
        except Exception as e:
            logger.error(f"Failed to setup MongoDB indexes: {e}")
    
    async def _initialize_slot_timing(self):
        """Initialize slot timing based on genesis block"""
        try:
            # Get genesis block to establish timing
            genesis_block = await self.db["blocks"].find_one({"height": 0})
            
            if genesis_block:
                genesis_time = genesis_block["timestamp"]
                current_time = datetime.now(timezone.utc)
                elapsed_seconds = (current_time - genesis_time).total_seconds()
                self.current_slot = int(elapsed_seconds // SLOT_DURATION_SEC)
            else:
                # No genesis block yet, start from slot 0
                self.current_slot = 0
            
            logger.info(f"Consensus initialized at slot: {self.current_slot}")
            
        except Exception as e:
            logger.error(f"Failed to initialize slot timing: {e}")
            self.current_slot = 0
    
    async def _consensus_loop(self):
        """Main consensus loop - runs every slot"""
        while self.running:
            try:
                slot_start_time = datetime.now(timezone.utc)
                
                # Start new consensus round
                await self._start_consensus_round(self.current_slot)
                
                # Wait for slot duration
                await asyncio.sleep(SLOT_DURATION_SEC)
                
                # Finalize round
                await self._finalize_consensus_round()
                
                # Move to next slot
                self.current_slot += 1
                
                # Update metrics
                round_time = (datetime.now(timezone.utc) - slot_start_time).total_seconds()
                self._update_metrics(round_time)
                
            except Exception as e:
                logger.error(f"Consensus loop error at slot {self.current_slot}: {e}")
                await asyncio.sleep(SLOT_DURATION_SEC)
                self.current_slot += 1
    
    async def _start_consensus_round(self, slot: int):
        """Start a new consensus round for the given slot"""
        try:
            # Calculate work credits for current epoch
            current_epoch = slot // (24 * 60 * 60 // SLOT_DURATION_SEC)  # Daily epochs
            await self._calculate_work_credits(current_epoch)
            
            # Select leader for this slot
            leader_schedule = await self._select_leader(slot)
            
            # Create consensus round
            self.current_round = ConsensusRound(
                slot=slot,
                phase=ConsensusPhase.LEADER_SELECTION,
                leader=leader_schedule.primary,
                fallbacks=leader_schedule.fallbacks,
                deadline=datetime.now(timezone.utc) + timedelta(milliseconds=SLOT_TIMEOUT_MS)
            )
            
            # Store leader schedule
            await self.db["leader_schedule"].replace_one(
                {"slot": slot},
                leader_schedule.to_dict(),
                upsert=True
            )
            
            # If we are the leader, propose a block
            if leader_schedule.primary == self.node_id:
                await self._propose_block()
            
            # Store consensus round
            await self.db["consensus_rounds"].replace_one(
                {"slot": slot},
                self._round_to_dict(self.current_round),
                upsert=True
            )
            
            logger.info(f"Consensus round started for slot {slot}, leader: {leader_schedule.primary}")
            
        except Exception as e:
            logger.error(f"Failed to start consensus round: {e}")
    
    async def _calculate_work_credits(self, epoch: int) -> List[WorkCreditsTally]:
        """Calculate work credits for all entities in the epoch"""
        try:
            # Get work proofs from the sliding window
            window_start = datetime.now(timezone.utc) - timedelta(days=LEADER_WINDOW_DAYS)
            
            proofs_cursor = self.db["task_proofs"].find({
                "timestamp": {"$gte": window_start}
            })
            
            # Aggregate credits by entity
            entity_credits: Dict[str, Dict[str, Any]] = {}
            
            async for proof_doc in proofs_cursor:
                entity_id = proof_doc["node_id"]
                proof_type = proof_doc["type"]
                value = proof_doc["value"]
                
                if entity_id not in entity_credits:
                    entity_credits[entity_id] = {
                        "relay_bandwidth": 0,
                        "storage_proofs": 0,
                        "validation_signatures": 0,
                        "uptime_score": 0.0
                    }
                
                # Calculate credits based on proof type
                if proof_type == TaskProofType.RELAY_BANDWIDTH.value:
                    # W_t = max(S_t, ceil(B_t / BASE_MB_PER_SESSION))
                    bandwidth_mb = value.get("bandwidth_mb", 0)
                    sessions = value.get("sessions_relayed", 0)
                    credits = max(sessions, int(bandwidth_mb / BASE_MB_PER_SESSION))
                    entity_credits[entity_id]["relay_bandwidth"] += credits
                    
                elif proof_type == TaskProofType.STORAGE_AVAILABILITY.value:
                    storage_gb = value.get("storage_gb", 0)
                    uptime_hours = value.get("uptime_hours", 0)
                    credits = int(storage_gb * uptime_hours / 24)
                    entity_credits[entity_id]["storage_proofs"] += credits
                    
                elif proof_type == TaskProofType.VALIDATION_SIGNATURE.value:
                    signatures_count = value.get("signatures_count", 0)
                    entity_credits[entity_id]["validation_signatures"] += signatures_count
                    
                elif proof_type == TaskProofType.UPTIME_BEACON.value:
                    uptime_hours = value.get("uptime_hours", 0)
                    entity_credits[entity_id]["uptime_score"] = min(uptime_hours / (LEADER_WINDOW_DAYS * 24), 1.0)
            
            # Create work tally objects
            tallies = []
            for entity_id, credits in entity_credits.items():
                total_credits = (
                    credits["relay_bandwidth"] +
                    credits["storage_proofs"] +
                    credits["validation_signatures"]
                )
                
                # Apply uptime multiplier
                live_score = total_credits * credits["uptime_score"]
                
                tally = WorkCreditsTally(
                    epoch=epoch,
                    entity_id=entity_id,
                    credits_total=total_credits,
                    relay_bandwidth=credits["relay_bandwidth"],
                    storage_proofs=credits["storage_proofs"],
                    validation_signatures=credits["validation_signatures"],
                    uptime_score=credits["uptime_score"],
                    live_score=live_score,
                    rank=0  # Will be set after sorting
                )
                tallies.append(tally)
            
            # Sort by live score and assign ranks
            tallies.sort(key=lambda x: x.live_score, reverse=True)
            for i, tally in enumerate(tallies):
                tally.rank = i + 1
            
            # Store tallies in MongoDB and cache
            for tally in tallies:
                await self.db["work_credits"].replace_one(
                    {"epoch": epoch, "entity_id": tally.entity_id},
                    tally.to_dict(),
                    upsert=True
                )
                self.work_credits_cache[tally.entity_id] = tally
            
            logger.info(f"Work credits calculated for epoch {epoch}: {len(tallies)} entities")
            return tallies
            
        except Exception as e:
            logger.error(f"Failed to calculate work credits: {e}")
            return []
    
    async def _select_leader(self, slot: int) -> LeaderSchedule:
        """Select block leader for the given slot"""
        try:
            # Get current work credits rankings
            current_epoch = slot // (24 * 60 * 60 // SLOT_DURATION_SEC)
            tallies_cursor = self.db["work_credits"].find({"epoch": current_epoch}).sort("rank", 1)
            
            # Update cooldown entities
            await self._update_cooldown_entities(slot)
            
            # Find eligible entities (not in cooldown)
            eligible_entities = []
            async for tally_doc in tallies_cursor:
                entity_id = tally_doc["entity_id"]
                if entity_id not in self.cooldown_entities:
                    eligible_entities.append(entity_id)
            
            # Select primary leader and fallbacks
            if eligible_entities:
                primary = eligible_entities[0]
                fallbacks = eligible_entities[1:6] if len(eligible_entities) > 1 else []
            else:
                # Emergency fallback
                primary = "emergency_fallback"
                fallbacks = ["emergency_fallback"]
            
            # Create leader schedule
            schedule = LeaderSchedule(
                slot=slot,
                primary=primary,
                fallbacks=fallbacks,
                deadline=datetime.now(timezone.utc) + timedelta(milliseconds=SLOT_TIMEOUT_MS)
            )
            
            logger.info(f"Leader selected for slot {slot}: {primary} (fallbacks: {fallbacks})")
            return schedule
            
        except Exception as e:
            logger.error(f"Failed to select leader for slot {slot}: {e}")
            # Return emergency fallback
            return LeaderSchedule(
                slot=slot,
                primary="emergency_fallback",
                fallbacks=["emergency_fallback"],
                deadline=datetime.now(timezone.utc) + timedelta(milliseconds=SLOT_TIMEOUT_MS)
            )
    
    async def _update_cooldown_entities(self, slot: int):
        """Update the set of entities in cooldown period"""
        try:
            cooldown_start_slot = slot - COOLDOWN_SLOTS
            
            # Get entities that produced blocks in cooldown period
            cooldown_cursor = self.db["leader_schedule"].find({
                "slot": {"$gte": cooldown_start_slot, "$lt": slot},
                "result.winner": {"$exists": True}
            })
            
            self.cooldown_entities.clear()
            async for schedule_doc in cooldown_cursor:
                if "result" in schedule_doc and "winner" in schedule_doc["result"]:
                    self.cooldown_entities.add(schedule_doc["result"]["winner"])
            
            logger.debug(f"Cooldown entities for slot {slot}: {self.cooldown_entities}")
            
        except Exception as e:
            logger.error(f"Failed to update cooldown entities: {e}")
    
    async def _propose_block(self):
        """Propose a new block as the selected leader"""
        try:
            if not self.current_round:
                return
            
            # Get pending transactions
            pending_txs = await self._get_pending_transactions()
            
            # Get previous block
            prev_block = await self.db["blocks"].find_one({}, sort=[("height", -1)])
            prev_hash = prev_block["hash"] if prev_block else "0" * 64
            height = (prev_block["height"] + 1) if prev_block else 0
            
            # Create new block
            block = Block(
                height=height,
                previous_hash=prev_hash,
                timestamp=datetime.now(timezone.utc),
                transactions=pending_txs[:1000],  # Max 1000 transactions per block
                merkle_root=self._calculate_merkle_root(pending_txs[:1000]),
                producer=self.node_id,
                signature=""  # Will be set after signing
            )
            
            # Sign the block
            block.signature = await self._sign_block(block)
            block.hash = self._calculate_block_hash(block)
            
            # Update consensus round
            self.current_round.phase = ConsensusPhase.BLOCK_PROPOSAL
            self.current_round.proposed_block = block
            
            # Broadcast block proposal
            await self._broadcast_block_proposal(block)
            
            logger.info(f"Block proposed for slot {self.current_round.slot}, height {height}")
            
        except Exception as e:
            logger.error(f"Failed to propose block: {e}")
    
    async def _get_pending_transactions(self) -> List[Transaction]:
        """Get pending transactions from mempool"""
        try:
            # Get transactions from mempool
            tx_cursor = self.db["mempool"].find({"status": "pending"}).sort("timestamp", 1)
            
            transactions = []
            async for tx_doc in tx_cursor:
                # Convert to Transaction object
                tx = Transaction(
                    id=tx_doc["id"],
                    from_address=tx_doc["from_address"],
                    to_address=tx_doc["to_address"],
                    value=tx_doc["value"],
                    data=tx_doc.get("data", ""),
                    timestamp=tx_doc["timestamp"],
                    signature=tx_doc["signature"]
                )
                transactions.append(tx)
                
                # Limit to reasonable number
                if len(transactions) >= 1000:
                    break
            
            return transactions
            
        except Exception as e:
            logger.error(f"Failed to get pending transactions: {e}")
            return []
    
    def _calculate_merkle_root(self, transactions: List[Transaction]) -> str:
        """Calculate Merkle root for transactions"""
        if not transactions:
            return "0" * 64
        
        # Create leaf hashes
        leaves = [blake3.blake3(tx.id.encode()).hexdigest() for tx in transactions]
        
        # Build Merkle tree
        while len(leaves) > 1:
            next_level = []
            for i in range(0, len(leaves), 2):
                left = leaves[i]
                right = leaves[i + 1] if i + 1 < len(leaves) else left
                combined = blake3.blake3((left + right).encode()).hexdigest()
                next_level.append(combined)
            leaves = next_level
        
        return leaves[0] if leaves else "0" * 64
    
    async def _sign_block(self, block: Block) -> str:
        """Sign a block with the node's private key"""
        try:
            # Create block hash for signing
            block_data = f"{block.height}{block.previous_hash}{block.timestamp.isoformat()}{block.merkle_root}{block.producer}"
            block_hash = blake3.blake3(block_data.encode()).hexdigest()
            
            # For now, return a mock signature
            # In production, this would use the node's private key
            signature = blake3.blake3(f"{self.node_id}:{block_hash}".encode()).hexdigest()
            
            return signature
            
        except Exception as e:
            logger.error(f"Failed to sign block: {e}")
            return ""
    
    def _calculate_block_hash(self, block: Block) -> str:
        """Calculate the hash of a block"""
        block_data = f"{block.height}{block.previous_hash}{block.timestamp.isoformat()}{block.merkle_root}{block.producer}{block.signature}"
        return blake3.blake3(block_data.encode()).hexdigest()
    
    async def _broadcast_block_proposal(self, block: Block):
        """Broadcast block proposal to network"""
        try:
            # Store proposed block
            await self.db["proposed_blocks"].insert_one({
                "slot": self.current_round.slot,
                "block": block.to_dict(),
                "proposer": self.node_id,
                "timestamp": datetime.now(timezone.utc)
            })
            
            # In a real implementation, this would broadcast to network peers
            logger.info(f"Block proposal broadcasted for slot {self.current_round.slot}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast block proposal: {e}")
    
    async def _finalize_consensus_round(self):
        """Finalize the current consensus round"""
        try:
            if not self.current_round:
                return
            
            # Check if we have a valid block
            if self.current_round.proposed_block:
                # Validate the proposed block
                is_valid = await self._validate_block(self.current_round.proposed_block)
                
                if is_valid:
                    # Accept the block
                    await self._accept_block(self.current_round.proposed_block)
                    self.current_round.result = "success"
                    self.metrics["blocks_produced"] += 1
                else:
                    # Reject the block
                    self.current_round.result = "invalid_block"
                    self.metrics["failed_rounds"] += 1
            else:
                # No block proposed
                self.current_round.result = "no_proposal"
                self.metrics["failed_rounds"] += 1
            
            # Record the result
            await self._record_consensus_result()
            
            # Update consensus state
            self.consensus_state = ConsensusState.IDLE
            self.current_round = None
            self.metrics["consensus_rounds"] += 1
            
        except Exception as e:
            logger.error(f"Failed to finalize consensus round: {e}")
    
    async def _validate_block(self, block: Block) -> bool:
        """Validate a proposed block"""
        try:
            # Check block structure
            if not block.hash or not block.signature:
                return False
            
            # Check height sequence
            prev_block = await self.db["blocks"].find_one({}, sort=[("height", -1)])
            expected_height = (prev_block["height"] + 1) if prev_block else 0
            if block.height != expected_height:
                return False
            
            # Check previous hash
            expected_prev_hash = prev_block["hash"] if prev_block else "0" * 64
            if block.previous_hash != expected_prev_hash:
                return False
            
            # Validate transactions
            for tx in block.transactions:
                if not await self._validate_transaction(tx):
                    return False
            
            # Verify Merkle root
            calculated_root = self._calculate_merkle_root(block.transactions)
            if block.merkle_root != calculated_root:
                return False
            
            # Verify block signature
            if not await self._verify_block_signature(block):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate block: {e}")
            return False
    
    async def _validate_transaction(self, tx: Transaction) -> bool:
        """Validate a transaction"""
        try:
            # Basic validation
            if not tx.id or not tx.signature:
                return False
            
            # Check if transaction already exists
            existing_tx = await self.db["transactions"].find_one({"id": tx.id})
            if existing_tx:
                return False
            
            # Verify transaction signature
            # In production, this would verify the cryptographic signature
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate transaction: {e}")
            return False
    
    async def _verify_block_signature(self, block: Block) -> bool:
        """Verify the signature of a block"""
        try:
            # In production, this would verify the cryptographic signature
            # For now, just check that signature exists
            return bool(block.signature)
            
        except Exception as e:
            logger.error(f"Failed to verify block signature: {e}")
            return False
    
    async def _accept_block(self, block: Block):
        """Accept a valid block into the blockchain"""
        try:
            # Store block in blockchain
            await self.db["blocks"].insert_one(block.to_dict())
            
            # Move transactions from mempool to confirmed
            for tx in block.transactions:
                await self.db["transactions"].insert_one(tx.to_dict())
                await self.db["mempool"].delete_one({"id": tx.id})
            
            logger.info(f"Block accepted: height {block.height}, hash {block.hash}")
            
        except Exception as e:
            logger.error(f"Failed to accept block: {e}")
    
    async def _record_consensus_result(self):
        """Record the result of the consensus round"""
        try:
            if not self.current_round:
                return
            
            # Update leader schedule with result
            await self.db["leader_schedule"].update_one(
                {"slot": self.current_round.slot},
                {"$set": {"result": {
                    "winner": self.current_round.leader if self.current_round.result == "success" else None,
                    "reason": self.current_round.result,
                    "timestamp": datetime.now(timezone.utc)
                }}}
            )
            
            # Update consensus round record
            await self.db["consensus_rounds"].update_one(
                {"slot": self.current_round.slot},
                {"$set": self._round_to_dict(self.current_round)}
            )
            
            # Add to cooldown if successful
            if self.current_round.result == "success":
                self.cooldown_entities.add(self.current_round.leader)
            
            logger.info(f"Consensus result recorded for slot {self.current_round.slot}: {self.current_round.result}")
            
        except Exception as e:
            logger.error(f"Failed to record consensus result: {e}")
    
    def _round_to_dict(self, round_obj: ConsensusRound) -> Dict[str, Any]:
        """Convert ConsensusRound to dictionary"""
        return {
            "slot": round_obj.slot,
            "phase": round_obj.phase.value,
            "leader": round_obj.leader,
            "fallbacks": round_obj.fallbacks,
            "proposed_block": round_obj.proposed_block.to_dict() if round_obj.proposed_block else None,
            "votes": round_obj.votes,
            "start_time": round_obj.start_time,
            "deadline": round_obj.deadline,
            "result": round_obj.result
        }
    
    def _update_metrics(self, round_time: float):
        """Update consensus performance metrics"""
        try:
            # Update average round time
            total_rounds = self.metrics["consensus_rounds"]
            if total_rounds > 0:
                current_avg = self.metrics["average_round_time"]
                self.metrics["average_round_time"] = (current_avg * total_rounds + round_time) / (total_rounds + 1)
            else:
                self.metrics["average_round_time"] = round_time
            
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")
    
    async def submit_work_proof(self, proof: TaskProof) -> bool:
        """Submit a work proof for PoOT consensus"""
        try:
            # Store proof in database
            await self.db["task_proofs"].insert_one(proof.to_dict())
            
            logger.info(f"Work proof submitted: {proof.node_id} - {proof.type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit work proof: {e}")
            return False
    
    async def get_consensus_status(self) -> Dict[str, Any]:
        """Get current consensus status"""
        try:
            return {
                "current_slot": self.current_slot,
                "consensus_state": self.consensus_state.value,
                "current_round": self._round_to_dict(self.current_round) if self.current_round else None,
                "metrics": self.metrics,
                "cooldown_entities": list(self.cooldown_entities)
            }
            
        except Exception as e:
            logger.error(f"Failed to get consensus status: {e}")
            return {}
    
    async def get_leader_schedule(self, slot: int) -> Optional[LeaderSchedule]:
        """Get leader schedule for a specific slot"""
        try:
            schedule_doc = await self.db["leader_schedule"].find_one({"slot": slot})
            if schedule_doc:
                return LeaderSchedule(
                    slot=schedule_doc["slot"],
                    primary=schedule_doc["primary"],
                    fallbacks=schedule_doc["fallbacks"],
                    deadline=schedule_doc.get("deadline")
                )
            return None
            
        except Exception as e:
            logger.error(f"Failed to get leader schedule: {e}")
            return None
    
    async def get_work_credits(self, epoch: int) -> List[WorkCreditsTally]:
        """Get work credits for a specific epoch"""
        try:
            tallies = []
            cursor = self.db["work_credits"].find({"epoch": epoch}).sort("rank", 1)
            
            async for tally_doc in cursor:
                tally = WorkCreditsTally(
                    epoch=tally_doc["epoch"],
                    entity_id=tally_doc["entity_id"],
                    credits_total=tally_doc["credits_total"],
                    relay_bandwidth=tally_doc["relay_bandwidth"],
                    storage_proofs=tally_doc["storage_proofs"],
                    validation_signatures=tally_doc["validation_signatures"],
                    uptime_score=tally_doc["uptime_score"],
                    live_score=tally_doc["live_score"],
                    rank=tally_doc["rank"]
                )
                tallies.append(tally)
            
            return tallies
            
        except Exception as e:
            logger.error(f"Failed to get work credits: {e}")
            return []
