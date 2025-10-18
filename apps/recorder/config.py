#!/usr/bin/env python3
"""
Configuration Module for Lucid RDP Recorder
"""

import os
from typing import Optional
from pydantic import BaseModel, Field, validator
from pathlib import Path


class RecorderConfig(BaseModel):
    """Configuration for the Lucid RDP Recorder"""
    
    # Recording settings
    resolution: str = Field(default="1920x1080", description="Recording resolution")
    fps: int = Field(default=30, description="Frames per second")
    bitrate: int = Field(default=2000000, description="Video bitrate in bps")
    capture_audio: bool = Field(default=True, description="Enable audio capture")
    audio_sample_rate: int = Field(default=44100, description="Audio sample rate")
    audio_channels: int = Field(default=2, description="Audio channels")
    
    # Chunking settings
    chunk_size_mb: int = Field(default=10, description="Chunk size in MB")
    compression_level: int = Field(default=6, description="Compression level (0-9)")
    
    # Database settings
    mongo_url: str = Field(
        default="mongodb://lucid:lucid@localhost:27017/lucid?authSource=admin",
        description="MongoDB connection URL"
    )
    
    # Blockchain settings
    blockchain_rpc_url: str = Field(
        default="http://localhost:8545",
        description="Blockchain RPC URL"
    )
    anchors_contract_address: Optional[str] = Field(
        default=None,
        description="Anchors contract address"
    )
    
    # Storage settings
    storage_path: str = Field(
        default="/opt/lucid/storage",
        description="Storage path for recordings"
    )
    max_storage_gb: int = Field(
        default=100,
        description="Maximum storage in GB"
    )
    
    # Security settings
    encryption_enabled: bool = Field(default=True, description="Enable encryption")
    key_rotation_hours: int = Field(default=24, description="Key rotation interval in hours")
    
    # Performance settings
    max_concurrent_sessions: int = Field(default=4, description="Maximum concurrent sessions")
    cpu_limit_percent: int = Field(default=80, description="CPU usage limit percentage")
    memory_limit_mb: int = Field(default=2048, description="Memory limit in MB")
    
    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    log_rotation_size_mb: int = Field(default=100, description="Log rotation size in MB")
    log_retention_days: int = Field(default=30, description="Log retention in days")
    
    # Network settings
    bind_address: str = Field(default="0.0.0.0", description="Bind address")
    port: int = Field(default=8084, description="Recorder service port")
    
    # Hardware settings
    hardware_encoder: str = Field(
        default="h264_v4l2m2m",
        description="Hardware encoder to use"
    )
    gpu_memory_mb: int = Field(
        default=256,
        description="GPU memory allocation in MB"
    )
    
    @validator('resolution')
    def validate_resolution(cls, v):
        """Validate resolution format"""
        try:
            width, height = map(int, v.split('x'))
            if width <= 0 or height <= 0:
                raise ValueError("Resolution must be positive")
            return v
        except (ValueError, AttributeError):
            raise ValueError("Resolution must be in format 'WIDTHxHEIGHT'")
    
    @validator('fps')
    def validate_fps(cls, v):
        """Validate FPS"""
        if v <= 0 or v > 120:
            raise ValueError("FPS must be between 1 and 120")
        return v
    
    @validator('bitrate')
    def validate_bitrate(cls, v):
        """Validate bitrate"""
        if v <= 0:
            raise ValueError("Bitrate must be positive")
        return v
    
    @validator('chunk_size_mb')
    def validate_chunk_size(cls, v):
        """Validate chunk size"""
        if v <= 0 or v > 1000:
            raise ValueError("Chunk size must be between 1 and 1000 MB")
        return v
    
    @validator('compression_level')
    def validate_compression_level(cls, v):
        """Validate compression level"""
        if v < 0 or v > 9:
            raise ValueError("Compression level must be between 0 and 9")
        return v
    
    @validator('audio_sample_rate')
    def validate_audio_sample_rate(cls, v):
        """Validate audio sample rate"""
        valid_rates = [8000, 16000, 22050, 44100, 48000, 96000]
        if v not in valid_rates:
            raise ValueError(f"Audio sample rate must be one of {valid_rates}")
        return v
    
    @validator('audio_channels')
    def validate_audio_channels(cls, v):
        """Validate audio channels"""
        if v < 1 or v > 8:
            raise ValueError("Audio channels must be between 1 and 8")
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()
    
    @validator('max_concurrent_sessions')
    def validate_max_sessions(cls, v):
        """Validate max concurrent sessions"""
        if v <= 0 or v > 16:
            raise ValueError("Max concurrent sessions must be between 1 and 16")
        return v
    
    @validator('cpu_limit_percent')
    def validate_cpu_limit(cls, v):
        """Validate CPU limit"""
        if v <= 0 or v > 100:
            raise ValueError("CPU limit must be between 1 and 100 percent")
        return v
    
    @validator('memory_limit_mb')
    def validate_memory_limit(cls, v):
        """Validate memory limit"""
        if v <= 0:
            raise ValueError("Memory limit must be positive")
        return v
    
    @validator('key_rotation_hours')
    def validate_key_rotation(cls, v):
        """Validate key rotation interval"""
        if v <= 0:
            raise ValueError("Key rotation interval must be positive")
        return v
    
    @validator('max_storage_gb')
    def validate_max_storage(cls, v):
        """Validate max storage"""
        if v <= 0:
            raise ValueError("Max storage must be positive")
        return v
    
    @validator('log_rotation_size_mb')
    def validate_log_rotation_size(cls, v):
        """Validate log rotation size"""
        if v <= 0:
            raise ValueError("Log rotation size must be positive")
        return v
    
    @validator('log_retention_days')
    def validate_log_retention(cls, v):
        """Validate log retention"""
        if v <= 0:
            raise ValueError("Log retention must be positive")
        return v
    
    @validator('gpu_memory_mb')
    def validate_gpu_memory(cls, v):
        """Validate GPU memory allocation"""
        if v <= 0:
            raise ValueError("GPU memory allocation must be positive")
        return v
    
    @classmethod
    def from_env(cls) -> 'RecorderConfig':
        """Create configuration from environment variables"""
        return cls(
            resolution=os.getenv('RECORDER_RESOLUTION', '1920x1080'),
            fps=int(os.getenv('RECORDER_FPS', '30')),
            bitrate=int(os.getenv('RECORDER_BITRATE', '2000000')),
            capture_audio=os.getenv('RECORDER_CAPTURE_AUDIO', 'true').lower() == 'true',
            audio_sample_rate=int(os.getenv('RECORDER_AUDIO_SAMPLE_RATE', '44100')),
            audio_channels=int(os.getenv('RECORDER_AUDIO_CHANNELS', '2')),
            chunk_size_mb=int(os.getenv('RECORDER_CHUNK_SIZE_MB', '10')),
            compression_level=int(os.getenv('RECORDER_COMPRESSION_LEVEL', '6')),
            mongo_url=os.getenv('MONGO_URL', 'mongodb://lucid:lucid@localhost:27017/lucid?authSource=admin'),
            blockchain_rpc_url=os.getenv('BLOCKCHAIN_RPC_URL', 'http://localhost:8545'),
            anchors_contract_address=os.getenv('ANCHORS_CONTRACT_ADDRESS'),
            storage_path=os.getenv('RECORDER_STORAGE_PATH', '/opt/lucid/storage'),
            max_storage_gb=int(os.getenv('RECORDER_MAX_STORAGE_GB', '100')),
            encryption_enabled=os.getenv('RECORDER_ENCRYPTION_ENABLED', 'true').lower() == 'true',
            key_rotation_hours=int(os.getenv('RECORDER_KEY_ROTATION_HOURS', '24')),
            max_concurrent_sessions=int(os.getenv('RECORDER_MAX_CONCURRENT_SESSIONS', '4')),
            cpu_limit_percent=int(os.getenv('RECORDER_CPU_LIMIT_PERCENT', '80')),
            memory_limit_mb=int(os.getenv('RECORDER_MEMORY_LIMIT_MB', '2048')),
            log_level=os.getenv('RECORDER_LOG_LEVEL', 'INFO'),
            log_file=os.getenv('RECORDER_LOG_FILE'),
            log_rotation_size_mb=int(os.getenv('RECORDER_LOG_ROTATION_SIZE_MB', '100')),
            log_retention_days=int(os.getenv('RECORDER_LOG_RETENTION_DAYS', '30')),
            bind_address=os.getenv('RECORDER_BIND_ADDRESS', '0.0.0.0'),
            port=int(os.getenv('RECORDER_PORT', '8084')),
            hardware_encoder=os.getenv('RECORDER_HARDWARE_ENCODER', 'h264_v4l2m2m'),
            gpu_memory_mb=int(os.getenv('RECORDER_GPU_MEMORY_MB', '256'))
        )
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary"""
        return self.dict()
    
    def save_to_file(self, file_path: str):
        """Save configuration to file"""
        import json
        
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'RecorderConfig':
        """Load configuration from file"""
        import json
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        return cls(**data)
    
    def create_directories(self):
        """Create necessary directories"""
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)
        
        if self.log_file:
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
