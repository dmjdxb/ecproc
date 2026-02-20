"""Structured logging with Rich."""

from __future__ import annotations

import logging

from rich.logging import RichHandler


def get_logger(name: str, *, level: int = logging.INFO) -> logging.Logger:
    """Get a structured logger with Rich formatting.

    Args:
        name: Logger name (typically __name__).
        level: Logging level.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = RichHandler(rich_tracebacks=True, markup=True)
        handler.setLevel(level)
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger
