"""
GUI Hardware Manager Proxy Endpoints Router

File: 03-api-gateway/api/app/routers/gui_hardware.py
Purpose: Proxy endpoints to gui-hardware-manager service for hardware wallet management

Architecture Note: This router proxies to gui-hardware-manager service
"""

import logging
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/info")
async def get_gui_hardware_manager_info():
    """Get GUI Hardware Manager service information"""
    try:
        from app.services.gui_hardware_manager_service import gui_hardware_manager_service
        await gui_hardware_manager_service.initialize()
        info = await gui_hardware_manager_service.get_manager_info()
        return info
    except Exception as e:
        logger.error(f"Failed to get GUI Hardware Manager info: {e}")
        raise HTTPException(status_code=503, detail=f"GUI Hardware Manager unavailable: {str(e)}")


@router.get("/health")
async def check_gui_hardware_manager_health():
    """Check GUI Hardware Manager service health"""
    try:
        from app.services.gui_hardware_manager_service import gui_hardware_manager_service
        is_healthy = await gui_hardware_manager_service.health_check()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "service": "gui-hardware-manager",
            "connected": is_healthy
        }
    except Exception as e:
        logger.error(f"GUI Hardware Manager health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "gui-hardware-manager",
            "connected": False,
            "error": str(e)
        }


@router.get("/devices")
async def list_hardware_devices():
    """List connected hardware wallet devices"""
    try:
        from app.services.gui_hardware_manager_service import gui_hardware_manager_service
        await gui_hardware_manager_service.initialize()
        devices = await gui_hardware_manager_service.list_devices()
        return devices
    except Exception as e:
        logger.error(f"Failed to list hardware devices: {e}")
        raise HTTPException(status_code=503, detail=f"Device listing failed: {str(e)}")


@router.get("/devices/{device_id}")
async def get_device_details(device_id: str):
    """Get hardware wallet device details"""
    try:
        from app.services.gui_hardware_manager_service import gui_hardware_manager_service
        await gui_hardware_manager_service.initialize()
        details = await gui_hardware_manager_service.get_device_details(device_id)
        return details
    except Exception as e:
        logger.error(f"Failed to get device details: {e}")
        raise HTTPException(status_code=503, detail=f"Device details failed: {str(e)}")


@router.post("/devices/{device_id}/verify")
async def verify_device(device_id: str):
    """Verify hardware wallet device connection"""
    try:
        from app.services.gui_hardware_manager_service import gui_hardware_manager_service
        await gui_hardware_manager_service.initialize()
        result = await gui_hardware_manager_service.verify_device(device_id)
        logger.info(f"Device verified: {device_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to verify device: {e}")
        raise HTTPException(status_code=503, detail=f"Device verification failed: {str(e)}")


@router.get("/wallets")
async def list_hardware_wallets():
    """List hardware wallet accounts"""
    try:
        from app.services.gui_hardware_manager_service import gui_hardware_manager_service
        await gui_hardware_manager_service.initialize()
        wallets = await gui_hardware_manager_service.list_wallets()
        return wallets
    except Exception as e:
        logger.error(f"Failed to list hardware wallets: {e}")
        raise HTTPException(status_code=503, detail=f"Wallet listing failed: {str(e)}")


@router.post("/wallets/{wallet_id}/sign")
async def sign_transaction(wallet_id: str):
    """Sign transaction with hardware wallet"""
    try:
        from app.services.gui_hardware_manager_service import gui_hardware_manager_service
        await gui_hardware_manager_service.initialize()
        result = await gui_hardware_manager_service.sign_transaction(wallet_id)
        logger.info(f"Transaction signed by wallet: {wallet_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to sign transaction: {e}")
        raise HTTPException(status_code=503, detail=f"Transaction signing failed: {str(e)}")
