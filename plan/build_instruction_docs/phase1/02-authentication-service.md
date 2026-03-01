# Authentication Service Container

## Overview
Build authentication service container with TRON signature verification and hardware wallet support for Phase 1 foundation services.

## Location
`auth/Dockerfile`

## Container Details
**Container**: `pickme/lucid-auth-service:latest-arm64`

## Multi-Stage Build Strategy

### Stage 1: Builder
```dockerfile
FROM python:3.11-slim as builder
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY auth/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target /build/deps

# Clean up unnecessary files
RUN find /build/deps -name "*.pyc" -delete && \
    find /build/deps -name "__pycache__" -type d -exec rm -rf {} + && \
    find /build/deps -name "*.dist-info" -type d -exec rm -rf {} +
```

### Stage 2: Runtime (Distroless)
```dockerfile
FROM gcr.io/distroless/python3-debian12:arm64

# Copy dependencies
COPY --from=builder /build/deps /app/deps

# Copy application code
COPY auth/ /app/

# Set environment variables
ENV PYTHONPATH=/app/deps
WORKDIR /app

# Set non-root user
USER 65532:65532

# Expose port
EXPOSE 8089

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["python", "-c", "import requests; requests.get('http://localhost:8089/health')"]

# Default command
CMD ["python", "main.py"]
```

## Requirements File
**File**: `auth/requirements.txt`

```txt
# Authentication Service Dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
httpx==0.25.2
aiofiles==23.2.1
python-multipart==0.0.6

# Authentication & Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
cryptography==41.0.8
bcrypt==4.1.2

# Database Connections
pymongo==4.6.0
redis==5.0.1
elasticsearch==8.11.0

# TRON Integration
tronweb==0.1.0
tronpy==0.4.0

# Hardware Wallet Support
ledgercomm==1.0.0
trezor==0.13.8
keepkey==6.3.1

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-mock==3.12.0
```

## Application Code Structure

### Main Application
**File**: `auth/main.py`

```python
"""
Lucid Authentication Service
Provides authentication, authorization, and hardware wallet integration
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn

from auth.authentication_service import AuthenticationService
from auth.hardware_wallet import HardwareWalletManager
from auth.api.auth_routes import auth_router
from auth.api.user_routes import user_router
from auth.api.hardware_wallet_routes import hardware_wallet_router
from auth.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global services
auth_service = None
hardware_wallet_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global auth_service, hardware_wallet_manager
    
    # Startup
    logger.info("Starting Lucid Authentication Service...")
    
    settings = get_settings()
    
    # Initialize authentication service
    auth_service = AuthenticationService(settings)
    await auth_service.initialize()
    
    # Initialize hardware wallet manager
    hardware_wallet_manager = HardwareWalletManager(settings)
    await hardware_wallet_manager.initialize()
    
    logger.info("Authentication Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Authentication Service...")
    if auth_service:
        await auth_service.cleanup()
    if hardware_wallet_manager:
        await hardware_wallet_manager.cleanup()
    logger.info("Authentication Service shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="Lucid Authentication Service",
    description="Authentication, authorization, and hardware wallet integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["authentication"])
app.include_router(user_router, prefix="/users", tags=["users"])
app.include_router(hardware_wallet_router, prefix="/hardware-wallet", tags=["hardware-wallet"])

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "lucid-auth-service",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Lucid Authentication Service",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8089,
        reload=False,
        log_level="info"
    )
```

### Authentication Service
**File**: `auth/authentication_service.py`

