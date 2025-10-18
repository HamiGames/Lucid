"""
Transactions Router

This module contains the transaction processing and management endpoints.
Implements the OpenAPI 3.0 specification for transaction operations.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
import logging

from ..schemas.transaction import (
    TransactionSubmitRequest, TransactionResponse, TransactionDetails,
    TransactionListResponse, TransactionBatchRequest, TransactionBatchResponse
)
from ..dependencies import get_current_user, verify_api_key, require_read_permission, require_write_permission
from ..services.transaction_service import TransactionService
from ..errors import TransactionNotFoundException, TransactionValidationException

router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"],
    responses={404: {"description": "Transaction not found"}},
)

logger = logging.getLogger(__name__)

@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_transaction(
    transaction_request: TransactionSubmitRequest,
    user = Depends(require_write_permission)
):
    """
    Submits a transaction to the lucid_blocks blockchain for processing.
    
    Accepts transaction data and submits it to the blockchain network.
    Returns transaction ID and status information.
    
    Transaction types supported:
    - session_anchor: Session manifest anchoring
    - data_storage: Data storage transactions
    - consensus_vote: Consensus voting transactions
    - system: System-level transactions
    """
    try:
        logger.info("Submitting transaction")
        tx_response = await TransactionService.submit_transaction(transaction_request.dict())
        return TransactionResponse(**tx_response)
    except Exception as e:
        logger.error(f"Failed to submit transaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit transaction"
        )

@router.get("/{tx_id}", response_model=TransactionDetails)
async def get_transaction_details(
    tx_id: str,
    user = Depends(require_read_permission)
):
    """
    Returns detailed information about a specific transaction.
    
    Provides comprehensive transaction information including:
    - Transaction metadata (ID, type, status, timestamps)
    - Transaction data payload
    - Fee and size information
    - Block information if confirmed
    - Transaction index in block
    """
    try:
        logger.info(f"Fetching transaction details for ID: {tx_id}")
        tx_details = await TransactionService.get_transaction_details(tx_id)
        if not tx_details:
            raise TransactionNotFoundException(tx_id)
        return TransactionDetails(**tx_details)
    except TransactionNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch transaction details for ID {tx_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve transaction details"
        )

@router.get("/pending", response_model=TransactionListResponse)
async def list_pending_transactions(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of pending transactions to return"),
    user = Depends(require_read_permission)
):
    """
    Returns a list of transactions pending confirmation.
    
    Provides information about transactions that have been submitted
    but not yet confirmed in a block. Useful for monitoring transaction
    processing status and network congestion.
    """
    try:
        logger.info(f"Listing pending transactions with limit={limit}")
        pending_txs = await TransactionService.list_pending_transactions(limit)
        return TransactionListResponse(**pending_txs)
    except Exception as e:
        logger.error(f"Failed to list pending transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve pending transactions"
        )

@router.post("/batch", response_model=TransactionBatchResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_batch_transactions(
    batch_request: TransactionBatchRequest,
    user = Depends(require_write_permission)
):
    """
    Submits multiple transactions in a single batch.
    
    Allows submission of up to 100 transactions in a single request.
    Returns batch ID and individual transaction IDs.
    
    Batch processing provides:
    - Improved efficiency for multiple transactions
    - Atomic processing (all or none)
    - Batch-level error handling
    - Individual transaction status tracking
    """
    try:
        logger.info("Submitting batch transactions")
        batch_response = await TransactionService.submit_batch_transactions(batch_request.dict())
        return TransactionBatchResponse(**batch_response)
    except Exception as e:
        logger.error(f"Failed to submit batch transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit batch transactions"
        )