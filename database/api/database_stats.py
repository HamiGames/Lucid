"""
Database Statistics API

Provides statistics and metrics endpoints for all database services:
- MongoDB collection statistics
- Redis memory and performance stats
- Elasticsearch index statistics
- Overall database metrics

Port: 8088 (Storage-Database Cluster)
Phase: Phase 1 - Foundation
"""

from fastapi import APIRouter, HTTPException, Query, status
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from ..services.mongodb_service import MongoDBService
from ..services.redis_service import RedisService
from ..services.elasticsearch_service import ElasticsearchService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/database/stats",
    tags=["database-stats"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

# Service instances (to be initialized at startup)
mongodb_service: MongoDBService = None
redis_service: RedisService = None
elasticsearch_service: ElasticsearchService = None


def init_services(mongodb: MongoDBService, redis: RedisService, elasticsearch: ElasticsearchService):
    """Initialize service instances"""
    global mongodb_service, redis_service, elasticsearch_service
    mongodb_service = mongodb
    redis_service = redis
    elasticsearch_service = elasticsearch


@router.get("/", response_model=Dict[str, Any])
async def get_overall_stats():
    """
    Get overall database statistics
    
    Returns:
        Comprehensive statistics for all database services
    """
    try:
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Get stats from all services
        mongodb_stats = await get_mongodb_stats_data()
        redis_stats = await get_redis_stats_data()
        elasticsearch_stats = await get_elasticsearch_stats_data()
        
        return {
            "timestamp": timestamp,
            "mongodb": mongodb_stats,
            "redis": redis_stats,
            "elasticsearch": elasticsearch_stats,
            "summary": {
                "total_databases": 3,
                "mongodb_collections": mongodb_stats.get("collections", 0),
                "redis_keys": redis_stats.get("total_keys", 0),
                "elasticsearch_indices": elasticsearch_stats.get("indices_count", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting overall stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get overall stats: {str(e)}"
        )


@router.get("/mongodb", response_model=Dict[str, Any])
async def get_mongodb_stats():
    """
    Get MongoDB database statistics
    
    Returns:
        MongoDB database stats including collection counts, sizes, and indexes
    """
    try:
        return await get_mongodb_stats_data()
    except Exception as e:
        logger.error(f"Error getting MongoDB stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get MongoDB stats: {str(e)}"
        )


@router.get("/mongodb/collection/{collection_name}", response_model=Dict[str, Any])
async def get_collection_stats(collection_name: str):
    """
    Get statistics for a specific MongoDB collection
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        Collection statistics including document count, size, and indexes
    """
    try:
        if not mongodb_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB service not available"
            )
        
        stats = await mongodb_service.get_collection_stats(collection_name)
        
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found"
            )
        
        return {
            "collection": collection_name,
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting collection stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get collection stats: {str(e)}"
        )


@router.get("/redis", response_model=Dict[str, Any])
async def get_redis_stats():
    """
    Get Redis statistics
    
    Returns:
        Redis stats including memory usage, connected clients, and performance metrics
    """
    try:
        return await get_redis_stats_data()
    except Exception as e:
        logger.error(f"Error getting Redis stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Redis stats: {str(e)}"
        )


@router.get("/redis/memory", response_model=Dict[str, Any])
async def get_redis_memory_stats():
    """
    Get detailed Redis memory statistics
    
    Returns:
        Detailed memory usage information
    """
    try:
        if not redis_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis service not available"
            )
        
        info = await redis_service.get_info()
        
        memory_stats = {
            "used_memory": info.get("used_memory", 0),
            "used_memory_human": info.get("used_memory_human", "0B"),
            "used_memory_rss": info.get("used_memory_rss", 0),
            "used_memory_peak": info.get("used_memory_peak", 0),
            "used_memory_peak_human": info.get("used_memory_peak_human", "0B"),
            "total_system_memory": info.get("total_system_memory", 0),
            "total_system_memory_human": info.get("total_system_memory_human", "0B"),
            "mem_fragmentation_ratio": info.get("mem_fragmentation_ratio", 0.0)
        }
        
        return {
            "memory": memory_stats,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error getting Redis memory stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Redis memory stats: {str(e)}"
        )


@router.get("/elasticsearch", response_model=Dict[str, Any])
async def get_elasticsearch_stats():
    """
    Get Elasticsearch statistics
    
    Returns:
        Elasticsearch cluster stats including indices, documents, and storage
    """
    try:
        return await get_elasticsearch_stats_data()
    except Exception as e:
        logger.error(f"Error getting Elasticsearch stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Elasticsearch stats: {str(e)}"
        )