```python
"""
Core authentication service implementation
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import pymongo
import redis
from elasticsearch import Elasticsearch

from auth.config import get_settings

logger = logging.getLogger(__name__)

class AuthenticationService:
    """Core authentication service"""
    
    def __init__(self, settings):
        self.settings = settings
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.mongo_client = None
        self.redis_client = None
        self.elasticsearch_client = None
        
    async def initialize(self):
        """Initialize database connections"""
        try:
            # MongoDB connection
            self.mongo_client = pymongo.MongoClient(self.settings.mongodb_uri)
            await self.mongo_client.admin.command('ping')
            logger.info("MongoDB connection established")
            
            # Redis connection
            self.redis_client = redis.from_url(self.settings.redis_url)
            await self.redis_client.ping()
            logger.info("Redis connection established")
            
            # Elasticsearch connection
            self.elasticsearch_client = Elasticsearch([self.settings.elasticsearch_url])
            await self.elasticsearch_client.ping()
            logger.info("Elasticsearch connection established")
            
        except Exception as e:
            logger.error(f"Failed to initialize authentication service: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup database connections"""
        if self.mongo_client:
            self.mongo_client.close()
        if self.redis_client:
            self.redis_client.close()
        if self.elasticsearch_client:
            self.elasticsearch_client.close()
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash password"""
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.settings.jwt_secret_key, algorithm="HS256")
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.settings.jwt_secret_key, algorithms=["HS256"])
            return payload
        except JWTError:
            return None
    
    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with username and password"""
        try:
            # Get user from MongoDB
            db = self.mongo_client.lucid
            user = db.users.find_one({"username": username})
            
            if not user:
                return None
            
            # Verify password
            if not self.verify_password(password, user["hashed_password"]):
                return None
            
            # Update last login
            db.users.update_one(
                {"username": username},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            
            return {
                "username": user["username"],
                "email": user["email"],
                "role": user["role"],
                "created_at": user["created_at"]
            }
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    async def create_user(self, username: str, email: str, password: str, role: str = "user") -> bool:
        """Create new user"""
        try:
            # Check if user exists
            db = self.mongo_client.lucid
            if db.users.find_one({"username": username}):
                return False
            
            # Create user
            user_data = {
                "username": username,
                "email": email,
                "hashed_password": self.get_password_hash(password),
                "role": role,
                "created_at": datetime.utcnow(),
                "last_login": None
            }
            
            db.users.insert_one(user_data)
            logger.info(f"User created: {username}")
            return True
            
        except Exception as e:
            logger.error(f"User creation error: {e}")
            return False
```

### Hardware Wallet Manager
**File**: `auth/hardware_wallet.py`

```python
"""
Hardware wallet integration for TRON signatures
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from ledgercomm import getDongle
from trezorlib import btc, messages
from keepkeylib import client

logger = logging.getLogger(__name__)

class HardwareWalletManager:
    """Hardware wallet manager for TRON signatures"""
    
    def __init__(self, settings):
        self.settings = settings
        self.ledger_dongle = None
        self.trezor_client = None
        self.keepkey_client = None
        
    async def initialize(self):
        """Initialize hardware wallet connections"""
        try:
            # Initialize Ledger
            self.ledger_dongle = getDongle()
            logger.info("Ledger hardware wallet initialized")
            
            # Initialize Trezor
            self.trezor_client = btc.BitcoinClient()
            logger.info("Trezor hardware wallet initialized")
            
            # Initialize KeepKey
            self.keepkey_client = client.KeepKeyClient()
            logger.info("KeepKey hardware wallet initialized")
            
        except Exception as e:
            logger.warning(f"Hardware wallet initialization failed: {e}")
    
    async def cleanup(self):
        """Cleanup hardware wallet connections"""
        if self.ledger_dongle:
            self.ledger_dongle.close()
        if self.trezor_client:
            self.trezor_client.close()
        if self.keepkey_client:
            self.keepkey_client.close()
    
    async def sign_tron_transaction(self, transaction_data: Dict[str, Any], wallet_type: str) -> Optional[str]:
        """Sign TRON transaction with hardware wallet"""
        try:
            if wallet_type == "ledger":
                return await self._sign_with_ledger(transaction_data)
            elif wallet_type == "trezor":
                return await self._sign_with_trezor(transaction_data)
            elif wallet_type == "keepkey":
                return await self._sign_with_keepkey(transaction_data)
            else:
                raise ValueError(f"Unsupported wallet type: {wallet_type}")
                
        except Exception as e:
            logger.error(f"Hardware wallet signing error: {e}")
            return None
    
    async def _sign_with_ledger(self, transaction_data: Dict[str, Any]) -> str:
        """Sign transaction with Ledger"""
        # Ledger TRON signing implementation
        pass
    
    async def _sign_with_trezor(self, transaction_data: Dict[str, Any]) -> str:
        """Sign transaction with Trezor"""
        # Trezor TRON signing implementation
        pass
    
    async def _sign_with_keepkey(self, transaction_data: Dict[str, Any]) -> str:
        """Sign transaction with KeepKey"""
        # KeepKey TRON signing implementation
        pass
```

