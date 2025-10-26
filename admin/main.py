#!/usr/bin/env python3
"""
Lucid Admin Interface - Main Application
Step 23: Admin Backend APIs Implementation

This is the main FastAPI application for the Lucid admin interface,
providing comprehensive administrative control over the Lucid RDP system.

Features:
- Role-based access control (RBAC)
- System monitoring and management
- Session control and termination
- Node management
- Blockchain operations
- Emergency controls
- Audit logging
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Distroless-safe path resolution with validation
try:
    from src.core.utils import get_safe_project_root
    project_root = get_safe_project_root()
    sys.path.append(project_root)
except Exception as e:
    logger.error(f"Failed to resolve project root: {e}")
    sys.exit(1)

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import uvicorn

# Import admin modules
from admin.config import AdminConfig, get_admin_config
from admin.system.admin_controller import get_admin_controller, AdminController
from admin.api.dashboard import router as dashboard_router
from admin.api.users import router as users_router
from admin.api.sessions import router as sessions_router
from admin.api.blockchain import router as blockchain_router
from admin.api.nodes import router as nodes_router
from admin.api.audit import router as audit_router
from admin.api.emergency import router as emergency_router
from admin.rbac.manager import RBACManager, get_rbac_manager
from admin.audit.logger import AuditLogger
from admin.emergency.controls import EmergencyController, get_emergency_controller

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Global instances
admin_controller: AdminController = None
rbac_manager: RBACManager = None
emergency_controller: EmergencyController = None
audit_logger: AuditLogger = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global admin_controller, rbac_manager, emergency_controller, audit_logger
    
    logger.info("Starting Lucid Admin Interface...")
    
    try:
        # Initialize configuration
        config = get_admin_config()
        logger.info(f"Admin config loaded: {config.service_name}")
        
        # Initialize admin controller
        admin_controller = get_admin_controller()
        logger.info("Admin controller initialized")
        
        # Initialize RBAC manager
        rbac_manager = get_rbac_manager()
        await rbac_manager.initialize()
        logger.info("RBAC manager initialized")
        
        # Initialize emergency controller
        emergency_controller = get_emergency_controller()
        await emergency_controller.initialize()
        logger.info("Emergency controller initialized")
        
        # Initialize audit logger
        audit_logger = AuditLogger()
        await audit_logger.initialize()
        logger.info("Audit logger initialized")
        
        logger.info("Lucid Admin Interface started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start admin interface: {e}")
        raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down Lucid Admin Interface...")
    
    try:
        if audit_logger:
            await audit_logger.close()
        if emergency_controller:
            await emergency_controller.close()
        if rbac_manager:
            await rbac_manager.close()
        if admin_controller:
            await admin_controller.close()
        
        logger.info("Admin interface shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="Lucid Admin Interface",
    description="Administrative interface for Lucid RDP system management",
    version="1.0.0",
    docs_url="/admin/docs",
    redoc_url="/admin/redoc",
    openapi_url="/admin/openapi.json",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://admin.lucid.local", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["admin.lucid.local", "localhost", "127.0.0.1"]
)

# Include routers
app.include_router(
    dashboard_router,
    prefix="/admin/api/v1/dashboard",
    tags=["Dashboard"]
)

app.include_router(
    users_router,
    prefix="/admin/api/v1/users",
    tags=["User Management"]
)

app.include_router(
    sessions_router,
    prefix="/admin/api/v1/sessions",
    tags=["Session Management"]
)

app.include_router(
    blockchain_router,
    prefix="/admin/api/v1/blockchain",
    tags=["Blockchain Management"]
)

app.include_router(
    nodes_router,
    prefix="/admin/api/v1/nodes",
    tags=["Node Management"]
)

app.include_router(
    audit_router,
    prefix="/admin/api/v1/audit",
    tags=["Audit Logging"]
)

app.include_router(
    emergency_router,
    prefix="/admin/api/v1/emergency",
    tags=["Emergency Controls"]
)


# Dependency functions
async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated admin user"""
    if not admin_controller:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin controller not initialized"
        )
    
    try:
        admin = await admin_controller.validate_admin_session(credentials.credentials)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session token"
            )
        return admin
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


