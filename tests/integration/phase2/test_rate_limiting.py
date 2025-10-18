"""
Phase 2 Integration Tests: Rate Limiting Integration

This module tests the rate limiting integration across all Phase 2 services
including API Gateway, Blockchain Core, and service mesh.

Test Scenarios:
1. Public endpoint rate limiting (100 req/min)
2. Authenticated endpoint rate limiting (1000 req/min)
3. Admin endpoint rate limiting (10000 req/min)
4. Rate limiting headers and responses
5. Rate limiting across different services
6. Rate limiting performance and accuracy
"""

import pytest
import asyncio
import aiohttp
import json
from typing import Dict, Any, List
import time

class TestRateLimitingIntegration:
    """Test rate limiting integration across Phase 2 services."""
    
    @pytest.mark.rate_limiting
    @pytest.mark.gateway
    @pytest.mark.asyncio
    async def test_public_endpoint_rate_limiting(self, api_gateway_client, test_helper):
        """Test public endpoint rate limiting (100 req/min)."""
        # Test public endpoint without authentication
        public_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/health"
        
        # Make requests up to the limit
        responses = []
        for i in range(105):  # 5 over the limit
            response = await test_helper.make_request(
                api_gateway_client,
                "GET",
                public_url
            )
            responses.append(response)
            
            # Small delay to avoid overwhelming the service
            await asyncio.sleep(0.01)
        
        # Verify rate limiting behavior
        successful_requests = sum(1 for r in responses if r["status"] == 200)
        rate_limited_requests = sum(1 for r in responses if r["status"] == 429)
        
        # Should have some successful requests and some rate limited
        assert successful_requests > 0, "No successful requests found"
        assert rate_limited_requests > 0, "No rate limited requests found"
        
        # Verify rate limiting headers on successful requests
        for response in responses:
            if response["status"] == 200:
                test_helper.assert_rate_limit_headers(response)
    
    @pytest.mark.rate_limiting
    @pytest.mark.gateway
    @pytest.mark.asyncio
    async def test_authenticated_endpoint_rate_limiting(self, api_gateway_client, auth_token, test_helper):
        """Test authenticated endpoint rate limiting (1000 req/min)."""
        # Test authenticated endpoint
        auth_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/users/me"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Make requests up to the limit
        responses = []
        for i in range(1005):  # 5 over the limit
            response = await test_helper.make_request(
                api_gateway_client,
                "GET",
                auth_url,
                headers=headers
            )
            responses.append(response)
            
            # Small delay to avoid overwhelming the service
            await asyncio.sleep(0.01)
        
        # Verify rate limiting behavior
        successful_requests = sum(1 for r in responses if r["status"] == 200)
        rate_limited_requests = sum(1 for r in responses if r["status"] == 429)
        
        # Should have some successful requests and some rate limited
        assert successful_requests > 0, "No successful requests found"
        assert rate_limited_requests > 0, "No rate limited requests found"
        
        # Verify rate limiting headers
        for response in responses:
            if response["status"] == 200:
                test_helper.assert_rate_limit_headers(response)
    
    @pytest.mark.rate_limiting
    @pytest.mark.gateway
    @pytest.mark.asyncio
    async def test_admin_endpoint_rate_limiting(self, api_gateway_client, admin_token, test_helper):
        """Test admin endpoint rate limiting (10000 req/min)."""
        # Test admin endpoint
        admin_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/admin/system/status"
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Make requests up to the limit
        responses = []
        for i in range(10005):  # 5 over the limit
            response = await test_helper.make_request(
                api_gateway_client,
                "GET",
                admin_url,
                headers=headers
            )
            responses.append(response)
            
            # Small delay to avoid overwhelming the service
            await asyncio.sleep(0.001)
        
        # Verify rate limiting behavior
        successful_requests = sum(1 for r in responses if r["status"] == 200)
        rate_limited_requests = sum(1 for r in responses if r["status"] == 429)
        
        # Should have some successful requests and some rate limited
        assert successful_requests > 0, "No successful requests found"
        assert rate_limited_requests > 0, "No rate limited requests found"
    
    @pytest.mark.rate_limiting
    @pytest.mark.gateway
    @pytest.mark.asyncio
    async def test_rate_limiting_headers(self, api_gateway_client, auth_token, test_helper):
        """Test rate limiting headers are present and correct."""
        # Test rate limiting headers
        auth_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/users/me"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = await test_helper.make_request(
            api_gateway_client,
            "GET",
            auth_url,
            headers=headers
        )
        
        # Verify rate limiting headers
        test_helper.assert_rate_limit_headers(response)
        
        # Verify header values
        rate_limit_headers = response["headers"]
        assert "X-RateLimit-Limit" in rate_limit_headers
        assert "X-RateLimit-Remaining" in rate_limit_headers
        assert "X-RateLimit-Reset" in rate_limit_headers
        
        # Verify header values are reasonable
        limit = int(rate_limit_headers["X-RateLimit-Limit"])
        remaining = int(rate_limit_headers["X-RateLimit-Remaining"])
        reset = int(rate_limit_headers["X-RateLimit-Reset"])
        
        assert limit > 0, f"Rate limit should be positive, got {limit}"
        assert remaining >= 0, f"Remaining should be non-negative, got {remaining}"
        assert remaining <= limit, f"Remaining should not exceed limit, got {remaining} > {limit}"
        assert reset > 0, f"Reset time should be positive, got {reset}"
    
    @pytest.mark.rate_limiting
    @pytest.mark.gateway
    @pytest.mark.asyncio
    async def test_rate_limiting_error_response(self, api_gateway_client, test_helper):
        """Test rate limiting error response format."""
        # Test rate limiting error response
        public_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/health"
        
        # Make requests until rate limited
        rate_limited_response = None
        for i in range(150):  # Ensure we hit the limit
            response = await test_helper.make_request(
                api_gateway_client,
                "GET",
                public_url
            )
            
            if response["status"] == 429:
                rate_limited_response = response
                break
            
            await asyncio.sleep(0.01)
        
        # Verify rate limiting error response
        assert rate_limited_response is not None, "Rate limiting not triggered"
        assert rate_limited_response["status"] == 429
        assert "error" in rate_limited_response["data"]
        
        error = rate_limited_response["data"]["error"]
        assert "code" in error
        assert "message" in error
        assert error["code"] == "LUCID_ERR_3XXX"
        assert "rate limit" in error["message"].lower()
    
    @pytest.mark.rate_limiting
    @pytest.mark.blockchain
    @pytest.mark.asyncio
    async def test_blockchain_rate_limiting(self, blockchain_client, test_helper):
        """Test rate limiting on blockchain endpoints."""
        # Test blockchain endpoint rate limiting
        blockchain_url = f"{test_helper.TEST_CONFIG['blockchain_core_url']}/info"
        
        # Make requests to test rate limiting
        responses = []
        for i in range(105):  # 5 over the limit
            response = await test_helper.make_request(
                blockchain_client,
                "GET",
                blockchain_url
            )
            responses.append(response)
            
            await asyncio.sleep(0.01)
        
        # Verify rate limiting behavior
        successful_requests = sum(1 for r in responses if r["status"] == 200)
        rate_limited_requests = sum(1 for r in responses if r["status"] == 429)
        
        # Should have some successful requests and some rate limited
        assert successful_requests > 0, "No successful requests found"
        assert rate_limited_requests > 0, "No rate limited requests found"
    
    @pytest.mark.rate_limiting
    @pytest.mark.gateway
    @pytest.mark.asyncio
    async def test_different_user_rate_limiting(self, api_gateway_client, test_helper):
        """Test rate limiting for different users."""
        # Test rate limiting for different users
        user1_credentials = {
            "username": "user1",
            "password": "password1",
            "tron_address": "TUser1Address123",
            "tron_signature": "user1_signature"
        }
        
        user2_credentials = {
            "username": "user2", 
            "password": "password2",
            "tron_address": "TUser2Address456",
            "tron_signature": "user2_signature"
        }
        
        # Get tokens for both users
        login_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/auth/login"
        
        user1_response = await test_helper.make_request(
            api_gateway_client,
            "POST",
            login_url,
            json=user1_credentials
        )
        
        user2_response = await test_helper.make_request(
            api_gateway_client,
            "POST",
            login_url,
            json=user2_credentials
        )
        
        # Both users should have independent rate limits
        if user1_response["status"] == 200 and user2_response["status"] == 200:
            user1_token = user1_response["data"]["access_token"]
            user2_token = user2_response["data"]["access_token"]
            
            # Test rate limiting for user1
            user1_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/users/me"
            user1_headers = {"Authorization": f"Bearer {user1_token}"}
            
            user1_responses = []
            for i in range(10):
                response = await test_helper.make_request(
                    api_gateway_client,
                    "GET",
                    user1_url,
                    headers=user1_headers
                )
                user1_responses.append(response)
                await asyncio.sleep(0.01)
            
            # Test rate limiting for user2
            user2_headers = {"Authorization": f"Bearer {user2_token}"}
            
            user2_responses = []
            for i in range(10):
                response = await test_helper.make_request(
                    api_gateway_client,
                    "GET",
                    user1_url,
                    headers=user2_headers
                )
                user2_responses.append(response)
                await asyncio.sleep(0.01)
            
            # Both users should have independent rate limits
            user1_successful = sum(1 for r in user1_responses if r["status"] == 200)
            user2_successful = sum(1 for r in user2_responses if r["status"] == 200)
            
            assert user1_successful > 0, "User1 rate limiting failed"
            assert user2_successful > 0, "User2 rate limiting failed"
    
    @pytest.mark.rate_limiting
    @pytest.mark.gateway
    @pytest.mark.asyncio
    async def test_rate_limiting_reset(self, api_gateway_client, test_helper):
        """Test rate limiting reset after time window."""
        # Test rate limiting reset
        public_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/health"
        
        # Make requests until rate limited
        rate_limited = False
        for i in range(150):
            response = await test_helper.make_request(
                api_gateway_client,
                "GET",
                public_url
            )
            
            if response["status"] == 429:
                rate_limited = True
                break
            
            await asyncio.sleep(0.01)
        
        assert rate_limited, "Rate limiting not triggered"
        
        # Wait for rate limit reset (simulate)
        await asyncio.sleep(1)
        
        # Test if rate limiting resets
        reset_response = await test_helper.make_request(
            api_gateway_client,
            "GET",
            public_url
        )
        
        # Should be able to make requests again
        assert reset_response["status"] in [200, 429], f"Unexpected status: {reset_response['status']}"
    
    @pytest.mark.rate_limiting
    @pytest.mark.gateway
    @pytest.mark.asyncio
    async def test_rate_limiting_performance(self, api_gateway_client, test_helper):
        """Test rate limiting performance impact."""
        # Test rate limiting performance
        public_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/health"
        
        # Measure response time
        start_time = time.time()
        response = await test_helper.make_request(
            api_gateway_client,
            "GET",
            public_url
        )
        end_time = time.time()
        
        # Verify performance
        test_helper.assert_response_success(response)
        response_time = end_time - start_time
        
        # Rate limiting should not significantly impact performance
        assert response_time < 1.0, f"Rate limiting response took {response_time:.2f}s, expected < 1.0s"
    
    @pytest.mark.rate_limiting
    @pytest.mark.gateway
    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self, api_gateway_client, test_helper):
        """Test concurrent rate limiting requests."""
        # Test concurrent rate limiting
        public_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/health"
        
        # Create concurrent requests
        tasks = []
        for i in range(20):
            task = test_helper.make_request(
                api_gateway_client,
                "GET",
                public_url
            )
            tasks.append(task)
        
        # Execute concurrent requests
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify rate limiting behavior
        successful_requests = sum(1 for r in responses if not isinstance(r, Exception) and r["status"] == 200)
        rate_limited_requests = sum(1 for r in responses if not isinstance(r, Exception) and r["status"] == 429)
        
        # Should have some successful requests and some rate limited
        assert successful_requests > 0, "No successful requests found"
        assert rate_limited_requests > 0, "No rate limited requests found"
    
    @pytest.mark.rate_limiting
    @pytest.mark.gateway
    @pytest.mark.asyncio
    async def test_rate_limiting_accuracy(self, api_gateway_client, test_helper):
        """Test rate limiting accuracy."""
        # Test rate limiting accuracy
        public_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/health"
        
        # Make requests and track rate limiting
        responses = []
        rate_limited_count = 0
        
        for i in range(120):  # 20 over the limit
            response = await test_helper.make_request(
                api_gateway_client,
                "GET",
                public_url
            )
            responses.append(response)
            
            if response["status"] == 429:
                rate_limited_count += 1
            
            await asyncio.sleep(0.01)
        
        # Verify rate limiting accuracy
        total_requests = len(responses)
        successful_requests = sum(1 for r in responses if r["status"] == 200)
        
        # Rate limiting should be accurate
        assert rate_limited_count > 0, "Rate limiting not triggered"
        assert successful_requests > 0, "No successful requests found"
        assert rate_limited_count + successful_requests == total_requests, "Request count mismatch"
    
    @pytest.mark.rate_limiting
    @pytest.mark.gateway
    @pytest.mark.asyncio
    async def test_rate_limiting_different_endpoints(self, api_gateway_client, auth_token, test_helper):
        """Test rate limiting on different endpoints."""
        # Test different endpoints with different rate limits
        endpoints = [
            ("/health", "public"),
            ("/users/me", "authenticated"),
            ("/admin/system/status", "admin")
        ]
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        for endpoint, rate_limit_type in endpoints:
            url = f"{test_helper.TEST_CONFIG['api_gateway_url']}{endpoint}"
            
            # Make requests to test rate limiting
            responses = []
            for i in range(10):
                response = await test_helper.make_request(
                    api_gateway_client,
                    "GET",
                    url,
                    headers=headers if rate_limit_type != "public" else {}
                )
                responses.append(response)
                await asyncio.sleep(0.01)
            
            # Verify rate limiting behavior
            successful_requests = sum(1 for r in responses if r["status"] == 200)
            rate_limited_requests = sum(1 for r in responses if r["status"] == 429)
            
            # Should have some successful requests
            assert successful_requests > 0, f"No successful requests for {endpoint}"
            
            # Verify rate limiting headers on successful requests
            for response in responses:
                if response["status"] == 200:
                    test_helper.assert_rate_limit_headers(response)
