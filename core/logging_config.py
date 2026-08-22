"""
Kaihara OS Logging Configuration.
Replaces print() with proper logging framework.
"""

import logging
import sys

LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "INFO"):
    """Configure logging for Kaihara OS."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Remove existing handlers
    root = logging.getLogger()
    root.handlers = []

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    root.addHandler(handler)
    root.setLevel(log_level)

    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return logging.getLogger("kaihara")


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a module."""
    return logging.getLogger(name)
