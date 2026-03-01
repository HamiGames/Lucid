# Cluster 09: Authentication - Detailed Build Guide

## Document Control

| Attribute | Value |
|-----------|-------|
| Cluster ID | 09-AUTHENTICATION |
| Build Phase | Phase 1 (Weeks 1-2) |
| Parallel Track | Track A |
| Version | 1.0.0 |

---

## Cluster Overview

### Service (Port 8089)
Authentication and authorization service

### Key Features
- TRON signature verification
- Hardware wallet integration (Ledger, Trezor, KeepKey)
- JWT token management
- Session handling
- RBAC (Role-Based Access Control)

### Dependencies
**None** - Foundation cluster (only needs Database from Track A)

---

## MVP Files (30 files, ~4,000 lines)

### Core Services (8 files, ~1,800 lines)
1. `auth/authentication_service.py` (400) - Main auth engine
2. `auth/user_manager.py` (300) - User lifecycle
3. `auth/hardware_wallet.py` (350) - HW wallet integration
4. `auth/session_manager.py` (320) - Session/JWT handling
5. `auth/permissions.py` (250) - RBAC engine
6. `auth/main.py` (180) - FastAPI entry point

### Middleware (3 files, ~400 lines)
7. `auth/middleware/auth_middleware.py` (150) - Auth middleware
8. `auth/middleware/rate_limit.py` (120) - Rate limiting
9. `auth/middleware/audit_log.py` (130) - Audit logging

### Data Models (4 files, ~550 lines)
10. `auth/models/user.py` (200) - User models
11. `auth/models/session.py` (150) - Session models
12. `auth/models/hardware_wallet.py` (120) - HW wallet models
13. `auth/models/permissions.py` (80) - Permission models

### Utilities (5 files, ~650 lines)
14. `auth/utils/crypto.py` (280) - Crypto utilities (TRON sig verification)
15. `auth/utils/validators.py` (180) - Input validation
16. `auth/utils/exceptions.py` (120) - Custom exceptions
17. `auth/utils/jwt_handler.py` (70) - JWT utilities

### Configuration (10 files, ~600 lines)
18-27. Dockerfile, docker-compose, requirements, env vars, configs

---

## Build Sequence (10 days)

### Days 1-2: Core Authentication
- Implement TRON signature verification
- Build user registration
- Create login/logout

### Days 3-4: Hardware Wallet Integration
- Integrate Ledger support
- Add Trezor support
- Implement KeepKey support

### Days 5-6: JWT & Session Management
- Implement JWT generation
- Build session management
- Add token refresh

### Days 7-8: RBAC & Permissions
- Build role system
- Implement permissions
- Add authorization checks

### Days 9-10: Testing & Containerization
- Integration testing
- Security testing
- Container deployment

---

## Key Implementations

### Authentication Service
```python
# auth/authentication_service.py (400 lines)
from eth_account.messages import encode_defunct
from web3 import Web3

class AuthenticationService:
    async def verify_tron_signature(
        self, 
        address: str, 
        message: str, 
        signature: str
    ) -> bool:
        # Verify TRON signature
        message_hash = encode_defunct(text=message)
        recovered_address = Web3().eth.account.recover_message(
            message_hash, 
            signature=signature
        )
        return recovered_address.lower() == address.lower()
        
    async def login(self, tron_address: str, signature: str):
        # Verify signature
        if not await self.verify_tron_signature(...):
            raise AuthenticationError("Invalid signature")
            
        # Get or create user
        user = await self.user_manager.get_or_create(tron_address)
        
        # Generate JWT tokens
        access_token = await self.generate_access_token(user)
        refresh_token = await self.generate_refresh_token(user)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user
        }
```

### Hardware Wallet Integration
```python
# auth/hardware_wallet.py (350 lines)
from ledgerblue.comm import getDongle
from trezorlib.client import TrezorClient

class HardwareWalletService:
    async def connect_ledger(self) -> bool:
        try:
            dongle = getDongle(True)
            return True
        except Exception:
            return False
            
    async def sign_with_ledger(self, message: str, path: str):
        dongle = getDongle(True)
        # Sign message with Ledger
        
    async def connect_trezor(self) -> bool:
        try:
            client = TrezorClient()
            return True
        except Exception:
            return False
            
    async def sign_with_trezor(self, message: str, address_n: list):
        client = TrezorClient()
        # Sign message with Trezor
```

