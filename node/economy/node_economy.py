# Path: node/economy/node_economy.py
# Lucid RDP Node Economy - Economic management for node operators
# Based on LUCID-STRICT requirements per Spec-1c

from __future__ import annotations

import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import json
import hashlib

# Import from reorganized structure
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "payment-systems"))
from tron_node.tron_client import TronNodeClient
from blockchain.core.blockchain_engine import PayoutRouter
# Note: payout_governance module not found in payment-systems, may need to be created or imported differently
# from payment_systems.governance.payout_governance import PayoutGovernance

logger = logging.getLogger(__name__)

# Economic Constants
PAYOUT_THRESHOLD_USDT = float(os.getenv("PAYOUT_THRESHOLD_USDT", "10.0"))  # $10 minimum
PAYOUT_FREQUENCY_HOURS = int(os.getenv("PAYOUT_FREQUENCY_HOURS", "24"))  # Daily
COMMISSION_RATE = float(os.getenv("COMMISSION_RATE", "0.05"))  # 5% platform fee
TAX_RATE = float(os.getenv("TAX_RATE", "0.0"))  # Node operator tax rate
PERFORMANCE_BONUS_RATE = float(os.getenv("PERFORMANCE_BONUS_RATE", "0.02"))  # 2% performance bonus


class EconomicStatus(Enum):
    """Economic status of node"""
    EARNING = "earning"
    PAYOUT_PENDING = "payout_pending"
    PAYOUT_PROCESSING = "payout_processing"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"


