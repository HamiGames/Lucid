"""
LUCID Payment Systems - TRON Wallet Backup API
Backup and recovery operations for wallets
Distroless container: lucid-tron-wallet-manager:latest
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..services.wallet_manager import wallet_manager_service
from ..services.wallet_backup import WalletBackupService

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/tron/backup", tags=["TRON Wallet Backup"])

# Request/Response Models
class BackupCreateRequest(BaseModel):
    """Backup creation request"""
    wallet_id: str = Field(..., description="Wallet ID to backup")

class BackupRestoreRequest(BaseModel):
    """Backup restore request"""
    wallet_id: str = Field(..., description="Wallet ID to restore")
    backup_id: str = Field(..., description="Backup ID to restore from")
    password: Optional[str] = Field(None, description="Wallet password (if required)")

class BackupResponse(BaseModel):
    """Backup response model"""
    backup_id: str = Field(..., description="Backup ID")
    wallet_id: str = Field(..., description="Wallet ID")
    backup_file: str = Field(..., description="Backup file path")
    created_at: str = Field(..., description="Backup creation timestamp")

class BackupListResponse(BaseModel):
    """Backup list response"""
    wallet_id: str = Field(..., description="Wallet ID")
    backups: List[BackupResponse] = Field(..., description="List of backups")
    total_count: int = Field(..., description="Total backup count")
    timestamp: str = Field(..., description="Response timestamp")

class BackupStatusResponse(BaseModel):
    """Backup status response"""
    backup_id: str = Field(..., description="Backup ID")
    wallet_id: str = Field(..., description="Wallet ID")
    status: str = Field(..., description="Backup status")
    file_exists: bool = Field(..., description="Whether backup file exists")
    file_size: Optional[int] = Field(None, description="Backup file size in bytes")
    created_at: Optional[str] = Field(None, description="Backup creation timestamp")
    timestamp: str = Field(..., description="Response timestamp")

@router.post("/", response_model=BackupResponse)
async def create_backup(request: BackupCreateRequest):
    """Create backup of wallet"""
    try:
        # Verify wallet exists
        wallet_response = await wallet_manager_service.get_wallet(request.wallet_id)
        if not wallet_response:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        # Create backup using service
        backup_result = await wallet_manager_service.create_backup(request.wallet_id)
        
        logger.info(f"Created backup for wallet {request.wallet_id}: {backup_result['backup_id']}")
        
        return BackupResponse(
            backup_id=backup_result["backup_id"],
            wallet_id=backup_result["wallet_id"],
            backup_file=backup_result["backup_file"],
            created_at=backup_result["created_at"]
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating backup for wallet {request.wallet_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create backup: {str(e)}")

@router.get("/{wallet_id}", response_model=BackupListResponse)
async def list_backups(wallet_id: str):
    """List backups for wallet"""
    try:
        # Verify wallet exists
        wallet_response = await wallet_manager_service.get_wallet(wallet_id)
        if not wallet_response:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        # Get recovery info which includes backups
        recovery_info = await wallet_manager_service.get_recovery_info(wallet_id)
        
        # Convert to BackupResponse format
        backups = []
        for backup_data in recovery_info.get("backups", []):
            backups.append(BackupResponse(
                backup_id=backup_data["backup_id"],
                wallet_id=wallet_id,
                backup_file=backup_data["file"],
                created_at=backup_data.get("created_at", datetime.now().isoformat())
            ))
        
        return BackupListResponse(
            wallet_id=wallet_id,
            backups=backups,
            total_count=len(backups),
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing backups for wallet {wallet_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")

@router.post("/restore", response_model=Dict[str, Any])
async def restore_backup(request: BackupRestoreRequest):
    """Restore wallet from backup"""
    try:
        # Verify wallet exists (or will be created)
        wallet_response = await wallet_manager_service.get_wallet(request.wallet_id)
        
        # Restore from backup using service
        restored_wallet = await wallet_manager_service.restore_backup(
            wallet_id=request.wallet_id,
            backup_id=request.backup_id,
            password=request.password
        )
        
        logger.info(f"Restored wallet {request.wallet_id} from backup {request.backup_id}")
        
        return {
            "message": "Wallet restored successfully",
            "wallet_id": restored_wallet.wallet_id,
            "backup_id": request.backup_id,
            "restored_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error restoring wallet {request.wallet_id} from backup {request.backup_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to restore backup: {str(e)}")

@router.delete("/{backup_id}")
async def delete_backup(backup_id: str):
    """Delete backup"""
    try:
        from pathlib import Path
        import os
        
        # Find backup file (backup_id format: wallet_id_YYYYMMDD_HHMMSS)
        # We need to search for the backup file
        # For now, we'll use the data directory structure
        data_dir = Path(os.getenv("DATA_DIRECTORY", "/data/payment-systems"))
        backup_dir = data_dir / "wallet-manager" / "backups"
        
        backup_file = backup_dir / f"{backup_id}.json"
        
        if not backup_file.exists():
            raise HTTPException(status_code=404, detail="Backup not found")
        
        # Delete backup file
        backup_file.unlink()
        
        logger.info(f"Deleted backup {backup_id}")
        
        return {
            "message": "Backup deleted successfully",
            "backup_id": backup_id,
            "deleted_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting backup {backup_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete backup: {str(e)}")

@router.get("/{backup_id}/status", response_model=BackupStatusResponse)
async def get_backup_status(backup_id: str):
    """Get backup status"""
    try:
        from pathlib import Path
        import os
        import json
        import aiofiles
        
        # Find backup file
        data_dir = Path(os.getenv("DATA_DIRECTORY", "/data/payment-systems"))
        backup_dir = data_dir / "wallet-manager" / "backups"
        backup_file = backup_dir / f"{backup_id}.json"
        
        file_exists = backup_file.exists()
        file_size = None
        created_at = None
        wallet_id = None
        
        if file_exists:
            file_size = backup_file.stat().st_size
            try:
                async with aiofiles.open(backup_file, "r") as f:
                    backup_data = json.loads(await f.read())
                    created_at = backup_data.get("backup_created_at")
                    wallet_id = backup_data.get("wallet_id")
            except Exception:
                pass
        
        return BackupStatusResponse(
            backup_id=backup_id,
            wallet_id=wallet_id or "unknown",
            status="available" if file_exists else "not_found",
            file_exists=file_exists,
            file_size=file_size,
            created_at=created_at,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error getting backup status for {backup_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get backup status: {str(e)}")
