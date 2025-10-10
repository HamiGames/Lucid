"""
Integration tests for end-to-end session anchoring flow.

Tests complete session lifecycle from creation to On-System Chain anchoring
with LucidAnchors contract integration.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any

from blockchain.core.blockchain_engine import BlockchainEngine, OnSystemChainClient
from blockchain.core.models import SessionManifest, ChunkMetadata, SessionAnchor


class TestSessionAnchoringFlow:
    """Test end-to-end session anchoring flow."""
    
    @pytest.fixture
    async def blockchain_engine(self):
        """Create blockchain engine for integration testing."""
        mock_db = AsyncMock()
        mock_on_chain_client = AsyncMock(spec=OnSystemChainClient)
        
        engine = BlockchainEngine()
        engine.db = mock_db
        engine.on_chain_client = mock_on_chain_client
        engine.tron_client = AsyncMock()  # Isolated payment service
        
        return engine
    
    @pytest.fixture
    def sample_session_data(self) -> Dict[str, Any]:
        """Sample session data for testing."""
        return {
            "session_id": "session_integration_001",
            "owner_address": "0xowner1234567890abcdef1234567890abcdef123456",
            "started_at": datetime.now(),
            "chunks": [
                {
                    "idx": 0,
                    "local_path": "/chunks/chunk_000",
                    "ciphertext_sha256": "0xchunk0001234567890abcdef1234567890abcdef123456",
                    "size_bytes": 1048576
                },
                {
                    "idx": 1,
                    "local_path": "/chunks/chunk_001",
                    "ciphertext_sha256": "0xchunk0011234567890abcdef1234567890abcdef123456",
                    "size_bytes": 2097152
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_complete_session_anchoring_flow(self, blockchain_engine, sample_session_data):
        """Test complete session anchoring flow from creation to On-System Chain."""
        # Mock On-System Chain contract calls
        mock_anchor_result = {
            "txid": "0xtx1234567890abcdef1234567890abcdef123456",
            "block_number": 12345,
            "gas_used": 150000,
            "status": "success"
        }
        
        mock_chunk_results = [
            {
                "txid": "0xtxchunk0001234567890abcdef1234567890abcdef123456",
                "block_number": 12346,
                "gas_used": 80000,
                "status": "success"
            },
            {
                "txid": "0xtxchunk0011234567890abcdef1234567890abcdef123456",
                "block_number": 12347,
                "gas_used": 90000,
                "status": "success"
            }
        ]
        
        blockchain_engine.on_chain_client.register_session.return_value = mock_anchor_result
        blockchain_engine.on_chain_client.store_chunk_metadata.side_effect = mock_chunk_results
        
        # Mock database operations
        blockchain_engine.db.sessions.insert_one.return_value = MagicMock(inserted_id="session_001")
        blockchain_engine.db.chunks.insert_many.return_value = MagicMock(inserted_ids=["chunk_001", "chunk_002"])
        
        # Execute complete session anchoring flow
        result = await blockchain_engine.anchor_session_flow(sample_session_data)
        
        # Verify session manifest creation
        assert result["session_id"] == sample_session_data["session_id"]
        assert result["manifest_hash"] is not None
        assert result["merkle_root"] is not None
        
        # Verify On-System Chain anchoring
        blockchain_engine.on_chain_client.register_session.assert_called_once()
        assert result["anchor_txid"] == mock_anchor_result["txid"]
        assert result["block_number"] == mock_anchor_result["block_number"]
        
        # Verify chunk metadata storage
        assert blockchain_engine.on_chain_client.store_chunk_metadata.call_count == 2
        
        # Verify database persistence
        blockchain_engine.db.sessions.insert_one.assert_called_once()
        blockchain_engine.db.chunks.insert_many.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_session_anchoring_with_retry_mechanism(self, blockchain_engine, sample_session_data):
        """Test session anchoring with retry mechanism for failed transactions."""
        # Mock first call failure, second call success
        mock_failure = Exception("Transaction failed")
        mock_success = {
            "txid": "0xtx1234567890abcdef1234567890abcdef123456",
            "block_number": 12345,
            "gas_used": 150000,
            "status": "success"
        }
        
        blockchain_engine.on_chain_client.register_session.side_effect = [mock_failure, mock_success]
        
        # Execute session anchoring with retry
        result = await blockchain_engine.anchor_session_flow(
            sample_session_data,
            max_retries=3,
            retry_delay=1
        )
        
        # Verify retry mechanism worked
        assert blockchain_engine.on_chain_client.register_session.call_count == 2
        assert result["anchor_txid"] == mock_success["txid"]
    
    @pytest.mark.asyncio
    async def test_session_anchoring_gas_optimization(self, blockchain_engine, sample_session_data):
        """Test session anchoring gas optimization and circuit breakers."""
        # Mock gas estimation
        blockchain_engine.on_chain_client.estimate_gas.return_value = 200000
        
        # Mock gas limit circuit breaker
        blockchain_engine.on_chain_client.gas_limit = 180000
        
        # Should fail due to gas limit
        with pytest.raises(Exception, match="Gas limit exceeded"):
            await blockchain_engine.anchor_session_flow(sample_session_data)
    
    @pytest.mark.asyncio
    async def test_session_anchoring_merkle_root_validation(self, blockchain_engine, sample_session_data):
        """Test Merkle root validation during session anchoring."""
        # Mock Merkle root calculation
        expected_merkle_root = "0xmerkle1234567890abcdef1234567890abcdef123456"
        blockchain_engine.on_chain_client.calculate_merkle_root.return_value = expected_merkle_root
        
        # Mock contract call with Merkle root
        mock_anchor_result = {
            "txid": "0xtx1234567890abcdef1234567890abcdef123456",
            "block_number": 12345,
            "gas_used": 150000,
            "status": "success"
        }
        
        blockchain_engine.on_chain_client.register_session.return_value = mock_anchor_result
        
        result = await blockchain_engine.anchor_session_flow(sample_session_data)
        
        # Verify Merkle root was calculated and used
        blockchain_engine.on_chain_client.calculate_merkle_root.assert_called_once()
        assert result["merkle_root"] == expected_merkle_root
        
        # Verify Merkle root was passed to contract
        call_args = blockchain_engine.on_chain_client.register_session.call_args
        assert call_args[1]["merkle_root"] == expected_merkle_root
    
    @pytest.mark.asyncio
    async def test_session_anchoring_event_monitoring(self, blockchain_engine, sample_session_data):
        """Test session anchoring event monitoring and status updates."""
        # Mock successful anchoring
        mock_anchor_result = {
            "txid": "0xtx1234567890abcdef1234567890abcdef123456",
            "block_number": 12345,
            "gas_used": 150000,
            "status": "success"
        }
        
        blockchain_engine.on_chain_client.register_session.return_value = mock_anchor_result
        
        # Mock event monitoring
        mock_events = [
            {
                "address": "0x1234567890abcdef1234567890abcdef12345678",
                "topics": ["0xSessionRegistered"],
                "data": "0x" + sample_session_data["session_id"],
                "blockNumber": 12345,
                "transactionHash": mock_anchor_result["txid"]
            }
        ]
        
        blockchain_engine.on_chain_client.get_session_registration_events.return_value = mock_events
        
        result = await blockchain_engine.anchor_session_flow(sample_session_data)
        
        # Verify event monitoring
        blockchain_engine.on_chain_client.get_session_registration_events.assert_called_once()
        assert result["events_detected"] == 1
    
    @pytest.mark.asyncio
    async def test_session_anchoring_database_consistency(self, blockchain_engine, sample_session_data):
        """Test database consistency during session anchoring."""
        # Mock successful anchoring
        mock_anchor_result = {
            "txid": "0xtx1234567890abcdef1234567890abcdef123456",
            "block_number": 12345,
            "gas_used": 150000,
            "status": "success"
        }
        
        blockchain_engine.on_chain_client.register_session.return_value = mock_anchor_result
        
        # Mock database transaction
        mock_db_session = AsyncMock()
        blockchain_engine.db.start_session.return_value.__aenter__.return_value = mock_db_session
        
        result = await blockchain_engine.anchor_session_flow(sample_session_data)
        
        # Verify database transaction was used
        blockchain_engine.db.start_session.assert_called_once()
        
        # Verify session and chunks were inserted in transaction
        mock_db_session.sessions.insert_one.assert_called_once()
        mock_db_session.chunks.insert_many.assert_called_once()
        
        # Verify transaction was committed
        mock_db_session.commit_transaction.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_session_anchoring_error_recovery(self, blockchain_engine, sample_session_data):
        """Test session anchoring error recovery and rollback."""
        # Mock database transaction failure
        mock_db_session = AsyncMock()
        mock_db_session.sessions.insert_one.side_effect = Exception("Database error")
        blockchain_engine.db.start_session.return_value.__aenter__.return_value = mock_db_session
        
        # Should handle error and rollback
        with pytest.raises(Exception, match="Database error"):
            await blockchain_engine.anchor_session_flow(sample_session_data)
        
        # Verify rollback was called
        mock_db_session.abort_transaction.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
