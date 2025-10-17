"""
Common Data Models
Shared Pydantic models used across blockchain API components.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Generic, TypeVar
from enum import Enum
from pydantic import BaseModel, Field, validator
from pydantic.generics import GenericModel

T = TypeVar('T')


class NetworkStatus(str, Enum):
    """Network status enumeration."""
    ACTIVE = "active"
    SYNCING = "syncing"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    OFFLINE = "offline"


class ChainInfo(BaseModel):
    """Information about the blockchain."""
    
    network: str = Field(..., description="Network name (e.g., lucid_blocks)")
    chain_id: str = Field(..., description="Chain identifier")
    latest_block_height: int = Field(..., ge=0, description="Height of latest block")
    latest_block_hash: str = Field(..., description="Hash of latest block")
    chain_length: int = Field(..., ge=0, description="Total number of blocks")
    consensus_algorithm: str = Field(..., description="Consensus algorithm (e.g., PoOT)")
    block_time_seconds: int = Field(..., ge=1, description="Target block time")
    status: NetworkStatus = Field(..., description="Current network status")
    timestamp: datetime = Field(..., description="Information timestamp")
    
    @validator('latest_block_hash')
    def validate_block_hash(cls, v):
        if not isinstance(v, str) or len(v) != 64:
            raise ValueError('Block hash must be a 64-character hexadecimal string')
        try:
            int(v, 16)
        except ValueError:
            raise ValueError('Block hash must be a valid hexadecimal string')
        return v.lower()
        
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PaginationParams(BaseModel):
    """Parameters for paginated requests."""
    
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")
    order_by: str = Field(default="timestamp", description="Field to order by")
    order_direction: str = Field(default="desc", description="Order direction (asc/desc)")
    
    @validator('order_direction')
    def validate_order_direction(cls, v):
        if v.lower() not in ['asc', 'desc']:
            raise ValueError('Order direction must be "asc" or "desc"')
        return v.lower()


class PaginatedResponse(GenericModel, Generic[T]):
    """Generic paginated response."""
    
    items: List[T] = Field(..., description="List of items")
    total_count: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")
    
    def __init__(self, **data):
        super().__init__(**data)
        # Calculate has_next and has_previous
        self.has_next = self.page < self.total_pages
        self.has_previous = self.page > 1


class ChunkMetadata(BaseModel):
    """Metadata for a session chunk."""
    
    chunk_id: str = Field(..., description="Unique chunk identifier")
    hash: str = Field(..., description="Chunk hash (SHA-256)")
    size_bytes: int = Field(..., ge=0, description="Chunk size in bytes")
    index: int = Field(..., ge=0, description="Chunk index in session")
    compression: Optional[str] = Field(None, description="Compression algorithm used")
    encryption: Optional[str] = Field(None, description="Encryption algorithm used")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Chunk creation time")
    
    @validator('hash')
    def validate_hash_format(cls, v):
        if not isinstance(v, str) or len(v) != 64:
            raise ValueError('Chunk hash must be a 64-character hexadecimal string')
        try:
            int(v, 16)
        except ValueError:
            raise ValueError('Chunk hash must be a valid hexadecimal string')
        return v.lower()
        
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SessionManifest(BaseModel):
    """Manifest describing a complete session."""
    
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="ID of session owner")
    chunks: List[ChunkMetadata] = Field(..., description="List of session chunks")
    total_size_bytes: int = Field(..., ge=0, description="Total session size")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation time")
    completed_at: Optional[datetime] = Field(None, description="Session completion time")
    
    # Session metadata
    duration_seconds: Optional[float] = Field(None, ge=0, description="Session duration")
    compression_ratio: Optional[float] = Field(None, ge=0, description="Compression ratio achieved")
    encryption_enabled: bool = Field(default=True, description="Whether encryption was used")
    
    @validator('chunks')
    def validate_chunks(cls, v):
        if not v:
            raise ValueError('Session must have at least one chunk')
        
        # Validate chunk indices are sequential
        expected_indices = set(range(len(v)))
        actual_indices = {chunk.index for chunk in v}
        if expected_indices != actual_indices:
            raise ValueError('Chunk indices must be sequential starting from 0')
            
        return v
        
    @property
    def chunk_count(self) -> int:
        """Get the number of chunks in the session."""
        return len(self.chunks)
        
    def get_chunk_hashes(self) -> List[str]:
        """Get list of all chunk hashes in order."""
        return [chunk.hash for chunk in sorted(self.chunks, key=lambda c: c.index)]
        
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HealthCheckResult(BaseModel):
    """Result of a health check operation."""
    
    healthy: bool = Field(..., description="Overall health status")
    service: str = Field(..., description="Service name")
    version: Optional[str] = Field(None, description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    
    # Component health details
    components: Dict[str, bool] = Field(default_factory=dict, description="Component health status")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Health metrics")
    errors: List[str] = Field(default_factory=list, description="Health check errors")
    warnings: List[str] = Field(default_factory=list, description="Health check warnings")
    
    # Performance metrics
    response_time_ms: Optional[float] = Field(None, ge=0, description="Response time in milliseconds")
    uptime_seconds: Optional[float] = Field(None, ge=0, description="Service uptime in seconds")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseModel):
    """Standard error response format."""
    
    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request identifier for tracking")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SuccessResponse(BaseModel):
    """Standard success response format."""
    
    success: bool = Field(True, description="Success indicator")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class APIVersion(BaseModel):
    """API version information."""
    
    version: str = Field(..., description="API version (e.g., v1)")
    build: Optional[str] = Field(None, description="Build identifier")
    commit: Optional[str] = Field(None, description="Git commit hash")
    build_date: Optional[datetime] = Field(None, description="Build date")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ServiceInfo(BaseModel):
    """Information about a service."""
    
    name: str = Field(..., description="Service name")
    version: APIVersion = Field(..., description="Version information")
    status: NetworkStatus = Field(..., description="Service status")
    description: Optional[str] = Field(None, description="Service description")
    endpoints: List[str] = Field(default_factory=list, description="Available endpoints")
    dependencies: List[str] = Field(default_factory=list, description="Service dependencies")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Service start time")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RateLimitInfo(BaseModel):
    """Rate limiting information."""
    
    limit: int = Field(..., ge=0, description="Rate limit (requests per window)")
    remaining: int = Field(..., ge=0, description="Remaining requests in current window")
    reset_time: datetime = Field(..., description="When the rate limit resets")
    window_seconds: int = Field(..., ge=1, description="Rate limit window in seconds")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SearchRequest(BaseModel):
    """Generic search request."""
    
    query: str = Field(..., min_length=1, description="Search query")
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")
    pagination: PaginationParams = Field(default_factory=PaginationParams, description="Pagination parameters")
    
    @validator('query')
    def validate_query(cls, v):
        # Basic query validation
        if len(v.strip()) == 0:
            raise ValueError('Query cannot be empty or whitespace only')
        return v.strip()


class SearchResponse(GenericModel, Generic[T]):
    """Generic search response."""
    
    results: List[T] = Field(..., description="Search results")
    total_count: int = Field(..., ge=0, description="Total number of results")
    query: str = Field(..., description="Original search query")
    search_time_ms: float = Field(..., ge=0, description="Search execution time")
    pagination: PaginationParams = Field(..., description="Pagination used")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
