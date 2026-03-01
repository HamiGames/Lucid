"""
Network Service Business Logic
File: gui-docker-manager/gui-docker-manager/services/network_service.py

Handles Docker network management operations.
"""

import logging
from typing import Dict, List, Any, Optional
from ..integration.docker_client import DockerClientAsync
from ..models.network import NetworkInfo, NetworkConnectedContainer

logger = logging.getLogger(__name__)


class NetworkService:
    """Business logic for Docker network operations"""

    def __init__(self, docker_client: DockerClientAsync):
        """Initialize network service"""
        self.docker_client = docker_client

    async def list_networks(self, filters: Optional[Dict[str, str]] = None) -> List[NetworkInfo]:
        """
        List Docker networks

        Args:
            filters: Optional filters (e.g., {"driver": "bridge"})

        Returns:
            List of NetworkInfo objects
        """
        try:
            networks = await self.docker_client.list_networks(filters=filters)
            return [self._parse_network_info(net) for net in networks]
        except Exception as e:
            logger.error(f"Failed to list networks: {e}")
            raise

    async def get_network(self, network_id: str) -> NetworkInfo:
        """
        Get network details

        Args:
            network_id: Network ID or name

        Returns:
            NetworkInfo object
        """
        try:
            network = await self.docker_client.get_network(network_id)
            return self._parse_network_info(network)
        except Exception as e:
            logger.error(f"Failed to get network {network_id}: {e}")
            raise

    async def create_network(
        self,
        name: str,
        driver: str = "bridge",
        labels: Optional[Dict[str, str]] = None,
        subnet: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new Docker network

        Args:
            name: Network name
            driver: Network driver
            labels: Network labels
            subnet: Subnet configuration

        Returns:
            Network creation result
        """
        try:
            logger.info(f"Creating network: {name} with driver {driver}")
            result = await self.docker_client.create_network(
                name=name,
                driver=driver,
                labels=labels,
                subnet=subnet
            )
            return result
        except Exception as e:
            logger.error(f"Failed to create network {name}: {e}")
            raise

    async def remove_network(self, network_id: str) -> Dict[str, Any]:
        """
        Remove a Docker network

        Args:
            network_id: Network ID or name

        Returns:
            Removal result
        """
        try:
            logger.info(f"Removing network: {network_id}")
            result = await self.docker_client.remove_network(network_id)
            return result
        except Exception as e:
            logger.error(f"Failed to remove network {network_id}: {e}")
            raise

    async def connect_container(
        self,
        network_id: str,
        container_id: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Connect container to network

        Args:
            network_id: Network ID or name
            container_id: Container ID or name
            ip_address: Optional IP address for container

        Returns:
            Connection result
        """
        try:
            logger.info(f"Connecting container {container_id} to network {network_id}")
            result = await self.docker_client.connect_network(
                network_id=network_id,
                container_id=container_id,
                ip_address=ip_address
            )
            return result
        except Exception as e:
            logger.error(f"Failed to connect container {container_id} to network {network_id}: {e}")
            raise

    async def disconnect_container(
        self,
        network_id: str,
        container_id: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Disconnect container from network

        Args:
            network_id: Network ID or name
            container_id: Container ID or name
            force: Force disconnection

        Returns:
            Disconnection result
        """
        try:
            logger.info(f"Disconnecting container {container_id} from network {network_id}")
            result = await self.docker_client.disconnect_network(
                network_id=network_id,
                container_id=container_id,
                force=force
            )
            return result
        except Exception as e:
            logger.error(f"Failed to disconnect container {container_id} from network {network_id}: {e}")
            raise

    async def inspect_network(self, network_id: str) -> Dict[str, Any]:
        """
        Inspect network details

        Args:
            network_id: Network ID or name

        Returns:
            Network inspection result
        """
        try:
            result = await self.docker_client.inspect_network(network_id)
            return result
        except Exception as e:
            logger.error(f"Failed to inspect network {network_id}: {e}")
            raise

    @staticmethod
    def _parse_network_info(network_data: Dict[str, Any]) -> NetworkInfo:
        """Parse raw network data into NetworkInfo object"""
        containers = []
        if network_data.get("Containers"):
            for container_id, container_info in network_data["Containers"].items():
                containers.append(
                    NetworkConnectedContainer(
                        container_id=container_id,
                        container_name=container_info.get("Name"),
                        ip_address=container_info.get("IPv4Address", "").split("/")[0],
                        gateway=container_info.get("Gateway")
                    )
                )

        return NetworkInfo(
            id=network_data.get("Id", ""),
            name=network_data.get("Name", ""),
            driver=network_data.get("Driver", ""),
            scope=network_data.get("Scope", ""),
            created=network_data.get("Created"),
            subnet=network_data.get("IPAM", {}).get("Config", [{}])[0].get("Subnet"),
            gateway=network_data.get("IPAM", {}).get("Config", [{}])[0].get("Gateway"),
            containers=containers,
            labels=network_data.get("Labels", {}),
            options=network_data.get("Options", {}),
            connected_container_count=len(containers)
        )