### Session Manager
```python
# auth/session_manager.py (320 lines)
import jwt
from datetime import datetime, timedelta

class SessionManager:
    def generate_access_token(self, user_id: str) -> str:
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(minutes=15),
            "type": "access"
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
        
    def generate_refresh_token(self, user_id: str) -> str:
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(days=7),
            "type": "refresh"
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
        
    async def validate_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=["HS256"]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError()
        except jwt.InvalidTokenError:
            raise InvalidTokenError()
```

### RBAC Engine
```python
# auth/permissions.py (250 lines)
from enum import Enum

class Role(Enum):
    USER = "user"
    NODE_OPERATOR = "node_operator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class Permission(Enum):
    CREATE_SESSION = "create_session"
    MANAGE_NODES = "manage_nodes"
    VIEW_BLOCKCHAIN = "view_blockchain"
    MANAGE_USERS = "manage_users"
    MANAGE_PAYOUTS = "manage_payouts"
    EMERGENCY_CONTROLS = "emergency_controls"

class RBACManager:
    ROLE_PERMISSIONS = {
        Role.USER: [Permission.CREATE_SESSION],
        Role.NODE_OPERATOR: [
            Permission.CREATE_SESSION,
            Permission.MANAGE_NODES
        ],
        Role.ADMIN: [
            Permission.CREATE_SESSION,
            Permission.MANAGE_NODES,
            Permission.VIEW_BLOCKCHAIN,
            Permission.MANAGE_USERS
        ],
        Role.SUPER_ADMIN: list(Permission)  # All permissions
    }
    
    async def check_permission(
        self, 
        user_id: str, 
        permission: Permission
    ) -> bool:
        user = await self.user_manager.get_user(user_id)
        user_permissions = self.ROLE_PERMISSIONS.get(user.role, [])
        return permission in user_permissions
```

---

## API Endpoints

### Authentication Endpoints
- `POST /auth/register` - Register new user with TRON address
- `POST /auth/login` - Login with TRON signature
- `POST /auth/verify` - Verify JWT token
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - User logout

### Hardware Wallet Endpoints
- `POST /auth/hw/connect` - Connect hardware wallet
- `POST /auth/hw/sign` - Sign with hardware wallet
- `GET /auth/hw/status` - Get hardware wallet status

### Session Endpoints
- `GET /auth/sessions` - List user sessions
- `DELETE /auth/sessions/{session_id}` - Revoke session

---

## Environment Variables
```bash
# Service Configuration
AUTH_SERVICE_PORT=8089
JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
MONGODB_URI=mongodb://mongodb:27017/lucid_auth
REDIS_URI=redis://redis:6379/1

# Security
BCRYPT_ROUNDS=12
MAX_LOGIN_ATTEMPTS=5
LOGIN_COOLDOWN_MINUTES=15

# Hardware Wallet
ENABLE_HARDWARE_WALLET=true
LEDGER_SUPPORTED=true
TREZOR_SUPPORTED=true
KEEPKEY_SUPPORTED=true
```

---

## Docker Compose
```yaml
version: '3.8'
services:
  auth-service:
    build:
      context: .
      dockerfile: Dockerfile
    image: lucid-auth-service:latest
    container_name: lucid-auth-service
    ports:
      - "8089:8089"
    environment:
      - AUTH_SERVICE_PORT=8089
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - MONGODB_URI=mongodb://mongodb:27017/lucid_auth
      - REDIS_URI=redis://redis:6379/1
    depends_on:
      - mongodb
      - redis
    networks:
      - lucid-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8089/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## Testing Strategy

### Unit Tests
- TRON signature verification
- JWT generation and validation
- Hardware wallet integration
- RBAC permission checks

### Integration Tests
- Login → Token generation → API access
- Hardware wallet → Sign → Verify
- Token refresh flow
- Session revocation

### Security Tests
- Brute force protection
- Token expiration
- Invalid signature handling
- Permission escalation attempts

---

## Success Criteria

- [ ] TRON signature verification working
- [ ] Hardware wallet integration (Ledger, Trezor, KeepKey)
- [ ] JWT token generation and validation
- [ ] Session management operational
- [ ] RBAC permissions enforced
- [ ] Rate limiting active
- [ ] Audit logging working
- [ ] All security tests passing
- [ ] Container deployed

---

**Build Time**: 10 days (2 developers)  
**Critical Path**: YES - Required by all API-dependent clusters

