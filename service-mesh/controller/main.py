"""
Lucid Service Mesh Controller - Main Entry Point
Wrapper module that imports and runs the main application

File: service-mesh/controller/main.py
"""

import asyncio
import logging
import os
import sys
import signal
from typing import Dict, Any, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


class ServiceMeshController:
    """
    Main service mesh controller class.
    
    Responsibilities:
    - Service discovery coordination via Consul
    - mTLS certificate management
    - Envoy configuration generation
    - Health monitoring
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.consul_manager: Optional[ConsulManager] = None
        self.certificate_manager: Optional[CertificateManager] = None
        self.envoy_config_generator: Optional[EnvoyConfigGenerator] = None
        self.running = False
        self.http_server = None
        
    async def initialize(self):
        """Initialize all service mesh components"""
        try:
            logger.info("Initializing Service Mesh Controller...")
            
            # Initialize Consul manager
            self.consul_manager = ConsulManager(self.settings)
            await self.consul_manager.initialize()
            logger.info("Consul manager initialized")
            
            # Initialize certificate manager
            self.certificate_manager = CertificateManager(self.settings)
            await self.certificate_manager.initialize()
            logger.info("Certificate manager initialized")
            
            # Initialize Envoy config generator
            self.envoy_config_generator = EnvoyConfigGenerator(self.settings)
            await self.envoy_config_generator.initialize()
            logger.info("Envoy config generator initialized")
            
            logger.info("Service Mesh Controller initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Service Mesh Controller: {e}")
            raise
    
    async def start(self):
        """Start the service mesh controller with HTTP server"""
        try:
            self.running = True
            logger.info("Starting Service Mesh Controller...")
            
            # Import and start FastAPI application
            try:
                import uvicorn
                from main import app
                
                config = uvicorn.Config(
                    app,
                    host=self.settings.SERVICE_MESH_HOST,
                    port=self.settings.HTTP_PORT,
                    log_level=self.settings.LOG_LEVEL.lower(),
                    access_log=True
                )
                server = uvicorn.Server(config)
                
                logger.info(f"HTTP server starting on {self.settings.SERVICE_MESH_HOST}:{self.settings.HTTP_PORT}")
                await server.serve()
                
            except ImportError as e:
                logger.warning(f"FastAPI/uvicorn not available: {e}")
                # Keep running without HTTP server
                while self.running:
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"Error in Service Mesh Controller: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the service mesh controller"""
        logger.info("Shutting down Service Mesh Controller...")
        
        self.running = False
        
        # Cleanup components
        if self.consul_manager:
            await self.consul_manager.cleanup()
        if self.certificate_manager:
            await self.certificate_manager.cleanup()
        if self.envoy_config_generator:
            await self.envoy_config_generator.cleanup()
        
        logger.info("Service Mesh Controller shutdown complete")
    
    def get_status(self) -> Dict[str, Any]:
        """Get controller status"""
        return {
            "status": "running" if self.running else "stopped",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "lucid-service-mesh-controller",
            "version": "1.0.0"
        }


async def main():
    """Main entry point for the service mesh controller"""
    logger.info("Starting Lucid Service Mesh Controller...")
    
    controller = ServiceMeshController()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(controller.shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await controller.initialize()
        await controller.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        await controller.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

