"""
Database Collections Management API

Provides endpoints for managing MongoDB collections:
- List collections
- Create collections
- Drop collections
- Rename collections
- Collection validation

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
    prefix="/database/collections",
    tags=["database-collections"],
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
class CreateCollectionRequest(BaseModel):
    """Request model for creating a collection"""
    name: str = Field(..., description="Collection name")
    capped: bool = Field(False, description="Whether the collection is capped")
    size: Optional[int] = Field(None, description="Size limit for capped collection (bytes)")
    max: Optional[int] = Field(None, description="Max documents for capped collection")
    validator: Optional[Dict[str, Any]] = Field(None, description="Document validator schema")


class RenameCollectionRequest(BaseModel):
    """Request model for renaming a collection"""
    old_name: str = Field(..., description="Current collection name")
    new_name: str = Field(..., description="New collection name")
    drop_target: bool = Field(False, description="Drop target collection if it exists")


@router.get("/", response_model=List[str])
async def list_collections():
    """
    List all collections in the database
    
    Returns:
        List of collection names
    """
    try:
        if not mongodb_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB service not available"
            )
        
        collections = await mongodb_service.list_collections()
        
        return collections
        
    except Exception as e:
        logger.error(f"Error listing collections: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list collections: {str(e)}"
        )


@router.get("/{collection_name}", response_model=Dict[str, Any])
async def get_collection_info(collection_name: str):
    """
    Get information about a specific collection
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        Collection information including stats and configuration
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
        
        # Get collection stats
        stats = await mongodb_service.get_collection_stats(collection_name)
        
        # Get collection info
        info = await mongodb_service.get_collection_info(collection_name)
        
        return {
            "name": collection_name,
            "exists": True,
            "stats": stats,
            "info": info,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting collection info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get collection info: {str(e)}"
        )


@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_collection(request: CreateCollectionRequest):
    """
    Create a new collection
    
    Args:
        request: Collection creation request
        
    Returns:
        Success message and collection info
    """
    try:
        if not mongodb_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB service not available"
            )
        
        # Check if collection already exists
        exists = await mongodb_service.collection_exists(request.name)
        if exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Collection '{request.name}' already exists"
            )
        
        # Create collection
        options = {}
        if request.capped:
            options["capped"] = True
            if request.size:
                options["size"] = request.size
            if request.max:
                options["max"] = request.max
        
        if request.validator:
            options["validator"] = request.validator
        
        result = await mongodb_service.create_collection(request.name, **options)
        
        return {
            "success": True,
            "message": f"Collection '{request.name}' created successfully",
            "collection": request.name,
            "options": options,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating collection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create collection: {str(e)}"
        )


@router.delete("/{collection_name}", response_model=Dict[str, Any])
async def drop_collection(collection_name: str):
    """
    Drop (delete) a collection
    
    Args:
        collection_name: Name of the collection to drop
        
    Returns:
        Success message
        
    Warning:
        This operation is irreversible and will delete all documents
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
        
        # Drop collection
        result = await mongodb_service.drop_collection(collection_name)
        
        return {
            "success": True,
            "message": f"Collection '{collection_name}' dropped successfully",
            "collection": collection_name,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error dropping collection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to drop collection: {str(e)}"
        )


@router.post("/rename", response_model=Dict[str, Any])
async def rename_collection(request: RenameCollectionRequest):
    """
    Rename a collection
    
    Args:
        request: Rename collection request
        
    Returns:
        Success message
    """
    try:
        if not mongodb_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB service not available"
            )
        
        # Check if source collection exists
        exists = await mongodb_service.collection_exists(request.old_name)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{request.old_name}' not found"
            )
        
        # Check if target collection exists
        target_exists = await mongodb_service.collection_exists(request.new_name)
        if target_exists and not request.drop_target:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Collection '{request.new_name}' already exists. Use drop_target=true to overwrite."
            )
        
        # Rename collection
        result = await mongodb_service.rename_collection(
            request.old_name,
            request.new_name,
            drop_target=request.drop_target
        )
        
        return {
            "success": True,
            "message": f"Collection renamed from '{request.old_name}' to '{request.new_name}'",
            "old_name": request.old_name,
            "new_name": request.new_name,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renaming collection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rename collection: {str(e)}"
        )


@router.get("/{collection_name}/count", response_model=Dict[str, Any])
async def get_document_count(collection_name: str):
    """
    Get document count for a collection
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        Document count
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
        
        # Get count
        count = await mongodb_service.count_documents(collection_name, {})
        
        return {
            "collection": collection_name,
            "count": count,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document count: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document count: {str(e)}"
        )


@router.post("/{collection_name}/validate", response_model=Dict[str, Any])
async def validate_collection(collection_name: str):
    """
    Validate a collection
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        Validation results
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
        
        # Validate collection
        validation_result = await mongodb_service.validate_collection(collection_name)
        
        return {
            "collection": collection_name,
            "valid": validation_result.get("valid", False),
            "errors": validation_result.get("errors", []),
            "warnings": validation_result.get("warnings", []),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating collection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate collection: {str(e)}"
        )

