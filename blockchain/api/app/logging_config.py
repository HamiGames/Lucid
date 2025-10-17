"""
Logging Configuration Module

This module contains logging configuration and utilities for the Blockchain API.
Handles structured logging, log formatting, and log levels.
"""

import logging
import logging.config
import sys
import json
from typing import Dict, Any, Optional
from datetime import datetime
import structlog
from structlog.stdlib import LoggerFactory

def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Set up logging configuration for the application."""
    
    # Configure structlog
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
            structlog.processors.JSONRenderer() if log_format == "json" else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Standard logging configuration
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "json": {
                "()": "structlog.stdlib.ProcessorFormatter",
                "processor": structlog.processors.JSONRenderer()
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "standard" if log_format != "json" else "json",
                "stream": sys.stdout
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "detailed",
                "filename": "logs/blockchain_api.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": "logs/blockchain_api_errors.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            }
        },
        "loggers": {
            "": {  # Root logger
                "level": log_level,
                "handlers": ["console", "file"],
                "propagate": False
            },
            "blockchain_api": {
                "level": log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            }
        }
    }
    
    # Apply logging configuration
    logging.config.dictConfig(logging_config)
    
    # Set up specific loggers
    logger = logging.getLogger("blockchain_api")
    logger.info(f"Logging configured with level: {log_level}, format: {log_format}")

class RequestLogger:
    """Request logger for API endpoints."""
    
    def __init__(self):
        self.logger = structlog.get_logger("blockchain_api.requests")
    
    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        response_time: float,
        client_ip: str,
        user_agent: Optional[str] = None,
        user_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log API request details."""
        log_data = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "response_time_ms": round(response_time * 1000, 2),
            "client_ip": client_ip,
            "timestamp": datetime.now().isoformat()
        }
        
        if user_agent:
            log_data["user_agent"] = user_agent
        
        if user_id:
            log_data["user_id"] = user_id
        
        if additional_data:
            log_data.update(additional_data)
        
        # Log based on status code
        if status_code >= 500:
            self.logger.error("API request error", **log_data)
        elif status_code >= 400:
            self.logger.warning("API request client error", **log_data)
        else:
            self.logger.info("API request", **log_data)

class SecurityLogger:
    """Security logger for authentication and authorization events."""
    
    def __init__(self):
        self.logger = structlog.get_logger("blockchain_api.security")
    
    def log_authentication_success(self, user_id: str, method: str, client_ip: str):
        """Log successful authentication."""
        self.logger.info(
            "Authentication successful",
            user_id=user_id,
            method=method,
            client_ip=client_ip,
            timestamp=datetime.now().isoformat()
        )
    
    def log_authentication_failure(self, username: str, method: str, client_ip: str, reason: str):
        """Log failed authentication."""
        self.logger.warning(
            "Authentication failed",
            username=username,
            method=method,
            client_ip=client_ip,
            reason=reason,
            timestamp=datetime.now().isoformat()
        )
    
    def log_authorization_failure(self, user_id: str, resource: str, action: str, client_ip: str):
        """Log authorization failure."""
        self.logger.warning(
            "Authorization failed",
            user_id=user_id,
            resource=resource,
            action=action,
            client_ip=client_ip,
            timestamp=datetime.now().isoformat()
        )
    
    def log_rate_limit_exceeded(self, client_ip: str, endpoint: str, limit: int, window: int):
        """Log rate limit exceeded."""
        self.logger.warning(
            "Rate limit exceeded",
            client_ip=client_ip,
            endpoint=endpoint,
            limit=limit,
            window=window,
            timestamp=datetime.now().isoformat()
        )
    
    def log_suspicious_activity(self, client_ip: str, activity_type: str, details: Dict[str, Any]):
        """Log suspicious activity."""
        self.logger.warning(
            "Suspicious activity detected",
            client_ip=client_ip,
            activity_type=activity_type,
            details=details,
            timestamp=datetime.now().isoformat()
        )

class BlockchainLogger:
    """Blockchain-specific logger for blockchain operations."""
    
    def __init__(self):
        self.logger = structlog.get_logger("blockchain_api.blockchain")
    
    def log_block_creation(self, block_height: int, block_hash: str, validator: str, tx_count: int):
        """Log block creation."""
        self.logger.info(
            "Block created",
            block_height=block_height,
            block_hash=block_hash,
            validator=validator,
            transaction_count=tx_count,
            timestamp=datetime.now().isoformat()
        )
    
    def log_transaction_submission(self, tx_id: str, tx_type: str, client_ip: str):
        """Log transaction submission."""
        self.logger.info(
            "Transaction submitted",
            tx_id=tx_id,
            tx_type=tx_type,
            client_ip=client_ip,
            timestamp=datetime.now().isoformat()
        )
    
    def log_session_anchoring(self, session_id: str, anchoring_id: str, client_ip: str):
        """Log session anchoring."""
        self.logger.info(
            "Session anchoring initiated",
            session_id=session_id,
            anchoring_id=anchoring_id,
            client_ip=client_ip,
            timestamp=datetime.now().isoformat()
        )
    
    def log_consensus_vote(self, vote_id: str, node_id: str, block_hash: str, vote: str):
        """Log consensus vote."""
        self.logger.info(
            "Consensus vote submitted",
            vote_id=vote_id,
            node_id=node_id,
            block_hash=block_hash,
            vote=vote,
            timestamp=datetime.now().isoformat()
        )
    
    def log_merkle_tree_operation(self, operation: str, root_hash: str, leaf_count: int):
        """Log Merkle tree operation."""
        self.logger.info(
            "Merkle tree operation",
            operation=operation,
            root_hash=root_hash,
            leaf_count=leaf_count,
            timestamp=datetime.now().isoformat()
        )

class PerformanceLogger:
    """Performance logger for monitoring and metrics."""
    
    def __init__(self):
        self.logger = structlog.get_logger("blockchain_api.performance")
    
    def log_slow_request(self, method: str, path: str, response_time: float, threshold: float = 1.0):
        """Log slow requests."""
        if response_time > threshold:
            self.logger.warning(
                "Slow request detected",
                method=method,
                path=path,
                response_time_ms=round(response_time * 1000, 2),
                threshold_ms=threshold * 1000,
                timestamp=datetime.now().isoformat()
            )
    
    def log_high_error_rate(self, endpoint: str, error_rate: float, threshold: float = 0.1):
        """Log high error rates."""
        if error_rate > threshold:
            self.logger.warning(
                "High error rate detected",
                endpoint=endpoint,
                error_rate=error_rate,
                threshold=threshold,
                timestamp=datetime.now().isoformat()
            )
    
    def log_system_metrics(self, metrics: Dict[str, Any]):
        """Log system performance metrics."""
        self.logger.info(
            "System metrics",
            **metrics,
            timestamp=datetime.now().isoformat()
        )
    
    def log_blockchain_metrics(self, metrics: Dict[str, Any]):
        """Log blockchain performance metrics."""
        self.logger.info(
            "Blockchain metrics",
            **metrics,
            timestamp=datetime.now().isoformat()
        )

# Global logger instances
request_logger = RequestLogger()
security_logger = SecurityLogger()
blockchain_logger = BlockchainLogger()
performance_logger = PerformanceLogger()

def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)

def log_exception(logger: structlog.BoundLogger, exception: Exception, context: Optional[Dict[str, Any]] = None):
    """Log an exception with context."""
    log_data = {
        "exception_type": type(exception).__name__,
        "exception_message": str(exception),
        "timestamp": datetime.now().isoformat()
    }
    
    if context:
        log_data.update(context)
    
    logger.error("Exception occurred", **log_data, exc_info=True)
