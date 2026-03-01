"""
Unit tests for PoOT (Proof of Operational Tasks) consensus engine.

Tests work credits calculation, leader selection with cooldown, and consensus parameters
according to Spec-1b lines 129-157.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any

from blockchain.core.blockchain_engine import PoOTConsensusEngine
from blockchain.core.models import WorkCredit, LeaderSchedule, TaskProof


class TestPoOTConsensusEngine:
    """Test PoOT consensus engine functionality."""
    
    @pytest.fixture
    async def consensus_engine(self):
        """Create a PoOT consensus engine for testing."""
        mock_db = AsyncMock()
        engine = PoOTConsensusEngine(mock_db)
        return engine
    
    @pytest.fixture
    def sample_task_proofs(self) -> List[TaskProof]:
        """Sample task proofs for testing."""
        return [
            TaskProof(
                node_id="node_001",
                pool_id=None,
                slot=1000,
                type="relay_bandwidth",
                value={"bytes_transferred": 5000000},  # 5MB
                sig="0x123...",
                ts=datetime.now()
            ),
            TaskProof(
                node_id="node_002",
                pool_id="pool_001",
                slot=1000,
                type="storage_availability",
                value={"chunks_stored": 100, "size_bytes": 1000000},
                sig="0x456...",
                ts=datetime.now()
            ),
            TaskProof(
                node_id="node_001",
                pool_id=None,
                slot=1001,
                type="validation_signature",
                value={"validated_sessions": 5},
                sig="0x789...",
                ts=datetime.now()
            ),
            TaskProof(
                node_id="node_003",
                pool_id=None,
                slot=1001,
                type="uptime_beacon",
                value={"uptime_seconds": 3600},  # 1 hour
                sig="0xabc...",
                ts=datetime.now()
            )
        ]
    
    @pytest.mark.asyncio
    async def test_work_credits_calculation(self, consensus_engine, sample_task_proofs):
        """Test work credits calculation according to Spec-1b work formula."""
        # Mock database queries
        consensus_engine.db.task_proofs.find.return_value.to_list = AsyncMock(
            return_value=sample_task_proofs
        )
        
        # Test work credits calculation
        work_credits = await consensus_engine.calculate_work_credits(
            entity_id="node_001",
            start_slot=1000,
            end_slot=1001
        )
        
        # Verify work formula: W_t = max(S_t, ceil(B_t / BASE_MB_PER_SESSION))
        # For node_001: relay_bandwidth (5MB) + validation_signature (5 sessions)
        expected_storage_credits = 5  # validation_signature sessions
        expected_bandwidth_credits = max(1, 5000000 // (5 * 1024 * 1024))  # 5MB / 5MB base
        expected_credits = max(expected_storage_credits, expected_bandwidth_credits)
        
        assert work_credits.entity_id == "node_001"
        assert work_credits.credits == expected_credits
        assert work_credits.live_score > 0
    
    @pytest.mark.asyncio
    async def test_leader_selection_with_cooldown(self, consensus_engine):
        """Test leader selection with cooldown mechanism (Spec-1b lines 135-157)."""
        # Mock work credits data
        mock_work_credits = [
            WorkCredit(entity_id="node_001", credits=1000, live_score=0.95, rank=1),
            WorkCredit(entity_id="node_002", credits=950, live_score=0.90, rank=2),
            WorkCredit(entity_id="node_003", credits=900, live_score=0.85, rank=3),
            WorkCredit(entity_id="node_001", credits=1000, live_score=0.95, rank=1),  # In cooldown
        ]
        
        consensus_engine.db.work_tally.find.return_value.to_list = AsyncMock(
            return_value=mock_work_credits
        )
        
        # Mock cooldown check
        with patch.object(consensus_engine, 'is_entity_in_cooldown') as mock_cooldown:
            mock_cooldown.side_effect = lambda entity_id, slot: entity_id == "node_001"
            
            leader_schedule = await consensus_engine.select_leader(slot=1005)
            
            # Should select node_002 (rank 2) since node_001 is in cooldown
            assert leader_schedule.primary == "node_002"
            assert "node_001" in leader_schedule.fallbacks
            assert leader_schedule.result["reason"] == "cooldown_skip"
    
    @pytest.mark.asyncio
    async def test_leader_selection_vrf_tie_breaking(self, consensus_engine):
        """Test VRF tie-breaking for entities with equal work credits."""
        # Mock work credits with ties
        mock_work_credits = [
            WorkCredit(entity_id="node_001", credits=1000, live_score=0.95, rank=1),
            WorkCredit(entity_id="node_002", credits=1000, live_score=0.95, rank=1),
            WorkCredit(entity_id="node_003", credits=1000, live_score=0.95, rank=1),
        ]
        
        consensus_engine.db.work_tally.find.return_value.to_list = AsyncMock(
            return_value=mock_work_credits
        )
        
        # Mock VRF selection
        with patch.object(consensus_engine, 'vrf_select_leader') as mock_vrf:
            mock_vrf.return_value = "node_002"
            
            leader_schedule = await consensus_engine.select_leader(slot=1000)
            
            assert leader_schedule.primary == "node_002"
            assert leader_schedule.result["reason"] == "vrf_tie_break"
    
    @pytest.mark.asyncio
    async def test_consensus_parameters_immutable(self, consensus_engine):
        """Test that consensus parameters are immutable (Spec-1b line 170)."""
        # Verify immutable parameters
        assert consensus_engine.SLOT_DURATION_SEC == 120
        assert consensus_engine.SLOT_TIMEOUT_MS == 5000
        assert consensus_engine.COOLDOWN_SLOTS == 16
        assert consensus_engine.LEADER_WINDOW_DAYS == 7
        assert consensus_engine.D_MIN == 0.2
        assert consensus_engine.BASE_MB_PER_SESSION == 5
        
        # Verify parameters cannot be changed
        with pytest.raises(AttributeError):
            consensus_engine.SLOT_DURATION_SEC = 60
    
    @pytest.mark.asyncio
    async def test_task_proof_validation(self, consensus_engine):
        """Test task proof validation and storage."""
        task_proof = TaskProof(
            node_id="node_001",
            pool_id=None,
            slot=1000,
            type="relay_bandwidth",
            value={"bytes_transferred": 5000000},
            sig="0x1234567890abcdef",
            ts=datetime.now()
        )
        
        # Mock signature validation
        with patch.object(consensus_engine, 'validate_signature') as mock_validate:
            mock_validate.return_value = True
            
            result = await consensus_engine.submit_task_proof(task_proof)
            
            assert result is True
            consensus_engine.db.task_proofs.insert_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_leader_schedule_persistence(self, consensus_engine):
        """Test leader schedule persistence in MongoDB."""
        leader_schedule = LeaderSchedule(
            slot=1000,
            primary="node_001",
            fallbacks=["node_002", "node_003"],
            result={"winner": "node_001", "reason": "highest_credits"}
        )
        
        await consensus_engine.persist_leader_schedule(leader_schedule)
        
        consensus_engine.db.leader_schedule.insert_one.assert_called_once_with(
            {
                "slot": 1000,
                "primary": "node_001",
                "fallbacks": ["node_002", "node_003"],
                "result": {"winner": "node_001", "reason": "highest_credits"}
            }
        )
    
    @pytest.mark.asyncio
    async def test_work_credits_window_calculation(self, consensus_engine):
        """Test work credits calculation over sliding window (7 days default)."""
        # Mock current slot calculation
        with patch.object(consensus_engine, 'get_current_slot') as mock_current_slot:
            mock_current_slot.return_value = 10080  # 7 days worth of 120s slots
            
            start_slot, end_slot = consensus_engine.calculate_work_window()
            
            # Should calculate 7 days worth of slots
            expected_slots = 7 * 24 * 60 * 60 // 120  # 7 days in 120s slots
            assert end_slot - start_slot == expected_slots
    
    @pytest.mark.asyncio
    async def test_density_threshold_enforcement(self, consensus_engine):
        """Test minimum density threshold D_MIN enforcement."""
        # Mock work credits with low density
        mock_work_credits = [
            WorkCredit(entity_id="node_001", credits=100, live_score=0.1, rank=1),  # Below D_MIN
        ]
        
        consensus_engine.db.work_tally.find.return_value.to_list = AsyncMock(
            return_value=mock_work_credits
        )
        
        # Should not select leaders below density threshold
        with patch.object(consensus_engine, 'is_entity_in_cooldown', return_value=False):
            leader_schedule = await consensus_engine.select_leader(slot=1000)
            
            # Should have no valid leader due to density threshold
            assert leader_schedule.primary is None
            assert leader_schedule.result["reason"] == "density_threshold_not_met"


if __name__ == "__main__":
    pytest.main([__file__])
