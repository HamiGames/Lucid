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
from contextlib import asynccontextmanager
import logging
from datetime import datetime
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient

# Import configuration and components from the auth package
try:
    from auth.config import settings
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import config: {e}")
    sys.exit(1)

from auth.middleware import AuthMiddleware, RateLimitMiddleware, AuditLogMiddleware
from auth.authentication_service import AuthenticationService
from auth.user_manager import UserManager
from auth.hardware_wallet import HardwareWalletManager
from auth.session_manager import SessionManager
from auth.permissions import RBACManager

# Configure logging with safe level validation
def get_safe_log_level(log_level_str: str) -> int:
    """Safely convert log level string to logging constant."""
    valid_levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    return valid_levels.get(log_level_str.upper(), logging.INFO)

logging.basicConfig(
    level=get_safe_log_level(settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize MongoDB client (will be connected in startup)
mongodb_client: AsyncIOMotorClient = None
mongodb_db = None

# Initialize services (will be fully initialized in startup)
user_manager: UserManager = None
hardware_wallet_service = HardwareWalletManager()
session_manager = SessionManager()
rbac_manager = RBACManager()
auth_service = AuthenticationService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown (distroless-compatible)"""
    global mongodb_client, mongodb_db, user_manager
    
    # Startup
    logger.info("Starting Lucid Authentication Service")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Port: {settings.AUTH_SERVICE_PORT}")
    
    # Initialize MongoDB connection
    try:
        mongodb_client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
            minPoolSize=settings.MONGODB_MIN_POOL_SIZE
        )
        mongodb_db = mongodb_client[settings.MONGODB_DATABASE]
        
        # Test connection
        await mongodb_client.admin.command('ping')
        logger.info("MongoDB connection established")
        
        # Initialize UserManager with database
        user_manager = UserManager(mongodb_db)
        logger.info("UserManager initialized")
        
        # Initialize RBACManager with UserManager
        rbac_manager.user_manager = user_manager
        logger.info("RBACManager initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB connection: {e}")
        raise
    
    # Initialize session manager
    await session_manager.initialize()
    logger.info("Session manager initialized")
    
    # Initialize hardware wallet support
    if settings.ENABLE_HARDWARE_WALLET:
        await hardware_wallet_service.initialize()
        logger.info("Hardware wallet support initialized")
    
    logger.info("All services initialized successfully")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Shutting down Lucid Authentication Service")
    
    # Close session manager
    await session_manager.close()
    
    # Close hardware wallet service
    await hardware_wallet_service.close()
    
    # Close MongoDB connection
    if mongodb_client:
        mongodb_client.close()
        logger.info("MongoDB connection closed")
    
    logger.info("Shutdown complete")


# Initialize FastAPI app with lifespan context manager (distroless-compatible)
app = FastAPI(
    title="Lucid Authentication Service",
    description="TRON-based authentication with hardware wallet support",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(AuditLogMiddleware)
app.add_middleware(RateLimitMiddleware)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Check database health
    db_healthy = False
    if mongodb_client:
        try:
            await mongodb_client.admin.command('ping')
            db_healthy = True
        except Exception:
            db_healthy = False
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "service": "auth-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "dependencies": {
            "database": db_healthy,
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


# Import and include routers from the auth package
from auth.api import auth_router, users_router, sessions_router, hardware_wallet_router, orchestration_router
from auth.api.endpoint_config import get_endpoint_config

# Get endpoint configuration
endpoint_config = get_endpoint_config()

# Include routers only if endpoints are enabled (customizable)
if endpoint_config.is_endpoint_enabled("auth"):
    app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
    logger.info("Authentication endpoints enabled")

if endpoint_config.is_endpoint_enabled("users"):
    app.include_router(users_router, prefix="/users", tags=["Users"])
    logger.info("User management endpoints enabled")

if endpoint_config.is_endpoint_enabled("sessions"):
    app.include_router(sessions_router, prefix="/sessions", tags=["Sessions"])
    logger.info("Session management endpoints enabled")

if endpoint_config.is_endpoint_enabled("hardware_wallet"):
    app.include_router(hardware_wallet_router, prefix="/hw", tags=["Hardware Wallet"])
    logger.info("Hardware wallet endpoints enabled")

# Include orchestration router if orchestration is enabled
if os.getenv("ENABLE_SERVICE_ORCHESTRATION", "false").lower() == "true":
    app.include_router(orchestration_router, prefix="/orchestrate", tags=["Service Orchestration"])
    logger.info("Service orchestration endpoints enabled")


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
        app,  # Use app object directly instead of "auth.main:app" (files are at /app/ root, not /app/auth/)
        host="0.0.0.0",
        port=settings.AUTH_SERVICE_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()

