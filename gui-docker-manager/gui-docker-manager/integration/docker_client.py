"""
Async Docker Client for Container Management
File: gui-docker-manager/gui-docker-manager/integration/docker_client.py
"""

import asyncio
import logging
import subprocess
from typing import Dict, List, Any, Optional
from .service_base import ServiceClientBase, ServiceError, ServiceTimeoutError

logger = logging.getLogger(__name__)


class DockerClientAsync:
    """
    Async Docker client for managing containers via Docker socket
    """
    
    def __init__(
        self,
        base_url: str = "unix:///var/run/docker.sock",
        timeout: Optional[float] = None,
        retry_count: Optional[int] = None,
        retry_delay: Optional[float] = None
    ):
        """
        Initialize Docker client
        
        Args:
            base_url: Docker socket path (default: unix:///var/run/docker.sock)
            timeout: Request timeout
            retry_count: Number of retries
            retry_delay: Delay between retries
        """
        self.base_url = base_url
        self.timeout = timeout or 30.0
        self.retry_count = retry_count or 3
        self.retry_delay = retry_delay or 1.0
        
        logger.info(f"Initialized Docker client with socket: {self.base_url}")
    
    async def _run_docker_command(self, *args) -> Dict[str, Any]:
        """
        Run docker command asynchronously
        
        Args:
            *args: Docker command arguments
            
        Returns:
            Command output as dictionary
        """
        cmd = ["docker"] + list(args)
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                raise ServiceError(f"Docker command failed: {error_msg}")
            
            output = stdout.decode('utf-8', errors='ignore').strip()
            return {"status": "success", "output": output}
            
        except asyncio.TimeoutError:
            raise ServiceTimeoutError(f"Docker command timed out after {self.timeout}s")
        except Exception as e:
            raise ServiceError(f"Docker command error: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Docker daemon health"""
        try:
            result = await self._run_docker_command("version")
            return {"status": "healthy", "message": "Docker daemon is running"}
        except Exception as e:
            logger.error(f"Docker health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def list_containers(self, all: bool = False) -> List[Dict[str, Any]]:
        """
        List Docker containers
        
        Args:
            all: Include stopped containers
            
        Returns:
            List of container information dictionaries
        """
        try:
            args = ["ps", "--format", "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Image}}"]
            if all:
                args.insert(1, "-a")
            
            result = await self._run_docker_command(*args)
            containers = []
            
            lines = result["output"].split("\n")[1:]  # Skip header
            for line in lines:
                if not line.strip():
                    continue
                parts = line.split("\t")
                if len(parts) >= 4:
                    containers.append({
                        "id": parts[0],
                        "name": parts[1],
                        "status": parts[2],
                        "image": parts[3],
                    })
            
            return containers
            
        except Exception as e:
            logger.error(f"Failed to list containers: {e}")
            raise
    
    async def get_container(self, container_id: str) -> Dict[str, Any]:
        """
        Get container details
        
        Args:
            container_id: Container ID or name
            
        Returns:
            Container information
        """
        try:
            result = await self._run_docker_command(
                "inspect",
                container_id,
                "--format=json"
            )
            # For simplicity, return basic info
            return {
                "id": container_id,
                "status": "found",
                "output": result["output"]
            }
        except Exception as e:
            logger.error(f"Failed to get container {container_id}: {e}")
            raise
    
    async def start_container(self, container_id: str) -> Dict[str, Any]:
        """
        Start a container
        
        Args:
            container_id: Container ID or name
            
        Returns:
            Operation result
        """
        try:
            await self._run_docker_command("start", container_id)
            logger.info(f"Started container: {container_id}")
            return {"status": "success", "message": f"Container {container_id} started"}
        except Exception as e:
            logger.error(f"Failed to start container {container_id}: {e}")
            raise
    
    async def stop_container(self, container_id: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Stop a container
        
        Args:
            container_id: Container ID or name
            timeout: Shutdown timeout
            
        Returns:
            Operation result
        """
        try:
            await self._run_docker_command("stop", "-t", str(timeout), container_id)
            logger.info(f"Stopped container: {container_id}")
            return {"status": "success", "message": f"Container {container_id} stopped"}
        except Exception as e:
            logger.error(f"Failed to stop container {container_id}: {e}")
            raise
    
    async def restart_container(self, container_id: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Restart a container
        
        Args:
            container_id: Container ID or name
            timeout: Shutdown timeout
            
        Returns:
            Operation result
        """
        try:
            await self._run_docker_command("restart", "-t", str(timeout), container_id)
            logger.info(f"Restarted container: {container_id}")
            return {"status": "success", "message": f"Container {container_id} restarted"}
        except Exception as e:
            logger.error(f"Failed to restart container {container_id}: {e}")
            raise
    
    async def get_logs(self, container_id: str, tail: int = 100) -> str:
        """
        Get container logs
        
        Args:
            container_id: Container ID or name
            tail: Number of log lines
            
        Returns:
            Log output
        """
        try:
            result = await self._run_docker_command(
                "logs",
                "--tail", str(tail),
                container_id
            )
            return result["output"]
        except Exception as e:
            logger.error(f"Failed to get logs for container {container_id}: {e}")
            raise
    
    async def get_stats(self, container_id: str) -> Dict[str, Any]:
        """
        Get container statistics
        
        Args:
            container_id: Container ID or name
            
        Returns:
            Container statistics
        """
        try:
            result = await self._run_docker_command(
                "stats",
                "--no-stream",
                "--format", "table {{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}",
                container_id
            )
            return {
                "status": "success",
                "stats": result["output"]
            }
        except Exception as e:
            logger.error(f"Failed to get stats for container {container_id}: {e}")
            raise
    
    async def close(self):
        """Close client (cleanup if needed)"""
        logger.debug("Docker client closed")
