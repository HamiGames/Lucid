# Lucid Coding Standards

## Document Control

| Attribute | Value |
|-----------|-------|
| Document ID | LUCID-CODE-001 |
| Version | 1.0.0 |
| Status | ACTIVE |
| Last Updated | 2025-01-14 |
| Based On | Master Build Plan v1.0.0 |

---

## Overview

This document establishes coding standards and best practices for the Lucid blockchain system. These standards ensure code quality, maintainability, and consistency across all components of the system.

### Code Quality Principles

```
┌─────────────────────────────────────────────────────────────┐
│                    Code Quality Framework                   │
│  Readability + Maintainability + Performance + Security    │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                Code Standards Layer                       │
│  Style + Naming + Documentation + Testing + Review        │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                Implementation Layer                      │
│  Python + JavaScript + Docker + Configuration            │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                Quality Assurance Layer                   │
│  Linting + Testing + Review + CI/CD + Monitoring          │
└─────────────────────────────────────────────────────────────┘
```

---

## Python Coding Standards

### Code Style

#### PEP 8 Compliance

```python
# Good: Follow PEP 8 guidelines
def calculate_block_hash(block_data: dict, timestamp: int) -> str:
    """Calculate SHA-256 hash of block data.
    
    Args:
        block_data: Dictionary containing block data
        timestamp: Unix timestamp of block creation
        
    Returns:
        Hexadecimal string representation of hash
        
    Raises:
        ValueError: If block_data is invalid
    """
    if not isinstance(block_data, dict):
        raise ValueError("block_data must be a dictionary")
    
    # Use descriptive variable names
    block_string = json.dumps(block_data, sort_keys=True)
    combined_data = f"{block_string}{timestamp}"
    
    return hashlib.sha256(combined_data.encode()).hexdigest()

# Bad: Non-compliant code
def calc_hash(bd,ts):
    return hashlib.sha256((json.dumps(bd)+str(ts)).encode()).hexdigest()
```

#### Line Length and Formatting

```python
# Good: Proper line length (max 120 characters)
def process_transaction(
    transaction_data: dict,
    validation_rules: list,
    blockchain_state: dict,
    network_config: dict
) -> TransactionResult:
    """Process a blockchain transaction with validation."""
    pass

# Good: Use parentheses for line continuation
result = (
    some_long_function_call(
        parameter1,
        parameter2,
        parameter3
    )
)

# Bad: Lines too long
def process_transaction(transaction_data, validation_rules, blockchain_state, network_config):
    pass
```

#### Import Organization

```python
# Good: Organized imports
# Standard library imports
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Union

# Third-party imports
import requests
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException

# Local imports
from .models import Transaction, Block
from .utils import validate_signature
from .exceptions import ValidationError
```

### Naming Conventions

#### Variables and Functions

```python
# Good: Descriptive names
user_authentication_token = "abc123"
max_retry_attempts = 3
is_transaction_valid = True

def validate_blockchain_transaction():
    pass

def calculate_merkle_root():
    pass

# Bad: Unclear names
token = "abc123"
max = 3
valid = True

def validate():
    pass

def calc():
    pass
```

#### Classes and Constants

```python
# Good: PascalCase for classes
class BlockchainEngine:
    pass

class TransactionValidator:
    pass

# Good: UPPER_CASE for constants
MAX_BLOCK_SIZE = 1024 * 1024  # 1MB
DEFAULT_CONSENSUS_ALGORITHM = "proof_of_stake"
SUPPORTED_HASH_ALGORITHMS = ["sha256", "sha3", "blake2b"]

# Good: Private methods with underscore
class BlockchainEngine:
    def _validate_block(self, block):
        pass
    
    def _calculate_difficulty(self):
        pass
```

### Type Hints

#### Function Signatures

