"""
Blockchain Engine Client for Session Token Recovery
File: gui-api-bridge/gui-api-bridge/integration/blockchain_client.py
Pattern: Follow sessions/integration/blockchain_client.py and blockchain/core/blockchain_engine.py patterns
Purpose: Integration with lucid-blockchain-engine for session data token recovery
"""

import logging
from typing import Optional, Dict, Any
from .service_base import ServiceBaseClient
from ..config import GuiAPIBridgeSettings

logger = logging.getLogger(__name__)


class BlockchainEngineClient(ServiceBaseClient):
    """
    Client for Blockchain Engine service
    Provides session token recovery and anchor verification functionality
    """
    
    def __init__(self, config: GuiAPIBridgeSettings):
        """Initialize blockchain engine client"""
        super().__init__(
            service_name="blockchain-engine",
            service_url=config.BLOCKCHAIN_ENGINE_URL,
            config=config,
        )
    
    async def get_session_anchor(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session anchor from blockchain
        
        Args:
            session_id: Session identifier
        
        Returns:
            Session anchor data with merkle_root and txid, or None on error
        """
        try:
            endpoint = f"/api/v1/sessions/{session_id}/anchor"
            response = await self.get(endpoint)
            
            if response:
                logger.info(f"Retrieved anchor for session {session_id}")
                return response
            else:
                logger.warning(f"Failed to get anchor for session {session_id}")
                return None
        
        except Exception as e:
            logger.error(f"Error getting session anchor: {e}")
            return None
    
    async def recover_session_token(
        self,
        session_id: str,
        owner_address: str,
    ) -> Optional[str]:
        """
        Recover session token from blockchain anchor
        
        Args:
            session_id: Session identifier
            owner_address: Owner wallet address to verify ownership
        
        Returns:
            Recovered session token, or None on error
        """
        try:
            # Get session anchor first
            anchor = await self.get_session_anchor(session_id)
            if not anchor:
                logger.warning(f"No anchor found for session {session_id}")
                return None
            
            # Verify ownership by checking owner_address
            # This would be part of the anchor data returned from blockchain
            if anchor.get("owner_address") != owner_address:
                logger.warning(f"Owner address mismatch for session {session_id}")
                return None
            
            # Extract or derive token from anchor data
            # The actual token recovery logic depends on how tokens are stored in anchors
            token = anchor.get("token") or anchor.get("session_token")
            
            if token:
                logger.info(f"Successfully recovered token for session {session_id}")
                return token
            else:
                logger.warning(f"No token found in anchor for session {session_id}")
                return None
        
        except Exception as e:
            logger.error(f"Error recovering session token: {e}")
            return None
    
    async def verify_session_anchor(
        self,
        session_id: str,
        merkle_root: str,
    ) -> bool:
        """
        Verify session anchor on blockchain
        
        Args:
            session_id: Session identifier
            merkle_root: Merkle root to verify
        
        Returns:
            True if anchor is valid, False otherwise
        """
        try:
            endpoint = f"/api/v1/sessions/{session_id}/verify"
            response = await self.post(
                endpoint,
                json={"merkle_root": merkle_root},
            )
            
            if response:
                is_valid = response.get("valid", False)
                logger.info(f"Anchor verification for {session_id}: {'VALID' if is_valid else 'INVALID'}")
                return is_valid
            else:
                logger.warning(f"Failed to verify anchor for session {session_id}")
                return False
        
        except Exception as e:
            logger.error(f"Error verifying session anchor: {e}")
            return False
    
    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session anchoring status
        
        Args:
            session_id: Session identifier
        
        Returns:
            Session status data, or None on error
        """
        try:
            endpoint = f"/api/v1/sessions/{session_id}/status"
            response = await self.get(endpoint)
            
            if response:
                logger.debug(f"Retrieved status for session {session_id}")
                return response
            else:
                logger.warning(f"Failed to get status for session {session_id}")
                return None
        
        except Exception as e:
            logger.error(f"Error getting session status: {e}")
            return None
    
    async def list_session_anchors(
        self,
        owner_address: Optional[str] = None,
        limit: int = 100,
    ) -> Optional[Dict[str, Any]]:
        """
        List session anchors for an owner
        
        Args:
            owner_address: Owner address to filter by (optional)
            limit: Maximum number of anchors to return
        
        Returns:
            List of session anchors, or None on error
        """
        try:
            endpoint = "/api/v1/sessions/anchors"
            params = {"limit": limit}
            
            if owner_address:
                params["owner_address"] = owner_address
            
            response = await self.get(endpoint, params=params)
            
            if response:
                logger.debug(f"Retrieved {len(response.get('anchors', []))} anchors")
                return response
            else:
                logger.warning("Failed to list session anchors")
                return None
        
        except Exception as e:
            logger.error(f"Error listing session anchors: {e}")
            return None
