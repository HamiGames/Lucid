#!/usr/bin/env python3
"""
LucidAnchors Smart Contract Interface
Based on rebuild-blockchain-engine.md specifications

Implements On-System Chain session manifest anchoring:
- registerSession(sessionId, manifestHash, startedAt, owner, merkleRoot, chunkCount)
- Gas-efficient event-based anchoring
- Session verification and proof generation
"""

import asyncio
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class AnchorStatus(Enum):
    """Anchor transaction status"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class SessionManifest:
    """Session manifest for anchoring"""
    session_id: str
    owner_address: str
    manifest_hash: str
    merkle_root: str
    chunk_count: int
    total_size: int
    start_time: datetime
    end_time: datetime
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for contract call"""
        return {
            "sessionId": self.session_id,
            "ownerAddress": self.owner_address,
            "manifestHash": self.manifest_hash,
            "merkleRoot": self.merkle_root,
            "chunkCount": self.chunk_count,
            "totalSize": self.total_size,
            "startTime": int(self.start_time.timestamp()),
            "endTime": int(self.end_time.timestamp()),
            "metadata": self.metadata
        }
    
    def calculate_hash(self) -> str:
        """Calculate manifest hash for verification"""
        manifest_data = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(manifest_data.encode()).hexdigest()


@dataclass
class AnchorTransaction:
    """Anchor transaction record"""
    tx_id: str
    session_id: str
    manifest_hash: str
    block_number: Optional[int]
    transaction_hash: Optional[str]
    status: AnchorStatus
    gas_used: Optional[int]
    gas_price: Optional[int]
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class AnchorProof:
    """Proof of anchoring"""
    anchor_id: str
    session_id: str
    merkle_root: str
    block_number: int
    transaction_hash: str
    block_hash: str
    block_timestamp: int
    proof_data: bytes
    validator_signature: Optional[bytes] = None