```python
# Good: Complete type hints
from typing import Dict, List, Optional, Union, Tuple

def process_transactions(
    transactions: List[Dict[str, Union[str, int]]],
    validation_rules: Optional[Dict[str, bool]] = None,
    timeout: int = 30
) -> Tuple[bool, List[str]]:
    """Process a list of transactions with validation."""
    pass

# Good: Complex type hints
from typing import Protocol, TypeVar, Generic

T = TypeVar('T')

class BlockchainNode(Protocol):
    def validate_block(self, block: Block) -> bool: ...

class BlockchainEngine(Generic[T]):
    def __init__(self, node: BlockchainNode) -> None:
        self.node = node
```

#### Variable Annotations

```python
# Good: Variable type hints
user_id: int = 12345
is_authenticated: bool = True
transaction_fees: List[float] = [0.001, 0.002, 0.003]
blockchain_state: Dict[str, Union[str, int]] = {
    "height": 1000,
    "hash": "abc123",
    "timestamp": 1640995200
}
```

### Error Handling

#### Exception Handling

```python
# Good: Specific exception handling
import logging
from .exceptions import ValidationError, NetworkError, ConsensusError

logger = logging.getLogger(__name__)

def validate_transaction(transaction: dict) -> bool:
    """Validate a blockchain transaction."""
    try:
        # Validate transaction structure
        if not isinstance(transaction, dict):
            raise ValidationError("Transaction must be a dictionary")
        
        # Validate required fields
        required_fields = ["sender", "receiver", "amount", "signature"]
        for field in required_fields:
            if field not in transaction:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate signature
        if not self._verify_signature(transaction):
            raise ValidationError("Invalid transaction signature")
        
        return True
        
    except ValidationError as e:
        logger.error(f"Transaction validation failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during validation: {e}")
        return False

# Bad: Generic exception handling
def validate_transaction(transaction):
    try:
        # validation logic
        return True
    except:
        return False
```

#### Custom Exceptions

```python
# Good: Custom exception hierarchy
class LucidError(Exception):
    """Base exception for Lucid system."""
    pass

class ValidationError(LucidError):
    """Raised when validation fails."""
    pass

class NetworkError(LucidError):
    """Raised when network operations fail."""
    pass

class ConsensusError(LucidError):
    """Raised when consensus operations fail."""
    pass
```

### Documentation

#### Docstrings

```python
# Good: Comprehensive docstrings
def create_block(
    transactions: List[Dict[str, Any]],
    previous_hash: str,
    timestamp: Optional[int] = None
) -> Block:
    """Create a new blockchain block.
    
    This function creates a new block containing the provided transactions
    and links it to the previous block in the chain.
    
    Args:
        transactions: List of transaction dictionaries to include in block
        previous_hash: SHA-256 hash of the previous block
        timestamp: Unix timestamp for block creation (defaults to current time)
        
    Returns:
        Block object containing transactions and metadata
        
    Raises:
        ValidationError: If transactions are invalid
        NetworkError: If network operations fail
        
    Example:
        >>> transactions = [{"sender": "alice", "receiver": "bob", "amount": 100}]
        >>> block = create_block(transactions, "abc123")
        >>> print(block.hash)
        'def456'
    """
    pass
```

#### Inline Comments

```python
# Good: Meaningful comments
def calculate_merkle_root(transactions: List[Transaction]) -> str:
    """Calculate Merkle root for transaction list."""
    if not transactions:
        return ""
    
    # Convert transactions to hash strings
    transaction_hashes = [tx.hash for tx in transactions]
    
    # Build Merkle tree bottom-up
    while len(transaction_hashes) > 1:
        next_level = []
        
        # Process pairs of hashes
        for i in range(0, len(transaction_hashes), 2):
            left = transaction_hashes[i]
            right = transaction_hashes[i + 1] if i + 1 < len(transaction_hashes) else left
            combined = left + right
            next_level.append(hashlib.sha256(combined.encode()).hexdigest())
        
        transaction_hashes = next_level
    
    return transaction_hashes[0]

# Bad: Obvious comments
def calculate_merkle_root(transactions):
    # Check if empty
    if not transactions:
        return ""
    
    # Get hashes
    hashes = [tx.hash for tx in transactions]
    
    # Loop
    while len(hashes) > 1:
        # Do something
        pass
```

---

## JavaScript/TypeScript Standards

### Code Style

#### ESLint Configuration

```javascript
// Good: Consistent formatting
const processTransaction = async (
  transactionData: TransactionData,
  validationRules: ValidationRules
): Promise<TransactionResult> => {
  try {
    // Validate transaction
    const isValid = await validateTransaction(transactionData, validationRules);
    
    if (!isValid) {
      throw new ValidationError('Transaction validation failed');
    }
    
    // Process transaction
    const result = await blockchainEngine.processTransaction(transactionData);
    
    return {
      success: true,
      transactionId: result.id,
      blockHash: result.blockHash
    };
    
  } catch (error) {
    logger.error('Transaction processing failed:', error);
    throw error;
  }
};
```

#### TypeScript Types

```typescript
// Good: Comprehensive type definitions
interface TransactionData {
  sender: string;
  receiver: string;
  amount: number;
  signature: string;
  timestamp: number;
}

interface ValidationRules {
  maxAmount: number;
  minAmount: number;
  allowedSenders: string[];
  requiredFields: string[];
}

interface TransactionResult {
  success: boolean;
  transactionId?: string;
  blockHash?: string;
  error?: string;
}

// Good: Generic types
class BlockchainEngine<T extends TransactionData> {
  private transactions: T[] = [];
  
  async processTransaction(transaction: T): Promise<TransactionResult> {
    // Implementation
  }
}
```

### Async/Await Patterns

```typescript
// Good: Proper async/await usage
const processBlockchainTransaction = async (
  transaction: TransactionData
): Promise<void> => {
  try {
    // Validate transaction
    await validateTransaction(transaction);
    
    // Add to mempool
    await mempool.addTransaction(transaction);
    
    // Broadcast to network
    await network.broadcastTransaction(transaction);
    
    logger.info('Transaction processed successfully', {
      transactionId: transaction.id
    });
    
  } catch (error) {
    logger.error('Transaction processing failed', {
      error: error.message,
      transactionId: transaction.id
    });
    throw error;
  }
};

// Good: Parallel processing
const processMultipleTransactions = async (
  transactions: TransactionData[]
): Promise<TransactionResult[]> => {
  const promises = transactions.map(transaction => 
    processBlockchainTransaction(transaction)
  );
  
  return Promise.allSettled(promises);
};
```

---

## Docker Standards

### Dockerfile Best Practices

#### Multi-stage Builds

```dockerfile
# Good: Multi-stage build for Python service
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM gcr.io/distroless/python3-debian12:latest

# Copy application and dependencies
COPY --from=builder /root/.local /root/.local
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create non-root user
USER 1000:1000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import requests; requests.get('http://localhost:8000/health')"]

# Run application
ENTRYPOINT ["python", "main.py"]
```

#### Security Hardening

```dockerfile
# Good: Security-hardened Dockerfile
FROM gcr.io/distroless/python3-debian12:latest

# Set working directory
WORKDIR /app

# Copy application
COPY --chown=1000:1000 . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production

# Create non-root user
USER 1000:1000

# Set read-only filesystem
# Note: This requires tmpfs for writable directories

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import requests; requests.get('http://localhost:8000/health')"]

# Run application
ENTRYPOINT ["python", "main.py"]
```

### Docker Compose Standards

#### Service Configuration

