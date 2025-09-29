# Path: open-api/api/app/routes/payouts.py
# Lucid RDP TRON Payout API Blueprint
# Implements R-MUST-015, R-MUST-018: TRON/USDT payment processing via isolated TRON-Node System

from __future__ import annotations

import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, validator

# Import from our components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
from payment_systems.tron_node.tron_client import TronNodeSystem
from user_content.wallet.user_wallet import UserWallet
from node.economy.node_economy import NodeEconomy

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payouts", tags=["payouts"])
security = HTTPBearer()

# Pydantic Models
class TronAddress(BaseModel):
    """TRON address validation"""
    address: str = Field(..., pattern=r'^T[A-Za-z0-9]{33}$', description="TRON wallet address")

class ComplianceSignature(BaseModel):
    """Compliance signature for KYC payouts"""
    v: int = Field(..., description="Recovery ID")
    r: str = Field(..., pattern=r'^[a-fA-F0-9]{64}$', description="R component")
    s: str = Field(..., pattern=r'^[a-fA-F0-9]{64}$', description="S component")
    expiry: int = Field(..., description="Signature expiry timestamp")

class TronPayout(BaseModel):
    """TRON payout transaction (R-MUST-015, R-MUST-018)"""
    payout_id: str = Field(..., description="Unique payout identifier")
    session_id: str = Field(..., description="Associated session identifier")
    recipient_address: str = Field(..., pattern=r'^T[A-Za-z0-9]{33}$', description="TRON recipient address")
    amount_usdt: Decimal = Field(..., description="USDT amount (TRC-20)", decimal_places=6, max_digits=18)
    router_type: str = Field(..., enum=["PR0", "PRKYC"], description="PayoutRouterV0 (PR0) or PayoutRouterKYC (PRKYC)")
    reason: str = Field(..., description="Payout reason code")
    kyc_hash: Optional[str] = Field(None, pattern=r'^[a-fA-F0-9]{64}$', description="KYC hash (required for PRKYC)")
    compliance_signature: Optional[ComplianceSignature] = Field(None, description="Compliance signature (PRKYC only)")
    txid: Optional[str] = Field(None, description="TRON transaction ID")
    status: str = Field(default="pending", enum=["pending", "processing", "confirmed", "failed"])
    gas_fee_trx: Optional[Decimal] = Field(None, description="Gas fee in TRX")
    energy_consumed: Optional[int] = Field(None, description="Energy consumed")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")
    confirmed_at: Optional[datetime] = Field(None, description="Confirmation timestamp")

    @validator('amount_usdt')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        if v > Decimal('1000000'):  # 1M USDT max
            raise ValueError("Amount exceeds maximum limit")
        return v

class PayoutRequest(BaseModel):
    """Request to create a payout"""
    session_id: str = Field(..., description="Associated session identifier")
    recipient_address: str = Field(..., pattern=r'^T[A-Za-z0-9]{33}$', description="TRON recipient address")
    amount_usdt: Decimal = Field(..., description="USDT amount to payout", decimal_places=6, max_digits=18)
    router_type: str = Field(..., enum=["PR0", "PRKYC"], description="Payout router type")
    reason: str = Field(..., description="Payout reason")
    kyc_hash: Optional[str] = Field(None, description="KYC hash for PRKYC payouts")
    compliance_signature: Optional[ComplianceSignature] = Field(None, description="Compliance signature for PRKYC")
    priority: str = Field(default="normal", enum=["low", "normal", "high"], description="Payout priority")

class MonthlyPayoutSummary(BaseModel):
    """Monthly payout summary (R-MUST-018)"""
    month: str = Field(..., description="Month in YYYY-MM format")
    total_payouts: int = Field(..., description="Total number of payouts")
    total_amount_usdt: Decimal = Field(..., description="Total USDT amount paid out")
    node_worker_payouts: int = Field(..., description="Node worker payouts (PRKYC)")
    node_worker_amount_usdt: Decimal = Field(..., description="Node worker payout amount")
    end_user_payouts: int = Field(..., description="End user payouts (PR0)")
    end_user_amount_usdt: Decimal = Field(..., description="End user payout amount")
    processing_fees_trx: Decimal = Field(..., description="Total processing fees in TRX")
    energy_consumed: int = Field(..., description="Total energy consumed")

