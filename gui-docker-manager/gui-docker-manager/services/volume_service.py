"""
Volume Service Business Logic
File: gui-docker-manager/gui-docker-manager/services/volume_service.py

Handles Docker volume management operations.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from ..integration.docker_client import DockerClientAsync
from ..models.volume import VolumeInfo, VolumeContainer, VolumeUsage

logger = logging.getLogger(__name__)


class VolumeService:
    """Business logic for Docker volume operations"""

    def __init__(self, docker_client: DockerClientAsync):
        """Initialize volume service"""
        self.docker_client = docker_client

    async def list_volumes(self, filters: Optional[Dict[str, str]] = None) -> List[VolumeInfo]:
        """
        List Docker volumes

        Args:
            filters: Optional filters

        Returns:
            List of VolumeInfo objects
        """
        try:
            volumes = await self.docker_client.list_volumes(filters=filters)
            return [self._parse_volume_info(vol) for vol in volumes]
        except Exception as e:
            logger.error(f"Failed to list volumes: {e}")
            raise

    async def get_volume(self, volume_name: str) -> VolumeInfo:
        """
        Get volume details

        Args:
            volume_name: Volume name

        Returns:
            VolumeInfo object
        """
        try:
            volume = await self.docker_client.get_volume(volume_name)
            return self._parse_volume_info(volume)
        except Exception as e:
            logger.error(f"Failed to get volume {volume_name}: {e}")
            raise

    async def create_volume(
        self,
        name: str,
        driver: str = "local",
        driver_options: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new Docker volume

        Args:
            name: Volume name
            driver: Volume driver
            driver_options: Driver options
            labels: Volume labels

        Returns:
            Volume creation result
        """
        try:
            logger.info(f"Creating volume: {name} with driver {driver}")
            result = await self.docker_client.create_volume(
                name=name,
                driver=driver,
                driver_options=driver_options,
                labels=labels
            )
            return result
        except Exception as e:
            logger.error(f"Failed to create volume {name}: {e}")
            raise

    async def remove_volume(self, volume_name: str, force: bool = False) -> Dict[str, Any]:
        """
        Remove a Docker volume

        Args:
            volume_name: Volume name
            force: Force removal

        Returns:
            Removal result
        """
        try:
            logger.info(f"Removing volume: {volume_name}")
            result = await self.docker_client.remove_volume(volume_name, force=force)
            return result
        except Exception as e:
            logger.error(f"Failed to remove volume {volume_name}: {e}")
            raise

    async def inspect_volume(self, volume_name: str) -> Dict[str, Any]:
        """
        Inspect volume details

        Args:
            volume_name: Volume name

        Returns:
            Volume inspection result
        """
        try:
            result = await self.docker_client.inspect_volume(volume_name)
            return result
        except Exception as e:
            logger.error(f"Failed to inspect volume {volume_name}: {e}")
            raise

    async def prune_volumes(self) -> Dict[str, Any]:
        """
        Prune unused volumes

        Returns:
            Prune result
        """
        try:
            logger.info("Pruning unused volumes")
            result = await self.docker_client.prune_volumes()
            return result
        except Exception as e:
            logger.error(f"Failed to prune volumes: {e}")
            raise

    @staticmethod
    def _parse_volume_info(volume_data: Dict[str, Any]) -> VolumeInfo:
        """Parse raw volume data into VolumeInfo object"""
        usage_data = volume_data.get("UsageData")
        usage = None
        if usage_data:
            usage = VolumeUsage(
                size_bytes=usage_data.get("Size"),
                ref_count=usage_data.get("RefCount", 0)
            )

        # Parse containers using this volume
        containers = []
        if volume_data.get("Containers"):
            for container_id, container_info in volume_data.get("Containers", {}).items():
                containers.append(
                    VolumeContainer(
                        container_id=container_id,
                        container_name=container_info.get("Name"),
                        mount_path=container_info.get("MountPath", ""),
                        read_only=container_info.get("ReadOnly", False)
                    )
                )

        return VolumeInfo(
            name=volume_data.get("Name", ""),
            driver=volume_data.get("Driver", "local"),
            driver_options=volume_data.get("DriverOpts", {}),
            mountpoint=volume_data.get("Mountpoint", ""),
            labels=volume_data.get("Labels", {}),
            scope=volume_data.get("Scope", "local"),
            created=volume_data.get("Created", datetime.utcnow()),
            containers=containers,
            usage=usage
        )
