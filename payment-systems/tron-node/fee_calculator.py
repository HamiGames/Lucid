"""
LUCID Payment Systems - TRON Fee Calculator
Comprehensive TRON fee estimation and optimization system
Distroless container: pickme/lucid:payment-systems:latest
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pydantic import BaseModel, Field

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_settings
from .tron_client import TronService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FeeType(str, Enum):
    """TRON fee types"""
    BANDWIDTH = "bandwidth"         # Bandwidth consumption
    ENERGY = "energy"               # Energy consumption
    TRX = "trx"                     # Direct TRX fees
    USDT = "usdt"                   # USDT transfer fees

class TransactionType(str, Enum):
    """Transaction types for fee calculation"""
    TRX_TRANSFER = "trx_transfer"           # Simple TRX transfer
    USDT_TRANSFER = "usdt_transfer"         # USDT-TRC20 transfer
    CONTRACT_CALL = "contract_call"         # Smart contract call
    PAYOUT_ROUTER_V0 = "payout_router_v0"   # PayoutRouterV0 call
    PAYOUT_ROUTER_KYC = "payout_router_kyc" # PayoutRouterKYC call
    DELEGATE_RESOURCE = "delegate_resource" # Resource delegation
    FREEZE_BALANCE = "freeze_balance"       # Balance freezing

class FeePriority(str, Enum):
    """Fee calculation priority levels"""
    LOW = "low"         # Lower fees, higher confirmation time
    NORMAL = "normal"   # Balanced fees and confirmation time
    HIGH = "high"       # Higher fees, faster confirmation
    URGENT = "urgent"   # Maximum fees for fastest confirmation

@dataclass
class FeeEstimate:
    """Fee estimate result"""
    transaction_type: TransactionType
    fee_type: FeeType
    estimated_fee_trx: float
    estimated_fee_sun: int
    bandwidth_consumed: int
    energy_consumed: int
    priority: FeePriority
    estimated_confirmation_time: int  # seconds
    gas_limit: Optional[int] = None
    energy_limit: Optional[int] = None
    fee_limit: Optional[int] = None
    confidence_level: float = 0.8  # 0.0 to 1.0

@dataclass
class NetworkConditions:
    """Current network conditions"""
    block_height: int
    bandwidth_price: int  # sun per bandwidth unit
    energy_price: int     # sun per energy unit
    network_congestion: float  # 0.0 to 1.0
    avg_confirmation_time: int  # seconds
    timestamp: datetime

class FeeCalculationRequest(BaseModel):
    """Request for fee calculation"""
    transaction_type: TransactionType = Field(..., description="Type of transaction")
    priority: FeePriority = Field(default=FeePriority.NORMAL, description="Fee priority level")
    amount_usdt: Optional[float] = Field(default=None, description="Amount in USDT")
    recipient_address: Optional[str] = Field(default=None, description="Recipient address")
    contract_address: Optional[str] = Field(default=None, description="Contract address")
    function_name: Optional[str] = Field(default=None, description="Smart contract function")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Function parameters")
    custom_bandwidth: Optional[int] = Field(default=None, description="Custom bandwidth limit")
    custom_energy: Optional[int] = Field(default=None, description="Custom energy limit")

class FeeCalculationResponse(BaseModel):
    """Response for fee calculation"""
    transaction_type: str
    priority: str
    estimated_fee_trx: float
    estimated_fee_sun: int
    bandwidth_consumed: int
    energy_consumed: int
    estimated_confirmation_time: int
    gas_limit: Optional[int]
    energy_limit: Optional[int]
    fee_limit: Optional[int]
    confidence_level: float
    network_conditions: Dict[str, Any]
    recommendations: List[str]
    timestamp: str

class FeeCalculator:
    """TRON fee estimation and optimization system"""
    
    def __init__(self):
        self.settings = get_settings()
        self.tron_service = TronService()
        
        # Fee constants (in sun)
        self.BASE_FEE_TRX = 0.1  # Base fee in TRX
        self.BANDWIDTH_UNIT_COST = 1000  # sun per bandwidth unit
        self.ENERGY_UNIT_COST = 420  # sun per energy unit (approximate)
        
        # Transaction costs (estimated)
        self.TRANSACTION_COSTS = {
            TransactionType.TRX_TRANSFER: {
                "bandwidth": 268,
                "energy": 0
            },
            TransactionType.USDT_TRANSFER: {
                "bandwidth": 268,
                "energy": 14800  # Approximate for USDT transfer
            },
            TransactionType.CONTRACT_CALL: {
                "bandwidth": 268,
                "energy": 20000  # Variable based on contract
            },
            TransactionType.PAYOUT_ROUTER_V0: {
                "bandwidth": 268,
                "energy": 25000  # Higher for router contract
            },
            TransactionType.PAYOUT_ROUTER_KYC: {
                "bandwidth": 268,
                "energy": 30000  # Highest for KYC operations
            },
            TransactionType.DELEGATE_RESOURCE: {
                "bandwidth": 268,
                "energy": 0
            },
            TransactionType.FREEZE_BALANCE: {
                "bandwidth": 268,
                "energy": 0
            }
        }
        
        # Priority multipliers
        self.PRIORITY_MULTIPLIERS = {
            FeePriority.LOW: 0.8,
            FeePriority.NORMAL: 1.0,
            FeePriority.HIGH: 1.5,
            FeePriority.URGENT: 2.0
        }
        
        # Network conditions cache
        self.network_conditions: Optional[NetworkConditions] = None
        self.last_network_update = None
        self.network_cache_duration = 300  # 5 minutes
        
        # Fee history for optimization
        self.fee_history: List[Tuple[datetime, float]] = []
        self.max_fee_history = 1000
        
        logger.info("FeeCalculator initialized")
    
    async def calculate_fee(self, request: FeeCalculationRequest) -> FeeCalculationResponse:
        """Calculate comprehensive fee estimate"""
        try:
            logger.info(f"Calculating fees for {request.transaction_type} transaction")
            
            # Get current network conditions
            network_conditions = await self._get_network_conditions()
            
            # Get base transaction costs
            base_costs = self.TRANSACTION_COSTS.get(request.transaction_type)
            if not base_costs:
                raise ValueError(f"Unknown transaction type: {request.transaction_type}")
            
            # Calculate base fees
            base_bandwidth = request.custom_bandwidth or base_costs["bandwidth"]
            base_energy = request.custom_energy or base_costs["energy"]
            
            # Apply priority multiplier
            priority_multiplier = self.PRIORITY_MULTIPLIERS[request.priority]
            
            # Calculate bandwidth fee
            bandwidth_fee_sun = int(base_bandwidth * network_conditions.bandwidth_price * priority_multiplier)
            
            # Calculate energy fee (if energy is consumed)
            energy_fee_sun = 0
            if base_energy > 0:
                # Check if account has energy
                energy_fee_sun = int(base_energy * network_conditions.energy_price * priority_multiplier)
            
            # Calculate total fee
            total_fee_sun = bandwidth_fee_sun + energy_fee_sun
            total_fee_trx = total_fee_sun / 1_000_000
            
            # Estimate confirmation time based on priority and network conditions
            base_confirmation_time = network_conditions.avg_confirmation_time
            if request.priority == FeePriority.URGENT:
                estimated_confirmation_time = max(10, base_confirmation_time // 2)
            elif request.priority == FeePriority.HIGH:
                estimated_confirmation_time = max(15, int(base_confirmation_time * 0.7))
            elif request.priority == FeePriority.LOW:
                estimated_confirmation_time = int(base_confirmation_time * 1.5)
            else:  # NORMAL
                estimated_confirmation_time = base_confirmation_time
            
            # Calculate confidence level based on network stability
            confidence_level = self._calculate_confidence_level(network_conditions, request.priority)
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(request, total_fee_trx, network_conditions)
            
            # Create fee estimate
            fee_estimate = FeeEstimate(
                transaction_type=request.transaction_type,
                fee_type=FeeType.TRX,
                estimated_fee_trx=total_fee_trx,
                estimated_fee_sun=total_fee_sun,
                bandwidth_consumed=base_bandwidth,
                energy_consumed=base_energy,
                priority=request.priority,
                estimated_confirmation_time=estimated_confirmation_time,
                gas_limit=base_bandwidth,
                energy_limit=base_energy if base_energy > 0 else None,
                fee_limit=total_fee_sun,
                confidence_level=confidence_level
            )
            
            # Store in history
            self._store_fee_history(total_fee_trx)
            
            # Create response
            response = FeeCalculationResponse(
                transaction_type=request.transaction_type.value,
                priority=request.priority.value,
                estimated_fee_trx=total_fee_trx,
                estimated_fee_sun=total_fee_sun,
                bandwidth_consumed=base_bandwidth,
                energy_consumed=base_energy,
                estimated_confirmation_time=estimated_confirmation_time,
                gas_limit=base_bandwidth,
                energy_limit=base_energy if base_energy > 0 else None,
                fee_limit=total_fee_sun,
                confidence_level=confidence_level,
                network_conditions={
                    "block_height": network_conditions.block_height,
                    "bandwidth_price": network_conditions.bandwidth_price,
                    "energy_price": network_conditions.energy_price,
                    "network_congestion": network_conditions.network_congestion,
                    "avg_confirmation_time": network_conditions.avg_confirmation_time
                },
                recommendations=recommendations,
                timestamp=datetime.now().isoformat()
            )
            
            logger.info(f"Fee calculated: {total_fee_trx:.6f} TRX ({total_fee_sun} sun)")
            return response
            
        except Exception as e:
            logger.error(f"Error calculating fees: {e}")
            raise
    
    async def _get_network_conditions(self) -> NetworkConditions:
        """Get current network conditions with caching"""
        now = datetime.now()
        
        # Check if we have recent network conditions
        if (self.network_conditions and 
            self.last_network_update and 
            (now - self.last_network_update).total_seconds() < self.network_cache_duration):
            return self.network_conditions
        
        try:
            # Get current block height
            block_height = self.tron_service.get_height()
            
            # Get network parameters (simplified - in production, you'd get real-time data)
            bandwidth_price = self.BANDWIDTH_UNIT_COST
            energy_price = self.ENERGY_UNIT_COST
            
            # Estimate network congestion (simplified)
            network_congestion = await self._estimate_network_congestion(block_height)
            
            # Estimate average confirmation time
            avg_confirmation_time = await self._estimate_confirmation_time(network_congestion)
            
            # Create network conditions
            self.network_conditions = NetworkConditions(
                block_height=block_height,
                bandwidth_price=bandwidth_price,
                energy_price=energy_price,
                network_congestion=network_congestion,
                avg_confirmation_time=avg_confirmation_time,
                timestamp=now
            )
            
            self.last_network_update = now
            
            logger.debug(f"Network conditions updated: congestion={network_congestion:.2f}, avg_time={avg_confirmation_time}s")
            return self.network_conditions
            
        except Exception as e:
            logger.error(f"Error getting network conditions: {e}")
            # Return default conditions
            return NetworkConditions(
                block_height=0,
                bandwidth_price=self.BANDWIDTH_UNIT_COST,
                energy_price=self.ENERGY_UNIT_COST,
                network_congestion=0.5,
                avg_confirmation_time=60,
                timestamp=now
            )
    
    async def _estimate_network_congestion(self, block_height: int) -> float:
        """Estimate network congestion level"""
        try:
            # Simplified congestion estimation based on recent fee history
            if len(self.fee_history) < 10:
                return 0.5  # Default moderate congestion
            
            # Calculate average fee trend
            recent_fees = [fee for timestamp, fee in self.fee_history[-10:]]
            avg_fee = sum(recent_fees) / len(recent_fees)
            
            # Simple congestion estimation based on fee variance
            fee_variance = sum((fee - avg_fee) ** 2 for fee in recent_fees) / len(recent_fees)
            congestion = min(1.0, fee_variance / avg_fee if avg_fee > 0 else 0.5)
            
            return congestion
            
        except Exception as e:
            logger.debug(f"Error estimating network congestion: {e}")
            return 0.5
    
    async def _estimate_confirmation_time(self, network_congestion: float) -> int:
        """Estimate average confirmation time based on network congestion"""
        # Base confirmation time (3 seconds per block, 19 blocks for confirmation)
        base_time = 19 * 3  # 57 seconds
        
        # Adjust for network congestion
        congestion_multiplier = 1.0 + (network_congestion * 0.5)  # 0.5 to 1.5x
        
        return int(base_time * congestion_multiplier)
    
    def _calculate_confidence_level(self, network_conditions: NetworkConditions, priority: FeePriority) -> float:
        """Calculate confidence level for fee estimate"""
        # Base confidence
        confidence = 0.8
        
        # Adjust based on network stability
        if network_conditions.network_congestion < 0.3:
            confidence += 0.1  # Low congestion = higher confidence
        elif network_conditions.network_congestion > 0.7:
            confidence -= 0.1  # High congestion = lower confidence
        
        # Adjust based on priority
        if priority == FeePriority.URGENT:
            confidence += 0.05  # Urgent transactions have higher confidence
        elif priority == FeePriority.LOW:
            confidence -= 0.05  # Low priority has lower confidence
        
        return max(0.0, min(1.0, confidence))
    
    async def _generate_recommendations(self, request: FeeCalculationRequest, 
                                      estimated_fee: float, 
                                      network_conditions: NetworkConditions) -> List[str]:
        """Generate fee optimization recommendations"""
        recommendations = []
        
        # Network congestion recommendations
        if network_conditions.network_congestion > 0.7:
            recommendations.append("Network is highly congested. Consider using URGENT priority for faster confirmation.")
        elif network_conditions.network_congestion < 0.3:
            recommendations.append("Network congestion is low. NORMAL priority should be sufficient.")
        
        # Fee optimization recommendations
        if request.transaction_type == TransactionType.USDT_TRANSFER:
            if estimated_fee > 1.0:  # More than 1 TRX
                recommendations.append("High energy consumption detected. Consider staking TRX for energy to reduce fees.")
        
        # Priority recommendations
        if request.priority == FeePriority.LOW and estimated_fee < 0.5:
            recommendations.append("Consider using NORMAL priority for better confirmation time with minimal cost increase.")
        
        # Batch recommendations
        if request.transaction_type in [TransactionType.PAYOUT_ROUTER_V0, TransactionType.PAYOUT_ROUTER_KYC]:
            recommendations.append("Consider batching multiple payouts to optimize gas costs.")
        
        # Energy optimization
        if request.transaction_type in [TransactionType.CONTRACT_CALL, TransactionType.USDT_TRANSFER]:
            recommendations.append("Consider delegating energy to reduce transaction costs.")
        
        return recommendations
    
    def _store_fee_history(self, fee: float):
        """Store fee in history for analysis"""
        self.fee_history.append((datetime.now(), fee))
        
        # Keep only recent history
        if len(self.fee_history) > self.max_fee_history:
            self.fee_history = self.fee_history[-self.max_fee_history:]
    
    async def get_fee_statistics(self) -> Dict[str, Any]:
        """Get fee statistics and trends"""
        try:
            if not self.fee_history:
                return {"error": "No fee history available"}
            
            # Calculate statistics
            fees = [fee for _, fee in self.fee_history]
            avg_fee = sum(fees) / len(fees)
            min_fee = min(fees)
            max_fee = max(fees)
            
            # Calculate trend (simple linear regression)
            if len(fees) >= 10:
                recent_avg = sum(fees[-10:]) / 10
                older_avg = sum(fees[-20:-10]) / 10 if len(fees) >= 20 else avg_fee
                trend = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0
            else:
                trend = 0
            
            # Get current network conditions
            network_conditions = await self._get_network_conditions()
            
            return {
                "total_calculations": len(self.fee_history),
                "average_fee_trx": avg_fee,
                "min_fee_trx": min_fee,
                "max_fee_trx": max_fee,
                "fee_trend": trend,
                "current_network_conditions": {
                    "bandwidth_price": network_conditions.bandwidth_price,
                    "energy_price": network_conditions.energy_price,
                    "network_congestion": network_conditions.network_congestion,
                    "avg_confirmation_time": network_conditions.avg_confirmation_time
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting fee statistics: {e}")
            return {"error": str(e)}
    
    async def optimize_fee(self, request: FeeCalculationRequest, 
                          max_fee_trx: float = 5.0) -> List[FeeCalculationResponse]:
        """Find optimal fee configuration within budget"""
        try:
            optimizations = []
            
            # Try different priorities
            for priority in [FeePriority.LOW, FeePriority.NORMAL, FeePriority.HIGH, FeePriority.URGENT]:
                test_request = FeeCalculationRequest(
                    transaction_type=request.transaction_type,
                    priority=priority,
                    amount_usdt=request.amount_usdt,
                    recipient_address=request.recipient_address,
                    contract_address=request.contract_address,
                    function_name=request.function_name,
                    parameters=request.parameters,
                    custom_bandwidth=request.custom_bandwidth,
                    custom_energy=request.custom_energy
                )
                
                fee_response = await self.calculate_fee(test_request)
                
                if fee_response.estimated_fee_trx <= max_fee_trx:
                    optimizations.append(fee_response)
            
            # Sort by fee amount (lowest first)
            optimizations.sort(key=lambda x: x.estimated_fee_trx)
            
            return optimizations
            
        except Exception as e:
            logger.error(f"Error optimizing fees: {e}")
            return []
    
    async def estimate_batch_fee(self, transaction_count: int, 
                                transaction_type: TransactionType,
                                priority: FeePriority = FeePriority.NORMAL) -> FeeCalculationResponse:
        """Estimate fees for batch transactions"""
        try:
            # Create batch request
            batch_request = FeeCalculationRequest(
                transaction_type=transaction_type,
                priority=priority,
                custom_bandwidth=self.TRANSACTION_COSTS[transaction_type]["bandwidth"] * transaction_count,
                custom_energy=self.TRANSACTION_COSTS[transaction_type]["energy"] * transaction_count
            )
            
            # Calculate batch fee
            batch_fee = await self.calculate_fee(batch_request)
            
            # Add batch-specific recommendations
            batch_fee.recommendations.append(f"Batch processing {transaction_count} transactions")
            batch_fee.recommendations.append("Consider batch size optimization for gas efficiency")
            
            return batch_fee
            
        except Exception as e:
            logger.error(f"Error estimating batch fees: {e}")
            raise

# Global instance
fee_calculator = FeeCalculator()

# Convenience functions for external use
async def calculate_fee(request: FeeCalculationRequest) -> FeeCalculationResponse:
    """Calculate transaction fees"""
    return await fee_calculator.calculate_fee(request)

async def get_fee_statistics() -> Dict[str, Any]:
    """Get fee statistics"""
    return await fee_calculator.get_fee_statistics()

async def optimize_fee(request: FeeCalculationRequest, max_fee_trx: float = 5.0) -> List[FeeCalculationResponse]:
    """Optimize fees within budget"""
    return await fee_calculator.optimize_fee(request, max_fee_trx)

async def estimate_batch_fee(transaction_count: int, transaction_type: TransactionType, 
                           priority: FeePriority = FeePriority.NORMAL) -> FeeCalculationResponse:
    """Estimate batch transaction fees"""
    return await fee_calculator.estimate_batch_fee(transaction_count, transaction_type, priority)

# Integration with PayoutManager
async def estimate_payout_manager_fee(
    payout_amount_usdt: float,
    router_type: str,
    sender_address: str,
    recipient_address: str,
    priority: str = "normal"
) -> Dict[str, Any]:
    """
    Estimate fee for PayoutManager transactions.
    
    This function integrates with the payout_manager.py to provide
    accurate fee estimates for different payout types.
    """
    try:
        # Determine transaction type based on router
        if router_type.lower() == "v0":
            tx_type = TransactionType.PAYOUT_ROUTER_V0
        elif router_type.lower() == "kyc":
            tx_type = TransactionType.PAYOUT_ROUTER_KYC
        else:
            tx_type = TransactionType.USDT_TRANSFER
        
        # Determine priority mapping
        priority_map = {
            "low": FeePriority.LOW,
            "normal": FeePriority.NORMAL,
            "high": FeePriority.HIGH,
            "urgent": FeePriority.URGENT
        }
        fee_priority = priority_map.get(priority, FeePriority.NORMAL)
        
        # Create fee calculation request
        request = FeeCalculationRequest(
            transaction_type=tx_type,
            priority=fee_priority,
            amount_usdt=payout_amount_usdt,
            recipient_address=recipient_address,
            sender_address=sender_address
        )
        
        # Get fee calculation
        fee_response = await fee_calculator.calculate_fee(request)
        
        # Get account resources
        account_resources = await fee_calculator.get_account_resources(sender_address)
        
        # Format response for PayoutManager
        return {
            "estimated_fee_trx": fee_response.estimated_fee_trx,
            "estimated_fee_sun": int(fee_response.estimated_fee_trx * 1_000_000),
            "energy_required": fee_response.energy_consumed,
            "bandwidth_required": fee_response.bandwidth_consumed,
            "confidence_level": fee_response.confidence_score,
            "estimated_confirmation_time": fee_response.estimated_confirmation_time,
            "optimization_suggestions": fee_response.recommendations,
            "account_resources": {
                "energy_available": account_resources.get("energy_limit", 0) - account_resources.get("energy_used", 0) if account_resources else 0,
                "bandwidth_available": account_resources.get("net_limit", 0) - account_resources.get("net_used", 0) if account_resources else 0,
                "sufficient_resources": (
                    (account_resources.get("energy_limit", 0) - account_resources.get("energy_used", 0)) >= fee_response.energy_consumed and
                    (account_resources.get("net_limit", 0) - account_resources.get("net_used", 0)) >= fee_response.bandwidth_consumed
                ) if account_resources else False
            },
            "network_conditions": fee_response.network_conditions,
            "recommendations": fee_response.recommendations
        }
        
    except Exception as e:
        logger.error(f"Error estimating PayoutManager fee: {e}")
        # Return default estimate
        return {
            "estimated_fee_trx": 1.0,  # Default 1 TRX
            "estimated_fee_sun": 1000000,
            "energy_required": 50000,
            "bandwidth_required": 350,
            "confidence_level": 0.5,
            "estimated_confirmation_time": 60,
            "optimization_suggestions": ["Unable to generate suggestions"],
            "account_resources": {
                "energy_available": 0,
                "bandwidth_available": 0,
                "sufficient_resources": False
            },
            "network_conditions": {},
            "recommendations": ["Unable to generate recommendations"]
        }

if __name__ == "__main__":
    # Example usage
    async def main():
        # Calculate fee for USDT transfer
        usdt_request = FeeCalculationRequest(
            transaction_type=TransactionType.USDT_TRANSFER,
            priority=FeePriority.NORMAL,
            amount_usdt=100.0,
            recipient_address="TYourTRONAddressHere123456789"
        )
        
        usdt_fee = await calculate_fee(usdt_request)
        print(f"USDT Transfer Fee: {usdt_fee.estimated_fee_trx:.6f} TRX")
        print(f"Estimated confirmation time: {usdt_fee.estimated_confirmation_time}s")
        print(f"Recommendations: {usdt_fee.recommendations}")
        
        # Calculate fee for PayoutRouterV0
        payout_request = FeeCalculationRequest(
            transaction_type=TransactionType.PAYOUT_ROUTER_V0,
            priority=FeePriority.HIGH,
            amount_usdt=50.0,
            contract_address="TYourContractAddressHere123456789"
        )
        
        payout_fee = await calculate_fee(payout_request)
        print(f"PayoutRouterV0 Fee: {payout_fee.estimated_fee_trx:.6f} TRX")
        
        # Optimize fees
        optimizations = await optimize_fee(usdt_request, max_fee_trx=2.0)
        print(f"Fee optimizations: {len(optimizations)} options")
        
        # Get statistics
        stats = await get_fee_statistics()
        print(f"Fee statistics: {stats}")
        
        # Example 5: Integration with PayoutManager
        # This would be called from payment-systems/tron-node/payout_manager.py
        payout_manager_fee = await estimate_payout_manager_fee(
            payout_amount_usdt=float(os.getenv("PAYOUT_AMOUNT_USDT", "25.0")),
            router_type="v0",
            sender_address=os.getenv("PAYOUT_ROUTER_ADDRESS", ""),
            recipient_address=os.getenv("RECIPIENT_WALLET_ADDRESS", ""),
            priority="normal"
        )
        logger.info(f"PayoutManager fee estimate: {payout_manager_fee['estimated_fee_trx']:.6f} TRX")
        
        # Integration documentation
        """
        Lucid RDP Fee Calculator Integration:
        
        1. payment-systems/tron-node/payout_manager.py:
           - Import: from .fee_calculator import estimate_payout_manager_fee
           - Use before creating payouts for accurate fee estimation
           - Include fee estimates in payout responses
           
        2. node/economy/node_economy.py:
           - Estimate fees before processing node operator rewards
           - Optimize payout timing based on network conditions
           - Include fee costs in economic calculations
           
        3. node/worker/node_worker.py:
           - Calculate session costs including transaction fees
           - Estimate payout fees for session completion rewards
           
        4. blockchain/core/blockchain_engine.py:
           - Use for TRON transaction fee optimization
           - Coordinate with TronNodeSystem resource management
        """
    
    asyncio.run(main())