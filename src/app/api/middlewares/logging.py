"""Request logging middleware with async-safe correlation ID propagation.

Uses contextvars.ContextVar to store the correlation ID per async context,
and a single logging.Filter installed at startup to inject it into all log records.
"""

import logging
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

CORRELATION_ID_HEADER = "X-Correlation-ID"

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="-")


class CorrelationIdFilter(logging.Filter):
    """Injects correlation_id from the current async context into every log record.

    Install once at startup via setup_logging — never add/remove per request.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get()
        return True


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs every request with method, path, status and duration.

    Sets the correlation ID in the ContextVar for the duration of the request.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        cid = request.headers.get(CORRELATION_ID_HEADER, str(uuid.uuid4()))
        token = correlation_id_var.set(cid)
        request.state.correlation_id = cid

        start_time = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "%s %s 500 %.2fms",
                request.method,
                request.url.path,
                duration_ms,
            )
            raise
        finally:
            correlation_id_var.reset(token)

        duration_ms = (time.monotonic() - start_time) * 1000
        response.headers[CORRELATION_ID_HEADER] = cid

        token = correlation_id_var.set(cid)
        logger.info(
            "%s %s %d %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        correlation_id_var.reset(token)

        return response
