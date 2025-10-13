# 12. Code Examples

## Overview

This document provides comprehensive code examples for implementing the TRON Payment System API, including client implementations, server-side code, and integration patterns.

## Client Implementations

### Python Client

#### Basic Client Setup

```python
# client/python/lucid_payment_client.py
import asyncio
import aiohttp
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PayoutRequest:
    recipient_address: str
    amount_usdt: float
    reference_id: str
    metadata: Optional[Dict] = None

@dataclass
class PayoutResponse:
    payout_id: str
    status: str
    transaction_hash: Optional[str]
    created_at: datetime
    estimated_confirmation: Optional[datetime]

class LucidPaymentClient:
    def __init__(self, api_key: str, base_url: str, timeout: int = 30):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            headers={'Authorization': f'Bearer {self.api_key}'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def create_payout(self, payout: PayoutRequest) -> PayoutResponse:
        """Create a single payout transaction."""
        url = f"{self.base_url}/api/payment/payouts"
        payload = {
            "recipient_address": payout.recipient_address,
            "amount_usdt": payout.amount_usdt,
            "reference_id": payout.reference_id,
            "metadata": payout.metadata or {}
        }
        
        async with self.session.post(url, json=payload) as response:
            response.raise_for_status()
            data = await response.json()
            
            return PayoutResponse(
                payout_id=data["payout_id"],
                status=data["status"],
                transaction_hash=data.get("transaction_hash"),
                created_at=datetime.fromisoformat(data["created_at"]),
                estimated_confirmation=datetime.fromisoformat(data["estimated_confirmation"]) if data.get("estimated_confirmation") else None
            )
    
    async def get_payout_status(self, payout_id: str) -> PayoutResponse:
        """Get the status of a payout transaction."""
        url = f"{self.base_url}/api/payment/payouts/{payout_id}"
        
        async with self.session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            
            return PayoutResponse(
                payout_id=data["payout_id"],
                status=data["status"],
                transaction_hash=data.get("transaction_hash"),
                created_at=datetime.fromisoformat(data["created_at"]),
                estimated_confirmation=datetime.fromisoformat(data["estimated_confirmation"]) if data.get("estimated_confirmation") else None
            )
    
    async def create_batch_payout(self, payouts: List[PayoutRequest]) -> Dict:
        """Create a batch payout transaction."""
        url = f"{self.base_url}/api/payment/payouts/batch"
        payload = {
            "payouts": [
                {
                    "recipient_address": p.recipient_address,
                    "amount_usdt": p.amount_usdt,
                    "reference_id": p.reference_id,
                    "metadata": p.metadata or {}
                }
                for p in payouts
            ]
        }
        
        async with self.session.post(url, json=payload) as response:
            response.raise_for_status()
            return await response.json()
    
    async def get_payment_stats(self) -> Dict:
        """Get payment system statistics."""
        url = f"{self.base_url}/api/payment/stats"
        
        async with self.session.get(url) as response:
            response.raise_for_status()
            return await response.json()

# Usage example
async def main():
    async with LucidPaymentClient("your-api-key", "https://api.lucid.example") as client:
        # Create a single payout
        payout = PayoutRequest(
            recipient_address="TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE",
            amount_usdt=100.0,
            reference_id="PAY-001",
            metadata={"description": "Salary payment"}
        )
        
        result = await client.create_payout(payout)
        print(f"Payout created: {result.payout_id}")
        
        # Check status
        status = await client.get_payout_status(result.payout_id)
        print(f"Status: {status.status}")

if __name__ == "__main__":
    asyncio.run(main())
```

#### Advanced Client with Retry Logic

