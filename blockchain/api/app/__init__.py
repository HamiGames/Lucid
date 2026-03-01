"""
Blockchain API Application Package

This package contains the complete Blockchain API implementation.
Implements the OpenAPI 3.0 specification for the lucid_blocks blockchain system.

Features:
- FastAPI application with OpenAPI documentation
- Authentication and authorization middleware
- Rate limiting and request logging
- Complete blockchain API endpoints
- Service layer for business logic
- Pydantic models for request/response validation
- Comprehensive monitoring and metrics
- Health checks and system monitoring
- Security utilities and validation
- Database and cache management
- Structured logging and error handling

Architecture:
- Clean separation of concerns
- Modular design with clear interfaces
- Comprehensive error handling
- Security-first approach
- Performance monitoring
- Scalable and maintainable code
"""

__version__ = "1.0.0"
__author__ = "Lucid Blockchain Team"
__description__ = "API for the lucid_blocks blockchain system with PoOT consensus"
__license__ = "Proprietary"

# Import main application components
from .main import app
from .config import settings, get_settings
from .dependencies import get_current_user, verify_api_key, require_permission
from .services import (
    BlockchainService, BlockService, TransactionService,
    AnchoringService, ConsensusService, MerkleService
)
from .schemas import (
    BlockchainInfo, BlockchainStatus, BlockDetails, TransactionDetails,
    SessionAnchoringRequest, ConsensusStatus, MerkleTreeResponse
)

# Import utilities
from .utils import (
    generate_hash, validate_hex_string, validate_uuid,
    format_timestamp, calculate_merkle_root, validate_merkle_proof
)

# Import security utilities
from .security import SecurityManager

# Import monitoring components
from .monitoring import metrics_collector, health_checker, performance_monitor
from .health_check import health_check_service
from .metrics import metrics_service, api_metrics, blockchain_metrics, system_metrics

# Import logging
from .logging_config import setup_logging, get_logger

# Import database and cache
from .database import init_database, close_database, get_database, get_collection
from .cache import init_cache, close_cache, get_cache

# Import error handling
from .errors import (
    BlockchainException, BlockNotFoundException, TransactionNotFoundException,
    SessionAnchoringException, ConsensusVoteException, MerkleTreeException
)

# Import rate limiting
from .rate_limiter import rate_limiter_manager, RateLimitMiddleware

__all__ = [
    # Main application
    "app", "settings", "get_settings",
    
    # Dependencies
    "get_current_user", "verify_api_key", "require_permission",
    
    # Services
    "BlockchainService", "BlockService", "TransactionService",
    "AnchoringService", "ConsensusService", "MerkleService",
    
    # Schemas
    "BlockchainInfo", "BlockchainStatus", "BlockDetails", "TransactionDetails",
    "SessionAnchoringRequest", "ConsensusStatus", "MerkleTreeResponse",
    
    # Utilities
    "generate_hash", "validate_hex_string", "validate_uuid",
    "format_timestamp", "calculate_merkle_root", "validate_merkle_proof",
    
    # Security
    "SecurityManager",
    
    # Monitoring
    "metrics_collector", "health_checker", "performance_monitor",
    "health_check_service", "metrics_service", "api_metrics", "blockchain_metrics", "system_metrics",
    
    # Logging
    "setup_logging", "get_logger",
    
    # Database and cache
    "init_database", "close_database", "get_database", "get_collection",
    "init_cache", "close_cache", "get_cache",
    
    # Error handling
    "BlockchainException", "BlockNotFoundException", "TransactionNotFoundException",
    "SessionAnchoringException", "ConsensusVoteException", "MerkleTreeException",
    
    # Rate limiting
    "rate_limiter_manager", "RateLimitMiddleware"
]