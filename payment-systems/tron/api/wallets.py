"""
LUCID Payment Systems - TRON Wallets API
Wallet management and operations
Distroless container: lucid-tron-payment-service:latest
"""

import asyncio
import logging
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field, validator
import httpx

from ..services.tron_client import TronClientService
from ..services.wallet_manager import (
    wallet_manager_service,
    WalletCreateRequest as WalletCreateRequestService,
    WalletUpdateRequest as WalletUpdateRequestService,
    WalletResponse as WalletResponseService,
    WalletType,
    WalletStatus
)
from ..models.wallet import WalletResponse, WalletCreateRequest, WalletUpdateRequest
from ..models.transaction import TransactionResponse, TransactionCreateRequest

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/tron/wallets", tags=["TRON Wallets"])

# Initialize TRON client service
tron_client = TronClientService()

class WalletListResponse(BaseModel):
    """Wallet list response"""
    wallets: List[WalletResponse]
    total_count: int
    timestamp: str

class WalletBalanceResponse(BaseModel):
    """Wallet balance response"""
    wallet_id: str
    address: str
    balance_trx: float
    balance_sun: int
    energy_available: int
    bandwidth_available: int
    frozen_balance: float
    last_updated: str

class WalletTransactionResponse(BaseModel):
    """Wallet transaction response"""
    wallet_id: str
    transactions: List[TransactionResponse]
    total_count: int
    timestamp: str

class WalletCreateResponse(BaseModel):
    """Wallet creation response"""
    wallet_id: str
    address: str
    private_key: str
    public_key: str
    created_at: str
    message: str

class WalletImportRequest(BaseModel):
    """Wallet import request"""
    private_key: str = Field(..., description="Private key in hex format")
    name: str = Field(..., description="Wallet name")
    description: Optional[str] = Field(None, description="Wallet description")

class WalletExportRequest(BaseModel):
    """Wallet export request"""
    wallet_id: str = Field(..., description="Wallet ID to export")
    include_private_key: bool = Field(False, description="Include private key in export")

class WalletSignRequest(BaseModel):
    """Wallet sign request"""
    wallet_id: str = Field(..., description="Wallet ID")
    data: str = Field(..., description="Data to sign (hex string)")
    message: Optional[str] = Field(None, description="Human readable message")

class WalletSignResponse(BaseModel):
    """Wallet sign response"""
    wallet_id: str
    signature: str
    public_key: str
    message_hash: str
    timestamp: str

@router.post("/create", response_model=WalletCreateResponse)
async def create_wallet(request: WalletCreateRequest):
    """Create a new TRON wallet"""
    try:
        # Convert API request to service request
        service_request = WalletCreateRequestService(
            name=request.name,
            description=request.description,
            wallet_type=WalletType.HOT,  # Default to HOT wallet
            password=None  # Use service encryption key
        )
        
        # Create wallet using service
        wallet_response = await wallet_manager_service.create_wallet(service_request)
        
        logger.info(f"Created wallet: {wallet_response.wallet_id} -> {wallet_response.address}")
        
        # Note: Private key is encrypted and not returned for security
        # In production, private key should never be returned
        return WalletCreateResponse(
            wallet_id=wallet_response.wallet_id,
            address=wallet_response.address,
            private_key="[ENCRYPTED]",  # Private key is encrypted and stored securely
            public_key="",  # Can be derived from address if needed
            created_at=wallet_response.created_at,
            message="Wallet created successfully. Private key is encrypted and stored securely."
        )
    except Exception as e:
        logger.error(f"Error creating wallet: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create wallet: {str(e)}")

