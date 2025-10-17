# Step 10 Quick Reference Guide
## API Gateway Services Layer

**Quick Access**: Essential information for using Step 10 components

---

## Service Usage Examples

### 1. Authentication Service

```python
from services.auth_service import auth_service

# Initialize
await auth_service.initialize()

# Login
token_response = await auth_service.login(
    tron_address="TXYZabc123...",
    signature="0x12345...",
    message="Sign this message"
)

# Verify token
payload = await auth_service.verify_token(token_response.access_token)

# Refresh token
new_tokens = await auth_service.refresh_token(token_response.refresh_token)

# Logout
await auth_service.logout(user_id="user_123")
```

### 2. User Service

```python
from services.user_service import user_service

# Get user
user = await user_service.get_user("user_123")

# Get by TRON address
user = await user_service.get_user_by_tron_address("TXYZabc123...")

# Create user
from models.user import UserCreate
new_user = await user_service.create_user(
    UserCreate(
        user_id="user_456",
        email="user@example.com",
        tron_address="TXYZabc123..."
    )
)

# List users
users = await user_service.list_users(skip=0, limit=100)
```

### 3. Session Service

```python
from services.session_service import session_service

# Create session
from models.session import SessionCreate
session = await session_service.create_session(
    user_id="user_123",
    session_create=SessionCreate(
        session_id="sess_789",
        session_type="rdp"
    )
)

# Update status
from models.session import SessionStatus
await session_service.update_session_status(
    "sess_789",
    SessionStatus.ACTIVE
)

# List user sessions
sessions = await session_service.list_user_sessions("user_123")
```

### 4. Rate Limiting Service

```python
from services.rate_limit_service import rate_limit_service, RateLimitTier

# Initialize
await rate_limit_service.initialize()

# Check rate limit
allowed, remaining, reset_time = await rate_limit_service.check_rate_limit(
    identifier="user_123",
    tier=RateLimitTier.AUTHENTICATED
)

if not allowed:
    raise RateLimitExceeded("Rate limit exceeded")

# Get rate limit info
info = await rate_limit_service.get_rate_limit_info(
    identifier="user_123",
    tier=RateLimitTier.AUTHENTICATED
)
# Returns: {"limit": 1000, "remaining": 950, "reset": 1234567890, "tier": "authenticated"}
```

### 5. Proxy Service

```python
from services.proxy_service import proxy_service

# Initialize
await proxy_service.initialize()

# Proxy request to blockchain
response = await proxy_service.proxy_request(
    service="blockchain",
    endpoint="/api/v1/chain/info",
    method="GET"
)

# Proxy request to session management
response = await proxy_service.proxy_request(
    service="session",
    endpoint="/sessions/create",
    method="POST",
    data={"user_id": "user_123"}
)

# Get circuit breaker status
status = await proxy_service.get_circuit_breaker_status()
# Returns: {"blockchain": {"state": "closed", "failure_count": 0, ...}, ...}
```

---

## Middleware Integration

### Rate Limiting Middleware

```python
from fastapi import Request, HTTPException
from services.rate_limit_service import rate_limit_service, RateLimitTier

async def rate_limit_middleware(request: Request, call_next):
    # Get identifier (IP or user_id)
    identifier = request.client.host
    if hasattr(request.state, "user"):
        identifier = request.state.user.user_id
        tier = RateLimitTier.AUTHENTICATED
    else:
        tier = RateLimitTier.PUBLIC
    
    # Check rate limit
    allowed, remaining, reset_time = await rate_limit_service.check_rate_limit(
        identifier, tier
    )
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(rate_limit_service.RATE_LIMITS[tier]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_time)
            }
        )
    
    # Add rate limit headers
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(rate_limit_service.RATE_LIMITS[tier])
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_time)
    
    return response
```

---

## Utilities Usage

### Security Utilities

```python
from utils.security import (
    hash_password,
    verify_password,
    generate_api_key,
    verify_signature
)

# Hash password
hashed, salt = hash_password("my_password")

# Verify password
is_valid = verify_password("my_password", hashed, salt)

# Generate API key
api_key = generate_api_key()

# Verify TRON signature
is_valid = verify_signature(
    message="Sign this message",
    signature="0x12345...",
    address="TXYZabc123..."
)
```

### Validation Utilities

```python
from utils.validation import (
    validate_email,
    validate_tron_address,
    validate_session_id,
    sanitize_string
)

# Validate email
if not validate_email("user@example.com"):
    raise ValueError("Invalid email")

# Validate TRON address
if not validate_tron_address("TXYZabc123..."):
    raise ValueError("Invalid TRON address")

# Validate session ID
if not validate_session_id("sess_123"):
    raise ValueError("Invalid session ID")

# Sanitize input
clean_text = sanitize_string(user_input, max_length=1000)
```

---

## Database Operations

### Using Repositories

```python
from database.connection import get_database
from repositories.user_repository import UserRepository

# Get database
db = await get_database()

# Create repository
user_repo = UserRepository(db)

# Find user
user_data = await user_repo.find_by_id("user_123")

# Create user
new_user = await user_repo.create({
    "user_id": "user_456",
    "email": "user@example.com",
    "tron_address": "TXYZabc123..."
})

# Update user
await user_repo.update("user_123", {"email": "newemail@example.com"})

# List users
users = await user_repo.list_users(skip=0, limit=100)
```

---

## Error Handling

### Service Errors

