#!/usr/bin/env python3
"""
Lucid RDP Exporter
S3 backup service for exporting session data and system backups
"""

import asyncio
import logging
import os
import json
import hashlib
import tempfile
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import structlog
import uuid
from pathlib import Path

logger = structlog.get_logger(__name__)

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    S3_AVAILABLE = True
    logger.info("AWS S3 SDK loaded successfully")
except ImportError:
    logger.warning("AWS S3 SDK not available, using mock implementation")
    S3_AVAILABLE = False

try:
    import aiofiles
    import aiohttp
    ASYNC_AVAILABLE = True
    logger.info("Async I/O libraries loaded successfully")
except ImportError:
    logger.warning("Async I/O libraries not available")
    ASYNC_AVAILABLE = False


class ExportStatus(Enum):
    """Export operation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BackupType(Enum):
    """Backup types"""
    SESSION_DATA = "session_data"
    SYSTEM_CONFIG = "system_config"
    DATABASE = "database"
    LOGS = "logs"
    BLOCKCHAIN_DATA = "blockchain_data"
    FULL_SYSTEM = "full_system"


class StorageProvider(Enum):
    """Storage providers"""
    AWS_S3 = "aws_s3"
    MINIO = "minio"
    GOOGLE_CLOUD = "google_cloud"
    AZURE_BLOB = "azure_blob"
    LOCAL_FILESYSTEM = "local_filesystem"


@dataclass
class ExportConfig:
    """Export configuration"""
    storage_provider: StorageProvider
    bucket_name: str
    region: str = "us-east-1"
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    endpoint_url: Optional[str] = None
    encryption_key: Optional[str] = None
    compression: bool = True
    chunk_size: int = 64 * 1024 * 1024  # 64MB
    max_concurrent_uploads: int = 5
    retry_attempts: int = 3
    timeout: int = 300  # 5 minutes


@dataclass
class ExportJob:
    """Export job information"""
    job_id: str
    backup_type: BackupType
    source_paths: List[str]
    destination_path: str
    status: ExportStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    progress: float = 0.0
    total_size: int = 0
    uploaded_size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class S3Exporter:
    """S3-based exporter"""
    
    def __init__(self, config: ExportConfig):
        self.config = config
        self.client = None
        self.session = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize S3 client"""
        try:
            if not S3_AVAILABLE:
                logger.warning("S3 not available, using mock client")
                return
            
            # Create S3 client
            session_kwargs = {
                'region_name': self.config.region
            }
            
            if self.config.access_key and self.config.secret_key:
                session_kwargs.update({
                    'aws_access_key_id': self.config.access_key,
                    'aws_secret_access_key': self.config.secret_key
                })
            
            self.session = boto3.Session(**session_kwargs)
            
            client_kwargs = {
                'service_name': 's3',
                'region_name': self.config.region
            }
            
            if self.config.endpoint_url:
                client_kwargs['endpoint_url'] = self.config.endpoint_url
            
            self.client = self.session.client(**client_kwargs)
            
            logger.info("S3 client initialized", provider=self.config.storage_provider.value)
            
        except Exception as e:
            logger.error("Failed to initialize S3 client", error=str(e))
            raise
    
    async def test_connection(self) -> bool:
        """Test S3 connection"""
        try:
            if not self.client:
                return False
            
            # Test bucket access
            self.client.head_bucket(Bucket=self.config.bucket_name)
            logger.info("S3 connection test successful")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.error("S3 bucket not found", bucket=self.config.bucket_name)
            else:
                logger.error("S3 connection test failed", error=str(e))
            return False
        except Exception as e:
            logger.error("S3 connection test failed", error=str(e))
            return False
    
    async def upload_file(self, local_path: str, remote_path: str, 
                         progress_callback=None) -> bool:
        """Upload file to S3"""
        try:
            if not self.client:
                logger.error("S3 client not initialized")
                return False
            
            # Get file size
            file_size = os.path.getsize(local_path)
            
            # Upload file
            extra_args = {}
            if self.config.encryption_key:
                extra_args['ServerSideEncryption'] = 'AES256'
            
            def upload_progress(bytes_transferred):
                if progress_callback:
                    progress = (bytes_transferred / file_size) * 100
                    progress_callback(progress)
            
            self.client.upload_file(
                local_path,
                self.config.bucket_name,
                remote_path,
                ExtraArgs=extra_args,
                Callback=upload_progress
            )
            
            logger.info("File uploaded successfully", 
                       local_path=local_path, remote_path=remote_path)
            return True
            
        except Exception as e:
            logger.error("Failed to upload file", 
                        local_path=local_path, remote_path=remote_path, error=str(e))
            return False
    
    async def upload_directory(self, local_dir: str, remote_prefix: str,
                              progress_callback=None) -> bool:
        """Upload directory to S3"""
        try:
            if not self.client:
                logger.error("S3 client not initialized")
                return False
            
            # Get all files in directory
            files = []
            for root, dirs, filenames in os.walk(local_dir):
                for filename in filenames:
                    local_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(local_path, local_dir)
                    remote_path = f"{remote_prefix}/{relative_path}".replace("\\", "/")
                    files.append((local_path, remote_path))
            
            total_files = len(files)
            uploaded_files = 0
            
            # Upload files
            for local_path, remote_path in files:
                success = await self.upload_file(local_path, remote_path)
                if success:
                    uploaded_files += 1
                
                if progress_callback:
                    progress = (uploaded_files / total_files) * 100
                    progress_callback(progress)
            
            logger.info("Directory uploaded", 
                       local_dir=local_dir, uploaded_files=uploaded_files, total_files=total_files)
            return uploaded_files == total_files
            
        except Exception as e:
            logger.error("Failed to upload directory", 
                        local_dir=local_dir, remote_prefix=remote_prefix, error=str(e))
            return False
    
    async def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download file from S3"""
        try:
            if not self.client:
                logger.error("S3 client not initialized")
                return False
            
            # Create local directory if needed
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Download file
            self.client.download_file(
                self.config.bucket_name,
                remote_path,
                local_path
            )
            
            logger.info("File downloaded successfully", 
                       remote_path=remote_path, local_path=local_path)
            return True
            
        except Exception as e:
            logger.error("Failed to download file", 
                        remote_path=remote_path, local_path=local_path, error=str(e))
            return False
    
    async def list_files(self, prefix: str = "") -> List[str]:
        """List files in S3 bucket"""
        try:
            if not self.client:
                return []
            
            response = self.client.list_objects_v2(
                Bucket=self.config.bucket_name,
                Prefix=prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append(obj['Key'])
            
            return files
            
        except Exception as e:
            logger.error("Failed to list files", prefix=prefix, error=str(e))
            return []
    
    async def delete_file(self, remote_path: str) -> bool:
        """Delete file from S3"""
        try:
            if not self.client:
                logger.error("S3 client not initialized")
                return False
            
            self.client.delete_object(
                Bucket=self.config.bucket_name,
                Key=remote_path
            )
            
            logger.info("File deleted successfully", remote_path=remote_path)
            return True
            
        except Exception as e:
            logger.error("Failed to delete file", remote_path=remote_path, error=str(e))
            return False


class LocalExporter:
    """Local filesystem exporter"""
    
    def __init__(self, config: ExportConfig):
        self.config = config
        self.base_path = config.bucket_name  # Use bucket_name as base path
    
    async def test_connection(self) -> bool:
        """Test local filesystem connection"""
        try:
            os.makedirs(self.base_path, exist_ok=True)
            logger.info("Local filesystem connection test successful")
            return True
        except Exception as e:
            logger.error("Local filesystem connection test failed", error=str(e))
            return False
    
    async def upload_file(self, local_path: str, remote_path: str, 
                         progress_callback=None) -> bool:
        """Upload file to local filesystem"""
        try:
            # Create destination path
            dest_path = os.path.join(self.base_path, remote_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Copy file
            import shutil
            shutil.copy2(local_path, dest_path)
            
            if progress_callback:
                progress_callback(100.0)
            
            logger.info("File uploaded to local filesystem", 
                       local_path=local_path, dest_path=dest_path)
            return True
            
        except Exception as e:
            logger.error("Failed to upload file to local filesystem", 
                        local_path=local_path, remote_path=remote_path, error=str(e))
            return False
    
    async def upload_directory(self, local_dir: str, remote_prefix: str,
                              progress_callback=None) -> bool:
        """Upload directory to local filesystem"""
        try:
            # Create destination path
            dest_dir = os.path.join(self.base_path, remote_prefix)
            
            # Copy directory
            import shutil
            shutil.copytree(local_dir, dest_dir, dirs_exist_ok=True)
            
            if progress_callback:
                progress_callback(100.0)
            
            logger.info("Directory uploaded to local filesystem", 
                       local_dir=local_dir, dest_dir=dest_dir)
            return True
            
        except Exception as e:
            logger.error("Failed to upload directory to local filesystem", 
                        local_dir=local_dir, remote_prefix=remote_prefix, error=str(e))
            return False
    
    async def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download file from local filesystem"""
        try:
            # Create local directory if needed
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Copy file
            import shutil
            shutil.copy2(os.path.join(self.base_path, remote_path), local_path)
            
            logger.info("File downloaded from local filesystem", 
                       remote_path=remote_path, local_path=local_path)
            return True
            
        except Exception as e:
            logger.error("Failed to download file from local filesystem", 
                        remote_path=remote_path, local_path=local_path, error=str(e))
            return False
    
    async def list_files(self, prefix: str = "") -> List[str]:
        """List files in local filesystem"""
        try:
            files = []
            search_path = os.path.join(self.base_path, prefix)
            
            if os.path.exists(search_path):
                for root, dirs, filenames in os.walk(search_path):
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(file_path, self.base_path)
                        files.append(relative_path.replace("\\", "/"))
            
            return files
            
        except Exception as e:
            logger.error("Failed to list files in local filesystem", prefix=prefix, error=str(e))
            return []
    
    async def delete_file(self, remote_path: str) -> bool:
        """Delete file from local filesystem"""
        try:
            file_path = os.path.join(self.base_path, remote_path)
            if os.path.exists(file_path):
                os.remove(file_path)
            
            logger.info("File deleted from local filesystem", remote_path=remote_path)
            return True
            
        except Exception as e:
            logger.error("Failed to delete file from local filesystem", 
                        remote_path=remote_path, error=str(e))
            return False


