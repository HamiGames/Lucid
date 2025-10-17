"""
Security Module

This module contains security utilities for the Blockchain API.
Handles JWT token operations, password hashing, and other security functions.
"""

import logging
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.hash import bcrypt
import base64

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SecurityManager:
    """Security manager for authentication and authorization."""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def generate_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Generate a JWT token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=30)
        
        to_encode.update({"exp": expire})
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            logger.error(f"Failed to generate token: {e}")
            raise
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a JWT token and return payload."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            logger.error(f"Token verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {e}")
            return None
    
    def generate_api_key(self, length: int = 32) -> str:
        """Generate a secure API key."""
        return secrets.token_urlsafe(length)
    
    def generate_session_id(self) -> str:
        """Generate a secure session ID."""
        return secrets.token_hex(16)
    
    def generate_nonce(self) -> str:
        """Generate a secure nonce."""
        return secrets.token_hex(16)
    
    def create_signature(
        self,
        data: Union[str, bytes, Dict[str, Any]],
        secret: str
    ) -> str:
        """Create HMAC signature for data."""
        if isinstance(data, dict):
            data = str(data)
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        signature = hmac.new(
            secret.encode('utf-8'),
            data,
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def verify_signature(
        self,
        data: Union[str, bytes, Dict[str, Any]],
        signature: str,
        secret: str
    ) -> bool:
        """Verify HMAC signature for data."""
        expected_signature = self.create_signature(data, secret)
        return hmac.compare_digest(signature, expected_signature)
    
    def generate_block_hash(
        self,
        block_data: Dict[str, Any],
        nonce: int
    ) -> str:
        """Generate block hash for mining."""
        # Create block header string
        header = f"{block_data['previous_hash']}{block_data['merkle_root']}{block_data['timestamp']}{nonce}"
        
        # Hash the header
        block_hash = hashlib.sha256(header.encode('utf-8')).hexdigest()
        
        return block_hash
    
    def validate_block_hash(
        self,
        block_hash: str,
        difficulty: float
    ) -> bool:
        """Validate block hash against difficulty target."""
        # Convert difficulty to target
        target = 2 ** (256 - int(difficulty))
        
        # Convert hash to integer
        hash_int = int(block_hash, 16)
        
        # Check if hash meets target
        return hash_int < target
    
    def generate_merkle_root(self, transactions: List[str]) -> str:
        """Generate Merkle root hash for transactions."""
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
        self,
        leaf_hash: str,
        proof_path: List[str],
        root_hash: str,
        leaf_index: int
    ) -> bool:
        """Validate Merkle proof for a transaction."""
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
    
    def encrypt_data(self, data: str, key: str) -> str:
        """Encrypt data using AES encryption."""
        # Simple encryption for demo purposes
        # In production, use proper AES encryption
        import base64
        
        # XOR encryption (not secure, for demo only)
        encrypted = ""
        for i, char in enumerate(data):
            encrypted += chr(ord(char) ^ ord(key[i % len(key)]))
        
        return base64.b64encode(encrypted.encode()).decode()
    
    def decrypt_data(self, encrypted_data: str, key: str) -> str:
        """Decrypt data using AES decryption."""
        # Simple decryption for demo purposes
        # In production, use proper AES decryption
        import base64
        
        # XOR decryption (not secure, for demo only)
        encrypted = base64.b64decode(encrypted_data.encode()).decode()
        decrypted = ""
        for i, char in enumerate(encrypted):
            decrypted += chr(ord(char) ^ ord(key[i % len(key)]))
        
        return decrypted
    
    def sanitize_input(self, input_data: str) -> str:
        """Sanitize user input to prevent injection attacks."""
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '|', '`', '$']
        
        for char in dangerous_chars:
            input_data = input_data.replace(char, '')
        
        # Remove extra whitespace
        input_data = ' '.join(input_data.split())
        
        return input_data
    
    def validate_session_id(self, session_id: str) -> bool:
        """Validate session ID format."""
        import re
        uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        return bool(re.match(uuid_pattern, session_id))
    
    def validate_block_hash_format(self, block_hash: str) -> bool:
        """Validate block hash format."""
        import re
        hash_pattern = r'^[a-fA-F0-9]{64}$'
        return bool(re.match(hash_pattern, block_hash))
    
    def validate_transaction_hash_format(self, tx_hash: str) -> bool:
        """Validate transaction hash format."""
        import re
        hash_pattern = r'^[a-fA-F0-9]{64}$'
        return bool(re.match(hash_pattern, tx_hash))
    
    def generate_consensus_vote_signature(
        self,
        vote_data: Dict[str, Any],
        private_key: str
    ) -> str:
        """Generate signature for consensus vote."""
        # Create vote string
        vote_string = f"{vote_data['node_id']}{vote_data['block_hash']}{vote_data['vote']}{vote_data['timestamp']}"
        
        # Sign with private key (simplified)
        signature = self.create_signature(vote_string, private_key)
        
        return signature
    
    def verify_consensus_vote_signature(
        self,
        vote_data: Dict[str, Any],
        signature: str,
        public_key: str
    ) -> bool:
        """Verify signature for consensus vote."""
        # Create vote string
        vote_string = f"{vote_data['node_id']}{vote_data['block_hash']}{vote_data['vote']}{vote_data['timestamp']}"
        
        # Verify signature
        return self.verify_signature(vote_string, signature, public_key)
    
    def generate_block_signature(
        self,
        block_data: Dict[str, Any],
        validator_private_key: str
    ) -> str:
        """Generate signature for block."""
        # Create block string
        block_string = f"{block_data['block_id']}{block_data['height']}{block_data['hash']}{block_data['timestamp']}"
        
        # Sign with validator's private key
        signature = self.create_signature(block_string, validator_private_key)
        
        return signature
    
    def verify_block_signature(
        self,
        block_data: Dict[str, Any],
        signature: str,
        validator_public_key: str
    ) -> bool:
        """Verify signature for block."""
        # Create block string
        block_string = f"{block_data['block_id']}{block_data['height']}{block_data['hash']}{block_data['timestamp']}"
        
        # Verify signature
        return self.verify_signature(block_string, signature, validator_public_key)
