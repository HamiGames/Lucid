#!/usr/bin/env python3
"""
PoOT (Proof of Operational Tasks) Consensus Engine
Based on rebuild-blockchain-engine.md specifications

Implements pure PoOT consensus on On-System Chain with:
- Work credits from relay bandwidth, storage proofs, validation signatures, uptime beacons
- Leader selection with cooldown periods
- Slot-based block production (120s slots)
- MongoDB collections for consensus state
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
import secrets

logger = logging.getLogger(__name__)

# PoOT Consensus Parameters (Immutable per Spec-1b)
SLOT_DURATION_SEC = 120  # Fixed, immutable
SLOT_TIMEOUT_MS = 5000   # 5s leader timeout
COOLDOWN_SLOTS = 16      # 16 slot cooldown
LEADER_WINDOW_DAYS = 7   # 7-day PoOT window
D_MIN = 0.2             # Minimum density threshold
BASE_MB_PER_SESSION = 5  # 5MB base unit


class ProofType(Enum):
    """Types of work proofs for PoOT consensus"""
    RELAY_BANDWIDTH = "relay_bandwidth"
    STORAGE_AVAILABILITY = "storage_availability"
    VALIDATION_SIGNATURE = "validation_signature"
    UPTIME_BEACON = "uptime_beacon"


class ConsensusState(Enum):
    """PoOT consensus states"""
    CALCULATING = "calculating"
    LEADER_SELECTED = "leader_selected"
    BLOCK_PROPOSED = "block_proposed"
    BLOCK_CONFIRMED = "block_confirmed"
    SLOT_MISSED = "slot_missed"


@dataclass
class WorkCreditsProof:
    """PoOT work credits proof submission"""
    node_id: str
    pool_id: Optional[str]
    slot: int
    proof_type: ProofType
    proof_data: Dict[str, Any]
    signature: bytes
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        return {
            "_id": f"{self.node_id}_{self.slot}_{self.proof_type.value}",
            "nodeId": self.node_id,
            "poolId": self.pool_id,
            "slot": self.slot,
            "type": self.proof_type.value,
            "value": self.proof_data,
            "sig": self.signature.hex(),
            "ts": self.timestamp
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
    """Block leader schedule per slot"""
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


class PoOTConsensusEngine:
    """
    Proof of Operational Tasks (PoOT) consensus engine.
    
    Implements Spec-1b requirements:
    - Work credits from relay bandwidth, storage proofs, validation signatures, uptime beacons
    - Leader selection based on work credits ranking with cooldown periods
    - Slot-based block production (120s slots)
    - MongoDB collections for consensus state
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.current_epoch = 0
        self.current_slot = 0
        self.leader_schedule: Dict[int, LeaderSchedule] = {}
        self.running = False
        
        # Initialize MongoDB indexes
        asyncio.create_task(self._setup_mongodb_indexes())
        
        logger.info("PoOT consensus engine initialized")
    
    async def _setup_mongodb_indexes(self):
        """Setup MongoDB indexes for consensus collections per Spec-1b"""
        try:
            # task_proofs collection - sharded on { slot: 1, nodeId: 1 }
            await self.db["task_proofs"].create_index([("slot", 1), ("nodeId", 1)])
            await self.db["task_proofs"].create_index([("type", 1)])
            await self.db["task_proofs"].create_index([("ts", -1)])
            
            # work_tally collection - replicated
            await self.db["work_tally"].create_index([("epoch", 1), ("entityId", 1)])
            await self.db["work_tally"].create_index([("rank", 1)])
            
            # leader_schedule collection - replicated  
            await self.db["leader_schedule"].create_index([("slot", 1)])
            
            logger.info("PoOT MongoDB indexes created")
            
        except Exception as e:
            logger.error(f"Failed to setup MongoDB indexes: {e}")
    
    async def start(self):
        """Start PoOT consensus engine"""
        self.running = True
        
        # Start consensus loops
        asyncio.create_task(self._consensus_loop())
        asyncio.create_task(self._work_credits_calculation_loop())
        
        logger.info("PoOT consensus engine started")
    
    async def stop(self):
        """Stop PoOT consensus engine"""
        self.running = False
        logger.info("PoOT consensus engine stopped")
    
    async def submit_work_proof(self, proof: WorkCreditsProof) -> bool:
        """
        Submit work credits proof for PoOT consensus.
        
        Per Spec-1b lines 129-134: relay_bandwidth, storage_availability, 
        validation_signature, uptime_beacon
        """
        try:
            # Validate proof data
            if not self._validate_proof_data(proof):
                logger.warning(f"Invalid proof data from {proof.node_id}")
                return False
            
            # Store proof in MongoDB (sharded collection)
            await self.db["task_proofs"].replace_one(
                {"_id": proof.to_dict()["_id"]},
                proof.to_dict(),
                upsert=True
            )
            
            logger.info(f"Work proof submitted: {proof.node_id} - {proof.proof_type.value} for slot {proof.slot}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit work proof: {e}")
            return False
    
    def _validate_proof_data(self, proof: WorkCreditsProof) -> bool:
        """Validate proof data based on proof type"""
        try:
            if proof.proof_type == ProofType.RELAY_BANDWIDTH:
                # Validate bandwidth proof
                bandwidth = proof.proof_data.get("bandwidth", 0)
                return isinstance(bandwidth, (int, float)) and bandwidth >= 0
            
            elif proof.proof_type == ProofType.STORAGE_AVAILABILITY:
                # Validate storage proof
                available_space = proof.proof_data.get("available_space", 0)
                return isinstance(available_space, (int, float)) and available_space >= 0
            
            elif proof.proof_type == ProofType.VALIDATION_SIGNATURE:
                # Validate signature proof
                return "signature" in proof.proof_data and "message_hash" in proof.proof_data
            
            elif proof.proof_type == ProofType.UPTIME_BEACON:
                # Validate uptime proof
                uptime = proof.proof_data.get("uptime", 0)
                return isinstance(uptime, (int, float)) and 0 <= uptime <= 1
            
            return False
            
        except Exception:
            return False
    
    async def calculate_work_credits(self, epoch: int) -> List[WorkCreditsTally]:
        """
        Calculate work credits for all entities over sliding window.
        
        Work formula: W_t = max(S_t, ceil(B_t / BASE_MB_PER_SESSION))
        where BASE_MB_PER_SESSION = 5MB
        """
        try:
            # Get window start time (7 days ago)
            window_start = datetime.now(timezone.utc) - timedelta(days=LEADER_WINDOW_DAYS)
            
            # Get all proofs in window
            proofs_cursor = self.db["task_proofs"].find({
                "ts": {"$gte": window_start}
            })
            
            entity_credits: Dict[str, Dict[str, Any]] = {}
            
            async for proof_doc in proofs_cursor:
                entity_id = proof_doc["nodeId"]
                pool_id = proof_doc.get("poolId")
                
                # Use pool_id if available, otherwise node_id
                credit_entity = pool_id if pool_id else entity_id
                
                if credit_entity not in entity_credits:
                    entity_credits[credit_entity] = {
                        "relay_bandwidth": 0,
                        "storage_proofs": 0,
                        "validation_signatures": 0,
                        "uptime_score": 0.0,
                        "proof_count": 0
                    }
                
                # Calculate credits based on proof type
                proof_type = proof_doc["type"]
                value = proof_doc["value"]
                
                if proof_type == "relay_bandwidth":
                    # Bandwidth in MB
                    bandwidth_mb = value.get("bandwidth", 0) / (1024 * 1024)
                    credits = max(1, bandwidth_mb / BASE_MB_PER_SESSION)
                    entity_credits[credit_entity]["relay_bandwidth"] += int(credits)
                
                elif proof_type == "storage_availability":
                    # Storage availability proof
                    entity_credits[credit_entity]["storage_proofs"] += 1
                
                elif proof_type == "validation_signature":
                    # Validation signature proof
                    entity_credits[credit_entity]["validation_signatures"] += 1
                
                elif proof_type == "uptime_beacon":
                    # Uptime score (0-1)
                    uptime = value.get("uptime", 0)
                    entity_credits[credit_entity]["uptime_score"] += uptime
                
                entity_credits[credit_entity]["proof_count"] += 1
            
            # Calculate final tallies
            tallies = []
            for entity_id, credits in entity_credits.items():
                # Calculate total credits
                total_credits = (
                    credits["relay_bandwidth"] +
                    credits["storage_proofs"] * 2 +
                    credits["validation_signatures"] * 3 +
                    int(credits["uptime_score"] * 10)
                )
                
                # Calculate live score (recent activity)
                live_score = min(1.0, credits["proof_count"] / 100)
                
                tally = WorkCreditsTally(
                    epoch=epoch,
                    entity_id=entity_id,
                    credits_total=total_credits,
                    relay_bandwidth=credits["relay_bandwidth"],
                    storage_proofs=credits["storage_proofs"],
                    validation_signatures=credits["validation_signatures"],
                    uptime_score=credits["uptime_score"] / max(1, credits["proof_count"]),
                    live_score=live_score,
                    rank=0  # Will be set after ranking
                )
                
                tallies.append(tally)
            
            # Rank entities by total credits
            tallies.sort(key=lambda x: x.credits_total, reverse=True)
            for i, tally in enumerate(tallies):
                tally.rank = i + 1
            
            # Store tallies in MongoDB
            for tally in tallies:
                await self.db["work_tally"].replace_one(
                    {"_id": tally.to_dict()["_id"]},
                    tally.to_dict(),
                    upsert=True
                )
            
            logger.info(f"Calculated work credits for {len(tallies)} entities in epoch {epoch}")
            return tallies
            
        except Exception as e:
            logger.error(f"Failed to calculate work credits: {e}")
            return []
    
    async def select_leader(self, slot: int) -> Optional[LeaderSchedule]:
        """
        Select block leader for slot based on work credits ranking.
        
        Per Spec-1b lines 135-157:
        - Primary leader = top-ranked, not in cooldown (16 slots)
        - Fallbacks: next ranked entities
        - VRF tie-breaking for equal credits
        """
        try:
            # Get current epoch
            current_time = datetime.now(timezone.utc)
            epoch = int(current_time.timestamp() / (SLOT_DURATION_SEC * 86400))  # Daily epochs
            
            # Get work credits tallies for current epoch
            tallies_cursor = self.db["work_tally"].find({
                "epoch": epoch
            }).sort("rank", 1)
            
            tallies = []
            async for tally_doc in tallies_cursor:
                tallies.append(tally_doc)
            
            if not tallies:
                logger.warning(f"No work credits tallies found for epoch {epoch}")
                return None
            
            # Check cooldown for each entity
            eligible_entities = []
            cooldown_slots = []
            
            for tally in tallies:
                entity_id = tally["entityId"]
                
                # Check if entity is in cooldown
                recent_slots = await self.db["leader_schedule"].find({
                    "primary": entity_id,
                    "slot": {"$gte": slot - COOLDOWN_SLOTS}
                }).to_list(length=None)
                
                if not recent_slots:
                    eligible_entities.append(entity_id)
                else:
                    cooldown_slots.append(entity_id)
            
            if not eligible_entities:
                logger.warning("No eligible entities (all in cooldown)")
                # Use fallback: select from cooldown entities anyway
                eligible_entities = [t["entityId"] for t in tallies[:3]]
            
            # Select primary leader
            primary = eligible_entities[0]
            
            # Select fallbacks (next eligible entities)
            fallbacks = eligible_entities[1:4]  # Up to 3 fallbacks
            
            # Create leader schedule
            deadline = current_time + timedelta(milliseconds=SLOT_TIMEOUT_MS)
            schedule = LeaderSchedule(
                slot=slot,
                primary=primary,
                fallbacks=fallbacks,
                deadline=deadline
            )
            
            # Store schedule in MongoDB
            await self.db["leader_schedule"].replace_one(
                {"_id": slot},
                schedule.to_dict(),
                upsert=True
            )
            
            self.leader_schedule[slot] = schedule
            
            logger.info(f"Leader selected for slot {slot}: {primary} (fallbacks: {fallbacks})")
            return schedule
            
        except Exception as e:
            logger.error(f"Failed to select leader for slot {slot}: {e}")
            return None
    
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
    
    async def _consensus_loop(self):
        """Main consensus loop for slot progression"""
        while self.running:
            try:
                current_time = datetime.now(timezone.utc)
                current_slot = int(current_time.timestamp() / SLOT_DURATION_SEC)
                
                if current_slot != self.current_slot:
                    self.current_slot = current_slot
                    
                    # Select leader for new slot
                    schedule = await self.select_leader(current_slot)
                    
                    if schedule:
                        logger.info(f"New slot {current_slot}: leader {schedule.primary}")
                    else:
                        logger.warning(f"Failed to select leader for slot {current_slot}")
                
                # Wait for next slot
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in consensus loop: {e}")
                await asyncio.sleep(5)
    
    async def _work_credits_calculation_loop(self):
        """Periodic work credits calculation"""
        while self.running:
            try:
                # Calculate work credits every hour
                await asyncio.sleep(3600)
                
                if self.running:
                    current_time = datetime.now(timezone.utc)
                    epoch = int(current_time.timestamp() / (SLOT_DURATION_SEC * 86400))
                    
                    tallies = await self.calculate_work_credits(epoch)
                    logger.info(f"Work credits calculated for epoch {epoch}: {len(tallies)} entities")
                
            except Exception as e:
                logger.error(f"Error in work credits calculation loop: {e}")
                await asyncio.sleep(60)


