"""Structured logging system for TurbineGuard simulation, controller, and verification."""

import logging
import sys
from datetime import datetime, timezone
from typing import Any


class StructuredFormatter(logging.Formatter):
    """Formats log records as structured, human-readable or JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        sim_id = getattr(record, "sim_id", "GLOBAL")
        state = getattr(record, "state", "---")
        fault = getattr(record, "fault", "NONE")
        action = getattr(record, "action", "---")
        
        base_msg = record.getMessage()
        return (
            f"[{timestamp}] [{record.levelname:^7}] [SIM:{sim_id}] "
            f"[STATE:{state}] [FAULT:{fault}] [ACTION:{action}] -> {base_msg}"
        )


def setup_logger(
    name: str = "turbineguard",
    level: int = logging.INFO,
    log_file: str | None = None
) -> logging.Logger:
    """Configures and returns a structured logger."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(StructuredFormatter())
        logger.addHandler(console_handler)
        
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(StructuredFormatter())
            logger.addHandler(file_handler)
            
    return logger


def log_event(
    logger: logging.Logger,
    level: int,
    message: str,
    sim_id: str = "SIM-001",
    state: str = "NORMAL",
    fault: str = "NONE",
    action: str = "MONITOR",
    **extra_fields: Any
) -> None:
    """Helper to emit structured log entries with rich engineering telemetry."""
    extra = {
        "sim_id": sim_id,
        "state": state,
        "fault": fault,
        "action": action,
        **extra_fields
    }
    logger.log(level, message, extra=extra)
