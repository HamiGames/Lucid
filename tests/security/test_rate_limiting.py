"""
Rate Limiting Security Tests

Tests rate limiting enforcement, tiered rate limits,
and protection against abuse and DoS attacks.

Author: Lucid Development Team
Version: 1.0.0
"""

import pytest
import time
import asyncio
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
import redis.asyncio as redis
import sys
sys.path.insert(0, '03-api-gateway')
from middleware.rate_limit import RateLimitMiddleware
sys.path.insert(0, '03-api-gateway')
from services.rate_limit_service import RateLimitService
sys.path.insert(0, '03-api-gateway')
from models.common import RateLimitTier


class TestRateLimitingSecurity:
    """Test rate limiting security mechanisms."""

    def setup_method(self):
        """Setup test fixtures."""
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.rate_limit_service = RateLimitService(self.redis_client)
        self.rate_limit_middleware = RateLimitMiddleware(
            app=None,
            redis_client=self.redis_client
        )
        
        # Test client identifiers
        self.public_ip = "192.168.1.100"
        self.authenticated_user_id = "user-123"
        self.admin_user_id = "admin-456"

    def test_public_rate_limiting(self):
        """Test public endpoint rate limiting."""
        # Test public rate limit (100 requests/minute)
        for i in range(101):
            response = self.rate_limit_middleware.check_rate_limit(
                client_id=self.public_ip,
                endpoint="/api/v1/public/info",
                tier=RateLimitTier.PUBLIC
            )
            
            if i < 100:
                assert response.allowed is True
            else:
                assert response.allowed is False
                assert response.retry_after > 0

    def test_authenticated_rate_limiting(self):
        """Test authenticated user rate limiting."""
        # Test authenticated rate limit (1000 requests/minute)
        for i in range(1001):
            response = self.rate_limit_middleware.check_rate_limit(
                client_id=self.authenticated_user_id,
                endpoint="/api/v1/sessions",
                tier=RateLimitTier.AUTHENTICATED
            )
            
            if i < 1000:
                assert response.allowed is True
            else:
                assert response.allowed is False
                assert response.retry_after > 0

    def test_admin_rate_limiting(self):
        """Test admin endpoint rate limiting."""
        # Test admin rate limit (10000 requests/minute)
        for i in range(10001):
            response = self.rate_limit_middleware.check_rate_limit(
                client_id=self.admin_user_id,
                endpoint="/api/v1/admin/dashboard",
                tier=RateLimitTier.ADMIN
            )
            
            if i < 10000:
                assert response.allowed is True
            else:
                assert response.allowed is False
                assert response.retry_after > 0

    def test_rate_limit_headers(self):
        """Test rate limit response headers."""
        response = self.rate_limit_middleware.check_rate_limit(
            client_id=self.public_ip,
            endpoint="/api/v1/public/info",
            tier=RateLimitTier.PUBLIC
        )
        
        assert hasattr(response, 'remaining_requests')
        assert hasattr(response, 'reset_time')
        assert hasattr(response, 'retry_after')

    def test_rate_limit_reset_mechanism(self):
        """Test rate limit reset mechanism."""
        # Exhaust rate limit
        for i in range(101):
            self.rate_limit_middleware.check_rate_limit(
                client_id=self.public_ip,
                endpoint="/api/v1/public/info",
                tier=RateLimitTier.PUBLIC
            )
        
        # Wait for reset (mock time)
        with patch('time.time', return_value=time.time() + 61):  # 61 seconds later
            response = self.rate_limit_middleware.check_rate_limit(
                client_id=self.public_ip,
                endpoint="/api/v1/public/info",
                tier=RateLimitTier.PUBLIC
            )
            assert response.allowed is True

    def test_different_endpoints_rate_limiting(self):
        """Test rate limiting for different endpoints."""
        # Test that different endpoints have separate rate limits
        endpoint_a = "/api/v1/sessions"
        endpoint_b = "/api/v1/users"
        
        # Exhaust rate limit for endpoint A
        for i in range(1001):
            self.rate_limit_middleware.check_rate_limit(
                client_id=self.authenticated_user_id,
                endpoint=endpoint_a,
                tier=RateLimitTier.AUTHENTICATED
            )
        
        # Endpoint B should still be available
        response = self.rate_limit_middleware.check_rate_limit(
            client_id=self.authenticated_user_id,
            endpoint=endpoint_b,
            tier=RateLimitTier.AUTHENTICATED
        )
        assert response.allowed is True

    def test_concurrent_rate_limiting(self):
        """Test concurrent rate limiting."""
        async def make_request():
            return self.rate_limit_middleware.check_rate_limit(
                client_id=self.public_ip,
                endpoint="/api/v1/public/info",
                tier=RateLimitTier.PUBLIC
            )
        
        # Test concurrent requests
        tasks = [make_request() for _ in range(50)]
        responses = asyncio.run(asyncio.gather(*tasks))
        
        # All should be allowed initially
        allowed_count = sum(1 for r in responses if r.allowed)
        assert allowed_count > 0

    def test_rate_limit_bypass_attempts(self):
        """Test protection against rate limit bypass attempts."""
        # Test IP spoofing attempt
        spoofed_ips = ["192.168.1.101", "192.168.1.102", "192.168.1.103"]
        
        for spoofed_ip in spoofed_ips:
            # Each IP should have its own rate limit
            for i in range(101):
                response = self.rate_limit_middleware.check_rate_limit(
                    client_id=spoofed_ip,
                    endpoint="/api/v1/public/info",
                    tier=RateLimitTier.PUBLIC
                )
                
                if i < 100:
                    assert response.allowed is True
                else:
                    assert response.allowed is False

    def test_user_agent_rate_limiting(self):
        """Test rate limiting based on user agent."""
        # Test different user agents
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "curl/7.68.0",
            "Python-requests/2.25.1"
        ]
        
        for user_agent in user_agents:
            # Each user agent should have separate rate limit
            response = self.rate_limit_middleware.check_rate_limit(
                client_id=f"{self.public_ip}:{user_agent}",
                endpoint="/api/v1/public/info",
                tier=RateLimitTier.PUBLIC
            )
            assert response.allowed is True

    def test_rate_limit_escalation_protection(self):
        """Test protection against rate limit escalation."""
        # Test that users cannot escalate their rate limits
        with pytest.raises(HTTPException) as exc_info:
            self.rate_limit_service.escalate_rate_limit(
                user_id=self.authenticated_user_id,
                requested_tier=RateLimitTier.ADMIN
            )
        assert exc_info.value.status_code == 403

    def test_rate_limit_whitelist(self):
        """Test rate limit whitelist functionality."""
        # Test whitelisted IP
        whitelisted_ip = "192.168.1.1"
        
        # Whitelisted IP should have unlimited access
        for i in range(10000):
            response = self.rate_limit_middleware.check_rate_limit(
                client_id=whitelisted_ip,
                endpoint="/api/v1/public/info",
                tier=RateLimitTier.PUBLIC
            )
            assert response.allowed is True

    def test_rate_limit_blacklist(self):
        """Test rate limit blacklist functionality."""
        # Test blacklisted IP
        blacklisted_ip = "192.168.1.999"
        
        # Blacklisted IP should be denied
        response = self.rate_limit_middleware.check_rate_limit(
            client_id=blacklisted_ip,
            endpoint="/api/v1/public/info",
            tier=RateLimitTier.PUBLIC
        )
        assert response.allowed is False

    def test_rate_limit_geolocation(self):
        """Test rate limiting based on geolocation."""
        # Test different countries
        countries = ["US", "CN", "RU", "IR"]
        
        for country in countries:
            # Each country should have separate rate limit
            response = self.rate_limit_middleware.check_rate_limit(
                client_id=f"{self.public_ip}:{country}",
                endpoint="/api/v1/public/info",
                tier=RateLimitTier.PUBLIC
            )
            assert response.allowed is True

    def test_rate_limit_adaptive_throttling(self):
        """Test adaptive rate limiting based on system load."""
        # Test high load scenario
        with patch('03-api-gateway.services.rate_limit_service.get_system_load', return_value=0.9):
            response = self.rate_limit_middleware.check_rate_limit(
                client_id=self.public_ip,
                endpoint="/api/v1/public/info",
                tier=RateLimitTier.PUBLIC
            )
            # Should be more restrictive under high load
            assert response.remaining_requests < 100

    def test_rate_limit_cleanup(self):
        """Test rate limit data cleanup."""
        # Create rate limit entries
        for i in range(10):
            self.rate_limit_middleware.check_rate_limit(
                client_id=f"test-{i}",
                endpoint="/api/v1/public/info",
                tier=RateLimitTier.PUBLIC
            )
        
        # Cleanup expired entries
        cleaned_count = self.rate_limit_service.cleanup_expired_entries()
        assert cleaned_count >= 0

    def test_rate_limit_metrics(self):
        """Test rate limit metrics collection."""
        # Generate some rate limit events
        for i in range(10):
            self.rate_limit_middleware.check_rate_limit(
                client_id=self.public_ip,
                endpoint="/api/v1/public/info",
                tier=RateLimitTier.PUBLIC
            )
        
        # Test metrics collection
        metrics = self.rate_limit_service.get_rate_limit_metrics()
        assert 'total_requests' in metrics
        assert 'blocked_requests' in metrics
        assert 'rate_limit_hits' in metrics

    def test_rate_limit_configuration_security(self):
        """Test rate limit configuration security."""
        # Test that rate limits cannot be modified by unauthorized users
        with pytest.raises(HTTPException) as exc_info:
            self.rate_limit_service.update_rate_limit_config(
                user_id=self.authenticated_user_id,
                new_config={"public_limit": 10000}
            )
        assert exc_info.value.status_code == 403

    def test_rate_limit_audit_logging(self):
        """Test rate limit audit logging."""
        with patch('03-api-gateway.middleware.logging.AuditLogger') as mock_logger:
            # Generate rate limit event
            self.rate_limit_middleware.check_rate_limit(
                client_id=self.public_ip,
                endpoint="/api/v1/public/info",
                tier=RateLimitTier.PUBLIC
            )
            
            # Verify audit logging
            mock_logger.log_rate_limit_event.assert_called()

    def test_rate_limit_ddos_protection(self):
        """Test DDoS protection through rate limiting."""
        # Simulate DDoS attack
        attack_ips = [f"192.168.1.{i}" for i in range(1, 101)]
        
        for ip in attack_ips:
            # Each IP should be rate limited individually
            for i in range(101):
                response = self.rate_limit_middleware.check_rate_limit(
                    client_id=ip,
                    endpoint="/api/v1/public/info",
                    tier=RateLimitTier.PUBLIC
                )
                
                if i < 100:
                    assert response.allowed is True
                else:
                    assert response.allowed is False

    def test_rate_limit_recovery_mechanism(self):
        """Test rate limit recovery mechanism."""
        # Exhaust rate limit
        for i in range(101):
            self.rate_limit_middleware.check_rate_limit(
                client_id=self.public_ip,
                endpoint="/api/v1/public/info",
                tier=RateLimitTier.PUBLIC
            )
        
        # Test gradual recovery
        recovery_time = 60  # 1 minute
        for second in range(0, recovery_time, 10):
            with patch('time.time', return_value=time.time() + second):
                response = self.rate_limit_middleware.check_rate_limit(
                    client_id=self.public_ip,
                    endpoint="/api/v1/public/info",
                    tier=RateLimitTier.PUBLIC
                )
                
                if second < 60:
                    assert response.allowed is False
                else:
                    assert response.allowed is True
