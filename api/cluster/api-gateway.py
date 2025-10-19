#!/usr/bin/env python3
"""
LUCID API Gateway - SPEC-1B Implementation
Central API gateway for routing and load balancing
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
import redis
from pymongo import MongoClient
import jwt
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIGateway:
    """Main API Gateway for Lucid RDP services"""
    
    def __init__(self):
        self.app = FastAPI(
            title="LUCID API Gateway",
            description="Central API gateway for Lucid RDP services",
            version="1.0.0"
        )
        
        # Initialize connections
        self.redis_client = None
        self.mongo_client = None
        self.service_registry = {}
        
        # Load configuration
        self.load_config()
        
        # Setup middleware
        self.setup_middleware()
        
        # Setup routes
        self.setup_routes()
        
        # Initialize connections
        asyncio.create_task(self.initialize_connections())
    
    def load_config(self):
        """Load configuration from environment variables"""
        self.config = {
            'redis_url': os.getenv('REDIS_URL', 'redis://localhost:6379'),
            'mongo_url': os.getenv('MONGO_URL', 'mongodb://localhost:27017'),
            'jwt_secret': os.getenv('JWT_SECRET', 'lucid_jwt_secret_key'),
            'service_timeout': int(os.getenv('SERVICE_TIMEOUT', '30')),
            'max_retries': int(os.getenv('MAX_RETRIES', '3')),
            'trusted_hosts': os.getenv('TRUSTED_HOSTS', 'localhost,127.0.0.1').split(',')
        }
    
    def setup_middleware(self):
        """Setup middleware for the API gateway"""
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Trusted host middleware
        self.app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=self.config['trusted_hosts']
        )
    
    def setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "services": self.service_registry
            }
        
        @self.app.post("/api/v1/auth/login")
        async def login(request: Request):
            """Authentication endpoint"""
            try:
                data = await request.json()
                # Validate credentials
                user = await self.authenticate_user(data.get('username'), data.get('password'))
                
                if not user:
                    raise HTTPException(status_code=401, detail="Invalid credentials")
                
                # Generate JWT token
                token = self.generate_jwt_token(user)
                
                return {
                    "access_token": token,
                    "token_type": "bearer",
                    "expires_in": 3600,
                    "user": user
                }
            except Exception as e:
                logger.error(f"Login error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.get("/api/v1/sessions")
        async def get_sessions(request: Request, current_user: dict = Depends(self.get_current_user)):
            """Get user sessions"""
            try:
                # Route to session service
                sessions = await self.route_to_service('session-service', '/sessions', request)
                return sessions
            except Exception as e:
                logger.error(f"Sessions error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.post("/api/v1/sessions")
        async def create_session(request: Request, current_user: dict = Depends(self.get_current_user)):
            """Create new session"""
            try:
                # Route to session service
                session = await self.route_to_service('session-service', '/sessions', request, method='POST')
                return session
            except Exception as e:
                logger.error(f"Create session error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.get("/api/v1/blockchain/status")
        async def get_blockchain_status(request: Request, current_user: dict = Depends(self.get_current_user)):
            """Get blockchain status"""
            try:
                # Route to blockchain service
                status = await self.route_to_service('blockchain-service', '/status', request)
                return status
            except Exception as e:
                logger.error(f"Blockchain status error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.post("/api/v1/payments/withdraw")
        async def withdraw_payment(request: Request, current_user: dict = Depends(self.get_current_user)):
            """Withdraw payment"""
            try:
                # Route to payment service
                result = await self.route_to_service('payment-service', '/withdraw', request, method='POST')
                return result
            except Exception as e:
                logger.error(f"Payment withdrawal error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
    
    async def initialize_connections(self):
        """Initialize database connections"""
        try:
            # Redis connection
            self.redis_client = redis.from_url(self.config['redis_url'])
            await self.redis_client.ping()
            logger.info("Redis connection established")
            
            # MongoDB connection
            self.mongo_client = MongoClient(self.config['mongo_url'])
            self.mongo_client.admin.command('ping')
            logger.info("MongoDB connection established")
            
        except Exception as e:
            logger.error(f"Connection initialization error: {e}")
    
    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user credentials"""
        try:
            # Query user from MongoDB
            db = self.mongo_client.lucid_rdp
            user = db.users.find_one({"username": username})
            
            if user and self.verify_password(password, user.get('password_hash')):
                return {
                    "id": str(user['_id']),
                    "username": user['username'],
                    "role": user.get('role', 'user'),
                    "permissions": user.get('permissions', [])
                }
            return None
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password hash"""
        # Implement password verification logic
        # This should use proper hashing like bcrypt
        return password == password_hash  # Simplified for demo
    
    def generate_jwt_token(self, user: Dict[str, Any]) -> str:
        """Generate JWT token for user"""
        payload = {
            "user_id": user['id'],
            "username": user['username'],
            "role": user['role'],
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        return jwt.encode(payload, self.config['jwt_secret'], algorithm="HS256")
    
    async def get_current_user(self, request: Request) -> Dict[str, Any]:
        """Get current authenticated user"""
        try:
            token = request.headers.get("Authorization", "").replace("Bearer ", "")
            
            if not token:
                raise HTTPException(status_code=401, detail="Missing authentication token")
            
            # Verify JWT token
            payload = jwt.decode(token, self.config['jwt_secret'], algorithms=["HS256"])
            
            return {
                "id": payload['user_id'],
                "username": payload['username'],
                "role": payload['role']
            }
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    async def route_to_service(self, service_name: str, endpoint: str, request: Request, method: str = 'GET') -> Dict[str, Any]:
        """Route request to appropriate service"""
        try:
            # Get service URL from registry
            service_url = self.service_registry.get(service_name)
            
            if not service_url:
                # Try to discover service
                service_url = await self.discover_service(service_name)
            
            if not service_url:
                raise HTTPException(status_code=503, detail=f"Service {service_name} not available")
            
            # Make request to service
            import httpx
            async with httpx.AsyncClient() as client:
                if method == 'GET':
                    response = await client.get(f"{service_url}{endpoint}")
                elif method == 'POST':
                    data = await request.json()
                    response = await client.post(f"{service_url}{endpoint}", json=data)
                else:
                    raise HTTPException(status_code=405, detail="Method not allowed")
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Service routing error: {e}")
            raise HTTPException(status_code=500, detail="Service unavailable")
    
    async def discover_service(self, service_name: str) -> Optional[str]:
        """Discover service URL"""
        try:
            # Check Redis for service registry
            service_info = await self.redis_client.get(f"service:{service_name}")
            
            if service_info:
                import json
                info = json.loads(service_info)
                self.service_registry[service_name] = info['url']
                return info['url']
            
            return None
        except Exception as e:
            logger.error(f"Service discovery error: {e}")
            return None
    
    def register_service(self, service_name: str, service_url: str):
        """Register service in registry"""
        self.service_registry[service_name] = service_url
        
        # Store in Redis for persistence
        service_info = {
            "name": service_name,
            "url": service_url,
            "registered_at": datetime.utcnow().isoformat()
        }
        
        if self.redis_client:
            self.redis_client.set(f"service:{service_name}", str(service_info))

# Initialize API Gateway
gateway = APIGateway()

if __name__ == "__main__":
    uvicorn.run(
        "api-gateway:gateway.app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
