# Authentication Cluster Implementation Guide

## Code Structure

### Directory Layout
```
auth/
├── authentication_service.py    # Main authentication service
├── user_manager.py             # User lifecycle management
├── hardware_wallet.py          # Hardware wallet integration
├── session_manager.py          # JWT token and session handling
├── permissions.py              # Role-based access control
├── middleware/
│   ├── auth_middleware.py      # Authentication middleware
│   ├── rate_limit.py           # Rate limiting middleware
│   └── audit_log.py            # Audit logging middleware
├── models/
│   ├── user.py                 # User data models
│   ├── session.py              # Session data models
│   └── hardware_wallet.py      # Hardware wallet models
├── utils/
│   ├── crypto.py               # Cryptographic utilities
│   ├── validators.py           # Input validation
│   └── exceptions.py           # Custom exceptions
└── tests/
    ├── test_auth.py            # Authentication tests
    ├── test_user_manager.py    # User management tests
    └── test_hardware_wallet.py # Hardware wallet tests
```

## Core Implementation

### Authentication Service
```python
# auth/authentication_service.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import jwt
import hashlib

class AuthenticationService:
    def __init__(self, secret_key: str, token_expire_minutes: int):
        self.secret_key = secret_key
        self.token_expire_minutes = token_expire_minutes
        
    async def authenticate_user(self, tron_address: str, signature: str, message: str) -> dict:
        # Verify TRON signature
        if not self.verify_tron_signature(message, signature, tron_address):
            raise HTTPException(status_code=401, detail="Invalid TRON signature")
            
        # Get or create user
        user = await self.user_manager.get_or_create_user(tron_address)
        
        # Generate tokens
        tokens = self.generate_token_pair(user)
        
        # Create session
        await self.session_manager.create_session(user['id'], tokens)
        
        return {
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'expires_in': self.token_expire_minutes * 60,
            'user': user
        }
        
    def verify_tron_signature(self, message: str, signature: str, address: str) -> bool:
        # Implementation of TRON signature verification
        pass
        
    def generate_token_pair(self, user: dict) -> dict:
        payload = {
            'user_id': user['id'],
            'tron_address': user['tron_address'],
            'role': user['role'],
            'exp': datetime.utcnow() + timedelta(minutes=self.token_expire_minutes)
        }
        
        access_token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        
        refresh_payload = {
            'user_id': user['id'],
            'type': 'refresh',
            'exp': datetime.utcnow() + timedelta(days=7)
        }
        
        refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm='HS256')
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token
        }
```

### Hardware Wallet Integration
```python
# auth/hardware_wallet.py
from typing import Optional, Dict, Any
import hid
import json

class HardwareWalletManager:
    def __init__(self):
        self.ledger_vendor_id = 0x2c97
        self.trezor_vendor_id = 0x534c
        self.keepkey_vendor_id = 0x2b24
        
    async def verify_hardware_wallet(self, wallet_type: str, device_id: str, 
                                   challenge: str, signature: str) -> bool:
        device = await self.connect_device(wallet_type, device_id)
        
        if not device:
            return False
            
        # Verify challenge signature
        return await device.verify_signature(challenge, signature)
        
    async def connect_device(self, wallet_type: str, device_id: str) -> Optional[Any]:
        devices = self.list_connected_devices()
        
        for device in devices:
            if device['type'] == wallet_type and device['id'] == device_id:
                return self.initialize_device(device)
                
        return None
        
    def list_connected_devices(self) -> list:
        devices = []
        
        # Scan for Ledger devices
        for device in hid.enumerate(self.ledger_vendor_id):
            devices.append({
                'type': 'ledger',
                'id': device['serial_number'],
                'path': device['path']
            })
            
        # Scan for Trezor devices
        for device in hid.enumerate(self.trezor_vendor_id):
            devices.append({
                'type': 'trezor',
                'id': device['serial_number'],
                'path': device['path']
            })
            
        return devices
```

### Session Manager
```python
# auth/session_manager.py
from datetime import datetime, timedelta
from typing import Optional, List
import redis
import uuid

class SessionManager:
    def __init__(self, redis_client: redis.Redis, db_client):
        self.redis = redis_client
        self.db = db_client
        
    async def create_session(self, user_id: str, tokens: dict) -> str:
        session_id = str(uuid.uuid4())
        
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'access_token_hash': self.hash_token(tokens['access_token']),
            'refresh_token_hash': self.hash_token(tokens['refresh_token']),
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(days=7),
            'last_activity': datetime.utcnow(),
            'revoked': False
        }
        
        # Store in MongoDB
        await self.db.sessions.insert_one(session_data)
        
        # Cache in Redis
        await self.redis.setex(
            f"session:{session_id}",
            timedelta(days=7),
            json.dumps(session_data)
        )
        
        return session_id
        
    async def validate_token(self, token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            # Check if token is blacklisted
            if await self.redis.get(f"blacklist:{self.hash_token(token)}"):
                return None
                
            return payload
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
            
    def hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
```

## Naming Conventions

### Service Naming
- **Container Name**: `lucid-auth-service`
- **Service Name**: `lucid-auth`
- **Image Name**: `pickme/lucid:auth-service`
- **Network Name**: `lucid-auth-net`

### Environment Variables
- `LUCID_AUTH_SECRET_KEY` - JWT signing key
- `LUCID_AUTH_TOKEN_EXPIRE_MINUTES` - Token expiration time
- `LUCID_AUTH_HARDWARE_WALLET_ENABLED` - Enable hardware wallet support
- `LUCID_AUTH_RATE_LIMIT_PER_MINUTE` - Rate limiting configuration
- `LUCID_AUTH_MONGODB_URL` - MongoDB connection string
- `LUCID_AUTH_REDIS_URL` - Redis connection string

## Distroless Container

### Dockerfile
```dockerfile
# Multi-stage build for distroless container
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM gcr.io/distroless/python3-debian11
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app
COPY auth/ ./auth/

EXPOSE 8090
CMD ["python", "-m", "auth.authentication_service"]
```

### Requirements
```txt
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
PyJWT==2.8.0
pymongo==4.6.0
redis==5.0.1
hidapi==0.14.0
cryptography==41.0.8
```

## Integration Patterns

### Beta Sidecar Integration
```yaml
# Docker Compose configuration
services:
  auth-service:
    image: pickme/lucid:auth-service
    container_name: lucid-auth-service
    environment:
      - LUCID_AUTH_SECRET_KEY=${AUTH_SECRET_KEY}
      - LUCID_AUTH_MONGODB_URL=mongodb://lucid_mongo:27017/lucid
    networks:
      - lucid-auth-net
    depends_on:
      - lucid_mongo
      - lucid_redis
      
  auth-sidecar:
    image: pickme/lucid:beta-sidecar
    container_name: lucid-auth-sidecar
    environment:
      - SIDECAR_SERVICE=auth
      - SIDECAR_PLANE=wallet
    networks:
      - lucid-auth-net
    depends_on:
      - auth-service
```

### Service Discovery
```python
# Service registration with Beta sidecar
async def register_auth_service():
    service_config = {
        'name': 'lucid-auth',
        'version': '1.0.0',
        'endpoints': [
            'https://auth.lucid.onion:8090',
            'https://auth-backup.lucid.onion:8090'
        ],
        'health_check': '/health',
        'plane': 'wallet'
    }
    
    await beta_sidecar.register_service(service_config)
```