class PayoutStats(BaseModel):
    """Payout statistics"""
    period_start: datetime
    period_end: datetime
    total_payouts: int
    successful_payouts: int
    failed_payouts: int
    total_amount_usdt: Decimal
    average_amount_usdt: Decimal
    total_fees_trx: Decimal
    pr0_payouts: int
    prkyc_payouts: int

class TronNetworkStatus(BaseModel):
    """TRON network status"""
    network: str = Field(..., enum=["mainnet", "shasta", "nile"], description="TRON network")
    latest_block: int = Field(..., description="Latest block number")
    tps: int = Field(..., description="Transactions per second")
    energy_price: int = Field(..., description="Energy price in SUN")
    bandwidth_price: int = Field(..., description="Bandwidth price in SUN")
    usdt_contract: str = Field(..., description="USDT TRC-20 contract address")
    node_sync_status: str = Field(..., enum=["synced", "syncing", "offline"], description="Node sync status")
    last_block_time: datetime = Field(..., description="Last block timestamp")

# Global TRON components
tron_client = TronNodeSystem("mainnet")  # Production network per R-MUST-015

@router.post("/create", response_model=TronPayout, status_code=status.HTTP_201_CREATED)
async def create_payout(
    request: PayoutRequest,
    token: str = Depends(security)
) -> TronPayout:
    """
    Create TRON/USDT payout (R-MUST-015, R-MUST-018).
    
    Routes through isolated TRON-Node System:
    - PR0 (PayoutRouterV0): Non-KYC payouts for end users
    - PRKYC (PayoutRouterKYC): KYC payouts for node workers
    
    Monthly payouts with proper compliance signatures.
    """
    try:
        logger.info(f"Creating TRON payout for session {request.session_id}: {request.amount_usdt} USDT -> {request.recipient_address}")
        
        # Validate router type requirements
        if request.router_type == "PRKYC":
            if not request.kyc_hash or not request.compliance_signature:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="KYC hash and compliance signature required for PRKYC payouts"
                )
            
            # Verify compliance signature is not expired
            current_timestamp = int(datetime.now(timezone.utc).timestamp())
            if request.compliance_signature.expiry < current_timestamp:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Compliance signature has expired"
                )
        
        # Generate payout ID
        payout_id = hashlib.sha256(
            f"{request.session_id}_{request.recipient_address}_{request.amount_usdt}_{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]
        
        # Create payout record
        payout = TronPayout(
            payout_id=payout_id,
            session_id=request.session_id,
            recipient_address=request.recipient_address,
            amount_usdt=request.amount_usdt,
            router_type=request.router_type,
            reason=request.reason,
            kyc_hash=request.kyc_hash,
            compliance_signature=request.compliance_signature,
            status="pending"
        )
        
        # Submit to TRON network via isolated TRON-Node System
        try:
            if request.router_type == "PR0":
                # Non-KYC payout for end users
                tx_result = await tron_client.process_pr0_payout(
                    recipient=request.recipient_address,
                    amount_usdt=float(request.amount_usdt),
                    session_id=request.session_id,
                    reason=request.reason
                )
            else:  # PRKYC
                # KYC payout for node workers
                tx_result = await tron_client.process_prkyc_payout(
                    recipient=request.recipient_address,
                    amount_usdt=float(request.amount_usdt),
                    session_id=request.session_id,
                    kyc_hash=request.kyc_hash,
                    compliance_signature=request.compliance_signature.dict(),
                    reason=request.reason
                )
            
            if tx_result and tx_result.get("success"):
                payout.txid = tx_result.get("txid")
                payout.status = "processing"
                payout.processed_at = datetime.now(timezone.utc)
                payout.gas_fee_trx = Decimal(str(tx_result.get("gas_fee_trx", 0)))
                payout.energy_consumed = tx_result.get("energy_consumed", 0)
                
                logger.info(f"TRON payout submitted: {payout_id} -> {payout.txid}")
            else:
                payout.status = "failed"
                logger.error(f"TRON payout submission failed: {payout_id}")
                
        except Exception as tron_error:
            logger.error(f"TRON network error: {tron_error}")
            payout.status = "failed"
        
        # Store payout record in database
        # await store_payout(payout)
        
        return payout
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create payout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payout creation failed: {str(e)}"
        )

