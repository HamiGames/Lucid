"""
LUCID Payment Systems - TRON Wallet Models
Wallet data models for TRON payment operations
Distroless container: lucid-tron-payment-service:latest
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

class WalletStatus(str, Enum):
    """Wallet status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    ARCHIVED = "archived"

class WalletCreateRequest(BaseModel):
    """Wallet creation request"""
    name: str = Field(..., description="Wallet name", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Wallet description", max_length=500)
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Wallet name cannot be empty')
        return v.strip()

class WalletUpdateRequest(BaseModel):
    """Wallet update request"""
    name: Optional[str] = Field(None, description="Wallet name", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Wallet description", max_length=500)
    status: Optional[WalletStatus] = Field(None, description="Wallet status")
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Wallet name cannot be empty')
        return v.strip() if v else v

class WalletResponse(BaseModel):
    """Wallet response model"""
    wallet_id: str = Field(..., description="Unique wallet identifier")
    name: str = Field(..., description="Wallet name")
    description: Optional[str] = Field(None, description="Wallet description")
    address: str = Field(..., description="TRON address")
    status: str = Field(..., description="Wallet status")
    balance_trx: float = Field(..., description="TRX balance")
    created_at: str = Field(..., description="Creation timestamp")
    last_updated: str = Field(..., description="Last update timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "wallet_id": "abc123def456",
                "name": "My TRON Wallet",
                "description": "Primary wallet for payments",
                "address": "TYourTRONAddressHere123456789",
                "status": "active",
                "balance_trx": 1000.0,
                "created_at": "2025-01-10T19:08:00Z",
                "last_updated": "2025-01-10T19:08:00Z"
            }
        }

class WalletBalance(BaseModel):
    """Wallet balance model"""
    wallet_id: str = Field(..., description="Wallet ID")
    address: str = Field(..., description="TRON address")
    balance_trx: float = Field(..., description="TRX balance")
    balance_sun: int = Field(..., description="Balance in SUN (1 TRX = 1,000,000 SUN)")
    energy_available: int = Field(..., description="Available energy")
    bandwidth_available: int = Field(..., description="Available bandwidth")
    frozen_balance: float = Field(..., description="Frozen balance")
    delegated_energy: int = Field(..., description="Delegated energy")
    delegated_bandwidth: int = Field(..., description="Delegated bandwidth")
    last_updated: str = Field(..., description="Last update timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "wallet_id": "abc123def456",
                "address": "TYourTRONAddressHere123456789",
                "balance_trx": 1000.0,
                "balance_sun": 1000000000,
                "energy_available": 50000,
                "bandwidth_available": 100000,
                "frozen_balance": 100.0,
                "delegated_energy": 0,
                "delegated_bandwidth": 0,
                "last_updated": "2025-01-10T19:08:00Z"
            }
        }

class WalletTransaction(BaseModel):
    """Wallet transaction model"""
    transaction_id: str = Field(..., description="Transaction ID")
    wallet_id: str = Field(..., description="Wallet ID")
    txid: str = Field(..., description="TRON transaction ID")
    from_address: str = Field(..., description="Sender address")
    to_address: str = Field(..., description="Recipient address")
    amount: float = Field(..., description="Transaction amount")
    currency: str = Field(..., description="Currency (TRX, USDT)")
    fee: float = Field(..., description="Transaction fee")
    status: str = Field(..., description="Transaction status")
    block_number: int = Field(..., description="Block number")
    timestamp: int = Field(..., description="Transaction timestamp")
    created_at: str = Field(..., description="Creation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "tx_abc123def456",
                "wallet_id": "abc123def456",
                "txid": "abc123def456789012345678901234567890123456789012345678901234567890",
                "from_address": "TFromAddress1234567890123456789012345",
                "to_address": "TToAddress1234567890123456789012345",
                "amount": 100.0,
                "currency": "TRX",
                "fee": 1.0,
                "status": "SUCCESS",
                "block_number": 12345678,
                "timestamp": 1641234567890,
                "created_at": "2025-01-10T19:08:00Z"
            }
        }

class WalletStats(BaseModel):
    """Wallet statistics model"""
    wallet_id: str = Field(..., description="Wallet ID")
    total_transactions: int = Field(..., description="Total transactions")
    total_sent: float = Field(..., description="Total amount sent")
    total_received: float = Field(..., description="Total amount received")
    average_transaction: float = Field(..., description="Average transaction amount")
    last_transaction: Optional[str] = Field(None, description="Last transaction timestamp")
    created_at: str = Field(..., description="Wallet creation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "wallet_id": "abc123def456",
                "total_transactions": 150,
                "total_sent": 5000.0,
                "total_received": 7500.0,
                "average_transaction": 50.0,
                "last_transaction": "2025-01-10T19:08:00Z",
                "created_at": "2025-01-01T00:00:00Z"
            }
        }

class WalletSignRequest(BaseModel):
    """Wallet sign request model"""
    data: Optional[str] = Field(None, description="Data to sign (hex string) - required for data_sign type")
    password: str = Field(..., description="Wallet password for decryption", min_length=1)
    message: Optional[str] = Field(None, description="Human readable message")
    transaction_type: str = Field("data_sign", description="Transaction type: data_sign or trx_transfer")
    to_address: Optional[str] = Field(None, description="Recipient address (required for trx_transfer)")
    amount: Optional[float] = Field(None, description="Amount in TRX (required for trx_transfer)")

class WalletSignResponse(BaseModel):
    """Wallet sign response model"""
    wallet_id: str = Field(..., description="Wallet ID")
    signature: Optional[str] = Field(None, description="Transaction signature")
    txid: Optional[str] = Field(None, description="Transaction ID (for transfers)")
    signed_transaction: Optional[Dict[str, Any]] = Field(None, description="Signed transaction data")
    public_key: Optional[str] = Field(None, description="Public key")
    message_hash: Optional[str] = Field(None, description="Message hash")
    timestamp: str = Field(..., description="Signing timestamp")

class WalletImportRequest(BaseModel):
    """Wallet import request model"""
    private_key: str = Field(..., description="Private key in hex format (64 characters)")
    name: str = Field(..., description="Wallet name", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Wallet description", max_length=500)

class WalletExportResponse(BaseModel):
    """Wallet export response model"""
    wallet: Dict[str, Any] = Field(..., description="Wallet data")
    exported_at: str = Field(..., description="Export timestamp")
    note: str = Field(..., description="Export note")

class PasswordVerifyRequest(BaseModel):
    """Password verification request model"""
    password: str = Field(..., description="Password to verify", min_length=1)
