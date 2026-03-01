"""
TRON Payout Router Service Module
Core payout routing logic and management
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class RouteType(str, Enum):
    """Supported route types"""
    V0 = "v0"
    KYC = "kyc"
    DIRECT = "direct"
    SMART = "smart"


class PayoutStatus(str, Enum):
    """Payout status"""
    PENDING = "pending"
    ROUTED = "routed"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PayoutRouterService:
    """TRON Payout Router Service"""
    
    def __init__(self):
        self.routes: Dict[str, Dict[str, Any]] = {}
        self.payouts: Dict[str, Dict[str, Any]] = {}
        self.batches: Dict[str, Dict[str, Any]] = {}
        self.metrics = {
            "total_routed": 0,
            "total_amount": 0.0,
            "successful_routes": 0,
            "failed_routes": 0,
            "average_route_time": 0.0,
        }
        self._initialize_routes()
    
    def _initialize_routes(self):
        """Initialize available routes"""
        self.routes = {
            RouteType.V0.value: {
                "name": "V0 Router",
                "status": "operational",
                "capacity": 1000,
                "active_payouts": 0,
                "success_rate": 0.995,
                "average_time_minutes": 5.2,
                "fee_percentage": 0.1,
            },
            RouteType.KYC.value: {
                "name": "KYC Router",
                "status": "operational",
                "capacity": 500,
                "active_payouts": 0,
                "success_rate": 0.988,
                "average_time_minutes": 7.1,
                "fee_percentage": 0.15,
            },
            RouteType.DIRECT.value: {
                "name": "Direct Router",
                "status": "operational",
                "capacity": 100,
                "active_payouts": 0,
                "success_rate": 0.972,
                "average_time_minutes": 3.5,
                "fee_percentage": 0.2,
            },
        }
    
    async def route_payout(
        self,
        payout_id: str,
        amount: float,
        recipient: str,
        priority: str = "normal",
        preferred_route: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Route a payout through optimal path"""
        try:
            logger.info(f"Routing payout {payout_id}: {amount} TRX to {recipient}")
            
            # Determine optimal route
            assigned_route = self._select_optimal_route(
                amount, priority, preferred_route
            )
            
            # Create payout record
            payout = {
                "payout_id": payout_id,
                "amount": amount,
                "recipient": recipient,
                "assigned_route": assigned_route,
                "status": PayoutStatus.ROUTED.value,
                "priority": priority,
                "created_at": datetime.utcnow().isoformat(),
                "route_assigned_at": datetime.utcnow().isoformat(),
                "estimated_completion": (
                    datetime.utcnow() 
                    + timedelta(minutes=self.routes[assigned_route]["average_time_minutes"])
                ).isoformat(),
            }
            
            self.payouts[payout_id] = payout
            
            # Update route metrics
            self.routes[assigned_route]["active_payouts"] += 1
            self.metrics["total_routed"] += 1
            self.metrics["total_amount"] += amount
            
            return {
                "payout_id": payout_id,
                "assigned_route": assigned_route,
                "status": "routed",
                "estimated_fee": self._calculate_fee(amount, assigned_route),
                "estimated_time_minutes": self.routes[assigned_route]["average_time_minutes"],
                "route_assigned_at": payout["route_assigned_at"],
            }
        except Exception as e:
            logger.error(f"Error routing payout: {e}")
            self.metrics["failed_routes"] += 1
            raise
    
    async def route_batch(
        self,
        payouts: List[Dict[str, Any]],
        strategy: str = "optimal"
    ) -> Dict[str, Any]:
        """Route a batch of payouts"""
        try:
            batch_id = str(uuid.uuid4())
            logger.info(f"Processing batch {batch_id} with {len(payouts)} payouts")
            
            routed_payouts = []
            failed_count = 0
            total_amount = 0.0
            
            for payout in payouts:
                try:
                    result = await self.route_payout(
                        payout_id=payout.get("payout_id"),
                        amount=payout.get("amount"),
                        recipient=payout.get("recipient"),
                        priority=payout.get("priority", "normal"),
                        preferred_route=payout.get("preferred_route"),
                    )
                    routed_payouts.append(result)
                    total_amount += payout.get("amount", 0)
                except Exception as e:
                    logger.error(f"Error routing payout in batch: {e}")
                    failed_count += 1
            
            batch = {
                "batch_id": batch_id,
                "total_payouts": len(payouts),
                "routed_payouts": len(routed_payouts),
                "failed_payouts": failed_count,
                "total_amount": total_amount,
                "strategy": strategy,
                "status": "processed",
                "created_at": datetime.utcnow().isoformat(),
            }
            
            self.batches[batch_id] = batch
            
            return batch
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            raise
    
    def _select_optimal_route(
        self,
        amount: float,
        priority: str,
        preferred_route: Optional[str]
    ) -> str:
        """Select optimal route for payout"""
        # If preferred route specified and available, use it
        if preferred_route and preferred_route in self.routes:
            route = self.routes[preferred_route]
            if (route["status"] == "operational" and 
                route["active_payouts"] < route["capacity"]):
                return preferred_route
        
        # For critical priority, prefer direct route
        if priority == "critical":
            if self._route_available(RouteType.DIRECT.value):
                return RouteType.DIRECT.value
        
        # Select based on amount and load balancing
        if amount > 50000:
            # Large amounts use V0 router
            if self._route_available(RouteType.V0.value):
                return RouteType.V0.value
        elif amount > 10000:
            # Medium amounts use KYC router
            if self._route_available(RouteType.KYC.value):
                return RouteType.KYC.value
        
        # Default to best available route
        available_routes = [
            route for route, info in self.routes.items()
            if self._route_available(route)
        ]
        
        if available_routes:
            return sorted(
                available_routes,
                key=lambda r: self.routes[r]["active_payouts"],
            )[0]
        
        return RouteType.V0.value
    
    def _route_available(self, route: str) -> bool:
        """Check if route is available"""
        if route not in self.routes:
            return False
        
        route_info = self.routes[route]
        return (
            route_info["status"] == "operational" and
            route_info["active_payouts"] < route_info["capacity"]
        )
    
    def _calculate_fee(self, amount: float, route: str) -> float:
        """Calculate fee for route"""
        if route in self.routes:
            fee_percentage = self.routes[route]["fee_percentage"] / 100
            return amount * fee_percentage
        return 0.0
    
    async def get_payout_status(self, payout_id: str) -> Dict[str, Any]:
        """Get payout status"""
        if payout_id not in self.payouts:
            raise ValueError(f"Payout {payout_id} not found")
        
        return self.payouts[payout_id]
    
    async def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """Get batch status"""
        if batch_id not in self.batches:
            raise ValueError(f"Batch {batch_id} not found")
        
        return self.batches[batch_id]
    
    async def get_route_health(self) -> Dict[str, Any]:
        """Get health status of all routes"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "routes": self.routes,
            "metrics": self.metrics,
        }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics"""
        total_payouts = len(self.payouts)
        completed = len([p for p in self.payouts.values() 
                        if p.get("status") == PayoutStatus.COMPLETED.value])
        
        return {
            "total_payouts": total_payouts,
            "completed_payouts": completed,
            "pending_payouts": total_payouts - completed,
            "total_amount_routed": self.metrics["total_amount"],
            "average_success_rate": sum(
                r["success_rate"] for r in self.routes.values()
            ) / len(self.routes) if self.routes else 0,
            "active_routes": len([r for r in self.routes.values() 
                                 if r["status"] == "operational"]),
        }
    
    async def complete_payout(self, payout_id: str, tx_hash: str) -> Dict[str, Any]:
        """Mark payout as completed"""
        if payout_id not in self.payouts:
            raise ValueError(f"Payout {payout_id} not found")
        
        payout = self.payouts[payout_id]
        payout["status"] = PayoutStatus.COMPLETED.value
        payout["transaction_hash"] = tx_hash
        payout["completed_at"] = datetime.utcnow().isoformat()
        
        # Update route metrics
        route = payout.get("assigned_route")
        if route in self.routes:
            self.routes[route]["active_payouts"] = max(
                0, self.routes[route]["active_payouts"] - 1
            )
            self.metrics["successful_routes"] += 1
        
        return payout
    
    async def cancel_payout(self, payout_id: str, reason: str) -> Dict[str, Any]:
        """Cancel a payout"""
        if payout_id not in self.payouts:
            raise ValueError(f"Payout {payout_id} not found")
        
        payout = self.payouts[payout_id]
        payout["status"] = PayoutStatus.CANCELLED.value
        payout["cancellation_reason"] = reason
        payout["cancelled_at"] = datetime.utcnow().isoformat()
        
        # Update route metrics
        route = payout.get("assigned_route")
        if route in self.routes:
            self.routes[route]["active_payouts"] = max(
                0, self.routes[route]["active_payouts"] - 1
            )
        
        return payout
