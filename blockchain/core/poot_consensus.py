# Path: blockchain/core/poot_consensus.py
"""
PoOT (Proof of Operational Tasks) Consensus Engine

Implements the complete PoOT consensus mechanism for Lucid blockchain
based on Spec-1b requirements.

Features:
- Work credits calculation and tallying
- Leader selection with cooldown periods
- Block production and validation
- Slot progression and timing
- Consensus state management
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
import time

from motor.motor_asyncio import AsyncIOMotorDatabase

from .models import TaskProof, TaskProofType, WorkCreditsTally, LeaderSchedule, ConsensusState
from .work_credits import WorkCreditsEngine, LEADER_WINDOW_DAYS, BASE_MB_PER_SESSION, D_MIN
from .leader_selection import LeaderSelectionEngine, SLOT_DURATION_SEC, SLOT_TIMEOUT_MS, COOLDOWN_SLOTS

logger = logging.getLogger(__name__)

# =============================================================================
# CONSENSUS PARAMETERS
# =============================================================================

CONSENSUS_VERSION = "1.0.0"
MAX_FALLBACK_ATTEMPTS = 3
EPOCH_DURATION_HOURS = 24  # Daily epochs for work credits calculation


class PoOTConsensusEngine:
    """
    Complete PoOT consensus engine.
    
    Orchestrates work credits calculation, leader selection, and block production
    according to Spec-1b requirements.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        
        # Initialize sub-engines
        self.work_credits_engine = WorkCreditsEngine(db)
        self.leader_selection_engine = LeaderSelectionEngine(db)
        
        # Consensus state
        self.current_epoch = 0
        self.current_slot = 0
        self.consensus_state = ConsensusState.CALCULATING
        self.last_block_time: Optional[datetime] = None
        
        # Callbacks for block production
        self.block_producer: Optional[Callable] = None
        self.block_validator: Optional[Callable] = None
        
        logger.info("PoOT consensus engine initialized")
    
    async def start_consensus(self):
        """Start the consensus engine"""
        try:
            # Initialize consensus state
            await self._initialize_consensus_state()
            
            # Start background tasks
            asyncio.create_task(self._epoch_timer())
            asyncio.create_task(self._slot_timer())
            
            logger.info("PoOT consensus engine started")
            
        except Exception as e:
            logger.error(f"Failed to start consensus engine: {e}")
            raise
    
    async def stop_consensus(self):
        """Stop the consensus engine"""
        try:
            # Cancel background tasks
            tasks = [task for task in asyncio.all_tasks() 
                    if task.get_name().startswith("poot_consensus")]
            
            for task in tasks:
                task.cancel()
            
            # Wait for tasks to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            logger.info("PoOT consensus engine stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop consensus engine: {e}")
    
    async def submit_task_proof(self, proof: TaskProof) -> bool:
        """Submit task proof for work credits"""
        return await self.work_credits_engine.submit_task_proof(proof)
    
    async def get_current_leader(self) -> Optional[str]:
        """Get current slot's leader"""
        try:
            schedule = await self.leader_selection_engine.select_leader(self.current_slot)
            return schedule.primary
        except Exception as e:
            logger.error(f"Failed to get current leader: {e}")
            return None
    
    async def _initialize_consensus_state(self):
        """Initialize consensus state from database"""
        try:
            # Get latest consensus state
            state_doc = await self.db["consensus_state"].find_one(
                {"_id": "current"}
            )
            
            if state_doc:
                self.current_epoch = state_doc.get("epoch", 0)
                self.current_slot = state_doc.get("slot", 0)
                self.consensus_state = ConsensusState(state_doc.get("state", "calculating"))
                self.last_block_time = state_doc.get("last_block_time")
            else:
                # Initialize with current time
                now = datetime.now(timezone.utc)
                self.current_epoch = self._calculate_epoch_from_time(now)
                self.current_slot = self._calculate_slot_from_time(now)
                self.consensus_state = ConsensusState.CALCULATING
                
                # Store initial state
                await self._save_consensus_state()
            
            logger.info(f"Consensus state initialized: epoch={self.current_epoch}, slot={self.current_slot}")
            
        except Exception as e:
            logger.error(f"Failed to initialize consensus state: {e}")
            raise
    
    async def _epoch_timer(self):
        """Epoch timer for work credits calculation"""
        while True:
            try:
                await asyncio.sleep(EPOCH_DURATION_HOURS * 3600)  # 24 hours
                
                # Calculate work credits for new epoch
                new_epoch = self.current_epoch + 1
                await self._calculate_epoch_work_credits(new_epoch)
                
                # Update current epoch
                self.current_epoch = new_epoch
                await self._save_consensus_state()
                
                logger.info(f"Epoch {new_epoch} completed, work credits calculated")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Epoch timer error: {e}")
                await asyncio.sleep(60)  # Wait before retry
    
    async def _slot_timer(self):
        """Slot timer for consensus progression"""
        while True:
            try:
                # Select leader for current slot
                await self._process_slot()
                
                # Wait for slot duration
                await asyncio.sleep(SLOT_DURATION_SEC)
                
                # Move to next slot
                self.current_slot += 1
                await self._save_consensus_state()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Slot timer error: {e}")
                await asyncio.sleep(5)  # Short wait before retry
    
    async def _process_slot(self):
        """Process current consensus slot"""
        try:
            self.consensus_state = ConsensusState.LEADER_SELECTED
            
            # Select leader for slot
            schedule = await self.leader_selection_engine.select_leader(self.current_slot)
            
            if schedule.primary == "fallback_node":
                # No eligible leader, mark slot as missed
                await self._handle_missed_slot()
                return
            
            # Attempt block production
            block_produced = await self._attempt_block_production(schedule)
            
            if block_produced:
                self.consensus_state = ConsensusState.BLOCK_CONFIRMED
                self.last_block_time = datetime.now(timezone.utc)
                
                # Record successful block
                await self.leader_selection_engine.record_block_result(
                    self.current_slot, schedule.primary, "success"
                )
            else:
                # Block production failed
                await self._handle_block_production_failure(schedule)
            
        except Exception as e:
            logger.error(f"Failed to process slot {self.current_slot}: {e}")
            await self._handle_missed_slot()
    
    async def _attempt_block_production(self, schedule: LeaderSchedule) -> bool:
        """Attempt block production by selected leader"""
        try:
            if not self.block_producer:
                logger.warning("No block producer configured")
                return False
            
            # Check if we're the leader
            # This would check if current node is the selected leader
            is_leader = await self._is_current_node_leader(schedule.primary)
            
            if not is_leader:
                # Not our turn to produce block
                return False
            
            # Attempt block production
            self.consensus_state = ConsensusState.BLOCK_PROPOSED
            
            block_data = await self._create_block_data()
            block_result = await self.block_producer(block_data)
            
            if block_result:
                logger.info(f"Block produced by {schedule.primary} for slot {self.current_slot}")
                return True
            else:
                logger.warning(f"Block production failed by {schedule.primary} for slot {self.current_slot}")
                return False
                
        except Exception as e:
            logger.error(f"Block production error: {e}")
            return False
    
    async def _handle_block_production_failure(self, schedule: LeaderSchedule):
        """Handle block production failure"""
        try:
            # Try fallback leaders
            for fallback in schedule.fallbacks[:MAX_FALLBACK_ATTEMPTS]:
                if fallback == "fallback_node" or fallback == "emergency_fallback":
                    continue
                
                logger.info(f"Attempting fallback block production by {fallback}")
                
                # Check if fallback is available and attempt production
                fallback_schedule = LeaderSchedule(
                    slot=self.current_slot,
                    primary=fallback,
                    fallbacks=schedule.fallbacks,
                    deadline=schedule.deadline
                )
                
                block_produced = await self._attempt_block_production(fallback_schedule)
                if block_produced:
                    await self.leader_selection_engine.record_block_result(
                        self.current_slot, fallback, "fallback_success"
                    )
                    return
            
            # All production attempts failed
            await self.leader_selection_engine.record_block_result(
                self.current_slot, "missed", "all_failed"
            )
            logger.warning(f"All block production attempts failed for slot {self.current_slot}")
            
        except Exception as e:
            logger.error(f"Error handling block production failure: {e}")
    
    async def _handle_missed_slot(self):
        """Handle missed slot (no eligible leader)"""
        try:
            self.consensus_state = ConsensusState.SLOT_MISSED
            
            await self.leader_selection_engine.record_block_result(
                self.current_slot, "missed", "no_eligible_leader"
            )
            
            logger.warning(f"Slot {self.current_slot} missed - no eligible leader")
            
        except Exception as e:
            logger.error(f"Error handling missed slot: {e}")
    
    async def _create_block_data(self) -> Dict[str, Any]:
        """Create block data for production"""
        try:
            # Get pending transactions/sessions for block
            pending_sessions = await self._get_pending_sessions()
            
            # Create block header
            block_data = {
                "slot": self.current_slot,
                "epoch": self.current_epoch,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "leader": await self.get_current_leader(),
                "previous_hash": await self._get_previous_block_hash(),
                "merkle_root": self._calculate_merkle_root(pending_sessions),
                "session_count": len(pending_sessions),
                "sessions": pending_sessions
            }
            
            return block_data
            
        except Exception as e:
            logger.error(f"Failed to create block data: {e}")
            return {}
    
    async def _get_pending_sessions(self) -> List[Dict[str, Any]]:
        """Get pending sessions for block inclusion"""
        try:
            cursor = self.db["sessions"].find({
                "status": "pending"
            }).limit(100)  # Limit sessions per block
            
            sessions = []
            async for doc in cursor:
                sessions.append(doc)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get pending sessions: {e}")
            return []
    
    async def _get_previous_block_hash(self) -> str:
        """Get hash of previous block"""
        try:
            # Get latest block
            latest_block = await self.db["blocks"].find_one(
                {}, sort=[("slot", -1)]
            )
            
            if latest_block:
                return latest_block.get("hash", "0x" + "0" * 64)
            else:
                return "0x" + "0" * 64  # Genesis block hash
                
        except Exception as e:
            logger.error(f"Failed to get previous block hash: {e}")
            return "0x" + "0" * 64
    
    def _calculate_merkle_root(self, sessions: List[Dict[str, Any]]) -> str:
        """Calculate Merkle root of sessions"""
        if not sessions:
            return "0x" + "0" * 64
        
        import hashlib
        
        # Sort sessions by session_id for consistent ordering
        sorted_sessions = sorted(sessions, key=lambda x: x["_id"])
        
        # Create leaf hashes
        leaf_hashes = []
        for session in sorted_sessions:
            leaf_data = f"{session['_id']}{session.get('manifest_hash', '')}{session.get('merkle_root', '')}"
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
    
    async def _is_current_node_leader(self, leader_id: str) -> bool:
        """Check if current node is the selected leader"""
        try:
            # This would check if current node's ID matches leader_id
            # For now, return False as placeholder
            # In real implementation, this would check node identity
            return False
            
        except Exception as e:
            logger.error(f"Failed to check leader identity: {e}")
            return False
    
    async def _calculate_epoch_work_credits(self, epoch: int):
        """Calculate work credits for epoch"""
        try:
            tallies = await self.work_credits_engine.calculate_work_credits(epoch)
            logger.info(f"Work credits calculated for epoch {epoch}: {len(tallies)} entities")
            
        except Exception as e:
            logger.error(f"Failed to calculate work credits for epoch {epoch}: {e}")
    
    async def _save_consensus_state(self):
        """Save current consensus state to database"""
        try:
            state_doc = {
                "_id": "current",
                "epoch": self.current_epoch,
                "slot": self.current_slot,
                "state": self.consensus_state.value,
                "last_block_time": self.last_block_time,
                "updated_at": datetime.now(timezone.utc)
            }
            
            await self.db["consensus_state"].replace_one(
                {"_id": "current"},
                state_doc,
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Failed to save consensus state: {e}")
    
    def _calculate_epoch_from_time(self, timestamp: datetime) -> int:
        """Calculate epoch number from timestamp"""
        epoch_start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        time_diff = timestamp - epoch_start
        return int(time_diff.total_seconds() // (EPOCH_DURATION_HOURS * 3600))
    
    def _calculate_slot_from_time(self, timestamp: datetime) -> int:
        """Calculate slot number from timestamp"""
        epoch_start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        time_diff = timestamp - epoch_start
        return int(time_diff.total_seconds() // SLOT_DURATION_SEC)
    
    def set_block_producer(self, producer: Callable):
        """Set block producer callback"""
        self.block_producer = producer
        logger.info("Block producer set")
    
    def set_block_validator(self, validator: Callable):
        """Set block validator callback"""
        self.block_validator = validator
        logger.info("Block validator set")
    
    async def get_consensus_status(self) -> Dict[str, Any]:
        """Get current consensus status"""
        try:
            current_leader = await self.get_current_leader()
            
            return {
                "consensus_version": CONSENSUS_VERSION,
                "current_epoch": self.current_epoch,
                "current_slot": self.current_slot,
                "consensus_state": self.consensus_state.value,
                "current_leader": current_leader,
                "last_block_time": self.last_block_time,
                "slot_duration_sec": SLOT_DURATION_SEC,
                "epoch_duration_hours": EPOCH_DURATION_HOURS,
                "cooldown_slots": COOLDOWN_SLOTS,
                "leader_window_days": LEADER_WINDOW_DAYS
            }
            
        except Exception as e:
            logger.error(f"Failed to get consensus status: {e}")
            return {}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def calculate_slot_end_time(slot: int, slot_duration: int = SLOT_DURATION_SEC) -> datetime:
    """Calculate end time for slot"""
    epoch_start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    slot_end = epoch_start + timedelta(seconds=(slot + 1) * slot_duration)
    return slot_end


def is_slot_active(slot: int, current_time: Optional[datetime] = None) -> bool:
    """Check if slot is currently active"""
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    slot_start = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=slot * SLOT_DURATION_SEC)
    slot_end = slot_start + timedelta(seconds=SLOT_DURATION_SEC)
    
    return slot_start <= current_time < slot_end


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "PoOTConsensusEngine",
    "calculate_slot_end_time",
    "is_slot_active",
    "CONSENSUS_VERSION",
    "EPOCH_DURATION_HOURS",
    "MAX_FALLBACK_ATTEMPTS"
]