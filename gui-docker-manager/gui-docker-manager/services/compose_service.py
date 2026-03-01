"""
Docker Compose Service Business Logic
File: gui-docker-manager/gui-docker-manager/services/compose_service.py
"""

import logging
import subprocess
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ComposeService:
    """Business logic for docker-compose operations"""
    
    def __init__(self, compose_dir: str = "/mnt/myssd/Lucid/Lucid/configs/docker/"):
        """Initialize compose service"""
        self.compose_dir = compose_dir
    
    async def compose_up(self, compose_file: str) -> Dict[str, Any]:
        """Start compose project"""
        try:
            compose_path = f"{self.compose_dir}{compose_file}"
            logger.info(f"Starting compose project: {compose_file}")
            
            result = subprocess.run(
                ["docker-compose", "-f", compose_path, "up", "-d"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                raise Exception(result.stderr)
            
            return {"status": "success", "message": f"Started {compose_file}"}
        except Exception as e:
            logger.error(f"Failed to start compose: {e}")
            raise
    
    async def compose_down(self, compose_file: str) -> Dict[str, Any]:
        """Stop compose project"""
        try:
            compose_path = f"{self.compose_dir}{compose_file}"
            logger.info(f"Stopping compose project: {compose_file}")
            
            result = subprocess.run(
                ["docker-compose", "-f", compose_path, "down"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                raise Exception(result.stderr)
            
            return {"status": "success", "message": f"Stopped {compose_file}"}
        except Exception as e:
            logger.error(f"Failed to stop compose: {e}")
            raise
    
    async def compose_status(self, compose_file: str) -> Dict[str, Any]:
        """Get compose project status"""
        try:
            compose_path = f"{self.compose_dir}{compose_file}"
            logger.info(f"Checking compose status: {compose_file}")
            
            result = subprocess.run(
                ["docker-compose", "-f", compose_path, "ps"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "status": "success",
                "compose_file": compose_file,
                "output": result.stdout
            }
        except Exception as e:
            logger.error(f"Failed to get compose status: {e}")
            raise
