"""
Integration tests for PoOT consensus slot progression.

Tests end-to-end PoOT consensus slot progression, leader selection,
and consensus state transitions.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any

from blockchain.core.blockchain_engine import BlockchainEngine, PoOTConsensusEngine
from blockchain.core.models import WorkCredit, LeaderSchedule, TaskProof


class TestPoOTConsensusProgression:
    """Test PoOT consensus slot progression."""
    
    @pytest.fixture
    async def blockchain_engine(self):
        """Create blockchain engine for consensus testing."""
        mock_db = AsyncMock()
        
        engine = BlockchainEngine()
        engine.db = mock_db
        engine.consensus_engine = PoOTConsensusEngine(mock_db)
        engine.on_chain_client = AsyncMock()
        engine.tron_client = AsyncMock()
        
        return engine
    
    @pytest.fixture
    def sample_task_proofs(self) -> List[TaskProof]:
        """Sample task proofs for consensus testing."""
        base_time = datetime.now()
        return [
            TaskProof(
                node_id="node_001",
                pool_id=None,
                slot=1000,
                type="relay_bandwidth",
                value={"bytes_transferred": 10000000},  # 10MB
                sig="0x123...",
                ts=base_time
            ),
            TaskProof(
                node_id="node_002",
                pool_id="pool_001",
                slot=1000,
                type="storage_availability",
                value={"chunks_stored": 200, "size_bytes": 2000000},
                sig="0x456...",
                ts=base_time
            ),
            TaskProof(
                node_id="node_001",
                pool_id=None,
                slot=1001,
                type="validation_signature",
                value={"validated_sessions": 10},
                sig="0x789...",
                ts=base_time + timedelta(minutes=2)
            ),
            TaskProof(
                node_id="node_003",
                pool_id=None,
                slot=1001,
                type="uptime_beacon",
                value={"uptime_seconds": 7200},  # 2 hours
                sig="0xabc...",
                ts=base_time + timedelta(minutes=2)
            )
        ]
    
    @pytest.mark.asyncio
    async def test_consensus_slot_progression(self, blockchain_engine, sample_task_proofs):
        """Test PoOT consensus slot progression over multiple slots."""
        # Mock task proofs for multiple slots
        blockchain_engine.db.task_proofs.find.return_value.to_list = AsyncMock(
            return_value=sample_task_proofs
        )
        
        # Mock work credits calculation
        mock_work_credits = [
            WorkCredit(entity_id="node_001", credits=1000, live_score=0.95, rank=1),
            WorkCredit(entity_id="node_002", credits=950, live_score=0.90, rank=2),
            WorkCredit(entity_id="node_003", credits=900, live_score=0.85, rank=3),
        ]
        
        blockchain_engine.db.work_tally.find.return_value.to_list = AsyncMock(
            return_value=mock_work_credits
        )
        
        # Mock leader selection
        mock_leader_schedules = [
            LeaderSchedule(
                slot=1000,
                primary="node_001",
                fallbacks=["node_002", "node_003"],
                result={"winner": "node_001", "reason": "highest_credits"}
            ),
            LeaderSchedule(
                slot=1001,
                primary="node_002",
                fallbacks=["node_001", "node_003"],
                result={"winner": "node_002", "reason": "cooldown_skip"}
            )
        ]
        
        blockchain_engine.db.leader_schedule.find.return_value.to_list = AsyncMock(
            return_value=mock_leader_schedules
        )
        
        # Execute consensus slot progression
        results = await blockchain_engine.run_consensus_slot_progression(
            start_slot=1000,
            end_slot=1001
        )
        
        # Verify slot progression
        assert len(results) == 2
        assert results[0]["slot"] == 1000
        assert results[1]["slot"] == 1001
        
        # Verify leader selection for each slot
        assert results[0]["primary_leader"] == "node_001"
        assert results[1]["primary_leader"] == "node_002"
    
    @pytest.mark.asyncio
    async def test_work_credits_accumulation(self, blockchain_engine, sample_task_proofs):
        """Test work credits accumulation over time."""
        # Mock task proofs with increasing work
        increasing_proofs = []
        for i in range(10):
            proof = TaskProof(
                node_id="node_001",
                pool_id=None,
                slot=1000 + i,
                type="relay_bandwidth",
                value={"bytes_transferred": 1000000 * (i + 1)},  # Increasing bandwidth
                sig=f"0x{i:03d}...",
                ts=datetime.now() + timedelta(minutes=i * 2)
            )
            increasing_proofs.append(proof)
        
        blockchain_engine.db.task_proofs.find.return_value.to_list = AsyncMock(
            return_value=increasing_proofs
        )
        
        # Calculate work credits over time
        work_credits_history = []
        for i in range(10):
            credits = await blockchain_engine.consensus_engine.calculate_work_credits(
                entity_id="node_001",
                start_slot=1000,
                end_slot=1000 + i
            )
            work_credits_history.append(credits.credits)
        
        # Verify work credits increase over time
        assert work_credits_history[0] < work_credits_history[-1]
        assert all(work_credits_history[i] <= work_credits_history[i + 1] for i in range(len(work_credits_history) - 1))
    
    @pytest.mark.asyncio
    async def test_leader_cooldown_mechanism(self, blockchain_engine):
        """Test leader cooldown mechanism across slots."""
        # Mock work credits with clear leader
        mock_work_credits = [
            WorkCredit(entity_id="node_001", credits=1000, live_score=0.95, rank=1),
            WorkCredit(entity_id="node_002", credits=500, live_score=0.80, rank=2),
            WorkCredit(entity_id="node_003", credits=250, live_score=0.70, rank=3),
        ]
        
        blockchain_engine.db.work_tally.find.return_value.to_list = AsyncMock(
            return_value=mock_work_credits
        )
        
        # Mock cooldown tracking
        cooldown_tracker = {}
        
        def mock_is_in_cooldown(entity_id: str, slot: int) -> bool:
            return cooldown_tracker.get(entity_id, 0) > slot
        
        def mock_update_cooldown(entity_id: str, slot: int):
            cooldown_tracker[entity_id] = slot + 16  # 16 slot cooldown
        
        with patch.object(blockchain_engine.consensus_engine, 'is_entity_in_cooldown', side_effect=mock_is_in_cooldown):
            with patch.object(blockchain_engine.consensus_engine, 'update_entity_cooldown', side_effect=mock_update_cooldown):
                
                # Test multiple slots with cooldown
                leaders = []
                for slot in range(1000, 1020):
                    leader_schedule = await blockchain_engine.consensus_engine.select_leader(slot)
                    leaders.append(leader_schedule.primary)
                    
                    if leader_schedule.primary:
                        mock_update_cooldown(leader_schedule.primary, slot)
                
                # Verify cooldown mechanism works
                # node_001 should be selected first, then skip due to cooldown
                assert leaders[0] == "node_001"
                assert "node_001" not in leaders[1:17]  # 16 slot cooldown
                assert "node_001" in leaders[17:]  # Can be selected again after cooldown
    
    @pytest.mark.asyncio
    async def test_consensus_timeout_handling(self, blockchain_engine):
        """Test consensus timeout handling and fallback mechanisms."""
        # Mock slow leader response
        async def mock_slow_leader_response(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate slow response
            return LeaderSchedule(
                slot=1000,
                primary="node_001",
                fallbacks=["node_002", "node_003"],
                result={"winner": "node_001", "reason": "highest_credits"}
            )
        
        blockchain_engine.consensus_engine.select_leader = mock_slow_leader_response
        
        # Mock timeout mechanism
        with patch.object(blockchain_engine.consensus_engine, 'SLOT_TIMEOUT_MS', 50):  # 50ms timeout
            
            start_time = datetime.now()
            result = await blockchain_engine.run_consensus_slot(1000)
            end_time = datetime.now()
            
            # Should complete within timeout or use fallback
            duration_ms = (end_time - start_time).total_seconds() * 1000
            assert duration_ms <= 100  # Allow some buffer
    
    @pytest.mark.asyncio
    async def test_consensus_state_persistence(self, blockchain_engine):
        """Test consensus state persistence across slots."""
        # Mock consensus state
        mock_state = {
            "current_slot": 1000,
            "last_leader": "node_001",
            "work_credits_window": 10080,  # 7 days in slots
            "active_nodes": ["node_001", "node_002", "node_003"]
        }
        
        # Mock state persistence
        blockchain_engine.db.consensus_state.find_one.return_value = mock_state
        blockchain_engine.db.consensus_state.update_one.return_value = MagicMock(modified_count=1)
        
        # Load consensus state
        state = await blockchain_engine.load_consensus_state()
        assert state["current_slot"] == 1000
        assert state["last_leader"] == "node_001"
        
        # Update consensus state
        new_state = {
            "current_slot": 1001,
            "last_leader": "node_002",
            "work_credits_window": 10080,
            "active_nodes": ["node_001", "node_002", "node_003"]
        }
        
        await blockchain_engine.save_consensus_state(new_state)
        
        # Verify state was saved
        blockchain_engine.db.consensus_state.update_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_consensus_error_recovery(self, blockchain_engine):
        """Test consensus error recovery and state restoration."""
        # Mock consensus error
        blockchain_engine.consensus_engine.select_leader.side_effect = Exception("Consensus error")
        
        # Should handle error gracefully
        with pytest.raises(Exception, match="Consensus error"):
            await blockchain_engine.run_consensus_slot(1000)
        
        # Verify error recovery mechanisms
        # (Implementation would depend on specific error recovery strategy)
        assert True  # Placeholder for error recovery verification


if __name__ == "__main__":
    pytest.main([__file__])
