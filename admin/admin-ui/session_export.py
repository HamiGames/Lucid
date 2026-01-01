"""
LUCID Admin UI - Session Manifest Export
Handles session data export, manifest generation, and proof export
Distroless container: pickme/lucid:admin-ui:latest
"""

import asyncio
import json
import logging
import os
import hashlib
import base64
import zipfile
import csv
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, BinaryIO
import aiofiles
import yaml
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field
import cryptography
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    MANIFEST = "manifest"
    PROOF = "proof"
    ARCHIVE = "archive"

class ExportStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class SessionChunk:
    """Session chunk data"""
    chunk_id: str
    index: int
    size: int
    hash: str
    encrypted_data: Optional[bytes] = None
    merkle_proof: Optional[List[str]] = None

@dataclass
class SessionManifest:
    """Session manifest data"""
    session_id: str
    created_at: datetime
    completed_at: Optional[datetime]
    status: SessionStatus
    owner_address: str
    node_id: str
    chunk_count: int
    total_size: int
    merkle_root: str
    chunks: List[SessionChunk]
    metadata: Dict[str, Any]

class ExportRequest(BaseModel):
    """Pydantic model for export requests"""
    session_ids: List[str] = Field(..., description="List of session IDs to export")
    export_format: ExportFormat = Field(default=ExportFormat.JSON, description="Export format")
    include_metadata: bool = Field(default=True, description="Include session metadata")
    include_chunks: bool = Field(default=False, description="Include chunk data")
    include_proofs: bool = Field(default=True, description="Include Merkle proofs")
    encryption_key: Optional[str] = Field(default=None, description="Encryption key for sensitive data")
    compression: bool = Field(default=True, description="Enable compression")
    filter_date_from: Optional[datetime] = Field(default=None, description="Filter sessions from date")
    filter_date_to: Optional[datetime] = Field(default=None, description="Filter sessions to date")
    filter_status: Optional[SessionStatus] = Field(default=None, description="Filter by session status")

class ExportStatusResponse(BaseModel):
    """Response model for export status"""
    export_id: str
    status: ExportStatus
    progress: int = Field(ge=0, le=100, description="Progress percentage")
    message: str
    created_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    error_details: Optional[str] = None
    session_count: int = 0
    exported_count: int = 0

