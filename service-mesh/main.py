"""
Lucid Service Mesh Controller
Provides service discovery, mTLS certificate management, and Envoy configuration

File: service-mesh/main.py
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from config import get_settings
from consul_manager import ConsulManager
from certificate_manager import CertificateManager
from envoy_config_generator import EnvoyConfigGenerator

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global services
consul_manager = None
certificate_manager = None
envoy_config_generator = None


# Request models
class ServiceRegistration(BaseModel):
    service_name: str
    service_address: str
    service_port: int
    health_check_url: str = None


class EnvoyConfigRequest(BaseModel):
    service_name: str
    service_address: str
    service_port: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global consul_manager, certificate_manager, envoy_config_generator
    
    # Startup
    logger.info("Starting Lucid Service Mesh Controller...")
    
    settings = get_settings()
    
    # Initialize Consul manager
    consul_manager = ConsulManager(settings)
    await consul_manager.initialize()
    
    # Initialize certificate manager
    certificate_manager = CertificateManager(settings)
    await certificate_manager.initialize()
    
    # Initialize Envoy config generator
    envoy_config_generator = EnvoyConfigGenerator(settings)
    await envoy_config_generator.initialize()
    
    logger.info("Service Mesh Controller started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Service Mesh Controller...")
    if consul_manager:
        await consul_manager.cleanup()
    if certificate_manager:
        await certificate_manager.cleanup()
    if envoy_config_generator:
        await envoy_config_generator.cleanup()
    logger.info("Service Mesh Controller shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Lucid Service Mesh Controller",
    description="Service discovery, mTLS certificate management, and Envoy configuration",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health & Root Endpoints
# =============================================================================

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for Docker healthcheck"""
    consul_healthy = await consul_manager.check_health() if consul_manager else False
    cert_healthy = await certificate_manager.check_health() if certificate_manager else False
    envoy_healthy = await envoy_config_generator.check_health() if envoy_config_generator else False
    
    return {
        "status": "healthy",
        "service": "lucid-service-mesh-controller",
        "version": "1.0.0",
        "components": {
            "consul": consul_healthy,
            "certificates": cert_healthy,
            "envoy": envoy_healthy
        }
    }


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint"""
    return {
        "message": "Lucid Service Mesh Controller",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "services": "/services",
            "certificates": "/certificates",
            "envoy": "/envoy"
        }
    }


# =============================================================================
# Service Discovery Endpoints
# =============================================================================

@app.get("/services", tags=["service-discovery"])
async def list_services() -> Dict[str, Any]:
    """List all registered services"""
    services = await consul_manager.list_services()
    return {
        "services": services,
        "count": len(services)
    }


@app.post("/services/register", tags=["service-discovery"])
async def register_service(registration: ServiceRegistration) -> Dict[str, Any]:
    """Register new service with Consul"""
    success = await consul_manager.register_service(
        service_name=registration.service_name,
        service_address=registration.service_address,
        service_port=registration.service_port,
        health_check_url=registration.health_check_url
    )
    
    if success:
        return {
            "status": "registered",
            "service_name": registration.service_name
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to register service")


@app.get("/services/{service_name}", tags=["service-discovery"])
async def get_service(service_name: str) -> Dict[str, Any]:
    """Get service details from Consul"""
    service = await consul_manager.discover_service(service_name)
    if service:
        return service
    raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")


@app.delete("/services/{service_name}", tags=["service-discovery"])
async def deregister_service(service_name: str) -> Dict[str, Any]:
    """Deregister service from Consul"""
    service_id = f"{service_name}-1"
    success = await consul_manager.deregister_service(service_id)
    
    if success:
        return {"status": "deregistered", "service_name": service_name}
    else:
        raise HTTPException(status_code=500, detail="Failed to deregister service")


# =============================================================================
# Certificate Management Endpoints
# =============================================================================

@app.get("/certificates", tags=["certificates"])
async def list_certificates() -> Dict[str, Any]:
    """List all certificates"""
    certificates = await certificate_manager.list_certificates()
    return {
        "certificates": certificates,
        "count": len(certificates)
    }


@app.post("/certificates/{service_name}", tags=["certificates"])
async def generate_certificate(service_name: str) -> Dict[str, Any]:
    """Generate mTLS certificate for service"""
    try:
        cert_info = await certificate_manager.generate_service_certificate(service_name)
        return cert_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate certificate: {str(e)}")


@app.get("/certificates/ca", tags=["certificates"])
async def get_ca_certificate() -> Dict[str, Any]:
    """Get CA certificate"""
    ca_cert = await certificate_manager.get_ca_certificate()
    if ca_cert:
        return {"ca_certificate": ca_cert}
    raise HTTPException(status_code=404, detail="CA certificate not available")


@app.get("/certificates/{service_name}", tags=["certificates"])
async def get_certificate(service_name: str) -> Dict[str, Any]:
    """Get certificate info for service"""
    cert_info = await certificate_manager.get_certificate(service_name)
    if cert_info:
        return cert_info
    raise HTTPException(status_code=404, detail=f"Certificate for '{service_name}' not found")


@app.delete("/certificates/{service_name}", tags=["certificates"])
async def revoke_certificate(service_name: str) -> Dict[str, Any]:
    """Revoke certificate for service"""
    success = await certificate_manager.revoke_certificate(service_name)
    if success:
        return {"status": "revoked", "service_name": service_name}
    raise HTTPException(status_code=404, detail=f"Certificate for '{service_name}' not found")


# =============================================================================
# Envoy Configuration Endpoints
# =============================================================================

@app.get("/envoy/configs", tags=["envoy"])
async def list_envoy_configs() -> Dict[str, Any]:
    """List all Envoy configurations"""
    configs = await envoy_config_generator.list_envoy_configs()
    return {
        "configs": configs,
        "count": len(configs)
    }


@app.post("/envoy/configs/{service_name}", tags=["envoy"])
async def generate_envoy_config(service_name: str, request: EnvoyConfigRequest) -> Dict[str, Any]:
    """Generate Envoy configuration for service"""
    try:
        config_path = await envoy_config_generator.generate_envoy_config(
            service_name=request.service_name,
            service_address=request.service_address,
            service_port=request.service_port
        )
        return {
            "status": "generated",
            "service_name": service_name,
            "config_path": config_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Envoy config: {str(e)}")


@app.get("/envoy/configs/{service_name}", tags=["envoy"])
async def get_envoy_config(service_name: str) -> Dict[str, Any]:
    """Get Envoy configuration for service"""
    config_info = await envoy_config_generator.get_envoy_config(service_name)
    if config_info:
        return config_info
    raise HTTPException(status_code=404, detail=f"Envoy config for '{service_name}' not found")


@app.get("/envoy/configs/{service_name}/content", tags=["envoy"])
async def get_envoy_config_content(service_name: str) -> Dict[str, Any]:
    """Get Envoy configuration content for service"""
    content = await envoy_config_generator.get_config_content(service_name)
    if content:
        return {"service_name": service_name, "content": content}
    raise HTTPException(status_code=404, detail=f"Envoy config for '{service_name}' not found")


@app.delete("/envoy/configs/{service_name}", tags=["envoy"])
async def delete_envoy_config(service_name: str) -> Dict[str, Any]:
    """Delete Envoy configuration for service"""
    success = await envoy_config_generator.delete_envoy_config(service_name)
    if success:
        return {"status": "deleted", "service_name": service_name}
    raise HTTPException(status_code=404, detail=f"Envoy config for '{service_name}' not found")


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    """Main entry point for running with asyncio"""
    settings = get_settings()
    config = uvicorn.Config(
        app,
        host=settings.SERVICE_MESH_HOST,
        port=settings.HTTP_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.SERVICE_MESH_HOST,
        port=settings.HTTP_PORT,
        reload=False,
        log_level=settings.LOG_LEVEL.lower()
    )

