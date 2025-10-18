"""
Unit tests for session anchoring to On-System Chain.

Tests LucidAnchors contract integration, event-based anchoring, and status monitoring
according to Spec-1b lines 56-59.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from blockchain.core.blockchain_engine import OnSystemChainClient, SessionAnchor
from blockchain.core.models import SessionManifest, ChunkMetadata


class TestSessionAnchoring:
    """Test session anchoring to On-System Chain."""
    
    @pytest.fixture
    async def on_chain_client(self):
        """Create On-System Chain client for testing."""
        mock_rpc_url = "http://test-rpc:8545"
        mock_contracts = {
            "LucidAnchors": "0x1234567890abcdef1234567890abcdef12345678",
            "LucidChunkStore": "0xabcdef1234567890abcdef1234567890abcdef12"
        }
        client = OnSystemChainClient(mock_rpc_url, mock_contracts)
        return client
    
    @pytest.fixture
    def sample_session_manifest(self) -> SessionManifest:
        """Sample session manifest for testing."""
        return SessionManifest(
            session_id="session_001",
            owner_address="0xowner1234567890abcdef1234567890abcdef123456",
            started_at=datetime.now(),
            manifest_hash="0xmanifest1234567890abcdef1234567890abcdef123456",
            merkle_root="0xmerkle1234567890abcdef1234567890abcdef123456",
            chunk_count=100,
            chunks=[
                ChunkMetadata(
                    idx=0,
                    local_path="/chunks/chunk_000",
                    ciphertext_sha256="0xchunk0001234567890abcdef1234567890abcdef123456",
                    size_bytes=1048576
                )
            ]
        )
    
    @pytest.mark.asyncio
    async def test_register_session_contract_call(self, on_chain_client, sample_session_manifest):
        """Test LucidAnchors contract registerSession call."""
        # Mock contract call
        mock_tx_receipt = {
            "transactionHash": "0xtx1234567890abcdef1234567890abcdef123456",
            "blockNumber": 12345,
            "gasUsed": 150000,
            "status": "0x1"
        }
        
        with patch.object(on_chain_client, 'call_contract') as mock_call:
            mock_call.return_value = mock_tx_receipt
            
            result = await on_chain_client.register_session(
                session_id=sample_session_manifest.session_id,
                manifest_hash=sample_session_manifest.manifest_hash,
                started_at=sample_session_manifest.started_at,
                owner=sample_session_manifest.owner_address,
                merkle_root=sample_session_manifest.merkle_root,
                chunk_count=sample_session_manifest.chunk_count
            )
            
            # Verify contract call parameters
            expected_params = [
                sample_session_manifest.session_id,
                sample_session_manifest.manifest_hash,
                int(sample_session_manifest.started_at.timestamp()),
                sample_session_manifest.owner_address,
                sample_session_manifest.merkle_root,
                sample_session_manifest.chunk_count
            ]
            
            mock_call.assert_called_once_with(
                "LucidAnchors",
                "registerSession",
                expected_params
            )
            
            assert result["txid"] == mock_tx_receipt["transactionHash"]
            assert result["block_number"] == mock_tx_receipt["blockNumber"]
            assert result["gas_used"] == mock_tx_receipt["gasUsed"]
    
    @pytest.mark.asyncio
    async def test_gas_estimation_circuit_breaker(self, on_chain_client, sample_session_manifest):
        """Test gas estimation and circuit breaker functionality."""
        # Mock high gas estimation
        with patch.object(on_chain_client, 'estimate_gas') as mock_estimate:
            mock_estimate.return_value = 500000  # Above circuit breaker threshold
            
            with pytest.raises(Exception, match="Gas limit exceeded"):
                await on_chain_client.register_session(
                    session_id=sample_session_manifest.session_id,
                    manifest_hash=sample_session_manifest.manifest_hash,
                    started_at=sample_session_manifest.started_at,
                    owner=sample_session_manifest.owner_address,
                    merkle_root=sample_session_manifest.merkle_root,
                    chunk_count=sample_session_manifest.chunk_count
                )
    
    @pytest.mark.asyncio
    async def test_chunk_metadata_storage(self, on_chain_client, sample_session_manifest):
        """Test LucidChunkStore contract for chunk metadata storage."""
        chunk_metadata = sample_session_manifest.chunks[0]
        
        mock_tx_receipt = {
            "transactionHash": "0xtxchunk1234567890abcdef1234567890abcdef123456",
            "blockNumber": 12346,
            "gasUsed": 80000,
            "status": "0x1"
        }
        
        with patch.object(on_chain_client, 'call_contract') as mock_call:
            mock_call.return_value = mock_tx_receipt
            
            result = await on_chain_client.store_chunk_metadata(
                session_id=sample_session_manifest.session_id,
                chunk_idx=chunk_metadata.idx,
                ciphertext_hash=chunk_metadata.ciphertext_sha256,
                size_bytes=chunk_metadata.size_bytes
            )
            
            expected_params = [
                sample_session_manifest.session_id,
                chunk_metadata.idx,
                chunk_metadata.ciphertext_sha256,
                chunk_metadata.size_bytes
            ]
            
            mock_call.assert_called_once_with(
                "LucidChunkStore",
                "storeChunkMetadata",
                expected_params
            )
            
            assert result["txid"] == mock_tx_receipt["transactionHash"]
    
    @pytest.mark.asyncio
    async def test_event_based_anchoring(self, on_chain_client, sample_session_manifest):
        """Test event-based anchoring for gas efficiency (Spec-1b lines 56-59)."""
        # Mock event logs from contract
        mock_events = [
            {
                "address": "0x1234567890abcdef1234567890abcdef12345678",
                "topics": ["0xSessionRegistered", "0x" + sample_session_manifest.session_id],
                "data": "0x" + sample_session_manifest.manifest_hash + sample_session_manifest.merkle_root,
                "blockNumber": 12345,
                "transactionHash": "0xtx1234567890abcdef1234567890abcdef123456"
            }
        ]
        
        with patch.object(on_chain_client, 'get_contract_events') as mock_events_func:
            mock_events_func.return_value = mock_events
            
            events = await on_chain_client.get_session_registration_events(
                from_block=12340,
                to_block=12350
            )
            
            assert len(events) == 1
            assert events[0]["session_id"] == sample_session_manifest.session_id
            assert events[0]["manifest_hash"] == sample_session_manifest.manifest_hash
    
    @pytest.mark.asyncio
    async def test_session_anchor_status_monitoring(self, on_chain_client):
        """Test session anchor status monitoring loop."""
        mock_anchor = SessionAnchor(
            session_id="session_001",
            manifest_hash="0xmanifest1234567890abcdef1234567890abcdef123456",
            merkle_root="0xmerkle1234567890abcdef1234567890abcdef123456",
            started_at=datetime.now(),
            owner_address="0xowner1234567890abcdef1234567890abcdef123456",
            chunk_count=100,
            block_number=12345,
            txid="0xtx1234567890abcdef1234567890abcdef123456",
            gas_used=150000,
            status="pending"
        )
        
        # Mock transaction status check
        with patch.object(on_chain_client, 'get_transaction_status') as mock_status:
            mock_status.return_value = "confirmed"
            
            status = await on_chain_client.check_anchor_status(mock_anchor)
            
            assert status == "confirmed"
            mock_status.assert_called_once_with(mock_anchor.txid)
    
    @pytest.mark.asyncio
    async def test_merkle_root_validation(self, on_chain_client, sample_session_manifest):
        """Test Merkle root validation for session chunks."""
        # Mock Merkle root calculation
        with patch.object(on_chain_client, 'calculate_merkle_root') as mock_merkle:
            mock_merkle.return_value = sample_session_manifest.merkle_root
            
            is_valid = await on_chain_client.validate_merkle_root(
                chunks=sample_session_manifest.chunks,
                expected_root=sample_session_manifest.merkle_root
            )
            
            assert is_valid is True
            mock_merkle.assert_called_once_with(sample_session_manifest.chunks)
    
    @pytest.mark.asyncio
    async def test_evm_compatibility(self, on_chain_client):
        """Test EVM compatibility and JSON-RPC interface."""
        # Mock EVM JSON-RPC calls
        with patch.object(on_chain_client, 'rpc_call') as mock_rpc:
            mock_rpc.return_value = {"result": "0x1"}
            
            block_number = await on_chain_client.get_latest_block_number()
            
            mock_rpc.assert_called_once_with("eth_blockNumber", [])
            assert block_number == 1
    
    @pytest.mark.asyncio
    async def test_contract_address_validation(self, on_chain_client):
        """Test contract address validation."""
        # Test valid contract addresses
        assert on_chain_client.validate_contract_address("0x1234567890abcdef1234567890abcdef12345678")
        
        # Test invalid contract addresses
        with pytest.raises(ValueError):
            on_chain_client.validate_contract_address("invalid_address")
        
        with pytest.raises(ValueError):
            on_chain_client.validate_contract_address("0x123")  # Too short


if __name__ == "__main__":
    pytest.main([__file__])
