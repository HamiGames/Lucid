#!/usr/bin/env python3
"""
Unit Tests for PoOT Consensus Engine
Based on rebuild-blockchain-engine.md specifications

Tests PoOT consensus functionality:
- Work credits calculation
- Leader selection algorithm
- Slot progression
- MongoDB integration
"""

import asyncio
import pytest
import logging
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from motor.motor_asyncio import AsyncIOMotorDatabase

# Import the modules to test
from blockchain.core.poot_consensus import (
    PoOTConsensusEngine, WorkCreditsProof, WorkCreditsTally, LeaderSchedule,
    ProofType, ConsensusState, SLOT_DURATION_SEC, COOLDOWN_SLOTS
)
from blockchain.core.work_credits import (
    WorkCreditsCalculator, WorkCreditsValidator, WorkCreditsAggregator,
    BandwidthProof, StorageProof, ValidationProof, UptimeProof
)
from blockchain.core.leader_selection import (
    LeaderSelector, EntityRanking, SelectionReason, VRFProvider, CooldownManager
)

logger = logging.getLogger(__name__)


class TestPoOTConsensus:
    """Test suite for PoOT consensus engine"""
    
    @pytest.fixture
    async def mock_db(self):
        """Mock MongoDB database"""
        db = AsyncMock(spec=AsyncIOMotorDatabase)
        
        # Mock collections
        db.__getitem__ = AsyncMock()
        db["task_proofs"] = AsyncMock()
        db["work_tally"] = AsyncMock()
        db["leader_schedule"] = AsyncMock()
        
        # Mock index creation
        db["task_proofs"].create_index = AsyncMock()
        db["work_tally"].create_index = AsyncMock()
        db["leader_schedule"].create_index = AsyncMock()
        
        return db
    
    @pytest.fixture
    async def consensus_engine(self, mock_db):
        """Create PoOT consensus engine for testing"""
        engine = PoOTConsensusEngine(mock_db)
        return engine
    
    @pytest.mark.asyncio
    async def test_consensus_engine_initialization(self, consensus_engine):
        """Test consensus engine initialization"""
        assert consensus_engine.db is not None
        assert consensus_engine.current_epoch == 0
        assert consensus_engine.current_slot == 0
        assert len(consensus_engine.leader_schedule) == 0
        assert not consensus_engine.running
    
    @pytest.mark.asyncio
    async def test_work_proof_submission(self, consensus_engine):
        """Test work proof submission"""
        # Create test proof
        proof = WorkCreditsProof(
            node_id="test_node_1",
            pool_id=None,
            slot=100,
            proof_type=ProofType.RELAY_BANDWIDTH,
            proof_data={"bandwidth": 1024000},
            signature=b"test_signature"
        )
        
        # Mock database insert
        consensus_engine.db["task_proofs"].replace_one = AsyncMock()
        
        # Submit proof
        result = await consensus_engine.submit_work_proof(proof)
        
        assert result is True
        consensus_engine.db["task_proofs"].replace_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_invalid_work_proof_submission(self, consensus_engine):
        """Test invalid work proof submission"""
        # Create invalid proof
        proof = WorkCreditsProof(
            node_id="test_node_1",
            pool_id=None,
            slot=100,
            proof_type=ProofType.RELAY_BANDWIDTH,
            proof_data={"bandwidth": -1000},  # Invalid negative bandwidth
            signature=b"test_signature"
        )
        
        # Submit proof
        result = await consensus_engine.submit_work_proof(proof)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_work_credits_calculation(self, consensus_engine):
        """Test work credits calculation"""
        # Mock database queries
        mock_proofs = [
            {
                "_id": "node1_100_relay_bandwidth",
                "nodeId": "node1",
                "slot": 100,
                "type": "relay_bandwidth",
                "value": {"bandwidth": 1024000},
                "ts": datetime.now(timezone.utc)
            },
            {
                "_id": "node1_101_storage_availability",
                "nodeId": "node1",
                "slot": 101,
                "type": "storage_availability",
                "value": {"available_space": 1000000000},
                "ts": datetime.now(timezone.utc)
            }
        ]
        
        consensus_engine.db["task_proofs"].find.return_value = mock_proofs
        consensus_engine.db["work_tally"].replace_one = AsyncMock()
        
        # Calculate work credits
        tallies = await consensus_engine.calculate_work_credits(epoch=1)
        
        assert len(tallies) > 0
        assert all(isinstance(tally, WorkCreditsTally) for tally in tallies)
        assert all(tally.epoch == 1 for tally in tallies)
    
    @pytest.mark.asyncio
    async def test_leader_selection(self, consensus_engine):
        """Test leader selection algorithm"""
        # Mock work credits tallies
        mock_tallies = [
            {
                "_id": "1_node1",
                "epoch": 1,
                "entityId": "node1",
                "credits": 100,
                "liveScore": 0.9,
                "rank": 1
            },
            {
                "_id": "1_node2",
                "epoch": 1,
                "entityId": "node2",
                "credits": 80,
                "liveScore": 0.8,
                "rank": 2
            }
        ]
        
        consensus_engine.db["work_tally"].find.return_value = mock_tallies
        consensus_engine.db["leader_schedule"].find.return_value = []
        consensus_engine.db["leader_schedule"].replace_one = AsyncMock()
        
        # Select leader
        schedule = await consensus_engine.select_leader(slot=100)
        
        assert schedule is not None
        assert isinstance(schedule, LeaderSchedule)
        assert schedule.slot == 100
        assert schedule.primary in ["node1", "node2"]
        assert len(schedule.fallbacks) > 0
    
    @pytest.mark.asyncio
    async def test_leader_selection_with_cooldown(self, consensus_engine):
        """Test leader selection with cooldown"""
        # Mock work credits tallies
        mock_tallies = [
            {
                "_id": "1_node1",
                "epoch": 1,
                "entityId": "node1",
                "credits": 100,
                "liveScore": 0.9,
                "rank": 1
            },
            {
                "_id": "1_node2",
                "epoch": 1,
                "entityId": "node2",
                "credits": 80,
                "liveScore": 0.8,
                "rank": 2
            }
        ]
        
        # Mock recent leader slots (node1 in cooldown)
        mock_recent_slots = [
            {
                "primary": "node1",
                "slot": 95  # Within cooldown period
            }
        ]
        
        consensus_engine.db["work_tally"].find.return_value = mock_tallies
        consensus_engine.db["leader_schedule"].find.return_value = mock_recent_slots
        consensus_engine.db["leader_schedule"].replace_one = AsyncMock()
        
        # Select leader
        schedule = await consensus_engine.select_leader(slot=100)
        
        assert schedule is not None
        # Should select node2 since node1 is in cooldown
        assert schedule.primary == "node2"
    
    @pytest.mark.asyncio
    async def test_consensus_engine_start_stop(self, consensus_engine):
        """Test consensus engine start/stop"""
        # Mock the async tasks
        with patch('asyncio.create_task') as mock_create_task:
            # Start engine
            await consensus_engine.start()
            
            assert consensus_engine.running is True
            assert mock_create_task.call_count >= 2  # At least 2 tasks created
            
            # Stop engine
            await consensus_engine.stop()
            
            assert consensus_engine.running is False


