#!/usr/bin/env python3
"""
LUCID ROLLBACK MANAGER - SPEC-4 Rollback Functionality
Professional rollback management for Pi deployment
Multi-platform build for ARM64 Pi and AMD64 development

This module provides comprehensive rollback functionality including:
- Automatic rollback triggers and conditions
- Version state management and snapshots
- System health monitoring and validation
- Rollback execution and verification
- Integration with update manager and signature verification
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
from typing import Dict, List, Optional, Tuple, Any, Union
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
ROLLBACK_PATH = os.getenv("ROLLBACK_PATH", "/opt/lucid/rollback")
SNAPSHOTS_PATH = os.getenv("SNAPSHOTS_PATH", "/opt/lucid/snapshots")
VERSIONS_PATH = os.getenv("VERSIONS_PATH", "/opt/lucid/versions")
ROLLBACK_TIMEOUT_SECONDS = int(os.getenv("ROLLBACK_TIMEOUT_SECONDS", "300"))
HEALTH_CHECK_INTERVAL_SECONDS = int(os.getenv("HEALTH_CHECK_INTERVAL_SECONDS", "60"))
MAX_SNAPSHOTS = int(os.getenv("MAX_SNAPSHOTS", "10"))
AUTO_ROLLBACK_ENABLED = os.getenv("AUTO_ROLLBACK_ENABLED", "true").lower() == "true"
HEALTH_CHECK_FAILURE_THRESHOLD = int(os.getenv("HEALTH_CHECK_FAILURE_THRESHOLD", "3"))

class RollbackStatus(Enum):
    """Rollback status enumeration"""
    IDLE = "idle"
    PREPARING = "preparing"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class RollbackTrigger(Enum):
    """Rollback trigger types"""
    MANUAL = "manual"
    HEALTH_CHECK_FAILURE = "health_check_failure"
    UPDATE_FAILURE = "update_failure"
    SYSTEM_ERROR = "system_error"
    TIMEOUT = "timeout"
    USER_REQUEST = "user_request"

class SystemHealth(Enum):
    """System health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"

@dataclass
class SystemSnapshot:
    """System snapshot structure"""
    snapshot_id: str
    version: str
    timestamp: datetime
    file_paths: List[str]
    system_state: Dict[str, Any]
    checksums: Dict[str, str]
    rollback_script: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class RollbackOperation:
    """Rollback operation structure"""
    operation_id: str
    trigger: RollbackTrigger
    target_version: str
    current_version: str
    status: RollbackStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    steps_completed: List[str] = None
    health_checks_passed: int = 0
    health_checks_failed: int = 0

    def __post_init__(self):
        if self.steps_completed is None:
            self.steps_completed = []

@dataclass
class HealthCheckResult:
    """Health check result structure"""
    check_name: str
    status: SystemHealth
    message: str
    timestamp: datetime
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}

class RollbackRequest(BaseModel):
    """Rollback request model"""
    target_version: Optional[str] = None
    reason: str = "Manual rollback"
    force: bool = False
    skip_health_checks: bool = False

class RollbackResponse(BaseModel):
    """Rollback response model"""
    success: bool
    message: str
    operation_id: str
    target_version: str
    estimated_duration_seconds: int

class HealthCheckResponse(BaseModel):
    """Health check response model"""
    overall_status: str
    checks: List[Dict[str, Any]]
    timestamp: str
    recommendations: List[str] = []

