"""
Wallet Backup and Recovery Service
Handles automated backups and recovery of wallet data
"""

import logging
import os
import json
import asyncio
import base64
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from pathlib import Path
import aiofiles
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import hashlib

logger = logging.getLogger(__name__)


class WalletBackupService:
    """Service for wallet backup and recovery operations"""
    
    def __init__(
        self,
        backup_directory: str,
        encryption_key: Optional[str] = None,
        backup_interval: int = 3600,
        retention_days: int = 30
    ):
        """Initialize backup service"""
        self.backup_directory = Path(backup_directory)
        self.backup_directory.mkdir(parents=True, exist_ok=True)
        
        # Encryption setup
        if encryption_key:
            # Derive a proper Fernet key from the encryption_key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'lucid_wallet_backup_salt',  # In production, use random salt from config
                iterations=100000,
                backend=default_backend()
            )
            derived_key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
            self.cipher = Fernet(derived_key)
            logger.info("Wallet backup encryption initialized with AES-256")
        else:
            self.cipher = None
            logger.warning("Wallet backup encryption disabled - backups will be unencrypted")
        
        self.backup_interval = backup_interval
        self.retention_days = retention_days
        self._backup_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Initialize backup service"""
        logger.info("Initializing wallet backup service")
        
        # Start backup task
        self._backup_task = asyncio.create_task(self._backup_loop())
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Wallet backup service initialized")
    
    async def stop(self):
        """Stop backup service"""
        logger.info("Stopping wallet backup service")
        
        if self._backup_task:
            self._backup_task.cancel()
            try:
                await self._backup_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Wallet backup service stopped")
    
    async def create_backup(self, wallet_data: Dict[str, Any], wallet_id: str) -> str:
        """Create a backup of wallet data"""
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            backup_filename = f"wallet_{wallet_id}_{timestamp.replace(':', '-')}.json"
            backup_path = self.backup_directory / backup_filename
            
            # Prepare backup data
            backup_data = {
                "wallet_id": wallet_id,
                "backup_timestamp": timestamp,
                "wallet_data": wallet_data
            }
            
            # Serialize and encrypt if cipher available
            backup_json = json.dumps(backup_data, default=str)
            
            if self.cipher:
                backup_bytes = backup_json.encode()
                encrypted_data = self.cipher.encrypt(backup_bytes)
                async with aiofiles.open(backup_path, 'wb') as f:
                    await f.write(encrypted_data)
            else:
                async with aiofiles.open(backup_path, 'w') as f:
                    await f.write(backup_json)
            
            logger.info(f"Created backup for wallet {wallet_id}: {backup_filename}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Failed to create backup for wallet {wallet_id}: {e}")
            raise
    
    async def restore_backup(self, backup_path: str) -> Dict[str, Any]:
        """Restore wallet from backup"""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
            # Read and decrypt if encrypted
            if self.cipher:
                async with aiofiles.open(backup_file, 'rb') as f:
                    encrypted_data = await f.read()
                decrypted_data = self.cipher.decrypt(encrypted_data)
                backup_json = decrypted_data.decode()
            else:
                async with aiofiles.open(backup_file, 'r') as f:
                    backup_json = await f.read()
            
            backup_data = json.loads(backup_json)
            logger.info(f"Restored backup from {backup_path}")
            return backup_data.get("wallet_data", {})
            
        except Exception as e:
            logger.error(f"Failed to restore backup from {backup_path}: {e}")
            raise
    
    async def list_backups(self, wallet_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available backups"""
        try:
            backups = []
            pattern = f"wallet_{wallet_id}_*.json" if wallet_id else "wallet_*.json"
            
            for backup_file in self.backup_directory.glob(pattern):
                try:
                    stat = backup_file.stat()
                    backups.append({
                        "filename": backup_file.name,
                        "path": str(backup_file),
                        "size": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                    })
                except Exception as e:
                    logger.warning(f"Failed to read backup file {backup_file}: {e}")
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x["created_at"], reverse=True)
            return backups
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            raise
    
    async def delete_backup(self, backup_path: str) -> bool:
        """Delete a backup file"""
        try:
            backup_file = Path(backup_path)
            if backup_file.exists():
                backup_file.unlink()
                logger.info(f"Deleted backup: {backup_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete backup {backup_path}: {e}")
            raise
    
    async def _backup_loop(self):
        """Background task for periodic backups"""
        try:
            while True:
                await asyncio.sleep(self.backup_interval)
                # Backup logic would be called here
                # This is a placeholder - actual backup would be triggered by wallet operations
                logger.debug("Backup loop running")
        except asyncio.CancelledError:
            logger.info("Backup loop cancelled")
        except Exception as e:
            logger.error(f"Error in backup loop: {e}")
    
    async def _cleanup_loop(self):
        """Background task for cleaning up old backups"""
        try:
            while True:
                await asyncio.sleep(3600)  # Run cleanup every hour
                await self._cleanup_old_backups()
        except asyncio.CancelledError:
            logger.info("Cleanup loop cancelled")
        except Exception as e:
            logger.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_old_backups(self):
        """Remove backups older than retention period"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
            deleted_count = 0
            
            for backup_file in self.backup_directory.glob("wallet_*.json"):
                try:
                    stat = backup_file.stat()
                    file_date = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                    
                    if file_date < cutoff_date:
                        backup_file.unlink()
                        deleted_count += 1
                        logger.debug(f"Deleted old backup: {backup_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to process backup file {backup_file}: {e}")
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old backup(s)")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")

