# API Gateway Cluster - Testing & Validation

## Overview

This document defines comprehensive testing strategies, validation procedures, and performance benchmarks for the API Gateway cluster, ensuring reliability, security, and performance compliance.

## Testing Strategy

### Testing Pyramid

```
┌─────────────────────────────────────────────────────────────┐
│                    E2E Tests (5%)                         │
│  - Full user workflows                                     │
│  - Cross-service integration                               │
│  - Performance benchmarks                                  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                  Integration Tests (25%)                   │
│  - API endpoint testing                                    │
│  - Database integration                                    │
│  - External service mocking                                │
│  - Authentication flows                                    │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                   Unit Tests (70%)                         │
│  - Business logic validation                               │
│  - Utility function testing                                │
│  - Model validation                                        │
│  - Security function testing                               │
└─────────────────────────────────────────────────────────────┘
```

## Unit Testing

### Test Configuration

```python
# conftest.py
import pytest
import asyncio
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.config import get_settings
from app.database.connection import get_database

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_settings():
    """Test configuration settings"""
    settings = get_settings()
    settings.MONGODB_URI = "mongodb://localhost:27017/lucid_gateway_test"
    settings.REDIS_URL = "redis://localhost:6379/1"
    settings.JWT_SECRET_KEY = "test-secret-key-for-testing-only"
    settings.DEBUG = True
    return settings

@pytest.fixture
async def test_client(test_settings):
    """Test client with mocked dependencies"""
    with TestClient(app) as client:
        yield client

@pytest.fixture
async def mock_mongodb():
    """Mock MongoDB client"""
    mock_client = AsyncMock()
    mock_db = AsyncMock()
    mock_collection = AsyncMock()
    
    mock_client.lucid_gateway_test = mock_db
    mock_db.users = mock_collection
    mock_db.sessions = mock_collection
    mock_db.auth_tokens = mock_collection
    
    return mock_client

@pytest.fixture
async def mock_redis():
    """Mock Redis client"""
    mock_client = AsyncMock()
    return mock_client

@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "test@example.com",
        "username": "testuser",
        "password_hash": "$2b$12$test_hash",
        "role": "user",
        "created_at": "2025-01-10T19:08:00Z"
    }

@pytest.fixture
def sample_jwt_token(test_settings, sample_user_data):
    """Sample JWT token for testing"""
    import jwt
    from datetime import datetime, timedelta
    
    payload = {
        "jti": "token-uuid-here",
        "sub": sample_user_data["user_id"],
        "user_id": sample_user_data["user_id"],
        "email": sample_user_data["email"],
        "username": sample_user_data["username"],
        "role": sample_user_data["role"],
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=15),
        "iss": "api-gateway",
        "aud": "lucid-blockchain"
    }
    
    return jwt.encode(payload, test_settings.JWT_SECRET_KEY, algorithm="HS256")
```

### Authentication Service Tests

