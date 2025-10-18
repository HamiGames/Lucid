# Path: blockchain/utils/validation.py
# Lucid Blockchain Core - Validation Utilities
# Provides validation functions for blockchain data structures
# Based on BUILD_REQUIREMENTS_GUIDE.md Step 11 and blockchain cluster specifications

from __future__ import annotations

import re
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import ipaddress

from .crypto import CryptoUtils, HashAlgorithm, SignatureAlgorithm

# Validation constants
MIN_BLOCK_HEIGHT = 0
MAX_BLOCK_HEIGHT = 2**63 - 1
MIN_TRANSACTION_VALUE = 0
MAX_TRANSACTION_VALUE = 2**63 - 1
MAX_TRANSACTION_DATA_SIZE = 1024 * 1024  # 1MB
MAX_BLOCK_SIZE = 10 * 1024 * 1024  # 10MB
MAX_TRANSACTIONS_PER_BLOCK = 10000
MIN_TIMESTAMP_DRIFT = timedelta(minutes=-5)  # 5 minutes in past
MAX_TIMESTAMP_DRIFT = timedelta(minutes=5)   # 5 minutes in future

class ValidationSeverity(Enum):
    """Validation error severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationResult:
    """Result of a validation operation"""
    is_valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    info: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.info is None:
            self.info = []
    
    def add_error(self, message: str):
        """Add an error message"""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add a warning message"""
        self.warnings.append(message)
    
    def add_info(self, message: str):
        """Add an info message"""
        self.info.append(message)
    
    def has_errors(self) -> bool:
        """Check if there are any errors"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings"""
        return len(self.warnings) > 0
    
    def get_all_messages(self) -> List[Tuple[ValidationSeverity, str]]:
        """Get all messages with their severity levels"""
        messages = []
        for error in self.errors:
            messages.append((ValidationSeverity.ERROR, error))
        for warning in self.warnings:
            messages.append((ValidationSeverity.WARNING, warning))
        for info in self.info:
            messages.append((ValidationSeverity.INFO, info))
        return messages

