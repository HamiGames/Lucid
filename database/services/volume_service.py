"""
Volume Service for Lucid Database Infrastructure
Provides volume management, monitoring, and optimization for database storage.

Database Cluster 08: Storage Database
Step 3: Redis & Elasticsearch Setup
"""

import asyncio
import logging
import os
import shutil
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VolumeService:
    """
    Volume management service for Lucid database infrastructure
    
    Provides:
    - Volume space monitoring
    - Storage usage tracking
    - Volume health checks
    - Cleanup and optimization
    - Storage alerts
    """
    
    def __init__(
        self,
        mongodb_data_path: str = "/data/mongodb",
        redis_data_path: str = "/data/redis",
        elasticsearch_data_path: str = "/data/elasticsearch",
        chunks_storage_path: str = "/data/chunks",
        merkle_storage_path: str = "/data/merkle",
        warning_threshold_percent: int = 80,
        critical_threshold_percent: int = 90
    ):
        """
        Initialize volume service
        
        Args:
            mongodb_data_path: MongoDB data directory
            redis_data_path: Redis data directory
            elasticsearch_data_path: Elasticsearch data directory
            chunks_storage_path: Session chunks storage
            merkle_storage_path: Merkle tree storage
            warning_threshold_percent: Warning threshold for disk usage
            critical_threshold_percent: Critical threshold for disk usage
        """
        self.volumes = {
            "mongodb": Path(mongodb_data_path),
            "redis": Path(redis_data_path),
            "elasticsearch": Path(elasticsearch_data_path),
            "chunks": Path(chunks_storage_path),
            "merkle": Path(merkle_storage_path)
        }
        
        self.warning_threshold = warning_threshold_percent
        self.critical_threshold = critical_threshold_percent
        
        self._create_volume_directories()
    
    def _create_volume_directories(self):
        """Create volume directories if they don't exist"""
        for name, path in self.volumes.items():
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Volume directory verified: {name} at {path}")
    
    async def get_volume_stats(self, volume_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get volume statistics
        
        Args:
            volume_name: Specific volume to check (all if None)
            
        Returns:
            Dict with volume statistics
        """
        try:
            stats = {}
            
            volumes_to_check = (
                {volume_name: self.volumes[volume_name]} 
                if volume_name and volume_name in self.volumes 
                else self.volumes
            )
            
            for name, path in volumes_to_check.items():
                if not path.exists():
                    stats[name] = {
                        "status": "missing",
                        "error": "Path does not exist"
                    }
                    continue
                
                # Get disk usage
                disk_usage = psutil.disk_usage(str(path))
                
                # Get directory size
                dir_size = self._get_directory_size(path)
                
                # Calculate usage percentage
                usage_percent = (dir_size / disk_usage.total * 100) if disk_usage.total > 0 else 0
                
                # Determine status
                status = "healthy"
                if usage_percent >= self.critical_threshold:
                    status = "critical"
                elif usage_percent >= self.warning_threshold:
                    status = "warning"
                
                stats[name] = {
                    "path": str(path),
                    "status": status,
                    "disk": {
                        "total": disk_usage.total,
                        "used": disk_usage.used,
                        "free": disk_usage.free,
                        "percent_used": disk_usage.percent
                    },
                    "directory": {
                        "size": dir_size,
                        "size_mb": dir_size / (1024 * 1024),
                        "size_gb": dir_size / (1024 * 1024 * 1024),
                        "percent_of_disk": usage_percent
                    },
                    "thresholds": {
                        "warning": self.warning_threshold,
                        "critical": self.critical_threshold
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "volumes": stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get volume stats: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_volume_health(self) -> Dict[str, Any]:
        """
        Get overall volume health status
        
        Returns:
            Dict with health status for all volumes
        """
        try:
            stats = await self.get_volume_stats()
            volumes = stats.get("volumes", {})
            
            # Determine overall health
            statuses = [vol.get("status", "unknown") for vol in volumes.values()]
            
            overall_status = "healthy"
            if "critical" in statuses:
                overall_status = "critical"
            elif "warning" in statuses:
                overall_status = "warning"
            elif "missing" in statuses:
                overall_status = "degraded"
            
            # Count volumes by status
            status_counts = {
                "healthy": statuses.count("healthy"),
                "warning": statuses.count("warning"),
                "critical": statuses.count("critical"),
                "missing": statuses.count("missing")
            }
            
            # Identify problem volumes
            problem_volumes = [
                name for name, vol in volumes.items() 
                if vol.get("status") != "healthy"
            ]
            
            return {
                "status": overall_status,
                "timestamp": datetime.utcnow().isoformat(),
                "total_volumes": len(volumes),
                "status_counts": status_counts,
                "problem_volumes": problem_volumes,
                "volumes": volumes
            }
            
        except Exception as e:
            logger.error(f"Failed to get volume health: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def check_volume_space(self, volume_name: str, required_gb: float) -> bool:
        """
        Check if volume has required free space
        
        Args:
            volume_name: Name of volume to check
            required_gb: Required free space in GB
            
        Returns:
            bool: True if enough space available
        """
        try:
            if volume_name not in self.volumes:
                logger.error(f"Unknown volume: {volume_name}")
                return False
            
            path = self.volumes[volume_name]
            disk_usage = psutil.disk_usage(str(path))
            
            required_bytes = required_gb * 1024 * 1024 * 1024
            has_space = disk_usage.free >= required_bytes
            
            if not has_space:
                logger.warning(
                    f"Insufficient space on {volume_name}: "
                    f"Required {required_gb}GB, Available {disk_usage.free / (1024**3):.2f}GB"
                )
            
            return has_space
            
        except Exception as e:
            logger.error(f"Failed to check volume space: {e}")
            return False
    
    async def cleanup_volume(
        self, 
        volume_name: str,
        older_than_days: Optional[int] = None,
        file_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Clean up old files from a volume
        
        Args:
            volume_name: Name of volume to clean
            older_than_days: Delete files older than this many days
            file_pattern: Pattern to match files (e.g., "*.tmp")
            
        Returns:
            Dict with cleanup statistics
        """
        try:
            if volume_name not in self.volumes:
                return {
                    "success": False,
                    "error": f"Unknown volume: {volume_name}"
                }
            
            path = self.volumes[volume_name]
            deleted_count = 0
            deleted_size = 0
            
            cutoff_time = None
            if older_than_days:
                from datetime import timedelta
                cutoff_time = datetime.utcnow() - timedelta(days=older_than_days)
            
            # Iterate through files
            for file_path in path.rglob('*'):
                if not file_path.is_file():
                    continue
                
                # Check file pattern
                if file_pattern and not file_path.match(file_pattern):
                    continue
                
                # Check file age
                if cutoff_time:
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_mtime > cutoff_time:
                        continue
                
                # Delete file
                try:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    deleted_count += 1
                    deleted_size += file_size
                    logger.debug(f"Deleted: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path}: {e}")
            
            logger.info(
                f"Volume cleanup completed: {volume_name} - "
                f"{deleted_count} files, {deleted_size / (1024**2):.2f}MB freed"
            )
            
            return {
                "success": True,
                "volume": volume_name,
                "deleted_files": deleted_count,
                "deleted_size_bytes": deleted_size,
                "deleted_size_mb": deleted_size / (1024 * 1024),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Volume cleanup error: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def optimize_volume(self, volume_name: str) -> Dict[str, Any]:
        """
        Optimize volume storage
        
        Args:
            volume_name: Name of volume to optimize
            
        Returns:
            Dict with optimization results
        """
        try:
            if volume_name not in self.volumes:
                return {
                    "success": False,
                    "error": f"Unknown volume: {volume_name}"
                }
            
            results = {
                "volume": volume_name,
                "optimizations": []
            }
            
            # Remove empty directories
            empty_dirs = self._remove_empty_directories(self.volumes[volume_name])
            if empty_dirs > 0:
                results["optimizations"].append({
                    "type": "empty_directories_removed",
                    "count": empty_dirs
                })
            
            # Remove duplicate files (simplified - actual implementation would be more complex)
            # This is a placeholder for more sophisticated deduplication
            
            # Update permissions (if needed)
            # This is a placeholder for permission optimization
            
            results["success"] = True
            results["timestamp"] = datetime.utcnow().isoformat()
            
            logger.info(f"Volume optimization completed: {volume_name}")
            return results
            
        except Exception as e:
            logger.error(f"Volume optimization error: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _remove_empty_directories(self, path: Path) -> int:
        """Remove empty directories recursively"""
        removed_count = 0
        try:
            for dirpath in sorted(path.rglob('*'), reverse=True):
                if dirpath.is_dir() and not any(dirpath.iterdir()):
                    dirpath.rmdir()
                    removed_count += 1
                    logger.debug(f"Removed empty directory: {dirpath}")
        except Exception as e:
            logger.warning(f"Error removing empty directories: {e}")
        return removed_count
    
    async def monitor_volume_growth(
        self, 
        volume_name: str,
        duration_seconds: int = 60
    ) -> Dict[str, Any]:
        """
        Monitor volume growth rate
        
        Args:
            volume_name: Name of volume to monitor
            duration_seconds: Duration to monitor (in seconds)
            
        Returns:
            Dict with growth statistics
        """
        try:
            if volume_name not in self.volumes:
                return {
                    "success": False,
                    "error": f"Unknown volume: {volume_name}"
                }
            
            path = self.volumes[volume_name]
            
            # Initial measurement
            initial_size = self._get_directory_size(path)
            initial_time = datetime.utcnow()
            
            # Wait for duration
            await asyncio.sleep(duration_seconds)
            
            # Final measurement
            final_size = self._get_directory_size(path)
            final_time = datetime.utcnow()
            
            # Calculate growth
            size_change = final_size - initial_size
            time_delta = (final_time - initial_time).total_seconds()
            growth_rate_per_hour = (size_change / time_delta) * 3600 if time_delta > 0 else 0
            
            return {
                "success": True,
                "volume": volume_name,
                "initial_size_bytes": initial_size,
                "final_size_bytes": final_size,
                "size_change_bytes": size_change,
                "size_change_mb": size_change / (1024 * 1024),
                "monitoring_duration_seconds": time_delta,
                "growth_rate_bytes_per_hour": growth_rate_per_hour,
                "growth_rate_mb_per_hour": growth_rate_per_hour / (1024 * 1024),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Volume monitoring error: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def export_volume_report(self, output_path: Optional[str] = None) -> str:
        """
        Export comprehensive volume report
        
        Args:
            output_path: Path to save report (auto-generated if None)
            
        Returns:
            Path to generated report
        """
        try:
            # Gather all statistics
            health = await self.get_volume_health()
            stats = await self.get_volume_stats()
            
            report = {
                "report_type": "volume_health_report",
                "generated_at": datetime.utcnow().isoformat(),
                "overall_health": health,
                "detailed_stats": stats
            }
            
            # Determine output path
            if not output_path:
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                output_path = f"/tmp/volume_report_{timestamp}.json"
            
            # Write report
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Volume report exported to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to export volume report: {e}")
            raise
    
    def _get_directory_size(self, path: Path) -> int:
        """Calculate total size of directory"""
        total_size = 0
        try:
            for item in path.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size
        except Exception as e:
            logger.warning(f"Could not calculate directory size for {path}: {e}")
        return total_size
    
    async def create_volume_snapshot(self, volume_name: str) -> Dict[str, Any]:
        """
        Create a snapshot of current volume state
        
        Args:
            volume_name: Name of volume to snapshot
            
        Returns:
            Dict with snapshot metadata
        """
        try:
            if volume_name not in self.volumes:
                return {
                    "success": False,
                    "error": f"Unknown volume: {volume_name}"
                }
            
            stats = await self.get_volume_stats(volume_name)
            
            snapshot = {
                "volume": volume_name,
                "timestamp": datetime.utcnow().isoformat(),
                "stats": stats.get("volumes", {}).get(volume_name, {}),
                "snapshot_type": "volume_state"
            }
            
            # Save snapshot
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            snapshot_path = Path(f"/tmp/volume_snapshot_{volume_name}_{timestamp}.json")
            
            with open(snapshot_path, 'w') as f:
                json.dump(snapshot, f, indent=2)
            
            logger.info(f"Volume snapshot created: {snapshot_path}")
            
            return {
                "success": True,
                "snapshot_path": str(snapshot_path),
                "snapshot": snapshot
            }
            
        except Exception as e:
            logger.error(f"Failed to create volume snapshot: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Global volume service instance
volume_service = None

async def get_volume_service(**kwargs) -> VolumeService:
    """
    Get or create volume service instance
    
    Args:
        **kwargs: VolumeService initialization parameters
        
    Returns:
        VolumeService instance
    """
    global volume_service
    
    if volume_service is None:
        volume_service = VolumeService(**kwargs)
    
    return volume_service
