"""Request logging middleware with async-safe correlation ID propagation.

Uses contextvars.ContextVar to store the correlation ID per async context,
and a single logging.Filter installed at startup to inject it into all log records.
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.logging import _UUID_RE, CORRELATION_ID_HEADER, correlation_id_var

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs every request with method, path, status and duration.

    Sets the correlation ID in the ContextVar for the duration of the request.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        raw = request.headers.get(CORRELATION_ID_HEADER, "")
        cid = raw if _UUID_RE.match(raw) else str(uuid.uuid4())
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
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "error_code": "INTERNAL_ERROR"},
                headers={CORRELATION_ID_HEADER: cid},
            )
        else:
            duration_ms = (time.monotonic() - start_time) * 1000
            response.headers[CORRELATION_ID_HEADER] = cid
            logger.info(
                "%s %s %d %.2fms",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
            return response
        finally:
            correlation_id_var.reset(token)
