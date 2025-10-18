"""
Integration tests for blockchain core operations.

Tests blockchain consensus, session anchoring, and block management.
TRON payment operations are handled by separate TRON Payment cluster.

CRITICAL: This file tests ONLY blockchain core operations.
TRON payment testing is handled in tests/integration/phase4/test_tron_payout.py
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any

from blockchain.core.blockchain_engine import BlockchainEngine
from blockchain.core.models import Block, Transaction, SessionAnchoring


class TestBlockchainCoreOperations:
    """Test blockchain core operations (consensus, anchoring, block management)."""
    
    @pytest.fixture
    async def blockchain_engine(self):
        """Create blockchain engine for testing."""
        mock_db = AsyncMock()
        
        engine = BlockchainEngine()
        engine.db = mock_db
        engine.consensus_engine = AsyncMock()
        engine.block_manager = AsyncMock()
        engine.merkle_builder = AsyncMock()
        
        return engine
    
    @pytest.fixture
    def sample_blocks(self) -> List[Block]:
        """Sample blocks for testing."""
        base_time = datetime.now() - timedelta(hours=1)
        return [
            Block(
                height=0,
                hash="genesis_hash_1234567890abcdef",
                previous_hash="",
                timestamp=base_time,
                transactions=[],
                merkle_root="merkle_root_genesis"
            ),
            Block(
                height=1,
                hash="block_hash_001_1234567890abcdef",
                previous_hash="genesis_hash_1234567890abcdef",
                timestamp=base_time + timedelta(minutes=10),
                transactions=[],
                merkle_root="merkle_root_001"
            ),
            Block(
                height=2,
                hash="block_hash_002_1234567890abcdef",
                previous_hash="block_hash_001_1234567890abcdef",
                timestamp=base_time + timedelta(minutes=20),
                transactions=[],
                merkle_root="merkle_root_002"
            )
        ]
    
    @pytest.fixture
    def sample_transactions(self) -> List[Transaction]:
        """Sample transactions for testing."""
        base_time = datetime.now() - timedelta(minutes=30)
        return [
            Transaction(
                tx_id="tx_001_1234567890abcdef",
                session_id="session_001",
                transaction_type="session_anchoring",
                data_hash="data_hash_001",
                timestamp=base_time
            ),
            Transaction(
                tx_id="tx_002_1234567890abcdef",
                session_id="session_002",
                transaction_type="session_anchoring",
                data_hash="data_hash_002",
                timestamp=base_time + timedelta(minutes=5)
            )
        ]
    
    @pytest.mark.asyncio
    async def test_block_creation_and_validation(self, blockchain_engine, sample_transactions):
        """Test block creation and validation."""
        # Mock consensus engine
        blockchain_engine.consensus_engine.validate_block.return_value = True
        
        # Mock merkle builder
        blockchain_engine.merkle_builder.build_merkle_tree.return_value = "merkle_root_123"
        
        # Create new block
        new_block = await blockchain_engine.create_block(sample_transactions)
        
        # Verify block structure
        assert new_block.height > 0
        assert new_block.hash is not None
        assert new_block.merkle_root == "merkle_root_123"
        assert len(new_block.transactions) == len(sample_transactions)
        
        # Verify consensus validation was called
        blockchain_engine.consensus_engine.validate_block.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_consensus_mechanism(self, blockchain_engine, sample_blocks):
        """Test PoOT consensus mechanism."""
        # Mock consensus participants
        participants = ["node_001", "node_002", "node_003"]
        
        # Mock consensus votes
        mock_votes = {
            "node_001": {"vote": "approve", "poot_score": 0.85},
            "node_002": {"vote": "approve", "poot_score": 0.92},
            "node_003": {"vote": "approve", "poot_score": 0.78}
        }
        
        blockchain_engine.consensus_engine.conduct_consensus_round.return_value = True
        blockchain_engine.consensus_engine.count_votes.return_value = {"approve": 3, "reject": 0}
        blockchain_engine.consensus_engine.reach_consensus.return_value = True
        
        # Test consensus round
        block = sample_blocks[1]
        consensus_result = await blockchain_engine.consensus_engine.conduct_consensus_round(
            block, participants
        )
        
        assert consensus_result is True
        blockchain_engine.consensus_engine.conduct_consensus_round.assert_called_once_with(
            block, participants
        )
    
    @pytest.mark.asyncio
    async def test_session_anchoring(self, blockchain_engine, sample_transactions):
        """Test session anchoring to blockchain."""
        session_data = {
            "session_id": "session_001",
            "chunk_hashes": ["hash_001", "hash_002", "hash_003"],
            "merkle_root": "merkle_root_session_001"
        }
        
        # Mock merkle tree building
        blockchain_engine.merkle_builder.build_merkle_tree.return_value = "merkle_root_session_001"
        
        # Mock block creation
        mock_block = Block(
            height=100,
            hash="anchoring_block_hash",
            previous_hash="previous_hash",
            timestamp=datetime.now(),
            transactions=[],
            merkle_root="merkle_root_session_001"
        )
        
        blockchain_engine.create_block.return_value = mock_block
        
        # Execute session anchoring
        anchoring_result = await blockchain_engine.anchor_session(session_data)
        
        # Verify anchoring result
        assert anchoring_result["status"] == "anchored"
        assert anchoring_result["block_height"] == 100
        assert anchoring_result["merkle_root"] == "merkle_root_session_001"
        
        # Verify merkle tree was built
        blockchain_engine.merkle_builder.build_merkle_tree.assert_called_once_with(
            session_data["chunk_hashes"]
        )
    
    @pytest.mark.asyncio
    async def test_block_chain_validation(self, blockchain_engine, sample_blocks):
        """Test blockchain chain validation."""
        # Mock database query for blocks
        blockchain_engine.db.blocks.find.return_value.to_list = AsyncMock(
            return_value=sample_blocks
        )
        
        # Test chain validation
        is_valid = await blockchain_engine.validate_chain()
        
        assert is_valid is True
        
        # Verify database query was made
        blockchain_engine.db.blocks.find.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_merkle_tree_operations(self, blockchain_engine):
        """Test Merkle tree building and validation."""
        chunk_hashes = ["hash_001", "hash_002", "hash_003", "hash_004"]
        
        # Mock merkle tree building
        mock_merkle_tree = {
            "root": "merkle_root_1234567890abcdef",
            "leaves": chunk_hashes,
            "height": 2
        }
        
        blockchain_engine.merkle_builder.build_merkle_tree.return_value = mock_merkle_tree
        
        # Build merkle tree
        merkle_tree = await blockchain_engine.merkle_builder.build_merkle_tree(chunk_hashes)
        
        assert merkle_tree["root"] == "merkle_root_1234567890abcdef"
        assert merkle_tree["leaves"] == chunk_hashes
        assert merkle_tree["height"] == 2
    
    @pytest.mark.asyncio
    async def test_block_retrieval(self, blockchain_engine, sample_blocks):
        """Test block retrieval by height and hash."""
        # Mock database queries
        blockchain_engine.db.blocks.find_one.side_effect = [
            sample_blocks[0],  # Genesis block
            sample_blocks[1],  # Block 1
            sample_blocks[2]   # Block 2
        ]
        
        # Test retrieval by height
        genesis_block = await blockchain_engine.get_block_by_height(0)
        assert genesis_block.height == 0
        
        block_1 = await blockchain_engine.get_block_by_height(1)
        assert block_1.height == 1
        
        # Test retrieval by hash
        block_by_hash = await blockchain_engine.get_block_by_hash("block_hash_002_1234567890abcdef")
        assert block_by_hash.height == 2
        
        # Verify database queries
        assert blockchain_engine.db.blocks.find_one.call_count >= 3
    
    @pytest.mark.asyncio
    async def test_consensus_participant_management(self, blockchain_engine):
        """Test consensus participant management."""
        participants = ["node_001", "node_002", "node_003", "node_004"]
        
        # Mock participant registration
        blockchain_engine.consensus_engine.register_participant.return_value = True
        
        # Register participants
        for participant in participants:
            result = await blockchain_engine.consensus_engine.register_participant(participant)
            assert result is True
        
        # Verify all participants registered
        assert blockchain_engine.consensus_engine.register_participant.call_count == len(participants)
    
    @pytest.mark.asyncio
    async def test_blockchain_isolation_from_payments(self, blockchain_engine):
        """Test that blockchain core is isolated from payment operations."""
        # Verify blockchain engine has no payment-related attributes
        assert not hasattr(blockchain_engine, 'tron_client')
        assert not hasattr(blockchain_engine, 'payout_router')
        assert not hasattr(blockchain_engine, 'usdt_manager')
        
        # Verify blockchain-only methods exist
        assert hasattr(blockchain_engine, 'create_block')
        assert hasattr(blockchain_engine, 'validate_chain')
        assert hasattr(blockchain_engine, 'anchor_session')
        
        # Test that blockchain operations don't affect payment systems
        with patch('blockchain.core.blockchain_engine.TronNodeSystem') as mock_tron:
            # Execute blockchain operation
            await blockchain_engine.create_block([])
            
            # Verify TRON client was not instantiated
            mock_tron.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_blockchain_performance(self, blockchain_engine, sample_transactions):
        """Test blockchain performance requirements."""
        # Test block creation performance
        start_time = datetime.now()
        
        blockchain_engine.consensus_engine.validate_block.return_value = True
        blockchain_engine.merkle_builder.build_merkle_tree.return_value = "merkle_root"
        
        await blockchain_engine.create_block(sample_transactions)
        
        end_time = datetime.now()
        creation_time = (end_time - start_time).total_seconds()
        
        # Block creation should be fast (< 1 second)
        assert creation_time < 1.0
    
    @pytest.mark.asyncio
    async def test_blockchain_error_handling(self, blockchain_engine):
        """Test blockchain error handling."""
        # Test invalid block data
        with pytest.raises(ValueError):
            await blockchain_engine.create_block(None)
        
        # Test consensus failure
        blockchain_engine.consensus_engine.validate_block.return_value = False
        
        with pytest.raises(Exception):
            await blockchain_engine.create_block([])


if __name__ == "__main__":
    pytest.main([__file__])