```python
# client/python/advanced_client.py
import asyncio
import aiohttp
import random
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential

class AdvancedLucidPaymentClient(LucidPaymentClient):
    def __init__(self, api_key: str, base_url: str, timeout: int = 30, max_retries: int = 3):
        super().__init__(api_key, base_url, timeout)
        self.max_retries = max_retries
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def create_payout_with_retry(self, payout: PayoutRequest) -> PayoutResponse:
        """Create payout with automatic retry logic."""
        return await self.create_payout(payout)
    
    async def create_payouts_parallel(self, payouts: List[PayoutRequest], 
                                    max_concurrent: int = 5) -> List[PayoutResponse]:
        """Create multiple payouts in parallel with concurrency control."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def create_single_payout(payout: PayoutRequest) -> PayoutResponse:
            async with semaphore:
                return await self.create_payout_with_retry(payout)
        
        tasks = [create_single_payout(payout) for payout in payouts]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def wait_for_confirmation(self, payout_id: str, 
                                  timeout_minutes: int = 30) -> PayoutResponse:
        """Wait for payout confirmation with timeout."""
        start_time = datetime.now()
        timeout_delta = timedelta(minutes=timeout_minutes)
        
        while datetime.now() - start_time < timeout_delta:
            status = await self.get_payout_status(payout_id)
            
            if status.status in ["confirmed", "failed"]:
                return status
            
            await asyncio.sleep(10)  # Wait 10 seconds before next check
        
        raise TimeoutError(f"Payout {payout_id} did not confirm within {timeout_minutes} minutes")
```

### JavaScript/Node.js Client

```javascript
// client/javascript/lucid-payment-client.js
const axios = require('axios');

class LucidPaymentClient {
    constructor(apiKey, baseUrl, timeout = 30000) {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.timeout = timeout;
        
        this.client = axios.create({
            baseURL: this.baseUrl,
            timeout: this.timeout,
            headers: {
                'Authorization': `Bearer ${this.apiKey}`,
                'Content-Type': 'application/json'
            }
        });
    }
    
    async createPayout(payoutRequest) {
        try {
            const response = await this.client.post('/api/payment/payouts', {
                recipient_address: payoutRequest.recipientAddress,
                amount_usdt: payoutRequest.amountUsdt,
                reference_id: payoutRequest.referenceId,
                metadata: payoutRequest.metadata || {}
            });
            
            return {
                payoutId: response.data.payout_id,
                status: response.data.status,
                transactionHash: response.data.transaction_hash,
                createdAt: new Date(response.data.created_at),
                estimatedConfirmation: response.data.estimated_confirmation 
                    ? new Date(response.data.estimated_confirmation) 
                    : null
            };
        } catch (error) {
            throw new Error(`Payout creation failed: ${error.response?.data?.detail || error.message}`);
        }
    }
    
    async getPayoutStatus(payoutId) {
        try {
            const response = await this.client.get(`/api/payment/payouts/${payoutId}`);
            return {
                payoutId: response.data.payout_id,
                status: response.data.status,
                transactionHash: response.data.transaction_hash,
                createdAt: new Date(response.data.created_at),
                estimatedConfirmation: response.data.estimated_confirmation 
                    ? new Date(response.data.estimated_confirmation) 
                    : null
            };
        } catch (error) {
            throw new Error(`Status retrieval failed: ${error.response?.data?.detail || error.message}`);
        }
    }
    
    async createBatchPayout(payouts) {
        try {
            const response = await this.client.post('/api/payment/payouts/batch', {
                payouts: payouts.map(p => ({
                    recipient_address: p.recipientAddress,
                    amount_usdt: p.amountUsdt,
                    reference_id: p.referenceId,
                    metadata: p.metadata || {}
                }))
            });
            
            return response.data;
        } catch (error) {
            throw new Error(`Batch payout creation failed: ${error.response?.data?.detail || error.message}`);
        }
    }
    
    async getPaymentStats() {
        try {
            const response = await this.client.get('/api/payment/stats');
            return response.data;
        } catch (error) {
            throw new Error(`Stats retrieval failed: ${error.response?.data?.detail || error.message}`);
        }
    }
}

// Usage example
async function main() {
    const client = new LucidPaymentClient('your-api-key', 'https://api.lucid.example');
    
    try {
        // Create a single payout
        const payout = await client.createPayout({
            recipientAddress: 'TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE',
            amountUsdt: 100.0,
            referenceId: 'PAY-001',
            metadata: { description: 'Salary payment' }
        });
        
        console.log(`Payout created: ${payout.payoutId}`);
        
        // Check status
        const status = await client.getPayoutStatus(payout.payoutId);
        console.log(`Status: ${status.status}`);
        
    } catch (error) {
        console.error('Error:', error.message);
    }
}

module.exports = LucidPaymentClient;
```

