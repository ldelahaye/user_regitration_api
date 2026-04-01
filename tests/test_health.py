from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.main import app


async def test_health_check_healthy(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["components"]["database"] == "up"
    assert data["components"]["email"] == "up"


async def test_health_check_degraded_when_email_down(client: AsyncClient) -> None:
    app.state.email_service.is_available = AsyncMock(return_value=False)
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["components"]["database"] == "up"
    assert data["components"]["email"] == "down"


async def test_health_check_503_when_database_down(client: AsyncClient) -> None:
    @asynccontextmanager
    async def _failing_acquire():  # type: ignore[no-untyped-def]
        raise ConnectionError("connection refused")
        yield  # pragma: no cover

    app.state.db_pool.acquire = _failing_acquire
    response = await client.get("/health")
    assert response.status_code == 503
