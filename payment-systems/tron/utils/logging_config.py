"""
LUCID Payment Systems - TRON Client Structured Logging Configuration
Structured JSON logging setup for tron-client service
Following architecture patterns from build/docs/
"""

import os
import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """Structured JSON log formatter"""
    
    def __init__(self, include_trace_id: bool = True):
        super().__init__()
        self.include_trace_id = include_trace_id
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add trace ID if available
        if self.include_trace_id and hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


def setup_structured_logging(
    log_level: Optional[str] = None,
    log_format: str = "json",
    log_file: Optional[str] = None,
    include_trace_id: bool = True
):
    """
    Setup structured logging for tron-client service
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format ("json" or "text")
        log_file: Log file path (optional)
        include_trace_id: Include trace ID in logs
    """
    # Get log level from environment or default
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO")
    
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Setup formatter
    if log_format.lower() == "json":
        formatter = StructuredFormatter(include_trace_id=include_trace_id)
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        root_logger.addHandler(file_handler)
    
    # Set root logger level
    root_logger.setLevel(level)
    
    # Configure third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("tronpy").setLevel(logging.WARNING)
    
    logging.info(f"Structured logging configured: level={log_level}, format={log_format}")


def add_trace_id(logger: logging.Logger, trace_id: str):
    """Add trace ID to logger context"""
    # This would typically use contextvars or similar
    # For now, we'll use a custom attribute
    for handler in logger.handlers:
        if isinstance(handler.formatter, StructuredFormatter):
            # Store trace ID in record
            pass