class BlockchainValidator:
    """
    Comprehensive validation utilities for blockchain data structures
    
    Provides validation for:
    - Blockchain addresses
    - Transaction data
    - Block data
    - Merkle trees
    - Cryptographic signatures
    - Network data
    - Session data
    """
    
    @staticmethod
    def validate_address(address: str) -> ValidationResult:
        """
        Validate a blockchain address
        
        Args:
            address: Address to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        if not isinstance(address, str):
            result.add_error("Address must be a string")
            return result
        
        if not address:
            result.add_error("Address cannot be empty")
            return result
        
        if not address.startswith("0x"):
            result.add_error("Address must start with '0x'")
            return result
        
        if len(address) != 42:
            result.add_error(f"Address must be 42 characters long, got {len(address)}")
            return result
        
        # Check if hex
        try:
            int(address[2:], 16)
        except ValueError:
            result.add_error("Address contains invalid hexadecimal characters")
            return result
        
        # Check for common invalid addresses
        if address == "0x" + "0" * 40:
            result.add_warning("Address is the zero address")
        
        return result
    
    @staticmethod
    def validate_hash(hash_value: str, expected_length: int = 64) -> ValidationResult:
        """
        Validate a hash value
        
        Args:
            hash_value: Hash to validate
            expected_length: Expected length of hash (default: 64 for 256-bit)
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        if not isinstance(hash_value, str):
            result.add_error("Hash must be a string")
            return result
        
        if not hash_value:
            result.add_error("Hash cannot be empty")
            return result
        
        if len(hash_value) != expected_length:
            result.add_error(f"Hash must be {expected_length} characters long, got {len(hash_value)}")
            return result
        
        # Check if hex
        try:
            int(hash_value, 16)
        except ValueError:
            result.add_error("Hash contains invalid hexadecimal characters")
            return result
        
        # Check for common invalid hashes
        if hash_value == "0" * expected_length:
            result.add_warning("Hash is all zeros")
        
        return result
    
    @staticmethod
    def validate_transaction_id(tx_id: str) -> ValidationResult:
        """
        Validate a transaction ID
        
        Args:
            tx_id: Transaction ID to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        if not isinstance(tx_id, str):
            result.add_error("Transaction ID must be a string")
            return result
        
        if not tx_id:
            result.add_error("Transaction ID cannot be empty")
            return result
        
        # Transaction ID should be a valid identifier
        if not re.match(r'^[a-zA-Z0-9_-]+$', tx_id):
            result.add_error("Transaction ID contains invalid characters")
            return result
        
        if len(tx_id) < 8:
            result.add_error("Transaction ID too short (minimum 8 characters)")
            return result
        
        if len(tx_id) > 128:
            result.add_error("Transaction ID too long (maximum 128 characters)")
            return result
        
        return result
    
    @staticmethod
    def validate_transaction_value(value: Union[int, float]) -> ValidationResult:
        """
        Validate a transaction value
        
        Args:
            value: Transaction value to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        if not isinstance(value, (int, float)):
            result.add_error("Transaction value must be a number")
            return result
        
        if value < MIN_TRANSACTION_VALUE:
            result.add_error(f"Transaction value cannot be negative: {value}")
            return result
        
        if value > MAX_TRANSACTION_VALUE:
            result.add_error(f"Transaction value too large: {value}")
            return result
        
        if isinstance(value, float) and value != int(value):
            result.add_warning("Transaction value has decimal places")
        
        return result
    
    @staticmethod
    def validate_transaction_data(data: str) -> ValidationResult:
        """
        Validate transaction data field
        
        Args:
            data: Transaction data to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        if not isinstance(data, str):
            result.add_error("Transaction data must be a string")
            return result
        
        # Check size
        data_size = len(data.encode('utf-8'))
        if data_size > MAX_TRANSACTION_DATA_SIZE:
            result.add_error(f"Transaction data too large: {data_size} bytes (max: {MAX_TRANSACTION_DATA_SIZE})")
            return result
        
        # Check if valid JSON (if not empty)
        if data and data.strip():
            try:
                json.loads(data)
                result.add_info("Transaction data is valid JSON")
            except json.JSONDecodeError:
                result.add_warning("Transaction data is not valid JSON")
        
        return result
    
    @staticmethod
    def validate_timestamp(timestamp: datetime, allow_future: bool = True) -> ValidationResult:
        """
        Validate a timestamp
        
        Args:
            timestamp: Timestamp to validate
            allow_future: Whether to allow future timestamps
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        if not isinstance(timestamp, datetime):
            result.add_error("Timestamp must be a datetime object")
            return result
        
        # Check timezone
        if timestamp.tzinfo is None:
            result.add_warning("Timestamp has no timezone information")
        elif timestamp.tzinfo != timezone.utc:
            result.add_warning("Timestamp is not in UTC")
        
        now = datetime.now(timezone.utc)
        
        # Check if too far in the past
        if timestamp < now + MIN_TIMESTAMP_DRIFT:
            result.add_error(f"Timestamp too far in the past: {timestamp}")
            return result
        
        # Check if too far in the future
        if not allow_future and timestamp > now + MAX_TIMESTAMP_DRIFT:
            result.add_error(f"Timestamp too far in the future: {timestamp}")
            return result
        
        return result
    
    @staticmethod
    def validate_block_height(height: int) -> ValidationResult:
        """
        Validate a block height
        
        Args:
            height: Block height to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        if not isinstance(height, int):
            result.add_error("Block height must be an integer")
            return result
        
        if height < MIN_BLOCK_HEIGHT:
            result.add_error(f"Block height cannot be negative: {height}")
            return result
        
        if height > MAX_BLOCK_HEIGHT:
            result.add_error(f"Block height too large: {height}")
            return result
        
        return result
    
    @staticmethod
    def validate_block_sequence(current_height: int, previous_height: int) -> ValidationResult:
        """
        Validate block height sequence
        
        Args:
            current_height: Current block height
            previous_height: Previous block height
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        # Validate individual heights
        current_result = BlockchainValidator.validate_block_height(current_height)
        previous_result = BlockchainValidator.validate_block_height(previous_height)
        
        if not current_result.is_valid:
            result.errors.extend(current_result.errors)
            return result
        
        if not previous_result.is_valid:
            result.errors.extend(previous_result.errors)
            return result
        
        # Check sequence
        if current_height == 0:
            # Genesis block
            if previous_height != -1:  # Special case for genesis
                result.add_info("Genesis block validation")
        else:
            if current_height != previous_height + 1:
                result.add_error(f"Invalid block sequence: {current_height} should follow {previous_height}")
                return result
        
        return result
    
    @staticmethod
    def validate_merkle_root(merkle_root: str, transaction_hashes: List[str]) -> ValidationResult:
        """
        Validate a Merkle root against transaction hashes
        
        Args:
            merkle_root: Merkle root to validate
            transaction_hashes: List of transaction hashes
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        # Validate merkle root format
        root_result = BlockchainValidator.validate_hash(merkle_root)
        if not root_result.is_valid:
            result.errors.extend(root_result.errors)
            return result
        
        # Validate transaction hashes
        for i, tx_hash in enumerate(transaction_hashes):
            hash_result = BlockchainValidator.validate_hash(tx_hash)
            if not hash_result.is_valid:
                result.add_error(f"Invalid transaction hash at index {i}: {tx_hash}")
                return result
        
        # Calculate expected Merkle root
        if not transaction_hashes:
            expected_root = "0" * 64
        else:
            # Build Merkle tree
            leaves = [CryptoUtils.create_merkle_leaf_hash(tx_hash) for tx_hash in transaction_hashes]
            
            while len(leaves) > 1:
                next_level = []
                for i in range(0, len(leaves), 2):
                    left = leaves[i]
                    right = leaves[i + 1] if i + 1 < len(leaves) else left
                    combined = CryptoUtils.create_merkle_internal_hash(left, right)
                    next_level.append(combined)
                leaves = next_level
            
            expected_root = leaves[0] if leaves else "0" * 64
        
        # Compare roots
        if merkle_root != expected_root:
            result.add_error(f"Merkle root mismatch: expected {expected_root}, got {merkle_root}")
            return result
        
        result.add_info(f"Merkle root validated for {len(transaction_hashes)} transactions")
        return result
    
    @staticmethod
    def validate_signature_format(signature: str) -> ValidationResult:
        """
        Validate signature format
        
        Args:
            signature: Signature to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        if not isinstance(signature, str):
            result.add_error("Signature must be a string")
            return result
        
        if not signature:
            result.add_error("Signature cannot be empty")
            return result
        
        # Check if hex
        try:
            int(signature, 16)
        except ValueError:
            result.add_error("Signature contains invalid hexadecimal characters")
            return result
        
        # Check length (Ed25519 signatures are 64 bytes = 128 hex chars)
        if len(signature) not in [128, 256, 512]:  # Support different signature lengths
            result.add_warning(f"Unusual signature length: {len(signature)} characters")
        
        return result
    
    @staticmethod
    def validate_node_id(node_id: str) -> ValidationResult:
        """
        Validate a node ID
        
        Args:
            node_id: Node ID to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        if not isinstance(node_id, str):
            result.add_error("Node ID must be a string")
            return result
        
        if not node_id:
            result.add_error("Node ID cannot be empty")
            return result
        
        # Node ID should be a valid identifier
        if not re.match(r'^[a-zA-Z0-9_-]+$', node_id):
            result.add_error("Node ID contains invalid characters")
            return result
        
        if len(node_id) < 3:
            result.add_error("Node ID too short (minimum 3 characters)")
            return result
        
        if len(node_id) > 64:
            result.add_error("Node ID too long (maximum 64 characters)")
            return result
        
        return result
    
    @staticmethod
    def validate_session_id(session_id: str) -> ValidationResult:
        """
        Validate a session ID
        
        Args:
            session_id: Session ID to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        if not isinstance(session_id, str):
            result.add_error("Session ID must be a string")
            return result
        
        if not session_id:
            result.add_error("Session ID cannot be empty")
            return result
        
        # Session ID should be a valid identifier
        if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
            result.add_error("Session ID contains invalid characters")
            return result
        
        if len(session_id) < 8:
            result.add_error("Session ID too short (minimum 8 characters)")
            return result
        
        if len(session_id) > 128:
            result.add_error("Session ID too long (maximum 128 characters)")
            return result
        
        return result
    
    @staticmethod
    def validate_ip_address(ip_address: str) -> ValidationResult:
        """
        Validate an IP address
        
        Args:
            ip_address: IP address to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        if not isinstance(ip_address, str):
            result.add_error("IP address must be a string")
            return result
        
        if not ip_address:
            result.add_error("IP address cannot be empty")
            return result
        
        try:
            ip = ipaddress.ip_address(ip_address)
            
            if ip.is_private:
                result.add_warning("IP address is private")
            
            if ip.is_loopback:
                result.add_warning("IP address is loopback")
            
            if ip.is_multicast:
                result.add_warning("IP address is multicast")
            
            if isinstance(ip, ipaddress.IPv6Address):
                result.add_info("IP address is IPv6")
            else:
                result.add_info("IP address is IPv4")
                
        except ValueError as e:
            result.add_error(f"Invalid IP address: {e}")
            return result
        
        return result
    
    @staticmethod
    def validate_port(port: int) -> ValidationResult:
        """
        Validate a network port
        
        Args:
            port: Port number to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        if not isinstance(port, int):
            result.add_error("Port must be an integer")
            return result
        
        if port < 1 or port > 65535:
            result.add_error(f"Port must be between 1 and 65535, got {port}")
            return result
        
        if port < 1024:
            result.add_warning("Port is in the privileged range (< 1024)")
        
        return result
    
    @staticmethod
    def validate_url(url: str) -> ValidationResult:
        """
        Validate a URL
        
        Args:
            url: URL to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        if not isinstance(url, str):
            result.add_error("URL must be a string")
            return result
        
        if not url:
            result.add_error("URL cannot be empty")
            return result
        
        # Basic URL validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(url):
            result.add_error("Invalid URL format")
            return result
        
        if url.startswith('http://'):
            result.add_warning("URL uses insecure HTTP protocol")
        
        return result
    
    @staticmethod
    def validate_json_data(data: str) -> ValidationResult:
        """
        Validate JSON data
        
        Args:
            data: JSON string to validate
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        if not isinstance(data, str):
            result.add_error("JSON data must be a string")
            return result
        
        if not data.strip():
            result.add_info("JSON data is empty")
            return result
        
        try:
            parsed = json.loads(data)
            result.add_info(f"Valid JSON with {len(str(parsed))} characters")
        except json.JSONDecodeError as e:
            result.add_error(f"Invalid JSON: {e}")
            return result
        
        return result
    
    @staticmethod
    def validate_chunk_metadata(chunk_id: str, chunk_hash: str, size: int) -> ValidationResult:
        """
        Validate chunk metadata
        
        Args:
            chunk_id: Chunk identifier
            chunk_hash: Chunk hash
            size: Chunk size in bytes
            
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        # Validate chunk ID
        if not isinstance(chunk_id, str) or not chunk_id:
            result.add_error("Chunk ID must be a non-empty string")
            return result
        
        # Validate chunk hash
        hash_result = BlockchainValidator.validate_hash(chunk_hash)
        if not hash_result.is_valid:
            result.errors.extend(hash_result.errors)
            return result
        
        # Validate size
        if not isinstance(size, int) or size < 0:
            result.add_error("Chunk size must be a non-negative integer")
            return result
        
        if size == 0:
            result.add_warning("Chunk size is zero")
        
        if size > 100 * 1024 * 1024:  # 100MB
            result.add_warning(f"Large chunk size: {size} bytes")
        
        return result

# Convenience functions for common validations
def is_valid_address(address: str) -> bool:
    """Check if address is valid"""
    return BlockchainValidator.validate_address(address).is_valid

def is_valid_hash(hash_value: str) -> bool:
    """Check if hash is valid"""
    return BlockchainValidator.validate_hash(hash_value).is_valid

def is_valid_transaction_id(tx_id: str) -> bool:
    """Check if transaction ID is valid"""
    return BlockchainValidator.validate_transaction_id(tx_id).is_valid

def is_valid_node_id(node_id: str) -> bool:
    """Check if node ID is valid"""
    return BlockchainValidator.validate_node_id(node_id).is_valid

def is_valid_session_id(session_id: str) -> bool:
    """Check if session ID is valid"""
    return BlockchainValidator.validate_session_id(session_id).is_valid

# Export main classes and functions
__all__ = [
    "BlockchainValidator",
    "ValidationResult",
    "ValidationSeverity",
    "is_valid_address",
    "is_valid_hash",
    "is_valid_transaction_id",
    "is_valid_node_id",
    "is_valid_session_id"
]
