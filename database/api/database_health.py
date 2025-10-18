"""
Database Health Check API

Provides health check endpoints for all database services:
- MongoDB health and connection status
- Redis health and connection status
- Elasticsearch health and cluster status
- Overall database system health

Port: 8088 (Storage-Database Cluster)
Phase: Phase 1 - Foundation
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
from datetime import datetime
import logging

from ..services.mongodb_service import MongoDBService
from ..services.redis_service import RedisService
from ..services.elasticsearch_service import ElasticsearchService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/database/health",
    tags=["database-health"],
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
async def get_overall_health():
    """
    Get overall database system health status
    
    Returns:
        Overall health status with details for each service
        
    Response Format:
    {
        "status": "healthy" | "degraded" | "unhealthy",
        "timestamp": "2025-10-14T12:00:00Z",
        "services": {
            "mongodb": {...},
            "redis": {...},
            "elasticsearch": {...}
        },
        "summary": {
            "total_services": 3,
            "healthy_services": 3,
            "degraded_services": 0,
            "unhealthy_services": 0
        }
    }
    """
    try:
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Check MongoDB health
        mongodb_health = await check_mongodb_health()
        
        # Check Redis health
        redis_health = await check_redis_health()
        
        # Check Elasticsearch health
        elasticsearch_health = await check_elasticsearch_health()
        
        # Calculate overall status
        services = {
            "mongodb": mongodb_health,
            "redis": redis_health,
            "elasticsearch": elasticsearch_health
        }
        
        healthy_count = sum(1 for s in services.values() if s["status"] == "healthy")
        degraded_count = sum(1 for s in services.values() if s["status"] == "degraded")
        unhealthy_count = sum(1 for s in services.values() if s["status"] == "unhealthy")
        
        # Determine overall status
        if unhealthy_count > 0:
            overall_status = "unhealthy"
        elif degraded_count > 0:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return {
            "status": overall_status,
            "timestamp": timestamp,
            "services": services,
            "summary": {
                "total_services": 3,
                "healthy_services": healthy_count,
                "degraded_services": degraded_count,
                "unhealthy_services": unhealthy_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error checking overall health: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check overall health: {str(e)}"
        )


@router.get("/mongodb", response_model=Dict[str, Any])
async def get_mongodb_health():
    """
    Get MongoDB health status
    
    Returns:
        MongoDB connection status, replica set status, and performance metrics
    """
    try:
        return await check_mongodb_health()
    except Exception as e:
        logger.error(f"Error checking MongoDB health: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check MongoDB health: {str(e)}"
        )


@router.get("/redis", response_model=Dict[str, Any])
async def get_redis_health():
    """
    Get Redis health status
    
    Returns:
        Redis connection status, memory usage, and connected clients
    """
    try:
        return await check_redis_health()
    except Exception as e:
        logger.error(f"Error checking Redis health: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check Redis health: {str(e)}"
        )


@router.get("/elasticsearch", response_model=Dict[str, Any])
async def get_elasticsearch_health():
    """
    Get Elasticsearch health status
    
    Returns:
        Elasticsearch cluster health, node count, and index status
    """
    try:
        return await check_elasticsearch_health()
    except Exception as e:
        logger.error(f"Error checking Elasticsearch health: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check Elasticsearch health: {str(e)}"
        )


@router.get("/ping")
async def ping():
    """
    Simple ping endpoint for basic health check
    
    Returns:
        Simple pong response
    """
    return {
        "status": "ok",
        "message": "pong",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


# Helper functions
async def check_mongodb_health() -> Dict[str, Any]:
    """Check MongoDB health"""
    try:
        if not mongodb_service:
            return {
                "status": "unhealthy",
                "message": "MongoDB service not initialized",
                "details": {}
            }
        
        # Perform health check
        is_healthy = await mongodb_service.health_check()
        
        if is_healthy:
            # Get additional stats
            stats = await mongodb_service.get_database_stats()
            return {
                "status": "healthy",
                "message": "MongoDB is operational",
                "details": {
                    "connected": True,
                    "database": stats.get("db", "lucid"),
                    "collections": stats.get("collections", 0),
                    "data_size": stats.get("dataSize", 0),
                    "storage_size": stats.get("storageSize", 0)
                }
            }
        else:
            return {
                "status": "unhealthy",
                "message": "MongoDB health check failed",
                "details": {
                    "connected": False
                }
            }
            
    except Exception as e:
        logger.error(f"MongoDB health check error: {str(e)}")
        return {
            "status": "unhealthy",
            "message": f"MongoDB error: {str(e)}",
            "details": {"error": str(e)}
        }


async def check_redis_health() -> Dict[str, Any]:
    """Check Redis health"""
    try:
        if not redis_service:
            return {
                "status": "unhealthy",
                "message": "Redis service not initialized",
                "details": {}
            }
        
        # Perform health check
        is_healthy = await redis_service.health_check()
        
        if is_healthy:
            # Get Redis info
            info = await redis_service.get_info()
            return {
                "status": "healthy",
                "message": "Redis is operational",
                "details": {
                    "connected": True,
                    "version": info.get("redis_version", "unknown"),
                    "uptime_seconds": info.get("uptime_in_seconds", 0),
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_human": info.get("used_memory_human", "0B")
                }
            }
        else:
            return {
                "status": "unhealthy",
                "message": "Redis health check failed",
                "details": {
                    "connected": False
                }
            }
            
    except Exception as e:
        logger.error(f"Redis health check error: {str(e)}")
        return {
            "status": "unhealthy",
            "message": f"Redis error: {str(e)}",
            "details": {"error": str(e)}
        }


async def check_elasticsearch_health() -> Dict[str, Any]:
    """Check Elasticsearch health"""
    try:
        if not elasticsearch_service:
            return {
                "status": "unhealthy",
                "message": "Elasticsearch service not initialized",
                "details": {}
            }
        
        # Perform health check
        is_healthy = await elasticsearch_service.health_check()
        
        if is_healthy:
            # Get cluster health
            cluster_health = await elasticsearch_service.get_cluster_health()
            return {
                "status": "healthy" if cluster_health.get("status") == "green" else "degraded",
                "message": f"Elasticsearch cluster is {cluster_health.get('status', 'unknown')}",
                "details": {
                    "connected": True,
                    "cluster_name": cluster_health.get("cluster_name", "unknown"),
                    "cluster_status": cluster_health.get("status", "unknown"),
                    "number_of_nodes": cluster_health.get("number_of_nodes", 0),
                    "number_of_data_nodes": cluster_health.get("number_of_data_nodes", 0),
                    "active_shards": cluster_health.get("active_shards", 0)
                }
            }
        else:
            return {
                "status": "unhealthy",
                "message": "Elasticsearch health check failed",
                "details": {
                    "connected": False
                }
            }
            
    except Exception as e:
        logger.error(f"Elasticsearch health check error: {str(e)}")
        return {
            "status": "unhealthy",
            "message": f"Elasticsearch error: {str(e)}",
            "details": {"error": str(e)}
        }

