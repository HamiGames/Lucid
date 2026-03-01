"""
LUCID TRON Relay - Verification Service
Provides transaction verification and validation services

SECURITY: READ-ONLY verification - does not sign or broadcast
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from config import config
from .relay_service import relay_service
from .cache_manager import cache_manager

logger = logging.getLogger(__name__)


class VerificationStatus(str, Enum):
    """Verification result status"""
    VERIFIED = "verified"
    PENDING = "pending"
    NOT_FOUND = "not_found"
    INSUFFICIENT_CONFIRMATIONS = "insufficient_confirmations"
    FAILED = "failed"
    ERROR = "error"


@dataclass
class VerificationResult:
    """Result of a verification operation"""
    txid: str
    status: VerificationStatus
    confirmations: int
    block_number: Optional[int]
    timestamp: Optional[int]
    from_address: Optional[str]
    to_address: Optional[str]
    amount: Optional[int]
    fee: Optional[int]
    contract_result: Optional[str]
    message: str
    verified_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "txid": self.txid,
            "status": self.status.value,
            "confirmations": self.confirmations,
            "block_number": self.block_number,
            "timestamp": self.timestamp,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "amount": self.amount,
            "fee": self.fee,
            "contract_result": self.contract_result,
            "message": self.message,
            "verified_at": self.verified_at
        }


class VerificationService:
    """
    Verification Service for TRON Relay
    
    Provides:
    - Transaction existence verification
    - Confirmation count checking
    - Receipt validation
    - TRC20 transfer verification
    
    Does NOT:
    - Create transactions
    - Sign anything
    - Modify blockchain state
    """
    
    def __init__(self):
        self.initialized = False
        self._stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "pending": 0
        }
    
    async def initialize(self):
        """Initialize the verification service"""
        logger.info("Initializing verification service")
        logger.info(f"Confirmation threshold: {config.confirmation_threshold}")
        self.initialized = True
        logger.info("✅ Verification service initialized")
    
    async def shutdown(self):
        """Shutdown the verification service"""
        self.initialized = False
    
    async def verify_transaction(self, txid: str) -> VerificationResult:
        """
        Verify a transaction exists and is confirmed
        
        Args:
            txid: Transaction ID to verify
            
        Returns:
            VerificationResult with status and details
        """
        self._stats["total"] += 1
        
        try:
            # Check cache first
            cached = await cache_manager.get_transaction_info(txid)
            if cached:
                logger.debug(f"Transaction {txid[:16]}... found in cache")
            
            # Get transaction info from network
            tx_info = cached or await relay_service.get_transaction_info(txid)
            
            if not tx_info:
                self._stats["failed"] += 1
                return VerificationResult(
                    txid=txid,
                    status=VerificationStatus.NOT_FOUND,
                    confirmations=0,
                    block_number=None,
                    timestamp=None,
                    from_address=None,
                    to_address=None,
                    amount=None,
                    fee=None,
                    contract_result=None,
                    message="Transaction not found on TRON network",
                    verified_at=datetime.utcnow().isoformat()
                )
            
            # Cache the result
            if not cached:
                await cache_manager.set_transaction_info(txid, tx_info)
            
            # Get confirmation count
            confirmations = await relay_service.get_transaction_confirmations(txid)
            
            # Extract details
            block_number = tx_info.get("blockNumber")
            timestamp = tx_info.get("blockTimeStamp")
            fee = tx_info.get("fee", 0)
            contract_result = tx_info.get("contractResult", [])
            result = tx_info.get("result", "")
            
            # Check confirmation threshold
            if confirmations >= config.confirmation_threshold:
                self._stats["successful"] += 1
                status = VerificationStatus.VERIFIED
                message = f"Transaction verified with {confirmations} confirmations"
            else:
                self._stats["pending"] += 1
                status = VerificationStatus.INSUFFICIENT_CONFIRMATIONS
                message = f"Transaction has {confirmations}/{config.confirmation_threshold} confirmations"
            
            # Try to get transaction details
            tx_data = await relay_service.get_transaction_by_id(txid)
            from_address = None
            to_address = None
            amount = None
            
            if tx_data and "raw_data" in tx_data:
                raw_data = tx_data["raw_data"]
                contracts = raw_data.get("contract", [])
                if contracts:
                    contract = contracts[0]
                    parameter = contract.get("parameter", {}).get("value", {})
                    from_address = parameter.get("owner_address")
                    to_address = parameter.get("to_address")
                    amount = parameter.get("amount")
            
            return VerificationResult(
                txid=txid,
                status=status,
                confirmations=confirmations,
                block_number=block_number,
                timestamp=timestamp,
                from_address=from_address,
                to_address=to_address,
                amount=amount,
                fee=fee,
                contract_result=contract_result[0] if contract_result else None,
                message=message,
                verified_at=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Verification error for {txid}: {e}")
            self._stats["failed"] += 1
            return VerificationResult(
                txid=txid,
                status=VerificationStatus.ERROR,
                confirmations=0,
                block_number=None,
                timestamp=None,
                from_address=None,
                to_address=None,
                amount=None,
                fee=None,
                contract_result=None,
                message=f"Verification error: {str(e)}",
                verified_at=datetime.utcnow().isoformat()
            )
    
    async def verify_receipt(self, txid: str) -> Dict[str, Any]:
        """
        Verify transaction receipt
        
        Args:
            txid: Transaction ID
            
        Returns:
            Receipt verification result
        """
        try:
            tx_info = await relay_service.get_transaction_info(txid)
            
            if not tx_info:
                return {
                    "txid": txid,
                    "receipt_found": False,
                    "message": "Transaction receipt not found"
                }
            
            # Extract receipt information
            receipt = {
                "txid": txid,
                "receipt_found": True,
                "block_number": tx_info.get("blockNumber"),
                "block_timestamp": tx_info.get("blockTimeStamp"),
                "fee": tx_info.get("fee", 0),
                "energy_usage": tx_info.get("receipt", {}).get("energy_usage", 0),
                "energy_fee": tx_info.get("receipt", {}).get("energy_fee", 0),
                "net_usage": tx_info.get("receipt", {}).get("net_usage", 0),
                "net_fee": tx_info.get("receipt", {}).get("net_fee", 0),
                "result": tx_info.get("result", ""),
                "contract_result": tx_info.get("contractResult", []),
                "verified_at": datetime.utcnow().isoformat()
            }
            
            return receipt
            
        except Exception as e:
            logger.error(f"Receipt verification error for {txid}: {e}")
            return {
                "txid": txid,
                "receipt_found": False,
                "message": f"Error: {str(e)}"
            }
    
    async def verify_trc20_transfer(
        self,
        txid: str,
        expected_contract: Optional[str] = None,
        expected_from: Optional[str] = None,
        expected_to: Optional[str] = None,
        expected_amount: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Verify a TRC20 token transfer
        
        Args:
            txid: Transaction ID
            expected_contract: Expected token contract address
            expected_from: Expected sender address
            expected_to: Expected recipient address
            expected_amount: Expected amount in smallest unit
            
        Returns:
            Verification result with match status
        """
        try:
            tx_info = await relay_service.get_transaction_info(txid)
            
            if not tx_info:
                return {
                    "txid": txid,
                    "verified": False,
                    "message": "Transaction not found"
                }
            
            # Check for TRC20 transfer logs
            logs = tx_info.get("log", [])
            if not logs:
                return {
                    "txid": txid,
                    "verified": False,
                    "message": "No TRC20 transfer logs found"
                }
            
            # Parse transfer event
            for log in logs:
                topics = log.get("topics", [])
                # Transfer event signature: Transfer(address,address,uint256)
                transfer_signature = "ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
                
                if len(topics) >= 3 and topics[0] == transfer_signature:
                    contract_address = log.get("address")
                    from_addr = "T" + topics[1][-40:]  # Extract address from topic
                    to_addr = "T" + topics[2][-40:]
                    amount = int(log.get("data", "0"), 16) if log.get("data") else 0
                    
                    # Check expectations
                    matches = {
                        "contract_match": expected_contract is None or contract_address == expected_contract,
                        "from_match": expected_from is None or from_addr == expected_from,
                        "to_match": expected_to is None or to_addr == expected_to,
                        "amount_match": expected_amount is None or amount == expected_amount
                    }
                    
                    all_match = all(matches.values())
                    
                    return {
                        "txid": txid,
                        "verified": all_match,
                        "contract_address": contract_address,
                        "from_address": from_addr,
                        "to_address": to_addr,
                        "amount": amount,
                        "matches": matches,
                        "message": "TRC20 transfer verified" if all_match else "TRC20 transfer found but expectations not met",
                        "verified_at": datetime.utcnow().isoformat()
                    }
            
            return {
                "txid": txid,
                "verified": False,
                "message": "No matching TRC20 transfer found in logs"
            }
            
        except Exception as e:
            logger.error(f"TRC20 verification error for {txid}: {e}")
            return {
                "txid": txid,
                "verified": False,
                "message": f"Error: {str(e)}"
            }
    
    async def batch_verify(self, txids: List[str]) -> List[VerificationResult]:
        """
        Verify multiple transactions in parallel
        
        Args:
            txids: List of transaction IDs to verify
            
        Returns:
            List of verification results
        """
        tasks = [self.verify_transaction(txid) for txid in txids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        verified_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                verified_results.append(VerificationResult(
                    txid=txids[i],
                    status=VerificationStatus.ERROR,
                    confirmations=0,
                    block_number=None,
                    timestamp=None,
                    from_address=None,
                    to_address=None,
                    amount=None,
                    fee=None,
                    contract_result=None,
                    message=f"Error: {str(result)}",
                    verified_at=datetime.utcnow().isoformat()
                ))
            else:
                verified_results.append(result)
        
        return verified_results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get verification statistics"""
        return {
            "total_verifications": self._stats["total"],
            "successful": self._stats["successful"],
            "failed": self._stats["failed"],
            "pending": self._stats["pending"],
            "confirmation_threshold": config.confirmation_threshold
        }


# Global verification service instance
verification_service = VerificationService()

