"""
LUCID TRON Relay - Verification API Endpoints
Transaction verification and validation endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

from config import config
from services.verification_service import verification_service, VerificationResult

router = APIRouter()


class VerifyTransactionRequest(BaseModel):
    """Transaction verification request"""
    txid: str = Field(..., description="Transaction ID to verify")


class VerifyTransactionResponse(BaseModel):
    """Transaction verification response"""
    txid: str
    status: str
    confirmations: int
    block_number: Optional[int]
    timestamp: Optional[int]
    from_address: Optional[str]
    to_address: Optional[str]
    amount: Optional[int]
    fee: Optional[int]
    message: str
    verified_at: str


class BatchVerifyRequest(BaseModel):
    """Batch verification request"""
    txids: List[str] = Field(..., description="List of transaction IDs to verify", max_length=100)


class BatchVerifyResponse(BaseModel):
    """Batch verification response"""
    total: int
    verified: int
    pending: int
    failed: int
    results: List[Dict[str, Any]]


class VerifyReceiptRequest(BaseModel):
    """Receipt verification request"""
    txid: str = Field(..., description="Transaction ID")


class VerifyTRC20Request(BaseModel):
    """TRC20 transfer verification request"""
    txid: str = Field(..., description="Transaction ID")
    expected_contract: Optional[str] = Field(None, description="Expected token contract address")
    expected_from: Optional[str] = Field(None, description="Expected sender address")
    expected_to: Optional[str] = Field(None, description="Expected recipient address")
    expected_amount: Optional[int] = Field(None, description="Expected amount in smallest unit")


@router.post("/transaction", response_model=VerifyTransactionResponse)
async def verify_transaction(request: VerifyTransactionRequest):
    """
    Verify a transaction exists and is confirmed
    
    Checks:
    - Transaction exists on TRON network
    - Has required confirmations
    - Returns transaction details
    """
    result = await verification_service.verify_transaction(request.txid)
    
    # Update global stats
    from main import service_state
    service_state["verification_stats"]["total"] = verification_service._stats["total"]
    service_state["verification_stats"]["successful"] = verification_service._stats["successful"]
    service_state["verification_stats"]["failed"] = verification_service._stats["failed"]
    
    return VerifyTransactionResponse(
        txid=result.txid,
        status=result.status.value,
        confirmations=result.confirmations,
        block_number=result.block_number,
        timestamp=result.timestamp,
        from_address=result.from_address,
        to_address=result.to_address,
        amount=result.amount,
        fee=result.fee,
        message=result.message,
        verified_at=result.verified_at
    )


@router.post("/batch", response_model=BatchVerifyResponse)
async def batch_verify_transactions(request: BatchVerifyRequest):
    """
    Verify multiple transactions in parallel
    
    Limited to 100 transactions per request
    """
    if len(request.txids) > 100:
        raise HTTPException(
            status_code=400,
            detail="Maximum 100 transactions per batch request"
        )
    
    results = await verification_service.batch_verify(request.txids)
    
    # Count results
    verified = sum(1 for r in results if r.status.value == "verified")
    pending = sum(1 for r in results if r.status.value == "insufficient_confirmations")
    failed = sum(1 for r in results if r.status.value in ["not_found", "failed", "error"])
    
    # Update global stats
    from main import service_state
    service_state["verification_stats"]["total"] = verification_service._stats["total"]
    service_state["verification_stats"]["successful"] = verification_service._stats["successful"]
    service_state["verification_stats"]["failed"] = verification_service._stats["failed"]
    
    return BatchVerifyResponse(
        total=len(results),
        verified=verified,
        pending=pending,
        failed=failed,
        results=[r.to_dict() for r in results]
    )


@router.post("/receipt")
async def verify_receipt(request: VerifyReceiptRequest):
    """
    Verify a transaction receipt
    
    Returns:
    - Receipt details including fees, energy, bandwidth usage
    """
    result = await verification_service.verify_receipt(request.txid)
    return result


@router.post("/trc20")
async def verify_trc20_transfer(request: VerifyTRC20Request):
    """
    Verify a TRC20 token transfer
    
    Can optionally verify:
    - Token contract address matches
    - Sender address matches
    - Recipient address matches
    - Amount matches
    """
    result = await verification_service.verify_trc20_transfer(
        txid=request.txid,
        expected_contract=request.expected_contract,
        expected_from=request.expected_from,
        expected_to=request.expected_to,
        expected_amount=request.expected_amount
    )
    return result


@router.get("/confirmation/{txid}")
async def check_confirmations(txid: str):
    """
    Check confirmation count for a transaction
    
    Returns:
    - Current confirmations
    - Whether threshold is met
    """
    from services.relay_service import relay_service
    
    confirmations = await relay_service.get_transaction_confirmations(txid)
    
    return {
        "txid": txid,
        "confirmations": confirmations,
        "threshold": config.confirmation_threshold,
        "confirmed": confirmations >= config.confirmation_threshold
    }


@router.get("/stats")
async def get_verification_stats():
    """Get verification statistics"""
    return verification_service.get_stats()


@router.get("/health")
async def verification_health():
    """Check verification service health"""
    from services.relay_service import relay_service
    
    tron_connected = await relay_service.check_tron_connection()
    
    return {
        "service": "verification",
        "initialized": verification_service.initialized,
        "tron_connected": tron_connected,
        "confirmation_threshold": config.confirmation_threshold,
        "stats": verification_service.get_stats(),
        "status": "healthy" if verification_service.initialized and tron_connected else "degraded"
    }