class PayoutStatus(Enum):
    """Payout status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RevenueMetrics:
    """Revenue metrics for node"""
    sessions_completed: int
    data_transferred_gb: float
    uptime_hours: float
    gross_revenue_usdt: float
    commission_usdt: float
    net_revenue_usdt: float
    performance_bonus_usdt: float
    tax_withheld_usdt: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sessions_completed": self.sessions_completed,
            "data_transferred_gb": self.data_transferred_gb,
            "uptime_hours": self.uptime_hours,
            "gross_revenue_usdt": self.gross_revenue_usdt,
            "commission_usdt": self.commission_usdt,
            "net_revenue_usdt": self.net_revenue_usdt,
            "performance_bonus_usdt": self.performance_bonus_usdt,
            "tax_withheld_usdt": self.tax_withheld_usdt,
            "timestamp": datetime.now(timezone.utc)
        }


@dataclass
class PayoutRecord:
    """Payout record"""
    payout_id: str
    node_address: str
    amount_usdt: float
    tron_txid: Optional[str]
    status: PayoutStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None
    revenue_period_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    revenue_period_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.payout_id,
            "node_address": self.node_address,
            "amount_usdt": self.amount_usdt,
            "tron_txid": self.tron_txid,
            "status": self.status.value,
            "created_at": self.created_at,
            "processed_at": self.processed_at,
            "revenue_period_start": self.revenue_period_start,
            "revenue_period_end": self.revenue_period_end
        }


class NodeEconomy:
    """
    Node economy management for Lucid RDP.
    
    Handles:
    - Revenue tracking and calculation
    - Payout processing and scheduling
    - Performance bonuses and penalties
    - Tax handling and compliance
    - Economic reporting and analytics
    """
    
    def __init__(self, node_address: str, private_key: str):
        self.node_address = node_address
        self.private_key = private_key
        self.node_id = hashlib.sha256(node_address.encode()).hexdigest()[:16]
        
        # Core components
        self.tron_client = TronNodeSystem("mainnet")
        self.payout_router = PayoutRouter()
        self.payout_governance = PayoutGovernance()
        
        # Economic state
        self.status = EconomicStatus.INACTIVE
        self.current_balance_usdt = 0.0
        self.pending_revenue_usdt = 0.0
        
        # Revenue tracking
        self.revenue_metrics: Optional[RevenueMetrics] = None
        self.last_metrics_update: Optional[datetime] = None
        
        # Session tracking
        self.completed_sessions: List[Dict[str, Any]] = []
        self.revenue_transactions: List[Dict[str, Any]] = []
        
        # Payout management
        self.payout_history: List[PayoutRecord] = []
        self.last_payout_time: Optional[datetime] = None
        self.next_payout_time: Optional[datetime] = None
        
        # Performance tracking
        self.uptime_start: Optional[datetime] = None
        self.downtime_events: List[Dict[str, Any]] = []
        
        logger.info(f"Node economy initialized: {self.node_id} ({node_address})")
    
    async def start(self):
        """Start economy management"""
        try:
            logger.info(f"Starting node economy {self.node_id}...")
            
            # Initialize components
            await self.payout_governance.initialize()
            
            # Load previous state
            await self._load_economic_state()
            
            # Start economic processes
            asyncio.create_task(self._monitor_payouts())
            asyncio.create_task(self._update_metrics())
            asyncio.create_task(self._track_uptime())
            
            self.status = EconomicStatus.EARNING
            self.uptime_start = datetime.now(timezone.utc)
            
            logger.info(f"Node economy {self.node_id} started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start node economy: {e}")
            self.status = EconomicStatus.INACTIVE
            raise
    
    async def stop(self):
        """Stop economy management"""
        try:
            logger.info(f"Stopping node economy {self.node_id}...")
            
            self.status = EconomicStatus.INACTIVE
            
            # Process pending payouts if any
            if self.pending_revenue_usdt >= PAYOUT_THRESHOLD_USDT:
                await self.process_payout()
            
            # Save economic state
            await self._save_economic_state()
            
            logger.info(f"Node economy {self.node_id} stopped")
            
        except Exception as e:
            logger.error(f"Error stopping node economy: {e}")
    
    async def record_session_revenue(self, session_data: Dict[str, Any]) -> bool:
        """
        Record revenue from completed session.
        
        Args:
            session_data: Session completion data
            
        Returns:
            True if revenue recorded successfully
        """
        try:
            session_id = session_data.get("session_id")
            revenue_usdt = float(session_data.get("cost_usdt", 0))
            data_gb = float(session_data.get("data_transferred_gb", 0))
            duration_hours = float(session_data.get("duration_hours", 0))
            
            if revenue_usdt <= 0:
                logger.warning(f"No revenue for session: {session_id}")
                return False
            
            # Calculate commission
            commission = revenue_usdt * COMMISSION_RATE
            net_revenue = revenue_usdt - commission
            
            # Record transaction
            revenue_tx = {
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc),
                "gross_revenue_usdt": revenue_usdt,
                "commission_usdt": commission,
                "net_revenue_usdt": net_revenue,
                "data_transferred_gb": data_gb,
                "duration_hours": duration_hours
            }
            
            self.revenue_transactions.append(revenue_tx)
            self.completed_sessions.append(session_data)
            
            # Update balances
            self.pending_revenue_usdt += net_revenue
            
            # Check payout threshold
            if self.pending_revenue_usdt >= PAYOUT_THRESHOLD_USDT:
                self.status = EconomicStatus.PAYOUT_PENDING
                
                # Schedule payout if time is right
                now = datetime.now(timezone.utc)
                if (not self.last_payout_time or 
                    (now - self.last_payout_time) >= timedelta(hours=PAYOUT_FREQUENCY_HOURS)):
                    asyncio.create_task(self.process_payout())
            
            logger.info(f"Revenue recorded: {net_revenue} USDT from session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record session revenue: {e}")
            return False
    
    async def process_payout(self) -> Optional[str]:
        """
        Process payout to node operator.
        
        Returns:
            Payout ID if successful
        """
        try:
            if self.pending_revenue_usdt < PAYOUT_THRESHOLD_USDT:
                logger.info(f"Payout amount below threshold: {self.pending_revenue_usdt}")
                return None
            
            if self.status == EconomicStatus.PAYOUT_PROCESSING:
                logger.warning("Payout already in progress")
                return None
            
            self.status = EconomicStatus.PAYOUT_PROCESSING
            
            # Calculate final payout amount
            base_payout = self.pending_revenue_usdt
            
            # Apply performance bonus
            performance_score = await self._calculate_performance_score()
            performance_bonus = 0.0
            
            if performance_score > 0.8:  # 80% performance threshold
                performance_bonus = base_payout * PERFORMANCE_BONUS_RATE
            
            # Apply tax withholding
            tax_amount = (base_payout + performance_bonus) * TAX_RATE
            
            final_payout = base_payout + performance_bonus - tax_amount
            
            # Create payout record
            payout_id = f"payout_{self.node_id}_{int(datetime.now(timezone.utc).timestamp())}"
            
            payout_record = PayoutRecord(
                payout_id=payout_id,
                node_address=self.node_address,
                amount_usdt=final_payout,
                tron_txid=None,
                status=PayoutStatus.PENDING,
                revenue_period_start=self.last_payout_time or datetime.now(timezone.utc) - timedelta(days=30),
                revenue_period_end=datetime.now(timezone.utc)
            )
            
            # Process payout via governance
            payout_result = await self.payout_governance.process_node_payout(
                node_address=self.node_address,
                amount_usdt=final_payout,
                payout_id=payout_id,
                performance_score=performance_score
            )
            
            if payout_result and payout_result.get("success"):
                payout_record.tron_txid = payout_result.get("tron_txid")
                payout_record.status = PayoutStatus.PROCESSING
                payout_record.processed_at = datetime.now(timezone.utc)
                
                # Update state
                self.payout_history.append(payout_record)
                self.pending_revenue_usdt = 0.0
                self.last_payout_time = datetime.now(timezone.utc)
                self.next_payout_time = self.last_payout_time + timedelta(hours=PAYOUT_FREQUENCY_HOURS)
                
                # Monitor payout completion
                asyncio.create_task(self._monitor_payout_completion(payout_id))
                
                logger.info(f"Payout processed: {final_payout} USDT ({payout_id})")
                return payout_id
            else:
                payout_record.status = PayoutStatus.FAILED
                self.payout_history.append(payout_record)
                logger.error(f"Payout failed: {payout_result}")
                return None
                
        except Exception as e:
            logger.error(f"Payout processing failed: {e}")
            return None
        finally:
            if self.status == EconomicStatus.PAYOUT_PROCESSING:
                self.status = EconomicStatus.EARNING
    
    async def get_economic_status(self) -> Dict[str, Any]:
        """Get economic status and metrics"""
        try:
            # Update metrics
            await self._calculate_revenue_metrics()
            
            # Calculate projected earnings
            daily_avg = self._calculate_daily_average_revenue()
            projected_monthly = daily_avg * 30
            
            # Get performance score
            performance_score = await self._calculate_performance_score()
            
            return {
                "node_id": self.node_id,
                "node_address": self.node_address,
                "status": self.status.value,
                "current_balance_usdt": self.current_balance_usdt,
                "pending_revenue_usdt": self.pending_revenue_usdt,
                "payout_threshold_usdt": PAYOUT_THRESHOLD_USDT,
                "last_payout_time": self.last_payout_time,
                "next_payout_time": self.next_payout_time,
                "revenue_metrics": self.revenue_metrics.to_dict() if self.revenue_metrics else None,
                "performance_score": performance_score,
                "projected_monthly_usdt": projected_monthly,
                "payout_history_count": len(self.payout_history),
                "last_updated": datetime.now(timezone.utc)
            }
            
        except Exception as e:
            logger.error(f"Failed to get economic status: {e}")
            return {"error": str(e)}
    
    async def get_revenue_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get revenue history"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            recent_transactions = [
                tx for tx in self.revenue_transactions
                if tx["timestamp"] >= cutoff_date
            ]
            
            return recent_transactions
            
        except Exception as e:
            logger.error(f"Failed to get revenue history: {e}")
            return []
    
    async def get_payout_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get payout history"""
        try:
            # Sort by creation date (newest first)
            sorted_payouts = sorted(
                self.payout_history,
                key=lambda p: p.created_at,
                reverse=True
            )
            
            return [payout.to_dict() for payout in sorted_payouts[:limit]]
            
        except Exception as e:
            logger.error(f"Failed to get payout history: {e}")
            return []
    
    def _calculate_daily_average_revenue(self) -> float:
        """Calculate daily average revenue"""
        try:
            if not self.revenue_transactions:
                return 0.0
            
            # Get last 30 days of transactions
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
            recent_transactions = [
                tx for tx in self.revenue_transactions
                if tx["timestamp"] >= cutoff_date
            ]
            
            if not recent_transactions:
                return 0.0
            
            total_revenue = sum(tx["net_revenue_usdt"] for tx in recent_transactions)
            days_active = (datetime.now(timezone.utc) - cutoff_date).days
            
            return total_revenue / max(days_active, 1)
            
        except Exception as e:
            logger.error(f"Failed to calculate daily average: {e}")
            return 0.0
    
    async def _calculate_performance_score(self) -> float:
        """Calculate node performance score"""
        try:
            if not self.uptime_start:
                return 0.0
            
            now = datetime.now(timezone.utc)
            total_time = (now - self.uptime_start).total_seconds()
            
            if total_time <= 0:
                return 0.0
            
            # Calculate downtime
            total_downtime = sum(
                (event.get("end_time", now) - event["start_time"]).total_seconds()
                for event in self.downtime_events
            )
            
            # Calculate uptime percentage
            uptime_percentage = max(0, (total_time - total_downtime) / total_time)
            
            # Factor in session completion rate
            completed_sessions = len(self.completed_sessions)
            completion_score = min(completed_sessions / 100, 1.0)  # Up to 100 sessions for full score
            
            # Combined performance score
            performance_score = (uptime_percentage * 0.7) + (completion_score * 0.3)
            
            return min(performance_score, 1.0)
            
        except Exception as e:
            logger.error(f"Failed to calculate performance score: {e}")
            return 0.0
    
    async def _calculate_revenue_metrics(self):
        """Calculate revenue metrics"""
        try:
            if not self.revenue_transactions:
                self.revenue_metrics = RevenueMetrics(
                    sessions_completed=0,
                    data_transferred_gb=0.0,
                    uptime_hours=0.0,
                    gross_revenue_usdt=0.0,
                    commission_usdt=0.0,
                    net_revenue_usdt=0.0,
                    performance_bonus_usdt=0.0,
                    tax_withheld_usdt=0.0
                )
                return
            
            # Calculate totals
            sessions_completed = len(self.completed_sessions)
            data_transferred_gb = sum(tx["data_transferred_gb"] for tx in self.revenue_transactions)
            gross_revenue_usdt = sum(tx["gross_revenue_usdt"] for tx in self.revenue_transactions)
            commission_usdt = sum(tx["commission_usdt"] for tx in self.revenue_transactions)
            net_revenue_usdt = sum(tx["net_revenue_usdt"] for tx in self.revenue_transactions)
            
            # Calculate uptime
            uptime_hours = 0.0
            if self.uptime_start:
                uptime_hours = (datetime.now(timezone.utc) - self.uptime_start).total_seconds() / 3600
            
            # Calculate performance bonus earned
            performance_bonus_usdt = net_revenue_usdt * PERFORMANCE_BONUS_RATE
            
            # Calculate tax withheld
            tax_withheld_usdt = (net_revenue_usdt + performance_bonus_usdt) * TAX_RATE
            
            self.revenue_metrics = RevenueMetrics(
                sessions_completed=sessions_completed,
                data_transferred_gb=data_transferred_gb,
                uptime_hours=uptime_hours,
                gross_revenue_usdt=gross_revenue_usdt,
                commission_usdt=commission_usdt,
                net_revenue_usdt=net_revenue_usdt,
                performance_bonus_usdt=performance_bonus_usdt,
                tax_withheld_usdt=tax_withheld_usdt
            )
            
            self.last_metrics_update = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Failed to calculate revenue metrics: {e}")
    
    async def _monitor_payouts(self):
        """Monitor payout schedule and processing"""
        try:
            while self.status != EconomicStatus.INACTIVE:
                now = datetime.now(timezone.utc)
                
                # Check for scheduled payouts
                if (self.status == EconomicStatus.PAYOUT_PENDING and
                    self.pending_revenue_usdt >= PAYOUT_THRESHOLD_USDT and
                    (not self.last_payout_time or 
                     (now - self.last_payout_time) >= timedelta(hours=PAYOUT_FREQUENCY_HOURS))):
                    
                    await self.process_payout()
                
                await asyncio.sleep(3600)  # Check every hour
                
        except Exception as e:
            logger.error(f"Payout monitoring failed: {e}")
    
    async def _monitor_payout_completion(self, payout_id: str):
        """Monitor payout completion status"""
        try:
            payout_record = None
            for payout in self.payout_history:
                if payout.payout_id == payout_id:
                    payout_record = payout
                    break
            
            if not payout_record or not payout_record.tron_txid:
                return
            
            # Monitor transaction status
            max_polls = 60  # 5 minutes with 5-second intervals
            poll_count = 0
            
            while poll_count < max_polls:
                status = await self.tron_client.get_transaction_status(payout_record.tron_txid)
                
                if status == "confirmed":
                    payout_record.status = PayoutStatus.COMPLETED
                    logger.info(f"Payout completed: {payout_id}")
                    break
                elif status == "failed":
                    payout_record.status = PayoutStatus.FAILED
                    logger.error(f"Payout failed: {payout_id}")
                    break
                
                await asyncio.sleep(5)
                poll_count += 1
            
            # If still processing after timeout
            if payout_record.status == PayoutStatus.PROCESSING:
                logger.warning(f"Payout monitoring timeout: {payout_id}")
            
        except Exception as e:
            logger.error(f"Payout completion monitoring failed: {e}")
    
    async def _update_metrics(self):
        """Update economic metrics"""
        try:
            while self.status != EconomicStatus.INACTIVE:
                await self._calculate_revenue_metrics()
                await asyncio.sleep(600)  # Update every 10 minutes
                
        except Exception as e:
            logger.error(f"Metrics update failed: {e}")
    
    async def _track_uptime(self):
        """Track node uptime"""
        try:
            while self.status != EconomicStatus.INACTIVE:
                # This would integrate with actual node monitoring
                # For now, just maintain uptime start time
                await asyncio.sleep(60)  # Check every minute
                
        except Exception as e:
            logger.error(f"Uptime tracking failed: {e}")
    
    async def _load_economic_state(self):
        """Load economic state from storage"""
        try:
            # This would load from persistent storage
            # For now, initialize with default values
            logger.info("Economic state loaded")
            
        except Exception as e:
            logger.error(f"Failed to load economic state: {e}")
    
    async def _save_economic_state(self):
        """Save economic state to storage"""
        try:
            # This would save to persistent storage
            # For now, just log
            logger.info("Economic state saved")
            
        except Exception as e:
            logger.error(f"Failed to save economic state: {e}")


