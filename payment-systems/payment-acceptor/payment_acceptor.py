"""
Payment Acceptor Module for Lucid Network
Handles incoming payment acceptance, validation, and processing
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import uuid4

from pydantic import BaseModel, Field

# Import existing payment system components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from tron_node.tron_client import TronService
from tron_node.usdt_trc20 import USDTTRC20Client, TransferType, TransactionStatus
from wallet.integration_manager import WalletIntegrationManager, WalletType, WalletRole

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaymentStatus(str, Enum):
    """Payment acceptance status"""
    PENDING = "pending"
    RECEIVED = "received"
    VALIDATED = "validated"
    PROCESSED = "processed"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REJECTED = "rejected"
    EXPIRED = "expired"

class PaymentType(str, Enum):
    """Types of payments accepted"""
    SESSION_PAYMENT = "session_payment"           # Payment for session services
    STORAGE_PAYMENT = "storage_payment"           # Payment for storage services
    BANDWIDTH_PAYMENT = "bandwidth_payment"       # Payment for bandwidth services
    NODE_REGISTRATION = "node_registration"       # Payment for node registration
    GOVERNANCE_FEE = "governance_fee"             # Payment for governance participation
    CUSTOM_SERVICE = "custom_service"             # Custom service payment
    DONATION = "donation"                         # Donation payment

class PaymentMethod(str, Enum):
    """Payment methods accepted"""
    USDT_TRC20 = "usdt_trc20"                    # USDT on TRON network
    TRX = "trx"                                  # TRON native token
    MULTI_TOKEN = "multi_token"                   # Multiple token payment

class PaymentPriority(str, Enum):
    """Payment processing priority"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class PaymentRequest:
    """Payment request data"""
    payment_id: str
    payment_type: PaymentType
    payment_method: PaymentMethod
    amount: float
    token_type: str = "USDT"
    recipient_address: str = ""
    sender_address: Optional[str] = None
    session_id: Optional[str] = None
    node_id: Optional[str] = None
    service_id: Optional[str] = None
    reference_id: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    priority: PaymentPriority = PaymentPriority.NORMAL
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: PaymentStatus = PaymentStatus.PENDING

@dataclass
class PaymentConfirmation:
    """Payment confirmation data"""
    payment_id: str
    txid: Optional[str] = None
    block_height: Optional[int] = None
    confirmation_count: int = 0
    required_confirmations: int = 19
    confirmed_at: Optional[datetime] = None
    gas_used: Optional[int] = None
    energy_used: Optional[int] = None
    fee_paid: Optional[float] = None

@dataclass
class PaymentValidation:
    """Payment validation result"""
    payment_id: str
    is_valid: bool
    validation_errors: List[str] = field(default_factory=list)
    compliance_checks: Dict[str, bool] = field(default_factory=dict)
    risk_score: float = 0.0
    validated_at: Optional[datetime] = None

class PaymentRequestModel(BaseModel):
    """Pydantic model for payment requests"""
    payment_type: PaymentType = Field(..., description="Type of payment")
    payment_method: PaymentMethod = Field(..., description="Payment method")
    amount: float = Field(..., gt=0, description="Payment amount")
    token_type: str = Field(default="USDT", description="Token type")
    recipient_address: str = Field(..., description="Recipient wallet address")
    sender_address: Optional[str] = Field(default=None, description="Sender wallet address")
    session_id: Optional[str] = Field(default=None, description="Associated session ID")
    node_id: Optional[str] = Field(default=None, description="Associated node ID")
    service_id: Optional[str] = Field(default=None, description="Service ID")
    reference_id: Optional[str] = Field(default=None, description="Reference ID")
    description: Optional[str] = Field(default=None, description="Payment description")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    priority: PaymentPriority = Field(default=PaymentPriority.NORMAL, description="Payment priority")
    expires_at: Optional[str] = Field(default=None, description="Expiration timestamp")

class PaymentResponseModel(BaseModel):
    """Pydantic model for payment responses"""
    payment_id: str
    status: str
    message: str
    amount: float
    token_type: str
    recipient_address: str
    payment_type: str
    payment_method: str
    created_at: str
    expires_at: Optional[str] = None
    estimated_confirmation: Optional[str] = None

