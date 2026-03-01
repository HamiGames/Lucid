#!/usr/bin/env python3
"""
Lucid Node Management Service - Main Application
Port: 8095
Features: Node pool management, PoOT calculation, payout threshold (10 USDT), max 100 nodes
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json
import uuid

# FastAPI imports
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Internal imports
from .node_manager import NodeManager, NodeConfig
from .poot_calculator import PoOTCalculator
from .payout_manager import PayoutManager
from .node_pool_manager import NodePoolManager
from .database_adapter import get_database_adapter, DatabaseAdapter
from .config import NodeManagementConfigManager
from .models import (
    NodeInfo, NodeStatus, PoolInfo, PayoutInfo, 
    PoOTProof, NodeMetrics, PoolMetrics
)

# Configure logging (structured logging per master design)
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
node_manager: Optional[NodeManager] = None
poot_calculator: Optional[PoOTCalculator] = None
payout_manager: Optional[PayoutManager] = None
pool_manager: Optional[NodePoolManager] = None
db_adapter: Optional[DatabaseAdapter] = None
config_manager: Optional[NodeManagementConfigManager] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global node_manager, poot_calculator, payout_manager, pool_manager, db_adapter, config_manager
    
    try:
        logger.info("Starting Lucid Node Management Service...")
        
        # Initialize configuration using Pydantic Settings (per master design)
        config_manager = NodeManagementConfigManager()
        config_dict = config_manager.get_node_management_config_dict()
        logger.info("Configuration initialized using Pydantic Settings")
        
        # Initialize database adapter
        db_adapter = await get_database_adapter()
        logger.info("Database adapter initialized")
        
        # Initialize PoOT calculator
        poot_calculator = PoOTCalculator(db_adapter)
        logger.info("PoOT calculator initialized")
        
        # Initialize payout manager
        payout_manager = PayoutManager(
            db_adapter=db_adapter,
            threshold_usdt=config_dict["payout_threshold_usdt"]
        )
        logger.info("Payout manager initialized")
        
        # Initialize node pool manager
        pool_manager = NodePoolManager(
            db_adapter=db_adapter,
            max_nodes_per_pool=config_dict["max_nodes_per_pool"]
        )
        logger.info("Node pool manager initialized")
        
        # Initialize node manager
        node_id = config_dict.get("node_id") or os.getenv("NODE_ID") or str(uuid.uuid4())
        node_config = NodeConfig(
            node_id=node_id,
            role="management",
            onion_address=config_dict.get("onion_address") or os.getenv("ONION_ADDRESS", ""),
            port=config_dict["port"],
            work_credits_enabled=True,
            relay_enabled=True
        )
        
        # Validate critical node configuration
        if not node_config.node_id:
            logger.error("NODE_ID is required but not set")
            raise ValueError("NODE_ID environment variable is required")
        
        node_manager = NodeManager(node_config, db_adapter)
        await node_manager.start()
        logger.info("Node manager started")
        
        # Start background tasks
        asyncio.create_task(periodic_poot_calculation())
        asyncio.create_task(periodic_payout_processing())
        asyncio.create_task(periodic_pool_health_check())
        
        logger.info("Lucid Node Management Service started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start Node Management Service: {e}", exc_info=True)
        raise
    finally:
        # Cleanup (graceful shutdown per master design)
        logger.info("Shutting down Lucid Node Management Service...")
        try:
            if node_manager:
                await node_manager.stop()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)
        logger.info("Lucid Node Management Service stopped")

# Create FastAPI application
app = FastAPI(
    title="Lucid Node Management Service",
    description="Node pool management, PoOT calculation, and payout processing",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

# Dependency injection
async def get_node_manager() -> NodeManager:
    if not node_manager:
        raise HTTPException(status_code=503, detail="Node manager not available")
    return node_manager

async def get_poot_calculator() -> PoOTCalculator:
    if not poot_calculator:
        raise HTTPException(status_code=503, detail="PoOT calculator not available")
    return poot_calculator

async def get_payout_manager() -> PayoutManager:
    if not payout_manager:
        raise HTTPException(status_code=503, detail="Payout manager not available")
    return payout_manager

async def get_pool_manager() -> NodePoolManager:
    if not pool_manager:
        raise HTTPException(status_code=503, detail="Pool manager not available")
    return pool_manager

# Background tasks
async def periodic_poot_calculation():
    """Periodic PoOT calculation task"""
    while True:
        try:
            if poot_calculator and config_manager:
                await poot_calculator.calculate_all_poots()
                logger.info("Periodic PoOT calculation completed")
        except Exception as e:
            logger.error(f"PoOT calculation error: {e}")
        
        # Get interval from config manager
        interval = config_manager.settings.POOT_CALCULATION_INTERVAL if config_manager else 300
        await asyncio.sleep(interval)

async def periodic_payout_processing():
    """Periodic payout processing task"""
    while True:
        try:
            if payout_manager:
                await payout_manager.process_pending_payouts()
                logger.info("Periodic payout processing completed")
        except Exception as e:
            logger.error(f"Payout processing error: {e}")
        
        # Get interval from config manager
        interval = config_manager.settings.PAYOUT_PROCESSING_INTERVAL if config_manager else 3600
        await asyncio.sleep(interval)

async def periodic_pool_health_check():
    """Periodic pool health check task"""
    while True:
        try:
            if pool_manager:
                await pool_manager.health_check_all_pools()
                logger.info("Periodic pool health check completed")
        except Exception as e:
            logger.error(f"Pool health check error: {e}")
        
        # Get interval from config manager
        interval = config_manager.settings.POOL_HEALTH_CHECK_INTERVAL if config_manager else 300
        await asyncio.sleep(interval)

# API Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {"service": "node-management", "status": "running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "node-management",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_nodes": len(node_manager.active_nodes) if node_manager and hasattr(node_manager, 'active_nodes') else 0,
        "max_nodes_per_pool": config_manager.settings.MAX_NODES_PER_POOL if config_manager else 100,
        "payout_threshold_usdt": config_manager.settings.PAYOUT_THRESHOLD_USDT if config_manager else 10.0
    }

@app.get("/metrics")
async def get_metrics(
    node_manager: NodeManager = Depends(get_node_manager),
    pool_manager: NodePoolManager = Depends(get_pool_manager)
):
    """Get system metrics"""
    try:
        node_metrics = await node_manager.get_metrics()
        pool_metrics = await pool_manager.get_metrics()
        
        return {
            "node_metrics": node_metrics,
            "pool_metrics": pool_metrics,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {e}")

# Node Management Endpoints

@app.get("/nodes", response_model=List[NodeInfo])
async def list_nodes(
    pool_id: Optional[str] = None,
    status: Optional[str] = None,
    pool_manager: NodePoolManager = Depends(get_pool_manager)
):
    """List all nodes, optionally filtered by pool and status"""
    try:
        nodes = await pool_manager.list_nodes(pool_id=pool_id, status=status)
        return nodes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list nodes: {e}")

@app.get("/nodes/{node_id}", response_model=NodeInfo)
async def get_node(
    node_id: str,
    pool_manager: NodePoolManager = Depends(get_pool_manager)
):
    """Get specific node information"""
    try:
        node = await pool_manager.get_node(node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        return node
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get node: {e}")

@app.post("/nodes/{node_id}/join-pool")
async def join_pool(
    node_id: str,
    pool_id: str,
    pool_manager: NodePoolManager = Depends(get_pool_manager)
):
    """Add node to a pool"""
    try:
        success = await pool_manager.add_node_to_pool(node_id, pool_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to add node to pool")
        return {"message": f"Node {node_id} added to pool {pool_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to join pool: {e}")

@app.post("/nodes/{node_id}/leave-pool")
async def leave_pool(
    node_id: str,
    pool_id: str,
    pool_manager: NodePoolManager = Depends(get_pool_manager)
):
    """Remove node from a pool"""
    try:
        success = await pool_manager.remove_node_from_pool(node_id, pool_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to remove node from pool")
        return {"message": f"Node {node_id} removed from pool {pool_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to leave pool: {e}")

# Pool Management Endpoints

@app.get("/pools", response_model=List[PoolInfo])
async def list_pools(
    pool_manager: NodePoolManager = Depends(get_pool_manager)
):
    """List all node pools"""
    try:
        pools = await pool_manager.list_pools()
        return pools
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list pools: {e}")

@app.get("/pools/{pool_id}", response_model=PoolInfo)
async def get_pool(
    pool_id: str,
    pool_manager: NodePoolManager = Depends(get_pool_manager)
):
    """Get specific pool information"""
    try:
        pool = await pool_manager.get_pool(pool_id)
        if not pool:
            raise HTTPException(status_code=404, detail="Pool not found")
        return pool
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pool: {e}")

@app.post("/pools")
async def create_pool(
    pool_name: str,
    max_nodes: Optional[int] = None,
    pool_manager: NodePoolManager = Depends(get_pool_manager)
):
    """Create a new node pool"""
    try:
        # Get max nodes from config manager if not provided
        if max_nodes is None:
            max_nodes = config_manager.settings.MAX_NODES_PER_POOL if config_manager else 100
        
        max_allowed = config_manager.settings.MAX_NODES_PER_POOL if config_manager else 100
        if max_nodes > max_allowed:
            raise HTTPException(
                status_code=400, 
                detail=f"Max nodes cannot exceed {max_allowed}"
            )
        
        pool_id = await pool_manager.create_pool(pool_name, max_nodes)
        return {"message": f"Pool created with ID: {pool_id}", "pool_id": pool_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create pool: {e}")

# PoOT Calculation Endpoints

@app.get("/poot/{node_id}", response_model=PoOTProof)
async def get_poot_proof(
    node_id: str,
    poot_calculator: PoOTCalculator = Depends(get_poot_calculator)
):
    """Get PoOT proof for a specific node"""
    try:
        proof = await poot_calculator.get_poot_proof(node_id)
        if not proof:
            raise HTTPException(status_code=404, detail="PoOT proof not found")
        return proof
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get PoOT proof: {e}")

@app.post("/poot/{node_id}/calculate")
async def calculate_poot(
    node_id: str,
    poot_calculator: PoOTCalculator = Depends(get_poot_calculator)
):
    """Calculate PoOT for a specific node"""
    try:
        proof = await poot_calculator.calculate_poot(node_id)
        return {"message": "PoOT calculated successfully", "proof": proof}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate PoOT: {e}")

@app.get("/poot/calculate-all")
async def calculate_all_poots(
    poot_calculator: PoOTCalculator = Depends(get_poot_calculator)
):
    """Calculate PoOT for all nodes"""
    try:
        results = await poot_calculator.calculate_all_poots()
        return {"message": "PoOT calculation completed", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate all PoOTs: {e}")

# Payout Management Endpoints

@app.get("/payouts", response_model=List[PayoutInfo])
async def list_payouts(
    node_id: Optional[str] = None,
    status: Optional[str] = None,
    payout_manager: PayoutManager = Depends(get_payout_manager)
):
    """List payouts, optionally filtered by node and status"""
    try:
        payouts = await payout_manager.list_payouts(node_id=node_id, status=status)
        return payouts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list payouts: {e}")

@app.get("/payouts/{payout_id}", response_model=PayoutInfo)
async def get_payout(
    payout_id: str,
    payout_manager: PayoutManager = Depends(get_payout_manager)
):
    """Get specific payout information"""
    try:
        payout = await payout_manager.get_payout(payout_id)
        if not payout:
            raise HTTPException(status_code=404, detail="Payout not found")
        return payout
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get payout: {e}")

@app.post("/payouts/process")
async def process_payouts(
    payout_manager: PayoutManager = Depends(get_payout_manager)
):
    """Process pending payouts"""
    try:
        results = await payout_manager.process_pending_payouts()
        return {"message": "Payout processing completed", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process payouts: {e}")

@app.get("/payouts/threshold")
async def get_payout_threshold():
    """Get current payout threshold"""
    threshold = config_manager.settings.PAYOUT_THRESHOLD_USDT if config_manager else 10.0
    return {
        "threshold_usdt": threshold,
        "description": "Minimum USDT amount required for payout processing"
    }

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    # This is only used for local development
    # In production, entrypoint.py is used
    port = int(os.getenv("NODE_MANAGEMENT_PORT", "8095"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )