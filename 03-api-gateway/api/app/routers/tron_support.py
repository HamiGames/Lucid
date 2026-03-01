"""
TRON Support Services Proxy Endpoints Router

File: 03-api-gateway/api/app/routers/tron_support.py
Purpose: Proxy endpoints to TRON support services (payout router, wallet manager, USDT manager)

Architecture Note: Proxies to isolated TRON payment system services
"""

import logging
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()


# Payout Router Endpoints
@router.get("/payout/info")
async def get_payout_router_info():
    """Get TRON Payout Router service information"""
    try:
        from app.services.tron_support_service import tron_support_service
        await tron_support_service.initialize()
        info = await tron_support_service.get_payout_info()
        return info
    except Exception as e:
        logger.error(f"Failed to get TRON Payout Router info: {e}")
        raise HTTPException(status_code=503, detail=f"TRON Payout Router unavailable: {str(e)}")


@router.get("/payout/health")
async def check_payout_router_health():
    """Check TRON Payout Router service health"""
    try:
        from app.services.tron_support_service import tron_support_service
        is_healthy = await tron_support_service.check_payout_health()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "service": "tron-payout-router",
            "connected": is_healthy
        }
    except Exception as e:
        logger.error(f"TRON Payout Router health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "tron-payout-router",
            "connected": False,
            "error": str(e)
        }


@router.get("/payout/status")
async def get_payout_status():
    """Get TRON Payout Router status"""
    try:
        from app.services.tron_support_service import tron_support_service
        await tron_support_service.initialize()
        status = await tron_support_service.get_payout_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get payout status: {e}")
        raise HTTPException(status_code=503, detail=f"Payout status check failed: {str(e)}")


# Wallet Manager Endpoints
@router.get("/wallets/info")
async def get_wallet_manager_info():
    """Get TRON Wallet Manager service information"""
    try:
        from app.services.tron_support_service import tron_support_service
        await tron_support_service.initialize()
        info = await tron_support_service.get_wallet_info()
        return info
    except Exception as e:
        logger.error(f"Failed to get TRON Wallet Manager info: {e}")
        raise HTTPException(status_code=503, detail=f"TRON Wallet Manager unavailable: {str(e)}")


@router.get("/wallets/health")
async def check_wallet_manager_health():
    """Check TRON Wallet Manager service health"""
    try:
        from app.services.tron_support_service import tron_support_service
        is_healthy = await tron_support_service.check_wallet_health()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "service": "tron-wallet-manager",
            "connected": is_healthy
        }
    except Exception as e:
        logger.error(f"TRON Wallet Manager health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "tron-wallet-manager",
            "connected": False,
            "error": str(e)
        }


@router.get("/wallets")
async def list_wallets():
    """List TRON wallets from Wallet Manager"""
    try:
        from app.services.tron_support_service import tron_support_service
        await tron_support_service.initialize()
        wallets = await tron_support_service.list_wallets()
        return wallets
    except Exception as e:
        logger.error(f"Failed to list wallets: {e}")
        raise HTTPException(status_code=503, detail=f"Wallet listing failed: {str(e)}")


# USDT Manager Endpoints
@router.get("/usdt/info")
async def get_usdt_manager_info():
    """Get TRON USDT Manager service information"""
    try:
        from app.services.tron_support_service import tron_support_service
        await tron_support_service.initialize()
        info = await tron_support_service.get_usdt_info()
        return info
    except Exception as e:
        logger.error(f"Failed to get TRON USDT Manager info: {e}")
        raise HTTPException(status_code=503, detail=f"TRON USDT Manager unavailable: {str(e)}")


@router.get("/usdt/health")
async def check_usdt_manager_health():
    """Check TRON USDT Manager service health"""
    try:
        from app.services.tron_support_service import tron_support_service
        is_healthy = await tron_support_service.check_usdt_health()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "service": "tron-usdt-manager",
            "connected": is_healthy
        }
    except Exception as e:
        logger.error(f"TRON USDT Manager health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "tron-usdt-manager",
            "connected": False,
            "error": str(e)
        }


@router.get("/usdt/balance/{wallet_id}")
async def get_usdt_balance(wallet_id: str):
    """Get USDT balance from USDT Manager"""
    try:
        from app.services.tron_support_service import tron_support_service
        await tron_support_service.initialize()
        balance = await tron_support_service.get_usdt_balance(wallet_id)
        return balance
    except Exception as e:
        logger.error(f"Failed to get USDT balance: {e}")
        raise HTTPException(status_code=503, detail=f"USDT balance retrieval failed: {str(e)}")


@router.post("/usdt/transfer")
async def transfer_usdt():
    """Transfer USDT via USDT Manager"""
    try:
        from app.services.tron_support_service import tron_support_service
        await tron_support_service.initialize()
        result = await tron_support_service.transfer_usdt()
        logger.info("USDT transfer initiated")
        return result
    except Exception as e:
        logger.error(f"Failed to transfer USDT: {e}")
        raise HTTPException(status_code=503, detail=f"USDT transfer failed: {str(e)}")
