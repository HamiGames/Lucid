# Path: vm/vm_manager.py

import asyncio
import logging
import docker
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


@dataclass
class VMInstance:
    vm_id: str
    name: str
    image: str
    status: str
    created_at: datetime
    ports: Dict[str, int]
    volumes: Dict[str, str]
    container_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "vm_id": self.vm_id,
            "name": self.name,
            "image": self.image,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "ports": self.ports,
            "volumes": self.volumes,
            "container_id": self.container_id
        }


class VMManager:
    """Manages lightweight VM instances using Docker containers."""
    
    def __init__(self):
        self.client = docker.from_env()
        self.instances: Dict[str, VMInstance] = {}
        
    async def create_vm(
        self,
        name: str,
        image: str = "ubuntu:22.04",
        ports: Optional[Dict] = None,
        volumes: Optional[Dict] = None
    ) -> VMInstance:
        """Create a new VM instance."""
        try:
            vm_id = str(uuid.uuid4())
            
            # Configure container
            container_config = {
                "image": image,
                "name": f"lucid-vm-{name}-{vm_id[:8]}",
                "detach": True,
                "network_mode": "lucid-vm-network"
            }
            
            if ports:
                container_config["ports"] = ports
            if volumes:
                container_config["volumes"] = volumes
                
            # Create container
            container = self.client.containers.run(**container_config)
            
            instance = VMInstance(
                vm_id=vm_id,
                name=name,
                image=image,
                status="running",
                created_at=datetime.now(timezone.utc),
                ports=ports or {},
                volumes=volumes or {},
                container_id=container.id
            )
            
            self.instances[vm_id] = instance
            logger.info(f"Created VM instance: {name}")
            return instance
            
        except Exception as e:
            logger.error(f"Failed to create VM: {e}")
            raise
            
    async def stop_vm(self, vm_id: str) -> bool:
        """Stop VM instance."""
        try:
            if vm_id not in self.instances:
                return False
                
            instance = self.instances[vm_id]
            container = self.client.containers.get(instance.container_id)
            container.stop()
            
            instance.status = "stopped"
            logger.info(f"Stopped VM: {instance.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop VM: {e}")
            return False
            
    async def remove_vm(self, vm_id: str) -> bool:
        """Remove VM instance."""
        try:
            if vm_id not in self.instances:
                return False
                
            instance = self.instances[vm_id]
            container = self.client.containers.get(instance.container_id)
            container.remove(force=True)
            
            del self.instances[vm_id]
            logger.info(f"Removed VM: {instance.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove VM: {e}")
            return False
            
    async def list_vms(self) -> List[VMInstance]:
        """List all VM instances."""
        return list(self.instances.values())
