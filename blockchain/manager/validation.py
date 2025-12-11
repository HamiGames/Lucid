"""
Block Validation Module
Handles validation of block structure and integrity

This module provides validation logic for blocks.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from ..core.block_manager import BlockManager, BlockValidationResult
from ..core.models import Transaction

logger = logging.getLogger(__name__)


class BlockValidator:
    """
    Validator for block operations.
    
    Handles validation of block structure and integrity.
    """
    
    def __init__(self, block_manager: BlockManager):
        """
        Initialize block validator.
        
        Args:
            block_manager: BlockManager instance
        """
        self.block_manager = block_manager
        logger.info("BlockValidator initialized")
    
    async def validate_block_structure(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate block structure (basic validation).
        
        Args:
            block_data: Block data dictionary
            
        Returns:
            Dictionary containing validation result
        """
        try:
            errors = []
            warnings = []
            
            # Check required fields
            required_fields = ["height", "hash", "previous_hash", "merkle_root", "timestamp", "producer"]
            for field in required_fields:
                if field not in block_data:
                    errors.append(f"Missing required field: {field}")
            
            # Check field types
            if "height" in block_data:
                if not isinstance(block_data["height"], int):
                    errors.append("Height must be an integer")
                elif block_data["height"] < 0:
                    errors.append("Height must be non-negative")
            
            if "hash" in block_data:
                if not isinstance(block_data["hash"], str):
                    errors.append("Hash must be a string")
                elif len(block_data["hash"]) == 0:
                    errors.append("Hash cannot be empty")
            
            if "previous_hash" in block_data:
                if not isinstance(block_data["previous_hash"], str):
                    errors.append("Previous hash must be a string")
            
            if "merkle_root" in block_data:
                if not isinstance(block_data["merkle_root"], str):
                    errors.append("Merkle root must be a string")
            
            if "transactions" in block_data:
                if not isinstance(block_data["transactions"], list):
                    errors.append("Transactions must be a list")
                else:
                    # Check transaction count
                    if len(block_data["transactions"]) > 1000:
                        errors.append(f"Too many transactions: {len(block_data['transactions'])}")
                    elif len(block_data["transactions"]) == 0:
                        warnings.append("Block has no transactions")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            logger.error(f"Failed to validate block structure: {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": []
            }
    
    async def validate_block(self, block) -> BlockValidationResult:
        """
        Validate block using core block manager.
        
        Args:
            block: Block object to validate
            
        Returns:
            BlockValidationResult
        """
        try:
            return await self.block_manager.validate_block(block)
        except Exception as e:
            logger.error(f"Failed to validate block: {e}")
            return BlockValidationResult(
                is_valid=False,
                errors=[str(e)]
            )
    
    async def block_from_dict(self, block_data: Dict[str, Any]):
        """
        Create Block object from dictionary.
        
        Args:
            block_data: Block data dictionary
            
        Returns:
            Block object
        """
        from datetime import datetime
        
        # Convert transactions
        transactions = []
        for tx_data in block_data.get("transactions", []):
            tx = Transaction(
                id=tx_data.get("id", ""),
                from_address=tx_data.get("from_address", ""),
                to_address=tx_data.get("to_address", ""),
                value=tx_data.get("value", 0),
                data=tx_data.get("data", ""),
                timestamp=tx_data.get("timestamp", datetime.now()),
                signature=tx_data.get("signature", "")
            )
            transactions.append(tx)
        
        # Create block object (matches block_manager structure)
        from types import SimpleNamespace
        block = SimpleNamespace()
        block.height = block_data["height"]
        block.hash = block_data["hash"]
        block.previous_hash = block_data["previous_hash"]
        block.timestamp = block_data["timestamp"]
        block.transactions = transactions
        block.merkle_root = block_data["merkle_root"]
        block.producer = block_data["producer"]
        block.signature = block_data.get("signature", "")
        block.size_bytes = block_data.get("size_bytes", 0)
        
        return block

