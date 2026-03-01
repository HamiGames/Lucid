"""
LUCID Payment Systems - TRX Staking Service
TRX staking and resource management for TRON network
Distroless container: lucid-trx-staking:latest
"""

import asyncio
import logging
import os
import time
import hashlib
import json
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import aiofiles
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StakingType(Enum):
    """Staking types"""
    FREEZE_BALANCE = "freeze_balance"
    UNFREEZE_BALANCE = "unfreeze_balance"
    VOTE_WITNESS = "vote_witness"
    DELEGATE_RESOURCE = "delegate_resource"
    UNDELEGATE_RESOURCE = "undelegate_resource"

class StakingStatus(Enum):
    """Staking status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class ResourceType(Enum):
    """Resource types"""
    ENERGY = "energy"
    BANDWIDTH = "bandwidth"

@dataclass
class StakingInfo:
    """Staking information"""
    staking_id: str
    wallet_address: str
    staking_type: StakingType
    amount_trx: float
    amount_sun: int
    duration: int  # Duration in days
    resource_type: Optional[ResourceType]
    witness_address: Optional[str]
    delegate_address: Optional[str]
    status: StakingStatus
    created_at: datetime
    expires_at: Optional[datetime]
    last_updated: datetime
    transaction_id: Optional[str] = None
    block_number: Optional[int] = None

@dataclass
class ResourceInfo:
    """Resource information"""
    wallet_address: str
    energy_available: int
    energy_used: int
    energy_limit: int
    bandwidth_available: int
    bandwidth_used: int
    bandwidth_limit: int
    frozen_balance: float
    frozen_balance_sun: int
    delegated_energy: int
    delegated_bandwidth: int
    last_updated: datetime

class StakingRequest(BaseModel):
    """Staking request"""
    wallet_address: str = Field(..., description="Wallet address")
    staking_type: StakingType = Field(..., description="Type of staking")
    amount_trx: float = Field(..., gt=0, description="Amount in TRX")
    duration_days: int = Field(..., gt=0, description="Duration in days")
    resource_type: Optional[ResourceType] = Field(None, description="Resource type for delegation")
    witness_address: Optional[str] = Field(None, description="Witness address for voting")
    delegate_address: Optional[str] = Field(None, description="Delegate address for resource delegation")
    private_key: str = Field(..., description="Private key for signing")

class StakingResponse(BaseModel):
    """Staking response"""
    staking_id: str
    transaction_id: str
    status: str
    amount_trx: float
    duration_days: int
    expires_at: str
    created_at: str

class UnstakingRequest(BaseModel):
    """Unstaking request"""
    staking_id: str = Field(..., description="Staking ID to unstake")
    private_key: str = Field(..., description="Private key for signing")

class UnstakingResponse(BaseModel):
    """Unstaking response"""
    staking_id: str
    transaction_id: str
    status: str
    amount_trx: float
    created_at: str

class ResourceInfoResponse(BaseModel):
    """Resource info response"""
    wallet_address: str
    energy_available: int
    energy_used: int
    energy_limit: int
    bandwidth_available: int
    bandwidth_used: int
    bandwidth_limit: int
    frozen_balance: float
    delegated_energy: int
    delegated_bandwidth: int
    last_updated: str

class TRXStakingService:
    """TRX staking service"""
    
    def __init__(self):
        self.settings = get_settings()
        
        # TRON client configuration - from environment variables
        self.tron_client_url = os.getenv("TRON_CLIENT_URL", os.getenv("TRX_STAKING_TRON_CLIENT_URL", "http://lucid-tron-client:8091"))
        
        # Initialize TRON client
        self._initialize_tron_client()
        
        # Data storage - from environment variables
        data_base = os.getenv("DATA_DIRECTORY", os.getenv("TRON_DATA_DIR", "/data/payment-systems"))
        self.data_dir = Path(data_base) / "trx-staking"
        self.staking_dir = self.data_dir / "staking"
        self.resources_dir = self.data_dir / "resources"
        self.logs_dir = self.data_dir / "logs"
        
        # Ensure directories exist
        for directory in [self.staking_dir, self.resources_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Staking tracking
        self.staking_records: Dict[str, StakingInfo] = {}
        self.resource_info: Dict[str, ResourceInfo] = {}
        
        # Load existing data
        asyncio.create_task(self._load_existing_data())
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_staking())
        asyncio.create_task(self._monitor_resources())
        asyncio.create_task(self._cleanup_old_data())
        
        logger.info("TRXStakingService initialized")
    
    def _initialize_tron_client(self):
        """Initialize TRON client connection"""
        try:
            # In production, this would connect to the TRON client service
            # For now, we'll use direct TRON connection
            self.tron = Tron()
            logger.info("TRON client initialized for staking")
        except Exception as e:
            logger.error(f"Failed to initialize TRON client: {e}")
            raise
    
    async def _load_existing_data(self):
        """Load existing data from disk"""
        try:
            # Load staking records
            staking_file = self.staking_dir / "staking_registry.json"
            if staking_file.exists():
                async with aiofiles.open(staking_file, "r") as f:
                    data = await f.read()
                    staking_data = json.loads(data)
                    
                    for staking_id, staking_record in staking_data.items():
                        # Convert datetime strings back to datetime objects
                        for field in ['created_at', 'expires_at', 'last_updated']:
                            if field in staking_record and staking_record[field]:
                                staking_record[field] = datetime.fromisoformat(staking_record[field])
                        
                        staking_info = StakingInfo(**staking_record)
                        self.staking_records[staking_id] = staking_info
                    
                logger.info(f"Loaded {len(self.staking_records)} existing staking records")
            
            # Load resource info
            resources_file = self.resources_dir / "resources_registry.json"
            if resources_file.exists():
                async with aiofiles.open(resources_file, "r") as f:
                    data = await f.read()
                    resources_data = json.loads(data)
                    
                    for wallet_address, resource_data in resources_data.items():
                        # Convert datetime strings back to datetime objects
                        if 'last_updated' in resource_data and resource_data['last_updated']:
                            resource_data['last_updated'] = datetime.fromisoformat(resource_data['last_updated'])
                        
                        resource_info = ResourceInfo(**resource_data)
                        self.resource_info[wallet_address] = resource_info
                    
                logger.info(f"Loaded {len(self.resource_info)} existing resource records")
                
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
    
    async def _save_staking_registry(self):
        """Save staking registry to disk"""
        try:
            staking_data = {}
            for staking_id, staking_info in self.staking_records.items():
                # Convert to dict and handle datetime serialization
                staking_dict = asdict(staking_info)
                for field in ['created_at', 'expires_at', 'last_updated']:
                    if staking_dict.get(field):
                        staking_dict[field] = staking_dict[field].isoformat()
                staking_data[staking_id] = staking_dict
            
            staking_file = self.staking_dir / "staking_registry.json"
            async with aiofiles.open(staking_file, "w") as f:
                await f.write(json.dumps(staking_data, indent=2))
                
        except Exception as e:
            logger.error(f"Error saving staking registry: {e}")
    
    async def _save_resources_registry(self):
        """Save resources registry to disk"""
        try:
            resources_data = {}
            for wallet_address, resource_info in self.resource_info.items():
                # Convert to dict and handle datetime serialization
                resource_dict = asdict(resource_info)
                if resource_dict.get('last_updated'):
                    resource_dict['last_updated'] = resource_dict['last_updated'].isoformat()
                resources_data[wallet_address] = resource_dict
            
            resources_file = self.resources_dir / "resources_registry.json"
            async with aiofiles.open(resources_file, "w") as f:
                await f.write(json.dumps(resources_data, indent=2))
                
        except Exception as e:
            logger.error(f"Error saving resources registry: {e}")
    
    async def stake_trx(self, request: StakingRequest) -> StakingResponse:
        """Stake TRX for resources"""
        try:
            logger.info(f"Staking TRX: {request.amount_trx} TRX for {request.duration_days} days")
            
            # Convert TRX to SUN
            amount_sun = int(request.amount_trx * 1_000_000)
            
            # Generate staking ID
            staking_id = f"stake_{int(time.time())}_{hashlib.sha256(request.wallet_address.encode()).hexdigest()[:8]}"
            
            # Create private key object
            private_key = PrivateKey(bytes.fromhex(request.private_key))
            
            # Calculate expiration
            expires_at = datetime.now() + timedelta(days=request.duration_days)
            
            # Create staking transaction based on type
            if request.staking_type == StakingType.FREEZE_BALANCE:
                # Freeze balance for energy
                txn = self.tron.trx.freeze_balance(
                    request.wallet_address,
                    amount_sun,
                    request.duration_days,
                    "ENERGY"
                ).build().sign(private_key)
                
            elif request.staking_type == StakingType.VOTE_WITNESS:
                # Vote for witness
                if not request.witness_address:
                    raise ValueError("Witness address required for voting")
                
                txn = self.tron.trx.vote_witness_account(
                    request.wallet_address,
                    request.witness_address,
                    amount_sun
                ).build().sign(private_key)
                
            elif request.staking_type == StakingType.DELEGATE_RESOURCE:
                # Delegate resources
                if not request.delegate_address:
                    raise ValueError("Delegate address required for resource delegation")
                
                if not request.resource_type:
                    raise ValueError("Resource type required for delegation")
                
                txn = self.tron.trx.delegate_resource(
                    request.wallet_address,
                    request.delegate_address,
                    amount_sun,
                    request.resource_type.value
                ).build().sign(private_key)
                
            else:
                raise ValueError(f"Unsupported staking type: {request.staking_type}")
            
            # Broadcast transaction
            result = txn.broadcast()
            
            if result.get("result"):
                transaction_id = result["txid"]
                
                # Create staking info
                staking_info = StakingInfo(
                    staking_id=staking_id,
                    wallet_address=request.wallet_address,
                    staking_type=request.staking_type,
                    amount_trx=request.amount_trx,
                    amount_sun=amount_sun,
                    duration=request.duration_days,
                    resource_type=request.resource_type,
                    witness_address=request.witness_address,
                    delegate_address=request.delegate_address,
                    status=StakingStatus.ACTIVE,
                    created_at=datetime.now(),
                    expires_at=expires_at,
                    last_updated=datetime.now(),
                    transaction_id=transaction_id
                )
                
                # Store staking record
                self.staking_records[staking_id] = staking_info
                
                # Save registry
                await self._save_staking_registry()
                
                # Log staking event
                await self._log_staking_event(staking_id, "trx_staked", {
                    "wallet_address": request.wallet_address,
                    "amount_trx": request.amount_trx,
                    "duration_days": request.duration_days,
                    "staking_type": request.staking_type.value,
                    "transaction_id": transaction_id
                })
                
                logger.info(f"TRX staked: {staking_id} -> {transaction_id}")
                
                return StakingResponse(
                    staking_id=staking_id,
                    transaction_id=transaction_id,
                    status=StakingStatus.ACTIVE.value,
                    amount_trx=request.amount_trx,
                    duration_days=request.duration_days,
                    expires_at=expires_at.isoformat(),
                    created_at=staking_info.created_at.isoformat()
                )
            else:
                raise RuntimeError(f"Staking transaction failed: {result}")
                
        except Exception as e:
            logger.error(f"Error staking TRX: {e}")
            raise
    
    async def unstake_trx(self, request: UnstakingRequest) -> UnstakingResponse:
        """Unstake TRX"""
        try:
            if request.staking_id not in self.staking_records:
                raise ValueError("Staking record not found")
            
            staking_info = self.staking_records[request.staking_id]
            
            logger.info(f"Unstaking TRX: {staking_info.amount_trx} TRX from {request.staking_id}")
            
            # Create private key object
            private_key = PrivateKey(bytes.fromhex(request.private_key))
            
            # Create unstaking transaction based on type
            if staking_info.staking_type == StakingType.FREEZE_BALANCE:
                # Unfreeze balance
                txn = self.tron.trx.unfreeze_balance(
                    staking_info.wallet_address,
                    staking_info.amount_sun,
                    "ENERGY"
                ).build().sign(private_key)
                
            elif staking_info.staking_type == StakingType.VOTE_WITNESS:
                # Unvote witness
                txn = self.tron.trx.unvote_witness_account(
                    staking_info.wallet_address,
                    staking_info.witness_address
                ).build().sign(private_key)
                
            elif staking_info.staking_type == StakingType.DELEGATE_RESOURCE:
                # Undelegate resources
                txn = self.tron.trx.undelegate_resource(
                    staking_info.wallet_address,
                    staking_info.delegate_address,
                    staking_info.amount_sun,
                    staking_info.resource_type.value
                ).build().sign(private_key)
                
            else:
                raise ValueError(f"Unsupported unstaking type: {staking_info.staking_type}")
            
            # Broadcast transaction
            result = txn.broadcast()
            
            if result.get("result"):
                transaction_id = result["txid"]
                
                # Update staking status
                staking_info.status = StakingStatus.CANCELLED
                staking_info.last_updated = datetime.now()
                
                # Save registry
                await self._save_staking_registry()
                
                # Log unstaking event
                await self._log_staking_event(request.staking_id, "trx_unstaked", {
                    "wallet_address": staking_info.wallet_address,
                    "amount_trx": staking_info.amount_trx,
                    "transaction_id": transaction_id
                })
                
                logger.info(f"TRX unstaked: {request.staking_id} -> {transaction_id}")
                
                return UnstakingResponse(
                    staking_id=request.staking_id,
                    transaction_id=transaction_id,
                    status=StakingStatus.CANCELLED.value,
                    amount_trx=staking_info.amount_trx,
                    created_at=staking_info.last_updated.isoformat()
                )
            else:
                raise RuntimeError(f"Unstaking transaction failed: {result}")
                
        except Exception as e:
            logger.error(f"Error unstaking TRX: {e}")
            raise
    
    async def get_resource_info(self, wallet_address: str) -> ResourceInfoResponse:
        """Get resource information"""
        try:
            logger.info(f"Getting resource info for: {wallet_address}")
            
            # Get account resources from TRON network
            account_resources = self.tron.get_account_resources(wallet_address)
            account = self.tron.get_account(wallet_address)
            
            # Create resource info
            resource_info = ResourceInfo(
                wallet_address=wallet_address,
                energy_available=account_resources.get("EnergyLimit", 0),
                energy_used=account_resources.get("EnergyUsed", 0),
                energy_limit=account_resources.get("EnergyLimit", 0),
                bandwidth_available=account_resources.get("NetLimit", 0),
                bandwidth_used=account_resources.get("NetUsed", 0),
                bandwidth_limit=account_resources.get("NetLimit", 0),
                frozen_balance=account.get("frozen", [{}])[0].get("frozen_balance", 0) / 1_000_000,
                frozen_balance_sun=account.get("frozen", [{}])[0].get("frozen_balance", 0),
                delegated_energy=account_resources.get("delegated_frozenV2_energy", 0),
                delegated_bandwidth=account_resources.get("delegated_frozenV2_bandwidth", 0),
                last_updated=datetime.now()
            )
            
            # Store resource info
            self.resource_info[wallet_address] = resource_info
            
            # Save registry
            await self._save_resources_registry()
            
            logger.info(f"Resource info updated for {wallet_address}")
            
            return ResourceInfoResponse(
                wallet_address=wallet_address,
                energy_available=resource_info.energy_available,
                energy_used=resource_info.energy_used,
                energy_limit=resource_info.energy_limit,
                bandwidth_available=resource_info.bandwidth_available,
                bandwidth_used=resource_info.bandwidth_used,
                bandwidth_limit=resource_info.bandwidth_limit,
                frozen_balance=resource_info.frozen_balance,
                delegated_energy=resource_info.delegated_energy,
                delegated_bandwidth=resource_info.delegated_bandwidth,
                last_updated=resource_info.last_updated.isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error getting resource info: {e}")
            raise
    
    async def list_staking_records(self, wallet_address: Optional[str] = None) -> List[StakingInfo]:
        """List staking records"""
        try:
            staking_list = []
            
            for staking_info in self.staking_records.values():
                if wallet_address is None or staking_info.wallet_address == wallet_address:
                    staking_list.append(staking_info)
            
            return staking_list
            
        except Exception as e:
            logger.error(f"Error listing staking records: {e}")
            return []
    
    async def _monitor_staking(self):
        """Monitor staking records"""
        try:
            while True:
                for staking_id, staking_info in self.staking_records.items():
                    try:
                        # Check if staking has expired
                        if (staking_info.expires_at and 
                            staking_info.expires_at < datetime.now() and 
                            staking_info.status == StakingStatus.ACTIVE):
                            
                            staking_info.status = StakingStatus.EXPIRED
                            staking_info.last_updated = datetime.now()
                            
                            # Log expiration
                            await self._log_staking_event(staking_id, "staking_expired", {
                                "wallet_address": staking_info.wallet_address,
                                "amount_trx": staking_info.amount_trx,
                                "expires_at": staking_info.expires_at.isoformat()
                            })
                            
                            logger.info(f"Staking expired: {staking_id}")
                        
                    except Exception as e:
                        logger.error(f"Error monitoring staking {staking_id}: {e}")
                
                # Save registry
                await self._save_staking_registry()
                
                # Wait before next check
                await asyncio.sleep(3600)  # Check every hour
                
        except asyncio.CancelledError:
            logger.info("Staking monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in staking monitoring: {e}")
    
    async def _monitor_resources(self):
        """Monitor resource information"""
        try:
            while True:
                for wallet_address, resource_info in self.resource_info.items():
                    try:
                        # Update resource info from TRON network
                        account_resources = self.tron.get_account_resources(wallet_address)
                        account = self.tron.get_account(wallet_address)
                        
                        # Update resource info
                        resource_info.energy_available = account_resources.get("EnergyLimit", 0)
                        resource_info.energy_used = account_resources.get("EnergyUsed", 0)
                        resource_info.energy_limit = account_resources.get("EnergyLimit", 0)
                        resource_info.bandwidth_available = account_resources.get("NetLimit", 0)
                        resource_info.bandwidth_used = account_resources.get("NetUsed", 0)
                        resource_info.bandwidth_limit = account_resources.get("NetLimit", 0)
                        resource_info.frozen_balance = account.get("frozen", [{}])[0].get("frozen_balance", 0) / 1_000_000
                        resource_info.frozen_balance_sun = account.get("frozen", [{}])[0].get("frozen_balance", 0)
                        resource_info.delegated_energy = account_resources.get("delegated_frozenV2_energy", 0)
                        resource_info.delegated_bandwidth = account_resources.get("delegated_frozenV2_bandwidth", 0)
                        resource_info.last_updated = datetime.now()
                        
                    except Exception as e:
                        logger.error(f"Error monitoring resources for {wallet_address}: {e}")
                
                # Save registry
                await self._save_resources_registry()
                
                # Wait before next check
                await asyncio.sleep(1800)  # Check every 30 minutes
                
        except asyncio.CancelledError:
            logger.info("Resource monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in resource monitoring: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old data"""
        try:
            while True:
                cutoff_date = datetime.now() - timedelta(days=90)
                
                # Clean up old expired staking records
                old_staking = []
                for staking_id, staking_info in self.staking_records.items():
                    if (staking_info.status == StakingStatus.EXPIRED and 
                        staking_info.last_updated < cutoff_date):
                        old_staking.append(staking_id)
                
                for staking_id in old_staking:
                    del self.staking_records[staking_id]
                
                if old_staking:
                    await self._save_staking_registry()
                    logger.info(f"Cleaned up {len(old_staking)} old staking records")
                
                # Wait before next cleanup
                await asyncio.sleep(3600)  # Clean up every hour
                
        except asyncio.CancelledError:
            logger.info("Data cleanup cancelled")
        except Exception as e:
            logger.error(f"Error in data cleanup: {e}")
    
    async def _log_staking_event(self, staking_id: str, event_type: str, data: Dict[str, Any]):
        """Log staking event"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "staking_id": staking_id,
                "event_type": event_type,
                "data": data
            }
            
            log_file = self.logs_dir / f"staking_events_{datetime.now().strftime('%Y%m%d')}.log"
            async with aiofiles.open(log_file, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging staking event: {e}")
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        try:
            total_staking = len(self.staking_records)
            active_staking = len([s for s in self.staking_records.values() if s.status == StakingStatus.ACTIVE])
            total_resources = len(self.resource_info)
            
            total_staked_trx = sum(s.amount_trx for s in self.staking_records.values() if s.status == StakingStatus.ACTIVE)
            
            return {
                "total_staking_records": total_staking,
                "active_staking_records": active_staking,
                "total_resource_records": total_resources,
                "total_staked_trx": total_staked_trx,
                "staking_status": {
                    status.value: len([s for s in self.staking_records.values() if s.status == status])
                    for status in StakingStatus
                },
                "staking_types": {
                    staking_type.value: len([s for s in self.staking_records.values() if s.staking_type == staking_type])
                    for staking_type in StakingType
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting service stats: {e}")
            return {"error": str(e)}

# Global instance
trx_staking_service = TRXStakingService()

# Convenience functions for external use
async def stake_trx(request: StakingRequest) -> StakingResponse:
    """Stake TRX"""
    return await trx_staking_service.stake_trx(request)

async def unstake_trx(request: UnstakingRequest) -> UnstakingResponse:
    """Unstake TRX"""
    return await trx_staking_service.unstake_trx(request)

async def get_resource_info(wallet_address: str) -> ResourceInfoResponse:
    """Get resource information"""
    return await trx_staking_service.get_resource_info(wallet_address)

async def list_staking_records(wallet_address: Optional[str] = None) -> List[StakingInfo]:
    """List staking records"""
    return await trx_staking_service.list_staking_records(wallet_address)

async def get_service_stats() -> Dict[str, Any]:
    """Get service statistics"""
    return await trx_staking_service.get_service_stats()

if __name__ == "__main__":
    # Example usage
    async def main():
        try:
            # Get resource info
            resource_info = await get_resource_info("TYourTRONAddressHere123456789")
            print(f"Resource info: {resource_info}")
            
            # List staking records
            staking_records = await list_staking_records()
            print(f"Staking records: {len(staking_records)}")
            
            # Get service stats
            stats = await get_service_stats()
            print(f"Service stats: {stats}")
            
        except Exception as e:
            print(f"Error: {e}")
    
    asyncio.run(main())
