"""
Wallet Audit Logging Service
Tracks all wallet operations for security and compliance
"""

import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from enum import Enum
from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId


class AuditAction(str, Enum):
    """Audit action types"""
    CREATE_WALLET = "create_wallet"
    UPDATE_WALLET = "update_wallet"
    DELETE_WALLET = "delete_wallet"
    EXPORT_WALLET = "export_wallet"
    IMPORT_WALLET = "import_wallet"
    SIGN_TRANSACTION = "sign_transaction"
    VIEW_BALANCE = "view_balance"
    VIEW_PRIVATE_KEY = "view_private_key"
    CHANGE_PASSWORD = "change_password"
    BACKUP_WALLET = "backup_wallet"
    RESTORE_WALLET = "restore_wallet"


class AuditSeverity(str, Enum):
    """Audit severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


logger = logging.getLogger(__name__)


class WalletAuditService:
    """Service for wallet audit logging"""
    
    def __init__(self, audit_collection: AsyncIOMotorCollection):
        """Initialize audit service"""
        self.audit_collection = audit_collection
        self._initialized = False
    
    async def initialize(self):
        """Initialize audit service and create indexes"""
        try:
            # Create indexes for efficient queries
            await self.audit_collection.create_index("wallet_id")
            await self.audit_collection.create_index("user_id")
            await self.audit_collection.create_index("action")
            await self.audit_collection.create_index("severity")
            await self.audit_collection.create_index("timestamp")
            await self.audit_collection.create_index([("wallet_id", 1), ("timestamp", -1)])
            await self.audit_collection.create_index([("user_id", 1), ("timestamp", -1)])
            await self.audit_collection.create_index([("action", 1), ("timestamp", -1)])
            
            self._initialized = True
            logger.info("Wallet audit service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize audit service: {e}")
            raise
    
    async def log_action(
        self,
        action: AuditAction,
        wallet_id: str,
        user_id: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> str:
        """Log an audit action"""
        try:
            audit_record = {
                "action": action.value,
                "wallet_id": wallet_id,
                "user_id": user_id,
                "severity": severity.value,
                "timestamp": datetime.now(timezone.utc),
                "success": success,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "details": details or {},
                "error_message": error_message
            }
            
            result = await self.audit_collection.insert_one(audit_record)
            audit_id = str(result.inserted_id)
            
            # Log critical actions immediately
            if severity == AuditSeverity.CRITICAL:
                logger.critical(
                    f"AUDIT CRITICAL: {action.value} on wallet {wallet_id} by user {user_id}"
                )
            elif severity == AuditSeverity.HIGH:
                logger.warning(
                    f"AUDIT HIGH: {action.value} on wallet {wallet_id} by user {user_id}"
                )
            
            return audit_id
            
        except Exception as e:
            logger.error(f"Failed to log audit action: {e}")
            # Don't raise - audit failures shouldn't break operations
            return ""
    
    async def get_audit_logs(
        self,
        wallet_id: Optional[str] = None,
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        severity: Optional[AuditSeverity] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit logs with filters"""
        try:
            query = {}
            
            if wallet_id:
                query["wallet_id"] = wallet_id
            if user_id:
                query["user_id"] = user_id
            if action:
                query["action"] = action.value
            if severity:
                query["severity"] = severity.value
            if start_date or end_date:
                query["timestamp"] = {}
                if start_date:
                    query["timestamp"]["$gte"] = start_date
                if end_date:
                    query["timestamp"]["$lte"] = end_date
            
            cursor = self.audit_collection.find(query).skip(skip).limit(limit).sort("timestamp", -1)
            logs = await cursor.to_list(length=limit)
            
            # Convert ObjectId to string
            for log in logs:
                if "_id" in log:
                    log["_id"] = str(log["_id"])
                if "timestamp" in log and isinstance(log["timestamp"], datetime):
                    log["timestamp"] = log["timestamp"].isoformat()
            
            return logs
            
        except Exception as e:
            logger.error(f"Failed to get audit logs: {e}")
            raise
    
    async def count_audit_logs(
        self,
        wallet_id: Optional[str] = None,
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        severity: Optional[AuditSeverity] = None
    ) -> int:
        """Count audit logs matching criteria"""
        try:
            query = {}
            
            if wallet_id:
                query["wallet_id"] = wallet_id
            if user_id:
                query["user_id"] = user_id
            if action:
                query["action"] = action.value
            if severity:
                query["severity"] = severity.value
            
            return await self.audit_collection.count_documents(query)
            
        except Exception as e:
            logger.error(f"Failed to count audit logs: {e}")
            raise
    
    async def get_security_events(
        self,
        wallet_id: Optional[str] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get security-related events (high/critical severity)"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            query = {
                "severity": {"$in": [AuditSeverity.HIGH.value, AuditSeverity.CRITICAL.value]},
                "timestamp": {"$gte": start_date}
            }
            
            if wallet_id:
                query["wallet_id"] = wallet_id
            
            cursor = self.audit_collection.find(query).sort("timestamp", -1).limit(100)
            events = await cursor.to_list(length=100)
            
            # Convert ObjectId to string
            for event in events:
                if "_id" in event:
                    event["_id"] = str(event["_id"])
                if "timestamp" in event and isinstance(event["timestamp"], datetime):
                    event["timestamp"] = event["timestamp"].isoformat()
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get security events: {e}")
            raise

