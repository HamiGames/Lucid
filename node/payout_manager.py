#!/usr/bin/env python3
"""
Lucid Node Management - Payout Manager
Handles payout processing with 10 USDT threshold
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from decimal import Decimal
import uuid

from .database_adapter import DatabaseAdapter
from .models import PayoutInfo, NodeInfo

logger = logging.getLogger(__name__)

# Payout Configuration
PAYOUT_THRESHOLD_USDT = float(os.getenv("PAYOUT_THRESHOLD_USDT", "10.0"))
PAYOUT_PROCESSING_FEE_PERCENT = float(os.getenv("PAYOUT_PROCESSING_FEE_PERCENT", "1.0"))
PAYOUT_MIN_AMOUNT_USDT = float(os.getenv("PAYOUT_MIN_AMOUNT_USDT", "1.0"))
PAYOUT_MAX_AMOUNT_USDT = float(os.getenv("PAYOUT_MAX_AMOUNT_USDT", "10000.0"))

class PayoutStatus:
    """Payout status constants"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PayoutManager:
    """
    Payout Manager for Node Management Service
    
    Handles:
    - Payout threshold validation (10 USDT minimum)
    - Payout processing and execution
    - Payout history and tracking
    - Fee calculation and deduction
    - Batch payout processing
    """
    
    def __init__(self, db_adapter: DatabaseAdapter, threshold_usdt: float = PAYOUT_THRESHOLD_USDT):
        self.db = db_adapter
        self.threshold_usdt = Decimal(str(threshold_usdt))
        self.processing_fee_percent = Decimal(str(PAYOUT_PROCESSING_FEE_PERCENT))
        self.min_amount = Decimal(str(PAYOUT_MIN_AMOUNT_USDT))
        self.max_amount = Decimal(str(PAYOUT_MAX_AMOUNT_USDT))
        
        # Payout tracking
        self.pending_payouts: Dict[str, PayoutInfo] = {}
        self.processing_payouts: Dict[str, PayoutInfo] = {}
        
        logger.info(f"Payout Manager initialized with threshold: {self.threshold_usdt} USDT")
    
    async def check_payout_eligibility(self, node_id: str, amount_usdt: float) -> Dict[str, Any]:
        """
        Check if a node is eligible for payout
        
        Args:
            node_id: Node identifier
            amount_usdt: Payout amount in USDT
            
        Returns:
            Dictionary with eligibility status and details
        """
        try:
            amount = Decimal(str(amount_usdt))
            
            # Check minimum amount
            if amount < self.min_amount:
                return {
                    "eligible": False,
                    "reason": f"Amount {amount} USDT below minimum {self.min_amount} USDT",
                    "threshold_met": False
                }
            
            # Check maximum amount
            if amount > self.max_amount:
                return {
                    "eligible": False,
                    "reason": f"Amount {amount} USDT exceeds maximum {self.max_amount} USDT",
                    "threshold_met": False
                }
            
            # Check threshold
            threshold_met = amount >= self.threshold_usdt
            
            # Calculate fees
            fee_amount = amount * (self.processing_fee_percent / Decimal("100"))
            net_amount = amount - fee_amount
            
            return {
                "eligible": True,
                "threshold_met": threshold_met,
                "amount_usdt": float(amount),
                "fee_usdt": float(fee_amount),
                "net_amount_usdt": float(net_amount),
                "fee_percent": float(self.processing_fee_percent)
            }
            
        except Exception as e:
            logger.error(f"Error checking payout eligibility for node {node_id}: {e}")
            return {
                "eligible": False,
                "reason": f"Error: {e}",
                "threshold_met": False
            }
    
    async def create_payout(self, node_id: str, amount_usdt: float, 
                          payout_address: str, description: str = "") -> Optional[str]:
        """
        Create a new payout request
        
        Args:
            node_id: Node identifier
            amount_usdt: Payout amount in USDT
            payout_address: Destination address for payout
            description: Optional description
            
        Returns:
            Payout ID if successful, None otherwise
        """
        try:
            # Check eligibility
            eligibility = await self.check_payout_eligibility(node_id, amount_usdt)
            if not eligibility["eligible"]:
                logger.warning(f"Node {node_id} not eligible for payout: {eligibility['reason']}")
                return None
            
            # Generate payout ID
            payout_id = str(uuid.uuid4())
            
            # Calculate amounts
            amount = Decimal(str(amount_usdt))
            fee_amount = amount * (self.processing_fee_percent / Decimal("100"))
            net_amount = amount - fee_amount
            
            # Create payout info
            payout = PayoutInfo(
                payout_id=payout_id,
                node_id=node_id,
                amount_usdt=float(amount),
                fee_usdt=float(fee_amount),
                net_amount_usdt=float(net_amount),
                payout_address=payout_address,
                status=PayoutStatus.PENDING,
                description=description,
                created_at=datetime.now(timezone.utc),
                processed_at=None,
                transaction_id=None
            )
            
            # Store payout
            self.pending_payouts[payout_id] = payout
            await self._store_payout(payout)
            
            logger.info(f"Payout created: {payout_id} for node {node_id}, amount: {amount} USDT")
            return payout_id
            
        except Exception as e:
            logger.error(f"Error creating payout for node {node_id}: {e}")
            return None
    
    async def process_payout(self, payout_id: str) -> bool:
        """
        Process a specific payout
        
        Args:
            payout_id: Payout identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get payout
            payout = await self.get_payout(payout_id)
            if not payout:
                logger.error(f"Payout {payout_id} not found")
                return False
            
            if payout.status != PayoutStatus.PENDING:
                logger.warning(f"Payout {payout_id} is not pending (status: {payout.status})")
                return False
            
            # Move to processing
            payout.status = PayoutStatus.PROCESSING
            payout.processed_at = datetime.now(timezone.utc)
            
            # Remove from pending, add to processing
            if payout_id in self.pending_payouts:
                del self.pending_payouts[payout_id]
            self.processing_payouts[payout_id] = payout
            
            # Update database
            await self._update_payout(payout)
            
            # Execute payout (simplified)
            success = await self._execute_payout(payout)
            
            if success:
                payout.status = PayoutStatus.COMPLETED
                payout.transaction_id = f"tx_{payout_id}_{int(datetime.now().timestamp())}"
                logger.info(f"Payout {payout_id} completed successfully")
            else:
                payout.status = PayoutStatus.FAILED
                logger.error(f"Payout {payout_id} failed")
            
            # Remove from processing
            if payout_id in self.processing_payouts:
                del self.processing_payouts[payout_id]
            
            # Update database
            await self._update_payout(payout)
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing payout {payout_id}: {e}")
            return False
    
    async def process_pending_payouts(self) -> Dict[str, Any]:
        """
        Process all pending payouts
        
        Returns:
            Dictionary with processing results
        """
        try:
            logger.info("Processing pending payouts")
            
            # Get all pending payouts
            pending_payouts = list(self.pending_payouts.values())
            if not pending_payouts:
                logger.info("No pending payouts to process")
                return {"success": True, "processed": 0, "results": []}
            
            results = []
            successful = 0
            failed = 0
            
            for payout in pending_payouts:
                try:
                    success = await self.process_payout(payout.payout_id)
                    if success:
                        results.append({
                            "payout_id": payout.payout_id,
                            "node_id": payout.node_id,
                            "status": "success",
                            "amount": payout.amount_usdt
                        })
                        successful += 1
                    else:
                        results.append({
                            "payout_id": payout.payout_id,
                            "node_id": payout.node_id,
                            "status": "failed",
                            "error": "Payout processing failed"
                        })
                        failed += 1
                except Exception as e:
                    logger.error(f"Error processing payout {payout.payout_id}: {e}")
                    results.append({
                        "payout_id": payout.payout_id,
                        "node_id": payout.node_id,
                        "status": "error",
                        "error": str(e)
                    })
                    failed += 1
            
            logger.info(f"Payout processing completed: {successful} successful, {failed} failed")
            return {
                "success": True,
                "processed": len(pending_payouts),
                "successful": successful,
                "failed": failed,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error in process_pending_payouts: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_payout(self, payout_id: str) -> Optional[PayoutInfo]:
        """
        Get payout information
        
        Args:
            payout_id: Payout identifier
            
        Returns:
            PayoutInfo object if found, None otherwise
        """
        try:
            # Check pending payouts
            if payout_id in self.pending_payouts:
                return self.pending_payouts[payout_id]
            
            # Check processing payouts
            if payout_id in self.processing_payouts:
                return self.processing_payouts[payout_id]
            
            # Load from database
            return await self._load_payout(payout_id)
            
        except Exception as e:
            logger.error(f"Error getting payout {payout_id}: {e}")
            return None
    
    async def list_payouts(self, node_id: Optional[str] = None, 
                          status: Optional[str] = None) -> List[PayoutInfo]:
        """
        List payouts with optional filtering
        
        Args:
            node_id: Filter by node ID
            status: Filter by status
            
        Returns:
            List of PayoutInfo objects
        """
        try:
            # Get all payouts from memory and database
            all_payouts = []
            
            # Add pending payouts
            all_payouts.extend(self.pending_payouts.values())
            
            # Add processing payouts
            all_payouts.extend(self.processing_payouts.values())
            
            # Load from database (simplified)
            # In a real implementation, this would query the database
            
            # Apply filters
            if node_id:
                all_payouts = [p for p in all_payouts if p.node_id == node_id]
            
            if status:
                all_payouts = [p for p in all_payouts if p.status == status]
            
            # Sort by creation time (newest first)
            all_payouts.sort(key=lambda p: p.created_at, reverse=True)
            
            return all_payouts
            
        except Exception as e:
            logger.error(f"Error listing payouts: {e}")
            return []
    
    async def cancel_payout(self, payout_id: str) -> bool:
        """
        Cancel a pending payout
        
        Args:
            payout_id: Payout identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            payout = await self.get_payout(payout_id)
            if not payout:
                logger.error(f"Payout {payout_id} not found")
                return False
            
            if payout.status != PayoutStatus.PENDING:
                logger.warning(f"Cannot cancel payout {payout_id} with status {payout.status}")
                return False
            
            # Cancel payout
            payout.status = PayoutStatus.CANCELLED
            
            # Remove from pending
            if payout_id in self.pending_payouts:
                del self.pending_payouts[payout_id]
            
            # Update database
            await self._update_payout(payout)
            
            logger.info(f"Payout {payout_id} cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling payout {payout_id}: {e}")
            return False
    
    async def get_payout_statistics(self) -> Dict[str, Any]:
        """
        Get payout statistics
        
        Returns:
            Dictionary with payout statistics
        """
        try:
            # Get all payouts
            all_payouts = await self.list_payouts()
            
            # Calculate statistics
            total_payouts = len(all_payouts)
            total_amount = sum(p.amount_usdt for p in all_payouts)
            total_fees = sum(p.fee_usdt for p in all_payouts)
            total_net = sum(p.net_amount_usdt for p in all_payouts)
            
            # Status breakdown
            status_counts = {}
            for payout in all_payouts:
                status_counts[payout.status] = status_counts.get(payout.status, 0) + 1
            
            # Recent payouts (last 24 hours)
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            recent_payouts = [p for p in all_payouts if p.created_at > recent_cutoff]
            
            return {
                "total_payouts": total_payouts,
                "total_amount_usdt": total_amount,
                "total_fees_usdt": total_fees,
                "total_net_usdt": total_net,
                "status_breakdown": status_counts,
                "recent_payouts_24h": len(recent_payouts),
                "threshold_usdt": float(self.threshold_usdt),
                "processing_fee_percent": float(self.processing_fee_percent)
            }
            
        except Exception as e:
            logger.error(f"Error getting payout statistics: {e}")
            return {}
    
    async def _execute_payout(self, payout: PayoutInfo) -> bool:
        """
        Execute the actual payout transaction
        
        Args:
            payout: Payout information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # This would integrate with the actual payment system
            # For now, simulate successful execution
            logger.info(f"Executing payout {payout.payout_id}: {payout.net_amount_usdt} USDT to {payout.payout_address}")
            
            # Simulate processing time
            await asyncio.sleep(1)
            
            # In a real implementation, this would:
            # 1. Validate the payout address
            # 2. Check available balance
            # 3. Execute the transaction via TRON network
            # 4. Wait for confirmation
            # 5. Update transaction status
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing payout {payout.payout_id}: {e}")
            return False
    
    async def _store_payout(self, payout: PayoutInfo):
        """Store payout in database"""
        try:
            # This would store the payout in the database
            logger.info(f"Storing payout {payout.payout_id}")
        except Exception as e:
            logger.error(f"Error storing payout: {e}")
    
    async def _update_payout(self, payout: PayoutInfo):
        """Update payout in database"""
        try:
            # This would update the payout in the database
            logger.info(f"Updating payout {payout.payout_id}")
        except Exception as e:
            logger.error(f"Error updating payout: {e}")
    
    async def _load_payout(self, payout_id: str) -> Optional[PayoutInfo]:
        """Load payout from database"""
        try:
            # This would load the payout from the database
            # For now, return None
            return None
        except Exception as e:
            logger.error(f"Error loading payout {payout_id}: {e}")
            return None