## Build Command

```bash
# Build authentication service container
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-auth-service:latest-arm64 \
  -f auth/Dockerfile \
  --push \
  .
```

## Build Script Implementation

**File**: `scripts/foundation/build-auth-service.sh`

```bash
#!/bin/bash
# scripts/foundation/build-auth-service.sh
# Build authentication service container

set -e

echo "Building authentication service container..."

# Create auth directory if it doesn't exist
mkdir -p auth

# Create requirements.txt
cat > auth/requirements.txt << 'EOF'
# Authentication Service Dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
httpx==0.25.2
aiofiles==23.2.1
python-multipart==0.0.6

# Authentication & Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
cryptography==41.0.8
bcrypt==4.1.2

# Database Connections
pymongo==4.6.0
redis==5.0.1
elasticsearch==8.11.0

# TRON Integration
tronweb==0.1.0
tronpy==0.4.0

# Hardware Wallet Support
ledgercomm==1.0.0
trezor==0.13.8
keepkey==6.3.1

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-mock==3.12.0
EOF

# Create Dockerfile
cat > auth/Dockerfile << 'EOF'
# Multi-stage build for authentication service
FROM python:3.11-slim as builder
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY auth/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target /build/deps

# Clean up unnecessary files
RUN find /build/deps -name "*.pyc" -delete && \
    find /build/deps -name "__pycache__" -type d -exec rm -rf {} + && \
    find /build/deps -name "*.dist-info" -type d -exec rm -rf {} +

# Final distroless stage
FROM gcr.io/distroless/python3-debian12:arm64

# Copy dependencies
COPY --from=builder /build/deps /app/deps

# Copy application code
COPY auth/ /app/

# Set environment variables
ENV PYTHONPATH=/app/deps
WORKDIR /app

# Set non-root user
USER 65532:65532

# Expose port
EXPOSE 8089

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["python", "-c", "import requests; requests.get('http://localhost:8089/health')"]

# Default command
CMD ["python", "main.py"]
EOF

# Build authentication service container
echo "Building authentication service container..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-auth-service:latest-arm64 \
  -f auth/Dockerfile \
  --push \
  .

echo "Authentication service container built and pushed successfully!"
echo "Container: pickme/lucid-auth-service:latest-arm64"
```

## Validation Criteria
- Container runs on Pi successfully
- Health endpoint responds correctly
- JWT token generation works
- Database connections established
- Hardware wallet integration functional
- TRON signature verification working

## Environment Configuration
Uses `.env.foundation` for:
- Database connection strings
- JWT secret key
- Encryption keys
- Service port configuration

## Security Features
- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: bcrypt password hashing
- **Hardware Wallet Integration**: Ledger, Trezor, KeepKey support
- **TRON Signature Verification**: Hardware wallet TRON transaction signing
- **Non-root User**: Container runs as non-root user
- **Distroless Runtime**: Minimal attack surface

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `POST /auth/refresh` - Refresh token
- `POST /auth/register` - User registration

### Hardware Wallet
- `POST /hardware-wallet/connect` - Connect hardware wallet
- `POST /hardware-wallet/sign` - Sign transaction
- `GET /hardware-wallet/status` - Wallet status

### User Management
- `GET /users/profile` - Get user profile
- `PUT /users/profile` - Update user profile
- `POST /users/change-password` - Change password

## Troubleshooting

### Build Failures
```bash
# Check build logs
docker buildx build --progress=plain \
  --platform linux/arm64 \
  -t pickme/lucid-auth-service:latest-arm64 \
  -f auth/Dockerfile \
  .
```

### Runtime Issues
```bash
# Check container logs
docker logs lucid-auth-service

# Test health endpoint
curl http://localhost:8089/health
```

### Database Connection Issues
- Verify MongoDB, Redis, and Elasticsearch are running
- Check connection strings in environment configuration
- Ensure network connectivity between services

## Next Steps
After successful authentication service build, proceed to Phase 1 Docker Compose generation.
