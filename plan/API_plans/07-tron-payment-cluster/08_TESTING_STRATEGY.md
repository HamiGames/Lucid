# TRON Payment System API - Testing Strategy

## Document Control

| Attribute | Value |
|-----------|-------|
| Document ID | TRON-API-TEST-008 |
| Version | 1.0.0 |
| Status | IN PROGRESS |
| Last Updated | 2025-10-12 |
| Owner | Lucid RDP Development Team |

---

## Overview

This document defines a comprehensive testing strategy for the TRON Payment System API, covering unit tests, integration tests, security tests, performance tests, and end-to-end validation. The strategy ensures reliability, security, and compliance with SPEC-1B-v2 requirements.

### Testing Principles

- **Test Coverage**: >80% code coverage requirement
- **Security First**: Comprehensive security testing
- **Performance Validation**: Load and stress testing
- **Integration Focus**: End-to-end workflow testing
- **Automated Validation**: CI/CD pipeline integration

---

## Unit Test Specifications

### Test Coverage Requirements

```python
# pytest configuration for unit tests
# pytest.ini
[tool:pytest]
testpaths = tests/unit
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --cov=payment_systems.tron_payment_service
    --cov-report=html:htmlcov
    --cov-report=xml:coverage.xml
    --cov-report=term-missing
    --cov-fail-under=80
    --maxfail=5
    --tb=short
markers =
    unit: Unit tests
    integration: Integration tests
    security: Security tests
    performance: Performance tests
    slow: Slow tests
```

### Payment Router Tests

```python
# tests/unit/test_payout_routers.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal
from datetime import datetime

from payment_systems.tron_payment_service.routers import PayoutRouterV0, PayoutRouterKYC
from payment_systems.tron_payment_service.models import PayoutRequest, PayoutResponse

class TestPayoutRouterV0:
    """Test suite for PayoutRouterV0 (non-KYC)"""
    
    @pytest.fixture
    def router_v0(self):
        return PayoutRouterV0()
    
    @pytest.fixture
    def valid_payout_request(self):
        return PayoutRequest(
            recipient_address="TYour33CharacterTRONAddressHere1234",
            amount_usdt=Decimal("5.50"),
            reason="Test payout",
            router_type="PayoutRouterV0"
        )
    
    @pytest.mark.unit
    async def test_create_payout_success(self, router_v0, valid_payout_request):
        """Test successful payout creation"""
        with patch.object(router_v0, '_validate_address') as mock_validate, \
             patch.object(router_v0, '_send_transaction') as mock_send:
            
            mock_validate.return_value = True
            mock_send.return_value = "0x1234567890abcdef..."
            
            result = await router_v0.create_payout(valid_payout_request)
            
            assert result.status == "pending"
            assert result.recipient_address == valid_payout_request.recipient_address
            assert result.amount_usdt == valid_payout_request.amount_usdt
            mock_validate.assert_called_once_with(valid_payout_request.recipient_address)
            mock_send.assert_called_once()
    
    @pytest.mark.unit
    async def test_create_payout_invalid_address(self, router_v0):
        """Test payout creation with invalid address"""
        invalid_request = PayoutRequest(
            recipient_address="invalid_address",
            amount_usdt=Decimal("5.50"),
            reason="Test payout",
            router_type="PayoutRouterV0"
        )
        
        with patch.object(router_v0, '_validate_address') as mock_validate:
            mock_validate.return_value = False
            
            with pytest.raises(ValueError, match="Invalid TRON address"):
                await router_v0.create_payout(invalid_request)
    
    @pytest.mark.unit
    async def test_create_payout_amount_limits(self, router_v0, valid_payout_request):
        """Test payout amount validation"""
        # Test minimum amount
        valid_payout_request.amount_usdt = Decimal("0.01")
        result = await router_v0.create_payout(valid_payout_request)
        assert result.amount_usdt == Decimal("0.01")
        
        # Test maximum amount
        valid_payout_request.amount_usdt = Decimal("10000.00")
        result = await router_v0.create_payout(valid_payout_request)
        assert result.amount_usdt == Decimal("10000.00")
        
        # Test amount too low
        valid_payout_request.amount_usdt = Decimal("0.005")
        with pytest.raises(ValueError, match="Amount too low"):
            await router_v0.create_payout(valid_payout_request)
        
        # Test amount too high
        valid_payout_request.amount_usdt = Decimal("10000.01")
        with pytest.raises(ValueError, match="Amount too high"):
            await router_v0.create_payout(valid_payout_request)

class TestPayoutRouterKYC:
    """Test suite for PayoutRouterKYC (KYC-gated)"""
    
    @pytest.fixture
    def router_kyc(self):
        return PayoutRouterKYC()
    
    @pytest.mark.unit
    async def test_kyc_verification_required(self, router_kyc, valid_payout_request):
        """Test KYC verification requirement"""
        with patch.object(router_kyc, '_verify_kyc_status') as mock_verify:
            mock_verify.return_value = False
            
            with pytest.raises(PermissionError, match="KYC verification required"):
                await router_kyc.create_payout(valid_payout_request)
    
    @pytest.mark.unit
    async def test_kyc_verified_payout(self, router_kyc, valid_payout_request):
        """Test successful KYC-verified payout"""
        with patch.object(router_kyc, '_verify_kyc_status') as mock_verify, \
             patch.object(router_kyc, '_send_transaction') as mock_send:
            
            mock_verify.return_value = True
            mock_send.return_value = "0x1234567890abcdef..."
            
            result = await router_kyc.create_payout(valid_payout_request)
            
            assert result.status == "pending"
            mock_verify.assert_called_once()
            mock_send.assert_called_once()
```

