"""
TRON Payment Gateway Service Module
Payment processing, reconciliation, webhook management, and settlement operations
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid
import json
import httpx

logger = logging.getLogger(__name__)


class PaymentStatus(str, Enum):
    """Payment statuses"""
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


class SettlementFrequency(str, Enum):
    """Settlement frequency"""
    INSTANT = "instant"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


class PaymentGatewayService:
    """Payment Gateway Service"""
    
    def __init__(self):
        # Payment storage
        self.payments: Dict[str, Dict[str, Any]] = {}
        self.batches: Dict[str, Dict[str, Any]] = {}
        self.refunds: Dict[str, Dict[str, Any]] = {}
        self.webhooks: Dict[str, Dict[str, Any]] = {}
        self.settlements: Dict[str, Dict[str, Any]] = {}
        
        # Webhook event queue
        self.webhook_queue: List[Dict[str, Any]] = []
        
        # Configuration
        self.fees = {
            "low": 0.001,      # 0.1%
            "normal": 0.0015,  # 0.15%
            "high": 0.002,     # 0.2%
            "urgent": 0.003,   # 0.3%
        }
        
        self.settlement_config = {
            "frequency": SettlementFrequency.DAILY.value,
            "time_utc": "23:00",
            "threshold": 100000.0,  # Minimum amount to trigger settlement
            "retention_period_days": 30,
        }
        
        # Metrics
        self.metrics = {
            "total_payments": 0,
            "successful_payments": 0,
            "failed_payments": 0,
            "total_volume": 0.0,
            "total_fees": 0.0,
            "refunded_volume": 0.0,
            "batches_processed": 0,
            "avg_processing_time": 0,
        }
    
    async def create_payment(
        self,
        payer_address: str,
        payee_address: str,
        amount: float,
        payment_method: str = "payment_gateway",
        priority: str = "normal",
        reference_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new payment"""
        try:
            logger.info(f"Creating payment: {amount} USDT from {payer_address} to {payee_address}")
            
            # Validate addresses
            if not payer_address.startswith("T") or len(payer_address) != 34:
                raise ValueError(f"Invalid payer address: {payer_address}")
            if not payee_address.startswith("T") or len(payee_address) != 34:
                raise ValueError(f"Invalid payee address: {payee_address}")
            
            # Calculate fee
            fee_rate = self.fees.get(priority, 0.0015)
            fee = amount * fee_rate
            net_amount = amount - fee
            
            # Create payment record
            payment_id = f"pay_{uuid.uuid4().hex[:16]}"
            payment = {
                "payment_id": payment_id,
                "payer_address": payer_address,
                "payee_address": payee_address,
                "amount": amount,
                "fee": fee,
                "net_amount": net_amount,
                "payment_method": payment_method,
                "priority": priority,
                "reference_id": reference_id,
                "description": description,
                "status": PaymentStatus.PENDING.value,
                "transaction_id": None,
                "confirmations": 0,
                "created_at": datetime.utcnow().isoformat(),
                "started_at": None,
                "completed_at": None,
                "retry_count": 0,
            }
            
            self.payments[payment_id] = payment
            
            # Update metrics
            self.metrics["total_payments"] += 1
            self.metrics["total_volume"] += amount
            self.metrics["total_fees"] += fee
            
            logger.info(f"Payment {payment_id} created successfully")
            return payment
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            raise
    
    async def process_batch_payments(
        self,
        payments: List[Dict[str, Any]],
        batch_reference: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process multiple payments in batch"""
        try:
            logger.info(f"Processing batch of {len(payments)} payments")
            
            batch_id = f"batch_{uuid.uuid4().hex[:16]}"
            successful = 0
            failed = 0
            
            # Process each payment
            for payment_data in payments:
                try:
                    await self.create_payment(
                        payer_address=payment_data["payer_address"],
                        payee_address=payment_data["payee_address"],
                        amount=payment_data["amount"],
                        payment_method=payment_data.get("payment_method", "payment_gateway"),
                        priority=payment_data.get("priority", "normal"),
                        reference_id=payment_data.get("reference_id"),
                        description=payment_data.get("description"),
                    )
                    successful += 1
                except Exception as e:
                    logger.warning(f"Failed to process payment in batch: {e}")
                    failed += 1
            
            # Create batch record
            batch = {
                "batch_id": batch_id,
                "total_payments": len(payments),
                "successful": successful,
                "failed": failed,
                "status": "processing" if failed == 0 else "partial_failure",
                "batch_reference": batch_reference,
                "created_at": datetime.utcnow().isoformat(),
            }
            
            self.batches[batch_id] = batch
            self.metrics["batches_processed"] += 1
            
            logger.info(f"Batch {batch_id} processed: {successful} successful, {failed} failed")
            return batch
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            raise
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Get payment status"""
        try:
            if payment_id not in self.payments:
                raise ValueError(f"Payment {payment_id} not found")
            
            return self.payments[payment_id]
        except Exception as e:
            logger.error(f"Error getting payment status: {e}")
            raise
    
    async def reconcile_payment(
        self,
        payment_id: str,
        external_transaction_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reconcile payment with blockchain"""
        try:
            if payment_id not in self.payments:
                raise ValueError(f"Payment {payment_id} not found")
            
            payment = self.payments[payment_id]
            
            # Update payment with confirmation
            payment["status"] = PaymentStatus.CONFIRMED.value
            payment["transaction_id"] = external_transaction_id
            payment["confirmations"] = 5
            payment["completed_at"] = datetime.utcnow().isoformat()
            
            # Update metrics
            self.metrics["successful_payments"] += 1
            
            # Queue webhook event
            await self._queue_webhook_event(
                "payment.confirmed",
                payment_id,
                payment,
            )
            
            reconciliation_id = f"recon_{uuid.uuid4().hex[:16]}"
            reconciliation = {
                "reconciliation_id": reconciliation_id,
                "payment_id": payment_id,
                "status": "completed",
                "verified": True,
                "verified_at": datetime.utcnow().isoformat(),
                "notes": notes,
            }
            
            logger.info(f"Payment {payment_id} reconciled successfully")
            return reconciliation
        except Exception as e:
            logger.error(f"Error reconciling payment: {e}")
            raise
    
    async def refund_payment(
        self,
        payment_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Refund a payment"""
        try:
            if payment_id not in self.payments:
                raise ValueError(f"Payment {payment_id} not found")
            
            payment = self.payments[payment_id]
            
            # Create refund record
            refund_id = f"refund_{uuid.uuid4().hex[:16]}"
            refund = {
                "refund_id": refund_id,
                "payment_id": payment_id,
                "amount": payment["amount"],
                "fee": payment["fee"],
                "status": "initiated",
                "reason": reason,
                "created_at": datetime.utcnow().isoformat(),
                "completed_at": None,
            }
            
            self.refunds[refund_id] = refund
            
            # Update payment status
            payment["status"] = PaymentStatus.REFUNDED.value
            
            # Update metrics
            self.metrics["refunded_volume"] += payment["amount"]
            
            # Queue webhook event
            await self._queue_webhook_event(
                "payment.refunded",
                payment_id,
                payment,
            )
            
            logger.info(f"Refund {refund_id} initiated for payment {payment_id}")
            return refund
        except Exception as e:
            logger.error(f"Error refunding payment: {e}")
            raise
    
    async def register_webhook(
        self,
        url: str,
        events: List[str],
        headers: Optional[Dict[str, str]] = None,
        active: bool = True,
    ) -> Dict[str, Any]:
        """Register a webhook"""
        try:
            webhook_id = f"webhook_{uuid.uuid4().hex[:16]}"
            secret = uuid.uuid4().hex
            
            webhook = {
                "webhook_id": webhook_id,
                "url": url,
                "events": events,
                "headers": headers or {},
                "active": active,
                "secret": secret,
                "created_at": datetime.utcnow().isoformat(),
                "last_used": None,
                "failure_count": 0,
            }
            
            self.webhooks[webhook_id] = webhook
            logger.info(f"Webhook {webhook_id} registered: {url}")
            return webhook
        except Exception as e:
            logger.error(f"Error registering webhook: {e}")
            raise
    
    async def _queue_webhook_event(
        self,
        event: str,
        payment_id: str,
        payment_data: Dict[str, Any],
    ) -> None:
        """Queue webhook event for delivery"""
        try:
            event_data = {
                "event": event,
                "payment_id": payment_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": payment_data,
            }
            
            self.webhook_queue.append(event_data)
            logger.info(f"Webhook event queued: {event} for {payment_id}")
        except Exception as e:
            logger.error(f"Error queuing webhook event: {e}")
    
    async def get_analytics(self, period_days: int = 30) -> Dict[str, Any]:
        """Get payment analytics"""
        try:
            total_payments = self.metrics["total_payments"]
            successful = self.metrics["successful_payments"]
            failed = self.metrics["failed_payments"]
            
            success_rate = (successful / total_payments * 100) if total_payments > 0 else 0
            
            return {
                "period_days": period_days,
                "total_payments": total_payments,
                "successful_payments": successful,
                "failed_payments": failed,
                "success_rate_percent": success_rate,
                "total_volume": self.metrics["total_volume"],
                "total_fees": self.metrics["total_fees"],
                "refunded_volume": self.metrics["refunded_volume"],
                "avg_payment_size": (self.metrics["total_volume"] / total_payments) if total_payments > 0 else 0,
                "batches_processed": self.metrics["batches_processed"],
            }
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            raise
    
    async def get_settlement_info(self) -> Dict[str, Any]:
        """Get settlement information"""
        try:
            pending_amount = sum(
                p["amount"] for p in self.payments.values()
                if p["status"] == PaymentStatus.COMPLETED.value
            )
            
            last_settlement = None
            if self.settlements:
                last_settlement = max(
                    self.settlements.values(),
                    key=lambda x: x["created_at"]
                )
            
            return {
                "settlement_frequency": self.settlement_config["frequency"],
                "settlement_time_utc": self.settlement_config["time_utc"],
                "settlement_threshold": self.settlement_config["threshold"],
                "pending_settlement_amount": pending_amount,
                "last_settlement": last_settlement,
                "next_settlement": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            }
        except Exception as e:
            logger.error(f"Error getting settlement info: {e}")
            raise
    
    async def calculate_fees(
        self,
        amount: float,
        priority: str = "normal",
    ) -> Dict[str, Any]:
        """Calculate payment fees"""
        try:
            fee_rate = self.fees.get(priority, 0.0015)
            transaction_fee = amount * fee_rate
            
            return {
                "amount": amount,
                "priority": priority,
                "fee_rate_percent": fee_rate * 100,
                "transaction_fee": transaction_fee,
                "net_amount": amount - transaction_fee,
            }
        except Exception as e:
            logger.error(f"Error calculating fees: {e}")
            raise
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": self.metrics,
        }
