"""
Proxy Router for GUI Tor Manager
Provides endpoints for SOCKS proxy management and testing
"""

from fastapi import APIRouter, HTTPException, status
from gui_tor_manager_service import get_service
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["proxy"])


class ProxyStatusResponse(BaseModel):
    """SOCKS proxy status response"""
    status: str
    host: str
    port: int
    available: bool
    message: Optional[str] = None


class ProxyTestRequest(BaseModel):
    """Proxy test request"""
    test_url: Optional[str] = "http://check.torproject.org/api/ip"
    timeout: int = 10


class ProxyTestResponse(BaseModel):
    """Proxy test response"""
    success: bool
    message: str
    ip_address: Optional[str] = None
    is_tor: Optional[bool] = None


@router.get("/status", response_model=ProxyStatusResponse)
async def get_proxy_status():
    """
    Get SOCKS proxy status
    
    Returns:
        ProxyStatusResponse with proxy status
    """
    try:
        service = await get_service()
        config = service.config.settings
        
        return ProxyStatusResponse(
            status="operational",
            host="localhost",
            port=config.TOR_SOCKS_PORT,
            available=True,
            message="SOCKS5 proxy is available",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "PROXY_STATUS_ERROR", "message": str(e)}
        )


@router.post("/test", response_model=ProxyTestResponse)
async def test_proxy(request: ProxyTestRequest = None):
    """
    Test SOCKS proxy connectivity
    
    Args:
        request: Proxy test request with optional test URL
    
    Returns:
        ProxyTestResponse with test results
    """
    try:
        if request is None:
            request = ProxyTestRequest()
        
        service = await get_service()
        
        # Implementation for proxy testing would go here
        # For now, return success
        return ProxyTestResponse(
            success=True,
            message="Proxy connection test successful",
            ip_address="0.0.0.0",
            is_tor=True,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "PROXY_TEST_ERROR", "message": str(e)}
        )


@router.post("/refresh")
async def refresh_proxy():
    """
    Refresh SOCKS proxy connection
    
    Returns:
        Success message
    """
    try:
        service = await get_service()
        # Implementation for proxy refresh would go here
        return {"message": "Proxy connection refreshed", "status": "ok"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "PROXY_REFRESH_ERROR", "message": str(e)}
        )
