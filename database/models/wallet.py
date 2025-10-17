"""
Wallet Data Models

Pydantic models for wallet entities in the Lucid system.
Handles wallet information, hardware wallets, and TRON addresses.

Database Collection: wallets (or part of users collection)
Phase: Phase 1 - Foundation
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class WalletType(str, Enum):
    """Wallet type enumeration"""
    SOFTWARE = "software"
    HARDWARE = "hardware"
    PAPER = "paper"
    MULTISIG = "multisig"


class WalletStatus(str, Enum):
    """Wallet status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    COMPROMISED = "compromised"


class HardwareWalletType(str, Enum):
    """Hardware wallet type enumeration"""
    LEDGER = "ledger"
    TREZOR = "trezor"
    KEEPKEY = "keepkey"
    OTHER = "other"


class HardwareWalletModel(BaseModel):
    """Hardware wallet model information"""
    type: HardwareWalletType = Field(..., description="Hardware wallet type")
    model: str = Field(..., description="Specific model name")
    firmware_version: Optional[str] = Field(None, description="Firmware version")
    app_version: Optional[str] = Field(None, description="App version")
    
    class Config:
        use_enum_values = True


class WalletBase(BaseModel):
    """Base wallet model with common fields"""
    wallet_type: WalletType = Field(..., description="Wallet type")
    tron_address: str = Field(..., description="TRON wallet address")
    status: WalletStatus = Field(default=WalletStatus.ACTIVE, description="Wallet status")
    
    @validator('tron_address')
    def validate_tron_address(cls, v):
        """Validate TRON address format"""
        if not v.startswith('T') or len(v) != 34:
            raise ValueError('Invalid TRON address format')
        return v
    
    class Config:
        use_enum_values = True


class WalletCreate(WalletBase):
    """Model for creating a new wallet"""
    user_id: str = Field(..., description="Owner user ID")
    nickname: Optional[str] = Field(None, max_length=100, description="Wallet nickname")
    public_key: Optional[str] = Field(None, description="Public key")
    hardware_wallet: Optional[HardwareWalletModel] = Field(None, description="Hardware wallet info")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class WalletUpdate(BaseModel):
    """Model for updating wallet information"""
    nickname: Optional[str] = Field(None, max_length=100)
    status: Optional[WalletStatus] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        use_enum_values = True


