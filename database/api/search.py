"""
Database Search API

Provides Elasticsearch search endpoints:
- Full-text search across indexed documents
- Search sessions
- Search blocks  
- Search transactions
- Search manifests
- Aggregations and analytics

Port: 8088 (Storage-Database Cluster)
Phase: Phase 1 - Foundation
"""

from fastapi import APIRouter, HTTPException, Query, Body, status
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from ..services.elasticsearch_service import ElasticsearchService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/database/search",
    tags=["database-search"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

# Service instance
elasticsearch_service: ElasticsearchService = None


def init_service(elasticsearch: ElasticsearchService):
    """Initialize Elasticsearch service instance"""
    global elasticsearch_service
    elasticsearch_service = elasticsearch


# Request/Response Models
class SearchRequest(BaseModel):
    """Request model for search operations"""
    query: str = Field(..., description="Search query string")
    index: Optional[str] = Field(None, description="Specific index to search (default: all lucid indices)")
    fields: Optional[List[str]] = Field(None, description="Specific fields to search in")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")
    size: int = Field(10, ge=1, le=1000, description="Number of results to return")
    from_: int = Field(0, ge=0, alias="from", description="Offset for pagination")
    sort: Optional[List[Dict[str, str]]] = Field(None, description="Sort specification")


class AggregationRequest(BaseModel):
    """Request model for aggregations"""
    index: str = Field(..., description="Index name")
    aggregations: Dict[str, Any] = Field(..., description="Aggregation specification")
    query: Optional[Dict[str, Any]] = Field(None, description="Optional query filter")


@router.post("/", response_model=Dict[str, Any])
async def search(request: SearchRequest):
    """
    Perform a full-text search across indexed documents
    
    Args:
        request: Search request
        
    Returns:
        Search results with hits and metadata
    """
    try:
        if not elasticsearch_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Elasticsearch service not available"
            )
        
        # Perform search
        results = await elasticsearch_service.search(
            query=request.query,
            index=request.index or "lucid-*",
            fields=request.fields,
            filters=request.filters,
            size=request.size,
            from_=request.from_,
            sort=request.sort
        )
        
        return {
            "query": request.query,
            "index": request.index or "lucid-*",
            "results": results,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error performing search: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform search: {str(e)}"
        )


@router.get("/sessions", response_model=Dict[str, Any])
async def search_sessions(
    query: str = Query(..., description="Search query"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    size: int = Query(10, ge=1, le=100),
    from_: int = Query(0, ge=0, alias="from")
):
    """
    Search session documents
    
    Args:
        query: Search query string
        user_id: Optional user ID filter
        status: Optional status filter
        size: Number of results to return
        from_: Offset for pagination
        
    Returns:
        Session search results
    """
    try:
        if not elasticsearch_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Elasticsearch service not available"
            )
        
        # Build filters
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        if status:
            filters["status"] = status
        
        # Search sessions
        results = await elasticsearch_service.search_sessions(
            query=query,
            filters=filters,
            size=size,
            from_=from_
        )
        
        return {
            "query": query,
            "filters": filters,
            "results": results,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error searching sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search sessions: {str(e)}"
        )


@router.get("/blocks", response_model=Dict[str, Any])
async def search_blocks(
    query: str = Query(..., description="Search query"),
    min_height: Optional[int] = Query(None, description="Minimum block height"),
    max_height: Optional[int] = Query(None, description="Maximum block height"),
    size: int = Query(10, ge=1, le=100),
    from_: int = Query(0, ge=0, alias="from")
):
    """
    Search blockchain blocks
    
    Args:
        query: Search query string
        min_height: Minimum block height filter
        max_height: Maximum block height filter
        size: Number of results to return
        from_: Offset for pagination
        
    Returns:
        Block search results
    """
    try:
        if not elasticsearch_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Elasticsearch service not available"
            )
        
        # Build filters
        filters = {}
        if min_height is not None:
            filters["height_gte"] = min_height
        if max_height is not None:
            filters["height_lte"] = max_height
        
        # Search blocks
        results = await elasticsearch_service.search_blocks(
            query=query,
            filters=filters,
            size=size,
            from_=from_
        )
        
        return {
            "query": query,
            "filters": filters,
            "results": results,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error searching blocks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search blocks: {str(e)}"
        )


