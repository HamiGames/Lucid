#!/usr/bin/env python3
"""
Lucid Session Management Pipeline Service
Main entry point for the pipeline manager service
"""

import asyncio
import signal
import sys
import logging
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .pipeline_manager import PipelineManager
from .config import PipelineConfig, PipelineSettings
from .state_machine import PipelineState, StateTransition
from core.logging import setup_logging, get_logger

# Initialize logging
setup_logging()

# Global pipeline manager instance
pipeline_manager: Optional[PipelineManager] = None
logger = get_logger(__name__)

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        if pipeline_manager:
            asyncio.create_task(pipeline_manager.shutdown())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global pipeline_manager
    
    logger = get_logger(__name__)
    logger.info("Starting Lucid Pipeline Manager Service")
    
    try:
        # Initialize pipeline manager
        config = PipelineConfig()
        if not config.validate_configuration():
            raise RuntimeError("Pipeline configuration validation failed")
        
        pipeline_manager = PipelineManager(config)
        
        # Setup signal handlers
        setup_signal_handlers()
        
        logger.info("Pipeline Manager Service started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start Pipeline Manager Service: {str(e)}")
        raise
    finally:
        # Shutdown pipeline manager
        if pipeline_manager:
            logger.info("Shutting down Pipeline Manager Service")
            await pipeline_manager.shutdown()
            pipeline_manager = None
        logger.info("Pipeline Manager Service shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="Lucid Pipeline Manager API",
    description="Session processing pipeline management service",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware (configured from environment variables)
# CORS_ORIGINS env var: comma-separated list of origins, or "*" for all
# Default to ["*"] if not set
import os
cors_origins_str = os.getenv('CORS_ORIGINS', '*')
if cors_origins_str == "*":
    cors_origins = ["*"]
else:
    cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger = get_logger(__name__)
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "LUCID_ERR_5000",
                "message": "Internal server error",
                "details": str(exc) if app.debug else "An unexpected error occurred"
            }
        }
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    global pipeline_manager
    
    if not pipeline_manager:
        raise HTTPException(status_code=503, detail="Pipeline manager not initialized")
    
    try:
        # Get basic health information
        active_pipelines = len(pipeline_manager.active_pipelines)
        
        return {
            "status": "healthy",
            "service": "lucid-pipeline-manager",
            "version": "1.0.0",
            "active_pipelines": active_pipelines,
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Health check failed")

@app.get("/status")
async def get_service_status():
    """Get detailed service status"""
    global pipeline_manager
    
    if not pipeline_manager:
        raise HTTPException(status_code=503, detail="Pipeline manager not initialized")
    
    try:
        # Get pipeline manager status
        active_pipelines = {}
        for session_id, pipeline in pipeline_manager.active_pipelines.items():
            active_pipelines[session_id] = {
                "pipeline_id": pipeline.pipeline_id,
                "state": pipeline.current_state.value,
                "created_at": pipeline.created_at.isoformat(),
                "started_at": pipeline.started_at.isoformat() if pipeline.started_at else None,
                "error_message": pipeline.error_message
            }
        
        return {
            "service": "lucid-pipeline-manager",
            "status": "running",
            "active_pipelines": active_pipelines,
            "total_pipelines": len(active_pipelines),
            "config": pipeline_manager.config.get_pipeline_config_dict(),
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Status check failed")

@app.post("/pipelines")
async def create_pipeline(session_id: str):
    """Create a new pipeline for a session"""
    global pipeline_manager
    
    if not pipeline_manager:
        raise HTTPException(status_code=503, detail="Pipeline manager not initialized")
    
    try:
        pipeline_id = await pipeline_manager.create_pipeline(session_id)
        
        logger = get_logger(__name__)
        logger.info(f"Created pipeline {pipeline_id} for session {session_id}")
        
        return {
            "session_id": session_id,
            "pipeline_id": pipeline_id,
            "status": "created",
            "message": "Pipeline created successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Failed to create pipeline for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create pipeline")

@app.post("/pipelines/{session_id}/start")
async def start_pipeline(session_id: str):
    """Start a pipeline for a session"""
    global pipeline_manager
    
    if not pipeline_manager:
        raise HTTPException(status_code=503, detail="Pipeline manager not initialized")
    
    try:
        success = await pipeline_manager.start_pipeline(session_id)
        
        if success:
            logger = get_logger(__name__)
            logger.info(f"Started pipeline for session {session_id}")
            
            return {
                "session_id": session_id,
                "status": "started",
                "message": "Pipeline started successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to start pipeline")
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Failed to start pipeline for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start pipeline")

@app.post("/pipelines/{session_id}/stop")
async def stop_pipeline(session_id: str):
    """Stop a pipeline for a session"""
    global pipeline_manager
    
    if not pipeline_manager:
        raise HTTPException(status_code=503, detail="Pipeline manager not initialized")
    
    try:
        success = await pipeline_manager.stop_pipeline(session_id)
        
        if success:
            logger = get_logger(__name__)
            logger.info(f"Stopped pipeline for session {session_id}")
            
            return {
                "session_id": session_id,
                "status": "stopped",
                "message": "Pipeline stopped successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to stop pipeline")
            
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Failed to stop pipeline for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to stop pipeline")

@app.get("/pipelines/{session_id}/status")
async def get_pipeline_status(session_id: str):
    """Get pipeline status for a session"""
    global pipeline_manager
    
    if not pipeline_manager:
        raise HTTPException(status_code=503, detail="Pipeline manager not initialized")
    
    try:
        status = await pipeline_manager.get_pipeline_status(session_id)
        
        if status is None:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        
        return status
        
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Failed to get pipeline status for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get pipeline status")

@app.delete("/pipelines/{session_id}")
async def cleanup_pipeline(session_id: str):
    """Clean up pipeline resources for a session"""
    global pipeline_manager
    
    if not pipeline_manager:
        raise HTTPException(status_code=503, detail="Pipeline manager not initialized")
    
    try:
        success = await pipeline_manager.cleanup_pipeline(session_id)
        
        if success:
            logger = get_logger(__name__)
            logger.info(f"Cleaned up pipeline for session {session_id}")
            
            return {
                "session_id": session_id,
                "status": "cleaned_up",
                "message": "Pipeline cleaned up successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to cleanup pipeline")
            
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Failed to cleanup pipeline for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cleanup pipeline")

@app.post("/pipelines/{session_id}/chunks")
async def process_chunk(session_id: str, chunk_data: bytes, chunk_metadata: dict = None):
    """Process a chunk through the pipeline"""
    global pipeline_manager
    
    if not pipeline_manager:
        raise HTTPException(status_code=503, detail="Pipeline manager not initialized")
    
    try:
        metadata = chunk_metadata or {}
        success = await pipeline_manager.process_chunk(session_id, chunk_data, metadata)
        
        if success:
            return {
                "session_id": session_id,
                "status": "processed",
                "message": "Chunk processed successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to process chunk")
            
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Failed to process chunk for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process chunk")

@app.get("/config")
async def get_configuration():
    """Get pipeline configuration"""
    global pipeline_manager
    
    if not pipeline_manager:
        raise HTTPException(status_code=503, detail="Pipeline manager not initialized")
    
    try:
        return pipeline_manager.config.get_pipeline_config_dict()
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Failed to get configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get configuration")

@app.get("/metrics")
async def get_metrics():
    """Get pipeline metrics"""
    global pipeline_manager
    
    if not pipeline_manager:
        raise HTTPException(status_code=503, detail="Pipeline manager not initialized")
    
    try:
        metrics = {
            "active_pipelines": len(pipeline_manager.active_pipelines),
            "total_workers": sum(
                len(workers) for workers in pipeline_manager.pipeline_workers.values()
            ),
            "pipeline_states": {},
            "stage_metrics": {},
            "integrations": {}
        }
        
        # Collect state statistics
        state_counts = {}
        for pipeline in pipeline_manager.active_pipelines.values():
            state = pipeline.current_state.value
            state_counts[state] = state_counts.get(state, 0) + 1
        
        metrics["pipeline_states"] = state_counts
        
        # Collect stage metrics
        for session_id, pipeline in pipeline_manager.active_pipelines.items():
            for stage in pipeline.stages:
                stage_key = f"{stage.stage_name}_{stage.stage_type}"
                if stage_key not in metrics["stage_metrics"]:
                    metrics["stage_metrics"][stage_key] = {
                        "total_chunks_processed": 0,
                        "total_errors": 0,
                        "average_processing_time_ms": 0.0,
                        "throughput_chunks_per_second": 0.0
                    }
                
                stage_metrics = metrics["stage_metrics"][stage_key]
                stage_metrics["total_chunks_processed"] += stage.metrics.total_chunks_processed
                stage_metrics["total_errors"] += stage.metrics.error_count
                stage_metrics["average_processing_time_ms"] += stage.metrics.average_processing_time_ms
                stage_metrics["throughput_chunks_per_second"] += stage.metrics.throughput_chunks_per_second
        
        # Collect integration service health
        if hasattr(pipeline_manager, 'integrations') and pipeline_manager.integrations:
            try:
                integration_health = await pipeline_manager.integrations.health_check_all()
                metrics["integrations"] = integration_health
            except Exception as e:
                logger.warning(f"Failed to get integration health: {str(e)}")
                metrics["integrations"] = {"error": str(e)}
        
        return metrics
        
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Failed to get metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")

def main():
    """Main entry point"""
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    try:
        # Load configuration
        config = PipelineSettings()
        
        logger.info(f"Starting Lucid Pipeline Manager on {config.HOST}:{config.PORT}")
        
        # Run the application
        uvicorn.run(
            "sessions.pipeline.main:app",
            host=config.HOST,
            port=config.PORT,
            reload=config.DEBUG,
            log_level=config.LOG_LEVEL.lower(),
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Failed to start Pipeline Manager: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
