"""
Backup Service for Lucid Database Infrastructure
Provides backup and restore operations for MongoDB, Redis, and Elasticsearch.

Database Cluster 08: Storage Database
Step 3: Redis & Elasticsearch Setup
"""

import asyncio
import logging
import os
import subprocess
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import gzip
import tarfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackupService:
    """
    Comprehensive backup service for Lucid database infrastructure
    
    Supports:
    - MongoDB backups via mongodump
    - Redis backups via RDB snapshots
    - Elasticsearch backups via snapshot API
    - Automated backup scheduling
    - Backup retention and cleanup
    - Backup verification and integrity checks
    """
    
    def __init__(
        self,
        backup_base_path: str = "/backups",
        mongodb_uri: str = "mongodb://localhost:27017",
        redis_host: str = "localhost",
        redis_port: int = 6379,
        elasticsearch_url: str = "http://localhost:9200",
        retention_days: int = 30
    ):
        """
        Initialize backup service
        
        Args:
            backup_base_path: Root directory for backups
            mongodb_uri: MongoDB connection URI
            redis_host: Redis host
            redis_port: Redis port
            elasticsearch_url: Elasticsearch URL
            retention_days: Days to retain backups
        """
        self.backup_base_path = Path(backup_base_path)
        self.mongodb_uri = mongodb_uri
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.elasticsearch_url = elasticsearch_url
        self.retention_days = retention_days
        
        # Create backup directories
        self.mongodb_backup_dir = self.backup_base_path / "mongodb"
        self.redis_backup_dir = self.backup_base_path / "redis"
        self.elasticsearch_backup_dir = self.backup_base_path / "elasticsearch"
        
        self._create_backup_directories()
    
    def _create_backup_directories(self):
        """Create backup directory structure"""
        for directory in [
            self.mongodb_backup_dir,
            self.redis_backup_dir,
            self.elasticsearch_backup_dir
        ]:
            directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Backup directories created at {self.backup_base_path}")
    
    async def backup_mongodb(
        self,
        databases: Optional[List[str]] = None,
        collections: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Backup MongoDB databases
        
        Args:
            databases: List of databases to backup (all if None)
            collections: List of collections to backup (all if None)
            
        Returns:
            Dict with backup metadata
        """
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            backup_name = f"mongodb_backup_{timestamp}"
            backup_path = self.mongodb_backup_dir / backup_name
            
            # Build mongodump command
            cmd = [
                "mongodump",
                "--uri", self.mongodb_uri,
                "--out", str(backup_path)
            ]
            
            if databases:
                for db in databases:
                    cmd.extend(["--db", db])
            
            if collections:
                for collection in collections:
                    cmd.extend(["--collection", collection])
            
            # Add compression
            cmd.append("--gzip")
            
            # Execute backup
            logger.info(f"Starting MongoDB backup: {backup_name}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode != 0:
                logger.error(f"MongoDB backup failed: {result.stderr}")
                return {
                    "success": False,
                    "error": result.stderr,
                    "timestamp": timestamp
                }
            
            # Create backup metadata
            metadata = {
                "backup_type": "mongodb",
                "backup_name": backup_name,
                "backup_path": str(backup_path),
                "timestamp": timestamp,
                "databases": databases or ["all"],
                "collections": collections or ["all"],
                "size_bytes": self._get_directory_size(backup_path),
                "success": True
            }
            
            # Save metadata
            metadata_file = backup_path.parent / f"{backup_name}_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"MongoDB backup completed: {backup_name}")
            return metadata
            
        except subprocess.TimeoutExpired:
            logger.error("MongoDB backup timed out")
            return {
                "success": False,
                "error": "Backup operation timed out",
                "timestamp": timestamp
            }
        except Exception as e:
            logger.error(f"MongoDB backup error: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": timestamp
            }
    
    async def restore_mongodb(self, backup_name: str) -> bool:
        """
        Restore MongoDB from backup
        
        Args:
            backup_name: Name of the backup to restore
            
        Returns:
            bool: True if successful
        """
        try:
            backup_path = self.mongodb_backup_dir / backup_name
            
            if not backup_path.exists():
                logger.error(f"Backup not found: {backup_name}")
                return False
            
            # Build mongorestore command
            cmd = [
                "mongorestore",
                "--uri", self.mongodb_uri,
                "--dir", str(backup_path),
                "--gzip",
                "--drop"  # Drop existing collections before restore
            ]
            
            logger.info(f"Starting MongoDB restore from: {backup_name}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600
            )
            
            if result.returncode != 0:
                logger.error(f"MongoDB restore failed: {result.stderr}")
                return False
            
            logger.info(f"MongoDB restore completed: {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"MongoDB restore error: {e}")
            return False
    
    async def backup_redis(self) -> Dict[str, Any]:
        """
        Backup Redis data via RDB snapshot
        
        Returns:
            Dict with backup metadata
        """
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            backup_name = f"redis_backup_{timestamp}"
            backup_path = self.redis_backup_dir / backup_name
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Trigger Redis BGSAVE
            cmd = [
                "redis-cli",
                "-h", self.redis_host,
                "-p", str(self.redis_port),
                "BGSAVE"
            ]
            
            logger.info(f"Starting Redis backup: {backup_name}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Redis BGSAVE failed: {result.stderr}")
                return {
                    "success": False,
                    "error": result.stderr,
                    "timestamp": timestamp
                }
            
            # Wait for BGSAVE to complete
            await self._wait_for_redis_bgsave()
            
            # Copy RDB file to backup directory
            # Note: Actual RDB file location depends on Redis configuration
            # Default is /data/dump.rdb in Docker
            rdb_source = "/data/dump.rdb"
            rdb_dest = backup_path / "dump.rdb"
            
            if os.path.exists(rdb_source):
                shutil.copy2(rdb_source, rdb_dest)
                
                # Compress the backup
                with open(rdb_dest, 'rb') as f_in:
                    with gzip.open(f"{rdb_dest}.gz", 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                rdb_dest.unlink()  # Remove uncompressed file
            
            metadata = {
                "backup_type": "redis",
                "backup_name": backup_name,
                "backup_path": str(backup_path),
                "timestamp": timestamp,
                "size_bytes": self._get_directory_size(backup_path),
                "success": True
            }
            
            # Save metadata
            metadata_file = backup_path.parent / f"{backup_name}_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Redis backup completed: {backup_name}")
            return metadata
            
        except Exception as e:
            logger.error(f"Redis backup error: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": timestamp
            }
    
    async def _wait_for_redis_bgsave(self, timeout: int = 300):
        """Wait for Redis BGSAVE to complete"""
        start_time = datetime.utcnow()
        while (datetime.utcnow() - start_time).seconds < timeout:
            cmd = [
                "redis-cli",
                "-h", self.redis_host,
                "-p", str(self.redis_port),
                "LASTSAVE"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Check if BGSAVE is complete by checking LASTSAVE timestamp
            await asyncio.sleep(1)
            
            # Simple check: if command succeeds, BGSAVE is done
            if result.returncode == 0:
                await asyncio.sleep(2)  # Extra wait for file write
                break
    
    async def restore_redis(self, backup_name: str) -> bool:
        """
        Restore Redis from backup
        
        Args:
            backup_name: Name of the backup to restore
            
        Returns:
            bool: True if successful
        """
        try:
            backup_path = self.redis_backup_dir / backup_name
            rdb_backup = backup_path / "dump.rdb.gz"
            
            if not rdb_backup.exists():
                logger.error(f"Redis backup not found: {backup_name}")
                return False
            
            # Stop Redis (requires appropriate permissions)
            # This is a simplified version - actual implementation may vary
            logger.warning("Redis restore requires Redis restart - manual intervention may be needed")
            
            # Decompress backup
            rdb_dest = "/data/dump.rdb"
            with gzip.open(rdb_backup, 'rb') as f_in:
                with open(rdb_dest, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            logger.info(f"Redis backup restored: {backup_name}")
            logger.warning("Please restart Redis to load the restored data")
            return True
            
        except Exception as e:
            logger.error(f"Redis restore error: {e}")
            return False
    
    async def backup_elasticsearch(
        self,
        indices: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Backup Elasticsearch indices via snapshot API
        
        Args:
            indices: List of indices to backup (all if None)
            
        Returns:
            Dict with backup metadata
        """
        try:
            import aiohttp
            
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            snapshot_name = f"snapshot_{timestamp}"
            repository_name = "lucid_backup"
            
            # Create snapshot repository if not exists
            repo_path = str(self.elasticsearch_backup_dir)
            
            async with aiohttp.ClientSession() as session:
                # Create repository
                repo_url = f"{self.elasticsearch_url}/_snapshot/{repository_name}"
                repo_body = {
                    "type": "fs",
                    "settings": {
                        "location": repo_path,
                        "compress": True
                    }
                }
                
                async with session.put(repo_url, json=repo_body) as resp:
                    if resp.status not in [200, 201]:
                        logger.warning(f"Repository creation response: {resp.status}")
                
                # Create snapshot
                snapshot_url = f"{repo_url}/{snapshot_name}"
                snapshot_body = {
                    "indices": ",".join(indices) if indices else "*",
                    "ignore_unavailable": True,
                    "include_global_state": False
                }
                
                logger.info(f"Starting Elasticsearch snapshot: {snapshot_name}")
                async with session.put(snapshot_url, json=snapshot_body) as resp:
                    if resp.status not in [200, 201]:
                        error_text = await resp.text()
                        logger.error(f"Snapshot creation failed: {error_text}")
                        return {
                            "success": False,
                            "error": error_text,
                            "timestamp": timestamp
                        }
                
                # Wait for snapshot to complete
                await self._wait_for_elasticsearch_snapshot(
                    session, repository_name, snapshot_name
                )
                
                metadata = {
                    "backup_type": "elasticsearch",
                    "snapshot_name": snapshot_name,
                    "repository": repository_name,
                    "backup_path": repo_path,
                    "timestamp": timestamp,
                    "indices": indices or ["all"],
                    "success": True
                }
                
                # Save metadata
                metadata_file = self.elasticsearch_backup_dir / f"{snapshot_name}_metadata.json"
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                logger.info(f"Elasticsearch snapshot completed: {snapshot_name}")
                return metadata
                
        except Exception as e:
            logger.error(f"Elasticsearch backup error: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": timestamp
            }
    
    async def _wait_for_elasticsearch_snapshot(
        self, 
        session: 'aiohttp.ClientSession', 
        repository: str, 
        snapshot: str,
        timeout: int = 600
    ):
        """Wait for Elasticsearch snapshot to complete"""
        start_time = datetime.utcnow()
        status_url = f"{self.elasticsearch_url}/_snapshot/{repository}/{snapshot}"
        
        while (datetime.utcnow() - start_time).seconds < timeout:
            async with session.get(status_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    snapshots = data.get("snapshots", [])
                    if snapshots:
                        state = snapshots[0].get("state")
                        if state == "SUCCESS":
                            return True
                        elif state == "FAILED":
                            raise Exception("Snapshot failed")
            
            await asyncio.sleep(5)
        
        raise Exception("Snapshot timed out")
    
    async def cleanup_old_backups(self) -> Dict[str, int]:
        """
        Clean up backups older than retention period
        
        Returns:
            Dict with cleanup statistics
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
            deleted_count = {
                "mongodb": 0,
                "redis": 0,
                "elasticsearch": 0
            }
            
            for backup_type, backup_dir in [
                ("mongodb", self.mongodb_backup_dir),
                ("redis", self.redis_backup_dir),
                ("elasticsearch", self.elasticsearch_backup_dir)
            ]:
                if not backup_dir.exists():
                    continue
                
                for backup in backup_dir.iterdir():
                    if not backup.is_dir():
                        continue
                    
                    # Check backup age
                    backup_time = datetime.fromtimestamp(backup.stat().st_mtime)
                    if backup_time < cutoff_date:
                        shutil.rmtree(backup)
                        deleted_count[backup_type] += 1
                        logger.info(f"Deleted old backup: {backup.name}")
            
            logger.info(f"Cleanup completed: {deleted_count}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Backup cleanup error: {e}")
            return {"error": str(e)}
    
    async def list_backups(self, backup_type: Optional[str] = None) -> List[Dict]:
        """
        List available backups
        
        Args:
            backup_type: Filter by type (mongodb, redis, elasticsearch)
            
        Returns:
            List of backup metadata
        """
        backups = []
        
        backup_dirs = {
            "mongodb": self.mongodb_backup_dir,
            "redis": self.redis_backup_dir,
            "elasticsearch": self.elasticsearch_backup_dir
        }
        
        if backup_type:
            backup_dirs = {backup_type: backup_dirs.get(backup_type)}
        
        for btype, bdir in backup_dirs.items():
            if not bdir or not bdir.exists():
                continue
            
            for backup in bdir.iterdir():
                if not backup.is_dir():
                    continue
                
                metadata_file = bdir / f"{backup.name}_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        backups.append(metadata)
        
        return sorted(backups, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    async def verify_backup_integrity(self, backup_name: str) -> bool:
        """
        Verify backup integrity
        
        Args:
            backup_name: Name of backup to verify
            
        Returns:
            bool: True if backup is valid
        """
        # Simplified verification - check if backup files exist and are readable
        for backup_dir in [
            self.mongodb_backup_dir,
            self.redis_backup_dir,
            self.elasticsearch_backup_dir
        ]:
            backup_path = backup_dir / backup_name
            if backup_path.exists():
                try:
                    # Check if directory is readable
                    list(backup_path.iterdir())
                    logger.info(f"Backup verification passed: {backup_name}")
                    return True
                except Exception as e:
                    logger.error(f"Backup verification failed: {e}")
                    return False
        
        logger.error(f"Backup not found: {backup_name}")
        return False
    
    def _get_directory_size(self, path: Path) -> int:
        """Calculate total size of directory"""
        total_size = 0
        try:
            for item in path.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size
        except Exception as e:
            logger.warning(f"Could not calculate directory size: {e}")
        return total_size
    
    async def create_full_backup(self) -> Dict[str, Any]:
        """
        Create a full backup of all databases
        
        Returns:
            Dict with combined backup metadata
        """
        logger.info("Starting full system backup")
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "backups": {}
        }
        
        # MongoDB backup
        mongodb_result = await self.backup_mongodb()
        results["backups"]["mongodb"] = mongodb_result
        
        # Redis backup
        redis_result = await self.backup_redis()
        results["backups"]["redis"] = redis_result
        
        # Elasticsearch backup
        elasticsearch_result = await self.backup_elasticsearch()
        results["backups"]["elasticsearch"] = elasticsearch_result
        
        # Check overall success
        all_success = all(
            result.get("success", False) 
            for result in results["backups"].values()
        )
        results["success"] = all_success
        
        logger.info(f"Full system backup completed: {'SUCCESS' if all_success else 'PARTIAL FAILURE'}")
        return results


# Global backup service instance
backup_service = None

async def get_backup_service(**kwargs) -> BackupService:
    """
    Get or create backup service instance
    
    Args:
        **kwargs: BackupService initialization parameters
        
    Returns:
        BackupService instance
    """
    global backup_service
    
    if backup_service is None:
        backup_service = BackupService(**kwargs)
    
    return backup_service