class Wallet(WalletBase):
    """Wallet model for API responses"""
    wallet_id: str = Field(..., description="Unique wallet identifier")
    user_id: str = Field(..., description="Owner user ID")
    
    # Wallet details
    nickname: Optional[str] = Field(None, description="Wallet nickname")
    public_key: Optional[str] = Field(None, description="Public key")
    
    # Hardware wallet information (if applicable)
    hardware_wallet: Optional[HardwareWalletModel] = Field(None, description="Hardware wallet info")
    
    # Wallet status
    is_primary: bool = Field(default=False, description="Whether this is the primary wallet")
    is_verified: bool = Field(default=False, description="Whether address is verified")
    verified_at: Optional[datetime] = Field(None, description="Verification timestamp")
    
    # Usage statistics
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")
    transaction_count: int = Field(default=0, ge=0, description="Number of transactions")
    
    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    tags: List[str] = Field(default_factory=list, description="Wallet tags")
    
    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class WalletInDB(Wallet):
    """Wallet model as stored in database (includes sensitive fields)"""
    
    # Private key storage (encrypted)
    encrypted_private_key: Optional[str] = Field(None, description="Encrypted private key")
    encryption_method: Optional[str] = Field(None, description="Encryption method used")
    key_derivation_path: Optional[str] = Field(None, description="HD wallet derivation path")
    
    # Signature information
    last_signature: Optional[str] = Field(None, description="Last signature created")
    signature_count: int = Field(default=0, description="Total signatures created")
    
    # Security fields
    last_backup: Optional[datetime] = Field(None, description="Last backup timestamp")
    backup_verified: bool = Field(default=False, description="Whether backup is verified")
    
    # Hardware wallet connection state
    hardware_connected: bool = Field(default=False, description="Whether hardware wallet is connected")
    last_connected: Optional[datetime] = Field(None, description="Last connection timestamp")
    connection_failures: int = Field(default=0, description="Connection failure count")
    
    # Audit fields
    created_by: Optional[str] = Field(None, description="User ID that created wallet")
    updated_by: Optional[str] = Field(None, description="User ID that last updated wallet")
    deleted_at: Optional[datetime] = Field(None, description="Soft delete timestamp")
    
    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class HardwareWallet(BaseModel):
    """Hardware wallet entity"""
    device_id: str = Field(..., description="Hardware device identifier")
    wallet_type: HardwareWalletType = Field(..., description="Hardware wallet type")
    model: str = Field(..., description="Device model")
    
    # Device information
    firmware_version: str = Field(..., description="Firmware version")
    app_version: Optional[str] = Field(None, description="TRON app version")
    serial_number: Optional[str] = Field(None, description="Device serial number")
    
    # Connection state
    connected: bool = Field(default=False, description="Whether device is connected")
    last_connected: Optional[datetime] = Field(None, description="Last connection timestamp")
    
    # Associated wallet
    tron_address: Optional[str] = Field(None, description="Associated TRON address")
    derivation_path: Optional[str] = Field(None, description="Derivation path")
    
    # Device status
    initialized: bool = Field(default=False, description="Whether device is initialized")
    pin_protected: bool = Field(default=False, description="Whether PIN protection is enabled")
    passphrase_protected: bool = Field(default=False, description="Whether passphrase is required")
    
    # Usage information
    user_id: Optional[str] = Field(None, description="Associated user ID")
    first_connected: datetime = Field(..., description="First connection timestamp")
    transaction_count: int = Field(default=0, description="Number of transactions signed")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class WalletBalance(BaseModel):
    """Wallet balance information (for display purposes)"""
    wallet_id: str = Field(..., description="Wallet identifier")
    tron_address: str = Field(..., description="TRON address")
    
    # TRX balance
    trx_balance: float = Field(default=0.0, description="TRX balance")
    trx_balance_frozen: float = Field(default=0.0, description="Frozen TRX balance")
    
    # USDT balance
    usdt_balance: float = Field(default=0.0, description="USDT-TRC20 balance")
    
    # Energy and bandwidth
    energy_available: int = Field(default=0, description="Available energy")
    energy_limit: int = Field(default=0, description="Energy limit")
    bandwidth_available: int = Field(default=0, description="Available bandwidth")
    bandwidth_limit: int = Field(default=0, description="Bandwidth limit")
    
    # Timestamp
    last_updated: datetime = Field(..., description="Last balance update timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class WalletTransaction(BaseModel):
    """Wallet transaction record (TRON network)"""
    transaction_id: str = Field(..., description="Transaction hash")
    wallet_id: str = Field(..., description="Wallet identifier")
    tron_address: str = Field(..., description="Wallet address")
    
    # Transaction details
    transaction_type: str = Field(..., description="Transaction type")
    direction: str = Field(..., description="Direction (incoming, outgoing)")
    amount: float = Field(..., description="Transaction amount")
    currency: str = Field(..., description="Currency (TRX, USDT)")
    
    # Counterparty
    from_address: str = Field(..., description="Sender address")
    to_address: str = Field(..., description="Recipient address")
    
    # Status
    status: str = Field(..., description="Transaction status")
    confirmations: int = Field(default=0, description="Number of confirmations")
    
    # Blockchain information
    block_number: Optional[int] = Field(None, description="Block number")
    block_timestamp: Optional[datetime] = Field(None, description="Block timestamp")
    
    # Fees
    fee_trx: float = Field(default=0.0, description="Transaction fee in TRX")
    energy_used: int = Field(default=0, description="Energy consumed")
    bandwidth_used: int = Field(default=0, description="Bandwidth consumed")
    
    # Timestamp
    created_at: datetime = Field(..., description="Transaction creation timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class WalletStatistics(BaseModel):
    """Wallet statistics and metrics"""
    wallet_id: str = Field(..., description="Wallet identifier")
    user_id: str = Field(..., description="User identifier")
    
    # Usage metrics
    total_transactions: int = Field(..., description="Total number of transactions")
    total_signatures: int = Field(..., description="Total signatures created")
    days_active: int = Field(..., description="Days wallet has been active")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")
    
    # Transaction metrics (TRON)
    total_sent_trx: float = Field(default=0.0, description="Total TRX sent")
    total_received_trx: float = Field(default=0.0, description="Total TRX received")
    total_sent_usdt: float = Field(default=0.0, description="Total USDT sent")
    total_received_usdt: float = Field(default=0.0, description="Total USDT received")
    
    # Fees spent
    total_fees_trx: float = Field(default=0.0, description="Total fees paid in TRX")
    total_energy_used: int = Field(default=0, description="Total energy consumed")
    total_bandwidth_used: int = Field(default=0, description="Total bandwidth consumed")
    
    # Current balance
    current_trx_balance: float = Field(default=0.0, description="Current TRX balance")
    current_usdt_balance: float = Field(default=0.0, description="Current USDT balance")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