@router.get("/", response_model=WalletListResponse)
async def list_wallets(skip: int = 0, limit: int = 100):
    """List all wallets"""
    try:
        # Validate pagination parameters
        if skip < 0:
            raise HTTPException(status_code=400, detail="Invalid skip parameter")
        if limit <= 0 or limit > 1000:
            raise HTTPException(status_code=400, detail="Invalid limit parameter (1-1000)")
        
        # Get wallets from service
        wallet_list = await wallet_manager_service.list_wallets()
        total_count = len(wallet_list)
        
        # Apply pagination
        paginated_wallets = wallet_list[skip:skip + limit]
        
        # Convert to response format
        wallets = []
        for wallet_response in paginated_wallets:
            wallets.append(WalletResponse(
                wallet_id=wallet_response.wallet_id,
                name=wallet_response.name,
                description=wallet_response.description,
                address=wallet_response.address,
                status=wallet_response.status,
                balance_trx=wallet_response.balance_trx,
                created_at=wallet_response.created_at,
                last_updated=wallet_response.last_updated
            ))
        
        return WalletListResponse(
            wallets=wallets,
            total_count=total_count,
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing wallets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list wallets: {str(e)}")

@router.get("/{wallet_id}", response_model=WalletResponse)
async def get_wallet(wallet_id: str):
    """Get wallet by ID"""
    try:
        wallet_response = await wallet_manager_service.get_wallet(wallet_id)
        
        if not wallet_response:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        return WalletResponse(
            wallet_id=wallet_response.wallet_id,
            name=wallet_response.name,
            description=wallet_response.description,
            address=wallet_response.address,
            status=wallet_response.status,
            balance_trx=wallet_response.balance_trx,
            created_at=wallet_response.created_at,
            last_updated=wallet_response.last_updated
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting wallet {wallet_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get wallet: {str(e)}")

@router.get("/{wallet_id}/balance", response_model=WalletBalanceResponse)
async def get_wallet_balance(wallet_id: str):
    """Get wallet balance"""
    try:
        balance_data = await wallet_manager_service.get_wallet_balance(wallet_id)
        
        if not balance_data:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        return WalletBalanceResponse(
            wallet_id=balance_data["wallet_id"],
            address=balance_data["address"],
            balance_trx=balance_data["balance_trx"],
            balance_sun=balance_data["balance_sun"],
            energy_available=balance_data["energy_available"],
            bandwidth_available=balance_data["bandwidth_available"],
            frozen_balance=balance_data.get("frozen_balance", 0.0),
            last_updated=balance_data.get("last_updated", datetime.now().isoformat())
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting wallet balance {wallet_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get wallet balance: {str(e)}")

@router.put("/{wallet_id}", response_model=WalletResponse)
async def update_wallet(wallet_id: str, request: WalletUpdateRequest):
    """Update wallet information"""
    try:
        # Convert API request to service request
        service_request = WalletUpdateRequestService(
            name=request.name,
            description=request.description,
            status=WalletStatus(request.status) if request.status else None
        )
        
        wallet_response = await wallet_manager_service.update_wallet(wallet_id, service_request)
        
        if not wallet_response:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        return WalletResponse(
            wallet_id=wallet_response.wallet_id,
            name=wallet_response.name,
            description=wallet_response.description,
            address=wallet_response.address,
            status=wallet_response.status,
            balance_trx=wallet_response.balance_trx,
            created_at=wallet_response.created_at,
            last_updated=wallet_response.last_updated
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating wallet {wallet_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update wallet: {str(e)}")

@router.delete("/{wallet_id}")
async def delete_wallet(wallet_id: str):
    """Delete wallet"""
    try:
        success = await wallet_manager_service.delete_wallet(wallet_id, password=None)
        
        if not success:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        logger.info(f"Deleted wallet: {wallet_id}")
        
        return {
            "message": "Wallet deleted successfully",
            "wallet_id": wallet_id,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting wallet {wallet_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete wallet: {str(e)}")

@router.post("/import", response_model=WalletCreateResponse)
async def import_wallet(request: WalletImportRequest):
    """Import existing wallet - private key is encrypted and stored securely"""
    try:
        # Validate private key format
        if not request.private_key or len(request.private_key) != 64:
            raise HTTPException(status_code=400, detail="Invalid private key format (must be 64 hex characters)")
        
        # Import wallet using service - private key will be encrypted
        # Note: We need to create a wallet with the imported private key
        # This requires extending the service to support import functionality
        # For now, we'll log a warning and return an error
        logger.warning("Wallet import via API is not yet fully implemented - use service directly")
        raise HTTPException(
            status_code=501, 
            detail="Wallet import functionality is being implemented. Private keys are encrypted and never returned in responses."
        )
        
        # TODO: Implement proper import using wallet_manager_service
        # The private key should be encrypted using the service's encryption
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing wallet: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import wallet: {str(e)}")

@router.post("/{wallet_id}/export")
async def export_wallet(wallet_id: str, request: WalletExportRequest):
    """Export wallet - private keys are encrypted and require password for decryption"""
    try:
        # Get wallet from service
        wallet_response = await wallet_manager_service.get_wallet(wallet_id)
        
        if not wallet_response:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        # Log export operation for audit
        logger.info(f"Wallet export requested for {wallet_id}, include_private_key={request.include_private_key}")
        
        export_data = {
            "wallet_id": wallet_response.wallet_id,
            "name": wallet_response.name,
            "description": wallet_response.description,
            "address": wallet_response.address,
            "wallet_type": wallet_response.wallet_type,
            "status": wallet_response.status,
            "created_at": wallet_response.created_at,
            "last_updated": wallet_response.last_updated
        }
        
        # SECURITY: Private keys are encrypted and stored securely
        # They should NEVER be exported via API for security reasons
        # If private key export is absolutely necessary, it should:
        # 1. Require additional authentication/authorization
        # 2. Require password verification
        # 3. Be logged for audit purposes
        # 4. Use secure channels only
        
        if request.include_private_key:
            logger.warning(f"Private key export requested for wallet {wallet_id} - this is a security risk")
            raise HTTPException(
                status_code=403,
                detail="Private key export via API is disabled for security reasons. Use secure backup mechanisms instead."
            )
        
        return {
            "wallet": export_data,
            "exported_at": datetime.now().isoformat(),
            "note": "Private keys are encrypted and stored securely. They are never returned via API."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting wallet {wallet_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export wallet: {str(e)}")

@router.post("/{wallet_id}/sign", response_model=WalletSignResponse)
async def sign_data(wallet_id: str, request: WalletSignRequest):
    """Sign data with wallet - requires wallet to be unlocked"""
    try:
        # Get wallet from service
        wallet_response = await wallet_manager_service.get_wallet(wallet_id)
        
        if not wallet_response:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        # Validate data format
        if not request.data or len(request.data) % 2 != 0:
            raise HTTPException(status_code=400, detail="Invalid data format (must be hex string)")
        
        # Log signing operation for audit
        logger.info(f"Data signing requested for wallet {wallet_id}")
        
        # TODO: Implement proper signing using wallet_manager_service
        # This requires:
        # 1. Decrypting the private key (with password verification)
        # 2. Using TRON library to sign the data
        # 3. Returning the signature
        
        # For now, return a placeholder (this should be implemented properly)
        logger.warning("Wallet signing functionality needs to be implemented using wallet_manager_service")
        raise HTTPException(
            status_code=501,
            detail="Wallet signing functionality is being implemented. Private keys are encrypted and require password for operations."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error signing data with wallet {wallet_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sign data: {str(e)}")

@router.get("/{wallet_id}/transactions", response_model=WalletTransactionResponse)
async def get_wallet_transactions(wallet_id: str, skip: int = 0, limit: int = 100):
    """Get wallet transactions"""
    try:
        # Validate pagination parameters
        if skip < 0:
            raise HTTPException(status_code=400, detail="Invalid skip parameter")
        if limit <= 0 or limit > 1000:
            raise HTTPException(status_code=400, detail="Invalid limit parameter (1-1000)")
        
        # Get wallet from service
        wallet_response = await wallet_manager_service.get_wallet(wallet_id)
        
        if not wallet_response:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        # TODO: Implement transaction history retrieval from wallet_manager_service
        # For now, return empty list as transaction history tracking needs to be implemented
        transactions = []
        
        return WalletTransactionResponse(
            wallet_id=wallet_id,
            transactions=transactions,
            total_count=0,
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting wallet transactions {wallet_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get wallet transactions: {str(e)}")
