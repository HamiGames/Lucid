"""
Configuration Module for Session Recorder
Manages configuration settings for the session recording service.

This module provides configuration management for the session recorder service,
including recording settings, hardware acceleration, FFmpeg configuration, and more.
Configuration is loaded from YAML file with environment variable overrides.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)


class RecordingVideoConfig(BaseSettings):
    """Video recording configuration"""
    enabled: bool = True
    codec: str = "h264_v4l2m2m"
    frame_rate: int = 30
    resolution: str = "1920x1080"
    bitrate: str = "2000k"
    quality: str = "high"
    hardware_acceleration: bool = True
    acceleration_method: str = "v4l2m2m"
    
    @field_validator('codec')
    @classmethod
    def validate_codec(cls, v):
        valid_codecs = ["h264_v4l2m2m", "libx264", "h264_nvenc"]
        if v not in valid_codecs:
            logger.warning(f"Unknown codec {v}, using default")
            return "h264_v4l2m2m"
        return v


class RecordingAudioConfig(BaseSettings):
    """Audio recording configuration"""
    enabled: bool = True
    codec: str = "opus"
    sample_rate: int = 48000
    channels: int = 2
    bitrate: str = "128k"


class RecordingDisplayConfig(BaseSettings):
    """Display capture configuration"""
    xrdp_display: str = ":10"
    capture_method: str = "x11grab"
    capture_area: str = "fullscreen"
    cursor_capture: bool = True
    cursor_size: int = 32


class ChunkGenerationConfig(BaseSettings):
    """Chunk generation configuration"""
    enabled: bool = True
    chunk_size_mb: int = 10
    chunk_duration_seconds: int = 300
    compression_level: int = 6
    compression_algorithm: str = "gzip"
    generate_metadata: bool = True
    include_timestamps: bool = True


class HardwareAccelerationConfig(BaseSettings):
    """Hardware acceleration configuration"""
    enabled: bool = True
    device: str = "/dev/video10"
    encoder: str = "h264_v4l2m2m"
    decoder: str = "h264_v4l2m2m"
    fallback_to_software: bool = True
    validate_hardware: bool = True


class FFmpegConfig(BaseSettings):
    """FFmpeg configuration"""
    path: str = "/usr/bin/ffmpeg"
    log_level: str = "warning"
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: int = 5


class SessionManagementConfig(BaseSettings):
    """Session management configuration"""
    max_concurrent_recordings: int = 10
    session_timeout_seconds: int = 7200
    auto_stop_on_idle: bool = False
    idle_timeout_seconds: int = 300
    cleanup_interval_seconds: int = 3600


class StorageConfig(BaseSettings):
    """Storage configuration"""
    recordings_path: str = "/app/recordings"
    chunks_path: str = "/app/chunks"
    max_storage_size_gb: int = 500
    retention_days: int = 30
    auto_cleanup: bool = True
    compression_enabled: bool = True
    encryption_enabled: bool = False


class QualityControlConfig(BaseSettings):
    """Quality control configuration"""
    enabled: bool = True
    min_quality_score: float = 0.7
    validate_chunks: bool = True
    validate_audio_sync: bool = True
    validate_video_integrity: bool = True
    auto_adjust_quality: bool = False


class MonitoringConfig(BaseSettings):
    """Monitoring configuration"""
    enabled: bool = True
    health_check_enabled: bool = True
    health_check_interval_seconds: int = 30
    health_check_timeout_seconds: int = 10


class ErrorHandlingConfig(BaseSettings):
    """Error handling configuration"""
    retry_enabled: bool = True
    max_retries: int = 3
    retry_delay_seconds: int = 5
    exponential_backoff: bool = True
    recovery_enabled: bool = True
    auto_recovery: bool = True
    recovery_timeout_seconds: int = 60
    preserve_partial_recordings: bool = True


class SecurityConfig(BaseSettings):
    """Security configuration"""
    require_authentication: bool = True
    require_authorization: bool = True
    allowed_roles: List[str] = ["USER", "NODE_OPERATOR", "ADMIN", "SUPER_ADMIN"]
    encrypt_recordings: bool = False
    mask_sensitive_data: bool = False
    audit_log_enabled: bool = True
    audit_log_retention_days: int = 90


class RecorderSettings(BaseSettings):
    """Main configuration class for session recorder service"""
    
    # Service Configuration
    service_name: str = "lucid-session-recorder"
    service_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # Network Configuration (from environment)
    host: str = "0.0.0.0"
    port: int = 8090
    
    # Recording Configuration
    recording_path: str = "/app/recordings"
    chunk_output_path: str = "/app/chunks"
    
    # Video Configuration
    video_enabled: bool = True
    video_codec: str = "h264_v4l2m2m"
    video_frame_rate: int = 30
    video_resolution: str = "1920x1080"
    video_bitrate: str = "2000k"
    video_quality: str = "high"
    video_hardware_acceleration: bool = True
    video_acceleration_method: str = "v4l2m2m"
    
    # Audio Configuration
    audio_enabled: bool = True
    audio_codec: str = "opus"
    audio_sample_rate: int = 48000
    audio_channels: int = 2
    audio_bitrate: str = "128k"
    
    # Display Configuration
    xrdp_display: str = ":10"
    capture_method: str = "x11grab"
    capture_area: str = "fullscreen"
    cursor_capture: bool = True
    cursor_size: int = 32
    
    # Chunk Generation
    chunk_generation_enabled: bool = True
    chunk_size_mb: int = 10
    chunk_duration_seconds: int = 300
    compression_level: int = 6
    compression_algorithm: str = "gzip"
    generate_metadata: bool = True
    include_timestamps: bool = True
    
    # Hardware Acceleration
    hardware_acceleration_enabled: bool = True
    hardware_device: str = "/dev/video10"
    hardware_encoder: str = "h264_v4l2m2m"
    hardware_decoder: str = "h264_v4l2m2m"
    hardware_fallback_to_software: bool = True
    hardware_validate: bool = True
    
    # FFmpeg Configuration
    ffmpeg_path: str = "/usr/bin/ffmpeg"
    ffmpeg_log_level: str = "warning"
    ffmpeg_timeout_seconds: int = 30
    ffmpeg_max_retries: int = 3
    ffmpeg_retry_delay_seconds: int = 5
    
    # Session Management
    max_concurrent_recordings: int = 10
    session_timeout_seconds: int = 7200
    auto_stop_on_idle: bool = False
    idle_timeout_seconds: int = 300
    cleanup_interval_seconds: int = 3600
    
    # Storage
    storage_recordings_path: str = "/app/recordings"
    storage_chunks_path: str = "/app/chunks"
    max_storage_size_gb: int = 500
    retention_days: int = 30
    auto_cleanup: bool = True
    storage_compression_enabled: bool = True
    storage_encryption_enabled: bool = False
    
    # Quality Control
    quality_control_enabled: bool = True
    min_quality_score: float = 0.7
    validate_chunks: bool = True
    validate_audio_sync: bool = True
    validate_video_integrity: bool = True
    auto_adjust_quality: bool = False
    
    # Monitoring
    monitoring_enabled: bool = True
    health_check_enabled: bool = True
    health_check_interval_seconds: int = 30
    health_check_timeout_seconds: int = 10
    
    # Error Handling
    retry_enabled: bool = True
    max_retries: int = 3
    retry_delay_seconds: int = 5
    exponential_backoff: bool = True
    recovery_enabled: bool = True
    auto_recovery: bool = True
    recovery_timeout_seconds: int = 60
    preserve_partial_recordings: bool = True
    
    # Security
    require_authentication: bool = True
    require_authorization: bool = True
    allowed_roles: List[str] = ["USER", "NODE_OPERATOR", "ADMIN", "SUPER_ADMIN"]
    encrypt_recordings: bool = False
    mask_sensitive_data: bool = False
    audit_log_enabled: bool = True
    audit_log_retention_days: int = 90
    
    model_config = {
        "env_file": None,
        "case_sensitive": True,
        "env_file_encoding": "utf-8"
    }
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            return "INFO"
        return v.upper()
    
    @field_validator('compression_algorithm')
    @classmethod
    def validate_compression_algorithm(cls, v):
        valid_algorithms = ["gzip", "zstd", "lz4"]
        if v.lower() not in valid_algorithms:
            return "gzip"
        return v.lower()


class RecorderConfig:
    """Configuration manager for session recorder"""
    
    def __init__(self, settings: Optional[RecorderSettings] = None):
        """Initialize configuration"""
        try:
            self.settings = settings or RecorderSettings()
            self._apply_environment_overrides()
        except Exception as e:
            logger.error(f"Failed to initialize recorder configuration: {e}")
            raise
    
    def _apply_environment_overrides(self):
        """Apply environment variable overrides"""
        # Override from environment variables (highest priority)
        if os.getenv("LUCID_RECORDING_PATH"):
            self.settings.recording_path = os.getenv("LUCID_RECORDING_PATH")
        if os.getenv("LUCID_CHUNK_OUTPUT_PATH"):
            self.settings.chunk_output_path = os.getenv("LUCID_CHUNK_OUTPUT_PATH")
        if os.getenv("LUCID_FFMPEG_PATH"):
            self.settings.ffmpeg_path = os.getenv("LUCID_FFMPEG_PATH")
        if os.getenv("LUCID_XRDP_DISPLAY"):
            self.settings.xrdp_display = os.getenv("LUCID_XRDP_DISPLAY")
        if os.getenv("LUCID_HARDWARE_ACCELERATION"):
            self.settings.video_hardware_acceleration = os.getenv("LUCID_HARDWARE_ACCELERATION").lower() == "true"
        if os.getenv("LUCID_VIDEO_CODEC"):
            self.settings.video_codec = os.getenv("LUCID_VIDEO_CODEC")
        if os.getenv("LUCID_AUDIO_CODEC"):
            self.settings.audio_codec = os.getenv("LUCID_AUDIO_CODEC")
        if os.getenv("LUCID_BITRATE"):
            self.settings.video_bitrate = os.getenv("LUCID_BITRATE")
        if os.getenv("LUCID_FPS"):
            try:
                self.settings.video_frame_rate = int(os.getenv("LUCID_FPS"))
            except (ValueError, TypeError):
                pass
        if os.getenv("LUCID_RESOLUTION"):
            self.settings.video_resolution = os.getenv("LUCID_RESOLUTION")
        if os.getenv("LUCID_CHUNK_SIZE_MB"):
            try:
                self.settings.chunk_size_mb = int(os.getenv("LUCID_CHUNK_SIZE_MB"))
            except (ValueError, TypeError):
                pass
        if os.getenv("LUCID_COMPRESSION_LEVEL"):
            try:
                self.settings.compression_level = int(os.getenv("LUCID_COMPRESSION_LEVEL"))
            except (ValueError, TypeError):
                pass
        if os.getenv("SESSION_RECORDER_PORT"):
            try:
                self.settings.port = int(os.getenv("SESSION_RECORDER_PORT"))
            except (ValueError, TypeError):
                pass
    
    def get_settings(self) -> RecorderSettings:
        """Get settings object"""
        return self.settings


def load_config(config_file: Optional[str] = None) -> RecorderConfig:
    """
    Load configuration from YAML file and environment variables.
    
    Configuration loading priority (highest to lowest):
    1. Environment variables (highest priority - override everything)
    2. YAML configuration file values
    3. Pydantic field defaults (lowest priority)
    
    Args:
        config_file: Optional path to YAML configuration file. If not provided,
                     will look for 'recorder-config.yaml' in sessions/config directory.
        
    Returns:
        Loaded configuration object with environment variables overriding YAML values
        
    Raises:
        FileNotFoundError: If config_file is provided but doesn't exist
        ValueError: If configuration validation fails
        ImportError: If PyYAML is not available (should not happen if requirements are installed)
    """
    try:
        yaml_data: Dict[str, Any] = {}
        yaml_file_path: Optional[Path] = None
        
        # Determine YAML file path
        if config_file:
            yaml_file_path = Path(config_file)
        else:
            # Try default locations
            default_locations = [
                Path(__file__).parent.parent.parent / "config" / "recorder-config.yaml",
                Path(__file__).parent / "recorder-config.yaml",
            ]
            for loc in default_locations:
                if loc.exists():
                    yaml_file_path = loc
                    break
        
        # Load YAML file if it exists
        if yaml_file_path and yaml_file_path.exists():
            if not YAML_AVAILABLE:
                logger.warning(f"PyYAML not available, skipping YAML file {yaml_file_path}")
            else:
                try:
                    with open(yaml_file_path, 'r', encoding='utf-8') as f:
                        yaml_data = yaml.safe_load(f) or {}
                    logger.info(f"Loaded YAML configuration from {yaml_file_path}")
                    
                    # Flatten nested YAML structure for Pydantic
                    flattened = _flatten_yaml_config(yaml_data)
                    
                    # Filter out empty string values from YAML (they should come from env vars)
                    flattened = {k: v for k, v in flattened.items() if v != "" or k in ["mongodb_url", "redis_url"]}
                    
                    yaml_data = flattened
                    
                except Exception as e:
                    logger.warning(f"Failed to load YAML configuration from {yaml_file_path}: {str(e)}")
                    logger.warning("Continuing with environment variables and defaults only")
                    yaml_data = {}
        elif config_file:
            # User specified a file but it doesn't exist - this is an error
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        else:
            logger.debug("No YAML configuration file found, using environment variables and defaults only")
        
        # Create settings with YAML data as defaults, then environment variables override
        if yaml_data:
            # Load from YAML data, then environment variables will override
            settings = RecorderSettings(**yaml_data)
        else:
            # Load from environment variables and defaults only
            settings = RecorderSettings()
        
        # Create config object
        config = RecorderConfig(settings)
        
        logger.info(f"Configuration loaded: service={config.settings.service_name}, version={config.settings.service_version}")
        
        return config
        
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        raise


def _flatten_yaml_config(yaml_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten nested YAML configuration structure for Pydantic.
    
    Maps nested YAML structure to flat Pydantic field names:
        recording:
            video:
                codec: "h264"
    To:
        video_codec: "h264"
    """
    flattened = {}
    
    # Handle global section
    if "global" in yaml_data:
        global_data = yaml_data["global"]
        flattened.update({
            "service_name": global_data.get("service_name", "lucid-session-recorder"),
            "service_version": global_data.get("service_version", "1.0.0"),
            "debug": global_data.get("debug", False),
            "log_level": global_data.get("log_level", "INFO"),
            "recording_path": global_data.get("recording_path", "/app/recordings"),
            "chunk_output_path": global_data.get("chunk_output_path", "/app/chunks"),
        })
    
    # Handle recording section
    if "recording" in yaml_data:
        rec = yaml_data["recording"]
        
        # Video config
        if "video" in rec:
            vid = rec["video"]
            flattened.update({
                "video_enabled": vid.get("enabled", True),
                "video_codec": vid.get("codec", "h264_v4l2m2m"),
                "video_frame_rate": vid.get("frame_rate", 30),
                "video_resolution": vid.get("resolution", "1920x1080"),
                "video_bitrate": vid.get("bitrate", "2000k"),
                "video_quality": vid.get("quality", "high"),
                "video_hardware_acceleration": vid.get("hardware_acceleration", True),
                "video_acceleration_method": vid.get("acceleration_method", "v4l2m2m"),
            })
        
        # Audio config
        if "audio" in rec:
            aud = rec["audio"]
            flattened.update({
                "audio_enabled": aud.get("enabled", True),
                "audio_codec": aud.get("codec", "opus"),
                "audio_sample_rate": aud.get("sample_rate", 48000),
                "audio_channels": aud.get("channels", 2),
                "audio_bitrate": aud.get("bitrate", "128k"),
            })
        
        # Display config
        if "display" in rec:
            disp = rec["display"]
            flattened.update({
                "xrdp_display": disp.get("xrdp_display", ":10"),
                "capture_method": disp.get("capture_method", "x11grab"),
                "capture_area": disp.get("capture_area", "fullscreen"),
                "cursor_capture": disp.get("cursor_capture", True),
                "cursor_size": disp.get("cursor_size", 32),
            })
        
        # Chunk generation config
        if "chunk_generation" in rec:
            chunk = rec["chunk_generation"]
            flattened.update({
                "chunk_generation_enabled": chunk.get("enabled", True),
                "chunk_size_mb": chunk.get("chunk_size_mb", 10),
                "chunk_duration_seconds": chunk.get("chunk_duration_seconds", 300),
                "compression_level": chunk.get("compression_level", 6),
                "compression_algorithm": chunk.get("compression_algorithm", "gzip"),
                "generate_metadata": chunk.get("generate_metadata", True),
                "include_timestamps": chunk.get("include_timestamps", True),
            })
    
    # Handle hardware_acceleration section
    if "hardware_acceleration" in yaml_data:
        hw = yaml_data["hardware_acceleration"]
        flattened.update({
            "hardware_acceleration_enabled": hw.get("enabled", True),
            "hardware_device": hw.get("device", "/dev/video10"),
            "hardware_encoder": hw.get("encoder", "h264_v4l2m2m"),
            "hardware_decoder": hw.get("decoder", "h264_v4l2m2m"),
            "hardware_fallback_to_software": hw.get("fallback_to_software", True),
            "hardware_validate": hw.get("validate_hardware", True),
        })
    
    # Handle ffmpeg section
    if "ffmpeg" in yaml_data:
        ff = yaml_data["ffmpeg"]
        flattened.update({
            "ffmpeg_path": ff.get("path", "/usr/bin/ffmpeg"),
            "ffmpeg_log_level": ff.get("log_level", "warning"),
            "ffmpeg_timeout_seconds": ff.get("timeout_seconds", 30),
            "ffmpeg_max_retries": ff.get("max_retries", 3),
            "ffmpeg_retry_delay_seconds": ff.get("retry_delay_seconds", 5),
        })
    
    # Handle session_management section
    if "session_management" in yaml_data:
        sm = yaml_data["session_management"]
        flattened.update({
            "max_concurrent_recordings": sm.get("max_concurrent_recordings", 10),
            "session_timeout_seconds": sm.get("session_timeout_seconds", 7200),
            "auto_stop_on_idle": sm.get("auto_stop_on_idle", False),
            "idle_timeout_seconds": sm.get("idle_timeout_seconds", 300),
            "cleanup_interval_seconds": sm.get("cleanup_interval_seconds", 3600),
        })
    
    # Handle storage section
    if "storage" in yaml_data:
        st = yaml_data["storage"]
        flattened.update({
            "storage_recordings_path": st.get("recordings_path", "/app/recordings"),
            "storage_chunks_path": st.get("chunks_path", "/app/chunks"),
            "max_storage_size_gb": st.get("max_storage_size_gb", 500),
            "retention_days": st.get("retention_days", 30),
            "auto_cleanup": st.get("auto_cleanup", True),
            "storage_compression_enabled": st.get("compression_enabled", True),
            "storage_encryption_enabled": st.get("encryption_enabled", False),
        })
    
    # Handle quality_control section
    if "quality_control" in yaml_data:
        qc = yaml_data["quality_control"]
        flattened.update({
            "quality_control_enabled": qc.get("enabled", True),
            "min_quality_score": qc.get("min_quality_score", 0.7),
            "validate_chunks": qc.get("validate_chunks", True),
            "validate_audio_sync": qc.get("validate_audio_sync", True),
            "validate_video_integrity": qc.get("validate_video_integrity", True),
            "auto_adjust_quality": qc.get("auto_adjust_quality", False),
        })
    
    # Handle monitoring section
    if "monitoring" in yaml_data:
        mon = yaml_data["monitoring"]
        flattened.update({
            "monitoring_enabled": mon.get("enabled", True),
        })
        if "health_check" in mon:
            hc = mon["health_check"]
            flattened.update({
                "health_check_enabled": hc.get("enabled", True),
                "health_check_interval_seconds": hc.get("interval_seconds", 30),
                "health_check_timeout_seconds": hc.get("timeout_seconds", 10),
            })
    
    # Handle error_handling section
    if "error_handling" in yaml_data:
        eh = yaml_data["error_handling"]
        if "retry" in eh:
            ret = eh["retry"]
            flattened.update({
                "retry_enabled": ret.get("enabled", True),
                "max_retries": ret.get("max_retries", 3),
                "retry_delay_seconds": ret.get("retry_delay_seconds", 5),
                "exponential_backoff": ret.get("exponential_backoff", True),
            })
        if "recovery" in eh:
            rec = eh["recovery"]
            flattened.update({
                "recovery_enabled": rec.get("enabled", True),
                "auto_recovery": rec.get("auto_recovery", True),
                "recovery_timeout_seconds": rec.get("recovery_timeout_seconds", 60),
                "preserve_partial_recordings": rec.get("preserve_partial_recordings", True),
            })
    
    # Handle security section
    if "security" in yaml_data:
        sec = yaml_data["security"]
        if "access_control" in sec:
            ac = sec["access_control"]
            flattened.update({
                "require_authentication": ac.get("require_authentication", True),
                "require_authorization": ac.get("require_authorization", True),
                "allowed_roles": ac.get("allowed_roles", ["USER", "NODE_OPERATOR", "ADMIN", "SUPER_ADMIN"]),
            })
        if "data_privacy" in sec:
            dp = sec["data_privacy"]
            flattened.update({
                "encrypt_recordings": dp.get("encrypt_recordings", False),
                "mask_sensitive_data": dp.get("mask_sensitive_data", False),
                "audit_log_enabled": dp.get("audit_log_enabled", True),
                "audit_log_retention_days": dp.get("audit_log_retention_days", 90),
            })
    
    # Handle network section
    if "network" in yaml_data:
        net = yaml_data["network"]
        flattened.update({
            "host": net.get("host", "0.0.0.0"),
            "port": net.get("port", 8090),
        })
    
    return flattened