```python
# tests/test_auth_service.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.auth_service import AuthService
from app.models.auth import LoginRequest, VerifyRequest
from app.utils.security import TokenManager

class TestAuthService:
    """Test cases for authentication service"""
    
    @pytest.fixture
    def auth_service(self, mock_mongodb, mock_redis):
        """Auth service instance with mocked dependencies"""
        return AuthService(mock_mongodb, mock_redis)
    
    @pytest.mark.asyncio
    async def test_magic_link_generation(self, auth_service, sample_user_data):
        """Test magic link generation"""
        # Mock user lookup
        auth_service.user_repo.get_user_by_email = AsyncMock(return_value=sample_user_data)
        auth_service.email_service.send_magic_link = AsyncMock(return_value=True)
        
        # Test magic link generation
        request = LoginRequest(email="test@example.com")
        result = await auth_service.initiate_login(request)
        
        # Assertions
        assert result["success"] is True
        assert "message" in result
        auth_service.user_repo.get_user_by_email.assert_called_once_with("test@example.com")
        auth_service.email_service.send_magic_link.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_totp_verification_success(self, auth_service, sample_user_data):
        """Test successful TOTP verification"""
        # Mock dependencies
        auth_service.user_repo.get_user_by_email = AsyncMock(return_value=sample_user_data)
        auth_service.totp_service.verify_code = AsyncMock(return_value=True)
        auth_service.token_manager.create_tokens = MagicMock(return_value={
            "access_token": "access_token_here",
            "refresh_token": "refresh_token_here"
        })
        
        # Test TOTP verification
        request = VerifyRequest(email="test@example.com", code="123456")
        result = await auth_service.verify_totp(request)
        
        # Assertions
        assert result["access_token"] == "access_token_here"
        assert result["refresh_token"] == "refresh_token_here"
        assert result["user"]["user_id"] == sample_user_data["user_id"]
    
    @pytest.mark.asyncio
    async def test_totp_verification_failure(self, auth_service, sample_user_data):
        """Test failed TOTP verification"""
        # Mock dependencies
        auth_service.user_repo.get_user_by_email = AsyncMock(return_value=sample_user_data)
        auth_service.totp_service.verify_code = AsyncMock(return_value=False)
        
        # Test TOTP verification
        request = VerifyRequest(email="test@example.com", code="000000")
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.verify_totp(request)
        
        assert exc_info.value.status_code == 401
        assert "Invalid verification code" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_token_refresh(self, auth_service, sample_user_data):
        """Test token refresh functionality"""
        # Mock dependencies
        auth_service.user_repo.get_user_by_id = AsyncMock(return_value=sample_user_data)
        auth_service.token_manager.create_tokens = MagicMock(return_value={
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token"
        })
        
        # Test token refresh
        result = await auth_service.refresh_token("refresh_token_here")
        
        # Assertions
        assert result["access_token"] == "new_access_token"
        assert result["refresh_token"] == "new_refresh_token"
    
    @pytest.mark.asyncio
    async def test_user_logout(self, auth_service, sample_user_data):
        """Test user logout functionality"""
        # Mock dependencies
        auth_service.token_manager.blacklist_token = AsyncMock(return_value=True)
        
        # Test logout
        result = await auth_service.logout("token_jti_here")
        
        # Assertions
        assert result["success"] is True
        assert "Successfully logged out" in result["message"]
        auth_service.token_manager.blacklist_token.assert_called_once_with("token_jti_here")
```

### Rate Limiting Tests

