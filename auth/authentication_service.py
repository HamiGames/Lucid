#!/usr/bin/env python3
"""
Lucid Authentication Service
Provides user authentication, hardware wallet integration, and session management
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn

from auth.user_manager import UserManager, UserRole, KYCStatus
from auth.hardware_wallet import HardwareWalletManager, WalletType

# Optional admin import - only if admin module is available
try:
    from admin.system.admin_controller import AdminController, AdminRole
except ImportError:
    AdminController = None
    AdminRole = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Pydantic models
class AuthenticationRequest(BaseModel):
    tron_address: str
    signature: str
    message: str
    public_key: str
    hardware_wallet_info: Optional[Dict[str, Any]] = None

class AuthenticationResponse(BaseModel):
    user_id: str
    session_token: str
    role: str
    kyc_status: str
    permissions: list

class HardwareWalletConnectRequest(BaseModel):
    wallet_type: str
    device_id: str
    derivation_path: str = "m/44'/195'/0'/0/0"

class HardwareWalletResponse(BaseModel):
    connected: bool
    address: Optional[str] = None
    device_info: Optional[Dict[str, Any]] = None

class AuthenticationService:
    """Main authentication service class"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Lucid Authentication Service",
            description="User authentication and hardware wallet management",
            version="0.1.0"
        )
        self.db_client: Optional[AsyncIOMotorClient] = None
        self.user_manager: Optional[UserManager] = None
        self.hardware_wallet_manager: Optional[HardwareWalletManager] = None
        self.admin_controller: Optional[AdminController] = None
        
    async def initialize(self):
        """Initialize the authentication service"""
        try:
            # Initialize database connection
            mongo_uri = os.getenv("MONGO_URI", "mongodb://lucid:lucid@mongo-distroless:27019/lucid?authSource=admin")
            self.db_client = AsyncIOMotorClient(mongo_uri)
            db = self.db_client.lucid
            
            # Initialize managers
            self.user_manager = UserManager(db)
            self.hardware_wallet_manager = HardwareWalletManager()
            if AdminController is not None:
                self.admin_controller = AdminController()
            else:
                self.admin_controller = None
                logger.warning("AdminController not available - admin features disabled")
            
            # Setup routes
            self._setup_routes()
            
            logger.info("Authentication service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize authentication service: {e}")
            raise
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "service": "authentication-service",
                "version": "0.1.0"
            }
        
        @self.app.post("/auth/authenticate", response_model=AuthenticationResponse)
        async def authenticate_user(request: AuthenticationRequest):
            """Authenticate user with TRON signature"""
            try:
                if not self.user_manager:
                    raise HTTPException(status_code=500, detail="User manager not initialized")
                
                # Authenticate user
                user = await self.user_manager.authenticate_user(
                    tron_address=request.tron_address,
                    signature=request.signature,
                    message=request.message,
                    public_key=request.public_key,
                    hardware_wallet_info=request.hardware_wallet_info
                )
                
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication failed"
                    )
                
                # Generate session token (simplified)
                session_token = f"session_{user.user_id}_{asyncio.get_event_loop().time()}"
                
                return AuthenticationResponse(
                    user_id=user.user_id,
                    session_token=session_token,
                    role=user.role.value,
                    kyc_status=user.kyc_status.value,
                    permissions=[p.value for p in user.permissions]
                )
                
            except Exception as e:
                logger.error(f"Authentication error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/auth/hardware-wallet/connect", response_model=HardwareWalletResponse)
        async def connect_hardware_wallet(request: HardwareWalletConnectRequest):
            """Connect to hardware wallet"""
            try:
                if not self.hardware_wallet_manager:
                    raise HTTPException(status_code=500, detail="Hardware wallet manager not initialized")
                
                wallet_type = WalletType(request.wallet_type)
                connected = await self.hardware_wallet_manager.connect_wallet(
                    request.device_id, wallet_type
                )
                
                if connected:
                    address = await self.hardware_wallet_manager.get_tron_address(
                        request.device_id, request.derivation_path
                    )
                    
                    return HardwareWalletResponse(
                        connected=True,
                        address=address,
                        device_info={"type": request.wallet_type, "device_id": request.device_id}
                    )
                else:
                    return HardwareWalletResponse(connected=False)
                    
            except Exception as e:
                logger.error(f"Hardware wallet connection error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/auth/hardware-wallet/discover")
        async def discover_hardware_wallets():
            """Discover available hardware wallets"""
            try:
                if not self.hardware_wallet_manager:
                    raise HTTPException(status_code=500, detail="Hardware wallet manager not initialized")
                
                wallets = await self.hardware_wallet_manager.discover_wallets()
                return {"wallets": [wallet.__dict__ for wallet in wallets]}
                
            except Exception as e:
                logger.error(f"Hardware wallet discovery error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/auth/user/{user_id}")
        async def get_user_info(user_id: str):
            """Get user information"""
            try:
                if not self.user_manager:
                    raise HTTPException(status_code=500, detail="User manager not initialized")
                
                user = await self.user_manager.get_user_by_id(user_id)
                if not user:
                    raise HTTPException(status_code=404, detail="User not found")
                
                return {
                    "user_id": user.user_id,
                    "tron_address": user.tron_address,
                    "role": user.role.value,
                    "kyc_status": user.kyc_status.value,
                    "created_at": user.created_at,
                    "last_login": user.last_login
                }
                
            except Exception as e:
                logger.error(f"Get user info error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def shutdown(self):
        """Shutdown the authentication service"""
        if self.db_client:
            self.db_client.close()
        logger.info("Authentication service shutdown complete")

# Global service instance
auth_service = AuthenticationService()

# Export the FastAPI app
app = auth_service.app

@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    await auth_service.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    await auth_service.shutdown()

def main():
    """Main entry point"""
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8085"))
    
    uvicorn.run(
        "auth.authentication_service:app",
        host=host,
        port=port,
        log_level="info",
        reload=False
    )

if __name__ == "__main__":
    main()
