#!/usr/bin/env python3
"""
Leader Selection Algorithm for PoOT Consensus
Based on rebuild-blockchain-engine.md specifications

Implements leader selection with:
- Work credits ranking
- Cooldown periods (16 slots)
- Fallback mechanisms
- VRF tie-breaking for equal credits
"""

import asyncio
import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# Leader Selection Constants
COOLDOWN_SLOTS = 16  # 16 slot cooldown per Spec-1b
MAX_FALLBACKS = 3   # Maximum number of fallback leaders
SLOT_TIMEOUT_MS = 5000  # 5s leader timeout


class SelectionReason(Enum):
    """Reasons for leader selection"""
    TOP_RANKED = "top_ranked"
    COOLDOWN_FALLBACK = "cooldown_fallback"
    VRF_TIEBREAK = "vrf_tiebreak"
    EMERGENCY_FALLBACK = "emergency_fallback"
    RANDOM_FALLBACK = "random_fallback"


@dataclass
class EntityRanking:
    """Entity ranking information"""
    entity_id: str
    total_credits: int
    live_score: float
    rank: int
    is_in_cooldown: bool
    last_leader_slot: Optional[int] = None


@dataclass
class LeaderSchedule:
    """Block leader schedule per slot"""
    slot: int
    primary: str  # entity_id
    fallbacks: List[str]  # fallback entity_ids
    winner: Optional[str] = None
    reason: SelectionReason = SelectionReason.TOP_RANKED
    deadline: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    vrf_seed: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        return {
            "_id": self.slot,
            "slot": self.slot,
            "primary": self.primary,
            "fallbacks": self.fallbacks,
            "result": {
                "winner": self.winner,
                "reason": self.reason.value
            },
            "vrf_seed": self.vrf_seed
        }


class VRFProvider:
    """Verifiable Random Function for tie-breaking"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_vrf_seed(self, slot: int, block_hash: Optional[str] = None) -> str:
        """
        Generate VRF seed for tie-breaking.
        
        Args:
            slot: Current consensus slot
            block_hash: Previous block hash (if available)
            
        Returns:
            VRF seed string
        """
        try:
            # Combine slot and block hash for seed generation
            seed_data = f"{slot}_{block_hash or 'genesis'}"
            seed_hash = hashlib.sha256(seed_data.encode()).hexdigest()
            
            self.logger.debug(f"Generated VRF seed for slot {slot}: {seed_hash[:16]}...")
            return seed_hash
            
        except Exception as e:
            self.logger.error(f"Failed to generate VRF seed: {e}")
            return secrets.token_hex(32)
    
    def vrf_select(self, candidates: List[str], seed: str) -> str:
        """
        Select candidate using VRF.
        
        Args:
            candidates: List of candidate entity IDs
            seed: VRF seed
            
        Returns:
            Selected entity ID
        """
        try:
            if not candidates:
                raise ValueError("No candidates provided")
            
            if len(candidates) == 1:
                return candidates[0]
            
            # Use VRF seed to select candidate
            seed_int = int(seed[:16], 16)  # Use first 16 hex chars as integer
            selected_index = seed_int % len(candidates)
            
            selected = candidates[selected_index]
            self.logger.debug(f"VRF selected {selected} from {len(candidates)} candidates")
            
            return selected
            
        except Exception as e:
            self.logger.error(f"Failed to VRF select: {e}")
            return candidates[0] if candidates else "fallback_node"


class CooldownManager:
    """Manages leader cooldown periods"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    async def is_entity_in_cooldown(self, entity_id: str, current_slot: int) -> Tuple[bool, Optional[int]]:
        """
        Check if entity is in cooldown period.
        
        Args:
            entity_id: Entity ID to check
            current_slot: Current consensus slot
            
        Returns:
            Tuple of (is_in_cooldown, last_leader_slot)
        """
        try:
            # Find recent leader slots for this entity
            recent_slots = await self.db["leader_schedule"].find({
                "primary": entity_id,
                "slot": {"$gte": current_slot - COOLDOWN_SLOTS}
            }).sort("slot", -1).to_list(length=1)
            
            if recent_slots:
                last_slot = recent_slots[0]["slot"]
                slots_since_leader = current_slot - last_slot
                is_in_cooldown = slots_since_leader < COOLDOWN_SLOTS
                
                self.logger.debug(f"Entity {entity_id}: last leader slot {last_slot}, slots since {slots_since_leader}, cooldown: {is_in_cooldown}")
                return is_in_cooldown, last_slot
            else:
                self.logger.debug(f"Entity {entity_id}: no recent leader slots, not in cooldown")
                return False, None
                
        except Exception as e:
            self.logger.error(f"Failed to check cooldown for {entity_id}: {e}")
            return False, None
    
    async def get_cooldown_entities(self, current_slot: int) -> List[str]:
        """
        Get list of entities currently in cooldown.
        
        Args:
            current_slot: Current consensus slot
            
        Returns:
            List of entity IDs in cooldown
        """
        try:
            # Find all entities that were leaders in recent slots
            recent_leaders = await self.db["leader_schedule"].find({
                "slot": {"$gte": current_slot - COOLDOWN_SLOTS}
            }).to_list(length=None)
            
            cooldown_entities = []
            for leader_doc in recent_leaders:
                entity_id = leader_doc["primary"]
                leader_slot = leader_doc["slot"]
                
                slots_since_leader = current_slot - leader_slot
                if slots_since_leader < COOLDOWN_SLOTS:
                    cooldown_entities.append(entity_id)
            
            # Remove duplicates
            cooldown_entities = list(set(cooldown_entities))
            
            self.logger.debug(f"Entities in cooldown: {cooldown_entities}")
            return cooldown_entities
            
        except Exception as e:
            self.logger.error(f"Failed to get cooldown entities: {e}")
            return []