```python
# tests/test_rate_limiting.py
import pytest
from unittest.mock import AsyncMock, patch
from app.middleware.rate_limit import RateLimitMiddleware
from fastapi import Request
from starlette.responses import Response

class TestRateLimiting:
    """Test cases for rate limiting middleware"""
    
    @pytest.fixture
    def rate_limit_middleware(self, mock_redis):
        """Rate limiting middleware with mocked Redis"""
        middleware = RateLimitMiddleware(None)
        middleware.redis_client = mock_redis
        return middleware
    
    @pytest.mark.asyncio
    async def test_public_endpoint_rate_limit(self, rate_limit_middleware):
        """Test rate limiting for public endpoints"""
        # Mock Redis responses
        rate_limit_middleware.redis_client.get = AsyncMock(return_value="50")  # Current count
        rate_limit_middleware.redis_client.incr = AsyncMock(return_value=51)
        rate_limit_middleware.redis_client.expire = AsyncMock(return_value=True)
        
        # Create mock request
        request = Request(
            scope={
                "type": "http",
                "method": "GET",
                "path": "/api/v1/meta/health",
                "headers": [],
                "client": ("127.0.0.1", 8080)
            }
        )
        
        # Test rate limit check
        tier = rate_limit_middleware._get_rate_limit_tier(request)
        assert tier == "public"
        
        # Test rate limit validation
        allowed = await rate_limit_middleware._check_rate_limit(request, tier)
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, rate_limit_middleware):
        """Test rate limit exceeded scenario"""
        # Mock Redis responses - limit exceeded
        rate_limit_middleware.redis_client.get = AsyncMock(return_value="100")  # At limit
        rate_limit_middleware.redis_client.get.side_effect = ["100", "0"]  # No burst allowance
        
        # Create mock request
        request = Request(
            scope={
                "type": "http",
                "method": "GET",
                "path": "/api/v1/meta/health",
                "headers": [],
                "client": ("127.0.0.1", 8080)
            }
        )
        
        # Test rate limit check
        tier = rate_limit_middleware._get_rate_limit_tier(request)
        allowed = await rate_limit_middleware._check_rate_limit(request, tier)
        
        assert allowed is False
    
    @pytest.mark.asyncio
    async def test_authenticated_endpoint_higher_limit(self, rate_limit_middleware):
        """Test higher rate limits for authenticated endpoints"""
        # Mock Redis responses
        rate_limit_middleware.redis_client.get = AsyncMock(return_value="500")  # Under limit
        rate_limit_middleware.redis_client.incr = AsyncMock(return_value=501)
        rate_limit_middleware.redis_client.expire = AsyncMock(return_value=True)
        
        # Create mock request with user state
        request = Request(
            scope={
                "type": "http",
                "method": "GET",
                "path": "/api/v1/sessions",
                "headers": [],
                "client": ("127.0.0.1", 8080)
            }
        )
        request.state.user_id = "user-uuid-here"
        
        # Test rate limit check
        tier = rate_limit_middleware._get_rate_limit_tier(request)
        assert tier == "authenticated"
        
        # Test rate limit validation
        allowed = await rate_limit_middleware._check_rate_limit(request, tier)
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_bandwidth_rate_limiting(self, rate_limit_middleware):
        """Test bandwidth-based rate limiting for chunk uploads"""
        # Mock Redis responses
        rate_limit_middleware.redis_client.get = AsyncMock(return_value="5000000")  # 5MB used
        rate_limit_middleware.redis_client.incrby = AsyncMock(return_value=6000000)
        rate_limit_middleware.redis_client.expire = AsyncMock(return_value=True)
        
        # Create mock request for chunk upload
        request = Request(
            scope={
                "type": "http",
                "method": "POST",
                "path": "/api/v1/sessions/session-id/chunks",
                "headers": [("content-length", "1000000")],  # 1MB chunk
                "client": ("127.0.0.1", 8080)
            }
        )
        request.state.user_id = "user-uuid-here"
        
        # Test bandwidth rate limiting
        allowed = await rate_limit_middleware._check_bandwidth_limit(
            request, "user:user-uuid-here", rate_limit_middleware.rate_limits["chunk_upload"]
        )
        
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_bandwidth_limit_exceeded(self, rate_limit_middleware):
        """Test bandwidth limit exceeded scenario"""
        # Mock Redis responses - bandwidth limit exceeded
        rate_limit_middleware.redis_client.get = AsyncMock(return_value="9500000")  # 9.5MB used
        
        # Create mock request for large chunk upload
        request = Request(
            scope={
                "type": "http",
                "method": "POST",
                "path": "/api/v1/sessions/session-id/chunks",
                "headers": [("content-length", "2000000")],  # 2MB chunk
                "client": ("127.0.0.1", 8080)
            }
        )
        request.state.user_id = "user-uuid-here"
        
        # Test bandwidth rate limiting
        allowed = await rate_limit_middleware._check_bandwidth_limit(
            request, "user:user-uuid-here", rate_limit_middleware.rate_limits["chunk_upload"]
        )
        
        assert allowed is False
```

### Input Validation Tests

