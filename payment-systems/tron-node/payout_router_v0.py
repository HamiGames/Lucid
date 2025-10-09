"""
LUCID Payment Systems - PayoutRouterV0 Integration
Non-KYC USDT payout router for end-users via TRON blockchain
Distroless container: pickme/lucid:payment-systems:latest
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import aiofiles
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field
import aiohttp
from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider
import httpx

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PayoutStatus(str, Enum):
    """Payout transaction status"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REJECTED = "rejected"
    EXPIRED = "expired"

class PayoutReason(str, Enum):
    """Payout reason codes"""
    SESSION_RELAY = "session_relay"
    STORAGE_PROOF = "storage_proof"
    VALIDATION_SIGNATURE = "validation_signature"
    UPTIME_REWARD = "uptime_reward"
    GOVERNANCE_PARTICIPATION = "governance_participation"
    CUSTOM = "custom"

class PayoutType(str, Enum):
    """Payout type classification"""
    IMMEDIATE = "immediate"      # Instant payout
    SCHEDULED = "scheduled"      # Scheduled payout
    BATCH = "batch"             # Batch payout
    EMERGENCY = "emergency"      # Emergency payout

@dataclass
class PayoutRequest:
    """Payout request data"""
    recipient_address: str
    amount_usdt: float
    reason: PayoutReason
    payout_type: PayoutType = PayoutType.IMMEDIATE
    session_id: Optional[str] = None
    node_id: Optional[str] = None
    work_credits: Optional[float] = None
    custom_data: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    gas_limit: Optional[int] = None
    energy_limit: Optional[int] = None

@dataclass
class PayoutTransaction:
    """Payout transaction record"""
    payout_id: str
    request: PayoutRequest
    txid: Optional[str] = None
    status: PayoutStatus = PayoutStatus.PENDING
    gas_used: Optional[int] = None
    energy_used: Optional[int] = None
    fee_paid: Optional[float] = None
    created_at: datetime = None
    confirmed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class RouterConfig:
    """PayoutRouterV0 configuration"""
    contract_address: str
    owner_address: str
    private_key: str
    usdt_contract_address: str
    gas_limit: int = 1000000
    energy_limit: int = 10000000
    fee_limit: int = 1000000000  # 1 TRX in sun
    max_payout_amount: float = 1000.0  # Max USDT per payout
    daily_limit: float = 10000.0  # Max USDT per day
    min_payout_amount: float = 0.01  # Min USDT per payout
    batch_size: int = 50  # Max payouts per batch
    confirmation_blocks: int = 19  # Blocks to wait for confirmation

class PayoutRequestModel(BaseModel):
    """Pydantic model for payout requests"""
    recipient_address: str = Field(..., description="TRON address to receive USDT")
    amount_usdt: float = Field(..., gt=0, description="Amount in USDT")
    reason: PayoutReason = Field(..., description="Reason for payout")
    payout_type: PayoutType = Field(default=PayoutType.IMMEDIATE, description="Type of payout")
    session_id: Optional[str] = Field(default=None, description="Associated session ID")
    node_id: Optional[str] = Field(default=None, description="Associated node ID")
    work_credits: Optional[float] = Field(default=None, description="Work credits earned")
    custom_data: Optional[Dict[str, Any]] = Field(default=None, description="Custom data")
    expires_at: Optional[str] = Field(default=None, description="Expiration timestamp")

class PayoutResponseModel(BaseModel):
    """Pydantic model for payout responses"""
    payout_id: str
    txid: Optional[str] = None
    status: str
    message: str
    amount_usdt: float
    recipient_address: str
    created_at: str
    estimated_confirmation: Optional[str] = None