class PaymentAcceptor:
    """Payment acceptance and processing system"""
    
    def __init__(self):
        self.payment_requests: Dict[str, PaymentRequest] = {}
        self.payment_confirmations: Dict[str, PaymentConfirmation] = {}
        self.payment_validations: Dict[str, PaymentValidation] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Initialize TRON services
        self.tron_service = TronService()
        self.usdt_client = USDTTRC20Client()
        self.wallet_manager = WalletIntegrationManager()
        
        # Configuration
        self.config = {
            "min_payment_amount": 0.01,
            "max_payment_amount": 10000.0,
            "default_expiry_hours": 24,
            "required_confirmations": 19,
            "validation_timeout_seconds": 300,
            "processing_timeout_seconds": 600,
            "max_concurrent_payments": 50,
            "supported_tokens": ["USDT", "TRX"],
            "supported_networks": ["TRON"]
        }
        
        # Start background tasks
        asyncio.create_task(self._monitor_payments())
        asyncio.create_task(self._process_payment_queue())
        asyncio.create_task(self._cleanup_expired_payments())
        
        logger.info("PaymentAcceptor initialized")

    async def create_payment_request(self, request: PaymentRequestModel) -> PaymentResponseModel:
        """Create a new payment request"""
        try:
            # Generate unique payment ID
            payment_id = f"PAY_{uuid4().hex[:16].upper()}"
            
            # Create payment request
            payment_request = PaymentRequest(
                payment_id=payment_id,
                payment_type=request.payment_type,
                payment_method=request.payment_method,
                amount=request.amount,
                token_type=request.token_type,
                recipient_address=request.recipient_address,
                sender_address=request.sender_address,
                session_id=request.session_id,
                node_id=request.node_id,
                service_id=request.service_id,
                reference_id=request.reference_id,
                description=request.description,
                metadata=request.metadata,
                priority=request.priority,
                expires_at=datetime.fromisoformat(request.expires_at) if request.expires_at else None
            )
            
            # Validate payment request
            validation_result = await self._validate_payment_request(payment_request)
            if not validation_result.is_valid:
                return PaymentResponseModel(
                    payment_id=payment_id,
                    status="failed",
                    message=f"Payment validation failed: {', '.join(validation_result.validation_errors)}",
                    amount=request.amount,
                    token_type=request.token_type,
                    recipient_address=request.recipient_address,
                    payment_type=request.payment_type.value,
                    payment_method=request.payment_method.value,
                    created_at=payment_request.created_at.isoformat()
                )
            
            # Store payment request
            self.payment_requests[payment_id] = payment_request
            self.payment_validations[payment_id] = validation_result
            
            # Create payment confirmation tracker
            self.payment_confirmations[payment_id] = PaymentConfirmation(
                payment_id=payment_id,
                required_confirmations=self.config["required_confirmations"]
            )
            
            # Log payment creation
            await self._log_payment_event(payment_id, "created", {
                "amount": request.amount,
                "type": request.payment_type.value,
                "method": request.payment_method.value
            })
            
            return PaymentResponseModel(
                payment_id=payment_id,
                status="pending",
                message="Payment request created successfully",
                amount=request.amount,
                token_type=request.token_type,
                recipient_address=request.recipient_address,
                payment_type=request.payment_type.value,
                payment_method=request.payment_method.value,
                created_at=payment_request.created_at.isoformat(),
                expires_at=payment_request.expires_at.isoformat() if payment_request.expires_at else None,
                estimated_confirmation=f"{self.config['required_confirmations']} blocks"
            )
            
        except Exception as e:
            logger.error(f"Error creating payment request: {e}")
            return PaymentResponseModel(
                payment_id="",
                status="failed",
                message=f"Failed to create payment request: {str(e)}",
                amount=request.amount,
                token_type=request.token_type,
                recipient_address=request.recipient_address,
                payment_type=request.payment_type.value,
                payment_method=request.payment_method.value,
                created_at=datetime.now(timezone.utc).isoformat()
            )

    async def _validate_payment_request(self, request: PaymentRequest) -> PaymentValidation:
        """Validate payment request"""
        validation_errors = []
        compliance_checks = {}
        
        # Amount validation
        if request.amount < self.config["min_payment_amount"]:
            validation_errors.append(f"Amount too small (minimum: {self.config['min_payment_amount']})")
        
        if request.amount > self.config["max_payment_amount"]:
            validation_errors.append(f"Amount too large (maximum: {self.config['max_payment_amount']})")
        
        # Token validation
        if request.token_type not in self.config["supported_tokens"]:
            validation_errors.append(f"Unsupported token type: {request.token_type}")
        
        # Address validation
        if not self._validate_tron_address(request.recipient_address):
            validation_errors.append("Invalid recipient address")
        
        if request.sender_address and not self._validate_tron_address(request.sender_address):
            validation_errors.append("Invalid sender address")
        
        # Payment type validation
        if request.payment_type == PaymentType.SESSION_PAYMENT and not request.session_id:
            validation_errors.append("Session ID required for session payments")
        
        if request.payment_type == PaymentType.NODE_REGISTRATION and not request.node_id:
            validation_errors.append("Node ID required for node registration payments")
        
        # Compliance checks
        compliance_checks["amount_within_limits"] = self.config["min_payment_amount"] <= request.amount <= self.config["max_payment_amount"]
        compliance_checks["valid_token"] = request.token_type in self.config["supported_tokens"]
        compliance_checks["valid_addresses"] = self._validate_tron_address(request.recipient_address)
        compliance_checks["required_fields"] = self._check_required_fields(request)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(request, compliance_checks)
        
        return PaymentValidation(
            payment_id=request.payment_id,
            is_valid=len(validation_errors) == 0,
            validation_errors=validation_errors,
            compliance_checks=compliance_checks,
            risk_score=risk_score,
            validated_at=datetime.now(timezone.utc)
        )

    def _validate_tron_address(self, address: str) -> bool:
        """Validate TRON address format"""
        if not address or len(address) != 34:
            return False
        return address.startswith('T') and address[1:].isalnum()

    def _check_required_fields(self, request: PaymentRequest) -> bool:
        """Check if required fields are present based on payment type"""
        if request.payment_type == PaymentType.SESSION_PAYMENT:
            return bool(request.session_id)
        elif request.payment_type == PaymentType.NODE_REGISTRATION:
            return bool(request.node_id)
        elif request.payment_type == PaymentType.STORAGE_PAYMENT:
            return bool(request.service_id)
        return True

    def _calculate_risk_score(self, request: PaymentRequest, compliance_checks: Dict[str, bool]) -> float:
        """Calculate payment risk score (0.0 to 1.0)"""
        risk_score = 0.0
        
        # Amount-based risk
        if request.amount > 1000.0:
            risk_score += 0.3
        elif request.amount > 100.0:
            risk_score += 0.1
        
        # Payment type risk
        if request.payment_type in [PaymentType.CUSTOM_SERVICE, PaymentType.DONATION]:
            risk_score += 0.2
        
        # Compliance risk
        failed_checks = sum(1 for check in compliance_checks.values() if not check)
        risk_score += failed_checks * 0.1
        
        # Priority risk
        if request.priority == PaymentPriority.URGENT:
            risk_score += 0.2
        
        return min(risk_score, 1.0)

    async def process_incoming_payment(self, txid: str, amount: float, 
                                     sender_address: str, recipient_address: str,
                                     token_type: str = "USDT") -> Optional[str]:
        """Process incoming payment transaction"""
        try:
            # Find matching payment request
            payment_id = await self._find_matching_payment_request(
                amount, recipient_address, token_type
            )
            
            if not payment_id:
                logger.warning(f"No matching payment request found for transaction {txid}")
                return None
            
            payment_request = self.payment_requests[payment_id]
            payment_confirmation = self.payment_confirmations[payment_id]
            
            # Update payment status
            payment_request.status = PaymentStatus.RECEIVED
            payment_request.sender_address = sender_address
            
            # Update confirmation data
            payment_confirmation.txid = txid
            payment_confirmation.confirmation_count = 1
            
            # Log payment received
            await self._log_payment_event(payment_id, "received", {
                "txid": txid,
                "amount": amount,
                "sender": sender_address
            })
            
            # Start monitoring for confirmations
            asyncio.create_task(self._monitor_payment_confirmation(payment_id, txid))
            
            return payment_id
            
        except Exception as e:
            logger.error(f"Error processing incoming payment {txid}: {e}")
            return None

    async def _find_matching_payment_request(self, amount: float, recipient_address: str, 
                                           token_type: str) -> Optional[str]:
        """Find matching payment request for incoming payment"""
        for payment_id, request in self.payment_requests.items():
            if (request.status == PaymentStatus.PENDING and
                abs(request.amount - amount) < 0.01 and
                request.recipient_address == recipient_address and
                request.token_type == token_type):
                return payment_id
        return None

    async def _monitor_payment_confirmation(self, payment_id: str, txid: str):
        """Monitor payment confirmation status"""
        try:
            payment_confirmation = self.payment_confirmations[payment_id]
            
            while payment_confirmation.confirmation_count < payment_confirmation.required_confirmations:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Get transaction status
                status = await self.usdt_client.get_transaction_status(txid)
                
                if status == TransactionStatus.CONFIRMED:
                    payment_confirmation.confirmation_count += 1
                    payment_confirmation.block_height = await self._get_transaction_block_height(txid)
                    
                    # Update payment status
                    if payment_confirmation.confirmation_count >= payment_confirmation.required_confirmations:
                        payment_request = self.payment_requests[payment_id]
                        payment_request.status = PaymentStatus.CONFIRMED
                        payment_confirmation.confirmed_at = datetime.now(timezone.utc)
                        
                        # Process confirmed payment
                        await self._process_confirmed_payment(payment_id)
                        
                        await self._log_payment_event(payment_id, "confirmed", {
                            "confirmations": payment_confirmation.confirmation_count,
                            "block_height": payment_confirmation.block_height
                        })
                        break
                
                elif status == TransactionStatus.FAILED:
                    payment_request = self.payment_requests[payment_id]
                    payment_request.status = PaymentStatus.FAILED
                    
                    await self._log_payment_event(payment_id, "failed", {
                        "reason": "Transaction failed on blockchain"
                    })
                    break
                    
        except Exception as e:
            logger.error(f"Error monitoring payment confirmation {payment_id}: {e}")

    async def _get_transaction_block_height(self, txid: str) -> Optional[int]:
        """Get block height for transaction"""
        try:
            # This would integrate with TRON API to get block height
            return self.tron_service.get_height()
        except Exception as e:
            logger.error(f"Error getting block height for {txid}: {e}")
            return None

    async def _process_confirmed_payment(self, payment_id: str):
        """Process confirmed payment"""
        try:
            payment_request = self.payment_requests[payment_id]
            
            # Update payment status
            payment_request.status = PaymentStatus.PROCESSED
            
            # Process based on payment type
            if payment_request.payment_type == PaymentType.SESSION_PAYMENT:
                await self._process_session_payment(payment_request)
            elif payment_request.payment_type == PaymentType.NODE_REGISTRATION:
                await self._process_node_registration_payment(payment_request)
            elif payment_request.payment_type == PaymentType.STORAGE_PAYMENT:
                await self._process_storage_payment(payment_request)
            else:
                await self._process_generic_payment(payment_request)
            
            await self._log_payment_event(payment_id, "processed", {
                "type": payment_request.payment_type.value
            })
            
        except Exception as e:
            logger.error(f"Error processing confirmed payment {payment_id}: {e}")

    async def _process_session_payment(self, payment_request: PaymentRequest):
        """Process session payment"""
        # Activate session or extend session duration
        if payment_request.session_id:
            self.active_sessions[payment_request.session_id] = {
                "payment_id": payment_request.payment_id,
                "amount": payment_request.amount,
                "activated_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)
            }

    async def _process_node_registration_payment(self, payment_request: PaymentRequest):
        """Process node registration payment"""
        # Register node or extend node registration
        if payment_request.node_id:
            # This would integrate with node registration system
            pass

    async def _process_storage_payment(self, payment_request: PaymentRequest):
        """Process storage payment"""
        # Allocate storage or extend storage duration
        if payment_request.service_id:
            # This would integrate with storage system
            pass

    async def _process_generic_payment(self, payment_request: PaymentRequest):
        """Process generic payment"""
        # Handle generic payment processing
        pass

    async def _monitor_payments(self):
        """Monitor active payments"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                for payment_id, request in self.payment_requests.items():
                    if request.status == PaymentStatus.PENDING:
                        # Check if payment has expired
                        if request.expires_at and datetime.now(timezone.utc) > request.expires_at:
                            request.status = PaymentStatus.EXPIRED
                            await self._log_payment_event(payment_id, "expired", {})
                            
            except Exception as e:
                logger.error(f"Error in payment monitoring: {e}")

    async def _process_payment_queue(self):
        """Process payment queue"""
        while True:
            try:
                await asyncio.sleep(10)  # Process every 10 seconds
                
                # Process high priority payments first
                for priority in [PaymentPriority.URGENT, PaymentPriority.HIGH, 
                               PaymentPriority.NORMAL, PaymentPriority.LOW]:
                    for payment_id, request in self.payment_requests.items():
                        if (request.status == PaymentStatus.RECEIVED and 
                            request.priority == priority):
                            await self._process_payment_request(payment_id)
                            
            except Exception as e:
                logger.error(f"Error in payment queue processing: {e}")

    async def _process_payment_request(self, payment_id: str):
        """Process individual payment request"""
        try:
            payment_request = self.payment_requests[payment_id]
            
            # Validate payment again
            validation_result = await self._validate_payment_request(payment_request)
            if not validation_result.is_valid:
                payment_request.status = PaymentStatus.REJECTED
                await self._log_payment_event(payment_id, "rejected", {
                    "errors": validation_result.validation_errors
                })
                return
            
            # Update validation
            self.payment_validations[payment_id] = validation_result
            payment_request.status = PaymentStatus.VALIDATED
            
            await self._log_payment_event(payment_id, "validated", {
                "risk_score": validation_result.risk_score
            })
            
        except Exception as e:
            logger.error(f"Error processing payment request {payment_id}: {e}")

    async def _cleanup_expired_payments(self):
        """Cleanup expired payments"""
        while True:
            try:
                await asyncio.sleep(3600)  # Cleanup every hour
                
                current_time = datetime.now(timezone.utc)
                expired_payments = []
                
                for payment_id, request in self.payment_requests.items():
                    if (request.status in [PaymentStatus.EXPIRED, PaymentStatus.FAILED, PaymentStatus.REJECTED] and
                        (current_time - request.created_at).days > 7):
                        expired_payments.append(payment_id)
                
                for payment_id in expired_payments:
                    del self.payment_requests[payment_id]
                    if payment_id in self.payment_confirmations:
                        del self.payment_confirmations[payment_id]
                    if payment_id in self.payment_validations:
                        del self.payment_validations[payment_id]
                
                if expired_payments:
                    logger.info(f"Cleaned up {len(expired_payments)} expired payments")
                    
            except Exception as e:
                logger.error(f"Error in payment cleanup: {e}")

    async def get_payment_status(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Get payment status"""
        if payment_id not in self.payment_requests:
            return None
        
        request = self.payment_requests[payment_id]
        confirmation = self.payment_confirmations.get(payment_id)
        validation = self.payment_validations.get(payment_id)
        
        return {
            "payment_id": payment_id,
            "status": request.status.value,
            "amount": request.amount,
            "token_type": request.token_type,
            "payment_type": request.payment_type.value,
            "payment_method": request.payment_method.value,
            "recipient_address": request.recipient_address,
            "sender_address": request.sender_address,
            "created_at": request.created_at.isoformat(),
            "expires_at": request.expires_at.isoformat() if request.expires_at else None,
            "txid": confirmation.txid if confirmation else None,
            "confirmations": confirmation.confirmation_count if confirmation else 0,
            "required_confirmations": confirmation.required_confirmations if confirmation else 0,
            "confirmed_at": confirmation.confirmed_at.isoformat() if confirmation and confirmation.confirmed_at else None,
            "is_valid": validation.is_valid if validation else False,
            "risk_score": validation.risk_score if validation else 0.0,
            "validation_errors": validation.validation_errors if validation else []
        }

    async def list_payments(self, status: Optional[PaymentStatus] = None, 
                          payment_type: Optional[PaymentType] = None,
                          limit: int = 100) -> List[Dict[str, Any]]:
        """List payments"""
        payments = []
        
        for payment_id, request in self.payment_requests.items():
            if status and request.status != status:
                continue
            if payment_type and request.payment_type != payment_type:
                continue
            
            payment_data = await self.get_payment_status(payment_id)
            if payment_data:
                payments.append(payment_data)
        
        # Sort by creation time (newest first)
        payments.sort(key=lambda x: x["created_at"], reverse=True)
        
        return payments[:limit]

    async def get_payment_statistics(self) -> Dict[str, Any]:
        """Get payment statistics"""
        total_payments = len(self.payment_requests)
        status_counts = {}
        type_counts = {}
        total_amount = 0.0
        
        for request in self.payment_requests.values():
            # Status counts
            status = request.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Type counts
            payment_type = request.payment_type.value
            type_counts[payment_type] = type_counts.get(payment_type, 0) + 1
            
            # Total amount
            if request.status == PaymentStatus.CONFIRMED:
                total_amount += request.amount
        
        return {
            "total_payments": total_payments,
            "status_breakdown": status_counts,
            "type_breakdown": type_counts,
            "total_amount_confirmed": total_amount,
            "active_sessions": len(self.active_sessions),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def _log_payment_event(self, payment_id: str, event_type: str, data: Dict[str, Any]):
        """Log payment event"""
        try:
            log_data = {
                "payment_id": payment_id,
                "event_type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data
            }
            
            # In a real implementation, this would write to a proper logging system
            logger.info(f"Payment Event: {json.dumps(log_data)}")
            
        except Exception as e:
            logger.error(f"Error logging payment event: {e}")

# Global instance
payment_acceptor = PaymentAcceptor()

# Public API functions
async def create_payment_request(request: PaymentRequestModel) -> PaymentResponseModel:
    """Create a new payment request"""
    return await payment_acceptor.create_payment_request(request)

async def process_incoming_payment(txid: str, amount: float, sender_address: str, 
                                 recipient_address: str, token_type: str = "USDT") -> Optional[str]:
    """Process incoming payment transaction"""
    return await payment_acceptor.process_incoming_payment(txid, amount, sender_address, recipient_address, token_type)

async def get_payment_status(payment_id: str) -> Optional[Dict[str, Any]]:
    """Get payment status"""
    return await payment_acceptor.get_payment_status(payment_id)

async def list_payments(status: Optional[PaymentStatus] = None, 
                       payment_type: Optional[PaymentType] = None,
                       limit: int = 100) -> List[Dict[str, Any]]:
    """List payments"""
    return await payment_acceptor.list_payments(status, payment_type, limit)

async def get_payment_statistics() -> Dict[str, Any]:
    """Get payment statistics"""
    return await payment_acceptor.get_payment_statistics()

async def main():
    """Main function for testing"""
    # Create a test payment request
    request = PaymentRequestModel(
        payment_type=PaymentType.SESSION_PAYMENT,
        payment_method=PaymentMethod.USDT_TRC20,
        amount=10.0,
        recipient_address="TTestAddress1234567890123456789012345",
        session_id="session_123",
        description="Test session payment"
    )
    
    response = await create_payment_request(request)
    print(f"Payment created: {response}")
    
    # Get payment status
    status = await get_payment_status(response.payment_id)
    print(f"Payment status: {status}")
    
    # Get statistics
    stats = await get_payment_statistics()
    print(f"Payment statistics: {stats}")

if __name__ == "__main__":
    asyncio.run(main())
