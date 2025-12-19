"""
Session Anchoring Service
Core service for anchoring session manifests to On-System Data Chain

This service integrates with the blockchain anchor system to provide
session anchoring functionality for the Lucid RDP system.
"""

from __future__ import annotations

import asyncio
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from ..blockchain_anchor import BlockchainAnchor, AnchorResult
from ..core.models import SessionManifest, SessionAnchor
from .storage import AnchoringStorage
from .manifest import ManifestBuilder

logger = logging.getLogger(__name__)

# Environment variable configuration (required, no hardcoded defaults)
ON_SYSTEM_CHAIN_RPC = os.getenv("ON_SYSTEM_CHAIN_RPC") or os.getenv("ON_SYSTEM_CHAIN_RPC_URL")
if not ON_SYSTEM_CHAIN_RPC:
    raise RuntimeError("ON_SYSTEM_CHAIN_RPC or ON_SYSTEM_CHAIN_RPC_URL environment variable not set")

LUCID_ANCHORS_ADDRESS = os.getenv("LUCID_ANCHORS_ADDRESS", "")
LUCID_CHUNK_STORE_ADDRESS = os.getenv("LUCID_CHUNK_STORE_ADDRESS", "")

MONGO_URL = os.getenv("MONGO_URL") or os.getenv("MONGODB_URL")
if not MONGO_URL:
    raise RuntimeError("MONGO_URL or MONGODB_URL environment variable not set")