```python
# tests/test_input_validation.py
import pytest
from app.utils.validation import InputValidator, FieldValidator
from fastapi import HTTPException

class TestInputValidation:
    """Test cases for input validation and sanitization"""
    
    @pytest.fixture
    def input_validator(self):
        """Input validator instance"""
        return InputValidator()
    
    @pytest.mark.asyncio
    async def test_request_size_validation(self, input_validator):
        """Test request size validation"""
        from fastapi import Request
        
        # Test valid request size
        request = Request(
            scope={
                "type": "http",
                "method": "POST",
                "path": "/api/v1/sessions",
                "headers": [("content-length", "1000")],
                "client": ("127.0.0.1", 8080)
            }
        )
        
        result = await input_validator.validate_request(request)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_request_size_exceeded(self, input_validator):
        """Test request size exceeded validation"""
        from fastapi import Request
        
        # Test oversized request
        request = Request(
            scope={
                "type": "http",
                "method": "POST",
                "path": "/api/v1/sessions",
                "headers": [("content-length", "200000000")],  # 200MB
                "client": ("127.0.0.1", 8080)
            }
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await input_validator.validate_request(request)
        
        assert exc_info.value.status_code == 413
        assert "Request too large" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_malicious_content_detection(self, input_validator):
        """Test malicious content detection"""
        # Test SQL injection
        malicious_content = b"'; DROP TABLE users; --"
        result = await input_validator._detect_malicious_content(malicious_content)
        assert result is True
        
        # Test XSS attempt
        xss_content = b"<script>alert('xss')</script>"
        result = await input_validator._detect_malicious_content(xss_content)
        assert result is True
        
        # Test path traversal
        path_traversal_content = b"../../../etc/passwd"
        result = await input_validator._detect_malicious_content(path_traversal_content)
        assert result is True
        
        # Test clean content
        clean_content = b'{"username": "testuser", "email": "test@example.com"}'
        result = await input_validator._detect_malicious_content(clean_content)
        assert result is False
    
    def test_email_validation(self):
        """Test email validation"""
        # Valid emails
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org"
        ]
        
        for email in valid_emails:
            result = FieldValidator.validate_email(email)
            assert result == email.lower().strip()
        
        # Invalid emails
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "",
            None
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValueError):
                FieldValidator.validate_email(email)
    
    def test_username_validation(self):
        """Test username validation"""
        # Valid usernames
        valid_usernames = [
            "testuser",
            "user_123",
            "user-name",
            "User123"
        ]
        
        for username in valid_usernames:
            result = FieldValidator.validate_username(username)
            assert result == username.lower().strip()
        
        # Invalid usernames
        invalid_usernames = [
            "ab",  # Too short
            "a" * 51,  # Too long
            "user@name",  # Invalid character
            "user.name",  # Invalid character
            "",  # Empty
            None  # None
        ]
        
        for username in invalid_usernames:
            with pytest.raises(ValueError):
                FieldValidator.validate_username(username)
    
    def test_password_validation(self):
        """Test password validation"""
        # Valid passwords
        valid_passwords = [
            "Password123",
            "MySecurePass1",
            "ComplexP@ss1"
        ]
        
        for password in valid_passwords:
            result = FieldValidator.validate_password(password)
            assert result == password
        
        # Invalid passwords
        invalid_passwords = [
            "short",  # Too short
            "nouppercase123",  # No uppercase
            "NOLOWERCASE123",  # No lowercase
            "NoNumbers",  # No numbers
            "a" * 129,  # Too long
            "",  # Empty
            None  # None
        ]
        
        for password in invalid_passwords:
            with pytest.raises(ValueError):
                FieldValidator.validate_password(password)
    
    def test_uuid_validation(self):
        """Test UUID validation"""
        import uuid
        
        # Valid UUIDs
        valid_uuid = str(uuid.uuid4())
        result = FieldValidator.validate_uuid(valid_uuid)
        assert result == valid_uuid
        
        # Invalid UUIDs
        invalid_uuids = [
            "not-a-uuid",
            "12345",
            "550e8400-e29b-41d4-a716",  # Incomplete
            "",  # Empty
            None  # None
        ]
        
        for invalid_uuid in invalid_uuids:
            with pytest.raises(ValueError):
                FieldValidator.validate_uuid(invalid_uuid)
    
    def test_string_sanitization(self):
        """Test string sanitization"""
        # Test null byte removal
        text_with_nulls = "test\x00string"
        result = FieldValidator.sanitize_string(text_with_nulls)
        assert result == "teststring"
        
        # Test control character removal
        text_with_control = "test\tstring\nwith\rcarriage"
        result = FieldValidator.sanitize_string(text_with_control)
        assert result == "teststringwithcarriage"
        
        # Test length truncation
        long_text = "a" * 2000
        result = FieldValidator.sanitize_string(long_text, max_length=100)
        assert len(result) == 100
        assert result == "a" * 100
        
        # Test whitespace trimming
        text_with_whitespace = "  test string  "
        result = FieldValidator.sanitize_string(text_with_whitespace)
        assert result == "test string"
```

## Integration Testing

### API Endpoint Tests