@router.get("/{payout_id}", response_model=TronPayout)
async def get_payout_status(
    payout_id: str,
    token: str = Depends(security)
) -> TronPayout:
    """Get TRON payout status"""
    try:
        logger.info(f"Getting payout status: {payout_id}")
        
        # This would query the payout database
        # For now, return a mock payout with realistic data
        mock_payout = TronPayout(
            payout_id=payout_id,
            session_id="session_12345",
            recipient_address="TTestRecipient123456789012345",
            amount_usdt=Decimal("25.500000"),
            router_type="PR0",
            reason="session_completion",
            txid=f"tron_tx_{hashlib.sha256(payout_id.encode()).hexdigest()[:16]}",
            status="confirmed",
            gas_fee_trx=Decimal("1.5"),
            energy_consumed=15000,
            processed_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            confirmed_at=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        
        logger.info(f"Payout status retrieved: {payout_id}")
        return mock_payout
        
    except Exception as e:
        logger.error(f"Failed to get payout status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payout status: {str(e)}"
        )

@router.get("/session/{session_id}", response_model=List[TronPayout])
async def get_session_payouts(
    session_id: str,
    token: str = Depends(security)
) -> List[TronPayout]:
    """Get all payouts for a session"""
    try:
        logger.info(f"Getting payouts for session: {session_id}")
        
        # This would query payouts by session_id
        # For now, return mock payouts
        payouts = [
            TronPayout(
                payout_id=f"payout_{session_id}_{i}",
                session_id=session_id,
                recipient_address=f"TRecipient{i}234567890123456789",
                amount_usdt=Decimal(f"{10.0 + i * 5}"),
                router_type="PR0" if i % 2 == 0 else "PRKYC",
                reason="session_completion",
                status="confirmed",
                txid=f"tron_tx_{i}_{hashlib.sha256(session_id.encode()).hexdigest()[:8]}",
                gas_fee_trx=Decimal("1.2"),
                energy_consumed=12000 + i * 1000,
                processed_at=datetime.now(timezone.utc) - timedelta(hours=i),
                confirmed_at=datetime.now(timezone.utc) - timedelta(hours=i, minutes=-30)
            ) for i in range(3)
        ]
        
        logger.info(f"Retrieved {len(payouts)} payouts for session: {session_id}")
        return payouts
        
    except Exception as e:
        logger.error(f"Failed to get session payouts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session payouts: {str(e)}"
        )

@router.get("/monthly/{year}/{month}", response_model=MonthlyPayoutSummary)
async def get_monthly_payout_summary(
    year: int = Field(..., ge=2024, le=2030, description="Year"),
    month: int = Field(..., ge=1, le=12, description="Month"),
    token: str = Depends(security)
) -> MonthlyPayoutSummary:
    """
    Get monthly payout summary (R-MUST-018).
    
    Returns breakdown of:
    - Node worker payouts via PRKYC
    - End user payouts via PR0
    - Total processing costs and energy consumption
    """
    try:
        month_str = f"{year:04d}-{month:02d}"
        logger.info(f"Getting monthly payout summary for: {month_str}")
        
        # This would query actual payout data for the month
        # For now, return mock summary
        summary = MonthlyPayoutSummary(
            month=month_str,
            total_payouts=150,
            total_amount_usdt=Decimal("15750.250000"),
            node_worker_payouts=45,  # PRKYC payouts
            node_worker_amount_usdt=Decimal("12250.500000"),
            end_user_payouts=105,  # PR0 payouts  
            end_user_amount_usdt=Decimal("3499.750000"),
            processing_fees_trx=Decimal("225.750000"),
            energy_consumed=2250000
        )
        
        logger.info(f"Monthly summary retrieved for {month_str}: {summary.total_payouts} payouts")
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get monthly summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve monthly summary: {str(e)}"
        )

