"""
Logging configuration using Loguru.
"""
import logging
import sys
from typing import Any

from loguru import logger


class InterceptHandler(logging.Handler):
    """Handler that intercepts standard logging and redirects to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record by redirecting to Loguru.

        Args:
            record: The log record from standard logging.
        """
        # Get corresponding Loguru level if it exists
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame = logging.currentframe()
        depth = 2
        while frame is not None and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """
    Configure logging with Loguru.

    This function:
    1. Removes existing handlers
    2. Intercepts standard library logging
    3. Configures Loguru with console and file sinks
    """
    # Remove all existing handlers
    logging.root.handlers = []

    # Intercept everything that goes to standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0)

    # Specific interception for Uvicorn
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False

    # Configure Loguru
    logger.remove()  # Remove default handler

    # Patcher to ensure request_id exists in extra context
    def add_request_id(record: dict[str, Any]) -> None:
        record["extra"].setdefault("request_id", "N/A")

    logger.configure(patcher=add_request_id)

    # Console Sink
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<magenta>{extra[request_id]}</magenta> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        level="INFO",
    )

    # File Sink
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        enqueue=True,
        level="INFO",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{extra[request_id]} | {name}:{function}:{line} - {message}"
        ),
    )
