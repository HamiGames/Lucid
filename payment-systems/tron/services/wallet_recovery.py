"""
Wallet Recovery Service
Handles wallet recovery mechanisms including seed phrase and backup recovery
"""

import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorCollection
from tronpy.keys import PrivateKey


logger = logging.getLogger(__name__)


class WalletRecoveryService:
    """Service for wallet recovery operations"""
    
    def __init__(
        self,
        recovery_collection: AsyncIOMotorCollection,
        backup_service: Optional[Any] = None
    ):
        """Initialize recovery service"""
        self.recovery_collection = recovery_collection
        self.backup_service = backup_service
        self._initialized = False
    
    async def initialize(self):
        """Initialize service and create indexes"""
        try:
            # Create indexes
            await self.recovery_collection.create_index("wallet_id")
            await self.recovery_collection.create_index("recovery_code")
            await self.recovery_collection.create_index("status")
            await self.recovery_collection.create_index("created_at")
            await self.recovery_collection.create_index([("wallet_id", 1), ("status", 1)])
            
            self._initialized = True
            logger.info("Wallet recovery service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize recovery service: {e}")
            raise
    
    async def create_recovery_code(
        self,
        wallet_id: str,
        user_id: str,
        recovery_method: str = "backup"
    ) -> Dict[str, Any]:
        """Create a recovery code for wallet"""
        try:
            import secrets
            recovery_code = secrets.token_urlsafe(32)
            
            recovery_record = {
                "wallet_id": wallet_id,
                "user_id": user_id,
                "recovery_code": recovery_code,
                "recovery_method": recovery_method,
                "status": "pending",
                "created_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)  # Expires at end of day
            }
            
            await self.recovery_collection.insert_one(recovery_record)
            
            logger.info(f"Created recovery code for wallet {wallet_id}")
            
            return {
                "recovery_code": recovery_code,
                "expires_at": recovery_record["expires_at"].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create recovery code: {e}")
            raise
    
    async def recover_wallet_from_backup(
        self,
        wallet_id: str,
        backup_path: str,
        recovery_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Recover wallet from backup file"""
        try:
            # Verify recovery code if provided
            if recovery_code:
                recovery_record = await self.recovery_collection.find_one({
                    "wallet_id": wallet_id,
                    "recovery_code": recovery_code,
                    "status": "pending"
                })
                
                if not recovery_record:
                    raise ValueError("Invalid or expired recovery code")
                
                # Check expiration
                expires_at = recovery_record.get("expires_at")
                if expires_at and expires_at < datetime.now(timezone.utc):
                    raise ValueError("Recovery code has expired")
            
            # Restore from backup
            if not self.backup_service:
                raise RuntimeError("Backup service not available")
            
            wallet_data = await self.backup_service.restore_backup(backup_path)
            
            # Mark recovery as completed
            if recovery_code:
                await self.recovery_collection.update_one(
                    {"recovery_code": recovery_code},
                    {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc)}}
                )
            
            logger.info(f"Recovered wallet {wallet_id} from backup")
            
            return {
                "wallet_id": wallet_id,
                "recovered_at": datetime.now(timezone.utc).isoformat(),
                "wallet_data": wallet_data
            }
            
        except Exception as e:
            logger.error(f"Failed to recover wallet from backup: {e}")
            raise
    
    async def recover_wallet_from_private_key(
        self,
        private_key: str,
        wallet_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Recover wallet from private key"""
        try:
            # Validate private key
            if len(private_key) != 64:
                raise ValueError("Invalid private key length")
            
            # Derive address from private key
            priv_key = PrivateKey(bytes.fromhex(private_key))
            address = priv_key.public_key.to_base58check_address()
            
            wallet_data = {
                "address": address,
                "private_key": private_key,  # Should be encrypted in production
                "recovered_at": datetime.now(timezone.utc).isoformat(),
                "recovery_method": "private_key"
            }
            
            if wallet_id:
                wallet_data["wallet_id"] = wallet_id
            
            logger.info(f"Recovered wallet from private key: {address}")
            
            return wallet_data
            
        except Exception as e:
            logger.error(f"Failed to recover wallet from private key: {e}")
            raise
    
    async def list_recovery_codes(
        self,
        wallet_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List recovery codes"""
        try:
            query = {}
            if wallet_id:
                query["wallet_id"] = wallet_id
            if user_id:
                query["user_id"] = user_id
            
            cursor = self.recovery_collection.find(query).sort("created_at", -1)
            codes = await cursor.to_list(length=100)
            
            # Remove sensitive data
            for code in codes:
                if "_id" in code:
                    code["_id"] = str(code["_id"])
                # Don't expose full recovery code in list
                if "recovery_code" in code:
                    code["recovery_code"] = code["recovery_code"][:8] + "..." 
                if "created_at" in code and isinstance(code["created_at"], datetime):
                    code["created_at"] = code["created_at"].isoformat()
            
            return codes
            
        except Exception as e:
            logger.error(f"Failed to list recovery codes: {e}")
            raise