class SessionExportManager:
    """Manages session data export and manifest generation"""
    
    def __init__(self):
        # Data storage paths - configured via environment variables
        base_data_dir = Path(os.getenv("ADMIN_DATA_DIR", "/app/data"))
        self.data_dir = Path(os.getenv("ADMIN_EXPORTS_DIR", str(base_data_dir / "exports")))
        self.temp_dir = Path(os.getenv("ADMIN_TEMP_DIR", str(base_data_dir / "temp")))
        self.logs_dir = Path(os.getenv("ADMIN_LOGS_DIR", str(base_data_dir / "logs")))
        self.keys_dir = Path(os.getenv("ADMIN_KEYS_DIR", str(base_data_dir / "keys")))
        
        # Ensure directories exist
        for directory in [self.data_dir, self.temp_dir, self.logs_dir, self.keys_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Configuration - all values must be provided via environment variables
        self.mongodb_url = os.getenv("MONGODB_URL") or os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
        self.blockchain_api_url = os.getenv("BLOCKCHAIN_API_URL") or os.getenv("BLOCKCHAIN_ENGINE_URL") or os.getenv("BLOCKCHAIN_URL")
        
        if not self.mongodb_url:
            raise ValueError("MONGODB_URL, MONGODB_URI, or MONGO_URI environment variable must be set")
        if not self.blockchain_api_url:
            raise ValueError("BLOCKCHAIN_API_URL, BLOCKCHAIN_ENGINE_URL, or BLOCKCHAIN_URL environment variable must be set")
        self.max_export_size_mb = int(os.getenv("MAX_EXPORT_SIZE_MB", "1000"))
        
        # Export state
        self.active_exports: Dict[str, ExportStatusResponse] = {}
        
        # Load existing export state
        asyncio.create_task(self._load_export_state())
    
    async def _load_export_state(self):
        """Load existing export state from disk"""
        try:
            state_file = self.data_dir / "export_state.json"
            if state_file.exists():
                async with aiofiles.open(state_file, "r") as f:
                    data = await f.read()
                    state = json.loads(data)
                    
                    # Restore active exports
                    for export_id, status_data in state.get("active_exports", {}).items():
                        self.active_exports[export_id] = ExportStatusResponse(**status_data)
                    
                logger.info(f"Loaded export state: {len(self.active_exports)} active exports")
        except Exception as e:
            logger.error(f"Error loading export state: {e}")
    
    async def _save_export_state(self):
        """Save current export state to disk"""
        try:
            state = {
                "active_exports": {k: asdict(v) for k, v in self.active_exports.items()},
                "last_updated": datetime.now().isoformat()
            }
            
            state_file = self.data_dir / "export_state.json"
            async with aiofiles.open(state_file, "w") as f:
                await f.write(json.dumps(state, indent=2, default=str))
                
        except Exception as e:
            logger.error(f"Error saving export state: {e}")
    
    async def create_export_request(self, request: ExportRequest) -> str:
        """Create a new export request"""
        try:
            export_id = f"export_{int(datetime.now().timestamp())}_{len(request.session_ids)}"
            
            # Validate request
            await self._validate_export_request(request)
            
            # Create status response
            status_response = ExportStatusResponse(
                export_id=export_id,
                status=ExportStatus.PENDING,
                progress=0,
                message="Export request created",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                estimated_completion=datetime.now() + timedelta(minutes=5),
                session_count=len(request.session_ids)
            )
            
            # Add to active exports
            self.active_exports[export_id] = status_response
            
            # Save state
            await self._save_export_state()
            
            # Log request
            await self._log_export_event(export_id, "request_created", {
                "session_count": len(request.session_ids),
                "export_format": request.export_format,
                "include_chunks": request.include_chunks
            })
            
            # Start export process
            asyncio.create_task(self._process_export(export_id, request))
            
            logger.info(f"Created export request: {export_id} for {len(request.session_ids)} sessions")
            return export_id
            
        except Exception as e:
            logger.error(f"Error creating export request: {e}")
            raise
    
    async def _validate_export_request(self, request: ExportRequest):
        """Validate export request"""
        if not request.session_ids:
            raise ValueError("No session IDs provided")
        
        if len(request.session_ids) > 1000:
            raise ValueError("Too many sessions requested (max 1000)")
        
        # Check if sessions exist and are accessible
        for session_id in request.session_ids:
            if not await self._session_exists(session_id):
                raise ValueError(f"Session {session_id} not found")
        
        # Validate date filters
        if request.filter_date_from and request.filter_date_to:
            if request.filter_date_from > request.filter_date_to:
                raise ValueError("Invalid date range: from date must be before to date")
    
    async def _session_exists(self, session_id: str) -> bool:
        """Check if session exists"""
        # This would check MongoDB in production
        return True
    
    async def _process_export(self, export_id: str, request: ExportRequest):
        """Process export request"""
        if export_id not in self.active_exports:
            logger.error(f"Export request not found: {export_id}")
            return
        
        status_response = self.active_exports[export_id]
        
        try:
            # Update status to in progress
            status_response.status = ExportStatus.IN_PROGRESS
            status_response.progress = 10
            status_response.message = "Starting session export"
            status_response.updated_at = datetime.now()
            await self._save_export_state()
            
            # Step 1: Collect session data
            sessions_data = await self._collect_session_data(request)
            status_response.progress = 30
            status_response.message = "Session data collected"
            await self._save_export_state()
            
            # Step 2: Generate manifests
            manifests = await self._generate_manifests(sessions_data, request)
            status_response.progress = 50
            status_response.message = "Manifests generated"
            await self._save_export_state()
            
            # Step 3: Export data
            export_file = await self._export_data(export_id, manifests, request)
            status_response.progress = 80
            status_response.message = "Data exported"
            await self._save_export_state()
            
            # Step 4: Finalize export
            await self._finalize_export(export_id, export_file)
            status_response.progress = 100
            status_response.status = ExportStatus.COMPLETED
            status_response.message = "Export completed successfully"
            status_response.file_path = str(export_file)
            status_response.file_size = export_file.stat().st_size
            status_response.exported_count = len(sessions_data)
            status_response.updated_at = datetime.now()
            await self._save_export_state()
            
            # Log success
            await self._log_export_event(export_id, "export_completed", {
                "file_path": str(export_file),
                "file_size": export_file.stat().st_size,
                "session_count": len(sessions_data)
            })
            
            logger.info(f"Successfully exported sessions: {export_id}")
            
        except Exception as e:
            # Update status to failed
            status_response.status = ExportStatus.FAILED
            status_response.error_details = str(e)
            status_response.message = f"Export failed: {str(e)}"
            status_response.updated_at = datetime.now()
            await self._save_export_state()
            
            # Log failure
            await self._log_export_event(export_id, "export_failed", {
                "error": str(e)
            })
            
            logger.error(f"Failed to export sessions {export_id}: {e}")
            raise
    
    async def _collect_session_data(self, request: ExportRequest) -> List[Dict[str, Any]]:
        """Collect session data from database"""
        try:
            sessions_data = []
            
            for session_id in request.session_ids:
                # This would query MongoDB in production
                session_data = {
                    "session_id": session_id,
                    "created_at": datetime.now() - timedelta(hours=2),
                    "completed_at": datetime.now() - timedelta(hours=1),
                    "status": "completed",
                    "owner_address": "TYourAddress123",
                    "node_id": "node-001",
                    "chunk_count": 150,
                    "total_size": 1024000,
                    "merkle_root": "0x1234567890abcdef",
                    "chunks": [],
                    "metadata": {
                        "compression": "zstd",
                        "encryption": "XChaCha20-Poly1305",
                        "chunk_size": 8192
                    }
                }
                
                # Add chunks if requested
                if request.include_chunks:
                    for i in range(10):  # Simulate chunks
                        chunk = {
                            "chunk_id": f"{session_id}_chunk_{i}",
                            "index": i,
                            "size": 8192,
                            "hash": f"chunk_hash_{i}",
                            "merkle_proof": [f"proof_{i}_{j}" for j in range(3)]
                        }
                        session_data["chunks"].append(chunk)
                
                # Apply filters
                if request.filter_date_from and session_data["created_at"] < request.filter_date_from:
                    continue
                if request.filter_date_to and session_data["created_at"] > request.filter_date_to:
                    continue
                if request.filter_status and session_data["status"] != request.filter_status.value:
                    continue
                
                sessions_data.append(session_data)
            
            return sessions_data
            
        except Exception as e:
            logger.error(f"Error collecting session data: {e}")
            raise
    
    async def _generate_manifests(self, sessions_data: List[Dict[str, Any]], request: ExportRequest) -> List[SessionManifest]:
        """Generate session manifests"""
        try:
            manifests = []
            
            for session_data in sessions_data:
                # Create chunks
                chunks = []
                for chunk_data in session_data.get("chunks", []):
                    chunk = SessionChunk(
                        chunk_id=chunk_data["chunk_id"],
                        index=chunk_data["index"],
                        size=chunk_data["size"],
                        hash=chunk_data["hash"],
                        merkle_proof=chunk_data.get("merkle_proof")
                    )
                    chunks.append(chunk)
                
                # Create manifest
                manifest = SessionManifest(
                    session_id=session_data["session_id"],
                    created_at=session_data["created_at"],
                    completed_at=session_data.get("completed_at"),
                    status=SessionStatus(session_data["status"]),
                    owner_address=session_data["owner_address"],
                    node_id=session_data["node_id"],
                    chunk_count=session_data["chunk_count"],
                    total_size=session_data["total_size"],
                    merkle_root=session_data["merkle_root"],
                    chunks=chunks,
                    metadata=session_data.get("metadata", {})
                )
                
                manifests.append(manifest)
            
            return manifests
            
        except Exception as e:
            logger.error(f"Error generating manifests: {e}")
            raise
    
    async def _export_data(self, export_id: str, manifests: List[SessionManifest], request: ExportRequest) -> Path:
        """Export data in requested format"""
        try:
            temp_file = self.temp_dir / f"{export_id}_temp"
            export_file = self.data_dir / f"{export_id}.{request.export_format}"
            
            if request.export_format == ExportFormat.JSON:
                await self._export_json(manifests, export_file, request)
            elif request.export_format == ExportFormat.CSV:
                await self._export_csv(manifests, export_file, request)
            elif request.export_format == ExportFormat.MANIFEST:
                await self._export_manifest(manifests, export_file, request)
            elif request.export_format == ExportFormat.PROOF:
                await self._export_proof(manifests, export_file, request)
            elif request.export_format == ExportFormat.ARCHIVE:
                await self._export_archive(manifests, export_file, request)
            else:
                raise ValueError(f"Unsupported export format: {request.export_format}")
            
            # Apply encryption if requested
            if request.encryption_key:
                await self._encrypt_export(export_file, request.encryption_key)
            
            # Apply compression if requested
            if request.compression:
                await self._compress_export(export_file)
            
            return export_file
            
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            raise
    
    async def _export_json(self, manifests: List[SessionManifest], export_file: Path, request: ExportRequest):
        """Export data as JSON"""
        try:
            export_data = {
                "export_info": {
                    "export_id": export_file.stem,
                    "created_at": datetime.now().isoformat(),
                    "format": "json",
                    "session_count": len(manifests),
                    "include_metadata": request.include_metadata,
                    "include_chunks": request.include_chunks,
                    "include_proofs": request.include_proofs
                },
                "sessions": []
            }
            
            for manifest in manifests:
                session_data = {
                    "session_id": manifest.session_id,
                    "created_at": manifest.created_at.isoformat(),
                    "completed_at": manifest.completed_at.isoformat() if manifest.completed_at else None,
                    "status": manifest.status.value,
                    "owner_address": manifest.owner_address,
                    "node_id": manifest.node_id,
                    "chunk_count": manifest.chunk_count,
                    "total_size": manifest.total_size,
                    "merkle_root": manifest.merkle_root
                }
                
                if request.include_metadata:
                    session_data["metadata"] = manifest.metadata
                
                if request.include_chunks:
                    session_data["chunks"] = []
                    for chunk in manifest.chunks:
                        chunk_data = {
                            "chunk_id": chunk.chunk_id,
                            "index": chunk.index,
                            "size": chunk.size,
                            "hash": chunk.hash
                        }
                        
                        if request.include_proofs and chunk.merkle_proof:
                            chunk_data["merkle_proof"] = chunk.merkle_proof
                        
                        session_data["chunks"].append(chunk_data)
                
                export_data["sessions"].append(session_data)
            
            async with aiofiles.open(export_file, "w") as f:
                await f.write(json.dumps(export_data, indent=2, default=str))
            
            logger.info(f"Exported JSON data to: {export_file}")
            
        except Exception as e:
            logger.error(f"Error exporting JSON: {e}")
            raise
    
    async def _export_csv(self, manifests: List[SessionManifest], export_file: Path, request: ExportRequest):
        """Export data as CSV"""
        try:
            async with aiofiles.open(export_file, "w", newline="") as f:
                writer = csv.writer(f)
                
                # Write header
                header = [
                    "session_id", "created_at", "completed_at", "status",
                    "owner_address", "node_id", "chunk_count", "total_size", "merkle_root"
                ]
                
                if request.include_metadata:
                    header.extend(["compression", "encryption", "chunk_size"])
                
                writer.writerow(header)
                
                # Write data
                for manifest in manifests:
                    row = [
                        manifest.session_id,
                        manifest.created_at.isoformat(),
                        manifest.completed_at.isoformat() if manifest.completed_at else "",
                        manifest.status.value,
                        manifest.owner_address,
                        manifest.node_id,
                        manifest.chunk_count,
                        manifest.total_size,
                        manifest.merkle_root
                    ]
                    
                    if request.include_metadata:
                        row.extend([
                            manifest.metadata.get("compression", ""),
                            manifest.metadata.get("encryption", ""),
                            manifest.metadata.get("chunk_size", "")
                        ])
                    
                    writer.writerow(row)
            
            logger.info(f"Exported CSV data to: {export_file}")
            
        except Exception as e:
            logger.error(f"Error exporting CSV: {e}")
            raise
    
    async def _export_manifest(self, manifests: List[SessionManifest], export_file: Path, request: ExportRequest):
        """Export data as manifest format"""
        try:
            manifest_data = {
                "manifest_version": "1.0",
                "created_at": datetime.now().isoformat(),
                "session_count": len(manifests),
                "sessions": []
            }
            
            for manifest in manifests:
                session_manifest = {
                    "session_id": manifest.session_id,
                    "created_at": manifest.created_at.isoformat(),
                    "completed_at": manifest.completed_at.isoformat() if manifest.completed_at else None,
                    "status": manifest.status.value,
                    "owner_address": manifest.owner_address,
                    "node_id": manifest.node_id,
                    "chunk_count": manifest.chunk_count,
                    "total_size": manifest.total_size,
                    "merkle_root": manifest.merkle_root,
                    "chunks": []
                }
                
                for chunk in manifest.chunks:
                    chunk_manifest = {
                        "chunk_id": chunk.chunk_id,
                        "index": chunk.index,
                        "size": chunk.size,
                        "hash": chunk.hash
                    }
                    
                    if request.include_proofs and chunk.merkle_proof:
                        chunk_manifest["merkle_proof"] = chunk.merkle_proof
                    
                    session_manifest["chunks"].append(chunk_manifest)
                
                manifest_data["sessions"].append(session_manifest)
            
            async with aiofiles.open(export_file, "w") as f:
                await f.write(json.dumps(manifest_data, indent=2, default=str))
            
            logger.info(f"Exported manifest data to: {export_file}")
            
        except Exception as e:
            logger.error(f"Error exporting manifest: {e}")
            raise
    
    async def _export_proof(self, manifests: List[SessionManifest], export_file: Path, request: ExportRequest):
        """Export data as proof format"""
        try:
            proof_data = {
                "proof_version": "1.0",
                "created_at": datetime.now().isoformat(),
                "session_count": len(manifests),
                "proofs": []
            }
            
            for manifest in manifests:
                session_proof = {
                    "session_id": manifest.session_id,
                    "merkle_root": manifest.merkle_root,
                    "chunk_count": manifest.chunk_count,
                    "total_size": manifest.total_size,
                    "chunk_proofs": []
                }
                
                for chunk in manifest.chunks:
                    if chunk.merkle_proof:
                        chunk_proof = {
                            "chunk_id": chunk.chunk_id,
                            "index": chunk.index,
                            "hash": chunk.hash,
                            "merkle_proof": chunk.merkle_proof
                        }
                        session_proof["chunk_proofs"].append(chunk_proof)
                
                proof_data["proofs"].append(session_proof)
            
            async with aiofiles.open(export_file, "w") as f:
                await f.write(json.dumps(proof_data, indent=2, default=str))
            
            logger.info(f"Exported proof data to: {export_file}")
            
        except Exception as e:
            logger.error(f"Error exporting proof: {e}")
            raise
    
    async def _export_archive(self, manifests: List[SessionManifest], export_file: Path, request: ExportRequest):
        """Export data as archive format"""
        try:
            # Create temporary directory for archive contents
            temp_dir = self.temp_dir / f"{export_file.stem}_archive"
            temp_dir.mkdir(exist_ok=True)
            
            # Export manifest
            manifest_file = temp_dir / "manifest.json"
            await self._export_manifest(manifests, manifest_file, request)
            
            # Export individual session data if chunks are included
            if request.include_chunks:
                sessions_dir = temp_dir / "sessions"
                sessions_dir.mkdir(exist_ok=True)
                
                for manifest in manifests:
                    session_file = sessions_dir / f"{manifest.session_id}.json"
                    session_data = {
                        "session_id": manifest.session_id,
                        "chunks": [asdict(chunk) for chunk in manifest.chunks]
                    }
                    
                    async with aiofiles.open(session_file, "w") as f:
                        await f.write(json.dumps(session_data, indent=2, default=str))
            
            # Create ZIP archive
            with zipfile.ZipFile(export_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in temp_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(temp_dir)
                        zipf.write(file_path, arcname)
            
            # Clean up temporary directory
            import shutil
            shutil.rmtree(temp_dir)
            
            logger.info(f"Exported archive data to: {export_file}")
            
        except Exception as e:
            logger.error(f"Error exporting archive: {e}")
            raise
    
    async def _encrypt_export(self, export_file: Path, encryption_key: str):
        """Encrypt export file"""
        try:
            # Generate encryption key from password
            key = hashlib.sha256(encryption_key.encode()).digest()
            fernet = Fernet(base64.urlsafe_b64encode(key))
            
            # Read file content
            async with aiofiles.open(export_file, "rb") as f:
                content = await f.read()
            
            # Encrypt content
            encrypted_content = fernet.encrypt(content)
            
            # Write encrypted content
            async with aiofiles.open(export_file, "wb") as f:
                await f.write(encrypted_content)
            
            logger.info(f"Encrypted export file: {export_file}")
            
        except Exception as e:
            logger.error(f"Error encrypting export: {e}")
            raise
    
    async def _compress_export(self, export_file: Path):
        """Compress export file"""
        try:
            compressed_file = export_file.with_suffix(export_file.suffix + ".gz")
            
            import gzip
            async with aiofiles.open(export_file, "rb") as f_in:
                content = await f_in.read()
            
            compressed_content = gzip.compress(content)
            
            async with aiofiles.open(compressed_file, "wb") as f_out:
                await f_out.write(compressed_content)
            
            # Replace original file
            export_file.unlink()
            compressed_file.rename(export_file)
            
            logger.info(f"Compressed export file: {export_file}")
            
        except Exception as e:
            logger.error(f"Error compressing export: {e}")
            raise
    
    async def _finalize_export(self, export_id: str, export_file: Path):
        """Finalize export process"""
        try:
            # Verify file exists and has content
            if not export_file.exists() or export_file.stat().st_size == 0:
                raise ValueError("Export file is empty or missing")
            
            # Check file size limit
            file_size_mb = export_file.stat().st_size / (1024 * 1024)
            if file_size_mb > self.max_export_size_mb:
                raise ValueError(f"Export file too large: {file_size_mb:.2f}MB > {self.max_export_size_mb}MB")
            
            # Set appropriate permissions
            export_file.chmod(0o644)
            
            logger.info(f"Finalized export: {export_id} -> {export_file}")
            
        except Exception as e:
            logger.error(f"Error finalizing export: {e}")
            raise
    
    async def get_export_status(self, export_id: str) -> Optional[ExportStatusResponse]:
        """Get export status for a request"""
        return self.active_exports.get(export_id)
    
    async def get_all_export_status(self) -> List[ExportStatusResponse]:
        """Get all export statuses"""
        return list(self.active_exports.values())
    
    async def download_export(self, export_id: str) -> Optional[Path]:
        """Get export file path for download"""
        if export_id not in self.active_exports:
            return None
        
        status_response = self.active_exports[export_id]
        
        if status_response.status != ExportStatus.COMPLETED:
            return None
        
        if not status_response.file_path:
            return None
        
        export_file = Path(status_response.file_path)
        if not export_file.exists():
            return None
        
        return export_file
    
    async def _log_export_event(self, export_id: str, event_type: str, data: Dict[str, Any]):
        """Log export event"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "export_id": export_id,
                "event_type": event_type,
                "data": data
            }
            
            log_file = self.logs_dir / f"export_{datetime.now().strftime('%Y%m%d')}.log"
            async with aiofiles.open(log_file, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging export event: {e}")
    
    async def cleanup_completed_exports(self, max_age_hours: int = 24):
        """Clean up completed exports older than max_age_hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            to_remove = []
            for export_id, status_response in self.active_exports.items():
                if (status_response.status in [ExportStatus.COMPLETED, ExportStatus.FAILED, ExportStatus.CANCELLED] 
                    and status_response.updated_at < cutoff_time):
                    to_remove.append(export_id)
            
            for export_id in to_remove:
                # Remove export file
                status_response = self.active_exports[export_id]
                if status_response.file_path:
                    export_file = Path(status_response.file_path)
                    if export_file.exists():
                        export_file.unlink()
                
                # Remove from active exports
                del self.active_exports[export_id]
            
            if to_remove:
                await self._save_export_state()
                logger.info(f"Cleaned up {len(to_remove)} completed exports")
                
        except Exception as e:
            logger.error(f"Error cleaning up exports: {e}")

# Global export manager instance
export_manager = SessionExportManager()

# Convenience functions for external use
async def create_export_request(request: ExportRequest) -> str:
    """Create a new export request"""
    return await export_manager.create_export_request(request)

async def get_export_status(export_id: str) -> Optional[ExportStatusResponse]:
    """Get export status for a request"""
    return await export_manager.get_export_status(export_id)

async def get_all_export_status() -> List[ExportStatusResponse]:
    """Get all export statuses"""
    return await export_manager.get_all_export_status()

async def download_export(export_id: str) -> Optional[Path]:
    """Get export file path for download"""
    return await export_manager.download_export(export_id)

if __name__ == "__main__":
    # Example usage
    async def main():
        # Create an export request
        request = ExportRequest(
            session_ids=["session-001", "session-002"],
            export_format=ExportFormat.JSON,
            include_metadata=True,
            include_chunks=False,
            include_proofs=True
        )
        
        export_id = await create_export_request(request)
        print(f"Created export request: {export_id}")
        
        # Check status
        status = await get_export_status(export_id)
        print(f"Status: {status}")
    
    asyncio.run(main())