```python
# tests/test_integration.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json

class TestAPIIntegration:
    """Integration tests for API endpoints"""
    
    @pytest.fixture
    def client(self, test_client):
        """Test client with mocked dependencies"""
        return test_client
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/api/v1/meta/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "service" in data
        assert data["service"] == "api-gateway"
    
    def test_service_info_endpoint(self, client):
        """Test service info endpoint"""
        response = client.get("/api/v1/meta/info")
        
        assert response.status_code == 200
        data = response.json()
        assert "service_name" in data
        assert "version" in data
        assert "features" in data
        assert data["service_name"] == "api-gateway"
    
    @patch('app.services.auth_service.AuthService.initiate_login')
    def test_login_endpoint_success(self, mock_login, client):
        """Test successful login endpoint"""
        mock_login.return_value = {
            "success": True,
            "message": "Magic link sent to your email"
        }
        
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Magic link sent to your email"
        mock_login.assert_called_once()
    
    @patch('app.services.auth_service.AuthService.initiate_login')
    def test_login_endpoint_invalid_email(self, mock_login, client):
        """Test login endpoint with invalid email"""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "invalid-email"}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "LUCID_ERR_1001"
    
    def test_protected_endpoint_without_auth(self, client):
        """Test protected endpoint without authentication"""
        response = client.get("/api/v1/users/me")
        
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "LUCID_ERR_2001"
    
    def test_protected_endpoint_with_invalid_token(self, client):
        """Test protected endpoint with invalid token"""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "LUCID_ERR_2001"
    
    @patch('app.services.auth_service.AuthService.verify_totp')
    def test_verify_endpoint_success(self, mock_verify, client, sample_jwt_token):
        """Test successful TOTP verification"""
        mock_verify.return_value = {
            "access_token": "access_token_here",
            "refresh_token": "refresh_token_here",
            "user": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "test@example.com",
                "username": "testuser",
                "role": "user"
            }
        }
        
        response = client.post(
            "/api/v1/auth/verify",
            json={"email": "test@example.com", "code": "123456"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["email"] == "test@example.com"
    
    @patch('app.services.user_service.UserService.get_current_user')
    def test_get_current_user_endpoint(self, mock_get_user, client, sample_jwt_token):
        """Test get current user endpoint"""
        mock_get_user.return_value = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "test@example.com",
            "username": "testuser",
            "role": "user",
            "created_at": "2025-01-10T19:08:00Z"
        }
        
        headers = {"Authorization": f"Bearer {sample_jwt_token}"}
        response = client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["username"] == "testuser"
    
    @patch('app.services.session_service.SessionService.create_session')
    def test_create_session_endpoint(self, mock_create_session, client, sample_jwt_token):
        """Test create session endpoint"""
        mock_create_session.return_value = {
            "session_id": "550e8400-e29b-41d4-a716-446655440001",
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Test Session",
            "status": "active",
            "created_at": "2025-01-10T19:08:00Z"
        }
        
        headers = {"Authorization": f"Bearer {sample_jwt_token}"}
        response = client.post(
            "/api/v1/sessions",
            json={"name": "Test Session"},
            headers=headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Session"
        assert data["status"] == "active"
    
    def test_rate_limit_enforcement(self, client):
        """Test rate limiting enforcement"""
        # Make multiple requests to trigger rate limiting
        for i in range(105):  # Exceed public endpoint limit
            response = client.get("/api/v1/meta/health")
            if response.status_code == 429:
                break
        
        assert response.status_code == 429
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "LUCID_ERR_3001"
        assert "Rate limit exceeded" in data["error"]["message"]
```

### Database Integration Tests