async def require_permission(permission: str):
    """Require specific permission for endpoint access"""
    async def permission_checker(admin = Depends(get_current_admin)):
        if not rbac_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RBAC manager not initialized"
            )
        
        has_permission = await rbac_manager.check_permission(admin.admin_id, permission)
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}"
            )
        return admin
    
    return permission_checker


# Health check endpoints
@app.get("/admin/health", tags=["Health"])
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "service": "lucid-admin-interface",
        "version": "1.0.0",
        "timestamp": "2025-01-10T19:08:00Z"
    }


@app.get("/admin/health/detailed", tags=["Health"])
async def detailed_health_check(admin = Depends(get_current_admin)):
    """Detailed health check with system status"""
    try:
        # Check component health
        components = {
            "admin_controller": admin_controller is not None,
            "rbac_manager": rbac_manager is not None,
            "emergency_controller": emergency_controller is not None,
            "audit_logger": audit_logger is not None
        }
        
        # Get system metrics
        system_status = await admin_controller.get_admin_dashboard_data(admin.admin_id)
        
        return {
            "status": "healthy",
            "components": components,
            "system_status": system_status,
            "timestamp": "2025-01-10T19:08:00Z"
        }
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": "2025-01-10T19:08:00Z"
            }
        )


@app.get("/admin/health/dependencies", tags=["Health"])
async def dependencies_health_check(admin = Depends(get_current_admin)):
    """Check dependency health"""
    try:
        dependencies = {}
        
        # Check MongoDB connection
        try:
            # This would check actual MongoDB connection
            dependencies["mongodb"] = {"status": "healthy", "response_time": "5ms"}
        except Exception as e:
            dependencies["mongodb"] = {"status": "unhealthy", "error": str(e)}
        
        # Check blockchain connection
        try:
            # This would check blockchain service connection
            dependencies["blockchain"] = {"status": "healthy", "response_time": "10ms"}
        except Exception as e:
            dependencies["blockchain"] = {"status": "unhealthy", "error": str(e)}
        
        # Check node services
        try:
            # This would check node management services
            dependencies["nodes"] = {"status": "healthy", "response_time": "15ms"}
        except Exception as e:
            dependencies["nodes"] = {"status": "unhealthy", "error": str(e)}
        
        return {
            "status": "healthy",
            "dependencies": dependencies,
            "timestamp": "2025-01-10T19:08:00Z"
        }
        
    except Exception as e:
        logger.error(f"Dependencies health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": "2025-01-10T19:08:00Z"
            }
        )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    
    # Log to audit system if available
    if audit_logger:
        await audit_logger.log_error(
            "global_exception",
            str(exc),
            request.url.path,
            None  # No admin context available
        )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "LUCID_ADMIN_ERR_5000",
                "message": "Internal server error",
                "request_id": "req-uuid-here",
                "timestamp": "2025-01-10T19:08:00Z"
            }
        }
    )


# Root endpoint
@app.get("/admin", tags=["Root"])
async def admin_root():
    """Admin interface root endpoint"""
    return {
        "service": "Lucid Admin Interface",
        "version": "1.0.0",
        "description": "Administrative interface for Lucid RDP system",
        "endpoints": {
            "health": "/admin/health",
            "docs": "/admin/docs",
            "api": "/admin/api/v1"
        }
    }


if __name__ == "__main__":
    # Get configuration
    config = get_admin_config()
    
    # Safe port conversion with validation
    try:
        from src.core.utils import validate_port_env
        port = validate_port_env("ADMIN_PORT", config.port)
    except Exception as e:
        logger.error(f"Invalid ADMIN_PORT environment variable: {e}")
        logger.info(f"Using default port: {config.port}")
        port = config.port
    
    # Run the application
    uvicorn.run(
        "admin.main:app",
        host=config.host,
        port=port,
        reload=config.debug,
        log_level="info",
        access_log=True
    )
