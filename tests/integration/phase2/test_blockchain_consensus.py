"""
Phase 2 Integration Tests: Blockchain Consensus Mechanism

This module tests the blockchain consensus mechanism (PoOT - Proof of Observation Time)
and its integration with the blockchain core system.

Test Scenarios:
1. Consensus mechanism initialization
2. PoOT score calculation
3. Consensus round execution
4. Validator participation
5. Consensus decision making
6. Block validation through consensus
"""

import pytest
import asyncio
import aiohttp
import json
from typing import Dict, Any, List
import time
import hashlib

class TestBlockchainConsensusIntegration:
    """Test blockchain consensus mechanism integration."""
    
    @pytest.mark.blockchain
    @pytest.mark.consensus
    @pytest.mark.asyncio
    async def test_consensus_initialization(self, blockchain_client, test_helper):
        """Test consensus mechanism initialization."""
        # Test consensus status
        consensus_url = f"{test_helper.TEST_CONFIG['blockchain_core_url']}/consensus/status"
        
        response = await test_helper.make_request(
            blockchain_client,
            "GET",
            consensus_url
        )
        
        # Verify consensus initialization
        test_helper.assert_response_success(response)
        assert "algorithm" in response["data"]
        assert "participants" in response["data"]
        assert "active_validators" in response["data"]
        assert "consensus_round" in response["data"]
        assert response["data"]["algorithm"] == "PoOT"
        assert isinstance(response["data"]["participants"], list)
        assert response["data"]["active_validators"] > 0
    
    @pytest.mark.blockchain
    @pytest.mark.consensus
    @pytest.mark.asyncio
    async def test_poot_score_calculation(self, blockchain_client, test_helper):
        """Test PoOT score calculation."""
        # Test PoOT score calculation
        poot_url = f"{test_helper.TEST_CONFIG['blockchain_core_url']}/consensus/poot/calculate"
        poot_data = {
            "node_id": "test_node_123",
            "session_time": 3600,  # 1 hour in seconds
            "observation_data": {
                "sessions_observed": 10,
                "total_time": 3600,
                "quality_score": 0.95
            }
        }
        
        response = await test_helper.make_request(
            blockchain_client,
            "POST",
            poot_url,
            json=poot_data
        )
        
        # Verify PoOT score calculation
        test_helper.assert_response_success(response)
        assert "poot_score" in response["data"]
        assert "node_id" in response["data"]
        assert "calculation_time" in response["data"]
        assert "score_components" in response["data"]
        
        # Verify score is within valid range (0-1)
        poot_score = response["data"]["poot_score"]
        assert 0 <= poot_score <= 1, f"PoOT score {poot_score} not in range [0,1]"
        
        # Verify score components
        components = response["data"]["score_components"]
        assert "time_factor" in components
        assert "quality_factor" in components
        assert "participation_factor" in components
    
    @pytest.mark.blockchain
    @pytest.mark.consensus
    @pytest.mark.asyncio
    async def test_consensus_round_execution(self, blockchain_client, sample_block_data, test_helper):
        """Test consensus round execution."""
        # Test consensus round
        consensus_url = f"{test_helper.TEST_CONFIG['blockchain_core_url']}/consensus/round"
        consensus_data = {
            "block_data": sample_block_data,
            "participants": ["node_1", "node_2", "node_3"],
            "timeout": 30
        }
        
        response = await test_helper.make_request(
            blockchain_client,
            "POST",
            consensus_url,
            json=consensus_data
        )
        
        # Verify consensus round response
        test_helper.assert_response_success(response)
        assert "round_id" in response["data"]
        assert "status" in response["data"]
        assert "participants" in response["data"]
        assert "votes" in response["data"]
        assert "decision" in response["data"]
        assert response["data"]["status"] in ["pending", "completed", "failed"]
    
    @pytest.mark.blockchain
    @pytest.mark.consensus
    @pytest.mark.asyncio
    async def test_validator_participation(self, blockchain_client, test_helper):
        """Test validator participation in consensus."""
        # Test validator registration
        register_url = f"{test_helper.TEST_CONFIG['blockchain_core_url']}/consensus/validators/register"
        validator_data = {
            "node_id": "validator_node_123",
            "public_key": "validator_public_key_123",
            "stake_amount": 1000,
            "reputation_score": 0.95
        }
        
        response = await test_helper.make_request(
            blockchain_client,
            "POST",
            register_url,
            json=validator_data
        )
        
        # Verify validator registration
        test_helper.assert_response_success(response)
        assert "validator_id" in response["data"]
        assert "status" in response["data"]
        assert response["data"]["status"] == "registered"
        
        # Test validator participation
        participate_url = f"{test_helper.TEST_CONFIG['blockchain_core_url']}/consensus/validators/participate"
        participation_data = {
            "validator_id": response["data"]["validator_id"],
            "round_id": "round_123",
            "vote": "approve"
        }
        
        participate_response = await test_helper.make_request(
            blockchain_client,
            "POST",
            participate_url,
            json=participation_data
        )
        
        # Verify participation
        test_helper.assert_response_success(participate_response)
        assert "participation_id" in participate_response["data"]
        assert "vote_recorded" in participate_response["data"]
        assert participate_response["data"]["vote_recorded"] is True
    
    @pytest.mark.blockchain
    @pytest.mark.consensus
    @pytest.mark.asyncio
    async def test_consensus_decision_making(self, blockchain_client, test_helper):
        """Test consensus decision making process."""
        # Test consensus decision
        decision_url = f"{test_helper.TEST_CONFIG['blockchain_core_url']}/consensus/decision"
        decision_data = {
            "round_id": "round_123",
            "votes": {
                "node_1": "approve",
                "node_2": "approve", 
                "node_3": "reject"
            },
            "threshold": 0.67
        }
        
        response = await test_helper.make_request(
            blockchain_client,
            "POST",
            decision_url,
            json=decision_data
        )
        
        # Verify decision
        test_helper.assert_response_success(response)
        assert "decision" in response["data"]
        assert "confidence" in response["data"]
        assert "vote_summary" in response["data"]
        assert response["data"]["decision"] in ["approved", "rejected", "pending"]
        
        # Verify vote summary
        vote_summary = response["data"]["vote_summary"]
        assert "total_votes" in vote_summary
        assert "approve_votes" in vote_summary
        assert "reject_votes" in vote_summary
        assert vote_summary["total_votes"] == 3
        assert vote_summary["approve_votes"] == 2
        assert vote_summary["reject_votes"] == 1
    
    @pytest.mark.blockchain
    @pytest.mark.consensus
    @pytest.mark.asyncio
    async def test_block_validation_consensus(self, blockchain_client, sample_block_data, test_helper):
        """Test block validation through consensus."""
        # Test block validation
        validate_url = f"{test_helper.TEST_CONFIG['blockchain_core_url']}/consensus/validate"
        validation_data = {
            "block_data": sample_block_data,
            "validators": ["node_1", "node_2", "node_3"],
            "validation_timeout": 30
        }
        
        response = await test_helper.make_request(
            blockchain_client,
            "POST",
            validate_url,
            json=validation_data
        )
        
        # Verify block validation
        test_helper.assert_response_success(response)
        assert "validation_id" in response["data"]
        assert "status" in response["data"]
        assert "validators_participated" in response["data"]
        assert "validation_result" in response["data"]
        assert response["data"]["status"] in ["validating", "completed", "failed"]
    
    @pytest.mark.blockchain
    @pytest.mark.consensus
    @pytest.mark.asyncio
    async def test_consensus_timeout_handling(self, blockchain_client, test_helper):
        """Test consensus timeout handling."""
        # Test consensus with short timeout
        timeout_url = f"{test_helper.TEST_CONFIG['blockchain_core_url']}/consensus/round"
        timeout_data = {
            "block_data": {"block_id": "test_block"},
            "participants": ["node_1", "node_2"],
            "timeout": 1  # 1 second timeout
        }
        
        start_time = time.time()
        response = await test_helper.make_request(
            blockchain_client,
            "POST",
            timeout_url,
            json=timeout_data
        )
        end_time = time.time()
        
        # Verify timeout handling
        test_helper.assert_response_success(response)
        assert "status" in response["data"]
        assert response["data"]["status"] in ["completed", "timeout", "failed"]
        
        # Verify timeout occurred within reasonable time
        elapsed_time = end_time - start_time
        assert elapsed_time <= 5.0, f"Consensus timeout took {elapsed_time:.2f}s, expected <= 5.0s"
    
    @pytest.mark.blockchain
    @pytest.mark.consensus
    @pytest.mark.asyncio
    async def test_consensus_metrics(self, blockchain_client, test_helper):
        """Test consensus metrics and statistics."""
        # Test consensus metrics
        metrics_url = f"{test_helper.TEST_CONFIG['blockchain_core_url']}/consensus/metrics"
        
        response = await test_helper.make_request(
            blockchain_client,
            "GET",
            metrics_url
        )
        
        # Verify consensus metrics
        test_helper.assert_response_success(response)
        assert "total_rounds" in response["data"]
        assert "successful_rounds" in response["data"]
        assert "failed_rounds" in response["data"]
        assert "average_round_time" in response["data"]
        assert "consensus_rate" in response["data"]
        assert "active_validators" in response["data"]
        
        # Verify metrics are reasonable
        assert response["data"]["total_rounds"] >= 0
        assert response["data"]["successful_rounds"] >= 0
        assert response["data"]["failed_rounds"] >= 0
        assert 0 <= response["data"]["consensus_rate"] <= 1
    
    @pytest.mark.blockchain
    @pytest.mark.consensus
    @pytest.mark.asyncio
    async def test_consensus_error_handling(self, blockchain_client, test_helper):
        """Test consensus error handling."""
        # Test consensus with invalid data
        invalid_url = f"{test_helper.TEST_CONFIG['blockchain_core_url']}/consensus/round"
        invalid_data = {
            "block_data": None,  # Invalid block data
            "participants": [],  # Empty participants
            "timeout": -1  # Invalid timeout
        }
        
        response = await test_helper.make_request(
            blockchain_client,
            "POST",
            invalid_url,
            json=invalid_data
        )
        
        # Verify error handling
        assert response["status"] == 400
        assert "error" in response["data"]
        assert response["data"]["error"]["code"] == "LUCID_ERR_1XXX"
    
    @pytest.mark.blockchain
    @pytest.mark.consensus
    @pytest.mark.asyncio
    async def test_consensus_performance(self, blockchain_client, test_helper):
        """Test consensus performance."""
        # Test consensus round performance
        consensus_url = f"{test_helper.TEST_CONFIG['blockchain_core_url']}/consensus/round"
        consensus_data = {
            "block_data": {"block_id": "perf_test_block"},
            "participants": ["node_1", "node_2", "node_3"],
            "timeout": 10
        }
        
        start_time = time.time()
        response = await test_helper.make_request(
            blockchain_client,
            "POST",
            consensus_url,
            json=consensus_data
        )
        end_time = time.time()
        
        # Verify performance
        test_helper.assert_response_success(response)
        consensus_time = end_time - start_time
        
        # Consensus should complete within 15 seconds
        assert consensus_time < 15.0, f"Consensus took {consensus_time:.2f}s, expected < 15.0s"
    
    @pytest.mark.blockchain
    @pytest.mark.consensus
    @pytest.mark.asyncio
    async def test_concurrent_consensus_rounds(self, blockchain_client, test_helper):
        """Test concurrent consensus rounds."""
        # Create multiple concurrent consensus rounds
        consensus_url = f"{test_helper.TEST_CONFIG['blockchain_core_url']}/consensus/round"
        
        tasks = []
        for i in range(3):
            consensus_data = {
                "block_data": {"block_id": f"concurrent_block_{i}"},
                "participants": ["node_1", "node_2", "node_3"],
                "timeout": 10
            }
            task = test_helper.make_request(
                blockchain_client,
                "POST",
                consensus_url,
                json=consensus_data
            )
            tasks.append(task)
        
        # Execute concurrent consensus rounds
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all consensus rounds completed
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                pytest.fail(f"Concurrent consensus round {i} failed: {response}")
            
            test_helper.assert_response_success(response)
            assert "round_id" in response["data"]
            assert "status" in response["data"]
    
    @pytest.mark.blockchain
    @pytest.mark.consensus
    @pytest.mark.asyncio
    async def test_consensus_consistency(self, blockchain_client, test_helper):
        """Test consensus consistency across multiple rounds."""
        # Test multiple consensus rounds for consistency
        consensus_url = f"{test_helper.TEST_CONFIG['blockchain_core_url']}/consensus/round"
        
        results = []
        for i in range(5):
            consensus_data = {
                "block_data": {"block_id": f"consistency_block_{i}"},
                "participants": ["node_1", "node_2", "node_3"],
                "timeout": 5
            }
            
            response = await test_helper.make_request(
                blockchain_client,
                "POST",
                consensus_url,
                json=consensus_data
            )
            
            test_helper.assert_response_success(response)
            results.append(response["data"])
        
        # Verify consistency
        assert len(results) == 5
        for result in results:
            assert "round_id" in result
            assert "status" in result
            assert result["status"] in ["completed", "timeout", "failed"]