@router.get("/elasticsearch/indices", response_model=List[Dict[str, Any]])
async def get_elasticsearch_indices_stats():
    """
    Get statistics for all Elasticsearch indices
    
    Returns:
        List of index statistics
    """
    try:
        if not elasticsearch_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Elasticsearch service not available"
            )
        
        indices = await elasticsearch_service.list_indices()
        
        indices_stats = []
        for index in indices:
            index_stats = await elasticsearch_service.get_index_stats(index)
            indices_stats.append({
                "index": index,
                "stats": index_stats
            })
        
        return indices_stats
        
    except Exception as e:
        logger.error(f"Error getting indices stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get indices stats: {str(e)}"
        )


@router.get("/performance", response_model=Dict[str, Any])
async def get_performance_metrics():
    """
    Get performance metrics for all databases
    
    Returns:
        Performance metrics including query times, throughput, and latency
    """
    try:
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Collect performance metrics from all services
        performance_metrics = {
            "timestamp": timestamp,
            "mongodb": {
                "query_latency_ms": 0,  # To be implemented
                "operations_per_second": 0  # To be implemented
            },
            "redis": {
                "query_latency_ms": 0,  # To be implemented
                "commands_per_second": 0  # To be implemented
            },
            "elasticsearch": {
                "query_latency_ms": 0,  # To be implemented
                "indexing_rate": 0  # To be implemented
            }
        }
        
        return performance_metrics
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance metrics: {str(e)}"
        )


# Helper functions
async def get_mongodb_stats_data() -> Dict[str, Any]:
    """Get MongoDB statistics data"""
    try:
        if not mongodb_service:
            return {"error": "MongoDB service not initialized"}
        
        db_stats = await mongodb_service.get_database_stats()
        
        return {
            "connected": True,
            "database": db_stats.get("db", "lucid"),
            "collections": db_stats.get("collections", 0),
            "views": db_stats.get("views", 0),
            "objects": db_stats.get("objects", 0),
            "data_size": db_stats.get("dataSize", 0),
            "storage_size": db_stats.get("storageSize", 0),
            "indexes": db_stats.get("indexes", 0),
            "index_size": db_stats.get("indexSize", 0),
            "avg_obj_size": db_stats.get("avgObjSize", 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting MongoDB stats data: {str(e)}")
        return {"error": str(e)}


async def get_redis_stats_data() -> Dict[str, Any]:
    """Get Redis statistics data"""
    try:
        if not redis_service:
            return {"error": "Redis service not initialized"}
        
        info = await redis_service.get_info()
        
        return {
            "connected": True,
            "version": info.get("redis_version", "unknown"),
            "uptime_seconds": info.get("uptime_in_seconds", 0),
            "uptime_days": info.get("uptime_in_days", 0),
            "connected_clients": info.get("connected_clients", 0),
            "blocked_clients": info.get("blocked_clients", 0),
            "used_memory": info.get("used_memory", 0),
            "used_memory_human": info.get("used_memory_human", "0B"),
            "total_keys": await redis_service.get_total_keys(),
            "total_commands_processed": info.get("total_commands_processed", 0),
            "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting Redis stats data: {str(e)}")
        return {"error": str(e)}


async def get_elasticsearch_stats_data() -> Dict[str, Any]:
    """Get Elasticsearch statistics data"""
    try:
        if not elasticsearch_service:
            return {"error": "Elasticsearch service not initialized"}
        
        cluster_stats = await elasticsearch_service.get_cluster_stats()
        cluster_health = await elasticsearch_service.get_cluster_health()
        
        return {
            "connected": True,
            "cluster_name": cluster_health.get("cluster_name", "unknown"),
            "cluster_status": cluster_health.get("status", "unknown"),
            "number_of_nodes": cluster_health.get("number_of_nodes", 0),
            "number_of_data_nodes": cluster_health.get("number_of_data_nodes", 0),
            "active_shards": cluster_health.get("active_shards", 0),
            "relocating_shards": cluster_health.get("relocating_shards", 0),
            "unassigned_shards": cluster_health.get("unassigned_shards", 0),
            "indices_count": cluster_stats.get("indices", {}).get("count", 0),
            "docs_count": cluster_stats.get("indices", {}).get("docs", {}).get("count", 0),
            "store_size_bytes": cluster_stats.get("indices", {}).get("store", {}).get("size_in_bytes", 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting Elasticsearch stats data: {str(e)}")
        return {"error": str(e)}