```yaml
# Good: Well-structured docker-compose.yml
version: '3.8'

services:
  lucid-api-gateway:
    build:
      context: .
      dockerfile: Dockerfile.api-gateway
    container_name: lucid-api-gateway
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - NODE_ENV=production
      - LOG_LEVEL=INFO
      - MONGODB_URI=mongodb://lucid:${MONGO_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
      - REDIS_URI=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0
    depends_on:
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-network
    volumes:
      - lucid-api-logs:/app/logs
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8080/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  lucid-mongodb:
    image: mongo:6.0
    container_name: lucid-mongodb
    restart: unless-stopped
    ports:
      - "27017:27017"
    environment:
      - MONGO_INITDB_ROOT_USERNAME=lucid
      - MONGO_INITDB_ROOT_PASSWORD=${MONGO_PASSWORD}
      - MONGO_INITDB_DATABASE=lucid
    volumes:
      - lucid-mongo-data:/data/db
      - ./configs/mongodb:/etc/mongod
    networks:
      - lucid-network
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.runCommand({ping: 1})"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  lucid-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

volumes:
  lucid-mongo-data:
  lucid-api-logs:
```

---

## Testing Standards

### Unit Testing

#### Python Testing with pytest

```python
# Good: Comprehensive unit tests
import pytest
from unittest.mock import Mock, patch
from .blockchain import BlockchainEngine
from .exceptions import ValidationError

class TestBlockchainEngine:
    """Test cases for BlockchainEngine class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.blockchain = BlockchainEngine()
        self.sample_transaction = {
            "sender": "alice",
            "receiver": "bob",
            "amount": 100,
            "signature": "abc123"
        }
    
    def test_create_block_success(self):
        """Test successful block creation."""
        # Arrange
        transactions = [self.sample_transaction]
        previous_hash = "def456"
        
        # Act
        block = self.blockchain.create_block(transactions, previous_hash)
        
        # Assert
        assert block.transactions == transactions
        assert block.previous_hash == previous_hash
        assert block.hash is not None
        assert len(block.hash) == 64  # SHA-256 hash length
    
    def test_create_block_invalid_transaction(self):
        """Test block creation with invalid transaction."""
        # Arrange
        invalid_transaction = {"invalid": "data"}
        
        # Act & Assert
        with pytest.raises(ValidationError):
            self.blockchain.create_block([invalid_transaction], "def456")
    
    @patch('blockchain.hashlib.sha256')
    def test_create_block_hash_calculation(self, mock_sha256):
        """Test hash calculation in block creation."""
        # Arrange
        mock_sha256.return_value.hexdigest.return_value = "mocked_hash"
        
        # Act
        block = self.blockchain.create_block([self.sample_transaction], "def456")
        
        # Assert
        assert block.hash == "mocked_hash"
        mock_sha256.assert_called_once()
```

#### JavaScript Testing with Jest

```javascript
// Good: Comprehensive JavaScript tests
const { BlockchainEngine } = require('../src/blockchain');
const { ValidationError } = require('../src/exceptions');

describe('BlockchainEngine', () => {
  let blockchain;
  let sampleTransaction;

  beforeEach(() => {
    blockchain = new BlockchainEngine();
    sampleTransaction = {
      sender: 'alice',
      receiver: 'bob',
      amount: 100,
      signature: 'abc123'
    };
  });

  describe('createBlock', () => {
    it('should create a block successfully', () => {
      // Arrange
      const transactions = [sampleTransaction];
      const previousHash = 'def456';

      // Act
      const block = blockchain.createBlock(transactions, previousHash);

      // Assert
      expect(block.transactions).toEqual(transactions);
      expect(block.previousHash).toBe(previousHash);
      expect(block.hash).toBeDefined();
      expect(block.hash).toHaveLength(64); // SHA-256 hash length
    });

    it('should throw ValidationError for invalid transaction', () => {
      // Arrange
      const invalidTransaction = { invalid: 'data' };

      // Act & Assert
      expect(() => {
        blockchain.createBlock([invalidTransaction], 'def456');
      }).toThrow(ValidationError);
    });
  });
});
```

### Integration Testing