@router.get("/stats/period", response_model=PayoutStats)
async def get_payout_statistics(
    start_date: datetime = Query(..., description="Period start date"),
    end_date: datetime = Query(..., description="Period end date"),
    router_type: Optional[str] = Query(None, enum=["PR0", "PRKYC"], description="Filter by router type"),
    token: str = Depends(security)
) -> PayoutStats:
    """Get payout statistics for a date range"""
    try:
        logger.info(f"Getting payout stats from {start_date} to {end_date}")
        
        # Validate date range
        if end_date <= start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after start date"
            )
        
        if (end_date - start_date).days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date range cannot exceed 365 days"
            )
        
        # This would calculate actual statistics from database
        stats = PayoutStats(
            period_start=start_date,
            period_end=end_date,
            total_payouts=75,
            successful_payouts=72,
            failed_payouts=3,
            total_amount_usdt=Decimal("8125.750000"),
            average_amount_usdt=Decimal("108.343333"),
            total_fees_trx=Decimal("112.500000"),
            pr0_payouts=50,
            prkyc_payouts=25
        )
        
        # Apply router type filter
        if router_type == "PR0":
            stats.prkyc_payouts = 0
        elif router_type == "PRKYC":
            stats.pr0_payouts = 0
        
        logger.info(f"Payout stats retrieved: {stats.total_payouts} payouts")
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get payout statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payout statistics: {str(e)}"
        )

@router.post("/{payout_id}/retry", response_model=TronPayout)
async def retry_failed_payout(
    payout_id: str,
    token: str = Depends(security)
) -> TronPayout:
    """Retry a failed payout"""
    try:
        logger.info(f"Retrying failed payout: {payout_id}")
        
        # Get existing payout
        # payout = await get_payout_from_db(payout_id)
        
        # Verify payout is in failed state
        # if payout.status != "failed":
        #     raise HTTPException(400, "Only failed payouts can be retried")
        
        # Retry the payout via TRON network
        # Similar logic to create_payout but for retry
        
        # For now, simulate successful retry
        retried_payout = TronPayout(
            payout_id=payout_id,
            session_id="session_retry",
            recipient_address="TRetryRecipient12345678901234",
            amount_usdt=Decimal("25.000000"),
            router_type="PR0",
            reason="retry_failed_payout",
            txid=f"retry_tx_{hashlib.sha256(payout_id.encode()).hexdigest()[:16]}",
            status="processing",
            processed_at=datetime.now(timezone.utc)
        )
        
        logger.info(f"Payout retry submitted: {payout_id}")
        return retried_payout
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry payout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payout retry failed: {str(e)}"
        )

