"""
Lucid Authentication Service - Session Manager
Handles JWT token generation, validation, and session management
"""

import jwt
import redis.asyncio as redis
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json
import uuid
from config import settings
from models.session import Session, TokenType, TokenPayload
from utils.exceptions import (
    TokenExpiredError,
    InvalidTokenError,
    SessionNotFoundError,
    MaxSessionsExceededError
)
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages user sessions and JWT tokens"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        self.refresh_token_expire = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URI,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=settings.REDIS_DECODE_RESPONSES,
                encoding="utf-8"
            )
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis connection established for session management")
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            raise
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
    
    async def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            if self.redis_client:
                await self.redis_client.ping()
                return True
            return False
        except Exception:
            return False
    
    def generate_access_token(self, user_id: str, role: str, additional_claims: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate JWT access token
        
        Args:
            user_id: User ID
            role: User role
            additional_claims: Additional claims to include in token
            
        Returns:
            JWT access token string
        """
        now = datetime.utcnow()
        exp = now + self.access_token_expire
        
        payload = {
            "user_id": user_id,
            "role": role,
            "type": TokenType.ACCESS.value,
            "iat": now,
            "exp": exp,
            "nbf": now,
            "jti": str(uuid.uuid4())
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.debug(f"Generated access token for user {user_id}, expires at {exp}")
        return token
    
    def generate_refresh_token(self, user_id: str) -> str:
        """
        Generate JWT refresh token
        
        Args:
            user_id: User ID
            
        Returns:
            JWT refresh token string
        """
        now = datetime.utcnow()
        exp = now + self.refresh_token_expire
        
        payload = {
            "user_id": user_id,
            "type": TokenType.REFRESH.value,
            "iat": now,
            "exp": exp,
            "nbf": now,
            "jti": str(uuid.uuid4())
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.debug(f"Generated refresh token for user {user_id}, expires at {exp}")
        return token
    
    async def validate_token(self, token: str, expected_type: Optional[TokenType] = None) -> TokenPayload:
        """
        Validate JWT token and return payload
        
        Args:
            token: JWT token string
            expected_type: Expected token type (ACCESS or REFRESH)
            
        Returns:
            TokenPayload object
            
        Raises:
            TokenExpiredError: If token is expired
            InvalidTokenError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Check token type if specified
            if expected_type and payload.get("type") != expected_type.value:
                raise InvalidTokenError(f"Invalid token type. Expected {expected_type.value}")
            
            # Check if token is blacklisted
            if await self.is_token_blacklisted(payload.get("jti")):
                raise InvalidTokenError("Token has been revoked")
            
            token_payload = TokenPayload(**payload)
            logger.debug(f"Token validated for user {token_payload.user_id}")
            return token_payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token validation failed: expired")
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token validation failed: {e}")
            raise InvalidTokenError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise InvalidTokenError(f"Token validation failed: {str(e)}")
    
    async def create_session(self, user_id: str, role: str, metadata: Optional[Dict[str, Any]] = None) -> Session:
        """
        Create new user session
        
        Args:
            user_id: User ID
            role: User role
            metadata: Session metadata (IP, user agent, etc.)
            
        Returns:
            Session object with tokens
            
        Raises:
            MaxSessionsExceededError: If user has too many active sessions
        """
        # Check max concurrent sessions
        active_sessions = await self.get_user_sessions(user_id)
        if len(active_sessions) >= settings.SESSION_MAX_CONCURRENT_PER_USER:
            logger.warning(f"User {user_id} exceeded max concurrent sessions")
            raise MaxSessionsExceededError(
                f"Maximum {settings.SESSION_MAX_CONCURRENT_PER_USER} concurrent sessions allowed"
            )
        
        # Generate tokens
        access_token = self.generate_access_token(user_id, role)
        refresh_token = self.generate_refresh_token(user_id)
        
        # Create session object
        session = Session(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + self.refresh_token_expire,
            metadata=metadata or {}
        )
        
        # Store session in Redis
        await self.store_session(session)
        
        logger.info(f"Created session {session.session_id} for user {user_id}")
        return session
    
    async def store_session(self, session: Session):
        """Store session in Redis"""
        session_key = f"session:{session.session_id}"
        user_sessions_key = f"user_sessions:{session.user_id}"
        
        # Store session data
        await self.redis_client.setex(
            session_key,
            int(self.refresh_token_expire.total_seconds()),
            json.dumps(session.dict(), default=str)
        )
        
        # Add to user's session list
        await self.redis_client.sadd(user_sessions_key, session.session_id)
        await self.redis_client.expire(user_sessions_key, int(self.refresh_token_expire.total_seconds()))
    
    async def get_session(self, session_id: str) -> Session:
        """
        Get session by ID
        
        Args:
            session_id: Session ID
            
        Returns:
            Session object
            
        Raises:
            SessionNotFoundError: If session not found
        """
        session_key = f"session:{session_id}"
        session_data = await self.redis_client.get(session_key)
        
        if not session_data:
            raise SessionNotFoundError(f"Session {session_id} not found")
        
        return Session(**json.loads(session_data))
    
    async def get_user_sessions(self, user_id: str) -> List[Session]:
        """Get all active sessions for a user"""
        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = await self.redis_client.smembers(user_sessions_key)
        
        sessions = []
        for session_id in session_ids:
            try:
                session = await self.get_session(session_id)
                sessions.append(session)
            except SessionNotFoundError:
                # Remove stale session ID
                await self.redis_client.srem(user_sessions_key, session_id)
        
        return sessions
    
    async def revoke_session(self, session_id: str):
        """Revoke a session"""
        try:
            session = await self.get_session(session_id)
            
            # Blacklist tokens
            access_payload = await self.validate_token(session.access_token, TokenType.ACCESS)
            refresh_payload = await self.validate_token(session.refresh_token, TokenType.REFRESH)
            
            await self.blacklist_token(access_payload.jti, self.access_token_expire)
            await self.blacklist_token(refresh_payload.jti, self.refresh_token_expire)
            
            # Remove session
            session_key = f"session:{session_id}"
            user_sessions_key = f"user_sessions:{session.user_id}"
            
            await self.redis_client.delete(session_key)
            await self.redis_client.srem(user_sessions_key, session_id)
            
            logger.info(f"Revoked session {session_id}")
        except SessionNotFoundError:
            logger.warning(f"Attempted to revoke non-existent session {session_id}")
    
    async def revoke_all_user_sessions(self, user_id: str):
        """Revoke all sessions for a user"""
        sessions = await self.get_user_sessions(user_id)
        for session in sessions:
            await self.revoke_session(session.session_id)
        logger.info(f"Revoked all sessions for user {user_id}")
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Dict with new access token and refresh token
        """
        # Validate refresh token
        payload = await self.validate_token(refresh_token, TokenType.REFRESH)
        
        # Generate new tokens
        access_token = self.generate_access_token(payload.user_id, payload.role)
        new_refresh_token = self.generate_refresh_token(payload.user_id)
        
        # Blacklist old refresh token
        await self.blacklist_token(payload.jti, self.refresh_token_expire)
        
        logger.info(f"Refreshed tokens for user {payload.user_id}")
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token
        }
    
    async def blacklist_token(self, jti: str, expiry: timedelta):
        """Add token to blacklist"""
        blacklist_key = f"blacklist:{jti}"
        await self.redis_client.setex(
            blacklist_key,
            int(expiry.total_seconds()),
            "1"
        )
    
    async def is_token_blacklisted(self, jti: str) -> bool:
        """Check if token is blacklisted"""
        blacklist_key = f"blacklist:{jti}"
        return await self.redis_client.exists(blacklist_key) > 0
    
    async def cleanup_expired_sessions(self):
        """Cleanup expired sessions (background task)"""
        # Redis TTL handles this automatically, but we can do additional cleanup
        logger.info("Session cleanup completed")

