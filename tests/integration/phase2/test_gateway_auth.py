"""
Phase 2 Integration Tests: API Gateway → Auth → Database Flow

This module tests the integration between API Gateway, Authentication service,
and Database for user authentication and authorization flows.

Test Scenarios:
1. User login flow through API Gateway
2. JWT token validation and refresh
3. Protected endpoint access
4. User session management
5. Database integration for user data
"""

import pytest
import asyncio
import aiohttp
import json
from typing import Dict, Any
import time

class TestGatewayAuthIntegration:
    """Test API Gateway → Auth → Database integration."""
    
    @pytest.mark.gateway
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_user_login_flow(self, api_gateway_client, test_user_credentials, test_helper):
        """Test complete user login flow through API Gateway."""
        # Test user login
        login_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/auth/login"
        
        response = await test_helper.make_request(
            api_gateway_client,
            "POST",
            login_url,
            json=test_user_credentials
        )
        
        # Verify login response
        test_helper.assert_response_success(response)
        assert "access_token" in response["data"]
        assert "refresh_token" in response["data"]
        assert "token_type" in response["data"]
        assert response["data"]["token_type"] == "bearer"
        
        # Verify token structure
        token = response["data"]["access_token"]
        assert len(token) > 0
        assert isinstance(token, str)
    
    @pytest.mark.gateway
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_jwt_token_validation(self, api_gateway_client, auth_token, test_helper):
        """Test JWT token validation through API Gateway."""
        # Test token validation endpoint
        validate_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/auth/verify"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = await test_helper.make_request(
            api_gateway_client,
            "POST",
            validate_url,
            headers=headers
        )
        
        # Verify token validation response
        test_helper.assert_response_success(response)
        assert "valid" in response["data"]
        assert response["data"]["valid"] is True
        assert "user_id" in response["data"]
        assert "expires_at" in response["data"]
    
    @pytest.mark.gateway
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_protected_endpoint_access(self, api_gateway_client, auth_token, test_helper):
        """Test access to protected endpoints with valid token."""
        # Test protected user endpoint
        user_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/users/me"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = await test_helper.make_request(
            api_gateway_client,
            "GET",
            user_url,
            headers=headers
        )
        
        # Verify protected endpoint access
        test_helper.assert_response_success(response)
        assert "user_id" in response["data"]
        assert "username" in response["data"]
        assert "created_at" in response["data"]
    
    @pytest.mark.gateway
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, api_gateway_client, test_helper):
        """Test unauthorized access to protected endpoints."""
        # Test protected endpoint without token
        user_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/users/me"
        
        response = await test_helper.make_request(
            api_gateway_client,
            "GET",
            user_url
        )
        
        # Verify unauthorized response
        assert response["status"] == 401
        assert "error" in response["data"]
        assert response["data"]["error"]["code"] == "LUCID_ERR_2XXX"
    
    @pytest.mark.gateway
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_invalid_token_access(self, api_gateway_client, test_helper):
        """Test access with invalid JWT token."""
        # Test protected endpoint with invalid token
        user_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/users/me"
        headers = {"Authorization": "Bearer invalid_token_12345"}
        
        response = await test_helper.make_request(
            api_gateway_client,
            "GET",
            user_url,
            headers=headers
        )
        
        # Verify invalid token response
        assert response["status"] == 401
        assert "error" in response["data"]
        assert "invalid" in response["data"]["error"]["message"].lower()
    
    @pytest.mark.gateway
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_token_refresh_flow(self, api_gateway_client, test_user_credentials, test_helper):
        """Test JWT token refresh flow."""
        # First, get initial tokens
        login_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/auth/login"
        login_response = await test_helper.make_request(
            api_gateway_client,
            "POST",
            login_url,
            json=test_user_credentials
        )
        
        test_helper.assert_response_success(login_response)
        refresh_token = login_response["data"]["refresh_token"]
        
        # Test token refresh
        refresh_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/auth/refresh"
        refresh_data = {"refresh_token": refresh_token}
        
        response = await test_helper.make_request(
            api_gateway_client,
            "POST",
            refresh_url,
            json=refresh_data
        )
        
        # Verify refresh response
        test_helper.assert_response_success(response)
        assert "access_token" in response["data"]
        assert "refresh_token" in response["data"]
        assert response["data"]["token_type"] == "bearer"
    
    @pytest.mark.gateway
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_user_logout_flow(self, api_gateway_client, auth_token, test_helper):
        """Test user logout flow."""
        # Test logout endpoint
        logout_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/auth/logout"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = await test_helper.make_request(
            api_gateway_client,
            "POST",
            logout_url,
            headers=headers
        )
        
        # Verify logout response
        test_helper.assert_response_success(response)
        assert "message" in response["data"]
        assert "success" in response["data"]["message"].lower()
        
        # Verify token is invalidated
        user_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/users/me"
        verify_response = await test_helper.make_request(
            api_gateway_client,
            "GET",
            user_url,
            headers=headers
        )
        
        # Should be unauthorized after logout
        assert verify_response["status"] == 401
    
    @pytest.mark.gateway
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_user_session_management(self, api_gateway_client, auth_token, test_helper):
        """Test user session management through API Gateway."""
        # Test get user sessions
        sessions_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/users/sessions"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = await test_helper.make_request(
            api_gateway_client,
            "GET",
            sessions_url,
            headers=headers
        )
        
        # Verify sessions response
        test_helper.assert_response_success(response)
        assert "sessions" in response["data"]
        assert isinstance(response["data"]["sessions"], list)
    
    @pytest.mark.gateway
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_database_integration(self, api_gateway_client, auth_token, test_helper):
        """Test database integration through API Gateway."""
        # Test user profile update (database write)
        profile_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/users/profile"
        headers = {"Authorization": f"Bearer {auth_token}"}
        profile_data = {
            "display_name": "Test User Updated",
            "email": "test@example.com"
        }
        
        response = await test_helper.make_request(
            api_gateway_client,
            "PUT",
            profile_url,
            headers=headers,
            json=profile_data
        )
        
        # Verify profile update response
        test_helper.assert_response_success(response)
        assert "message" in response["data"]
        assert "updated" in response["data"]["message"].lower()
        
        # Test user profile retrieval (database read)
        get_profile_response = await test_helper.make_request(
            api_gateway_client,
            "GET",
            profile_url,
            headers=headers
        )
        
        # Verify profile retrieval
        test_helper.assert_response_success(get_profile_response)
        assert "display_name" in get_profile_response["data"]
        assert "email" in get_profile_response["data"]
        assert get_profile_response["data"]["display_name"] == "Test User Updated"
    
    @pytest.mark.gateway
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_concurrent_authentication(self, api_gateway_client, test_user_credentials, test_helper):
        """Test concurrent authentication requests."""
        # Create multiple concurrent login requests
        login_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/auth/login"
        
        tasks = []
        for i in range(5):
            task = test_helper.make_request(
                api_gateway_client,
                "POST",
                login_url,
                json=test_user_credentials
            )
            tasks.append(task)
        
        # Execute concurrent requests
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all requests succeeded
        for response in responses:
            if isinstance(response, Exception):
                pytest.fail(f"Concurrent authentication failed: {response}")
            
            test_helper.assert_response_success(response)
            assert "access_token" in response["data"]
    
    @pytest.mark.gateway
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, api_gateway_client, test_helper):
        """Test authentication error handling."""
        # Test login with invalid credentials
        login_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/auth/login"
        invalid_credentials = {
            "username": "invalid_user",
            "password": "invalid_password",
            "tron_address": "invalid_address",
            "tron_signature": "invalid_signature"
        }
        
        response = await test_helper.make_request(
            api_gateway_client,
            "POST",
            login_url,
            json=invalid_credentials
        )
        
        # Verify error response
        assert response["status"] == 401
        assert "error" in response["data"]
        assert response["data"]["error"]["code"] == "LUCID_ERR_2XXX"
    
    @pytest.mark.gateway
    @pytest.mark.auth
    @pytest.mark.asyncio
    async def test_authentication_performance(self, api_gateway_client, test_user_credentials, test_helper):
        """Test authentication performance."""
        login_url = f"{test_helper.TEST_CONFIG['api_gateway_url']}/auth/login"
        
        # Measure login time
        start_time = time.time()
        response = await test_helper.make_request(
            api_gateway_client,
            "POST",
            login_url,
            json=test_user_credentials
        )
        end_time = time.time()
        
        # Verify performance
        test_helper.assert_response_success(response)
        login_time = end_time - start_time
        
        # Authentication should complete within 2 seconds
        assert login_time < 2.0, f"Authentication took {login_time:.2f}s, expected < 2.0s"
        
        # Verify response time headers
        assert "X-Response-Time" in response["headers"] or "X-Process-Time" in response["headers"]
