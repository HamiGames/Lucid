"""
LUCID TRON Wallet Manager Service - Main Entry Point
Standalone wallet manager container following Lucid architecture patterns
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Ensure site-packages is in Python path (per master-docker-design.md)
site_packages = '/usr/local/lib/python3.11/site-packages'
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)

# Add app directory to path
app_dir = '/app'
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

import sys
from pathlib import Path

# Add payment-systems directory to path
payment_systems_dir = Path(__file__).parent.parent
if str(payment_systems_dir) not in sys.path:
    sys.path.insert(0, str(payment_systems_dir))

from datetime import datetime, timezone
from tron.services.wallet_manager import WalletManagerService
from tron.repositories.wallet_repository import WalletRepository
from tron.services.wallet_backup import WalletBackupService
from tron.services.wallet_audit import WalletAuditService, AuditAction, AuditSeverity
from tron.services.wallet_transaction_history import WalletTransactionHistoryService
from tron.services.wallet_validator import WalletValidator
from tron.services.wallet_access_control import WalletAccessControlService
from tron.services.wallet_recovery import WalletRecoveryService
from tron.api.wallets import router as wallets_router

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
wallet_repository: Optional[WalletRepository] = None
wallet_manager_service: Optional[WalletManagerService] = None
backup_service: Optional[WalletBackupService] = None
audit_service: Optional[WalletAuditService] = None
transaction_history_service: Optional[WalletTransactionHistoryService] = None
validator_service: Optional[WalletValidator] = None
access_control_service: Optional[WalletAccessControlService] = None
recovery_service: Optional[WalletRecoveryService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global wallet_repository, wallet_manager_service, backup_service
    global audit_service, transaction_history_service, validator_service
    global access_control_service, recovery_service
    
    # Startup
    logger.info("Starting TRON Wallet Manager Service...")
    
    try:
        # Get configuration from environment
        mongo_url = os.getenv("MONGODB_URL") or os.getenv("MONGODB_URI")
        if not mongo_url:
            raise ValueError("MONGODB_URL or MONGODB_URI environment variable must be set")
        
        mongo_database = os.getenv("MONGODB_DATABASE", "lucid_payments")
        backup_directory = os.getenv("BACKUP_DIRECTORY", "/data/wallets/backups")
        encryption_key = os.getenv("WALLET_ENCRYPTION_KEY") or os.getenv("ENCRYPTION_KEY")
        
        # Initialize repository
        wallet_repository = WalletRepository(mongo_url, mongo_database)
        await wallet_repository.connect()
        
        # Initialize backup service
        backup_service = WalletBackupService(
            backup_directory=backup_directory,
            encryption_key=encryption_key,
            backup_interval=int(os.getenv("BACKUP_INTERVAL", "3600")),
            retention_days=int(os.getenv("RETENTION_DAYS", "30"))
        )
        await backup_service.initialize()
        
        # Initialize audit service
        audit_collection = wallet_repository.db["wallet_audit_logs"]
        audit_service = WalletAuditService(audit_collection)
        await audit_service.initialize()
        
        # Initialize transaction history service
        history_collection = wallet_repository.db["wallet_transaction_history"]
        transaction_history_service = WalletTransactionHistoryService(history_collection)
        await transaction_history_service.initialize()
        
        # Initialize validator service
        validator_service = WalletValidator()
        
        # Initialize access control service
        access_collection = wallet_repository.db["wallet_access_control"]
        access_control_service = WalletAccessControlService(access_collection)
        await access_control_service.initialize()
        
        # Initialize recovery service
        recovery_collection = wallet_repository.db["wallet_recovery"]
        recovery_service = WalletRecoveryService(recovery_collection, backup_service)
        await recovery_service.initialize()
        
        # Initialize wallet manager service
        wallet_manager_service = WalletManagerService()
        await wallet_manager_service.initialize()
        
        logger.info("TRON Wallet Manager Service started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start TRON Wallet Manager Service: {e}", exc_info=True)
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down TRON Wallet Manager Service...")
        
        try:
            if wallet_manager_service:
                await wallet_manager_service.stop()
            if backup_service:
                await backup_service.stop()
            if wallet_repository:
                await wallet_repository.disconnect()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)


# Create FastAPI application
app = FastAPI(
    title="TRON Wallet Manager Service",
    description="Wallet management service for TRON payments",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true",
    allow_methods=os.getenv("CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(","),
    allow_headers=os.getenv("CORS_HEADERS", "*").split(","),
)

# Include routers
app.include_router(wallets_router, prefix="/api/v1/tron", tags=["wallets"])


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        health_status = {
            "status": "healthy",
            "service": "tron-wallet-manager",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Check database connection
        if wallet_repository:
            try:
                await wallet_repository.db.command('ping')
                health_status["database"] = "connected"
            except Exception as e:
                health_status["database"] = f"error: {str(e)}"
                health_status["status"] = "unhealthy"
        else:
            health_status["database"] = "not_initialized"
            health_status["status"] = "unhealthy"
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        return health_status
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "tron-wallet-manager",
        "status": "running",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("SERVICE_PORT", "8093"))
    
    uvicorn.run(
        "wallet_manager_main:app",
        host=host,
        port=port,
        log_level=log_level.lower()
    )

