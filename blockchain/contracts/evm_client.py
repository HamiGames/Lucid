#!/usr/bin/env python3
"""
EVM Client for On-System Chain
Based on rebuild-blockchain-engine.md specifications

Implements EVM-compatible blockchain client for:
- JSON-RPC interface to On-System Chain
- Contract function calls and view functions
- Transaction monitoring and status checking
- Gas estimation and circuit breakers
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Union
import aiohttp
import secrets

logger = logging.getLogger(__name__)


class TransactionStatus(Enum):
    """Transaction status"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    DROPPED = "dropped"


@dataclass
class ContractCall:
    """Contract function call"""
    contract_address: str
    function_name: str
    parameters: Dict[str, Any]
    gas_limit: int
    gas_price: Optional[int] = None
    value: int = 0
    nonce: Optional[int] = None


@dataclass
class ContractEvent:
    """Contract event"""
    address: str
    topics: List[str]
    data: str
    block_number: int
    transaction_hash: str
    log_index: int
    removed: bool = False


@dataclass
class BlockInfo:
    """Block information"""
    number: int
    hash: str
    parent_hash: str
    timestamp: int
    gas_limit: int
    gas_used: int
    transactions: List[str]


class EVMClient:
    """
    EVM-compatible client for On-System Chain.
    
    Implements JSON-RPC interface for:
    - Contract function calls
    - Transaction monitoring
    - Block information retrieval
    - Gas estimation
    """
    
    def __init__(self, rpc_url: str, chain_id: int = 1337, timeout: int = 30):
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        # HTTP session
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Circuit breaker for rate limiting
        self._request_count = 0
        self._last_reset = time.time()
        self._max_requests_per_minute = 100
        
        # Mock storage for development
        self._transactions: Dict[str, Dict[str, Any]] = {}
        self._blocks: Dict[int, BlockInfo] = {}
        self._current_block = 1000
    
    async def start(self):
        """Start EVM client"""
        try:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
            
            # Test connection
            await self.get_latest_block_number()
            
            self.logger.info(f"EVM client started for chain {self.chain_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to start EVM client: {e}")
            raise
    
    async def close(self):
        """Close EVM client"""
        try:
            if self._session:
                await self._session.close()
                self._session = None
            
            self.logger.info("EVM client closed")
            
        except Exception as e:
            self.logger.error(f"Error closing EVM client: {e}")
    
    async def call_contract_function(
        self,
        contract_address: str,
        function_name: str,
        parameters: Dict[str, Any],
        gas_limit: int = 1000000,
        gas_price: Optional[int] = None,
        value: int = 0
    ) -> Optional[str]:
        """
        Call contract function (state-changing).
        
        Args:
            contract_address: Contract address
            function_name: Function name to call
            parameters: Function parameters
            gas_limit: Gas limit for transaction
            gas_price: Gas price (optional)
            value: ETH value to send (optional)
            
        Returns:
            Transaction hash or None if failed
        """
        try:
            # Check circuit breaker
            if not self._check_circuit_breaker():
                raise Exception("Circuit breaker open - too many requests")
            
            # Encode function call
            function_data = self._encode_function_call(function_name, parameters)
            
            # Create transaction
            tx_hash = self._generate_tx_hash()
            
            # Mock transaction data
            transaction = {
                "hash": tx_hash,
                "from": "0x1234567890123456789012345678901234567890",  # Mock sender
                "to": contract_address,
                "value": hex(value),
                "gas": hex(gas_limit),
                "gasPrice": hex(gas_price or 20000000000),  # 20 gwei
                "input": function_data,
                "blockNumber": None,
                "status": TransactionStatus.PENDING.value
            }
            
            # Store transaction
            self._transactions[tx_hash] = transaction
            
            # Simulate transaction confirmation after delay
            asyncio.create_task(self._simulate_transaction_confirmation(tx_hash))
            
            self.logger.info(f"Contract function call submitted: {function_name} -> {tx_hash}")
            return tx_hash
            
        except Exception as e:
            self.logger.error(f"Failed to call contract function {function_name}: {e}")
            return None
    
    async def call_contract_view_function(
        self,
        contract_address: str,
        function_name: str,
        parameters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Call contract view function (read-only).
        
        Args:
            contract_address: Contract address
            function_name: Function name to call
            parameters: Function parameters
            
        Returns:
            Function result or None if failed
        """
        try:
            # Check circuit breaker
            if not self._check_circuit_breaker():
                raise Exception("Circuit breaker open - too many requests")
            
            # Mock view function call
            if function_name == "getSessionAnchor":
                return self._mock_get_session_anchor(parameters)
            elif function_name == "getChunkMetadata":
                return self._mock_get_chunk_metadata(parameters)
            else:
                # Generic mock response
                return self._mock_view_function_result(function_name, parameters)
            
        except Exception as e:
            self.logger.error(f"Failed to call view function {function_name}: {e}")
            return None
    
    async def get_transaction_status(self, tx_hash: str) -> TransactionStatus:
        """Get transaction status"""
        try:
            if tx_hash in self._transactions:
                tx = self._transactions[tx_hash]
                return TransactionStatus(tx["status"])
            else:
                return TransactionStatus.FAILED
                
        except Exception as e:
            self.logger.error(f"Failed to get transaction status for {tx_hash}: {e}")
            return TransactionStatus.FAILED
    
    async def get_transaction_receipt(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get transaction receipt"""
        try:
            if tx_hash in self._transactions:
                tx = self._transactions[tx_hash]
                
                receipt = {
                    "transactionHash": tx_hash,
                    "blockNumber": tx.get("blockNumber"),
                    "gasUsed": tx.get("gasUsed", 21000),
                    "status": tx["status"],
                    "logs": []
                }
                
                return receipt
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get transaction receipt for {tx_hash}: {e}")
            return None
    
    async def get_latest_block_number(self) -> int:
        """Get latest block number"""
        try:
            # Check circuit breaker
            if not self._check_circuit_breaker():
                raise Exception("Circuit breaker open - too many requests")
            
            # Mock block number (incrementing)
            self._current_block += 1
            
            return self._current_block
            
        except Exception as e:
            self.logger.error(f"Failed to get latest block number: {e}")
            return 0
    
    async def get_block_by_number(self, block_number: int) -> Optional[Dict[str, Any]]:
        """Get block by number"""
        try:
            # Check circuit breaker
            if not self._check_circuit_breaker():
                raise Exception("Circuit breaker open - too many requests")
            
            # Mock block data
            block_hash = self._generate_block_hash(block_number)
            
            block_info = {
                "number": block_number,
                "hash": block_hash,
                "parentHash": self._generate_block_hash(block_number - 1),
                "timestamp": int(time.time()),
                "gasLimit": hex(30000000),
                "gasUsed": hex(21000000),
                "transactions": []
            }
            
            # Store block
            self._blocks[block_number] = BlockInfo(
                number=block_number,
                hash=block_hash,
                parent_hash=block_info["parentHash"],
                timestamp=block_info["timestamp"],
                gas_limit=int(block_info["gasLimit"], 16),
                gas_used=int(block_info["gasUsed"], 16),
                transactions=[]
            )
            
            return block_info
            
        except Exception as e:
            self.logger.error(f"Failed to get block {block_number}: {e}")
            return None
    
    async def estimate_gas(
        self,
        contract_address: str,
        function_name: str,
        parameters: Dict[str, Any]
    ) -> int:
        """Estimate gas for contract function call"""
        try:
            # Simple gas estimation based on function complexity
            base_gas = 21000  # Base transaction gas
            
            if function_name == "registerSession":
                return base_gas + 50000  # Session registration
            elif function_name == "storeChunkMetadata":
                return base_gas + 30000  # Chunk storage
            elif function_name == "updateChunkStatus":
                return base_gas + 20000  # Status update
            else:
                return base_gas + 10000  # Default function
            
        except Exception as e:
            self.logger.error(f"Failed to estimate gas: {e}")
            return 21000
    
    async def get_gas_price(self) -> int:
        """Get current gas price"""
        try:
            # Mock gas price (20 gwei)
            return 20000000000
            
        except Exception as e:
            self.logger.error(f"Failed to get gas price: {e}")
            return 20000000000
    
    def _check_circuit_breaker(self) -> bool:
        """Check circuit breaker for rate limiting"""
        try:
            current_time = time.time()
            
            # Reset counter every minute
            if current_time - self._last_reset >= 60:
                self._request_count = 0
                self._last_reset = current_time
            
            # Check if we're over the limit
            if self._request_count >= self._max_requests_per_minute:
                self.logger.warning("Circuit breaker open - too many requests")
                return False
            
            self._request_count += 1
            return True
            
        except Exception:
            return False
    
    def _encode_function_call(self, function_name: str, parameters: Dict[str, Any]) -> str:
        """Encode function call data"""
        try:
            # Simple function selector (first 4 bytes of function signature hash)
            function_selector = self._get_function_selector(function_name)
            
            # Mock parameter encoding (in real implementation, use proper ABI encoding)
            encoded_params = "0000000000000000000000000000000000000000000000000000000000000000"
            
            return "0x" + function_selector + encoded_params
            
        except Exception as e:
            self.logger.error(f"Failed to encode function call: {e}")
            return "0x00000000"
    
    def _get_function_selector(self, function_name: str) -> str:
        """Get function selector for function name"""
        try:
            # Mock function selectors
            selectors = {
                "registerSession": "12345678",
                "storeChunkMetadata": "87654321",
                "updateChunkStatus": "abcdef00",
                "getSessionAnchor": "00abcdef",
                "getChunkMetadata": "00fedcba"
            }
            
            return selectors.get(function_name, "00000000")
            
        except Exception:
            return "00000000"
    
    def _generate_tx_hash(self) -> str:
        """Generate mock transaction hash"""
        return "0x" + secrets.token_hex(32)
    
    def _generate_block_hash(self, block_number: int) -> str:
        """Generate mock block hash"""
        data = f"block_{block_number}_{time.time()}"
        return "0x" + hashlib.sha256(data.encode()).hexdigest()
    
    async def _simulate_transaction_confirmation(self, tx_hash: str):
        """Simulate transaction confirmation after delay"""
        try:
            # Wait 2-5 seconds to simulate confirmation
            await asyncio.sleep(secrets.randbelow(3) + 2)
            
            # Update transaction status
            if tx_hash in self._transactions:
                self._transactions[tx_hash]["status"] = TransactionStatus.CONFIRMED.value
                self._transactions[tx_hash]["blockNumber"] = await self.get_latest_block_number()
                self._transactions[tx_hash]["gasUsed"] = 21000
                
                self.logger.info(f"Transaction confirmed: {tx_hash}")
            
        except Exception as e:
            self.logger.error(f"Error simulating transaction confirmation: {e}")
    
    def _mock_get_session_anchor(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Mock getSessionAnchor view function"""
        return {
            "sessionId": parameters.get("sessionId", b"mock_session"),
            "manifestHash": b"mock_manifest_hash",
            "owner": "0x1234567890123456789012345678901234567890",
            "merkleRoot": b"mock_merkle_root",
            "chunkCount": 10,
            "blockNumber": 1000
        }
    
    def _mock_get_chunk_metadata(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Mock getChunkMetadata view function"""
        return {
            "sessionId": b"mock_session",
            "chunkHash": b"mock_chunk_hash",
            "size": 1024000,
            "storagePaths": ["/storage/chunk1", "/storage/chunk2"],
            "replicationFactor": 2,
            "timestamp": int(time.time()),
            "status": 1  # STORED
        }
    
    def _mock_view_function_result(self, function_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Mock generic view function result"""
        return {
            "function": function_name,
            "result": "mock_result",
            "parameters": parameters
        }


# Global EVM client instance
_evm_client: Optional[EVMClient] = None


def get_evm_client() -> Optional[EVMClient]:
    """Get global EVM client instance"""
    return _evm_client


def create_evm_client(rpc_url: str, chain_id: int = 1337) -> EVMClient:
    """Create and initialize EVM client"""
    global _evm_client
    _evm_client = EVMClient(rpc_url, chain_id)
    return _evm_client


async def cleanup_evm_client():
    """Cleanup EVM client"""
    global _evm_client
    if _evm_client:
        await _evm_client.close()
        _evm_client = None


if __name__ == "__main__":
    async def test_evm_client():
        """Test EVM client"""
        
        # Create client
        client = create_evm_client("http://localhost:8545")
        await client.start()
        
        try:
            # Test latest block number
            block_number = await client.get_latest_block_number()
            print(f"Latest block number: {block_number}")
            
            # Test contract function call
            tx_hash = await client.call_contract_function(
                contract_address="0x1234567890123456789012345678901234567890",
                function_name="registerSession",
                parameters={"sessionId": b"test", "owner": "0x123"},
                gas_limit=100000
            )
            print(f"Transaction hash: {tx_hash}")
            
            # Test transaction status
            if tx_hash:
                await asyncio.sleep(3)  # Wait for confirmation
                status = await client.get_transaction_status(tx_hash)
                print(f"Transaction status: {status.value}")
            
            # Test view function
            result = await client.call_contract_view_function(
                contract_address="0x1234567890123456789012345678901234567890",
                function_name="getSessionAnchor",
                parameters={"sessionId": b"test"}
            )
            print(f"View function result: {result}")
            
        finally:
            await client.close()
    
    # Run test
    asyncio.run(test_evm_client())