```python
from services.auth_service import AuthenticationError, TokenExpiredError, InvalidTokenError
from services.proxy_service import ServiceUnavailableError
from services.rate_limit_service import RateLimitExceeded

try:
    token = await auth_service.verify_token(token_string)
except TokenExpiredError:
    # Token expired, need to refresh
    new_token = await auth_service.refresh_token(refresh_token)
except InvalidTokenError:
    # Invalid token, need to login again
    raise HTTPException(status_code=401, detail="Invalid token")
except AuthenticationError as e:
    # Authentication service unavailable
    raise HTTPException(status_code=503, detail=str(e))

try:
    response = await proxy_service.proxy_request("blockchain", "/api/v1/chain/info")
except ServiceUnavailableError as e:
    # Backend service unavailable (circuit breaker open)
    raise HTTPException(status_code=503, detail=str(e))

try:
    allowed, _, _ = await rate_limit_service.check_rate_limit(identifier, tier)
except RateLimitExceeded:
    raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

---

## Configuration

### Required Environment Variables

```bash
# Authentication
AUTH_SERVICE_URL=http://auth-service:8089
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
TOKEN_EXPIRE_MINUTES=15

# Database
MONGODB_URI=mongodb://mongodb:27017/lucid
REDIS_URI=redis://redis:6379/0

# Backend Services
BLOCKCHAIN_SERVICE_URL=http://blockchain-core:8084
SESSION_SERVICE_URL=http://session-api:8087
NODE_SERVICE_URL=http://node-management:8095

# Rate Limiting
RATE_LIMIT_PUBLIC=100
RATE_LIMIT_AUTHENTICATED=1000
RATE_LIMIT_ADMIN=10000
```

---

## Rate Limiting Tiers

| Tier | Limit | Use Case |
|------|-------|----------|
| PUBLIC | 100 req/min | Unauthenticated requests |
| AUTHENTICATED | 1000 req/min | Authenticated users |
| ADMIN | 10000 req/min | Admin users |

---

## Circuit Breaker States

| State | Behavior | Transition |
|-------|----------|------------|
| CLOSED | Normal operation | After 5 failures → OPEN |
| OPEN | Fail fast | After 30 seconds → HALF_OPEN |
| HALF_OPEN | Testing recovery | After 2 successes → CLOSED |

---

## API Response Formats

### Success Response
```json
{
    "data": { ... },
    "status": "success"
}
```

### Error Response
```json
{
    "error": {
        "code": "LUCID_ERR_XXXX",
        "message": "Human-readable error message",
        "details": { ... }
    }
}
```

### Rate Limit Headers
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1634567890
```

---

## Common Patterns

### Authenticated Request Pattern

```python
from fastapi import Depends, HTTPException
from services.auth_service import auth_service

async def get_current_user(token: str):
    try:
        payload = await auth_service.verify_token(token)
        return payload
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Token expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/protected")
async def protected_endpoint(user = Depends(get_current_user)):
    return {"message": f"Hello {user.user_id}"}
```

### Proxied Request Pattern

```python
from services.proxy_service import proxy_service, ServiceUnavailableError

@app.get("/blockchain/info")
async def get_blockchain_info():
    try:
        response = await proxy_service.proxy_request(
            service="blockchain",
            endpoint="/api/v1/chain/info",
            method="GET"
        )
        return response
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
```

---

## Testing

### Unit Test Example

```python
import pytest
from services.rate_limit_service import RateLimitService, RateLimitTier

@pytest.mark.asyncio
async def test_rate_limit_enforcement():
    service = RateLimitService()
    await service.initialize()
    
    # Make requests up to limit
    for i in range(100):
        allowed, remaining, _ = await service.check_rate_limit(
            "test_user",
            RateLimitTier.PUBLIC
        )
        assert allowed
        assert remaining == 99 - i
    
    # Next request should be denied
    allowed, remaining, _ = await service.check_rate_limit(
        "test_user",
        RateLimitTier.PUBLIC
    )
    assert not allowed
    assert remaining == 0
    
    await service.close()
```

---

## Troubleshooting

### Common Issues

**Rate Limit Always Returns Zero**
- Check Redis connection: `redis-cli ping`
- Verify REDIS_URI in environment

**Circuit Breaker Always Open**
- Check backend service health
- Review service URLs in configuration
- Check circuit breaker status: `await proxy_service.get_circuit_breaker_status()`

**Authentication Fails**
- Verify AUTH_SERVICE_URL is correct
- Check JWT_SECRET_KEY matches auth service
- Test auth service health: `curl http://auth-service:8089/health`

**Database Connection Fails**
- Verify MongoDB is running: `docker ps | grep mongo`
- Check MONGODB_URI format
- Test connection: `mongosh $MONGODB_URI`

---

## Performance Tips

1. **Connection Pooling**: Services use connection pooling by default
2. **Rate Limit Caching**: Rate limit checks are fast (Redis)
3. **Circuit Breaker**: Fails fast when service is down
4. **Async Operations**: All services use async/await
5. **Batch Operations**: Use repositories for bulk operations

---

## Security Best Practices

1. **Never log JWT tokens**: Use `logger.debug` for sensitive data
2. **Validate all inputs**: Use validation utilities
3. **Use constant-time comparison**: For secrets and tokens
4. **Implement rate limiting**: On all public endpoints
5. **Use circuit breakers**: For all external service calls

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-10-14  
**Related**: STEP_10_COMPLETION_SUMMARY.md

