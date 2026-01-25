"""
LUCID Payment Systems - Payment API
REST API endpoints for payment gateway operations
Distroless container: lucid-payment-gateway:latest
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# Import payment service
from ..services.payment_gateway import payment_gateway_service

# Import payment models from dedicated models file
from ..models.payment import (
    PaymentCreateRequest,
    PaymentStatusRequest,
    PaymentResponse,
    PaymentStatusResponse,
    PaymentStatus,
    PaymentType,
    PaymentMethod
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/tron/payments", tags=["payments"])

# ============================================================================
# Additional Pydantic Models for API
# ============================================================================

class PaymentListRequest(BaseModel):
    """List payments filter request"""
    status: Optional[PaymentStatus] = Field(None, description="Filter by payment status")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Results offset")

class PaymentCancelRequest(BaseModel):
    """Cancel payment request"""
    reason: Optional[str] = Field(None, description="Cancellation reason")

class PaymentStatsResponse(BaseModel):
    """Payment statistics response"""
    total_payments: int
    pending_payments: int
    processing_payments: int
    completed_payments: int
    failed_payments: int
    total_amount: float
    completed_amount: float
    timestamp: str

# ============================================================================
# Payment CRUD Endpoints
# ============================================================================

@router.post("/create", response_model=PaymentResponse, status_code=201)
async def create_payment(request: PaymentCreateRequest):
    """
    Create a new payment.
    
    This endpoint initiates a new payment transaction with the specified parameters.
    The payment starts in PENDING status and will be processed asynchronously.
    
    Args:
        request: Payment creation request with payment details
        
    Returns:
        PaymentResponse: Newly created payment with ID and status
        
    Raises:
        HTTPException: If payment creation fails
    """
    try:
        logger.info(f"API: Creating payment from {request.from_address} to {request.to_address}")
        payment = await payment_gateway_service.create_payment(request)
        return payment
    except Exception as e:
        logger.error(f"API: Error creating payment: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: str):
    """
    Get payment details by ID.
    
    Returns the complete payment information including status, amounts, and timestamps.
    
    Args:
        payment_id: Unique payment identifier
        
    Returns:
        PaymentResponse: Payment details
        
    Raises:
        HTTPException: If payment not found
    """
    try:
        logger.info(f"API: Getting payment {payment_id}")
        if payment_id not in payment_gateway_service.payments:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        payment_info = payment_gateway_service.payments[payment_id]
        return PaymentResponse(
            payment_id=payment_info.payment_id,
            transaction_id=payment_info.transaction_id,
            status=payment_info.status.value,
            amount=payment_info.amount,
            currency=payment_info.currency,
            from_address=payment_info.from_address,
            to_address=payment_info.to_address,
            fee=payment_info.fee,
            created_at=payment_info.created_at.isoformat(),
            processed_at=payment_info.processed_at.isoformat() if payment_info.processed_at else None,
            completed_at=payment_info.completed_at.isoformat() if payment_info.completed_at else None,
            error_message=payment_info.error_message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Error getting payment {payment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[PaymentResponse])
async def list_payments(
    status: Optional[str] = Query(None, description="Filter by payment status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Results offset")
):
    """
    List payments with optional filtering and pagination.
    
    Returns a paginated list of payments, optionally filtered by status.
    Results are sorted by creation time (newest first).
    
    Args:
        status: Optional status filter (pending, processing, completed, failed, cancelled, refunded)
        limit: Maximum results to return (default 100, max 1000)
        offset: Number of results to skip
        
    Returns:
        List[PaymentResponse]: List of payments
        
    Raises:
        HTTPException: If filtering fails
    """
    try:
        logger.info(f"API: Listing payments - status={status}, limit={limit}, offset={offset}")
        
        # Parse status filter
        payment_status = None
        if status:
            try:
                payment_status = PaymentStatus(status.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        # Get payments
        payments = await payment_gateway_service.list_payments(
            status=payment_status,
            limit=limit + offset
        )
        
        # Apply offset and limit
        paginated_payments = payments[offset:offset + limit]
        
        return paginated_payments
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Error listing payments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{payment_id}/process", response_model=PaymentResponse)
async def process_payment(payment_id: str):
    """
    Process a payment.
    
    Transitions a payment from PENDING to PROCESSING status and initiates the transaction.
    The actual blockchain transaction will be executed based on the payment type.
    
    Args:
        payment_id: ID of payment to process
        
    Returns:
        PaymentResponse: Updated payment status
        
    Raises:
        HTTPException: If payment cannot be processed
    """
    try:
        logger.info(f"API: Processing payment {payment_id}")
        payment = await payment_gateway_service.process_payment(payment_id)
        return payment
    except ValueError as e:
        logger.error(f"API: Invalid payment {payment_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"API: Error processing payment {payment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{payment_id}/status", response_model=PaymentStatusResponse)
async def get_payment_status(payment_id: str):
    """
    Get payment status.
    
    Returns the current status and details of a specific payment.
    
    Args:
        payment_id: ID of payment to check
        
    Returns:
        PaymentStatusResponse: Payment status details
        
    Raises:
        HTTPException: If payment not found
    """
    try:
        logger.info(f"API: Getting status for payment {payment_id}")
        status_request = PaymentStatusRequest(payment_id=payment_id)
        status = await payment_gateway_service.get_payment_status(status_request)
        return status
    except ValueError as e:
        logger.error(f"API: Payment not found {payment_id}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"API: Error getting payment status {payment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{payment_id}/cancel", response_model=PaymentResponse)
async def cancel_payment(payment_id: str, request: Optional[PaymentCancelRequest] = None):
    """
    Cancel a payment.
    
    Cancels a payment that is still in PENDING or PROCESSING status.
    Once a payment is COMPLETED or FAILED, it cannot be cancelled.
    
    Args:
        payment_id: ID of payment to cancel
        request: Optional cancellation details with reason
        
    Returns:
        PaymentResponse: Updated payment status
        
    Raises:
        HTTPException: If payment cannot be cancelled
    """
    try:
        logger.info(f"API: Cancelling payment {payment_id}")
        
        if payment_id not in payment_gateway_service.payments:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        payment_info = payment_gateway_service.payments[payment_id]
        
        # Check if payment can be cancelled
        if payment_info.status not in [PaymentStatus.PENDING, PaymentStatus.PROCESSING]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel payment with status {payment_info.status.value}"
            )
        
        # Mark payment as cancelled
        payment_info.status = PaymentStatus.CANCELLED
        payment_info.error_message = request.reason if request and request.reason else "Cancelled by user"
        
        # Remove from active processing queues
        if payment_id in payment_gateway_service.pending_payments:
            del payment_gateway_service.pending_payments[payment_id]
        if payment_id in payment_gateway_service.processing_payments:
            del payment_gateway_service.processing_payments[payment_id]
        
        # Log cancellation event
        await payment_gateway_service._log_payment_event(
            payment_id,
            "payment_cancelled",
            {"reason": request.reason if request and request.reason else "User cancellation"}
        )
        
        # Save registry
        await payment_gateway_service._save_payments_registry()
        
        logger.info(f"API: Payment {payment_id} cancelled")
        
        return PaymentResponse(
            payment_id=payment_info.payment_id,
            transaction_id=payment_info.transaction_id,
            status=payment_info.status.value,
            amount=payment_info.amount,
            currency=payment_info.currency,
            from_address=payment_info.from_address,
            to_address=payment_info.to_address,
            fee=payment_info.fee,
            created_at=payment_info.created_at.isoformat(),
            processed_at=payment_info.processed_at.isoformat() if payment_info.processed_at else None,
            completed_at=payment_info.completed_at.isoformat() if payment_info.completed_at else None,
            error_message=payment_info.error_message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Error cancelling payment {payment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary", response_model=dict)
async def get_payment_stats():
    """
    Get payment gateway statistics and summary.
    
    Returns comprehensive statistics about payment processing including:
    - Total payment counts by status
    - Total and completed amounts
    - Payment type distribution
    - Timestamp of statistics
    
    Returns:
        dict: Payment statistics summary
        
    Raises:
        HTTPException: If statistics retrieval fails
    """
    try:
        logger.info("API: Getting payment statistics")
        stats = await payment_gateway_service.get_service_stats()
        return stats
    except Exception as e:
        logger.error(f"API: Error getting payment statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Global router instance for importing
payment_router = router
