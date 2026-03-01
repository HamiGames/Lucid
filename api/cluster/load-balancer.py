#!/usr/bin/env python3
"""
LUCID Load Balancer - SPEC-1B Implementation
Load balancing and health checking for microservices
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import aiohttp
from fastapi import FastAPI, HTTPException, Request
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BackendServer:
    """Backend server information"""
    url: str
    weight: int
    health_status: str
    last_health_check: datetime
    response_time: float
    active_connections: int
    total_requests: int

class LoadBalancer:
    """Load balancer for Lucid microservices"""
    
    def __init__(self):
        self.app = FastAPI(
            title="LUCID Load Balancer",
            description="Load balancing and health checking for Lucid RDP services",
            version="1.0.0"
        )
        
        # Backend servers
        self.backends: Dict[str, List[BackendServer]] = {}
        
        # Load balancing algorithms
        self.algorithms = {
            'round_robin': self.round_robin,
            'weighted_round_robin': self.weighted_round_robin,
            'least_connections': self.least_connections,
            'weighted_least_connections': self.weighted_least_connections,
            'least_response_time': self.least_response_time
        }
        
        # Configuration
        self.config = {
            'health_check_interval': 30,
            'health_check_timeout': 5,
            'max_retries': 3,
            'circuit_breaker_threshold': 5,
            'circuit_breaker_timeout': 60
        }
        
        # Circuit breaker state
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        # Setup routes
        self.setup_routes()
        
        # Start health checking
        asyncio.create_task(self.health_check_loop())
    
    def setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "backend_services": len(self.backends)
            }
        
        @self.app.post("/api/v1/backends/{service_name}")
        async def add_backend(request: Request, service_name: str):
            """Add backend server"""
            try:
                data = await request.json()
                
                # Validate required fields
                if 'url' not in data:
                    raise HTTPException(status_code=400, detail="Missing required field: url")
                
                backend = BackendServer(
                    url=data['url'],
                    weight=data.get('weight', 1),
                    health_status='unknown',
                    last_health_check=datetime.utcnow(),
                    response_time=0.0,
                    active_connections=0,
                    total_requests=0
                )
                
                # Add to backends
                if service_name not in self.backends:
                    self.backends[service_name] = []
                
                self.backends[service_name].append(backend)
                
                return {
                    "status": "success",
                    "message": f"Backend {data['url']} added to {service_name}",
                    "backend": {
                        "url": backend.url,
                        "weight": backend.weight
                    }
                }
                
            except Exception as e:
                logger.error(f"Add backend error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.delete("/api/v1/backends/{service_name}/{backend_url}")
        async def remove_backend(service_name: str, backend_url: str):
            """Remove backend server"""
            try:
                if service_name not in self.backends:
                    raise HTTPException(status_code=404, detail="Service not found")
                
                # Find and remove backend
                for i, backend in enumerate(self.backends[service_name]):
                    if backend.url == backend_url:
                        del self.backends[service_name][i]
                        
                        return {
                            "status": "success",
                            "message": f"Backend {backend_url} removed from {service_name}"
                        }
                
                raise HTTPException(status_code=404, detail="Backend not found")
                
            except Exception as e:
                logger.error(f"Remove backend error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.get("/api/v1/backends/{service_name}")
        async def list_backends(service_name: str):
            """List backend servers for a service"""
            try:
                if service_name not in self.backends:
                    raise HTTPException(status_code=404, detail="Service not found")
                
                backends = []
                for backend in self.backends[service_name]:
                    backends.append({
                        "url": backend.url,
                        "weight": backend.weight,
                        "health_status": backend.health_status,
                        "last_health_check": backend.last_health_check.isoformat(),
                        "response_time": backend.response_time,
                        "active_connections": backend.active_connections,
                        "total_requests": backend.total_requests
                    })
                
                return {
                    "status": "success",
                    "service": service_name,
                    "backends": backends,
                    "total": len(backends)
                }
                
            except Exception as e:
                logger.error(f"List backends error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.get("/api/v1/backends/{service_name}/select")
        async def select_backend(request: Request, service_name: str):
            """Select backend server for load balancing"""
            try:
                if service_name not in self.backends:
                    raise HTTPException(status_code=404, detail="Service not found")
                
                # Get algorithm from query params
                algorithm = request.query_params.get('algorithm', 'round_robin')
                
                if algorithm not in self.algorithms:
                    raise HTTPException(status_code=400, detail="Invalid algorithm")
                
                # Select backend
                backend = await self.algorithms[algorithm](service_name)
                
                if not backend:
                    raise HTTPException(status_code=503, detail="No healthy backends available")
                
                # Update metrics
                backend.active_connections += 1
                backend.total_requests += 1
                
                return {
                    "status": "success",
                    "backend": {
                        "url": backend.url,
                        "weight": backend.weight,
                        "health_status": backend.health_status
                    },
                    "algorithm": algorithm
                }
                
            except Exception as e:
                logger.error(f"Select backend error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.post("/api/v1/backends/{service_name}/health")
        async def health_check_backend(request: Request, service_name: str):
            """Manual health check for backend"""
            try:
                data = await request.json()
                backend_url = data.get('url')
                
                if not backend_url:
                    raise HTTPException(status_code=400, detail="Missing backend URL")
                
                # Find backend
                backend = None
                for b in self.backends.get(service_name, []):
                    if b.url == backend_url:
                        backend = b
                        break
                
                if not backend:
                    raise HTTPException(status_code=404, detail="Backend not found")
                
                # Perform health check
                health_status = await self.check_backend_health(backend)
                
                return {
                    "status": "success",
                    "backend": {
                        "url": backend.url,
                        "health_status": health_status,
                        "last_health_check": backend.last_health_check.isoformat(),
                        "response_time": backend.response_time
                    }
                }
                
            except Exception as e:
                logger.error(f"Health check backend error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
    
    async def round_robin(self, service_name: str) -> Optional[BackendServer]:
        """Round robin load balancing"""
        backends = self.backends.get(service_name, [])
        if not backends:
            return None
        
        # Filter healthy backends
        healthy_backends = [b for b in backends if b.health_status == 'healthy']
        if not healthy_backends:
            return None
        
        # Simple round robin
        current_time = time.time()
        index = int(current_time) % len(healthy_backends)
        return healthy_backends[index]
    
    async def weighted_round_robin(self, service_name: str) -> Optional[BackendServer]:
        """Weighted round robin load balancing"""
        backends = self.backends.get(service_name, [])
        if not backends:
            return None
        
        # Filter healthy backends
        healthy_backends = [b for b in backends if b.health_status == 'healthy']
        if not healthy_backends:
            return None
        
        # Weighted round robin
        total_weight = sum(b.weight for b in healthy_backends)
        current_time = time.time()
        index = int(current_time * 1000) % total_weight
        
        current_weight = 0
        for backend in healthy_backends:
            current_weight += backend.weight
            if index < current_weight:
                return backend
        
        return healthy_backends[0]
    
    async def least_connections(self, service_name: str) -> Optional[BackendServer]:
        """Least connections load balancing"""
        backends = self.backends.get(service_name, [])
        if not backends:
            return None
        
        # Filter healthy backends
        healthy_backends = [b for b in backends if b.health_status == 'healthy']
        if not healthy_backends:
            return None
        
        # Select backend with least connections
        return min(healthy_backends, key=lambda b: b.active_connections)
    
    async def weighted_least_connections(self, service_name: str) -> Optional[BackendServer]:
        """Weighted least connections load balancing"""
        backends = self.backends.get(service_name, [])
        if not backends:
            return None
        
        # Filter healthy backends
        healthy_backends = [b for b in backends if b.health_status == 'healthy']
        if not healthy_backends:
            return None
        
        # Select backend with least connections relative to weight
        return min(healthy_backends, key=lambda b: b.active_connections / b.weight)
    
    async def least_response_time(self, service_name: str) -> Optional[BackendServer]:
        """Least response time load balancing"""
        backends = self.backends.get(service_name, [])
        if not backends:
            return None
        
        # Filter healthy backends
        healthy_backends = [b for b in backends if b.health_status == 'healthy']
        if not healthy_backends:
            return None
        
        # Select backend with least response time
        return min(healthy_backends, key=lambda b: b.response_time)
    
    async def check_backend_health(self, backend: BackendServer) -> str:
        """Check backend health"""
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{backend.url}/health",
                    timeout=aiohttp.ClientTimeout(total=self.config['health_check_timeout'])
                ) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        backend.health_status = 'healthy'
                        backend.response_time = response_time
                    else:
                        backend.health_status = 'unhealthy'
                    
                    backend.last_health_check = datetime.utcnow()
                    
                    return backend.health_status
                    
        except Exception as e:
            logger.error(f"Health check failed for {backend.url}: {e}")
            backend.health_status = 'unhealthy'
            backend.last_health_check = datetime.utcnow()
            return 'unhealthy'
    
    async def health_check_loop(self):
        """Periodic health check loop"""
        while True:
            try:
                for service_name, backends in self.backends.items():
                    for backend in backends:
                        await self.check_backend_health(backend)
                
                await asyncio.sleep(self.config['health_check_interval'])
                
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(10)

# Initialize load balancer
load_balancer = LoadBalancer()

if __name__ == "__main__":
    uvicorn.run(
        "load-balancer:load_balancer.app",
        host="0.0.0.0",
        port=8082,
        reload=True,
        log_level="info"
    )
