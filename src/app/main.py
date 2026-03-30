import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.middlewares.logging import LoggingMiddleware
from app.api.routers.users import router as users_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.infrastructure.database.client import close_pool, init_pool
from app.infrastructure.database.migrations import run_migrations
from app.infrastructure.email.client import create_email_service
from app.infrastructure.email.templates import load_templates

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging(debug=settings.debug)
    pool = await init_pool(
        settings.database_url,
        min_size=settings.database_min_pool_size,
        max_size=settings.database_max_pool_size,
    )
    app.state.db_pool = pool
    app.state.email_service = create_email_service(settings)
    await app.state.email_service.check_connectivity()
    load_templates()
    await run_migrations(pool)
    logger.info("Application startup complete")
    yield
    await app.state.email_service.close()
    await close_pool(app.state.db_pool)
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)
register_exception_handlers(app)
app.include_router(users_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}
