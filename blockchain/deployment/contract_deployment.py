# LUCID Contract Deployment - Smart contract deployment service
# LUCID-STRICT Layer 2 Service Integration
# Multi-platform support for Pi 5 ARM64

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import httpx

# Payment service integration (handled separately)
# Payment operations are isolated to payment service cluster

# Database integration
try:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
    HAS_MOTOR = True
except ImportError:
    HAS_MOTOR = False
    AsyncIOMotorClient = None
    AsyncIOMotorDatabase = None

logger = logging.getLogger(__name__)

# Configuration from environment (required)
MONGODB_URL = os.getenv("MONGODB_URL") or os.getenv("MONGO_URL")
if not MONGODB_URL:
    raise RuntimeError("MONGODB_URL or MONGO_URL environment variable not set")
CONTRACT_ARTIFACTS_PATH = Path(os.getenv("CONTRACT_ARTIFACTS_PATH", "/data/contracts"))
DEPLOYMENT_LOG_PATH = Path(os.getenv("DEPLOYMENT_LOG_PATH", "/data/logs"))


class DeploymentStatus(Enum):
    """Contract deployment status states"""
    PENDING = "pending"
    COMPILING = "compiling"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"
    VERIFIED = "verified"


@dataclass
class ContractDeployment:
    """Contract deployment metadata"""
    deployment_id: str
    contract_name: str
    contract_version: str
    network: str
    status: DeploymentStatus
    created_at: datetime
    deployed_at: Optional[datetime] = None
    contract_address: Optional[str] = None
    transaction_hash: Optional[str] = None
    gas_used: Optional[int] = None
    deployment_cost: Optional[float] = None
    artifacts_path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContractDeploymentService:
    """
    Smart contract deployment service for Lucid blockchain system.
    
    Handles On-System Chain smart contract compilation, deployment, and verification.
    Implements LUCID-STRICT Layer 2 Service Integration requirements.
    """
    
    def __init__(self):
        """Initialize contract deployment service"""
        self.app = FastAPI(
            title="Lucid Contract Deployment",
            description="Smart contract deployment service for Lucid blockchain system",
            version="1.0.0"
        )
        
        # Database connection
        self.db_client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        
        # Payment service integration (handled separately)
        
        # Deployment tracking
        self.active_deployments: Dict[str, ContractDeployment] = {}
        self.deployment_tasks: Dict[str, asyncio.Task] = {}
        
        # Setup routes
        self._setup_routes()
        
        # Create directories
        self._create_directories()
    
    def _create_directories(self) -> None:
        """Create required directories"""
        for path in [CONTRACT_ARTIFACTS_PATH, DEPLOYMENT_LOG_PATH]:
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {path}")
    
    def _setup_routes(self) -> None:
        """Setup FastAPI routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "service": "contract-deployment",
                "active_deployments": len(self.active_deployments)
            }
        
        @self.app.post("/deployments/create")
        async def create_deployment(request: CreateDeploymentRequest):
            """Create new contract deployment"""
            return await self.create_deployment(
                contract_name=request.contract_name,
                contract_version=request.contract_version,
                network=request.network,
                metadata=request.metadata
            )
        
        @self.app.get("/deployments/{deployment_id}")
        async def get_deployment(deployment_id: str):
            """Get deployment information"""
            if deployment_id not in self.active_deployments:
                raise HTTPException(404, "Deployment not found")
            
            deployment = self.active_deployments[deployment_id]
            return {
                "deployment_id": deployment.deployment_id,
                "contract_name": deployment.contract_name,
                "status": deployment.status.value,
                "created_at": deployment.created_at.isoformat(),
                "deployed_at": deployment.deployed_at.isoformat() if deployment.deployed_at else None,
                "contract_address": deployment.contract_address,
                "transaction_hash": deployment.transaction_hash
            }
        
        @self.app.post("/deployments/{deployment_id}/deploy")
        async def deploy_contract(deployment_id: str):
            """Deploy contract to blockchain"""
            return await self.deploy_contract(deployment_id)
        
        @self.app.get("/deployments")
        async def list_deployments():
            """List all deployments"""
            return {
                "deployments": [
                    {
                        "deployment_id": deployment.deployment_id,
                        "contract_name": deployment.contract_name,
                        "status": deployment.status.value,
                        "created_at": deployment.created_at.isoformat()
                    }
                    for deployment in self.active_deployments.values()
                ]
            }
        
        @self.app.get("/contracts/{contract_address}")
        async def get_contract_info(contract_address: str):
            """Get deployed contract information"""
            return await self.get_contract_info(contract_address)
    
    async def _setup_database(self) -> None:
        """Setup database connection"""
        if not HAS_MOTOR:
            logger.warning("Motor not available, database operations disabled")
            return
        
        try:
            self.db_client = AsyncIOMotorClient(MONGODB_URL)
            self.db = self.db_client.lucid
            
            # Test connection
            await self.db_client.admin.command('ping')
            logger.info("Database connection established")
            
            # Create indexes
            await self._create_database_indexes()
            
        except Exception as e:
            logger.error(f"Database setup failed: {e}")
            self.db_client = None
            self.db = None
    
    
    async def _create_database_indexes(self) -> None:
        """Create database indexes for contract deployments"""
        if not self.db:
            return
        
        try:
            # Contract deployments collection
            await self.db.contract_deployments.create_index("deployment_id", unique=True)
            await self.db.contract_deployments.create_index("contract_name")
            await self.db.contract_deployments.create_index("status")
            await self.db.contract_deployments.create_index("created_at")
            await self.db.contract_deployments.create_index("contract_address")
            
            logger.info("Database indexes created")
            
        except Exception as e:
            logger.error(f"Database index creation failed: {e}")
    
    async def create_deployment(self, 
                              contract_name: str, 
                              contract_version: str,
                              network: str = None,
                              metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create new contract deployment"""
        try:
            # Generate deployment ID
            deployment_id = f"deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
            
            # Create deployment object
            deployment = ContractDeployment(
                deployment_id=deployment_id,
                contract_name=contract_name,
                contract_version=contract_version,
                network=network or "on_system_chain",
                status=DeploymentStatus.PENDING,
                created_at=datetime.now(timezone.utc),
                artifacts_path=CONTRACT_ARTIFACTS_PATH / deployment_id,
                metadata=metadata or {}
            )
            
            # Create artifacts directory
            deployment.artifacts_path.mkdir(parents=True, exist_ok=True)
            
            # Store in memory
            self.active_deployments[deployment_id] = deployment
            
            # Store in database
            if self.db:
                await self.db.contract_deployments.insert_one(deployment.__dict__)
            
            logger.info(f"Created contract deployment: {deployment_id}")
            
            return {
                "deployment_id": deployment_id,
                "contract_name": contract_name,
                "status": deployment.status.value,
                "created_at": deployment.created_at.isoformat(),
                "artifacts_path": str(deployment.artifacts_path)
            }
            
        except Exception as e:
            logger.error(f"Deployment creation failed: {e}")
            raise HTTPException(500, f"Deployment creation failed: {str(e)}")
    
    async def deploy_contract(self, deployment_id: str) -> Dict[str, Any]:
        """Deploy contract to blockchain"""
        if deployment_id not in self.active_deployments:
            raise HTTPException(404, "Deployment not found")
        
        deployment = self.active_deployments[deployment_id]
        
        try:
            # Update status
            deployment.status = DeploymentStatus.DEPLOYING
            
            # Start deployment task
            task = asyncio.create_task(self._run_contract_deployment(deployment))
            self.deployment_tasks[deployment_id] = task
            
            # Update database
            if self.db:
                await self.db.contract_deployments.update_one(
                    {"deployment_id": deployment_id},
                    {"$set": {"status": deployment.status.value}}
                )
            
            logger.info(f"Started contract deployment: {deployment_id}")
            
            return {
                "deployment_id": deployment_id,
                "status": deployment.status.value,
                "message": "Deployment started"
            }
            
        except Exception as e:
            logger.error(f"Contract deployment failed: {e}")
            deployment.status = DeploymentStatus.FAILED
            raise HTTPException(500, f"Contract deployment failed: {str(e)}")
    
    async def _run_contract_deployment(self, deployment: ContractDeployment) -> None:
        """Run contract deployment (simulated)"""
        try:
            logger.info(f"Running contract deployment: {deployment.deployment_id}")
            
            # Simulate compilation
            deployment.status = DeploymentStatus.COMPILING
            await asyncio.sleep(5)  # Simulate compilation time
            
            # Simulate deployment
            deployment.status = DeploymentStatus.DEPLOYING
            await asyncio.sleep(10)  # Simulate deployment time
            
            # Simulate successful deployment
            deployment.status = DeploymentStatus.DEPLOYED
            deployment.deployed_at = datetime.now(timezone.utc)
            deployment.contract_address = f"T{os.urandom(20).hex()}"
            deployment.transaction_hash = f"0x{os.urandom(32).hex()}"
            deployment.gas_used = 1000000
            deployment.deployment_cost = 0.1
            
            # Update database
            if self.db:
                await self.db.contract_deployments.update_one(
                    {"deployment_id": deployment.deployment_id},
                    {"$set": {
                        "status": deployment.status.value,
                        "deployed_at": deployment.deployed_at,
                        "contract_address": deployment.contract_address,
                        "transaction_hash": deployment.transaction_hash,
                        "gas_used": deployment.gas_used,
                        "deployment_cost": deployment.deployment_cost
                    }}
                )
            
            logger.info(f"Contract deployment completed: {deployment.deployment_id}")
            
        except Exception as e:
            logger.error(f"Contract deployment error: {e}")
            deployment.status = DeploymentStatus.FAILED
    


# Pydantic models
class CreateDeploymentRequest(BaseModel):
    contract_name: str
    contract_version: str
    network: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# Global deployment service instance
deployment_service = ContractDeploymentService()

# FastAPI app instance
app = deployment_service.app

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("Starting Contract Deployment Service...")
    await deployment_service._setup_database()
    logger.info("Contract Deployment Service started")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Shutting down Contract Deployment Service...")
    
    # Cancel all deployment tasks
    for task in deployment_service.deployment_tasks.values():
        task.cancel()
    
    # Close database connection
    if deployment_service.db_client:
        deployment_service.db_client.close()
    
    logger.info("Contract Deployment Service stopped")


def main():
    """Main entry point"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[contract-deployment] %(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run server
    uvicorn.run(
        "contract_deployment:app",
        host="0.0.0.0",
        port=8090,
        log_level="info"
    )


if __name__ == "__main__":
    main()
