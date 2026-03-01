#!/usr/bin/env python3
"""
Gas Estimator for EVM Transactions
Based on rebuild-blockchain-engine.md specifications

Provides gas estimation for On-System Chain transactions:
- Contract function gas estimation
- Circuit breakers for gas limit protection
- Dynamic gas price calculation
- Transaction cost optimization
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class GasEstimationMethod(Enum):
    """Gas estimation methods"""
    STATIC = "static"
    DYNAMIC = "dynamic"
    HISTORICAL = "historical"
    SIMULATION = "simulation"


@dataclass
class GasEstimate:
    """Gas estimate result"""
    gas_limit: int
    gas_price: int
    total_cost_wei: int
    method: GasEstimationMethod
    confidence: float
    timestamp: datetime
    error_margin: float = 0.1


@dataclass
class GasPriceHistory:
    """Gas price history entry"""
    timestamp: datetime
    gas_price: int
    block_number: int
    network_congestion: float


class GasEstimator:
    """
    Gas estimator for EVM transactions.
    
    Provides intelligent gas estimation with:
    - Multiple estimation methods
    - Historical data analysis
    - Circuit breaker protection
    - Cost optimization
    """
    
    # Base gas costs for common operations
    BASE_TRANSACTION_GAS = 21000
    CONTRACT_CALL_GAS = 2300
    STORAGE_SET_GAS = 20000
    STORAGE_UPDATE_GAS = 5000
    
    # Contract-specific gas costs
    CONTRACT_GAS_COSTS = {
        "registerSession": 50000,
        "storeChunkMetadata": 30000,
        "updateChunkStatus": 20000,
        "getSessionAnchor": 0,  # View function
        "getChunkMetadata": 0,  # View function
    }
    
    def __init__(self, evm_client):
        self.evm_client = evm_client
        self.logger = logging.getLogger(__name__)
        
        # Gas price history for dynamic estimation
        self._gas_price_history: List[GasPriceHistory] = []
        self._max_history_size = 1000
        
        # Circuit breaker for gas limit protection
        self._max_gas_limit = 10000000  # 10M gas limit
        self._min_gas_limit = 21000     # Base transaction gas
        
        # Estimation confidence thresholds
        self._high_confidence_threshold = 0.9
        self._medium_confidence_threshold = 0.7
        self._low_confidence_threshold = 0.5
    
    async def estimate_gas_for_function(
        self,
        contract_address: str,
        function_name: str,
        parameters: Dict[str, Any],
        method: GasEstimationMethod = GasEstimationMethod.DYNAMIC
    ) -> GasEstimate:
        """
        Estimate gas for contract function call.
        
        Args:
            contract_address: Contract address
            function_name: Function name to call
            parameters: Function parameters
            method: Estimation method to use
            
        Returns:
            GasEstimate with gas limit and price
        """
        try:
            # Get current gas price
            current_gas_price = await self._get_current_gas_price()
            
            # Estimate gas limit based on method
            if method == GasEstimationMethod.STATIC:
                gas_limit = self._estimate_static_gas(function_name, parameters)
                confidence = 0.8
            elif method == GasEstimationMethod.DYNAMIC:
                gas_limit = await self._estimate_dynamic_gas(function_name, parameters)
                confidence = 0.9
            elif method == GasEstimationMethod.HISTORICAL:
                gas_limit = await self._estimate_historical_gas(function_name, parameters)
                confidence = 0.7
            elif method == GasEstimationMethod.SIMULATION:
                gas_limit = await self._estimate_simulation_gas(contract_address, function_name, parameters)
                confidence = 0.95
            else:
                gas_limit = self._estimate_static_gas(function_name, parameters)
                confidence = 0.8
            
            # Apply circuit breaker protection
            gas_limit = self._apply_circuit_breaker(gas_limit)
            
            # Calculate total cost
            total_cost_wei = gas_limit * current_gas_price
            
            # Create gas estimate
            estimate = GasEstimate(
                gas_limit=gas_limit,
                gas_price=current_gas_price,
                total_cost_wei=total_cost_wei,
                method=method,
                confidence=confidence,
                timestamp=datetime.now(timezone.utc),
                error_margin=0.1
            )
            
            self.logger.info(f"Gas estimated for {function_name}: {gas_limit} gas, {current_gas_price} wei/gas")
            return estimate
            
        except Exception as e:
            self.logger.error(f"Failed to estimate gas for {function_name}: {e}")
            # Return safe fallback estimate
            return self._get_fallback_estimate()
    
    def _estimate_static_gas(self, function_name: str, parameters: Dict[str, Any]) -> int:
        """Estimate gas using static costs"""
        try:
            # Base transaction gas
            gas = self.BASE_TRANSACTION_GAS
            
            # Add contract call gas
            gas += self.CONTRACT_CALL_GAS
            
            # Add function-specific gas
            function_gas = self.CONTRACT_GAS_COSTS.get(function_name, 10000)
            gas += function_gas
            
            # Add parameter-based gas (estimate based on data size)
            parameter_gas = self._estimate_parameter_gas(parameters)
            gas += parameter_gas
            
            return gas
            
        except Exception as e:
            self.logger.error(f"Failed to estimate static gas: {e}")
            return self._max_gas_limit // 2
    
    async def _estimate_dynamic_gas(self, function_name: str, parameters: Dict[str, Any]) -> int:
        """Estimate gas using dynamic analysis"""
        try:
            # Start with static estimate
            static_gas = self._estimate_static_gas(function_name, parameters)
            
            # Get network congestion factor
            congestion_factor = await self._get_network_congestion()
            
            # Adjust gas based on congestion
            if congestion_factor > 0.8:  # High congestion
                gas_multiplier = 1.5
            elif congestion_factor > 0.5:  # Medium congestion
                gas_multiplier = 1.2
            else:  # Low congestion
                gas_multiplier = 1.0
            
            dynamic_gas = int(static_gas * gas_multiplier)
            
            return dynamic_gas
            
        except Exception as e:
            self.logger.error(f"Failed to estimate dynamic gas: {e}")
            return self._estimate_static_gas(function_name, parameters)
    
    async def _estimate_historical_gas(self, function_name: str, parameters: Dict[str, Any]) -> int:
        """Estimate gas using historical data"""
        try:
            # Get historical gas prices
            historical_prices = self._get_recent_gas_prices(hours=24)
            
            if not historical_prices:
                return self._estimate_static_gas(function_name, parameters)
            
            # Calculate average gas price
            avg_gas_price = sum(hp.gas_price for hp in historical_prices) / len(historical_prices)
            
            # Get current gas price
            current_gas_price = await self._get_current_gas_price()
            
            # Calculate price ratio
            price_ratio = current_gas_price / avg_gas_price
            
            # Adjust gas limit based on price ratio
            base_gas = self._estimate_static_gas(function_name, parameters)
            historical_gas = int(base_gas * price_ratio)
            
            return historical_gas
            
        except Exception as e:
            self.logger.error(f"Failed to estimate historical gas: {e}")
            return self._estimate_static_gas(function_name, parameters)
    
    async def _estimate_simulation_gas(self, contract_address: str, function_name: str, parameters: Dict[str, Any]) -> int:
        """Estimate gas using simulation (if available)"""
        try:
            # Try to get actual gas estimate from EVM client
            if hasattr(self.evm_client, 'estimate_gas'):
                estimated_gas = await self.evm_client.estimate_gas(
                    contract_address, function_name, parameters
                )
                
                if estimated_gas > 0:
                    # Add safety margin
                    safety_margin = 1.2
                    return int(estimated_gas * safety_margin)
            
            # Fallback to dynamic estimation
            return await self._estimate_dynamic_gas(function_name, parameters)
            
        except Exception as e:
            self.logger.error(f"Failed to estimate simulation gas: {e}")
            return await self._estimate_dynamic_gas(function_name, parameters)
    
    def _estimate_parameter_gas(self, parameters: Dict[str, Any]) -> int:
        """Estimate gas based on parameter size"""
        try:
            total_gas = 0
            
            for param_name, param_value in parameters.items():
                if isinstance(param_value, bytes):
                    # Gas for bytes data
                    data_size = len(param_value)
                    gas = 16 * data_size  # 16 gas per byte
                elif isinstance(param_value, str):
                    # Gas for string data
                    data_size = len(param_value.encode('utf-8'))
                    gas = 16 * data_size
                elif isinstance(param_value, list):
                    # Gas for array data
                    gas = 20 * len(param_value)  # 20 gas per array element
                else:
                    # Gas for simple types
                    gas = 20
                
                total_gas += gas
            
            return total_gas
            
        except Exception as e:
            self.logger.error(f"Failed to estimate parameter gas: {e}")
            return 1000  # Safe fallback
    
    async def _get_current_gas_price(self) -> int:
        """Get current gas price from EVM client"""
        try:
            if hasattr(self.evm_client, 'get_gas_price'):
                return await self.evm_client.get_gas_price()
            else:
                # Default gas price (20 gwei)
                return 20000000000
                
        except Exception as e:
            self.logger.error(f"Failed to get current gas price: {e}")
            return 20000000000
    
    async def _get_network_congestion(self) -> float:
        """Get network congestion factor"""
        try:
            # This would typically query the network for congestion metrics
            # For now, return a mock congestion factor
            return 0.3  # Low congestion
            
        except Exception as e:
            self.logger.error(f"Failed to get network congestion: {e}")
            return 0.5  # Medium congestion as fallback
    
    def _get_recent_gas_prices(self, hours: int = 24) -> List[GasPriceHistory]:
        """Get recent gas price history"""
        try:
            cutoff_time = datetime.now(timezone.utc).timestamp() - (hours * 3600)
            
            recent_prices = [
                price for price in self._gas_price_history
                if price.timestamp.timestamp() >= cutoff_time
            ]
            
            return recent_prices
            
        except Exception as e:
            self.logger.error(f"Failed to get recent gas prices: {e}")
            return []
    
    def _apply_circuit_breaker(self, gas_limit: int) -> int:
        """Apply circuit breaker protection to gas limit"""
        try:
            # Ensure gas limit is within safe bounds
            if gas_limit < self._min_gas_limit:
                self.logger.warning(f"Gas limit too low: {gas_limit}, using minimum: {self._min_gas_limit}")
                return self._min_gas_limit
            
            if gas_limit > self._max_gas_limit:
                self.logger.warning(f"Gas limit too high: {gas_limit}, using maximum: {self._max_gas_limit}")
                return self._max_gas_limit
            
            return gas_limit
            
        except Exception as e:
            self.logger.error(f"Failed to apply circuit breaker: {e}")
            return self._max_gas_limit // 2
    
    def _get_fallback_estimate(self) -> GasEstimate:
        """Get fallback gas estimate when estimation fails"""
        return GasEstimate(
            gas_limit=500000,  # Safe fallback
            gas_price=20000000000,  # 20 gwei
            total_cost_wei=500000 * 20000000000,
            method=GasEstimationMethod.STATIC,
            confidence=0.5,
            timestamp=datetime.now(timezone.utc),
            error_margin=0.2
        )
    
    async def update_gas_price_history(self, gas_price: int, block_number: int):
        """Update gas price history"""
        try:
            history_entry = GasPriceHistory(
                timestamp=datetime.now(timezone.utc),
                gas_price=gas_price,
                block_number=block_number,
                network_congestion=await self._get_network_congestion()
            )
            
            self._gas_price_history.append(history_entry)
            
            # Limit history size
            if len(self._gas_price_history) > self._max_history_size:
                self._gas_price_history = self._gas_price_history[-self._max_history_size:]
            
        except Exception as e:
            self.logger.error(f"Failed to update gas price history: {e}")
    
    def get_gas_estimation_stats(self) -> Dict[str, Any]:
        """Get gas estimation statistics"""
        try:
            if not self._gas_price_history:
                return {
                    "history_size": 0,
                    "avg_gas_price": 0,
                    "min_gas_price": 0,
                    "max_gas_price": 0
                }
            
            prices = [entry.gas_price for entry in self._gas_price_history]
            
            return {
                "history_size": len(self._gas_price_history),
                "avg_gas_price": sum(prices) / len(prices),
                "min_gas_price": min(prices),
                "max_gas_price": max(prices),
                "latest_gas_price": prices[-1] if prices else 0
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get gas estimation stats: {e}")
            return {}


# Global gas estimator instance
_gas_estimator: Optional[GasEstimator] = None


def get_gas_estimator() -> Optional[GasEstimator]:
    """Get global gas estimator instance"""
    return _gas_estimator


def create_gas_estimator(evm_client) -> GasEstimator:
    """Create and initialize gas estimator"""
    global _gas_estimator
    _gas_estimator = GasEstimator(evm_client)
    return _gas_estimator


async def cleanup_gas_estimator():
    """Cleanup gas estimator"""
    global _gas_estimator
    _gas_estimator = None


if __name__ == "__main__":
    async def test_gas_estimator():
        """Test gas estimator"""
        from .evm_client import EVMClient
        
        # Mock EVM client for testing
        evm_client = EVMClient("http://localhost:8545")
        
        # Create gas estimator
        estimator = create_gas_estimator(evm_client)
        
        try:
            # Test gas estimation
            estimate = await estimator.estimate_gas_for_function(
                contract_address="0x1234567890123456789012345678901234567890",
                function_name="registerSession",
                parameters={"sessionId": b"test", "owner": "0x123"},
                method=GasEstimationMethod.DYNAMIC
            )
            
            print(f"Gas estimate:")
            print(f"  Gas limit: {estimate.gas_limit}")
            print(f"  Gas price: {estimate.gas_price}")
            print(f"  Total cost: {estimate.total_cost_wei} wei")
            print(f"  Method: {estimate.method.value}")
            print(f"  Confidence: {estimate.confidence}")
            
            # Test different methods
            for method in GasEstimationMethod:
                estimate = await estimator.estimate_gas_for_function(
                    contract_address="0x1234567890123456789012345678901234567890",
                    function_name="storeChunkMetadata",
                    parameters={"chunkId": b"test", "size": 1024},
                    method=method
                )
                
                print(f"{method.value}: {estimate.gas_limit} gas (confidence: {estimate.confidence})")
            
            # Test stats
            stats = estimator.get_gas_estimation_stats()
            print(f"Gas estimation stats: {stats}")
            
        finally:
            await evm_client.close()
    
    # Run test
    asyncio.run(test_gas_estimator())
