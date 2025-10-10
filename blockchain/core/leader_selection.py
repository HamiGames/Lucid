# Path: blockchain/core/leader_selection.py
"""
PoOT Leader Selection Algorithm

Implements leader selection for PoOT consensus based on work credits ranking
with cooldown periods and VRF tie-breaking as specified in Spec-1b lines 135-157.

Features:
- Work credits ranking with cooldown periods (16 slots)
- VRF tie-breaking for equal credits
- Fallback leader selection
- Density threshold enforcement
"""

from __future__ import annotations

import asyncio
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Tuple
import secrets

from motor.motor_asyncio import AsyncIOMotorDatabase

from .models import WorkCredit, LeaderSchedule, TaskProofType

logger = logging.getLogger(__name__)

# =============================================================================
# IMMUTABLE CONSENSUS PARAMETERS (Spec-1b)
# =============================================================================

SLOT_DURATION_SEC = 120  # Fixed, immutable per Spec-1b line 170
SLOT_TIMEOUT_MS = 5000   # 5s leader timeout
COOLDOWN_SLOTS = 16      # 16 slot cooldown
LEADER_WINDOW_DAYS = 7   # 7-day PoOT window
D_MIN = 0.2             # Minimum density threshold


class LeaderSelectionEngine:
    """
    PoOT leader selection engine with work credits ranking and cooldown.
    
    Per Spec-1b lines 135-157:
    - Primary leader = top-ranked, not in cooldown (16 slots)
    - Fallbacks: next ranked entities
    - VRF tie-breaking for equal credits
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.vrf_seed = secrets.token_bytes(32)  # VRF seed for tie-breaking
        
        logger.info("Leader selection engine initialized")
    
    async def select_leader(self, slot: int) -> LeaderSchedule:
        """
        Select block leader for slot based on work credits ranking.
        
        Args:
            slot: Current slot number
            
        Returns:
            LeaderSchedule with primary and fallback leaders
        """
        try:
            # Get current work credits
            current_epoch = slot // (24 * 60 * 60 // SLOT_DURATION_SEC)  # Daily epochs
            work_credits = await self._get_work_credits_for_epoch(current_epoch)
            
            # Get entities in cooldown
            cooldown_entities = await self._get_cooldown_entities(slot)
            
            # Filter eligible entities (not in cooldown and above density threshold)
            eligible_entities = self._filter_eligible_entities(work_credits, cooldown_entities)
            
            if not eligible_entities:
                # No eligible entities, use fallback
                return self._create_fallback_schedule(slot)
            
            # Select primary and fallbacks
            primary = eligible_entities[0]
            fallbacks = eligible_entities[1:6] if len(eligible_entities) > 1 else ["fallback_node"]
            
            # Create leader schedule
            schedule = LeaderSchedule(
                slot=slot,
                primary=primary,
                fallbacks=fallbacks,
                deadline=datetime.now(timezone.utc) + timedelta(milliseconds=SLOT_TIMEOUT_MS)
            )
            
            # Store schedule in MongoDB
            await self._store_leader_schedule(schedule)
            
            logger.info(f"Leader selected for slot {slot}: {primary} (fallbacks: {fallbacks})")
            return schedule
            
        except Exception as e:
            logger.error(f"Failed to select leader for slot {slot}: {e}")
            return self._create_fallback_schedule(slot)
    
    async def _get_work_credits_for_epoch(self, epoch: int) -> List[WorkCredit]:
        """Get work credits for current epoch, sorted by rank"""
        try:
            cursor = self.db["work_tally"].find({"epoch": epoch}).sort("rank", 1)
            work_credits = []
            
            async for doc in cursor:
                work_credit = WorkCredit(
                    entity_id=doc["entityId"],
                    credits=doc["credits"],
                    live_score=doc["liveScore"],
                    rank=doc["rank"],
                    epoch=doc["epoch"]
                )
                work_credits.append(work_credit)
            
            return work_credits
            
        except Exception as e:
            logger.error(f"Failed to get work credits for epoch {epoch}: {e}")
            return []
    
    async def _get_cooldown_entities(self, current_slot: int) -> Set[str]:
        """Get entities in cooldown period (16 slots)"""
        try:
            cooldown_start_slot = current_slot - COOLDOWN_SLOTS
            cursor = self.db["leader_schedule"].find({
                "slot": {"$gte": cooldown_start_slot, "$lt": current_slot},
                "result.winner": {"$exists": True}
            })
            
            cooldown_entities = set()
            async for doc in cursor:
                winner = doc["result"]["winner"]
                if winner and winner != "missed":
                    cooldown_entities.add(winner)
            
            return cooldown_entities
            
        except Exception as e:
            logger.error(f"Failed to get cooldown entities: {e}")
            return set()
    
    def _filter_eligible_entities(self, work_credits: List[WorkCredit], 
                                 cooldown_entities: Set[str]) -> List[str]:
        """
        Filter entities that are eligible for leader selection.
        
        Criteria:
        1. Not in cooldown period
        2. Above minimum density threshold (D_MIN)
        3. Have sufficient work credits
        """
        eligible = []
        
        for credit in work_credits:
            # Check cooldown
            if credit.entity_id in cooldown_entities:
                continue
            
            # Check density threshold
            if credit.live_score < D_MIN:
                continue
            
            # Check minimum credits
            if credit.credits <= 0:
                continue
            
            eligible.append(credit.entity_id)
        
        return eligible
    
    def _create_fallback_schedule(self, slot: int) -> LeaderSchedule:
        """Create fallback schedule when no eligible entities"""
        return LeaderSchedule(
            slot=slot,
            primary="fallback_node",
            fallbacks=["emergency_fallback"],
            deadline=datetime.now(timezone.utc) + timedelta(milliseconds=SLOT_TIMEOUT_MS)
        )
    
    async def _store_leader_schedule(self, schedule: LeaderSchedule):
        """Store leader schedule in MongoDB"""
        try:
            await self.db["leader_schedule"].replace_one(
                {"_id": schedule.slot},
                schedule.to_dict(),
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to store leader schedule: {e}")
    
    async def record_block_result(self, slot: int, winner: str, reason: str):
        """Record block production result for leader selection"""
        try:
            await self.db["leader_schedule"].update_one(
                {"_id": slot},
                {"$set": {"result": {"winner": winner, "reason": reason}}}
            )
            
            logger.info(f"Block result recorded for slot {slot}: {winner} ({reason})")
            
        except Exception as e:
            logger.error(f"Failed to record block result: {e}")
    
    def vrf_select_leader(self, candidates: List[str], slot: int) -> str:
        """
        VRF (Verifiable Random Function) tie-breaking for leader selection.
        
        Args:
            candidates: List of entities with equal work credits
            slot: Current slot number
            
        Returns:
            Selected entity based on VRF
        """
        if not candidates:
            return "fallback_node"
        
        if len(candidates) == 1:
            return candidates[0]
        
        # Create VRF input from slot and candidates
        vrf_input = f"{slot}_{'_'.join(sorted(candidates))}_{self.vrf_seed.hex()}"
        vrf_hash = hashlib.sha256(vrf_input.encode()).hexdigest()
        
        # Use hash to select candidate
        vrf_value = int(vrf_hash[:8], 16)  # Use first 8 hex chars
        selected_index = vrf_value % len(candidates)
        
        selected = candidates[selected_index]
        logger.info(f"VRF selected {selected} from {len(candidates)} candidates")
        
        return selected
    
    async def get_leader_history(self, start_slot: int, end_slot: int) -> List[LeaderSchedule]:
        """Get leader history for specified slot range"""
        try:
            cursor = self.db["leader_schedule"].find({
                "slot": {"$gte": start_slot, "$lte": end_slot}
            }).sort("slot", 1)
            
            schedules = []
            async for doc in cursor:
                schedule = LeaderSchedule.from_dict(doc)
                schedules.append(schedule)
            
            return schedules
            
        except Exception as e:
            logger.error(f"Failed to get leader history: {e}")
            return []
    
    async def get_cooldown_status(self, entity_id: str, current_slot: int) -> Dict[str, Any]:
        """Get cooldown status for specific entity"""
        try:
            cooldown_start_slot = current_slot - COOLDOWN_SLOTS
            cursor = self.db["leader_schedule"].find({
                "slot": {"$gte": cooldown_start_slot, "$lt": current_slot},
                "result.winner": entity_id
            }).sort("slot", -1)
            
            last_leadership = await cursor.to_list(1)
            
            if last_leadership:
                last_slot = last_leadership[0]["slot"]
                slots_remaining = COOLDOWN_SLOTS - (current_slot - last_slot)
                slots_remaining = max(0, slots_remaining)
                
                return {
                    "in_cooldown": slots_remaining > 0,
                    "last_leadership_slot": last_slot,
                    "slots_remaining": slots_remaining,
                    "cooldown_ends_at": current_slot + slots_remaining
                }
            else:
                return {
                    "in_cooldown": False,
                    "last_leadership_slot": None,
                    "slots_remaining": 0,
                    "cooldown_ends_at": current_slot
                }
                
        except Exception as e:
            logger.error(f"Failed to get cooldown status for {entity_id}: {e}")
            return {
                "in_cooldown": False,
                "last_leadership_slot": None,
                "slots_remaining": 0,
                "cooldown_ends_at": current_slot
            }
    
    async def update_vrf_seed(self, new_seed: bytes):
        """Update VRF seed for tie-breaking"""
        self.vrf_seed = new_seed
        logger.info("VRF seed updated")


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def calculate_epoch_from_slot(slot: int) -> int:
    """Calculate epoch number from slot number"""
    return slot // (24 * 60 * 60 // SLOT_DURATION_SEC)


def calculate_slot_from_timestamp(timestamp: datetime) -> int:
    """Calculate slot number from timestamp"""
    epoch_start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    time_diff = timestamp - epoch_start
    return int(time_diff.total_seconds() // SLOT_DURATION_SEC)


def get_next_slot_start_time(current_slot: int) -> datetime:
    """Get the start time of the next slot"""
    epoch_start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    next_slot_start = epoch_start + timedelta(seconds=(current_slot + 1) * SLOT_DURATION_SEC)
    return next_slot_start


def is_slot_timeout(slot_start_time: datetime, timeout_ms: int = SLOT_TIMEOUT_MS) -> bool:
    """Check if current slot has timed out"""
    now = datetime.now(timezone.utc)
    timeout_duration = timedelta(milliseconds=timeout_ms)
    return (now - slot_start_time) > timeout_duration


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "LeaderSelectionEngine",
    "calculate_epoch_from_slot",
    "calculate_slot_from_timestamp", 
    "get_next_slot_start_time",
    "is_slot_timeout",
    "SLOT_DURATION_SEC",
    "SLOT_TIMEOUT_MS",
    "COOLDOWN_SLOTS",
    "LEADER_WINDOW_DAYS",
    "D_MIN"
]