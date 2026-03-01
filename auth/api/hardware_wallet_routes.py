"""
Lucid Authentication Service - Hardware Wallet Routes
POST /hw/connect, POST /hw/sign, GET /hw/status
Supports Ledger, Trezor, and KeepKey
"""

from fastapi import APIRouter, HTTPException, status
from auth.models.hardware_wallet import (
    HardwareWalletConnect,
    HardwareWalletConnectResponse,
    HardwareWalletSign,
    HardwareWalletSignResponse,
    HardwareWalletStatusResponse
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/connect", response_model=HardwareWalletConnectResponse)
async def connect_hardware_wallet(request: HardwareWalletConnect):
    """
    Connect hardware wallet (Ledger, Trezor, or KeepKey)
    
    - Detects hardware wallet
    - Retrieves TRON address
    - Returns wallet information
    """
    logger.info(f"Hardware wallet connect: {request.wallet_type}")
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/sign", response_model=HardwareWalletSignResponse)
async def sign_with_hardware_wallet(request: HardwareWalletSign):
    """
    Sign message with hardware wallet
    
    - Sends message to hardware wallet
    - User confirms on device
    - Returns signature
    """
    logger.info(f"Hardware wallet sign: {request.wallet_id}")
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/status/{wallet_id}", response_model=HardwareWalletStatusResponse)
async def get_hardware_wallet_status(wallet_id: str):
    """
    Get hardware wallet connection status
    
    - Returns current connection status
    - Returns device information
    """
    logger.info(f"Hardware wallet status: {wallet_id}")
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/disconnect/{wallet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_hardware_wallet(wallet_id: str):
    """
    Disconnect hardware wallet
    
    - Closes connection to hardware wallet
    - Cleans up resources
    """
    logger.info(f"Hardware wallet disconnect: {wallet_id}")
    raise HTTPException(status_code=501, detail="Not implemented")


# Add router to main router
from . import hardware_wallet_router as main_router
main_router.include_router(router)