@router.get("/transactions", response_model=Dict[str, Any])
async def search_transactions(
    query: str = Query(..., description="Search query"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type"),
    size: int = Query(10, ge=1, le=100),
    from_: int = Query(0, ge=0, alias="from")
):
    """
    Search transactions
    
    Args:
        query: Search query string
        transaction_type: Optional transaction type filter
        size: Number of results to return
        from_: Offset for pagination
        
    Returns:
        Transaction search results
    """
    try:
        if not elasticsearch_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Elasticsearch service not available"
            )
        
        # Build filters
        filters = {}
        if transaction_type:
            filters["transaction_type"] = transaction_type
        
        # Search transactions
        results = await elasticsearch_service.search(
            query=query,
            index="lucid-transactions",
            filters=filters,
            size=size,
            from_=from_
        )
        
        return {
            "query": query,
            "filters": filters,
            "results": results,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error searching transactions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search transactions: {str(e)}"
        )


@router.get("/manifests", response_model=Dict[str, Any])
async def search_manifests(
    query: str = Query(..., description="Search query"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    size: int = Query(10, ge=1, le=100),
    from_: int = Query(0, ge=0, alias="from")
):
    """
    Search manifests
    
    Args:
        query: Search query string
        user_id: Optional user ID filter
        size: Number of results to return
        from_: Offset for pagination
        
    Returns:
        Manifest search results
    """
    try:
        if not elasticsearch_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Elasticsearch service not available"
            )
        
        # Build filters
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        
        # Search manifests
        results = await elasticsearch_service.search(
            query=query,
            index="lucid-manifests",
            filters=filters,
            size=size,
            from_=from_
        )
        
        return {
            "query": query,
            "filters": filters,
            "results": results,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error searching manifests: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search manifests: {str(e)}"
        )


@router.get("/audit-logs", response_model=Dict[str, Any])
async def search_audit_logs(
    query: str = Query(..., description="Search query"),
    action: Optional[str] = Query(None, description="Filter by action"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    size: int = Query(10, ge=1, le=100),
    from_: int = Query(0, ge=0, alias="from")
):
    """
    Search audit logs
    
    Args:
        query: Search query string
        action: Optional action filter
        user_id: Optional user ID filter
        size: Number of results to return
        from_: Offset for pagination
        
    Returns:
        Audit log search results
    """
    try:
        if not elasticsearch_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Elasticsearch service not available"
            )
        
        # Build filters
        filters = {}
        if action:
            filters["action"] = action
        if user_id:
            filters["user_id"] = user_id
        
        # Search audit logs
        results = await elasticsearch_service.search(
            query=query,
            index="lucid-audit-logs",
            filters=filters,
            size=size,
            from_=from_,
            sort=[{"timestamp": "desc"}]
        )
        
        return {
            "query": query,
            "filters": filters,
            "results": results,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error searching audit logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search audit logs: {str(e)}"
        )


@router.post("/aggregate", response_model=Dict[str, Any])
async def aggregate(request: AggregationRequest):
    """
    Perform aggregations on indexed data
    
    Args:
        request: Aggregation request
        
    Returns:
        Aggregation results
    """
    try:
        if not elasticsearch_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Elasticsearch service not available"
            )
        
        # Perform aggregation
        results = await elasticsearch_service.aggregate(
            index=request.index,
            aggregations=request.aggregations,
            query=request.query
        )
        
        return {
            "index": request.index,
            "aggregations": request.aggregations,
            "results": results,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error performing aggregation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform aggregation: {str(e)}"
        )


@router.get("/indices", response_model=List[Dict[str, Any]])
async def list_search_indices():
    """
    List all search indices
    
    Returns:
        List of index names and their document counts
    """
    try:
        if not elasticsearch_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Elasticsearch service not available"
            )
        
        # List indices
        indices = await elasticsearch_service.list_indices()
        
        indices_info = []
        for index in indices:
            stats = await elasticsearch_service.get_index_stats(index)
            indices_info.append({
                "name": index,
                "doc_count": stats.get("docs", {}).get("count", 0),
                "size_bytes": stats.get("store", {}).get("size_in_bytes", 0)
            })
        
        return indices_info
        
    except Exception as e:
        logger.error(f"Error listing search indices: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list search indices: {str(e)}"
        )


@router.get("/suggest", response_model=List[str])
async def get_search_suggestions(
    query: str = Query(..., description="Partial search query"),
    index: Optional[str] = Query(None, description="Index to search (default: all)"),
    field: str = Query("_all", description="Field to search for suggestions"),
    size: int = Query(5, ge=1, le=20)
):
    """
    Get search suggestions based on partial query
    
    Args:
        query: Partial search query
        index: Optional index to search
        field: Field to get suggestions from
        size: Number of suggestions to return
        
    Returns:
        List of suggestions
    """
    try:
        if not elasticsearch_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Elasticsearch service not available"
            )
        
        # Get suggestions
        suggestions = await elasticsearch_service.get_suggestions(
            query=query,
            index=index or "lucid-*",
            field=field,
            size=size
        )
        
        return suggestions
        
    except Exception as e:
        logger.error(f"Error getting suggestions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestions: {str(e)}"
        )