## Server Implementation Examples

### FastAPI Application Structure

```python
# server/main.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import uvicorn
from app.core.config import settings
from app.core.database import init_db
from app.api.v1 import payment_router
from app.core.middleware import RateLimitMiddleware, SecurityMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Lucid TRON Payment API",
    description="Secure TRON payment processing system",
    version="1.0.0",
    lifespan=lifespan
)

# Security middleware
app.add_middleware(SecurityMiddleware)
app.add_middleware(RateLimitMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Include routers
app.include_router(payment_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "tron-payment-api"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
```

### Payment Router Implementation

```python
# server/app/api/v1/payment.py
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from app.core.auth import get_current_user
from app.core.rate_limit import rate_limit
from app.schemas.payment import (
    PayoutRequest, PayoutResponse, BatchPayoutRequest, 
    BatchPayoutResponse, PaymentStats
)
from app.services.payment_service import PaymentService
from app.services.tron_service import TronService
from app.core.circuit_breaker import CircuitBreaker

router = APIRouter()
security = HTTPBearer()

# Circuit breaker for TRON network calls
tron_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=TronServiceError
)

@router.post("/payouts", response_model=PayoutResponse)
@rate_limit(calls=100, period=3600)  # 100 calls per hour
async def create_payout(
    payout_request: PayoutRequest,
    current_user: dict = Depends(get_current_user),
    payment_service: PaymentService = Depends()
):
    """Create a single payout transaction."""
    
    # Validate user permissions
    if not current_user.get("can_create_payouts"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create payouts"
        )
    
    try:
        # Create payout record
        payout_id = str(uuid.uuid4())
        payout = await payment_service.create_payout(
            payout_id=payout_id,
            recipient_address=payout_request.recipient_address,
            amount_usdt=payout_request.amount_usdt,
            reference_id=payout_request.reference_id,
            metadata=payout_request.metadata,
            user_id=current_user["user_id"]
        )
        
        # Process transaction via circuit breaker
        async with tron_circuit_breaker:
            transaction_hash = await payment_service.process_payout(payout)
        
        # Update payout with transaction hash
        await payment_service.update_payout_status(
            payout_id=payout_id,
            status="pending",
            transaction_hash=transaction_hash
        )
        
        return PayoutResponse(
            payout_id=payout_id,
            status="pending",
            transaction_hash=transaction_hash,
            created_at=datetime.utcnow(),
            estimated_confirmation=datetime.utcnow() + timedelta(minutes=3)
        )
        
    except TronServiceError as e:
        await payment_service.update_payout_status(
            payout_id=payout_id,
            status="failed",
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"TRON network error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/payouts/{payout_id}", response_model=PayoutResponse)
@rate_limit(calls=1000, period=3600)
async def get_payout_status(
    payout_id: str,
    current_user: dict = Depends(get_current_user),
    payment_service: PaymentService = Depends()
):
    """Get the status of a payout transaction."""
    
    payout = await payment_service.get_payout(payout_id)
    if not payout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payout not found"
        )
    
    # Check user access to this payout
    if payout.user_id != current_user["user_id"] and not current_user.get("admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this payout"
        )
    
    return PayoutResponse(
        payout_id=payout.payout_id,
        status=payout.status,
        transaction_hash=payout.transaction_hash,
        created_at=payout.created_at,
        estimated_confirmation=payout.estimated_confirmation
    )

@router.post("/payouts/batch", response_model=BatchPayoutResponse)
@rate_limit(calls=10, period=3600)  # 10 batch requests per hour
async def create_batch_payout(
    batch_request: BatchPayoutRequest,
    current_user: dict = Depends(get_current_user),
    payment_service: PaymentService = Depends()
):
    """Create a batch payout transaction."""
    
    # Validate batch size
    if len(batch_request.payouts) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch size cannot exceed 100 payouts"
        )
    
    # Validate total amount
    total_amount = sum(p.amount_usdt for p in batch_request.payouts)
    if total_amount > 10000:  # $10,000 limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Total batch amount cannot exceed $10,000"
        )
    
    try:
        batch_id = str(uuid.uuid4())
        
        # Create batch record
        batch = await payment_service.create_batch(
            batch_id=batch_id,
            payouts=batch_request.payouts,
            user_id=current_user["user_id"]
        )
        
        # Process batch via circuit breaker
        async with tron_circuit_breaker:
            results = await payment_service.process_batch(batch)
        
        return BatchPayoutResponse(
            batch_id=batch_id,
            status="processing",
            total_payouts=len(batch_request.payouts),
            successful_payouts=len([r for r in results if r.status == "success"]),
            failed_payouts=len([r for r in results if r.status == "failed"]),
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch processing failed: {str(e)}"
        )

@router.get("/stats", response_model=PaymentStats)
@rate_limit(calls=60, period=3600)
async def get_payment_stats(
    current_user: dict = Depends(get_current_user),
    payment_service: PaymentService = Depends()
):
    """Get payment system statistics."""
    
    if not current_user.get("can_view_stats"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view statistics"
        )
    
    stats = await payment_service.get_payment_stats(user_id=current_user["user_id"])
    return PaymentStats(**stats)
```