class TestWorkCredits:
    """Test suite for work credits system"""
    
    @pytest.fixture
    def calculator(self):
        """Create work credits calculator"""
        return WorkCreditsCalculator()
    
    @pytest.fixture
    def validator(self):
        """Create work credits validator"""
        return WorkCreditsValidator()
    
    @pytest.fixture
    def aggregator(self):
        """Create work credits aggregator"""
        return WorkCreditsAggregator()
    
    def test_bandwidth_credits_calculation(self, calculator):
        """Test bandwidth credits calculation"""
        proof = BandwidthProof(
            bytes_transferred=100 * 1024 * 1024,  # 100 MB
            duration_seconds=10.0,  # 10 seconds
            timestamp=datetime.now(timezone.utc)
        )
        
        credits = calculator.calculate_bandwidth_credits(proof)
        
        assert credits > 0
        assert credits >= 1  # Minimum credits
    
    def test_storage_credits_calculation(self, calculator):
        """Test storage credits calculation"""
        proof = StorageProof(
            total_capacity_bytes=1000 * 1024 * 1024 * 1024,  # 1 TB
            available_capacity_bytes=800 * 1024 * 1024 * 1024,  # 800 GB
            chunks_stored=150,
            verification_hash="a" * 64,
            timestamp=datetime.now(timezone.utc)
        )
        
        credits = calculator.calculate_storage_credits(proof)
        
        assert credits > 0
        assert credits >= 8  # At least 80% availability = 8 credits
        assert credits <= 30  # Max 10 + 20 bonus = 30 credits
    
    def test_validation_credits_calculation(self, calculator):
        """Test validation credits calculation"""
        proof = ValidationProof(
            message_hash="b" * 64,
            signature=b"test_signature",
            validator_address="0x1234567890123456789012345678901234567890",
            validation_count=25,
            timestamp=datetime.now(timezone.utc)
        )
        
        credits = calculator.calculate_validation_credits(proof)
        
        assert credits > 0
        assert credits == 75  # 25 * 3 = 75 credits
    
    def test_uptime_credits_calculation(self, calculator):
        """Test uptime credits calculation"""
        proof = UptimeProof(
            uptime_percentage=99.5,
            consecutive_uptime_hours=168,  # 1 week
            last_heartbeat=datetime.now(timezone.utc),
            timestamp=datetime.now(timezone.utc)
        )
        
        credits = calculator.calculate_uptime_credits(proof)
        
        assert credits > 0
        assert credits >= 99  # At least 99 credits from uptime
        assert credits <= 119  # Max 99 + 20 bonus = 119 credits
    
    def test_bandwidth_proof_validation(self, validator):
        """Test bandwidth proof validation"""
        # Valid proof
        valid_proof = BandwidthProof(
            bytes_transferred=1000000,
            duration_seconds=10.0,
            timestamp=datetime.now(timezone.utc)
        )
        
        assert validator.validate_bandwidth_proof(valid_proof) is True
        
        # Invalid proof (negative bytes)
        invalid_proof = BandwidthProof(
            bytes_transferred=-1000,
            duration_seconds=10.0,
            timestamp=datetime.now(timezone.utc)
        )
        
        assert validator.validate_bandwidth_proof(invalid_proof) is False
    
    def test_storage_proof_validation(self, validator):
        """Test storage proof validation"""
        # Valid proof
        valid_proof = StorageProof(
            total_capacity_bytes=1000000000,
            available_capacity_bytes=800000000,
            chunks_stored=10,
            verification_hash="a" * 64,
            timestamp=datetime.now(timezone.utc)
        )
        
        assert validator.validate_storage_proof(valid_proof) is True
        
        # Invalid proof (invalid hash)
        invalid_proof = StorageProof(
            total_capacity_bytes=1000000000,
            available_capacity_bytes=800000000,
            chunks_stored=10,
            verification_hash="invalid",
            timestamp=datetime.now(timezone.utc)
        )
        
        assert validator.validate_storage_proof(invalid_proof) is False
    
    def test_credits_aggregation(self, aggregator):
        """Test credits aggregation"""
        from blockchain.core.work_credits import WorkCreditsEntry, WorkCreditsType
        
        # Create test entries
        entries = [
            WorkCreditsEntry("node1", None, WorkCreditsType.RELAY_BANDWIDTH, 10, {}, datetime.now(timezone.utc)),
            WorkCreditsEntry("node1", None, WorkCreditsType.STORAGE_AVAILABILITY, 20, {}, datetime.now(timezone.utc)),
            WorkCreditsEntry("node2", "pool1", WorkCreditsType.VALIDATION_SIGNATURE, 30, {}, datetime.now(timezone.utc)),
        ]
        
        # Aggregate credits
        entity_credits = aggregator.aggregate_credits(entries)
        
        assert len(entity_credits) == 2  # node1 and pool1
        assert entity_credits["node1"] == 30  # 10 + 20
        assert entity_credits["pool1"] == 30  # Uses pool_id
    
    def test_entity_ranking(self, aggregator):
        """Test entity ranking"""
        entity_credits = {
            "node1": 100,
            "node2": 80,
            "node3": 120
        }
        
        ranked = aggregator.rank_entities(entity_credits)
        
        assert len(ranked) == 3
        assert ranked[0] == ("node3", 120)  # Highest credits
        assert ranked[1] == ("node1", 100)
        assert ranked[2] == ("node2", 80)   # Lowest credits