### TronService Tests

```python
# tests/unit/test_tron_service.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal

from payment_systems.tron_payment_service.services import TronService
from payment_systems.tron_payment_service.models import TronTransaction

class TestTronService:
    """Test suite for TronService"""
    
    @pytest.fixture
    def tron_service(self):
        return TronService(
            network="mainnet",
            node_url="https://api.trongrid.io",
            private_key="test_private_key"
        )
    
    @pytest.mark.unit
    async def test_send_usdt_transaction_success(self, tron_service):
        """Test successful USDT transaction"""
        with patch.object(tron_service, '_create_transaction') as mock_create, \
             patch.object(tron_service, '_sign_transaction') as mock_sign, \
             patch.object(tron_service, '_broadcast_transaction') as mock_broadcast:
            
            mock_create.return_value = MagicMock()
            mock_sign.return_value = "signed_transaction"
            mock_broadcast.return_value = "0x1234567890abcdef..."
            
            result = await tron_service.send_usdt_transaction(
                to_address="TYour33CharacterTRONAddressHere1234",
                amount_usdt=Decimal("5.50")
            )
            
            assert result.txid == "0x1234567890abcdef..."
            assert result.status == "pending"
            mock_create.assert_called_once()
            mock_sign.assert_called_once()
            mock_broadcast.assert_called_once()
    
    @pytest.mark.unit
    async def test_get_transaction_status(self, tron_service):
        """Test transaction status retrieval"""
        with patch.object(tron_service, '_query_transaction') as mock_query:
            mock_query.return_value = {
                "id": "0x1234567890abcdef...",
                "blockNumber": 12345678,
                "confirmations": 19,
                "contractResult": ["SUCCESS"]
            }
            
            result = await tron_service.get_transaction_status("0x1234567890abcdef...")
            
            assert result.txid == "0x1234567890abcdef..."
            assert result.confirmations == 19
            assert result.status == "confirmed"
    
    @pytest.mark.unit
    async def test_network_connection_failure(self, tron_service):
        """Test handling of network connection failures"""
        with patch.object(tron_service, '_query_transaction') as mock_query:
            mock_query.side_effect = ConnectionError("Network unavailable")
            
            with pytest.raises(ConnectionError, match="Network unavailable"):
                await tron_service.get_transaction_status("0x1234567890abcdef...")
```

### Circuit Breaker Tests

```python
# tests/unit/test_circuit_breaker.py
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from payment_systems.tron_payment_service.circuit_breaker import CircuitBreaker, SecurityLimits

class TestCircuitBreaker:
    """Test suite for CircuitBreaker"""
    
    @pytest.fixture
    def circuit_breaker(self):
        limits = SecurityLimits()
        limits.daily_limit_usdt = 1000.0
        limits.hourly_limit_usdt = 100.0
        limits.failure_threshold = 3
        return CircuitBreaker(limits)
    
    @pytest.mark.unit
    async def test_circuit_closed_normal_operation(self, circuit_breaker):
        """Test normal operation with closed circuit"""
        assert await circuit_breaker.check_limits(50.0) == True
        await circuit_breaker.record_success(50.0)
        assert circuit_breaker.state == "closed"
    
    @pytest.mark.unit
    async def test_circuit_opens_on_failure_threshold(self, circuit_breaker):
        """Test circuit opens when failure threshold reached"""
        for i in range(3):
            await circuit_breaker.record_failure()
        
        assert circuit_breaker.state == "open"
        assert await circuit_breaker.check_limits(50.0) == False
    
    @pytest.mark.unit
    async def test_daily_limit_enforcement(self, circuit_breaker):
        """Test daily limit enforcement"""
        # Exceed daily limit
        assert await circuit_breaker.check_limits(1001.0) == False
        assert circuit_breaker.state == "open"
    
    @pytest.mark.unit
    async def test_hourly_limit_enforcement(self, circuit_breaker):
        """Test hourly limit enforcement"""
        # Exceed hourly limit
        assert await circuit_breaker.check_limits(101.0) == False
        assert circuit_breaker.state == "open"
```

