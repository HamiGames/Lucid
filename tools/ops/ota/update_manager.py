#!/usr/bin/env python3
"""
LUCID UPDATE MANAGER - SPEC-4 OTA Update System
Professional OTA update orchestration for Pi deployment
Multi-platform build for ARM64 Pi and AMD64 development

This module provides comprehensive OTA update orchestration including:
- Update discovery and validation
- Download management with integrity checks
- Installation orchestration
- Health monitoring and rollback triggers
- Integration with signature verification and rollback systems
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

import httpx
import structlog
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Environment configuration
OTA_PATH = os.getenv("OTA_PATH", "/opt/lucid/ota")
SIGNATURES_PATH = os.getenv("SIGNATURES_PATH", "/opt/lucid/signatures")
VERSIONS_PATH = os.getenv("VERSIONS_PATH", "/opt/lucid/versions")
UPDATE_CHECK_INTERVAL_SECONDS = int(os.getenv("UPDATE_CHECK_INTERVAL_SECONDS", "3600"))
DOWNLOAD_TIMEOUT_SECONDS = int(os.getenv("DOWNLOAD_TIMEOUT_SECONDS", "300"))
INSTALLATION_TIMEOUT_SECONDS = int(os.getenv("INSTALLATION_TIMEOUT_SECONDS", "600"))
ROLLBACK_TIMEOUT_SECONDS = int(os.getenv("ROLLBACK_TIMEOUT_SECONDS", "300"))
MIN_FREE_SPACE_MB = int(os.getenv("MIN_FREE_SPACE_MB", "1000"))

# Service endpoints
SIGNATURE_VERIFIER_URL = os.getenv("SIGNATURE_VERIFIER_URL", "http://localhost:8113")
ROLLBACK_MANAGER_URL = os.getenv("ROLLBACK_MANAGER_URL", "http://localhost:8114")
UPDATE_SERVER_URL = os.getenv("UPDATE_SERVER_URL", "https://updates.lucid.network")

class UpdateStatus(Enum):
    """Update status enumeration"""
    IDLE = "idle"
    CHECKING = "checking"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    INSTALLING = "installing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"

class UpdatePriority(Enum):
    """Update priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class UpdateInfo:
    """Update information structure"""
    version: str
    release_date: str
    size_bytes: int
    checksum_sha256: str
    signature: str
    priority: UpdatePriority
    changelog: str
    download_url: str
    min_free_space_mb: int
    dependencies: List[str]
    rollback_version: Optional[str] = None

@dataclass
class UpdateProgress:
    """Update progress tracking"""
    status: UpdateStatus
    progress_percent: float
    current_operation: str
    bytes_downloaded: int
    total_bytes: int
    start_time: datetime
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None

@dataclass
class SystemInfo:
    """System information for update compatibility"""
    current_version: str
    architecture: str
    platform: str
    free_space_mb: int
    last_update: Optional[datetime]
    update_channel: str

class UpdateRequest(BaseModel):
    """Update request model"""
    version: Optional[str] = None
    force: bool = False
    priority: UpdatePriority = UpdatePriority.MEDIUM

class UpdateResponse(BaseModel):
    """Update response model"""
    success: bool
    message: str
    update_id: Optional[str] = None
    progress_url: Optional[str] = None