class LucidAnchorsInterface(ABC):
    """Abstract interface for LucidAnchors contract"""
    
    @abstractmethod
    async def register_session(self, manifest: SessionManifest, gas_limit: int = 1000000) -> str:
        """
        Register session manifest on blockchain.
        
        Args:
            manifest: Session manifest to register
            gas_limit: Maximum gas to use
            
        Returns:
            Transaction hash
        """
        pass
    
    @abstractmethod
    async def get_session_anchor(self, session_id: str) -> Optional[AnchorTransaction]:
        """
        Get session anchor transaction.
        
        Args:
            session_id: Session ID to query
            
        Returns:
            AnchorTransaction or None
        """
        pass
    
    @abstractmethod
    async def verify_anchor_proof(self, proof: AnchorProof) -> bool:
        """
        Verify anchor proof.
        
        Args:
            proof: Anchor proof to verify
            
        Returns:
            True if valid, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_anchor_status(self, tx_hash: str) -> AnchorStatus:
        """
        Get anchor transaction status.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Anchor status
        """
        pass


class LucidAnchorsContract(LucidAnchorsInterface):
    """
    LucidAnchors smart contract implementation.
    
    Implements On-System Chain session anchoring with:
    - registerSession function call
    - Event-based anchoring for gas efficiency
    - Session verification and proof generation
    """
    
    # Contract ABI for LucidAnchors
    CONTRACT_ABI = [
        {
            "inputs": [
                {"name": "sessionId", "type": "bytes32"},
                {"name": "manifestHash", "type": "bytes32"},
                {"name": "startedAt", "type": "uint256"},
                {"name": "owner", "type": "address"},
                {"name": "merkleRoot", "type": "bytes32"},
                {"name": "chunkCount", "type": "uint256"}
            ],
            "name": "registerSession",
            "outputs": [{"name": "", "type": "bool"}],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "anonymous": False,
            "inputs": [
                {"indexed": True, "name": "sessionId", "type": "bytes32"},
                {"indexed": True, "name": "owner", "type": "address"},
                {"indexed": False, "name": "manifestHash", "type": "bytes32"},
                {"indexed": False, "name": "merkleRoot", "type": "bytes32"},
                {"indexed": False, "name": "chunkCount", "type": "uint256"},
                {"indexed": False, "name": "blockNumber", "type": "uint256"}
            ],
            "name": "SessionAnchored",
            "type": "event"
        },
        {
            "inputs": [
                {"name": "sessionId", "type": "bytes32"}
            ],
            "name": "getSessionAnchor",
            "outputs": [
                {"name": "manifestHash", "type": "bytes32"},
                {"name": "owner", "type": "address"},
                {"name": "merkleRoot", "type": "bytes32"},
                {"name": "chunkCount", "type": "uint256"},
                {"name": "blockNumber", "type": "uint256"}
            ],
            "stateMutability": "view",
            "type": "function"
        }
    ]
    
    def __init__(self, contract_address: str, evm_client: 'EVMClient'):
        self.contract_address = contract_address
        self.evm_client = evm_client
        self.logger = logging.getLogger(__name__)
        
        # Mock storage for development
        self._session_anchors: Dict[str, AnchorTransaction] = {}
        self._anchor_proofs: Dict[str, AnchorProof] = {}
    
    async def register_session(self, manifest: SessionManifest, gas_limit: int = 1000000) -> str:
        """
        Register session manifest on blockchain.
        
        Per Spec-1b: registerSession(sessionId, manifestHash, startedAt, owner, merkleRoot, chunkCount)
        """
        try:
            # Prepare function call parameters
            session_id_bytes = bytes.fromhex(manifest.session_id.replace("-", ""))
            manifest_hash_bytes = bytes.fromhex(manifest.manifest_hash.replace("0x", ""))
            merkle_root_bytes = bytes.fromhex(manifest.merkle_root.replace("0x", ""))
            
            params = {
                "sessionId": session_id_bytes,
                "manifestHash": manifest_hash_bytes,
                "startedAt": int(manifest.start_time.timestamp()),
                "owner": manifest.owner_address,
                "merkleRoot": merkle_root_bytes,
                "chunkCount": manifest.chunk_count
            }
            
            # Submit transaction
            tx_hash = await self.evm_client.call_contract_function(
                contract_address=self.contract_address,
                function_name="registerSession",
                parameters=params,
                gas_limit=gas_limit
            )
            
            if not tx_hash:
                raise Exception("Failed to submit registerSession transaction")
            
            # Create anchor transaction record
            anchor_tx = AnchorTransaction(
                tx_id=f"anchor_{manifest.session_id}",
                session_id=manifest.session_id,
                manifest_hash=manifest.manifest_hash,
                block_number=None,
                transaction_hash=tx_hash,
                status=AnchorStatus.PENDING,
                gas_used=None,
                gas_price=None,
                created_at=datetime.now(timezone.utc)
            )
            
            # Store in mock storage
            self._session_anchors[manifest.session_id] = anchor_tx
            
            self.logger.info(f"Session {manifest.session_id} registered with tx {tx_hash}")
            return tx_hash
            
        except Exception as e:
            self.logger.error(f"Failed to register session {manifest.session_id}: {e}")
            raise
    
    async def get_session_anchor(self, session_id: str) -> Optional[AnchorTransaction]:
        """Get session anchor transaction"""
        try:
            # Check mock storage first
            if session_id in self._session_anchors:
                return self._session_anchors[session_id]
            
            # Query blockchain
            session_id_bytes = bytes.fromhex(session_id.replace("-", ""))
            
            result = await self.evm_client.call_contract_view_function(
                contract_address=self.contract_address,
                function_name="getSessionAnchor",
                parameters={"sessionId": session_id_bytes}
            )
            
            if result:
                # Parse result and create AnchorTransaction
                anchor_tx = AnchorTransaction(
                    tx_id=f"anchor_{session_id}",
                    session_id=session_id,
                    manifest_hash=result["manifestHash"].hex(),
                    block_number=result["blockNumber"],
                    transaction_hash=None,
                    status=AnchorStatus.CONFIRMED,
                    gas_used=None,
                    gas_price=None,
                    created_at=datetime.now(timezone.utc),
                    confirmed_at=datetime.now(timezone.utc)
                )
                
                return anchor_tx
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get session anchor for {session_id}: {e}")
            return None
    
    async def verify_anchor_proof(self, proof: AnchorProof) -> bool:
        """Verify anchor proof"""
        try:
            # Get session anchor from blockchain
            anchor_tx = await self.get_session_anchor(proof.session_id)
            
            if not anchor_tx:
                self.logger.warning(f"No anchor found for session {proof.session_id}")
                return False
            
            # Verify block number matches
            if anchor_tx.block_number != proof.block_number:
                self.logger.warning(f"Block number mismatch: expected {anchor_tx.block_number}, got {proof.block_number}")
                return False
            
            # Verify transaction hash matches
            if anchor_tx.transaction_hash != proof.transaction_hash:
                self.logger.warning(f"Transaction hash mismatch")
                return False
            
            # Verify merkle root matches
            if anchor_tx.manifest_hash != proof.merkle_root:
                self.logger.warning(f"Merkle root mismatch")
                return False
            
            # Verify proof data integrity
            if not self._verify_proof_data_integrity(proof):
                self.logger.warning(f"Proof data integrity check failed")
                return False
            
            self.logger.info(f"Anchor proof verified for session {proof.session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to verify anchor proof: {e}")
            return False
    
    def _verify_proof_data_integrity(self, proof: AnchorProof) -> bool:
        """Verify proof data integrity"""
        try:
            # Check proof data is not empty
            if not proof.proof_data or len(proof.proof_data) == 0:
                return False
            
            # Verify block hash format
            if not proof.block_hash or len(proof.block_hash) != 66:  # 0x + 64 hex chars
                return False
            
            # Verify block timestamp is reasonable
            current_time = datetime.now(timezone.utc).timestamp()
            if proof.block_timestamp > current_time or proof.block_timestamp < 0:
                return False
            
            return True
            
        except Exception:
            return False
    
    async def get_anchor_status(self, tx_hash: str) -> AnchorStatus:
        """Get anchor transaction status"""
        try:
            # Query transaction status from EVM client
            tx_status = await self.evm_client.get_transaction_status(tx_hash)
            
            if tx_status == "confirmed":
                return AnchorStatus.CONFIRMED
            elif tx_status == "failed":
                return AnchorStatus.FAILED
            else:
                return AnchorStatus.PENDING
                
        except Exception as e:
            self.logger.error(f"Failed to get anchor status for {tx_hash}: {e}")
            return AnchorStatus.FAILED
    
    async def generate_anchor_proof(self, session_id: str) -> Optional[AnchorProof]:
        """Generate anchor proof for session"""
        try:
            # Get session anchor
            anchor_tx = await self.get_session_anchor(session_id)
            
            if not anchor_tx or anchor_tx.status != AnchorStatus.CONFIRMED:
                self.logger.warning(f"Cannot generate proof for session {session_id}: anchor not confirmed")
                return None
            
            # Get block information
            block_info = await self.evm_client.get_block_by_number(anchor_tx.block_number)
            
            if not block_info:
                self.logger.error(f"Failed to get block {anchor_tx.block_number}")
                return None
            
            # Generate proof data
            proof_data = self._generate_proof_data(anchor_tx, block_info)
            
            # Create anchor proof
            proof = AnchorProof(
                anchor_id=f"proof_{session_id}",
                session_id=session_id,
                merkle_root=anchor_tx.manifest_hash,
                block_number=anchor_tx.block_number,
                transaction_hash=anchor_tx.transaction_hash,
                block_hash=block_info["hash"],
                block_timestamp=block_info["timestamp"],
                proof_data=proof_data
            )
            
            # Store proof
            self._anchor_proofs[session_id] = proof
            
            self.logger.info(f"Anchor proof generated for session {session_id}")
            return proof
            
        except Exception as e:
            self.logger.error(f"Failed to generate anchor proof for {session_id}: {e}")
            return None
    
    def _generate_proof_data(self, anchor_tx: AnchorTransaction, block_info: Dict[str, Any]) -> bytes:
        """Generate proof data for anchor transaction"""
        try:
            # Combine anchor and block data
            proof_data = {
                "sessionId": anchor_tx.session_id,
                "manifestHash": anchor_tx.manifest_hash,
                "blockNumber": anchor_tx.block_number,
                "transactionHash": anchor_tx.transaction_hash,
                "blockHash": block_info["hash"],
                "blockTimestamp": block_info["timestamp"]
            }
            
            # Serialize and hash
            proof_json = json.dumps(proof_data, sort_keys=True)
            proof_hash = hashlib.sha256(proof_json.encode()).digest()
            
            return proof_hash
            
        except Exception as e:
            self.logger.error(f"Failed to generate proof data: {e}")
            return b""
    
    async def list_session_anchors(self, owner_address: Optional[str] = None, limit: int = 100) -> List[AnchorTransaction]:
        """List session anchors with optional filtering"""
        try:
            anchors = []
            
            # Get from mock storage
            for anchor_tx in self._session_anchors.values():
                if owner_address is None or anchor_tx.session_id.startswith(owner_address):
                    anchors.append(anchor_tx)
            
            # Sort by creation time
            anchors.sort(key=lambda x: x.created_at, reverse=True)
            
            return anchors[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to list session anchors: {e}")
            return []
    
    async def get_contract_stats(self) -> Dict[str, Any]:
        """Get contract statistics"""
        try:
            total_anchors = len(self._session_anchors)
            confirmed_anchors = len([a for a in self._session_anchors.values() if a.status == AnchorStatus.CONFIRMED])
            pending_anchors = len([a for a in self._session_anchors.values() if a.status == AnchorStatus.PENDING])
            failed_anchors = len([a for a in self._session_anchors.values() if a.status == AnchorStatus.FAILED])
            
            return {
                "contract_address": self.contract_address,
                "total_anchors": total_anchors,
                "confirmed_anchors": confirmed_anchors,
                "pending_anchors": pending_anchors,
                "failed_anchors": failed_anchors,
                "total_proofs": len(self._anchor_proofs)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get contract stats: {e}")
            return {}


# Global contract instance
_anchors_contract: Optional[LucidAnchorsContract] = None


def get_anchors_contract() -> Optional[LucidAnchorsContract]:
    """Get global LucidAnchors contract instance"""
    return _anchors_contract


def create_anchors_contract(contract_address: str, evm_client: 'EVMClient') -> LucidAnchorsContract:
    """Create and initialize LucidAnchors contract"""
    global _anchors_contract
    _anchors_contract = LucidAnchorsContract(contract_address, evm_client)
    return _anchors_contract


async def cleanup_anchors_contract():
    """Cleanup anchors contract"""
    global _anchors_contract
    _anchors_contract = None


if __name__ == "__main__":
    async def test_anchors_contract():
        """Test LucidAnchors contract"""
        from .evm_client import EVMClient
        
        # Mock EVM client for testing
        evm_client = EVMClient("http://localhost:8545")
        
        # Create contract
        contract = create_anchors_contract("0x1234567890123456789012345678901234567890", evm_client)
        
        try:
            # Test session manifest
            manifest = SessionManifest(
                session_id="test-session-001",
                owner_address="0xabcdef1234567890123456789012345678901234",
                manifest_hash="0x" + "a" * 64,
                merkle_root="0x" + "b" * 64,
                chunk_count=10,
                total_size=1024000,
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                metadata={"test": "data"}
            )
            
            # Test registration
            tx_hash = await contract.register_session(manifest)
            print(f"Session registered with tx: {tx_hash}")
            
            # Test getting anchor
            anchor = await contract.get_session_anchor(manifest.session_id)
            if anchor:
                print(f"Anchor found: {anchor.status.value}")
            else:
                print("No anchor found")
            
            # Test contract stats
            stats = await contract.get_contract_stats()
            print(f"Contract stats: {stats}")
            
        finally:
            await evm_client.close()
    
    # Run test
    asyncio.run(test_anchors_contract())