---

## Integration Test Scenarios

### API Gateway Integration Tests

```python
# tests/integration/test_api_gateway_integration.py
import pytest
import httpx
from fastapi.testclient import TestClient

from payment_systems.tron_payment_service.main import app
from payment_systems.tron_payment_service.auth import create_access_token

class TestAPIGatewayIntegration:
    """Integration tests for API Gateway communication"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_token(self):
        return create_access_token(data={"sub": "test_user", "role": "end_user"})
    
    @pytest.fixture
    def admin_token(self):
        return create_access_token(data={"sub": "admin_user", "role": "admin"})
    
    @pytest.mark.integration
    async def test_create_payout_via_gateway(self, client, auth_token):
        """Test payout creation through API Gateway proxy"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        payload = {
            "recipient_address": "TYour33CharacterTRONAddressHere1234",
            "amount_usdt": 5.50,
            "reason": "Test payout",
            "router_type": "PayoutRouterV0"
        }
        
        response = client.post("/api/payment/payouts", json=payload, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert data["recipient_address"] == payload["recipient_address"]
        assert data["amount_usdt"] == payload["amount_usdt"]
    
    @pytest.mark.integration
    async def test_batch_payout_via_gateway(self, client, admin_token):
        """Test batch payout creation through API Gateway"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {
            "payouts": [
                {
                    "recipient_address": "TYour33CharacterTRONAddressHere1234",
                    "amount_usdt": 5.50,
                    "reason": "Test payout 1"
                },
                {
                    "recipient_address": "TAnother33CharacterTRONAddressHere567",
                    "amount_usdt": 3.25,
                    "reason": "Test payout 2"
                }
            ],
            "router_type": "PayoutRouterV0"
        }
        
        response = client.post("/api/payment/payouts/batch", json=payload, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["total_payouts"] == 2
        assert len(data["payout_ids"]) == 2
    
    @pytest.mark.integration
    async def test_authentication_required(self, client):
        """Test that authentication is required for protected endpoints"""
        payload = {
            "recipient_address": "TYour33CharacterTRONAddressHere1234",
            "amount_usdt": 5.50,
            "reason": "Test payout",
            "router_type": "PayoutRouterV0"
        }
        
        response = client.post("/api/payment/payouts", json=payload)
        
        assert response.status_code == 401
        assert "Unauthorized" in response.json()["detail"]
    
    @pytest.mark.integration
    async def test_rate_limiting_enforcement(self, client, auth_token):
        """Test rate limiting enforcement"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        payload = {
            "recipient_address": "TYour33CharacterTRONAddressHere1234",
            "amount_usdt": 5.50,
            "reason": "Test payout",
            "router_type": "PayoutRouterV0"
        }
        
        # Make requests exceeding rate limit
        responses = []
        for i in range(15):  # Exceed limit of 10 per minute
            response = client.post("/api/payment/payouts", json=payload, headers=headers)
            responses.append(response.status_code)
        
        # Some requests should be rate limited
        assert 429 in responses
```

### Database Integration Tests

