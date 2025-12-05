"""
Lucid Authentication Service - User Routes
GET /users/{user_id}, PUT /users/{user_id}, etc.
"""

from fastapi import APIRouter, HTTPException, status, Request, Depends
from auth.models.user import UserResponse, UserUpdate
from auth.main import user_manager, mongodb_db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def get_current_user_id(request: Request) -> str:
    """Extract current user ID from request state (set by AuthMiddleware)"""
    if not hasattr(request.state, 'user_id') or not request.state.authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return request.state.user_id


@router.get("/me", response_model=UserResponse)
async def get_current_user(request: Request):
    """Get current authenticated user"""
    try:
        user_id = get_current_user_id(request)
        logger.info(f"Get current user: {user_id}")
        
        if not user_manager or not mongodb_db:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        # Get user from database
        user_doc = await mongodb_db.users.find_one({"user_id": user_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            user_id=user_doc.get("user_id"),
            tron_address=user_doc.get("tron_address"),
            role=user_doc.get("role", "USER"),
            created_at=user_doc.get("created_at"),
            updated_at=user_doc.get("updated_at")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, request: Request):
    """Get user by ID"""
    try:
        current_user_id = get_current_user_id(request)
        logger.info(f"Get user {user_id} by user {current_user_id}")
        
        if not user_manager or not mongodb_db:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        # Check if user can access this user (same user or admin)
        if user_id != current_user_id:
            # Check if current user is admin
            current_user_doc = await mongodb_db.users.find_one({"user_id": current_user_id})
            if not current_user_doc or current_user_doc.get("role") not in ["ADMIN", "SUPER_ADMIN"]:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Get user from database
        user_doc = await mongodb_db.users.find_one({"user_id": user_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            user_id=user_doc.get("user_id"),
            tron_address=user_doc.get("tron_address"),
            role=user_doc.get("role", "USER"),
            created_at=user_doc.get("created_at"),
            updated_at=user_doc.get("updated_at")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, update: UserUpdate, request: Request):
    """Update user profile"""
    try:
        current_user_id = get_current_user_id(request)
        logger.info(f"Update user {user_id} by user {current_user_id}")
        
        if not user_manager or not mongodb_db:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        # Check if user can update this profile (same user or admin)
        if user_id != current_user_id:
            # Check if current user is admin
            current_user_doc = await mongodb_db.users.find_one({"user_id": current_user_id})
            if not current_user_doc or current_user_doc.get("role") not in ["ADMIN", "SUPER_ADMIN"]:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Update user in database
        update_data = update.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        result = await mongodb_db.users.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get updated user
        user_doc = await mongodb_db.users.find_one({"user_id": user_id})
        return UserResponse(
            user_id=user_doc.get("user_id"),
            tron_address=user_doc.get("tron_address"),
            role=user_doc.get("role", "USER"),
            created_at=user_doc.get("created_at"),
            updated_at=user_doc.get("updated_at")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# Add router to main router
from . import users_router as main_router
main_router.include_router(router)

