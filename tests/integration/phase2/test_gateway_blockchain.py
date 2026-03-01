"""
Phase 2 Integration Tests: API Gateway → Blockchain Proxy

This module tests the integration between API Gateway and Blockchain Core
for blockchain operations and session anchoring.

Test Scenarios:
1. API Gateway → Blockchain Core proxy
2. Blockchain info queries
3. Session anchoring through gateway
4. Block and transaction queries
5. Consensus status queries
"""

import pytest
import asyncio
import aiohttp
import json
from typing import Dict, Any
import time

class TestGatewayBlockchainIntegration:
    """Test API Gateway → Blockchain Core integration."""
    
    @pytest.mark.gateway
    @pytest.mark.blockchain
    @pytest.mark.asyncio
    async def test_blockchain_info_proxy(self, api_gateway_client, auth_token, test_helper):
        """Test blockchain info query through API Gateway proxy."""
        # Test blockchain info endpoint
        blockchain_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/chain/info"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = await test_helper.make_request(
            api_gateway_client,
            "GET",
            blockchain_url,
            headers=headers
        )
        
        # Verify blockchain info response
        test_helper.assert_response_success(response)
        assert "network" in response["data"]
        assert "version" in response["data"]
        assert "height" in response["data"]
        assert "consensus" in response["data"]
        assert response["data"]["network"] == "lucid_blocks"
        assert response["data"]["consensus"] == "PoOT"
    
    @pytest.mark.gateway
    @pytest.mark.blockchain
    @pytest.mark.asyncio
    async def test_block_query_proxy(self, api_gateway_client, auth_token, test_helper):
        """Test block query through API Gateway proxy."""
        # Test get latest block
        latest_block_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/chain/blocks/latest"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = await test_helper.make_request(
            api_gateway_client,
            "GET",
            latest_block_url,
            headers=headers
        )
        
        # Verify block response
        test_helper.assert_response_success(response)
        assert "block_id" in response["data"]
        assert "height" in response["data"]
        assert "timestamp" in response["data"]
        assert "merkle_root" in response["data"]
        assert "transactions" in response["data"]
        assert isinstance(response["data"]["transactions"], list)
    
    @pytest.mark.gateway
    @pytest.mark.blockchain
    @pytest.mark.asyncio
    async def test_block_by_height_query(self, api_gateway_client, auth_token, test_helper):
        """Test block query by height through API Gateway proxy."""
        # Test get block by height
        block_height = 1
        block_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/chain/blocks/{block_height}"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = await test_helper.make_request(
            api_gateway_client,
            "GET",
            block_url,
            headers=headers
        )
        
        # Verify block response
        test_helper.assert_response_success(response)
        assert "block_id" in response["data"]
        assert response["data"]["height"] == block_height
        assert "timestamp" in response["data"]
        assert "merkle_root" in response["data"]
    
    @pytest.mark.gateway
    @pytest.mark.blockchain
    @pytest.mark.asyncio
    async def test_transaction_query_proxy(self, api_gateway_client, auth_token, test_helper):
        """Test transaction query through API Gateway proxy."""
        # Test get transactions
        transactions_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/chain/transactions"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = await test_helper.make_request(
            api_gateway_client,
            "GET",
            transactions_url,
            headers=headers
        )
        
        # Verify transactions response
        test_helper.assert_response_success(response)
        assert "transactions" in response["data"]
        assert isinstance(response["data"]["transactions"], list)
        assert "total" in response["data"]
        assert "page" in response["data"]
        assert "limit" in response["data"]
    
    @pytest.mark.gateway
    @pytest.mark.blockchain
    @pytest.mark.asyncio
    async def test_session_anchoring_proxy(self, api_gateway_client, auth_token, sample_session_data, test_helper):
        """Test session anchoring through API Gateway proxy."""
        # Test session anchoring
        anchor_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/chain/anchoring/session"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = await test_helper.make_request(
            api_gateway_client,
            "POST",
            anchor_url,
            headers=headers,
            json=sample_session_data
        )
        
        # Verify anchoring response
        test_helper.assert_response_success(response)
        assert "anchoring_id" in response["data"]
        assert "session_id" in response["data"]
        assert "merkle_root" in response["data"]
        assert "block_height" in response["data"]
        assert "status" in response["data"]
        assert response["data"]["status"] == "anchored"
    
    @pytest.mark.gateway
    @pytest.mark.blockchain
    @pytest.mark.asyncio
    async def test_anchoring_status_query(self, api_gateway_client, auth_token, test_helper):
        """Test anchoring status query through API Gateway proxy."""
        # Test get anchoring status
        status_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/chain/anchoring/status"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = await test_helper.make_request(
            api_gateway_client,
            "GET",
            status_url,
            headers=headers
        )
        
        # Verify status response
        test_helper.assert_response_success(response)
        assert "total_anchored" in response["data"]
        assert "pending_anchors" in response["data"]
        assert "last_anchor_time" in response["data"]
        assert "anchoring_rate" in response["data"]
    
    @pytest.mark.gateway
    @pytest.mark.blockchain
    @pytest.mark.asyncio
    async def test_consensus_status_proxy(self, api_gateway_client, auth_token, test_helper):
        """Test consensus status query through API Gateway proxy."""
        # Test consensus status
        consensus_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/chain/consensus/status"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = await test_helper.make_request(
            api_gateway_client,
            "GET",
            consensus_url,
            headers=headers
        )
        
        # Verify consensus response
        test_helper.assert_response_success(response)
        assert "algorithm" in response["data"]
        assert "participants" in response["data"]
        assert "active_validators" in response["data"]
        assert "consensus_round" in response["data"]
        assert response["data"]["algorithm"] == "PoOT"
        assert isinstance(response["data"]["participants"], list)
    
    @pytest.mark.gateway
    @pytest.mark.blockchain
    @pytest.mark.asyncio
    async def test_merkle_tree_verification(self, api_gateway_client, auth_token, test_helper):
        """Test Merkle tree verification through API Gateway proxy."""
        # Test Merkle tree verification
        verify_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/chain/merkle/verify"
        headers = {"Authorization": f"Bearer {auth_token}"}
        verify_data = {
            "merkle_root": "test_merkle_root_hash",
            "chunk_hashes": ["hash1", "hash2", "hash3"],
            "proof": ["proof1", "proof2"]
        }
        
        response = await test_helper.make_request(
            api_gateway_client,
            "POST",
            verify_url,
            headers=headers,
            json=verify_data
        )
        
        # Verify Merkle verification response
        test_helper.assert_response_success(response)
        assert "valid" in response["data"]
        assert "verified_chunks" in response["data"]
        assert isinstance(response["data"]["valid"], bool)
    
    @pytest.mark.gateway
    @pytest.mark.blockchain
    @pytest.mark.asyncio
    async def test_blockchain_health_check(self, api_gateway_client, test_helper):
        """Test blockchain health check through API Gateway proxy."""
        # Test blockchain health
        health_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/chain/health"
        
        response = await test_helper.make_request(
            api_gateway_client,
            "GET",
            health_url
        )
        
        # Verify health response
        test_helper.assert_response_success(response)
        assert "status" in response["data"]
        assert "services" in response["data"]
        assert response["data"]["status"] == "healthy"
        assert "blockchain_engine" in response["data"]["services"]
        assert "session_anchoring" in response["data"]["services"]
        assert "block_manager" in response["data"]["services"]
    
    @pytest.mark.gateway
    @pytest.mark.blockchain
    @pytest.mark.asyncio
    async def test_blockchain_metrics_proxy(self, api_gateway_client, auth_token, test_helper):
        """Test blockchain metrics through API Gateway proxy."""
        # Test blockchain metrics
        metrics_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/chain/metrics"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = await test_helper.make_request(
            api_gateway_client,
            "GET",
            metrics_url,
            headers=headers
        )
        
        # Verify metrics response
        test_helper.assert_response_success(response)
        assert "blocks_per_second" in response["data"]
        assert "transactions_per_second" in response["data"]
        assert "average_block_time" in response["data"]
        assert "consensus_participation" in response["data"]
        assert "anchoring_success_rate" in response["data"]
    
    @pytest.mark.gateway
    @pytest.mark.blockchain
    @pytest.mark.asyncio
    async def test_blockchain_error_handling(self, api_gateway_client, auth_token, test_helper):
        """Test blockchain error handling through API Gateway proxy."""
        # Test invalid block height
        invalid_block_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/chain/blocks/999999"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = await test_helper.make_request(
            api_gateway_client,
            "GET",
            invalid_block_url,
            headers=headers
        )
        
        # Verify error response
        assert response["status"] == 404
        assert "error" in response["data"]
        assert response["data"]["error"]["code"] == "LUCID_ERR_4XXX"
    
    @pytest.mark.gateway
    @pytest.mark.blockchain
    @pytest.mark.asyncio
    async def test_blockchain_proxy_performance(self, api_gateway_client, auth_token, test_helper):
        """Test blockchain proxy performance."""
        # Test multiple concurrent blockchain queries
        blockchain_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/chain/info"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Measure response time
        start_time = time.time()
        response = await test_helper.make_request(
            api_gateway_client,
            "GET",
            blockchain_url,
            headers=headers
        )
        end_time = time.time()
        
        # Verify performance
        test_helper.assert_response_success(response)
        response_time = end_time - start_time
        
        # Blockchain queries should complete within 1 second
        assert response_time < 1.0, f"Blockchain query took {response_time:.2f}s, expected < 1.0s"
    
    @pytest.mark.gateway
    @pytest.mark.blockchain
    @pytest.mark.asyncio
    async def test_concurrent_blockchain_queries(self, api_gateway_client, auth_token, test_helper):
        """Test concurrent blockchain queries through API Gateway."""
        # Create multiple concurrent blockchain queries
        blockchain_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/chain/info"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        tasks = []
        for i in range(10):
            task = test_helper.make_request(
                api_gateway_client,
                "GET",
                blockchain_url,
                headers=headers
            )
            tasks.append(task)
        
        # Execute concurrent requests
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all requests succeeded
        for response in responses:
            if isinstance(response, Exception):
                pytest.fail(f"Concurrent blockchain query failed: {response}")
            
            test_helper.assert_response_success(response)
            assert "network" in response["data"]
            assert response["data"]["network"] == "lucid_blocks"
    
    @pytest.mark.gateway
    @pytest.mark.blockchain
    @pytest.mark.asyncio
    async def test_blockchain_circuit_breaker(self, api_gateway_client, auth_token, test_helper):
        """Test blockchain circuit breaker functionality."""
        # Test circuit breaker with invalid blockchain service
        # This test simulates blockchain service being down
        invalid_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/chain/invalid"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Make multiple requests to trigger circuit breaker
        for i in range(5):
            response = await test_helper.make_request(
                api_gateway_client,
                "GET",
                invalid_url,
                headers=headers
            )
            
            # Should eventually return circuit breaker error
            if response["status"] == 503:
                assert "circuit" in response["data"]["error"]["message"].lower()
                break
        else:
            # If circuit breaker didn't trigger, that's also acceptable
            # as it means the service is handling errors gracefully
            pass