```python
# tests/integration/test_database_integration.py
import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

from payment_systems.tron_payment_service.database import MongoDB
from payment_systems.tron_payment_service.models import PayoutRequest, PayoutResponse

class TestDatabaseIntegration:
    """Integration tests for database operations"""
    
    @pytest.fixture
    async def mongo_client(self):
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        yield client
        await client.drop_database("test_payments")
        client.close()
    
    @pytest.fixture
    async def db(self, mongo_client):
        return MongoDB(mongo_client, "test_payments")
    
    @pytest.mark.integration
    async def test_create_payout_document(self, db):
        """Test creating payout document in database"""
        payout_request = PayoutRequest(
            recipient_address="TYour33CharacterTRONAddressHere1234",
            amount_usdt=5.50,
            reason="Test payout",
            router_type="PayoutRouterV0"
        )
        
        payout_response = await db.create_payout(payout_request)
        
        assert payout_response.payout_id is not None
        assert payout_response.status == "pending"
        assert payout_response.created_at is not None
        
        # Verify document was saved
        saved_payout = await db.get_payout(payout_response.payout_id)
        assert saved_payout is not None
        assert saved_payout.recipient_address == payout_request.recipient_address
    
    @pytest.mark.integration
    async def test_update_payout_status(self, db):
        """Test updating payout status"""
        payout_request = PayoutRequest(
            recipient_address="TYour33CharacterTRONAddressHere1234",
            amount_usdt=5.50,
            reason="Test payout",
            router_type="PayoutRouterV0"
        )
        
        payout_response = await db.create_payout(payout_request)
        
        # Update status to confirmed
        await db.update_payout_status(
            payout_response.payout_id,
            "confirmed",
            txid="0x1234567890abcdef...",
            confirmations=19
        )
        
        updated_payout = await db.get_payout(payout_response.payout_id)
        assert updated_payout.status == "confirmed"
        assert updated_payout.txid == "0x1234567890abcdef..."
        assert updated_payout.confirmations == 19
    
    @pytest.mark.integration
    async def test_list_payouts_with_filters(self, db):
        """Test listing payouts with filters"""
        # Create test payouts
        for i in range(5):
            payout_request = PayoutRequest(
                recipient_address=f"TYour33CharacterTRONAddressHere{i:02d}",
                amount_usdt=5.50 + i,
                reason=f"Test payout {i}",
                router_type="PayoutRouterV0"
            )
            await db.create_payout(payout_request)
        
        # Test listing with limit
        payouts = await db.list_payouts(limit=3)
        assert len(payouts) == 3
        
        # Test listing with status filter
        confirmed_payouts = await db.list_payouts(status="confirmed")
        assert len(confirmed_payouts) == 0  # None confirmed yet
        
        pending_payouts = await db.list_payouts(status="pending")
        assert len(pending_payouts) == 5  # All pending
```

---

## Load Testing Procedures

### Concurrent Payout Testing

```python
# tests/performance/test_concurrent_payouts.py
import pytest
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import time

class TestConcurrentPayouts:
    """Load tests for concurrent payout operations"""
    
    @pytest.fixture
    def base_url(self):
        return "http://localhost:8090"
    
    @pytest.fixture
    def auth_token(self):
        return create_access_token(data={"sub": "load_test_user", "role": "admin"})
    
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_concurrent_single_payouts(self, base_url, auth_token):
        """Test concurrent single payout creation"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        async def create_payout(session, payout_id):
            payload = {
                "recipient_address": f"TYour33CharacterTRONAddressHere{payout_id:02d}",
                "amount_usdt": 1.0,
                "reason": f"Load test payout {payout_id}",
                "router_type": "PayoutRouterV0"
            }
            
            async with session.post(
                f"{base_url}/api/payment/payouts",
                json=payload,
                headers=headers
            ) as response:
                return response.status, await response.json()
        
        # Create 50 concurrent requests
        async with aiohttp.ClientSession() as session:
            tasks = [create_payout(session, i) for i in range(50)]
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
        
        # Analyze results
        successful_requests = [r for r in results if isinstance(r, tuple) and r[0] == 201]
        failed_requests = [r for r in results if r not in successful_requests]
        
        print(f"Concurrent requests: {len(results)}")
        print(f"Successful: {len(successful_requests)}")
        print(f"Failed: {len(failed_requests)}")
        print(f"Duration: {end_time - start_time:.2f} seconds")
        print(f"Requests per second: {len(results) / (end_time - start_time):.2f}")
        
        # Assertions
        assert len(successful_requests) >= 40  # At least 80% success rate
        assert (end_time - start_time) < 30  # Complete within 30 seconds
    
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_concurrent_batch_payouts(self, base_url, auth_token):
        """Test concurrent batch payout creation"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        async def create_batch_payout(session, batch_id):
            payload = {
                "payouts": [
                    {
                        "recipient_address": f"TYour33CharacterTRONAddressHere{batch_id:02d}",
                        "amount_usdt": 1.0,
                        "reason": f"Batch test payout {batch_id}"
                    }
                ],
                "router_type": "PayoutRouterV0"
            }
            
            async with session.post(
                f"{base_url}/api/payment/payouts/batch",
                json=payload,
                headers=headers
            ) as response:
                return response.status, await response.json()
        
        # Create 20 concurrent batch requests
        async with aiohttp.ClientSession() as session:
            tasks = [create_batch_payout(session, i) for i in range(20)]
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
        
        successful_requests = [r for r in results if isinstance(r, tuple) and r[0] == 201]
        
        print(f"Concurrent batch requests: {len(results)}")
        print(f"Successful: {len(successful_requests)}")
        print(f"Duration: {end_time - start_time:.2f} seconds")
        
        assert len(successful_requests) >= 15  # At least 75% success rate
```