```python
# Good: Integration tests
import pytest
import requests
from .fixtures import test_app, test_client

class TestAPIIntegration:
    """Integration tests for API endpoints."""
    
    def test_transaction_endpoint_success(self, test_client):
        """Test successful transaction creation."""
        # Arrange
        transaction_data = {
            "sender": "alice",
            "receiver": "bob",
            "amount": 100,
            "signature": "abc123"
        }
        
        # Act
        response = test_client.post("/api/v1/transactions", json=transaction_data)
        
        # Assert
        assert response.status_code == 201
        assert "transaction_id" in response.json()
        assert response.json()["status"] == "pending"
    
    def test_transaction_endpoint_validation_error(self, test_client):
        """Test transaction validation error."""
        # Arrange
        invalid_transaction = {"invalid": "data"}
        
        # Act
        response = test_client.post("/api/v1/transactions", json=invalid_transaction)
        
        # Assert
        assert response.status_code == 400
        assert "error" in response.json()
```

---

## Code Review Standards

### Review Checklist

#### Code Quality

- [ ] **Functionality**: Code works as intended
- [ ] **Performance**: No obvious performance issues
- [ ] **Security**: No security vulnerabilities
- [ ] **Error Handling**: Proper error handling and logging
- [ ] **Documentation**: Code is well-documented

#### Code Style

- [ ] **Formatting**: Code follows style guidelines
- [ ] **Naming**: Variables and functions have clear names
- [ ] **Structure**: Code is well-organized and modular
- [ ] **Comments**: Complex logic is commented
- [ ] **Imports**: Imports are organized and necessary

#### Testing

- [ ] **Unit Tests**: Unit tests cover new functionality
- [ ] **Integration Tests**: Integration tests are updated
- [ ] **Test Coverage**: Adequate test coverage
- [ ] **Test Quality**: Tests are meaningful and maintainable

### Review Process

#### Pre-Review

```bash
# Run linting
flake8 . --max-line-length=120
black . --check
mypy . --ignore-missing-imports

# Run tests
pytest tests/ -v --cov=. --cov-report=html

# Run security checks
bandit -r . -f json -o security-report.json
safety check --json --output safety-report.json
```

#### Review Guidelines

1. **Be Constructive**: Provide helpful feedback
2. **Be Specific**: Point out specific issues
3. **Be Educational**: Explain why changes are needed
4. **Be Respectful**: Maintain professional tone
5. **Be Thorough**: Check all aspects of the code

---

## Performance Standards

### Python Performance

#### Efficient Data Structures

```python
# Good: Use appropriate data structures
from collections import defaultdict, deque
from typing import Dict, List

class TransactionPool:
    """Efficient transaction pool using deque for FIFO operations."""
    
    def __init__(self):
        self.transactions = deque()
        self.transaction_map: Dict[str, Transaction] = {}
    
    def add_transaction(self, transaction: Transaction) -> bool:
        """Add transaction to pool."""
        if transaction.id in self.transaction_map:
            return False
        
        self.transactions.append(transaction)
        self.transaction_map[transaction.id] = transaction
        return True
    
    def get_transactions(self, limit: int = 100) -> List[Transaction]:
        """Get transactions from pool."""
        return list(self.transactions)[:limit]
```

#### Memory Management

```python
# Good: Efficient memory usage
import gc
from typing import Generator

def process_large_dataset(data: List[dict]) -> Generator[dict, None, None]:
    """Process large dataset efficiently using generators."""
    for item in data:
        # Process item
        processed_item = process_item(item)
        yield processed_item
        
        # Force garbage collection for large datasets
        if len(data) > 10000:
            gc.collect()

# Good: Context managers for resource management
from contextlib import contextmanager

@contextmanager
def database_connection():
    """Context manager for database connections."""
    conn = None
    try:
        conn = create_connection()
        yield conn
    finally:
        if conn:
            conn.close()
```

### JavaScript Performance

#### Efficient Algorithms

```javascript
// Good: Efficient blockchain validation
class BlockchainValidator {
  validateChain(chain) {
    // Use Map for O(1) lookups
    const blockMap = new Map();
    const seenHashes = new Set();
    
    for (const block of chain) {
      // Check for duplicate hashes
      if (seenHashes.has(block.hash)) {
        return false;
      }
      seenHashes.add(block.hash);
      
      // Validate block
      if (!this.validateBlock(block)) {
        return false;
      }
      
      // Check previous hash
      if (block.previousHash && !blockMap.has(block.previousHash)) {
        return false;
      }
      
      blockMap.set(block.hash, block);
    }
    
    return true;
  }
}
```

