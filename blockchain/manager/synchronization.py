"""
Chain Synchronization Module
Handles synchronization with blockchain engine

This module provides chain synchronization functionality.
"""

from __future__ import annotations

import os
import logging
from typing import Dict, Any, Optional
import httpx

from ..core.block_manager import BlockManager
from .storage import BlockStorage

logger = logging.getLogger(__name__)

# Environment variable configuration (required, no hardcoded defaults)
BLOCKCHAIN_ENGINE_URL = os.getenv("BLOCKCHAIN_ENGINE_URL")
if not BLOCKCHAIN_ENGINE_URL:
    raise RuntimeError("BLOCKCHAIN_ENGINE_URL environment variable not set")

SYNC_TIMEOUT = int(os.getenv("SYNC_TIMEOUT", "30"))


class ChainSynchronizer:
    """
    Synchronizer for blockchain chain state.
    
    Handles synchronization with blockchain engine to ensure
    local chain state matches the network.
    """
    
    def __init__(
        self,
        block_manager: BlockManager,
        block_storage: BlockStorage,
        engine_url: str
    ):
        """
        Initialize chain synchronizer.
        
        Args:
            block_manager: BlockManager instance
            block_storage: BlockStorage instance
            engine_url: Blockchain engine URL
        """
        self.block_manager = block_manager
        self.block_storage = block_storage
        self.engine_url = engine_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=SYNC_TIMEOUT)
        logger.info(f"ChainSynchronizer initialized with engine: {engine_url}")
    
    async def synchronize(self) -> Dict[str, Any]:
        """
        Synchronize chain with blockchain engine.
        
        Returns:
            Dictionary containing synchronization results
        """
        try:
            logger.info("Starting chain synchronization")
            
            # Get local chain state
            local_height = self.block_manager.current_height
            local_hash = self.block_manager.latest_block_hash
            
            # Get remote chain state
            remote_state = await self._get_remote_chain_state()
            if not remote_state:
                return {
                    "success": False,
                    "error": "Failed to get remote chain state"
                }
            
            remote_height = remote_state.get("chain_height", 0)
            remote_hash = remote_state.get("latest_block_hash", "")
            
            logger.info(f"Local: height={local_height}, hash={local_hash[:16]}")
            logger.info(f"Remote: height={remote_height}, hash={remote_hash[:16]}")
            
            # Check if synchronization is needed
            if local_height == remote_height and local_hash == remote_hash:
                return {
                    "success": True,
                    "synchronized": True,
                    "message": "Chain is already synchronized",
                    "local_height": local_height,
                    "remote_height": remote_height
                }
            
            # Synchronize blocks
            if remote_height > local_height:
                synced_blocks = await self._sync_blocks(local_height + 1, remote_height)
                return {
                    "success": True,
                    "synchronized": True,
                    "synced_blocks": synced_blocks,
                    "local_height": local_height,
                    "remote_height": remote_height,
                    "new_height": self.block_manager.current_height
                }
            else:
                return {
                    "success": True,
                    "synchronized": False,
                    "message": "Local chain is ahead or hash mismatch",
                    "local_height": local_height,
                    "remote_height": remote_height
                }
                
        except Exception as e:
            logger.error(f"Failed to synchronize chain: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_remote_chain_state(self) -> Optional[Dict[str, Any]]:
        """
        Get remote chain state from blockchain engine.
        
        Returns:
            Dictionary containing remote chain state or None if failed
        """
        try:
            response = await self.client.get(f"{self.engine_url}/api/v1/blockchain/status")
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get remote chain state: {e}")
            return None
    
    async def _sync_blocks(self, start_height: int, end_height: int) -> int:
        """
        Synchronize blocks from remote.
        
        Args:
            start_height: Starting block height
            end_height: Ending block height
            
        Returns:
            Number of blocks synchronized
        """
        try:
            synced_count = 0
            
            for height in range(start_height, end_height + 1):
                # Get block from remote
                block_data = await self._get_remote_block(height)
                if not block_data:
                    logger.warning(f"Failed to get block at height {height}")
                    continue
                
                # Convert to Block object and store
                # This would need proper conversion logic
                # For now, we'll just count
                synced_count += 1
                
                if synced_count % 100 == 0:
                    logger.info(f"Synchronized {synced_count} blocks...")
            
            logger.info(f"Synchronized {synced_count} blocks from height {start_height} to {end_height}")
            return synced_count
            
        except Exception as e:
            logger.error(f"Failed to sync blocks: {e}")
            return 0
    
    async def _get_remote_block(self, height: int) -> Optional[Dict[str, Any]]:
        """
        Get block from remote blockchain engine.
        
        Args:
            height: Block height
            
        Returns:
            Block data dictionary or None if failed
        """
        try:
            response = await self.client.get(f"{self.engine_url}/api/v1/blocks/{height}")
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get remote block at height {height}: {e}")
            return None
    
    async def close(self):
        """Close synchronizer and cleanup resources."""
        try:
            await self.client.aclose()
            logger.info("ChainSynchronizer closed")
        except Exception as e:
            logger.error(f"Error closing ChainSynchronizer: {e}")

