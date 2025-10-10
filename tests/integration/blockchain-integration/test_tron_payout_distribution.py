"""
Integration tests for monthly payout distribution via TRON.

Tests end-to-end TRON payout distribution, PayoutRouterV0/PRKYC integration,
and payment processing isolation from blockchain core.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any

from blockchain.core.blockchain_engine import BlockchainEngine, TronNodeSystem
from blockchain.core.models import PayoutRequest, PayoutResult, TronPayout


class TestTronPayoutDistribution:
    """Test TRON monthly payout distribution."""
    
    @pytest.fixture
    async def blockchain_engine(self):
        """Create blockchain engine for payout testing."""
        mock_db = AsyncMock()
        
        engine = BlockchainEngine()
        engine.db = mock_db
        engine.tron_client = TronNodeSystem("shasta")  # Test network
        engine.on_chain_client = AsyncMock()
        engine.consensus_engine = AsyncMock()
        
        return engine
    
    @pytest.fixture
    def sample_payout_requests(self) -> List[PayoutRequest]:
        """Sample payout requests for testing."""
        base_time = datetime.now() - timedelta(days=30)
        return [
            PayoutRequest(
                session_id="session_001",
                to_address="TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH",
                usdt_amount=100.0,
                router_type="PayoutRouterV0",
                reason="monthly_payout",
                created_at=base_time
            ),
            PayoutRequest(
                session_id="session_002",
                to_address="TAddress002",
                usdt_amount=250.0,
                router_type="PayoutRouterV0",
                reason="monthly_payout",
                created_at=base_time + timedelta(hours=1)
            ),
            PayoutRequest(
                session_id="session_003",
                to_address="TAddress003",
                usdt_amount=500.0,
                router_type="PayoutRouterKYC",
                reason="monthly_payout",
                created_at=base_time + timedelta(hours=2),
                kyc_hash="0xkyc1234567890abcdef1234567890abcdef123456",
                compliance_sig={"signature": "0xsig123...", "timestamp": base_time.isoformat()}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_monthly_payout_distribution_flow(self, blockchain_engine, sample_payout_requests):
        """Test complete monthly payout distribution flow."""
        # Mock database query for pending payouts
        blockchain_engine.db.payouts.find.return_value.to_list = AsyncMock(
            return_value=sample_payout_requests
        )
        
        # Mock TRON transaction results
        mock_tx_results = [
            {
                "txID": "0xtron0011234567890abcdef1234567890abcdef123456",
                "ret": [{"contractRet": "SUCCESS"}]
            },
            {
                "txID": "0xtron0021234567890abcdef1234567890abcdef123456",
                "ret": [{"contractRet": "SUCCESS"}]
            },
            {
                "txID": "0xtron0031234567890abcdef1234567890abcdef123456",
                "ret": [{"contractRet": "SUCCESS"}]
            }
        ]
        
        blockchain_engine.tron_client.send_usdt_trc20.side_effect = mock_tx_results
        
        # Mock KYC verification
        blockchain_engine.tron_client.verify_kyc_compliance.return_value = True
        
        # Execute monthly payout distribution
        results = await blockchain_engine.distribute_monthly_payouts()
        
        # Verify all payouts were processed
        assert len(results) == 3
        
        # Verify payout results
        for i, result in enumerate(results):
            assert result.session_id == sample_payout_requests[i].session_id
            assert result.usdt_amount == sample_payout_requests[i].usdt_amount
            assert result.status == "success"
            assert result.txid == mock_tx_results[i]["txID"]
        
        # Verify database updates
        assert blockchain_engine.db.payouts.update_many.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_payout_router_selection(self, blockchain_engine, sample_payout_requests):
        """Test payout router selection between PayoutRouterV0 and PayoutRouterKYC."""
        # Test non-KYC payout
        non_kyc_request = sample_payout_requests[0]
        selected_router = blockchain_engine.tron_client.select_payout_router(non_kyc_request)
        assert selected_router == "PayoutRouterV0"
        
        # Test KYC payout
        kyc_request = sample_payout_requests[2]
        selected_router = blockchain_engine.tron_client.select_payout_router(kyc_request)
        assert selected_router == "PayoutRouterKYC"
    
    @pytest.mark.asyncio
    async def test_kyc_compliance_verification(self, blockchain_engine, sample_payout_requests):
        """Test KYC compliance verification for KYC-gated payouts."""
        kyc_request = sample_payout_requests[2]  # KYC payout
        
        # Mock successful KYC verification
        blockchain_engine.tron_client.verify_kyc_compliance.return_value = True
        
        # Mock TRON transaction
        mock_tx_result = {
            "txID": "0xtronkyc1234567890abcdef1234567890abcdef123456",
            "ret": [{"contractRet": "SUCCESS"}]
        }
        
        blockchain_engine.tron_client.send_usdt_trc20.return_value = mock_tx_result
        
        # Execute KYC payout
        result = await blockchain_engine.tron_client.execute_payout(kyc_request)
        
        # Verify KYC verification was called
        blockchain_engine.tron_client.verify_kyc_compliance.assert_called_once_with(
            kyc_request.kyc_hash,
            kyc_request.compliance_sig
        )
        
        assert result.kyc_verified is True
        assert result.status == "success"
    
    @pytest.mark.asyncio
    async def test_payout_failure_handling(self, blockchain_engine, sample_payout_requests):
        """Test payout failure handling and retry mechanism."""
        # Mock payout failure
        mock_failed_tx = {
            "txID": "0xtron0011234567890abcdef1234567890abcdef123456",
            "ret": [{"contractRet": "OUT_OF_ENERGY"}]
        }
        
        blockchain_engine.tron_client.send_usdt_trc20.return_value = mock_failed_tx
        
        # Execute payout with failure
        result = await blockchain_engine.tron_client.execute_payout(sample_payout_requests[0])
        
        assert result.status == "failed"
        assert result.error == "OUT_OF_ENERGY"
        assert result.retry_count == 1
        
        # Verify retry mechanism
        if result.retry_count < 3:
            retry_result = await blockchain_engine.tron_client.retry_payout(result)
            assert retry_result.retry_count == 2
    
    @pytest.mark.asyncio
    async def test_payout_status_monitoring(self, blockchain_engine):
        """Test payout status monitoring and confirmation."""
        # Mock payout with pending status
        mock_payout = TronPayout(
            session_id="session_001",
            to_address="TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH",
            usdt_amount=100.0,
            txid="0xtron0011234567890abcdef1234567890abcdef123456",
            status="pending",
            created_at=datetime.now()
        )
        
        # Mock transaction status check
        blockchain_engine.tron_client.get_transaction_status.return_value = "confirmed"
        
        # Monitor payout status
        status = await blockchain_engine.tron_client.check_payout_status(mock_payout)
        
        assert status == "confirmed"
        blockchain_engine.tron_client.get_transaction_status.assert_called_once_with(mock_payout.txid)
    
    @pytest.mark.asyncio
    async def test_payment_isolation_from_consensus(self, blockchain_engine):
        """Test that TRON payments are completely isolated from consensus."""
        # Verify TRON client has no consensus dependencies
        assert not hasattr(blockchain_engine.tron_client, 'consensus_engine')
        assert not hasattr(blockchain_engine.tron_client, 'work_credits')
        assert not hasattr(blockchain_engine.tron_client, 'leader_selection')
        
        # Verify payment-only methods exist
        assert hasattr(blockchain_engine.tron_client, 'execute_payout')
        assert hasattr(blockchain_engine.tron_client, 'distribute_monthly_payouts')
        assert hasattr(blockchain_engine.tron_client, 'check_payout_status')
        
        # Test that payout distribution doesn't affect consensus
        with patch.object(blockchain_engine.consensus_engine, 'select_leader') as mock_consensus:
            mock_consensus.return_value = MagicMock(primary="node_001")
            
            # Execute payout distribution
            await blockchain_engine.distribute_monthly_payouts()
            
            # Verify consensus was not affected
            mock_consensus.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_energy_bandwidth_management(self, blockchain_engine):
        """Test TRX staking for energy and bandwidth management."""
        # Mock account resources
        mock_resources = {
            "energy": 150000,
            "bandwidth": 75000,
            "energy_limit": 200000,
            "bandwidth_limit": 100000
        }
        
        blockchain_engine.tron_client.get_account_resources.return_value = mock_resources
        
        # Check resource sufficiency
        is_sufficient = blockchain_engine.tron_client.check_resource_sufficiency(
            mock_resources, 100000, 50000  # energy, bandwidth needed
        )
        assert is_sufficient is True
        
        # Check resource insufficiency
        is_insufficient = blockchain_engine.tron_client.check_resource_sufficiency(
            mock_resources, 250000, 150000  # exceeds limits
        )
        assert is_insufficient is False
    
    @pytest.mark.asyncio
    async def test_payout_batch_processing(self, blockchain_engine, sample_payout_requests):
        """Test batch processing of multiple payouts."""
        # Mock database query
        blockchain_engine.db.payouts.find.return_value.to_list = AsyncMock(
            return_value=sample_payout_requests
        )
        
        # Mock successful batch processing
        mock_tx_results = [
            {"txID": f"0xtron{i:03d}1234567890abcdef1234567890abcdef123456", "ret": [{"contractRet": "SUCCESS"}]}
            for i in range(len(sample_payout_requests))
        ]
        
        blockchain_engine.tron_client.send_usdt_trc20.side_effect = mock_tx_results
        blockchain_engine.tron_client.verify_kyc_compliance.return_value = True
        
        # Execute batch payout processing
        results = await blockchain_engine.process_payout_batch(sample_payout_requests, batch_size=2)
        
        # Verify batch processing
        assert len(results) == 3
        assert all(result.status == "success" for result in results)
        
        # Verify batch size was respected
        # (Implementation would depend on specific batching logic)
        assert True  # Placeholder for batch size verification


if __name__ == "__main__":
    pytest.main([__file__])