---

## Security Standards

### Input Validation

```python
# Good: Comprehensive input validation
from typing import Any, Dict
import re

class InputValidator:
    """Validates user input for security."""
    
    @staticmethod
    def validate_transaction_data(data: Dict[str, Any]) -> bool:
        """Validate transaction data."""
        # Check required fields
        required_fields = ["sender", "receiver", "amount", "signature"]
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate sender/receiver format
        if not re.match(r'^[a-zA-Z0-9]{40}$', data["sender"]):
            raise ValidationError("Invalid sender format")
        
        if not re.match(r'^[a-zA-Z0-9]{40}$', data["receiver"]):
            raise ValidationError("Invalid receiver format")
        
        # Validate amount
        if not isinstance(data["amount"], (int, float)) or data["amount"] <= 0:
            raise ValidationError("Amount must be a positive number")
        
        # Validate signature
        if not re.match(r'^[a-fA-F0-9]{128}$', data["signature"]):
            raise ValidationError("Invalid signature format")
        
        return True
```

### Secure Coding Practices

```python
# Good: Secure password handling
import hashlib
import secrets
from typing import Tuple

class PasswordManager:
    """Secure password management."""
    
    @staticmethod
    def hash_password(password: str) -> Tuple[str, str]:
        """Hash password with salt."""
        salt = secrets.token_hex(32)
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        )
        return password_hash.hex(), salt
    
    @staticmethod
    def verify_password(password: str, password_hash: str, salt: str) -> bool:
        """Verify password against hash."""
        test_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return test_hash.hex() == password_hash
```

---

## Documentation Standards

### API Documentation

```python
# Good: OpenAPI documentation
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

class TransactionRequest(BaseModel):
    """Transaction creation request."""
    sender: str
    receiver: str
    amount: float
    signature: str
    
    class Config:
        schema_extra = {
            "example": {
                "sender": "alice1234567890123456789012345678901234567890",
                "receiver": "bob1234567890123456789012345678901234567890",
                "amount": 100.0,
                "signature": "abc123def456..."
            }
        }

class TransactionResponse(BaseModel):
    """Transaction creation response."""
    transaction_id: str
    status: str
    block_hash: Optional[str] = None

app = FastAPI(
    title="Lucid Blockchain API",
    description="API for Lucid blockchain system",
    version="1.0.0"
)

@app.post(
    "/api/v1/transactions",
    response_model=TransactionResponse,
    summary="Create Transaction",
    description="Create a new blockchain transaction"
)
async def create_transaction(
    transaction: TransactionRequest
) -> TransactionResponse:
    """Create a new blockchain transaction.
    
    This endpoint creates a new transaction and adds it to the mempool
    for processing by the blockchain network.
    
    Args:
        transaction: Transaction data including sender, receiver, amount, and signature
        
    Returns:
        TransactionResponse with transaction ID and status
        
    Raises:
        HTTPException: If transaction validation fails
    """
    try:
        # Validate transaction
        if not validate_transaction(transaction):
            raise HTTPException(status_code=400, detail="Invalid transaction")
        
        # Process transaction
        result = await blockchain_engine.process_transaction(transaction)
        
        return TransactionResponse(
            transaction_id=result.id,
            status=result.status,
            block_hash=result.block_hash
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

## References

- [Development Setup Guide](./development-setup-guide.md)
- [Deployment Guide](../deployment/deployment-guide.md)
- [Troubleshooting Guide](../deployment/troubleshooting-guide.md)
- [Master Build Plan](../../plan/API_plans/00-master-architecture/01-MASTER_BUILD_PLAN.md)

---

**Document Version**: 1.0.0  
**Status**: ACTIVE  
**Last Updated**: 2025-01-14