class AnchoringService:
    """
    Main anchoring service for session manifests.
    
    Handles anchoring operations to On-System Data Chain via LucidAnchors contract.
    Integrates with MongoDB for persistence and On-System Chain for blockchain anchoring.
    """
    
    def __init__(self, mongo_client: Optional[AsyncIOMotorClient] = None):
        """
        Initialize anchoring service.
        
        Args:
            mongo_client: Optional MongoDB client. If not provided, creates new client.
        """
        if mongo_client:
            self.mongo_client = mongo_client
        else:
            # Get connection pool settings from environment variables (aligned with blockchain-engine)
            server_selection_timeout_ms = int(os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "5000"))
            connect_timeout_ms = int(os.getenv("MONGODB_CONNECT_TIMEOUT_MS", "10000"))
            socket_timeout_ms = int(os.getenv("MONGODB_SOCKET_TIMEOUT_MS", "20000"))
            max_pool_size = int(os.getenv("MONGODB_MAX_POOL_SIZE", "50"))
            min_pool_size = int(os.getenv("MONGODB_MIN_POOL_SIZE", "5"))
            max_idle_time_ms = int(os.getenv("MONGODB_MAX_IDLE_TIME_MS", "30000"))
            retry_writes = os.getenv("MONGODB_RETRY_WRITES", "true").lower() in ("true", "1", "yes")
            retry_reads = os.getenv("MONGODB_RETRY_READS", "true").lower() in ("true", "1", "yes")
            
            # Create client with connection options (aligned with blockchain-engine)
            self.mongo_client = AsyncIOMotorClient(
                MONGO_URL,
                serverSelectionTimeoutMS=server_selection_timeout_ms,
                connectTimeoutMS=connect_timeout_ms,
                socketTimeoutMS=socket_timeout_ms,
                maxPoolSize=max_pool_size,
                minPoolSize=min_pool_size,
                maxIdleTimeMS=max_idle_time_ms,
                retryWrites=retry_writes,
                retryReads=retry_reads
            )
        
        # Extract database name from connection string or use environment variable, default to "lucid"
        # Parse database name from MONGO_URL if present, otherwise use env var or default
        database_name = os.getenv("MONGO_DB") or os.getenv("DATABASE_NAME") or os.getenv("SESSION_ANCHORING_DB_NAME", "lucid")
        
        # Try to extract database name from connection string
        try:
            from urllib.parse import urlparse
            parsed = urlparse(MONGO_URL)
            if parsed.path and parsed.path != "/":
                # Connection string has database in path (e.g., mongodb://host/dbname)
                db_from_url = parsed.path.lstrip("/").split("?")[0]
                if db_from_url:
                    database_name = db_from_url
        except Exception:
            # If parsing fails, use the database_name from env/default
            pass
        
        self.db: AsyncIOMotorDatabase = self.mongo_client.get_database(database_name)
        
        # Initialize blockchain anchor
        self.blockchain_anchor = BlockchainAnchor(self.mongo_client)
        
        # Initialize storage
        self.storage = AnchoringStorage(self.db)
        
        # Initialize manifest builder
        self.manifest_builder = ManifestBuilder()
        
        logger.info("AnchoringService initialized")
    
    async def anchor_session(
        self,
        session_id: str,
        owner_address: str,
        merkle_root: str,
        chunk_count: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Anchor a session manifest to On-System Data Chain.
        
        Args:
            session_id: Unique session identifier
            owner_address: Ethereum address of session owner
            merkle_root: Merkle root hash of session chunks
            chunk_count: Number of chunks in session
            metadata: Optional session metadata
            
        Returns:
            Dictionary containing anchoring result with anchoring_id, status, etc.
        """
        try:
            logger.info(f"Initiating session anchoring for session: {session_id}")
            
            # Create session manifest
            manifest = SessionManifest(
                session_id=session_id,
                owner_address=owner_address,
                started_at=datetime.now(timezone.utc),
                manifest_hash="",  # Will be calculated
                merkle_root=merkle_root,
                chunk_count=chunk_count,
                chunks=[]  # Chunks stored separately
            )
            
            # Anchor to blockchain
            anchor_result: AnchorResult = await self.blockchain_anchor.anchor_session(manifest)
            
            # Store anchoring record
            anchoring_id = str(uuid.uuid4())
            await self.storage.store_anchoring_record(
                anchoring_id=anchoring_id,
                session_id=session_id,
                anchor_txid=anchor_result.anchor_txid,
                status=anchor_result.status,
                block_number=anchor_result.block_number,
                merkle_root=merkle_root,
                metadata=metadata or {}
            )
            
            logger.info(f"Session {session_id} anchored successfully: {anchor_result.anchor_txid}")
            
            return {
                "anchoring_id": anchoring_id,
                "session_id": session_id,
                "status": anchor_result.status,
                "transaction_id": anchor_result.anchor_txid,
                "block_number": anchor_result.block_number,
                "submitted_at": anchor_result.anchor_timestamp.isoformat(),
                "estimated_confirmation_time": None  # Will be updated when confirmed
            }
            
        except Exception as e:
            logger.error(f"Failed to anchor session {session_id}: {e}", exc_info=True)
            raise
    
    async def get_anchoring_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get anchoring status for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary containing anchoring status or None if not found
        """
        try:
            logger.info(f"Fetching anchoring status for session: {session_id}")
            
            # Get from storage
            record = await self.storage.get_anchoring_record(session_id)
            if not record:
                return None
            
            # Check blockchain status if pending
            if record.get("status") == "pending" and record.get("transaction_id"):
                # Check transaction status on blockchain via anchor service
                await self.blockchain_anchor.check_anchor_confirmations()
                
                # Re-fetch record after status check
                record = await self.storage.get_anchoring_record(session_id)
                if not record:
                    return None
            
            return {
                "session_id": session_id,
                "anchoring_id": record.get("anchoring_id"),
                "status": record.get("status", "unknown"),
                "submitted_at": record.get("submitted_at"),
                "confirmed_at": record.get("confirmed_at"),
                "block_height": record.get("block_number"),
                "transaction_id": record.get("transaction_id"),
                "merkle_root": record.get("merkle_root")
            }
            
        except Exception as e:
            logger.error(f"Failed to get anchoring status for {session_id}: {e}", exc_info=True)
            return None
    
    async def verify_anchoring(
        self,
        session_id: str,
        merkle_root: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify session anchoring on blockchain.
        
        Args:
            session_id: Session identifier
            merkle_root: Optional merkle root to verify against
            
        Returns:
            Dictionary containing verification result
        """
        try:
            logger.info(f"Verifying anchoring for session: {session_id}")
            
            # Get anchoring record
            record = await self.storage.get_anchoring_record(session_id)
            if not record:
                return {
                    "verified": False,
                    "reason": "Anchoring record not found"
                }
            
            transaction_id = record.get("transaction_id")
            if not transaction_id:
                return {
                    "verified": False,
                    "reason": "No transaction ID found"
                }
            
            # Verify transaction via blockchain anchor's chain client
            try:
                status, block_number = await self.blockchain_anchor.on_chain_client.get_transaction_status(
                    transaction_id
                )
                verified = status == "confirmed"
            except Exception as e:
                logger.warning(f"Failed to verify transaction via chain client: {e}, falling back to anchor records")
                # Fallback: check anchor records
                anchors = await self.blockchain_anchor.get_session_anchors(session_id)
                if not anchors:
                    return {
                        "verified": False,
                        "reason": "No anchor records found"
                    }
                
                # Find matching transaction
                anchor_record = next((a for a in anchors if a.get("anchor_txid") == transaction_id), None)
                if not anchor_record:
                    return {
                        "verified": False,
                        "reason": "Transaction not found in anchor records"
                    }
                
                status = anchor_record.get("status", "unknown")
                block_number = anchor_record.get("block_number")
                verified = status == "confirmed"
            
            # Verify merkle root if provided
            merkle_proof_valid = True
            if merkle_root:
                stored_merkle_root = record.get("merkle_root")
                merkle_proof_valid = merkle_root.lower() == stored_merkle_root.lower() if stored_merkle_root else False
            
            return {
                "verified": verified and merkle_proof_valid,
                "block_height": block_number,
                "transaction_id": transaction_id,
                "confirmation_time": record.get("confirmed_at"),
                "merkle_proof_valid": merkle_proof_valid,
                "status": status
            }
            
        except Exception as e:
            logger.error(f"Failed to verify anchoring for {session_id}: {e}", exc_info=True)
            return {
                "verified": False,
                "reason": str(e)
            }
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get current status of anchoring service.
        
        Returns:
            Dictionary containing service status metrics
        """
        try:
            # Get statistics from storage
            stats = await self.storage.get_statistics()
            
            return {
                "status": "healthy",
                "pending_anchorings": stats.get("pending", 0),
                "processing_anchorings": stats.get("processing", 0),
                "completed_today": stats.get("completed_today", 0),
                "average_confirmation_time": stats.get("avg_confirmation_time", 0.0),
                "total_anchorings": stats.get("total", 0),
                "failed_anchorings": stats.get("failed", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get service status: {e}", exc_info=True)
            return {
                "status": "degraded",
                "error": str(e)
            }
    
    async def close(self):
        """Close service and cleanup resources."""
        try:
            await self.blockchain_anchor.close()
            self.mongo_client.close()
            logger.info("AnchoringService closed")
        except Exception as e:
            logger.error(f"Error closing AnchoringService: {e}")

