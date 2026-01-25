"""
LUCID Payment Systems - Payment Gateway Service
Payment processing and gateway operations for TRON payments
Distroless container: lucid-payment-gateway:latest
"""

import asyncio
import logging
import os
import time
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import aiofiles
from dataclasses import asdict
import httpx
from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_settings

# Import payment models from dedicated models file
from ..models.payment import (
    PaymentStatus,
    PaymentType,
    PaymentMethod,
    PaymentInfo,
    PaymentRequest,
    PaymentCreateRequest,
    PaymentResponse,
    PaymentStatusRequest,
    PaymentStatusResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaymentGatewayService:
    """Payment gateway service"""
    
    def __init__(self):
        self.settings = get_settings()
        
        # TRON client configuration - from environment variables
        self.tron_client_url = os.getenv("TRON_CLIENT_URL", os.getenv("PAYMENT_GATEWAY_TRON_CLIENT_URL", "http://lucid-tron-client:8091"))
        self.wallet_manager_url = os.getenv("WALLET_MANAGER_URL", os.getenv("PAYMENT_GATEWAY_WALLET_MANAGER_URL", "http://lucid-wallet-manager:8093"))
        self.usdt_manager_url = os.getenv("USDT_MANAGER_URL", os.getenv("PAYMENT_GATEWAY_USDT_MANAGER_URL", "http://lucid-usdt-manager:8094"))
        self.payout_router_url = os.getenv("PAYOUT_ROUTER_URL", os.getenv("PAYMENT_GATEWAY_PAYOUT_ROUTER_URL", "http://lucid-payout-router:8092"))
        
        # Initialize TRON client
        self._initialize_tron_client()
        
        # Data storage - from environment variables
        data_base = os.getenv("DATA_DIRECTORY", os.getenv("TRON_DATA_DIR", "/data/payment-systems"))
        self.data_dir = Path(data_base) / "payment-gateway"
        self.payments_dir = self.data_dir / "payments"
        self.logs_dir = self.data_dir / "logs"
        
        # Ensure directories exist
        for directory in [self.payments_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Payment tracking
        self.payments: Dict[str, PaymentInfo] = {}
        self.pending_payments: Dict[str, PaymentInfo] = {}
        self.processing_payments: Dict[str, PaymentInfo] = {}
        self.completed_payments: Dict[str, PaymentInfo] = {}
        self.failed_payments: Dict[str, PaymentInfo] = {}
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self.is_running = False
        
        logger.info("PaymentGatewayService initialized (not yet started)")
    
    async def initialize(self):
        """Initialize service and start background tasks"""
        try:
            logger.info("Starting PaymentGatewayService...")
            
            # Load existing data from disk
            await self._load_existing_data()
            
            # Start background processing tasks
            self.is_running = True
            self.background_tasks = [
                asyncio.create_task(self._process_payments()),
                asyncio.create_task(self._monitor_payments()),
                asyncio.create_task(self._cleanup_old_data())
            ]
            
            logger.info("PaymentGatewayService started successfully with background tasks")
        except Exception as e:
            logger.error(f"Error initializing PaymentGatewayService: {e}")
            raise
    
    async def stop(self):
        """Stop service and cancel background tasks"""
        try:
            logger.info("Stopping PaymentGatewayService...")
            
            # Set running flag to False
            self.is_running = False
            
            # Cancel all background tasks
            for task in self.background_tasks:
                if task and not task.done():
                    task.cancel()
            
            # Wait for all tasks to complete
            if self.background_tasks:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            # Save current state
            await self._save_payments_registry()
            
            logger.info("PaymentGatewayService stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping PaymentGatewayService: {e}")
            raise
    
    def _initialize_tron_client(self):
        """Initialize TRON client connection"""
        try:
            # In production, this would connect to the TRON client service
            # For now, we'll use direct TRON connection
            self.tron = Tron()
            logger.info("TRON client initialized for payment gateway")
        except Exception as e:
            logger.error(f"Failed to initialize TRON client: {e}")
            raise
    
    async def _load_existing_data(self):
        """Load existing data from disk"""
        try:
            # Load payments
            payments_file = self.payments_dir / "payments_registry.json"
            if payments_file.exists():
                async with aiofiles.open(payments_file, "r") as f:
                    data = await f.read()
                    payments_data = json.loads(data)
                    
                    for payment_id, payment_data in payments_data.items():
                        # Convert datetime strings back to datetime objects
                        for field in ['created_at', 'processed_at', 'completed_at']:
                            if field in payment_data and payment_data[field]:
                                payment_data[field] = datetime.fromisoformat(payment_data[field])
                        
                        payment_info = PaymentInfo(**payment_data)
                        self.payments[payment_id] = payment_info
                        
                        # Categorize by status
                        if payment_info.status == PaymentStatus.PENDING:
                            self.pending_payments[payment_id] = payment_info
                        elif payment_info.status == PaymentStatus.PROCESSING:
                            self.processing_payments[payment_id] = payment_info
                        elif payment_info.status == PaymentStatus.COMPLETED:
                            self.completed_payments[payment_id] = payment_info
                        elif payment_info.status == PaymentStatus.FAILED:
                            self.failed_payments[payment_id] = payment_info
                    
                logger.info(f"Loaded {len(self.payments)} existing payments")
                
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
    
    async def _save_payments_registry(self):
        """Save payments registry to disk"""
        try:
            payments_data = {}
            for payment_id, payment_info in self.payments.items():
                # Convert to dict and handle datetime serialization
                payment_dict = asdict(payment_info)
                for field in ['created_at', 'processed_at', 'completed_at']:
                    if payment_dict.get(field):
                        payment_dict[field] = payment_dict[field].isoformat()
                payments_data[payment_id] = payment_dict
            
            payments_file = self.payments_dir / "payments_registry.json"
            async with aiofiles.open(payments_file, "w") as f:
                await f.write(json.dumps(payments_data, indent=2))
                
        except Exception as e:
            logger.error(f"Error saving payments registry: {e}")
    
    async def create_payment(self, request: PaymentCreateRequest) -> PaymentResponse:
        """Create a new payment"""
        try:
            logger.info(f"Creating payment: {request.amount} {request.currency} from {request.from_address} to {request.to_address}")
            
            # Generate payment ID
            payment_id = f"pay_{int(time.time())}_{hashlib.sha256(request.from_address.encode()).hexdigest()[:8]}"
            
            # Create payment info
            payment_info = PaymentInfo(
                payment_id=payment_id,
                from_address=request.from_address,
                to_address=request.to_address,
                amount=request.amount,
                currency=request.currency,
                payment_type=request.payment_type,
                payment_method=request.payment_method,
                status=PaymentStatus.PENDING,
                transaction_id=None,
                fee=0.0,
                created_at=datetime.now(),
                processed_at=None,
                completed_at=None,
                error_message=None,
                metadata=request.metadata
            )
            
            # Store payment
            self.payments[payment_id] = payment_info
            self.pending_payments[payment_id] = payment_info
            
            # Save registry
            await self._save_payments_registry()
            
            # Log payment creation
            await self._log_payment_event(payment_id, "payment_created", {
                "from_address": request.from_address,
                "to_address": request.to_address,
                "amount": request.amount,
                "currency": request.currency,
                "payment_type": request.payment_type.value
            })
            
            logger.info(f"Created payment: {payment_id}")
            
            return PaymentResponse(
                payment_id=payment_id,
                transaction_id=None,
                status=PaymentStatus.PENDING.value,
                amount=request.amount,
                currency=request.currency,
                from_address=request.from_address,
                to_address=request.to_address,
                fee=0.0,
                created_at=payment_info.created_at.isoformat(),
                processed_at=None,
                completed_at=None,
                error_message=None
            )
            
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            raise
    
    async def process_payment(self, payment_id: str) -> PaymentResponse:
        """Process a payment"""
        try:
            if payment_id not in self.payments:
                raise ValueError("Payment not found")
            
            payment_info = self.payments[payment_id]
            
            if payment_info.status != PaymentStatus.PENDING:
                raise ValueError(f"Payment cannot be processed: {payment_info.status}")
            
            logger.info(f"Processing payment: {payment_id}")
            
            # Update status to processing
            payment_info.status = PaymentStatus.PROCESSING
            payment_info.processed_at = datetime.now()
            
            # Move to processing
            self.processing_payments[payment_id] = payment_info
            if payment_id in self.pending_payments:
                del self.pending_payments[payment_id]
            
            # Process based on payment type
            try:
                if payment_info.payment_type == PaymentType.TRX_TRANSFER:
                    await self._process_trx_transfer(payment_info)
                elif payment_info.payment_type == PaymentType.USDT_TRANSFER:
                    await self._process_usdt_transfer(payment_info)
                elif payment_info.payment_type == PaymentType.CONTRACT_PAYMENT:
                    await self._process_contract_payment(payment_info)
                elif payment_info.payment_type == PaymentType.STAKING_PAYMENT:
                    await self._process_staking_payment(payment_info)
                elif payment_info.payment_type == PaymentType.FEE_PAYMENT:
                    await self._process_fee_payment(payment_info)
                else:
                    raise ValueError(f"Unsupported payment type: {payment_info.payment_type}")
                
                # Mark as completed
                payment_info.status = PaymentStatus.COMPLETED
                payment_info.completed_at = datetime.now()
                
                # Move to completed
                self.completed_payments[payment_id] = payment_info
                if payment_id in self.processing_payments:
                    del self.processing_payments[payment_id]
                
                # Log completion
                await self._log_payment_event(payment_id, "payment_completed", {
                    "transaction_id": payment_info.transaction_id,
                    "amount": payment_info.amount,
                    "currency": payment_info.currency
                })
                
                logger.info(f"Payment completed: {payment_id} -> {payment_info.transaction_id}")
                
            except Exception as e:
                # Mark as failed
                payment_info.status = PaymentStatus.FAILED
                payment_info.error_message = str(e)
                
                # Move to failed
                self.failed_payments[payment_id] = payment_info
                if payment_id in self.processing_payments:
                    del self.processing_payments[payment_id]
                
                # Log failure
                await self._log_payment_event(payment_id, "payment_failed", {
                    "error": str(e)
                })
                
                logger.error(f"Payment failed: {payment_id} - {e}")
                raise
            
            # Save registry
            await self._save_payments_registry()
            
            return PaymentResponse(
                payment_id=payment_id,
                transaction_id=payment_info.transaction_id,
                status=payment_info.status.value,
                amount=payment_info.amount,
                currency=payment_info.currency,
                from_address=payment_info.from_address,
                to_address=payment_info.to_address,
                fee=payment_info.fee,
                created_at=payment_info.created_at.isoformat(),
                processed_at=payment_info.processed_at.isoformat() if payment_info.processed_at else None,
                completed_at=payment_info.completed_at.isoformat() if payment_info.completed_at else None,
                error_message=payment_info.error_message
            )
            
        except Exception as e:
            logger.error(f"Error processing payment {payment_id}: {e}")
            raise
    
    async def _process_trx_transfer(self, payment_info: PaymentInfo):
        """Process TRX transfer"""
        try:
            # Convert TRX to SUN
            amount_sun = int(payment_info.amount * 1_000_000)
            
            # Create transfer transaction
            txn = self.tron.trx.transfer(
                payment_info.from_address,
                payment_info.to_address,
                amount_sun
            ).build()
            
            # Sign transaction if private key provided
            if payment_info.metadata and "private_key" in payment_info.metadata:
                private_key = PrivateKey(bytes.fromhex(payment_info.metadata["private_key"]))
                txn = txn.sign(private_key)
            
            # Broadcast transaction
            result = txn.broadcast()
            
            if result.get("result"):
                payment_info.transaction_id = result["txid"]
                payment_info.fee = 0.1  # Mock fee
            else:
                raise RuntimeError(f"TRX transfer failed: {result}")
                
        except Exception as e:
            logger.error(f"Error processing TRX transfer: {e}")
            raise
    
    async def _process_usdt_transfer(self, payment_info: PaymentInfo):
        """Process USDT transfer"""
        try:
            # USDT contract address - from environment variable
            usdt_contract = os.getenv("USDT_CONTRACT_ADDRESS", os.getenv("PAYMENT_GATEWAY_USDT_CONTRACT_ADDRESS", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"))
            
            # Get USDT contract
            contract = self.tron.get_contract(usdt_contract)
            
            # Get decimals
            decimals = contract.functions.decimals()
            amount_raw = int(payment_info.amount * (10 ** decimals))
            
            # Create transfer transaction
            txn = contract.functions.transfer(
                payment_info.to_address,
                amount_raw
            ).with_owner(payment_info.from_address).build()
            
            # Sign transaction if private key provided
            if payment_info.metadata and "private_key" in payment_info.metadata:
                private_key = PrivateKey(bytes.fromhex(payment_info.metadata["private_key"]))
                txn = txn.sign(private_key)
            
            # Broadcast transaction
            result = txn.broadcast()
            
            if result.get("result"):
                payment_info.transaction_id = result["txid"]
                payment_info.fee = 0.1  # Mock fee
            else:
                raise RuntimeError(f"USDT transfer failed: {result}")
                
        except Exception as e:
            logger.error(f"Error processing USDT transfer: {e}")
            raise
    
    async def _process_contract_payment(self, payment_info: PaymentInfo):
        """Process contract payment"""
        try:
            # This would integrate with specific contract calls
            # For now, simulate the process
            
            # Generate mock transaction ID
            payment_info.transaction_id = f"tx_{int(time.time())}_{hashlib.sha256(payment_info.payment_id.encode()).hexdigest()[:16]}"
            payment_info.fee = 0.1  # Mock fee
            
            # Simulate processing time
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error processing contract payment: {e}")
            raise
    
    async def _process_staking_payment(self, payment_info: PaymentInfo):
        """Process staking payment"""
        try:
            # This would integrate with the staking service
            # For now, simulate the process
            
            # Generate mock transaction ID
            payment_info.transaction_id = f"tx_{int(time.time())}_{hashlib.sha256(payment_info.payment_id.encode()).hexdigest()[:16]}"
            payment_info.fee = 0.1  # Mock fee
            
            # Simulate processing time
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error processing staking payment: {e}")
            raise
    
    async def _process_fee_payment(self, payment_info: PaymentInfo):
        """Process fee payment"""
        try:
            # This would handle fee payments
            # For now, simulate the process
            
            # Generate mock transaction ID
            payment_info.transaction_id = f"tx_{int(time.time())}_{hashlib.sha256(payment_info.payment_id.encode()).hexdigest()[:16]}"
            payment_info.fee = 0.0  # No fee for fee payments
            
            # Simulate processing time
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error processing fee payment: {e}")
            raise
    
    async def get_payment_status(self, request: PaymentStatusRequest) -> PaymentStatusResponse:
        """Get payment status"""
        try:
            if request.payment_id not in self.payments:
                raise ValueError("Payment not found")
            
            payment_info = self.payments[request.payment_id]
            
            return PaymentStatusResponse(
                payment_id=payment_info.payment_id,
                status=payment_info.status.value,
                transaction_id=payment_info.transaction_id,
                amount=payment_info.amount,
                currency=payment_info.currency,
                from_address=payment_info.from_address,
                to_address=payment_info.to_address,
                fee=payment_info.fee,
                created_at=payment_info.created_at.isoformat(),
                processed_at=payment_info.processed_at.isoformat() if payment_info.processed_at else None,
                completed_at=payment_info.completed_at.isoformat() if payment_info.completed_at else None,
                error_message=payment_info.error_message
            )
            
        except Exception as e:
            logger.error(f"Error getting payment status: {e}")
            raise
    
    async def list_payments(self, status: Optional[PaymentStatus] = None, limit: int = 100) -> List[PaymentResponse]:
        """List payments with optional status filter"""
        try:
            payments_list = []
            
            # Get payments based on status
            if status == PaymentStatus.PENDING:
                payments_dict = self.pending_payments
            elif status == PaymentStatus.PROCESSING:
                payments_dict = self.processing_payments
            elif status == PaymentStatus.COMPLETED:
                payments_dict = self.completed_payments
            elif status == PaymentStatus.FAILED:
                payments_dict = self.failed_payments
            else:
                payments_dict = self.payments
            
            # Sort by creation time (newest first)
            sorted_payments = sorted(payments_dict.items(), 
                                  key=lambda x: x[1].created_at, reverse=True)
            
            # Limit results
            limited_payments = sorted_payments[:limit]
            
            for payment_id, payment_info in limited_payments:
                payments_list.append(PaymentResponse(
                    payment_id=payment_info.payment_id,
                    transaction_id=payment_info.transaction_id,
                    status=payment_info.status.value,
                    amount=payment_info.amount,
                    currency=payment_info.currency,
                    from_address=payment_info.from_address,
                    to_address=payment_info.to_address,
                    fee=payment_info.fee,
                    created_at=payment_info.created_at.isoformat(),
                    processed_at=payment_info.processed_at.isoformat() if payment_info.processed_at else None,
                    completed_at=payment_info.completed_at.isoformat() if payment_info.completed_at else None,
                    error_message=payment_info.error_message
                ))
            
            return payments_list
            
        except Exception as e:
            logger.error(f"Error listing payments: {e}")
            return []
    
    async def _process_payments(self):
        """Process pending payments"""
        try:
            while True:
                # Process pending payments
                for payment_id, payment_info in list(self.pending_payments.items()):
                    try:
                        # Process payment
                        await self.process_payment(payment_id)
                        
                    except Exception as e:
                        logger.error(f"Error processing payment {payment_id}: {e}")
                
                # Wait before next check
                await asyncio.sleep(10)  # Check every 10 seconds
                
        except asyncio.CancelledError:
            logger.info("Payment processing cancelled")
        except Exception as e:
            logger.error(f"Error in payment processing: {e}")
    
    async def _monitor_payments(self):
        """Monitor payment status"""
        try:
            while True:
                # Check for stuck payments
                now = datetime.now()
                stuck_threshold = timedelta(hours=1)
                
                stuck_payments = []
                for payment_id, payment_info in self.processing_payments.items():
                    if (payment_info.processed_at and 
                        now - payment_info.processed_at > stuck_threshold):
                        stuck_payments.append(payment_id)
                
                # Mark stuck payments as failed
                for payment_id in stuck_payments:
                    payment_info = self.processing_payments[payment_id]
                    payment_info.status = PaymentStatus.FAILED
                    payment_info.error_message = "Payment processing timeout"
                    
                    # Move to failed
                    self.failed_payments[payment_id] = payment_info
                    del self.processing_payments[payment_id]
                    
                    logger.warning(f"Payment stuck and marked as failed: {payment_id}")
                
                # Save registry if there were stuck payments
                if stuck_payments:
                    await self._save_payments_registry()
                
                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
        except asyncio.CancelledError:
            logger.info("Payment monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in payment monitoring: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old data"""
        try:
            while True:
                cutoff_date = datetime.now() - timedelta(days=30)
                
                # Clean up old completed payments
                old_payments = []
                for payment_id, payment_info in self.completed_payments.items():
                    if payment_info.completed_at and payment_info.completed_at < cutoff_date:
                        old_payments.append(payment_id)
                
                for payment_id in old_payments:
                    del self.completed_payments[payment_id]
                    if payment_id in self.payments:
                        del self.payments[payment_id]
                
                if old_payments:
                    await self._save_payments_registry()
                    logger.info(f"Cleaned up {len(old_payments)} old payments")
                
                # Wait before next cleanup
                await asyncio.sleep(3600)  # Clean up every hour
                
        except asyncio.CancelledError:
            logger.info("Data cleanup cancelled")
        except Exception as e:
            logger.error(f"Error in data cleanup: {e}")
    
    async def _log_payment_event(self, payment_id: str, event_type: str, data: Dict[str, Any]):
        """Log payment event"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "payment_id": payment_id,
                "event_type": event_type,
                "data": data
            }
            
            log_file = self.logs_dir / f"payment_events_{datetime.now().strftime('%Y%m%d')}.log"
            async with aiofiles.open(log_file, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging payment event: {e}")
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        try:
            total_payments = len(self.payments)
            pending_payments = len(self.pending_payments)
            processing_payments = len(self.processing_payments)
            completed_payments = len(self.completed_payments)
            failed_payments = len(self.failed_payments)
            
            total_amount = sum(p.amount for p in self.payments.values())
            completed_amount = sum(p.amount for p in self.completed_payments.values())
            
            return {
                "total_payments": total_payments,
                "pending_payments": pending_payments,
                "processing_payments": processing_payments,
                "completed_payments": completed_payments,
                "failed_payments": failed_payments,
                "total_amount": total_amount,
                "completed_amount": completed_amount,
                "payment_status": {
                    status.value: len([p for p in self.payments.values() if p.status == status])
                    for status in PaymentStatus
                },
                "payment_types": {
                    payment_type.value: len([p for p in self.payments.values() if p.payment_type == payment_type])
                    for payment_type in PaymentType
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting service stats: {e}")
            return {"error": str(e)}

# Global instance
payment_gateway_service = PaymentGatewayService()

# Convenience functions for external use
async def create_payment(request: PaymentCreateRequest) -> PaymentResponse:
    """Create a new payment"""
    return await payment_gateway_service.create_payment(request)

async def process_payment(payment_id: str) -> PaymentResponse:
    """Process a payment"""
    return await payment_gateway_service.process_payment(payment_id)

async def get_payment_status(request: PaymentStatusRequest) -> PaymentStatusResponse:
    """Get payment status"""
    return await payment_gateway_service.get_payment_status(request)

async def list_payments(status: Optional[PaymentStatus] = None, limit: int = 100) -> List[PaymentResponse]:
    """List payments"""
    return await payment_gateway_service.list_payments(status, limit)

async def get_service_stats() -> Dict[str, Any]:
    """Get service statistics"""
    return await payment_gateway_service.get_service_stats()

if __name__ == "__main__":
    # Example usage
    async def main():
        try:
            # Create a payment
            payment_request = PaymentCreateRequest(
                from_address="TFromAddress1234567890123456789012345",
                to_address="TToAddress1234567890123456789012345",
                amount=100.0,
                currency="TRX",
                payment_type=PaymentType.TRX_TRANSFER,
                payment_method=PaymentMethod.WALLET,
                private_key=os.getenv("TRON_TEST_PRIVATE_KEY", ""),  # Use environment variable for test private key
                metadata={"description": "Test payment"}
            )
            
            payment = await create_payment(payment_request)
            print(f"Created payment: {payment}")
            
            # Process payment
            processed_payment = await process_payment(payment.payment_id)
            print(f"Processed payment: {processed_payment}")
            
            # Get payment status
            status_request = PaymentStatusRequest(payment_id=payment.payment_id)
            status = await get_payment_status(status_request)
            print(f"Payment status: {status}")
            
            # List payments
            payments = await list_payments(limit=10)
            print(f"Recent payments: {len(payments)}")
            
            # Get service stats
            stats = await get_service_stats()
            print(f"Service stats: {stats}")
            
        except Exception as e:
            print(f"Error: {e}")
    
    asyncio.run(main())
