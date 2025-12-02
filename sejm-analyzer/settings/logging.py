"""Logging configuration."""

import sys

from loguru import logger

from settings import LOG_DIR


def setup_logging(level: str = "INFO", to_file: bool = True):
    """Configure logging with console and optional file output."""
    logger.remove()

    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | <level>{message}</level>",
        level=level,
        colorize=True,
    )

    if to_file:
        LOG_DIR.mkdir(exist_ok=True)
        logger.add(
            LOG_DIR / "sejm_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <7} | {name}:{function}:{line} | {message}",
            level="DEBUG",
            rotation="00:00",
            retention="7 days",
            compression="gz",
        )
        logger.info("Logging to {}", LOG_DIR)

    return logger