class UpdateManager:
    """Main update manager class"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Lucid Update Manager",
            description="OTA Update Orchestration Service",
            version="1.0.0"
        )
        self.setup_middleware()
        self.setup_routes()
        
        # State management
        self.current_update: Optional[UpdateProgress] = None
        self.system_info: SystemInfo = self._get_system_info()
        self.update_history: List[Dict] = []
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Background tasks
        self.update_check_task: Optional[asyncio.Task] = None
        self.health_monitor_task: Optional[asyncio.Task] = None
        
        logger.info("Update Manager initialized", 
                   current_version=self.system_info.current_version,
                   architecture=self.system_info.architecture)

    def setup_middleware(self):
        """Setup FastAPI middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "service": "update_manager",
                "version": "1.0.0",
                "system_info": asdict(self.system_info),
                "current_update": asdict(self.current_update) if self.current_update else None
            }
        
        @self.app.get("/status")
        async def get_status():
            """Get current update status"""
            return {
                "current_update": asdict(self.current_update) if self.current_update else None,
                "system_info": asdict(self.system_info),
                "update_history": self.update_history[-10:]  # Last 10 updates
            }
        
        @self.app.post("/check-updates")
        async def check_updates():
            """Check for available updates"""
            try:
                updates = await self._check_available_updates()
                return {
                    "success": True,
                    "updates": [asdict(update) for update in updates],
                    "current_version": self.system_info.current_version
                }
            except Exception as e:
                logger.error("Failed to check updates", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/start-update", response_model=UpdateResponse)
        async def start_update(request: UpdateRequest, background_tasks: BackgroundTasks):
            """Start update process"""
            if self.current_update and self.current_update.status not in [UpdateStatus.COMPLETED, UpdateStatus.FAILED]:
                raise HTTPException(status_code=409, detail="Update already in progress")
            
            try:
                update_id = f"update_{int(time.time())}"
                background_tasks.add_task(self._execute_update, update_id, request)
                
                return UpdateResponse(
                    success=True,
                    message="Update started",
                    update_id=update_id,
                    progress_url=f"/update-progress/{update_id}"
                )
            except Exception as e:
                logger.error("Failed to start update", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/update-progress/{update_id}")
        async def get_update_progress(update_id: str):
            """Get update progress"""
            if not self.current_update:
                raise HTTPException(status_code=404, detail="No active update")
            
            return asdict(self.current_update)
        
        @self.app.post("/cancel-update")
        async def cancel_update():
            """Cancel current update"""
            if not self.current_update:
                raise HTTPException(status_code=404, detail="No active update")
            
            if self.current_update.status in [UpdateStatus.COMPLETED, UpdateStatus.FAILED]:
                raise HTTPException(status_code=400, detail="Update already finished")
            
            # Trigger rollback
            await self._trigger_rollback("User requested cancellation")
            return {"success": True, "message": "Update cancelled, rollback initiated"}

    def _ensure_directories(self):
        """Ensure required directories exist"""
        directories = [OTA_PATH, SIGNATURES_PATH, VERSIONS_PATH]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            logger.debug("Ensured directory exists", directory=directory)

    def _get_system_info(self) -> SystemInfo:
        """Get current system information"""
        try:
            # Get current version from version file or default
            version_file = Path(VERSIONS_PATH) / "current.json"
            if version_file.exists():
                with open(version_file) as f:
                    version_data = json.load(f)
                    current_version = version_data.get("version", "1.0.0")
                    last_update = datetime.fromisoformat(version_data.get("last_update", "1970-01-01T00:00:00"))
            else:
                current_version = "1.0.0"
                last_update = None
            
            # Get system architecture
            architecture = os.uname().machine if hasattr(os, 'uname') else "unknown"
            platform = sys.platform
            
            # Get free space
            free_space_mb = shutil.disk_usage(OTA_PATH).free // (1024 * 1024)
            
            return SystemInfo(
                current_version=current_version,
                architecture=architecture,
                platform=platform,
                free_space_mb=free_space_mb,
                last_update=last_update,
                update_channel="stable"
            )
        except Exception as e:
            logger.error("Failed to get system info", error=str(e))
            return SystemInfo(
                current_version="1.0.0",
                architecture="unknown",
                platform="unknown",
                free_space_mb=0,
                last_update=None,
                update_channel="stable"
            )

    async def _check_available_updates(self) -> List[UpdateInfo]:
        """Check for available updates from update server"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{UPDATE_SERVER_URL}/api/updates",
                    params={
                        "current_version": self.system_info.current_version,
                        "architecture": self.system_info.architecture,
                        "platform": self.system_info.platform,
                        "channel": self.system_info.update_channel
                    }
                )
                response.raise_for_status()
                
                updates_data = response.json()
                updates = []
                
                for update_data in updates_data.get("updates", []):
                    update = UpdateInfo(
                        version=update_data["version"],
                        release_date=update_data["release_date"],
                        size_bytes=update_data["size_bytes"],
                        checksum_sha256=update_data["checksum_sha256"],
                        signature=update_data["signature"],
                        priority=UpdatePriority(update_data["priority"]),
                        changelog=update_data["changelog"],
                        download_url=update_data["download_url"],
                        min_free_space_mb=update_data["min_free_space_mb"],
                        dependencies=update_data.get("dependencies", []),
                        rollback_version=update_data.get("rollback_version")
                    )
                    updates.append(update)
                
                logger.info("Checked for updates", 
                           current_version=self.system_info.current_version,
                           available_updates=len(updates))
                
                return updates
                
        except Exception as e:
            logger.error("Failed to check for updates", error=str(e))
            return []

    async def _execute_update(self, update_id: str, request: UpdateRequest):
        """Execute the update process"""
        try:
            self.current_update = UpdateProgress(
                status=UpdateStatus.CHECKING,
                progress_percent=0.0,
                current_operation="Checking for updates",
                bytes_downloaded=0,
                total_bytes=0,
                start_time=datetime.now()
            )
            
            # Step 1: Check for available updates
            await self._update_progress(UpdateStatus.CHECKING, 10.0, "Checking for updates")
            updates = await self._check_available_updates()
            
            if not updates:
                await self._update_progress(UpdateStatus.COMPLETED, 100.0, "No updates available")
                return
            
            # Select update based on request
            selected_update = self._select_update(updates, request)
            if not selected_update:
                await self._update_progress(UpdateStatus.COMPLETED, 100.0, "No suitable update found")
                return
            
            # Step 2: Validate system requirements
            await self._update_progress(UpdateStatus.CHECKING, 20.0, "Validating system requirements")
            if not await self._validate_system_requirements(selected_update):
                await self._update_progress(UpdateStatus.FAILED, 0.0, "System requirements not met")
                return
            
            # Step 3: Download update
            await self._update_progress(UpdateStatus.DOWNLOADING, 30.0, "Downloading update")
            download_path = await self._download_update(selected_update)
            
            # Step 4: Verify signature
            await self._update_progress(UpdateStatus.VERIFYING, 70.0, "Verifying signature")
            if not await self._verify_signature(download_path, selected_update):
                await self._update_progress(UpdateStatus.FAILED, 0.0, "Signature verification failed")
                return
            
            # Step 5: Install update
            await self._update_progress(UpdateStatus.INSTALLING, 80.0, "Installing update")
            if not await self._install_update(download_path, selected_update):
                await self._update_progress(UpdateStatus.FAILED, 0.0, "Installation failed")
                await self._trigger_rollback("Installation failed")
                return
            
            # Step 6: Complete update
            await self._update_progress(UpdateStatus.COMPLETED, 100.0, "Update completed successfully")
            await self._finalize_update(selected_update)
            
            logger.info("Update completed successfully", 
                       update_id=update_id,
                       version=selected_update.version)
            
        except Exception as e:
            logger.error("Update failed", update_id=update_id, error=str(e))
            await self._update_progress(UpdateStatus.FAILED, 0.0, f"Update failed: {str(e)}")
            await self._trigger_rollback(f"Update failed: {str(e)}")

    def _select_update(self, updates: List[UpdateInfo], request: UpdateRequest) -> Optional[UpdateInfo]:
        """Select the appropriate update based on request"""
        if request.version:
            # Find specific version
            for update in updates:
                if update.version == request.version:
                    return update
            return None
        
        # Select latest version based on priority
        if request.priority == UpdatePriority.CRITICAL:
            critical_updates = [u for u in updates if u.priority == UpdatePriority.CRITICAL]
            if critical_updates:
                return max(critical_updates, key=lambda x: x.version)
        
        # Return latest version
        return max(updates, key=lambda x: x.version) if updates else None

    async def _validate_system_requirements(self, update: UpdateInfo) -> bool:
        """Validate system requirements for update"""
        # Check free space
        if self.system_info.free_space_mb < update.min_free_space_mb:
            logger.error("Insufficient free space", 
                        required=update.min_free_space_mb,
                        available=self.system_info.free_space_mb)
            return False
        
        # Check dependencies
        for dependency in update.dependencies:
            if not await self._check_dependency(dependency):
                logger.error("Missing dependency", dependency=dependency)
                return False
        
        return True

    async def _check_dependency(self, dependency: str) -> bool:
        """Check if a dependency is available"""
        # This would check for required system packages, libraries, etc.
        return True

    async def _download_update(self, update: UpdateInfo) -> str:
        """Download the update package"""
        download_path = Path(OTA_PATH) / f"update_{update.version}.tar.gz"
        
        try:
            async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT_SECONDS) as client:
                async with client.stream("GET", update.download_url) as response:
                    response.raise_for_status()
                    
                    total_size = int(response.headers.get("content-length", 0))
                    self.current_update.total_bytes = total_size
                    
                    with open(download_path, "wb") as f:
                        downloaded = 0
                        async for chunk in response.aiter_bytes():
                            f.write(chunk)
                            downloaded += len(chunk)
                            self.current_update.bytes_downloaded = downloaded
                            
                            # Update progress
                            if total_size > 0:
                                progress = 30.0 + (downloaded / total_size) * 40.0
                                await self._update_progress(
                                    UpdateStatus.DOWNLOADING, 
                                    progress, 
                                    f"Downloading: {downloaded // 1024 // 1024}MB / {total_size // 1024 // 1024}MB"
                                )
            
            logger.info("Update downloaded successfully", 
                       version=update.version,
                       size=download_path.stat().st_size)
            
            return str(download_path)
            
        except Exception as e:
            logger.error("Failed to download update", error=str(e))
            if download_path.exists():
                download_path.unlink()
            raise

    async def _verify_signature(self, download_path: str, update: UpdateInfo) -> bool:
        """Verify the update signature"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{SIGNATURE_VERIFIER_URL}/verify",
                    json={
                        "file_path": download_path,
                        "signature": update.signature,
                        "checksum": update.checksum_sha256
                    }
                )
                response.raise_for_status()
                
                result = response.json()
                return result.get("verified", False)
                
        except Exception as e:
            logger.error("Failed to verify signature", error=str(e))
            return False

    async def _install_update(self, download_path: str, update: UpdateInfo) -> bool:
        """Install the update package"""
        try:
            # Extract update package
            extract_path = Path(OTA_PATH) / f"extract_{update.version}"
            extract_path.mkdir(exist_ok=True)
            
            # Extract tar.gz
            subprocess.run([
                "tar", "-xzf", download_path, "-C", str(extract_path)
            ], check=True)
            
            # Run installation script if present
            install_script = extract_path / "install.sh"
            if install_script.exists():
                subprocess.run([
                    "bash", str(install_script)
                ], check=True, timeout=INSTALLATION_TIMEOUT_SECONDS)
            
            # Clean up
            shutil.rmtree(extract_path)
            
            logger.info("Update installed successfully", version=update.version)
            return True
            
        except Exception as e:
            logger.error("Failed to install update", error=str(e))
            return False

    async def _finalize_update(self, update: UpdateInfo):
        """Finalize the update process"""
        try:
            # Update version file
            version_data = {
                "version": update.version,
                "last_update": datetime.now().isoformat(),
                "update_id": f"update_{int(time.time())}"
            }
            
            version_file = Path(VERSIONS_PATH) / "current.json"
            with open(version_file, "w") as f:
                json.dump(version_data, f, indent=2)
            
            # Update system info
            self.system_info.current_version = update.version
            self.system_info.last_update = datetime.now()
            
            # Add to history
            self.update_history.append({
                "version": update.version,
                "timestamp": datetime.now().isoformat(),
                "status": "completed",
                "size_bytes": update.size_bytes
            })
            
            logger.info("Update finalized", version=update.version)
            
        except Exception as e:
            logger.error("Failed to finalize update", error=str(e))

    async def _trigger_rollback(self, reason: str):
        """Trigger rollback process"""
        try:
            await self._update_progress(UpdateStatus.ROLLING_BACK, 0.0, f"Rolling back: {reason}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{ROLLBACK_MANAGER_URL}/rollback",
                    json={"reason": reason}
                )
                response.raise_for_status()
                
                result = response.json()
                if result.get("success"):
                    await self._update_progress(UpdateStatus.COMPLETED, 100.0, "Rollback completed")
                else:
                    await self._update_progress(UpdateStatus.FAILED, 0.0, "Rollback failed")
                    
        except Exception as e:
            logger.error("Failed to trigger rollback", error=str(e))
            await self._update_progress(UpdateStatus.FAILED, 0.0, f"Rollback failed: {str(e)}")

    async def _update_progress(self, status: UpdateStatus, progress: float, operation: str):
        """Update progress information"""
        if self.current_update:
            self.current_update.status = status
            self.current_update.progress_percent = progress
            self.current_update.current_operation = operation
            
            if status == UpdateStatus.FAILED:
                self.current_update.error_message = operation
            
            logger.info("Update progress", 
                       status=status.value,
                       progress=progress,
                       operation=operation)

    async def start_background_tasks(self):
        """Start background monitoring tasks"""
        self.update_check_task = asyncio.create_task(self._periodic_update_check())
        self.health_monitor_task = asyncio.create_task(self._health_monitor())
        logger.info("Background tasks started")

    async def _periodic_update_check(self):
        """Periodic update checking task"""
        while True:
            try:
                await asyncio.sleep(UPDATE_CHECK_INTERVAL_SECONDS)
                
                if not self.current_update:
                    updates = await self._check_available_updates()
                    critical_updates = [u for u in updates if u.priority == UpdatePriority.CRITICAL]
                    
                    if critical_updates:
                        logger.info("Critical update available", 
                                   version=critical_updates[0].version)
                        # Auto-start critical updates
                        request = UpdateRequest(priority=UpdatePriority.CRITICAL)
                        await self._execute_update(f"auto_{int(time.time())}", request)
                        
            except Exception as e:
                logger.error("Error in periodic update check", error=str(e))

    async def _health_monitor(self):
        """Health monitoring task"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Check system health
                free_space_mb = shutil.disk_usage(OTA_PATH).free // (1024 * 1024)
                self.system_info.free_space_mb = free_space_mb
                
                if free_space_mb < MIN_FREE_SPACE_MB:
                    logger.warning("Low disk space", 
                                 free_space_mb=free_space_mb,
                                 min_required=MIN_FREE_SPACE_MB)
                
            except Exception as e:
                logger.error("Error in health monitor", error=str(e))

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down update manager")
        
        if self.update_check_task:
            self.update_check_task.cancel()
        if self.health_monitor_task:
            self.health_monitor_task.cancel()
        
        # Wait for tasks to complete
        tasks = [t for t in [self.update_check_task, self.health_monitor_task] if t]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

async def main():
    """Main entry point"""
    update_manager = UpdateManager()
    
    # Start background tasks
    await update_manager.start_background_tasks()
    
    # Start the server
    config = uvicorn.Config(
        update_manager.app,
        host="0.0.0.0",
        port=8112,
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await update_manager.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
