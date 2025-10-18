#!/usr/bin/env python3
"""
LUCID Database Monitoring Service
LUCID-STRICT Layer 0 Core Infrastructure
Professional database monitoring and health check service for Pi deployment
"""

import asyncio
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.core import CollectorRegistry

# Database integration
try:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
    import pymongo
    HAS_MOTOR = True
except ImportError:
    HAS_MOTOR = False
    AsyncIOMotorClient = None
    AsyncIOMotorDatabase = None

logger = logging.getLogger(__name__)

# Configuration from environment
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin")
MONITORING_SERVICE_PORT = int(os.getenv("MONITORING_SERVICE_PORT", "8091"))
METRICS_PORT = int(os.getenv("METRICS_PORT", "9216"))
MONITORING_INTERVAL = int(os.getenv("MONITORING_INTERVAL", "30"))
PROMETHEUS_ENABLED = os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true"

# Prometheus metrics
REGISTRY = CollectorRegistry()

# Database metrics
DB_CONNECTIONS = Gauge('mongodb_connections', 'Number of database connections', registry=REGISTRY)
DB_OPERATIONS = Counter('mongodb_operations_total', 'Total database operations', ['operation'], registry=REGISTRY)
DB_QUERY_TIME = Histogram('mongodb_query_duration_seconds', 'Database query duration', ['operation'], registry=REGISTRY)
DB_COLLECTION_SIZE = Gauge('mongodb_collection_size_bytes', 'Collection size in bytes', ['collection'], registry=REGISTRY)
DB_INDEX_SIZE = Gauge('mongodb_index_size_bytes', 'Index size in bytes', ['collection'], registry=REGISTRY)

# System metrics
SYSTEM_CPU = Gauge('system_cpu_percent', 'System CPU usage percentage', registry=REGISTRY)
SYSTEM_MEMORY = Gauge('system_memory_percent', 'System memory usage percentage', registry=REGISTRY)
SYSTEM_DISK = Gauge('system_disk_percent', 'System disk usage percentage', registry=REGISTRY)

# Health metrics
HEALTH_STATUS = Gauge('database_health_status', 'Database health status (1=healthy, 0=unhealthy)', registry=REGISTRY)
HEALTH_CHECK_DURATION = Histogram('database_health_check_duration_seconds', 'Health check duration', registry=REGISTRY)