```python
# tests/test_database_integration.py
import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from app.database.connection import get_database
from app.database.repositories.user_repository import UserRepository

class TestDatabaseIntegration:
    """Integration tests for database operations"""
    
    @pytest.fixture
    async def test_db(self):
        """Test database connection"""
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client.lucid_gateway_test
        yield db
        # Cleanup
        await client.drop_database("lucid_gateway_test")
        client.close()
    
    @pytest.fixture
    def user_repository(self, test_db):
        """User repository with test database"""
        return UserRepository(test_db)
    
    @pytest.mark.asyncio
    async def test_user_creation(self, user_repository):
        """Test user creation in database"""
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "$2b$12$test_hash",
            "role": "user",
            "created_at": "2025-01-10T19:08:00Z"
        }
        
        # Create user
        result = await user_repository.create_user(user_data)
        
        assert result["user_id"] is not None
        assert result["email"] == "test@example.com"
        assert result["username"] == "testuser"
        
        # Verify user exists
        user = await user_repository.get_user_by_email("test@example.com")
        assert user is not None
        assert user["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_user_lookup_by_id(self, user_repository):
        """Test user lookup by ID"""
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "$2b$12$test_hash",
            "role": "user"
        }
        
        # Create user
        created_user = await user_repository.create_user(user_data)
        user_id = created_user["user_id"]
        
        # Lookup user by ID
        user = await user_repository.get_user_by_id(user_id)
        
        assert user is not None
        assert user["user_id"] == user_id
        assert user["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_user_update(self, user_repository):
        """Test user update operations"""
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "$2b$12$test_hash",
            "role": "user"
        }
        
        # Create user
        created_user = await user_repository.create_user(user_data)
        user_id = created_user["user_id"]
        
        # Update user
        update_data = {
            "username": "updateduser",
            "first_name": "Test",
            "last_name": "User"
        }
        
        result = await user_repository.update_user(user_id, update_data)
        
        assert result["username"] == "updateduser"
        assert result["first_name"] == "Test"
        assert result["last_name"] == "User"
        
        # Verify update
        user = await user_repository.get_user_by_id(user_id)
        assert user["username"] == "updateduser"
        assert user["first_name"] == "Test"
    
    @pytest.mark.asyncio
    async def test_duplicate_email_prevention(self, user_repository):
        """Test prevention of duplicate email addresses"""
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "$2b$12$test_hash",
            "role": "user"
        }
        
        # Create first user
        await user_repository.create_user(user_data)
        
        # Attempt to create second user with same email
        duplicate_user_data = {
            "email": "test@example.com",
            "username": "differentuser",
            "password_hash": "$2b$12$different_hash",
            "role": "user"
        }
        
        with pytest.raises(Exception):  # Should raise duplicate key error
            await user_repository.create_user(duplicate_user_data)
    
    @pytest.mark.asyncio
    async def test_user_deletion(self, user_repository):
        """Test user deletion"""
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "$2b$12$test_hash",
            "role": "user"
        }
        
        # Create user
        created_user = await user_repository.create_user(user_data)
        user_id = created_user["user_id"]
        
        # Delete user
        result = await user_repository.delete_user(user_id)
        assert result is True
        
        # Verify user is deleted
        user = await user_repository.get_user_by_id(user_id)
        assert user is None
```

## Performance Testing

### Load Testing Configuration

```python
# tests/test_performance.py
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
import requests

class TestPerformance:
    """Performance tests for API Gateway"""
    
    @pytest.fixture
    def base_url(self):
        """Base URL for API testing"""
        return "http://localhost:8080"
    
    def test_response_time_health_endpoint(self, base_url):
        """Test response time for health endpoint"""
        start_time = time.time()
        response = requests.get(f"{base_url}/api/v1/meta/health")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 0.1  # Should respond within 100ms
    
    def test_concurrent_requests(self, base_url):
        """Test concurrent request handling"""
        def make_request():
            response = requests.get(f"{base_url}/api/v1/meta/health")
            return response.status_code
        
        # Make 100 concurrent requests
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(make_request) for _ in range(100)]
            results = [future.result() for future in futures]
        
        # All requests should succeed
        assert all(status == 200 for status in results)
    
    def test_rate_limit_performance(self, base_url):
        """Test rate limiting performance impact"""
        def make_request():
            response = requests.get(f"{base_url}/api/v1/meta/health")
            return response.status_code, response.elapsed.total_seconds()
        
        # Make requests and measure performance
        start_time = time.time()
        results = []
        
        for i in range(50):
            status, elapsed = make_request()
            results.append((status, elapsed))
        
        total_time = time.time() - start_time
        avg_response_time = sum(elapsed for _, elapsed in results) / len(results)
        
        # Performance should not degrade significantly
        assert total_time < 10  # Total time under 10 seconds
        assert avg_response_time < 0.2  # Average response time under 200ms
        
        # Most requests should succeed (some may hit rate limit)
        success_count = sum(1 for status, _ in results if status == 200)
        assert success_count >= 40  # At least 80% should succeed
    
    def test_memory_usage_under_load(self, base_url):
        """Test memory usage under load"""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Generate load
        def make_request():
            response = requests.get(f"{base_url}/api/v1/meta/health")
            return response.status_code
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(200)]
            results = [future.result() for future in futures]
        
        # Check memory usage after load
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (under 100MB)
        assert memory_increase < 100 * 1024 * 1024
        
        # All requests should still succeed
        assert all(status == 200 for status in results)
```

### Benchmark Tests

