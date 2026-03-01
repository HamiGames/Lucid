"""
Utility Functions

This module contains utility functions used throughout the Blockchain API.
Includes validation helpers, formatting functions, and common operations.
"""

import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def generate_hash(data: Union[str, bytes, dict]) -> str:
    """Generate SHA256 hash for the given data."""
    if isinstance(data, dict):
        data = json.dumps(data, sort_keys=True)
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    return hashlib.sha256(data).hexdigest()

def validate_hex_string(value: str, length: int = 64) -> bool:
    """Validate that a string is a valid hexadecimal string of specified length."""
    if not isinstance(value, str):
        return False
    
    if len(value) != length:
        return False
    
    try:
        int(value, 16)
        return True
    except ValueError:
        return False

def validate_uuid(value: str) -> bool:
    """Validate that a string is a valid UUID."""
    import re
    uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
    return bool(re.match(uuid_pattern, value))

def format_timestamp(timestamp: Union[datetime, str, float]) -> str:
    """Format timestamp to ISO 8601 format."""
    if isinstance(timestamp, str):
        return timestamp
    elif isinstance(timestamp, datetime):
        return timestamp.isoformat()
    elif isinstance(timestamp, (int, float)):
        return datetime.fromtimestamp(timestamp).isoformat()
    else:
        return datetime.now().isoformat()

def parse_timestamp(timestamp: str) -> datetime:
    """Parse ISO 8601 timestamp string to datetime object."""
    try:
        return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except ValueError:
        return datetime.now()

def calculate_merkle_root(transactions: List[str]) -> str:
    """Calculate Merkle root hash for a list of transaction hashes."""
    if not transactions:
        return "0" * 64
    
    if len(transactions) == 1:
        return transactions[0]
    
    # Convert to bytes for hashing
    tx_hashes = [bytes.fromhex(tx) for tx in transactions]
    
    while len(tx_hashes) > 1:
        next_level = []
        for i in range(0, len(tx_hashes), 2):
            if i + 1 < len(tx_hashes):
                # Hash two transactions together
                combined = tx_hashes[i] + tx_hashes[i + 1]
                next_level.append(hashlib.sha256(combined).digest())
            else:
                # Odd number of transactions, hash with itself
                combined = tx_hashes[i] + tx_hashes[i]
                next_level.append(hashlib.sha256(combined).digest())
        tx_hashes = next_level
    
    return tx_hashes[0].hex()

def validate_merkle_proof(
    leaf_hash: str,
    proof_path: List[str],
    root_hash: str,
    leaf_index: int
) -> bool:
    """Validate a Merkle proof for a given leaf hash."""
    current_hash = bytes.fromhex(leaf_hash)
    
    for i, proof_hash in enumerate(proof_path):
        proof_bytes = bytes.fromhex(proof_hash)
        
        # Determine if we're the left or right child
        if leaf_index % 2 == 0:
            # We're the left child
            current_hash = hashlib.sha256(current_hash + proof_bytes).digest()
        else:
            # We're the right child
            current_hash = hashlib.sha256(proof_bytes + current_hash).digest()
        
        leaf_index //= 2
    
    return current_hash.hex() == root_hash

def paginate_results(
    items: List[Any],
    page: int,
    limit: int
) -> Dict[str, Any]:
    """Paginate a list of items."""
    total = len(items)
    start = (page - 1) * limit
    end = start + limit
    
    paginated_items = items[start:end]
    total_pages = (total + limit - 1) // limit
    
    return {
        "items": paginated_items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": total_pages
        }
    }

def sanitize_error_message(error: str) -> str:
    """Sanitize error message for client consumption."""
    # Remove sensitive information
    sensitive_patterns = [
        r'password',
        r'token',
        r'secret',
        r'key',
        r'credential'
    ]
    
    import re
    for pattern in sensitive_patterns:
        error = re.sub(pattern, '[REDACTED]', error, flags=re.IGNORECASE)
    
    return error

def calculate_block_difficulty(block_time: float, target_time: float = 10.0) -> float:
    """Calculate block difficulty based on block time."""
    if block_time <= 0:
        return 1.0
    
    return target_time / block_time

def validate_block_structure(block_data: Dict[str, Any]) -> List[str]:
    """Validate block structure and return list of errors."""
    errors = []
    
    # Required fields
    required_fields = [
        'block_id', 'height', 'hash', 'previous_hash',
        'merkle_root', 'timestamp', 'nonce', 'difficulty',
        'transaction_count', 'block_size_bytes', 'transactions',
        'validator', 'signature'
    ]
    
    for field in required_fields:
        if field not in block_data:
            errors.append(f"Missing required field: {field}")
    
    # Validate field types
    if 'height' in block_data and not isinstance(block_data['height'], int):
        errors.append("Height must be an integer")
    
    if 'hash' in block_data and not validate_hex_string(block_data['hash']):
        errors.append("Hash must be a valid 64-character hexadecimal string")
    
    if 'previous_hash' in block_data and not validate_hex_string(block_data['previous_hash']):
        errors.append("Previous hash must be a valid 64-character hexadecimal string")
    
    if 'merkle_root' in block_data and not validate_hex_string(block_data['merkle_root']):
        errors.append("Merkle root must be a valid 64-character hexadecimal string")
    
    if 'nonce' in block_data and not isinstance(block_data['nonce'], int):
        errors.append("Nonce must be an integer")
    
    if 'difficulty' in block_data and not isinstance(block_data['difficulty'], (int, float)):
        errors.append("Difficulty must be a number")
    
    if 'transaction_count' in block_data and not isinstance(block_data['transaction_count'], int):
        errors.append("Transaction count must be an integer")
    
    if 'block_size_bytes' in block_data and not isinstance(block_data['block_size_bytes'], int):
        errors.append("Block size must be an integer")
    
    if 'transactions' in block_data and not isinstance(block_data['transactions'], list):
        errors.append("Transactions must be a list")
    
    if 'validator' in block_data and not isinstance(block_data['validator'], str):
        errors.append("Validator must be a string")
    
    if 'signature' in block_data and not isinstance(block_data['signature'], str):
        errors.append("Signature must be a string")
    
    return errors

def validate_transaction_structure(transaction_data: Dict[str, Any]) -> List[str]:
    """Validate transaction structure and return list of errors."""
    errors = []
    
    # Required fields
    required_fields = ['type', 'data', 'signature', 'fee', 'timestamp']
    
    for field in required_fields:
        if field not in transaction_data:
            errors.append(f"Missing required field: {field}")
    
    # Validate field types
    if 'type' in transaction_data and not isinstance(transaction_data['type'], str):
        errors.append("Type must be a string")
    
    if 'data' in transaction_data and not isinstance(transaction_data['data'], dict):
        errors.append("Data must be a dictionary")
    
    if 'signature' in transaction_data and not isinstance(transaction_data['signature'], str):
        errors.append("Signature must be a string")
    
    if 'fee' in transaction_data and not isinstance(transaction_data['fee'], (int, float)):
        errors.append("Fee must be a number")
    
    if 'timestamp' in transaction_data and not isinstance(transaction_data['timestamp'], str):
        errors.append("Timestamp must be a string")
    
    return errors

def format_bytes(bytes_value: int) -> str:
    """Format bytes value to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"

def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format."""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f} hours"
    else:
        days = seconds / 86400
        return f"{days:.1f} days"