class HealthStatus(Enum):
    """Health status states"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class DatabaseStats:
    """Database statistics"""
    connections: int
    operations: int
    query_time: float
    collection_sizes: Dict[str, int]
    index_sizes: Dict[str, int]
    health_status: HealthStatus
    last_check: datetime


class MonitoringRequest(BaseModel):
    """Monitoring request model"""
    database: str
    collections: Optional[List[str]] = None
    metrics: Optional[List[str]] = None


class MonitoringResponse(BaseModel):
    """Monitoring response model"""
    status: str
    database: str
    stats: Dict[str, Any]
    timestamp: datetime


class DatabaseMonitoringService:
    """Database monitoring service implementation"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Lucid Database Monitoring Service",
            description="Professional database monitoring and health check service",
            version="1.0.0"
        )
        self.scheduler = AsyncIOScheduler()
        self.mongo_client: Optional[AsyncIOMotorClient] = None
        self.mongo_db: Optional[AsyncIOMotorDatabase] = None
        self.current_stats: Optional[DatabaseStats] = None
        
        # Setup routes
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            try:
                start_time = time.time()
                
                if self.mongo_client:
                    await self.mongo_client.admin.command('ping')
                
                duration = time.time() - start_time
                HEALTH_CHECK_DURATION.observe(duration)
                
                return {
                    "status": "healthy",
                    "timestamp": datetime.now(timezone.utc),
                    "response_time": duration
                }
            except Exception as e:
                HEALTH_CHECK_DURATION.observe(time.time() - start_time)
                raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
        
        @self.app.get("/metrics")
        async def metrics():
            """Prometheus metrics endpoint"""
            if not PROMETHEUS_ENABLED:
                raise HTTPException(status_code=404, detail="Metrics not enabled")
            
            return generate_latest(REGISTRY)
        
        @self.app.post("/monitor", response_model=MonitoringResponse)
        async def start_monitoring(request: MonitoringRequest):
            """Start monitoring specific database and collections"""
            try:
                stats = await self._collect_database_stats(request.database, request.collections)
                
                return MonitoringResponse(
                    status="monitoring",
                    database=request.database,
                    stats={
                        "connections": stats.connections,
                        "operations": stats.operations,
                        "query_time": stats.query_time,
                        "collection_sizes": stats.collection_sizes,
                        "index_sizes": stats.index_sizes,
                        "health_status": stats.health_status.value
                    },
                    timestamp=stats.last_check
                )
                
            except Exception as e:
                logger.error(f"Failed to start monitoring: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/stats")
        async def get_current_stats():
            """Get current database statistics"""
            if not self.current_stats:
                raise HTTPException(status_code=404, detail="No statistics available")
            
            return {
                "database": "lucid",
                "stats": {
                    "connections": self.current_stats.connections,
                    "operations": self.current_stats.operations,
                    "query_time": self.current_stats.query_time,
                    "collection_sizes": self.current_stats.collection_sizes,
                    "index_sizes": self.current_stats.index_sizes,
                    "health_status": self.current_stats.health_status.value
                },
                "timestamp": self.current_stats.last_check
            }
        
        @self.app.get("/alerts")
        async def get_alerts():
            """Get current alerts"""
            alerts = []
            
            if self.current_stats:
                # Check for high connection count
                if self.current_stats.connections > 80:
                    alerts.append({
                        "type": "high_connections",
                        "severity": "warning",
                        "message": f"High connection count: {self.current_stats.connections}",
                        "timestamp": datetime.now(timezone.utc)
                    })
                
                # Check for slow queries
                if self.current_stats.query_time > 1.0:
                    alerts.append({
                        "type": "slow_queries",
                        "severity": "warning",
                        "message": f"Slow query time: {self.current_stats.query_time:.2f}s",
                        "timestamp": datetime.now(timezone.utc)
                    })
                
                # Check for unhealthy status
                if self.current_stats.health_status != HealthStatus.HEALTHY:
                    alerts.append({
                        "type": "unhealthy_database",
                        "severity": "critical",
                        "message": f"Database health status: {self.current_stats.health_status.value}",
                        "timestamp": datetime.now(timezone.utc)
                    })
            
            return {"alerts": alerts}
    
    async def _collect_database_stats(self, database: str, collections: Optional[List[str]] = None) -> DatabaseStats:
        """Collect database statistics"""
        try:
            start_time = time.time()
            
            # Get database stats
            db_stats = await self.mongo_client[database].command("dbStats")
            
            # Get connection stats
            conn_stats = await self.mongo_client.admin.command("connPoolStats")
            
            # Get collection stats
            collection_sizes = {}
            index_sizes = {}
            
            if collections:
                for collection_name in collections:
                    try:
                        coll_stats = await self.mongo_client[database].command("collStats", collection_name)
                        collection_sizes[collection_name] = coll_stats.get("size", 0)
                        index_sizes[collection_name] = coll_stats.get("totalIndexSize", 0)
                    except Exception as e:
                        logger.warning(f"Failed to get stats for collection {collection_name}: {e}")
            
            # Calculate health status
            health_status = HealthStatus.HEALTHY
            if db_stats.get("ok", 0) != 1:
                health_status = HealthStatus.UNHEALTHY
            
            query_time = time.time() - start_time
            
            # Update Prometheus metrics
            DB_CONNECTIONS.set(conn_stats.get("totalCreated", 0))
            DB_QUERY_TIME.labels(operation="stats").observe(query_time)
            
            for collection, size in collection_sizes.items():
                DB_COLLECTION_SIZE.labels(collection=collection).set(size)
            
            for collection, size in index_sizes.items():
                DB_INDEX_SIZE.labels(collection=collection).set(size)
            
            HEALTH_STATUS.set(1 if health_status == HealthStatus.HEALTHY else 0)
            
            stats = DatabaseStats(
                connections=conn_stats.get("totalCreated", 0),
                operations=db_stats.get("operations", 0),
                query_time=query_time,
                collection_sizes=collection_sizes,
                index_sizes=index_sizes,
                health_status=health_status,
                last_check=datetime.now(timezone.utc)
            )
            
            self.current_stats = stats
            return stats
            
        except Exception as e:
            logger.error(f"Failed to collect database stats: {e}")
            HEALTH_STATUS.set(0)
            raise
    
    async def _scheduled_monitoring(self):
        """Scheduled monitoring task"""
        try:
            logger.info("Running scheduled database monitoring")
            
            # Collect stats for all collections
            collections = ["sessions", "authentication", "work_proofs", "blockchain_data", "contracts"]
            await self._collect_database_stats("lucid", collections)
            
            logger.info("Scheduled monitoring completed")
            
        except Exception as e:
            logger.error(f"Scheduled monitoring failed: {e}")
    
    async def start(self):
        """Start the monitoring service"""
        try:
            # Connect to MongoDB
            if HAS_MOTOR:
                self.mongo_client = AsyncIOMotorClient(MONGODB_URL)
                self.mongo_db = self.mongo_client.get_default_database()
                logger.info("Connected to MongoDB")
            
            # Setup scheduler
            self.scheduler.add_job(
                self._scheduled_monitoring,
                'interval',
                seconds=MONITORING_INTERVAL,
                id="scheduled_monitoring",
                name="Scheduled Database Monitoring"
            )
            self.scheduler.start()
            logger.info(f"Scheduler started with interval: {MONITORING_INTERVAL}s")
            
            # Create monitoring directories
            Path("/data/monitoring").mkdir(parents=True, exist_ok=True)
            Path("/data/metrics").mkdir(parents=True, exist_ok=True)
            Path("/var/log/monitoring").mkdir(parents=True, exist_ok=True)
            
            logger.info("Database monitoring service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring service: {e}")
            raise
    
    async def stop(self):
        """Stop the monitoring service"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Scheduler stopped")
            
            if self.mongo_client:
                self.mongo_client.close()
                logger.info("MongoDB connection closed")
            
            logger.info("Database monitoring service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping monitoring service: {e}")


async def main():
    """Main application entry point"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start service
    service = DatabaseMonitoringService()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(service.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await service.start()
        
        # Start FastAPI server
        config = uvicorn.Config(
            service.app,
            host="0.0.0.0",
            port=MONITORING_SERVICE_PORT,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
        
    except Exception as e:
        logger.error(f"Service failed: {e}")
        await service.stop()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
