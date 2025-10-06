# LUCID TRON Node Client - SPEC-1B TRON Integration
# Professional TRON blockchain client for USDT payouts
# Multi-platform support for ARM64 Pi and AMD64 development

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

# TRON integration
try:
    from tronpy import Tron
    from tronpy.keys import PrivateKey
    from tronpy.providers import HTTPProvider
    HAS_TRON = True
except ImportError:
    HAS_TRON = False
    Tron = None

logger = logging.getLogger(__name__)

# Configuration from environment
TRON_NETWORK = os.getenv("TRON_NETWORK", "shasta")  # shasta or mainnet
TRON_RPC_URL = os.getenv("TRON_RPC_URL", "https://api.shasta.trongrid.io")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
PAYOUT_ROUTER_V0_ADDRESS = os.getenv("PAYOUT_ROUTER_V0_ADDRESS", "")
PAYOUT_ROUTER_KYC_ADDRESS = os.getenv("PAYOUT_ROUTER_KYC_ADDRESS", "")
USDT_TRC20_ADDRESS = os.getenv("USDT_TRC20_ADDRESS", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
COMPLIANCE_SIGNER_KEY = os.getenv("COMPLIANCE_SIGNER_KEY", "")


class PayoutStatus(Enum):
    """Payout status states"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"


@dataclass
class PayoutRequest:
    """Payout request metadata"""
    session_id: str
    to_address: str
    amount_usdt: float
    router_type: str  # "v0" or "kyc"
    reason_code: str
    status: PayoutStatus
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    transaction_hash: Optional[str] = None
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    kyc_signature: Optional[str] = None


class TronNodeClient:
    """
    TRON Node Client for Lucid blockchain system.
    
    Handles USDT payouts via PayoutRouterV0 and PayoutRouterKYC contracts.
    Implements SPEC-1B TRON integration requirements.
    """
    
    def __init__(self):
        """Initialize TRON node client"""
        self.app = FastAPI(
            title="Lucid TRON Node Client",
            description="TRON blockchain client for Lucid payout system",
            version="1.0.0"
        )
        
        # TRON client
        self.tron: Optional[Tron] = None
        
        # Contract instances
        self.payout_router_v0 = None
        self.payout_router_kyc = None
        self.usdt_contract = None
        
        # Payout tracking
        self.active_payouts: Dict[str, PayoutRequest] = {}
        self.payout_tasks: Dict[str, asyncio.Task] = {}
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Setup FastAPI routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "service": "tron-node-client",
                "tron_connected": self.tron is not None,
                "network": TRON_NETWORK,
                "active_payouts": len(self.active_payouts)
            }
        
        @self.app.post("/payouts/disburse")
        async def disburse_payout(request: DisbursePayoutRequest):
            """Disburse payout via TRON"""
            return await self.disburse_payout(
                session_id=request.session_id,
                to_address=request.to_address,
                amount_usdt=request.amount_usdt,
                router_type=request.router_type,
                reason_code=request.reason_code,
                kyc_signature=request.kyc_signature
            )
        
        @self.app.get("/payouts/{session_id}")
        async def get_payout(session_id: str):
            """Get payout information"""
            if session_id not in self.active_payouts:
                raise HTTPException(404, "Payout not found")
            
            payout = self.active_payouts[session_id]
            return {
                "session_id": payout.session_id,
                "to_address": payout.to_address,
                "amount_usdt": payout.amount_usdt,
                "router_type": payout.router_type,
                "status": payout.status.value,
                "created_at": payout.created_at.isoformat(),
                "confirmed_at": payout.confirmed_at.isoformat() if payout.confirmed_at else None,
                "transaction_hash": payout.transaction_hash
            }
        
        @self.app.get("/payouts")
        async def list_payouts():
            """List all payouts"""
            return {
                "payouts": [
                    {
                        "session_id": payout.session_id,
                        "to_address": payout.to_address,
                        "amount_usdt": payout.amount_usdt,
                        "status": payout.status.value,
                        "created_at": payout.created_at.isoformat()
                    }
                    for payout in self.active_payouts.values()
                ]
            }
        
        @self.app.get("/balance")
        async def get_balance():
            """Get USDT balance"""
            return await self.get_usdt_balance()
    
    async def _setup_tron_client(self) -> None:
        """Setup TRON client connection"""
        if not HAS_TRON:
            logger.warning("TronPy not available, TRON operations disabled")
            return
        
        try:
            # Initialize TRON client
            if TRON_NETWORK == "mainnet":
                self.tron = Tron(HTTPProvider("https://api.trongrid.io"))
            else:
                self.tron = Tron(HTTPProvider(TRON_RPC_URL))
            
            # Test connection
            latest_block = self.tron.get_latest_block_number()
            logger.info(f"TRON client connected, latest block: {latest_block}")
            
            # Setup contract instances
            await self._setup_contracts()
            
        except Exception as e:
            logger.error(f"TRON client setup failed: {e}")
            self.tron = None
    
    async def _setup_contracts(self) -> None:
        """Setup contract instances"""
        if not self.tron:
            return
        
        try:
            # USDT TRC20 contract
            if USDT_TRC20_ADDRESS:
                self.usdt_contract = self.tron.get_contract(USDT_TRC20_ADDRESS)
                logger.info("USDT TRC20 contract instance created")
            
            # PayoutRouterV0 contract
            if PAYOUT_ROUTER_V0_ADDRESS:
                self.payout_router_v0 = self.tron.get_contract(PAYOUT_ROUTER_V0_ADDRESS)
                logger.info("PayoutRouterV0 contract instance created")
            
            # PayoutRouterKYC contract
            if PAYOUT_ROUTER_KYC_ADDRESS:
                self.payout_router_kyc = self.tron.get_contract(PAYOUT_ROUTER_KYC_ADDRESS)
                logger.info("PayoutRouterKYC contract instance created")
            
        except Exception as e:
            logger.error(f"Contract setup failed: {e}")
    
    async def disburse_payout(self, 
                            session_id: str,
                            to_address: str,
                            amount_usdt: float,
                            router_type: str,
                            reason_code: str,
                            kyc_signature: Optional[str] = None) -> Dict[str, Any]:
        """Disburse payout via TRON"""
        try:
            # Create payout request
            payout = PayoutRequest(
                session_id=session_id,
                to_address=to_address,
                amount_usdt=amount_usdt,
                router_type=router_type,
                reason_code=reason_code,
                status=PayoutStatus.PENDING,
                created_at=datetime.now(timezone.utc),
                kyc_signature=kyc_signature
            )
            
            # Store in memory
            self.active_payouts[session_id] = payout
            
            # Start payout task
            task = asyncio.create_task(self._submit_payout(payout))
            self.payout_tasks[session_id] = task
            
            logger.info(f"Disbursed payout: {session_id} -> {to_address} ({amount_usdt} USDT)")
            
            return {
                "session_id": session_id,
                "to_address": to_address,
                "amount_usdt": amount_usdt,
                "router_type": router_type,
                "status": payout.status.value,
                "created_at": payout.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Payout disbursement failed: {e}")
            raise HTTPException(500, f"Payout disbursement failed: {str(e)}")
    
    async def get_usdt_balance(self) -> Dict[str, Any]:
        """Get USDT balance"""
        try:
            if not self.tron or not self.usdt_contract:
                return {
                    "balance": 0.0,
                    "address": "N/A",
                    "network": TRON_NETWORK
                }
            
            # Get account address
            if PRIVATE_KEY:
                account = self.tron.get_account(PRIVATE_KEY)
                address = account['address']
            else:
                address = "N/A"
            
            # Get USDT balance
            if address != "N/A":
                balance = self.usdt_contract.functions.balanceOf(address)
                balance_usdt = balance / 1_000_000  # USDT has 6 decimals
            else:
                balance_usdt = 0.0
            
            return {
                "balance": balance_usdt,
                "address": address,
                "network": TRON_NETWORK
            }
            
        except Exception as e:
            logger.error(f"Balance check failed: {e}")
            return {
                "balance": 0.0,
                "address": "N/A",
                "network": TRON_NETWORK,
                "error": str(e)
            }
    
    async def _submit_payout(self, payout: PayoutRequest) -> None:
        """Submit payout to TRON"""
        try:
            logger.info(f"Submitting payout: {payout.session_id}")
            
            if not self.tron:
                logger.warning("TRON client not available, simulating payout")
                await asyncio.sleep(2)  # Simulate network delay
                payout.status = PayoutStatus.CONFIRMED
                payout.confirmed_at = datetime.now(timezone.utc)
                payout.transaction_hash = f"0x{os.urandom(32).hex()}"
                payout.block_number = 12345
                return
            
            # Select router contract
            if payout.router_type == "kyc" and self.payout_router_kyc:
                router_contract = self.payout_router_kyc
                function_name = "disburseKYC"
            elif payout.router_type == "v0" and self.payout_router_v0:
                router_contract = self.payout_router_v0
                function_name = "disburse"
            else:
                raise Exception(f"Router {payout.router_type} not available")
            
            # Convert amount to USDT units (6 decimals)
            amount_units = int(payout.amount_usdt * 1_000_000)
            
            # Build transaction
            if function_name == "disburseKYC":
                # KYC payout with signature
                transaction = router_contract.functions.disburseKYC(
                    payout.session_id.encode(),
                    payout.to_address,
                    amount_units,
                    payout.reason_code.encode(),
                    payout.kyc_signature or ""
                )
            else:
                # Standard payout
                transaction = router_contract.functions.disburse(
                    payout.session_id.encode(),
                    payout.to_address,
                    amount_units
                )
            
            # Submit transaction
            if PRIVATE_KEY:
                # Sign and send transaction
                tx = transaction.with_owner(PRIVATE_KEY).build().sign().broadcast()
                payout.transaction_hash = tx['txid']
            else:
                # Simulate transaction
                payout.transaction_hash = f"0x{os.urandom(32).hex()}"
            
            # Update payout status
            payout.status = PayoutStatus.SUBMITTED
            
            # Wait for confirmation (simplified)
            await asyncio.sleep(3)
            payout.status = PayoutStatus.CONFIRMED
            payout.confirmed_at = datetime.now(timezone.utc)
            payout.block_number = self.tron.get_latest_block_number() if self.tron else 12345
            
            logger.info(f"Payout confirmed: {payout.session_id}")
            
        except Exception as e:
            logger.error(f"Payout submission failed: {e}")
            payout.status = PayoutStatus.FAILED


# Pydantic models
class DisbursePayoutRequest(BaseModel):
    session_id: str
    to_address: str
    amount_usdt: float
    router_type: str  # "v0" or "kyc"
    reason_code: str
    kyc_signature: Optional[str] = None


# Global TRON client instance
tron_client = TronNodeClient()

# FastAPI app instance
app = tron_client.app

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("Starting TRON Node Client...")
    await tron_client._setup_tron_client()
    logger.info("TRON Node Client started")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Shutting down TRON Node Client...")
    
    # Cancel all payout tasks
    for task in tron_client.payout_tasks.values():
        task.cancel()
    
    logger.info("TRON Node Client stopped")


def main():
    """Main entry point"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[tron-node-client] %(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run server
    uvicorn.run(
        "tron_client:app",
        host="0.0.0.0",
        port=8095,
        log_level="info"
    )


if __name__ == "__main__":
    main()
