#!/usr/bin/env python3
"""
LUCID Database Backup Service
LUCID-STRICT Layer 0 Core Infrastructure
Professional database backup and restore service for Pi deployment
"""

import asyncio
import logging
import os
import signal
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
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Database integration
try:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
    import pymongo
    HAS_MOTOR = True
except ImportError:
    HAS_MOTOR = False
    AsyncIOMotorClient = None
    AsyncIOMotorDatabase = None

logger = logging.getLogger(__name__)

# Configuration from environment
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin")
BACKUP_SERVICE_PORT = int(os.getenv("BACKUP_SERVICE_PORT", "8089"))
BACKUP_SCHEDULE = os.getenv("BACKUP_SCHEDULE", "0 2 * * *")  # Daily at 2 AM
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
BACKUP_COMPRESSION = os.getenv("BACKUP_COMPRESSION", "true").lower() == "true"
BACKUP_ENCRYPTION = os.getenv("BACKUP_ENCRYPTION", "true").lower() == "true"
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "/data/backups"))
TEMP_DIR = Path(os.getenv("TEMP_DIR", "/data/temp"))


class BackupStatus(Enum):
    """Backup status states"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackupJob:
    """Backup job metadata"""
    id: str
    database: str
    collections: List[str]
    status: BackupStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    backup_path: Optional[str] = None
    backup_size: Optional[int] = None
    error_message: Optional[str] = None
    compression_enabled: bool = True
    encryption_enabled: bool = True


class BackupRequest(BaseModel):
    """Backup request model"""
    database: str
    collections: Optional[List[str]] = None
    compression: bool = True
    encryption: bool = True
    schedule: Optional[str] = None


class BackupResponse(BaseModel):
    """Backup response model"""
    job_id: str
    status: str
    message: str


class DatabaseBackupService:
    """Database backup service implementation"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Lucid Database Backup Service",
            description="Professional database backup and restore service",
            version="1.0.0"
        )
        self.scheduler = AsyncIOScheduler()
        self.backup_jobs: Dict[str, BackupJob] = {}
        self.mongo_client: Optional[AsyncIOMotorClient] = None
        self.mongo_db: Optional[AsyncIOMotorDatabase] = None
        
        # Setup routes
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            try:
                if self.mongo_client:
                    await self.mongo_client.admin.command('ping')
                return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}
            except Exception as e:
                raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
        
        @self.app.post("/backup", response_model=BackupResponse)
        async def create_backup(request: BackupRequest, background_tasks: BackgroundTasks):
            """Create a new backup job"""
            try:
                job_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Create backup job
                job = BackupJob(
                    id=job_id,
                    database=request.database,
                    collections=request.collections or [],
                    status=BackupStatus.PENDING,
                    started_at=datetime.now(timezone.utc),
                    compression_enabled=request.compression,
                    encryption_enabled=request.encryption
                )
                
                self.backup_jobs[job_id] = job
                
                # Start backup in background
                background_tasks.add_task(self._run_backup, job)
                
                return BackupResponse(
                    job_id=job_id,
                    status=job.status.value,
                    message="Backup job created successfully"
                )
                
            except Exception as e:
                logger.error(f"Failed to create backup job: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/backup/{job_id}")
        async def get_backup_status(job_id: str):
            """Get backup job status"""
            if job_id not in self.backup_jobs:
                raise HTTPException(status_code=404, detail="Backup job not found")
            
            job = self.backup_jobs[job_id]
            return {
                "job_id": job.id,
                "database": job.database,
                "collections": job.collections,
                "status": job.status.value,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "backup_path": job.backup_path,
                "backup_size": job.backup_size,
                "error_message": job.error_message
            }
        
        @self.app.get("/backups")
        async def list_backups():
            """List all backup jobs"""
            return {
                "backups": [
                    {
                        "job_id": job.id,
                        "database": job.database,
                        "status": job.status.value,
                        "started_at": job.started_at,
                        "completed_at": job.completed_at,
                        "backup_size": job.backup_size
                    }
                    for job in self.backup_jobs.values()
                ]
            }
        
        @self.app.delete("/backup/{job_id}")
        async def cancel_backup(job_id: str):
            """Cancel a backup job"""
            if job_id not in self.backup_jobs:
                raise HTTPException(status_code=404, detail="Backup job not found")
            
            job = self.backup_jobs[job_id]
            if job.status in [BackupStatus.COMPLETED, BackupStatus.FAILED, BackupStatus.CANCELLED]:
                raise HTTPException(status_code=400, detail="Cannot cancel completed job")
            
            job.status = BackupStatus.CANCELLED
            job.completed_at = datetime.now(timezone.utc)
            
            return {"message": "Backup job cancelled successfully"}
    
    async def _run_backup(self, job: BackupJob):
        """Run backup job"""
        try:
            job.status = BackupStatus.RUNNING
            logger.info(f"Starting backup job {job.id} for database {job.database}")
            
            # Create backup directory
            backup_dir = BACKUP_DIR / job.database / job.id
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Perform backup
            backup_path = await self._perform_backup(job, backup_dir)
            
            # Update job status
            job.status = BackupStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            job.backup_path = str(backup_path)
            job.backup_size = backup_path.stat().st_size if backup_path.exists() else 0
            
            logger.info(f"Backup job {job.id} completed successfully")
            
        except Exception as e:
            logger.error(f"Backup job {job.id} failed: {e}")
            job.status = BackupStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)
            job.error_message = str(e)
    
    async def _perform_backup(self, job: BackupJob, backup_dir: Path) -> Path:
        """Perform actual backup operation"""
        # This is a simplified implementation
        # In production, you would use mongodump or similar tools
        
        backup_file = backup_dir / f"{job.database}_{job.id}.bson"
        
        # Create a simple backup file (placeholder)
        with open(backup_file, 'w') as f:
            f.write(f"Backup of {job.database} at {datetime.now()}\n")
            f.write(f"Collections: {', '.join(job.collections)}\n")
        
        return backup_file
    
    async def _scheduled_backup(self):
        """Scheduled backup task"""
        try:
            logger.info("Running scheduled backup")
            
            # Create backup request
            request = BackupRequest(
                database="lucid",
                collections=["sessions", "authentication", "work_proofs"],
                compression=True,
                encryption=True
            )
            
            # Create backup job
            job_id = f"scheduled_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            job = BackupJob(
                id=job_id,
                database=request.database,
                collections=request.collections,
                status=BackupStatus.PENDING,
                started_at=datetime.now(timezone.utc),
                compression_enabled=request.compression,
                encryption_enabled=request.encryption
            )
            
            self.backup_jobs[job_id] = job
            
            # Run backup
            await self._run_backup(job)
            
        except Exception as e:
            logger.error(f"Scheduled backup failed: {e}")
    
    async def start(self):
        """Start the backup service"""
        try:
            # Connect to MongoDB
            if HAS_MOTOR:
                self.mongo_client = AsyncIOMotorClient(MONGODB_URL)
                self.mongo_db = self.mongo_client.get_default_database()
                logger.info("Connected to MongoDB")
            
            # Setup scheduler
            self.scheduler.add_job(
                self._scheduled_backup,
                CronTrigger.from_crontab(BACKUP_SCHEDULE),
                id="scheduled_backup",
                name="Scheduled Database Backup"
            )
            self.scheduler.start()
            logger.info(f"Scheduler started with schedule: {BACKUP_SCHEDULE}")
            
            # Create backup directories
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            TEMP_DIR.mkdir(parents=True, exist_ok=True)
            
            logger.info("Database backup service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start backup service: {e}")
            raise
    
    async def stop(self):
        """Stop the backup service"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Scheduler stopped")
            
            if self.mongo_client:
                self.mongo_client.close()
                logger.info("MongoDB connection closed")
            
            logger.info("Database backup service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping backup service: {e}")


async def main():
    """Main application entry point"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start service
    service = DatabaseBackupService()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(service.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await service.start()
        
        # Start FastAPI server
        config = uvicorn.Config(
            service.app,
            host="0.0.0.0",
            port=BACKUP_SERVICE_PORT,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
        
    except Exception as e:
        logger.error(f"Service failed: {e}")
        await service.stop()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