class RollbackManager:
    """Main rollback manager class"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Lucid Rollback Manager",
            description="Rollback Management Service",
            version="1.0.0"
        )
        self.setup_middleware()
        self.setup_routes()
        
        # State management
        self.current_rollback: Optional[RollbackOperation] = None
        self.snapshots: Dict[str, SystemSnapshot] = {}
        self.rollback_history: List[RollbackOperation] = []
        self.health_check_results: List[HealthCheckResult] = []
        self.health_check_failures: int = 0
        
        # Background tasks
        self.health_monitor_task: Optional[asyncio.Task] = None
        self.snapshot_cleanup_task: Optional[asyncio.Task] = None
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Load existing snapshots
        self._load_snapshots()
        
        logger.info("Rollback Manager initialized", 
                   loaded_snapshots=len(self.snapshots),
                   auto_rollback_enabled=AUTO_ROLLBACK_ENABLED)

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
                "service": "rollback_manager",
                "version": "1.0.0",
                "loaded_snapshots": len(self.snapshots),
                "current_rollback": asdict(self.current_rollback) if self.current_rollback else None,
                "auto_rollback_enabled": AUTO_ROLLBACK_ENABLED
            }
        
        @self.app.get("/snapshots")
        async def list_snapshots():
            """List available snapshots"""
            return {
                "snapshots": [
                    {
                        "snapshot_id": snapshot.snapshot_id,
                        "version": snapshot.version,
                        "timestamp": snapshot.timestamp.isoformat(),
                        "file_count": len(snapshot.file_paths),
                        "metadata": snapshot.metadata
                    }
                    for snapshot in sorted(self.snapshots.values(), 
                                         key=lambda x: x.timestamp, 
                                         reverse=True)
                ]
            }
        
        @self.app.post("/snapshots/create")
        async def create_snapshot(version: str, description: str = ""):
            """Create a new system snapshot"""
            try:
                snapshot = await self._create_snapshot(version, description)
                return {
                    "success": True,
                    "snapshot_id": snapshot.snapshot_id,
                    "message": f"Snapshot created for version {version}"
                }
            except Exception as e:
                logger.error("Failed to create snapshot", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/rollback", response_model=RollbackResponse)
        async def execute_rollback(request: RollbackRequest, background_tasks: BackgroundTasks):
            """Execute rollback operation"""
            if self.current_rollback and self.current_rollback.status not in [RollbackStatus.COMPLETED, RollbackStatus.FAILED]:
                raise HTTPException(status_code=409, detail="Rollback already in progress")
            
            try:
                operation_id = f"rollback_{int(time.time())}"
                background_tasks.add_task(self._execute_rollback, operation_id, request)
                
                return RollbackResponse(
                    success=True,
                    message="Rollback started",
                    operation_id=operation_id,
                    target_version=request.target_version or "latest",
                    estimated_duration_seconds=ROLLBACK_TIMEOUT_SECONDS
                )
            except Exception as e:
                logger.error("Failed to start rollback", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/rollback/status")
        async def get_rollback_status():
            """Get current rollback status"""
            if not self.current_rollback:
                return {"status": "idle", "message": "No rollback in progress"}
            
            return asdict(self.current_rollback)
        
        @self.app.post("/rollback/cancel")
        async def cancel_rollback():
            """Cancel current rollback"""
            if not self.current_rollback:
                raise HTTPException(status_code=404, detail="No rollback in progress")
            
            if self.current_rollback.status in [RollbackStatus.COMPLETED, RollbackStatus.FAILED]:
                raise HTTPException(status_code=400, detail="Rollback already finished")
            
            self.current_rollback.status = RollbackStatus.CANCELLED
            self.current_rollback.end_time = datetime.now()
            self.current_rollback.error_message = "Cancelled by user"
            
            return {"success": True, "message": "Rollback cancelled"}
        
        @self.app.get("/health-check", response_model=HealthCheckResponse)
        async def perform_health_check():
            """Perform comprehensive health check"""
            try:
                results = await self._perform_health_checks()
                overall_status = self._determine_overall_health(results)
                recommendations = self._generate_recommendations(results)
                
                return HealthCheckResponse(
                    overall_status=overall_status.value,
                    checks=[
                        {
                            "name": result.check_name,
                            "status": result.status.value,
                            "message": result.message,
                            "timestamp": result.timestamp.isoformat(),
                            "details": result.details
                        }
                        for result in results
                    ],
                    timestamp=datetime.now().isoformat(),
                    recommendations=recommendations
                )
            except Exception as e:
                logger.error("Health check failed", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/rollback-history")
        async def get_rollback_history():
            """Get rollback history"""
            return {
                "history": [
                    {
                        "operation_id": op.operation_id,
                        "trigger": op.trigger.value,
                        "target_version": op.target_version,
                        "status": op.status.value,
                        "start_time": op.start_time.isoformat(),
                        "end_time": op.end_time.isoformat() if op.end_time else None,
                        "error_message": op.error_message
                    }
                    for op in self.rollback_history[-20:]  # Last 20 rollbacks
                ]
            }

    def _ensure_directories(self):
        """Ensure required directories exist"""
        directories = [ROLLBACK_PATH, SNAPSHOTS_PATH, VERSIONS_PATH]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            logger.debug("Ensured directory exists", directory=directory)

    def _load_snapshots(self):
        """Load existing snapshots from storage"""
        snapshots_file = Path(SNAPSHOTS_PATH) / "snapshots.json"
        if snapshots_file.exists():
            try:
                with open(snapshots_file) as f:
                    snapshots_data = json.load(f)
                
                for snapshot_data in snapshots_data.get("snapshots", []):
                    snapshot = SystemSnapshot(
                        snapshot_id=snapshot_data["snapshot_id"],
                        version=snapshot_data["version"],
                        timestamp=datetime.fromisoformat(snapshot_data["timestamp"]),
                        file_paths=snapshot_data["file_paths"],
                        system_state=snapshot_data["system_state"],
                        checksums=snapshot_data["checksums"],
                        rollback_script=snapshot_data.get("rollback_script"),
                        metadata=snapshot_data.get("metadata", {})
                    )
                    self.snapshots[snapshot.snapshot_id] = snapshot
                
                logger.info("Loaded snapshots from storage", count=len(self.snapshots))
                
            except Exception as e:
                logger.error("Failed to load snapshots", error=str(e))

    async def _save_snapshots(self):
        """Save snapshots to storage"""
        try:
            snapshots_data = {
                "snapshots": [
                    {
                        "snapshot_id": snapshot.snapshot_id,
                        "version": snapshot.version,
                        "timestamp": snapshot.timestamp.isoformat(),
                        "file_paths": snapshot.file_paths,
                        "system_state": snapshot.system_state,
                        "checksums": snapshot.checksums,
                        "rollback_script": snapshot.rollback_script,
                        "metadata": snapshot.metadata
                    }
                    for snapshot in self.snapshots.values()
                ]
            }
            
            snapshots_file = Path(SNAPSHOTS_PATH) / "snapshots.json"
            with open(snapshots_file, "w") as f:
                json.dump(snapshots_data, f, indent=2)
            
            logger.debug("Saved snapshots to storage", count=len(self.snapshots))
            
        except Exception as e:
            logger.error("Failed to save snapshots", error=str(e))

    async def _create_snapshot(self, version: str, description: str = "") -> SystemSnapshot:
        """Create a new system snapshot"""
        try:
            snapshot_id = f"snapshot_{version}_{int(time.time())}"
            
            # Define critical system paths to snapshot
            critical_paths = [
                "/opt/lucid",
                "/etc/lucid",
                "/var/lib/lucid",
                "/usr/local/bin/lucid"
            ]
            
            # Collect file paths and checksums
            file_paths = []
            checksums = {}
            
            for path in critical_paths:
                path_obj = Path(path)
                if path_obj.exists():
                    if path_obj.is_file():
                        file_paths.append(str(path_obj))
                        checksums[str(path_obj)] = await self._calculate_file_checksum(str(path_obj))
                    elif path_obj.is_dir():
                        for file_path in path_obj.rglob("*"):
                            if file_path.is_file():
                                file_paths.append(str(file_path))
                                checksums[str(file_path)] = await self._calculate_file_checksum(str(file_path))
            
            # Create snapshot archive
            snapshot_archive = Path(SNAPSHOTS_PATH) / f"{snapshot_id}.tar.gz"
            await self._create_snapshot_archive(file_paths, snapshot_archive)
            
            # Get system state
            system_state = await self._capture_system_state()
            
            snapshot = SystemSnapshot(
                snapshot_id=snapshot_id,
                version=version,
                timestamp=datetime.now(),
                file_paths=file_paths,
                system_state=system_state,
                checksums=checksums,
                metadata={
                    "description": description,
                    "archive_path": str(snapshot_archive),
                    "file_count": len(file_paths)
                }
            )
            
            self.snapshots[snapshot_id] = snapshot
            await self._save_snapshots()
            
            logger.info("Created snapshot", 
                       snapshot_id=snapshot_id,
                       version=version,
                       file_count=len(file_paths))
            
            return snapshot
            
        except Exception as e:
            logger.error("Failed to create snapshot", error=str(e))
            raise

    async def _calculate_file_checksum(self, file_path: str) -> str:
        """Calculate file checksum"""
        import hashlib
        
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    async def _create_snapshot_archive(self, file_paths: List[str], archive_path: Path):
        """Create snapshot archive"""
        try:
            # Create temporary directory for snapshot
            temp_dir = Path(SNAPSHOTS_PATH) / f"temp_{int(time.time())}"
            temp_dir.mkdir(exist_ok=True)
            
            # Copy files to temp directory preserving structure
            for file_path in file_paths:
                src_path = Path(file_path)
                if src_path.exists():
                    # Create relative path structure
                    rel_path = src_path.relative_to(src_path.anchor)
                    dst_path = temp_dir / rel_path
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dst_path)
            
            # Create tar.gz archive
            subprocess.run([
                "tar", "-czf", str(archive_path), "-C", str(temp_dir), "."
            ], check=True)
            
            # Clean up temp directory
            shutil.rmtree(temp_dir)
            
        except Exception as e:
            logger.error("Failed to create snapshot archive", error=str(e))
            raise

    async def _capture_system_state(self) -> Dict[str, Any]:
        """Capture current system state"""
        try:
            system_state = {
                "timestamp": datetime.now().isoformat(),
                "platform": sys.platform,
                "python_version": sys.version,
                "environment_variables": dict(os.environ),
                "processes": [],
                "network_interfaces": [],
                "disk_usage": {},
                "memory_usage": {}
            }
            
            # Get disk usage
            for path in ["/", "/opt", "/var", "/tmp"]:
                if Path(path).exists():
                    usage = shutil.disk_usage(path)
                    system_state["disk_usage"][path] = {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free
                    }
            
            # Get running processes (simplified)
            try:
                result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    system_state["processes"] = result.stdout.split('\n')[:20]  # First 20 processes
            except Exception:
                pass
            
            return system_state
            
        except Exception as e:
            logger.error("Failed to capture system state", error=str(e))
            return {"error": str(e)}

    async def _execute_rollback(self, operation_id: str, request: RollbackRequest):
        """Execute rollback operation"""
        try:
            # Find target snapshot
            target_snapshot = self._find_target_snapshot(request.target_version)
            if not target_snapshot:
                raise ValueError(f"No snapshot found for version: {request.target_version}")
            
            # Create rollback operation
            self.current_rollback = RollbackOperation(
                operation_id=operation_id,
                trigger=RollbackTrigger.MANUAL,
                target_version=target_snapshot.version,
                current_version=self._get_current_version(),
                status=RollbackStatus.PREPARING,
                start_time=datetime.now()
            )
            
            # Step 1: Prepare rollback
            await self._update_rollback_status(RollbackStatus.PREPARING, "Preparing rollback")
            await self._prepare_rollback(target_snapshot)
            self.current_rollback.steps_completed.append("prepare")
            
            # Step 2: Execute rollback
            await self._update_rollback_status(RollbackStatus.EXECUTING, "Executing rollback")
            await self._restore_snapshot(target_snapshot)
            self.current_rollback.steps_completed.append("restore")
            
            # Step 3: Verify rollback
            await self._update_rollback_status(RollbackStatus.VERIFYING, "Verifying rollback")
            verification_passed = await self._verify_rollback(target_snapshot)
            self.current_rollback.steps_completed.append("verify")
            
            if verification_passed:
                # Step 4: Complete rollback
                await self._update_rollback_status(RollbackStatus.COMPLETED, "Rollback completed successfully")
                await self._finalize_rollback(target_snapshot)
                self.current_rollback.steps_completed.append("finalize")
            else:
                # Rollback verification failed
                await self._update_rollback_status(RollbackStatus.FAILED, "Rollback verification failed")
            
            self.current_rollback.end_time = datetime.now()
            self.rollback_history.append(self.current_rollback)
            
            logger.info("Rollback operation completed",
                       operation_id=operation_id,
                       target_version=target_snapshot.version,
                       status=self.current_rollback.status.value)
            
        except Exception as e:
            logger.error("Rollback operation failed", operation_id=operation_id, error=str(e))
            if self.current_rollback:
                self.current_rollback.status = RollbackStatus.FAILED
                self.current_rollback.error_message = str(e)
                self.current_rollback.end_time = datetime.now()
                self.rollback_history.append(self.current_rollback)

    def _find_target_snapshot(self, target_version: Optional[str]) -> Optional[SystemSnapshot]:
        """Find target snapshot for rollback"""
        if target_version:
            # Find specific version
            for snapshot in self.snapshots.values():
                if snapshot.version == target_version:
                    return snapshot
        else:
            # Find latest snapshot
            if self.snapshots:
                return max(self.snapshots.values(), key=lambda x: x.timestamp)
        
        return None

    def _get_current_version(self) -> str:
        """Get current system version"""
        version_file = Path(VERSIONS_PATH) / "current.json"
        if version_file.exists():
            try:
                with open(version_file) as f:
                    version_data = json.load(f)
                return version_data.get("version", "unknown")
            except Exception:
                pass
        return "unknown"

    async def _prepare_rollback(self, snapshot: SystemSnapshot):
        """Prepare for rollback operation"""
        try:
            # Check if snapshot archive exists
            archive_path = Path(snapshot.metadata.get("archive_path", ""))
            if not archive_path.exists():
                raise FileNotFoundError(f"Snapshot archive not found: {archive_path}")
            
            # Verify snapshot integrity
            if not await self._verify_snapshot_integrity(snapshot):
                raise ValueError("Snapshot integrity verification failed")
            
            logger.info("Rollback preparation completed", snapshot_id=snapshot.snapshot_id)
            
        except Exception as e:
            logger.error("Rollback preparation failed", error=str(e))
            raise

    async def _verify_snapshot_integrity(self, snapshot: SystemSnapshot) -> bool:
        """Verify snapshot integrity"""
        try:
            archive_path = Path(snapshot.metadata.get("archive_path", ""))
            if not archive_path.exists():
                return False
            
            # Check archive file size
            if archive_path.stat().st_size == 0:
                return False
            
            # Verify archive can be extracted
            test_dir = Path(SNAPSHOTS_PATH) / f"test_{int(time.time())}"
            test_dir.mkdir(exist_ok=True)
            
            try:
                subprocess.run([
                    "tar", "-tzf", str(archive_path)
                ], check=True, capture_output=True, cwd=str(test_dir))
                return True
            except subprocess.CalledProcessError:
                return False
            finally:
                if test_dir.exists():
                    shutil.rmtree(test_dir)
            
        except Exception as e:
            logger.error("Snapshot integrity verification error", error=str(e))
            return False

    async def _restore_snapshot(self, snapshot: SystemSnapshot):
        """Restore system from snapshot"""
        try:
            archive_path = Path(snapshot.metadata.get("archive_path", ""))
            
            # Create backup of current state
            backup_path = Path(ROLLBACK_PATH) / f"backup_{int(time.time())}"
            backup_path.mkdir(exist_ok=True)
            
            # Backup current critical files
            for file_path in snapshot.file_paths:
                src_path = Path(file_path)
                if src_path.exists():
                    rel_path = src_path.relative_to(src_path.anchor)
                    dst_path = backup_path / rel_path
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dst_path)
            
            # Extract snapshot
            extract_dir = Path(ROLLBACK_PATH) / f"extract_{int(time.time())}"
            extract_dir.mkdir(exist_ok=True)
            
            subprocess.run([
                "tar", "-xzf", str(archive_path), "-C", str(extract_dir)
            ], check=True)
            
            # Restore files
            for file_path in snapshot.file_paths:
                src_path = extract_dir / Path(file_path).name
                dst_path = Path(file_path)
                
                if src_path.exists():
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dst_path)
            
            # Clean up
            shutil.rmtree(extract_dir)
            
            logger.info("Snapshot restored successfully", snapshot_id=snapshot.snapshot_id)
            
        except Exception as e:
            logger.error("Failed to restore snapshot", error=str(e))
            raise

    async def _verify_rollback(self, snapshot: SystemSnapshot) -> bool:
        """Verify rollback was successful"""
        try:
            # Check if critical files exist and have correct checksums
            for file_path, expected_checksum in snapshot.checksums.items():
                if Path(file_path).exists():
                    actual_checksum = await self._calculate_file_checksum(file_path)
                    if actual_checksum != expected_checksum:
                        logger.warning("Checksum mismatch after rollback",
                                     file_path=file_path,
                                     expected=expected_checksum,
                                     actual=actual_checksum)
                        return False
            
            # Perform health checks
            health_results = await self._perform_health_checks()
            overall_health = self._determine_overall_health(health_results)
            
            if overall_health in [SystemHealth.UNHEALTHY, SystemHealth.CRITICAL]:
                logger.warning("System health check failed after rollback",
                             overall_health=overall_health.value)
                return False
            
            logger.info("Rollback verification passed", snapshot_id=snapshot.snapshot_id)
            return True
            
        except Exception as e:
            logger.error("Rollback verification failed", error=str(e))
            return False

    async def _finalize_rollback(self, snapshot: SystemSnapshot):
        """Finalize rollback operation"""
        try:
            # Update version file
            version_data = {
                "version": snapshot.version,
                "last_rollback": datetime.now().isoformat(),
                "rollback_snapshot": snapshot.snapshot_id
            }
            
            version_file = Path(VERSIONS_PATH) / "current.json"
            with open(version_file, "w") as f:
                json.dump(version_data, f, indent=2)
            
            logger.info("Rollback finalized", 
                       version=snapshot.version,
                       snapshot_id=snapshot.snapshot_id)
            
        except Exception as e:
            logger.error("Failed to finalize rollback", error=str(e))

    async def _perform_health_checks(self) -> List[HealthCheckResult]:
        """Perform comprehensive health checks"""
        results = []
        current_time = datetime.now()
        
        # Check 1: Disk space
        try:
            usage = shutil.disk_usage("/")
            free_gb = usage.free / (1024**3)
            if free_gb < 1.0:
                status = SystemHealth.CRITICAL
                message = f"Critical: Only {free_gb:.1f}GB free space"
            elif free_gb < 5.0:
                status = SystemHealth.UNHEALTHY
                message = f"Warning: Only {free_gb:.1f}GB free space"
            else:
                status = SystemHealth.HEALTHY
                message = f"OK: {free_gb:.1f}GB free space"
            
            results.append(HealthCheckResult(
                check_name="disk_space",
                status=status,
                message=message,
                timestamp=current_time,
                details={"free_gb": free_gb}
            ))
        except Exception as e:
            results.append(HealthCheckResult(
                check_name="disk_space",
                status=SystemHealth.CRITICAL,
                message=f"Failed to check disk space: {str(e)}",
                timestamp=current_time
            ))
        
        # Check 2: Critical services
        try:
            # Check if critical Lucid services are running
            critical_services = ["update_manager", "signature_verifier", "rollback_manager"]
            running_services = []
            
            for service in critical_services:
                try:
                    # Simple port check (services should be listening on their ports)
                    ports = {"update_manager": 8112, "signature_verifier": 8113, "rollback_manager": 8114}
                    port = ports.get(service)
                    if port:
                        result = subprocess.run(["netstat", "-ln"], capture_output=True, text=True, timeout=5)
                        if f":{port}" in result.stdout:
                            running_services.append(service)
                except Exception:
                    pass
            
            if len(running_services) == len(critical_services):
                status = SystemHealth.HEALTHY
                message = "All critical services running"
            elif len(running_services) > 0:
                status = SystemHealth.DEGRADED
                message = f"Some services running: {', '.join(running_services)}"
            else:
                status = SystemHealth.CRITICAL
                message = "No critical services running"
            
            results.append(HealthCheckResult(
                check_name="critical_services",
                status=status,
                message=message,
                timestamp=current_time,
                details={"running_services": running_services}
            ))
        except Exception as e:
            results.append(HealthCheckResult(
                check_name="critical_services",
                status=SystemHealth.CRITICAL,
                message=f"Failed to check services: {str(e)}",
                timestamp=current_time
            ))
        
        # Check 3: System load
        try:
            result = subprocess.run(["uptime"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                load_avg = result.stdout.split()[-3:]  # Last 3 load averages
                load_1min = float(load_avg[0].rstrip(','))
                
                if load_1min > 5.0:
                    status = SystemHealth.CRITICAL
                    message = f"High system load: {load_1min}"
                elif load_1min > 2.0:
                    status = SystemHealth.UNHEALTHY
                    message = f"Elevated system load: {load_1min}"
                else:
                    status = SystemHealth.HEALTHY
                    message = f"Normal system load: {load_1min}"
                
                results.append(HealthCheckResult(
                    check_name="system_load",
                    status=status,
                    message=message,
                    timestamp=current_time,
                    details={"load_1min": load_1min}
                ))
        except Exception as e:
            results.append(HealthCheckResult(
                check_name="system_load",
                status=SystemHealth.DEGRADED,
                message=f"Failed to check system load: {str(e)}",
                timestamp=current_time
            ))
        
        # Store results
        self.health_check_results.extend(results)
        
        # Keep only recent results
        cutoff_time = current_time - timedelta(hours=24)
        self.health_check_results = [
            result for result in self.health_check_results 
            if result.timestamp > cutoff_time
        ]
        
        return results

    def _determine_overall_health(self, results: List[HealthCheckResult]) -> SystemHealth:
        """Determine overall system health from check results"""
        if not results:
            return SystemHealth.UNHEALTHY
        
        # Count health statuses
        status_counts = {}
        for result in results:
            status_counts[result.status] = status_counts.get(result.status, 0) + 1
        
        # Determine overall health
        if status_counts.get(SystemHealth.CRITICAL, 0) > 0:
            return SystemHealth.CRITICAL
        elif status_counts.get(SystemHealth.UNHEALTHY, 0) > 0:
            return SystemHealth.UNHEALTHY
        elif status_counts.get(SystemHealth.DEGRADED, 0) > 0:
            return SystemHealth.DEGRADED
        else:
            return SystemHealth.HEALTHY

    def _generate_recommendations(self, results: List[HealthCheckResult]) -> List[str]:
        """Generate recommendations based on health check results"""
        recommendations = []
        
        for result in results:
            if result.status == SystemHealth.CRITICAL:
                if result.check_name == "disk_space":
                    recommendations.append("Free up disk space immediately")
                elif result.check_name == "critical_services":
                    recommendations.append("Restart critical services")
                elif result.check_name == "system_load":
                    recommendations.append("Investigate high system load")
            elif result.status == SystemHealth.UNHEALTHY:
                if result.check_name == "disk_space":
                    recommendations.append("Consider cleaning up old files")
                elif result.check_name == "system_load":
                    recommendations.append("Monitor system load trends")
        
        return recommendations

    async def _update_rollback_status(self, status: RollbackStatus, message: str):
        """Update rollback status"""
        if self.current_rollback:
            self.current_rollback.status = status
            logger.info("Rollback status update", 
                       operation_id=self.current_rollback.operation_id,
                       status=status.value,
                       message=message)

    async def start_background_tasks(self):
        """Start background monitoring tasks"""
        self.health_monitor_task = asyncio.create_task(self._health_monitor())
        self.snapshot_cleanup_task = asyncio.create_task(self._snapshot_cleanup())
        logger.info("Background tasks started")

    async def _health_monitor(self):
        """Health monitoring task"""
        while True:
            try:
                await asyncio.sleep(HEALTH_CHECK_INTERVAL_SECONDS)
                
                # Perform health checks
                results = await self._perform_health_checks()
                overall_health = self._determine_overall_health(results)
                
                # Track consecutive failures
                if overall_health in [SystemHealth.UNHEALTHY, SystemHealth.CRITICAL]:
                    self.health_check_failures += 1
                else:
                    self.health_check_failures = 0
                
                # Trigger auto-rollback if threshold exceeded
                if (AUTO_ROLLBACK_ENABLED and 
                    self.health_check_failures >= HEALTH_CHECK_FAILURE_THRESHOLD and
                    not self.current_rollback):
                    
                    logger.warning("Health check failure threshold exceeded, triggering auto-rollback",
                                 failures=self.health_check_failures,
                                 threshold=HEALTH_CHECK_FAILURE_THRESHOLD)
                    
                    # Find latest stable snapshot
                    latest_snapshot = max(self.snapshots.values(), key=lambda x: x.timestamp) if self.snapshots else None
                    if latest_snapshot:
                        request = RollbackRequest(
                            target_version=latest_snapshot.version,
                            reason="Auto-rollback due to health check failures",
                            force=True
                        )
                        await self._execute_rollback(f"auto_{int(time.time())}", request)
                
            except Exception as e:
                logger.error("Error in health monitor", error=str(e))

    async def _snapshot_cleanup(self):
        """Cleanup old snapshots"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                # Sort snapshots by timestamp
                sorted_snapshots = sorted(self.snapshots.values(), key=lambda x: x.timestamp, reverse=True)
                
                # Remove excess snapshots
                if len(sorted_snapshots) > MAX_SNAPSHOTS:
                    snapshots_to_remove = sorted_snapshots[MAX_SNAPSHOTS:]
                    
                    for snapshot in snapshots_to_remove:
                        # Remove archive file
                        archive_path = Path(snapshot.metadata.get("archive_path", ""))
                        if archive_path.exists():
                            archive_path.unlink()
                        
                        # Remove from memory
                        del self.snapshots[snapshot.snapshot_id]
                        
                        logger.info("Removed old snapshot", 
                                   snapshot_id=snapshot.snapshot_id,
                                   version=snapshot.version)
                    
                    # Save updated snapshots
                    await self._save_snapshots()
                
            except Exception as e:
                logger.error("Error in snapshot cleanup", error=str(e))

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down rollback manager")
        
        if self.health_monitor_task:
            self.health_monitor_task.cancel()
        if self.snapshot_cleanup_task:
            self.snapshot_cleanup_task.cancel()
        
        # Wait for tasks to complete
        tasks = [t for t in [self.health_monitor_task, self.snapshot_cleanup_task] if t]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Save snapshots before shutdown
        await self._save_snapshots()

async def main():
    """Main entry point"""
    rollback_manager = RollbackManager()
    
    # Start background tasks
    await rollback_manager.start_background_tasks()
    
    # Start the server
    config = uvicorn.Config(
        rollback_manager.app,
        host="0.0.0.0",
        port=8114,
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await rollback_manager.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
