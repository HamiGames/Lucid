"""
Database Indexes Management API

Provides endpoints for managing MongoDB indexes:
- List indexes for collections
- Create indexes
- Drop indexes
- Reindex collections
- Index statistics

Port: 8088 (Storage-Database Cluster)
Phase: Phase 1 - Foundation
"""

from fastapi import APIRouter, HTTPException, Body, status
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from ..services.mongodb_service import MongoDBService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/database/indexes",
    tags=["database-indexes"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

# Service instance
mongodb_service: MongoDBService = None


def init_service(mongodb: MongoDBService):
    """Initialize MongoDB service instance"""
    global mongodb_service
    mongodb_service = mongodb


# Request/Response Models
class CreateIndexRequest(BaseModel):
    """Request model for creating an index"""
    collection: str = Field(..., description="Collection name")
    keys: Dict[str, int] = Field(..., description="Index keys specification (1 for ascending, -1 for descending)")
    name: Optional[str] = Field(None, description="Index name")
    unique: bool = Field(False, description="Whether the index should enforce uniqueness")
    sparse: bool = Field(False, description="Whether the index should be sparse")
    background: bool = Field(False, description="Whether to build the index in the background")
    expireAfterSeconds: Optional[int] = Field(None, description="TTL for documents (seconds)")


class DropIndexRequest(BaseModel):
    """Request model for dropping an index"""
    collection: str = Field(..., description="Collection name")
    index_name: str = Field(..., description="Name of the index to drop")


@router.get("/{collection_name}", response_model=List[Dict[str, Any]])
async def list_indexes(collection_name: str):
    """
    List all indexes for a collection
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        List of index specifications
    """
    try:
        if not mongodb_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB service not available"
            )
        
        # Check if collection exists
        exists = await mongodb_service.collection_exists(collection_name)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found"
            )
        
        # List indexes
        indexes = await mongodb_service.list_indexes(collection_name)
        
        return indexes
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing indexes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list indexes: {str(e)}"
        )


@router.get("/{collection_name}/{index_name}", response_model=Dict[str, Any])
async def get_index_info(collection_name: str, index_name: str):
    """
    Get information about a specific index
    
    Args:
        collection_name: Name of the collection
        index_name: Name of the index
        
    Returns:
        Index specification and statistics
    """
    try:
        if not mongodb_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB service not available"
            )
        
        # List all indexes and find the requested one
        indexes = await mongodb_service.list_indexes(collection_name)
        
        index_info = None
        for index in indexes:
            if index.get("name") == index_name:
                index_info = index
                break
        
        if not index_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Index '{index_name}' not found in collection '{collection_name}'"
            )
        
        return {
            "collection": collection_name,
            "index": index_info,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting index info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get index info: {str(e)}"
        )


@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_index(request: CreateIndexRequest):
    """
    Create a new index on a collection
    
    Args:
        request: Index creation request
        
    Returns:
        Success message and index name
    """
    try:
        if not mongodb_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB service not available"
            )
        
        # Check if collection exists
        exists = await mongodb_service.collection_exists(request.collection)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{request.collection}' not found"
            )
        
        # Build index options
        index_options = {
            "unique": request.unique,
            "sparse": request.sparse,
            "background": request.background
        }
        
        if request.name:
            index_options["name"] = request.name
        
        if request.expireAfterSeconds is not None:
            index_options["expireAfterSeconds"] = request.expireAfterSeconds
        
        # Create index
        index_name = await mongodb_service.create_index(
            request.collection,
            list(request.keys.items()),
            **index_options
        )
        
        return {
            "success": True,
            "message": f"Index created successfully",
            "collection": request.collection,
            "index_name": index_name,
            "keys": request.keys,
            "options": index_options,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating index: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create index: {str(e)}"
        )


@router.delete("/", response_model=Dict[str, Any])
async def drop_index(request: DropIndexRequest):
    """
    Drop an index from a collection
    
    Args:
        request: Drop index request
        
    Returns:
        Success message
    """
    try:
        if not mongodb_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB service not available"
            )
        
        # Check if collection exists
        exists = await mongodb_service.collection_exists(request.collection)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{request.collection}' not found"
            )
        
        # Cannot drop the _id index
        if request.index_name == "_id_":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot drop the _id index"
            )
        
        # Drop index
        result = await mongodb_service.drop_index(request.collection, request.index_name)
        
        return {
            "success": True,
            "message": f"Index '{request.index_name}' dropped successfully",
            "collection": request.collection,
            "index_name": request.index_name,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error dropping index: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to drop index: {str(e)}"
        )


@router.post("/{collection_name}/create-all", response_model=Dict[str, Any])
async def create_collection_indexes(collection_name: str):
    """
    Create all standard indexes for a Lucid collection
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        List of created indexes
    """
    try:
        if not mongodb_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB service not available"
            )
        
        # Check if collection exists
        exists = await mongodb_service.collection_exists(collection_name)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found"
            )
        
        # Create indexes based on collection type
        created_indexes = await mongodb_service.create_collection_indexes(collection_name)
        
        return {
            "success": True,
            "message": f"Indexes created for collection '{collection_name}'",
            "collection": collection_name,
            "indexes_created": len(created_indexes),
            "indexes": created_indexes,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating collection indexes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create collection indexes: {str(e)}"
        )


@router.post("/create-all-lucid-indexes", response_model=Dict[str, Any])
async def create_all_lucid_indexes():
    """
    Create all standard indexes for all Lucid collections
    
    This endpoint creates the complete set of 45+ indexes across all collections
    as specified in the Lucid database schema.
    
    Returns:
        Summary of created indexes
    """
    try:
        if not mongodb_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB service not available"
            )
        
        # Create all indexes
        result = await mongodb_service.create_indexes()
        
        return {
            "success": True,
            "message": "All Lucid indexes created successfully",
            "collections_processed": result.get("collections_processed", 0),
            "indexes_created": result.get("indexes_created", 0),
            "details": result.get("details", []),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error creating all Lucid indexes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create all Lucid indexes: {str(e)}"
        )


@router.post("/{collection_name}/reindex", response_model=Dict[str, Any])
async def reindex_collection(collection_name: str):
    """
    Rebuild all indexes for a collection
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        Success message
        
    Note:
        This operation can take significant time for large collections
    """
    try:
        if not mongodb_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB service not available"
            )
        
        # Check if collection exists
        exists = await mongodb_service.collection_exists(collection_name)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found"
            )
        
        # Reindex collection
        result = await mongodb_service.reindex_collection(collection_name)
        
        return {
            "success": True,
            "message": f"Collection '{collection_name}' reindexed successfully",
            "collection": collection_name,
            "indexes_rebuilt": result.get("indexes_rebuilt", 0),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reindexing collection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reindex collection: {str(e)}"
        )


@router.get("/{collection_name}/stats", response_model=Dict[str, Any])
async def get_index_stats(collection_name: str):
    """
    Get statistics for all indexes on a collection
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        Index statistics including usage and size
    """
    try:
        if not mongodb_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB service not available"
            )
        
        # Check if collection exists
        exists = await mongodb_service.collection_exists(collection_name)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found"
            )
        
        # Get index stats
        index_stats = await mongodb_service.get_index_stats(collection_name)
        
        return {
            "collection": collection_name,
            "index_stats": index_stats,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting index stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get index stats: {str(e)}"
        )

