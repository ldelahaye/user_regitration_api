import logging
import logging.config
from typing import Any


def setup_logging(*, debug: bool = False) -> None:
    """Configure structured logging for the application."""
    log_level = "DEBUG" if debug else "INFO"

    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "format": (
                    "%(asctime)s | %(levelname)-8s | %(name)s | correlation_id=%(correlation_id)s | %(message)s"
                ),
                "datefmt": "%Y-%m-%dT%H:%M:%S%z",
                "defaults": {"correlation_id": "-"},
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "structured",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
        "loggers": {
            "app": {
                "level": log_level,
                "propagate": True,
            },
            "uvicorn": {
                "level": "INFO",
                "propagate": True,
            },
            "uvicorn.access": {
                "level": "WARNING",
                "propagate": True,
            },
        },
    }

    logging.config.dictConfig(config)
