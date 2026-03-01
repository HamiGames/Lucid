# LUCID Common Input Controller - Input/Clipboard/File Transfer Security Controls
# Implements comprehensive input validation, clipboard security, and file transfer controls
# LUCID-STRICT Layer 1 Common Security Integration

from __future__ import annotations

import asyncio
import logging
import secrets
import time
import hashlib
import mimetypes
import magic
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, Callable, Set, BinaryIO
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import uuid
import base64
import re
import tempfile
import os

from .trust_nothing_engine import (
    SecurityContext, SecurityAssessment, SecurityPolicy, 
    PolicyLevel, TrustLevel, RiskLevel, ActionType, VerificationMethod,
    TrustNothingEngine
)

logger = logging.getLogger(__name__)

# Input Control Configuration
INPUT_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
CLIPBOARD_MAX_SIZE_BYTES = 1024 * 1024    # 1MB
FILE_TRANSFER_MAX_SIZE_BYTES = 100 * 1024 * 1024  # 100MB
INPUT_VALIDATION_TIMEOUT_SECONDS = 30
SUSPICIOUS_PATTERN_THRESHOLD = 0.8
CONTENT_SCAN_DEPTH_LIMIT = 1000


class InputType(Enum):
    """Types of input data"""
    TEXT = "text"
    BINARY = "binary"
    FILE = "file"
    CLIPBOARD = "clipboard"
    URL = "url"
    JSON = "json"
    XML = "xml"
    HTML = "html"
    SQL = "sql"
    SCRIPT = "script"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    ARCHIVE = "archive"
    EXECUTABLE = "executable"


class InputRiskLevel(Enum):
    """Risk levels for input content"""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    MALICIOUS = "malicious"


class TransferDirection(Enum):
    """Direction of data transfer"""
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"
    EXTERNAL = "external"


class ContentScanResult(Enum):
    """Result of content scanning"""
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    ENCRYPTED = "encrypted"
    COMPRESSED = "compressed"
    CORRUPTED = "corrupted"
    UNKNOWN = "unknown"


@dataclass
class InputValidationRequest:
    """Request for input validation"""
    request_id: str
    input_type: InputType
    content: Union[str, bytes]
    source: str
    destination: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    transfer_direction: TransferDirection = TransferDirection.INBOUND
    metadata: Dict[str, Any] = field(default_factory=dict)
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class InputValidationResult:
    """Result of input validation"""
    validation_id: str
    request: InputValidationRequest
    is_safe: bool
    risk_level: InputRiskLevel
    content_type: str
    size_bytes: int
    scan_result: ContentScanResult
    threats_detected: List[str]
    sanitized_content: Optional[Union[str, bytes]] = None
    validation_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClipboardEvent:
    """Clipboard access event"""
    event_id: str
    user_id: str
    session_id: str
    action: str  # copy, paste, cut
    content_type: str
    content_size: int
    source_application: str
    destination_application: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_sanitized: bool = False
    risk_level: InputRiskLevel = InputRiskLevel.SAFE


@dataclass
class FileTransferEvent:
    """File transfer event"""
    event_id: str
    user_id: str
    session_id: str
    filename: str
    file_size: int
    file_type: str
    source_path: str
    destination_path: str
    transfer_direction: TransferDirection
    checksum: str
    scan_result: ContentScanResult
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_quarantined: bool = False


