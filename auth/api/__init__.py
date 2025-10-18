"""
Lucid Authentication Service - API Routes Package
"""

from fastapi import APIRouter

# Create routers
auth_router = APIRouter()
users_router = APIRouter()
sessions_router = APIRouter()
hardware_wallet_router = APIRouter()

# Import route handlers
from . import auth_routes, user_routes, session_routes, hardware_wallet_routes

__all__ = [
    "auth_router",
    "users_router", 
    "sessions_router",
    "hardware_wallet_router"
]

