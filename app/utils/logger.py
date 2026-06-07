"""Logging configuration for the Insurance Claims Agent.

Format: [TIMESTAMP] [LEVEL] [module] - message
Console logging is always available; file logging is best-effort so a read-only
or full filesystem never crashes the app.
"""
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FORMATTER = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(module)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def setup_logger(name: str = "InsuranceAgent") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if logger.handlers:  # avoid duplicate handlers on re-import
        return logger

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(_FORMATTER)
    logger.addHandler(console_handler)

    # Best-effort rotating file handler.
    try:
        Path("logs").mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d")
        file_handler = RotatingFileHandler(
            f"logs/agent_{timestamp}.log",
            maxBytes=5_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(_FORMATTER)
        logger.addHandler(file_handler)
    except OSError as e:
        logger.warning("File logging disabled (%s); using console only.", e)

    return logger


# Global logger instance
logger = setup_logger()
