#!/usr/bin/env python3
"""
LUCID Service Registry - SPEC-1B Implementation
Service discovery and registration for microservices
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import redis
import aiohttp
from fastapi import FastAPI, HTTPException, Request
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ServiceInfo:
    """Service information structure"""
    name: str
    url: str
    port: int
    status: str
    health_endpoint: str
    last_heartbeat: datetime
    metadata: Dict[str, Any]

class ServiceRegistry:
    """Service registry for Lucid microservices"""
    
    def __init__(self):
        self.app = FastAPI(
            title="LUCID Service Registry",
            description="Service discovery and registration for Lucid RDP services",
            version="1.0.0"
        )
        
        # Initialize Redis connection
        self.redis_client = None
        
        # Service cache
        self.services: Dict[str, ServiceInfo] = {}
        
        # Configuration
        self.config = {
            'redis_url': 'redis://localhost:6379',
            'heartbeat_interval': 30,
            'service_ttl': 120,
            'health_check_interval': 60
        }
        
        # Setup routes
        self.setup_routes()
        
        # Initialize connections
        asyncio.create_task(self.initialize_connections())
    
    def setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "registered_services": len(self.services)
            }
        
        @self.app.post("/api/v1/services/register")
        async def register_service(request: Request):
            """Register a service"""
            try:
                data = await request.json()
                
                # Validate required fields
                required_fields = ['name', 'url', 'port', 'health_endpoint']
                for field in required_fields:
                    if field not in data:
                        raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
                
                # Create service info
                service_info = ServiceInfo(
                    name=data['name'],
                    url=data['url'],
                    port=data['port'],
                    status='registered',
                    health_endpoint=data['health_endpoint'],
                    last_heartbeat=datetime.utcnow(),
                    metadata=data.get('metadata', {})
                )
                
                # Register service
                await self.register_service(service_info)
                
                return {
                    "status": "success",
                    "message": f"Service {data['name']} registered successfully",
                    "service": asdict(service_info)
                }
                
            except Exception as e:
                logger.error(f"Service registration error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.post("/api/v1/services/{service_name}/heartbeat")
        async def heartbeat(service_name: str):
            """Update service heartbeat"""
            try:
                if service_name not in self.services:
                    raise HTTPException(status_code=404, detail="Service not found")
                
                # Update heartbeat
                self.services[service_name].last_heartbeat = datetime.utcnow()
                self.services[service_name].status = 'healthy'
                
                # Store in Redis
                await self.store_service_info(self.services[service_name])
                
                return {
                    "status": "success",
                    "message": f"Heartbeat updated for {service_name}",
                    "timestamp": self.services[service_name].last_heartbeat.isoformat()
                }
                
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.get("/api/v1/services")
        async def list_services():
            """List all registered services"""
            try:
                services = []
                for service in self.services.values():
                    services.append(asdict(service))
                
                return {
                    "status": "success",
                    "services": services,
                    "total": len(services)
                }
                
            except Exception as e:
                logger.error(f"List services error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.get("/api/v1/services/{service_name}")
        async def get_service(service_name: str):
            """Get specific service information"""
            try:
                if service_name not in self.services:
                    raise HTTPException(status_code=404, detail="Service not found")
                
                return {
                    "status": "success",
                    "service": asdict(self.services[service_name])
                }
                
            except Exception as e:
                logger.error(f"Get service error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.delete("/api/v1/services/{service_name}")
        async def unregister_service(service_name: str):
            """Unregister a service"""
            try:
                if service_name not in self.services:
                    raise HTTPException(status_code=404, detail="Service not found")
                
                # Remove from cache
                del self.services[service_name]
                
                # Remove from Redis
                await self.redis_client.delete(f"service:{service_name}")
                
                return {
                    "status": "success",
                    "message": f"Service {service_name} unregistered successfully"
                }
                
            except Exception as e:
                logger.error(f"Unregister service error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.get("/api/v1/services/discover/{service_name}")
        async def discover_service(service_name: str):
            """Discover service URL"""
            try:
                if service_name not in self.services:
                    # Try to load from Redis
                    service_info = await self.load_service_info(service_name)
                    if not service_info:
                        raise HTTPException(status_code=404, detail="Service not found")
                else:
                    service_info = self.services[service_name]
                
                # Check if service is healthy
                if service_info.status != 'healthy':
                    raise HTTPException(status_code=503, detail="Service unavailable")
                
                return {
                    "status": "success",
                    "service": {
                        "name": service_info.name,
                        "url": service_info.url,
                        "port": service_info.port,
                        "status": service_info.status
                    }
                }
                
            except Exception as e:
                logger.error(f"Service discovery error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
    
    async def initialize_connections(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(self.config['redis_url'])
            await self.redis_client.ping()
            logger.info("Redis connection established")
            
            # Load existing services from Redis
            await self.load_all_services()
            
        except Exception as e:
            logger.error(f"Connection initialization error: {e}")
    
    async def register_service(self, service_info: ServiceInfo):
        """Register a service"""
        try:
            # Add to cache
            self.services[service_info.name] = service_info
            
            # Store in Redis
            await self.store_service_info(service_info)
            
            logger.info(f"Service {service_info.name} registered at {service_info.url}")
            
        except Exception as e:
            logger.error(f"Service registration error: {e}")
            raise
    
    async def store_service_info(self, service_info: ServiceInfo):
        """Store service info in Redis"""
        try:
            service_data = {
                'name': service_info.name,
                'url': service_info.url,
                'port': service_info.port,
                'status': service_info.status,
                'health_endpoint': service_info.health_endpoint,
                'last_heartbeat': service_info.last_heartbeat.isoformat(),
                'metadata': json.dumps(service_info.metadata)
            }
            
            # Store with TTL
            await self.redis_client.hset(
                f"service:{service_info.name}",
                mapping=service_data
            )
            await self.redis_client.expire(
                f"service:{service_info.name}",
                self.config['service_ttl']
            )
            
        except Exception as e:
            logger.error(f"Store service info error: {e}")
            raise
    
    async def load_service_info(self, service_name: str) -> Optional[ServiceInfo]:
        """Load service info from Redis"""
        try:
            service_data = await self.redis_client.hgetall(f"service:{service_name}")
            
            if not service_data:
                return None
            
            return ServiceInfo(
                name=service_data[b'name'].decode(),
                url=service_data[b'url'].decode(),
                port=int(service_data[b'port']),
                status=service_data[b'status'].decode(),
                health_endpoint=service_data[b'health_endpoint'].decode(),
                last_heartbeat=datetime.fromisoformat(service_data[b'last_heartbeat'].decode()),
                metadata=json.loads(service_data[b'metadata'].decode())
            )
            
        except Exception as e:
            logger.error(f"Load service info error: {e}")
            return None
    
    async def load_all_services(self):
        """Load all services from Redis"""
        try:
            # Get all service keys
            service_keys = await self.redis_client.keys("service:*")
            
            for key in service_keys:
                service_name = key.decode().replace("service:", "")
                service_info = await self.load_service_info(service_name)
                
                if service_info:
                    self.services[service_name] = service_info
            
            logger.info(f"Loaded {len(self.services)} services from Redis")
            
        except Exception as e:
            logger.error(f"Load all services error: {e}")
    
    async def health_check_services(self):
        """Periodic health check of registered services"""
        while True:
            try:
                for service_name, service_info in list(self.services.items()):
                    # Check if service is still alive
                    if datetime.utcnow() - service_info.last_heartbeat > timedelta(seconds=self.config['service_ttl']):
                        logger.warning(f"Service {service_name} appears to be down")
                        service_info.status = 'unhealthy'
                        
                        # Remove from cache
                        del self.services[service_name]
                        
                        # Remove from Redis
                        await self.redis_client.delete(f"service:{service_name}")
                
                await asyncio.sleep(self.config['health_check_interval'])
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(10)

# Initialize service registry
registry = ServiceRegistry()

if __name__ == "__main__":
    uvicorn.run(
        "service-registry:registry.app",
        host="0.0.0.0",
        port=8081,
        reload=True,
        log_level="info"
    )