### Performance Benchmarks

```python
# tests/performance/test_performance_benchmarks.py
import pytest
import time
import statistics
from typing import List

class TestPerformanceBenchmarks:
    """Performance benchmark tests"""
    
    @pytest.mark.performance
    async def test_payout_creation_latency(self, client, auth_token):
        """Test payout creation latency benchmarks"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        payload = {
            "recipient_address": "TYour33CharacterTRONAddressHere1234",
            "amount_usdt": 5.50,
            "reason": "Performance test",
            "router_type": "PayoutRouterV0"
        }
        
        latencies: List[float] = []
        
        # Measure 100 requests
        for i in range(100):
            start_time = time.time()
            response = client.post("/api/payment/payouts", json=payload, headers=headers)
            end_time = time.time()
            
            assert response.status_code == 201
            latencies.append(end_time - start_time)
        
        # Calculate statistics
        mean_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
        
        print(f"Mean latency: {mean_latency:.3f}s")
        print(f"Median latency: {median_latency:.3f}s")
        print(f"P95 latency: {p95_latency:.3f}s")
        print(f"P99 latency: {p99_latency:.3f}s")
        
        # Assertions
        assert mean_latency < 2.0  # Mean latency under 2 seconds
        assert p95_latency < 5.0   # P95 latency under 5 seconds
        assert p99_latency < 10.0  # P99 latency under 10 seconds
    
    @pytest.mark.performance
    async def test_database_query_performance(self, db):
        """Test database query performance"""
        # Create test data
        for i in range(1000):
            payout_request = PayoutRequest(
                recipient_address=f"TYour33CharacterTRONAddressHere{i:04d}",
                amount_usdt=1.0 + (i % 100),
                reason=f"Performance test {i}",
                router_type="PayoutRouterV0"
            )
            await db.create_payout(payout_request)
        
        # Test query performance
        start_time = time.time()
        payouts = await db.list_payouts(limit=100)
        end_time = time.time()
        
        query_time = end_time - start_time
        print(f"Database query time: {query_time:.3f}s")
        
        assert query_time < 1.0  # Query should complete within 1 second
        assert len(payouts) == 100  # Should return correct number of results
```

---

## Security Testing Requirements

### Authentication Bypass Testing

```python
# tests/security/test_auth_bypass.py
import pytest
from fastapi.testclient import TestClient

class TestAuthenticationBypass:
    """Security tests for authentication bypass attempts"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.mark.security
    async def test_invalid_jwt_token(self, client):
        """Test handling of invalid JWT tokens"""
        headers = {"Authorization": "Bearer invalid_token"}
        payload = {
            "recipient_address": "TYour33CharacterTRONAddressHere1234",
            "amount_usdt": 5.50,
            "reason": "Test payout",
            "router_type": "PayoutRouterV0"
        }
        
        response = client.post("/api/payment/payouts", json=payload, headers=headers)
        
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]
    
    @pytest.mark.security
    async def test_expired_jwt_token(self, client):
        """Test handling of expired JWT tokens"""
        # Create expired token
        expired_token = create_access_token(
            data={"sub": "test_user", "role": "end_user"},
            expires_delta=timedelta(seconds=-1)  # Expired
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        payload = {
            "recipient_address": "TYour33CharacterTRONAddressHere1234",
            "amount_usdt": 5.50,
            "reason": "Test payout",
            "router_type": "PayoutRouterV0"
        }
        
        response = client.post("/api/payment/payouts", json=payload, headers=headers)
        
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()
    
    @pytest.mark.security
    async def test_malformed_authorization_header(self, client):
        """Test handling of malformed authorization headers"""
        malformed_headers = [
            {"Authorization": "invalid_format"},
            {"Authorization": "Bearer"},
            {"Authorization": "Bearer "},
            {"Authorization": "Basic dGVzdDp0ZXN0"},  # Basic auth instead of Bearer
        ]
        
        payload = {
            "recipient_address": "TYour33CharacterTRONAddressHere1234",
            "amount_usdt": 5.50,
            "reason": "Test payout",
            "router_type": "PayoutRouterV0"
        }
        
        for headers in malformed_headers:
            response = client.post("/api/payment/payouts", json=payload, headers=headers)
            assert response.status_code == 401
    
    @pytest.mark.security
    async def test_privilege_escalation_attempts(self, client):
        """Test privilege escalation attempts"""
        # Create token with end_user role
        user_token = create_access_token(data={"sub": "test_user", "role": "end_user"})
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # Try to access admin-only endpoint
        response = client.get("/api/payment/stats", headers=headers)
        
        # Should be forbidden or limited access
        assert response.status_code in [403, 200]  # 403 forbidden or 200 with limited data
        
        if response.status_code == 200:
            data = response.json()
            # Verify limited data is returned
            assert "circuit_breaker_status" not in data  # Admin-only field
```

