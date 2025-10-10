"""
LUCID Admin UI - Next.js Backend API Handlers
FastAPI backend for Next.js admin interface
Distroless container: pickme/lucid:admin-ui:latest
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import json
import os
import logging
from datetime import datetime, timedelta
import aiofiles
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LUCID Admin UI API",
    description="Backend API for LUCID Admin Interface",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://admin-ui-distroless:3000", "http://api-gateway-distroless:8098"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class SystemStatus(BaseModel):
    status: str
    uptime: str
    services: Dict[str, str]
    last_updated: datetime

class ProvisioningRequest(BaseModel):
    node_id: str
    node_type: str = Field(..., description="worker, validator, or relay")
    network: str = Field(default="shasta", description="TRON network")
    resources: Dict[str, Any] = Field(default_factory=dict)
    auto_approve: bool = Field(default=False)

class SessionExportRequest(BaseModel):
    session_ids: List[str]
    export_format: str = Field(default="json", description="json, csv, or manifest")
    include_metadata: bool = Field(default=True)
    include_chunks: bool = Field(default=False)

class NodeInfo(BaseModel):
    node_id: str
    node_type: str
    status: str
    last_seen: datetime
    resources: Dict[str, Any]
    performance_metrics: Dict[str, float]

class SessionInfo(BaseModel):
    session_id: str
    created_at: datetime
    status: str
    duration: Optional[int]
    chunk_count: int
    merkle_root: str
    owner_address: str

# Configuration
ADMIN_API_PORT = int(os.getenv("ADMIN_UI_PORT", "8098"))
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://lucid:lucid@lucid_mongo:27017/lucid")
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://lucid_api_gateway:8080")
BLOCKCHAIN_API_URL = os.getenv("BLOCKCHAIN_API_URL", "http://blockchain_api:8084")

# Data storage paths
DATA_DIR = Path("/data/admin")
EXPORTS_DIR = DATA_DIR / "exports"
LOGS_DIR = DATA_DIR / "logs"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# In-memory cache for system status
system_cache = {
    "status": "initializing",
    "uptime": "0s",
    "services": {},
    "last_updated": datetime.now()
}

@app.on_event("startup")
async def startup_event():
    """Initialize admin API on startup"""
    logger.info("Starting LUCID Admin UI API")
    logger.info(f"Admin API Port: {ADMIN_API_PORT}")
    logger.info(f"MongoDB URL: {MONGODB_URL}")
    logger.info(f"API Gateway URL: {API_GATEWAY_URL}")
    logger.info(f"Blockchain API URL: {BLOCKCHAIN_API_URL}")
    
    # Initialize system status
    await update_system_status()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "admin-ui-api",
        "version": "1.0.0"
    }

@app.get("/api/status", response_model=SystemStatus)
async def get_system_status():
    """Get overall system status"""
    try:
        await update_system_status()
        return SystemStatus(**system_cache)
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system status")

async def update_system_status():
    """Update system status cache"""
    try:
        # Check core services
        services = {}
        
        # Check API Gateway
        try:
            # This would be an actual health check in production
            services["api_gateway"] = "healthy"
        except:
            services["api_gateway"] = "unhealthy"
        
        # Check Blockchain API
        try:
            # This would be an actual health check in production
            services["blockchain_api"] = "healthy"
        except:
            services["blockchain_api"] = "unhealthy"
        
        # Check MongoDB
        try:
            # This would be an actual health check in production
            services["mongodb"] = "healthy"
        except:
            services["mongodb"] = "unhealthy"
        
        # Update cache
        system_cache.update({
            "status": "healthy" if all(s == "healthy" for s in services.values()) else "degraded",
            "services": services,
            "last_updated": datetime.now(),
            "uptime": "24h"  # This would be calculated from actual uptime
        })
        
    except Exception as e:
        logger.error(f"Error updating system status: {e}")
        system_cache["status"] = "error"

@app.get("/api/nodes", response_model=List[NodeInfo])
async def get_nodes():
    """Get list of all nodes"""
    try:
        # This would query MongoDB in production
        nodes = [
            NodeInfo(
                node_id="node-001",
                node_type="worker",
                status="active",
                last_seen=datetime.now(),
                resources={"cpu": 0.75, "memory": 0.60, "storage": 0.45},
                performance_metrics={"throughput": 150.5, "latency": 12.3}
            ),
            NodeInfo(
                node_id="node-002",
                node_type="validator",
                status="active",
                last_seen=datetime.now() - timedelta(minutes=5),
                resources={"cpu": 0.45, "memory": 0.80, "storage": 0.30},
                performance_metrics={"throughput": 200.1, "latency": 8.7}
            )
        ]
        return nodes
    except Exception as e:
        logger.error(f"Error getting nodes: {e}")
        raise HTTPException(status_code=500, detail="Failed to get nodes")

@app.get("/api/sessions", response_model=List[SessionInfo])
async def get_sessions(
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    node_id: Optional[str] = None
):
    """Get list of sessions with optional filtering"""
    try:
        # This would query MongoDB in production
        sessions = [
            SessionInfo(
                session_id="session-001",
                created_at=datetime.now() - timedelta(hours=2),
                status="completed",
                duration=7200,
                chunk_count=150,
                merkle_root="0x1234567890abcdef",
                owner_address="TYourAddress123"
            ),
            SessionInfo(
                session_id="session-002",
                created_at=datetime.now() - timedelta(hours=1),
                status="active",
                duration=None,
                chunk_count=75,
                merkle_root="0xabcdef1234567890",
                owner_address="TYourAddress456"
            )
        ]
        
        # Apply filters
        if status:
            sessions = [s for s in sessions if s.status == status]
        
        # Apply pagination
        return sessions[offset:offset + limit]
        
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sessions")

@app.post("/api/provision")
async def provision_node(request: ProvisioningRequest, background_tasks: BackgroundTasks):
    """Provision a new node"""
    try:
        logger.info(f"Provisioning node: {request.node_id} of type: {request.node_type}")
        
        # Add to background tasks for async processing
        background_tasks.add_task(process_provisioning, request)
        
        return {
            "status": "accepted",
            "node_id": request.node_id,
            "message": "Node provisioning initiated",
            "estimated_completion": (datetime.now() + timedelta(minutes=5)).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error provisioning node: {e}")
        raise HTTPException(status_code=500, detail="Failed to provision node")

async def process_provisioning(request: ProvisioningRequest):
    """Background task to process node provisioning"""
    try:
        # Simulate provisioning process
        await asyncio.sleep(2)
        
        # Log provisioning event
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "node_provisioned",
            "node_id": request.node_id,
            "node_type": request.node_type,
            "network": request.network
        }
        
        log_file = LOGS_DIR / f"provisioning_{datetime.now().strftime('%Y%m%d')}.log"
        async with aiofiles.open(log_file, "a") as f:
            await f.write(json.dumps(log_entry) + "\n")
        
        logger.info(f"Successfully provisioned node: {request.node_id}")
        
    except Exception as e:
        logger.error(f"Error in provisioning background task: {e}")

@app.post("/api/export/sessions")
async def export_sessions(request: SessionExportRequest, background_tasks: BackgroundTasks):
    """Export session data"""
    try:
        export_id = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Starting session export: {export_id}")
        
        # Add to background tasks for async processing
        background_tasks.add_task(process_session_export, export_id, request)
        
        return {
            "status": "accepted",
            "export_id": export_id,
            "message": "Session export initiated",
            "estimated_completion": (datetime.now() + timedelta(minutes=2)).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error exporting sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to export sessions")

async def process_session_export(export_id: str, request: SessionExportRequest):
    """Background task to process session export"""
    try:
        # Simulate export process
        await asyncio.sleep(1)
        
        # Create export data
        export_data = {
            "export_id": export_id,
            "timestamp": datetime.now().isoformat(),
            "session_ids": request.session_ids,
            "export_format": request.export_format,
            "include_metadata": request.include_metadata,
            "include_chunks": request.include_chunks,
            "sessions": []
        }
        
        # Add session data (this would query MongoDB in production)
        for session_id in request.session_ids:
            session_data = {
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
                "status": "completed",
                "chunk_count": 100,
                "merkle_root": "0x1234567890abcdef"
            }
            export_data["sessions"].append(session_data)
        
        # Save export file
        export_file = EXPORTS_DIR / f"{export_id}.{request.export_format}"
        
        if request.export_format == "json":
            async with aiofiles.open(export_file, "w") as f:
                await f.write(json.dumps(export_data, indent=2))
        elif request.export_format == "csv":
            # Convert to CSV format
            csv_content = "session_id,created_at,status,chunk_count,merkle_root\n"
            for session in export_data["sessions"]:
                csv_content += f"{session['session_id']},{session['created_at']},{session['status']},{session['chunk_count']},{session['merkle_root']}\n"
            async with aiofiles.open(export_file, "w") as f:
                await f.write(csv_content)
        
        logger.info(f"Successfully exported sessions: {export_id}")
        
    except Exception as e:
        logger.error(f"Error in session export background task: {e}")

@app.get("/api/exports/{export_id}")
async def download_export(export_id: str):
    """Download exported session data"""
    try:
        # Find export file
        export_files = list(EXPORTS_DIR.glob(f"{export_id}.*"))
        if not export_files:
            raise HTTPException(status_code=404, detail="Export not found")
        
        export_file = export_files[0]
        
        # Return file
        return FileResponse(
            path=str(export_file),
            filename=export_file.name,
            media_type="application/octet-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading export: {e}")
        raise HTTPException(status_code=500, detail="Failed to download export")

@app.get("/api/logs")
async def get_logs(
    log_type: str = "system",
    limit: int = 100,
    offset: int = 0
):
    """Get system logs"""
    try:
        log_file = LOGS_DIR / f"{log_type}_{datetime.now().strftime('%Y%m%d')}.log"
        
        if not log_file.exists():
            return {"logs": [], "total": 0}
        
        # Read log file
        async with aiofiles.open(log_file, "r") as f:
            lines = await f.readlines()
        
        # Parse log entries
        logs = []
        for line in lines:
            try:
                log_entry = json.loads(line.strip())
                logs.append(log_entry)
            except:
                continue
        
        # Apply pagination
        total = len(logs)
        logs = logs[offset:offset + limit]
        
        return {
            "logs": logs,
            "total": total,
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get logs")

@app.get("/api/metrics")
async def get_metrics():
    """Get system metrics"""
    try:
        # This would collect real metrics in production
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_usage": 0.45,
                "memory_usage": 0.60,
                "disk_usage": 0.30,
                "network_io": {"in": 1024, "out": 2048}
            },
            "services": {
                "api_gateway": {"requests_per_second": 150, "avg_response_time": 12.5},
                "blockchain_api": {"transactions_per_second": 25, "avg_processing_time": 45.2},
                "mongodb": {"connections": 50, "queries_per_second": 200}
            },
            "nodes": {
                "total": 5,
                "active": 4,
                "inactive": 1
            },
            "sessions": {
                "total": 1250,
                "active": 15,
                "completed": 1235
            }
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_handlers:app",
        host="0.0.0.0",
        port=ADMIN_API_PORT,
        reload=False,
        log_level="info"
    )
