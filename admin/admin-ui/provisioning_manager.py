"""
LUCID Admin UI - System Provisioning Manager
Manages node provisioning, resource allocation, and system configuration
Distroless container: pickme/lucid:admin-ui:latest
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import aiofiles
import yaml
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NodeType(str, Enum):
    WORKER = "worker"
    VALIDATOR = "validator"
    RELAY = "relay"
    GATEWAY = "gateway"

class ProvisioningStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class NetworkType(str, Enum):
    SHASTA = "shasta"
    MAINNET = "mainnet"
    NILE = "nile"

@dataclass
class ResourceRequirements:
    """Resource requirements for node provisioning"""
    cpu_cores: int = 2
    memory_gb: int = 4
    storage_gb: int = 50
    network_bandwidth_mbps: int = 100
    gpu_required: bool = False
    gpu_memory_gb: int = 0

@dataclass
class NodeConfiguration:
    """Node configuration for provisioning"""
    node_id: str
    node_type: NodeType
    network: NetworkType
    resources: ResourceRequirements
    auto_approve: bool = False
    custom_config: Dict[str, Any] = None

class ProvisioningRequest(BaseModel):
    """Pydantic model for provisioning requests"""
    node_id: str = Field(..., description="Unique node identifier")
    node_type: NodeType = Field(..., description="Type of node to provision")
    network: NetworkType = Field(default=NetworkType.MAINNET, description="Blockchain network")
    resources: Dict[str, Any] = Field(default_factory=dict, description="Resource requirements")
    auto_approve: bool = Field(default=False, description="Auto-approve provisioning")
    custom_config: Dict[str, Any] = Field(default_factory=dict, description="Custom configuration")

class ProvisioningStatusResponse(BaseModel):
    """Response model for provisioning status"""
    request_id: str
    status: ProvisioningStatus
    progress: int = Field(ge=0, le=100, description="Progress percentage")
    message: str
    created_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime] = None
    error_details: Optional[str] = None

class ProvisioningManager:
    """Manages node provisioning and system configuration"""
    
    def __init__(self):
        # Data storage paths - configured via environment variables
        base_data_dir = Path(os.getenv("ADMIN_DATA_DIR", "/app/data"))
        self.data_dir = Path(os.getenv("ADMIN_PROVISIONING_DIR", str(base_data_dir / "provisioning")))
        self.config_dir = Path(os.getenv("ADMIN_CONFIG_DIR", str(base_data_dir / "configs")))
        self.logs_dir = Path(os.getenv("ADMIN_LOGS_DIR", str(base_data_dir / "logs")))
        self.templates_dir = Path(os.getenv("ADMIN_TEMPLATES_DIR", str(base_data_dir / "templates")))
        
        # Ensure directories exist
        for directory in [self.data_dir, self.config_dir, self.logs_dir, self.templates_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Configuration - all values must be provided via environment variables
        self.mongodb_url = os.getenv("MONGODB_URL") or os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
        self.api_gateway_url = os.getenv("API_GATEWAY_URL")
        self.blockchain_api_url = os.getenv("BLOCKCHAIN_API_URL") or os.getenv("BLOCKCHAIN_ENGINE_URL") or os.getenv("BLOCKCHAIN_URL")
        
        if not self.mongodb_url:
            raise ValueError("MONGODB_URL, MONGODB_URI, or MONGO_URI environment variable must be set")
        if not self.api_gateway_url:
            raise ValueError("API_GATEWAY_URL environment variable must be set")
        if not self.blockchain_api_url:
            raise ValueError("BLOCKCHAIN_API_URL, BLOCKCHAIN_ENGINE_URL, or BLOCKCHAIN_URL environment variable must be set")
        
        # Provisioning state
        self.active_provisioning: Dict[str, ProvisioningStatusResponse] = {}
        self.provisioning_queue: List[str] = []
        
        # Load existing provisioning state
        asyncio.create_task(self._load_provisioning_state())
    
    async def _load_provisioning_state(self):
        """Load existing provisioning state from disk"""
        try:
            state_file = self.data_dir / "provisioning_state.json"
            if state_file.exists():
                async with aiofiles.open(state_file, "r") as f:
                    data = await f.read()
                    state = json.loads(data)
                    
                    # Restore active provisioning
                    for request_id, status_data in state.get("active_provisioning", {}).items():
                        self.active_provisioning[request_id] = ProvisioningStatusResponse(**status_data)
                    
                    # Restore queue
                    self.provisioning_queue = state.get("provisioning_queue", [])
                    
                logger.info(f"Loaded provisioning state: {len(self.active_provisioning)} active, {len(self.provisioning_queue)} queued")
        except Exception as e:
            logger.error(f"Error loading provisioning state: {e}")
    
    async def _save_provisioning_state(self):
        """Save current provisioning state to disk"""
        try:
            state = {
                "active_provisioning": {k: asdict(v) for k, v in self.active_provisioning.items()},
                "provisioning_queue": self.provisioning_queue,
                "last_updated": datetime.now().isoformat()
            }
            
            state_file = self.data_dir / "provisioning_state.json"
            async with aiofiles.open(state_file, "w") as f:
                await f.write(json.dumps(state, indent=2, default=str))
                
        except Exception as e:
            logger.error(f"Error saving provisioning state: {e}")
    
    async def create_provisioning_request(self, request: ProvisioningRequest) -> str:
        """Create a new provisioning request"""
        try:
            request_id = f"req_{int(time.time())}_{request.node_id}"
            
            # Validate request
            await self._validate_provisioning_request(request)
            
            # Create status response
            status_response = ProvisioningStatusResponse(
                request_id=request_id,
                status=ProvisioningStatus.PENDING,
                progress=0,
                message="Provisioning request created",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                estimated_completion=datetime.now() + timedelta(minutes=10)
            )
            
            # Add to active provisioning
            self.active_provisioning[request_id] = status_response
            
            # Add to queue
            self.provisioning_queue.append(request_id)
            
            # Save state
            await self._save_provisioning_state()
            
            # Log request
            await self._log_provisioning_event(request_id, "request_created", {
                "node_id": request.node_id,
                "node_type": request.node_type,
                "network": request.network
            })
            
            # Start provisioning process
            asyncio.create_task(self._process_provisioning_queue())
            
            logger.info(f"Created provisioning request: {request_id} for node: {request.node_id}")
            return request_id
            
        except Exception as e:
            logger.error(f"Error creating provisioning request: {e}")
            raise
    
    async def _validate_provisioning_request(self, request: ProvisioningRequest):
        """Validate provisioning request"""
        # Check if node ID already exists
        if await self._node_exists(request.node_id):
            raise ValueError(f"Node {request.node_id} already exists")
        
        # Validate resource requirements
        if request.resources:
            required_fields = ["cpu_cores", "memory_gb", "storage_gb"]
            for field in required_fields:
                if field not in request.resources:
                    raise ValueError(f"Missing required resource field: {field}")
        
        # Validate network configuration
        if request.network not in [NetworkType.SHASTA, NetworkType.MAINNET, NetworkType.NILE]:
            raise ValueError(f"Invalid network: {request.network}")
    
    async def _node_exists(self, node_id: str) -> bool:
        """Check if node already exists"""
        # This would check MongoDB in production
        return False
    
    async def _process_provisioning_queue(self):
        """Process provisioning queue"""
        while self.provisioning_queue:
            request_id = self.provisioning_queue.pop(0)
            
            try:
                await self._provision_node(request_id)
            except Exception as e:
                logger.error(f"Error provisioning node {request_id}: {e}")
                # Update status to failed
                if request_id in self.active_provisioning:
                    self.active_provisioning[request_id].status = ProvisioningStatus.FAILED
                    self.active_provisioning[request_id].error_details = str(e)
                    self.active_provisioning[request_id].updated_at = datetime.now()
                    await self._save_provisioning_state()
    
    async def _provision_node(self, request_id: str):
        """Provision a node"""
        if request_id not in self.active_provisioning:
            logger.error(f"Provisioning request not found: {request_id}")
            return
        
        status_response = self.active_provisioning[request_id]
        
        try:
            # Update status to in progress
            status_response.status = ProvisioningStatus.IN_PROGRESS
            status_response.progress = 10
            status_response.message = "Starting node provisioning"
            status_response.updated_at = datetime.now()
            await self._save_provisioning_state()
            
            # Step 1: Create node configuration
            await self._create_node_configuration(request_id)
            status_response.progress = 25
            status_response.message = "Node configuration created"
            await self._save_provisioning_state()
            
            # Step 2: Allocate resources
            await self._allocate_resources(request_id)
            status_response.progress = 50
            status_response.message = "Resources allocated"
            await self._save_provisioning_state()
            
            # Step 3: Deploy node container
            await self._deploy_node_container(request_id)
            status_response.progress = 75
            status_response.message = "Node container deployed"
            await self._save_provisioning_state()
            
            # Step 4: Initialize node services
            await self._initialize_node_services(request_id)
            status_response.progress = 90
            status_response.message = "Node services initialized"
            await self._save_provisioning_state()
            
            # Step 5: Verify deployment
            await self._verify_node_deployment(request_id)
            status_response.progress = 100
            status_response.status = ProvisioningStatus.COMPLETED
            status_response.message = "Node provisioning completed successfully"
            status_response.updated_at = datetime.now()
            await self._save_provisioning_state()
            
            # Log success
            await self._log_provisioning_event(request_id, "provisioning_completed", {
                "status": "success"
            })
            
            logger.info(f"Successfully provisioned node: {request_id}")
            
        except Exception as e:
            # Update status to failed
            status_response.status = ProvisioningStatus.FAILED
            status_response.error_details = str(e)
            status_response.message = f"Provisioning failed: {str(e)}"
            status_response.updated_at = datetime.now()
            await self._save_provisioning_state()
            
            # Log failure
            await self._log_provisioning_event(request_id, "provisioning_failed", {
                "error": str(e)
            })
            
            logger.error(f"Failed to provision node {request_id}: {e}")
            raise
    
    async def _create_node_configuration(self, request_id: str):
        """Create node configuration files"""
        try:
            status_response = self.active_provisioning[request_id]
            
            # Load template
            template_file = self.templates_dir / f"{status_response.node_type}_template.yaml"
            if not template_file.exists():
                # Create default template
                await self._create_default_template(status_response.node_type)
            
            # Read template
            async with aiofiles.open(template_file, "r") as f:
                template_content = await f.read()
            
            # Generate configuration
            config = yaml.safe_load(template_content)
            config["node_id"] = status_response.node_id
            config["network"] = status_response.network
            config["resources"] = status_response.resources
            
            # Save configuration
            config_file = self.config_dir / f"{request_id}_config.yaml"
            async with aiofiles.open(config_file, "w") as f:
                await f.write(yaml.dump(config, default_flow_style=False))
            
            logger.info(f"Created node configuration: {config_file}")
            
        except Exception as e:
            logger.error(f"Error creating node configuration: {e}")
            raise
    
    async def _create_default_template(self, node_type: str):
        """Create default template for node type"""
        templates = {
            "worker": {
                "node_type": "worker",
                "services": ["session_processor", "chunk_handler", "encryption"],
                "resources": {
                    "cpu_cores": 2,
                    "memory_gb": 4,
                    "storage_gb": 50
                },
                "network": {
                    "ports": [8090, 8091, 8092],
                    "protocols": ["http", "websocket"]
                }
            },
            "validator": {
                "node_type": "validator",
                "services": ["consensus", "validation", "block_producer"],
                "resources": {
                    "cpu_cores": 4,
                    "memory_gb": 8,
                    "storage_gb": 100
                },
                "network": {
                    "ports": [
                        int(os.getenv("ADMIN_INTERFACE_PORT", "8120")),
                        int(os.getenv("NODE_MANAGEMENT_PORT", "8095"))
                    ],
                    "protocols": ["p2p", "rpc"]
                }
            },
            "relay": {
                "node_type": "relay",
                "services": ["message_relay", "peer_discovery", "routing"],
                "resources": {
                    "cpu_cores": 1,
                    "memory_gb": 2,
                    "storage_gb": 20
                },
                "network": {
                    "ports": [7000, 7001],
                    "protocols": ["p2p", "relay"]
                }
            }
        }
        
        template = templates.get(node_type, templates["worker"])
        template_file = self.templates_dir / f"{node_type}_template.yaml"
        
        async with aiofiles.open(template_file, "w") as f:
            await f.write(yaml.dump(template, default_flow_style=False))
    
    async def _allocate_resources(self, request_id: str):
        """Allocate resources for node"""
        try:
            # This would integrate with container orchestration in production
            # For now, simulate resource allocation
            await asyncio.sleep(1)
            
            # Log resource allocation
            await self._log_provisioning_event(request_id, "resources_allocated", {
                "cpu_cores": 2,
                "memory_gb": 4,
                "storage_gb": 50
            })
            
            logger.info(f"Allocated resources for node: {request_id}")
            
        except Exception as e:
            logger.error(f"Error allocating resources: {e}")
            raise
    
    async def _deploy_node_container(self, request_id: str):
        """Deploy node container"""
        try:
            # This would use Docker/Kubernetes in production
            # For now, simulate container deployment
            await asyncio.sleep(2)
            
            # Log container deployment
            await self._log_provisioning_event(request_id, "container_deployed", {
                "container_id": f"lucid_{request_id}",
                "image": "pickme/lucid:node-worker:latest"
            })
            
            logger.info(f"Deployed container for node: {request_id}")
            
        except Exception as e:
            logger.error(f"Error deploying container: {e}")
            raise
    
    async def _initialize_node_services(self, request_id: str):
        """Initialize node services"""
        try:
            # This would start node services in production
            # For now, simulate service initialization
            await asyncio.sleep(1)
            
            # Log service initialization
            await self._log_provisioning_event(request_id, "services_initialized", {
                "services": ["session_processor", "chunk_handler", "encryption"]
            })
            
            logger.info(f"Initialized services for node: {request_id}")
            
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            raise
    
    async def _verify_node_deployment(self, request_id: str):
        """Verify node deployment"""
        try:
            # This would perform health checks in production
            # For now, simulate verification
            await asyncio.sleep(1)
            
            # Log verification
            await self._log_provisioning_event(request_id, "deployment_verified", {
                "health_status": "healthy",
                "services_status": "running"
            })
            
            logger.info(f"Verified deployment for node: {request_id}")
            
        except Exception as e:
            logger.error(f"Error verifying deployment: {e}")
            raise
    
    async def get_provisioning_status(self, request_id: str) -> Optional[ProvisioningStatusResponse]:
        """Get provisioning status for a request"""
        return self.active_provisioning.get(request_id)
    
    async def get_all_provisioning_status(self) -> List[ProvisioningStatusResponse]:
        """Get all provisioning statuses"""
        return list(self.active_provisioning.values())
    
    async def cancel_provisioning(self, request_id: str) -> bool:
        """Cancel a provisioning request"""
        try:
            if request_id not in self.active_provisioning:
                return False
            
            status_response = self.active_provisioning[request_id]
            
            if status_response.status in [ProvisioningStatus.COMPLETED, ProvisioningStatus.FAILED]:
                return False
            
            # Update status
            status_response.status = ProvisioningStatus.CANCELLED
            status_response.message = "Provisioning cancelled by user"
            status_response.updated_at = datetime.now()
            
            # Remove from queue if present
            if request_id in self.provisioning_queue:
                self.provisioning_queue.remove(request_id)
            
            # Save state
            await self._save_provisioning_state()
            
            # Log cancellation
            await self._log_provisioning_event(request_id, "provisioning_cancelled", {})
            
            logger.info(f"Cancelled provisioning request: {request_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling provisioning: {e}")
            return False
    
    async def _log_provisioning_event(self, request_id: str, event_type: str, data: Dict[str, Any]):
        """Log provisioning event"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,
                "event_type": event_type,
                "data": data
            }
            
            log_file = self.logs_dir / f"provisioning_{datetime.now().strftime('%Y%m%d')}.log"
            async with aiofiles.open(log_file, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging provisioning event: {e}")
    
    async def cleanup_completed_provisioning(self, max_age_hours: int = 24):
        """Clean up completed provisioning requests older than max_age_hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            to_remove = []
            for request_id, status_response in self.active_provisioning.items():
                if (status_response.status in [ProvisioningStatus.COMPLETED, ProvisioningStatus.FAILED, ProvisioningStatus.CANCELLED] 
                    and status_response.updated_at < cutoff_time):
                    to_remove.append(request_id)
            
            for request_id in to_remove:
                del self.active_provisioning[request_id]
            
            if to_remove:
                await self._save_provisioning_state()
                logger.info(f"Cleaned up {len(to_remove)} completed provisioning requests")
                
        except Exception as e:
            logger.error(f"Error cleaning up provisioning requests: {e}")

# Global provisioning manager instance
provisioning_manager = ProvisioningManager()

# Convenience functions for external use
async def create_provisioning_request(request: ProvisioningRequest) -> str:
    """Create a new provisioning request"""
    return await provisioning_manager.create_provisioning_request(request)

async def get_provisioning_status(request_id: str) -> Optional[ProvisioningStatusResponse]:
    """Get provisioning status for a request"""
    return await provisioning_manager.get_provisioning_status(request_id)

async def get_all_provisioning_status() -> List[ProvisioningStatusResponse]:
    """Get all provisioning statuses"""
    return await provisioning_manager.get_all_provisioning_status()

async def cancel_provisioning(request_id: str) -> bool:
    """Cancel a provisioning request"""
    return await provisioning_manager.cancel_provisioning(request_id)

if __name__ == "__main__":
    # Example usage
    async def main():
        # Create a provisioning request
        request = ProvisioningRequest(
            node_id="test-node-001",
            node_type=NodeType.WORKER,
            network=NetworkType.SHASTA,
            resources={
                "cpu_cores": 2,
                "memory_gb": 4,
                "storage_gb": 50
            }
        )
        
        request_id = await create_provisioning_request(request)
        print(f"Created provisioning request: {request_id}")
        
        # Check status
        status = await get_provisioning_status(request_id)
        print(f"Status: {status}")
    
    asyncio.run(main())