class TestLeaderSelection:
    """Test suite for leader selection algorithm"""
    
    @pytest.fixture
    async def mock_db(self):
        """Mock MongoDB database"""
        db = AsyncMock(spec=AsyncIOMotorDatabase)
        db.__getitem__ = AsyncMock()
        db["work_tally"] = AsyncMock()
        db["leader_schedule"] = AsyncMock()
        return db
    
    @pytest.fixture
    def leader_selector(self, mock_db):
        """Create leader selector"""
        return LeaderSelector(mock_db)
    
    @pytest.fixture
    def vrf_provider(self):
        """Create VRF provider"""
        return VRFProvider()
    
    @pytest.fixture
    def cooldown_manager(self, mock_db):
        """Create cooldown manager"""
        return CooldownManager(mock_db)
    
    def test_vrf_seed_generation(self, vrf_provider):
        """Test VRF seed generation"""
        seed = vrf_provider.generate_vrf_seed(slot=100, block_hash="0x123")
        
        assert seed is not None
        assert len(seed) == 64  # 32 bytes = 64 hex chars
        
        # Same inputs should produce same seed
        seed2 = vrf_provider.generate_vrf_seed(slot=100, block_hash="0x123")
        assert seed == seed2
        
        # Different inputs should produce different seeds
        seed3 = vrf_provider.generate_vrf_seed(slot=101, block_hash="0x123")
        assert seed != seed3
    
    def test_vrf_selection(self, vrf_provider):
        """Test VRF candidate selection"""
        candidates = ["node1", "node2", "node3"]
        seed = "a" * 64
        
        selected = vrf_provider.vrf_select(candidates, seed)
        
        assert selected in candidates
        
        # Same seed should select same candidate
        selected2 = vrf_provider.vrf_select(candidates, seed)
        assert selected == selected2
    
    @pytest.mark.asyncio
    async def test_cooldown_check(self, cooldown_manager):
        """Test cooldown checking"""
        # Mock database query
        cooldown_manager.db["leader_schedule"].find.return_value = []
        
        # Check cooldown for entity with no recent slots
        is_cooldown, last_slot = await cooldown_manager.is_entity_in_cooldown("node1", 100)
        
        assert is_cooldown is False
        assert last_slot is None
    
    @pytest.mark.asyncio
    async def test_cooldown_check_with_recent_slots(self, cooldown_manager):
        """Test cooldown checking with recent slots"""
        # Mock database query with recent slot
        mock_recent_slots = [
            {"primary": "node1", "slot": 95}  # Within cooldown period
        ]
        cooldown_manager.db["leader_schedule"].find.return_value = mock_recent_slots
        
        # Check cooldown for entity with recent slot
        is_cooldown, last_slot = await cooldown_manager.is_entity_in_cooldown("node1", 100)
        
        assert is_cooldown is True
        assert last_slot == 95
    
    @pytest.mark.asyncio
    async def test_leader_selection_with_tallies(self, leader_selector):
        """Test leader selection with work credits tallies"""
        # Mock work credits tallies
        mock_tallies = [
            {
                "_id": "1_node1",
                "epoch": 1,
                "entityId": "node1",
                "credits": 100,
                "liveScore": 0.9,
                "rank": 1
            },
            {
                "_id": "1_node2",
                "epoch": 1,
                "entityId": "node2",
                "credits": 80,
                "liveScore": 0.8,
                "rank": 2
            }
        ]
        
        # Mock database queries
        leader_selector.db["work_tally"].find.return_value = mock_tallies
        leader_selector.db["leader_schedule"].find.return_value = []
        leader_selector.db["leader_schedule"].replace_one = AsyncMock()
        
        # Select leader
        schedule = await leader_selector.select_leader(slot=100, epoch=1)
        
        assert schedule is not None
        assert schedule.slot == 100
        assert schedule.primary in ["node1", "node2"]
        assert len(schedule.fallbacks) > 0
        assert schedule.reason in [SelectionReason.TOP_RANKED, SelectionReason.VRF_TIEBREAK]


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
