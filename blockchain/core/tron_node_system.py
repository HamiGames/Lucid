#!/usr/bin/env python3
"""
Isolated TRON Node System - Payment Service Only
Based on rebuild-blockchain-engine.md specifications

REBUILT: Extract from core blockchain engine, mark as payment service only.
No other services may call TRON directly - all TRON interactions
must go through this isolated service for security.

Handles:
- USDT-TRC20 payouts via PayoutRouterV0 (non-KYC) or PayoutRouterKYC
- Monthly payout distribution (R-MUST-018)
- Energy/bandwidth management via TRX staking
- Circuit breakers and daily limits
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from motor.motor_asyncio import AsyncIOMotorDatabase
from tronpy import Tron
from tronpy.keys import PrivateKey as TronPrivateKey
from tronpy.providers import HTTPProvider
import httpx

from .models import (
    TronPayout, TronTransaction, USDTBalance, TronNetwork, 
    PayoutRouter, PayoutStatus, PayoutRequest, PayoutResult
)

logger = logging.getLogger(__name__)

# =============================================================================
# TRON NETWORK CONFIGURATION
# =============================================================================

TRON_NETWORK = os.getenv("TRON_NETWORK", "shasta")
USDT_TRC20_MAINNET = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
USDT_TRC20_SHASTA = "TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs"
PAYOUT_ROUTER_V0_ADDRESS = os.getenv("PAYOUT_ROUTER_V0_ADDRESS", "")
PAYOUT_ROUTER_KYC_ADDRESS = os.getenv("PAYOUT_ROUTER_KYC_ADDRESS", "")

# Circuit breaker limits
DAILY_PAYOUT_LIMIT_USDT = 10000.0  # $10k daily limit
MAX_PAYOUT_RETRY_ATTEMPTS = 3
PAYOUT_RETRY_DELAY_SECONDS = 30


class TronServiceStatus(Enum):
    """TRON service status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    MAINTENANCE = "maintenance"


@dataclass
class TronServiceMetrics:
    """TRON service metrics for monitoring"""
    total_payouts: int = 0
    successful_payouts: int = 0
    failed_payouts: int = 0
    daily_payout_amount: float = 0.0
    last_payout_time: Optional[datetime] = None
    service_uptime: float = 0.0
    error_count: int = 0


