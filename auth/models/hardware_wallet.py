"""
Lucid Authentication Service - Hardware Wallet Model
Supports Ledger, Trezor, and KeepKey
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class HardwareWalletType(str, Enum):
    """Supported hardware wallet types"""
    LEDGER = "ledger"
    TREZOR = "trezor"
    KEEPKEY = "keepkey"


class HardwareWalletStatus(str, Enum):
    """Hardware wallet connection status"""
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    ERROR = "error"


class HardwareWallet(BaseModel):
    """Hardware wallet model"""
    
    wallet_id: str = Field(..., description="Wallet identifier")
    user_id: str = Field(..., description="User ID")
    wallet_type: HardwareWalletType = Field(..., description="Wallet type")
    
    # Device information
    device_id: Optional[str] = Field(None, description="Device identifier")
    device_model: Optional[str] = Field(None, description="Device model")
    firmware_version: Optional[str] = Field(None, description="Firmware version")
    
    # Derivation path
    derivation_path: str = Field(default="m/44'/195'/0'/0/0", description="BIP44 derivation path")
    
    # TRON address
    tron_address: Optional[str] = Field(None, description="TRON address")
    public_key: Optional[str] = Field(None, description="Public key")
    
    # Status
    status: HardwareWalletStatus = Field(default=HardwareWalletStatus.DISCONNECTED, description="Connection status")
    last_connected_at: Optional[datetime] = Field(None, description="Last connection time")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "wallet_id": "hw_1234567890abcdef",
                "user_id": "usr_1234567890abcdef",
                "wallet_type": "ledger",
                "device_id": "ledger_nano_s_001",
                "device_model": "Nano S",
                "firmware_version": "2.1.0",
                "derivation_path": "m/44'/195'/0'/0/0",
                "tron_address": "TXYZPvGUMN8cXPFQtPqrQjBBVSFQwgFQ1v",
                "status": "connected",
                "created_at": "2025-01-01T00:00:00Z"
            }
        }


class HardwareWalletConnect(BaseModel):
    """Hardware wallet connection request"""
    
    wallet_type: HardwareWalletType = Field(..., description="Wallet type")
    derivation_path: Optional[str] = Field("m/44'/195'/0'/0/0", description="Derivation path")
    
    class Config:
        json_schema_extra = {
            "example": {
                "wallet_type": "ledger",
                "derivation_path": "m/44'/195'/0'/0/0"
            }
        }


class HardwareWalletConnectResponse(BaseModel):
    """Hardware wallet connection response"""
    
    wallet_id: str
    wallet_type: str
    tron_address: str
    public_key: str
    device_model: Optional[str] = None
    firmware_version: Optional[str] = None
    status: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "wallet_id": "hw_1234567890abcdef",
                "wallet_type": "ledger",
                "tron_address": "TXYZPvGUMN8cXPFQtPqrQjBBVSFQwgFQ1v",
                "public_key": "0x04...",
                "device_model": "Nano S",
                "firmware_version": "2.1.0",
                "status": "connected"
            }
        }


class HardwareWalletSign(BaseModel):
    """Hardware wallet sign request"""
    
    wallet_id: str = Field(..., description="Wallet ID")
    message: str = Field(..., description="Message to sign")
    derivation_path: Optional[str] = Field(None, description="Derivation path")
    
    class Config:
        json_schema_extra = {
            "example": {
                "wallet_id": "hw_1234567890abcdef",
                "message": "Sign this message to authenticate with Lucid: 2025-01-01T00:00:00Z",
                "derivation_path": "m/44'/195'/0'/0/0"
            }
        }


class HardwareWalletSignResponse(BaseModel):
    """Hardware wallet sign response"""
    
    signature: str = Field(..., description="Signature")
    message: str = Field(..., description="Signed message")
    tron_address: str = Field(..., description="TRON address")
    
    class Config:
        json_schema_extra = {
            "example": {
                "signature": "0x1234567890abcdef...",
                "message": "Sign this message to authenticate with Lucid: 2025-01-01T00:00:00Z",
                "tron_address": "TXYZPvGUMN8cXPFQtPqrQjBBVSFQwgFQ1v"
            }
        }


class HardwareWalletStatusResponse(BaseModel):
    """Hardware wallet status response"""
    
    wallet_id: str
    wallet_type: str
    status: str
    tron_address: Optional[str] = None
    device_model: Optional[str] = None
    last_connected_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "wallet_id": "hw_1234567890abcdef",
                "wallet_type": "ledger",
                "status": "connected",
                "tron_address": "TXYZPvGUMN8cXPFQtPqrQjBBVSFQwgFQ1v",
                "device_model": "Nano S",
                "last_connected_at": "2025-01-01T00:00:00Z"
            }
        }

