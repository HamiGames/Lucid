"""
Routers Package

This package contains all API route handlers for the Blockchain API.
Implements the OpenAPI 3.0 specification for all endpoints.

Modules:
- blockchain: Blockchain information and status endpoints
- blocks: Block management and validation endpoints
- transactions: Transaction processing endpoints
- anchoring: Session anchoring endpoints
- consensus: Consensus mechanism endpoints
- merkle: Merkle tree operation endpoints
- monitoring: Monitoring and metrics endpoints
"""

from . import blockchain, blocks, transactions, anchoring, consensus, merkle, monitoring

__all__ = [
    "blockchain",
    "blocks", 
    "transactions",
    "anchoring",
    "consensus",
    "merkle",
    "monitoring"
]