class InputController:
    """
    Input Security Controller
    
    Provides comprehensive input validation, clipboard security, and file transfer controls
    for the LUCID system with real-time threat detection and content sanitization.
    """
    
    def __init__(self, trust_engine: Optional[TrustNothingEngine] = None):
        self.trust_engine = trust_engine or TrustNothingEngine()
        self.validation_cache: Dict[str, InputValidationResult] = {}
        self.clipboard_events: List[ClipboardEvent] = []
        self.file_transfer_events: List[FileTransferEvent] = []
        self.quarantine_directory: Path = Path(tempfile.gettempdir()) / "lucid_quarantine"
        
        # Security patterns
        self.malicious_patterns: Dict[str, List[str]] = {
            "sql_injection": [
                r"('|(\\')|(;)|(--)|(/\*)|(\*/)|(\|)|(\+)|(\*)|(%)|(union)|(select)|(insert)|(update)|(delete)|(drop)|(create)|(alter)|(exec)|(execute)",
                r"(script)|(javascript)|(vbscript)|(onload)|(onerror)|(onclick)",
                r"(<script)|(</script)|(<iframe)|(</iframe)|(<object)|(</object)",
                r"(eval\()|(document\.)|(window\.)|(alert\()|(confirm\()"
            ],
            "xss_attack": [
                r"(<script[^>]*>.*?</script>)",
                r"(javascript:)",
                r"(on\w+\s*=)",
                r"(<iframe[^>]*>.*?</iframe>)",
                r"(<object[^>]*>.*?</object>)",
                r"(<embed[^>]*>)",
                r"(<link[^>]*>)",
                r"(<meta[^>]*>)"
            ],
            "command_injection": [
                r"(\||\&|\;|\$|\`|\$\(|\$\{|\<\>|\>\>|\<\<)",
                r"(cmd\.exe|command\.com|powershell|bash|sh|zsh)",
                r"(nc\s|netcat\s|telnet\s|ssh\s)",
                r"(wget|curl|fetch|download)",
                r"(rm\s|del\s|delete\s|format\s)"
            ],
            "path_traversal": [
                r"(\.\./)|(\.\.\\\\)|(\.\.%2f)|(\.\.%5c)",
                r"(/etc/passwd)|(/etc/shadow)|(/windows/system32)",
                r"(c:\\windows\\system32)|(c:/windows/system32)"
            ],
            "data_exfiltration": [
                r"(password|passwd|secret|token|key|credential)",
                r"(ssn|social security|credit card|account number)",
                r"(api_key|access_token|refresh_token)",
                r"(base64|hex|binary|encoded)"
            ]
        }
        
        # Allowed file extensions
        self.allowed_extensions: Set[str] = {
            '.txt', '.md', '.json', '.xml', '.csv', '.log',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg',
            '.mp3', '.wav', '.ogg', '.mp4', '.avi', '.mov',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.tar', '.gz', '.7z'
        }
        
        # Dangerous file extensions
        self.dangerous_extensions: Set[str] = {
            '.exe', '.bat', '.cmd', '.com', '.scr', '.pif',
            '.js', '.vbs', '.ps1', '.sh', '.py', '.php',
            '.jar', '.war', '.ear', '.deb', '.rpm', '.msi',
            '.dll', '.so', '.dylib', '.app', '.pkg', '.dmg'
        }
        
        # Clipboard monitoring
        self.clipboard_monitoring_enabled = True
        self.clipboard_max_events = 1000
        
        # Initialize quarantine directory
        self._initialize_quarantine_directory()
        
        logger.info("Input Controller initialized with security controls")
    
    async def validate_input(
        self,
        content: Union[str, bytes],
        input_type: InputType,
        source: str,
        destination: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        sanitize: bool = True
    ) -> InputValidationResult:
        """
        Validate input content for security threats
        
        Args:
            content: Input content to validate
            input_type: Type of input content
            source: Source of the input
            destination: Destination for the input
            user_id: User ID (if applicable)
            session_id: Session ID (if applicable)
            sanitize: Whether to sanitize the content
            
        Returns:
            InputValidationResult with validation status and recommendations
        """
        validation_id = str(uuid.uuid4())
        
        # Create validation request
        request = InputValidationRequest(
            request_id=validation_id,
            input_type=input_type,
            content=content,
            source=source,
            destination=destination,
            user_id=user_id,
            session_id=session_id
        )
        
        try:
            # Check cache for recent validations
            cache_key = self._generate_cache_key(content, input_type)
            if cache_key in self.validation_cache:
                cached_result = self.validation_cache[cache_key]
                if self._is_cache_valid(cached_result):
                    logger.info(f"Using cached validation for {validation_id}")
                    return cached_result
            
            # Perform content analysis
            content_type, size_bytes = await self._analyze_content(content, input_type)
            scan_result, threats_detected = await self._scan_content(content, input_type)
            
            # Determine risk level
            risk_level = self._calculate_risk_level(scan_result, threats_detected, size_bytes)
            
            # Check size limits
            if not await self._check_size_limits(content, input_type):
                threats_detected.append("Content size exceeds limits")
                risk_level = InputRiskLevel.HIGH
            
            # Perform deep content analysis
            if input_type in [InputType.TEXT, InputType.JSON, InputType.XML, InputType.HTML]:
                pattern_threats = await self._detect_malicious_patterns(content)
                threats_detected.extend(pattern_threats)
            
            # Check file type if applicable
            if input_type == InputType.FILE:
                file_threats = await self._analyze_file_type(content, source)
                threats_detected.extend(file_threats)
            
            # Sanitize content if requested and safe to do so
            sanitized_content = None
            if sanitize and risk_level not in [InputRiskLevel.CRITICAL, InputRiskLevel.MALICIOUS]:
                sanitized_content = await self._sanitize_content(content, input_type)
            
            # Create validation result
            result = InputValidationResult(
                validation_id=validation_id,
                request=request,
                is_safe=risk_level in [InputRiskLevel.SAFE, InputRiskLevel.LOW],
                risk_level=risk_level,
                content_type=content_type,
                size_bytes=size_bytes,
                scan_result=scan_result,
                threats_detected=threats_detected,
                sanitized_content=sanitized_content,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
            )
            
            # Generate recommendations
            result.recommendations = await self._generate_recommendations(
                risk_level, threats_detected, scan_result
            )
            
            # Cache the result
            self.validation_cache[cache_key] = result
            
            # Log validation event
            await self._log_input_validation(result)
            
            logger.info(f"Input validation completed: {validation_id}, risk: {risk_level.value}")
            return result
            
        except Exception as e:
            logger.error(f"Input validation failed for {validation_id}: {e}")
            return await self._create_unsafe_result(
                request, f"Validation error: {str(e)}", InputRiskLevel.CRITICAL
            )
    
    async def monitor_clipboard_access(
        self,
        user_id: str,
        session_id: str,
        action: str,
        content: Union[str, bytes],
        source_app: str,
        dest_app: str
    ) -> ClipboardEvent:
        """
        Monitor and validate clipboard access
        
        Args:
            user_id: User ID
            session_id: Session ID
            action: Clipboard action (copy, paste, cut)
            content: Clipboard content
            source_app: Source application
            dest_app: Destination application
            
        Returns:
            ClipboardEvent with validation results
        """
        event_id = str(uuid.uuid4())
        
        # Validate clipboard content
        validation_result = await self.validate_input(
            content=content,
            input_type=InputType.CLIPBOARD,
            source=source_app,
            destination=dest_app,
            user_id=user_id,
            session_id=session_id
        )
        
        # Create clipboard event
        event = ClipboardEvent(
            event_id=event_id,
            user_id=user_id,
            session_id=session_id,
            action=action,
            content_type=validation_result.content_type,
            content_size=validation_result.size_bytes,
            source_application=source_app,
            destination_application=dest_app,
            is_sanitized=validation_result.sanitized_content is not None,
            risk_level=validation_result.risk_level
        )
        
        # Store event
        self.clipboard_events.append(event)
        
        # Cleanup old events
        if len(self.clipboard_events) > self.clipboard_max_events:
            self.clipboard_events = self.clipboard_events[-self.clipboard_max_events:]
        
        # Log clipboard event
        await self._log_clipboard_event(event, validation_result)
        
        logger.info(f"Clipboard event monitored: {event_id}, action: {action}, risk: {validation_result.risk_level.value}")
        return event
    
    async def validate_file_transfer(
        self,
        filename: str,
        file_content: bytes,
        source_path: str,
        destination_path: str,
        transfer_direction: TransferDirection,
        user_id: str,
        session_id: str
    ) -> Tuple[bool, FileTransferEvent]:
        """
        Validate file transfer for security
        
        Args:
            filename: Name of the file
            file_content: File content
            source_path: Source file path
            destination_path: Destination file path
            transfer_direction: Direction of transfer
            user_id: User ID
            session_id: Session ID
            
        Returns:
            Tuple of (is_safe, FileTransferEvent)
        """
        event_id = str(uuid.uuid4())
        
        # Validate file content
        validation_result = await self.validate_input(
            content=file_content,
            input_type=InputType.FILE,
            source=source_path,
            destination=destination_path,
            user_id=user_id,
            session_id=session_id
        )
        
        # Calculate file checksum
        checksum = hashlib.sha256(file_content).hexdigest()
        
        # Determine if file should be quarantined
        is_quarantined = validation_result.risk_level in [
            InputRiskLevel.HIGH, InputRiskLevel.CRITICAL, InputRiskLevel.MALICIOUS
        ]
        
        # Create file transfer event
        event = FileTransferEvent(
            event_id=event_id,
            user_id=user_id,
            session_id=session_id,
            filename=filename,
            file_size=validation_result.size_bytes,
            file_type=validation_result.content_type,
            source_path=source_path,
            destination_path=destination_path,
            transfer_direction=transfer_direction,
            checksum=checksum,
            scan_result=validation_result.scan_result,
            is_quarantined=is_quarantined
        )
        
        # Store event
        self.file_transfer_events.append(event)
        
        # Quarantine file if necessary
        if is_quarantined:
            await self._quarantine_file(filename, file_content, event_id)
        
        # Log file transfer event
        await self._log_file_transfer_event(event, validation_result)
        
        is_safe = validation_result.is_safe and not is_quarantined
        logger.info(f"File transfer validated: {event_id}, safe: {is_safe}, quarantined: {is_quarantined}")
        
        return is_safe, event
    
    async def get_clipboard_history(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[ClipboardEvent]:
        """Get clipboard access history for a user"""
        user_events = [
            event for event in self.clipboard_events
            if event.user_id == user_id
        ]
        
        return sorted(user_events, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    async def get_file_transfer_history(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[FileTransferEvent]:
        """Get file transfer history for a user"""
        user_events = [
            event for event in self.file_transfer_events
            if event.user_id == user_id
        ]
        
        return sorted(user_events, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    async def cleanup_expired_validations(self) -> int:
        """Clean up expired validation cache entries"""
        current_time = datetime.now(timezone.utc)
        expired_keys = []
        
        for cache_key, result in self.validation_cache.items():
            if result.expires_at and current_time > result.expires_at:
                expired_keys.append(cache_key)
        
        for cache_key in expired_keys:
            del self.validation_cache[cache_key]
        
        logger.info(f"Cleaned up {len(expired_keys)} expired validations")
        return len(expired_keys)
    
    async def _analyze_content(
        self,
        content: Union[str, bytes],
        input_type: InputType
    ) -> Tuple[str, int]:
        """Analyze content type and size"""
        size_bytes = len(content)
        
        if input_type == InputType.FILE:
            content_type = await self._detect_file_type(content)
        elif isinstance(content, str):
            content_type = "text/plain"
        else:
            content_type = "application/octet-stream"
        
        return content_type, size_bytes
    
    async def _detect_file_type(self, content: bytes) -> str:
        """Detect file type using magic bytes"""
        try:
            # Use python-magic if available
            if hasattr(magic, 'from_buffer'):
                return magic.from_buffer(content, mime=True)
            
            # Fallback to file extension detection
            return mimetypes.guess_type("file")[0] or "application/octet-stream"
        except Exception:
            return "application/octet-stream"
    
    async def _scan_content(
        self,
        content: Union[str, bytes],
        input_type: InputType
    ) -> Tuple[ContentScanResult, List[str]]:
        """Scan content for threats and anomalies"""
        threats_detected = []
        scan_result = ContentScanResult.CLEAN
        
        # Check for encryption
        if self._is_encrypted(content):
            scan_result = ContentScanResult.ENCRYPTED
            threats_detected.append("Encrypted content detected")
        
        # Check for compression
        if self._is_compressed(content):
            scan_result = ContentScanResult.COMPRESSED
            threats_detected.append("Compressed content detected")
        
        # Check for suspicious patterns
        if isinstance(content, str):
            suspicious_patterns = await self._detect_suspicious_patterns(content)
            if suspicious_patterns:
                scan_result = ContentScanResult.SUSPICIOUS
                threats_detected.extend(suspicious_patterns)
        
        # Check for malicious content
        if threats_detected and len(threats_detected) > 3:
            scan_result = ContentScanResult.MALICIOUS
        
        return scan_result, threats_detected
    
    def _is_encrypted(self, content: Union[str, bytes]) -> bool:
        """Check if content appears to be encrypted"""
        if isinstance(content, str):
            content_bytes = content.encode()
        else:
            content_bytes = content
        
        # Check entropy (simplified)
        if len(content_bytes) > 100:
            unique_bytes = len(set(content_bytes))
            entropy_ratio = unique_bytes / len(content_bytes)
            return entropy_ratio > 0.8
        
        return False
    
    def _is_compressed(self, content: Union[str, bytes]) -> bool:
        """Check if content appears to be compressed"""
        if isinstance(content, str):
            content_bytes = content.encode()
        else:
            content_bytes = content
        
        # Check for common compression signatures
        compression_signatures = [
            b'\x50\x4b\x03\x04',  # ZIP
            b'\x50\x4b\x05\x06',  # ZIP (empty)
            b'\x50\x4b\x07\x08',  # ZIP (spanned)
            b'\x1f\x8b\x08',      # GZIP
            b'BZh',               # BZIP2
            b'\xfd7zXZ',          # XZ
            b'PK\x03\x04',        # ZIP (alternative)
        ]
        
        for signature in compression_signatures:
            if content_bytes.startswith(signature):
                return True
        
        return False
    
    async def _detect_malicious_patterns(self, content: str) -> List[str]:
        """Detect malicious patterns in text content"""
        threats = []
        
        for threat_type, patterns in self.malicious_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                    threats.append(f"{threat_type} pattern detected")
        
        return threats
    
    async def _detect_suspicious_patterns(self, content: str) -> List[str]:
        """Detect suspicious patterns that may indicate malicious intent"""
        suspicious_patterns = []
        
        # Check for base64 encoded content
        if re.search(r'^[A-Za-z0-9+/]{20,}={0,2}$', content.strip()):
            suspicious_patterns.append("Base64 encoded content")
        
        # Check for hex encoded content
        if re.search(r'^[0-9a-fA-F]{20,}$', content.strip()):
            suspicious_patterns.append("Hex encoded content")
        
        # Check for suspicious URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, content)
        for url in urls:
            if any(domain in url.lower() for domain in ['bit.ly', 'tinyurl', 'goo.gl', 't.co']):
                suspicious_patterns.append("Suspicious URL detected")
        
        return suspicious_patterns
    
    async def _analyze_file_type(self, content: bytes, source: str) -> List[str]:
        """Analyze file type for security risks"""
        threats = []
        
        # Check file extension
        file_path = Path(source)
        extension = file_path.suffix.lower()
        
        if extension in self.dangerous_extensions:
            threats.append(f"Dangerous file extension: {extension}")
        
        # Check magic bytes
        if content.startswith(b'MZ'):  # Windows executable
            threats.append("Windows executable detected")
        elif content.startswith(b'\x7fELF'):  # Linux executable
            threats.append("Linux executable detected")
        elif content.startswith(b'\xfe\xed\xfa'):  # macOS executable
            threats.append("macOS executable detected")
        
        return threats
    
    def _calculate_risk_level(
        self,
        scan_result: ContentScanResult,
        threats_detected: List[str],
        size_bytes: int
    ) -> InputRiskLevel:
        """Calculate overall risk level for input content"""
        
        if scan_result == ContentScanResult.MALICIOUS:
            return InputRiskLevel.MALICIOUS
        
        if scan_result == ContentScanResult.SUSPICIOUS:
            return InputRiskLevel.HIGH
        
        if len(threats_detected) > 3:
            return InputRiskLevel.HIGH
        elif len(threats_detected) > 1:
            return InputRiskLevel.MEDIUM
        elif len(threats_detected) > 0:
            return InputRiskLevel.LOW
        
        # Check size-based risks
        if size_bytes > FILE_TRANSFER_MAX_SIZE_BYTES:
            return InputRiskLevel.MEDIUM
        
        return InputRiskLevel.SAFE
    
    async def _check_size_limits(
        self,
        content: Union[str, bytes],
        input_type: InputType
    ) -> bool:
        """Check if content size is within limits"""
        size_bytes = len(content)
        
        if input_type == InputType.CLIPBOARD:
            return size_bytes <= CLIPBOARD_MAX_SIZE_BYTES
        elif input_type == InputType.FILE:
            return size_bytes <= FILE_TRANSFER_MAX_SIZE_BYTES
        else:
            return size_bytes <= INPUT_MAX_SIZE_BYTES
    
    async def _sanitize_content(
        self,
        content: Union[str, bytes],
        input_type: InputType
    ) -> Optional[Union[str, bytes]]:
        """Sanitize content to remove potential threats"""
        if isinstance(content, str):
            # Remove HTML tags
            sanitized = re.sub(r'<[^>]+>', '', content)
            
            # Remove script tags completely
            sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.DOTALL | re.IGNORECASE)
            
            # Remove javascript: protocols
            sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
            
            # Remove null bytes
            sanitized = sanitized.replace('\x00', '')
            
            return sanitized
        else:
            # For binary content, we can't safely sanitize
            return None
    
    async def _generate_recommendations(
        self,
        risk_level: InputRiskLevel,
        threats_detected: List[str],
        scan_result: ContentScanResult
    ) -> List[str]:
        """Generate security recommendations based on analysis"""
        recommendations = []
        
        if risk_level == InputRiskLevel.MALICIOUS:
            recommendations.append("Content appears malicious - block access immediately")
        elif risk_level == InputRiskLevel.CRITICAL:
            recommendations.append("High-risk content detected - review before allowing access")
        elif risk_level == InputRiskLevel.HIGH:
            recommendations.append("Suspicious content detected - additional verification recommended")
        
        if scan_result == ContentScanResult.ENCRYPTED:
            recommendations.append("Encrypted content detected - verify source and purpose")
        
        if scan_result == ContentScanResult.COMPRESSED:
            recommendations.append("Compressed content detected - scan after extraction")
        
        if "sql_injection" in str(threats_detected):
            recommendations.append("SQL injection patterns detected - validate input parameters")
        
        if "xss_attack" in str(threats_detected):
            recommendations.append("XSS attack patterns detected - sanitize output")
        
        return recommendations
    
    async def _quarantine_file(
        self,
        filename: str,
        file_content: bytes,
        event_id: str
    ) -> None:
        """Quarantine a suspicious file"""
        quarantine_path = self.quarantine_directory / f"{event_id}_{filename}"
        
        try:
            with open(quarantine_path, 'wb') as f:
                f.write(file_content)
            
            logger.warning(f"File quarantined: {quarantine_path}")
        except Exception as e:
            logger.error(f"Failed to quarantine file {filename}: {e}")
    
    def _initialize_quarantine_directory(self) -> None:
        """Initialize quarantine directory"""
        self.quarantine_directory.mkdir(parents=True, exist_ok=True)
        
        # Set restrictive permissions
        try:
            os.chmod(self.quarantine_directory, 0o700)
        except Exception as e:
            logger.warning(f"Could not set quarantine directory permissions: {e}")
    
    def _generate_cache_key(self, content: Union[str, bytes], input_type: InputType) -> str:
        """Generate cache key for validation results"""
        if isinstance(content, str):
            content_hash = hashlib.sha256(content.encode()).hexdigest()
        else:
            content_hash = hashlib.sha256(content).hexdigest()
        
        return f"{input_type.value}:{content_hash}"
    
    def _is_cache_valid(self, result: InputValidationResult) -> bool:
        """Check if cached result is still valid"""
        if not result.expires_at:
            return False
        
        return datetime.now(timezone.utc) < result.expires_at
    
    async def _create_unsafe_result(
        self,
        request: InputValidationRequest,
        reason: str,
        risk_level: InputRiskLevel
    ) -> InputValidationResult:
        """Create an unsafe validation result"""
        return InputValidationResult(
            validation_id=request.request_id,
            request=request,
            is_safe=False,
            risk_level=risk_level,
            content_type="unknown",
            size_bytes=len(request.content),
            scan_result=ContentScanResult.MALICIOUS,
            threats_detected=[reason],
            recommendations=[f"Content blocked: {reason}"]
        )
    
    async def _log_input_validation(self, result: InputValidationResult) -> None:
        """Log input validation event for audit trail"""
        event_data = {
            "validation_id": result.validation_id,
            "input_type": result.request.input_type.value,
            "source": result.request.source,
            "destination": result.request.destination,
            "risk_level": result.risk_level.value,
            "content_type": result.content_type,
            "size_bytes": result.size_bytes,
            "scan_result": result.scan_result.value,
            "threats_count": len(result.threats_detected),
            "is_safe": result.is_safe,
            "timestamp": result.request.requested_at.isoformat()
        }
        
        logger.info(f"Input validation event: {json.dumps(event_data)}")
    
    async def _log_clipboard_event(
        self,
        event: ClipboardEvent,
        validation_result: InputValidationResult
    ) -> None:
        """Log clipboard event for audit trail"""
        event_data = {
            "event_id": event.event_id,
            "user_id": event.user_id,
            "action": event.action,
            "content_type": event.content_type,
            "content_size": event.content_size,
            "source_app": event.source_application,
            "dest_app": event.destination_application,
            "risk_level": event.risk_level.value,
            "is_sanitized": event.is_sanitized,
            "timestamp": event.timestamp.isoformat()
        }
        
        logger.info(f"Clipboard event: {json.dumps(event_data)}")
    
    async def _log_file_transfer_event(
        self,
        event: FileTransferEvent,
        validation_result: InputValidationResult
    ) -> None:
        """Log file transfer event for audit trail"""
        event_data = {
            "event_id": event.event_id,
            "user_id": event.user_id,
            "filename": event.filename,
            "file_size": event.file_size,
            "file_type": event.file_type,
            "source_path": event.source_path,
            "destination_path": event.destination_path,
            "transfer_direction": event.transfer_direction.value,
            "checksum": event.checksum,
            "scan_result": event.scan_result.value,
            "is_quarantined": event.is_quarantined,
            "timestamp": event.timestamp.isoformat()
        }
        
        logger.info(f"File transfer event: {json.dumps(event_data)}")


# Global input controller instance
_input_controller: Optional[InputController] = None


def get_input_controller() -> Optional[InputController]:
    """Get global input controller instance"""
    return _input_controller


def create_input_controller(trust_engine: Optional[TrustNothingEngine] = None) -> InputController:
    """Create new input controller instance"""
    global _input_controller
    _input_controller = InputController(trust_engine)
    return _input_controller


async def main():
    """Main function for testing"""
    # Initialize input controller
    controller = create_input_controller()
    
    # Test input validation
    test_content = "Hello, this is a test message with <script>alert('xss')</script>"
    result = await controller.validate_input(
        content=test_content,
        input_type=InputType.TEXT,
        source="test_app",
        destination="lucid_system"
    )
    
    print(f"Input validation result: {result.is_safe}")
    print(f"Risk level: {result.risk_level.value}")
    print(f"Threats detected: {result.threats_detected}")
    print(f"Recommendations: {result.recommendations}")


if __name__ == "__main__":
    asyncio.run(main())