# Global node economy instance
_node_economy: Optional[NodeEconomy] = None


def get_node_economy() -> Optional[NodeEconomy]:
    """Get global node economy instance"""
    global _node_economy
    return _node_economy


def create_node_economy(node_address: str, private_key: str) -> NodeEconomy:
    """Create node economy instance"""
    global _node_economy
    _node_economy = NodeEconomy(node_address, private_key)
    return _node_economy


async def cleanup_node_economy():
    """Cleanup node economy"""
    global _node_economy
    if _node_economy:
        await _node_economy.stop()
        _node_economy = None


if __name__ == "__main__":
    # Test node economy
    async def test_node_economy():
        print("Testing Lucid Node Economy...")
        
        # Test with sample TRON address
        test_address = "TTestNodeAddress123456789012345"
        test_key = "0123456789abcdef" * 4  # 64 char hex
        
        economy = create_node_economy(test_address, test_key)
        
        try:
            await economy.start()
            
            # Get economic status
            status = await economy.get_economic_status()
            print(f"Economic status: {status}")
            
            # Test session revenue recording
            session_data = {
                "session_id": "test_session_123",
                "cost_usdt": 0.5,
                "data_transferred_gb": 2.0,
                "duration_hours": 1.0
            }
            
            success = await economy.record_session_revenue(session_data)
            print(f"Revenue recorded: {success}")
            
            # Get updated status
            status = await economy.get_economic_status()
            print(f"Updated status: {status}")
            
            # Get revenue history
            history = await economy.get_revenue_history()
            print(f"Revenue history: {len(history)} transactions")
            
            # Wait a bit
            await asyncio.sleep(2)
            
        finally:
            await economy.stop()
        
        print("Test completed")
    
    asyncio.run(test_node_economy())