class PayoutRouterV0:
    """PayoutRouterV0 contract integration for non-KYC USDT payouts"""
    
    def __init__(self):
        self.settings = get_settings()
        
        # TRON network configuration
        self.network = self.settings.TRON_NETWORK
        self.endpoint = self._resolve_endpoint()
        
        # Contract addresses
        self.payout_router_address = self.settings.PAYOUT_ROUTER_V0_ADDRESS
        self.usdt_address = self._get_usdt_address()
        
        # Initialize TRON client
        headers = {}
        if self.settings.TRONGRID_API_KEY:
            headers["TRON-PRO-API-KEY"] = self.settings.TRONGRID_API_KEY
        
        self.provider = HTTPProvider(
            self.endpoint, 
            client=httpx.Client(headers=headers, timeout=30)
        )
        self.tron = Tron(provider=self.provider)
        
        # Router configuration
        self.config = RouterConfig(
            contract_address=self.payout_router_address,
            owner_address=self.settings.TRON_ADDRESS or "",
            private_key=self.settings.TRON_PRIVATE_KEY or "",
            usdt_contract_address=self.usdt_address,
            gas_limit=int(os.getenv("PAYOUT_GAS_LIMIT", "1000000")),
            energy_limit=int(os.getenv("PAYOUT_ENERGY_LIMIT", "10000000")),
            fee_limit=int(os.getenv("PAYOUT_FEE_LIMIT", "1000000000")),
            max_payout_amount=float(os.getenv("MAX_PAYOUT_AMOUNT", "1000.0")),
            daily_limit=float(os.getenv("DAILY_PAYOUT_LIMIT", "10000.0")),
            min_payout_amount=float(os.getenv("MIN_PAYOUT_AMOUNT", "0.01")),
            batch_size=int(os.getenv("PAYOUT_BATCH_SIZE", "50")),
            confirmation_blocks=int(os.getenv("CONFIRMATION_BLOCKS", "19"))
        )
        
        # Data storage
        self.data_dir = Path("/data/payment-systems/payout-router-v0")
        self.payouts_dir = self.data_dir / "payouts"
        self.logs_dir = self.data_dir / "logs"
        
        # Ensure directories exist
        for directory in [self.payouts_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Payout tracking
        self.pending_payouts: Dict[str, PayoutTransaction] = {}
        self.confirmed_payouts: Dict[str, PayoutTransaction] = {}
        
        # Daily limits tracking
        self.daily_payouts: Dict[str, float] = {}  # date -> total_amount
        self.last_reset_date = datetime.now().date()
        
        # Load existing payouts
        asyncio.create_task(self._load_existing_payouts())
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_pending_payouts())
        asyncio.create_task(self._cleanup_old_payouts())
        
        logger.info(f"PayoutRouterV0 initialized: {self.network} -> {self.endpoint}")
    
    def _resolve_endpoint(self) -> str:
        """Resolve TRON endpoint"""
        if self.settings.TRON_HTTP_ENDPOINT:
            return self.settings.TRON_HTTP_ENDPOINT
        
        if self.network.lower() == "shasta":
            return "https://api.shasta.trongrid.io"
        
        return "https://api.trongrid.io"
    
    def _get_usdt_address(self) -> str:
        """Get USDT contract address for network"""
        if self.network.lower() == "mainnet":
            return "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # USDT-TRC20 mainnet
        else:
            return "TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs"  # USDT-TRC20 shasta
    
    async def _load_existing_payouts(self):
        """Load existing payouts from disk"""
        try:
            payouts_file = self.payouts_dir / "payouts_registry.json"
            if payouts_file.exists():
                async with aiofiles.open(payouts_file, "r") as f:
                    data = await f.read()
                    payouts_data = json.loads(data)
                    
                    for payout_id, payout_data in payouts_data.items():
                        # Convert datetime strings back to datetime objects
                        if 'created_at' in payout_data:
                            payout_data['created_at'] = datetime.fromisoformat(payout_data['created_at'])
                        if 'confirmed_at' in payout_data and payout_data['confirmed_at']:
                            payout_data['confirmed_at'] = datetime.fromisoformat(payout_data['confirmed_at'])
                        if 'expires_at' in payout_data and payout_data['expires_at']:
                            payout_data['expires_at'] = datetime.fromisoformat(payout_data['expires_at'])
                        
                        payout_transaction = PayoutTransaction(**payout_data)
                        
                        if payout_transaction.status == PayoutStatus.PENDING:
                            self.pending_payouts[payout_id] = payout_transaction
                        else:
                            self.confirmed_payouts[payout_id] = payout_transaction
                    
                logger.info(f"Loaded {len(self.pending_payouts)} pending and {len(self.confirmed_payouts)} confirmed payouts")
                
        except Exception as e:
            logger.error(f"Error loading existing payouts: {e}")
    
    async def _save_payouts_registry(self):
        """Save payouts registry to disk"""
        try:
            all_payouts = {**self.pending_payouts, **self.confirmed_payouts}
            
            payouts_data = {}
            for payout_id, payout_transaction in all_payouts.items():
                # Convert to dict and handle datetime serialization
                payout_dict = asdict(payout_transaction)
                if payout_dict['created_at']:
                    payout_dict['created_at'] = payout_dict['created_at'].isoformat()
                if payout_dict['confirmed_at']:
                    payout_dict['confirmed_at'] = payout_dict['confirmed_at'].isoformat()
                if payout_dict['expires_at']:
                    payout_dict['expires_at'] = payout_dict['expires_at'].isoformat()
                payouts_data[payout_id] = payout_dict
            
            payouts_file = self.payouts_dir / "payouts_registry.json"
            async with aiofiles.open(payouts_file, "w") as f:
                await f.write(json.dumps(payouts_data, indent=2))
                
        except Exception as e:
            logger.error(f"Error saving payouts registry: {e}")
    
    async def create_payout(self, request: PayoutRequestModel) -> PayoutResponseModel:
        """Create a new USDT payout via PayoutRouterV0"""
        try:
            logger.info(f"Creating payout: {request.amount_usdt} USDT to {request.recipient_address}")
            
            # Validate payout request
            await self._validate_payout_request(request)
            
            # Generate payout ID
            payout_id = await self._generate_payout_id(request)
            
            # Convert to internal request format
            payout_request = PayoutRequest(
                recipient_address=request.recipient_address,
                amount_usdt=request.amount_usdt,
                reason=PayoutReason(request.reason),
                payout_type=PayoutType(request.payout_type),
                session_id=request.session_id,
                node_id=request.node_id,
                work_credits=request.work_credits,
                custom_data=request.custom_data,
                expires_at=datetime.fromisoformat(request.expires_at) if request.expires_at else None
            )
            
            # Create payout transaction
            payout_transaction = PayoutTransaction(
                payout_id=payout_id,
                request=payout_request,
                created_at=datetime.now()
            )
            
            # Process payout based on type
            if request.payout_type == PayoutType.IMMEDIATE:
                txid = await self._execute_immediate_payout(payout_transaction)
                payout_transaction.txid = txid
                payout_transaction.status = PayoutStatus.PENDING
            elif request.payout_type == PayoutType.BATCH:
                payout_transaction.status = PayoutStatus.PENDING
                # Will be processed in next batch
            else:
                payout_transaction.status = PayoutStatus.PENDING
                # Will be processed according to schedule
            
            # Store payout
            self.pending_payouts[payout_id] = payout_transaction
            
            # Update daily limits
            await self._update_daily_limits(request.amount_usdt)
            
            # Save registry
            await self._save_payouts_registry()
            
            # Log payout creation
            await self._log_payout_event(payout_id, "payout_created", {
                "recipient_address": request.recipient_address,
                "amount_usdt": request.amount_usdt,
                "reason": request.reason,
                "payout_type": request.payout_type,
                "txid": payout_transaction.txid
            })
            
            logger.info(f"Created payout: {payout_id} -> {payout_transaction.txid}")
            
            # Calculate estimated confirmation time
            estimated_confirmation = None
            if payout_transaction.txid:
                current_block = self.tron.get_latest_block_number()
                estimated_block = current_block + self.config.confirmation_blocks
                # Rough estimate: 3 seconds per block
                estimated_time = datetime.now() + timedelta(seconds=self.config.confirmation_blocks * 3)
                estimated_confirmation = estimated_time.isoformat()
            
            return PayoutResponseModel(
                payout_id=payout_id,
                txid=payout_transaction.txid,
                status=payout_transaction.status.value,
                message="Payout created successfully",
                amount_usdt=request.amount_usdt,
                recipient_address=request.recipient_address,
                created_at=payout_transaction.created_at.isoformat(),
                estimated_confirmation=estimated_confirmation
            )
            
        except Exception as e:
            logger.error(f"Error creating payout: {e}")
            raise
    
    async def _validate_payout_request(self, request: PayoutRequestModel):
        """Validate payout request"""
        # Check amount limits
        if request.amount_usdt < self.config.min_payout_amount:
            raise ValueError(f"Amount too small: {request.amount_usdt} < {self.config.min_payout_amount}")
        
        if request.amount_usdt > self.config.max_payout_amount:
            raise ValueError(f"Amount too large: {request.amount_usdt} > {self.config.max_payout_amount}")
        
        # Check daily limits
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.daily_payouts = {}
            self.last_reset_date = today
        
        daily_total = self.daily_payouts.get(today.isoformat(), 0.0)
        if daily_total + request.amount_usdt > self.config.daily_limit:
            raise ValueError(f"Daily limit exceeded: {daily_total + request.amount_usdt} > {self.config.daily_limit}")
        
        # Validate TRON address
        try:
            # Basic TRON address validation
            if not request.recipient_address.startswith('T') or len(request.recipient_address) != 34:
                raise ValueError("Invalid TRON address format")
        except Exception as e:
            raise ValueError(f"Invalid recipient address: {e}")
        
        # Check contract balance
        await self._check_contract_balance(request.amount_usdt)
    
    async def _check_contract_balance(self, amount_usdt: float):
        """Check if contract has sufficient USDT balance"""
        try:
            # Get contract USDT balance
            usdt_contract = self.tron.get_contract(self.usdt_address)
            balance_response = usdt_contract.functions.balanceOf(self.config.contract_address)
            
            # Convert from smallest unit (6 decimals for USDT)
            balance_usdt = balance_response / 1_000_000
            
            if balance_usdt < amount_usdt:
                raise RuntimeError(f"Insufficient contract balance: {balance_usdt} < {amount_usdt}")
            
            logger.debug(f"Contract USDT balance: {balance_usdt}")
            
        except Exception as e:
            logger.error(f"Error checking contract balance: {e}")
            raise
    
    async def _generate_payout_id(self, request: PayoutRequestModel) -> str:
        """Generate unique payout ID"""
        timestamp = int(time.time())
        recipient_hash = hashlib.sha256(request.recipient_address.encode()).hexdigest()[:8]
        amount_hash = hashlib.sha256(str(request.amount_usdt).encode()).hexdigest()[:4]
        
        return f"payout_v0_{timestamp}_{recipient_hash}_{amount_hash}"
    
    async def _execute_immediate_payout(self, payout_transaction: PayoutTransaction) -> str:
        """Execute immediate USDT payout"""
        try:
            if not self.config.private_key:
                raise RuntimeError("Private key not configured")
            
            # Initialize private key
            private_key = PrivateKey(bytes.fromhex(self.config.private_key))
            from_address = private_key.public_key.to_base58check_address()
            
            # Get contract instance
            payout_contract = self.tron.get_contract(self.config.contract_address)
            
            # Convert amount to smallest unit
            amount_sun = int(payout_transaction.request.amount_usdt * 1_000_000)
            
            # Build transaction
            transaction = payout_contract.functions.payout(
                payout_transaction.request.recipient_address,
                amount_sun
            ).with_owner(from_address).fee_limit(self.config.fee_limit)
            
            # Sign and broadcast transaction
            signed_tx = transaction.build().sign(private_key)
            result = signed_tx.broadcast()
            
            if result.get('result'):
                txid = result['txid']
                logger.info(f"Payout transaction broadcasted: {txid}")
                return txid
            else:
                raise RuntimeError(f"Transaction failed: {result}")
                
        except Exception as e:
            logger.error(f"Error executing immediate payout: {e}")
            raise
    
    async def _update_daily_limits(self, amount_usdt: float):
        """Update daily payout limits"""
        today = datetime.now().date().isoformat()
        self.daily_payouts[today] = self.daily_payouts.get(today, 0.0) + amount_usdt
    
    async def _monitor_pending_payouts(self):
        """Monitor pending payouts for confirmation"""
        try:
            while True:
                for payout_id, payout_transaction in list(self.pending_payouts.items()):
                    if payout_transaction.txid:
                        # Check transaction status
                        status = await self._check_transaction_status(payout_transaction.txid)
                        
                        if status == "confirmed":
                            payout_transaction.status = PayoutStatus.CONFIRMED
                            payout_transaction.confirmed_at = datetime.now()
                            
                            # Move to confirmed payouts
                            self.confirmed_payouts[payout_id] = payout_transaction
                            del self.pending_payouts[payout_id]
                            
                            # Log confirmation
                            await self._log_payout_event(payout_id, "payout_confirmed", {
                                "txid": payout_transaction.txid,
                                "amount_usdt": payout_transaction.request.amount_usdt,
                                "recipient_address": payout_transaction.request.recipient_address
                            })
                            
                            logger.info(f"Payout confirmed: {payout_id} -> {payout_transaction.txid}")
                        
                        elif status == "failed":
                            payout_transaction.status = PayoutStatus.FAILED
                            payout_transaction.error_message = "Transaction failed on blockchain"
                            
                            # Log failure
                            await self._log_payout_event(payout_id, "payout_failed", {
                                "txid": payout_transaction.txid,
                                "error": payout_transaction.error_message
                            })
                            
                            logger.error(f"Payout failed: {payout_id} -> {payout_transaction.txid}")
                
                # Save registry
                await self._save_payouts_registry()
                
                # Wait before next check
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            logger.info("Payout monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in payout monitoring: {e}")
    
    async def _check_transaction_status(self, txid: str) -> str:
        """Check transaction status on blockchain"""
        try:
            transaction_info = self.tron.get_transaction_info(txid)
            
            if not transaction_info:
                return "pending"
            
            receipt = transaction_info.get('receipt', {})
            if receipt.get('result') == 'SUCCESS':
                return "confirmed"
            else:
                return "failed"
                
        except Exception as e:
            logger.debug(f"Error checking transaction status: {e}")
            return "pending"
    
    async def _cleanup_old_payouts(self):
        """Clean up old confirmed payouts"""
        try:
            while True:
                cutoff_date = datetime.now() - timedelta(days=30)
                
                old_payouts = []
                for payout_id, payout_transaction in self.confirmed_payouts.items():
                    if (payout_transaction.confirmed_at and 
                        payout_transaction.confirmed_at < cutoff_date):
                        old_payouts.append(payout_id)
                
                # Remove old payouts
                for payout_id in old_payouts:
                    del self.confirmed_payouts[payout_id]
                
                if old_payouts:
                    await self._save_payouts_registry()
                    logger.info(f"Cleaned up {len(old_payouts)} old payouts")
                
                # Wait before next cleanup
                await asyncio.sleep(3600)  # 1 hour
                
        except asyncio.CancelledError:
            logger.info("Payout cleanup cancelled")
        except Exception as e:
            logger.error(f"Error in payout cleanup: {e}")
    
    async def get_payout_status(self, payout_id: str) -> Optional[Dict[str, Any]]:
        """Get payout status"""
        try:
            # Check pending payouts
            if payout_id in self.pending_payouts:
                payout = self.pending_payouts[payout_id]
            elif payout_id in self.confirmed_payouts:
                payout = self.confirmed_payouts[payout_id]
            else:
                return None
            
            return {
                "payout_id": payout.payout_id,
                "recipient_address": payout.request.recipient_address,
                "amount_usdt": payout.request.amount_usdt,
                "reason": payout.request.reason.value,
                "status": payout.status.value,
                "txid": payout.txid,
                "created_at": payout.created_at.isoformat(),
                "confirmed_at": payout.confirmed_at.isoformat() if payout.confirmed_at else None,
                "error_message": payout.error_message,
                "retry_count": payout.retry_count
            }
            
        except Exception as e:
            logger.error(f"Error getting payout status: {e}")
            return None
    
    async def list_payouts(self, status: Optional[PayoutStatus] = None, 
                          limit: int = 100) -> List[Dict[str, Any]]:
        """List payouts with optional status filter"""
        try:
            all_payouts = {**self.pending_payouts, **self.confirmed_payouts}
            
            if status:
                filtered_payouts = {k: v for k, v in all_payouts.items() 
                                  if v.status == status}
            else:
                filtered_payouts = all_payouts
            
            # Sort by creation time (newest first)
            sorted_payouts = sorted(filtered_payouts.items(), 
                                  key=lambda x: x[1].created_at, reverse=True)
            
            # Limit results
            limited_payouts = sorted_payouts[:limit]
            
            payouts_list = []
            for payout_id, payout in limited_payouts:
                payouts_list.append({
                    "payout_id": payout.payout_id,
                    "recipient_address": payout.request.recipient_address,
                    "amount_usdt": payout.request.amount_usdt,
                    "reason": payout.request.reason.value,
                    "status": payout.status.value,
                    "txid": payout.txid,
                    "created_at": payout.created_at.isoformat(),
                    "confirmed_at": payout.confirmed_at.isoformat() if payout.confirmed_at else None,
                    "error_message": payout.error_message
                })
            
            return payouts_list
            
        except Exception as e:
            logger.error(f"Error listing payouts: {e}")
            return []
    
    async def get_payout_stats(self) -> Dict[str, Any]:
        """Get payout statistics"""
        try:
            all_payouts = {**self.pending_payouts, **self.confirmed_payouts}
            
            total_payouts = len(all_payouts)
            pending_payouts = len(self.pending_payouts)
            confirmed_payouts = len(self.confirmed_payouts)
            failed_payouts = sum(1 for p in all_payouts.values() 
                               if p.status == PayoutStatus.FAILED)
            
            total_amount = sum(p.request.amount_usdt for p in all_payouts.values())
            confirmed_amount = sum(p.request.amount_usdt for p in all_payouts.values() 
                                 if p.status == PayoutStatus.CONFIRMED)
            
            # Daily statistics
            today = datetime.now().date().isoformat()
            daily_amount = self.daily_payouts.get(today, 0.0)
            daily_count = sum(1 for p in all_payouts.values() 
                            if p.created_at.date().isoformat() == today)
            
            return {
                "total_payouts": total_payouts,
                "pending_payouts": pending_payouts,
                "confirmed_payouts": confirmed_payouts,
                "failed_payouts": failed_payouts,
                "total_amount_usdt": total_amount,
                "confirmed_amount_usdt": confirmed_amount,
                "daily_amount_usdt": daily_amount,
                "daily_count": daily_count,
                "daily_limit_usdt": self.config.daily_limit,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting payout stats: {e}")
            return {"error": str(e)}
    
    async def _log_payout_event(self, payout_id: str, event_type: str, data: Dict[str, Any]):
        """Log payout event"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "payout_id": payout_id,
                "event_type": event_type,
                "data": data
            }
            
            log_file = self.logs_dir / f"payout_events_{datetime.now().strftime('%Y%m%d')}.log"
            async with aiofiles.open(log_file, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging payout event: {e}")

# Global instance
payout_router_v0 = PayoutRouterV0()

# Convenience functions for external use
async def create_payout(request: PayoutRequestModel) -> PayoutResponseModel:
    """Create a new payout via PayoutRouterV0"""
    return await payout_router_v0.create_payout(request)

async def get_payout_status(payout_id: str) -> Optional[Dict[str, Any]]:
    """Get payout status"""
    return await payout_router_v0.get_payout_status(payout_id)

async def list_payouts(status: Optional[PayoutStatus] = None, 
                      limit: int = 100) -> List[Dict[str, Any]]:
    """List payouts"""
    return await payout_router_v0.list_payouts(status, limit)

async def get_payout_stats() -> Dict[str, Any]:
    """Get payout statistics"""
    return await payout_router_v0.get_payout_stats()

if __name__ == "__main__":
    # Example usage
    async def main():
        # Create a payout request
        payout_request = PayoutRequestModel(
            recipient_address="TYourTRONAddressHere123456789",
            amount_usdt=10.0,
            reason=PayoutReason.SESSION_RELAY,
            payout_type=PayoutType.IMMEDIATE,
            session_id="session_123",
            work_credits=5.5
        )
        
        try:
            # Create payout
            response = await create_payout(payout_request)
            print(f"Payout created: {response}")
            
            # Get status
            status = await get_payout_status(response.payout_id)
            print(f"Payout status: {status}")
            
            # List recent payouts
            payouts = await list_payouts(limit=10)
            print(f"Recent payouts: {len(payouts)}")
            
            # Get statistics
            stats = await get_payout_stats()
            print(f"Payout stats: {stats}")
            
        except Exception as e:
            print(f"Error: {e}")
    
    asyncio.run(main())