### Rate Limit Testing

```python
# tests/security/test_rate_limiting.py
import pytest
import time
from fastapi.testclient import TestClient

class TestRateLimiting:
    """Security tests for rate limiting"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_token(self):
        return create_access_token(data={"sub": "test_user", "role": "end_user"})
    
    @pytest.mark.security
    async def test_rate_limit_enforcement(self, client, auth_token):
        """Test rate limit enforcement"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        payload = {
            "recipient_address": "TYour33CharacterTRONAddressHere1234",
            "amount_usdt": 5.50,
            "reason": "Rate limit test",
            "router_type": "PayoutRouterV0"
        }
        
        # Make requests exceeding rate limit
        responses = []
        for i in range(15):  # Exceed limit of 10 per minute
            response = client.post("/api/payment/payouts", json=payload, headers=headers)
            responses.append(response.status_code)
            
            # Small delay to avoid overwhelming
            time.sleep(0.1)
        
        # Verify rate limiting occurred
        rate_limited_responses = [r for r in responses if r == 429]
        assert len(rate_limited_responses) > 0
        
        # Verify rate limit headers are present
        response = client.post("/api/payment/payouts", json=payload, headers=headers)
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
    
    @pytest.mark.security
    async def test_rate_limit_bypass_attempts(self, client):
        """Test rate limit bypass attempts"""
        # Try different user tokens
        tokens = [
            create_access_token(data={"sub": f"user_{i}", "role": "end_user"})
            for i in range(5)
        ]
        
        payload = {
            "recipient_address": "TYour33CharacterTRONAddressHere1234",
            "amount_usdt": 5.50,
            "reason": "Rate limit bypass test",
            "router_type": "PayoutRouterV0"
        }
        
        # Each user should have independent rate limits
        for token in tokens:
            headers = {"Authorization": f"Bearer {token}"}
            
            # Make requests up to limit
            for i in range(10):
                response = client.post("/api/payment/payouts", json=payload, headers=headers)
                assert response.status_code in [201, 429]  # Should not be 401
            
            # Next request should be rate limited
            response = client.post("/api/payment/payouts", json=payload, headers=headers)
            assert response.status_code == 429
```

---

## TRON Network Mocking Strategies

### Mock TRON Service

```python
# tests/mocks/mock_tron_service.py
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal
from datetime import datetime

class MockTronService:
    """Mock TRON service for testing"""
    
    def __init__(self):
        self.transactions = {}
        self.next_txid = 1
    
    async def send_usdt_transaction(self, to_address: str, amount_usdt: Decimal):
        """Mock USDT transaction sending"""
        txid = f"0x{self.next_txid:064x}"
        self.next_txid += 1
        
        transaction = {
            "txid": txid,
            "to_address": to_address,
            "amount_usdt": float(amount_usdt),
            "status": "pending",
            "created_at": datetime.utcnow(),
            "confirmations": 0
        }
        
        self.transactions[txid] = transaction
        return transaction
    
    async def get_transaction_status(self, txid: str):
        """Mock transaction status retrieval"""
        if txid not in self.transactions:
            raise ValueError(f"Transaction not found: {txid}")
        
        transaction = self.transactions[txid]
        
        # Simulate confirmation progress
        if transaction["confirmations"] < 19:
            transaction["confirmations"] += 1
            if transaction["confirmations"] >= 19:
                transaction["status"] = "confirmed"
        
        return transaction
    
    async def get_balance(self, address: str):
        """Mock balance retrieval"""
        return Decimal("1000.0")  # Mock balance
    
    async def validate_address(self, address: str):
        """Mock address validation"""
        return address.startswith("T") and len(address) == 34

# Pytest fixture for mock service
@pytest.fixture
def mock_tron_service():
    return MockTronService()

# Pytest fixture to replace real service
@pytest.fixture
def app_with_mock_tron(mock_tron_service):
    with patch('payment_systems.tron_payment_service.services.TronService') as mock:
        mock.return_value = mock_tron_service
        yield app
```

### Mock Database

