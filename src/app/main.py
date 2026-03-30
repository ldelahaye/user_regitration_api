import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.middlewares.logging import LoggingMiddleware
from app.core.config import settings
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging(debug=settings.debug)
    logger.info("Application startup complete")
    yield
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}
