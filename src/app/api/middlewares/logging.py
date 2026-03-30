import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

CORRELATION_ID_HEADER = "X-Correlation-ID"


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs every request with method, path, status and duration.

    Generates a correlation ID per request for distributed tracing.
    The ID is stored in request.state, added to log records via a filter,
    and returned in the response headers.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get(CORRELATION_ID_HEADER, str(uuid.uuid4()))
        request.state.correlation_id = correlation_id

        log_filter = _CorrelationIdFilter(correlation_id)
        root_logger = logging.getLogger()
        root_logger.addFilter(log_filter)

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
            root_logger.removeFilter(log_filter)

        duration_ms = (time.monotonic() - start_time) * 1000
        response.headers[CORRELATION_ID_HEADER] = correlation_id

        # Re-add filter briefly for the log statement
        root_logger.addFilter(log_filter)
        logger.info(
            "%s %s %d %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        root_logger.removeFilter(log_filter)

        return response


class _CorrelationIdFilter(logging.Filter):
    """Injects correlation_id into every log record."""

    def __init__(self, correlation_id: str) -> None:
        super().__init__()
        self.correlation_id = correlation_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = self.correlation_id
        return True