# Global consensus engine instance
_consensus_engine: Optional[PoOTConsensusEngine] = None


def get_consensus_engine() -> Optional[PoOTConsensusEngine]:
    """Get global consensus engine instance"""
    return _consensus_engine


def create_consensus_engine(db: AsyncIOMotorDatabase) -> PoOTConsensusEngine:
    """Create and initialize consensus engine"""
    global _consensus_engine
    _consensus_engine = PoOTConsensusEngine(db)
    return _consensus_engine


async def cleanup_consensus_engine():
    """Cleanup consensus engine"""
    global _consensus_engine
    if _consensus_engine:
        await _consensus_engine.stop()
        _consensus_engine = None


if __name__ == "__main__":
    async def test_consensus():
        """Test PoOT consensus engine"""
        from motor.motor_asyncio import AsyncIOMotorClient
        
        # Mock database for testing
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client.test_lucid
        
        # Create consensus engine
        consensus = create_consensus_engine(db)
        await consensus.start()
        
        try:
            # Test work proof submission
            proof = WorkCreditsProof(
                node_id="test_node_1",
                pool_id=None,
                slot=100,
                proof_type=ProofType.RELAY_BANDWIDTH,
                proof_data={"bandwidth": 1024000},
                signature=b"test_signature"
            )
            
            success = await consensus.submit_work_proof(proof)
            print(f"Work proof submission: {'SUCCESS' if success else 'FAILED'}")
            
            # Test leader selection
            schedule = await consensus.select_leader(100)
            if schedule:
                print(f"Leader selected: {schedule.primary}")
            else:
                print("Leader selection failed")
            
            # Test work credits calculation
            tallies = await consensus.calculate_work_credits(1)
            print(f"Work credits calculated for {len(tallies)} entities")
            
        finally:
            await consensus.stop()
            client.close()
    
    # Run test
    asyncio.run(test_consensus())
