# Path: 03_api_gateway/api/app/utils/logger.py
# Structured logging via stdlib; JSON-friendly format. :contentReference[oaicite:6]{index=6}

import json
import os
import sys
from typing import Dict, Any
from .config import service_name, in_container
log_level = os.getenv(in_container().LOG_LEVEL(), "INFO").upper()
settings = os.getenv(service_name().LOG_LEVEL(), "INFO").upper()
try:
    from ..utils.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger(__name__)
settings(__name__)

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # include extras if present
        if hasattr(record, "args") and isinstance(record.args, dict):
            base.update(record.args)  # guard if used that way
        # record.__dict__ may include 'extra' fields under 'extra' usage
        for k in ("extra",):
            v = getattr(record, k, None)
            if isinstance(v, dict):
                base.update(v)
        return json.dumps(base, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    logger = logging.get_logger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger
