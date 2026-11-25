import logging
import sys
from typing import Any, Dict


class StructuredFormatter(logging.Formatter):
    """
    Structured log formatter outputting timestamp, level, logger name, and message.
    """

    FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self):
        super().__init__(fmt=self.FORMAT, datefmt=self.DATE_FORMAT)

    def format(self, record: logging.LogRecord) -> str:
        # Standardize extra structured context if present
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            extra_str = " | extra=" + str(record.extra_data)
            record.msg = f"{record.msg}{extra_str}"
        return super().format(record)


def setup_logging(debug: bool = False) -> None:
    """
    Configures application-wide logging handlers and log levels.
    """
    log_level = logging.DEBUG if debug else logging.INFO

    # Root handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = [handler]

    # Suppress overly noisy external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("groq").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger instance for a given module.
    """
    return logging.getLogger(name)
