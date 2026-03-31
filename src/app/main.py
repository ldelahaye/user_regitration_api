import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.middlewares.logging import LoggingMiddleware
from app.api.routers.users import router as users_router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.infrastructure.database.client import close_pool, init_pool
from app.infrastructure.database.migrations import run_migrations
from app.infrastructure.email.client import create_email_service
from app.infrastructure.email.templates import load_templates

logger = logging.getLogger(__name__)

_INSECURE_HMAC_DEFAULT = "change-me-in-production"


@asynccontextmanager
async def _startup_phase(description: str) -> AsyncIterator[None]:
    """Log a structured error and re-raise if a startup phase fails."""
    try:
        yield
    except Exception:
        logger.error("Startup failed: %s", description, exc_info=True)
        raise


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging(debug=settings.debug)

    if settings.email_mock:
        logger.warning("SECURITY: email_mock is enabled — emails will NOT be sent")

    if settings.hmac_secret.get_secret_value() == _INSECURE_HMAC_DEFAULT and not settings.debug:
        raise RuntimeError("APP_HMAC_SECRET is set to the default value — set a strong secret before deploying")

    async with _startup_phase("database pool initialization"):
        pool = await init_pool(
            settings.database_url.get_secret_value(),
            min_size=settings.database_min_pool_size,
            max_size=settings.database_max_pool_size,
        )
    app.state.db_pool = pool

    async with _startup_phase("email service"):
        app.state.email_service = create_email_service(settings)
        await app.state.email_service.check_connectivity()

    async with _startup_phase("email templates"):
        load_templates()

    async with _startup_phase("database migrations"):
        await run_migrations(pool)

    logger.info("Application startup complete")
    yield
    if email_service := getattr(app.state, "email_service", None):
        await email_service.close()
    if db_pool := getattr(app.state, "db_pool", None):
        await close_pool(db_pool)
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)
if settings.cors_allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
    )
register_exception_handlers(app)
app.include_router(users_router)


@app.get("/health", response_model=dict[str, str], status_code=status.HTTP_200_OK)
async def health_check(request: Request) -> dict[str, str]:
    try:
        async with request.app.state.db_pool.acquire() as conn:
            await conn.execute("SELECT 1")
    except Exception:
        logger.warning("Health check failed: database unreachable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unreachable",
        ) from None
    return {"status": "healthy"}
