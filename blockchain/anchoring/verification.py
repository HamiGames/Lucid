"""
Anchoring Verification Module
Handles verification of anchored session manifests

This module provides verification logic for session anchoring operations.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from ..blockchain_anchor import BlockchainAnchor

logger = logging.getLogger(__name__)


class AnchoringVerifier:
    """
    Verifier for session anchoring operations.
    
    Handles verification of anchored sessions against On-System Data Chain.
    """
    
    def __init__(self, blockchain_anchor: BlockchainAnchor):
        """
        Initialize anchoring verifier.
        
        Args:
            blockchain_anchor: BlockchainAnchor instance
        """
        self.blockchain_anchor = blockchain_anchor
        logger.info("AnchoringVerifier initialized")
    
    async def verify_transaction(
        self,
        transaction_id: str
    ) -> Dict[str, Any]:
        """
        Verify transaction on blockchain.
        
        Args:
            transaction_id: Blockchain transaction ID
            
        Returns:
            Dictionary containing verification result
        """
        try:
            status, block_number = await self.blockchain_anchor.on_chain_client.get_transaction_status(transaction_id)
            
            return {
                "verified": status == "confirmed",
                "status": status,
                "block_number": block_number,
                "transaction_id": transaction_id
            }
            
        except Exception as e:
            logger.error(f"Failed to verify transaction {transaction_id}: {e}")
            return {
                "verified": False,
                "status": "error",
                "error": str(e),
                "transaction_id": transaction_id
            }
    
    async def verify_merkle_root(
        self,
        session_id: str,
        expected_merkle_root: str
    ) -> Dict[str, Any]:
        """
        Verify merkle root for a session.
        
        Args:
            session_id: Session identifier
            expected_merkle_root: Expected merkle root hash
            
        Returns:
            Dictionary containing verification result
        """
        try:
            # Get session anchors from blockchain anchor
            anchors = await self.blockchain_anchor.get_session_anchors(session_id)
            
            if not anchors:
                return {
                    "verified": False,
                    "reason": "Session anchor not found on blockchain"
                }
            
            # Get the most recent anchor
            anchor = anchors[0] if anchors else None
            if not anchor:
                return {
                    "verified": False,
                    "reason": "No anchor records found"
                }
            
            # Compare merkle roots (check stored session manifest)
            # Merkle root is stored in the session manifest
            stored_merkle_root = anchor.get("merkle_root") or ""
            if not stored_merkle_root:
                # Try to get from session collection
                session = await self.blockchain_anchor.sessions_collection.find_one({"_id": session_id})
                if session:
                    stored_merkle_root = session.get("merkle_root", "")
            
            verified = stored_merkle_root.lower() == expected_merkle_root.lower() if stored_merkle_root else False
            
            return {
                "verified": verified,
                "expected_merkle_root": expected_merkle_root,
                "stored_merkle_root": stored_merkle_root,
                "match": verified
            }
            
        except Exception as e:
            logger.error(f"Failed to verify merkle root for {session_id}: {e}")
            return {
                "verified": False,
                "reason": str(e)
            }
    
    async def verify_session_anchor(
        self,
        session_id: str,
        merkle_root: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive verification of session anchor.
        
        Args:
            session_id: Session identifier
            merkle_root: Optional merkle root to verify
            
        Returns:
            Dictionary containing comprehensive verification result
        """
        try:
            # Get session anchors
            anchors = await self.blockchain_anchor.get_session_anchors(session_id)
            
            if not anchors:
                return {
                    "verified": False,
                    "reason": "Session anchor not found on blockchain"
                }
            
            # Get the most recent anchor
            anchor = anchors[0] if anchors else None
            if not anchor:
                return {
                    "verified": False,
                    "reason": "No anchor records found"
                }
            
            transaction_id = anchor.get("anchor_txid")
            if not transaction_id:
                return {
                    "verified": False,
                    "reason": "No transaction ID in anchor"
                }
            
            # Verify transaction
            tx_verification = await self.verify_transaction(transaction_id)
            
            # Verify merkle root if provided
            merkle_verification = None
            if merkle_root:
                merkle_verification = await self.verify_merkle_root(session_id, merkle_root)
            
            return {
                "verified": tx_verification.get("verified", False) and (
                    merkle_verification.get("verified", True) if merkle_verification else True
                ),
                "transaction_verification": tx_verification,
                "merkle_verification": merkle_verification,
                "block_number": anchor.get("block_number"),
                "transaction_id": transaction_id,
                "status": anchor.get("status", "unknown")
            }
            
        except Exception as e:
            logger.error(f"Failed to verify session anchor for {session_id}: {e}")
            return {
                "verified": False,
                "reason": str(e)
            }

