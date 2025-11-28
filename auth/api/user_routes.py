"""
Lucid Authentication Service - User Routes
GET /users/{user_id}, PUT /users/{user_id}, etc.
"""

from fastapi import APIRouter, HTTPException, status
from models.user import UserResponse, UserUpdate
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get user by ID"""
    logger.info(f"Get user: {user_id}")
    raise HTTPException(status_code=501, detail="Not implemented")


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, update: UserUpdate):
    """Update user profile"""
    logger.info(f"Update user: {user_id}")
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/me", response_model=UserResponse)
async def get_current_user():
    """Get current authenticated user"""
    logger.info("Get current user")
    raise HTTPException(status_code=501, detail="Not implemented")


# Add router to main router
from . import users_router as main_router
main_router.include_router(router)

