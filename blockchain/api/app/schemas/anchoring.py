"""
Anchoring Schema Models

This module defines Pydantic models for session anchoring API endpoints.
Implements the OpenAPI 3.0 specification for session manifest anchoring.

Models:
- SessionAnchoringRequest: Session anchoring request
- SessionAnchoringResponse: Session anchoring response
- SessionAnchoringStatus: Session anchoring status
- AnchoringVerificationRequest: Anchoring verification request
- AnchoringVerificationResponse: Anchoring verification response
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class SessionAnchoringRequest(BaseModel):
    """Request for anchoring a session manifest to the blockchain."""
    session_id: str = Field(..., description="Session UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
    manifest_data: Dict[str, Any] = Field(..., description="Session manifest data")
    merkle_root: str = Field(..., description="Merkle tree root hash", pattern=r'^[a-fA-F0-9]{64}$')
    user_signature: Optional[str] = Field(None, description="User signature for the session")


class SessionAnchoringResponse(BaseModel):
    """Response after initiating session anchoring."""
    anchoring_id: str = Field(..., description="Unique anchoring ID")
    status: str = Field(..., description="Anchoring status", enum=["pending", "processing", "confirmed", "failed"])
    submitted_at: datetime = Field(..., description="Anchoring submission timestamp")
    estimated_confirmation_time: Optional[datetime] = Field(None, description="Estimated confirmation time")


class SessionAnchoringStatus(BaseModel):
    """Current status of session anchoring."""
    session_id: str = Field(..., description="Session UUID")
    anchoring_id: str = Field(..., description="Unique anchoring ID")
    status: str = Field(..., description="Anchoring status", enum=["pending", "processing", "confirmed", "failed"])
    submitted_at: datetime = Field(..., description="Anchoring submission timestamp")
    confirmed_at: Optional[datetime] = Field(None, description="Anchoring confirmation timestamp")
    block_height: Optional[int] = Field(None, description="Block height where session was anchored")
    transaction_id: Optional[str] = Field(None, description="Transaction ID of the anchoring")
    merkle_root: str = Field(..., description="Merkle tree root hash")


class AnchoringVerificationRequest(BaseModel):
    """Request for verifying session anchoring."""
    session_id: str = Field(..., description="Session UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
    merkle_root: str = Field(..., description="Merkle tree root hash", pattern=r'^[a-fA-F0-9]{64}$')


class AnchoringVerificationResponse(BaseModel):
    """Response containing anchoring verification results."""
    verified: bool = Field(..., description="Whether the anchoring is verified")
    block_height: Optional[int] = Field(None, description="Block height where session was anchored")
    transaction_id: Optional[str] = Field(None, description="Transaction ID of the anchoring")
    confirmation_time: Optional[datetime] = Field(None, description="Anchoring confirmation timestamp")
    merkle_proof_valid: bool = Field(..., description="Whether the Merkle proof is valid")


class AnchoringServiceStatus(BaseModel):
    """Status of the anchoring service."""
    status: str = Field(..., description="Service status", enum=["healthy", "busy", "error"])
    pending_anchorings: int = Field(..., description="Number of pending anchoring requests")
    processing_anchorings: int = Field(..., description="Number of processing anchoring requests")
    completed_today: int = Field(..., description="Number of completed anchorings today")
    average_confirmation_time: float = Field(..., description="Average confirmation time in seconds")
