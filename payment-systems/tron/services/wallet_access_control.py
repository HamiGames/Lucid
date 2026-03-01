"""
Wallet Access Control Service
Manages RBAC and permissions for wallet operations
"""

import logging
import os
from typing import Optional, Dict, Any, List, Set
from datetime import datetime, timezone, timedelta
from enum import Enum
from motor.motor_asyncio import AsyncIOMotorCollection


class Permission(str, Enum):
    """Wallet operation permissions"""
    VIEW_WALLET = "view_wallet"
    CREATE_WALLET = "create_wallet"
    UPDATE_WALLET = "update_wallet"
    DELETE_WALLET = "delete_wallet"
    EXPORT_WALLET = "export_wallet"
    IMPORT_WALLET = "import_wallet"
    SIGN_TRANSACTION = "sign_transaction"
    VIEW_BALANCE = "view_balance"
    VIEW_PRIVATE_KEY = "view_private_key"
    BACKUP_WALLET = "backup_wallet"
    RESTORE_WALLET = "restore_wallet"


class Role(str, Enum):
    """User roles"""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    OPERATOR = "operator"


# Role-based permissions mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: {
        Permission.VIEW_WALLET,
        Permission.CREATE_WALLET,
        Permission.UPDATE_WALLET,
        Permission.DELETE_WALLET,
        Permission.EXPORT_WALLET,
        Permission.IMPORT_WALLET,
        Permission.SIGN_TRANSACTION,
        Permission.VIEW_BALANCE,
        Permission.VIEW_PRIVATE_KEY,
        Permission.BACKUP_WALLET,
        Permission.RESTORE_WALLET
    },
    Role.OPERATOR: {
        Permission.VIEW_WALLET,
        Permission.CREATE_WALLET,
        Permission.UPDATE_WALLET,
        Permission.SIGN_TRANSACTION,
        Permission.VIEW_BALANCE,
        Permission.BACKUP_WALLET
    },
    Role.USER: {
        Permission.VIEW_WALLET,
        Permission.SIGN_TRANSACTION,
        Permission.VIEW_BALANCE,
        Permission.BACKUP_WALLET
    },
    Role.VIEWER: {
        Permission.VIEW_WALLET,
        Permission.VIEW_BALANCE
    }
}


logger = logging.getLogger(__name__)


class WalletAccessControlService:
    """Service for wallet access control and RBAC"""
    
    def __init__(self, access_collection: AsyncIOMotorCollection):
        """Initialize access control service"""
        self.access_collection = access_collection
        self._initialized = False
    
    async def initialize(self):
        """Initialize service and create indexes"""
        try:
            # Create indexes
            await self.access_collection.create_index("wallet_id")
            await self.access_collection.create_index("user_id")
            await self.access_collection.create_index([("wallet_id", 1), ("user_id", 1)], unique=True)
            
            self._initialized = True
            logger.info("Access control service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize access control service: {e}")
            raise
    
    def has_permission(
        self,
        user_role: Role,
        permission: Permission
    ) -> bool:
        """Check if role has permission"""
        role_perms = ROLE_PERMISSIONS.get(user_role, set())
        return permission in role_perms
    
    async def check_wallet_access(
        self,
        wallet_id: str,
        user_id: str,
        permission: Permission
    ) -> Tuple[bool, Optional[str]]:
        """Check if user has access to wallet operation"""
        try:
            # Get wallet access record
            access_record = await self.access_collection.find_one({
                "wallet_id": wallet_id,
                "user_id": user_id
            })
            
            if not access_record:
                return False, "User does not have access to this wallet"
            
            # Get user role
            user_role = Role(access_record.get("role", Role.USER.value))
            
            # Check permission
            if not self.has_permission(user_role, permission):
                return False, f"User role {user_role.value} does not have permission {permission.value}"
            
            # Check if access is revoked
            if access_record.get("revoked", False):
                return False, "Access to this wallet has been revoked"
            
            # Check expiration
            if "expires_at" in access_record and access_record["expires_at"]:
                expires_at = access_record["expires_at"]
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if expires_at < datetime.now(timezone.utc):
                    return False, "Access to this wallet has expired"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error checking wallet access: {e}")
            return False, str(e)
    
    async def grant_wallet_access(
        self,
        wallet_id: str,
        user_id: str,
        role: Role,
        granted_by: str,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """Grant access to wallet"""
        try:
            access_record = {
                "wallet_id": wallet_id,
                "user_id": user_id,
                "role": role.value,
                "granted_by": granted_by,
                "granted_at": datetime.now(timezone.utc),
                "revoked": False,
                "expires_at": expires_at
            }
            
            await self.access_collection.update_one(
                {"wallet_id": wallet_id, "user_id": user_id},
                {"$set": access_record},
                upsert=True
            )
            
            logger.info(f"Granted {role.value} access to wallet {wallet_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to grant wallet access: {e}")
            raise
    
    async def revoke_wallet_access(
        self,
        wallet_id: str,
        user_id: str,
        revoked_by: str
    ) -> bool:
        """Revoke access to wallet"""
        try:
            result = await self.access_collection.update_one(
                {"wallet_id": wallet_id, "user_id": user_id},
                {
                    "$set": {
                        "revoked": True,
                        "revoked_at": datetime.now(timezone.utc),
                        "revoked_by": revoked_by
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Revoked access to wallet {wallet_id} for user {user_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to revoke wallet access: {e}")
            raise
    
    async def get_wallet_users(self, wallet_id: str) -> List[Dict[str, Any]]:
        """Get all users with access to wallet"""
        try:
            cursor = self.access_collection.find({
                "wallet_id": wallet_id,
                "revoked": False
            })
            
            users = await cursor.to_list(length=1000)
            
            # Convert ObjectId to string
            for user in users:
                if "_id" in user:
                    user["_id"] = str(user["_id"])
                if "granted_at" in user and isinstance(user["granted_at"], datetime):
                    user["granted_at"] = user["granted_at"].isoformat()
                if "expires_at" in user and isinstance(user["expires_at"], datetime):
                    user["expires_at"] = user["expires_at"].isoformat()
            
            return users
            
        except Exception as e:
            logger.error(f"Failed to get wallet users: {e}")
            raise
    
    async def get_user_wallets(self, user_id: str) -> List[str]:
        """Get all wallet IDs user has access to"""
        try:
            cursor = self.access_collection.find({
                "user_id": user_id,
                "revoked": False
            })
            
            access_records = await cursor.to_list(length=1000)
            wallet_ids = [record["wallet_id"] for record in access_records]
            
            return wallet_ids
            
        except Exception as e:
            logger.error(f"Failed to get user wallets: {e}")
            raise

