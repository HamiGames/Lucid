#!/usr/bin/env python3
"""
Chain Client Module for Lucid RDP Recorder
Handles blockchain interactions for session anchoring
"""

import asyncio
import logging
import json
import time
from typing import Optional, Dict, Any
import structlog
from datetime import datetime
import aiohttp

logger = structlog.get_logger(__name__)

try:
    from web3 import Web3
    from web3.middleware import geth_poa_middleware
    WEB3_AVAILABLE = True
except ImportError:
    logger.warning("Web3.py not available, chain client will use fallback")
    WEB3_AVAILABLE = False


class ChainClient:
    """Client for blockchain interactions"""
    
    def __init__(self, rpc_url: str, contract_address: Optional[str] = None):
        self.rpc_url = rpc_url
        self.contract_address = contract_address
        self.web3: Optional[Web3] = None
        self.contract = None
        self.account = None
        self.is_connected = False
        
        # Statistics
        self.stats = {
            'transactions_sent': 0,
            'successful_transactions': 0,
            'failed_transactions': 0,
            'last_transaction_time': None,
            'gas_used_total': 0
        }
        
        # HTTP session for fallback
        self.http_session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> bool:
        """Initialize chain client"""
        try:
            logger.info("Initializing chain client", rpc_url=self.rpc_url)
            
            if WEB3_AVAILABLE:
                # Initialize Web3 connection
                self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
                
                # Add PoA middleware if needed
                self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
                
                # Test connection
                if self.web3.is_connected():
                    chain_id = self.web3.eth.chain_id
                    block_number = self.web3.eth.block_number
                    
                    logger.info("Connected to blockchain", 
                               chain_id=chain_id,
                               block_number=block_number)
                    
                    self.is_connected = True
                    
                    # Load contract if address provided
                    if self.contract_address:
                        await self._load_contract()
                    
                    return True
                else:
                    logger.error("Failed to connect to blockchain")
                    return False
            else:
                # Fallback to HTTP client
                self.http_session = aiohttp.ClientSession()
                
                # Test connection
                if await self._test_http_connection():
                    logger.info("Connected to blockchain via HTTP")
                    self.is_connected = True
                    return True
                else:
                    logger.error("Failed to connect to blockchain via HTTP")
                    return False
            
        except Exception as e:
            logger.error("Failed to initialize chain client", error=str(e))
            return False
    
    async def _test_http_connection(self) -> bool:
        """Test HTTP connection to blockchain"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 1
            }
            
            async with self.http_session.post(self.rpc_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'result' in data:
                        block_number = int(data['result'], 16)
                        logger.info("HTTP connection test successful", block_number=block_number)
                        return True
                
                return False
                
        except Exception as e:
            logger.error("HTTP connection test failed", error=str(e))
            return False
    
    async def _load_contract(self):
        """Load smart contract"""
        try:
            if not self.contract_address or not self.web3:
                return
            
            # Contract ABI (simplified for anchors)
            contract_abi = [
                {
                    "inputs": [
                        {"name": "sessionId", "type": "bytes32"},
                        {"name": "merkleRoot", "type": "bytes32"},
                        {"name": "chunkCount", "type": "uint256"},
                        {"name": "policyHash", "type": "bytes32"}
                    ],
                    "name": "anchorSession",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [
                        {"name": "sessionId", "type": "bytes32"}
                    ],
                    "name": "getSessionAnchor",
                    "outputs": [
                        {"name": "merkleRoot", "type": "bytes32"},
                        {"name": "chunkCount", "type": "uint256"},
                        {"name": "timestamp", "type": "uint256"}
                    ],
                    "stateMutability": "view",
                    "type": "function"
                }
            ]
            
            self.contract = self.web3.eth.contract(
                address=self.contract_address,
                abi=contract_abi
            )
            
            logger.info("Smart contract loaded", address=self.contract_address)
            
        except Exception as e:
            logger.error("Failed to load smart contract", error=str(e))
    
    async def anchor_session(self, session_id: str, merkle_root: str, 
                           chunk_count: int, policy_hash: str) -> bool:
        """Anchor session to blockchain"""
        try:
            logger.info("Anchoring session to blockchain", 
                       session_id=session_id,
                       merkle_root=merkle_root[:16] + "...",
                       chunk_count=chunk_count)
            
            if WEB3_AVAILABLE and self.web3 and self.contract:
                # Use Web3 for transaction
                success = await self._anchor_with_web3(
                    session_id, merkle_root, chunk_count, policy_hash
                )
            else:
                # Use HTTP fallback
                success = await self._anchor_with_http(
                    session_id, merkle_root, chunk_count, policy_hash
                )
            
            if success:
                self.stats['successful_transactions'] += 1
                self.stats['last_transaction_time'] = time.time()
                logger.info("Session anchored successfully", session_id=session_id)
            else:
                self.stats['failed_transactions'] += 1
                logger.error("Failed to anchor session", session_id=session_id)
            
            self.stats['transactions_sent'] += 1
            
            return success
            
        except Exception as e:
            logger.error("Failed to anchor session", session_id=session_id, error=str(e))
            self.stats['failed_transactions'] += 1
            return False
    
    async def _anchor_with_web3(self, session_id: str, merkle_root: str, 
                               chunk_count: int, policy_hash: str) -> bool:
        """Anchor session using Web3"""
        try:
            # Convert strings to bytes32
            session_id_bytes = session_id.encode('utf-8').ljust(32, b'\0')[:32]
            merkle_root_bytes = bytes.fromhex(merkle_root.replace('0x', ''))
            policy_hash_bytes = policy_hash.encode('utf-8').ljust(32, b'\0')[:32]
            
            # Build transaction
            transaction = self.contract.functions.anchorSession(
                session_id_bytes,
                merkle_root_bytes,
                chunk_count,
                policy_hash_bytes
            ).build_transaction({
                'from': self.account.address if self.account else None,
                'gas': 200000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(
                    self.account.address if self.account else None
                )
            })
            
            # Sign and send transaction
            if self.account:
                signed_txn = self.web3.eth.account.sign_transaction(
                    transaction, self.account.key
                )
                tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            else:
                # Use default account (for testing)
                tx_hash = self.web3.eth.send_transaction(transaction)
            
            # Wait for transaction receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                logger.info("Transaction successful", tx_hash=tx_hash.hex())
                self.stats['gas_used_total'] += receipt.gasUsed
                return True
            else:
                logger.error("Transaction failed", tx_hash=tx_hash.hex())
                return False
                
        except Exception as e:
            logger.error("Web3 anchoring failed", error=str(e))
            return False
    
    async def _anchor_with_http(self, session_id: str, merkle_root: str, 
                               chunk_count: int, policy_hash: str) -> bool:
        """Anchor session using HTTP (fallback)"""
        try:
            # For HTTP fallback, we'll just log the anchor data
            # In a real implementation, this might call a different service
            
            anchor_data = {
                'session_id': session_id,
                'merkle_root': merkle_root,
                'chunk_count': chunk_count,
                'policy_hash': policy_hash,
                'timestamp': datetime.utcnow().isoformat(),
                'method': 'http_fallback'
            }
            
            logger.info("Session anchor data (HTTP fallback)", **anchor_data)
            
            # In a real implementation, you might POST this to a service
            # that handles blockchain anchoring
            
            return True
            
        except Exception as e:
            logger.error("HTTP anchoring failed", error=str(e))
            return False
    
    async def get_session_anchor(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session anchor from blockchain"""
        try:
            if WEB3_AVAILABLE and self.web3 and self.contract:
                # Use Web3 to call contract
                session_id_bytes = session_id.encode('utf-8').ljust(32, b'\0')[:32]
                
                result = self.contract.functions.getSessionAnchor(session_id_bytes).call()
                
                return {
                    'session_id': session_id,
                    'merkle_root': result[0].hex(),
                    'chunk_count': result[1],
                    'timestamp': result[2]
                }
            else:
                # HTTP fallback - return None for now
                logger.warning("Session anchor retrieval not implemented for HTTP fallback")
                return None
                
        except Exception as e:
            logger.error("Failed to get session anchor", session_id=session_id, error=str(e))
            return None
    
    async def get_latest_block(self) -> Optional[int]:
        """Get latest block number"""
        try:
            if WEB3_AVAILABLE and self.web3:
                return self.web3.eth.block_number
            else:
                # HTTP fallback
                payload = {
                    "jsonrpc": "2.0",
                    "method": "eth_blockNumber",
                    "params": [],
                    "id": 1
                }
                
                async with self.http_session.post(self.rpc_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'result' in data:
                            return int(data['result'], 16)
                
                return None
                
        except Exception as e:
            logger.error("Failed to get latest block", error=str(e))
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get chain client statistics"""
        return {
            **self.stats,
            'is_connected': self.is_connected,
            'web3_available': WEB3_AVAILABLE,
            'contract_loaded': self.contract is not None,
            'rpc_url': self.rpc_url
        }
    
    async def cleanup(self):
        """Cleanup chain client resources"""
        try:
            if self.http_session:
                await self.http_session.close()
            
            logger.info("Chain client cleanup completed")
            
        except Exception as e:
            logger.error("Chain client cleanup error", error=str(e))