class ExporterService:
    """Main exporter service"""
    
    def __init__(self, config: ExportConfig):
        self.config = config
        self.exporter = None
        self.jobs: Dict[str, ExportJob] = {}
        self.is_running = False
        
        # Initialize exporter based on provider
        if config.storage_provider == StorageProvider.LOCAL_FILESYSTEM:
            self.exporter = LocalExporter(config)
        else:
            self.exporter = S3Exporter(config)
    
    async def start(self):
        """Start the exporter service"""
        try:
            # Test connection
            if not await self.exporter.test_connection():
                raise Exception("Failed to connect to storage provider")
            
            self.is_running = True
            logger.info("Exporter service started", 
                       provider=self.config.storage_provider.value)
            
        except Exception as e:
            logger.error("Failed to start exporter service", error=str(e))
            raise
    
    async def stop(self):
        """Stop the exporter service"""
        try:
            self.is_running = False
            logger.info("Exporter service stopped")
        except Exception as e:
            logger.error("Failed to stop exporter service", error=str(e))
    
    async def create_export_job(self, backup_type: BackupType, source_paths: List[str],
                               destination_path: str, metadata: Dict[str, Any] = None) -> str:
        """Create a new export job"""
        try:
            job_id = str(uuid.uuid4())
            
            # Calculate total size
            total_size = 0
            for path in source_paths:
                if os.path.isfile(path):
                    total_size += os.path.getsize(path)
                elif os.path.isdir(path):
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            total_size += os.path.getsize(os.path.join(root, file))
            
            # Create job
            job = ExportJob(
                job_id=job_id,
                backup_type=backup_type,
                source_paths=source_paths,
                destination_path=destination_path,
                status=ExportStatus.PENDING,
                created_at=datetime.utcnow(),
                total_size=total_size,
                metadata=metadata or {}
            )
            
            self.jobs[job_id] = job
            
            logger.info("Export job created", job_id=job_id, backup_type=backup_type.value)
            return job_id
            
        except Exception as e:
            logger.error("Failed to create export job", error=str(e))
            raise
    
    async def execute_export_job(self, job_id: str) -> bool:
        """Execute an export job"""
        try:
            if job_id not in self.jobs:
                logger.error("Export job not found", job_id=job_id)
                return False
            
            job = self.jobs[job_id]
            
            # Update job status
            job.status = ExportStatus.IN_PROGRESS
            job.started_at = datetime.utcnow()
            
            logger.info("Starting export job", job_id=job_id)
            
            # Execute export based on backup type
            success = False
            
            if job.backup_type == BackupType.SESSION_DATA:
                success = await self._export_session_data(job)
            elif job.backup_type == BackupType.SYSTEM_CONFIG:
                success = await self._export_system_config(job)
            elif job.backup_type == BackupType.DATABASE:
                success = await self._export_database(job)
            elif job.backup_type == BackupType.LOGS:
                success = await self._export_logs(job)
            elif job.backup_type == BackupType.BLOCKCHAIN_DATA:
                success = await self._export_blockchain_data(job)
            elif job.backup_type == BackupType.FULL_SYSTEM:
                success = await self._export_full_system(job)
            else:
                logger.error("Unknown backup type", backup_type=job.backup_type.value)
                return False
            
            # Update job status
            if success:
                job.status = ExportStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.progress = 100.0
                logger.info("Export job completed", job_id=job_id)
            else:
                job.status = ExportStatus.FAILED
                job.error_message = "Export failed"
                logger.error("Export job failed", job_id=job_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to execute export job", job_id=job_id, error=str(e))
            if job_id in self.jobs:
                self.jobs[job_id].status = ExportStatus.FAILED
                self.jobs[job_id].error_message = str(e)
            return False
    
    async def _export_session_data(self, job: ExportJob) -> bool:
        """Export session data"""
        try:
            # Create temporary archive
            with tempfile.TemporaryDirectory() as temp_dir:
                archive_path = os.path.join(temp_dir, "session_data.tar.gz")
                
                # Create archive
                import tarfile
                with tarfile.open(archive_path, "w:gz") as tar:
                    for path in job.source_paths:
                        if os.path.exists(path):
                            tar.add(path, arcname=os.path.basename(path))
                
                # Upload archive
                remote_path = f"{job.destination_path}/session_data_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.tar.gz"
                
                def progress_callback(progress):
                    job.progress = progress
                    job.uploaded_size = int((progress / 100) * job.total_size)
                
                success = await self.exporter.upload_file(archive_path, remote_path, progress_callback)
                
                if success:
                    job.metadata['archive_path'] = remote_path
                    job.metadata['archive_size'] = os.path.getsize(archive_path)
                
                return success
                
        except Exception as e:
            logger.error("Failed to export session data", error=str(e))
            return False
    
    async def _export_system_config(self, job: ExportJob) -> bool:
        """Export system configuration"""
        try:
            # Create configuration archive
            with tempfile.TemporaryDirectory() as temp_dir:
                archive_path = os.path.join(temp_dir, "system_config.tar.gz")
                
                # Create archive
                import tarfile
                with tarfile.open(archive_path, "w:gz") as tar:
                    for path in job.source_paths:
                        if os.path.exists(path):
                            tar.add(path, arcname=os.path.basename(path))
                
                # Upload archive
                remote_path = f"{job.destination_path}/system_config_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.tar.gz"
                
                def progress_callback(progress):
                    job.progress = progress
                    job.uploaded_size = int((progress / 100) * job.total_size)
                
                success = await self.exporter.upload_file(archive_path, remote_path, progress_callback)
                
                if success:
                    job.metadata['archive_path'] = remote_path
                    job.metadata['archive_size'] = os.path.getsize(archive_path)
                
                return success
                
        except Exception as e:
            logger.error("Failed to export system configuration", error=str(e))
            return False
    
    async def _export_database(self, job: ExportJob) -> bool:
        """Export database"""
        try:
            # Create database dump
            with tempfile.TemporaryDirectory() as temp_dir:
                dump_path = os.path.join(temp_dir, "database_dump.sql")
                
                # Create database dump (simplified)
                with open(dump_path, 'w') as f:
                
                # Upload dump
                remote_path = f"{job.destination_path}/database_dump_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.sql"
                
                def progress_callback(progress):
                    job.progress = progress
                    job.uploaded_size = int((progress / 100) * job.total_size)
                
                success = await self.exporter.upload_file(dump_path, remote_path, progress_callback)
                
                if success:
                    job.metadata['dump_path'] = remote_path
                    job.metadata['dump_size'] = os.path.getsize(dump_path)
                
                return success
                
        except Exception as e:
            logger.error("Failed to export database", error=str(e))
            return False
    
    async def _export_logs(self, job: ExportJob) -> bool:
        """Export logs"""
        try:
            # Create logs archive
            with tempfile.TemporaryDirectory() as temp_dir:
                archive_path = os.path.join(temp_dir, "logs.tar.gz")
                
                # Create archive
                import tarfile
                with tarfile.open(archive_path, "w:gz") as tar:
                    for path in job.source_paths:
                        if os.path.exists(path):
                            tar.add(path, arcname=os.path.basename(path))
                
                # Upload archive
                remote_path = f"{job.destination_path}/logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.tar.gz"
                
                def progress_callback(progress):
                    job.progress = progress
                    job.uploaded_size = int((progress / 100) * job.total_size)
                
                success = await self.exporter.upload_file(archive_path, remote_path, progress_callback)
                
                if success:
                    job.metadata['archive_path'] = remote_path
                    job.metadata['archive_size'] = os.path.getsize(archive_path)
                
                return success
                
        except Exception as e:
            logger.error("Failed to export logs", error=str(e))
            return False
    
    async def _export_blockchain_data(self, job: ExportJob) -> bool:
        """Export blockchain data"""
        try:
            # Create blockchain data archive
            with tempfile.TemporaryDirectory() as temp_dir:
                archive_path = os.path.join(temp_dir, "blockchain_data.tar.gz")
                
                # Create archive
                import tarfile
                with tarfile.open(archive_path, "w:gz") as tar:
                    for path in job.source_paths:
                        if os.path.exists(path):
                            tar.add(path, arcname=os.path.basename(path))
                
                # Upload archive
                remote_path = f"{job.destination_path}/blockchain_data_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.tar.gz"
                
                def progress_callback(progress):
                    job.progress = progress
                    job.uploaded_size = int((progress / 100) * job.total_size)
                
                success = await self.exporter.upload_file(archive_path, remote_path, progress_callback)
                
                if success:
                    job.metadata['archive_path'] = remote_path
                    job.metadata['archive_size'] = os.path.getsize(archive_path)
                
                return success
                
        except Exception as e:
            logger.error("Failed to export blockchain data", error=str(e))
            return False
    
    async def _export_full_system(self, job: ExportJob) -> bool:
        """Export full system"""
        try:
            # Create full system archive
            with tempfile.TemporaryDirectory() as temp_dir:
                archive_path = os.path.join(temp_dir, "full_system.tar.gz")
                
                # Create archive
                import tarfile
                with tarfile.open(archive_path, "w:gz") as tar:
                    for path in job.source_paths:
                        if os.path.exists(path):
                            tar.add(path, arcname=os.path.basename(path))
                
                # Upload archive
                remote_path = f"{job.destination_path}/full_system_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.tar.gz"
                
                def progress_callback(progress):
                    job.progress = progress
                    job.uploaded_size = int((progress / 100) * job.total_size)
                
                success = await self.exporter.upload_file(archive_path, remote_path, progress_callback)
                
                if success:
                    job.metadata['archive_path'] = remote_path
                    job.metadata['archive_size'] = os.path.getsize(archive_path)
                
                return success
                
        except Exception as e:
            logger.error("Failed to export full system", error=str(e))
            return False
    
    def get_job_status(self, job_id: str) -> Optional[ExportJob]:
        """Get export job status"""
        return self.jobs.get(job_id)
    
    def list_jobs(self) -> List[ExportJob]:
        """List all export jobs"""
        return list(self.jobs.values())
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel an export job"""
        try:
            if job_id not in self.jobs:
                return False
            
            job = self.jobs[job_id]
            
            if job.status == ExportStatus.PENDING:
                job.status = ExportStatus.CANCELLED
                logger.info("Export job cancelled", job_id=job_id)
                return True
            elif job.status == ExportStatus.IN_PROGRESS:
                # In a real implementation, this would stop the ongoing operation
                job.status = ExportStatus.CANCELLED
                logger.info("Export job cancelled", job_id=job_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Failed to cancel export job", job_id=job_id, error=str(e))
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        total_jobs = len(self.jobs)
        completed_jobs = len([j for j in self.jobs.values() if j.status == ExportStatus.COMPLETED])
        failed_jobs = len([j for j in self.jobs.values() if j.status == ExportStatus.FAILED])
        pending_jobs = len([j for j in self.jobs.values() if j.status == ExportStatus.PENDING])
        in_progress_jobs = len([j for j in self.jobs.values() if j.status == ExportStatus.IN_PROGRESS])
        
        return {
            'total_jobs': total_jobs,
            'completed_jobs': completed_jobs,
            'failed_jobs': failed_jobs,
            'pending_jobs': pending_jobs,
            'in_progress_jobs': in_progress_jobs,
            'success_rate': (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0,
            'is_running': self.is_running,
            'storage_provider': self.config.storage_provider.value,
            's3_available': S3_AVAILABLE,
            'async_available': ASYNC_AVAILABLE
        }


async def main():
    """Main entry point for exporter service"""
    # Configure logging
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
    
    # Create export configuration
    config = ExportConfig(
        storage_provider=StorageProvider.LOCAL_FILESYSTEM,  # Default to local
        bucket_name="/tmp/lucid_backups",
        region="us-east-1"
    )
    
    # Create and start service
    service = ExporterService(config)
    
    try:
        await service.start()
        
        # Keep running
        logger.info("Exporter service running")
        while service.is_running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
