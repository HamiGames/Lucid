"""
Routes Registration

This module registers all API routers with the FastAPI application.
Implements the OpenAPI 3.0 specification for all endpoints.
"""

from fastapi import FastAPI
from .routers import blockchain, blocks, transactions, anchoring, consensus, merkle, monitoring

def register_routes(app: FastAPI):
    """
    Registers all API routers with the FastAPI application.
    
    This function sets up all the API endpoints according to the OpenAPI 3.0 specification:
    - Blockchain information endpoints
    - Block management endpoints
    - Transaction processing endpoints
    - Session anchoring endpoints
    - Consensus mechanism endpoints
    - Merkle tree operation endpoints
    - Monitoring and metrics endpoints
    """
    
    # Register blockchain information endpoints
    app.include_router(blockchain.router, prefix="/api/v1")
    
    # Register block management endpoints
    app.include_router(blocks.router, prefix="/api/v1")
    
    # Register transaction processing endpoints
    app.include_router(transactions.router, prefix="/api/v1")
    
    # Register session anchoring endpoints
    app.include_router(anchoring.router, prefix="/api/v1")
    
    # Register consensus mechanism endpoints
    app.include_router(consensus.router, prefix="/api/v1")
    
    # Register Merkle tree operation endpoints
    app.include_router(merkle.router, prefix="/api/v1")
    
    # Register monitoring and metrics endpoints
    app.include_router(monitoring.router, prefix="/api/v1")
    
    # Register additional health check endpoints
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Basic health check endpoint."""
        return {"status": "healthy", "service": "lucid-blockchain-api"}
    
    @app.get("/api/v1/health", tags=["Health"])
    async def api_health_check():
        """API health check endpoint."""
        return {
            "status": "healthy",
            "service": "lucid-blockchain-api",
            "version": "1.0.0"
        }