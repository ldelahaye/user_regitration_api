from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    with (
        patch("app.main.init_pool", new_callable=AsyncMock) as mock_init,
        patch("app.main.run_migrations", new_callable=AsyncMock),
        patch("app.main.close_pool", new_callable=AsyncMock),
        patch("app.main.create_email_service", return_value=AsyncMock()),
        patch("app.main.load_templates"),
    ):
        mock_init.return_value = AsyncMock()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