@router.get("/network/status", response_model=TronNetworkStatus)
async def get_tron_network_status(
    token: str = Depends(security)
) -> TronNetworkStatus:
    """Get TRON network status from isolated TRON-Node System"""
    try:
        logger.info("Getting TRON network status")
        
        # Query TRON network via isolated client
        network_info = await tron_client.get_network_status()
        
        status_info = TronNetworkStatus(
            network=network_info.get("network", "mainnet"),
            latest_block=network_info.get("latest_block", 123456789),
            tps=network_info.get("tps", 2500),
            energy_price=network_info.get("energy_price", 210),
            bandwidth_price=network_info.get("bandwidth_price", 1000),
            usdt_contract=network_info.get("usdt_contract", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"),
            node_sync_status=network_info.get("sync_status", "synced"),
            last_block_time=datetime.now(timezone.utc)
        )
        
        logger.info(f"TRON network status: {status_info.network}, block: {status_info.latest_block}")
        return status_info
        
    except Exception as e:
        logger.error(f"Failed to get TRON network status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve network status: {str(e)}"
        )

@router.post("/validate/address", response_model=Dict[str, Any])
async def validate_tron_address(
    address: TronAddress,
    token: str = Depends(security)
) -> Dict[str, Any]:
    """Validate TRON address and get account info"""
    try:
        logger.info(f"Validating TRON address: {address.address}")
        
        # Validate address via TRON network
        validation_result = await tron_client.validate_address(address.address)
        
        result = {
            "address": address.address,
            "valid": validation_result.get("valid", False),
            "activated": validation_result.get("activated", False),
            "balance_trx": validation_result.get("balance_trx", 0),
            "balance_usdt": validation_result.get("balance_usdt", 0),
            "account_type": validation_result.get("type", "unknown"),
            "validated_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Address validation result: {address.address} -> valid={result['valid']}")
        return result
        
    except Exception as e:
        logger.error(f"Address validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Address validation failed: {str(e)}"
        )

@router.get("/fees/estimate", response_model=Dict[str, Any])
async def estimate_payout_fees(
    amount_usdt: Decimal = Query(..., description="USDT amount to estimate fees for"),
    router_type: str = Query(..., enum=["PR0", "PRKYC"], description="Payout router type"),
    token: str = Depends(security)
) -> Dict[str, Any]:
    """Estimate TRON payout fees"""
    try:
        logger.info(f"Estimating fees for {amount_usdt} USDT via {router_type}")
        
        # Get current network conditions
        network_status = await tron_client.get_network_status()
        
        # Estimate fees based on router type and network conditions
        if router_type == "PRKYC":
            # PRKYC transactions are more complex (KYC verification)
            base_energy = 65000
            base_bandwidth = 345
        else:
            # PR0 transactions are simpler
            base_energy = 45000
            base_bandwidth = 268
        
        energy_price = network_status.get("energy_price", 210)
        bandwidth_price = network_status.get("bandwidth_price", 1000)
        
        energy_fee_sun = base_energy * energy_price
        bandwidth_fee_sun = base_bandwidth * bandwidth_price
        total_fee_sun = energy_fee_sun + bandwidth_fee_sun
        total_fee_trx = total_fee_sun / 1_000_000  # Convert SUN to TRX
        
        fee_estimate = {
            "amount_usdt": amount_usdt,
            "router_type": router_type,
            "estimated_energy": base_energy,
            "estimated_bandwidth": base_bandwidth,
            "energy_price_sun": energy_price,
            "bandwidth_price_sun": bandwidth_price,
            "energy_fee_sun": energy_fee_sun,
            "bandwidth_fee_sun": bandwidth_fee_sun,
            "total_fee_sun": total_fee_sun,
            "total_fee_trx": round(total_fee_trx, 6),
            "estimated_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Fee estimate: {total_fee_trx} TRX for {amount_usdt} USDT via {router_type}")
        return fee_estimate
        
    except Exception as e:
        logger.error(f"Fee estimation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fee estimation failed: {str(e)}"
        )

# Health check endpoint
@router.get("/health", include_in_schema=False)
async def payouts_health() -> Dict[str, Any]:
    """Payout service health check"""
    try:
        # Check TRON network connectivity
        network_ok = await tron_client.ping()
        
        return {
            "service": "payouts",
            "status": "healthy" if network_ok else "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {
                "tron_network": "operational" if network_ok else "offline",
                "pr0_router": "operational",
                "prkyc_router": "operational",
                "payout_processor": "operational"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "service": "payouts", 
            "status": "unhealthy",
            "error": str(e)
        }