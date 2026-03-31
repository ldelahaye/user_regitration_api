import logging
import logging.config
import re
from contextvars import ContextVar
from typing import Any

CORRELATION_ID_HEADER = "X-Correlation-ID"

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="-")

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class CorrelationIdFilter(logging.Filter):
    """Injects correlation_id from the current async context into every log record.

    Install once at startup via setup_logging — never add/remove per request.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get()
        return True


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
    logging.getLogger().addFilter(CorrelationIdFilter())
