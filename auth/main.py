"""
Lucid Authentication Service - Main Entry Point
Cluster 09: Authentication Service
Port: 8089

This service handles:
- TRON signature verification
- Hardware wallet integration (Ledger, Trezor, KeepKey)
- JWT token management (15min access, 7day refresh)
- RBAC engine (4 roles)
"""

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime

from config import settings
from middleware import AuthMiddleware, RateLimitMiddleware, AuditLogMiddleware
from authentication_service import AuthenticationService
from user_manager import UserManager
from hardware_wallet import HardwareWalletService
from session_manager import SessionManager
from permissions import RBACManager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Lucid Authentication Service",
    description="TRON-based authentication with hardware wallet support",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
user_manager = UserManager()
hardware_wallet_service = HardwareWalletService()
session_manager = SessionManager()
rbac_manager = RBACManager()
auth_service = AuthenticationService(
    user_manager=user_manager,
    hardware_wallet_service=hardware_wallet_service,
    session_manager=session_manager,
    rbac_manager=rbac_manager
)

# Add custom middleware
app.add_middleware(AuditLogMiddleware)
app.add_middleware(RateLimitMiddleware)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Lucid Authentication Service")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Port: {settings.AUTH_SERVICE_PORT}")
    
    # Initialize database connections
    await user_manager.initialize()
    logger.info("Database connections initialized")
    
    # Initialize hardware wallet support
    if settings.ENABLE_HARDWARE_WALLET:
        await hardware_wallet_service.initialize()
        logger.info("Hardware wallet support initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Lucid Authentication Service")
    await user_manager.close()
    await hardware_wallet_service.close()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "auth-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "dependencies": {
            "database": await user_manager.health_check(),
            "redis": await session_manager.health_check(),
            "hardware_wallet": hardware_wallet_service.is_available() if settings.ENABLE_HARDWARE_WALLET else "disabled"
        }
    }


@app.get("/meta/info")
async def service_info():
    """Service information endpoint"""
    return {
        "service_name": "lucid-auth-service",
        "cluster": "09-authentication",
        "version": "1.0.0",
        "port": settings.AUTH_SERVICE_PORT,
        "features": {
            "tron_signature_verification": True,
            "hardware_wallet_support": settings.ENABLE_HARDWARE_WALLET,
            "jwt_token_management": True,
            "rbac_engine": True,
            "supported_hardware_wallets": [
                "Ledger" if settings.LEDGER_SUPPORTED else None,
                "Trezor" if settings.TREZOR_SUPPORTED else None,
                "KeepKey" if settings.KEEPKEY_SUPPORTED else None
            ]
        },
        "token_expiry": {
            "access_token_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_days": settings.REFRESH_TOKEN_EXPIRE_DAYS
        },
        "rbac_roles": ["USER", "NODE_OPERATOR", "ADMIN", "SUPER_ADMIN"]
    }


# Import and include routers
from api import auth_router, users_router, sessions_router, hardware_wallet_router

app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(users_router, prefix="/users", tags=["Users"])
app.include_router(sessions_router, prefix="/sessions", tags=["Sessions"])
app.include_router(hardware_wallet_router, prefix="/hw", tags=["Hardware Wallet"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "LUCID_ERR_5000",
                "message": "Internal server error",
                "service": "auth-service",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


def main():
    """Run the application"""
    uvicorn.run(
        "auth.main:app",
        host="0.0.0.0",
        port=settings.AUTH_SERVICE_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()