```python
# tests/test_benchmarks.py
import pytest
import time
import statistics
from fastapi.testclient import TestClient

class TestBenchmarks:
    """Benchmark tests for API performance"""
    
    @pytest.fixture
    def client(self, test_client):
        """Test client for benchmarking"""
        return test_client
    
    def test_health_endpoint_benchmark(self, client):
        """Benchmark health endpoint performance"""
        response_times = []
        
        # Run 100 requests and measure response times
        for _ in range(100):
            start_time = time.time()
            response = client.get("/api/v1/meta/health")
            end_time = time.time()
            
            response_times.append(end_time - start_time)
            assert response.status_code == 200
        
        # Calculate statistics
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        p99_response_time = statistics.quantiles(response_times, n=100)[98]  # 99th percentile
        
        # Performance assertions
        assert avg_response_time < 0.05  # Average under 50ms
        assert p95_response_time < 0.1   # 95% under 100ms
        assert p99_response_time < 0.2   # 99% under 200ms
        
        print(f"Health endpoint benchmark:")
        print(f"  Average: {avg_response_time:.3f}s")
        print(f"  P95: {p95_response_time:.3f}s")
        print(f"  P99: {p99_response_time:.3f}s")
    
    def test_authentication_benchmark(self, client):
        """Benchmark authentication flow performance"""
        response_times = []
        
        # Mock authentication service
        with patch('app.services.auth_service.AuthService.initiate_login') as mock_login:
            mock_login.return_value = {"success": True, "message": "Magic link sent"}
            
            # Run 50 authentication requests
            for _ in range(50):
                start_time = time.time()
                response = client.post(
                    "/api/v1/auth/login",
                    json={"email": "test@example.com"}
                )
                end_time = time.time()
                
                response_times.append(end_time - start_time)
                assert response.status_code == 200
        
        # Calculate statistics
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]
        
        # Performance assertions
        assert avg_response_time < 0.1  # Average under 100ms
        assert p95_response_time < 0.2  # 95% under 200ms
        
        print(f"Authentication benchmark:")
        print(f"  Average: {avg_response_time:.3f}s")
        print(f"  P95: {p95_response_time:.3f}s")
    
    def test_rate_limiting_benchmark(self, client):
        """Benchmark rate limiting performance"""
        response_times = []
        success_count = 0
        
        # Run requests and measure rate limiting performance
        for i in range(150):  # Exceed rate limit
            start_time = time.time()
            response = client.get("/api/v1/meta/health")
            end_time = time.time()
            
            response_times.append(end_time - start_time)
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:
                # Rate limited - this is expected
                pass
        
        # Calculate statistics
        avg_response_time = statistics.mean(response_times)
        success_rate = success_count / 150
        
        # Performance assertions
        assert avg_response_time < 0.05  # Rate limiting should be fast
        assert success_rate > 0.6  # At least 60% should succeed before rate limiting
        
        print(f"Rate limiting benchmark:")
        print(f"  Average response time: {avg_response_time:.3f}s")
        print(f"  Success rate: {success_rate:.2%}")
```

## Test Execution

### Test Configuration

```python
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=app
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    benchmark: Benchmark tests
    slow: Slow running tests
```

### Test Execution Scripts

```bash
#!/bin/bash
# scripts/run_tests.sh

set -e

echo "Running Lucid API Gateway Tests..."

# Run unit tests
echo "Running unit tests..."
pytest tests/ -m unit -v

# Run integration tests
echo "Running integration tests..."
pytest tests/ -m integration -v

# Run performance tests
echo "Running performance tests..."
pytest tests/ -m performance -v --tb=short

# Run benchmark tests
echo "Running benchmark tests..."
pytest tests/ -m benchmark -v --tb=short

# Generate coverage report
echo "Generating coverage report..."
pytest --cov=app --cov-report=html --cov-report=term-missing

echo "All tests completed successfully!"
```

### Continuous Integration Configuration

```yaml
# .github/workflows/test.yml
name: API Gateway Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      mongodb:
        image: mongo:7.0
        ports:
          - 27017:27017
        env:
          MONGO_INITDB_ROOT_USERNAME: admin
          MONGO_INITDB_ROOT_PASSWORD: password
      
      redis:
        image: redis:7.2-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-asyncio
    
    - name: Run unit tests
      run: pytest tests/ -m unit -v
    
    - name: Run integration tests
      run: pytest tests/ -m integration -v
    
    - name: Run performance tests
      run: pytest tests/ -m performance -v --tb=short
    
    - name: Generate coverage report
      run: pytest --cov=app --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
