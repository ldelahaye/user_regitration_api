from httpx import AsyncClient

from app.api.middlewares.logging import CORRELATION_ID_HEADER


async def test_response_contains_correlation_id(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert CORRELATION_ID_HEADER in response.headers
    assert len(response.headers[CORRELATION_ID_HEADER]) > 0


async def test_correlation_id_is_propagated_from_request(client: AsyncClient) -> None:
    custom_id = "test-correlation-123"
    response = await client.get("/health", headers={CORRELATION_ID_HEADER: custom_id})

    assert response.status_code == 200
    assert response.headers[CORRELATION_ID_HEADER] == custom_id


async def test_unique_correlation_id_per_request(client: AsyncClient) -> None:
    response_1 = await client.get("/health")
    response_2 = await client.get("/health")

    id_1 = response_1.headers[CORRELATION_ID_HEADER]
    id_2 = response_2.headers[CORRELATION_ID_HEADER]
    assert id_1 != id_2
