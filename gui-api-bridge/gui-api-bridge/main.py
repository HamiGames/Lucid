"""
FastAPI Application for GUI API Bridge Service
File: gui-api-bridge/gui-api-bridge/main.py
Pattern: Follow sessions/api/main.py and 03-api-gateway/api/app/main.py patterns
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .config import get_config
from .healthcheck import HealthCheck
from .middleware.logging import LoggingMiddleware
from .middleware.auth import AuthMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .services.routing_service import RoutingService
from .integration.integration_manager import IntegrationManager
from .routers import user, developer, node, admin, websocket

logger = logging.getLogger(__name__)


class GuiAPIBridgeApp:
    """GUI API Bridge FastAPI application wrapper"""
    
    def __init__(self):
        """Initialize application"""
        self.config = get_config().settings
        self.integration_manager = None
        self.routing_service = None
        self.health_check = None
        self.app = None
    
    async def lifespan(self):
        """Lifespan context manager for startup/shutdown"""
        try:
            # Startup
            logger.info(f"Starting {self.config.SERVICE_NAME} service")
            
            # Initialize integration manager
            self.integration_manager = IntegrationManager(self.config)
            await self.integration_manager.initialize()
            logger.info("Integration manager initialized")
            
            # Initialize routing service
            self.routing_service = RoutingService(self.config, self.integration_manager)
            logger.info("Routing service initialized")
            
            # Initialize health check
            self.health_check = HealthCheck(self.config, self.integration_manager)
            logger.info("Health check initialized")
            
            logger.info(f"{self.config.SERVICE_NAME} service started successfully")
            yield
            
        except Exception as e:
            logger.error(f"Error during startup: {e}")
            raise
        
        finally:
            # Shutdown
            logger.info(f"Shutting down {self.config.SERVICE_NAME} service")
            
            if self.integration_manager:
                await self.integration_manager.cleanup()
                logger.info("Integration manager cleaned up")
            
            logger.info(f"{self.config.SERVICE_NAME} service shut down")
    
    def create_app(self) -> FastAPI:
        """Create FastAPI application"""
        
        # Create FastAPI app with lifespan
        @asynccontextmanager
        async def app_lifespan(app: FastAPI):
            """Lifespan context manager"""
            async for _ in self.lifespan():
                yield
        
        self.app = FastAPI(
            title=self.config.SERVICE_NAME,
            description="API bridge service for Electron GUI integration",
            version=self.config.SERVICE_VERSION,
            lifespan=app_lifespan,
        )
        
        # Add CORS middleware
        cors_origins = [o.strip() for o in self.config.CORS_ORIGINS.split(",")]
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add custom middleware
        self.app.add_middleware(LoggingMiddleware)
        self.app.add_middleware(AuthMiddleware, config=self.config)
        self.app.add_middleware(RateLimitMiddleware, config=self.config)
        
        # Exception handlers
        @self.app.exception_handler(RequestValidationError)
        async def validation_exception_handler(request: Request, exc: RequestValidationError):
            """Handle validation errors"""
            logger.error(f"Validation error: {exc}")
            return JSONResponse(
                status_code=422,
                content={
                    "detail": "Validation error",
                    "errors": exc.errors(),
                },
            )
        
        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            """Handle general exceptions"""
            logger.error(f"Unhandled exception: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "message": str(exc) if self.config.DEBUG else "Internal error",
                },
            )
        
        # Health check endpoint
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            if self.health_check is None:
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "unavailable",
                        "message": "Service not initialized",
                    },
                )
            return await self.health_check.check()
        
        # Root endpoint
        @self.app.get("/")
        async def root():
            """Root endpoint"""
            return {
                "service": self.config.SERVICE_NAME,
                "version": self.config.SERVICE_VERSION,
                "status": "running",
                "api_version": "v1",
            }
        
        # API v1 endpoints placeholder
        @self.app.get("/api/v1")
        async def api_v1_root():
            """API v1 root endpoint"""
            return {
                "version": "v1",
                "routes": [
                    "/api/v1/user",
                    "/api/v1/developer",
                    "/api/v1/node",
                    "/api/v1/admin",
                    "/ws",
                ],
            }
        
        # Include routers
        self.app.include_router(user.router)
        self.app.include_router(developer.router)
        self.app.include_router(node.router)
        self.app.include_router(admin.router)
        self.app.include_router(websocket.router)
        
        logger.info(f"FastAPI application created for {self.config.SERVICE_NAME}")
        logger.info(f"Included routers: user, developer, node, admin, websocket")
        return self.app


def create_app() -> FastAPI:
    """Factory function to create FastAPI application"""
    app_wrapper = GuiAPIBridgeApp()
    return app_wrapper.create_app()


# Create app instance
app = create_app()