### Service Layer Implementation

```python
# server/app/services/payment_service.py
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.payment import Payout, BatchPayout
from app.services.tron_service import TronService
from app.core.logging import get_logger

logger = get_logger(__name__)

class PaymentService:
    def __init__(self, db: Session, tron_service: TronService):
        self.db = db
        self.tron_service = tron_service
    
    async def create_payout(
        self,
        payout_id: str,
        recipient_address: str,
        amount_usdt: float,
        reference_id: str,
        metadata: Dict[str, Any],
        user_id: str
    ) -> Payout:
        """Create a new payout record."""
        
        payout = Payout(
            payout_id=payout_id,
            recipient_address=recipient_address,
            amount_usdt=amount_usdt,
            reference_id=reference_id,
            metadata=metadata,
            user_id=user_id,
            status="created",
            created_at=datetime.utcnow()
        )
        
        self.db.add(payout)
        self.db.commit()
        self.db.refresh(payout)
        
        logger.info(f"Created payout {payout_id} for {recipient_address}")
        return payout
    
    async def process_payout(self, payout: Payout) -> str:
        """Process a payout transaction on TRON network."""
        
        try:
            # Validate recipient address
            if not self.tron_service.validate_address(payout.recipient_address):
                raise ValueError(f"Invalid TRON address: {payout.recipient_address}")
            
            # Check wallet balance
            balance = await self.tron_service.get_usdt_balance()
            if balance < payout.amount_usdt:
                raise ValueError(f"Insufficient balance: {balance} < {payout.amount_usdt}")
            
            # Create and send transaction
            transaction_hash = await self.tron_service.send_usdt(
                to_address=payout.recipient_address,
                amount=payout.amount_usdt
            )
            
            logger.info(f"Sent USDT transaction {transaction_hash} for payout {payout.payout_id}")
            return transaction_hash
            
        except Exception as e:
            logger.error(f"Failed to process payout {payout.payout_id}: {str(e)}")
            raise
    
    async def update_payout_status(
        self,
        payout_id: str,
        status: str,
        transaction_hash: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Update payout status."""
        
        payout = self.db.query(Payout).filter(Payout.payout_id == payout_id).first()
        if not payout:
            raise ValueError(f"Payout {payout_id} not found")
        
        payout.status = status
        payout.updated_at = datetime.utcnow()
        
        if transaction_hash:
            payout.transaction_hash = transaction_hash
        
        if error_message:
            payout.error_message = error_message
        
        self.db.commit()
        logger.info(f"Updated payout {payout_id} status to {status}")
    
    async def get_payout(self, payout_id: str) -> Optional[Payout]:
        """Get payout by ID."""
        return self.db.query(Payout).filter(Payout.payout_id == payout_id).first()
    
    async def create_batch(
        self,
        batch_id: str,
        payouts: List[Dict[str, Any]],
        user_id: str
    ) -> BatchPayout:
        """Create a batch payout record."""
        
        batch = BatchPayout(
            batch_id=batch_id,
            user_id=user_id,
            total_payouts=len(payouts),
            status="created",
            created_at=datetime.utcnow()
        )
        
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        
        # Create individual payout records
        for payout_data in payouts:
            payout_id = str(uuid.uuid4())
            payout = Payout(
                payout_id=payout_id,
                batch_id=batch_id,
                recipient_address=payout_data["recipient_address"],
                amount_usdt=payout_data["amount_usdt"],
                reference_id=payout_data["reference_id"],
                metadata=payout_data.get("metadata", {}),
                user_id=user_id,
                status="created",
                created_at=datetime.utcnow()
            )
            self.db.add(payout)
        
        self.db.commit()
        logger.info(f"Created batch {batch_id} with {len(payouts)} payouts")
        return batch
    
    async def process_batch(self, batch: BatchPayout) -> List[Dict[str, Any]]:
        """Process a batch of payouts."""
        
        results = []
        payouts = self.db.query(Payout).filter(Payout.batch_id == batch.batch_id).all()
        
        for payout in payouts:
            try:
                transaction_hash = await self.process_payout(payout)
                await self.update_payout_status(
                    payout.payout_id,
                    "pending",
                    transaction_hash=transaction_hash
                )
                results.append({
                    "payout_id": payout.payout_id,
                    "status": "success",
                    "transaction_hash": transaction_hash
                })
            except Exception as e:
                await self.update_payout_status(
                    payout.payout_id,
                    "failed",
                    error_message=str(e)
                )
                results.append({
                    "payout_id": payout.payout_id,
                    "status": "failed",
                    "error": str(e)
                })
        
        # Update batch status
        successful = len([r for r in results if r["status"] == "success"])
        batch.status = "completed" if successful == len(payouts) else "partial"
        batch.successful_payouts = successful
        batch.failed_payouts = len(payouts) - successful
        batch.updated_at = datetime.utcnow()
        
        self.db.commit()
        logger.info(f"Processed batch {batch.batch_id}: {successful}/{len(payouts)} successful")
        return results
    
    async def get_payment_stats(self, user_id: str) -> Dict[str, Any]:
        """Get payment statistics for a user."""
        
        # Get payout statistics
        total_payouts = self.db.query(Payout).filter(Payout.user_id == user_id).count()
        successful_payouts = self.db.query(Payout).filter(
            Payout.user_id == user_id,
            Payout.status == "confirmed"
        ).count()
        
        total_amount = self.db.query(Payout).filter(
            Payout.user_id == user_id,
            Payout.status == "confirmed"
        ).with_entities(func.sum(Payout.amount_usdt)).scalar() or 0
        
        # Get recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_payouts = self.db.query(Payout).filter(
            Payout.user_id == user_id,
            Payout.created_at >= yesterday
        ).count()
        
        return {
            "total_payouts": total_payouts,
            "successful_payouts": successful_payouts,
            "failed_payouts": total_payouts - successful_payouts,
            "total_amount_usdt": float(total_amount),
            "recent_payouts_24h": recent_payouts,
            "success_rate": successful_payouts / total_payouts if total_payouts > 0 else 0
        }
```

