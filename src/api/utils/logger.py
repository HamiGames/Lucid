# Path: src/api/utils/logger.py
# Structured logging via stdlib; JSON-friendly format.

import json
import logging
import sys
from typing import Any, Dict


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
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger
