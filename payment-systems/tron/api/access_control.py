"""
LUCID Payment Systems - TRON Wallet Access Control API
RBAC and permissions management for wallets
Distroless container: lucid-tron-wallet-manager:latest
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field

from ..services.wallet_access_control import (
    WalletAccessControlService,
    Role,
    Permission
)
from ..services.wallet_manager import wallet_manager_service

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/tron/access", tags=["TRON Wallet Access Control"])

# Global access control service instance (will be initialized in main app)
access_control_service: Optional[WalletAccessControlService] = None

# Request/Response Models
class AccessGrantRequest(BaseModel):
    """Access grant request"""
    wallet_id: str = Field(..., description="Wallet ID")
    user_id: str = Field(..., description="User ID to grant access")
    role: str = Field(..., description="Role: ADMIN, OPERATOR, USER, VIEWER")
    expires_at: Optional[str] = Field(None, description="Access expiration timestamp (ISO format)")

class AccessResponse(BaseModel):
    """Access response model"""
    wallet_id: str = Field(..., description="Wallet ID")
    user_id: str = Field(..., description="User ID")
    role: str = Field(..., description="User role")
    granted_by: str = Field(..., description="User who granted access")
    granted_at: str = Field(..., description="Grant timestamp")
    expires_at: Optional[str] = Field(None, description="Expiration timestamp")
    revoked: bool = Field(False, description="Whether access is revoked")

class AccessListResponse(BaseModel):
    """Access list response"""
    wallet_id: str = Field(..., description="Wallet ID")
    users: List[AccessResponse] = Field(..., description="List of users with access")
    total_count: int = Field(..., description="Total user count")
    timestamp: str = Field(..., description="Response timestamp")

class PermissionUpdateRequest(BaseModel):
    """Permission update request"""
    role: str = Field(..., description="New role: ADMIN, OPERATOR, USER, VIEWER")
    expires_at: Optional[str] = Field(None, description="New expiration timestamp (ISO format)")

class UserWalletsResponse(BaseModel):
    """User wallets response"""
    user_id: str = Field(..., description="User ID")
    wallet_ids: List[str] = Field(..., description="List of wallet IDs user has access to")
    total_count: int = Field(..., description="Total wallet count")
    timestamp: str = Field(..., description="Response timestamp")

def get_access_control_service() -> WalletAccessControlService:
    """Dependency to get access control service"""
    if access_control_service is None:
        raise HTTPException(status_code=503, detail="Access control service not initialized")
    return access_control_service

@router.post("/wallet/{wallet_id}/access", response_model=AccessResponse)
async def grant_wallet_access(
    wallet_id: str,
    request: AccessGrantRequest,
    service: WalletAccessControlService = Depends(get_access_control_service)
):
    """Grant wallet access to user"""
    try:
        # Verify wallet exists
        wallet_response = await wallet_manager_service.get_wallet(wallet_id)
        if not wallet_response:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        # Validate role
        try:
            role = Role(request.role.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {request.role}. Must be one of: ADMIN, OPERATOR, USER, VIEWER")
        
        # Parse expiration date if provided
        expires_at = None
        if request.expires_at:
            try:
                expires_at = datetime.fromisoformat(request.expires_at.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid expires_at format. Use ISO 8601 format.")
        
        # Get current user from request (in production, this would come from JWT token)
        # For now, use a placeholder
        granted_by = "system"  # TODO: Extract from JWT token
        
        # Grant access
        success = await service.grant_wallet_access(
            wallet_id=wallet_id,
            user_id=request.user_id,
            role=role,
            granted_by=granted_by,
            expires_at=expires_at
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to grant access")
        
        # Get the access record
        users = await service.get_wallet_users(wallet_id)
        access_record = next((u for u in users if u["user_id"] == request.user_id), None)
        
        if not access_record:
            raise HTTPException(status_code=500, detail="Access granted but record not found")
        
        logger.info(f"Granted {role.value} access to wallet {wallet_id} for user {request.user_id}")
        
        return AccessResponse(
            wallet_id=wallet_id,
            user_id=request.user_id,
            role=access_record.get("role", role.value),
            granted_by=access_record.get("granted_by", granted_by),
            granted_at=access_record.get("granted_at", datetime.now().isoformat()),
            expires_at=access_record.get("expires_at"),
            revoked=access_record.get("revoked", False)
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error granting access to wallet {wallet_id} for user {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to grant access: {str(e)}")

@router.get("/wallet/{wallet_id}/access", response_model=AccessListResponse)
async def list_wallet_access(
    wallet_id: str,
    service: WalletAccessControlService = Depends(get_access_control_service)
):
    """List wallet access permissions"""
    try:
        # Verify wallet exists
        wallet_response = await wallet_manager_service.get_wallet(wallet_id)
        if not wallet_response:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        # Get users with access
        users_data = await service.get_wallet_users(wallet_id)
        
        # Convert to AccessResponse format
        users = []
        for user_data in users_data:
            users.append(AccessResponse(
                wallet_id=wallet_id,
                user_id=user_data.get("user_id", ""),
                role=user_data.get("role", "USER"),
                granted_by=user_data.get("granted_by", "system"),
                granted_at=user_data.get("granted_at", datetime.now().isoformat()),
                expires_at=user_data.get("expires_at"),
                revoked=user_data.get("revoked", False)
            ))
        
        return AccessListResponse(
            wallet_id=wallet_id,
            users=users,
            total_count=len(users),
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing access for wallet {wallet_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list access: {str(e)}")

@router.delete("/wallet/{wallet_id}/access/{user_id}")
async def revoke_wallet_access(
    wallet_id: str,
    user_id: str,
    service: WalletAccessControlService = Depends(get_access_control_service)
):
    """Revoke wallet access for user"""
    try:
        # Verify wallet exists
        wallet_response = await wallet_manager_service.get_wallet(wallet_id)
        if not wallet_response:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        # Get current user from request (in production, this would come from JWT token)
        revoked_by = "system"  # TODO: Extract from JWT token
        
        # Revoke access
        success = await service.revoke_wallet_access(
            wallet_id=wallet_id,
            user_id=user_id,
            revoked_by=revoked_by
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Access record not found")
        
        logger.info(f"Revoked access to wallet {wallet_id} for user {user_id}")
        
        return {
            "message": "Access revoked successfully",
            "wallet_id": wallet_id,
            "user_id": user_id,
            "revoked_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking access to wallet {wallet_id} for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to revoke access: {str(e)}")

@router.get("/user/{user_id}/wallets", response_model=UserWalletsResponse)
async def get_user_wallets(
    user_id: str,
    service: WalletAccessControlService = Depends(get_access_control_service)
):
    """List user's accessible wallets"""
    try:
        # Get wallet IDs user has access to
        wallet_ids = await service.get_user_wallets(user_id)
        
        return UserWalletsResponse(
            user_id=user_id,
            wallet_ids=wallet_ids,
            total_count=len(wallet_ids),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error getting wallets for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user wallets: {str(e)}")

@router.put("/wallet/{wallet_id}/access/{user_id}", response_model=AccessResponse)
async def update_user_permissions(
    wallet_id: str,
    user_id: str,
    request: PermissionUpdateRequest,
    service: WalletAccessControlService = Depends(get_access_control_service)
):
    """Update user permissions for wallet"""
    try:
        # Verify wallet exists
        wallet_response = await wallet_manager_service.get_wallet(wallet_id)
        if not wallet_response:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        # Validate role
        try:
            role = Role(request.role.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {request.role}. Must be one of: ADMIN, OPERATOR, USER, VIEWER")
        
        # Parse expiration date if provided
        expires_at = None
        if request.expires_at:
            try:
                expires_at = datetime.fromisoformat(request.expires_at.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid expires_at format. Use ISO 8601 format.")
        
        # Get current user from request (in production, this would come from JWT token)
        granted_by = "system"  # TODO: Extract from JWT token
        
        # Update access (grant with new role/expiration)
        success = await service.grant_wallet_access(
            wallet_id=wallet_id,
            user_id=user_id,
            role=role,
            granted_by=granted_by,
            expires_at=expires_at
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update permissions")
        
        # Get the updated access record
        users = await service.get_wallet_users(wallet_id)
        access_record = next((u for u in users if u["user_id"] == user_id), None)
        
        if not access_record:
            raise HTTPException(status_code=404, detail="Access record not found")
        
        logger.info(f"Updated permissions for user {user_id} on wallet {wallet_id} to {role.value}")
        
        return AccessResponse(
            wallet_id=wallet_id,
            user_id=user_id,
            role=access_record.get("role", role.value),
            granted_by=access_record.get("granted_by", granted_by),
            granted_at=access_record.get("granted_at", datetime.now().isoformat()),
            expires_at=access_record.get("expires_at"),
            revoked=access_record.get("revoked", False)
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating permissions for user {user_id} on wallet {wallet_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update permissions: {str(e)}")