### TRON Service Implementation

```python
# server/app/services/tron_service.py
import asyncio
from typing import Optional
from tronpy import Tron
from tronpy.providers import HTTPProvider
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class TronServiceError(Exception):
    """Custom exception for TRON service errors."""
    pass

class TronService:
    def __init__(self):
        self.provider = HTTPProvider(settings.TRON_NODE_URL)
        self.client = Tron(provider=self.provider)
        self.usdt_contract_address = settings.USDT_CONTRACT_ADDRESS
        self.wallet_address = settings.WALLET_ADDRESS
        self.private_key = settings.WALLET_PRIVATE_KEY
    
    def validate_address(self, address: str) -> bool:
        """Validate TRON address format."""
        try:
            return self.client.is_address(address)
        except Exception:
            return False
    
    async def get_usdt_balance(self) -> float:
        """Get USDT balance of the wallet."""
        try:
            contract = self.client.get_contract(self.usdt_contract_address)
            balance = contract.functions.balanceOf(self.wallet_address)
            return balance / 1_000_000  # USDT has 6 decimals
        except Exception as e:
            logger.error(f"Failed to get USDT balance: {str(e)}")
            raise TronServiceError(f"Balance check failed: {str(e)}")
    
    async def send_usdt(self, to_address: str, amount: float) -> str:
        """Send USDT to specified address."""
        try:
            # Validate recipient address
            if not self.validate_address(to_address):
                raise TronServiceError(f"Invalid recipient address: {to_address}")
            
            # Get contract instance
            contract = self.client.get_contract(self.usdt_contract_address)
            
            # Convert amount to contract units (6 decimals)
            amount_units = int(amount * 1_000_000)
            
            # Create transaction
            txn = contract.functions.transfer(to_address, amount_units)
            
            # Sign and broadcast transaction
            txn = txn.with_owner(self.wallet_address).fee_limit(10_000_000)
            signed_txn = txn.build().sign(self.private_key)
            result = signed_txn.broadcast()
            
            if result.get("result"):
                transaction_hash = result["txid"]
                logger.info(f"USDT transaction sent: {transaction_hash}")
                return transaction_hash
            else:
                raise TronServiceError(f"Transaction failed: {result}")
                
        except Exception as e:
            logger.error(f"Failed to send USDT: {str(e)}")
            raise TronServiceError(f"USDT transfer failed: {str(e)}")
    
    async def get_transaction_status(self, tx_hash: str) -> dict:
        """Get transaction status and confirmation count."""
        try:
            tx_info = self.client.get_transaction(tx_hash)
            
            if tx_info:
                return {
                    "confirmed": tx_info.get("ret", [{}])[0].get("contractRet") == "SUCCESS",
                    "block_number": tx_info.get("blockNumber"),
                    "timestamp": tx_info.get("timestamp")
                }
            else:
                return {"confirmed": False, "block_number": None, "timestamp": None}
                
        except Exception as e:
            logger.error(f"Failed to get transaction status: {str(e)}")
            return {"confirmed": False, "block_number": None, "timestamp": None}
```