```python
# tests/mocks/mock_database.py
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from typing import List, Optional

class MockMongoDB:
    """Mock MongoDB for testing"""
    
    def __init__(self):
        self.payouts = {}
        self.next_id = 1
    
    async def create_payout(self, payout_request):
        """Mock payout creation"""
        payout_id = f"payout_{self.next_id:05d}"
        self.next_id += 1
        
        payout = {
            "payout_id": payout_id,
            "status": "pending",
            "recipient_address": payout_request.recipient_address,
            "amount_usdt": float(payout_request.amount_usdt),
            "reason": payout_request.reason,
            "router_type": payout_request.router_type,
            "created_at": datetime.utcnow(),
            "request_id": f"req_{payout_id}"
        }
        
        self.payouts[payout_id] = payout
        return payout
    
    async def get_payout(self, payout_id: str):
        """Mock payout retrieval"""
        return self.payouts.get(payout_id)
    
    async def list_payouts(self, limit: int = 20, offset: int = 0, **filters):
        """Mock payout listing"""
        all_payouts = list(self.payouts.values())
        
        # Apply filters
        if "status" in filters:
            all_payouts = [p for p in all_payouts if p["status"] == filters["status"]]
        
        # Apply pagination
        start = offset
        end = offset + limit
        return all_payouts[start:end]
    
    async def update_payout_status(self, payout_id: str, status: str, **updates):
        """Mock payout status update"""
        if payout_id in self.payouts:
            self.payouts[payout_id]["status"] = status
            self.payouts[payout_id].update(updates)
            return True
        return False

@pytest.fixture
def mock_database():
    return MockMongoDB()
```

---

## Test Data Generation Utilities

### Test Data Factory

```python
# tests/factories/test_data_factory.py
import factory
from decimal import Decimal
from datetime import datetime, timedelta
import random
import string

from payment_systems.tron_payment_service.models import (
    PayoutRequest, PayoutResponse, BatchPayoutRequest
)

class PayoutRequestFactory(factory.Factory):
    """Factory for creating test PayoutRequest objects"""
    
    class Meta:
        model = PayoutRequest
    
    recipient_address = factory.LazyFunction(
        lambda: f"T{''.join(random.choices(string.ascii_letters + string.digits, k=33))}"
    )
    amount_usdt = factory.LazyFunction(lambda: Decimal(str(random.uniform(0.01, 1000.0))))
    reason = factory.Faker('sentence', nb_words=4)
    router_type = factory.Iterator(["PayoutRouterV0", "PayoutRouterKYC"])
    priority = factory.Iterator(["LOW", "NORMAL", "HIGH", "URGENT"])
    batch_type = factory.Iterator(["IMMEDIATE", "HOURLY", "DAILY", "WEEKLY"])
    session_id = factory.LazyFunction(
        lambda: f"session_{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"
    )
    node_id = factory.LazyFunction(
        lambda: f"node_{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"
    )

class PayoutResponseFactory(factory.Factory):
    """Factory for creating test PayoutResponse objects"""
    
    class Meta:
        model = PayoutResponse
    
    payout_id = factory.LazyFunction(
        lambda: f"payout_{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"
    )
    status = factory.Iterator(["pending", "processing", "confirmed", "failed"])
    recipient_address = factory.LazyFunction(
        lambda: f"T{''.join(random.choices(string.ascii_letters + string.digits, k=33))}"
    )
    amount_usdt = factory.LazyFunction(lambda: Decimal(str(random.uniform(0.01, 1000.0))))
    router_type = factory.Iterator(["PayoutRouterV0", "PayoutRouterKYC"])
    priority = factory.Iterator(["LOW", "NORMAL", "HIGH", "URGENT"])
    batch_type = factory.Iterator(["IMMEDIATE", "HOURLY", "DAILY", "WEEKLY"])
    txid = factory.LazyFunction(
        lambda: f"0x{''.join(random.choices(string.ascii_lowercase + string.digits, k=64))}"
    )
    confirmations = factory.LazyFunction(lambda: random.randint(0, 19))
    created_at = factory.LazyFunction(datetime.utcnow)
    request_id = factory.LazyFunction(
        lambda: f"req_{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"
    )

class BatchPayoutRequestFactory(factory.Factory):
    """Factory for creating test BatchPayoutRequest objects"""
    
    class Meta:
        model = BatchPayoutRequest
    
    payouts = factory.List([
        factory.SubFactory(PayoutRequestFactory) for _ in range(random.randint(1, 5))
    ])
    router_type = factory.Iterator(["PayoutRouterV0", "PayoutRouterKYC"])
    priority = factory.Iterator(["LOW", "NORMAL", "HIGH", "URGENT"])
    batch_type = factory.Iterator(["HOURLY", "DAILY", "WEEKLY"])

# Test data generators
def generate_test_payouts(count: int) -> List[PayoutRequest]:
    """Generate multiple test payout requests"""
    return PayoutRequestFactory.build_batch(count)

def generate_test_batch_payouts(count: int) -> List[BatchPayoutRequest]:
    """Generate multiple test batch payout requests"""
    return BatchPayoutRequestFactory.build_batch(count)

def generate_edge_case_payouts() -> List[PayoutRequest]:
    """Generate edge case payout requests for testing"""
    edge_cases = [
        # Minimum amount
        PayoutRequestFactory.build(amount_usdt=Decimal("0.01")),
        # Maximum amount
        PayoutRequestFactory.build(amount_usdt=Decimal("10000.00")),
        # Very long reason
        PayoutRequestFactory.build(reason="A" * 200),
        # Special characters in reason
        PayoutRequestFactory.build(reason="Special chars: !@#$%^&*()"),
        # Unicode characters
        PayoutRequestFactory.build(reason="Unicode: 🚀💰💎"),
    ]
    return edge_cases
```

