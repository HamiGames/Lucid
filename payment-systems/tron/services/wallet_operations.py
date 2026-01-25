"""
LUCID Payment Systems - Wallet Operations Coordinator Service
High-level operations coordinating multiple services
Distroless container: lucid-tron-wallet-manager:latest
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .wallet_manager import WalletManagerService
from .wallet_backup import WalletBackupService
from .wallet_audit import WalletAuditService, AuditAction, AuditSeverity
from .tron_client import TronClientService

logger = logging.getLogger(__name__)


class WalletOperationsService:
    """High-level wallet operations coordinator"""
    
    def __init__(
        self,
        wallet_manager: WalletManagerService,
        backup_service: Optional[WalletBackupService] = None,
        audit_service: Optional[WalletAuditService] = None,
        tron_client: Optional[TronClientService] = None
    ):
        """Initialize operations service"""
        self.wallet_manager = wallet_manager
        self.backup_service = backup_service
        self.audit_service = audit_service
        self.tron_client = tron_client
    
    async def sign_transaction_with_audit(
        self,
        wallet_id: str,
        password: str,
        transaction_data: Dict[str, Any],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sign transaction with audit logging"""
        try:
            # Sign transaction
            sign_result = await self.wallet_manager.sign_transaction(
                wallet_id=wallet_id,
                password=password,
                transaction_data=transaction_data
            )
            
            # Log audit event
            if self.audit_service:
                await self.audit_service.log_action(
                    action=AuditAction.SIGN_TRANSACTION,
                    wallet_id=wallet_id,
                    user_id=user_id,
                    severity=AuditSeverity.HIGH,
                    details={
                        "transaction_type": transaction_data.get("type"),
                        "txid": sign_result.get("txid"),
                        "to_address": transaction_data.get("to_address"),
                        "amount": transaction_data.get("amount")
                    },
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=True
                )
            
            return sign_result
            
        except Exception as e:
            # Log failed audit event
            if self.audit_service:
                await self.audit_service.log_action(
                    action=AuditAction.SIGN_TRANSACTION,
                    wallet_id=wallet_id,
                    user_id=user_id,
                    severity=AuditSeverity.HIGH,
                    details=transaction_data,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    error_message=str(e)
                )
            raise
    
    async def import_wallet_with_audit(
        self,
        private_key: str,
        name: str,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Import wallet with audit logging"""
        try:
            # Import wallet
            wallet_response = await self.wallet_manager.import_wallet(
                private_key=private_key,
                name=name,
                description=description
            )
            
            # Log audit event
            if self.audit_service:
                await self.audit_service.log_action(
                    action=AuditAction.IMPORT_WALLET,
                    wallet_id=wallet_response.wallet_id,
                    user_id=user_id,
                    severity=AuditSeverity.MEDIUM,
                    details={
                        "name": name,
                        "address": wallet_response.address
                    },
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=True
                )
            
            return {
                "wallet_id": wallet_response.wallet_id,
                "address": wallet_response.address,
                "created_at": wallet_response.created_at
            }
            
        except Exception as e:
            # Log failed audit event
            if self.audit_service:
                await self.audit_service.log_action(
                    action=AuditAction.IMPORT_WALLET,
                    wallet_id="unknown",
                    user_id=user_id,
                    severity=AuditSeverity.HIGH,
                    details={"name": name},
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    error_message=str(e)
                )
            raise
    
    async def create_backup_with_encryption(
        self,
        wallet_id: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create backup with encryption and audit logging"""
        try:
            # Create backup using wallet manager
            backup_result = await self.wallet_manager.create_backup(wallet_id)
            
            # Log audit event
            if self.audit_service:
                await self.audit_service.log_action(
                    action=AuditAction.BACKUP_WALLET,
                    wallet_id=wallet_id,
                    user_id=user_id,
                    severity=AuditSeverity.MEDIUM,
                    details={
                        "backup_id": backup_result["backup_id"],
                        "backup_file": backup_result["backup_file"]
                    },
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=True
                )
            
            return backup_result
            
        except Exception as e:
            # Log failed audit event
            if self.audit_service:
                await self.audit_service.log_action(
                    action=AuditAction.BACKUP_WALLET,
                    wallet_id=wallet_id,
                    user_id=user_id,
                    severity=AuditSeverity.MEDIUM,
                    details={},
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    error_message=str(e)
                )
            raise
    
    async def restore_wallet_with_validation(
        self,
        wallet_id: str,
        backup_id: str,
        password: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Restore wallet with validation and audit logging"""
        try:
            # Restore wallet
            restored_wallet = await self.wallet_manager.restore_backup(
                wallet_id=wallet_id,
                backup_id=backup_id,
                password=password
            )
            
            # Log audit event
            if self.audit_service:
                await self.audit_service.log_action(
                    action=AuditAction.RESTORE_WALLET,
                    wallet_id=wallet_id,
                    user_id=user_id,
                    severity=AuditSeverity.HIGH,
                    details={
                        "backup_id": backup_id,
                        "restored_address": restored_wallet.address
                    },
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=True
                )
            
            return {
                "wallet_id": restored_wallet.wallet_id,
                "address": restored_wallet.address,
                "restored_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            # Log failed audit event
            if self.audit_service:
                await self.audit_service.log_action(
                    action=AuditAction.RESTORE_WALLET,
                    wallet_id=wallet_id,
                    user_id=user_id,
                    severity=AuditSeverity.CRITICAL,
                    details={"backup_id": backup_id},
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    error_message=str(e)
                )
            raise