## Integration Examples

### Webhook Implementation

```python
# server/app/webhooks/payment_webhooks.py
from fastapi import APIRouter, HTTPException, Request
from app.core.webhook_auth import verify_webhook_signature
from app.services.notification_service import NotificationService
import hmac
import hashlib
import json

router = APIRouter()

@router.post("/payment-status")
async def payment_status_webhook(request: Request):
    """Handle payment status update webhooks."""
    
    # Verify webhook signature
    signature = request.headers.get("X-Webhook-Signature")
    body = await request.body()
    
    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    data = json.loads(body)
    
    # Process webhook data
    payout_id = data.get("payout_id")
    status = data.get("status")
    transaction_hash = data.get("transaction_hash")
    
    # Update payout status in database
    await update_payout_from_webhook(payout_id, status, transaction_hash)
    
    # Send notifications if needed
    notification_service = NotificationService()
    await notification_service.send_status_notification(payout_id, status)
    
    return {"status": "success"}
```

### Database Models

```python
# server/app/models/payment.py
from sqlalchemy import Column, String, Float, DateTime, Text, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Payout(Base):
    __tablename__ = "payouts"
    
    payout_id = Column(String(36), primary_key=True)
    batch_id = Column(String(36), nullable=True)
    user_id = Column(String(36), nullable=False)
    recipient_address = Column(String(42), nullable=False)
    amount_usdt = Column(Float, nullable=False)
    reference_id = Column(String(100), nullable=False)
    metadata = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="created")
    transaction_hash = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    confirmed_at = Column(DateTime, nullable=True)

class BatchPayout(Base):
    __tablename__ = "batch_payouts"
    
    batch_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False)
    total_payouts = Column(Integer, nullable=False)
    successful_payouts = Column(Integer, default=0)
    failed_payouts = Column(Integer, default=0)
    status = Column(String(20), nullable=False, default="created")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
```

