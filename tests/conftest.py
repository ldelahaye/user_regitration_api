from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    mock_conn = AsyncMock()
    mock_pool = AsyncMock()

    @asynccontextmanager
    async def _mock_acquire():  # type: ignore[no-untyped-def]
        yield mock_conn

    mock_pool.acquire = _mock_acquire
    with (
        patch("app.main.init_pool", new_callable=AsyncMock),
        patch("app.main.run_migrations", new_callable=AsyncMock),
        patch("app.main.close_pool", new_callable=AsyncMock),
        patch("app.main.create_email_service", return_value=AsyncMock()),
        patch("app.main.load_templates"),
    ):
        app.state.db_pool = mock_pool
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