class LeaderSelector:
    """Main leader selection algorithm"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.vrf = VRFProvider()
        self.cooldown_manager = CooldownManager(db)
        self.logger = logging.getLogger(__name__)
    
    async def select_leader(self, slot: int, epoch: int) -> Optional[LeaderSchedule]:
        """
        Select block leader for slot based on work credits ranking.
        
        Per Spec-1b lines 135-157:
        - Primary leader = top-ranked, not in cooldown (16 slots)
        - Fallbacks: next ranked entities
        - VRF tie-breaking for equal credits
        
        Args:
            slot: Consensus slot number
            epoch: Current consensus epoch
            
        Returns:
            LeaderSchedule or None if selection failed
        """
        try:
            # Get work credits tallies for current epoch
            tallies = await self._get_work_credits_tallies(epoch)
            
            if not tallies:
                self.logger.warning(f"No work credits tallies found for epoch {epoch}")
                return await self._emergency_fallback_selection(slot)
            
            # Check cooldown for each entity
            rankings = await self._build_entity_rankings(tallies, slot)
            
            if not rankings:
                self.logger.warning("No eligible entities after cooldown check")
                return await self._emergency_fallback_selection(slot)
            
            # Select primary leader
            primary_selection = await self._select_primary_leader(rankings, slot)
            
            # Select fallbacks
            fallbacks = await self._select_fallback_leaders(rankings, primary_selection.entity_id, MAX_FALLBACKS)
            
            # Generate VRF seed for tie-breaking
            vrf_seed = self.vrf.generate_vrf_seed(slot)
            
            # Create leader schedule
            deadline = datetime.now(timezone.utc) + timedelta(milliseconds=SLOT_TIMEOUT_MS)
            schedule = LeaderSchedule(
                slot=slot,
                primary=primary_selection.entity_id,
                fallbacks=fallbacks,
                reason=primary_selection.reason,
                deadline=deadline,
                vrf_seed=vrf_seed
            )
            
            # Store schedule in MongoDB
            await self._store_leader_schedule(schedule)
            
            self.logger.info(f"Leader selected for slot {slot}: {primary_selection.entity_id} (reason: {primary_selection.reason.value})")
            return schedule
            
        except Exception as e:
            self.logger.error(f"Failed to select leader for slot {slot}: {e}")
            return await self._emergency_fallback_selection(slot)
    
    async def _get_work_credits_tallies(self, epoch: int) -> List[Dict[str, Any]]:
        """Get work credits tallies for epoch"""
        try:
            tallies_cursor = self.db["work_tally"].find({
                "epoch": epoch
            }).sort("rank", 1)
            
            tallies = []
            async for tally_doc in tallies_cursor:
                tallies.append(tally_doc)
            
            return tallies
            
        except Exception as e:
            self.logger.error(f"Failed to get work credits tallies: {e}")
            return []
    
    async def _build_entity_rankings(self, tallies: List[Dict[str, Any]], slot: int) -> List[EntityRanking]:
        """Build entity rankings with cooldown information"""
        try:
            rankings = []
            
            for tally in tallies:
                entity_id = tally["entityId"]
                
                # Check cooldown status
                is_in_cooldown, last_leader_slot = await self.cooldown_manager.is_entity_in_cooldown(entity_id, slot)
                
                ranking = EntityRanking(
                    entity_id=entity_id,
                    total_credits=tally["credits"],
                    live_score=tally["liveScore"],
                    rank=tally["rank"],
                    is_in_cooldown=is_in_cooldown,
                    last_leader_slot=last_leader_slot
                )
                
                rankings.append(ranking)
            
            return rankings
            
        except Exception as e:
            self.logger.error(f"Failed to build entity rankings: {e}")
            return []
    
    async def _select_primary_leader(self, rankings: List[EntityRanking], slot: int) -> EntityRanking:
        """Select primary leader from rankings"""
        try:
            # Separate eligible and cooldown entities
            eligible_entities = [r for r in rankings if not r.is_in_cooldown]
            cooldown_entities = [r for r in rankings if r.is_in_cooldown]
            
            if eligible_entities:
                # Select from eligible entities (not in cooldown)
                selected = eligible_entities[0]
                selected.reason = SelectionReason.TOP_RANKED
                
                # Check for ties in credits
                tied_entities = [r for r in eligible_entities if r.total_credits == selected.total_credits]
                
                if len(tied_entities) > 1:
                    # Use VRF for tie-breaking
                    vrf_seed = self.vrf.generate_vrf_seed(slot)
                    tied_ids = [r.entity_id for r in tied_entities]
                    vrf_selected_id = self.vrf.vrf_select(tied_ids, vrf_seed)
                    
                    # Find the VRF-selected entity
                    for entity in tied_entities:
                        if entity.entity_id == vrf_selected_id:
                            entity.reason = SelectionReason.VRF_TIEBREAK
                            return entity
                
                return selected
            
            elif cooldown_entities:
                # All top entities are in cooldown, select from cooldown entities
                selected = cooldown_entities[0]
                selected.reason = SelectionReason.COOLDOWN_FALLBACK
                return selected
            
            else:
                # No entities available, emergency fallback
                return EntityRanking(
                    entity_id="emergency_fallback",
                    total_credits=0,
                    live_score=0.0,
                    rank=999,
                    is_in_cooldown=False
                )
                
        except Exception as e:
            self.logger.error(f"Failed to select primary leader: {e}")
            return EntityRanking(
                entity_id="emergency_fallback",
                total_credits=0,
                live_score=0.0,
                rank=999,
                is_in_cooldown=False
            )
    
    async def _select_fallback_leaders(self, rankings: List[EntityRanking], primary_id: str, max_fallbacks: int) -> List[str]:
        """Select fallback leaders"""
        try:
            fallbacks = []
            
            # Get entities excluding the primary
            available_entities = [r for r in rankings if r.entity_id != primary_id]
            
            # Prioritize entities not in cooldown
            eligible_fallbacks = [r for r in available_entities if not r.is_in_cooldown]
            cooldown_fallbacks = [r for r in available_entities if r.is_in_cooldown]
            
            # Add eligible fallbacks first
            for entity in eligible_fallbacks[:max_fallbacks]:
                fallbacks.append(entity.entity_id)
            
            # Add cooldown fallbacks if needed
            if len(fallbacks) < max_fallbacks:
                remaining_slots = max_fallbacks - len(fallbacks)
                for entity in cooldown_fallbacks[:remaining_slots]:
                    fallbacks.append(entity.entity_id)
            
            return fallbacks
            
        except Exception as e:
            self.logger.error(f"Failed to select fallback leaders: {e}")
            return ["fallback_1", "fallback_2", "fallback_3"][:max_fallbacks]
    
    async def _emergency_fallback_selection(self, slot: int) -> LeaderSchedule:
        """Emergency fallback selection when normal selection fails"""
        try:
            # Use random selection as last resort
            fallback_entities = ["emergency_node_1", "emergency_node_2", "emergency_node_3"]
            
            vrf_seed = self.vrf.generate_vrf_seed(slot)
            primary = self.vrf.vrf_select(fallback_entities, vrf_seed)
            
            fallbacks = [e for e in fallback_entities if e != primary]
            
            deadline = datetime.now(timezone.utc) + timedelta(milliseconds=SLOT_TIMEOUT_MS)
            schedule = LeaderSchedule(
                slot=slot,
                primary=primary,
                fallbacks=fallbacks,
                reason=SelectionReason.EMERGENCY_FALLBACK,
                deadline=deadline,
                vrf_seed=vrf_seed
            )
            
            await self._store_leader_schedule(schedule)
            
            self.logger.warning(f"Emergency fallback selection for slot {slot}: {primary}")
            return schedule
            
        except Exception as e:
            self.logger.error(f"Failed emergency fallback selection: {e}")
            # Ultimate fallback
            return LeaderSchedule(
                slot=slot,
                primary="ultimate_fallback",
                fallbacks=["backup_1", "backup_2"],
                reason=SelectionReason.EMERGENCY_FALLBACK
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
            self.logger.error(f"Failed to store leader schedule: {e}")
    
    async def record_block_result(self, slot: int, winner: str, reason: str):
        """Record block production result"""
        try:
            await self.db["leader_schedule"].update_one(
                {"_id": slot},
                {"$set": {"result": {"winner": winner, "reason": reason}}}
            )
            
            self.logger.info(f"Block result recorded for slot {slot}: {winner} ({reason})")
            
        except Exception as e:
            self.logger.error(f"Failed to record block result: {e}")


# Global leader selector instance
_leader_selector: Optional[LeaderSelector] = None


def get_leader_selector() -> Optional[LeaderSelector]:
    """Get global leader selector instance"""
    return _leader_selector


def create_leader_selector(db: AsyncIOMotorDatabase) -> LeaderSelector:
    """Create and initialize leader selector"""
    global _leader_selector
    _leader_selector = LeaderSelector(db)
    return _leader_selector


async def cleanup_leader_selector():
    """Cleanup leader selector"""
    global _leader_selector
    _leader_selector = None


if __name__ == "__main__":
    async def test_leader_selection():
        """Test leader selection algorithm"""
        from motor.motor_asyncio import AsyncIOMotorClient
        
        # Mock database for testing
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client.test_lucid
        
        # Create leader selector
        selector = create_leader_selector(db)
        
        try:
            # Test leader selection
            schedule = await selector.select_leader(100, 1)
            
            if schedule:
                print(f"Leader selected for slot {schedule.slot}:")
                print(f"  Primary: {schedule.primary}")
                print(f"  Fallbacks: {schedule.fallbacks}")
                print(f"  Reason: {schedule.reason.value}")
                print(f"  VRF Seed: {schedule.vrf_seed[:16]}...")
            else:
                print("Leader selection failed")
            
            # Test cooldown check
            cooldown_manager = CooldownManager(db)
            is_cooldown, last_slot = await cooldown_manager.is_entity_in_cooldown("test_node", 100)
            print(f"Cooldown check: {is_cooldown}, last slot: {last_slot}")
            
        finally:
            client.close()
    
    # Run test
    asyncio.run(test_leader_selection())