## Testing Examples

### Unit Tests

```python
# tests/test_payment_service.py
import pytest
from unittest.mock import AsyncMock, Mock
from app.services.payment_service import PaymentService
from app.services.tron_service import TronService, TronServiceError

@pytest.fixture
def mock_db():
    return Mock()

@pytest.fixture
def mock_tron_service():
    service = Mock(spec=TronService)
    service.validate_address.return_value = True
    service.get_usdt_balance.return_value = 1000.0
    service.send_usdt.return_value = "0x1234567890abcdef"
    return service

@pytest.fixture
def payment_service(mock_db, mock_tron_service):
    return PaymentService(mock_db, mock_tron_service)

@pytest.mark.asyncio
async def test_create_payout_success(payment_service, mock_db):
    """Test successful payout creation."""
    
    payout_data = {
        "payout_id": "test-123",
        "recipient_address": "TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE",
        "amount_usdt": 100.0,
        "reference_id": "REF-001",
        "metadata": {"description": "Test payment"},
        "user_id": "user-123"
    }
    
    # Mock database operations
    mock_payout = Mock()
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None
    
    result = await payment_service.create_payout(**payout_data)
    
    assert result is not None
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_process_payout_insufficient_balance(payment_service, mock_tron_service):
    """Test payout processing with insufficient balance."""
    
    mock_tron_service.get_usdt_balance.return_value = 50.0  # Less than required
    
    payout = Mock()
    payout.recipient_address = "TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE"
    payout.amount_usdt = 100.0
    
    with pytest.raises(ValueError, match="Insufficient balance"):
        await payment_service.process_payout(payout)

@pytest.mark.asyncio
async def test_process_payout_invalid_address(payment_service, mock_tron_service):
    """Test payout processing with invalid address."""
    
    mock_tron_service.validate_address.return_value = False
    
    payout = Mock()
    payout.recipient_address = "invalid-address"
    payout.amount_usdt = 100.0
    
    with pytest.raises(ValueError, match="Invalid TRON address"):
        await payment_service.process_payout(payout)
```

### Integration Tests

```python
# tests/test_integration.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}

@pytest.mark.asyncio
async def test_create_payout_integration(client, auth_headers):
    """Test complete payout creation flow."""
    
    payout_data = {
        "recipient_address": "TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE",
        "amount_usdt": 100.0,
        "reference_id": "TEST-001",
        "metadata": {"description": "Integration test"}
    }
    
    response = await client.post(
        "/api/v1/payouts",
        json=payout_data,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "payout_id" in data
    assert data["status"] == "pending"
    assert "transaction_hash" in data

@pytest.mark.asyncio
async def test_get_payout_status_integration(client, auth_headers):
    """Test payout status retrieval."""
    
    # First create a payout
    payout_data = {
        "recipient_address": "TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE",
        "amount_usdt": 50.0,
        "reference_id": "TEST-002"
    }
    
    create_response = await client.post(
        "/api/v1/payouts",
        json=payout_data,
        headers=auth_headers
    )
    
    payout_id = create_response.json()["payout_id"]
    
    # Then get its status
    status_response = await client.get(
        f"/api/v1/payouts/{payout_id}",
        headers=auth_headers
    )
    
    assert status_response.status_code == 200
    data = status_response.json()
    assert data["payout_id"] == payout_id
    assert "status" in data
```

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-XX  
**Next Review**: 2024-04-XX