---

## Pytest Configuration

### Test Configuration

```ini
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --cov=payment_systems.tron_payment_service
    --cov-report=html:htmlcov
    --cov-report=xml:coverage.xml
    --cov-report=term-missing
    --cov-fail-under=80
    --maxfail=5
    --tb=short
    -v
markers =
    unit: Unit tests
    integration: Integration tests
    security: Security tests
    performance: Performance tests
    slow: Slow tests
    mock: Tests using mocks
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

### Test Categories

```python
# Test execution commands
# Run unit tests only
pytest -m unit

# Run integration tests only
pytest -m integration

# Run security tests only
pytest -m security

# Run performance tests only
pytest -m performance

# Run all tests except slow ones
pytest -m "not slow"

# Run with coverage
pytest --cov=payment_systems.tron_payment_service --cov-report=html

# Run specific test file
pytest tests/unit/test_payout_routers.py -v

# Run with parallel execution
pytest -n auto
```

---

## CI/CD Integration

### GitHub Actions Configuration

```yaml
# .github/workflows/test-payment-api.yml
name: TRON Payment API Tests

on:
  push:
    branches: [main, develop]
    paths: ['payment-systems/tron-payment-service/**']
  pull_request:
    branches: [main]
    paths: ['payment-systems/tron-payment-service/**']

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      mongodb:
        image: mongo:7.0
        ports:
          - 27017:27017
        options: >-
          --health-cmd "mongosh --eval 'db.runCommand(\"ping\").ok'"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r payment-systems/tron-payment-service/requirements.txt
          pip install -r payment-systems/tron-payment-service/requirements-dev.txt
      
      - name: Run unit tests
        run: |
          pytest -m unit --cov=payment_systems.tron_payment_service --cov-report=xml
      
      - name: Run integration tests
        run: |
          pytest -m integration
      
      - name: Run security tests
        run: |
          pytest -m security
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: payment-api
          name: payment-api-coverage
      
      - name: Run performance tests
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        run: |
          pytest -m performance --maxfail=3
```

### Test Reporting

```python
# Test reporting configuration
import pytest
import json
from datetime import datetime

class TestReporter:
    """Custom test reporter for detailed reporting"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "coverage": 0.0
            }
        }
    
    def pytest_runtest_logreport(self, report):
        """Capture test results"""
        if report.when == "call":
            self.results["tests"].append({
                "name": report.nodeid,
                "outcome": report.outcome,
                "duration": report.duration,
                "message": report.longreprtext if report.failed else None
            })
    
    def pytest_sessionfinish(self, session, exitstatus):
        """Generate final report"""
        self.results["summary"]["total"] = len(self.results["tests"])
        self.results["summary"]["passed"] = len([t for t in self.results["tests"] if t["outcome"] == "passed"])
        self.results["summary"]["failed"] = len([t for t in self.results["tests"] if t["outcome"] == "failed"])
        self.results["summary"]["skipped"] = len([t for t in self.results["tests"] if t["outcome"] == "skipped"])
        
        # Save report
        with open("test_report.json", "w") as f:
            json.dump(self.results, f, indent=2)

# Usage in pytest.ini
addopts = --tb=short --reporter=TestReporter
```

---

## References

- [07_SECURITY_COMPLIANCE.md](07_SECURITY_COMPLIANCE.md) - Security implementation
- [09_DEPLOYMENT_PROCEDURES.md](09_DEPLOYMENT_PROCEDURES.md) - Deployment testing
- [pytest Documentation](https://docs.pytest.org/) - Testing framework
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/) - API testing guide
- [TRON Testnet](https://developers.tron.network/docs/testnet) - TRON testing resources

---

**Document Status**: [IN PROGRESS]  
**Last Review**: 2025-10-12  
**Next Review**: 2025-11-12