class TronNodeSystem:
    """
    Isolated TRON blockchain client for payouts (R-MUST-015).
    
    REBUILT: Extract from core blockchain engine, mark as payment service only.
    No other services may call TRON directly - all TRON interactions
    must go through this isolated service for security.
    
    Handles:
    - USDT-TRC20 payouts via PayoutRouterV0 (non-KYC) or PayoutRouterKYC
    - Monthly payout distribution (R-MUST-018)
    - Energy/bandwidth management via TRX staking
    - Circuit breakers and daily limits
    """
    
    def __init__(self, network: str = TRON_NETWORK, db: Optional[AsyncIOMotorDatabase] = None):
        self.network = TronNetwork(
            name=network,
            rpc_url=self._get_rpc_url(network)
        )
        
        # Initialize TRON client
        self.tron = Tron(
            provider=HTTPProvider(self.network.rpc_url),
            network=network
        )
        
        # Database connection for payout tracking
        self.db = db
        self.payouts_collection = db.payouts if db else None
        
        # Service state
        self.status = TronServiceStatus.DISCONNECTED
        self.metrics = TronServiceMetrics()
        self.start_time = datetime.now(timezone.utc)
        
        # Circuit breaker state
        self.daily_payouts: Dict[str, float] = {}  # date -> amount
        self.is_circuit_breaker_open = False
        
        # Private keys for payout operations (should be loaded securely)
        self.payout_private_key = os.getenv("TRON_PAYOUT_PRIVATE_KEY")
        if not self.payout_private_key:
            logger.warning("TRON_PAYOUT_PRIVATE_KEY not set - payouts will fail")
        
        logger.info(f"TronNodeSystem initialized for network: {network}")
    
    def _get_rpc_url(self, network: str) -> str:
        """Get TRON RPC URL based on network"""
        if network == "mainnet":
            return "https://api.trongrid.io"
        elif network == "shasta":
            return "https://api.shasta.trongrid.io"
        else:
            raise ValueError(f"Unsupported TRON network: {network}")
    
    async def connect(self) -> bool:
        """Connect to TRON network"""
        try:
            # Test connection by getting latest block
            latest_block = self.tron.get_latest_block()
            if latest_block:
                self.status = TronServiceStatus.CONNECTED
                logger.info(f"Connected to TRON {self.network.name} network")
                return True
            else:
                self.status = TronServiceStatus.ERROR
                return False
        except Exception as e:
            logger.error(f"Failed to connect to TRON network: {e}")
            self.status = TronServiceStatus.ERROR
            return False
    
    async def get_usdt_balance(self, address: str) -> float:
        """Get USDT balance for an address"""
        try:
            # Get USDT contract
            usdt_contract = self.tron.get_contract(self.network.usdt_contract)
            
            # Call balanceOf function
            balance = usdt_contract.functions.balanceOf(address).call()
            
            # Convert from smallest unit (6 decimals for USDT)
            usdt_balance = balance / 1_000_000
            
            return usdt_balance
            
        except Exception as e:
            logger.error(f"Failed to get USDT balance for {address}: {e}")
            return 0.0
    
    async def send_usdt_payout(
        self, 
        payout_request: PayoutRequest,
        private_key: Optional[str] = None
    ) -> PayoutResult:
        """
        Send USDT payout via TRON network.
        
        Args:
            payout_request: Payout request details
            private_key: Private key for signing (uses default if not provided)
        
        Returns:
            PayoutResult with transaction details
        """
        if not private_key:
            private_key = self.payout_private_key
        
        if not private_key:
            return PayoutResult(
                session_id=payout_request.session_id,
                usdt_amount=payout_request.usdt_amount,
                txid="",
                status="failed",
                router=payout_request.router_type.value,
                error="No private key available for payout"
            )
        
        try:
            # Check circuit breaker
            if self.is_circuit_breaker_open:
                return PayoutResult(
                    session_id=payout_request.session_id,
                    usdt_amount=payout_request.usdt_amount,
                    txid="",
                    status="failed",
                    router=payout_request.router_type.value,
                    error="Circuit breaker is open"
                )
            
            # Check daily limits
            today = datetime.now(timezone.utc).date().isoformat()
            daily_amount = self.daily_payouts.get(today, 0.0)
            
            if daily_amount + payout_request.usdt_amount > DAILY_PAYOUT_LIMIT_USDT:
                return PayoutResult(
                    session_id=payout_request.session_id,
                    usdt_amount=payout_request.usdt_amount,
                    txid="",
                    status="failed",
                    router=payout_request.router_type.value,
                    error="Daily payout limit exceeded"
                )
            
            # Get USDT contract
            usdt_contract = self.tron.get_contract(self.network.usdt_contract)
            
            # Convert amount to smallest unit
            amount_smallest = int(payout_request.usdt_amount * 1_000_000)
            
            # Create transfer transaction
            private_key_obj = TronPrivateKey(bytes.fromhex(private_key))
            from_address = private_key_obj.public_key.to_base58check_address()
            
            # Build transfer transaction
            txn = (
                usdt_contract.functions.transfer(payout_request.to_address, amount_smallest)
                .with_owner(from_address)
                .build()
                .sign(private_key_obj)
            )
            
            # Broadcast transaction
            result = txn.broadcast().wait()
            txid = result.get("id") or result.get("txid")
            
            if txid:
                # Update metrics
                self.metrics.total_payouts += 1
                self.metrics.successful_payouts += 1
                self.metrics.daily_payout_amount += payout_request.usdt_amount
                self.metrics.last_payout_time = datetime.now(timezone.utc)
                self.daily_payouts[today] = daily_amount + payout_request.usdt_amount
                
                # Store payout record
                if self.payouts_collection:
                    payout_record = TronPayout(
                        session_id=payout_request.session_id,
                        recipient_address=payout_request.to_address,
                        amount_usdt=payout_request.usdt_amount,
                        router_type=payout_request.router_type,
                        reason=payout_request.reason,
                        kyc_hash=payout_request.kyc_hash,
                        compliance_signature=payout_request.compliance_signature,
                        txid=txid,
                        status="confirmed"
                    )
                    
                    await self.payouts_collection.insert_one(payout_record.to_dict())
                
                logger.info(f"USDT payout successful: {txid} for {payout_request.usdt_amount} USDT")
                
                return PayoutResult(
                    session_id=payout_request.session_id,
                    usdt_amount=payout_request.usdt_amount,
                    txid=txid,
                    status="success",
                    router=payout_request.router_type.value
                )
            else:
                self.metrics.failed_payouts += 1
                return PayoutResult(
                    session_id=payout_request.session_id,
                    usdt_amount=payout_request.usdt_amount,
                    txid="",
                    status="failed",
                    router=payout_request.router_type.value,
                    error="Transaction broadcast failed"
                )
                
        except Exception as e:
            logger.error(f"Failed to send USDT payout: {e}")
            self.metrics.failed_payouts += 1
            self.metrics.error_count += 1
            
            return PayoutResult(
                session_id=payout_request.session_id,
                usdt_amount=payout_request.usdt_amount,
                txid="",
                status="failed",
                router=payout_request.router_type.value,
                error=str(e)
            )
    
    async def get_payout_status(self, txid: str) -> Dict[str, Any]:
        """Get status of a payout transaction"""
        try:
            # Get transaction info
            txn_info = self.tron.get_transaction(txid)
            
            if not txn_info:
                return {
                    "status": "not_found",
                    "txid": txid,
                    "block_number": None,
                    "confirmations": 0
                }
            
            # Check if transaction is confirmed
            if txn_info.get("ret") and txn_info["ret"][0].get("contractRet") == "SUCCESS":
                block_number = txn_info.get("blockNumber", 0)
                latest_block = self.tron.get_latest_block_number()
                confirmations = latest_block - block_number
                
                return {
                    "status": "confirmed" if confirmations >= 1 else "pending",
                    "txid": txid,
                    "block_number": block_number,
                    "confirmations": confirmations
                }
            else:
                return {
                    "status": "failed",
                    "txid": txid,
                    "block_number": None,
                    "confirmations": 0
                }
                
        except Exception as e:
            logger.error(f"Failed to get payout status for {txid}: {e}")
            return {
                "status": "error",
                "txid": txid,
                "error": str(e)
            }
    
    async def process_monthly_payouts(self, payout_requests: List[PayoutRequest]) -> List[PayoutResult]:
        """
        Process monthly payout distribution (R-MUST-018).
        
        Args:
            payout_requests: List of payout requests to process
        
        Returns:
            List of payout results
        """
        results = []
        
        for request in payout_requests:
            try:
                # Determine router type based on KYC status
                if request.kyc_hash and request.compliance_signature:
                    request.router_type = PayoutRouter.PRKYC
                else:
                    request.router_type = PayoutRouter.PR0
                
                # Send payout
                result = await self.send_usdt_payout(request)
                results.append(result)
                
                # Small delay between payouts to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to process payout for {request.session_id}: {e}")
                results.append(PayoutResult(
                    session_id=request.session_id,
                    usdt_amount=request.usdt_amount,
                    txid="",
                    status="failed",
                    router=request.router_type.value,
                    error=str(e)
                ))
        
        logger.info(f"Processed {len(results)} monthly payouts")
        return results
    
    async def check_circuit_breaker(self) -> bool:
        """Check if circuit breaker should be opened"""
        # Check daily limits
        today = datetime.now(timezone.utc).date().isoformat()
        daily_amount = self.daily_payouts.get(today, 0.0)
        
        if daily_amount >= DAILY_PAYOUT_LIMIT_USDT:
            self.is_circuit_breaker_open = True
            logger.warning("Circuit breaker opened due to daily limit")
            return True
        
        # Check error rate
        total_operations = self.metrics.total_payouts + self.metrics.error_count
        if total_operations > 10:  # Only check after some operations
            error_rate = self.metrics.error_count / total_operations
            if error_rate > 0.5:  # 50% error rate
                self.is_circuit_breaker_open = True
                logger.warning("Circuit breaker opened due to high error rate")
                return True
        
        return False
    
    async def reset_circuit_breaker(self):
        """Reset circuit breaker (typically at start of new day)"""
        self.is_circuit_breaker_open = False
        self.daily_payouts.clear()
        logger.info("Circuit breaker reset")
    
    async def get_service_metrics(self) -> TronServiceMetrics:
        """Get service metrics"""
        # Update uptime
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        self.metrics.service_uptime = uptime
        
        return self.metrics
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            # Test TRON connection
            latest_block = self.tron.get_latest_block()
            
            # Get service metrics
            metrics = await self.get_service_metrics()
            
            # Check circuit breaker
            await self.check_circuit_breaker()
            
            return {
                "status": self.status.value,
                "network": self.network.name,
                "latest_block": latest_block.get("block_header", {}).get("raw_data", {}).get("number", 0) if latest_block else 0,
                "circuit_breaker_open": self.is_circuit_breaker_open,
                "metrics": {
                    "total_payouts": metrics.total_payouts,
                    "successful_payouts": metrics.successful_payouts,
                    "failed_payouts": metrics.failed_payouts,
                    "daily_payout_amount": metrics.daily_payout_amount,
                    "service_uptime": metrics.service_uptime,
                    "error_count": metrics.error_count
                }
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "network": self.network.name,
                "circuit_breaker_open": self.is_circuit_breaker_open
            }
    
    async def close(self):
        """Close TRON connection"""
        try:
            if hasattr(self.tron, 'close'):
                await self.tron.close()
            self.status = TronServiceStatus.DISCONNECTED
            logger.info("TronNodeSystem connection closed")
        except Exception as e:
            logger.error(f"Error closing TronNodeSystem: {e}")


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

async def create_tron_node_system(
    network: str = TRON_NETWORK,
    db: Optional[AsyncIOMotorDatabase] = None
) -> TronNodeSystem:
    """
    Factory function to create and initialize TronNodeSystem.
    
    Args:
        network: TRON network (mainnet, shasta)
        db: MongoDB database connection
    
    Returns:
        Initialized TronNodeSystem instance
    """
    tron_system = TronNodeSystem(network=network, db=db)
    
    # Connect to TRON network
    connected = await tron_system.connect()
    if not connected:
        logger.warning("Failed to connect to TRON network during initialization")
    
    return tron_system
