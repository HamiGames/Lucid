# Path: user/user_manager.py

from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import uuid
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    user_id: str
    email: str
    username: str
    role: str = "user"  # user, admin, node_operator
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None
    is_active: bool = True
    permissions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "username": self.username,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_active": self.is_active,
            "permissions": self.permissions,
            "metadata": self.metadata
        }


class UserManager:
    """Manages user profiles and authentication."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        
    async def create_user(self, email: str, username: str, password: str) -> UserProfile:
        """Create a new user."""
        try:
            user_id = str(uuid.uuid4())
            password_hash = self._hash_password(password)
            
            user = UserProfile(
                user_id=user_id,
                email=email,
                username=username
            )
            
            # Store user
            user_doc = user.to_dict()
            user_doc["password_hash"] = password_hash
            
            await self.db["users"].insert_one(user_doc)
            
            logger.info(f"Created user: {username}")
            return user
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise
            
    async def authenticate(self, username: str, password: str) -> Optional[UserProfile]:
        """Authenticate user with username/password."""
        try:
            user_doc = await self.db["users"].find_one({
                "$or": [
                    {"username": username},
                    {"email": username}
                ]
            })
            
            if not user_doc:
                return None
                
            if not self._verify_password(password, user_doc["password_hash"]):
                return None
                
            # Update last login
            await self.db["users"].update_one(
                {"user_id": user_doc["user_id"]},
                {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}}
            )
            
            return UserProfile(
                user_id=user_doc["user_id"],
                email=user_doc["email"],
                username=user_doc["username"],
                role=user_doc.get("role", "user"),
                created_at=datetime.fromisoformat(user_doc["created_at"]),
                last_login=datetime.now(timezone.utc),
                is_active=user_doc.get("is_active", True),
                permissions=user_doc.get("permissions", []),
                metadata=user_doc.get("metadata", {})
            )
            
        except Exception as e:
            logger.error(f"Failed to authenticate user: {e}")
            return None
            
    def _hash_password(self, password: str) -> str:
        """Hash password with salt."""
        salt = uuid.uuid4().hex
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex() + ':' + salt
        
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        try:
            password_hash, salt = hashed.split(':')
            return password_hash == hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
        except:
            return False
